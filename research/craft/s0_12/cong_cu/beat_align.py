"""Diem cat co trung phach nhac khong. Usage: py beat_align.py <video> <result.json> [t0 t1] [tol=0.08]
In JSON: tempo, so cat trong [t0,t1], ti le cat cach phach <= tol, ti le ngau nhien (2*tol/chu ky), lech trung binh / chu ky
(0 = dung phach, 0.25 = ngau nhien deu). Chi so, khong loi."""
import sys, json, subprocess, tempfile, os
import numpy as np, librosa
v, rj = sys.argv[1], sys.argv[2]
t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
t1 = float(sys.argv[4]) if len(sys.argv) > 4 else 1e9
tol = float(sys.argv[5]) if len(sys.argv) > 5 else 0.08
wav = os.path.join(tempfile.gettempdir(), "beat_align_tmp.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", v, "-ac", "1", "-ar", "22050", wav], check=True)
y, sr = librosa.load(wav, sr=22050); os.remove(wav)
tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
tempo = float(np.atleast_1d(tempo)[0]); period = 60.0 / tempo
beats = beats[(beats >= t0 - period) & (beats <= t1 + period)]
d = json.load(open(rj, encoding="utf-8"))
cuts = [s["start"] for s in d["shots"] if s["start"] > 0 and t0 <= s["start"] <= t1]
if not cuts or len(beats) < 2:
    print(json.dumps({"err": "khong du du lieu", "n_cuts": len(cuts)})); sys.exit()
off = np.array([np.min(np.abs(beats - c)) for c in cuts])
half = np.concatenate([beats, (beats[:-1] + beats[1:]) / 2])
offh = np.array([np.min(np.abs(half - c)) for c in cuts])
out = {"video": os.path.basename(v), "window": [t0, min(t1, float(len(y) / sr))], "tempo_bpm": round(tempo, 1),
       "n_cuts": len(cuts), "tol_s": tol,
       "hit_beat": round(float(np.mean(off <= tol)), 2), "chance_beat": round(min(1.0, 2 * tol / period), 2),
       "hit_half_beat": round(float(np.mean(offh <= tol)), 2), "chance_half_beat": round(min(1.0, 4 * tol / period), 2),
       "mean_offset_over_period": round(float(np.mean(off) / period), 3)}
print(json.dumps(out, ensure_ascii=False))
