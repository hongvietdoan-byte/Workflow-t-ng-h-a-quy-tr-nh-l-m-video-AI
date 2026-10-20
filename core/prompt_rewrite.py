"""S14.17 — Đạo diễn viết lại prompt shot trước mỗi lần gen lại (người dùng duyệt 04/10, docs/KE_HOACH_NANG_CAP_DASHBOARD_2026-10-03.md
mục 6c ý 6).

Trước: ghi chú từ chối của người (tiếng Việt) hoặc câu `fix` của QC được nối nguyên văn vào CUỐI prompt dạng "Fix: …" (core/runner.py
model_fix) — câu tả sai ở đầu prompt vẫn nằm nguyên, model hay làm theo nó. Nay (cờ `director_rewrite`): Đạo diễn (Claude, khâu
`director_rewrite`) đọc prompt cũ + ghi chú / lỗi QC + ảnh/khung lỗi → viết prompt tiếng Anh MỚI cho shot (sửa đúng chỗ gây lỗi, giữ phần
đúng); bản cũ được lưu (bảng prompt_versions), prompt của shot = bản mới, job mới không nối "Fix:" nữa (retry_reason = REWRITE_NOTE…).

Không im lặng (CHUAN_XAY_DUNG luật 1): Claude lỗi / chưa cấu hình / hết tiền / trả lời không dùng được → giữ hành vi cũ (nối "Fix: …") và ghi
diag cảnh báo FALLBACK_CODE. Gửi lại vì lỗi nhà cung cấp (không có câu sửa) không bao giờ gọi Đạo diễn. Lượt Claude đi qua sổ chi + ước tính
như mọi khâu Claude (client của llm_runner, stage STAGE → dòng ngân sách claude_director); lần gen lại do máy vẫn đếm vào AUTO_REGEN_LIMIT
(rewrite không thêm lượt đếm, và không chạy khi đã chạm giới hạn)."""
import difflib
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from . import diag, features
from .pipeline import REWRITE_NOTE

FLAG = "director_rewrite"
STAGE = "director_rewrite"
FALLBACK_CODE = "director_rewrite_fallback"
DONE_CODE = "director_rewrite"
PROMPT_FILE = "26_director_rewrite.md"
MAX_PROMPT_CHARS = 4000
KINDS = {"image_gen": "image", "video_gen": "video"}
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SHOT_KEYS = ("characters", "shot", "size", "angle", "camera_move", "action", "blocking", "start_frame", "location", "time", "mood",
              "lighting", "emotional_intent", "duration_s")


class RewriteRefused(Exception):
    """The Director's answer cannot be used (same prompt, a character outside the shot…): the old way (Fix:) is used instead."""


@dataclass
class RewriteResult:
    new_prompt: str
    changed: List[str] = field(default_factory=list)
    why: str = ""
    version: int = 0
    old_prompt: str = ""
    removed_words: List[str] = field(default_factory=list)


# C1 (rà soát R14 — người dùng 14/10 chọn BẬT): khi cờ change_review_motion bật, bản motion prompt Đạo diễn TỰ viết lại trước lần gen
# lại cũng qua Tổ rà soát — rà NGAY tại chỗ (không chờ vòng nền), xanh gửi luôn; ĐỎ → viết lại thêm MỘT lần (Plan.apply) rồi mới giữ.
REVIEW_AUTO_REWRITE = True


def enabled() -> bool:
    return features.on(FLAG)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def client_for(p):
    """The Claude client for the rewrite (ledger = this database, so the call is on the cost ledger and its warnings). None = not set up."""
    from . import llm_runner
    return llm_runner.client_from_env(ledger=llm_runner.db_file(p.conn))


# ---- the shot's prompt and its versions -----------------------------------------------------------------------------------------
def current_prompt(conn, scene_id: int, kind: str) -> Optional[str]:
    if kind == "image":
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()
        return (json.loads(row["data"] or "{}").get("image_prompt") if row else None) or None
    row = conn.execute("SELECT motion_prompt FROM motion_prompts WHERE scene_id=?", (scene_id,)).fetchone()
    return (row["motion_prompt"] if row else None) or None


