"""Which video model for which scene — from the ClipAI model guide (data/video_models.json, copied from the slide
"Hôm nay tôi chọn mô hình video như thế nào"), not a fixed default.

The project picks a priority (quality / balanced / value, the two ladders of the slide plus a mix); every scene then gets a
recommendation with its reason and price, which the person can override per scene (motion_prompts.video_model).
A project that still has the v1 `projects.video_model` set keeps using that one model everywhere.
"""
import json
import math
import os
from typing import Dict, List, Optional

from . import dialogue
from .memo import read_json

PROFILES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "video_models.json")
PRIORITIES = ("quality", "balanced", "value")
DEFAULT_PRIORITY = "balanced"


def load_profiles(path: Optional[str] = None) -> Dict:
    try:
        data = read_json(path or PROFILES_PATH)      # cached by file mtime (core.memo); a broken file is never cached
    except (OSError, ValueError):
        data = {}
    data.setdefault("models", {})
    data.setdefault("priorities", {p: {"label": p, "note": ""} for p in PRIORITIES})
    return data


def api_models(profiles: Optional[Dict] = None) -> Dict[str, Dict]:
    """Models the pipeline can actually send (the web-only ones are shown for information only)."""
    profiles = profiles or load_profiles()
    return {k: v for k, v in profiles["models"].items() if v.get("api")}


def priority_of(project_row) -> str:
    """The project's priority; DEFAULT_PRIORITY for display when it was never chosen (see chosen_priority)."""
    return chosen_priority(project_row) or DEFAULT_PRIORITY


def chosen_priority(project_row) -> Optional[str]:
    """None for a project made before v2 that never chose a priority: it keeps the v1 behaviour (the provider default model)."""
    try:
        value = project_row["model_priority"]
    except (KeyError, IndexError):
        value = None
    return value if value in PRIORITIES else None


def _features(scene_data: Dict, mp_row=None, video_audio: bool = False) -> Dict:
    lines = dialogue.scene_lines(scene_data)
    speakers = {who for who, _ in lines if who}
    return {"complex": scene_data.get("camera_complexity") == "complex",
            "hero": scene_data.get("shot_role") == "hero",
            "transition": scene_data.get("shot_role") == "transition",
            "cast": len(scene_data.get("characters") or []),
            "speakers": len(speakers),
            "ref_video": bool(mp_row is not None and "ref_video_path" in mp_row.keys() and mp_row["ref_video_path"]),
            "native_audio": bool(video_audio)}


def recommend(scene_data: Dict, priority: str, mp_row=None, video_audio: bool = False, look: Optional[str] = None) -> Dict:
    """{"model": alias, "resolution": tier or None, "reason": Vietnamese sentence} for one scene."""
    from .adapters.clipai import SEEDANCE_REFS_WITH_FIRST_FRAME
    f = _features(scene_data, mp_row, video_audio)
    multi_dialogue = f["speakers"] >= 2 and f["cast"] >= 2
    crowd = f["cast"] >= 3
    if look == "FF_INGAME" and not f["ref_video"]:
        # W11: in GĐ6 Seedance blocked in-game-looking people as "real person"/copyright; Kling keeps the Free Fire render and costs least
        return _pick("kling", "look in-game Free Fire — Kling 3.0 Omni giữ đúng kiểu render in-game và ít bị chặn “người thật” hơn Seedance")
    if crowd and not SEEDANCE_REFS_WITH_FIRST_FRAME:
        # K3: every clip starts from a first frame, and Seedance then takes no per-person references — the old reason no longer holds
        crowd = False
        if priority != "quality" and not (f["complex"] or f["hero"] or f["ref_video"]):
            return _pick("kling", "≥3 nhân vật — mọi model chỉ nhận khung đầu (Seedance bỏ ảnh tham chiếu khi có khung đầu): "
                                  "Kling 3.0 Omni rẻ nhất, nhân vật lấy từ khung đầu")
    if priority == "quality":
        if f["ref_video"]:
            return _pick("seedance-2.5", "cần tham chiếu đa phương thức (video chuyển động) — Seedance 2.5 xử lý tham chiếu phức tạp tốt nhất")
        if f["complex"] or f["hero"]:
            return _pick("seedance-2.5", "cảnh " + ("phức tạp" if f["complex"] else "quan trọng") + " — ưu tiên chất lượng: Seedance 2.5 (điện ảnh, chi tiết chất liệu)")
        return _pick("seedance", "ưu tiên chất lượng: Seedance 2.0 ở 1080p", "1080p")
    if priority == "value":
        if f["ref_video"]:
            return _pick("seedance", "có video chuyển động tham chiếu — Seedance 2.0 nhận tham chiếu đa phương thức với giá thấp hơn 2.5")
        if crowd:
            return _pick("seedance-fast", "≥3 nhân vật — Seedance nhận ảnh tham chiếu riêng từng người (giữ nhân vật), bản Fast rẻ hơn")
        if multi_dialogue or f["transition"]:
            return _pick("kling", ("đối thoại nhiều nhân vật" if multi_dialogue else "cảnh chuyển tiếp đơn giản")
                         + " — Kling 3.0 Omni rẻ nhất ($0.08/s)")
        return _pick("seedance-fast", "tiết kiệm: Seedance 2.0 Fast — dòng Seedance 2.0 xếp hạng hiệu quả chi phí cao hơn Kling")
    # balanced
    if f["ref_video"] or (f["complex"] and f["hero"]):
        return _pick("seedance-2.5", "cảnh then chốt / cần tham chiếu phức tạp — dùng Seedance 2.5 cho chất lượng cao nhất")
    if f["complex"] or f["hero"] or crowd:
        why = "cảnh phức tạp" if f["complex"] else "cảnh quan trọng" if f["hero"] else "≥3 nhân vật (Seedance nhận ảnh tham chiếu từng người)"
        return _pick("seedance", f"{why} — Seedance 2.0 cân bằng chất lượng và giá")
    if multi_dialogue:
        return _pick("kling", "đối thoại nhiều nhân vật / tái sử dụng nhân vật — điểm mạnh của Kling 3.0 Omni, lại rẻ nhất")
    if f["transition"]:
        return _pick("seedance-fast", "cảnh chuyển tiếp — Seedance 2.0 Fast đủ dùng, rẻ hơn")
    return _pick("seedance-fast", "cảnh thường — Seedance 2.0 Fast (hiệu quả chi phí tốt theo bảng ClipAI)")


