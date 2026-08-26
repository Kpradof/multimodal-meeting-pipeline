"""Audit someone else's meeting notes against what the meeting actually holds.

A notetaker writes its summary from what it heard. If the speech recognition
mishears a figure, the summary inherits it and nothing downstream can tell.
This takes that summary as input, pulls out the checkable claims, and looks for
each one in the indexed channels -- including the documents that were on screen,
which the notetaker never saw.

    .venv/bin/python src/audit.py notes.txt
    .venv/bin/python src/audit.py --demo

The demo input is AMI's own hand written summary of ES2008a. It is a real
summary produced by human annotators who listened to the recording, and it
contains a real error. Nothing about it was written for this repo.
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import search
from teach import recap

HERE = Path(__file__).resolve().parent.parent
load_dotenv(HERE / ".env")
MODEL = "claude-sonnet-5"

_client = None


def client():
    global _client
    if _client is None:
        from anthropic import Anthropic
        _client = Anthropic()
    return _client


EXTRACT = """Below is a summary of a meeting, written by someone who was not you.

Pull out every claim in it that could be checked against a record of the
meeting. A checkable claim states something specific: a figure, a price, a
deadline, a decision, an assignment of work to a person.

Skip anything vague ("the team discussed the project"), anything about how
people felt, and anything that only describes the shape of the meeting.

Return JSON only, no prose:

{"claims": [{"text": "<the claim, quoted or tightly paraphrased>",
             "kind": "figure|decision|assignment|deadline"}]}"""


JUDGE = """You are checking one claim from a meeting summary against evidence
retrieved from the meeting itself.

The evidence comes from three channels. AUDIO is a machine transcript and can
mishear, especially numbers. SLIDE is text taken from the documents that were
projected, and it is written, so for figures it is the stronger source. VIDEO is
a description of what was visible.

Return JSON only, no prose:

{"verdict": "SUPPORTED|CONTRADICTED|NO_EVIDENCE",
 "citation": "<the label of the single most relevant piece of evidence>",
 "note": "<one sentence. If CONTRADICTED, say what the record holds instead.>"}

Rules:
- CONTRADICTED means the evidence states something incompatible with the claim.
- NO_EVIDENCE means nothing retrieved speaks to the claim either way. It is not
  a failure of the claim, only of the retrieval.
- If AUDIO and SLIDE disagree about a figure, say so in the note and treat the
  written document as the record."""


def text_of(response):
    """First real text block. The model may emit a thinking block first."""
    for block in response.content:
        if getattr(block, "type", None) == "text":
            return block.text
    return ""


def _json(text):
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}


def extract_claims(summary):
    r = client().messages.create(
        model=MODEL, max_tokens=1500, system=EXTRACT,
        messages=[{"role": "user", "content": summary}])
    return _json(text_of(r)).get("claims", [])


def verify(claim, top_k=6):
    hits = search.semantic(claim["text"], limit=top_k)
    if not hits:
        return {"verdict": "NO_EVIDENCE", "citation": "-",
                "note": "Nothing retrieved."}, []
    ev = "\n".join(
        "[%s ES2008%s %s] %s" % (s, p, ts or "document", c)
        for s, p, ts, c, _ in hits)
    r = client().messages.create(
        model=MODEL, max_tokens=400, system=JUDGE,
        messages=[{"role": "user",
                   "content": "Claim: %s\n\nEvidence:\n%s" % (claim["text"], ev)}])
    return _json(text_of(r)), hits


def demo_summary():
    """AMI's own hand written summary of ES2008a, as the notes to audit."""
    root = ET.parse(HERE / "data/annotations/ES2008a.abssumm.xml").getroot()
    out = []
    for ch in root:
        tag = ch.tag.split("}")[-1]
        if tag in ("abstract", "decisions", "actions"):
            for s in ch:
                t = (s.text or "").strip()
                if t:
                    out.append(t)
    return "\n".join(out)


def run(summary):
    print("Auditing %d characters of notes.\n" % len(summary))
    claims = extract_claims(summary)
    print("Checkable claims found: %d\n" % len(claims))

    rows = []
    for i, c in enumerate(claims, 1):
        v, _ = verify(c)
        rows.append((c, v))
        mark = {"SUPPORTED": "ok", "CONTRADICTED": "CONFLICT",
                "NO_EVIDENCE": "no evidence"}.get(v.get("verdict"), "?")
        print("%2d. [%-11s] %s" % (i, mark, c["text"][:66]))
        if v.get("verdict") == "CONTRADICTED":
            print("      record: %s" % v.get("note", "")[:96])
            print("      source: %s" % v.get("citation", ""))

    tally = {}
    for _, v in rows:
        tally[v.get("verdict", "?")] = tally.get(v.get("verdict", "?"), 0) + 1
    print("\n" + "-" * 74)
    for k in ("SUPPORTED", "CONTRADICTED", "NO_EVIDENCE"):
        print("  %-14s %d" % (k, tally.get(k, 0)))
    return rows, tally


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--demo"]
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is required to audit notes.")

    if args:
        summary = Path(args[0]).read_text(encoding="utf-8")
        label = args[0]
    else:
        summary = demo_summary()
        label = "AMI's own hand written summary of ES2008a"
    print("Input: %s\n" % label)

    rows, tally = run(summary)
    recap(
        "Auditing someone else's notes",
        ["Pulled %d checkable claims out of the notes" % len(rows),
         "Searched all three channels for evidence on each one",
         "Flagged %d as contradicted by the record" % tally.get("CONTRADICTED", 0)],
        "A notetaker writes from what it heard, so it cannot tell you when it "
        "misheard. Checking its output against the documents that were on screen "
        "is the only place that error becomes visible.",
        "NO_EVIDENCE is a retrieval result, not a verdict on the claim. Reading "
        "those by hand is what tells you whether the index is missing something."
    )
