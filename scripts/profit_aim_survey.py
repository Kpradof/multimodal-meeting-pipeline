"""How many hand-annotated summaries record the profit aim, and which figure?

The AMI scenario hands every team the same finance slide. If the annotators were
only listening, their summaries should disagree with the document in more than
one meeting. This measures that without transcribing anything.
"""
import re, zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent.parent
ZIP = HERE / "data/ami_annotations.zip"

pat = re.compile(r"([\w.]+)\s+(million|m\b)", re.I)
rows = []
with zipfile.ZipFile(ZIP) as z:
    names = sorted(n for n in z.namelist() if n.endswith(".abssumm.xml"))
    for n in names:
        mid = Path(n).name.split(".")[0]
        root = ET.fromstring(z.read(n))
        for ch in root:
            tag = ch.tag.split("}")[-1]
            for s in ch:
                t = (s.text or "").strip()
                if not t:
                    continue
                low = t.lower()
                if "million" in low or re.search(r"\d+\s*m\b", low):
                    if any(k in low for k in ("profit", "aim", "sale", "sell", "revenue", "euro")):
                        rows.append((mid, tag, t))

print("abstractive summaries reviewed: %d" % len(names))
print("mentions of a millions figure tied to finance: %d\n" % len(rows))
for mid, tag, t in rows:
    print("  %-10s %-11s %s" % (mid, tag, t))

print("\n--- count by figure ---")
c = {}
for _, _, t in rows:
    m = pat.search(t)
    k = m.group(1).lower() if m else "?"
    c[k] = c.get(k, 0) + 1
for k, v in sorted(c.items(), key=lambda x: -x[1]):
    print("  %-12s %d" % (k, v))