def _pick(alias: str, reason: str, resolution: Optional[str] = None) -> Dict:
    return {"model": alias, "resolution": resolution, "reason": reason}


def price_per_sec(alias: str, resolution: Optional[str] = None, pricing: Optional[Dict] = None) -> Optional[float]:
    """Price from the pricing table (what the cost ledger uses), falling back to the slide's listed price."""
    prof = load_profiles()["models"].get(alias) or {}
    if pricing:
        key = f"{prof.get('canonical', alias)}:{resolution or prof.get('tier', '')}"
        value = (pricing.get("per_video_second") or {}).get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return prof.get("usd_per_sec")


def scene_choice(conn, scene_id: int, project_row=None, mp_row=None) -> Dict:
    """_scene_choice, then the project's cheap test mode (kế hoạch v3: test runs at 720p or lower): Seedance 2.0 / 2.5 become
    2.0 Fast (the variants compared stay on the same price level) and no 1080p tier is asked for."""
    if project_row is None:
        scene = conn.execute("SELECT project_id FROM scenes WHERE id=?", (scene_id,)).fetchone()
        project_row = conn.execute("SELECT * FROM projects WHERE id=?", (scene["project_id"],)).fetchone()
    choice = _scene_choice(conn, scene_id, project_row, mp_row)
    if "test_quality" in project_row.keys() and project_row["test_quality"]:
        choice = {**choice, "resolution": None}
        if choice["model"] in ("seedance", "seedance-2.5"):
            choice.update(model="seedance-fast", reason=choice["reason"] + " (chế độ thử rẻ: dùng bản Fast 720p)")
    return choice


