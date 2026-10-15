"""Sân khấu 3D tự động cho mọi dự án (cờ `stage_auto`, mặc định TẮT) — kế hoạch docs/KE_HOACH_NOI_SAN_KHAU_3D_TU_DONG_2026-10-15.md,
người dùng duyệt 15/10 Q1–Q7 (sổ quyết định `stage-auto-plan-2026-10-15`).

Gốc lỗi (#31, 15/10): Sân khấu 3D v2 (K1 lưới → Đạo diễn khai dàn cảnh + yêu cầu khung → K3 giải máy → K4 Blender đo → trường
`stage_camera`) chỉ chạy tay ở #24 (tools/stage_grid.py v3 + tools/experiments/stage_v2_p24/apply_v4.py) — cờ `stage_camera` bật
mà #27–#31 không shot nào có máy sân khấu. Module này nối cùng các khâu đó vào chạy tự động:

- **Một sân khấu = một mô hình 3D** (hoặc một họ mô hình khai `model3d.stage_family` ở Kho, vd phòng 447 cửa đóng + 448 cửa mở):
  chỗ đứng là tọa độ model nên mọi chỗ đứng của một model đã chung khung tọa độ. Họ chưa khai mà bộ chỗ đứng trùng hệt → VÀNG.
- **Mỗi cảnh truyện (story_scene) trên một sân khấu = một đoạn** (Q1: một lượt Đạo diễn mỗi cảnh). Gốc O = chỗ đứng nhiều shot
  nhất của đoạn; K1 cache theo sha model + chỗ đứng. Vị trí CUỐI của người/vật ở đoạn trước cùng sân khấu (tọa độ model) được đưa
  cho Đạo diễn làm vị trí đầu (người + vật giữ chỗ, đổi shot chỉ đổi máy, trừ khi kịch bản cho di chuyển).
- Đầu vào từ Kho + kịch bản (không còn tham số cứng #24): chiều cao = hồ sơ chuẩn `height_m`, đạo cụ = vật Kho của shot
  (place_refs.shot_objects) có `size`. Thiếu → nói rõ, đoạn đó KHÔNG chạy (không mặc định 1,7 m).
- Máy chỉ ở ô đi tới được từ O (stage_solver.reachable_cells — chặn "máy lọt ngoài tường phòng").
- Shot không đạt sau ≤ 2 lượt sửa (stage_director.MAX_ROUNDS) → giữ ở cổng nền 3D (autopilot `_plate_ack`) kèm lý do + lời
  khuyên; "Tiếp tục" = shot đó dùng máy cũ, ghi VÀNG "không theo sân khấu". Không bao giờ âm thầm quay về máy cũ.
- Mọi lời gọi Claude qua sổ chi (llm_runner.tagged) + ước tính nói trước (cost.llm_estimate). Đoạn có shot đã vẽ ảnh → không đổi
  máy (ảnh đã trả tiền sẽ lệch nền) trừ khi `force` (CLI `py tools/stage_auto.py --project N --force --yes`).
"""
import hashlib
import json
import os
import re
from typing import Callable, Dict, List, Optional, Tuple

from . import diag, features

FLAG = "stage_auto"
CODE = "stage_auto"
FIELD = "stage_camera"                 # = plate_camera.STAGE_FIELD
SEG_FIELD = "stage_segment"
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOL = None


def enabled() -> bool:
    return features.on(FLAG)


