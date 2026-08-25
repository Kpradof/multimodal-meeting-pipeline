import glob, json
import xml.etree.ElementTree as ET

A, B = 452.0, 495.0

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

print("=" * 72)
print("REFERENCIA HUMANA (AMI, anotada a mano)  %.0f-%.0fs" % (A, B))
print("=" * 72)
print(" ".join(w for t, s, w in words if A <= t <= B))

segs = json.loads(open("out/ES2008a.transcript.json").read())["segments"]
print()
print("=" * 72)
print("WHISPER large-v3-turbo")
print("=" * 72)
for s in segs:
    if s["end"] >= A and s["start"] <= B:
        print("[%7.2f - %7.2f] %s" % (s["start"], s["end"], s["text"]))
