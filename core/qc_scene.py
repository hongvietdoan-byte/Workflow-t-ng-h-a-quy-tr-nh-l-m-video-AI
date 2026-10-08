"""QC per script scene (flag scene_qc; docs/THIET_KE_LAI_QC_VA_KET_NOI_2026-09-27.md).

Why: on the 54 labelled pictures of #8 the per-picture Claude QC scored faulty pictures (0.67) like good ones (0.69), approved 6 of 16 obvious
faults and rejected none of them; it never saw two frames side by side, had no reference for the place, and one of its criteria was
overwritten by code. The person asked for a QC that is stricter, reasons about each fault and names the right fix.

Layer 0 — code, free, every picture as it arrives (`check_frame`): the shot size measured from the face height (thresholds measured on
the #7/#8 frames of known size), eyes under the app's top bar, a night face too dark, faces missing / extra. A sure fault is redrawn at once
with a precise fix sentence (runner.RedrawWithFix); an unsure one becomes a flag for layer 1.
Layer 1 — Claude, ONE call per script scene once all its frames exist (`review_scene`): a contact sheet of the scene's frames, the scene's
establishing picture (the standard of the place and light), one standard picture per character + Lock, the shot table and the layer-0
flags; for every frame yes/no checks WITH visible evidence, a verdict (pass / fix / doubt) and the root cause (prompt / reference / model /
plan) so the right input is changed. pass → approved; fix → drawn again with the fix (not for `plan`: the shot table is wrong, a person
decides); doubt → held for the person with the evidence.
"""
import json
import os
import re
from typing import Dict, List, Optional, Tuple

from . import features

FEATURE = "scene_qc"
SIZES = ["WS", "MLS", "MS", "MCU", "CU", "ECU"]
# face height / frame height where each size starts (vertical frames; measured 2026-09-27: WS 0.04–0.07, MS 0.14–0.18, MCU ~0.22,
# CU 0.26–0.30, ECU 0.67)
SIZE_FROM = [("ECU", 0.50), ("CU", 0.25), ("MCU", 0.20), ("MS", 0.12), ("MLS", 0.08), ("WS", 0.0)]
TOP_BAR = 0.15            # the app's top bar covers ~15 % of a vertical frame (editor/safe_zones.md)
DARK_REDRAW, DARK_FLAG = 0.15, 0.20      # mean face brightness 0–1 (night frames liked by the person: 0.19–0.26)
CHECKS = ("identity", "place", "action", "framing", "continuity", "artifacts")
VERDICTS = ("pass", "fix", "doubt")
CAUSES = ("prompt", "reference", "model", "plan", "none")
SHEET_MAX = 6
EQUIV = {"EWS": "WS", "GAME_TPS": "WS", "LS": "WS"}


def enabled() -> bool:
    return features.on(FEATURE)


def shadow() -> bool:
    """🎓 học việc (B1 08/10): runs and records its decision, never acts."""
    return features.shadow(FEATURE)


def active() -> bool:
    """On or học việc — for choosing a branch only (the old QC must not come back while this is học việc)."""
    return features.active(FEATURE)


def measured_size(face_h: float) -> str:
    return next(name for name, start in SIZE_FROM if face_h >= start)


def _behind(data: Dict) -> bool:
    words = f"{data.get('angle') or ''} {data.get('shot') or ''} {data.get('blocking') or ''} {data.get('start_frame') or ''}".lower()
    return "ots" in words or "over the shoulder" in words or "over-the-shoulder" in words or "from behind" in words or "back to camera" in words


# ---- layer 0 -------------------------------------------------------------------------------------------------------------
TIER_FLAG = 5              # S5.4: long horizontal edge lines behind the people (wall tops, step edges) — calibrated 29/09: the 16
                           # eye-level renders of the real tower model count 0–3, #8's "stacked terraces" frames 5–10 (S5, S8, S20, S24)
TIER_SIZES = ("WS", "EWS", "MLS", "MS", "GAME_TPS")