def tool():
    """tools/stage_grid.py (K1 / K3+K4 Blender) nạp như module — không chạy CLI."""
    global _TOOL
    if _TOOL is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("stage_grid_tool", os.path.join(_ROOT, "tools", "stage_grid.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _TOOL = mod
    return _TOOL


def _say(conn, pid: int, sev: str, msg: str, log: Callable[[str], None]) -> None:
    diag.record(conn, "director", sev, msg, CODE, pid)
    log(msg)


def key_of(name: str) -> str:
    """Khóa vật cho dàn cảnh: chữ thường + số, không dấu, không '_' (stage_solver.beat_raw)."""
    from .assets import fold
    k = re.sub(r"[^a-z0-9]", "", fold(name or "").lower())
    return k or "vat"


# ---- sân khấu + đoạn -------------------------------------------------------------------------------------------------------
def stage_key(place: Dict, entry: Dict) -> str:
    fam = str(entry.get("stage_family") or "").strip()
    return key_of(fam) if fam else f"kho{place['id']}"


def family_hints(segs: List[Dict]) -> List[str]:
    """Hai bối cảnh Kho có bộ chỗ đứng trùng hệt (cùng một phòng, khác trạng thái cửa…) mà chưa khai cùng `stage_family` → VÀNG,
    KHÔNG tự gộp (người khai ở Kho)."""
    seen: Dict[str, Tuple[str, str]] = {}
    out = []
    for g in segs:
        sig = json.dumps(g["entry"].get("spots") or {}, sort_keys=True)
        prev = seen.get(sig)
        if prev and prev[0] != g["stage"]:
            msg = (f"Kho #{prev[1]} và #{g['place']['id']} có bộ chỗ đứng trùng hệt nhưng là hai sân khấu khác nhau — nếu là cùng một "
                   "nơi (vd cùng phòng, khác trạng thái cửa) hãy khai `stage_family` giống nhau cho model 3D ở Kho")
            if msg not in out:
                out.append(msg)
        seen.setdefault(sig, (g["stage"], str(g["place"]["id"])))
    return out


def segments(conn, pid: int) -> List[Dict]:
    """[{id, scene, stage, place, entry, shots, spots {tên: [idx]}, main_spot}] — một đoạn mỗi (cảnh truyện, sân khấu), theo thứ tự
    phim (shot đầu của đoạn)."""
    from . import location_pack
    out: Dict[Tuple[str, str], Dict] = {}
    for s in location_pack.shots_at_3d_places(conn, pid):
        scene = s["data"].get("story_scene")
        scene = str(scene) if scene not in (None, "") else f"shot{s['idx']}"
        st = stage_key(s["place"], s["entry"])
        g = out.setdefault((scene, st), {"id": f"{scene}@{st}", "scene": scene, "stage": st, "place": s["place"], "entry": s["entry"],
                                         "shots": [], "spots": {}})
        g["shots"].append(s)
        g["spots"].setdefault(location_pack.spot_for(s["entry"], s["data"]).get("name"), []).append(s["idx"])
    res = sorted(out.values(), key=lambda g: min(s["idx"] for s in g["shots"]))
    for g in res:
        g["shots"].sort(key=lambda s: s["idx"])
        g["main_spot"] = max(g["spots"], key=lambda n: (len(g["spots"][n]), -min(g["spots"][n])))
    return res


def base_dir(data_dir: str, pid: int, stage: str) -> str:
    return os.path.join(data_dir, str(pid), "stage", stage)


def ensure_k1(entry: Dict, spot: str, base: str, log: Callable[[str], None] = lambda m: None) -> str:
    """K1 của chỗ đứng (0 USD, Blender ≈ 20 s), cache theo sha model + tọa độ chỗ đứng. Lỗi = ValueError / BlenderError."""
    out = os.path.join(base, f"k1_{key_of(spot)}")
    want = {"sha256": entry.get("sha256"), "path": entry.get("path"), "at": (entry.get("spots") or {}).get(spot, {}).get("at")}
    mark = os.path.join(out, "k1_key.json")
    if os.path.exists(os.path.join(out, "stage.json")) and os.path.exists(mark):
        try:
            with open(mark, encoding="utf-8") as f:
                if json.load(f) == want:
                    return out
        except (OSError, ValueError):
            pass
    log(f"Sân khấu: đo sàn K1 chỗ đứng '{spot}' (Blender, 0 USD)")
    tool().k1_run(entry, spot, out)
    with open(mark, "w", encoding="utf-8") as f:
        json.dump(want, f, ensure_ascii=False)
    return out


def _rel(stage: Dict, model_xyz) -> List[float]:
    o = stage["origin_model"]
    return [round(float(model_xyz[k]) - o[k], 3) for k in range(3)]


def _model(stage: Dict, rel_xyz) -> List[float]:
    o = stage["origin_model"]
    return [round(o[k] + float(rel_xyz[k] if k < len(rel_xyz) else 0.0), 3) for k in range(3)]


def inputs_for(conn, pid: int, seg: Dict, k1_dir: str, prev_state: Optional[Dict] = None) -> Tuple[Dict, List[str]]:
    """Đề bài prompt 29 cho một đoạn, lấy từ Kho + kịch bản (CSDL chỉ đọc, 0 USD). Trả (inputs, thiếu) — thiếu khác rỗng thì KHÔNG
    gọi Đạo diễn (luật 1 CHUAN_XAY_DUNG: không bịa chiều cao / kích thước)."""
    from . import assets, formats, place_refs
    with open(os.path.join(k1_dir, "stage.json"), encoding="utf-8") as f:
        st = json.load(f)
    with open(os.path.join(k1_dir, "grid.json"), encoding="utf-8") as f:
        grid = json.load(f)["cells"]
    missing: List[str] = []
    people, fixed, keys = [], [], set()
    names: List[str] = []
    for s in seg["shots"]:
        for n in s["data"].get("characters") or []:
            if isinstance(n, str) and n not in names:
                names.append(n)
    for n in names:
        prof = assets.standard_for(conn, pid, n)
        k = key_of(n)
        while k in keys:
            k += "x"
        keys.add(k)
        if not prof or not prof.get("height_m"):
            missing.append(f"chiều cao nhân vật {n} (Kho → hồ sơ chuẩn `height_m`, đã duyệt)")
            continue
        people.append({"key": k, "label": n, "H": float(prof["height_m"])})
    objs: Dict[int, Dict] = {}
    for s in seg["shots"]:
        for a in place_refs.shot_objects(conn, pid, s["data"]):
            objs.setdefault(a["id"], a)
    for a in objs.values():
        size = a.get("size") or {}
        h = size.get("height_m")
        d = size.get("width_m") or size.get("depth_m") or size.get("length_m")
        if not h or not d:
            missing.append(f"kích thước đạo cụ {a.get('name')} (Kho #{a.get('id')}: cần cao + rộng, m)")
            continue
        k = key_of(a.get("name"))
        while k in keys:
            k += "x"
        keys.add(k)
        fixed.append({"key": k, "kind": "dao_cu", "label": a.get("name"), "h": round(float(h), 3), "d": round(float(d), 3),
                      "source": f"Kho #{a.get('id')} size"})
    marks = st.get("marks") or {}
    if "thap_chan" in marks:
        fixed.append({"key": "moc", "kind": "moc", "from_marks": "thap",
                      "label": f"mốc bản đồ ({(marks.get('thap_object') or {}).get('name') or 'anchor'})"})
    notes = []
    if any(o["kind"] == "dao_cu" for o in fixed):
        notes.append("Đạo cụ không ghi `at`: bạn đặt vị trí theo kịch bản, GIỮ nguyên h / d / kind.")
    main = seg["main_spot"]
    for name, sp in (seg["entry"].get("spots") or {}).items():
        if name != main and sp.get("at"):
            r = _rel(st, sp["at"])
            used = seg["spots"].get(name)
            notes.append(f"Chỗ đứng khác trên CÙNG sân khấu: `{name}` tại ({r[0]:+.2f} Đ, {r[1]:+.2f} B, cao {r[2]:+.2f} m) so với O"
                         + (f" — shot {', '.join(map(str, used))} của cảnh này đứng ở đó" if used else ""))
    if prev_state:
        for k, o in prev_state.get("objects", {}).items():
            r = _rel(st, o["at_model"])
            facing = "" if o.get("facing") is None else f", hướng {o['facing']}°"
            pose = f", {o['tu_the']}" if o.get("tu_the") else ""
            notes.append(f"Vị trí CUỐI ở cảnh trước trên cùng sân khấu (cảnh {prev_state.get('scene')}): `{k}` tại ({r[0]:+.2f}, "
                         f"{r[1]:+.2f}){facing}{pose} — GIỮ chỗ này trừ khi kịch bản cho di chuyển (ghi beat + _ly_do)")
    shots = []
    for s in seg["shots"]:
        d = s["data"]
        old = "; ".join(x for x in (d.get("blocking"), " ".join(str(d.get(k) or "") for k in ("size", "angle", "camera_move")).strip(),
                                    d.get("end_state")) if x)
        shots.append({"shot": s["idx"], "action": d.get("action") or d.get("text") or "", "ghi_chu_khung_cu": old,
                      "do_dai": f"{d.get('duration_s')} s" if d.get("duration_s") else ""})
    aspect = formats.project_aspect(conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()) or "9:16"
    inputs = {"pid": pid, "canh": f"cảnh {seg['scene']} — {seg['place'].get('name')} ({len(seg['shots'])} shot)",
              "place": seg["place"]["id"], "spot": main, "aspect": aspect, "fixed": fixed, "people": people,
              "shots": shots, "floor": tool()._floor_notes(grid), "user_notes": notes}
    return inputs, missing


# ---- kết quả → máy của shot -----------------------------------------------------------------------------------------------
def cameras_from(stage: Dict, v2: Dict, seg_id: str, rd: str) -> Tuple[Dict[int, Dict], Dict[int, str]]:
    """v2.json → ({shot: stage_camera (tọa độ model)}, {shot: lý do hỏng}). Như apply_v4.stage_cameras (#24) + khối đạo cụ chung
    + ảnh hướng dẫn người nộm (clay K4, Q2)."""
    cams, bad = {}, {}
    for s in v2.get("shots", []):
        b = s.get("best")
        if not b or not b.get("ok"):
            why = "không có phương án máy" if not b else "; ".join(f"{k}: {v}" for k, v in b["check"]["why"].items())
            bad[s["shot"]] = why
            continue
        m, sp = b["m"], s["spec"]
        cam = {"location": [round(v, 3) for v in _model(stage, m["at"])], "look_at": [round(v, 3) for v in _model(stage, m["aim"])],
               "lens": m["lens"], "source": f"Sân khấu 3D tự động {seg_id} shot {s['shot']} ({b['tag']})", "cell": m.get("cell"),
               "auto": True, "segment": seg_id}
        props = []
        for o in (s.get("objs") or {}).values():
            if o.get("kind") != "dao_cu":
                continue
            at = _model(stage, [o["xy"][0], o["xy"][1], o.get("z", 0.0)])
            if o.get("shape") == "gieng":
                props.append({"kind": "well", "at": at, "radius": o["r"], "height": o["h"], "hollow": bool(o.get("hollow")), "sides": 8,
                              "tone": "da_toi"})
            else:
                props.append({"kind": "block", "shape": "cylinder", "at": at, "size": [2 * o["r"], 2 * o["r"], o["h"]],
                              "rotation_deg": 0, "label": o.get("label") or o.get("key"), "source": o.get("source") or "dàn cảnh"})
        if props:
            cam["props"] = props
        if b.get("clay"):
            cam["guide"] = os.path.join(rd, b["clay"])
        if sp.get("pov"):
            cam["pov"] = sp["pov"]
        if sp.get("may") and b.get("end"):
            e = b["end"]["m"]
            cam["move"] = {"kieu": sp["may"]["kieu"], "m": sp["may"]["m"], "rung": sp["may"].get("rung"),
                           "end_location": [round(v, 3) for v in _model(stage, e["at"])],
                           "end_look_at": [round(v, 3) for v in _model(stage, e["aim"])]}
        cams[s["shot"]] = cam
    return cams, bad


def end_state(stage: Dict, answer: Dict, scene: str) -> Dict:
    """Vị trí cuối (nhịp của shot cuối) của mọi người/đạo cụ, tọa độ MODEL — đầu vào của đoạn sau cùng sân khấu."""
    from . import stage_solver as ss
    bl = answer["blocking"]
    last = sorted(answer["shot_specs"], key=lambda s: s["shot"])[-1] if answer.get("shot_specs") else {}
    raw = ss.beat_raw(bl, last.get("nhip")) if last.get("nhip") else ss.beat_raw(bl)
    out = {}
    for k, o in raw.items():
        if o.get("kind") == "moc" or not o.get("at"):
            continue
        out[k] = {"at_model": _model(stage, [o["at"][0], o["at"][1], o.get("z", 0.0)]), "facing": o.get("facing"),
                  "tu_the": o.get("tu_the"), "kind": o.get("kind")}
    return {"scene": scene, "objects": out}


def apply(conn, seg: Dict, cams: Dict[int, Dict]) -> List[int]:
    """Ghi `stage_camera` vào shot (máy hệ thống, không khóa tay). Shot người dùng khóa `stage_camera` → giữ. Máy tự động cũ của shot
    nay không đạt → gỡ (máy cũ của nó lệch đầu vào mới — nền 3D về máy thường, có VÀNG)."""
    changed = []
    for s in seg["shots"]:
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (s["id"],)).fetchone()
        data = json.loads(row["data"] or "{}")
        if FIELD in (data.get("_user_locked") or []):
            continue
        new = cams.get(s["idx"])
        old = data.get(FIELD)
        if new is None and not (isinstance(old, dict) and old.get("auto")):
            continue
        if new == old:
            continue
        if new is None:
            data.pop(FIELD, None)
            data.pop(SEG_FIELD, None)
        else:
            data[FIELD], data[SEG_FIELD] = new, seg["id"]
        conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), s["id"]))
        s["data"] = data
        changed.append(s["idx"])
    if changed:
        conn.commit()
    return changed


