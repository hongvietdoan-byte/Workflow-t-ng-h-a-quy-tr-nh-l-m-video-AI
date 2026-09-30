"""S2.6 + S1.15 — thử có trả tiền (người dùng duyệt 01/10; nhánh C): trần riêng ≤ MAX_SENDS lượt âm thanh và ≤ CAP_USD.

S2.6  Seed Audio 1.0: MỘT track thoại cả cảnh (cảnh truyện 2 của dự án #8: Maxim / Kenta / Kelly, 5 câu) khóa giọng bằng 3 file mẫu
      (@Audio1–3 = file gốc đã dùng để clone 3 giọng team FF: Kelly 70, Kenta 30168, Maxim 72), tiếng Việt, mốc [x.xs:y.ys],
      xin mốc phụ đề (enable_subtitle). So với TTS từng câu của #8 (đọc từ CSDL + audio_assets, KHÔNG sửa #8).
S1.15 Eleven Music v2.5 (`music_v2_5`, tên lấy từ web ClipAI): 1 bản theo đúng brief của bản music_v2 mới nhất của #8 (draft 30747),
      cùng độ dài — so độ dài, LUFS, nghe bằng tools/audio_listen.py.

    py <worktree>/tools/experiments/audio_s26_s115.py refs            tải 3 file giọng mẫu, đo độ dài (0 USD)
    py <worktree>/tools/experiments/audio_s26_s115.py plan            in đúng yêu cầu sẽ gửi (0 USD)
    py <worktree>/tools/experiments/audio_s26_s115.py seed --variant 1 --why "..."    gửi Seed Audio (qua trần + sổ chi)
    py <worktree>/tools/experiments/audio_s26_s115.py music --why "..."               gửi Eleven Music v2.5 (qua trần + sổ chi)
    py <worktree>/tools/experiments/audio_s26_s115.py poll            chờ + tải về + lưu nguyên mục audio-list (0 USD)
    py <worktree>/tools/experiments/audio_s26_s115.py check           đo: chữ (faster-whisper), mốc, giọng, LUFS (0 USD)

Chạy từ D:\\AI-Video-Pipeline (CSDL + dashboard.env + token ở đó)."""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

OUT = "D:/AI-Video-Output/2026-10-01_s2-6_s1-15"
RUNS = os.path.join(OUT, "runs.json")
MAX_SENDS = 10            # nhánh C: ≤ 10 lượt âm thanh (đợt thử còn 24 lượt chung)
CAP_USD = 1.0             # nhánh C: ≤ 1,0 USD (âm thanh chưa có giá trong pricing.json → ước tính theo giá web niêm yết)
MAX_TRIES = 3             # lần đầu + tạo lại tối đa 2 lần (mỗi lần đổi đầu vào, có lý do)
PID = 8                   # dự án #8 — chỉ ĐỌC
STORY_SCENE = 2           # cảnh truyện 2: Maxim hỏi, Kenta chặn, Maxim trêu, Kelly xin, Kenta từ chối (3 nhân vật, 5 câu)
# Giá niêm yết trên web (docs/PHAN_TICH_CLIP_MAU_CLIPAI_2026-09-28.md mục 4): Seed Audio ≈ 15 ¢/phút; Eleven Music v2.5 ≈ 7,5 ¢/30 s.
SEED_USD_PER_MIN = 0.15
MUSIC_USD_PER_30S = 0.075
VOICES = {"KELLY": 70, "KENTA": 30168, "MAXIM": 72}      # data/voices_vi.json (Kenta: 69 đã bỏ 29/09 → 30168)
ORDER = ("KELLY", "KENTA", "MAXIM")                       # @Audio1, @Audio2, @Audio3
WHO = {"KELLY": "Kelly is a young woman", "KENTA": "Kenta is a young man", "MAXIM": "Maxim is a young man, Kenta's friend"}
# Cách nói lấy từ `delivery` của #8, dịch sang tiếng Anh cho phần chỉ đạo (lời thoại giữ nguyên tiếng Việt).
MANNER = {
    "tò mò, trêu nhẹ": "curious, lightly teasing",
    "lạnh, chặn lại": "cold, cutting him off, fast",
    "khẳng định đùa mà thật": "half joking but meaning it",
    "cầu xin nhưng cứng rắn": "pleading but firm, slow, after a short pause",
    "kiên quyết, có gì đó nặng nề": "resolute, something heavy in the voice, slow",
}
MUSIC_SOURCE_DRAFT = "30747"      # bản music_v2 mới nhất của #8 (brief theo nhịp truyện, 88,53 s)