def _scene_choice(conn, scene_id: int, project_row=None, mp_row=None) -> Dict:
    """The model a scene's video will use: person's override > v1 project-wide model > recommendation.
    {"model", "resolution", "reason", "source": "override"|"project"|"auto", "recommended": {...}}"""
    scene = conn.execute("SELECT project_id, data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    project_row = project_row or conn.execute("SELECT * FROM projects WHERE id=?", (scene["project_id"],)).fetchone()
    if mp_row is None:
        mp_row = conn.execute("SELECT * FROM motion_prompts WHERE scene_id=?", (scene_id,)).fetchone()
    data = json.loads(scene["data"] or "{}")
    rec = recommend(data, priority_of(project_row), mp_row, bool(project_row["video_audio"]),
                    look=project_row["look"] if "look" in project_row.keys() else None)
    override = mp_row["video_model"] if mp_row is not None and "video_model" in mp_row.keys() else None
    from . import shots
    if shots.mode(project_row) == "multishot" and data.get("shot_no") and len(shots.multishot_group_of(conn, scene_id) or []) > 1:
        # M9: a shot inside a Kling multi-shot group is made in the group's one Kling request — a per-shot override cannot apply
        return {"model": "kling", "resolution": None, "source": "auto", "recommended": rec,
                "reason": "Kling multi-shot: các shot liền nhau của nhóm được gen chung một lần"
                          + (" (model bạn chọn riêng cho shot này không áp dụng trong nhóm)" if override else "")}
    if override:
        return {"model": override, "resolution": None, "reason": "bạn chọn cho cảnh này", "source": "override", "recommended": rec}
    from . import seedance_refs
    if data.get("shot_no") and seedance_refs.enabled(conn, scene["project_id"]):
        if seedance_refs.eligible(data):
            grouped = len(shots.group_of(conn, scene_id) or []) > 1
            from . import lipsync
            takes = [r["data"] for r in (shots.group_of(conn, scene_id) or [{"data": data}])]
            if lipsync.enabled() and any(lipsync.method_for(d) == "take" for d in takes):
                return {"model": "seedance-2.5", "resolution": "720p", "source": "auto", "recommended": rec,
                        "reason": "khớp môi (c) — S4.2: clip " + ("nhóm" if grouped else "một shot") + " có thoại thấy mặt → Seedance 2.5 "
                                  "kèm track giọng + câu thoại & mốc giây trong prompt (người dùng chọn 29/09, A/B S4.6)"}
            return {"model": "seedance", "resolution": "720p", "source": "auto", "recommended": rec,
                    "reason": ("Seedance chỉ ảnh tham chiếu, gộp với các shot liền (mỗi shot có ảnh storyboard riêng)" if grouped
                               else "Seedance chỉ ảnh tham chiếu, một shot") + " — người dùng chốt ưu tiên Seedance (2026-09-27)"}
        if seedance_refs.face_closeup(data) and seedance_refs.route(data) != "kling":
            return {"model": "kling", "resolution": None, "source": "auto", "recommended": rec,
                    "reason": "shot cận thấy mặt: Kling từ khung đầu = ảnh storyboard đã duyệt, giữ đúng mặt (cờ closeup_start_frame, S4.1)"}
        if seedance_refs.route(data) == "kling":
            return {"model": "kling", "resolution": None, "source": "auto", "recommended": rec,
                    "reason": "Seedance đã từ chối shot này (cả gộp lẫn một shot) → Kling từ khung đầu"}
    from . import lipsync, shots as _sh
    if lipsync.enabled() and data.get("shot_no") and lipsync.voiced(lipsync.method_for(data)) and _sh.mode(project_row) != "multishot":
        # (a Kling multi-shot project stays on Kling: the runner says the shot gets no lip sync instead of silently skipping it)
        return {"model": "seedance", "resolution": "720p", "source": "auto", "recommended": rec,
                "reason": "khớp môi khi tạo: Seedance nhận giọng thoại của shot (reference_audio)"}
    if project_row["video_model"]:
        return {"model": project_row["video_model"], "resolution": None, "reason": "model chung của dự án (cách chọn cũ)",
                "source": "project", "recommended": rec}
    if chosen_priority(project_row) is None:
        return {"model": "kling", "resolution": None, "source": "legacy", "recommended": rec,
                "reason": "dự án cũ chưa chọn ưu tiên model: dùng mặc định cũ (Kling 3.0 Omni) — chọn ưu tiên ở Bước 1 để dùng đề xuất theo cảnh"}
    from . import shots
    mode = shots.mode(project_row)
    if mode == "multishot" and data.get("shot_no"):
        return {"model": "kling", "resolution": None, "source": "auto", "recommended": rec,
                "reason": "Kling multi-shot: các shot liền nhau của nhóm được gen chung một lần"}
    if mode == "per_shot" and data.get("shot_no"):
        group = shots.sequence_rows(conn, scene_id)
        if len(group) > 1 and lipsync.enabled() and any(lipsync.voiced(lipsync.method_for(r["data"])) for r in group):
            # a lip-sync shot must be Seedance (it speaks the voice line) and a continuity group keeps ONE model: the whole group goes
            return {"model": "seedance", "resolution": "720p", "source": "auto", "recommended": rec,
                    "reason": "cả nhóm cảnh dùng Seedance vì có shot khớp môi khi tạo (cắt giữa hai model dễ lộ)"}
        if len(group) > 1:                  # one model for a continuity group: cutting between two models shows
            recs = []
            for r in group:
                mp = conn.execute("SELECT * FROM motion_prompts WHERE scene_id=?", (r["id"],)).fetchone()
                recs.append(recommend(r["data"], priority_of(project_row), mp, bool(project_row["video_audio"])))
            models = [x["model"] for x in recs]
            best = max(dict.fromkeys(models), key=models.count)
            pick = next(x for x in recs if x["model"] == best)
            return {**pick, "source": "auto", "recommended": rec,
                    "reason": pick["reason"] + " — cả nhóm cảnh dùng chung model này (cắt giữa hai model dễ lộ)"}
    return {**rec, "source": "auto", "recommended": rec}


def _remake_runs(conn, group):
    """A Seedance reference group as it will really be sent: whole when none of its shots has a clip; else the consecutive runs of
    shots still WITHOUT a clip (each run one group clip, a lone shot a clip of its own, >= 4 s billed) — #8 2026-09-28 the estimate
    priced 19 remade shots as group clips (6.48 USD) while they went one by one (~0.48 USD each)."""
    def has(sid):
        return bool(conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen' AND state IN "
                                 "('succeeded','approved','pending_review','running')", (sid,)).fetchone())
    made = [has(r["id"]) for r in group]
    if not any(made):
        return [group]
    runs, cur = [], []
    for r, m in zip(group, made):
        if m:
            if cur:
                runs.append(cur)
            cur = []
        else:
            cur.append(r)
    if cur:
        runs.append(cur)
    return runs