def _last_change_event(conn) -> Optional[int]:
    """Mã lần ghi change_events lớn nhất hiện có (None = CSDL cũ chưa có bảng)."""
    try:
        return conn.execute("SELECT COALESCE(MAX(id), 0) FROM change_events").fetchone()[0]
    except Exception:  # noqa: BLE001 - old database without the table: nothing to skip
        return None


def _set_prompt(conn, scene_id: int, kind: str, text: str) -> None:
    if kind == "image":
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()
        data = json.loads(row["data"] or "{}")
        data["image_prompt"] = text
        conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), scene_id))
    else:
        conn.execute("UPDATE motion_prompts SET motion_prompt=? WHERE scene_id=?", (text, scene_id))


def versions(conn, scene_id: int, kind: str) -> List[Dict]:
    """Every saved version of the shot's prompt, oldest first ({version, prompt, source, note, changed: [..], why, job_id, created_at})."""
    try:
        rows = conn.execute("SELECT * FROM prompt_versions WHERE scene_id=? AND kind=? ORDER BY version", (scene_id, kind)).fetchall()
    except Exception:  # noqa: BLE001 - a database made before S14.17 (connect() adds the table): no versions
        return []
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["changed"] = json.loads(r["changed"] or "[]")
        except ValueError:
            d["changed"] = []
        out.append(d)
    return out


def live_versions(conn, scene_id: int, kind: str) -> List[Dict]:
    """The versions, only while the shot's prompt is still the last one saved (a prompt edited by hand afterwards — or a scene id reused
    after a re-split — makes the old comparison meaningless: nothing is shown and nothing can be reverted)."""
    vers = versions(conn, scene_id, kind)
    if not vers or vers[-1]["prompt"] != current_prompt(conn, scene_id, kind):
        return []
    return vers


def _add_version(conn, project_id: int, scene_id: int, kind: str, prompt: str, source: str, note: Optional[str] = None,
                 changed: Optional[List[str]] = None, why: Optional[str] = None, job_id: Optional[int] = None,
                 who: Optional[str] = None) -> int:
    row = conn.execute("SELECT MAX(version) FROM prompt_versions WHERE scene_id=? AND kind=?", (scene_id, kind)).fetchone()
    version = (row[0] or 0) + 1
    conn.execute("INSERT INTO prompt_versions (project_id, scene_id, kind, version, prompt, source, note, changed, why, job_id, created_at,"
                 " created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                 (project_id, scene_id, kind, version, prompt, source, note, json.dumps(changed or [], ensure_ascii=False), why, job_id,
                  _now(), who))
    return version


def revert(p, scene_id: int, kind: str) -> str:
    """"↩ Dùng lại prompt cũ": the shot's prompt goes back to the version before the Director's last rewrite (saved as a new version
    'revert'). No Claude call, no job — free; the person presses gen lại when they want a take with it. Returns the prompt now in use."""
    from . import access
    access.need_edit_scene(p, scene_id, "dùng lại prompt cũ")
    vers = live_versions(p.conn, scene_id, kind)
    if len(vers) < 2 or vers[-1]["source"] != "director_rewrite":
        raise ValueError("Không có bản prompt do Đạo diễn sửa để quay lại (hoặc prompt đã được sửa tay sau đó).")
    old = vers[-2]["prompt"]
    pid = p.conn.execute("SELECT project_id FROM scenes WHERE id=?", (scene_id,)).fetchone()["project_id"]
    _set_prompt(p.conn, scene_id, kind, old)
    _add_version(p.conn, pid, scene_id, kind, old, "revert", note=f"dùng lại prompt v{vers[-2]['version']}", who=p.actor)
    p.conn.commit()
    from . import prompt_formula                          # F1-A: the prompt back in use gets its own check (no growth: it is older)
    prompt_formula.on_prompt_saved(p.conn, scene_id, kind, None, old)
    return old


