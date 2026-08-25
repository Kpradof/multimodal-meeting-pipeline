"""Ask the meetings a question from the terminal.

The interactive CLI from lab_5: type a question, choose whether to narrow it to
one channel, and it answers citing where each fact came from.

    .venv/bin/python src/ask.py
    .venv/bin/python src/ask.py "how much does the remote cost to produce"
    .venv/bin/python src/ask.py --source SLIDE "what is the profit aim"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rag
from teach import recap

SOURCES = ("AUDIO", "SLIDE", "VIDEO")


def answer(query, source_filter=None, top_k=10):
    print("\nSearching %s..."
          % (source_filter.lower() if source_filter else "all three channels"))
    out = rag.multimodal_rag(query, top_k=top_k, source_filter=source_filter)

    if out["results"]:
        print("\nRetrieved evidence")
        print("-" * 74)
        for r in out["results"][:len(out["sources"])]:
            print("  %.3f  %-5s ES2008%s %-9s %s"
                  % (r["sim"], r["source"], r["part"], r["start"] or "document",
                     r["text"][:44].replace("\n", " ")))

    print("\nContext tokens: %d (%s)"
          % (out["tokens_used"],
             "exact" if rag.counter_is_exact() else "estimated, no API key"))
    print("Sources cited : %d" % len(out["sources"]))

    print("\nAnswer")
    print("-" * 74)
    print(out["response"])
    return out


def interactive():
    print("Ask the ES2008 meetings. Empty line to quit.\n")
    while True:
        try:
            q = input("Question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not q:
            break
        print("\nFilter: AUDIO, SLIDE, VIDEO, or Enter for all")
        f = input("Filter: ").strip().upper()
        answer(q, f if f in SOURCES else None)
        print()


if __name__ == "__main__":
    args = sys.argv[1:]
    src = None
    if "--source" in args:
        i = args.index("--source")
        src = args[i + 1].upper()
        del args[i:i + 2]

    if args:
        answer(" ".join(args), src if src in SOURCES else None)
    else:
        interactive()

    recap(
        "Asking the meeting",
        ["Turned a question into a vector and retrieved evidence from three channels",
         "Assembled the context inside the token budget",
         "Generated an answer citing the second or the document behind each fact"],
        "An answer without a citation cannot be audited. With the timestamp and "
        "the source, anyone can go back to the audio and check, which is the only "
        "way to notice when the pipeline was confidently wrong.",
        "What is still missing is for the answer to flag a cross-channel conflict "
        "by itself, instead of waiting for someone to read it."
    )
