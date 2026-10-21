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
import time
from typing import Dict, List, Optional, Sequence, Tuple

from . import features

FLAG = "chat_prompts"
STAGE = "chat_prompt"
GUIDES = os.path.join(os.path.dirname(__file__), "..", "knowledge", "model_guides")
MAX_IMAGES = 8                         # khung đầu + ảnh tham chiếu + bản lỗi: đủ để nhìn như người dùng đưa trong chat
CACHE_KEY = "chat_prompt:{}"           # app_settings: dấu vân tay đầu vào → prompt đã viết
INTENT_KEYS = ("shot", "size", "angle", "camera_move", "action", "action_peak", "blocking", "performance", "emotional_intent",
               "end_state", "dialogue", "mood", "lighting", "time", "weather", "why")
# Kiểm thật #30 14/10: 6/7 bản D6 bị chặn "mất mã Image 3" — Claude viết "Images 2 and 3 show KELLY" (bản code ghép: "Images 2/3"),
# code chỉ đọc được "Images 2" → tưởng mất ảnh 3. Danh từ SỐ NHIỀU "Images" + dãy số nối bằng / , and & - – to: mỗi số một ảnh (dải
# "2-4" = 2, 3, 4). Số ít "Image 2 and 3" KHÔNG tính (có thể là "Image 2 and 3 people").
_LIST_SEP = r"\s*(?:,\s*and|,|and|&|/|-|–|to)\s*"
# #29 926/928 (14/10): "mất mã Shot 1, Shot 2" — a code in other capitals ("SHOT 1", "shot 1", "IMAGE 3") is the same code; the
# number still has to match exactly (\b: "Shot 12" is not "Shot 1"). Block tags [Event] keep their exact spelling.
# Rà 14/10: the codes the rewrite MUST keep are read from the assembled prompt in their exact capitals ("Shot 2", "Image 3") — a
# lower-case "shot 2" there is prose ("same spot as shot 2" = the scene's own shot number), not a code; only the ANSWER is read in
# any capitals (REF_TOKEN_ANY_CASE).
_CODES = r"\bImages \d+(?:" + _LIST_SEP + r"\d+)+\b|\bImages? \d+(?:/\d+)*\b|\bShot \d+\b"
REF_TOKEN = re.compile(_CODES + r"|\[[A-Z][A-Za-z ]*\]")
REF_TOKEN_ANY_CASE = re.compile(r"(?i:" + _CODES + r")|\[[A-Z][A-Za-z ]*\]")
_CODE_WORD = re.compile(r"^(images|image|shot)\b", re.I)
MAX_CALLS_PER_JOB = 2                  # inputs that keep changing every poll never pay again and again: the last prompt written is kept
CALLS_KEY = "chat_prompt_calls:{}"
MAX_FIX_TURNS = 1                      # việc 5 (14/10): a refused answer gets ONE fix turn told the exact fault, per job, then the old way
REFUSED_KEY = "chat_prompt_refused:{}"
# C-M71 A5 (P31-G29): Claude hết tiền / hết lượt — lỗi của TÀI KHOẢN, không phải của job: gửi bản code ghép, MỘT diag có mã (cùng lời →
# runner._diag_once gộp một dòng mỗi job), KHÔNG tính vào MAX_CALLS_PER_JOB (trước: 2 nhịp hết tiền = job mất D6 vĩnh viễn), và không
# gọi lại D6 trong QUOTA_PAUSE_S (mọi job) — llm_runner vốn đã chặn trước khi trả tiền, đây chỉ bớt lượt thử + nhiễu.
QUOTA_CODES = ("out_of_credit", "usage_limit")
QUOTA_CODE = "chat_prompt_quota"
QUOTA_KEY = "chat_prompt_quota"
QUOTA_PAUSE_S = 600
QUOTA_MSG = ("D6 (đường như chat): Claude hết tiền / hết lượt — gửi bản code ghép như cũ; tạm không gọi D6 {m} phút (nạp tiền / chờ giờ "
             "mở lại thì D6 tự chạy lại)")
