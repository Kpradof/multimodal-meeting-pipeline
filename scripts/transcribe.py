"""Transcribe one meeting with local Whisper. Skips ones already done."""
import json, sys, time
from pathlib import Path
import mlx_whisper

HERE = Path(__file__).resolve().parent.parent
MODEL = "mlx-community/whisper-large-v3-turbo"


def run(mid):
    audio = HERE / "data" / mid / "audio.wav"
    out = HERE / "out" / f"{mid}.transcript.json"
    out.parent.mkdir(exist_ok=True)
    if out.exists():
        print(f"{mid}: already transcribed"); return

    t0 = time.time()
    res = mlx_whisper.transcribe(str(audio), path_or_hf_repo=MODEL,
                                 word_timestamps=True, verbose=False)
    el = time.time() - t0
    segs = [{"start": s["start"], "end": s["end"], "text": s["text"].strip(),
             "words": [{"w": w["word"], "s": w["start"], "e": w["end"]}
                       for w in s.get("words", [])]}
            for s in res["segments"]]
    out.write_text(json.dumps({"language": res.get("language"), "segments": segs},
                              ensure_ascii=False, indent=1))
    dur = segs[-1]["end"] if segs else 0
    print(f"{mid}: {len(segs)} segs, {dur/60:.1f} min audio, "
          f"{el:.0f}s cpu ({dur/el:.1f}x realtime)")


if __name__ == "__main__":
    for mid in sys.argv[1:]:
        run(mid)
