"""MỘT nguồn sự thật bố cục của một shot (người dùng 22/10: "giữ mối liên kết chặt chẽ" giữa C-3D-GOC-A / C-3D-GOC-B / C-QC-BOCUC).

Hợp đồng: docs/CLOUD_TASKS.md mục "LIÊN KẾT C-3D-GOC-A / C-3D-GOC-B / C-QC-BOCUC". Chỉ đọc, 0 USD, không gọi model / Blender.
Người đọc (QC qc_spec, kiểm bố cục layout_audit, câu tả nền R3) đọc ở đây — không tự tính lại; gói 3D điền thêm trường VÀO hàm này,
không viết hàm song song. Đổi khóa / kiểu = tăng VERSION + sửa tests/test_layout_facts.py + báo hộp thư.

    facts_for_shot(conn, pid, scene_id, data_dir, data=None) -> {
      version, scene_id, story_scene, spot, mates [scene_id], anchor_scene_id, ref_scene_id,
      camera {source: stage_camera|camera_plan|plate|none, pos, aim, yaw_deg, pitch_deg, lens_mm, height_m, setup, angle, size},
      people [{name, side: left|center|right|unknown, source, height_pct, dist_m}],
      landmarks [{name, in_frame, side, in_pct, size_pct, source}],
      positions {entity: [x, y]},
      horizon {plate_row, image_row, mismatch, measured, reasons, job_id},
      missing [lý do tiếng Việt], provenance {trường: nguồn}}

v1 (cloud-claude, 22/10) chỉ lấy từ dữ liệu sẵn có: nhóm / chỗ đứng (scene_storyboard), máy (stage_camera / camera_plan / plate_view),
bên trái-phải của người theo chữ blocking (cùng cách đọc mệnh đề layout của Tổ QC trước đây), mốc trong khung (stage_facts, khi có máy
3D), chân trời (stage_facts + plate_layout.json). Còn trống, có lý do trong `missing`: số đo người (R2), mốc theo tầm nhìn máy khi
không có máy 3D (R3). positions (R1, C-3D-GOC-B) đọc bản đồ cảnh core/world_map.
"""
import json
import math
import re
from typing import Dict, List, Optional

VERSION = 1
SAME_VIEW_YAW_DEG = 60.0     # hai máy 3D lệch hướng ≤ 60° coi là cùng phía trục (giữ trái/phải); ngưỡng đầu, chưa hiệu chỉnh
_SIDE_WORD = {"left": "left", "right": "right", "center": "center", "centre": "center"}


def blocking_side_match(blocking: str, name: str):
    """Câu blocking đặt `name` ở frame-left/right/center — MỘT cách đọc cho cả Tổ QC (qc_spec mệnh đề layout) và layout_facts."""
    return re.search(rf"\b{re.escape(name)}\b[^,;.]*?\bframe[- ](left|right|center|centre)\b", str(blocking or ""), re.I)


def side_in_blocking(blocking: str, name: str) -> Optional[str]:
    """'left' / 'right' / 'center' khi chữ blocking đặt `name` ở frame-left/right/center."""
    m = blocking_side_match(blocking, name)
    return _SIDE_WORD[m.group(1).lower()] if m else None


def _stage(data: Dict) -> Optional[Dict]:
    """Máy Sân khấu 3D của shot — CHỈ khi cờ stage_camera bật (như ảnh / QC dùng nó); cờ tắt thì toạ độ cũ còn trong data không được
    tính (rà 22/10: yaw của máy không dùng khi vẽ sẽ cho 'cùng phía trục' sai)."""
    from . import features, stage_facts
    return stage_facts.stage_of(data) if features.on("stage_camera") else None