def word_diff(old: str, new: str) -> List[Tuple[str, str]]:
    """[(op, text)] with op 'same' | 'del' | 'ins', word by word (spaces kept), for the old/new comparison on the cards."""
    a, b = re.findall(r"\s+|[^\s]+", old or ""), re.findall(r"\s+|[^\s]+", new or "")
    out: List[Tuple[str, str]] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            out.append(("same", "".join(a[i1:i2])))
            continue
        if i2 > i1:
            out.append(("del", "".join(a[i1:i2])))
        if j2 > j1:
            out.append(("ins", "".join(b[j1:j2])))
    return out


# ---- the Director's call -----------------------------------------------------------------------------------------------------------
def _block(title: str, obj) -> str:
    return f"# {title}\n```json\n{json.dumps(obj, ensure_ascii=False, indent=1)}\n```"


def _prior_notes(p, job) -> List[str]:
    """Ghi chú người dùng của đúng chuỗi lần gen; không lấy shot/loại khác."""
    chain, seen = [], set()
    current = job
    while current is not None and current["id"] not in seen:
        if current["scene_id"] != job["scene_id"] or current["type"] != job["type"]:
            break
        seen.add(current["id"])
        chain.append(current["id"])
        current = p.job(current["parent_job_id"]) if current["parent_job_id"] else None
    notes = []
    for jid in reversed(chain):
        for row in p.conn.execute("SELECT note FROM review_log WHERE job_id=? AND reviewer_type='user' "
                                  "AND decision='reject' ORDER BY id", (jid,)):
            if row["note"] and row["note"].strip():
                notes.append(row["note"])
    return notes


