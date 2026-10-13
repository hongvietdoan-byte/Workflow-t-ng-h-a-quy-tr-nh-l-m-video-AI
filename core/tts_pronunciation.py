"""Đ12v6: từ điển chữ TTS theo profile giọng, không SSML và không tự gửi lại."""
import hashlib
import json
import re
from . import access


def validate(words):
    if not isinstance(words, dict) or len(words) > 100:
        raise ValueError("Từ điển phải là object, tối đa 100 cụm từ")
    clean = {}
    for src, dst in words.items():
        if not isinstance(src, str) or not isinstance(dst, str) or not src.strip() or not dst.strip():
            raise ValueError("Mỗi mục cần cụm gốc và chữ TTS không rỗng")
        if len(src) > 100 or len(dst) > 200 or any(c in src + dst for c in "<>\n\r"):
            raise ValueError("Chỉ nhận chữ thuần, không SSML; cụm gốc ≤100, chữ TTS ≤200 ký tự")
        key = src.strip()
        if key.casefold() in {k.casefold() for k in clean}:
            raise ValueError("Cụm từ bị trùng")
        clean[key] = dst.strip()
    return clean


def apply(text, words):
    words = validate(words)
    if not words:
        return text
    lookup = {k.casefold(): v for k, v in words.items()}
    pattern = r"(?<![\w])(?:" + "|".join(re.escape(k) for k in sorted(words, key=len, reverse=True)) + r")(?![\w])"
    return re.sub(pattern, lambda m: lookup[m.group().casefold()], text, flags=re.IGNORECASE)


def prepare(text, profile, model):
    cfg = profile.get("pronunciation") or {}
    if not isinstance(cfg, dict):
        raise ValueError("Từ điển phát âm bị hỏng — lưu lại trước khi tạo giọng")
    words = cfg.get("words") or {} if cfg.get("voice_id") == profile.get("voice_id") and cfg.get("model") == model else {}
    said = apply(text, words)
    scope = [said, profile.get("voice_id"), model]
    key = hashlib.sha256(json.dumps(scope, ensure_ascii=False).encode()).hexdigest()
    return said, {"key": key, "voice_id": profile.get("voice_id"), "model": model,
                  "sent_text": said, "dictionary_hash": hashlib.sha256(json.dumps(words, sort_keys=True, ensure_ascii=False).encode()).hexdigest()}


def save(p, project_id, name, words):
    from . import voice
    access.need_edit(p, project_id, "lưu từ điển phát âm")
    row = p.conn.execute("SELECT voice_profile FROM characters WHERE project_id=? AND name=?", (project_id, name)).fetchone()
    profile = voice.get_profile(row)
    if not profile.get("voice_id"):
        raise ValueError("Chọn giọng trước khi lưu từ điển")
    profile["pronunciation"] = {"words": validate(words), "voice_id": profile["voice_id"], "model": voice.vi_model(profile.get("model"))}
    voice.set_profile(p.conn, project_id, name, profile)


def _identity(e):
    return [e.get(k) for k in ("asset_id", "scene_id", "line", "file", "text", "pronunciation", "state")]


def _local_path(directory, filename):
    import ntpath
    from pathlib import Path
    # Chặn UNC/drive/escape bằng cú pháp trước khi resolve (có thể truy cập mạng).
    if not isinstance(filename, str) or not filename or ntpath.splitdrive(filename)[0] or filename.startswith(("/", "\\")):
        return None
    parts = filename.replace("\\", "/").split("/")
    if any(part in ("..", "") or ":" in part for part in parts):
        return None
    root = Path(directory).resolve()
    target = root.joinpath(*parts).resolve()
    return str(target) if target.is_relative_to(root) else None


def check(directory, asr=None, *, p=None, project_id=None, force=False):
    from . import audio_lib, voice_check
    import os
    if p is not None:
        access.need_edit(p, project_id, "kiểm phát âm")
    asr = asr or voice_check.transcribe_local
    updates = []
    for e in audio_lib.load(directory):
        if not e.get("pronunciation") or e.get("state") != "succeeded":
            continue
        path = _local_path(directory, e.get("file"))
        problem = None
        stamp = None
        if path is None:
            problem = "Đường dẫn giọng không thuộc dự án — cần kiểm tra file"
        elif not os.path.isfile(path):
            problem = "Thiếu file giọng — cần khôi phục hoặc tạo lại bằng tay"
        else:
            stamp = [e["file"], os.stat(path).st_mtime_ns, e.get("text"), os.environ.get("VOICE_ASR_MODEL", "small"), 1]
        previous = e.get("pronunciation_check") or {}
        if not force and stamp is not None and previous.get("stamp") == stamp and previous.get("heard") is not None:
            continue
        heard = None
        if not problem:
            try:
                heard = asr(path)
            except Exception:
                pass
        result = voice_check.compare(e.get("text") or "", heard) if heard is not None else None
        differs = heard is not None and voice_check._words(e.get("text")) != voice_check._words(heard)
        checked = {"stamp": stamp, "level": "yellow" if heard is None or differs else "ok", "heard": heard,
            "score": result["score"] if result else None,
            "message": problem or ("Chưa có ASR/model local — nghe lại; không tải model tự động" if heard is None else
                       "Chữ nghe khác gốc — nghe lại và thêm cụm từ vào từ điển phát âm" if differs else "Chữ nghe khớp câu gốc")}
        updates.append((_identity(e), checked))
    def patch(items):
        changed = False
        for identity, checked in updates:
            for e in items:
                if _identity(e) != identity or e.get("state") != "succeeded":
                    continue
                if checked["stamp"] is not None:
                    path = _local_path(directory, e.get("file"))
                    try:
                        if path is None or os.stat(path).st_mtime_ns != checked["stamp"][1]:
                            continue
                    except OSError:
                        continue
                if e.get("pronunciation_check") != checked:
                    e["pronunciation_check"] = checked
                    changed = True
        return changed
    if updates:
        audio_lib.patch_manifest(directory, patch)


def changed(entry, original, said, meta):
    previous = entry.get("pronunciation") or {}
    return (previous.get("key") != meta["key"] if previous else
            said != original or entry.get("model", meta["model"]) != meta["model"])


def stale_lines(conn, project_id, data_dir):
    from . import voice, audio_lib
    made = {(e.get("scene_id"), e.get("line")): e for e in audio_lib.load(audio_lib.assets_dir(data_dir, project_id))
            if e.get("kind") == "tts" and e.get("state") == "succeeded"}
    out = []
    for ln in voice.planned_lines(conn, project_id):
        e = made.get((ln["scene_id"], ln["line"]))
        if not e or not ln.get("voice"):
            continue
        model = voice.vi_model(ln["voice"].get("model"))
        original = voice.speakable(ln["text"])
        try:
            said, meta = prepare(original, ln["voice"], model)
        except ValueError:
            out.append(ln)  # UI báo cần sửa; generate vẫn chặn thay vì bỏ qua từ điển hỏng
            continue
        if changed(e, original, said, meta):
            out.append(ln)
    return out