# ---- một đoạn ------------------------------------------------------------------------------------------------------------
def _estimate(conn, calls: int) -> str:
    from . import cost
    from .stage_director import STAGE
    try:
        usd = cost.llm_estimate(conn, STAGE, calls)
    except Exception:  # noqa: BLE001 - bảng giá lỗi: nói, không dừng
        usd = None
    return f"≈ {usd * cost.LLM_MARGIN:.3f} USD" if usd is not None else "chưa có giá Claude"


def fingerprint(inputs: Dict) -> str:
    return hashlib.sha1(json.dumps(inputs, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def run_segment(conn, pid: int, seg: Dict, data_dir: str, client, prev_state: Optional[Dict] = None,
                log: Callable[[str], None] = lambda m: None) -> Dict:
    """K1 → đề bài → Đạo diễn (≤ MAX_ROUNDS lượt, sổ chi) → K3 + K4 → máy từng shot. Không ghi CSDL (apply làm việc đó).
    Trả {"cams", "bad" {shot: lý do}, "missing" [..], "state", "reused"}; kết quả lưu <data_dir>/<pid>/stage/<sân khấu>/<đoạn>/
    result.json theo vân tay đầu vào — chạy lại cùng đầu vào không gọi Claude lần nữa."""
    from . import llm_runner
    from . import stage_director as sd
    base = base_dir(data_dir, pid, seg["stage"])
    res: Dict = {"cams": {}, "bad": {}, "missing": [], "state": None, "reused": False}
    try:
        k1 = ensure_k1(seg["entry"], seg["main_spot"], base, log)
    except Exception as e:  # noqa: BLE001 - Blender / model 3D: nói rõ, đoạn không chạy
        res["missing"].append(f"không đo được sân khấu K1 chỗ đứng '{seg['main_spot']}': {type(e).__name__}: {e}")
        return res
    inputs, missing = inputs_for(conn, pid, seg, k1, prev_state)
    if missing:
        res["missing"] = missing
        return res
    with open(os.path.join(k1, "stage.json"), encoding="utf-8") as f:
        st = json.load(f)
    fp = fingerprint(inputs)
    out = os.path.join(base, f"doan_{key_of(seg['scene'])}")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "result.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                old = json.load(f)
            if old.get("fp") == fp:
                return dict(old, cams={int(k): v for k, v in old["cams"].items()}, bad={int(k): v for k, v in old["bad"].items()},
                            reused=True)
        except (OSError, ValueError, KeyError):
            pass
    if client is None:
        res["missing"].append("chưa cấu hình Claude (ANTHROPIC_API_KEY / LLM_PROVIDER) — Đạo diễn chưa dàn cảnh")
        return res
    _say(conn, pid, "info", f"Sân khấu {seg['id']}: Đạo diễn dàn cảnh + yêu cầu khung {len(seg['shots'])} shot — ước tính "
                            f"{_estimate(conn, 1)} (tối đa {2 * sd.MAX_ROUNDS} lời gọi {_estimate(conn, 2 * sd.MAX_ROUNDS)})", log)
    with open(os.path.join(out, "inputs.json"), "w", encoding="utf-8") as f:
        json.dump(inputs, f, ensure_ascii=False, indent=1)
    prev, feedback, obj, v2, rd = None, [], None, None, out
    for rnd in range(1, sd.MAX_ROUNDS + 1):
        text = sd.build_prompt(inputs, prev, feedback)
        with llm_runner.tagged(sd.STAGE, pid):
            obj, tin, tout = llm_runner.ask_json(client, text, lambda o: sd.validate_answer(o, inputs, st.get("marks")),
                                                 note=log)
        if obj.get("can_hoi"):
            _say(conn, pid, "warn", f"Sân khấu {seg['id']}: Đạo diễn hỏi — {obj['can_hoi']}", log)
        bl = dict(obj["blocking"], place=inputs["place"], spot=inputs["spot"], aspect=inputs["aspect"])
        rd = os.path.join(out, f"r{rnd}")
        os.makedirs(rd, exist_ok=True)
        for fn, data in (("answer.json", obj), ("blocking.json", bl), ("shot_specs.json", {"shots": obj["shot_specs"]})):
            with open(os.path.join(rd, fn), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
        try:
            solve, v2 = tool().v2_run(bl, obj["shot_specs"], rd, k1, m3=seg["entry"], reach=True, log=log)
        except Exception as e:  # noqa: BLE001 - Blender đo lỗi: nói rõ, không gán máy chưa đo
            res["missing"].append(f"không đo được máy bằng Blender (K4): {type(e).__name__}: {e}")
            return res
        feedback = sd.feedback_from(solve, v2)
        log(f"Sân khấu {seg['id']} lượt {rnd}: vào {tin} / ra {tout} token, {len(feedback)} shot cần sửa")
        if not feedback:
            break
        prev = obj
    cams, bad = cameras_from(st, v2 or {}, seg["id"], rd)
    for s in seg["shots"]:
        if s["idx"] not in cams and s["idx"] not in bad:
            bad[s["idx"]] = "bộ giải không đặt được máy (lỗi yêu cầu khung)"
    advice = {int(x.split(":", 1)[0].replace("shot", "").strip()): x for x in feedback if x.startswith("shot ")} if feedback else {}
    res.update(cams=cams, bad={k: advice.get(k, v) for k, v in bad.items()}, state=end_state(st, obj, seg["scene"]), fp=fp)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in res.items() if k != "reused"}, f, ensure_ascii=False, indent=1)
    return res


# ---- cả dự án ------------------------------------------------------------------------------------------------------------
def run(conn, pid: int, data_dir: str, client=None, force: bool = False, log: Callable[[str], None] = lambda m: None) -> Optional[Dict]:
    """Mọi đoạn của dự án, nối tiếp theo sân khấu (vị trí cuối đoạn trước → đầu đoạn sau). None khi cờ TẮT (không làm gì).
    Trả {"applied": [idx], "held": [(vân tay, câu)], "skipped": [đoạn]}: `held` = shot không đạt / đoạn thiếu đầu vào — autopilot
    giữ ở cổng nền 3D cho người xem (Tiếp tục = các shot đó dùng máy thường, VÀNG)."""
    if not enabled():
        return None
    from .camera_plan import drawn_shots
    segs = segments(conn, pid)
    out: Dict = {"applied": [], "held": [], "skipped": []}
    for h in family_hints(segs):
        _say(conn, pid, "warn", h, log)
    state: Dict[str, Dict] = {}
    for seg in segs:
        done = drawn_shots(conn, seg)
        if done and not force:
            out["skipped"].append(seg["id"])
            if any(not s["data"].get(FIELD) for s in seg["shots"]):
                _say(conn, pid, "warn", f"Sân khấu {seg['id']}: shot {', '.join(map(str, done))} đã có ảnh — không đổi máy (ảnh đã vẽ "
                                        f"sẽ lệch nền 3D); muốn dàn lại cả cảnh: py tools/stage_auto.py --project {pid} --force --yes", log)
            continue
        r = run_segment(conn, pid, seg, data_dir, client, state.get(seg["stage"]), log)
        if r["missing"]:
            line = f"sân khấu {seg['id']} chưa chạy — thiếu: " + "; ".join(r["missing"])
            _say(conn, pid, "warn", line, log)
            out["held"].append(("stageauto:" + hashlib.sha1(line.encode("utf-8")).hexdigest()[:12], line))
            continue
        if r.get("state"):
            state[seg["stage"]] = r["state"]
        out["applied"] += apply(conn, seg, r["cams"])
        for idx, why in sorted(r["bad"].items()):
            line = (f"shot {idx} ({seg['id']}): sân khấu chưa đặt được máy sau {2} lượt sửa — {why} (sửa yêu cầu khung / chỗ đứng, hoặc "
                    "Tiếp tục = shot dùng máy thường, không theo sân khấu)")
            _say(conn, pid, "warn", line, log)
            out["held"].append(("stageauto:" + hashlib.sha1(line.encode("utf-8")).hexdigest()[:12], line))
    return out


def estimate(conn, pid: int, data_dir: str, force: bool = False) -> Dict:
    """Ước tính Claude (không gọi): số đoạn sẽ chạy × một lượt, xấu nhất × 2·MAX_ROUNDS. 0 USD."""
    from . import cost
    from .camera_plan import drawn_shots
    from .stage_director import MAX_ROUNDS, STAGE
    segs = [g for g in segments(conn, pid) if force or not drawn_shots(conn, g)]
    one = cost.llm_estimate(conn, STAGE, 1)
    n = len(segs)
    return {"segments": [g["id"] for g in segs], "shots": sum(len(g["shots"]) for g in segs),
            "usd": None if one is None else round(one * cost.LLM_MARGIN * n, 3),
            "usd_max": None if one is None else round(one * cost.LLM_MARGIN * n * 2 * MAX_ROUNDS, 3)}
