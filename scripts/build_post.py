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
 "I've been learning multimodal data pipelines in Snowflake (OCR, ASR, VLM), so I rebuilt it locally to check the kind of notes those tools produce (Granola, Fathom, Gemini) vs the deck that was up on the screen during the meeting. Then I ran it on notes a machine wrote + notes humans wrote:",

 "In my case study, notes used as ground truth in research, it flagged one of eleven claims: the profit aim was written as fifteen million euro. The slide reads \"Profit aim: 50 M euro\", and so do the minutes typed up afterwards. The handwritten transcript also reads \"fifteen million\": the error came in through the audio.",

 arrow("Three channels, one table",
       "speech becomes text with Whisper, the deck is read out of the .ppt, and the whiteboard is described by a model that can see it. One embedding model turns all three into vectors, so one search covers all of them."),

 arrow("The checker on top",
       "it pulls the checkable claims out of a set of notes, looks for each across the three channels, and answers supported, contradicted, or no evidence. Three runs agreed."),

 arrow("Every stage has a Cortex equivalent",
       "AI_TRANSCRIBE for speech, AI_PARSE_DOCUMENT for the deck, AI_EMBED for the vectors, plus token counting and generation. Same embedding model, from HuggingFace."),

 "On notes a model wrote from the audio alone, it caught the same miss: 1,250 euro for a cost the deck puts at 12.50.",

 bold("Some lessons learned:"),

 arrow("The generated channel has to speak the language of the corpus",
       "I wrote the vision prompt in Spanish over English meetings, so descriptions grouped by language rather than topic. A pricing question returned ten video frames and no pricing."),

 arrow("Scene change sampling fails on whiteboards",
       "it grabs a frame when the picture changes a lot, which works for slides. Strokes appear slowly, so ffmpeg returned zero frames until I sampled on a timer."),

 arrow("A cutoff copied from a tutorial returns nothing",
       "every match gets a cosine similarity score, and you pick where results stop counting. I set 0.5. This model rarely passes 0.4 here, so the search came back empty and raised no error."),

 bold("Tech Stack:"),

 "- Whisper large v3 turbo, running local",

 "- snowflake-arctic-embed-m, the embedding model Cortex runs",

 "- DuckDB, the one table",

 "- Claude, claims and verdicts",

 "- AMI Meeting Corpus, CC BY 4.0",

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
