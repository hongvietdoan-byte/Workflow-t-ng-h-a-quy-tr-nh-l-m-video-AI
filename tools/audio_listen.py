"""Listen to a video's sound without ears (S0.12, người dùng 2026-09-29: Claude cannot hear — measure instead).

    py tools/audio_listen.py VIDEO [--start 0 --end 180] [--out DIR] [--whisper small] [--lang zh] [--no-tags] [--no-words]

Steps, all local, 0 USD (models downloaded once from their official hosts):
1. demucs (Meta, htdemucs) splits the sound into vocals / drums / bass / other → "music" = drums + bass + other;
2. loudness per second of the voice and of the music → where music is present, enters, stops, swells (thresholds below);
3. AudioSet tags per 2 s window of the music stem (MIT/ast-finetuned-audioset, Hugging Face) — instruments and the mood classes
   ("Sad music", "Tender music", "Exciting music", "Scary music", "Happy music", "Angry music");
4. faster-whisper (SYSTRAN) on the vocals stem → lines with time marks;
5. librosa: tempo and a rough key of the music stem.
Writes <out>/listen.json and <out>/listen.md (a readable timeline). Every value is a measurement or a model's guess with its score —
never a fixed meaning (knowledge/craft/PHUONG_PHAP_PHAN_TICH.md)."""
import argparse
import json
import os
import subprocess
import sys

import numpy as np

MUSIC_ON_DB = -38.0        # music stem RMS above this (dBFS) = clear music
MUSIC_SOFT_DB = -50.0      # between the two: a soft bed (ducked under dialogue); below: no music
VOICE_ON_DB = -35.0
SWELL_DB = 6.0             # music louder by this over 3 s = a swell
MOODS = ("Happy music", "Sad music", "Tender music", "Exciting music", "Angry music", "Scary music", "Funny music")


def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def load(path, sr=22050):
    import librosa
    y, _ = librosa.load(path, sr=sr, mono=True)
    return y, sr


def rms_db(y, sr, hop_s=1.0):
    n = int(sr * hop_s)
    out = []
    for i in range(0, len(y), n):
        seg = y[i:i + n]
        r = float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0
        out.append(round(20 * np.log10(max(r, 1e-6)), 1))
    return out


def level(v):
    """0 = no music, 1 = soft music (under the dialogue — a ducked bed reads here), 2 = clear music."""
    return 0 if v < MUSIC_SOFT_DB else (1 if v < MUSIC_ON_DB else 2)


LEVEL_WORDS = {0: "không nhạc", 1: "nhạc nhỏ (nền dưới thoại)", 2: "nhạc rõ"}


def events(music_db, hold=2):
    """Changes of the music level (3 s median, a new level must hold `hold` s) — test on #8 v4: the planned silences at 37–44 s and
    54–58 s came out, the ducked bed under the lines no longer flickers on / off every second."""
    sm = [float(np.median(music_db[max(0, t - 1):t + 2])) for t in range(len(music_db))]
    lv = [level(v) for v in sm]
    ev, cur = [], None
    for t in range(len(lv)):
        if lv[t] != cur and all(x == lv[t] for x in lv[t:t + hold]):
            ev.append({"t": t, "what": LEVEL_WORDS[lv[t]], "db": round(sm[t], 1)})
            cur = lv[t]
        if t >= 3 and lv[t] and sm[t] - sm[t - 3] >= SWELL_DB and (not ev or ev[-1]["t"] < t - 2):
            ev.append({"t": t, "what": "nhạc to lên", "db": round(sm[t], 1)})
    return ev


def tags(music_wav, win=2.0):
    from transformers import pipeline
    clf = pipeline("audio-classification", model="MIT/ast-finetuned-audioset-10-10-0.4593", top_k=40)
    y, sr = load(music_wav, 16000)
    out = []
    for i in range(0, len(y), int(sr * win)):
        seg = y[i:i + int(sr * win)]
        if len(seg) < sr * 0.5:
            break
        res = clf({"raw": seg, "sampling_rate": sr})
        top = [(r["label"], round(r["score"], 2)) for r in res[:4]]
        mood = [(r["label"], round(r["score"], 2)) for r in res if r["label"] in MOODS and r["score"] >= 0.05]
        out.append({"t": round(i / sr, 1), "top": top, "mood": mood})
    return out


