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
 "I've been learning multimodal data pipelines in Snowflake, ASR and OCR, so I rebuilt the course locally to see how a meeting breaks down into text you can actually query, (also created a repo, link at the end of the post). Here is how it works:",

 "A meeting has 3 components: what people said, what was on the screen, and what someone drew on the board. Most tools only read the first one. All three end up as text in a single table, audio and video carrying timestamps.",

 arrow("Audio to text",
       "Whisper runs locally with word-level timestamps. 2.2 hours of meetings transcribed in under 11 minutes, and confidential audio never leaves the laptop."),

 arrow("Documents to text",
       "the decks and minutes that were projected, mapped to the meeting where each one was shown."),

 arrow("Video to text",
       "ffmpeg samples frames, and a vision model describes them and transcribes any legible text on the board."),

 arrow("One table, not three",
       "all three channels get embedded with the same model and land in one DuckDB table, so a single query ranks audio, documents and video against each other."),

 arrow("Answers you can audit",
       "a token budget for the context, and answers that carry the audio timestamp or the document they came from."),

 "Every stage has an exact Snowflake Cortex equivalent, and the embedding model is the same one Cortex runs, from HuggingFace.",

 bold("Some lessons learned:"),

 arrow("The generated channel has to speak the language of the corpus",
       "I wrote the vision prompt in Spanish over English meetings, so the descriptions clustered by language instead of topic, and a pricing question returned ten video frames and no pricing."),

 arrow("Scene change sampling fails on whiteboards",
       "slides cut hard between frames, but strokes accumulate slowly, so ffmpeg returned zero frames until I sampled by interval instead."),

 arrow("The similarity threshold belongs to the model",
       "arctic-embed rarely passes 0.4 on this corpus, so a 0.5 cutoff returns zero rows and raises nothing at all."),

 bold("Tech Stack:"),

 "- Whisper large v3 turbo, transcription with word-level timestamps",

 "- snowflake-arctic-embed-m, embeddings, the same model Snowflake Cortex runs",

 "- DuckDB, one table holding audio, documents and video",

 "- Claude, frame descriptions and the cited answers",

 "- AMI Meeting Corpus, CC BY 4.0, so anyone can clone and run the demo",

 "- Repo, demo meeting included: %s" % REPO,

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