def _env():
    from tools.experiments.group_test import load_env
    load_env(os.getcwd())


def _conn():
    from core.db import connect
    return connect(os.environ.get("PIPELINE_DB") or os.path.join("data", "manifest.sqlite"))


def _runs():
    try:
        with open(RUNS, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def _save_runs(runs):
    os.makedirs(OUT, exist_ok=True)
    with open(RUNS, "w", encoding="utf-8") as f:
        json.dump(runs, f, ensure_ascii=False, indent=1)


def _spent_usd(runs):
    """Tiền thật khi ClipAI trả `cost` (≈ 0,01 USD/đơn vị); không có thì dùng ước tính đã ghi lúc gửi."""
    total = 0.0
    for r in runs:
        total += (r["cost_units"] * 0.01) if r.get("cost_units") is not None else r.get("est_usd", 0.0)
    return round(total, 4)


def guard(est_usd, kind):
    runs = _runs()
    sends = len(runs)
    if sends + 1 > MAX_SENDS:
        raise SystemExit(f"TRẦN CHẶN: đã gửi {sends}/{MAX_SENDS} lượt âm thanh của nhánh")
    tries = sum(1 for r in runs if r["kind"] == kind)
    if tries + 1 > MAX_TRIES:
        raise SystemExit(f"TRẦN CHẶN: {kind} đã gửi {tries} lần (lần đầu + tạo lại ≤ 2)")
    usd = _spent_usd(runs)
    if usd + est_usd > CAP_USD + 1e-9:
        raise SystemExit(f"TRẦN CHẶN: đã chi ≈ ${usd:.3f} + lần này ≈ ${est_usd:.3f} > trần ${CAP_USD:.2f}")
    print(f"trần nhánh: {sends}/{MAX_SENDS} lượt, ≈ ${usd:.3f} + ${est_usd:.3f} ≤ ${CAP_USD:.2f}")


# ---- dữ liệu #8 (chỉ đọc) --------------------------------------------------------------------------------------------------------
def scene_lines(conn):
    """Các câu thoại của cảnh truyện STORY_SCENE (CSDL) + mốc đặt câu của bản mix #8 (audio_assets/assets.json)."""
    rows = conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (PID,)).fetchall()
    shots = [(r["id"], r["idx"], json.loads(r["data"] or "{}")) for r in rows]
    shots = [s for s in shots if s[2].get("story_scene") == STORY_SCENE]
    if not shots:
        raise SystemExit(f"#8 không có cảnh truyện {STORY_SCENE}")
    with open(os.path.join("data", "projects", str(PID), "audio_assets", "assets.json"), encoding="utf-8") as f:
        assets = [a for a in json.load(f) if a.get("kind") == "tts" and a.get("use")]
    by_scene = {a["scene_id"]: a for a in assets}
    lines = []
    for sid, idx, d in shots:
        for n, dl in enumerate(d.get("dialogue") or [], 1):
            a = by_scene.get(sid)
            if not a:
                raise SystemExit(f"shot {idx} có thoại nhưng #8 không có file TTS — không so được (không im lặng)")
            lines.append({"shot": idx, "speaker": dl["speaker"], "text": dl["text"], "delivery": dl.get("delivery") or {},
                          "tts_file": os.path.join("data", "projects", str(PID), "audio_assets", a["file"]),
                          "tts_voice": a.get("voice_id"), "abs_start": float(a["start"]), "dur": a["duration_ms"] / 1000.0})
    return lines


def timeline(lines, lead=1.2, tail=1.8):
    """Mốc trong track cảnh = mốc của bản mix #8, dời về 0 (câu đầu ở `lead` s); mốc làm tròn 0,1 s (Seed Audio: 100 ms)."""
    t0 = lines[0]["abs_start"] - lead
    for ln in lines:
        ln["t0"] = round(ln["abs_start"] - t0, 1)
        ln["t1"] = round(ln["abs_start"] - t0 + ln["dur"], 1)
    total = round(lines[-1]["t1"] + tail, 1)
    return lines, total