def build_prompt(p, job, kind: str, old: str, note: Optional[str], fix: Optional[str], qc: Optional[Dict], seen: int,
                 by: str = "user") -> str:
    from . import looks
    conn = p.conn
    proj = p.project(job["project_id"])
    row = conn.execute("SELECT idx, data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
    data = json.loads(row["data"] or "{}")
    shot = {k: data[k] for k in _SHOT_KEYS if data.get(k) not in (None, "", [])}
    if data.get("dialogue"):
        shot["dialogue"] = [{"speaker": d.get("speaker"), "text": d.get("text")} for d in data["dialogue"] if isinstance(d, dict)]
    if kind == "video":
        mp = conn.execute("SELECT camera, duration_sec, negative_prompt FROM motion_prompts WHERE scene_id=?", (job["scene_id"],)).fetchone()
        if mp is not None:
            shot.update({k: mp[k] for k in ("camera", "duration_sec", "negative_prompt") if mp[k]})
    with open(os.path.join(_ROOT, "prompts", PROMPT_FILE), encoding="utf-8") as f:
        system = f.read()
    who = {"qc": "Tổ QC (máy) từ chối",
           "change_review": "Tổ rà soát tác động chấm ĐỎ bản bạn vừa viết lại — sửa đúng điều được nêu, giữ phần còn lại"}.get(
        by, "Người dùng yêu cầu gen lại")
    look = looks.of(proj)
    parts = [system,
             f"# Việc lần này\nShot {row['idx']} — prompt {'ẢNH (image_prompt)' if kind == 'image' else 'VIDEO (motion_prompt)'}; {who}."
             + (f" Look dự án: {look}" + (" — KHÔNG dùng chữ tả thực." if look == "FF_INGAME" else ".") if look else ""),
             "# Prompt cũ của shot\n```text\n" + old + "\n```",
             _block("Bối cảnh shot (kịch bản — không thêm gì ngoài đây)", shot)]
    history = _prior_notes(p, job)
    if history:
        parts.append(_block("Ghi chú các lần từ chối trước (giữ ý còn đúng; ghi chú mới ưu tiên nếu mâu thuẫn)", history))
    if note:
        parts.append("# Ghi chú\n" + note)
    if fix and fix != note:
        parts.append("# Câu sửa (fix)\n" + fix)
    if qc:
        parts.append(_block("Lỗi QC (root_cause, problem, fix)", {k: qc.get(k) for k in ("root_cause", "problem", "fix") if qc.get(k)}))
    parts.append("# Ảnh/khung lỗi\n" + (f"Đính kèm {seen} ảnh của bản vừa gen (bản bị từ chối)." if seen else
                                         "Không có ảnh/khung của bản lỗi — dựa vào ghi chú / lỗi QC."))
    return "\n\n---\n\n".join(parts)


def _images(job, kind: str) -> Tuple[List[Tuple[str, str]], Optional[str]]:
    """(pictures of the faulty take for Claude, the temporary folder to delete afterwards or None)."""
    path = job["result_path"]
    if not path or not os.path.exists(path):
        return [], None
    if kind == "image":
        return [("Ảnh lỗi (bản vừa gen, bị từ chối):", path)], None
    tmp = tempfile.mkdtemp(prefix="rewrite_")
    try:
        from .video_analysis import extract_frames
        frames = extract_frames(path, tmp, count=3)
    except Exception:  # noqa: BLE001 - no ffmpeg / unreadable clip: the Director works from the notes (said in the prompt)
        shutil.rmtree(tmp, ignore_errors=True)
        return [], None
    return [(f"Khung {i} của clip lỗi:", fr) for i, fr in enumerate(frames, 1)], tmp


def _validate(obj) -> Dict:
    from .llm_io import SchemaError
    if not isinstance(obj, dict) or not isinstance(obj.get("new_prompt"), str) or not obj["new_prompt"].strip():
        raise SchemaError("root: {new_prompt: chuỗi, changed: [chuỗi], why: chuỗi}")
    if len(obj["new_prompt"]) > MAX_PROMPT_CHARS:
        raise SchemaError(f"new_prompt dài quá {MAX_PROMPT_CHARS} ký tự")
    changed = obj.get("changed")
    if changed is not None and (not isinstance(changed, list) or not all(isinstance(c, str) for c in changed)):
        raise SchemaError("changed: danh sách chuỗi")
    return obj


def _same(a: str, b: str) -> bool:
    return " ".join((a or "").split()).lower() == " ".join((b or "").split()).lower()


def _new_people(conn, job, old: str, new: str) -> List[str]:
    data = json.loads(conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")
    cast = {str(c).lower() for c in data.get("characters") or []}
    out = []
    for r in conn.execute("SELECT name FROM characters WHERE project_id=?", (job["project_id"],)):
        name = r["name"]
        pat = re.compile(rf"(?<!\w){re.escape(name)}(?!\w)", re.I)
        if pat.search(new) and not pat.search(old) and name.lower() not in cast:
            out.append(name)
    return out


def _variant_mentions(asset, variant, variants, text):
    """Guard riêng: định danh đầy đủ thắng alias skin chung, không đổi selector ảnh."""
    from . import assets, prop_lock
    said = assets.fold(text or "").split()
    tokens = prop_lock._variant_tokens(variant)
    if tokens and any(said[i:i + len(tokens)] == tokens for i in range(len(said) - len(tokens) + 1)):
        return True
    # Khi có định danh của skin khác, tên chung không cho phép skin này.
    others = [prop_lock._variant_tokens(v) for v in variants if v != variant]
    if any(t and any(said[i:i + len(t)] == t for i in range(len(said) - len(t) + 1)) for t in others):
        return False
    hits = [v for v in variants if prop_lock._says_variant(asset, v, said)]
    return hits == [variant]


_REST_OF_CLAUSE = re.compile(r"\b(?:not|no|never|without|remove|avoid|instead of|previous|previously|incorrectly)\b|"
                             r"(?<!\w)(?:không|đừng|loại bỏ|bỏ|lần trước|trước đó|thay vì)(?!\w)", re.I)
_NEAR_WORDS = re.compile(r"\b(?:wrong|old)\b|(?<!\w)(?:sai|cũ)(?!\w)", re.I)


def _variant_instruction(text):
    """Chỉ dẫn phủ định/nhắc lần lỗi cũ không cấp phép thêm skin. Rà 12/10: chỉ bỏ phần bị phủ định, không bỏ cả câu — "Đổi sang skin
    Hỏa Ngục, không dùng bản mặc định" vẫn cho phép Hỏa Ngục: tách ở , / but / nhưng; từ phủ định bỏ phần còn lại của mệnh đề; "sai /
    cũ / wrong / old" chỉ bỏ 2 từ mỗi bên."""
    keep = []
    for part in re.split(r"[.;!?\n,]+|\b(?:but|however)\b|(?<!\w)(?:nhưng|mà)(?!\w)", text or "", flags=re.I):
        m = _REST_OF_CLAUSE.search(part)
        if m:
            part = part[:m.start()]
        words = part.split()
        drop = set()
        for i, w in enumerate(words):
            if _NEAR_WORDS.fullmatch(re.sub(r"[^\w]", "", w)):
                drop.update(range(max(0, i - 2), i + 3))
        part = " ".join(w for i, w in enumerate(words) if i not in drop)
        if part.strip():
            keep.append(part.strip())
    return " ; ".join(keep)


def propose_rewrite(p, job, note: Optional[str] = None, fix: Optional[str] = None, qc: Optional[Dict] = None,
                    client=None, by: str = "user") -> RewriteResult:
    """The Director's new prompt for the shot's next take — Claude call + code checks, NOTHING written (the job is still alive while
    Claude thinks, so the automatic run never sees the shot without a live take — review S14.17 #1). Raises LlmError (Claude),
    RewriteRefused (answer not usable) or ValueError (nothing to rewrite) — the caller then keeps the old way."""
    from . import llm_runner, looks
    from .runner import no_minor_age
    kind = KINDS.get(job["type"])
    if kind is None:
        raise ValueError(f"loại việc {job['type']} không có prompt shot để viết lại")
    old = current_prompt(p.conn, job["scene_id"], kind)
    if not old:
        raise ValueError("shot chưa có prompt " + ("ảnh" if kind == "image" else "motion") + " để viết lại")
    client = client if client is not None else client_for(p)
    if client is None:
        raise llm_runner.LlmError("Chưa cấu hình Claude: " + llm_runner.missing_hint(), code="config")
    images, tmp = _images(job, kind)
    try:
        text = build_prompt(p, job, kind, old, note, fix, qc, len(images), by)
        with llm_runner.tagged(STAGE, job["project_id"]):
            obj, _, _ = llm_runner.ask_json(client, text, _validate, images)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    new = no_minor_age(obj["new_prompt"]).strip()
    new, removed = looks.clean_prompt(p.project(job["project_id"]), new)
    new = new.strip()
    if not new or _same(new, old):
        raise RewriteRefused("Đạo diễn trả lại y prompt cũ — gen lại như vậy là gửi lại cùng đầu vào")
    extra = _new_people(p.conn, job, old, new)
    if extra:
        raise RewriteRefused("prompt mới thêm nhân vật không có trong shot: " + ", ".join(extra))
    from . import prop_lock, assets
    if prop_lock.enabled():
        added = []
        row = p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()   # rà 12/10: the shot's own words
        shot_data = json.loads(row["data"] or "{}") if row else {}
        shot_words = prop_lock.shot_text(shot_data)                                                  # (action / blocking) count too
        for a in assets.project_assets(p.conn, job["project_id"]):
            if a.get("kind") not in prop_lock.KINDS:
                continue
            variants = list(dict.fromkeys(prop_lock._variants(a) +
                [r["variant"] for r in p.conn.execute("SELECT variant FROM asset_images WHERE asset_id=? AND variant IS NOT NULL AND trim(variant)!=''", (a["id"],))] +
                [f.split("—", 1)[0].split("–", 1)[0].strip() for f in prop_lock._forms(a.get("description") or "")
                 if f.lower().startswith("skin ")]))
            allowed = (old, shot_words, _variant_instruction(note), _variant_instruction(fix))
            # 14/10 #30: the form the scene script gives this prop (prop_lock.variant_source — only sentences naming it, no spoken
            # lines, exactly one form) is allowed too — a SEPARATE source, never the scene text glued to the shot's words (rà: a scene
            # naming another skin in full would block this one by _variant_mentions' "full name of another skin" rule)
            # (the forms known here: the Kho rows + description forms, as the guard sees them — a missing picture file still names one)
            from_scene = prop_lock.variant_source(p.conn, job["project_id"], shot_data,
                                                  dict(a, images=[{"variant": v} for v in variants]), shot_words)
            from_scene = from_scene[0] if from_scene[1] == "scene" else None
            added.extend(v for v in variants if _variant_mentions(a, v, variants, new) and v != from_scene
                         and not any(_variant_mentions(a, v, variants, source) for source in allowed))
        if added:
            raise RewriteRefused("prompt mới tự thêm biến thể đạo cụ ngoài prompt cũ + ghi chú: " + ", ".join(added))
    changed = [c.strip() for c in obj.get("changed") or [] if c.strip()][:8]
    if removed:
        changed.append("Code gỡ chữ kéo về tả thực (look in-game): " + ", ".join(removed))
    return RewriteResult(new, changed, str(obj.get("why") or ""), 0, old, removed)


def save_rewrite(p, job, res: RewriteResult, note: Optional[str] = None) -> int:
    """Write the proposed prompt into the shot (old one kept as a version). Returns the new version number."""
    kind = KINDS[job["type"]]
    vers = versions(p.conn, job["scene_id"], kind)
    if not vers or vers[-1]["prompt"] != res.old_prompt:   # the prompt in use now (the Director's / a hand edit) is saved before it changes
        _add_version(p.conn, job["project_id"], job["scene_id"], kind, res.old_prompt, "original" if not vers else "manual", who=p.actor)
    res.version = _add_version(p.conn, job["project_id"], job["scene_id"], kind, res.new_prompt, "director_rewrite",
                               note=(note or "")[:600], changed=res.changed, why=res.why[:600], job_id=job["id"], who=p.actor)
    last_ev = _last_change_event(p.conn)
    _set_prompt(p.conn, job["scene_id"], kind, res.new_prompt)
    if kind == "video" and last_ev is not None:
        from . import change_review
        if not (REVIEW_AUTO_REWRITE and change_review.motion_enabled()):
            # cờ change_review_motion tắt (hoặc tắt rà bản tự viết): như trước C1 — bản viết lại tự động không qua Tổ rà soát motion
            p.conn.execute("UPDATE change_events SET state='skipped', reviewed_at=?, note=? WHERE id>? AND kind='motion' AND "
                           "scene_id=? AND state='pending'", (_now(), "Đạo diễn viết lại motion prompt tự động trước khi gen lại — "
                                                              "không rà (cờ change_review_motion tắt)", last_ev, job["scene_id"]))
        else:
            p.conn.commit()
            _review_now(p, job)
    p.conn.commit()
    from . import prompt_formula                          # F1-A (F0 mục 4b): the Director's rewrite is checked + compared to the old one
    prompt_formula.on_prompt_saved(p.conn, job["scene_id"], kind, res.old_prompt, res.new_prompt)
    try:                                                  # rà 12/10: the new prompt is saved — a failing note never turns it into a fallback
        _done(p, job, res)
    except Exception as e:  # noqa: BLE001 - said on stderr
        import sys
        print(f"prompt_rewrite: không ghi được dòng DONE ({type(e).__name__}: {e})", file=sys.stderr)
    return res.version


def _review_now(p, job) -> None:
    """C1: rà ngay bản motion vừa viết lại (change_review.review_scene_now) — một lời gọi Claude qua sổ chi, nhãn change_review.
    Không có Claude → chỉ luật code (thay đổi 'code_only', không giữ gen) + VÀNG; không bao giờ làm hỏng lần gen lại."""
    from . import change_review, world_rules
    try:
        client = client_for(p)
    except Exception:  # noqa: BLE001 - no Claude set up: the code rules still run, said below
        client = None
    try:
        change_review.review_scene_now(p.conn, world_rules.data_dir_abs(), job["scene_id"], client=client)
    except Exception as e:  # noqa: BLE001 - said; the background round reviews what is still pending
        diag.record(p.conn, "video", "warn", f"Rà soát bản motion Đạo diễn vừa viết lại lỗi ({type(e).__name__}: {str(e)[:160]}) — "
                    "vòng nền rà lại", "rewrite_review_fail", job["project_id"], scene_id=job["scene_id"], job_id=job["id"])
        return
    if client is None:
        diag.record(p.conn, "video", "warn", "Chưa rà bằng Claude bản motion Đạo diễn vừa viết lại (không gọi được Claude) — luật code "
                    "đã chạy, lần gen lại không bị giữ; vòng nền rà khi có Claude", "rewrite_review_noclaude", job["project_id"],
                    scene_id=job["scene_id"], job_id=job["id"])


def _red_after_review(p, job) -> Optional[str]:
    """Lý do ĐỎ của Tổ rà soát cho shot ngay sau lần rà tại chỗ (None = gửi được)."""
    from . import change_review
    if not (REVIEW_AUTO_REWRITE and change_review.motion_enabled()):
        return None
    try:
        rows = p.conn.execute("SELECT khau, msg FROM change_findings WHERE scene_id=? AND status='open' AND level='do' AND khau IN "
                              "('motion', 'khung_cuoi', 'video') ORDER BY id", (job["scene_id"],)).fetchall()
    except Exception:  # noqa: BLE001 - the runner checks again before sending (blocking)
        return None
    # chỉ ĐỎ của khâu mà motion prompt sửa được (motion / khung cuối / video) mới đáng một lần viết lại nữa — ĐỎ khâu ảnh / nền thì
    # viết lại motion vô ích: runner giữ kèm lý do như thường
    return "; ".join(f"{r[0]}: {r[1]}" for r in rows[:3]) or None


def _done(p, job, res: RewriteResult) -> None:
    """Every saved rewrite (including script callers) closes the old fallback on the same image/video stage."""
    kind = KINDS[job["type"]]
    unit = "ảnh" if kind == "image" else "clip"
    idx = p.conn.execute("SELECT idx FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
    diag.record(p.conn, kind, "info", f"Đạo diễn đã viết lại prompt {unit} shot {idx['idx'] if idx else '?'} (v{res.version}): "
                + "; ".join(res.changed)[:250], DONE_CODE, job["project_id"], scene_id=job["scene_id"], job_id=job["id"])
    p.last_rewrite_fallback = None


def rewrite_for_retry(p, job, note: Optional[str] = None, fix: Optional[str] = None, qc: Optional[Dict] = None,
                      client=None, by: str = "user") -> RewriteResult:
    """propose_rewrite + save_rewrite in one go (tools / tests)."""
    res = propose_rewrite(p, job, note=note, fix=fix, qc=qc, client=client, by=by)
    save_rewrite(p, job, res, note or fix)
    return res


class Plan:
    """What before_retry decided: `reason` = the retry_reason if nothing is rewritten; apply() — called AFTER the old take was rejected,
    right before the new job is inserted — writes the new prompt and returns the retry_reason to store."""

    def __init__(self, p, job, reason: Optional[str], res: Optional[RewriteResult] = None, note: Optional[str] = None):
        self.p, self.job, self.reason, self.res, self.note = p, job, reason, res, note

    def apply(self) -> Optional[str]:
        if self.res is None:
            return self.reason
        p, job = self.p, self.job
        kind = KINDS[job["type"]]
        try:
            if current_prompt(p.conn, job["scene_id"], kind) != self.res.old_prompt:
                raise RewriteRefused("prompt của shot vừa được sửa tay trong lúc Đạo diễn viết — giữ bản của người")
            version = save_rewrite(p, job, self.res, self.note)
        except Exception as e:  # noqa: BLE001 - never lose the take: the old way, said
            _fallback(p, job, e)
            return self.reason
        if kind == "video":
            version = self._second_try(version)
        return f"{REWRITE_NOTE} (v{version}): {(self.note or '')[:300]}"

    def _second_try(self, version: int) -> int:
        """C1: Tổ rà soát chấm ĐỎ bản viết lại → Đạo diễn viết lại thêm MỘT lần, lời ĐỎ làm điều phải sửa (đổi đầu vào — luật gen lại).
        Vẫn ĐỎ → giữ: runner báo lý do, người quyết ở 📥 Việc cần bạn."""
        p, job = self.p, self.job
        red = _red_after_review(p, job)
        if not red:
            return version
        try:
            again = propose_rewrite(p, job, note=self.note, fix=red, by="change_review")
            if current_prompt(p.conn, job["scene_id"], "video") != again.old_prompt:
                raise RewriteRefused("prompt của shot vừa đổi trong lúc Đạo diễn viết lại lần hai")
            return save_rewrite(p, job, again, f"Tổ rà soát: {red}")
        except Exception as e:  # noqa: BLE001 - the first rewrite stays; the hold + its reason are shown by the runner
            diag.record(p.conn, "video", "warn", f"Đạo diễn chưa viết lại lần hai theo Tổ rà soát ({type(e).__name__}: {str(e)[:160]})"
                        " — lần gen lại chờ bạn ở 📥 Việc cần bạn", "rewrite_review_red", job["project_id"],
                        scene_id=job["scene_id"], job_id=job["id"])
            return version


def _fallback(p, job, e: BaseException) -> None:
    kind = KINDS[job["type"]]
    unit = "ảnh" if kind == "image" else "clip"
    idx = p.conn.execute("SELECT idx FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
    msg = (f"Đạo diễn chưa viết lại prompt {unit} shot {idx['idx'] if idx else '?'} ({type(e).__name__}: {str(e)[:160]}) — lần gen "
           "lại dùng cách cũ: nối 'Fix: …' vào cuối prompt (ghi chú của bạn giữ nguyên)")
    diag.record(p.conn, kind, "warn", msg, FALLBACK_CODE, job["project_id"], scene_id=job["scene_id"], job_id=job["id"])
    # rà gộp Đ16v1 (12/10, #27): a script calling Pipeline.reject outside the Dashboard (no ANTHROPIC_API_KEY / dashboard.env in its
    # process) never saw the fallback — said on stderr too and kept on the Pipeline for the caller (never silent)
    p.last_rewrite_fallback = diag.redact(msg)
    print("⚠ " + p.last_rewrite_fallback, file=sys.stderr)


def before_retry(p, job, reason: Optional[str], note: Optional[str] = None, qc: Optional[Dict] = None,
                 by: str = "user") -> Plan:
    """Hook of core.pipeline (reject / reopen_approved) and core.regen, called while the old take is STILL ALIVE: `reason` is what the
    next job would carry (the "Fix:" text). Returns a Plan; Plan.apply() gives REWRITE_NOTE… when the Director rewrote the prompt, else
    `reason` unchanged (flag off, nothing to fix — e.g. a resend after a provider failure —, or the rewrite failed: then said in diag)."""
    from .runner import model_fix
    if job is None or job["type"] not in KINDS or not enabled():
        return Plan(p, job, reason)
    fix = model_fix(reason)
    if fix is None:                                       # plain resend / no fix: the input does not change, nothing to rewrite
        return Plan(p, job, reason)
    try:
        res = propose_rewrite(p, job, note=note if note and note != fix else None, fix=fix, qc=qc, by=by)
    except Exception as e:  # noqa: BLE001 - every failure keeps the old way, said (never silent)
        _fallback(p, job, e)
        return Plan(p, job, reason)
    return Plan(p, job, reason, res, note or fix)
