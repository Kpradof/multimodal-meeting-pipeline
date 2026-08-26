# multimodal-meeting-pipeline

A meeting leaves three trails: what people **said**, what was on the **screen**,
and what someone **drew on the board**. This pipeline turns all three into text
with timestamps, keeps them in one table, and answers questions citing where
every fact came from.

It runs locally and free. The demo uses public data, so you can clone it and run
it without credentials for anything.

Architecture and full write-up: `docs/architecture.html`

---

## Attribution

This is a reimplementation of the pipeline taught in **Building Multimodal Data
Pipelines** (DeepLearning.AI with Snowflake), rebuilt to run without a paid
Snowflake account.

The architecture is the course's, not mine. `src/rag.py` in particular mirrors
lesson 5 closely enough that it should be named: `retrieve_context`,
`build_context_with_token_limit`, `generate_rag_response` and `multimodal_rag`
keep the same signatures and the same roles, and the chunk size of 500, the
overlap of 50, the 4000 token context budget and the `arctic-embed-m` model
choice all come from the labs.

No course code is copied. The labs are SQL calls into Snowflake Cortex; this is
Python calling local libraries. What is mine is the local implementation, the
document and whiteboard channels, the frame sampling, the verification scripts,
and the findings in `FINDINGS.md`.

Dataset: **AMI Meeting Corpus**, CC BY 4.0.
https://groups.inf.ed.ac.uk/ami/corpus/

---

## What it does

Ask a question, get an answer that cites the second of audio or the document
behind each claim. When two channels disagree, the discrepancy surfaces instead
of one side being silently dropped:

    $ .venv/bin/python src/ask.py "what is the profit aim and the maximum production cost"

    Retrieved evidence
    ---------------------------------------------------------------
      0.391  SLIDE ES2008a document   Production costs: max. 12.50 euro
      0.269  AUDIO ES2008a 00:07:49   We don't have to worry about specifics...
      0.234  SLIDE ES2008a document   Profit aim: 50 M euro

    Answer
    ---------------------------------------------------------------
    The maximum production cost per unit is 12.50 euro [SLIDE ES2008a].
    The audio says "a maximum of 1250 euro" [AUDIO ES2008a 00:07:49], which
    is inconsistent: the same speaker says they are selling at "twice what
    we'd like to produce it for", and the selling price is 25 euro.

That arithmetic check is not coded anywhere. The model derives it from the
cross-channel evidence.

How it frames the disagreement varies between runs. It reliably surfaces the
two figures and reasons about which holds, but it has called the 1250 both a
transcription error and a spoken slip. The numeric conclusion has been right
every time; the attribution has not.

---

## Auditing notes a tool wrote

The demo input is AMI's own hand written summary of ES2008a, produced by
annotators who listened to the recording. It was written years before this repo
and nothing in it was arranged for this test.

    $ .venv/bin/python src/audit.py --demo

    Checkable claims found: 11

     1. [ok         ] The remote will be sold for 25 Euro.
     2. [CONFLICT   ] The profit aim is fifteen million Euro.
          record: The slide states the profit aim is 50 million euro.
          source: [SLIDE ES2008a document] Profit aim: 50 M euro
     3. [ok         ] The maximum production cost for the remote is 12.50 Euro.
     ...

     SUPPORTED      8
     CONTRADICTED   1
     NO_EVIDENCE    2

One claim flagged out of eleven, and it is the one that is wrong. The projected
slide reads `Profit aim: 50 M euro`, and so do the minutes the project manager
wrote herself. The annotators only had the audio.

Three consecutive runs return the same eleven claims and the same single
conflict. `NO_EVIDENCE` is a retrieval result, not a verdict: it means nothing
retrieved spoke to the claim, which is worth reading by hand.

---

## Quick start

Requirements: Python 3.11+, `ffmpeg`, and an `ANTHROPIC_API_KEY` only for the
video channel and answer generation.

    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    cp .env.example .env          # then put your key in it

    .venv/bin/python scripts/fetch_meeting.py ES2008a
    .venv/bin/python scripts/transcribe.py ES2008a
    .venv/bin/python src/index.py
    .venv/bin/python src/ask.py

