"""Recap blocks that each stage prints when it finishes.

The repo teaches while it runs, not only in the README. Every module closes with
what it did, why that matters, and what comes next, in the shape of the course's
"Next Steps" sections.
"""

W = 74


def recap(title, did, why, nxt):
    """Print the closing block for a stage.

    did  -- list of what this stage just did
    why  -- one sentence: why this step exists at all
    nxt  -- which stage follows, and what it needs from this one
    """
    print()
    print("=" * W)
    print(title.upper())
    print("=" * W)
    print("\nWhat you just did")
    for d in did:
        print("  - %s" % d)
    print("\nWhy it matters")
    for line in _wrap(why):
        print("  %s" % line)
    print("\nWhat comes next")
    for line in _wrap(nxt):
        print("  %s" % line)
    print("=" * W)


def _wrap(text, width=70):
    words, line, out = text.split(), "", []
    for w in words:
        if len(line) + len(w) + 1 > width:
            out.append(line); line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    return out
