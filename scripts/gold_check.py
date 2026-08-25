"""Read AMI's manual word-level transcript and show the disputed figures.

The reference is annotated by hand, one word per element with its own start
time, so it is the closest thing to ground truth for what was said out loud.
Punctuation elements carry no timestamp, hence the carry-forward below.
"""
import glob
import re
import xml.etree.ElementTree as ET

words = []
for f in sorted(glob.glob("data/annotations/ES2008a.?.words.xml")):
    spk = f.split(".")[-3]
    last = 0.0
    for w in ET.parse(f).getroot():
        if w.tag == "w" and w.text:
            st = w.get("starttime")
            t = float(st) if st is not None else last
            last = t
            words.append((t, spk, w.text))
words.sort(key=lambda x: x[0])
gold = " ".join(w[2] for w in words)

print("words in the manual transcript:", len(words))
for term in ["fifteen", "fifty", "million", "twelve", "euro", "euros"]:
    pat = r"\b" + term + r"\b"
    print("  '%s': %d" % (term, len(re.findall(pat, gold, re.I))))

print("\n--- context around each disputed figure ---")
for i, (t, spk, w) in enumerate(words):
    if w.lower() in ("million", "fifteen", "fifty", "twelve"):
        ctx = " ".join(x[2] for x in words[max(0, i - 16): i + 14])
        print("\n[%7.2fs] speaker %s -> '%s'" % (t, spk, w))
        print("   " + ctx)