# ---- S2.6 prompt ----------------------------------------------------------------------------------------------------------------
def seed_text(lines, total, variant=1):
    """variant 1: chỉ đạo tiếng Anh + lời tiếng Việt trong ngoặc kép, mỗi câu một mốc [a s:b s] (định dạng Prompt Assistant)."""
    head = []
    for k, who in enumerate(ORDER, 1):
        head.append(f"{WHO[who]}; {who.title()}'s voice is exactly the voice in @Audio{k}.")
    head.append("All dialogue is spoken in Vietnamese, natural and conversational, each speaker keeping the accent and timbre "
                "of their reference audio.")
    head.append(f"Total audio duration: {total:.1f} seconds. Dialogue only: no music, no sound effects, no ambience; "
                "silence between the lines.")
    body = []
    for ln in lines:
        manner = MANNER.get(ln["delivery"].get("emotion", ""), ln["delivery"].get("emotion", ""))
        stress = ln["delivery"].get("stress")
        extra = f", stressing \u201c{stress}\u201d" if stress else ""
        k = ORDER.index(ln["speaker"]) + 1
        body.append(f"[{ln['t0']:.1f}s:{ln['t1']:.1f}s] {ln['speaker'].title()} (@Audio{k}), {manner}{extra}: \u201c{ln['text']}\u201d")
    if variant == 2:
        # đổi đầu vào (chỉ dùng khi lần 1 lệch giọng): nhắc lại giọng ngay trong từng câu + cấm pha giọng
        head.append("Never mix the voices: each line is spoken only by its own speaker's reference voice.")
    return "\n".join(head) + "\n\n" + "\n".join(body)


# ---- refs ------------------------------------------------------------------------------------------------------------------------
def _probe_seconds(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True)
    try:
        return round(float(out.stdout.strip()), 2)
    except ValueError:
        return None


def ref_urls(provider):
    """Mẫu giọng = file gốc mà team đã dùng để clone từng giọng (voice-actors ?game_code=FF → input_params.audio_url)."""
    voices = {v.get("id"): v for v in provider.voice_actors(game_code="FF")}
    urls = {}
    for who in ORDER:
        v = voices.get(VOICES[who])
        url = ((v or {}).get("input_params") or {}).get("audio_url")
        if not url:
            raise SystemExit(f"không lấy được file mẫu của giọng {VOICES[who]} ({who}) — dừng, không gửi thiếu mẫu")
        urls[who] = url
    return urls


def cmd_refs(provider):
    os.makedirs(os.path.join(OUT, "ref"), exist_ok=True)
    for who, url in ref_urls(provider).items():
        dest = os.path.join(OUT, "ref", f"{who.lower()}_{VOICES[who]}.mp3")
        if not os.path.exists(dest):
            urllib.request.urlretrieve(url, dest)
        size = os.path.getsize(dest)
        sec = _probe_seconds(dest)
        ok = sec is not None and sec <= 30 and size <= 10 * 1024 * 1024
        print(who, VOICES[who], f"{sec}s", f"{size / 1e6:.2f} MB", "OK" if ok else "VƯỢT GIỚI HẠN (≤ 30 s, ≤ 10 MB)", url)


def cmd_plan(provider, conn, variant):
    from core.adapters.clipai_audio import ClipAIAudioProvider
    lines, total = timeline(scene_lines(conn))
    text = seed_text(lines, total, variant)
    urls = ref_urls(provider)
    body = ClipAIAudioProvider.seed_audio_body(text, [urls[w] for w in ORDER], name=f"s2.6 #8 canh {STORY_SCENE} v{variant}")
    print("== S2.6 Seed Audio — POST /api/sound/generate")
    print(json.dumps(body, ensure_ascii=False, indent=1))
    print(f"ký tự: {len(text)} / 3000 · ước tính ≈ ${total / 60 * SEED_USD_PER_MIN:.3f}")
    d = music_source()
    print("\n== S1.15 Eleven Music v2.5 — POST /api/sound/generate")
    print(json.dumps({"model": "music_v2_5", "provider": "elevenlabs", "type": "music", "prompt": d["prompt"][:120] + "…",
                      "input_params": {"output_format": "mp3", "force_instrumental": True, "music_length_ms": d["length_ms"]}},
                     ensure_ascii=False, indent=1))
    print(f"prompt: {len(d['prompt'])} ký tự · ước tính ≈ ${d['length_ms'] / 30000 * MUSIC_USD_PER_30S:.3f}")
    return lines, total


