"""Retrieval and context budgeting -- the RAG architecture from lab_5.

Three pieces:

    retrieve_context()               searches all three channels at once
    count_tokens()                   counts with the model's real tokenizer
    build_context_with_token_limit() assembles context without overrunning

Generation is the fourth piece and needs ANTHROPIC_API_KEY. Everything else
runs at no cost.

The four function names and signatures come straight from lesson 5. See the
attribution section in the README.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import search
from teach import recap

MAX_CONTEXT_TOKENS = 4000
MODEL = "claude-sonnet-5"

_client = None
_exact = None


def _anthropic():
    global _client
    if _client is None:
        from anthropic import Anthropic
        _client = Anthropic()
    return _client


def count_tokens(text):
    """Equivalent to AI_COUNT_TOKENS('ai_complete', model, text).

    With ANTHROPIC_API_KEY it counts exactly, using the model's own tokenizer,
    and that call is not billed. Without a key it falls back to a rough 4
    characters per token heuristic: fine for development, not for publishing
    a number.
    """
    global _exact
    if os.getenv("ANTHROPIC_API_KEY"):
        r = _anthropic().messages.count_tokens(
            model=MODEL, messages=[{"role": "user", "content": text}])
        _exact = True
        return r.input_tokens
    _exact = False
    return max(1, len(text) // 4)


def counter_is_exact():
    return bool(_exact)


def retrieve_context(query, top_k=5, source_filter=None):
    """Searches the unified table. Mirrors retrieve_context() from lab_5."""
    rows = search.semantic(query, source=source_filter, limit=top_k)
    return [{"source": s, "part": p, "start": ts, "text": c, "sim": sim}
            for s, p, ts, c, sim in rows]


def build_context_with_token_limit(results, max_tokens=MAX_CONTEXT_TOKENS,
                                   greedy=False, verbose=True):
    """Assemble the context within a token budget.

    The lab stops with `break` at the first fragment that does not fit. That
    discards smaller pieces further down the ranking which would have fit.
    With greedy=True it keeps evaluating instead of stopping.

    Which one is right depends on what you are optimising: `break` preserves
    relevance order, greedy preserves coverage. There is no correct default,
    which is why it is a parameter and not a hidden decision.
    """
    parts, sources, used, skipped = [], [], 0, 0

    for r in results:
        ref = "ES2008%s %s" % (r["part"], r["start"] or "document")
        piece = "[%s] %s:\n%s\n" % (r["source"], ref, r["text"])
        n = count_tokens(piece)

        if used + n > max_tokens:
            if greedy:
                skipped += 1
                continue
            if verbose:
                print("  stopped at %d pieces (%d tokens); the next one did not fit"
                      % (len(parts), used))
            break

        parts.append(piece)
        sources.append(ref)
        used += n

    if greedy and skipped and verbose:
        print("  %d piece(s) skipped for size, %d included (%d tokens)"
              % (skipped, len(parts), used))

    return "\n---\n".join(parts), sources, used


SYSTEM = """You answer questions about a meeting using only the evidence given.

Rules:

- Cite the source of every claim with its bracketed label, exactly as it
  appears in the evidence. For example: [AUDIO ES2008a 00:07:49].
- If the evidence is not enough to answer, say so. Do not fill the gap with
  what you know about the world.
- If two channels contradict each other, do NOT quietly pick one. Say they
  disagree, cite both, and explain which is more reliable and why.

Be brief. No preamble."""


def generate_rag_response(query, context, sources):
    """Generate the cited answer. Equivalent to CORTEX.COMPLETE in lab_5."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return "(no ANTHROPIC_API_KEY: cannot generate the answer)"
    r = _anthropic().messages.create(
        model=MODEL, max_tokens=900, system=SYSTEM,
        messages=[{"role": "user", "content":
                   "Evidence:\n\n%s\n\nQuestion: %s" % (context, query)}])
    return r.content[0].text.strip()


def multimodal_rag(query, top_k=10, source_filter=None,
                   max_tokens=MAX_CONTEXT_TOKENS, verbose=True):
    """The full lab_5 pipeline, from question to cited answer."""
    results = retrieve_context(query, top_k=top_k, source_filter=source_filter)
    if not results:
        return {"response": "No relevant content found.",
                "sources": [], "tokens_used": 0, "results": []}
    ctx, srcs, toks = build_context_with_token_limit(
        results, max_tokens, verbose=verbose)
    return {"response": generate_rag_response(query, ctx, srcs),
            "sources": srcs, "tokens_used": toks,
            "source_filter": source_filter, "results": results}


if __name__ == "__main__":
    q = "what did the team decide about pricing and production cost"
    res = retrieve_context(q, top_k=8)

    print("Retrieved for: '%s'\n" % q)
    for r in res:
        print("  %.3f  %-5s ES2008%s %-9s %s"
              % (r["sim"], r["source"], r["part"], r["start"] or "-",
                 r["text"][:48].replace("\n", " ")))

    print("\nBuilding context with a %d token limit..." % MAX_CONTEXT_TOKENS)
    ctx, srcs, toks = build_context_with_token_limit(res)
    print("  context: %d sources, %d tokens (%s)"
          % (len(srcs), toks, "exact" if counter_is_exact() else "estimated"))

    print("\nSame context on a small budget (300 tokens):")
    ctx2, s2, t2 = build_context_with_token_limit(res, max_tokens=300)
    print("  break : %d sources, %d tokens" % (len(s2), t2))
    ctx3, s3, t3 = build_context_with_token_limit(res, max_tokens=300, greedy=True)
    print("  greedy: %d sources, %d tokens" % (len(s3), t3))

    recap(
        "RAG: retrieval and context budget",
        ["Retrieved %d fragments from audio and documents with a single query" % len(res),
         "Counted tokens per fragment (%s)"
         % ("the model's real tokenizer" if counter_is_exact()
            else "heuristic, no API key"),
         "Assembled the context under two different cutoff policies"],
        "The context limit is not an implementation detail: it decides what evidence "
        "the model sees. Stopping at the first overflow preserves relevance; "
        "continuing preserves coverage. Choosing without measuring is guessing.",
        "The cited answer and the video channel are still missing. Both need "
        "ANTHROPIC_API_KEY."
    )
