"""Write meeting notes the way a notetaker does: from the audio, and only that.

Granola, Fathom and the rest read a transcript and summarise it. They never see
the deck. This reproduces that constraint exactly -- the model is handed the
Whisper transcript and nothing else -- so the notes it writes inherit whatever
the speech recognition got wrong.

    .venv/bin/python scripts/simulate_notetaker.py ES2008a

Output goes to out/<meeting>.notetaker.txt, ready for src/audit.py.
"""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent.parent
load_dotenv(HERE / ".env")
MODEL = "claude-sonnet-5"

SYSTEM = """You are a meeting notetaker. You are given a transcript of a meeting
and nothing else. Write the notes you would send to the participants afterwards.

Include the decisions that were made, the figures that were agreed, and who is
doing what next. Write them as plain statements, one per line, the way a
notetaker app would.

Work only from the transcript. You have no other source."""


def text_of(response):
    for block in response.content:
        if getattr(block, "type", None) == "text":
            return block.text
    return ""


def run(mid):
    from anthropic import Anthropic
    segs = json.loads((HERE / "out" / (mid + ".transcript.json")).read_text())["segments"]
    transcript = " ".join(s["text"] for s in segs)

    r = Anthropic().messages.create(
        model=MODEL, max_tokens=1200, system=SYSTEM,
        messages=[{"role": "user", "content": transcript}])
    notes = text_of(r).strip()

    out = HERE / "out" / (mid + ".notetaker.txt")
    out.write_text(notes, encoding="utf-8")
    print("transcript in : %d characters" % len(transcript))
    print("notes out     : %d characters" % len(notes))
    print("written       : %s\n" % out)
    print(notes)
    return out


if __name__ == "__main__":
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is required.")
    run(sys.argv[1] if len(sys.argv) > 1 else "ES2008a")
