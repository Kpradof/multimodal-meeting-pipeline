"""Recompute from source every figure published in docs/architecture.html.

This is not a list of remembered values: it reads the files and counts again.
Run it after every edit. If a line says FAIL, the page is wrong, not the script.
"""
import glob
import json
import re
import sys
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

import duckdb

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
import documents

fails = []


def check(label, got, want, fmt="%s"):
    ok = abs(got - want) < 1e-6 if isinstance(want, float) else got == want
    print("  [%s] %-42s published %s  actual %s"
          % ("OK  " if ok else "FAIL", label, fmt % want, fmt % got))
    if not ok:
        fails.append(label)


print("Transcription")
tot_min = tot_cpu = 0.0
CPU = {"ES2008a": 220.5, "ES2008b": 143.0, "ES2008c": 121.0, "ES2008d": 153.0}
for m in ("ES2008a", "ES2008b", "ES2008c", "ES2008d"):
    segs = json.loads((HERE / "out" / (m + ".transcript.json")).read_text())["segments"]
    tot_min += segs[-1]["end"] / 60.0
    tot_cpu += CPU[m]
check("minutes of audio transcribed", round(tot_min), 133)
check("aggregate rate vs real time", round(tot_min * 60 / tot_cpu, 1), 12.5, "%.1f")

print("\nIndex")
con = duckdb.connect(str(HERE / "out/meetings.duckdb"), read_only=True)
check("total chunks", con.execute("SELECT COUNT(*) FROM content").fetchone()[0], 574)
for src, want in (("AUDIO", 237), ("SLIDE", 322), ("VIDEO", 15)):
    got = con.execute("SELECT COUNT(*) FROM content WHERE source=?", [src]).fetchone()[0]
    check("%s chunks" % src, got, want)
check("vector dimensions",
      len(con.execute("SELECT embedding FROM content LIMIT 1").fetchone()[0]), 768)
con.close()

print("\nSources")
check("document files", len(list((HERE / "data/docs").glob("*"))), 13)
check("lines extracted from documents",
      sum(len(documents.for_meeting(p)) for p in "abcd"), 322)
check("video frames described",
      len(json.loads((HERE / "out/ES2008a.video.json").read_text())), 15)

print("\nAPI cost")
v = json.loads((HERE / "out/ES2008a.video.json").read_text())
cost = sum(r["in_tokens"] for r in v) / 1e6 * 3 + sum(r["out_tokens"] for r in v) / 1e6 * 15
check("API cost of the current pipeline", round(cost, 2), 0.07, "$%.2f")

print("\nFinance slide (verbatim text)")
ppt = (HERE / "data/docs/PresentationKickOff.Rose.ppt")
txt = "\n".join(documents.extract(ppt))
for want in ("Selling price: 25 euro", "Profit aim: 50 M euro",
             "Production costs: max. 12.50 euro"):
    ok = want in txt
    print("  [%s] %s" % ("OK  " if ok else "FAIL", want))
    if not ok:
        fails.append(want)

print("\nHuman answer keys stating a profit aim")
rows = []
with zipfile.ZipFile(HERE / "data/ami_annotations.zip") as z:
    names = [n for n in z.namelist() if n.endswith(".abssumm.xml")]
    for n in names:
        for ch in ET.fromstring(z.read(n)):
            for s in ch:
                t = (s.text or "").strip().lower()
                if ("million" in t or re.search(r"\d+\s*m\b", t)) and "profit" in t:
                    rows.append((Path(n).name.split(".")[0], t))
check("abstractive summaries reviewed", len(names), 142)
mids = {m for m, _ in rows}
lo = {m for m, t in rows if "fifteen" in t or re.search(r"\b15\b", t)}
check("meetings stating a profit aim", len(mids), 12)
check("meetings stating it as 15 M", len(lo), 2)
print("       both of them:", ", ".join(sorted(lo)))

print()
if fails:
    print("%d check(s) failed. Fix the page, not the script." % len(fails))
    sys.exit(1)
print("Every published figure matches its source.")
