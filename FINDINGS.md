# Verified findings

Corpus: AMI Meeting Corpus (CC BY 4.0). Every number here is recomputed by the
scripts named below. Nothing is written from memory.

---

## What was discarded

Initial hypothesis: audio-only pipelines fail because people say "let's go with
this one" while pointing at something, and the referent never reaches the text.

False in this meeting. Two deictic references in 2,233 words. There is no
phenomenon to measure. The hypothesis was abandoned before anything was built on
top of it.

`scripts/check_trap.py`

---

## The finding

The AMI scenario hands every team the same finance slide. Verified verbatim in
three independent scenarios (ES2008, ES2006, IS1009):

    Selling price: 25 euro
    Profit aim: 50 M euro
    Market range: international
    Production costs: max. 12.50 euro

Of the 142 hand-annotated abstractive summaries in the corpus, 12 state a profit
aim explicitly tied to the word "profit". Ten say fifty or 50. Two say fifteen
or 15:

- ES2008a — "The profit aim is fifteen million Euro."
- TS3008a — "The profit aim is 15 million Euros."

That is: **2 of 12 human answer keys record the meeting's central figure wrong**,
a figure that was projected on screen in front of the annotator.

`scripts/profit_aim_survey.py`

Caveat: TS3008 does not publish its kick-off deck, so that case is inferred from
template consistency rather than verified directly. ES2008a is verified directly.

---

## ES2008a in detail: five channels, two crossed errors

Profit aim
- projected slide: 50 M euro
- minutes written by the project manager herself: 50 M euro
- AMI manual transcript: "fifteen million"
- AMI abstractive answer key: "fifteen million Euro"
- Whisper large-v3-turbo: "50 million"

Maximum production cost
- projected slide: max. 12.50 euro
- minutes written by the project manager herself: max. 12.50 euro
- AMI manual transcript: "twelve fifty"
- AMI abstractive answer key: "12.50 Euro"
- Whisper large-v3-turbo: "1250"

Two figures, one slide. The human annotator got the first wrong. Whisper got the
second wrong. Neither could have known: both were only listening.

The meeting also contains its own arithmetic proof. The speaker says, and both
transcribe it correctly: "we're selling it for twice what we'd like to produce it
for". Twenty five is twice 12.50. Not twice 1250.

`scripts/diff_window.py`, `scripts/gold_check.py`

---

## Whisper's numeric accuracy on ES2008a

Compared against AMI's manual transcript, aligned in a 5 second window, with
multi-word numerals composed before comparing. Without composing, the count
inflates the errors: "twenty five" is two tokens in the reference and one in
Whisper.

33 of 37 figures match. The four that do not:

- 460.33 s — human "fifteen million", Whisper "50 million"
- 478.65 s — human "twelve fifty", Whisper "1250"
- 678.44 s — human "three", Whisper omits it
- 939.81 s — human "one", Whisper omits it

The errors are not evenly spread. The two omissions are irrelevant. The two
disagreements land on the only two figures in the meeting that carry money.

`scripts/number_audit.py`

---

## Why this justifies a multimodal pipeline

Not because of "more context". Because of cross-corroboration: a figure asserted
in audio can be checked against the same figure on screen, and a discrepancy is
an actionable signal rather than a nicer summary.

Neither channel dominates. On the same slide, the human ear got one figure wrong
and the model got the other wrong. An audio-only pipeline cannot emit that
signal: it is not lacking quality, it is lacking a second channel to check
itself against.

---

## Cost to reproduce

Zero. Whisper runs locally on Apple Silicon at 12.5x real time on an M4 Pro. The
data is public: about 90 MB of audio and video per meeting, 22 MB of
annotations. The only billed call is describing whiteboard frames, at $0.07.

---

## Known limits of what was built

- The generated channel has to speak the language of the corpus. With the vision
  prompt in Spanish over an English corpus, the descriptions formed their own
  cluster: in the vector space, language outweighed topic. A Spanish query about
  pricing returned 10 of 10 video frames, none related to pricing. With the
  prompt in English, the top two results become the two finance lines from the
  slide.
- The first vision pass included the overhead camera and cost $0.16. It was
  discarded: 17 nearly identical descriptions that polluted the ranking. The
  current pass, whiteboard only, costs $0.07.
- Scene change sampling returns zero frames on a whiteboard even at a threshold
  of 0.02. Strokes accumulate too slowly for any frame to differ enough from the
  one before. That channel needs interval sampling.
- Document extraction leaked binary format debris into the index. Fragments like
  `<real>774</real>` and `rpp<3A?` were taking real slots in the top ten. A
  stricter prose filter cut the document channel from 621 lines to 322 and the
  index from 873 chunks to 574. Fewer rows, better ranking.
- The similarity threshold belongs to the model. `arctic-embed-m` rarely passes
  0.4 on this corpus, so a 0.5 threshold returns zero rows without raising
  anything. `search.py` prints the distribution before applying it.
- Topic aggregation retrieves poorly. 500 character chunks dilute the topic; this
  needs finer granularity or reranking.
- ES2008d publishes no documents, so only the audio channel exists there. There
  is nothing to check it against.
- With both channels in context, the model does surface the numeric conflict on
  its own, and the numeric conclusion has been correct every time. How it frames
  the disagreement varies between runs: it has called the 1250 both a
  transcription error and a spoken slip. The first is correct, the second is not.
