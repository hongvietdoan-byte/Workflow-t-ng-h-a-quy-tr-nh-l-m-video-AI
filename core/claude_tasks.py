"""v2 Claude tasks that turn the skill kit into checks inside the pipeline (each one: prompt + knowledge + validator + where the answer
goes). Same `ask_json` path as the Director/QC/motion steps, so they run with the API key, Claude Code on this PC or the mock.

- review_dialogue      narration-writer "dialogue craft" + clip length → suggested line fixes (the person applies them)
- lint_motion          Seedance Final QC + the ClipAI slide's 4 ambiguity checks → issues + revised prompt per scene
- qc_video             Character Lock + physics check on frames of a clip → scores → same QC decision path as pictures
- set_consistency      game-asset-set "three-layer QA" on one contact sheet of the approved pictures → outliers to redo
- character_lock       Character Lock drafted from a character's reference pictures
- cast_voices          a voice (and a persona line) for each speaking character
- music_brief          music brief from genre, intent and scene timing (prompts/04, previously unused)
"""
import json
import os
from typing import Dict, List, Optional, Tuple

from . import assets, dialogue, diag, layout, llm_io, model_router, prompts, voice
from .llm_runner import LlmError, ask_json, tagged
from .pipeline import Pipeline
from .states import JobState

_ROOT = os.path.join(os.path.dirname(__file__), "..")


