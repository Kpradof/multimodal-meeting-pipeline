"""Measure how many of the meeting's figures survive transcription.

Composes multi-word numerals ("twenty five" -> 25) before comparing, because
Whisper emits a single token. Without composing, the count inflates the errors.

Aligns by time window against AMI's manual transcript and prints every case for
a human to read. It does not conclude on its own.
"""
import glob, json, re
import xml.etree.ElementTree as ET

UNITS = {"zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,
         "eight":8,"nine":9,"ten":10,"eleven":11,"twelve":12,"thirteen":13,
         "fourteen":14,"fifteen":15,"sixteen":16,"seventeen":17,"eighteen":18,
         "nineteen":19}
TENS = {"twenty":20,"thirty":30,"forty":40,"fifty":50,"sixty":60,"seventy":70,
        "eighty":80,"ninety":90}
SCALE = {"hundred":100,"thousand":1000,"million":1000000}
NUMWORD = set(UNITS) | set(TENS) | set(SCALE)


def is_num(tok):
    return tok in NUMWORD or re.fullmatch(r"\d+([.,]\d+)?", tok) is not None


def compose(tokens):
    """['twenty','five'] -> [25]; ['fifteen','million'] -> [15000000]"""
    out, cur, seen = [], 0, False
    for tok in tokens:
        if re.fullmatch(r"\d+([.,]\d+)?", tok):
            if seen: out.append(cur); cur = 0
            out.append(float(tok.replace(",", ".")))
            seen = False
            continue
        if tok in TENS:
            if seen and cur % 10 == 0 and cur >= 20: out.append(cur); cur = 0
            cur += TENS[tok]; seen = True
        elif tok in UNITS:
            if seen and cur % 10 != 0 and cur < 20: out.append(cur); cur = 0
            cur += UNITS[tok]; seen = True
        elif tok in SCALE:
            cur = (cur or 1) * SCALE[tok]; seen = True
    if seen: out.append(cur)
    return [float(x) for x in out]


# --- human reference -------------------------------------------------------
words = []
for f in sorted(glob.glob("data/annotations/ES2008a.?.words.xml")):
    last = 0.0
    for w in ET.parse(f).getroot():
        if w.tag == "w" and w.text:
            st = w.get("starttime")
            t = float(st) if st is not None else last
            last = t
            words.append((t, w.text.lower().strip(".,?!")))
words.sort(key=lambda x: x[0])

# group adjacent numerals (up to a 1.5s gap) into one figure
groups, cur = [], []
for t, w in words:
    if is_num(w) and (not cur or t - cur[-1][0] <= 1.5):
        cur.append((t, w))
    else:
        if cur: groups.append(cur)
        cur = [(t, w)] if is_num(w) else []
if cur: groups.append(cur)

gold = []
for g in groups:
    for v in compose([w for _, w in g]):
        gold.append((g[0][0], " ".join(w for _, w in g), v))

# --- whisper -----------------------------------------------------------------
segs = json.loads(open("out/ES2008a.transcript.json").read())["segments"]
wtoks = []
for s in segs:
    for w in s.get("words", []):
        tok = w["w"].lower().strip(" .,?!€$")
        if is_num(tok): wtoks.append((w["s"], tok))

wgroups, cur = [], []
for t, w in wtoks:
    if not cur or t - cur[-1][0] <= 1.5: cur.append((t, w))
    else: wgroups.append(cur); cur = [(t, w)]
if cur: wgroups.append(cur)

wh = []
for g in wgroups:
    for v in compose([w for _, w in g]):
        wh.append((g[0][0], " ".join(w for _, w in g), v))

# --- comparison -------------------------------------------------------------
print("figures (composed) in the human reference: %d" % len(gold))
print("figures (composed) in Whisper           : %d" % len(wh))
print()
print("%-9s %-22s %-22s %s" % ("time", "human", "whisper (+/-5s)", ""))
print("-" * 74)
ok = bad = 0
errors = []
for t, txt, val in gold:
    near = [(wt, wtxt, wv) for wt, wtxt, wv in wh if abs(wt - t) <= 5.0]
    match = any(abs(wv - val) < 1e-9 for _, _, wv in near)
    shown = ", ".join("%s=%g" % (wtxt, wv) for _, wtxt, wv in near) or "-"
    if match: ok += 1
    else:
        bad += 1
        errors.append((t, txt, val, shown))
    print("%8.2fs %-22s %-22s %s" % (t, "%s=%g" % (txt, val), shown, "" if match else "<-- DIFFERS"))
print("-" * 74)
print("match: %d/%d    differ: %d" % (ok, len(gold), bad))
print()
print("DIFFERENCES:")
for t, txt, val, shown in errors:
    print("  [%.2fs] human '%s' (=%g)  vs whisper: %s" % (t, txt, val, shown))
