"""Paso 3 del plan: verificar la trampa a mano, antes de construir nada mas.

Pregunta: las decisiones que los anotadores humanos registraron, se pueden
recuperar solo del audio? O su objeto vivia en un canal visual?

No decide nada solo. Imprime evidencia para leer con ojos.
"""
import json, re, sys
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent.parent
transcript = json.loads((HERE / "out/ES2008a.transcript.json").read_text())
segments = transcript["segments"]
full = " ".join(s["text"] for s in segments)

# --- answer key humano -------------------------------------------------------
root = ET.parse(HERE / "data/annotations/ES2008a.abssumm.xml").getroot()
key = {}
for child in root:
    tag = child.tag.split("}")[-1]
    key[tag] = [(s.text or "").strip() for s in child if (s.text or "").strip()]

# --- 1. las cifras decididas, aparecen habladas? -----------------------------
# Las decisiones del answer key son numericas. Whisper escribe numeros como
# palabras, asi que hay que buscar ambas formas.
NUMBER_FORMS = {
    "25 euro (precio de venta)": [r"\btwenty[- ]?five\b", r"\b25\b"],
    "15 millones (meta de ganancia)": [r"\bfifteen million\b", r"\b15 million\b"],
    "12.50 euro (costo max)": [r"\btwelve fifty\b", r"\btwelve (euro )?fifty\b",
                                r"\b12[.,]50\b", r"\btwelve and a half\b",
                                r"\btwelve point five\b"],
}
print("=" * 70)
print("1. LAS CIFRAS DECIDIDAS, SE DICEN EN VOZ ALTA?")
print("=" * 70)
low = full.lower()
for label, pats in NUMBER_FORMS.items():
    hits = []
    for p in pats:
        for m in re.finditer(p, low):
            ctx = full[max(0, m.start() - 90): m.end() + 90].replace("\n", " ")
            hits.append(f'"...{ctx}..."')
    print(f"\n{label}: {'HABLADA' if hits else 'NO APARECE EN EL AUDIO'}")
    for h in hits[:3]:
        print("   ", h)

# --- 2. densidad de deicticos ------------------------------------------------
DEICTIC = [r"\bthis one\b", r"\bthat one\b", r"\bright here\b", r"\bover here\b",
           r"\bup here\b", r"\bon the board\b", r"\bthe board\b", r"\bon the screen\b",
           r"\bas you can see\b", r"\byou can see\b", r"\bhere we\b", r"\bthese ones\b",
           r"\blike this\b", r"\bwhat i drew\b", r"\bmy drawing\b", r"\bthe slide\b"]
print("\n" + "=" * 70)
print("2. REFERENCIAS QUE APUNTAN A ALGO NO DICHO")
print("=" * 70)
total = 0
for p in DEICTIC:
    n = len(re.findall(p, low))
    if n:
        total += n
        print(f"  {p:24s} {n}")
print(f"\n  total: {total} en {len(segments)} segmentos ({len(full.split())} palabras)")

# --- 3. answer key completo --------------------------------------------------
print("\n" + "=" * 70)
print("3. ANSWER KEY HUMANO (AMI abssumm)")
print("=" * 70)
for tag in ("decisions", "actions", "problems"):
    print(f"\n{tag}:")
    for item in key.get(tag, []):
        print("  -", item)
