"""Video channel: describe frames with a model that can see, then index them.

Mirrors the VLM container from lab_4. The course deploys a vision model inside
Snowflake with frame sampling, a prompt and structured output. Here ffmpeg does
the sampling and Claude does the describing.

Sampling, a lesson that cost one failed attempt:

    Scene change detection works on slide decks, which cut hard between slides.
    On a whiteboard it does not: strokes accumulate slowly and no frame differs
    enough from the one before it. At a threshold of 0.02 over the ES2008a
    whiteboard, ffmpeg returns zero frames. That channel needs interval sampling.
"""
import base64
import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from teach import recap

HERE = Path(__file__).resolve().parent.parent
load_dotenv(HERE / ".env")

MODEL = "claude-sonnet-5"
FRAMES = HERE / "out/frames"
OUT = HERE / "out"

# The generated channel has to speak the language of the corpus. With a Spanish
# prompt, the descriptions came out in Spanish while the audio and the documents
# were English: in the vector space language outweighed topic, and the
# descriptions formed their own neighborhood. A Spanish question about pricing
# retrieved ten of ten video frames, none of them about pricing.
PROMPT = """You are looking at one frame from a recorded work meeting.

Describe ONLY what is visible. Do not invent context or guess what is being
discussed.

If any text, numbers or diagrams are legible, transcribe them verbatim -- they
are the most important thing in the frame. If the frame shows the room, say how
many people are present and what they are doing.

At most 3 sentences. No preamble."""


def sample(meeting, source, video, every=30, scene=None):
    """Extract frames. `scene` uses change detection, otherwise interval."""
    d = FRAMES / meeting
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("%s_*.jpg" % source):
        old.unlink()
    vf = ("select='gt(scene,%s)',scale=768:-1" % scene if scene
          else "fps=1/%d,scale=768:-1" % every)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video),
           "-vf", vf, "-q:v", "4", str(d / ("%s_%%03d.jpg" % source))]
    if scene:
        cmd.insert(-1, "-vsync"); cmd.insert(-1, "vfr")
    subprocess.run(cmd, check=True)
    return sorted(d.glob("%s_*.jpg" % source)), every


def describe(paths, client):
    out = []
    for i, p in enumerate(paths):
        img = base64.standard_b64encode(p.read_bytes()).decode()
        r = client.messages.create(
            model=MODEL, max_tokens=300,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64",
                                             "media_type": "image/jpeg", "data": img}},
                {"type": "text", "text": PROMPT}]}])
        text = r.content[0].text.strip()
        out.append({"file": p.name, "text": text,
                    "in_tokens": r.usage.input_tokens,
                    "out_tokens": r.usage.output_tokens})
        print("  [%2d/%2d] %s -> %s" % (i + 1, len(paths), p.name, text[:58]))
    return out


def run(meeting="ES2008a"):
    from anthropic import Anthropic
    client = Anthropic()
    d = HERE / "data" / meeting
    rows = []

    # Whiteboard only. The overhead camera returned 17 nearly identical
    # descriptions ("overhead view of a room with an oval table"): it spent
    # tokens and polluted the ranking without adding signal. See FINDINGS.md.
    jobs = [("wb", d / "whiteboard.avi", 30)]
    for source, video, every in jobs:
        if not video.exists():
            print("%s: no video, skipping" % source); continue
        paths, step = sample(meeting, source, video, every=every)
        print("\n%s: %d frames, one every %ds" % (source, len(paths), step))
        for k, desc in enumerate(describe(paths, client)):
            rows.append({"meeting": meeting, "channel": source,
                         "t": k * step, "file": desc["file"], "text": desc["text"],
                         "in_tokens": desc["in_tokens"], "out_tokens": desc["out_tokens"]})

    path = OUT / ("%s.video.json" % meeting)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=1))

    tin = sum(r["in_tokens"] for r in rows)
    tout = sum(r["out_tokens"] for r in rows)
    cost = tin / 1e6 * 3 + tout / 1e6 * 15     # Sonnet pricing
    print("\ntokens: %d in, %d out  ->  ~$%.3f" % (tin, tout, cost))
    return rows, cost


if __name__ == "__main__":
    rows, cost = run()
    recap(
        "Video channel",
        ["Sampled %d frames from the whiteboard" % len(rows),
         "Described each one with a model that can see, transcribing legible text",
         "Stored the descriptions with their timestamps, ready to index"],
        "This is the third channel, and the only one that sees what nobody said "
        "out loud. A figure projected on screen and never spoken exists only here.",
        "index.py adds these descriptions to the unified table, and from there "
        "cross-modal search compares audio, documents and video with a single query."
    )