def tier_lines(path: str) -> int:
    """How many long horizontal edges cross the lower 70 % of the frame (a row ≥ 35 % edge pixels; rows within 6 px are one line)."""
    import numpy as np
    from PIL import Image
    im = np.asarray(Image.open(path).convert("L").resize((360, 640)), dtype=np.float32) / 255
    rows = (np.abs(im[2:, :] - im[:-2, :]) > 0.08).mean(axis=1)
    lines, last = 0, -10
    for i in range(int(len(rows) * 0.30), len(rows)):
        if rows[i] >= 0.35:
            if i - last > 6:
                lines += 1
            last = i
    return lines


def check_frame(path: str, data: Dict, flat_place: bool = False, measure: Optional[Dict] = None) -> List[Dict]:
    """Code checks of one frame. [{code, severity: "redraw" | "flag", problem (vi), fix (en)}]; [] when fine or when the face detector is
    not available (said by the caller). flat_place: the scene's place is described as flat (library layout sentence) — the frame's
    background is counted for stacked terraces (S5.4, playbook G1). measure (KLD-16): a dict filled with {measured, planned, face_h} whenever
    a face is found — also when the size is right — so the học việc log keeps the pairs that calibrate SIZE_FROM."""
    from . import text_placement
    blank = _blank(path)
    if blank:                                     # an empty / black / one-colour picture never reaches Claude (regression 2026-09-27:
        return [{"code": "blank", "severity": "redraw", "problem": blank,    # the scene QC passed a black cell)
                 "fix": "Draw the full scene of the shot: the characters in the place, lit, in focus."}]
    out: List[Dict] = []
    size = EQUIV.get(str(data.get("size") or "").upper(), str(data.get("size") or "").upper())
    if flat_place and size in TIER_SIZES:
        n = tier_lines(path)
        if n >= TIER_FLAG:                        # a flag for eyes (qc playbook G1), never a redraw by itself: people / props also draw lines
            out.append({"code": "stacked_tiers", "severity": "flag",
                        "problem": f"nền có {n} đường ngang dài (mép tường / bậc chồng lớp) — bối cảnh trong Kho được tả là mặt bằng phẳng",
                        "fix": "Keep the place's real layout: flat open ground, only low retaining walls, no stacked terraces."})
    boxes = text_placement.face_boxes(path)
    if boxes is None:
        return out
    cast = [str(c) for c in data.get("characters") or []]
    night = str(data.get("time") or "").lower() == "night"
    if not boxes:
        if size in ("ECU", "CU", "MCU") and not _behind(data):
            out.append({"code": "no_face", "severity": "flag", "problem": f"không thấy khuôn mặt nào dù shot {size}",
                        "fix": "The character's face is clearly visible, turned towards the camera."})
        return out
    big = max(boxes, key=lambda b: b[3] - b[1])
    h = big[3] - big[1]
    got = measured_size(h)
    if measure is not None:
        measure.update({"measured": got, "planned": size or None, "face_h": round(float(h), 3)})
    if size in SIZES:
        steps = SIZES.index(got) - SIZES.index(size)
        severe = abs(steps) >= 2 or (size in ("CU", "ECU") and steps < 0)
        if steps:
            want = {"ECU": "an extreme close-up: only the face fills the frame", "CU": "a close-up: head and top of the shoulders, the face "
                    "fills about a third of the frame height", "MCU": "a medium close-up: head and chest", "MS": "a medium shot: from the "
                    "waist up", "MLS": "a medium long shot: from the knees up", "WS": "a wide shot: whole bodies with the place around them"}[size]
            out.append({"code": "shot_size", "severity": "redraw" if severe else "flag",
                        "problem": f"cỡ cảnh đo được {got} (mặt cao {h:.2f} khung) — shot xin {size}", "fix": f"Frame as {want}.",
                        "measured": got, "planned": size})
    eye = big[1] + 0.4 * h
    if eye < TOP_BAR and size in ("ECU", "CU", "MCU", "MS") and size != "ECU":
        out.append({"code": "top_bar", "severity": "redraw" if size in ("CU", "MCU") else "flag",
                    "problem": f"mắt ở {eye:.0%} từ trên — nằm dưới thanh giao diện ứng dụng",
                    "fix": "Leave headroom: the eyes sit about one third from the top of the frame."})
    if night:
        light = _face_light(path, big)
        if light is not None and light < DARK_FLAG:
            out.append({"code": "dark_face", "severity": "redraw" if light < DARK_REDRAW else "flag",
                        "problem": f"mặt quá tối ({light:.2f})",
                        "fix": "Night, but the faces are clearly lit: warm street-lamp key light on the faces, cool moonlight rim light."})
    if len(boxes) > len(cast) + (0 if size in ("ECU", "CU", "MCU") else 1):
        out.append({"code": "extra_faces", "severity": "flag", "problem": f"{len(boxes)} khuôn mặt, bảng shot có {len(cast)} người",
                    "fix": "Only " + (", ".join(cast) or "the listed characters") + " in the frame — no other people."})
    return out


