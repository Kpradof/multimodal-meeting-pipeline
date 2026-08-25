# Design notes

What is built, what is not, and the interface the second engine would implement.

Findings and evidence live in `FINDINGS.md`. Usage lives in `README.md`.

---

## Stage interfaces

The pipeline is a set of stages. Each has one implementation today, and each has
an exact Snowflake Cortex counterpart it could be swapped for:

    transcribe(audio)      -> [Segment(start, end, text)]
    describe(frames)       -> [FrameNote(ts, text)]
    chunk(segments)        -> [Chunk]
    embed(texts)           -> ndarray
    search(query, k)       -> [Hit]
    count_tokens(text)     -> int
    complete(prompt)       -> str

Both engines have to produce the same output schema, otherwise nothing can
compare them.

### Stage by stage

transcribe — lesson L2
- local: `mlx-whisper` on Apple Silicon, `faster-whisper` elsewhere, word level timestamps
- snowflake: `AI_TRANSCRIBE`

describe — lessons L2 and L4
- local: Claude vision over frames sampled by interval
- snowflake: `AI_PARSE_DOCUMENT`, and the VLM container for video

chunk — lesson L2
- local: segment aligned chunking, so timestamps stay exact
- snowflake: `SPLIT_TEXT_RECURSIVE_CHARACTER`

embed — lesson L2
- local: `snowflake-arctic-embed-m` from HuggingFace
- snowflake: `AI_EMBED`
- It is the same model on both sides. The vectors should match, and that is
  testable: a test comparing both engines over the same text is worth more than
  any paragraph in the README.

search — lesson L5
- local: DuckDB `array_cosine_similarity`
- snowflake: `VECTOR_COSINE_SIMILARITY` over the unified table

count_tokens — lesson L5
- local: `client.messages.count_tokens()`, the model's real tokenizer, not billed
- snowflake: `AI_COUNT_TOKENS('ai_complete', 'claude-4-sonnet', text)`
- Both point at the same model, so the counts should agree. Another parity test.

complete — lesson L5
- local: Claude API
- snowflake: `CORTEX.COMPLETE`

Storage: DuckDB locally, Snowflake tables on the other side. Same logical DDL.

---

## Why a second engine at all

A repo that requires a paid Snowflake account is one almost nobody runs. One that
never mentions Snowflake does not demonstrate the course. The abstraction solves
both, and designing the interface is itself the part worth showing: it forces you
to understand what each Cortex function does rather than copy the call.

**None of the Snowflake side is written.** A trial account blocks every Cortex AI
function, so it could not be verified today, and code that has not been run does
not get published as working.

---

## Repo layout

    docs/          architecture write-up and the slide
    src/           the pipeline stages
    scripts/       fetch, transcribe, verification, post and slide generators
    data/          downloaded corpus, gitignored
    out/           transcripts, index, generated post, gitignored

---

## What is left

- The Snowflake engine, once a non-trial account exists
- An eval set with trap, control and skill questions, so conflict detection can
  be measured instead of demonstrated
- Reranking, or finer chunks, for topic aggregation
- `GUIDE.md`, mapping each stage back to its lesson
