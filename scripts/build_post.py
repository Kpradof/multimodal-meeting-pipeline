# -*- coding: utf-8 -*-
"""Generate the LinkedIn post and enforce the mechanical rules.

Edit this file, NEVER out/post_final.txt: the next build overwrites it.
Exits non-zero if a rule is broken.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "out/post_final.txt"
REPO = "github.com/Kpradof/multimodal-meeting-pipeline"


def bold(t):
    """MATHEMATICAL SANS-SERIF BOLD. Generated, not typed: typed it corrupts."""
    o = []
    for c in t:
        if "A" <= c <= "Z":   o.append(chr(0x1D5D4 + ord(c) - ord("A")))
        elif "a" <= c <= "z": o.append(chr(0x1D5EE + ord(c) - ord("a")))
        elif "0" <= c <= "9": o.append(chr(0x1D7EC + ord(c) - ord("0")))
        else: o.append(c)
    return "".join(o)


def arrow(claim, rest):
    return "➡️ %s: %s" % (bold(claim), rest)


POST = "\n\n".join([
 "I've been learning multimodal data pipelines in Snowflake (OCR, ASR, VLM), so I rebuilt it locally to check the kind of notes those tools produce (Granola, Fathom, Gemini etc) vs the deck that was up on the screen during the meeting. Then I pointed it at notes written by humans:",

 "In my case study, it flagged one claim out of eleven: the notes said the profit aim was fifteen million euro. The slide projected during that meeting reads \"Profit aim: 50 M euro\", and so do the minutes typed up afterwards. The handwritten transcript also reads \"fifteen million\", so the error came in through the audio and rode into the summary.",

 arrow("Three channels, one table",
       "audio through Whisper with word-level timestamps, the projected deck parsed straight out of the .ppt, and whiteboard frames described by a vision model. All three embedded with the same model, so a single query ranks them against each other."),

 arrow("The checker on top",
       "it pulls the checkable claims out of a set of notes, searches all three channels for each one, and returns supported, contradicted or no evidence. Three consecutive runs returned the same eleven claims and the same single conflict."),

 arrow("Every stage has a Cortex equivalent",
       "AI_TRANSCRIBE, AI_PARSE_DOCUMENT, AI_EMBED, VECTOR_COSINE_SIMILARITY, AI_COUNT_TOKENS, CORTEX.COMPLETE. The embedding model is the same one Cortex runs, published on HuggingFace, so the vectors are comparable."),

 "The notes are AMI's own, used as ground truth in meeting summarization research. Across that corpus twelve summaries state a profit aim: ten say fifty million, two say fifteen.",

 bold("Some lessons learned:"),

 arrow("No evidence is a retrieval result, not a verdict",
       "two claims came back unmatched. That says the search missed them, not that they are false, and it is the part worth reading by hand."),

 arrow("For figures, the written document wins",
       "speech turns 12.50 into \"twelve fifty\" and a transcript has to guess. A slide does not."),

 bold("Tech Stack:"),

 "- Whisper large v3 turbo, transcription with word-level timestamps, running locally",

 "- snowflake-arctic-embed-m, embeddings, the same model Snowflake Cortex runs",

 "- DuckDB, one table holding audio, documents and video",

 "- Claude, claim extraction and the verdicts",

 "- AMI Meeting Corpus, CC BY 4.0, so anyone can clone and run the demo",

 "- Repo, demo included: %s" % REPO,

 "#MultimodalAI #DataEngineering #AIEngineering",
])

# --- mechanical rules -------------------------------------------------------
fails = []

if "—" in POST or "--" in POST:
    fails.append("em dash or double hyphen")

if re.search(r"\$\s?\d", POST):
    fails.append("price or API cost in the body")

links = re.findall(r"(?:https?://)?(?:www\.)?[a-z0-9.-]+\.[a-z]{2,}/\S+", POST)
if len(links) > 1:
    fails.append("more than one link in the body: %s" % links)
if links and "github.com/Kpradof" not in links[0]:
    fails.append("the only allowed link is the repo, not %r" % links[0])

tags = re.findall(r"#\w+", POST)
if len(tags) != 3:
    fails.append("hashtags: %d, must be 3" % len(tags))

if not POST.split("\n")[0].rstrip().endswith(":"):
    fails.append("the hook does not end in a colon")

n = len(POST)
if n > 3000:
    fails.append("length %d, LinkedIn cuts at 3000" % n)
if n > 2400:
    fails.append("length %d, target is around 2000" % n)

longest = max(len(p) for p in POST.split("\n\n"))
if longest > 460:
    fails.append("paragraph of %d characters, anything denser gets split" % longest)

for word in ("you should", "you need", "what saves you", "the hard work isn't"):
    if word in POST.lower():
        fails.append("phrase that instructs the reader: %r" % word)

print("characters       : %d" % n)
print("longest paragraph: %d" % longest)
print("hashtags        : %d" % len(tags))

if fails:
    print("\nFAILED:")
    for f in fails:
        print("  -", f)
    sys.exit(1)

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(POST, encoding="utf-8")
print("\nwritten: %s" % OUT)
print("\n" + "=" * 74 + "\n")
print(POST)
