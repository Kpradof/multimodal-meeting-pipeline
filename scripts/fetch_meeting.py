"""Download one AMI meeting's assets and extract its manual annotations."""
import subprocess, sys, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
MIRROR = "https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus"
ZIP = HERE / "data/ami_annotations.zip"


def fetch(url, dest):
    if dest.exists() and dest.stat().st_size > 0:
        print("  already there:", dest.name); return
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-sL", "--max-time", "900", "-o", str(dest), url], check=True)
    print("  downloaded: %s (%.1f MB)" % (dest.name, dest.stat().st_size / 1e6))


def main(mid):
    print("==", mid)
    d = HERE / "data" / mid
    fetch(f"{MIRROR}/{mid}/audio/{mid}.Mix-Headset.wav", d / "audio.wav")

    ann = HERE / "data/annotations"
    ann.mkdir(exist_ok=True)
    with zipfile.ZipFile(ZIP) as z:
        wanted = [n for n in z.namelist()
                  if f"/{mid}." in n and (
                      n.endswith(".words.xml") or "abssumm" in n or "decision" in n)]
        for n in wanted:
            out = ann / Path(n).name
            if not out.exists():
                out.write_bytes(z.read(n))
        print("  annotations: %d files" % len(wanted))


if __name__ == "__main__":
    for mid in sys.argv[1:]:
        main(mid)