def _row(conn, scene_id: int) -> Optional[Dict]:
    r = conn.execute("SELECT id, idx, data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    return None if r is None else {"id": r["id"], "idx": r["idx"], "data": json.loads(r["data"] or "{}")}


def _camera(data: Dict, missing: List[str], prov: Dict) -> Dict:
    from . import stage_facts
    st = _stage(data)
    if st is not None:
        dx, dy, dz = (st["aim"][i] - st["cam"][i] for i in range(3))
        h = stage_facts.horizon(st["cam"], st["aim"], st["lens"])
        prov["camera"] = "stage_camera"
        return {"source": "stage_camera", "pos": list(st["cam"]), "aim": list(st["aim"]),
                "yaw_deg": round(math.degrees(math.atan2(dy, dx)), 1), "pitch_deg": h["pitch_deg"], "lens_mm": st["lens"],
                "height_m": st["cam"][2], "setup": data.get("camera_setup") or data.get("plate_setup") or None,
                "angle": data.get("angle"), "size": data.get("size")}
    setup = data.get("camera_setup") or data.get("plate_setup")
    base = {"pos": None, "aim": None, "yaw_deg": None, "pitch_deg": None, "height_m": None, "lens_mm": data.get("lens_mm"),
            "setup": setup or None, "angle": data.get("angle"), "size": data.get("size")}
    if setup:
        prov["camera"] = "camera_plan"
        missing.append("máy chưa giải trên sân khấu 3D (chỉ có tên góc máy sơ đồ) — chưa có toạ độ / hướng / độ cao đo được")
        return dict(base, source="camera_plan")
    if data.get("plate_view"):
        prov["camera"] = "plate"
        missing.append("chỉ có hướng nhìn nền (plate_view), chưa có máy 3D / góc máy sơ đồ")
        return dict(base, source="plate")
    prov["camera"] = "none"
    missing.append("shot chưa có máy (không stage_camera, camera_setup, plate_view)")
    return dict(base, source="none")


def _landmarks(data: Dict, missing: List[str], prov: Dict) -> List[Dict]:
    from . import stage_facts
    if _stage(data) is None:
        missing.append("chưa biết mốc nào trong khung: shot không có máy 3D đang dùng (cờ stage_camera / stage_camera) — R3")
        return []
    res = stage_facts.derive(data, render=False)
    if res.get("missing"):
        missing.append(f"không tính được mốc trong khung: {res['missing']}")
        return []
    side = {"left_third": "left", "middle_third": "center", "right_third": "right"}
    prov["landmarks"] = "stage_facts.in_frame"
    return [{"name": f.get("name") or f["subject"], "in_frame": bool(f.get("in_frame")), "side": side.get(f["value"]),
             "in_pct": f["numbers"].get("in_pct"), "size_pct": f["numbers"].get("size_pct"), "source": "stage_facts"}
            for f in res["facts"] if f["kind"] == "in_frame"]


def _horizon(conn, data_dir: str, pid: int, scene_id: int, data: Dict, prov: Dict) -> Dict:
    from . import plate_layout_qc, stage_facts
    out = {"plate_row": None, "image_row": None, "mismatch": None, "measured": False, "reasons": [], "job_id": None}
    st = _stage(data)
    if st is not None:
        out["plate_row"] = stage_facts.horizon(st["cam"], st["aim"], st["lens"])["w"]
        prov["horizon.plate_row"] = "stage_facts.horizon"
    try:
        with open(plate_layout_qc.record_path(data_dir, pid), encoding="utf-8") as f:
            rows = [r for r in json.load(f) if r.get("scene_id") == scene_id]
    except (OSError, ValueError, TypeError):
        rows = []
    if rows:
        r = max(rows, key=lambda x: x.get("job_id") or 0)
        out.update(image_row=r.get("horizon_image"), mismatch=bool(r.get("mismatch")), measured=bool(r.get("measured", True)),
                   reasons=list(r.get("reasons") or []), job_id=r.get("job_id"))
        if out["plate_row"] is None:
            out["plate_row"] = r.get("horizon_plate")
        prov["horizon.image_row"] = "plate_layout.json"
    return out


def _positions(data_dir: str, pid: int, data: Dict, missing: List[str], prov: Dict, shot_idx=None) -> Dict:
    """R1 (C-3D-GOC-B): toạ độ mặt sàn {thực thể: [x, y]} ở shot này từ bản đồ cảnh core/world_map — NGUỒN DUY NHẤT của vị trí xuyên shot
    (cùng map mà câu vị trí M3.3 và bất biến core/position_invariants đọc). Không có map còn hiệu lực / map tương đối → {} + lý do."""
    from . import world_map
    sc = data.get("story_scene")
    try:
        m = world_map.load(data_dir, pid, sc) if sc is not None else None
    except (OSError, ValueError, TypeError) as e:          # map hỏng: nói, không làm sập QC / kiểm bố cục
        missing.append(f"không đọc được bản đồ cảnh ({type(e).__name__}) — vị trí xuyên shot chưa có (R1)")
        return {}
    if not m:
        missing.append("cảnh chưa có bản đồ (world_map) — vị trí xuyên shot chỉ còn trong chữ (R1)")
        return {}
    if m.get("invalidated") or m.get("kind") not in ("3d", "2d"):
        why = "đã cũ" if m.get("invalidated") else f"loại {m.get('kind')} (không có toạ độ)"
        missing.append(f"bản đồ cảnh {why} — không có toạ độ vật / người (R1)")
        return {}
    # valid_from / valid_to của map theo shot_specs 'shot' = scenes.idx (số chung cả dự án, stage_auto), KHÔNG phải shot_no trong cảnh
    out, bad = {}, 0
    for e in world_map.entities_at(m, shot_idx):
        try:
            out[str(e["entity_id"])] = [round(float(v), 3) for v in e["transform"]["xyz"][:2]]
        except (KeyError, TypeError, ValueError):
            bad += 1
    if bad:
        missing.append(f"{bad} thực thể của bản đồ cảnh thiếu / sai toạ độ — bỏ qua (R1)")
    prov["positions"] = f"world_map r{m.get('map_revision')} ({m.get('kind')})"
    return out


def facts_for_shot(conn, pid: int, scene_id: int, data_dir: str, data: Optional[Dict] = None) -> Dict:
    from . import scene_storyboard
    missing: List[str] = []
    prov: Dict[str, str] = {}
    row = _row(conn, scene_id)
    if data is None:
        data = (row or {}).get("data") or {}
    spot = data.get("plate_spot") if isinstance(data.get("plate_spot"), str) and data.get("plate_spot").strip() else None
    if spot is None:
        missing.append("shot không khai chỗ đứng (plate_spot)")
    g = None
    try:
        g = scene_storyboard.group_of(conn, pid, scene_id)
    except Exception as e:  # noqa: BLE001 - nhóm không tính được: nói, không đoán
        missing.append(f"không tính được nhóm cảnh ({type(e).__name__}: {e})")
    mates = [m["id"] for m in scene_storyboard.spot_mates(g, scene_id)] if g else []
    anchor = g["anchor"]["id"] if g and scene_storyboard.uses_anchor(g, scene_id) else None
    ref = None
    if g and mates:                              # shot tham chiếu bố cục cùng chỗ: rộng nhất trong (bạn cùng chỗ + chính shot)
        same = [s for s in g["shots"] if s["id"] in mates or s["id"] == scene_id]
        best = scene_storyboard.anchor_of(same)
        ref = best["id"] if best and best["id"] != scene_id else None
    prov["group"] = "scene_storyboard.group_of"
    cast = [str(c).upper() for c in data.get("characters") or []]
    people = []
    for name in cast:
        side = side_in_blocking(data.get("blocking"), name)
        people.append({"name": name, "side": side or "unknown", "source": "blocking" if side else None,
                       "height_pct": None, "dist_m": None})
    if cast:
        missing.append("chưa có số đo người (cỡ % khung / khoảng cách tới máy) — R2 C-3D-GOC-A điền")
    camera = _camera(data, missing, prov)
    landmarks = _landmarks(data, missing, prov)
    positions = _positions(data_dir, pid, data, missing, prov, shot_idx=(row or {}).get("idx"))
    return {"version": VERSION, "scene_id": scene_id, "story_scene": data.get("story_scene"), "spot": spot, "mates": mates,
            "anchor_scene_id": anchor, "ref_scene_id": ref, "camera": camera, "people": people, "landmarks": landmarks,
            "positions": positions, "horizon": _horizon(conn, data_dir, pid, scene_id, data, prov),
            "missing": missing, "provenance": prov}


def same_view(a: Dict, b: Dict) -> Optional[bool]:
    """Hai shot nhìn cùng phía trục (bên trái/phải của người giữ nguyên)? True / False / None = không biết (không đoán).
    Hai máy 3D: hướng lệch ≤ SAME_VIEW_YAW_DEG. Không có máy 3D: cùng tên góc máy sơ đồ (camera_setup) = cùng máy."""
    ca, cb = a.get("camera") or {}, b.get("camera") or {}
    if ca.get("yaw_deg") is not None and cb.get("yaw_deg") is not None:
        d = abs((ca["yaw_deg"] - cb["yaw_deg"] + 180) % 360 - 180)
        return d <= SAME_VIEW_YAW_DEG
    if ca.get("setup") and cb.get("setup"):
        return True if ca["setup"] == cb["setup"] else None
    return None


def expected_side(conn, pid: int, scene_id: int, data_dir: str, name: str, mine: Optional[Dict] = None) -> Dict:
    """Bên khung mong đợi của `name` theo shot tham chiếu CÙNG CHỖ: {"side", "ref_scene_id", "why"} — side None khi không suy ra được
    (why nói vì sao). Chỉ khi shot này không tự khai bên, shot tham chiếu có khai, và hai máy cùng phía trục."""
    mine = mine or facts_for_shot(conn, pid, scene_id, data_dir)
    own = next((p for p in mine["people"] if p["name"] == name), None)
    if own and own["side"] != "unknown":
        return {"side": own["side"], "ref_scene_id": None, "why": "shot tự khai trong blocking"}
    if not mine["ref_scene_id"]:
        return {"side": None, "ref_scene_id": None, "why": "không có shot cùng chỗ rộng hơn làm tham chiếu"}
    ref = facts_for_shot(conn, pid, mine["ref_scene_id"], data_dir)
    theirs = next((p for p in ref["people"] if p["name"] == name), None)
    if not theirs or theirs["side"] == "unknown":
        return {"side": None, "ref_scene_id": ref["scene_id"], "why": f"shot tham chiếu không khai bên của {name}"}
    sv = same_view(mine, ref)
    if sv is not True:
        return {"side": None, "ref_scene_id": ref["scene_id"],
                "why": "hai máy ngược phía trục — bên trái/phải đổi" if sv is False else "không biết hai máy có cùng phía trục không"}
    return {"side": theirs["side"], "ref_scene_id": ref["scene_id"], "why": "theo shot cùng chỗ, cùng phía trục"}


def scene_of_job(conn, job_id: int) -> Optional[int]:
    if conn is None or job_id is None:
        return None
    r = conn.execute("SELECT scene_id FROM jobs WHERE id=?", (job_id,)).fetchone()
    return None if r is None else r["scene_id"]