# Thử D6 #29 14/10: "Images 2/3" là HAI mã (Image 2, Image 3) — Claude viết "Image 2 and Image 3" không phải mất mã.
_IMAGES_GROUP = re.compile(r"\bImages? (\d+(?:/\d+)*)\b")
_IMAGES_LIST = re.compile(r"Images (\d+(?:" + _LIST_SEP + r"\d+)+)", re.I)
_RANGE = re.compile(r"(\d+)\s*(?:-|–|to)\s*(\d+)", re.I)
# Thử D6 #29 14/10 shot 5: D6 tự gọi mốc là "clock tower" (dịch tên Kho "Tháp Đồng Hồ") → Seedance vẽ mặt đồng hồ, tháp thật không có.
# Chữ tả một bộ phận mà bản code ghép không nói thì không được thêm: code đổi về chữ trung tính (không bỏ cả bản D6).
_ADDED_FEATURE = ((re.compile(r"\bclock[- ]?tower\b", re.I), "stone tower"), (re.compile(r"\bclock[- ]?faces?\b", re.I), "tower top"))
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


# #29 job 928 (14/10): the cap said "đầu vào vẫn đổi" while the two paid calls had the SAME inputs (both answers refused, not kept by
# the code of that day). Each paid call now remembers its fingerprint + one short hash per input part, so the cap says the truth:
# same inputs (answers refused / Claude errors) or exactly which part changed. The fingerprint itself is unchanged (stored prompts stay).
PART_NAMES = (("assembled", "bản code ghép"), ("images", "ảnh"), ("intent", "ý đồ shot"), ("notes", "ghi chú người dùng"),
              ("limit", "trần ký tự"), ("model", "model"))