def words(vocals_wav, model, lang):
    from faster_whisper import WhisperModel
    m = WhisperModel(model, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(vocals_wav, language=lang, vad_filter=True)
    return [{"start": round(s.start, 1), "end": round(s.end, 1), "text": s.text.strip()} for s in segs]


def music_facts(music_wav):
    import librosa
    y, sr = load(music_wav)
    if float(np.sqrt(np.mean(y ** 2))) < 1e-4:
        return {}
    tempo = librosa.feature.tempo(y=y, sr=sr)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    major = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    best = max(((np.corrcoef(np.roll(p, k), chroma)[0, 1], f"{names[k]} {'trưởng' if p is major else 'thứ'}")
                for p in (major, minor) for k in range(12)))
    return {"tempo_bpm": round(float(np.atleast_1d(tempo)[0]), 1), "key_guess": best[1], "key_score": round(float(best[0]), 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--start", type=float, default=0)
    ap.add_argument("--end", type=float, default=0)
    ap.add_argument("--out", default="")
    ap.add_argument("--whisper", default="small")
    ap.add_argument("--lang", default=None)
    ap.add_argument("--no-tags", action="store_true")
    ap.add_argument("--no-words", action="store_true")
    a = ap.parse_args()
    out = a.out or os.path.splitext(a.video)[0] + "_listen"
    os.makedirs(out, exist_ok=True)
    wav = os.path.join(out, "mix.wav")
    cut = (["-ss", str(a.start)] + (["-to", str(a.end)] if a.end else []))
    run(["ffmpeg", "-y", "-v", "error", *cut, "-i", a.video, "-vn", "-ac", "2", "-ar", "44100", wav])
    run([sys.executable, "-m", "demucs.separate", "-n", "htdemucs", "-o", out, wav])
    stem = os.path.join(out, "htdemucs", "mix")
    music = os.path.join(out, "music.wav")
    run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(stem, "drums.wav"), "-i", os.path.join(stem, "bass.wav"),
         "-i", os.path.join(stem, "other.wav"), "-filter_complex", "amix=inputs=3:normalize=0", music])
    vocals = os.path.join(stem, "vocals.wav")
    ym, sr = load(music)
    yv, _ = load(vocals)
    res = {"source": os.path.basename(a.video), "start": a.start, "music_db": rms_db(ym, sr), "voice_db": rms_db(yv, sr)}
    res["music_events"] = events(res["music_db"])
    res["music_share"] = round(sum(v > MUSIC_SOFT_DB for v in res["music_db"]) / max(len(res["music_db"]), 1), 2)
    res["music"] = music_facts(music)
    if not a.no_tags:
        res["tags"] = tags(music)
    if not a.no_words:
        res["lines"] = words(vocals, a.whisper, a.lang)
    with open(os.path.join(out, "listen.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    md = [f"# Nghe bằng số — {res['source']} (từ {a.start:g} s)", "",
          f"- Có nhạc {int(res['music_share'] * 100)} % thời gian (lớp nhạc tách bằng demucs: > {MUSIC_SOFT_DB} dBFS nhỏ, > {MUSIC_ON_DB} rõ)",
          f"- Tempo ~{res['music'].get('tempo_bpm', '?')} BPM · giọng đoán {res['music'].get('key_guess', '?')} "
          f"(độ khớp {res['music'].get('key_score', '?')})", "", "## Sự kiện nhạc (giây trong đoạn)"]
    md += [f"- {e['t']} s: {e['what']} ({e['db']} dB)" for e in res["music_events"]] or ["- (không có)"]
    if res.get("tags"):
        md += ["", "## Nhãn AudioSet trên lớp nhạc (2 s / dòng)"]
        md += [f"- {t['t']} s: " + ", ".join(f"{l} {s}" for l, s in t["top"]) + (" · cảm xúc: " + ", ".join(f"{l} {s}" for l, s in t["mood"])
               if t["mood"] else "") for t in res["tags"]]
    if res.get("lines"):
        md += ["", "## Lời thoại / lời hát (faster-whisper trên lớp giọng)"]
        md += [f"- {l['start']}–{l['end']} s: {l['text']}" for l in res["lines"]]
    with open(os.path.join(out, "listen.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(os.path.join(out, "listen.md"))


if __name__ == "__main__":
    main()