def for_trainee(flags: List[Dict]) -> List[Dict]:
    """KLD-16 (08/10): in 🎓 học việc a size measured from the face is never a redraw — SIZE_FROM is not calibrated yet (on #22 the
    person kept frames it called wrong). A copy; the other checks keep their severity."""
    out = []
    for f in flags:
        f = dict(f)
        if f.get("code") == "shot_size" and f.get("severity") == "redraw":
            f["severity"] = "flag"
        out.append(f)
    return out


def size_calibration(conn, project_ids: Optional[List[int]] = None) -> List[Dict]:
    """KLD-16: the pairs that calibrate SIZE_FROM (0 USD) — one row per scene_qc học việc frame that had a face: measured size, planned
    size, face height, what the trainee would do, and the person's decision on that frame (trainee_log.truth when scored, else the
    person's first review_log decision after the trainee; None = not decided yet). Thresholds are NOT changed here."""
    q = "SELECT id, at, project_id, job_id, decision, detail, truth FROM trainee_log WHERE feature=? AND detail IS NOT NULL"
    args: list = [FEATURE]
    if project_ids:
        q += " AND project_id IN (" + ",".join("?" * len(project_ids)) + ")"
        args += list(project_ids)
    out = []
    for r in conn.execute(q + " ORDER BY id", args).fetchall():
        try:
            size = (json.loads(r["detail"]) or {}).get("size")
        except ValueError:
            size = None
        if not size or not size.get("measured"):
            continue
        person = r["truth"]
        if person is None and r["job_id"] is not None:
            from .trainee import _t                 # the same "decided AFTER the role" rule as trainee.score_project
            at = _t(r["at"])
            revs = conn.execute("SELECT decision, decided_at FROM review_log WHERE job_id=? AND reviewer_type='user' "
                                "ORDER BY decided_at, id", (r["job_id"],)).fetchall()
            after = [v for v in revs if at is not None and _t(v["decided_at"]) is not None and _t(v["decided_at"]) > at]
            person = after[0]["decision"] if after else None
        out.append({"project_id": r["project_id"], "job_id": r["job_id"], "measured": size.get("measured"),
                    "planned": size.get("planned"), "face_h": size.get("face_h"), "trainee": r["decision"], "person": person})
    return out


def _blank(path: str) -> Optional[str]:
    """Why the picture is not a picture (missing, unreadable, black, one flat colour), else None."""
    try:
        import numpy as np
        from PIL import Image
        im = np.asarray(Image.open(path).convert("L").resize((96, 170)), dtype=float) / 255.0
    except Exception as e:  # noqa: BLE001
        return f"không đọc được ảnh ({type(e).__name__})"
    if im.mean() < 0.03:
        return "ảnh đen hoàn toàn"
    if im.std() < 0.02:
        return "ảnh một màu, không có nội dung"
    return None