def input_parts(kind: str, model: Optional[str], assembled: str, images: Sequence[Tuple[str, str]], intent: Dict, notes: Sequence[str],
                limit: int) -> Dict[str, str]:
    """{part: short hash} of what `fingerprint` hashes — only to say WHICH input changed between two paid calls."""
    vals = {"assembled": assembled, "images": [[lab, _file_mark(p)] for lab, p in images], "intent": intent, "notes": list(notes),
            "limit": limit, "model": [kind, model, guide_for(kind, model)]}
    return {k: hashlib.sha256(json.dumps(v, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()[:12]
            for k, v in vals.items()}


def cap_reason(calls: Dict, key: str, parts) -> str:
    """Why this job reached MAX_CALLS_PER_JOB, from what its paid calls remembered. parts: {part: short hash}, or a callable giving
    it — called only when the inputs did change (it rereads every picture)."""
    keys = calls.get("keys") or []
    if key in keys:
        return ("cùng đầu vào (vân tay không đổi) mà chưa có bản dùng được — các lượt trước bị code từ chối hoặc Claude lỗi, "
                "xem chat_prompt_refused / chat_prompt_fail của job này")
    before = calls.get("parts") or {}
    if not before:
        return "đầu vào khác lần gọi trước (bản ghi cũ không lưu phần nào đổi)"
    parts = parts() if callable(parts) else parts
    changed = [name for k, name in PART_NAMES if before.get(k) != parts.get(k)]
    return "đầu vào đổi: " + (", ".join(changed) if changed else "không rõ phần nào")


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
            f"# Bắt buộc (code kiểm, sai là bản của bạn bị bỏ)\n- Giữ ĐÚNG CHỮ từng mã: {', '.join(required_codes(assembled)) or '(không có)'}"
            " — mọi số ảnh phải còn, đúng số: viết \"Image 3\", hoặc nhóm như bản ghép (\"Images 2/3\", \"Images 2 and 3\"); không bỏ số "
            "nào, không đổi số, không thay bằng \"the references\" / \"these images\".\n"
            f"- Tối đa {limit} ký tự (đếm cả khoảng trắng); quá là bị bỏ.\n"
            "- Không gọi tên vật / mốc bằng một bộ phận mà ảnh và bản code ghép không có (vd tên Kho \"Tháp Đồng Hồ\" nhưng tháp KHÔNG có "
            "mặt đồng hồ → \"the tower\", không viết \"clock tower\").\n\n"
            f"# Trả về\nĐúng một JSON: {{\"prompt\": \"<prompt tiếng Anh, ≤ {limit} ký tự>\", \"changes\": [\"<điều bạn đổi so với bản code "
            "ghép, tiếng Việt, ngắn>\"]}}")


def fix_text(first: str, answer: str, problems: Sequence[str], assembled: str, limit: int) -> str:
    """Việc 5 (14/10): the ONE fix turn after `check` refused the answer — the same brief + exactly what was wrong + the refused text,
    so Claude repairs that point instead of the paid answer being thrown away."""
    lost = sorted(_ref_units(assembled) - _ref_units(answer, any_case=True))
    how = []
    if lost:
        how.append(f"Bản của bạn thiếu {', '.join(lost)}: đặt lại đúng chữ đó vào câu nói về ảnh / đoạn đó (giữ nguyên số, như bản code "
                   "ghép), không thêm ảnh mới.")
    if len(answer) > limit:
        how.append(f"Bản của bạn dài {len(answer)} ký tự: rút còn ≤ {limit} (bỏ câu lặp, giữ mọi mã ảnh và dữ kiện).")
    if any("tiếng Việt" in p for p in problems):
        how.append("Bản của bạn còn chữ tiếng Việt: viết toàn bộ bằng tiếng Anh.")
    return (first + "\n\n# Lượt sửa (một lần duy nhất)\nCode đã từ chối bản bạn vừa viết vì: " + "; ".join(problems) + ".\n"
            + "\n".join(f"- {h}" for h in how) + "\nSửa ĐÚNG các điểm trên, giữ phần còn lại của bản bạn; trả về đúng một JSON như trên.\n\n"
            f"# Bản bạn vừa viết (bị từ chối)\n{answer}")


def _ref_units(text: str, any_case: bool = False) -> set:
    """The picture / shot / block codes of a text, one per picture: "Images 2/3" → {"Image 2", "Image 3"}. any_case: also "SHOT 1",
    "image 3" — for the rewrite's ANSWER; the assembled prompt's codes are only the exactly written ones."""
    out = set()
    for tok in (REF_TOKEN_ANY_CASE if any_case else REF_TOKEN).findall(text or ""):
        tok = _CODE_WORD.sub(lambda w: {"images": "Images", "image": "Image", "shot": "Shot"}[w.group(1).lower()], tok)
        m = _IMAGES_GROUP.fullmatch(tok)
        lst = None if m else _IMAGES_LIST.fullmatch(tok)
        if m:
            out.update(f"Image {n}" for n in m.group(1).split("/"))
        elif lst:
            body = lst.group(1)
            for a, b in _RANGE.findall(body):                       # "Images 2-4" → 2, 3, 4 (a short range only)
                if int(a) < int(b) <= int(a) + MAX_IMAGES:
                    out.update(f"Image {n}" for n in range(int(a), int(b) + 1))
            out.update(f"Image {n}" for n in re.findall(r"\d+", body))
        else:
            out.add(tok)
    return out


def required_codes(assembled: str) -> List[str]:
    """The codes the rewrite must keep word for word (told to Claude, checked after)."""
    def key(t):
        last = t.split()[-1]
        return (t.split()[0], int(last) if last.isdigit() else 0, t)
    return sorted(_ref_units(assembled), key=key)


def no_added_features(assembled: str, prompt: str) -> Tuple[str, List[str]]:
    """(prompt, the words replaced) — a landmark feature the assembled prompt never names ("clock tower") goes back to a neutral word."""
    fixed = []
    for rx, neutral in _ADDED_FEATURE:
        if not rx.search(assembled or "") and rx.search(prompt):
            fixed += [m.group(0) for m in rx.finditer(prompt)]
            prompt = rx.sub(neutral, prompt)
    return prompt, fixed


def check(assembled: str, prompt: str, limit: int) -> List[str]:
    """Why the new prompt cannot be sent ([] = it can). Only checks — nothing is added to the text."""
    problems = []
    if not prompt.strip():
        problems.append("prompt rỗng")
    if len(prompt) > limit:
        problems.append(f"dài {len(prompt)} > {limit} ký tự")
    lost = sorted(_ref_units(assembled) - _ref_units(prompt, any_case=True))
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


def _keep_refused(conn, job_id: int, turn: int, prompt: str, problems: Sequence[str]) -> None:
    """A paid answer that `check` refused is KEPT (app_settings chat_prompt_refused:<job>): 14/10 the 6 refused #30 answers were thrown
    away, so the root cause could only be read from the one that passed."""
    key = REFUSED_KEY.format(job_id)
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    try:
        kept = json.loads(row[0]) if row else []
    except ValueError:
        kept = []
    kept = (kept + [{"turn": turn, "problems": list(problems), "prompt": prompt}])[-4:]
    conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (key, json.dumps(kept, ensure_ascii=False)))
    conn.commit()


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


def _quota_paused(conn) -> bool:
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (QUOTA_KEY,)).fetchone()
    try:
        at = float(json.loads(row[0]).get("at")) if row else None
    except (ValueError, TypeError, AttributeError):
        return False
    return at is not None and time.time() - at < QUOTA_PAUSE_S


