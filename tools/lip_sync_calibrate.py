"""S4.5: calibrate clip_measure.lip_sync on real clips (free — local models only). Prints, per spoken line, the mouth ↔ voice score
with the right voice, the same voice moved off its time ("wrong_time"), and another voice put at the same seconds ("other_voice").

    py -3 tools/lip_sync_calibrate.py [--data D:/AI-Video-Pipeline/data/projects] [--out D:/AI-Video-Output/...]

Cases (29/09): #8's 4 shots lip-synced one by one (videos/<idx>_raw.mp4 = the generated clip, on the timeline of lipsync/shot_<id>.wav)
and #10's dialogue take S4.6 (c) — 2 clips, voice lipsync/take_s3.wav, lines MAXIM 0.3–1.7 · KENTA 2.1–2.8 · KELLY 3.2–3.9 s."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import clip_measure as cm  # noqa: E402

N8 = {21: 158, 25: 162, 28: 165, 31: 168}
TAKE10 = [{"speaker": "MAXIM", "start": 0.3, "end": 1.7}, {"speaker": "KENTA", "start": 2.1, "end": 2.8},
          {"speaker": "KELLY", "start": 3.2, "end": 3.9}]
CLIPS10 = ["khop-moi_c_ingame_co-giong.mp4", "khop-moi_c_ta-thuc-3d_co-giong.mp4"]


def other_voice(trk, fps, n, turn, voices):
    """Best score when another voice's loud part is put inside this line's window (does the check hear syllables, or only timing?)."""
    import numpy as np
    t = np.arange(n) / fps
    win = (t >= turn["start"] - cm.LIP_PAD) & (t <= turn["end"] + cm.LIP_PAD)
    size, first = int(win.sum()), int(np.argmax(win))
    scores = []
    for v in voices:
        env = cm._voice_envelope(v, fps, int(8 * fps))
        on = [i for i, e in enumerate(env) if e > max(env) * 0.1]
        for st in range(on[0], max(on[0] + 1, on[-1] - size), 6):
            if st + size > len(env):
                continue
            e = np.zeros(n)
            e[first:first + size] = env[st:st + size]
            vals = [cm._lag_corr(np.array([np.nan if x is None else x for x in k["open"]]), e) for k in trk]
            vals = [x for x in vals if x is not None]
            if vals:
                scores.append(max(vals))
    return (round(float(np.median(scores)), 2), round(max(scores), 2)) if scores else (None, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(os.path.dirname(__file__), "..", "data", "projects"))
    ap.add_argument("--out", default=r"D:\AI-Video-Output\2026-09-29_ab-hanh-dong-s4-6\vong2")
    a = ap.parse_args()
    wav8 = {s: os.path.join(a.data, "8", "lipsync", f"shot_{s}.wav") for s in N8.values()}
    take = os.path.join(a.data, "10", "lipsync", "take_s3.wav")
    rows = []
    for idx, sid in N8.items():
        clip = os.path.join(a.data, "8", "videos", f"{idx}_raw.mp4")
        if os.path.exists(clip):
            rows.append((f"#8 clip {idx}", clip, wav8[sid], None, [w for s, w in wav8.items() if s != sid]))
    for c in CLIPS10:
        clip = os.path.join(a.out, c)
        if os.path.exists(clip) and os.path.exists(take):
            rows.append((f"#10 {c}", clip, take, TAKE10, list(wav8.values())))
        else:
            print("THIẾU:", clip, "hoặc", take)
    for name, clip, voice, turns, others in rows:
        trk = cm.mouth_tracks(clip)
        res = cm.lip_sync(clip, voice, turns, tracks=trk)
        print(name, "→", res.get("flag"), res.get("note") or "")
        for r in res.get("turns", []):
            if "score" in r:
                med, top = other_voice(trk[0], trk[1], trk[2], r, others)
                r["other_voice"] = {"median": med, "max": top}
            print("   ", json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