def music_source():
    with open(os.path.join("data", "projects", str(PID), "music_drafts", "drafts.json"), encoding="utf-8") as f:
        d = next(x for x in json.load(f) if str(x.get("asset_id")) == MUSIC_SOURCE_DRAFT)
    return d


# ---- paid ------------------------------------------------------------------------------------------------------------------------
def _send(provider, conn, kind, model, est, why, submit):
    from core import budget
    from core.cost import record_usage
    guard(est, kind)
    with budget.SPEND_LOCK:
        over = budget.check_audio(conn, provider.name)
        if over:
            raise SystemExit("TRẦN CHUNG CHẶN: " + over)
        runs = _runs()
        rec = {"kind": kind, "model": model, "why": why, "est_usd": round(est, 4), "at": time.strftime("%Y-%m-%d %H:%M:%S"),
               "asset_id": None, "state": "sending"}
        try:
            rec["asset_id"] = submit()
            rec["state"] = "running"
        except Exception as e:  # noqa: BLE001 - kept in runs.json; a refused request is shown, never retried here
            rec.update(state="refused", message=f"{type(e).__name__}: {e}", est_usd=0.0)
            runs.append(rec)
            _save_runs(runs)
            raise SystemExit(f"ClipAI từ chối ({kind}): {e}")
        record_usage(conn, None, "audio", provider.name, model, "default", 1, "item", project_id=None, stage="experiment_s26_s115")
        runs.append(rec)
        _save_runs(runs)
    print("đã gửi:", kind, model, "asset", rec["asset_id"])


def cmd_seed(provider, conn, variant, why):
    lines, total = timeline(scene_lines(conn))
    text = seed_text(lines, total, variant)
    urls = ref_urls(provider)
    est = total / 60 * SEED_USD_PER_MIN * 1.5          # dư 50 % vì giá chưa đo
    _send(provider, conn, "seed", "seed-audio-1.0", est, f"v{variant}: {why}",
          lambda: provider.generate_seed_audio(text, [urls[w] for w in ORDER], name=f"s2.6 #8 canh {STORY_SCENE} v{variant}"))


def cmd_music(provider, conn, why):
    d = music_source()
    est = d["length_ms"] / 30000 * MUSIC_USD_PER_30S * 1.5
    _send(provider, conn, "music", "music_v2_5", est, why,
          lambda: provider.generate_music(d["prompt"], d["length_ms"], True, name="s1.15 #8 v2.5", model="music_v2_5"))


def cmd_poll(provider, wait=900):
    t0 = time.time()
    while True:
        runs = _runs()
        pending = [r for r in runs if r["state"] == "running"]
        for r in pending:
            cat = "tts" if r["kind"] == "seed" else "music"
            item = provider.asset(cat, r["asset_id"])
            if not item:
                continue
            with open(os.path.join(OUT, f"item_{r['kind']}_{r['asset_id']}.json"), "w", encoding="utf-8") as f:
                json.dump(item, f, ensure_ascii=False, indent=1)
            cost = next((item[k] for k in item if re.search(r"cost|credit|price", k, re.I) and isinstance(item[k], (int, float))), None)
            if cost is not None:
                r["cost_units"] = cost
            if item.get("status") == "success" and item.get("url"):
                dest = os.path.join(OUT, f"{r['kind']}_{r['asset_id']}.mp3")
                provider.download(item["url"], dest)
                r.update(state="succeeded", file=os.path.basename(dest), duration_ms=item.get("duration_ms"))
            elif item.get("status") in ("failed", "deleted"):
                r.update(state="failed", message=json.dumps(item.get("provider_error"), ensure_ascii=False))
        _save_runs(runs)
        print(time.strftime("%H:%M:%S"), [(r["kind"], r["asset_id"], r["state"]) for r in runs], flush=True)
        if not any(r["state"] == "running" for r in runs) or time.time() - t0 > wait:
            break
        time.sleep(15)


# ---- đo (0 USD) ------------------------------------------------------------------------------------------------------------------
def _norm(s):
    s = unicodedata.normalize("NFC", s.lower())
    return re.sub(r"[^\w\s]", " ", s).split()


def _wav(src, dest, sr=16000):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-ac", "1", "-ar", str(sr), dest], check=True)
    return dest