def saved_view(conn, job_id: int, kind: str) -> Dict:
    """C-M71 A5 (P31-G29): what tools/pregen_check --payload can say about the REAL D6 package of a job without calling Claude —
    {"state": "saved", "prompt", "note"} = the last D6 prompt written for this job (CALLS_KEY 'last', else the cache rows of the job),
    or {"state": "unseen", "note"} (never silent: the package actually sent will be Claude's rewrite at send time)."""
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (CALLS_KEY.format(job_id),)).fetchone()
    try:
        last = json.loads(row[0]).get("last") if row else None
    except (ValueError, AttributeError):
        last = None
    if not last:
        for (value,) in conn.execute("SELECT value FROM app_settings WHERE key LIKE 'chat_prompt:%' ORDER BY rowid DESC"):
            try:
                got = json.loads(value)
            except ValueError:
                continue
            if isinstance(got, dict) and got.get("job") == job_id and got.get("kind") == kind and got.get("prompt"):
                last = got["prompt"]
                break
    if last:
        return {"state": "saved", "prompt": last,
                "note": f"D6 bản đã lưu của job {job_id} (lượt Claude gần nhất) — đầu vào đổi thì lúc gửi Claude viết lại bản mới"}
    return {"state": "unseen", "note": "D6 bật: gói thật sẽ do Claude viết lại lúc gửi — chưa xem được (chưa có bản lưu); prompt in "
                                       "dưới đây là bản code ghép"}


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
        if hit and hit.get("refused") and hit.get("prompt_refused") and not check(assembled, hit["prompt_refused"], limit):
            return hit["prompt_refused"]                                # a later, corrected check accepts the kept answer (0 USD)
        if hit and hit.get("refused"):                                  # same inputs already refused after the fix turn: not paid again
            say("warn", "chat_prompt_refused", f"D6 job {job['id']}: đầu vào này đã bị từ chối sau lượt sửa (" + "; ".join(hit["refused"])
                + ") — gửi bản code ghép như cũ (không gọi lại)")
            return assembled
        if _quota_paused(conn):                                         # C-M71 A5: hết tiền / hết lượt gần đây — không gọi lại mỗi nhịp
            say("warn", QUOTA_CODE, QUOTA_MSG.format(m=QUOTA_PAUSE_S // 60))
            return assembled
        calls = conn.execute("SELECT value FROM app_settings WHERE key=?", (CALLS_KEY.format(job["id"]),)).fetchone()
        calls = json.loads(calls[0]) if calls else {"n": 0, "last": None}
        before_calls = json.dumps(calls, ensure_ascii=False)
        parts = lambda: input_parts(kind, model, assembled, pics, intent, notes, limit)   # noqa: E731 - only when needed (rereads pictures)
        if calls["n"] >= MAX_CALLS_PER_JOB:
            say("warn", "chat_prompt_cap", f"D6 job {job['id']}: đã gọi Claude {calls['n']} lần, {cap_reason(calls, key, parts)} — "
                + ("dùng bản D6 gần nhất" if calls.get("last") else "gửi bản code ghép như cũ") + " (không gọi thêm)")
            return calls.get("last") or assembled
        if client is None:
            from .prompt_rewrite import client_for
            client = client_for(p, job)          # V3.1 M1.4b: provider chụp lúc tạo job
        if client is None:
            say("warn", "chat_prompt_noclaude", "D6 (đường như chat): chưa có Claude — gửi bản code ghép như cũ")
            return assembled
        from . import llm_runner
        usd = estimate(conn, len(pics))
        calls["n"] += 1
        calls["keys"] = ((calls.get("keys") or []) + [key])[-MAX_CALLS_PER_JOB * 2:]   # which inputs were paid for (cap_reason)
        calls["parts"] = parts()
        conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                     (CALLS_KEY.format(job["id"]), json.dumps(calls, ensure_ascii=False)))
        conn.commit()
        first = build_text(kind, model, assembled, pics, intent, notes, limit)
        from .runner import no_minor_age

        def ask(text):
            with llm_runner.tagged(STAGE, job["project_id"]):
                got, _, _ = llm_runner.ask_json(client, text, _validate, pics)
            out, fixed = no_added_features(assembled, no_minor_age(got["prompt"]).strip())
            if fixed:
                say("info", "chat_prompt_feature_word", "D6: bỏ chữ tả bộ phận bản code ghép không có (" + ", ".join(dict.fromkeys(fixed))
                    + ") — vd 'clock tower' làm model vẽ mặt đồng hồ")
            return got, out

        try:
            obj, new = ask(first)
        except Exception as e:  # noqa: BLE001 - Claude down / over the cap / bad answer: the old way, said
            if getattr(e, "code", None) in QUOTA_CODES:               # C-M71 A5: account out — not this job's try; paused, one coded line
                conn.execute("UPDATE app_settings SET value=? WHERE key=?", (before_calls, CALLS_KEY.format(job["id"])))
                conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                             (QUOTA_KEY, json.dumps({"at": time.time(), "code": e.code, "msg": str(e)[:200]}, ensure_ascii=False)))
                conn.commit()
                say("warn", QUOTA_CODE, QUOTA_MSG.format(m=QUOTA_PAUSE_S // 60))
                return assembled
            say("warn", "chat_prompt_fail", f"D6 job {job['id']} (đường như chat) không viết được prompt ({str(e)[:200]}) — gửi bản code ghép như cũ")
            return assembled
        problems = check(assembled, new, limit)
        if problems:
            _keep_refused(conn, job["id"], 1, new, problems)
            if calls.get("fix", 0) >= MAX_FIX_TURNS:
                say("warn", "chat_prompt_refused", f"D6 job {job['id']}: bản Claude viết không gửi được (" + "; ".join(problems)
                    + ") — đã dùng lượt sửa của job này, gửi bản code ghép như cũ")
                _store(conn, key, {"prompt": None, "refused": problems, "prompt_refused": new, "job": job["id"], "kind": kind})
                return assembled
            usd_fix = estimate(conn, len(pics))                        # the fix turn: priced + recorded like the first one
            calls["fix"] = calls.get("fix", 0) + 1
            conn.execute("UPDATE app_settings SET value=? WHERE key=?", (json.dumps(calls, ensure_ascii=False), CALLS_KEY.format(job["id"])))
            conn.commit()
            say("info", "chat_prompt_fix_turn", f"D6 job {job['id']}: bản đầu bị từ chối (" + "; ".join(problems) + ") — hỏi Claude sửa "
                "đúng lỗi đó 1 lượt" + (f", ≈ {usd_fix:.3f} USD" if usd_fix is not None else ", chưa có giá"))
            try:
                obj, new = ask(fix_text(first, new, problems, assembled, limit))
            except Exception as e:  # noqa: BLE001 - the fix turn failed: the old way, said
                say("warn", "chat_prompt_refused", f"D6 job {job['id']}: bản Claude viết không gửi được (" + "; ".join(problems)
                    + f"), lượt sửa lỗi ({str(e)[:160]}) — gửi bản code ghép như cũ")
                return assembled
            again = check(assembled, new, limit)
            if again:
                _keep_refused(conn, job["id"], 2, new, again)
                _store(conn, key, {"prompt": None, "refused": again, "prompt_refused": new, "job": job["id"], "kind": kind})
                say("warn", "chat_prompt_refused", f"D6 job {job['id']}: bản Claude viết không gửi được cả sau 1 lượt sửa (" + "; ".join(again)
                    + ") — gửi bản code ghép như cũ")
                return assembled
            usd = None if usd is None or usd_fix is None else usd + usd_fix
            say("info", "chat_prompt_fixed", f"D6 job {job['id']}: lượt sửa đạt — gửi bản D6 (thay vì vứt bản đã trả tiền)")
        calls["last"] = new
        conn.execute("UPDATE app_settings SET value=? WHERE key=?", (json.dumps(calls, ensure_ascii=False), CALLS_KEY.format(job["id"])))
        _store(conn, key, {"prompt": new, "changes": obj.get("changes") or [], "job": job["id"], "kind": kind, "usd_est": usd,
                           "assembled_len": len(assembled)})
        say("info", "chat_prompt", f"D6 job {job['id']} (đường như chat): Claude nhìn {len(pics)} ảnh viết lại prompt {('ảnh' if kind == 'image' else 'video')} "
            f"({len(assembled)} → {len(new)} ký tự)" + (f", ≈ {usd:.3f} USD" if usd is not None else "")
            + ("; đổi: " + "; ".join((obj.get("changes") or [])[:3]) if obj.get("changes") else ""))
        return new
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
