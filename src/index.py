"""Chunk, embed and store all three channels in a single table.

Mirrors what the course does inside Snowflake:

    SPLIT_TEXT_RECURSIVE_CHARACTER    ->  segment aligned chunking
    AI_EMBED('snowflake-arctic-embed-m')  ->  the same model from HuggingFace
    unified table + VECTOR_COSINE_SIMILARITY  ->  DuckDB

The embedding model is literally the one running inside Cortex, so vectors from
either engine are comparable. That is testable, and the test is worth more than
any paragraph in the README.
"""
import json
import sys
from pathlib import Path

import duckdb
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import documents
from teach import recap

HERE = Path(__file__).resolve().parent.parent
DB = HERE / "out/meetings.duckdb"
MODEL = "Snowflake/snowflake-arctic-embed-m"   # the same id AI_EMBED takes
CHUNK_SIZE, OVERLAP = 500, 50                  # the values lab_2 uses


def hhmmss(sec):
    s = int(sec)
    return "%02d:%02d:%02d" % (s // 3600, (s % 3600) // 60, s % 60)


def build(parts="abcd"):
    rows = []

    for part in parts:
        tpath = HERE / "out" / ("ES2008%s.transcript.json" % part)
        if not tpath.exists():
            continue

        # --- AUDIO: chunks built out of the segments themselves ---
        # Accumulating segments until the chunk fills gives exact timestamps.
        # Splitting the joined text and then locating each chunk with find()
        # returns wrong timestamps whenever a phrase repeats in the meeting.
        segs = json.loads(tpath.read_text())["segments"]
        buf, start = [], None
        for s in segs:
            if start is None:
                start = s["start"]
            buf.append(s)
            size = sum(len(x["text"]) + 1 for x in buf)
            if size >= CHUNK_SIZE:
                text = " ".join(x["text"] for x in buf)
                rows.append(("AUDIO", part, start, buf[-1]["end"], text, tpath.name))
                # overlap: keep trailing segments until OVERLAP chars are held
                keep, acc = [], 0
                for x in reversed(buf):
                    if acc >= OVERLAP:
                        break
                    keep.insert(0, x); acc += len(x["text"]) + 1
                buf = keep
                start = buf[0]["start"] if buf else None
        if buf:
            rows.append(("AUDIO", part, start, buf[-1]["end"],
                         " ".join(x["text"] for x in buf), tpath.name))

        # --- SLIDE: text from the projected documents, no timestamps ---
        for name, line in documents.for_meeting(part):
            rows.append(("SLIDE", part, None, None, line, name))

        # --- VIDEO: frame descriptions, timed by when they were sampled ---
        vpath = HERE / "out" / ("ES2008%s.video.json" % part)
        if vpath.exists():
            for r in json.loads(vpath.read_text()):
                rows.append(("VIDEO", part, r["t"], r["t"],
                             r["text"], "%s/%s" % (r["channel"], r["file"])))

    print("rows to index: %d" % len(rows))
    print("loading %s ..." % MODEL)
    model = SentenceTransformer(MODEL)
    vecs = model.encode([r[4] for r in rows], batch_size=64,
                        show_progress_bar=True, normalize_embeddings=True)
    dim = vecs.shape[1]

    DB.parent.mkdir(exist_ok=True)
    if DB.exists():
        DB.unlink()
    con = duckdb.connect(str(DB))
    con.execute("""
        CREATE TABLE content (
            id           INTEGER,
            source       VARCHAR,
            meeting_id   VARCHAR,
            meeting_part VARCHAR,
            start_time   VARCHAR,
            end_time     VARCHAR,
            content      VARCHAR,
            origin       VARCHAR,
            embedding    FLOAT[%d]
        )
    """ % dim)
    con.executemany(
        "INSERT INTO content VALUES (?,?,?,?,?,?,?,?,?)",
        [(i, r[0], "ES2008", r[1],
          hhmmss(r[2]) if r[2] is not None else None,
          hhmmss(r[3]) if r[3] is not None else None,
          r[4], r[5], v.tolist())
         for i, (r, v) in enumerate(zip(rows, vecs))])

    counts = con.execute("""
        SELECT source, meeting_part, COUNT(*)
        FROM content GROUP BY 1,2 ORDER BY 1,2
    """).fetchall()
    con.close()

    print("\nvector dimensions: %d" % dim)
    for src, part, n in counts:
        print("  %-6s ES2008%s  %4d" % (src, part, n))
    return len(rows), dim


if __name__ == "__main__":
    n, dim = build()
    recap(
        "Vector index",
        ["Chunked the transcripts at roughly %d characters with %d of overlap,\n"
         "     aligned to segment boundaries so the timestamps stay exact"
         % (CHUNK_SIZE, OVERLAP),
         "Embedded %d fragments with %s" % (n, MODEL),
         "Stored audio, documents and video in one %d dimension table" % dim],
        "One table for every modality is what makes cross-modal search possible: "
        "the same question is compared against what was said and against what was "
        "projected, without treating them as separate systems.",
        "search.py runs cosine similarity over this table: per channel, across "
        "all of them, and combined with time windows."
    )
