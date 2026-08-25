"""Cosine similarity search over the unified table.

Mirrors the queries in lab_4, swapping Snowflake's VECTOR_COSINE_SIMILARITY for
DuckDB's array_cosine_similarity. The SQL is nearly identical; what changes is
where it runs and what it costs.
"""
import sys
from pathlib import Path

import duckdb
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from teach import recap

HERE = Path(__file__).resolve().parent.parent
DB = HERE / "out/meetings.duckdb"
MODEL = "Snowflake/snowflake-arctic-embed-m"

_model = None


def embed(text):
    """The local equivalent of AI_EMBED('snowflake-arctic-embed-m', text).

    arctic-embed distinguishes a query from a document: queries take a prefix.
    Leaving it out degrades the ranking without raising anything.
    """
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL)
    q = "Represent this sentence for searching relevant passages: " + text
    return _model.encode([q], normalize_embeddings=True)[0].tolist()


def _con():
    return duckdb.connect(str(DB), read_only=True)


def semantic(query, source=None, part=None, limit=5):
    """Semantic search, optionally narrowed to one channel or one meeting."""
    where, args = ["TRUE"], []
    if source:
        where.append("source = ?"); args.append(source)
    if part:
        where.append("meeting_part = ?"); args.append(part)
    with _con() as con:
        return con.execute("""
            SELECT source, meeting_part, start_time, content,
                   ROUND(array_cosine_similarity(embedding, ?::FLOAT[768]), 3) AS sim
            FROM content
            WHERE %s
            ORDER BY sim DESC
            LIMIT ?
        """ % " AND ".join(where), [embed(query)] + args + [limit]).fetchall()


def cross_modal(query, per_source=3):
    """One query vector against every channel, ranked within each."""
    with _con() as con:
        return con.execute("""
            WITH scored AS (
                SELECT source, meeting_part, start_time, content,
                       ROUND(array_cosine_similarity(embedding, ?::FLOAT[768]), 3) AS sim,
                       ROW_NUMBER() OVER (PARTITION BY source ORDER BY
                           array_cosine_similarity(embedding, ?::FLOAT[768]) DESC) AS rk
                FROM content
            )
            SELECT source, meeting_part, start_time, content, sim
            FROM scored WHERE rk <= ?
            ORDER BY source, sim DESC
        """, [embed(query), embed(query), per_source]).fetchall()


def time_and_semantic(query, part, before="00:10:00", limit=5):
    """Time window plus similarity, the way lab_4 combines the two."""
    with _con() as con:
        return con.execute("""
            SELECT source, meeting_part, start_time, content,
                   ROUND(array_cosine_similarity(embedding, ?::FLOAT[768]), 3) AS sim
            FROM content
            WHERE source = 'AUDIO' AND meeting_part = ? AND start_time < ?
            ORDER BY sim DESC
            LIMIT ?
        """, [embed(query), part, before, limit]).fetchall()


def topic_time(query, threshold=0.25):
    """How long a topic was discussed, summing the duration of matching chunks.

    The threshold belongs to the model. arctic-embed-m rarely passes 0.4 on this
    corpus, so 0.5 returns zero rows without raising anything at all. Calibrating
    it against the real distribution is not optional.
    """
    with _con() as con:
        return con.execute("""
            SELECT meeting_part,
                   COUNT(*) AS chunks,
                   ROUND(SUM(epoch(end_time::TIME) - epoch(start_time::TIME)) / 60.0, 1) AS minutes
            FROM content
            WHERE source = 'AUDIO'
              AND array_cosine_similarity(embedding, ?::FLOAT[768]) > ?
            GROUP BY 1 ORDER BY 1
        """, [embed(query), threshold]).fetchall()


def score_range(query):
    """min, median and max similarity. Without this, picking a threshold is guessing."""
    with _con() as con:
        return con.execute("""
            SELECT MIN(sim), MEDIAN(sim), MAX(sim) FROM (
                SELECT array_cosine_similarity(embedding, ?::FLOAT[768]) AS sim
                FROM content WHERE source = 'AUDIO')
        """, [embed(query)]).fetchone()


def show(rows, title):
    print("\n%s" % title)
    print("-" * 74)
    for r in rows:
        src, part, ts, content, sim = r
        print("  %.3f  %-5s ES2008%s %-9s %s"
              % (sim, src, part, ts or "-", content[:52].replace("\n", " ")))


if __name__ == "__main__":
    q1 = "product pricing and profit target"
    show(semantic(q1, limit=5), "Semantic search -- '%s'" % q1)
    show(cross_modal(q1), "Cross-modal, one query against every channel")

    q2 = "what the remote control should look like"
    show(semantic(q2, source="SLIDE", limit=4), "Documents only -- '%s'" % q2)

    q3 = "introductions and getting to know the team"
    show(time_and_semantic(q3, part="a", before="00:05:00"),
         "Time plus semantics -- '%s', ES2008a, first 5 minutes" % q3)

    q4 = "budget and costs"
    lo, med, hi = score_range(q4)
    print("\nSimilarity distribution -- '%s'" % q4)
    print("-" * 74)
    print("  min %.3f   median %.3f   max %.3f   ->  threshold used: 0.25" % (lo, med, hi))
    print("\nTime per topic -- '%s'" % q4)
    print("-" * 74)
    for part, chunks, mins in topic_time(q4):
        print("  ES2008%s  %d chunks  %.1f min" % (part, chunks, mins or 0))

    recap(
        "Cross-modal search",
        ["Turned the question into a vector with the same model the index uses",
         "Ran cosine similarity per channel, across channels, and inside a time window",
         "Aggregated time per topic by summing the duration of matching chunks"],
        "The query does not look for words, it looks for meaning. 'profit target' "
        "finds a slide that says 'Profit aim' without sharing a single exact word, "
        "and it does that the same way in audio as in documents.",
        "The third channel is still missing here. Video descriptions need a model "
        "that can see the frames, which is where the API key comes in."
    )