def plan(conn, project_id: int, pricing: Optional[Dict] = None, priority: Optional[str] = None) -> List[Dict]:
    """One row per scene with a motion prompt or an approved image: choice, reason, seconds, price. `priority` forces another
    ladder (for the "compare with the other priorities" line) and ignores overrides."""
    proj = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    from . import seedance_refs
    ref_groups = {}                       # scene id -> its Seedance reference group: ONE clip, priced on the group's first shot
    if seedance_refs.enabled(conn, project_id):
        for g in seedance_refs.groups(conn, project_id):
            for part in _remake_runs(conn, g):             # 28/09: a group partly made already is remade in runs (runner._redo_run)
                if len(part) > 1:
                    for r in part:
                        ref_groups[r["id"]] = part
    rows = []
    for s in conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall():
        mp = conn.execute("SELECT * FROM motion_prompts WHERE scene_id=?", (s["id"],)).fetchone()
        data = json.loads(s["data"] or "{}")
        choice = scene_choice(conn, s["id"], proj, mp)
        if priority and choice.get("source") != "override" and not _in_multishot(conn, s["id"], proj, data):
            # M18: another priority ladder changes only the recommendation — a model the person picked for a shot and a Kling
            # multi-shot group (always Kling, one request) stay as they are, as they would in the real run
            choice = {**recommend(data, priority, mp, bool(proj["video_audio"]),
                                  look=proj["look"] if "look" in proj.keys() else None), "source": "auto"}
        seconds = float(mp["duration_sec"]) if mp is not None else float(data.get("duration_s") or 5)
        billed = billed_seconds(choice["model"], math.ceil(seconds - 1e-6) if data.get("shot_no") else seconds)
        group = ref_groups.get(s["id"])
        if group and choice.get("source") != "override":
            if group[0]["id"] == s["id"]:
                secs = []
                for r in group:
                    m = conn.execute("SELECT duration_sec FROM motion_prompts WHERE scene_id=?", (r["id"],)).fetchone()
                    secs.append(seedance_refs.floored(r["data"], float((m["duration_sec"] if m is not None and m["duration_sec"] else None)
                                                                        or r["data"].get("duration_s") or 0)))
                billed = float(seedance_refs.seconds(secs))
            else:
                billed = 0.0                   # made inside the group clip of its first shot
                choice = {**choice, "reason": choice["reason"] + f" (trong clip nhóm của shot {group[0]['idx']})"}
        unit = price_per_sec(choice["model"], choice.get("resolution"), pricing)
        rows.append({"scene_id": s["id"], "idx": s["idx"], **choice, "seconds": seconds, "billed_seconds": billed,
                     "usd_per_sec": unit, "cost": None if unit is None else unit * billed})
    return rows


def _in_multishot(conn, scene_id: int, proj, data: Dict) -> bool:
    from . import shots
    return shots.mode(proj) == "multishot" and bool(data.get("shot_no")) and len(shots.multishot_group_of(conn, scene_id) or []) > 1


def billed_seconds(alias: str, seconds: float) -> float:
    """Seconds the model really makes and charges: a v3 shot shorter than the model's minimum (Kling 3s, Seedance 4s) is made
    at the minimum and cut afterwards."""
    from .adapters.clipai import effective_duration, resolve_model
    try:
        canonical, family = resolve_model(alias)[:2]
    except Exception:  # noqa: BLE001 - unknown / web-only model: price what was asked
        return float(seconds)
    return float(effective_duration(canonical, family, seconds))


def total(rows: List[Dict]) -> Optional[float]:
    costs = [r["cost"] for r in rows]
    return None if any(c is None for c in costs) else sum(costs)


def set_override(conn, scene_id: int, alias: Optional[str]) -> None:
    """The person's own model for one scene (None = back to the recommendation)."""
    if alias and alias not in api_models():
        raise ValueError(f"model '{alias}' không gửi được qua API")
    conn.execute("UPDATE motion_prompts SET video_model=? WHERE scene_id=?", (alias or None, scene_id))
    conn.commit()
