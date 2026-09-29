"""Ghep tieng day du tu ban tai tron vao doan bi cut tieng. Usage: py fix_audio.py seg.webm full.mp4 guess_start_s out.mkv
Do lech bang tuong quan cheo 20s tieng dau doan (co that) voi ban tron quanh guess +-30s."""
import sys, subprocess, numpy as np
seg, full, guess, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
SR = 4000
def pcm(p, ss, t):
    b = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(max(0, ss)), "-i", p, "-t", str(t), "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True).stdout
    return np.frombuffer(b, np.int16).astype(np.float32)
a = pcm(seg, 5, 20); lo = max(0, guess - 30)
b = pcm(full, lo, 80)
a = (a - a.mean()) / (a.std() + 1e-6); b = (b - b.mean()) / (b.std() + 1e-6)
n = len(b) + len(a); fa = np.fft.rfft(a, n); fb = np.fft.rfft(b, n)
c = np.fft.irfft(fb * np.conj(fa), n)[: len(b) - len(a)]
k = int(np.argmax(c)); off = lo + k / SR - 5
score = float(c[k] / len(a))
print(f"offset {off:.3f}s score {score:.2f}")
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", seg], capture_output=True, text=True).stdout)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", seg, "-ss", f"{off:.3f}", "-i", full, "-map", "0:v", "-map", "1:a", "-t", str(dur), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", out], check=True)
print("wrote", out, dur)