def _face_light(path: str, box) -> Optional[float]:
    try:
        import numpy as np
        from PIL import Image
        im = np.asarray(Image.open(path).convert("L"), dtype=float) / 255.0
    except Exception:  # noqa: BLE001
        return None
    H, W = im.shape
    l, t, r, b = box
    crop = im[int(t * H):max(int(b * H), int(t * H) + 1), int(l * W):max(int(r * W), int(l * W) + 1)]
    return float(crop.mean()) if crop.size else None


def _store(data_dir: str, pid: int) -> str:
    return os.path.join(data_dir, str(pid), "qc_scene")


def _load(data_dir: str, pid: int, name: str) -> Dict:
    try:
        with open(os.path.join(_store(data_dir, pid), name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(data_dir: str, pid: int, name: str, obj: Dict) -> None:
    os.makedirs(_store(data_dir, pid), exist_ok=True)
    with open(os.path.join(_store(data_dir, pid), name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def record_flags(data_dir: str, pid: int, job_id: int, flags: List[Dict]) -> None:
    idx = _load(data_dir, pid, "layer0.json")
    idx[str(job_id)] = flags
    _save(data_dir, pid, "layer0.json", idx)


def flags_of(data_dir: str, pid: int, job_id: int) -> List[Dict]:
    return _load(data_dir, pid, "layer0.json").get(str(job_id)) or []


# ---- layer 1 -------------------------------------------------------------------------------------------------------------
def validate(obj, expected: List[Tuple[int, str]]) -> Dict:
    """Strict: every frame once, every check with visible evidence, a failed check → fix / doubt, a fix → English sentence + cause."""
    from .llm_io import SchemaError
    if not isinstance(obj, dict) or not isinstance(obj.get("frames"), list):
        raise SchemaError("root: {frames: [...], scene: {...}}")
    seen = {}
    for f in obj["frames"]:
        if not isinstance(f, dict) or not isinstance(f.get("k"), int):
            raise SchemaError("frames[]: cần k (số) cho mọi khung")
        if f["k"] in seen:
            raise SchemaError(f"khung K{f['k']} xuất hiện 2 lần")
        seen[f["k"]] = f
        checks = f.get("checks") or {}
        for c in CHECKS:
            ck = checks.get(c)
            if not isinstance(ck, dict) or not isinstance(ck.get("ok"), bool) or len(str(ck.get("evidence") or "").strip()) < 8:
                raise SchemaError(f"K{f['k']}.{c}: cần ok (true/false) + evidence là điều nhìn thấy cụ thể")
            if re.fullmatch(r"\W*(ổn|tốt|ok|không (thấy )?lỗi|good|fine|none)\W*", str(ck["evidence"]).strip(), re.I):
                raise SchemaError(f"K{f['k']}.{c}: evidence phải là điều nhìn thấy, không phải lời kết luận")
        if f.get("verdict") not in VERDICTS or f.get("root_cause") not in CAUSES:
            raise SchemaError(f"K{f['k']}: verdict ∈ {VERDICTS}, root_cause ∈ {CAUSES}")
        failed = [c for c in CHECKS if not checks[c]["ok"]]
        if failed and f["verdict"] == "pass":
            raise SchemaError(f"K{f['k']}: {failed} không đạt mà verdict = pass")
        if f["verdict"] == "fix":
            if f["root_cause"] == "none" or not str(f.get("problem") or "").strip():
                raise SchemaError(f"K{f['k']}: fix cần problem + root_cause")
            fix = str(f.get("fix") or "")
            if f["root_cause"] != "plan" and (len(fix) < 15 or re.search(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]", fix, re.I)):
                raise SchemaError(f"K{f['k']}: fix phải là một câu mệnh lệnh tiếng Anh")
    missing = [k for k, _ in expected if k not in seen]
    if missing:
        raise SchemaError(f"thiếu khung {missing}")
    return obj


def scene_frames(p, pid: int, story_scene, data_dir: str) -> Optional[List[Dict]]:
    """The scene's shots with their current picture, or None while a picture of the scene is still queued / being made."""
    rows = []
    for s in p.conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall():
        d = json.loads(s["data"] or "{}")
        if d.get("story_scene") != story_scene or not d.get("shot_no"):
            continue
        if p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND state IN ('queued','running','retryable')",
                          (s["id"],)).fetchone():
            return None
        j = p.conn.execute("SELECT id, state FROM jobs WHERE scene_id=? AND type='image_gen' AND state IN "
                           "('succeeded','pending_review','approved') ORDER BY id DESC LIMIT 1", (s["id"],)).fetchone()
        if j is None:
            return None
        path = os.path.join(data_dir, str(pid), "images", f"job_{j['id']}.png")
        if not os.path.exists(path):
            return None
        rows.append({"scene_id": s["id"], "idx": s["idx"], "data": d, "job_id": j["id"], "state": j["state"], "path": path})
    return rows or None


def _shot_line(k: int, r: Dict) -> Dict:
    d = r["data"]
    words = f"{d.get('blocking') or ''} {d.get('start_frame') or ''}"
    return {"K": k, "shot": f"S{d.get('story_scene')}·{d.get('shot_no')}", "size": d.get("size"), "angle": d.get("angle"),
            "characters": d.get("characters"), "time": d.get("time"), "action": (d.get("action") or "")[:160],
            "left_right": re.findall(r"[A-Z]{3,}[^,;.]{0,40}frame-(?:left|right)", words)[:3]}


def build_request(p, pid: int, frames: List[Dict], data_dir: str) -> Tuple[str, List[Tuple[str, str]], List[Tuple[int, str]]]:
    from . import assets, layout, prompts, scene_establish
    from .claude_tasks import _read
    story = frames[0]["data"].get("story_scene")
    out_dir = os.path.join(_store(data_dir, pid), f"scene_{story}")
    os.makedirs(out_dir, exist_ok=True)
    labels = [(k, f"K{k} · S{r['data'].get('story_scene')}·{r['data'].get('shot_no')} · {r['data'].get('size') or ''}")
              for k, r in enumerate(frames, 1)]
    images: List[Tuple[str, str]] = []
    for n in range(0, len(frames), SHEET_MAX):
        chunk = list(zip(frames[n:n + SHEET_MAX], labels[n:n + SHEET_MAX]))
        sheet = layout.storyboard([(r["path"], lab) for r, (_, lab) in chunk], os.path.join(out_dir, f"sheet_{n // SHEET_MAX + 1}.png"),
                                  cols=3, cell=(384, 683))
        images.append((f"Tấm ghép khung {chunk[0][1][0]}–{chunk[-1][1][0]} của cảnh:", sheet))
    est = scene_establish.picture(data_dir, pid, story)
    if est:
        images.append(("Ảnh toàn cảnh của cảnh — CHUẨN NƠI CHỐN + ÁNH SÁNG:", assets.thumbnail(est, 1024)))
    names: List[str] = []
    for r in frames:
        for n in r["data"].get("characters") or []:
            if str(n) not in names:
                names.append(str(n))
    links = assets.link_characters(p.conn, pid, names)
    for n in names:
        ref = (links.get(n) or {}).get("ref")
        if ref and os.path.exists(ref.get("path", "")):
            images.append((f"Ảnh chuẩn — {n}:", assets.thumbnail(ref["path"], 900)))
    table = [_shot_line(k, r) for k, r in enumerate(frames, 1)]
    flags = {f"K{k}": flags_of(data_dir, pid, r["job_id"]) for k, r in enumerate(frames, 1) if flags_of(data_dir, pid, r["job_id"])}
    prompt = "\n\n---\n\n".join(x for x in [
        _read("prompts", "21_scene_qc.md"), _read("knowledge", "ai_image_failure_modes.md"),
        prompts.lock_text(p.conn, pid, names),
        "# Bảng shot của cảnh\n```json\n" + json.dumps(table, ensure_ascii=False, indent=1) + "\n```",
        ("# Cờ đo bằng code (lớp 0) — xác minh bằng mắt\n```json\n" + json.dumps(flags, ensure_ascii=False, indent=1) + "\n```") if flags else "",
        "" if est else "(Cảnh này KHÔNG có ảnh toàn cảnh — điểm place so với mô tả nơi chốn trong bảng shot.)"] if x)
    return prompt, images, labels


def review_scene(p, pid: int, story_scene, client, data_dir: str, frames: Optional[List[Dict]] = None) -> Dict:
    """Layer 1 for one scene; applies the verdicts to the frames that wait for a decision. Returns the answer (+ "applied")."""
    from .claude_tasks import _run
    frames = frames or scene_frames(p, pid, story_scene, data_dir)
    if not frames:
        raise ValueError(f"cảnh {story_scene} chưa đủ khung")
    prompt, images, labels = build_request(p, pid, frames, data_dir)
    obj = _run(p, pid, "qc", prompt, lambda o: validate(o, labels), client, images)
    applied = apply(p, pid, frames, obj, data_dir)
    rec = _load(data_dir, pid, "reviews.json")
    rec.setdefault(str(story_scene), []).append({"jobs": [r["job_id"] for r in frames], "answer": obj, "applied": applied})
    _save(data_dir, pid, "reviews.json", rec)
    return {**obj, "applied": applied}


def _hold(p, job_id: int, note: str) -> None:
    from .states import JobState
    if p.job(job_id)["state"] == "succeeded":
        p.transition(job_id, JobState.PENDING_REVIEW, actor="ai_agent", note=note)
    p.conn.execute("INSERT INTO qc_results (job_id, criterion, score, threshold_at_time, auto_decision) VALUES (?,?,?,?,?)",
                   (job_id, "scene_qc_hold", 0.0, 1.0, "hold"))
    p.conn.commit()


def trusted() -> bool:
    """Layer 1 may approve / redraw on its own only once it has passed its acceptance test (FEATURE_SCENE_QC_TRUSTED=1 is set by
    hand after that). Regression 2026-09-27 on the labelled composites of #8: it caught 6/12 obvious faults but never for the right
    reason (passed 6 pasted rectangles + a Big-Ben tower) and flagged 12/21 good frames for trivia — so until then its verdicts are
    notes for the person: every frame waits at the storyboard gate."""
    return features.on("scene_qc_trusted")


def apply(p, pid: int, frames: List[Dict], obj: Dict, data_dir: str) -> Dict[str, str]:
    """pass → approved (unless a layer-0 flag is left); fix → drawn again with the fix (plan → held); doubt → held with the evidence.
    Not trusted yet (see trusted()): every frame is held with the verdict as a note."""
    from .states import JobState
    by_k = {f["k"]: f for f in obj["frames"]}
    out: Dict[str, str] = {}
    if not trusted():
        for k, r in enumerate(frames, 1):
            f = by_k[k]
            if p.job(r["job_id"])["state"] not in ("succeeded", "pending_review"):
                out[f"K{k}"] = f"giữ nguyên ({p.job(r['job_id'])['state']})"
                continue
            bad = "; ".join(f"{c}: {f['checks'][c]['evidence']}" for c in CHECKS if not f["checks"][c]["ok"])
            note = (f"QC cảnh (tham khảo, chưa nghiệm thu) {f['verdict']}"
                    + (f" [{f['root_cause']}]: {f.get('problem') or bad}" if f["verdict"] != "pass" else "")
                    + (f" — {f['note']}" if f.get("note") else "") + (f" — sửa gợi ý: {f['fix']}" if f.get("fix") else ""))
            _hold(p, r["job_id"], note[:600])
            out[f"K{k}"] = f"giữ cho người ({f['verdict']})"
        return out
    for k, r in enumerate(frames, 1):
        f = by_k[k]
        job = p.job(r["job_id"])
        if job["state"] not in ("succeeded", "pending_review"):
            out[f"K{k}"] = f"giữ nguyên ({job['state']})"
            continue
        evidence = "; ".join(f"{c}: {f['checks'][c]['evidence']}" for c in CHECKS if not f["checks"][c]["ok"])
        if f["verdict"] == "pass":
            left = [x for x in flags_of(data_dir, pid, r["job_id"]) if x.get("severity") == "flag"]
            if left:
                _hold(p, r["job_id"], "QC cảnh: đạt nhưng còn cờ đo bằng code — " + "; ".join(x["problem"] for x in left))
                out[f"K{k}"] = "giữ cho người (cờ lớp 0)"
            else:
                if job["state"] == "succeeded":
                    p.transition(r["job_id"], JobState.PENDING_REVIEW, actor="ai_agent", note="QC cảnh: đạt")
                p.approve(r["job_id"], "ai_agent", "QC cảnh: đạt — " + f["seen"][:120] if f.get("seen") else "QC cảnh: đạt")
                out[f"K{k}"] = "duyệt"
        elif f["verdict"] == "fix" and f["root_cause"] != "plan":
            if job["state"] == "succeeded":
                p.transition(r["job_id"], JobState.PENDING_REVIEW, actor="ai_agent", note="QC cảnh")
            res = p.reject(r["job_id"], "ai_agent", f"QC cảnh [{f['root_cause']}]: {f['problem']} — {evidence}"[:600], fix=f["fix"],
                           qc={"root_cause": f.get("root_cause"), "problem": f.get("problem"), "fix": f.get("fix")})   # S14.17 Đạo diễn đọc lỗi
            out[f"K{k}"] = f"vẽ lại ({f['root_cause']}) → {res}"
        else:
            why = "bảng shot cần người sửa" if f["verdict"] == "fix" else "chưa đủ rõ"
            _hold(p, r["job_id"], f"QC cảnh: {why} — {f.get('problem') or evidence}"[:600])
            out[f"K{k}"] = f"giữ cho người ({why})"
    return out


CLAUDE_FLAG = "scene_qc_claude"


def claude_on() -> bool:
    """Layer 1 (one Claude look per scene) runs by itself only when switched on, or when the QC agent replaces it. Trial #8
    2026-09-27: it failed its acceptance test, its verdicts were notes only, and re-reading a whole scene after each redraw cost
    ~0.5 USD of the Claude cap for nothing — layer 0 (code, free) keeps running in the image runner."""
    from . import qc_agent, qc_team
    return features.on(CLAUDE_FLAG) or qc_agent.enabled() or qc_team.enabled()


def to_review(frames: List[Dict], judged: List[int]) -> List[Dict]:
    """The frames a new look needs: after a redraw, the changed frames and their neighbours in the scene (the continuity strip),
    not the whole scene again. No earlier look → every frame."""
    if not judged:
        return frames
    changed = [i for i, r in enumerate(frames) if r["job_id"] not in judged]
    keep = sorted({j for i in changed for j in (i - 1, i, i + 1) if 0 <= j < len(frames)})
    return [frames[i] for i in keep] or frames


def _trainee_team(p, pid: int, s, client, data_dir: str, frames: List[Dict], key: List[int], done: Dict) -> None:
    """🎓 qc_team học việc: the changed frames only (as the real team would), never stops the project; reviews.json marks the look
    `"trainee": true` with no verdict in it (the person must not see one before deciding)."""
    from . import qc_team
    seen = [j for prev in done.get(str(s), []) if prev.get("trainee") for j in prev.get("jobs") or []]
    subset = to_review(frames, seen)
    try:
        res = qc_team.review_scene(p, pid, s, client, data_dir, frames, focus=[r["job_id"] for r in subset], shadow=True)
    except Exception as e:                             # noqa: BLE001 — học việc never breaks the real run
        res = {"stopped": str(e)}
    rec = _load(data_dir, pid, "reviews.json")
    rec.setdefault(str(s), []).append({"jobs": key, "looked_at": [r["job_id"] for r in subset], "trainee": True,
                                       **({"trainee_stopped": str(res["stopped"])[:200]} if res.get("stopped") else {})})
    _save(data_dir, pid, "reviews.json", rec)


def run_ready_scenes(p, pid: int, client, data_dir: str) -> Dict:
    """Review every script scene whose frames are all made and some still wait for a decision; each set of pictures once.
    Layer 1 off (claude_on): the new frames go to the person without a Claude call."""
    done = _load(data_dir, pid, "reviews.json")
    scenes = []
    for (raw,) in p.conn.execute("SELECT data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)):
        s = json.loads(raw or "{}").get("story_scene")
        if s is not None and s not in scenes:
            scenes.append(s)
    summary = {"reviewed": [], "failed": [], "waiting": []}
    for s in scenes:
        frames = scene_frames(p, pid, s, data_dir)
        if not frames or not any(r["state"] in ("succeeded", "pending_review") for r in frames):
            continue
        key = [r["job_id"] for r in frames]
        if any(prev.get("jobs") == key for prev in done.get(str(s), [])):
            continue                                   # these very pictures were judged already
        if not claude_on():
            from .states import JobState
            for r in frames:
                if p.job(r["job_id"])["state"] == "succeeded":
                    p.transition(r["job_id"], JobState.PENDING_REVIEW, actor="system", note="QC Claude theo cảnh đang tắt — chờ người duyệt")
            rec = _load(data_dir, pid, "reviews.json")
            rec.setdefault(str(s), []).append({"jobs": key, "skipped": "QC Claude tắt (lớp 0 bằng code vẫn chạy)"})
            _save(data_dir, pid, "reviews.json", rec)
            summary["waiting"].append(s)
            from . import qc_team
            if qc_team.shadow():                       # 🎓 Tổ QC học việc (B5 08/10): looks, records block/pass only — no hold / note
                _trainee_team(p, pid, s, client, data_dir, frames, key, done)
            continue
        judged = [j for prev in done.get(str(s), []) if not prev.get("skipped") and not prev.get("trainee")
                  for j in prev.get("jobs") or []]
        subset = to_review(frames, judged)
        try:
            from . import qc_agent, qc_team
            if qc_team.enabled():                      # Tổ QC (01/10): code + C1 per frame, every frame held for the person
                res = qc_team.review_scene(p, pid, s, client, data_dir, frames, focus=[r["job_id"] for r in subset])
                if res.get("stopped"):
                    summary["failed"].append((s, res["stopped"]))
                    if res.get("blocked"):
                        continue
                else:
                    rec = _load(data_dir, pid, "reviews.json")
                    rec.setdefault(str(s), []).append({"jobs": key, "looked_at": [r["job_id"] for r in subset], "team": res["results"]})
                    _save(data_dir, pid, "reviews.json", rec)
                    summary["reviewed"].append((s, res["applied"]))
                continue
            if qc_agent.enabled():                     # the investigating agent: the whole scene as context, records the subset
                res = qc_agent.review_scene(p, pid, s, client, data_dir, frames, focus=[r["job_id"] for r in subset])
                if res.get("stopped"):                 # a lock / Claude blocked / cut short: said, and NOT marked as judged, so the
                    summary["failed"].append((s, res["stopped"]))    # frames are looked at again once the cause is fixed (review 28/09)
                    if res.get("blocked"):
                        continue
                else:
                    rec = _load(data_dir, pid, "reviews.json")
                    rec.setdefault(str(s), []).append({"jobs": key, "looked_at": [r["job_id"] for r in subset],
                                                       "agent": {k: v for k, v in res.items() if k != "applied"}, "applied": res["applied"]})
                    _save(data_dir, pid, "reviews.json", rec)
            else:
                res = review_scene(p, pid, s, client, data_dir, subset)
                if len(subset) < len(frames):          # the scene's full set counts as judged (only the changed strip was looked at)
                    rec = _load(data_dir, pid, "reviews.json")
                    rec.setdefault(str(s), []).append({"jobs": key, "looked_at": [r["job_id"] for r in subset]})
                    _save(data_dir, pid, "reviews.json", rec)
            summary["reviewed"].append((s, res["applied"]))
        except Exception as e:  # noqa: BLE001 - one scene's failure is said, the others go on
            from .llm_runner import fail_text
            summary["failed"].append((s, fail_text(e, f"{type(e).__name__}: {e}")))      # keeps LlmError.code for the autopilot
    return summary