def _read(*parts: str) -> str:
    with open(os.path.join(_ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _note(p: Pipeline, stage: str, project_id: int):
    return lambda message: diag.record(p.conn, stage, "warn", message, "bad_json_retry", project_id)


def _block(title: str, obj) -> str:
    return f"# {title}\n```json\n{json.dumps(obj, ensure_ascii=False, indent=1)}\n```"


def _run(p: Pipeline, project_id: int, stage: str, prompt: str, validate, client, images=()):
    if client is None:
        raise LlmError("Chưa cấu hình Claude (ANTHROPIC_API_KEY hoặc LLM_PROVIDER=claude_cli).", code="config")
    try:
        with tagged(stage, project_id):
            return ask_json(client, prompt, validate, images, note=_note(p, stage, project_id))[0]
    except LlmError as e:
        diag.record(p.conn, stage, "warn" if e.transient else "error", str(e), e.code, project_id)
        raise


# ---- 1. dialogue review ---------------------------------------------------------------------------------------------------
def _check_dialogue_review(obj) -> None:
    if not isinstance(obj, dict) or not isinstance(obj.get("lines"), list):
        raise llm_io.SchemaError("root: {summary, lines: [...], split: [...]}")
    for i, ln in enumerate(obj["lines"]):
        if not isinstance(ln, dict) or not isinstance(ln.get("idx"), int) or not isinstance(ln.get("line"), int) \
                or not isinstance(ln.get("suggestion"), str):
            raise llm_io.SchemaError(f"lines[{i}]: {{idx, line, speaker, problem, suggestion}}")


def review_dialogue(p: Pipeline, project_id: int, client) -> Dict:
    conn = p.conn
    proj = p.project(project_id)
    personas = {r["name"]: voice.get_profile(r).get("persona", "") for r in
                conn.execute("SELECT name, voice_profile FROM characters WHERE project_id=?", (project_id,))}
    scenes = []
    for s in conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall():
        rows = dialogue.scene_lines(json.loads(s["data"] or "{}"))
        if rows:
            scenes.append({"idx": s["idx"], "max_sec": dialogue.max_clip_seconds(p, project_id, s["id"]),
                           "lines": [{"line": n, "speaker": w, "text": t} for n, (w, t) in enumerate(rows, 1)]})
    if not scenes:
        return {"summary": "Kịch bản chưa có thoại.", "lines": [], "split": []}
    prompt = "\n\n---\n\n".join([_read("prompts", "10_dialogue_review.md"), _read("knowledge", "dialogue_craft.md"),
                                 f"# Thể loại: {proj['genre'] or 'chưa rõ'}", _block("Nhân vật (persona)", personas),
                                 _block("Thoại theo cảnh", scenes)])
    return _run(p, project_id, "director", prompt, _check_dialogue_review, client)


def apply_dialogue_fix(p: Pipeline, project_id: int, idx: int, line: int, text: str) -> None:
    """Replace one line (the person accepted the suggestion). The scene's dialogue becomes a structured list set by hand."""
    row = p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=?", (project_id, idx)).fetchone()
    rows = [{"speaker": w, "text": t} for w, t in dialogue.scene_lines(json.loads(row["data"] or "{}"))]
    if not 1 <= line <= len(rows):
        raise ValueError(f"cảnh {idx} không có câu thoại số {line}")
    rows[line - 1]["text"] = text.strip()
    llm_io.update_scene(p, project_id, idx, {"dialogue": rows})


# ---- 2. motion prompt lint --------------------------------------------------------------------------------------------------
def _check_lint(obj) -> None:
    if not isinstance(obj, dict) or not isinstance(obj.get("scenes"), list):
        raise llm_io.SchemaError("root: {scenes: [...]}")
    for i, s in enumerate(obj["scenes"]):
        if not isinstance(s, dict) or not isinstance(s.get("idx"), int) or not isinstance(s.get("ok"), bool) \
                or not isinstance(s.get("issues", []), list):
            raise llm_io.SchemaError(f"scenes[{i}]: {{idx, ok, issues, revised_prompt}}")


def lint_motion(p: Pipeline, project_id: int, client, scene_ids: Optional[List[int]] = None) -> Dict:
    """Check the motion prompts (all, or the given scenes); the result is kept on each prompt (`motion_prompts.lint`)."""
    conn = p.conn
    rows = conn.execute("SELECT s.id sid, s.idx, s.data, m.motion_prompt, m.duration_sec FROM motion_prompts m JOIN scenes s"
                        " ON s.id=m.scene_id WHERE s.project_id=? ORDER BY s.idx", (project_id,)).fetchall()
    rows = [r for r in rows if scene_ids is None or r["sid"] in scene_ids]
    if not rows:
        return {"scenes": []}
    items = []
    for r in rows:
        data = json.loads(r["data"] or "{}")
        items.append({"idx": r["idx"], "video_model": model_router.scene_choice(conn, r["sid"])["model"],
                      "camera_complexity": data.get("camera_complexity"), "blocking": data.get("blocking"),
                      "dialogue": data.get("dialogue"), "duration_sec": r["duration_sec"], "motion_prompt": r["motion_prompt"]})
    prompt = "\n\n---\n\n".join([_read("prompts", "11_motion_lint.md"), _read("knowledge", "motion_prompt_lint.md"),
                                 _block("Motion prompt cần rà", items)])
    obj = _run(p, project_id, "motion", prompt, _check_lint, client)
    by_idx = {r["idx"]: r["sid"] for r in rows}
    for s in obj["scenes"]:
        sid = by_idx.get(s["idx"])
        if sid:
            conn.execute("UPDATE motion_prompts SET lint=? WHERE scene_id=?", (json.dumps(s, ensure_ascii=False), sid))
    conn.commit()
    return obj


def apply_lint(p: Pipeline, project_id: int, scene_id: int) -> bool:
    """Use the revised prompt proposed by the check (the prompt then waits for approval again)."""
    row = p.conn.execute("SELECT s.idx, m.* FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id WHERE m.scene_id=?",
                         (scene_id,)).fetchone()
    lint = json.loads(row["lint"] or "{}") if row else {}
    new = (lint.get("revised_prompt") or "").strip()
    if not new:
        return False
    llm_io.store_motion_prompts(p, project_id, {"scenes": [{"idx": row["idx"], "motion_prompt": new, "camera": row["camera"],
                                                            "duration_sec": row["duration_sec"],
                                                            "negative_prompt": row["negative_prompt"]}]})
    return True


# ---- 3. video QC ------------------------------------------------------------------------------------------------------------
def video_criteria() -> List[str]:
    data = json.loads(_read("data", "qc_checklist.json"))
    return [c["key"] for c in data.get("video_criteria") or []]


def qc_video(p: Pipeline, job_id: int, client, data_dir: str, autofix: Optional[bool] = None) -> Dict:
    """Score one finished clip from evenly spaced frames next to its approved first frame and the character references; the score
    goes through the same decision path as pictures (threshold, hard criteria, automatic redo, escalation)."""
    from . import performance, video_analysis     # GĐ4: QC checks the acting the Director asked for (at the drawn strength)
    job = p.job(job_id)
    path = job["result_path"]
    if not path or not os.path.exists(path):
        raise LlmError("clip này chưa có file để kiểm tra", code="no_video")
    frames_dir = os.path.join(data_dir, str(job["project_id"]), "qc_frames", f"job_{job_id}")
    frames = video_analysis.extract_frames(path, frames_dir, 6)
    scene = p.conn.execute("SELECT idx, data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
    data = json.loads(scene["data"] or "{}")
    mp = p.conn.execute("SELECT motion_prompt FROM motion_prompts WHERE scene_id=?", (job["scene_id"],)).fetchone()
    first = job["source_job_id"] and os.path.join(data_dir, str(job["project_id"]), "images", f"job_{job['source_job_id']}.png")
    refs = assets.scene_references(p.conn, job["project_id"], data)[:4]
    # M12 (trial 2A): the frames carried no time, so QC invented "at 5–6 s" for a 3,1 s clip — label each frame with its real second
    try:
        dur = float(video_analysis.probe(path)["duration_sec"] or 0.0)
    except Exception:  # noqa: BLE001 - no time known: the labels say only the frame number (never a guessed second)
        dur = 0.0
    margin, k = min(0.5, dur / (len(frames) + 1)), max(len(frames) - 1, 1)
    images = [(f"Khung {n}/{len(frames)} của clip" + (f" (≈ {margin + (dur - 2 * margin) * (n - 1) / k:.1f}s / tổng {dur:.1f}s)" if dur else "")
               + ":", f) for n, f in enumerate(frames, 1)]
    if first and os.path.exists(first):
        images.append(("Ảnh khung đầu đã duyệt:", first))
    images += [(f"Ảnh tham chiếu — {r['label']}:", assets.thumbnail(r["path"], 700)) for r in refs]
    criteria = video_criteria()
    prompt = _read("prompts", "12_video_qc.md") + "\n\n---\n\n" + _read("knowledge", "character_lock.md") + prompts.CACHE_BREAK \
        + "\n\n---\n\n".join(x for x in [
        prompts.lock_text(p.conn, job["project_id"], data.get("characters")),
        "# Motion prompt của clip\n" + (mp["motion_prompt"] if mp else ""),
        _block("Thông số cảnh", dict({k: data.get(k) for k in ("characters", "blocking", "shot", "camera_complexity")},
                                     **({"performance": performance.for_prompt(data)} if data.get("performance") else {})))] if x)
    obj = _run(p, job["project_id"], "video", prompt, lambda o: llm_io.validate_qc_result(o, criteria), client, images)
    proj = p.project(job["project_id"])
    fix = bool(proj["qc_autofix"]) if autofix is None else autofix
    issues = str(obj.get("issues") or "").strip() or None
    decision = p.apply_qc(job_id, obj["criteria"], issues=issues, autofix=fix)
    return {"decision": decision, "issues": issues}


def unchecked_videos(p: Pipeline, project_id: int) -> List[int]:
    """Finished clips that have not been scored yet (video QC switched on for the project)."""
    if not p.project(project_id)["qc_video"]:
        return []
    return [r["id"] for r in p.conn.execute(
        "SELECT j.id FROM jobs j WHERE j.project_id=? AND j.type='video_gen' AND j.state='succeeded'"
        " AND NOT EXISTS (SELECT 1 FROM qc_results q WHERE q.job_id=j.id) ORDER BY j.id", (project_id,))]


def qc_video_batch(p: Pipeline, project_id: int, client, data_dir: str) -> Dict:
    out = {"checked": 0, "failed": [], "decisions": {}}
    for jid in unchecked_videos(p, project_id):
        try:
            r = qc_video(p, jid, client, data_dir)
        except (LlmError, Exception) as e:  # noqa: BLE001 - one clip that cannot be read must not stop the others
            out["failed"].append((jid, str(e)))
            if isinstance(e, LlmError) and e.code in ("auth", "config", "budget"):
                break
            if not (isinstance(e, LlmError) and e.code in ("bad_json", "no_video", "bad_image", "truncated", "refusal", "empty",
                                                            "too_many_images")):
                continue                       # a missing tool / network problem is not this clip's fault: reported by the caller
            diag.record(p.conn, "video", "warn", f"QC clip #{jid} lỗi: {str(e)[:200]}", "video_qc_error", project_id, job_id=jid)
            tries = p.conn.execute("SELECT COALESCE(SUM(count), 0) FROM diag_events WHERE job_id=? AND code='video_qc_error'",
                                   (jid,)).fetchone()[0]
            if tries >= 2:                 # M13: not every tick forever — the person looks at it (flagged)
                p.transition(jid, JobState.PENDING_REVIEW, actor="ai_agent", note=f"QC video không chạy được 2 lần — cần bạn xem: {e}")
                p.conn.execute("UPDATE jobs SET escalated=1 WHERE id=?", (jid,))
                p.conn.commit()
            continue
        out["checked"] += 1
        out["decisions"][r["decision"]] = out["decisions"].get(r["decision"], 0) + 1
    return out


# ---- 4. whole-set consistency ----------------------------------------------------------------------------------------------
def _check_set(obj) -> None:
    if not isinstance(obj, dict) or not isinstance(obj.get("ok"), bool) or not isinstance(obj.get("issues"), list):
        raise llm_io.SchemaError("root: {ok, summary, issues: [...]}")
    for i, it in enumerate(obj["issues"]):
        if not isinstance(it, dict) or not isinstance(it.get("idx"), int) or not isinstance(it.get("problem"), str):
            raise llm_io.SchemaError(f"issues[{i}]: {{idx, problem, fix}}")


def contact_sheet(p: Pipeline, project_id: int, data_dir: str) -> Optional[str]:
    from . import formats
    frames = []
    for r in p.conn.execute("SELECT s.idx, s.data, (SELECT j.id FROM jobs j WHERE j.scene_id=s.id AND j.type='image_gen'"
                            " AND j.state='approved' ORDER BY j.id DESC LIMIT 1) AS jid FROM scenes s WHERE s.project_id=?"
                            " ORDER BY s.idx", (project_id,)):
        path = r["jid"] and os.path.join(data_dir, str(project_id), "images", f"job_{r['jid']}.png")
        if path and os.path.exists(path):
            d = json.loads(r["data"] or "{}")
            frames.append((path, f"S{r['idx']:02d}" + (f" · nhóm {d['sequence']}" if d.get("sequence") else "")))
    if len(frames) < 2:
        return None
    cell = formats.spec(formats.project_aspect(p.project(project_id)))["cell"]
    return layout.storyboard(frames, os.path.join(data_dir, str(project_id), "qc_set", "contact_sheet.png"), cols=4, cell=cell)


def set_consistency(p: Pipeline, project_id: int, client, data_dir: str) -> Dict:
    sheet = contact_sheet(p, project_id, data_dir)
    if sheet is None:
        raise LlmError("cần ít nhất 2 ảnh đã duyệt để so đồng bộ", code="not_enough")
    scenes = [{"idx": r["idx"], **{k: json.loads(r["data"] or "{}").get(k) for k in ("sequence", "location", "time", "characters")}}
              for r in p.conn.execute("SELECT idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,))]
    prompt = "\n\n---\n\n".join(x for x in [_read("prompts", "13_set_consistency.md"), _read("knowledge", "set_consistency_qa.md"),
                                            prompts.world_bible_text(p, project_id), _block("Các cảnh", scenes)] if x)
    obj = _run(p, project_id, "qc", prompt, _check_set, client, [("Tấm ghép các ảnh đã duyệt:", sheet)])
    with open(os.path.join(os.path.dirname(sheet), "result.json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return obj


CLIP_SET_NOTE = ("# Lần rà này là các CLIP VIDEO (kế hoạch v3)\n"
                 "Tấm ghép 1: khung GIỮA của mỗi clip dùng được, theo thứ tự phim (nhãn = mã shot/cảnh). Tấm ghép 2 (nếu có): các ĐIỂM NỐI "
                 "giữa hai shot liền mạch — khung CUỐI của shot trước đặt cạnh khung ĐẦU của shot sau. Ngoài đồng bộ màu/ánh sáng/phong cách/"
                 "nhân vật giữa các clip (clip do model khác nhau làm dễ lệch chất hình), kiểm tra điểm nối: người, vị trí, hướng, ánh sáng có "
                 "khớp không. `idx` = số thứ tự của clip cần làm lại; `fix` = câu tiếng Anh đưa vào motion prompt khi gen lại.")


def clip_frames(p: Pipeline, project_id: int, data_dir: str) -> Tuple[Optional[str], Optional[str]]:
    """(sheet of the middle frame of every usable clip, sheet of the cut points between continuing shots) — None when fewer
    than 2 clips."""
    import subprocess
    from . import final_cut, formats, shots
    from .ffmpeg_studio import find_ffmpeg, probe_duration
    folder = os.path.join(data_dir, str(project_id), "qc_set", "clips")
    os.makedirs(folder, exist_ok=True)
    clips = [c for c in final_cut.collect_clips(p, data_dir, project_id) if c.get("path") and c.get("idx")]
    if len(clips) < 2:
        return None, None
    ffmpeg = find_ffmpeg()
    mids, cuts = [], []
    by_idx = {c["idx"]: c for c in clips}

    def grab(path, t, name):
        dest = os.path.join(folder, name)
        subprocess.run([ffmpeg, "-y", "-ss", f"{max(t, 0):.2f}", "-i", path, "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "4", dest],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
        return dest if os.path.exists(dest) else ""

    for c in clips:
        row = p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=?", (project_id, c["idx"])).fetchone()
        data = json.loads(row["data"] or "{}") if row else {}
        dur = probe_duration(c["path"]) or 2.0
        mids.append((grab(c["path"], dur / 2, f"mid_{c['idx']:03d}.jpg"), shots.label(data, c["idx"])))
        nxt = by_idx.get(c["idx"] + 1)
        if data.get("continuous_with_next") and nxt:
            cuts.append((grab(c["path"], dur - 0.1, f"end_{c['idx']:03d}.jpg"), shots.label(data, c["idx"]) + " cuối"))
            cuts.append((grab(nxt["path"], 0.05, f"start_{nxt['idx']:03d}.jpg"), f"#{nxt['idx']} đầu"))
    cell = formats.spec(formats.project_aspect(p.project(project_id)))["cell"]
    mid_sheet = layout.storyboard([m for m in mids if m[0]], os.path.join(folder, "clips_mid.png"), cols=6, cell=cell)
    cut_sheet = layout.storyboard([c for c in cuts if c[0]], os.path.join(folder, "clips_cuts.png"), cols=4, cell=cell) if cuts else None
    return mid_sheet, cut_sheet


def clip_set_consistency(p: Pipeline, project_id: int, client, data_dir: str) -> Dict:
    """QC across ALL clips (v3): colour / light / look / character drift between clips (models differ) and matching cut points."""
    mid, cuts = clip_frames(p, project_id, data_dir)
    if mid is None:
        raise LlmError("cần ít nhất 2 clip để so đồng bộ", code="not_enough")
    rows = [{"idx": r["idx"], **{k: json.loads(r["data"] or "{}").get(k) for k in ("story_scene", "shot_no", "sequence", "location",
                                                                                   "characters", "continuous_with_next")}}
            for r in p.conn.execute("SELECT idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,))]
    prompt = "\n\n---\n\n".join(x for x in [_read("prompts", "13_set_consistency.md"), CLIP_SET_NOTE, _read("knowledge", "set_consistency_qa.md"),
                                            prompts.world_bible_text(p, project_id), _block("Các cảnh", rows)] if x)
    images = [("Tấm ghép 1 — khung giữa của từng clip:", mid)] + ([("Tấm ghép 2 — các điểm nối shot liền mạch:", cuts)] if cuts else [])
    obj = _run(p, project_id, "qc", prompt, _check_set, client, images)
    with open(os.path.join(data_dir, str(project_id), "qc_set", "clips_result.json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return obj


def last_clip_set_check(data_dir: str, project_id: int) -> Optional[Dict]:
    try:
        with open(os.path.join(data_dir, str(project_id), "qc_set", "clips_result.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def last_set_check(data_dir: str, project_id: int) -> Optional[Dict]:
    try:
        with open(os.path.join(data_dir, str(project_id), "qc_set", "result.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def redo_from_set_check(p: Pipeline, project_id: int, idx: int, fix: str) -> None:
    """Regenerate the approved picture of scene idx with the fix sentence (the person pressed 'gen lại'). The model gets only the
    English fix (the QC's `fix`), never the Vietnamese note; without a fix it would be the same input again — refused (luật 6)."""
    if not (fix or "").strip():
        raise ValueError(f"cảnh {idx}: QC đồng bộ không nêu câu sửa — gen lại sẽ gửi y hệt đầu vào; sửa prompt ảnh ở Bước 1 trước")
    row = p.conn.execute("SELECT j.id FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE s.project_id=? AND s.idx=?"
                         " AND j.type='image_gen' AND j.state='approved' ORDER BY j.id DESC LIMIT 1", (project_id, idx)).fetchone()
    if row is None:
        raise ValueError(f"cảnh {idx} không có ảnh đã duyệt")
    p.reopen_approved(row["id"], f"Đồng bộ cả bộ: {fix}", fix=fix.strip())


# ---- 5. Character Lock from pictures -----------------------------------------------------------------------------------------
def _check_lock(obj) -> None:
    llm_io._check_lock(obj, "lock")


def character_lock(p: Pipeline, project_id: int, name: str, client) -> Dict:
    row = p.conn.execute("SELECT * FROM characters WHERE project_id=? AND name=?", (project_id, name)).fetchone()
    if row is None:
        raise ValueError(f"không có nhân vật '{name}'")
    linked = assets.link_characters(p.conn, project_id, [name]).get(name)
    images = [(f"Ảnh tham chiếu — {name}:", assets.thumbnail(r["path"], 900)) for r in (linked or {}).get("refs", [])]
    images += [(f"Ảnh trang phục — {name}:", assets.thumbnail(i["path"], 900)) for i in assets.outfit_images(p.conn, project_id, name)]
    prompt = "\n\n---\n\n".join([_read("prompts", "14_character_lock.md"), _read("knowledge", "character_lock.md"),
                                 f"# {name}\nMô tả: {row['description']}\nTrang phục: {row['wardrobe'] or ''}"])
    obj = _run(p, project_id, "director", prompt, _check_lock, client, images)
    set_lock(p, project_id, name, obj)
    return obj


def set_lock(p: Pipeline, project_id: int, name: str, lock: Optional[Dict]) -> None:
    value = None if not lock or not any((lock.get(k) or "").strip() for k in llm_io.LOCK_KEYS) else \
        json.dumps({k: (lock.get(k) or "").strip() for k in llm_io.LOCK_KEYS}, ensure_ascii=False)
    p.conn.execute("UPDATE characters SET lock_rules=? WHERE project_id=? AND name=?", (value, project_id, name))
    p.conn.commit()


def get_lock(row) -> Dict:
    try:
        return json.loads(row["lock_rules"] or "{}")
    except (ValueError, KeyError, IndexError, TypeError):
        return {}


# ---- 5b. Character Bible vs the library pictures (F1) --------------------------------------------------------------------------
def _check_bible(names):
    def check(obj) -> None:
        if not isinstance(obj, dict) or not isinstance(obj.get("characters"), list):
            raise llm_io.SchemaError("root: {characters: [...]}")
        got = {str(c.get("name")) for c in obj["characters"] if isinstance(c, dict)}
        if got != set(names):
            raise llm_io.SchemaError(f"cần đúng các nhân vật {sorted(names)}, nhận {sorted(got)}")
        for c in obj["characters"]:
            if not isinstance(c.get("ok"), bool) or not isinstance(c.get("mismatches", []), list):
                raise llm_io.SchemaError("mỗi mục cần ok (true/false) và mismatches (danh sách)")
    return check


def _bible_key(row, refs) -> str:
    import hashlib
    h = hashlib.sha1((row["description"] or "").encode("utf-8") + (row["wardrobe"] or "").encode("utf-8")
                     + (row["lock_rules"] or "").encode("utf-8"))      # trial 2A: a wrong Lock went to every picture unchecked
    for r in refs:
        try:
            with open(r["path"], "rb") as f:
                h.update(hashlib.sha1(f.read()).digest())
        except OSError:
            h.update(r["path"].encode("utf-8"))
    return h.hexdigest()[:16]


def bible_check(p: Pipeline, project_id: int, client) -> Dict:
    """F1 (GĐ6 R1): does each character's Bible text agree with its library pictures? One Claude call for the characters whose
    text or pictures changed since the last check (cached per description + pictures). Returns {name: result}."""
    rows = {r["name"]: r for r in p.conn.execute("SELECT * FROM characters WHERE project_id=?", (project_id,))}
    linked = assets.link_characters(p.conn, project_id, list(rows))
    todo, images, out = [], [], {}
    for name, row in rows.items():
        refs = ((linked.get(name) or {}).get("refs") or [])[:1]
        if not refs:
            continue
        key = _bible_key(row, refs)
        old = json.loads(row["bible_check"] or "{}") if row["bible_check"] else {}
        if old.get("key") == key:
            out[name] = old
            continue
        if len(images) + 1 > 12:
            break                                          # the rest waits for the next call (never cut silently: they stay unchecked)
        todo.append((name, row, key))
        images.append((f"Ảnh tài nguyên chuẩn — {name}:", assets.thumbnail(refs[0]["path"], 900)))
    if todo:
        text = "\n".join((f"- **{n}**: {r['description'] or ''} {r['wardrobe'] or ''}".strip()
                          + (f" | Lock — luôn giữ: {get_lock(r).get('must_keep')}" if get_lock(r).get("must_keep") else ""))
                         for n, r, _ in todo)
        obj = _run(p, project_id, "director", _read("prompts", "18_bible_check.md") + "\n\n---\n\n# Nhân vật cần kiểm\n" + text,
                   _check_bible([n for n, _, _ in todo]), client, images)
        by_name = {str(c["name"]): c for c in obj["characters"]}
        for name, _, key in todo:
            res = dict(by_name[name], key=key)
            p.conn.execute("UPDATE characters SET bible_check=? WHERE project_id=? AND name=?",
                           (json.dumps(res, ensure_ascii=False), project_id, name))
            out[name] = res
        p.conn.commit()
    return out


def bible_flags(p: Pipeline, project_id: int) -> Dict[str, List[str]]:
    """{name: [mismatch...]} of the last check whose text/pictures are still current (empty = none known)."""
    rows = {r["name"]: r for r in p.conn.execute("SELECT * FROM characters WHERE project_id=?", (project_id,))}
    linked = assets.link_characters(p.conn, project_id, list(rows))
    out = {}
    for name, row in rows.items():
        res = json.loads(row["bible_check"] or "{}") if row["bible_check"] else {}
        refs = ((linked.get(name) or {}).get("refs") or [])[:1]
        if res and refs and res.get("key") == _bible_key(row, refs) and not res.get("ok"):
            out[name] = [str(m) for m in res.get("mismatches") or []] or ["mô tả chưa khớp ảnh"]
    return out


# ---- 6. voice casting ------------------------------------------------------------------------------------------------------
def _check_cast(obj) -> None:
    if not isinstance(obj, dict) or not isinstance(obj.get("cast"), list):
        raise llm_io.SchemaError("root: {cast: [...]}")
    for i, c in enumerate(obj["cast"]):
        if not isinstance(c, dict) or not isinstance(c.get("name"), str) or not isinstance(c.get("voice_id"), int):
            raise llm_io.SchemaError(f"cast[{i}]: {{name, voice_id, why, persona}}")


def cast_voices(p: Pipeline, project_id: int, client, voices: List[Dict], overwrite: bool = False) -> Dict:
    """Pick a voice for every speaking character without one (or all when overwrite)."""
    speakers = {w.upper() for ln in voice.planned_lines(p.conn, project_id) for w in [ln["speaker"]] if w}
    rows = p.conn.execute("SELECT name, description, voice_profile FROM characters WHERE project_id=?", (project_id,)).fetchall()
    todo = [r for r in rows if r["name"].upper() in speakers and (overwrite or not voice.get_profile(r).get("voice_id"))]
    if not todo or not voices:
        return {"cast": []}
    samples = {}
    for ln in voice.planned_lines(p.conn, project_id):
        samples.setdefault(ln["speaker"].upper(), []).append(ln["text"])
    chars = [{"name": r["name"], "description": r["description"], "lines": samples.get(r["name"].upper(), [])[:3]} for r in todo]
    pool = [{"id": v.get("id"), "name": voice.display_name(v), "description": v.get("description") or v.get("labels") or "",
             "tieng_viet": voice.speaks_vi(v), "gender": voice.voice_gender(v), "uu_tien": voice.preferred(v) is not None}
            for v in voice.casting_pool(voices)]
    if not pool:                           # AU-b: never cast a voice that does not speak Vietnamese for Vietnamese lines
        raise LlmError("thư viện giọng Clip AI không có giọng nào ghi hỗ trợ tiếng Việt — chưa chọn giọng (chưa gọi Claude)",
                       code="no_vi_voice")
    names = {v.get("id") for v in voice.casting_pool(voices)}
    prompt = "\n\n---\n\n".join([_read("prompts", "15_voice_casting.md"), _block("Nhân vật", chars), _block("Giọng có sẵn", pool)])
    obj = _run(p, project_id, "director", prompt, _check_cast, client)
    vi_ids = names
    names = {v.get("id"): voice.display_name(v) for v in voices}
    for c in obj["cast"]:
        if c["voice_id"] in names and c["voice_id"] in vi_ids:
            voice.set_profile(p.conn, project_id, c["name"], {"voice_id": c["voice_id"], "voice_name": names[c["voice_id"]],
                                                            "persona": c.get("persona", "")})
    return obj


# ---- 7. music brief --------------------------------------------------------------------------------------------------------
def _check_brief(obj) -> None:
    if not isinstance(obj, dict) or not isinstance(obj.get("prompt"), str) or not obj["prompt"].strip():
        raise llm_io.SchemaError("root: {..., prompt: '...'}")


def music_brief(p: Pipeline, project_id: int, client) -> Dict:
    """{"prompt", "length_ms", "instrumental"} written by Claude from the scenes; the template brief when Claude is not available."""
    from . import music
    fallback = music.default_brief(p, project_id)
    if client is None:
        return fallback
    scenes = []
    for r in p.conn.execute("SELECT s.idx, s.data, m.duration_sec FROM scenes s LEFT JOIN motion_prompts m ON m.scene_id=s.id"
                            " WHERE s.project_id=? ORDER BY s.idx", (project_id,)):
        d = json.loads(r["data"] or "{}")
        scenes.append({"idx": r["idx"], "seconds": r["duration_sec"] or d.get("duration_s") or 5, "mood": d.get("mood"),
                       "emotional_intent": d.get("emotional_intent"), "shot_role": d.get("shot_role")})
    proj = p.project(project_id)
    prompt = "\n\n---\n\n".join([_read("prompts", "04_music_brief.md"), f"# Thể loại: {proj['genre'] or 'chưa rõ'}",
                                 _block("Các cảnh", scenes)])
    try:
        obj = _run(p, project_id, "music", prompt, _check_brief, client)
    except LlmError:
        return fallback
    seconds = max(float(obj.get("duration_sec") or 0), fallback["length_ms"] / 1000)   # the music must cover the whole film
    return {"prompt": obj["prompt"][:2000], "length_ms": int(min(max(float(seconds) * 1000, music.MIN_MS), music.MAX_MS)),
            "instrumental": bool(obj.get("instrumental", True)), "brief": obj}
