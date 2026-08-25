"""Document channel: the text that was on the screen.

In the course this comes from AI_PARSE_DOCUMENT run over slide images. Here it
comes from the original .ppt files AMI publishes, which is the same information
without passing through OCR. Once the video channel is in place, frame
descriptions join as a third source.
"""
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
DOCS = HERE / "data/docs"

# Which document was presented in each meeting of the ES2008 series.
# a = kick-off, b = functional design, c = conceptual design, d = detailed design
MEETING_DOCS = {
    "a": ["PresentationKickOff.Rose.ppt"],
    "b": ["Functional.Design-meeting-Rose.ppt",
          "Functional_requirements.jessie.ppt",
          "Technical.functions-presentation--Iain.ppt",
          "Trend_watching.jessie.ppt",
          "Working_design.-Alima.ppt"],
    "c": ["Conceptual.Design-Meeting-Rose.ppt",
          "Components_design.ppt",
          "Interface_concept.-Iain.ppt"],
    "d": [],
}

# OLE format debris that `strings` returns alongside the real text.
NOISE = re.compile(
    r"^(Microsoft|Arial|Times New Roman|Wingdings|Tahoma|Verdana|Courier|Symbol|"
    r"PowerPoint|Root Entry|Current User|Pictures|Summary|PP\d|Default Design|"
    r"Slide \d+|Blank Presentation|\W*)$", re.I)

# Markup and struct fragments the binary carries: <real>774</real>, rpp<3A?,
# CFURLString, and similar. These are not content and they take real slots in
# the ranking, so they have to go before indexing, not after.
# No real slide text contains an angle bracket, so it is a clean discard.
MARKUP = re.compile(r"[<>]|\{\\|xpacket|rdf:|uuid:|^\s*[A-Za-z]{1,3}[^A-Za-z\s]")


def looks_like_prose(s):
    """Keep only lines that read as language, not as struct debris.

    Two words of three or more letters, and at least two thirds of the line
    made of letters, digits, spaces or ordinary punctuation. A line that fails
    either test is format leakage.
    """
    if MARKUP.search(s):
        return False
    words = re.findall(r"[A-Za-z]{3,}", s)
    if len(words) < 2:
        return False
    ok = sum(c.isalnum() or c in " .,:;!?'\"()-/&%" for c in s)
    return ok / len(s) >= 0.66


def extract(path):
    """Pull readable lines out of a binary .ppt or .doc."""
    out = subprocess.run(["strings", "-n", "4", str(path)],
                         capture_output=True, text=True).stdout
    seen, lines = set(), []
    for raw in out.splitlines():
        s = raw.strip()
        if len(s) < 4 or NOISE.match(s):
            continue
        if not looks_like_prose(s):            # drop struct and markup leakage
            continue
        if s in seen:                          # .ppt files repeat every slide
            continue
        seen.add(s)
        lines.append(s)
    return lines


def for_meeting(part):
    """Return [(document_name, line)] for what was projected in that meeting."""
    rows = []
    for name in MEETING_DOCS.get(part, []):
        p = DOCS / name
        if not p.exists():
            continue
        for line in extract(p):
            rows.append((name, line))
    return rows


if __name__ == "__main__":
    from teach import recap
    total = 0
    for part in "abcd":
        rows = for_meeting(part)
        total += len(rows)
        print("ES2008%s: %d lines from %d document(s)"
              % (part, len(rows), len(MEETING_DOCS[part])))
        for name, line in rows[:4]:
            print("   [%s] %s" % (name.split(".")[0][:22], line[:60]))
    recap(
        "Document channel",
        ["Extracted %d lines of text from the presentations that were projected" % total,
         "Mapped each document to the meeting where it was shown",
         "Filtered out binary format debris and repeated lines"],
        "This is the second channel. Without it there is nothing to check what "
        "was said out loud against, and a misheard figure passes unnoticed.",
        "index.py chunks this text together with the transcript, turns both into "
        "vectors using the same model Snowflake runs, and stores them in a "
        "single table."
    )