def build_tts_track(lines, total, dest):
    """Track so sánh: các file TTS từng câu của #8 đặt đúng mốc t0 (như bản mix #8), cùng độ dài track cảnh."""
    import numpy as np
    import soundfile as sf
    sr = 44100
    track = np.zeros(int(total * sr) + sr, dtype=np.float32)
    for ln in lines:
        tmp = os.path.join(OUT, "tmp_line.wav")
        _wav(ln["tts_file"], tmp, sr)
        y, _ = sf.read(tmp, dtype="float32")
        a = int(ln["t0"] * sr)
        track[a:a + len(y)] += y[: len(track) - a]
    sf.write(dest, track[: int(total * sr)], sr)
    return dest


def transcribe(path, model="small"):
    from faster_whisper import WhisperModel
    m = WhisperModel(model, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(path, language="vi", vad_filter=True, word_timestamps=True)
    out = []
    for s in segs:
        out.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(),
                    "words": [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)} for w in (s.words or [])]})
    return out


def voice_profile(path, t0=None, t1=None):
    """Hồ sơ giọng thô (không tải model): trung vị F0 + trung bình MFCC 2..20 của phần có tiếng. Chỉ để so gần/xa, không phải
    nhận dạng người nói."""
    import librosa
    import numpy as np
    y, sr = librosa.load(path, sr=16000, mono=True, offset=t0 or 0.0, duration=(t1 - t0) if t1 else None)
    if len(y) < 1600:
        return None
    f0, voiced, _ = librosa.pyin(y, fmin=70, fmax=400, sr=sr)
    f0v = f0[voiced] if voiced is not None else []
    mf = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
    rms = librosa.feature.rms(y=y)[0]
    keep = rms[: mf.shape[1]] > (0.2 * rms.max())
    vec = mf[1:, keep].mean(axis=1) if keep.any() else mf[1:].mean(axis=1)
    return {"f0": round(float(np.nanmedian(f0v)), 1) if len(f0v) else None, "mfcc": vec}


def _cos(a, b):
    import numpy as np
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def lufs(path):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", out.stderr, re.S)
    if not m:
        return None
    d = json.loads(m.group(0))
    return {"lufs_i": float(d["input_i"]), "true_peak": float(d["input_tp"]), "lra": float(d["input_lra"])}


def match_lines(lines, segs):
    """Mỗi câu kịch bản ↔ đoạn lời nghe được: chọn cửa sổ từ liên tiếp giống nhất (difflib) — trả độ giống chữ + mốc nghe được."""
    words = [w for s in segs for w in s["words"]]
    toks = [(_norm(w["w"]), w) for w in words]
    flat = [(t, w) for ts, w in toks for t in ts]
    res = []
    for ln in lines:
        want = _norm(ln["text"])
        best = (0.0, None, None)
        for i in range(len(flat)):
            for j in range(i + 1, min(len(flat), i + len(want) + 3) + 1):
                got = [t for t, _ in flat[i:j]]
                r = difflib.SequenceMatcher(None, want, got).ratio()
                if r > best[0]:
                    best = (r, float(flat[i][1]["s"]), float(flat[j - 1][1]["e"]))
        res.append({"speaker": ln["speaker"], "text": ln["text"], "want": [ln["t0"], ln["t1"]], "score": round(best[0], 2),
                    "heard": [best[1], best[2]]})
    return res


def subtitle_marks(item):
    """Mốc phụ đề Seed Audio trả về — tìm mọi trường có 'subtitle'/'sentence'/'word' trong mục audio-list (chưa biết tên chính xác)."""
    found = {}

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                if re.search(r"subtitle|sentence|words?$|timestamp|caption", k, re.I) and v not in (None, "", [], {}, True, False):
                    found[path + k] = v
                walk(v, path + k + ".")
        elif isinstance(node, list):
            for i, v in enumerate(node[:3]):
                walk(v, path + f"[{i}].")
    walk(item, "")
    return found