Without a key, transcription, chunking, embeddings and the whole vector search
still work. Only frame description and the final written answer switch off.

---

## The stages

Every module ends by printing what it did, why it matters, and what comes next.
The repo teaches while it runs, not only in this file.

`src/documents.py` — document channel
Pulls the text out of the decks and minutes that were projected, and maps each
one to the meeting where it was shown.

`scripts/transcribe.py` — audio channel
Whisper large-v3-turbo locally, with word level timestamps. 12.5x real time on
an M4 Pro.

`src/vision.py` — video channel
Samples frames with ffmpeg and has a vision model describe them, transcribing
any legible text verbatim.

`src/index.py` — unified table
Chunks, embeds with `snowflake-arctic-embed-m`, and stores all three channels in
a single 768 dimension DuckDB table.

`src/search.py` — search
Cosine similarity per channel, across all of them, combined with time windows,
and minutes-per-topic aggregation.

`src/rag.py` — context
Retrieval, token counting, and context assembly inside a budget.

`src/ask.py` — asking
The CLI. Interactive, or with the question as an argument.

`src/audit.py` — auditing someone else's notes
Takes a summary written by a notetaker, pulls out the checkable claims, and
looks for each one across the three channels. A notetaker writes from what it
heard, so it cannot tell you when it misheard. The documents that were on screen
are where that becomes visible.

`scripts/verify_claims.py` — the guard
Recomputes every published figure from source. It has already caught a real
error: the write-up said thirteen meetings where there were twelve.

---

## The engine

What runs today is the **local** engine, and it runs free: Whisper,
arctic-embed, DuckDB, Claude API. Every stage has an exact Snowflake Cortex
counterpart:

    transcribe        AI_TRANSCRIBE
    read documents    AI_PARSE_DOCUMENT
    chunk             SPLIT_TEXT_RECURSIVE_CHARACTER
    embed             AI_EMBED
    search            VECTOR_COSINE_SIMILARITY
    count tokens      AI_COUNT_TOKENS
    generate          CORTEX.COMPLETE

The embedding model is literally the same on both sides.
`snowflake-arctic-embed-m` is published on HuggingFace, so the vectors are
comparable rather than merely similar, and that can be tested instead of
promised.

**The Snowflake engine is not written yet.** The per-stage interface design is in
`PLAN.md`, but there is no code for it. A trial account blocks every Cortex AI
function, so it could not even be verified today, and code that has not been run
does not get published as working.

---

## What it cost to run

    133 min of audio transcribed      12.5x real time, locally
    574 chunks indexed                237 audio, 322 documents, 15 video
    768 dimensions                    the same model Cortex runs
    $0.07                             the only spend: describing the whiteboard

Transcription, embeddings, vector search and token counting cost nothing: they
run locally on Apple Silicon, or they are calls that are not billed.

---

## Limits, said out loud

**The generated channel has to speak the language of the corpus.** With the
vision prompt written in Spanish over English meetings, the frame descriptions
formed their own vector neighborhood: language outweighed topic. A Spanish
question about pricing returned ten out of ten video frames, none about pricing.

**Scene change sampling fails on whiteboards.** It works on slide decks, which
cut hard between frames. Strokes accumulate slowly, so at a threshold of 0.02
ffmpeg returns zero frames. That channel needs interval sampling.

**The overhead camera was dropped.** Its seventeen frames returned nearly the
same sentence each time. It spent tokens and polluted the ranking.

**The similarity threshold belongs to the model, not to you.**
`arctic-embed-m` rarely passes 0.4 on this corpus. A 0.5 cutoff returns zero rows
and raises nothing at all.

**Topic aggregation retrieves poorly.** 500 character chunks dilute the topic;
this needs finer granularity or reranking.

**A meeting without documents has nothing to check itself against.** ES2008d does
not publish its own, so only the audio channel exists there.

---

## Data

The AMI Meeting Corpus is real product design meetings recorded with audio,
video, whiteboard capture, the decks that were projected, the minutes that were
written, and hand made annotations.

None of it is versioned here. `scripts/fetch_meeting.py` downloads it.

---

## License

MIT, see `LICENSE`. The AMI corpus keeps its own CC BY 4.0 terms.
