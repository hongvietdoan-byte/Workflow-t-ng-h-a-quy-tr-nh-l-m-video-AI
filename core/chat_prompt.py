"""D6 "đường như chat" (người dùng 14/10, docs/DANH_GIA_VAI_DAO_DIEN_2026-10-14.md mục 3b–3c; cờ `chat_prompts`, TẮT).

Người dùng: đưa ảnh + nội dung cho Claude viết prompt Seedance thì hầu như đều tốt; trong pipeline thì kém — vì prompt gửi đi là bản CODE ghép
(chữ Đạo diễn viết mù trước khi có ảnh + ~10 lớp câu nối thêm), không có Claude nào NHÌN đúng các ảnh sẽ gửi rồi viết một đoạn liền mạch. Người
dùng chỉ MÔ TẢ; chuyển thành prompt là việc của công cụ.

Ở đây, ngay trước khi gửi (runner `_finish_args` cho ảnh, `_submit_args` cho video), MỘT lượt Claude cho mỗi shot nhận đúng như trong chat:
các ảnh sẽ gửi (khung đầu, ảnh tham chiếu, bản lỗi lần trước nếu là gen lại), ý đồ shot của Đạo diễn, mô tả / ghi chú của người dùng, một trang
hướng dẫn riêng của model đích (`knowledge/model_guides/`), và bản code ghép làm DỮ KIỆN — rồi viết lại thành một prompt liền mạch. Code chỉ KIỂM
(độ dài, mã đánh số ảnh còn đủ, chữ Việt sót, tuổi) — không nối thêm câu. Kết quả lưu theo dấu vân tay đầu vào (runner dựng prompt mỗi vòng chờ:
không trả tiền lặp). Không dùng được (cờ tắt, chưa có Claude, vượt trần, câu trả lời không đạt) → giữ bản code ghép như cũ và NÓI ra (diag).
"""
import hashlib
import json
import os
import re
import shutil
import tempfile
from typing import Dict, List, Optional, Sequence, Tuple

from . import features

FLAG = "chat_prompts"
STAGE = "chat_prompt"
GUIDES = os.path.join(os.path.dirname(__file__), "..", "knowledge", "model_guides")
MAX_IMAGES = 8                         # khung đầu + ảnh tham chiếu + bản lỗi: đủ để nhìn như người dùng đưa trong chat
CACHE_KEY = "chat_prompt:{}"           # app_settings: dấu vân tay đầu vào → prompt đã viết
INTENT_KEYS = ("shot", "size", "angle", "camera_move", "action", "action_peak", "blocking", "performance", "emotional_intent",
               "end_state", "dialogue", "mood", "lighting", "time", "weather", "why")
REF_TOKEN = re.compile(r"\bImages? \d+(?:/\d+)*\b|\bShot \d+\b|\[[A-Z][A-Za-z ]*\]")
MAX_CALLS_PER_JOB = 2                  # inputs that keep changing every poll never pay again and again: the last prompt written is kept
CALLS_KEY = "chat_prompt_calls:{}"
VIETNAMESE = re.compile(r"[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]", re.I)


def enabled() -> bool:
    return features.on(FLAG)


NOTE_LABEL = "Mô tả điều muốn đổi (tiếng Việt được — Claude nhìn ảnh và tự chuyển thành prompt; không cần viết prompt)"


def note_label(old: str) -> str:
    """D4 nhập vào D6 (người dùng 14/10: người dùng chỉ MÔ TẢ): the reject-note box asks for a description when the flag is on."""
    return NOTE_LABEL if enabled() else old


def guide_for(kind: str, model: Optional[str]) -> str:
    """The one-page guide of the target: image.md, seedance.md, kling.md (unknown video model → seedance.md)."""
    name = "image" if kind == "image" else ("kling" if "kling" in str(model or "").lower() else "seedance")
    with open(os.path.join(GUIDES, f"{name}.md"), encoding="utf-8") as f:
        return f.read()


def intent_of(data: Dict) -> Dict:
    """The Director's intent for the shot (Vietnamese is fine — Claude reads it like the person's chat message)."""
    return {k: data[k] for k in INTENT_KEYS if data.get(k) not in (None, "", [], {})}


def user_notes(conn, scene_id: int, typ: str, retry_reason: Optional[str] = None, limit: int = 3) -> List[str]:
    """What the PERSON said about this shot (their review notes, newest first) + this retry's reason — the description that wins."""
    out = []
    for r in conn.execute("SELECT l.note FROM review_log l JOIN jobs j ON j.id=l.job_id WHERE j.scene_id=? AND j.type=? AND "
                          "l.reviewer_type='user' AND l.note IS NOT NULL AND TRIM(l.note)!='' ORDER BY l.id DESC LIMIT ?",
                          (scene_id, typ, limit)):
        out.append(r[0].strip())
    if retry_reason and retry_reason.strip() and retry_reason.strip() not in out:
        out.append(retry_reason.strip())
    return out