def cmd_check(provider, conn):
    lines, total = timeline(scene_lines(conn))
    report = {"scene": STORY_SCENE, "total_s": total, "lines": [{k: ln[k] for k in ("speaker", "text", "t0", "t1")} for ln in lines]}
    refs = {who: voice_profile(os.path.join(OUT, "ref", f"{who.lower()}_{VOICES[who]}.mp3")) for who in ORDER}
    report["ref_f0"] = {w: refs[w]["f0"] for w in ORDER}
    tts = build_tts_track(lines, total, os.path.join(OUT, "tts8_track.wav"))
    candidates = [("tts8", tts, None)]
    for r in _runs():
        if r["kind"] == "seed" and r.get("file"):
            candidates.append((f"seed_{r['asset_id']}", os.path.join(OUT, r["file"]), r))
    for name, path, run in candidates:
        wav = _wav(path, os.path.join(OUT, f"{name}_16k.wav"))
        segs = transcribe(wav)
        m = match_lines(lines, segs)
        for x, ln in zip(m, lines):
            if x["heard"][0] is not None:
                p = voice_profile(wav, x["heard"][0], x["heard"][1] + 0.05)
                if p:
                    sims = {w: round(_cos(p["mfcc"], refs[w]["mfcc"]), 3) for w in ORDER}
                    x["f0"] = p["f0"]
                    x["closest_ref"] = max(sims, key=sims.get)
                    x["ref_sim"] = sims
            x["start_err_s"] = None if x["heard"][0] is None else round(x["heard"][0] - x["want"][0], 2)
        entry = {"file": path, "seconds": _probe_seconds(path), "lufs": lufs(path), "asr": segs, "lines": m}
        if run is not None:
            item_path = os.path.join(OUT, f"item_seed_{run['asset_id']}.json")
            if os.path.exists(item_path):
                with open(item_path, encoding="utf-8") as f:
                    entry["subtitles_found"] = {k: (v if len(json.dumps(v, ensure_ascii=False)) < 4000 else "…")
                                                for k, v in subtitle_marks(json.load(f)).items()}
        report[name] = entry
    for r in _runs():
        if r["kind"] == "music" and r.get("file"):
            src = os.path.join("data", "projects", str(PID), "music_drafts", f"draft_{MUSIC_SOURCE_DRAFT}.mp3")
            report["music"] = {"v2": {"file": src, "seconds": _probe_seconds(src), "lufs": lufs(src)},
                               "v2_5": {"file": os.path.join(OUT, r["file"]), "seconds": _probe_seconds(os.path.join(OUT, r["file"])),
                                        "lufs": lufs(os.path.join(OUT, r["file"]))},
                               "brief_length_s": music_source()["length_ms"] / 1000}
    with open(os.path.join(OUT, "check.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1, default=str)
    print(json.dumps({k: v for k, v in report.items() if k not in ("tts8",) and not k.startswith("seed_")}, ensure_ascii=False,
                     indent=1, default=str)[:3000])
    for name, _, _ in candidates:
        e = report[name]
        print(f"\n== {name}: {e['seconds']} s, LUFS {e['lufs']}")
        for x in e["lines"]:
            print(f"  {x['speaker']:6} chữ {x['score']:.2f}  muốn {x['want']} nghe {x['heard']} lệch {x['start_err_s']}  "
                  f"F0 {x.get('f0')} gần {x.get('closest_ref')} {x.get('ref_sim')}  | {x['text']}")
        if e.get("subtitles_found") is not None:
            print("  mốc phụ đề trả về:", json.dumps(e["subtitles_found"], ensure_ascii=False)[:1500])
    print("\n→", os.path.join(OUT, "check.json"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("refs", "plan", "seed", "music", "poll", "check"))
    ap.add_argument("--variant", type=int, default=1)
    ap.add_argument("--why", default="")
    ap.add_argument("--wait", type=int, default=900)
    a = ap.parse_args()
    _env()
    from core.adapters.clipai_audio import ClipAIAudioProvider
    provider = ClipAIAudioProvider.from_env()
    conn = _conn()
    os.makedirs(OUT, exist_ok=True)
    if a.cmd in ("seed", "music") and not a.why:
        raise SystemExit("--why bắt buộc (lý do gửi / đầu vào đã đổi gì)")
    if a.cmd == "refs":
        cmd_refs(provider)
    elif a.cmd == "plan":
        cmd_plan(provider, conn, a.variant)
    elif a.cmd == "seed":
        cmd_seed(provider, conn, a.variant, a.why)
    elif a.cmd == "music":
        cmd_music(provider, conn, a.why)
    elif a.cmd == "poll":
        cmd_poll(provider, a.wait)
    else:
        cmd_check(provider, conn)


if __name__ == "__main__":
    main()