def _file_mark(path: str) -> List:
    """By CONTENT, not date: a start frame re-extracted from the previous clip on every poll is the same picture (no new paid call)."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return [os.path.basename(path), None]
    return [os.path.basename(path), h.hexdigest()[:16]]


def fingerprint(kind: str, model: Optional[str], assembled: str, images: Sequence[Tuple[str, str]], intent: Dict,
                notes: Sequence[str], limit: int) -> str:
    blob = json.dumps({"v": 1, "kind": kind, "model": model, "assembled": assembled, "images": [[lab, _file_mark(p)] for lab, p in images],
                       "intent": intent, "notes": list(notes), "limit": limit, "guide": guide_for(kind, model)},
                      sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def build_text(kind: str, model: Optional[str], assembled: str, images: Sequence[Tuple[str, str]], intent: Dict, notes: Sequence[str],
               limit: int) -> str:
    what = "ảnh khung đầu" if kind == "image" else f"video ({model or 'seedance'})"
    pics = "\n".join(f"- {lab}" for lab, _ in images) or "- (không có ảnh)"
    said = "\n".join(f"- {n}" for n in notes) or "- (người dùng chưa ghi chú gì cho shot này)"
    return (f"Bạn là Đạo diễn kiêm người viết prompt. Viết prompt {what} cho MỘT shot, như khi người dùng đưa ảnh + mô tả cho bạn trong chat.\n\n"
            f"# Hướng dẫn model đích\n{guide_for(kind, model)}\n\n"
            f"# Ảnh bạn đang thấy (đúng các ảnh sẽ gửi, theo thứ tự)\n{pics}\n\n"
            f"# Ý đồ shot của Đạo diễn\n{json.dumps(intent, ensure_ascii=False, indent=1)}\n\n"
            f"# Mô tả / ghi chú của người dùng (thắng ý đồ cũ khi khác nhau)\n{said}\n\n"
            f"# Bản code ghép (DỮ KIỆN — giữ đủ dữ kiện và mọi mã ảnh, được viết lại câu chữ, bỏ trùng, sửa chỗ trái ảnh)\n{assembled}\n\n"
            f"# Trả về\nĐúng một JSON: {{\"prompt\": \"<prompt tiếng Anh, ≤ {limit} ký tự>\", \"changes\": [\"<điều bạn đổi so với bản code "
            "ghép, tiếng Việt, ngắn>\"]}}")


def check(assembled: str, prompt: str, limit: int) -> List[str]:
    """Why the new prompt cannot be sent ([] = it can). Only checks — nothing is added to the text."""
    problems = []
    if not prompt.strip():
        problems.append("prompt rỗng")
    if len(prompt) > limit:
        problems.append(f"dài {len(prompt)} > {limit} ký tự")
    lost = sorted(set(REF_TOKEN.findall(assembled)) - set(REF_TOKEN.findall(prompt)))
    if lost:
        problems.append("mất mã ảnh / shot: " + ", ".join(lost))
    viet_before = set(VIETNAMESE.findall(assembled.lower()))
    if VIETNAMESE.search(prompt) and not viet_before:
        problems.append("còn chữ tiếng Việt")
    return problems


def _validate(obj) -> Dict:
    from .llm_io import SchemaError
    if not isinstance(obj, dict) or not isinstance(obj.get("prompt"), str) or not obj["prompt"].strip():
        raise SchemaError("root: {prompt: chuỗi, changes: [chuỗi]}")
    ch = obj.get("changes")
    if ch is not None and (not isinstance(ch, list) or not all(isinstance(c, str) for c in ch)):
        raise SchemaError("changes: danh sách chuỗi")
    return obj


def estimate(conn, images: int) -> Optional[float]:
    from . import cost
    return cost.llm_estimate(conn, STAGE, 1, images=images, ledger_stage=STAGE)


def _cached(conn, key: str) -> Optional[Dict]:
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (CACHE_KEY.format(key),)).fetchone()
    if row is None:
        return None
    try:
        return json.loads(row[0])
    except ValueError:
        return None


def _store(conn, key: str, value: Dict) -> None:
    conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (CACHE_KEY.format(key), json.dumps(value, ensure_ascii=False)))
    conn.commit()


def previous_take(conn, job, kind: str) -> Tuple[List[Tuple[str, str]], Optional[str]]:
    """The take this one redoes (parent job), as pictures: the image itself, or 3 frames of the clip. (pictures, temp dir or None)."""
    parent = job["parent_job_id"] if "parent_job_id" in job.keys() else None
    row = conn.execute("SELECT result_path FROM jobs WHERE id=?", (parent,)).fetchone() if parent else None
    path = row["result_path"] if row else None
    if not path or not os.path.exists(path):
        return [], None
    if kind == "image":
        return [("Bản lần trước (bị loại — đừng lặp lỗi của nó)", path)], None
    tmp = tempfile.mkdtemp(prefix="chat_prompt_")
    try:
        from .video_analysis import extract_frames
        frames = extract_frames(path, tmp, count=3)
    except Exception:  # noqa: BLE001 - no ffmpeg / unreadable clip: written from the notes only
        shutil.rmtree(tmp, ignore_errors=True)
        return [], None
    return [(f"Khung {i} của clip lần trước (bị loại)", fr) for i, fr in enumerate(frames, 1)], tmp


def rewrite(p, job, kind: str, assembled: str, images: Sequence[Tuple[str, str]], model: Optional[str] = None,
            limit: int = 4000, client=None, say=None) -> str:
    """The prompt to send: Claude's one coherent prompt (cached by its inputs), or `assembled` unchanged when D6 cannot be used — the
    reason said through `say(level, code, message)` (never silent). `images` = (label, path) of the pictures that WILL be sent."""
    if not enabled():
        return assembled
    say = say or (lambda *a: None)
    conn = p.conn
    row = conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
    data = json.loads(row["data"] or "{}") if row else {}
    typ = "image_gen" if kind == "image" else "video_gen"
    intent = intent_of(data)
    notes = user_notes(conn, job["scene_id"], typ, job["retry_reason"] if "retry_reason" in job.keys() else None)
    before, tmp = previous_take(conn, job, kind)
    pics = [(lab, path) for lab, path in images if path and os.path.exists(path)][:MAX_IMAGES - len(before)] + before
    key = fingerprint(kind, model, assembled, pics, intent, notes, limit)
    hit = _cached(conn, key)
    try:
        if hit and hit.get("prompt"):
            return hit["prompt"]
        calls = conn.execute("SELECT value FROM app_settings WHERE key=?", (CALLS_KEY.format(job["id"]),)).fetchone()
        calls = json.loads(calls[0]) if calls else {"n": 0, "last": None}
        if calls["n"] >= MAX_CALLS_PER_JOB:
            say("warn", "chat_prompt_cap", f"D6: job {job['id']} đã gọi Claude {calls['n']} lần mà đầu vào vẫn đổi — "
                + ("dùng bản D6 gần nhất" if calls.get("last") else "gửi bản code ghép như cũ") + " (không gọi thêm)")
            return calls.get("last") or assembled
        if client is None:
            from .prompt_rewrite import client_for
            client = client_for(p)
        if client is None:
            say("warn", "chat_prompt_noclaude", "D6 (đường như chat): chưa có Claude — gửi bản code ghép như cũ")
            return assembled
        from . import llm_runner
        usd = estimate(conn, len(pics))
        calls["n"] += 1
        conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                     (CALLS_KEY.format(job["id"]), json.dumps(calls, ensure_ascii=False)))
        conn.commit()
        try:
            with llm_runner.tagged(STAGE, job["project_id"]):
                obj, _, _ = llm_runner.ask_json(client, build_text(kind, model, assembled, pics, intent, notes, limit), _validate, pics)
        except Exception as e:  # noqa: BLE001 - Claude down / over the cap / bad answer: the old way, said
            say("warn", "chat_prompt_fail", f"D6 (đường như chat) không viết được prompt ({str(e)[:200]}) — gửi bản code ghép như cũ")
            return assembled
        from .runner import no_minor_age
        new = no_minor_age(obj["prompt"]).strip()
        problems = check(assembled, new, limit)
        if problems:
            say("warn", "chat_prompt_refused", "D6: bản Claude viết không gửi được (" + "; ".join(problems) + ") — gửi bản code ghép như cũ")
            return assembled
        calls["last"] = new
        conn.execute("UPDATE app_settings SET value=? WHERE key=?", (json.dumps(calls, ensure_ascii=False), CALLS_KEY.format(job["id"])))
        _store(conn, key, {"prompt": new, "changes": obj.get("changes") or [], "job": job["id"], "kind": kind, "usd_est": usd,
                           "assembled_len": len(assembled)})
        say("info", "chat_prompt", f"D6 (đường như chat): Claude nhìn {len(pics)} ảnh viết lại prompt {('ảnh' if kind == 'image' else 'video')} "
            f"({len(assembled)} → {len(new)} ký tự)" + (f", ≈ {usd:.3f} USD" if usd is not None else "")
            + ("; đổi: " + "; ".join((obj.get("changes") or [])[:3]) if obj.get("changes") else ""))
        return new
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
