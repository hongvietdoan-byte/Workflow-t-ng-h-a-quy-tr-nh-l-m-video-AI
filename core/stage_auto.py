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
from core import kho_profile
import hashlib
import json
import os
import re
import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import diag, features

FLAG = "stage_auto"
CODE = "stage_auto"
FIELD = "stage_camera"                 # = plate_camera.STAGE_FIELD
K1_VERSION = 2                         # 2 = sàn trong nhà chọn mặt hướng lên gần cao độ chỗ đứng (không lấy trần)
MAX_GRID_CELLS = 64                    # cạnh lưới K1 tối đa (64 m) — chỗ đứng xa hơn: ô 'ngoài lưới' như cũ (bộ giải chỉ xếp hạng)
NEAR_SPOT_M = 25.0                     # chỗ đứng khác (không shot nào của cảnh dùng) chỉ nêu cho Đạo diễn khi trong bán kính này quanh O
HANDHELD_FLAG = "stage_handheld_props"
HANDHELD_NOTE = ("Vũ khí / đồ cầm tay (`cam_duoc`): ghi vào objects như đạo cụ. Chưa xuất hiện → `{\"hidden\": true}` ở các nhịp trước; "
                 "nằm đâu đó → `at` (+ `z` = cao mặt đặt, m); trong tay → `\"cam_tay\": \"<khóa người>\", \"tay\": \"phai|trai|hai_tay\"` "
                 "(code tính điểm tay theo chỗ đứng + hướng mặt + tư thế; người phải có `facing`). Quay phim ghi vật này vào "
                 "`thanh_phan` khi shot cần thấy nó — Blender đo % thấy.")
# Vũ khí chưa có số đo Kho: câu tỉ lệ Kho (prop_lock.weapon_scale — tập 1 dùng, lấy từ ảnh nhân vật cầm súng, vd SKORP "≈ 3
# head-heights long") → dài = N × H người cầm × HEAD_PER_H. ƯỚC TÍNH: HEAD_PER_H = chuẩn người lớn 1/7,5; cao = WEAPON_H_PER_L × dài
# (đo trên ảnh Kho #433 'kelly_cam_skorp_ty_le': nòng→báng ≈ 470 px ≈ 3,4 đầu, cao kể cả băng đạn ≈ 0,3 dài).
HANDHELD_REDO_ENV = "STAGE_HANDHELD_REDO"
HEAD_PER_H = 1 / 7.5
WEAPON_H_PER_L = 0.3
_HEADS = re.compile(r"(?<![\w.,–-])(\d+(?:[.,]\d+)?)(?!\s*[-–]\s*\d)\s*(?:x|×)?\s*(?:head[- ]?heights?|heads?\b"
                    r"|đầu\b(?!\s*(?:đạn|nòng|súng|báng|ray)))", re.I)      # rà 16/10: "2–3 đầu" / "đầu đạn" / "OB55" không tính


def placed_without_handheld(k1_dir: str, seg: Dict) -> bool:
    """Người dùng 16/10 ('bật cho cảnh mới; cảnh đã duyệt giữ nguyên'): đoạn đã có máy sân khấu lưu (result.json có `cams`) dựng KHÔNG
    có đồ cầm tay → giữ đầu vào cũ (vân tay không đổi: không gỡ máy, không gọi API dàn lại). Lượt đã có đồ cầm tay → giữ bật.
    Dàn lại đoạn cũ CÓ súng: env HANDHELD_REDO_ENV=1 (CLI `--cam-tay`, chọn có chủ ý)."""
    if os.environ.get(HANDHELD_REDO_ENV) == "1":
        return False
    seg_dir = os.path.join(os.path.dirname(os.path.abspath(k1_dir)), f"doan_{key_of(seg['scene'])}")
    try:
        with open(os.path.join(seg_dir, "result.json"), encoding="utf-8") as f:
            res = json.load(f)
    except (OSError, ValueError):
        return False
    if not res.get("cams"):
        return False
    rd = os.path.join(seg_dir, res.get("round") or "")
    src = os.path.join(rd, "inputs.json") if os.path.exists(os.path.join(rd, "inputs.json")) else os.path.join(seg_dir, "inputs.json")
    try:                                                  # như result_round: lượt ngoại tuyến / chia vai có inputs.json riêng, API r<n> ở đoạn
        with open(src, encoding="utf-8") as f:
            fixed = json.load(f).get("fixed") or []
    except (OSError, ValueError):
        fixed = []
    return not any(o.get("cam_duoc") for o in fixed if isinstance(o, dict))


def weapon_size_from_scale(conn, asset: Dict, holder_h: float) -> Optional[Tuple[float, float, str]]:
    """(cao, dài, nguồn) ước tính từ câu tỉ lệ của Kho, None khi Kho không ghi số đầu."""
    from . import prop_lock
    try:
        text = prop_lock.weapon_scale(conn, asset) or ""
    except Exception:  # noqa: BLE001 - hồ sơ hỏng: không ước tính (ghi chú 'không đo được')
        return None
    m = _HEADS.search(text)
    if not m:
        return None
    n = float(m.group(1).replace(",", "."))
    d = n * holder_h * HEAD_PER_H
    return round(WEAPON_H_PER_L * d, 3), round(d, 3), (f"ước tính từ tỉ lệ Kho #{asset.get('id')} ({n:g} đầu × {holder_h:g} m / 7,5; "
                                                         f"cao = {WEAPON_H_PER_L:g} × dài)")


SEG_FIELD = "stage_segment"
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOL = None


def enabled() -> bool:
    """Cờ stage_auto VÀ các cờ nó cần (features.REQUIRES: stage_camera — nền 3D mới dùng máy sân khấu; place_render_refs — có nền
    3D). Thiếu một cờ → không chạy (rà 15/10: trả tiền Đạo diễn mà máy không được dùng, G0 lại bị bỏ)."""
    return features.on(FLAG) and all(features.on(n) for n in features.REQUIRES.get(FLAG, ()))


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
    """Ghi ⚙ Chẩn đoán + nhật ký MỘT lần cho mỗi câu (autopilot gọi run() mỗi nhịp — rà 15/10: không đẩy trôi nhật ký)."""
    try:
        seen = conn.execute("SELECT 1 FROM diag_events WHERE project_id=? AND COALESCE(code,'')=? AND message=? LIMIT 1",
                            (pid, CODE, diag.redact(msg)[:400])).fetchone()
    except Exception:  # noqa: BLE001 - không có bảng diag: cứ nói
        seen = None
    if seen and sev != "info":                            # rà 15/10: câu ước tính trước lời gọi trả tiền luôn được nói lại
        return
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


def set_family(conn, place_ids: List[int], family: str) -> None:
    """Khai họ sân khấu cho các bối cảnh Kho (cùng một nơi, khác trạng thái — vd phòng 447 cửa đóng + 448 cửa mở): ghi
    `profile.model3d.stage_family`. Bối cảnh chưa có model 3D → ValueError (không đoán)."""
    fam = str(family or "").strip()
    if not fam:
        raise ValueError("cần tên họ sân khấu")
    ids = list(dict.fromkeys(int(pid_) for pid_ in (place_ids or [])))
    updates = []
    for pid_ in ids:
        row = conn.execute("SELECT profile FROM assets WHERE id=?", (pid_,)).fetchone()
        prof = json.loads(row["profile"] or "{}") if row else {}
        if not prof.get("model3d"):
            raise ValueError(f"Kho #{pid_} chưa có model 3D")
        prof["model3d"]["stage_family"] = fam
        updates.append((json.dumps(prof, ensure_ascii=False), pid_))
    conn.execute("SAVEPOINT stage_family_update")
    try:
        conn.executemany("UPDATE assets SET profile=? WHERE id=?", updates)
        conn.execute("RELEASE SAVEPOINT stage_family_update")
        conn.commit()
    except Exception:
        conn.execute("ROLLBACK TO SAVEPOINT stage_family_update")
        conn.execute("RELEASE SAVEPOINT stage_family_update")
        raise


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


def family_suggestions(segs: List[Dict]) -> List[Dict]:
    """Nhóm bối cảnh có dấu chỗ đứng giống hệt nhưng stage khác để người dùng xem xét thủ công; không tự gộp.

    Mỗi gợi ý giữ cả cấu hình khai báo ở Kho và cấu hình quan sát từ `spots`, để UI phân biệt bằng chứng với kết luận.
    """
    groups: Dict[str, List[Dict]] = {}
    for g in segs or []:
        place_id = (g.get("place") or {}).get("id")
        if place_id is None:
            continue
        spots = g.get("entry", {}).get("spots") or {}
        if not spots:
            continue                                      # không có dấu vị trí đo được thì không đủ căn cứ gợi ý cùng họ
        sig = json.dumps(spots, sort_keys=True, ensure_ascii=False)
        groups.setdefault(sig, []).append({"place_id": int(place_id), "stage": str(g.get("stage") or ""),
                                           "declared": str(g.get("entry", {}).get("stage_family") or "").strip() or None})
    out = []
    for sig, members in groups.items():
        unique = {m["place_id"]: m for m in members}
        members = list(unique.values())
        if len(members) < 2 or len({m["stage"] for m in members}) < 2:
            continue
        declared = {m["declared"] for m in members if m["declared"]}
        # Một họ đã khai thống nhất thì không còn gợi ý. Xung đột khai báo vẫn được đưa ra để người kiểm tra.
        if len(declared) == 1 and all(m["declared"] for m in members):
            continue
        spots = json.loads(sig)
        out.append({"place_ids": sorted(unique), "spots": spots,
                    "family": next(iter(declared)) if len(declared) == 1 else None,
                    "members": sorted(members, key=lambda m: m["place_id"]),
                    "declared_conflict": len(declared) > 1})
    return sorted(out, key=lambda g: g["place_ids"])


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
    """Luôn TUYỆT ĐỐI (16/10 #31 cảnh 4: 'data/projects/…' tương đối → Blender bản Store chạy thư mục khác ghi ảnh ra C:/data)."""
    return os.path.abspath(os.path.join(data_dir, str(pid), "stage", stage))


def grid_cells(seg: Dict) -> int:
    """Số ô (cạnh lưới K1, 1 m/ô) đủ phủ MỌI chỗ đứng shot của đoạn quanh gốc O + 6 m (16/10 #31 cảnh 4: khe tây / ngã rẽ bắc cách O
    14 m nằm ngoài lưới 20 × 20 → mọi phương án máy 'ngoài lưới')."""
    import math as _m
    spots = seg["entry"].get("spots") or {}
    o = (spots.get(seg["main_spot"]) or {}).get("at") or [0, 0, 0]
    far = max([0.0] + [max(abs(spots[n]["at"][0] - o[0]), abs(spots[n]["at"][1] - o[1])) for n in seg.get("spots") or {}
                       if n in spots and spots[n].get("at")])
    return min(MAX_GRID_CELLS, max(20, 2 * int(_m.ceil(far + 6.0))))      # rà 16/10: trần — K1 tăng theo bình phương cạnh lưới


def ensure_k1_seg(seg: Dict, base: str, log: Callable[[str], None] = lambda m: None) -> str:
    return ensure_k1(seg["entry"], seg["main_spot"], base, log, cells=grid_cells(seg))


def _k1_key(entry: Dict, spot: str, base: str, cells: int = 20) -> Tuple[str, Dict]:
    out = os.path.join(base, f"k1_{key_of(spot)}" + (f"_{int(cells)}" if cells != 20 else ""))
    want = {"sha256": entry.get("sha256"), "path": entry.get("path"), "at": (entry.get("spots") or {}).get(spot, {}).get("at")}
    if cells != 20:
        want["cells"] = int(cells)                        # lưới lớn hơn = K1 khác (cache riêng)
    from .location_pack import stretch_spec
    if stretch_spec(entry):                               # G8 19/10: rào nâng theo game = hình học khác → K1 đo lại
        want["stretch"] = stretch_spec(entry)
    want["k1_version"] = K1_VERSION                       # đổi cách đo (16/10: sàn dưới trần) → đo lại
    return out, want


def k1_cached(seg: Dict, base: str) -> Optional[str]:
    """Thư mục K1 của đoạn khi ĐÃ đo đúng model + chỗ đứng (cache còn hiệu lực), None khi chưa — KHÔNG chạy Blender (M4.8 bàn đạo diễn:
    trạng thái vẽ mỗi lần Streamlit chạy lại không được đo K1)."""
    out, want = _k1_key(seg["entry"], seg["main_spot"], base, grid_cells(seg))
    try:
        with open(os.path.join(out, "k1_key.json"), encoding="utf-8") as f:
            return out if os.path.exists(os.path.join(out, "stage.json")) and json.load(f) == want else None
    except (OSError, ValueError):
        return None


def ensure_k1(entry: Dict, spot: str, base: str, log: Callable[[str], None] = lambda m: None, cells: int = 20) -> str:
    """K1 của chỗ đứng (0 USD, Blender ≈ 20 s), cache theo sha model + tọa độ chỗ đứng. Lỗi = ValueError / BlenderError."""
    out, want = _k1_key(entry, spot, base, cells)
    mark = os.path.join(out, "k1_key.json")
    bad = os.path.join(out, "k1_error.json")
    if os.path.exists(os.path.join(out, "stage.json")) and os.path.exists(mark):
        try:
            with open(mark, encoding="utf-8") as f:
                if json.load(f) == want:
                    return out
        except (OSError, ValueError):
            pass
    if os.path.exists(bad):                               # lỗi lần trước với cùng model + chỗ đứng: nói lại, không chạy Blender mỗi nhịp
        try:
            with open(bad, encoding="utf-8") as f:
                old = json.load(f)
            if old.get("want") == want:
                raise ValueError(f"{old.get('error')} (lỗi lần trước — xóa {bad} để đo lại)")
        except (OSError, TypeError, AttributeError):
            pass
    log(f"Sân khấu: đo sàn K1 chỗ đứng '{spot}' (Blender, 0 USD)")
    try:
        tool().k1_run(entry, spot, out, cells=cells)
    except Exception as e:
        os.makedirs(out, exist_ok=True)
        with open(bad, "w", encoding="utf-8") as f:
            json.dump({"want": want, "error": f"{type(e).__name__}: {e}"[:600]}, f, ensure_ascii=False)
        raise
    if os.path.exists(bad):
        os.remove(bad)
    with open(mark, "w", encoding="utf-8") as f:
        json.dump(want, f, ensure_ascii=False)
    return out


def _rel(stage: Dict, model_xyz) -> List[float]:
    o = stage["origin_model"]
    return [round(float(model_xyz[k]) - o[k], 3) for k in range(3)]


def _model(stage: Dict, rel_xyz) -> List[float]:
    o = stage["origin_model"]
    return [round(o[k] + float(rel_xyz[k] if k < len(rel_xyz) else 0.0), 3) for k in range(3)]


# V3.1 M2.4 G1 (#31 shot 28/30/34/35 "XÁC ĐEN BIẾT BAY"): đạo cụ cảnh trước chỉ mang sang khi cùng thế giới + shot nhắc tên
PROPS_BYD_FLAG = "stage_props_byd"


def _world_keys(shots: List[Dict]) -> Tuple[set, set]:
    """Thế giới của các shot (chưa có world_id M3): (các location_asset, các giờ chuẩn hóa plate_env) — thiếu = chưa rõ, không tính."""
    from .plate_env import time_of
    return ({d["location_asset"] for d in shots if d.get("location_asset") is not None},
            {time_of(d) for d in shots if d.get("time") or d.get("time_of_day")})


def _prop_carry(conn, pid: int, seg: Dict, prev_state: Dict) -> Callable[[str, Dict], Optional[str]]:
    """Hàm (khóa, vật) → lý do KHÔNG mang (None = mang): khác thế giới với cảnh trước, hoặc BYĐ (vat / thanh_phan) lẫn chữ shot của đoạn
    này không nhắc tên vật. BYĐ thiếu → chỉ xét chữ shot (không đoán thêm)."""
    from . import prop_lock, shot_intent
    from .assets import fold
    prev_scene = str(prev_state.get("scene"))
    prev_shots = []
    for r in conn.execute("SELECT data FROM scenes WHERE project_id=?", (pid,)):
        try:
            d = json.loads(r["data"] or "{}")
        except ValueError:
            continue
        if str(d.get("story_scene")) == prev_scene:
            prev_shots.append(d)
    now = [s["data"] for s in seg["shots"]]
    was, cur = _world_keys(prev_shots), _world_keys(now)
    other_world = any(a and b and not (a & b) for a, b in zip(was, cur))      # đổi nơi (Kho) hoặc đổi giờ; thiếu một bên = chưa rõ
    text = " " + " ".join(fold(prop_lock.shot_text(d)).lower() for d in now) + " "
    named = {fold(n).lower() for d in now for n in shot_intent.named_things(d)}

    def why(k: str, o: Dict) -> Optional[str]:
        if other_world:
            return "đoạn này khác thế giới (location_asset / time khác cảnh trước)"
        names = {fold(str(x)).lower() for x in (k, k.replace("_", " "), o.get("label")) if x}
        if names & named or any(n in text for n in names if len(n) >= 3):
            return None
        return "BYĐ / chữ shot của đoạn này không nhắc tên vật"
    return why


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
        prof = kho_profile.for_character(conn, pid, n)
        k = key_of(n)
        while k in keys:
            k += "x"
        keys.add(k)
        if not prof or not prof.get("height_m"):
            missing.append(f"chiều cao nhân vật {n} (Kho → hồ sơ chuẩn `height_m`, đã duyệt)")
            continue
        people.append({"key": k, "label": n, "H": float(prof["height_m"])})
    objs: Dict[int, Dict] = {}
    props_of: Dict[int, List[int]] = {}
    handheld: Dict[int, Dict] = {}
    holders: Dict[int, set] = {}
    hand_on = features.on(HANDHELD_FLAG) and not placed_without_handheld(k1_dir, seg)
    for s in seg["shots"]:
        for a in place_refs.shot_objects(conn, pid, s["data"]):
            if a.get("kind") != "weapon":
                props_of.setdefault(s["idx"], []).append(a["id"])
            if a.get("kind") == "weapon":                 # rà 15/10: súng / vũ khí cầm tay — không phải khối đứng trên sàn
                if hand_on:                               # 16/10 cờ stage_handheld_props: vật theo nhịp (chỗ khai / tay nhân vật)
                    handheld.setdefault(a["id"], a)
                    holders.setdefault(a["id"], set()).update(x for x in s["data"].get("characters") or [] if isinstance(x, str))
                continue
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
    hand_notes = []
    for a in handheld.values():
        size = a.get("size") or {}
        h = size.get("height_m")
        d = max([v for v in (size.get("length_m"), size.get("width_m"), size.get("depth_m")) if v] or [0])   # vũ khí: bề dài
        src = f"Kho #{a.get('id')} size"
        if not h or not d:                                # 16/10 người dùng: Kho đã có ảnh nhân vật cầm súng → câu tỉ lệ (tập 1 dùng)
            hs = [p["H"] for p in people if p["label"] in holders.get(a["id"], ())]
            est = weapon_size_from_scale(conn, a, max(hs)) if hs else None     # H lớn nhất trong các nhân vật của shot
            if est:                                       # rà 16/10: chỉ điền phần Kho thiếu, số đo Kho thắng
                src = est[2] if not (h or d) else f"Kho #{a.get('id')} size + {est[2]}"
                h, d = h or est[0], d or est[1]
        if not h or not d:                                # không chặn cả cảnh: nói rõ vật này không đo được
            hand_notes.append(f"(vũ khí {a.get('name')} Kho #{a.get('id')} thiếu kích thước cao + dài và câu tỉ lệ 'N head-heights' → "
                              "không có trong dàn cảnh, code KHÔNG đo được % thấy)")
            continue
        k = key_of(a.get("name"))
        while k in keys:
            k += "x"
        keys.add(k)
        fixed.append({"key": k, "kind": "dao_cu", "label": a.get("name"), "h": round(float(h), 3), "d": round(float(d), 3),
                      "cam_duoc": True, "source": src})
    marks = st.get("marks") or {}
    if "thap_chan" in marks:
        fixed.append({"key": "moc", "kind": "moc", "from_marks": "thap",
                      "label": f"mốc bản đồ ({(marks.get('thap_object') or {}).get('name') or 'anchor'})"})
    notes = []
    if any(o["kind"] == "dao_cu" for o in fixed):
        notes.append("Đạo cụ không ghi `at`: bạn đặt vị trí theo kịch bản, GIỮ nguyên h / d / kind.")
    if any(o.get("cam_duoc") for o in fixed):
        notes.append(HANDHELD_NOTE)
    notes += hand_notes
    main = seg["main_spot"]
    far = 0
    from .assets import fold
    fold_all = fold(" ".join(str(s["data"].get(k) or "") for s in seg["shots"] for k in ("action", "blocking", "location"))).lower()
    for name, sp in (seg["entry"].get("spots") or {}).items():
        if name != main and sp.get("at"):
            r = _rel(st, sp["at"])
            used = seg["spots"].get(name)
            said = name.replace("_", " ") in fold_all or bool(sp.get("label") and fold(str(sp["label"])).lower() in fold_all)
            if not used and not said and (r[0] ** 2 + r[1] ** 2) ** 0.5 > NEAR_SPOT_M:
                far += 1                                  # 16/10 gói thật #31 cảnh 4: 30 chỗ đứng cả bản đồ (tới 200 m) là nhiễu
                continue
            notes.append(f"Chỗ đứng khác trên CÙNG sân khấu: `{name}` tại ({r[0]:+.2f} Đ, {r[1]:+.2f} B, cao {r[2]:+.2f} m) so với O"
                         + (f" — shot {', '.join(map(str, used))} của cảnh này đứng ở đó" if used else ""))
    if far:
        notes.append(f"(code bỏ {far} chỗ đứng khác cách O hơn {NEAR_SPOT_M:g} m mà kịch bản cảnh này không nhắc)")
    have_keys = {o["key"] for o in fixed}
    by_key = {o["key"]: o for o in fixed}
    carry = _prop_carry(conn, pid, seg, prev_state) if prev_state and features.on(PROPS_BYD_FLAG) else None
    dropped = set()
    for k, o in (prev_state or {}).get("objects", {}).items():
        if k in by_key and "at" not in by_key[k] and by_key[k]["kind"] != "moc":     # đạo cụ Kho đã đặt ở cảnh trước: giữ chỗ
            r = _rel(st, o["at_model"])
            by_key[k]["at"] = [r[0], r[1]]
            continue
        # rà 15/10: đạo cụ của cảnh trước trên cùng sân khấu = vật CỐ ĐỊNH ở đúng chỗ cũ (không thì Đạo diễn bị từ chối vì "tự thêm")
        if o.get("kind") not in ("nguoi", "moc") and k not in have_keys and o.get("h") and o.get("d"):
            why = carry(k, o) if carry else None
            if why:                                   # M2.4 G1 (cờ stage_props_byd): không mang vật cảnh trước mà shot không nhắc
                notes.append(f"(code bỏ đạo cụ `{k}` ({o.get('label') or k}) của cảnh {prev_state.get('scene')}: {why})")
                dropped.add(k)
                continue
            r = _rel(st, o["at_model"])
            fixed.append({"key": k, "kind": o["kind"], "at": [r[0], r[1]], "h": o["h"], "d": o["d"], "label": o.get("label") or k,
                          **({"hollow": True} if o.get("hollow") else {}), "source": f"cảnh {prev_state.get('scene')} (cùng sân khấu)"})
            have_keys.add(k)
    if prev_state:
        for k, o in prev_state.get("objects", {}).items():
            if k in have_keys or k in dropped:
                continue
            r = _rel(st, o["at_model"])
            facing = "" if o.get("facing") is None else f", hướng {o['facing']}°"
            pose = f", {o['tu_the']}" if o.get("tu_the") else ""
            notes.append(f"Vị trí CUỐI ở cảnh trước trên cùng sân khấu (cảnh {prev_state.get('scene')}): `{k}` tại ({r[0]:+.2f}, "
                         f"{r[1]:+.2f}){facing}{pose} — GIỮ chỗ này trừ khi kịch bản cho di chuyển (ghi beat + _ly_do)")
    shots = []
    skipped = []
    key_by_name = {p["label"]: p["key"] for p in people}
    from .assets import fold
    key_by_fold = {fold(p["label"]).lower(): p["key"] for p in people}
    from .location_pack import spot_for
    for s in seg["shots"]:
        d = s["data"]
        old = "; ".join(x for x in (d.get("blocking"), " ".join(str(d.get(k) or "") for k in ("size", "angle", "camera_move")).strip(),
                                    d.get("end_state")) if x)
        sp = spot_for(seg["entry"], d)
        r = _rel(st, sp["at"]) if sp.get("at") else None
        if not [n for n in (d.get("characters") or []) if n in key_by_name] and not props_of.get(s["idx"]):
            # 16/10 (#31 cảnh 1 shot 1–3, cảnh 2 shot 5: POV nhìn cửa / lối vào — thuộc model 3D, không phải vật dàn cảnh): shot không
            # người, không nhắc đạo cụ nào →
            # sân khấu không có gì để dàn; shot dùng máy nền thường (plate_view), nói rõ — không bắt Đạo diễn bịa thứ chính
            skipped.append(s["idx"])
            continue
        # 16/10 (#31 cảnh 4 người dùng "chưa được": địch không vào khung, shot 16–18 giống nhau, Kelly 17–18 sai chỗ): đề bài trước
        # KHÔNG có nhân vật / chỗ đứng / cỡ / góc của từng shot — nay có, và bộ kiểm + số đo bắt theo đúng các trường này
        shots.append({"shot": s["idx"], "action": d.get("action") or d.get("text") or "", "ghi_chu_khung_cu": old,
                      "do_dai": f"{d.get('duration_s')} s" if d.get("duration_s") else "",
                      "nhan_vat": [key_by_name[n] for n in (d.get("characters") or []) if n in key_by_name],
                      "cho_dung": {"ten": sp.get("name"), "at": [r[0], r[1]] if r else None},
                      "co_kich_ban": d.get("size"), "goc_kich_ban": d.get("angle"), "may_kich_ban": d.get("camera_move"),
                      # 16/10 lần 4: luật 'trong khung' theo VAI shot (dữ kiện kịch bản, không đoán chữ) — xem stage_director.must_see
                      "vai_shot": d.get("role"),
                      # rà 16/10: speaker 'KELLY' ≠ characters 'Kelly' — so khớp sau khi bỏ dấu + chữ hoa
                      "nguoi_noi": [key_by_fold[fold(x.get("speaker") or "").lower()] for x in (d.get("dialogue") or [])
                                    if isinstance(x, dict) and fold(x.get("speaker") or "").lower() in key_by_fold],
                      "ten": {key_by_name[n]: n for n in (d.get("characters") or []) if n in key_by_name}})
    aspect = formats.project_aspect(conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()) or "9:16"
    if skipped:
        notes.append(f"(shot {', '.join(map(str, skipped))} không có người / đạo cụ để dàn — không cần yêu cầu khung, dùng máy nền thường)")
    inputs = {"pid": pid, "canh": f"cảnh {seg['scene']} — {seg['place'].get('name')} ({len(seg['shots'])} shot)",
              "bo_qua": skipped,
              # 16/10 gốc lỗi chạy thật #31 cảnh 4 (lần 2, 0,37 USD): cờ director_blockout (nhánh C — bối cảnh KHÔNG có model 3D)
              # bật trên máy → đề bài nối "Sơ đồ khối bắt buộc" + bộ kiểm đòi schema khối. Quyết định nhánh lấy từ Kho như v3_main.
              "_blockout_enabled": _branch_c(conn, seg["place"]["id"]),
              "auto": True, "place": seg["place"]["id"], "spot": main, "aspect": aspect, "fixed": fixed, "people": people,
              "shots": shots, "floor": tool()._floor_notes(grid), "user_notes": notes}
    return inputs, missing


def _branch_c(conn, place_id) -> bool:
    """Nhánh C (khai sơ đồ khối) chỉ cho bối cảnh KHÔNG có model 3D — Kho quyết định (director_blockout.scene_uses_blockout)."""
    from . import director_blockout
    try:
        return bool(director_blockout.scene_uses_blockout(conn, {"place": place_id}))
    except ValueError:
        return False


def _free_spots(fixed: List[Dict], n: int) -> List[List[float]]:
    """n điểm đứng cho câu trả lời mẫu: O rồi các vòng 1,5 / 2,5 / 3,5 / 5 m × 8 hướng, cách mọi vật cố định có `at` ít nhất
    bán kính + 0,5 m (rà 16/10: người mẫu đứng chồng giếng ở O → cổng chặn mãi)."""
    import math as _m
    taken = [(f["at"][0], f["at"][1], float(f.get("d") or 1.0) / 2 + 0.5) for f in fixed if f.get("at") and f.get("kind") != "moc"]
    out = []
    for r in (0.0, 1.5, 2.5, 3.5, 5.0, 7.0):
        for k in (range(8) if r else [0]):
            x, y = round(r * _m.sin(k * _m.pi / 4), 2), round(r * _m.cos(k * _m.pi / 4), 2)
            if all(_m.hypot(x - a, y - b) >= rad for a, b, rad in taken) and all(_m.hypot(x - a, y - b) >= 0.8 for a, b in out):
                out.append([x, y])
                if len(out) >= n:
                    return out
    return out


def example_answer(inputs: Dict) -> Dict:
    """Câu trả lời MẪU đúng định dạng dựng từ chính đề bài — cho cổng 0 USD (preflight). Người đứng ở chỗ trống (_free_spots), đạo
    cụ chưa có `at` cũng vậy; shot nào cũng một thứ `chinh` (người đầu, không có người thì vật cố định đầu tiên)."""
    people = inputs.get("people") or []
    fixed = inputs.get("fixed") or []
    loose = [f for f in fixed if f.get("kind") != "moc" and not f.get("at")]
    spots = _free_spots(fixed, len(people) + len(loose))
    objs = []
    for p, at in zip(people, spots):
        objs.append({"key": p["key"], "kind": "nguoi", "at": at, "H": p["H"], "facing": 0, "label": p.get("label", p["key"])})
    for f, at in zip(loose, spots[len(people):]):
        objs.append({k: v for k, v in f.items() if k != "source"} | {"at": at})
    from .stage_grid import FRAMING
    specs = []
    for i, s in enumerate(inputs.get("shots") or []):
        cast = [k for k in (s.get("nhan_vat") or []) if any(p["key"] == k for p in people)] or ([people[0]["key"]] if people else [])
        if cast:
            parts = [{"vat": cast[0], "vai": "chinh", "vung": "giua-tren", "thay": "mat", "co_pct": [40, 80]}]
            parts += [{"vat": k, "vai": "phu", "vung": "phai" if j % 2 else "trai"} for j, k in enumerate(cast[1:])]
        elif fixed:
            parts = [{"vat": fixed[0]["key"], "vai": "chinh", "vung": "giua"}]
        else:
            parts = []
        co = s.get("co_kich_ban") if s.get("co_kich_ban") in FRAMING else "MS"
        specs.append({"shot": s["shot"], "muc_dich": "…", "co": co, "do_cao": ("ngang", "cao", "thap")[i % 3], "goc": "ngang",
                      "thanh_phan": parts})
    return {"blocking": {"objects": objs}, "shot_specs": specs, "can_hoi": []}


PLACEHOLDER = {"at": "<[x, y] mét so với O>", "facing": "<độ từ Bắc>", "co": "<EWS|WS|GAME_TPS|MLS|MS|MCU|CU|ECU>",
               "do_cao": "<ngang|thap|cao|tren_dau>", "goc": "<ngang|cui|ngua>", "vung": "<NGANG-DỌC, vd trai-duoi>",
               "co_pct": "<[min, max] % khung>", "thay": "<mat|lung|nghieng>", "muc_dich": "<người xem cần thấy gì>",
               "vai": "<chinh|phu|khong_duoc_co>"}


def _placeholders(v):
    if isinstance(v, dict):
        return {k: (PLACEHOLDER[k] if k in PLACEHOLDER else _placeholders(x)) for k, x in v.items()}
    if isinstance(v, list):
        return [_placeholders(x) for x in v]
    return v


def preflight(inputs: Dict, marks: Optional[Dict]) -> List[str]:
    """Cổng 0 USD BẮT BUỘC trước lời gọi trả tiền: (1) đề bài không đòi phần bộ kiểm không cần / ngược lại (nhánh C cho bối cảnh có
    model 3D); (2) câu trả lời mẫu dựng từ đề bài qua được bộ kiểm thật (stage_director.validate_answer, đúng cờ máy này). Trả lỗi."""
    import copy as _c
    from . import director_blockout, llm_io
    from . import stage_director as sd
    out = []
    if director_blockout.enabled(inputs):
        out.append("đề bài sân khấu đòi sơ đồ khối nhánh C cho bối cảnh có model 3D (cờ director_blockout) — đề bài/bộ kiểm không khớp")
    try:
        sd.validate_answer(_c.deepcopy(example_answer(inputs)), dict(inputs, _skip_k3=True), marks)
    except (llm_io.SchemaError, ValueError, KeyError, TypeError) as e:
        out.append(f"câu trả lời mẫu đúng định dạng không qua bộ kiểm: {str(e)[:300]}")
    return out


def format_example(inputs: Dict) -> str:
    """Khuôn ĐỊNH DẠNG gửi kèm đề bài (rà 16/10: ví dụ có số thì Claude dễ chép vị trí giả) — cùng cấu trúc với câu trả lời mẫu đã qua
    bộ kiểm, giá trị thay bằng chữ giữ chỗ; một người (+ một đạo cụ cần đặt) + một shot."""
    ex = example_answer(inputs)
    objs = ex["blocking"]["objects"]
    keep = objs[:1] + [o for o in objs if o.get("kind") != "nguoi"][:1]
    shape = _placeholders({"blocking": {"objects": keep}, "shot_specs": ex["shot_specs"][:1], "can_hoi": []})
    head = ("## Khuôn ĐỊNH DẠNG (code dựng từ đề bài này, cùng cấu trúc với câu trả lời đã cho qua bộ kiểm) — KHÔNG chép giá trị: "
            "mọi chữ <…> là chỗ bạn điền theo kịch bản; trả đủ mọi người, mọi shot")
    return "\n\n" + head + "\n```json\n" + json.dumps(shape, ensure_ascii=False) + "\n```"


# ---- kết quả → máy của shot -----------------------------------------------------------------------------------------------
COLOUR_WORDS = {(1.0, 0.45, 0.05): "orange", (0.85, 0.05, 0.1): "red", (0.2, 0.75, 0.3): "green", (0.6, 0.3, 0.9): "purple",
                (0.1, 0.4, 1.0): "blue", (0.95, 0.85, 0.05): "yellow", (1.0, 0.4, 0.75): "pink"}


def mannequin_colours(beats: Dict, labels: Dict[str, str]) -> Dict[str, str]:
    """{màu người nộm: tên nhân vật} — cùng thứ tự gán màu của tools/stage_grid.blender_props (hình clay K4 tô theo đó)."""
    import copy
    out: Dict[str, str] = {}
    seen = set()
    for p in tool().blender_props(copy.deepcopy(beats)):
        if p.get("kind") == "person" and p["key"] not in seen:
            seen.add(p["key"])
            word = COLOUR_WORDS.get(tuple(round(c, 2) for c in p["rgb"]))
            if word:                                      # rà 16/10: > 7 người → màu quay vòng; ghi cả hai tên, không bỏ im lặng
                name = labels.get(p["key"], p["key"])
                out[word] = f"{out[word]} / {name}" if word in out else name
    return out


def cameras_from(stage: Dict, v2: Dict, seg_id: str, rd: str, colours: Optional[Dict[str, str]] = None
                 ) -> Tuple[Dict[int, Dict], Dict[int, str]]:
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
            if o.get("kind") != "dao_cu" or o.get("cam_duoc"):    # 16/10: đồ cầm tay chỉ để đo — không vẽ khối vào ảnh nền
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
            if colours:
                cam["guide_people"] = colours
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
        if o.get("kind") == "moc" or not o.get("at") or o.get("cam_duoc") or o.get("cam_tay"):
            continue                                      # 16/10: đồ cầm tay không thành vật cố định của cảnh sau (Kho thêm lại)
        # 16/10 (#31 cảnh 6→7): nhịp cuối có di chuyển → vị trí cuối là `den`, không phải `at`; nhịp ghi `at` mới mà không `den` thì
        # `den` của objects gốc (beat_raw gộp dict) không còn đúng
        ov = ((bl.get("beats") or {}).get(last.get("nhip")) or {}).get(k) or {}
        end = ov.get("den") or (o["at"] if "at" in ov else o.get("den")) or o["at"]
        out[k] = {"at_model": _model(stage, [end[0], end[1], o.get("z", 0.0)]), "facing": o.get("facing"),
                  **{x: o[x] for x in ("h", "d", "label", "hollow") if x in o},
                  "tu_the": o.get("tu_the"), "kind": o.get("kind")}
    return {"scene": scene, "objects": out}


def draw_beats(rd: str, log: Callable[[str], None] = lambda m: None) -> Optional[str]:
    """top_beats.png của lượt K4 (16/10 người dùng: ảnh nhìn từ trên đánh số / làm mờ theo nhịp, mặt cắt bỏ mái). Ảnh phụ cho người
    xem — lỗi chỉ ghi log, không làm hỏng lượt đã trả tiền."""
    try:
        p = tool().draw_beats(rd)
        return p if isinstance(p, str) else None
    except Exception as e:  # noqa: BLE001 - ảnh phụ
        log(f"không vẽ được top_beats.png ({rd}): {type(e).__name__}: {e}")
        return None


def _guard(conn, s: Dict, data: Dict, changes: Dict, who: Optional[Dict], expected_revs: Optional[Dict]) -> None:
    """M4.8 (C-M48-DESK-CORE, kế hoạch bàn đạo diễn mục 7): lần ghi máy đi qua write guard (M2.5, SHADOW — chỉ ghi ⚙ Chẩn đoán "lẽ ra
    đã…", không chặn, không đổi giá trị) TRƯỚC lệnh UPDATE như cũ. `who` None (nơi gọi cũ) hoặc cờ field_guard TẮT → không đọc thêm,
    không ghi gì thêm (y hệt hôm nay). `expected_revs` {idx: _rev đọc lúc mở lượt duyệt} → lệch = stale_write."""
    if who is None:
        return
    from . import write_guard
    revs = expected_revs or {}
    rev = revs.get(s["idx"], revs.get(str(s["idx"])))
    write_guard.write_scene(conn, s["id"], changes, who, expected_rev=rev if rev is not None else write_guard.rev(data))


def apply(conn, seg: Dict, cams: Dict[int, Dict], skipped=(), who: Optional[Dict] = None,
          expected_revs: Optional[Dict] = None) -> List[int]:
    """Ghi `stage_camera` vào shot (máy hệ thống, không khóa tay). Shot người dùng khóa `stage_camera` → giữ. Máy tự động cũ của shot
    nay không đạt → gỡ (máy cũ của nó lệch đầu vào mới — nền 3D về máy thường, có VÀNG). Shot `skipped` (không người / đạo cụ để
    dàn) chỉ ghi `stage_segment` = đã xét cùng sân khấu (location_pack.stage_report không giữ cảnh oan), máy nền thường.
    `who` (write_guard.actor, M4.8): ai ghi — mỗi shot đổi qua write guard SHADOW trước UPDATE (None = như cũ, không qua guard)."""
    changed = []
    for s in seg["shots"]:
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (s["id"],)).fetchone()
        data = json.loads(row["data"] or "{}")
        if s["idx"] in skipped and s["idx"] not in cams and not data.get(FIELD):
            if data.get(SEG_FIELD) != seg["id"]:
                _guard(conn, s, data, {SEG_FIELD: seg["id"]}, who, expected_revs)
                data[SEG_FIELD] = seg["id"]
                conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), s["id"]))
                conn.commit()
                _flush(conn, who)
                s["data"] = data
            continue
        if FIELD in (data.get("_user_locked") or []):
            continue
        new = cams.get(s["idx"])
        old = data.get(FIELD)
        if new is None and not (isinstance(old, dict) and old.get("auto")):
            continue
        if new == old:
            continue
        if who is not None:
            from .write_guard import DELETE
            _guard(conn, s, data, {FIELD: DELETE, SEG_FIELD: DELETE} if new is None else {FIELD: new, SEG_FIELD: seg["id"]}, who,
                   expected_revs)
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
    _flush(conn, who)
    return changed


def _flush(conn, who: Optional[Dict]) -> None:
    """Rà C-M48-DESK-CORE (CAO 1): dòng shadow của shot 2, 3… được write guard GIỮ vì lúc đó apply đang trong giao dịch → ghi sau commit
    (không thì mất khi kết nối đóng — luồng nền / autopilot không bao giờ báo)."""
    if who is not None:
        from . import write_guard
        write_guard.flush(conn)


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
                log: Callable[[str], None] = lambda m: None, force: bool = False) -> Dict:
    """K1 → đề bài → Đạo diễn (≤ MAX_ROUNDS lượt, sổ chi) → K3 + K4 → máy từng shot. Không ghi CSDL (apply làm việc đó).
    Trả {"cams", "bad" {shot: lý do}, "missing" [..], "state", "reused"}; kết quả lưu <data_dir>/<pid>/stage/<sân khấu>/<đoạn>/
    result.json theo vân tay đầu vào — chạy lại cùng đầu vào không gọi Claude lần nữa."""
    from . import llm_runner
    from . import stage_director as sd
    base = base_dir(data_dir, pid, seg["stage"])
    res: Dict = {"cams": {}, "bad": {}, "missing": [], "state": None, "reused": False}
    try:
        k1 = ensure_k1_seg(seg, base, log)
    except Exception as e:  # noqa: BLE001 - Blender / model 3D: nói rõ, đoạn không chạy
        res["missing"].append(f"không đo được sân khấu K1 chỗ đứng '{seg['main_spot']}': {type(e).__name__}: {e}")
        return res
    inputs, missing = inputs_for(conn, pid, seg, k1, prev_state)
    if missing:
        res["missing"], res["stale"] = missing, True      # đầu vào đổi/thiếu → máy tự động cũ của đoạn không còn đúng
        return res
    res["bo_qua"] = inputs["bo_qua"]
    if not inputs["shots"]:
        # rà 16/10: mọi shot của đoạn không người / đạo cụ (vd cảnh chỉ có POV nhìn cửa) → không có gì để dàn, KHÔNG gọi Đạo diễn
        log(f"Sân khấu {seg['id']}: shot {', '.join(map(str, inputs['bo_qua']))} không người / đạo cụ — không dàn, dùng máy nền thường")
        res["skipped_all"] = True
        return res
    with open(os.path.join(k1, "stage.json"), encoding="utf-8") as f:
        st = json.load(f)
    fp = fingerprint(inputs)
    res["stale"] = any((s["data"].get(FIELD) or {}).get("auto") and (s["data"].get(FIELD) or {}).get("inputs_fp") != fp
                       for s in seg["shots"])
    out = os.path.join(base, f"doan_{key_of(seg['scene'])}")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "result.json")
    if os.path.exists(path) and not force:
        try:
            with open(path, encoding="utf-8") as f:
                old = json.load(f)
            if old.get("fp") == fp:
                return dict(old, cams={int(k): v for k, v in old["cams"].items()}, bad={int(k): v for k, v in old["bad"].items()},
                            reused=True)
        except (OSError, ValueError, KeyError):
            pass
    gate = preflight(inputs, st.get("marks"))
    if gate:                                              # 16/10: không trả tiền cho đề bài mà chính bộ kiểm không cho qua
        res["missing"] += [f"cổng 0 USD chưa qua — {g}" for g in gate]
        return res
    if client is None:
        res["missing"].append("chưa cấu hình Claude (" + llm_runner.missing_hint() + ") — Đạo diễn chưa dàn cảnh")
        return res
    _say(conn, pid, "info", f"Sân khấu {seg['id']}: Đạo diễn dàn cảnh + yêu cầu khung {len(seg['shots'])} shot — ước tính "
                            f"{_estimate(conn, 1)} (tối đa {2 * sd.MAX_ROUNDS} lời gọi {_estimate(conn, 2 * sd.MAX_ROUNDS)})", log)
    with open(os.path.join(out, "inputs.json"), "w", encoding="utf-8") as f:
        json.dump(inputs, f, ensure_ascii=False, indent=1)
    before_run = set(os.listdir(out))                     # tệp của LẦN trước (cất sau khi có câu trả lời mới)
    prev, feedback, obj, v2, rd = None, [], None, None, out
    for rnd in range(1, sd.MAX_ROUNDS + 1):
        text = sd.build_prompt(inputs, prev, feedback) + (format_example(inputs) if prev is None else "")
        with open(os.path.join(out, f"prompt_r{rnd}.md"), "w", encoding="utf-8") as f:
            f.write(text)
        try:
            with llm_runner.tagged(sd.STAGE, pid):
                obj, tin, tout = llm_runner.ask_json(client, text, lambda o: sd.validate_answer(o, inputs, st.get("marks")),
                                                     note=log, bad_reply=_keep_reply(conn, pid, seg, out, rnd))
        except llm_runner.LlmError as e:
            if getattr(e, "code", None) != "bad_json":
                raise                                     # đăng nhập / hạn mức / hết tiền / sổ chi: autopilot dừng như khâu Claude khác
            res["missing"].append(f"Đạo diễn trả lời sai mẫu 2 lần (lượt {rnd}): {str(e)[:200]}")
            return _save(path, dict(res, fp=fp))
        if rnd == 1:                                      # 16/10: chỉ cất lượt của lần trước khi ĐÃ có câu trả lời mới (lỗi Claude → giữ nguyên)
            _archive_rounds(out, only=before_run - {f"prompt_r{rnd}.md"})
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
            return _save(path, dict(res, fp=fp))
        draw_beats(rd, log)
        feedback = sd.feedback_from(solve, v2)
        post = post_checks(inputs, v2)                    # 16/10: nhân vật kịch bản phải THẤY trong khung đo được; shot liền nhau khác máy
        feedback += [f"shot {k}: {v}" for k, v in sorted(post.items())]
        log(f"Sân khấu {seg['id']} lượt {rnd}: vào {tin} / ra {tout} token, {len(feedback)} shot cần sửa")
        if not feedback:
            break
        prev = obj
    try:                                                  # rà 15/10: lỗi lạ sau khi đã trả tiền Claude vẫn được lưu (không hỏi lại)
        try:
            colours = mannequin_colours(solve["beats"], {p["key"]: p["label"] for p in inputs["people"]}) if v2 else {}
        except (ValueError, KeyError, TypeError):
            colours = {}
        cams, bad = cameras_from(st, v2 or {}, seg["id"], rd, colours)
        for k, why in post_checks(inputs, v2 or {}).items():     # số đo Blender: không đạt luật kịch bản → không gán máy, báo
            if k in cams:
                cams.pop(k)
                bad[k] = why
        for cam in cams.values():
            cam["inputs_fp"] = fp
        res["guide_missing"] = guides_missing(cams)
        res["soft"] = soft_checks(inputs, v2 or {})
        res["round"] = os.path.basename(rd)               # rà 16/10: lượt cuối của LẦN chạy này (r* cũ của lần trước còn trên đĩa)
        for s in seg["shots"]:
            if s["idx"] not in cams and s["idx"] not in bad and s["idx"] not in (inputs.get("bo_qua") or []):
                bad[s["idx"]] = "bộ giải không đặt được máy (lỗi yêu cầu khung)"
        advice = {}
        for x in feedback or []:
            m = re.match(r"shot (\d+)\b", x)
            if m:
                advice[int(m.group(1))] = x
        res.update(cams=cams, bad={k: advice.get(k, v) for k, v in bad.items()}, state=end_state(st, obj, seg["scene"]), fp=fp)
    except Exception as e:  # noqa: BLE001 - nói rõ, lưu theo vân tay
        res.update(cams={}, bad={}, state=None)
        res["missing"].append(f"không dựng được máy từ kết quả đo: {type(e).__name__}: {e}")
        return _save(path, dict(res, fp=fp))
    return _save(path, res)


def _keep_reply(conn, pid: int, seg: Dict, out: str, rnd: int):
    """16/10: câu trả lời SAI MẪU đã trả tiền được giữ NGUYÊN VĂN — tệp trong thư mục đoạn + sổ bad_replies (director_lease) — để đối
    chiếu đề bài ↔ bộ kiểm (lần chạy thật cảnh 4 mất 4 câu trả lời không lưu)."""
    from . import director_lease
    keep = director_lease.capture(conn, pid, f"stage:{seg['id']}")
    n = [0]

    def save(text):
        n[0] += 1
        try:
            with open(os.path.join(out, f"bad_reply_r{rnd}_{n[0]}.txt"), "w", encoding="utf-8") as f:
                f.write(text or "")
        except OSError:
            pass
        keep(text)
    return save


SEEN_MIN_PCT = 15.0                    # nhân vật của shot phải thấy ít nhất bấy nhiêu % điểm thân (đầu HOẶC cuối khung khi máy chạy)
SAME_CAM_M, SAME_CAM_DEG = 0.5, 15.0   # hai shot liền nhau cùng chỗ: máy gần hơn + hướng lệch ít hơn + cùng ống = một máy


def post_checks(inputs: Dict, v2: Dict) -> Dict[int, str]:
    """16/10 (#31 cảnh 4 'chưa được', số đo thật: địch 0 % ở mọi shot, máy shot 17 / 18 cách nhau 0,07 m): luật kịch bản kiểm trên
    SỐ ĐO Blender (v2.json): {shot: lý do}. Lý do đi vào vòng sửa của Đạo diễn; còn hỏng thì shot không có máy (báo ĐỎ ở cổng)."""
    import math as _m
    info = {s["shot"]: s for s in inputs.get("shots") or []}
    out: Dict[int, str] = {}
    prev = None
    for s in sorted(v2.get("shots") or [], key=lambda x: x["shot"]):
        b = s.get("best") or {}
        m = b.get("m") or {}
        sh = info.get(s["shot"]) or {}
        spec = s.get("spec") or {}
        from .stage_director import must_see
        need = set(must_see(sh, spec)) if sh else set()
        lost = []
        for k in sorted(need):
            seen = [((m.get("obj") or {}).get(k) or {}).get("seen_pct") or 0.0]
            if b.get("end"):
                seen.append((((b["end"].get("m") or {}).get("obj") or {}).get(k) or {}).get("seen_pct") or 0.0)
            if max(seen) < SEEN_MIN_PCT:
                lost.append(f"`{k}` {max(seen):.0f} %")
        if lost:
            out[s["shot"]] = (f"nhân vật kịch bản không thấy trong khung đo được ({', '.join(lost)} < {SEEN_MIN_PCT:g} %) — đặt họ gần hơn "
                              "trong nhịp của shot / đổi cỡ, độ cao để khung chứa họ")
        if prev is not None and m.get("at") and prev[1].get("at"):
            same_spot = (info.get(prev[0]) or {}).get("cho_dung", {}).get("ten") == (sh.get("cho_dung") or {}).get("ten")
            d = _m.dist(m["at"], prev[1]["at"])
            yaw = lambda q: _m.degrees(_m.atan2(q["aim"][0] - q["at"][0], q["aim"][1] - q["at"][1]))
            dy = abs((yaw(m) - yaw(prev[1]) + 180) % 360 - 180) if m.get("aim") and prev[1].get("aim") else 999
            lens_ratio = max(float(m.get("lens") or 1), float(prev[1].get("lens") or 1)) / max(min(float(m.get("lens") or 1),
                                                                                                float(prev[1].get("lens") or 1)), 1e-6)
            other_size = spec.get("co") != (prev[2].get("co") if len(prev) > 2 else spec.get("co"))
            if same_spot and d < SAME_CAM_M and dy < SAME_CAM_DEG and lens_ratio < 1.3 and not other_size:
                out[s["shot"]] = (out.get(s["shot"], "") + ("; " if s["shot"] in out else "")
                                  + f"máy trùng shot {prev[0]} (cách {d:.2f} m, lệch {dy:.0f}°, cùng ống {m.get('lens')} mm) — đổi góc / "
                                    "độ cao / cỡ")
        prev = (s["shot"], m, spec) if m else None        # rà 16/10: shot không có số đo → shot sau không so với shot cách một
    return out


def soft_checks(inputs: Dict, v2: Dict) -> Dict[int, str]:
    """VÀNG (không giữ shot): nhân vật kịch bản KHÔNG bắt buộc theo vai shot (thiết lập / quan sát…) mà thấy < SEEN_MIN_PCT % khung."""
    from .stage_director import must_see
    info = {s["shot"]: s for s in inputs.get("shots") or []}
    out = {}
    for s in v2.get("shots") or []:
        sh, spec = info.get(s["shot"]) or {}, s.get("spec") or {}
        b = s.get("best") or {}
        m = (b.get("m") or {}).get("obj") or {}
        e = (((b.get("end") or {}).get("m") or {}).get("obj")) or {}          # rà 16/10: cả khung cuối khi máy chạy (như post_checks)
        need = set(must_see(sh, spec))
        low = [k for k in sh.get("nhan_vat") or [] if k not in need and k != spec.get("pov")
               and max(((m.get(k) or {}).get("seen_pct") or 0.0), ((e.get(k) or {}).get("seen_pct") or 0.0)) < SEEN_MIN_PCT]
        if low:
            out[s["shot"]] = (f"vai shot `{sh.get('vai_shot')}`: {', '.join(f'`{k}`' for k in low)} ở xa / ngoài khung (< {SEEN_MIN_PCT:g} %) — "
                              "cho phép, chỉ báo để người xem kiểm")
    return out


def guides_missing(cams: Dict[int, Dict]) -> List[int]:
    """Shot có máy sân khấu mà ảnh người nộm (clay K4) KHÔNG có trên đĩa (16/10 #31 cảnh 4: Blender bản Store ghi ra C:/data) —
    gỡ `guide` khỏi máy đó (không trỏ tệp không có) và trả danh sách để báo ĐỎ."""
    out = []
    for idx, cam in cams.items():
        if cam.get("guide") and not os.path.exists(cam["guide"]):
            cam.pop("guide", None)
            cam.pop("guide_people", None)
            out.append(idx)
    return sorted(out)


def _say_guides(conn, pid: int, seg: Dict, r: Dict, out: Dict, log) -> None:
    miss = r.get("guide_missing") or []
    if not miss:
        return
    line = (f"sân khấu {seg['id']}: ảnh người nộm (clay) của shot {', '.join(map(str, miss))} KHÔNG có trên đĩa — ảnh vẽ sẽ thiếu chỗ "
            f"đứng; dựng lại 0 USD: py tools/stage_auto.py --project {pid} --scene {seg['scene']} --rerender")
    _say(conn, pid, "error", line, log)
    out["held"].append(("stageauto:" + hashlib.sha1(line.encode("utf-8")).hexdigest()[:12], line))


def result_round(data_dir: str, pid: int, seg: Dict) -> Optional[str]:
    """Thư mục lượt K4 mà result.json của đoạn đang dùng (r<n> hoặc cc_<giờ> ngoại tuyến), hoặc None."""
    got = last_answer(data_dir, pid, seg)
    return got[0] if got else None


def last_answer(data_dir: str, pid: int, seg: Dict) -> Optional[Tuple[str, Dict]]:
    """(thư mục lượt, câu trả lời) của lượt Đạo diễn cuối của LẦN chạy trả tiền gần nhất (result.json "round"; không có thì lượt số
    lớn nhất), hoặc None."""
    out = os.path.join(base_dir(data_dir, pid, seg["stage"]), f"doan_{key_of(seg['scene'])}")
    try:
        with open(os.path.join(out, "result.json"), encoding="utf-8") as f:
            rnd = json.load(f).get("round")
        if rnd and os.path.exists(os.path.join(out, rnd, "answer.json")):
            with open(os.path.join(out, rnd, "answer.json"), encoding="utf-8") as f:
                return os.path.join(out, rnd), json.load(f)
    except (OSError, ValueError):
        pass
    rounds = sorted((d for d in (os.listdir(out) if os.path.isdir(out) else []) if re.fullmatch(r"r\d+", d)
                     and os.path.exists(os.path.join(out, d, "answer.json"))), key=lambda d: int(d[1:]))
    if not rounds:
        return None
    rd = os.path.join(out, rounds[-1])
    with open(os.path.join(rd, "answer.json"), encoding="utf-8") as f:
        return rd, json.load(f)


def rerender(conn, pid: int, seg: Dict, data_dir: str, log: Callable[[str], None] = lambda m: None, who: Optional[Dict] = None) -> Dict:
    """Đo + render lại (K3 + K4 Blender, 0 USD) từ câu trả lời Đạo diễn ĐÃ trả tiền của lượt cuối — không gọi Claude. Dùng khi ảnh
    clay / số đo hỏng (16/10: Blender ghi sai chỗ). Ghi máy vào shot như run (apply). Trả {"applied", "held", "missing"}."""
    out: Dict = {"applied": [], "held": [], "missing": []}
    got = last_answer(data_dir, pid, seg)
    if got is None:
        out["missing"].append(f"sân khấu {seg['id']}: chưa có câu trả lời Đạo diễn đã lưu — phải chạy có trả tiền trước")
        return out
    rd, obj = got
    base = base_dir(data_dir, pid, seg["stage"])
    k1 = ensure_k1_seg(seg, base, log)
    inputs, missing = inputs_for(conn, pid, seg, k1, stored_state_before(data_dir, pid, seg, conn))
    if missing:
        out["missing"] += missing
        return out
    fp = fingerprint(inputs)
    try:                                                  # rà 16/10: câu trả lời cũ chỉ dùng cho ĐÚNG đầu vào đã gửi Đạo diễn
        # rà 16/10: lượt chia vai (crew/m<n>) / ngoại tuyến (cc_*) có inputs.json trong thư mục lượt; lượt API r<n> ở thư mục đoạn
        src = os.path.join(rd, "inputs.json") if os.path.exists(os.path.join(rd, "inputs.json")) else os.path.join(os.path.dirname(rd), "inputs.json")
        with open(src, encoding="utf-8") as f:
            sent = fingerprint(json.load(f))
    except (OSError, ValueError):
        sent = None
    if sent != fp:
        out["missing"].append(f"sân khấu {seg['id']}: đầu vào (kịch bản / Kho / cảnh trước) đã đổi so với lần trả tiền — không dựng lại "
                              "từ câu trả lời cũ; phải chạy có trả tiền")
        return out
    with open(os.path.join(k1, "stage.json"), encoding="utf-8") as f:
        st = json.load(f)
    bl = round_blocking(obj["blocking"], inputs)
    solve, v2 = tool().v2_run(bl, obj["shot_specs"], rd, k1, m3=seg["entry"], reach=True, log=log)
    draw_beats(rd, log)
    try:
        colours = mannequin_colours(solve["beats"], {p["key"]: p["label"] for p in inputs["people"]})
    except (ValueError, KeyError, TypeError):
        colours = {}
    cams, bad = cameras_from(st, v2 or {}, seg["id"], rd, colours)
    for k, why in post_checks(inputs, v2 or {}).items():
        if k in cams:
            cams.pop(k)
            bad[k] = why
    for cam in cams.values():
        cam["inputs_fp"] = fp
    for s in seg["shots"]:
        if s["idx"] not in cams and s["idx"] not in bad and s["idx"] not in (inputs.get("bo_qua") or []):
            bad[s["idx"]] = "bộ giải không đặt được máy (lỗi yêu cầu khung)"
    seg_dir = os.path.join(base_dir(data_dir, pid, seg["stage"]), f"doan_{key_of(seg['scene'])}")
    rnd = os.path.relpath(rd, seg_dir).replace(os.sep, "/")
    res = {"cams": cams, "bad": bad, "missing": [], "state": end_state(st, obj, seg["scene"]), "fp": fp,
           "guide_missing": guides_missing(cams), "round": rnd, "rerendered_from": rnd, "soft": soft_checks(inputs, v2 or {})}
    try:                                                  # rà 16/10: giữ nguồn / khóa chia vai của kết quả cũ
        with open(os.path.join(seg_dir, "result.json"), encoding="utf-8") as f:
            old = json.load(f)
        res.update({k: old[k] for k in ("crew", "nguon", "usd") if k in old})
        if isinstance(res.get("crew"), dict) and res["crew"].get("picked"):    # rà 16/10: dựng lại = giải lại, lựa chọn cũ không còn
            res["crew"] = dict(res["crew"], picked=None, giai_lai=True)
    except (OSError, ValueError):
        pass
    _save(os.path.join(seg_dir, "result.json"), res)
    out["applied"] = apply(conn, seg, cams, inputs.get("bo_qua") or [], who=who)
    _say_guides(conn, pid, seg, res, out, log)
    for idx, why in sorted(bad.items()):
        out["held"].append(("stageauto:rerender:" + str(idx), f"shot {idx} ({seg['id']}): {why}"))
    return out


def _archive_rounds(out: str, only=None) -> None:
    """Dời r*/ + prompt_r*.md + bad_reply_* của lần chạy trước vào cu_<giờ>/ — lần mới không ghi đè câu trả lời đã trả tiền."""
    import shutil
    olds = [x for x in os.listdir(out) if (re.fullmatch(r"r[0-9]+", x) or x.startswith(("prompt_r", "bad_reply_r")))
            and (only is None or x in only)]
    if not olds:
        return
    dest = os.path.join(out, "cu_" + time.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(dest, exist_ok=True)
    for x in olds:
        shutil.move(os.path.join(out, x), os.path.join(dest, x))


# ---- chế độ NGOẠI TUYẾN (16/10 người dùng: bàn đạo diễn chạy nền, không gọi API trả tiền) -----------------------------------
def offline_prompt(conn, pid: int, seg: Dict, data_dir: str) -> Tuple[str, List[str]]:
    """(đề bài đầy đủ gửi Đạo diễn = build_prompt + khuôn định dạng, lỗi cổng 0 USD / thiếu đầu vào) — KHÔNG gọi API. Người hoặc một
    phiên Claude Code đọc đề bài này, viết câu trả lời JSON rồi đưa vào offline_answer."""
    from . import stage_director as sd
    base = base_dir(data_dir, pid, seg["stage"])
    k1 = ensure_k1_seg(seg, base)
    inputs, missing = inputs_for(conn, pid, seg, k1, stored_state_before(data_dir, pid, seg, conn))
    with open(os.path.join(k1, "stage.json"), encoding="utf-8") as f:
        marks = json.load(f).get("marks")
    return sd.build_prompt(inputs) + format_example(inputs), missing + preflight(inputs, marks)


def offline_answer(conn, pid: int, seg: Dict, data_dir: str, obj: Dict, source: str = "claude_code",
                   log: Callable[[str], None] = lambda m: None) -> Dict:
    """Câu trả lời Đạo diễn VIẾT NGOÀI (người / phiên Claude Code) thay cho lời gọi Claude — 0 USD. Chạy đúng các bước của run_segment:
    bộ kiểm (luật kịch bản + K3) → K3 + K4 Blender → số đo (post_checks). Lỗi → {"ok": False, "errors": [...]} (người viết sửa rồi
    chạy lại, không ghi máy); đạt → ghi stage_camera như đường thường, result.json ghi nguồn `source` + 0 USD."""
    import copy as _c
    from . import llm_io
    from . import stage_director as sd
    out_res: Dict = {"ok": False, "errors": [], "applied": [], "removed": [], "soft": {}}
    base = base_dir(data_dir, pid, seg["stage"])
    k1 = ensure_k1_seg(seg, base, log)
    inputs, missing = inputs_for(conn, pid, seg, k1, stored_state_before(data_dir, pid, seg, conn))
    with open(os.path.join(k1, "stage.json"), encoding="utf-8") as f:
        st = json.load(f)
    gate = preflight(inputs, st.get("marks"))
    if missing or gate:
        out_res["errors"] = missing + [f"cổng 0 USD chưa qua — {g}" for g in gate]
        return out_res
    obj = _c.deepcopy(obj)
    try:
        sd.validate_answer(obj, inputs, st.get("marks"))
    except (llm_io.SchemaError, ValueError, KeyError, TypeError) as e:
        out_res["errors"] = [x for x in str(e).split("; ") if x]
        return out_res
    out = os.path.join(base, f"doan_{key_of(seg['scene'])}")
    os.makedirs(out, exist_ok=True)
    rd = os.path.join(out, "cc_" + time.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(rd, exist_ok=True)
    bl = dict(obj["blocking"], place=inputs["place"], spot=inputs["spot"], aspect=inputs["aspect"])
    for fn, data in (("answer.json", obj), ("blocking.json", bl), ("shot_specs.json", {"shots": obj["shot_specs"]}),
                     ("inputs.json", inputs)):
        with open(os.path.join(rd, fn), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    try:
        solve, v2 = tool().v2_run(bl, obj["shot_specs"], rd, k1, m3=seg["entry"], reach=True, log=log)
    except Exception as e:  # noqa: BLE001 - rà 16/10: lỗi Blender ghi vào errors (người viết thấy trong .loi.txt)
        out_res["errors"] = [f"không đo được máy bằng Blender (K4): {type(e).__name__}: {e}"]
        return out_res
    out_res["top_beats"] = draw_beats(rd, log)            # cả khi lỗi: người viết câu trả lời xem nhịp để sửa
    errors = sd.feedback_from(solve, v2) + [f"shot {k}: {v}" for k, v in sorted(post_checks(inputs, v2).items())]
    out_res["soft"] = soft_checks(inputs, v2)
    out_res["dir"] = rd
    if errors:
        out_res["errors"] = errors
        return out_res
    try:
        colours = mannequin_colours(solve["beats"], {p["key"]: p["label"] for p in inputs["people"]})
    except (ValueError, KeyError, TypeError):
        colours = {}
    cams, bad = cameras_from(st, v2, seg["id"], rd, colours)
    for s in seg["shots"]:
        if s["idx"] not in cams and s["idx"] not in bad and s["idx"] not in (inputs.get("bo_qua") or []):
            bad[s["idx"]] = "bộ giải không đặt được máy (lỗi yêu cầu khung)"
    fp = fingerprint(inputs)
    for cam in cams.values():
        cam["inputs_fp"] = fp
        cam["source"] = cam["source"] + f" · Đạo diễn ngoại tuyến ({source}, 0 USD)"
    missing_guides = guides_missing(cams)
    res = {"cams": cams, "bad": bad, "missing": [], "state": end_state(st, obj, seg["scene"]), "fp": fp, "guide_missing": missing_guides,
           "round": os.path.relpath(rd, out), "nguon": source, "usd": 0.0, "soft": out_res["soft"]}
    with open(os.path.join(out, "inputs.json"), "w", encoding="utf-8") as f:
        json.dump(inputs, f, ensure_ascii=False, indent=1)
    _save(os.path.join(out, "result.json"), res)
    changed = apply(conn, seg, cams, inputs.get("bo_qua") or [])
    out_res.update(ok=not bad and not missing_guides, applied=[i for i in changed if i in cams],
                   removed=[i for i in changed if i not in cams], bad=bad, guide_missing=missing_guides)
    _say(conn, pid, "info", f"Sân khấu {seg['id']}: máy đặt từ câu trả lời Đạo diễn NGOẠI TUYẾN ({source}, 0 USD) — shot "
                            + ", ".join(map(str, sorted(cams))), log)
    held: Dict = {"held": []}
    _say_guides(conn, pid, seg, res, held, log)
    out_res["held"] = held["held"]
    return out_res


def round_blocking(bl: Dict, inputs: Dict) -> Dict:
    """blocking.json của một lượt (dạng mọi người đọc: world_map, change_review, shot_lessons, stage_solver): dàn cảnh + place / spot /
    aspect của đầu vào."""
    return dict(bl, place=inputs["place"], spot=inputs["spot"], aspect=inputs["aspect"])


def fill_round_files(rd: str) -> List[str]:
    """Bù blocking.json + shot_specs.json còn thiếu của một lượt TỪ answer.json + inputs.json của chính lượt đó (23/10: crew/final
    trước bản sửa không ghi hai tệp này → cảnh rơi khỏi bản đồ 3D). Không ghi đè tệp đã có. Trả tên tệp đã ghi."""
    with open(os.path.join(rd, "answer.json"), encoding="utf-8") as f:
        ans = json.load(f)
    with open(os.path.join(rd, "inputs.json"), encoding="utf-8") as f:
        inputs = json.load(f)
    wrote = []
    for fn, data in (("blocking.json", round_blocking(ans["blocking"], inputs)), ("shot_specs.json", {"shots": ans["shot_specs"]})):
        path = os.path.join(rd, fn)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            wrote.append(fn)
    return wrote


# ---- CHIA VAI (cờ stage_crew — docs/KE_HOACH_CHIA_VAI_SAN_KHAU_2026-10-16.md) ----------------------------------------------------
CREW_DIR = "crew"


def _crew_ctx(conn, pid: int, seg: Dict, data_dir: str, prev_state: Optional[Dict] = None, stored: bool = True,
              log: Callable[[str], None] = lambda m: None) -> Dict:
    base = base_dir(data_dir, pid, seg["stage"])
    k1 = ensure_k1_seg(seg, base, log)
    inputs, missing = inputs_for(conn, pid, seg, k1, stored_state_before(data_dir, pid, seg, conn) if stored else prev_state)
    with open(os.path.join(k1, "stage.json"), encoding="utf-8") as f:
        st = json.load(f)
    out = os.path.join(base, f"doan_{key_of(seg['scene'])}")
    return {"k1": k1, "inputs": inputs, "missing": missing, "st": st, "out": out, "crew": os.path.join(out, CREW_DIR),
            "fp": fingerprint(inputs), "seg": seg}


def _crew_load(ctx: Dict) -> Optional[Dict]:
    try:
        with open(os.path.join(ctx["crew"], "state.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _crew_save(ctx: Dict, state: Dict) -> None:
    os.makedirs(ctx["crew"], exist_ok=True)
    with open(os.path.join(ctx["crew"], "state.json"), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def _crew_reset(ctx: Dict) -> None:
    """Cất lượt chia vai cũ (crew/ → crew_cu_<giờ>/) — không ghi đè câu trả lời đã có."""
    import shutil
    if os.path.isdir(ctx["crew"]):
        shutil.move(ctx["crew"], os.path.join(ctx["out"], "crew_cu_" + time.strftime("%Y%m%d_%H%M%S")))


def _crew_measure(ctx: Dict, log: Callable[[str], None]):
    """measure(bl, specs) cho stage_crew.ingest: K3 + K4 Blender (0 USD) vào crew/m<n>/ + top_beats.png → (thư mục tương đối, v2)."""
    def measure(bl: Dict, specs: List[Dict]):
        os.makedirs(ctx["crew"], exist_ok=True)
        n = 1 + sum(1 for d in os.listdir(ctx["crew"]) if re.fullmatch(r"m\d+", d))
        rd = os.path.join(ctx["crew"], f"m{n}")
        os.makedirs(rd, exist_ok=True)
        inputs = ctx["inputs"]
        full = round_blocking(bl, inputs)
        for fn, data in (("answer.json", {"blocking": bl, "shot_specs": specs}), ("blocking.json", full),
                         ("shot_specs.json", {"shots": specs}), ("inputs.json", inputs)):
            with open(os.path.join(rd, fn), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
        _solve, v2 = tool().v2_run(full, specs, rd, ctx["k1"], m3=ctx["seg"]["entry"], reach=True, log=log)
        v2 = dict(v2 or {}, s0=(_solve or {}).get("s0"))
        for fn, data in (("v2.json", v2), ("setups.json", {"beats": (_solve or {}).get("beats") or {}})):
            if not os.path.exists(os.path.join(rd, fn)):  # v2_run thật đã ghi; giữ chắc cho bảng đối chiếu / màu người nộm đọc lại
                with open(os.path.join(rd, fn), "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)
        draw_beats(rd, log)
        return os.path.relpath(rd, ctx["out"]).replace(os.sep, "/"), v2
    return measure


def _crew_v2(ctx: Dict, rel: str) -> Dict[int, Dict]:
    with open(os.path.join(ctx["out"], rel, "v2.json"), encoding="utf-8") as f:
        return {s["shot"]: s for s in json.load(f).get("shots") or []}


def _crew_score(entry: Optional[Dict]) -> Tuple:
    """Xếp lần đo của MỘT shot (nhỏ = tốt): đạt luật khung, C1, số luật hỏng (cả khung cuối)."""
    b = (entry or {}).get("best") or {}
    if not b:
        return (1, 1, 99)
    fails = len((b.get("check") or {}).get("fail") or []) + len((((b.get("end") or {}).get("check") or {}).get("fail")) or [])
    return (0 if b.get("ok") else 1, 0 if b.get("c1_ok", True) else 1, fails)


def _crew_pick(ctx: Dict, state: Dict, k: str) -> str:
    """Tối ưu 16/10 (ca thử: lần đo m3 tốt hơn m4 mà luồng giữ lần CUỐI): lần đo Quay phim đã duyệt (khop / giu_lech); không có thì
    lần đo ít lỗi nhất trong mọi lần đo của shot (hòa → lần sau)."""
    acc = (state.get("accepted") or {}).get(k)
    if acc:
        return acc
    hist = (state.get("shot_hist") or {}).get(k) or [state["shot_measure"][k]]
    ok_hist = [r for r in hist if r not in ((state.get("rejected") or {}).get(k) or [])] or hist[-1:]   # bỏ lần đo Quay phim đã bác
    return min(enumerate(ok_hist), key=lambda x: (_crew_score(_crew_v2(ctx, x[1]).get(int(k))), -x[0]))[1]


def _crew_merged(ctx: Dict, state: Dict, best: bool = False) -> Dict:
    """v2 GHÉP theo shot (tối ưu 16/10: chỉ đo lại shot đổi): mỗi shot lấy số đo từ lần đo hiện tại của nó (`best` = lần chốt), ảnh clay
    thành đường dẫn tuyệt đối, `_rd` = thư mục lần đo. State cũ (trước 16/10 chiều) không có shot_measure → lần đo cuối cho mọi shot."""
    import copy as _c
    sm = state.get("shot_measure") or {str(sh): state["measure"] for sh in _crew_v2(ctx, state["measure"])}
    shots = []
    for k in sorted(sm, key=int):
        rel = _crew_pick(ctx, dict(state, shot_measure=sm), k) if best else sm[k]
        e = _c.deepcopy(_crew_v2(ctx, rel).get(int(k)))
        if not e:
            continue
        rd = os.path.join(ctx["out"], rel)
        for b in (e.get("best") or {}, ((e.get("best") or {}).get("end") or {})):
            if b.get("clay"):
                b["clay"] = os.path.abspath(os.path.join(rd, b["clay"]))
        e["_rd"], e["_rel"] = os.path.abspath(rd), rel
        shots.append(e)
    return {"shots": shots}


def _crew_colours(ctx: Dict, rd: str) -> Dict[str, str]:
    try:
        with open(os.path.join(rd, "setups.json"), encoding="utf-8") as f:
            return mannequin_colours(json.load(f).get("beats") or {}, {p["key"]: p["label"] for p in ctx["inputs"]["people"]})
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def _crew_view(ctx: Dict, state: Dict, limit: Optional[int] = None) -> Tuple[Optional[Dict], List[str], List[Tuple[str, str]]]:
    """(bảng đối chiếu, dòng thêm: màu người nộm + tệp ảnh, ảnh (nhãn, đường dẫn) cho API) của lần đo cuối. `limit` (API: MAX_IMAGES):
    ưu tiên top_beats + clay của shot CÓ VẤN ĐỀ (Blender hỏng, vật chắn, kết luận trước chưa khớp); ảnh không gửi được nêu rõ."""
    from . import stage_crew as sc
    if not state.get("measure"):
        return None, [], []
    rd = os.path.join(ctx["out"], state["measure"])
    v2 = _crew_merged(ctx, state)                         # số đo hiện tại của TỪNG shot (shot không sửa giữ lần đo cũ)
    table = sc.compare_table(ctx["inputs"], state["specs"], v2, state.get("keep"), post_checks(ctx["inputs"], v2))
    for k, why in (state.get("measure_errors") or {}).items():
        if table is not None:
            table[int(k)] = [f"KHÔNG CÓ SỐ ĐO — {why}"]
    for e in v2["shots"]:
        if e["_rel"] != state["measure"] and e["shot"] in (table or {}):
            table[e["shot"]].append(f"(số đo giữ từ lần đo {e['_rel']} — shot này không sửa ở lượt trước)")
    colours = _crew_colours(ctx, rd)
    images, later = [], []
    full = os.path.join(ctx["out"], state.get("full_measure") or state["measure"])
    if os.path.exists(os.path.join(full, "top_beats.png")):     # rà 16/10: lần đo một phần chỉ có máy của shot vừa sửa
        images.append(("ảnh nhìn từ trên theo nhịp (top_beats, lần đo đầy đủ " + (state.get("full_measure") or state["measure"])
                       + " — máy shot sửa sau xem ở ảnh clay)", os.path.join(full, "top_beats.png")))
    verdicts = state.get("verdicts") or {}
    for s in sorted(v2.get("shots") or [], key=lambda x: x["shot"]):
        clay = (s.get("best") or {}).get("clay")
        if not (clay and os.path.exists(clay)):
            continue
        rows = " ".join((table or {}).get(s["shot"]) or [])
        issue = "HỎNG" in rows or "GIỮA máy" in rows or (verdicts.get(str(s["shot"])) or {}).get("ket_luan") not in (None, "khop")
        (images if issue or limit is None else later).append((f"ảnh clay shot {s['shot']}", clay))
    cut: List[Tuple[str, str]] = []
    if limit is not None:
        images, cut = (images + later)[:limit], (images + later)[limit:]
    extra = sc.colour_lines(colours) + ["", "## Ảnh của lần đo này (đọc từng ảnh)"] + [f"- {lab}: {p}" for lab, p in images]
    if cut:
        extra.append(f"- KHÔNG gửi kèm (vượt trần {limit} ảnh / lời gọi; shot không có vấn đề trước): " + ", ".join(lab for lab, _ in cut))
    return table, extra, images


def crew_prompt(conn, pid: int, seg: Dict, data_dir: str, reset: bool = False) -> Tuple[str, List[str], Dict]:
    """NGOẠI TUYẾN 0 USD: (đề bài của vai đang tới lượt, vấn đề, state). Người / phiên Claude Code đóng vai đó rồi đưa câu trả lời vào
    crew_answer. `reset` = cất lượt cũ, bắt đầu lại từ Đạo diễn."""
    from . import stage_crew as sc
    ctx = _crew_ctx(conn, pid, seg, data_dir)
    problems = list(ctx["missing"]) + preflight(ctx["inputs"], ctx["st"].get("marks"))
    if reset:
        _crew_reset(ctx)
    state = _crew_load(ctx)
    if state is not None and state["fp"] != ctx["fp"]:
        problems.append("đầu vào (kịch bản / Kho / cảnh trước) đã đổi so với lượt chia vai đang dở — chạy lại với --crew-reset")
    state = state or sc.new_state(ctx["fp"])
    _crew_save(ctx, state)
    if state["phase"] == "xong":
        return "", problems + ["lượt chia vai đã xong (đã ghi máy) — --crew-reset để làm lại"], state
    if state["phase"] == "duyet" and sc.user_approves():
        return "", problems + ["chờ NGƯỜI DÙNG duyệt ảnh ghép (--beats) rồi --crew-approve / --crew-tra-lai"], state
    table, extra, _ = _crew_view(ctx, state)
    return sc.prompt_for(state, ctx["inputs"], table, extra), problems, state


def crew_answer(conn, pid: int, seg: Dict, data_dir: str, obj: Dict, source: str = "claude_code",
                log: Callable[[str], None] = lambda m: None, who: Optional[Dict] = None, expected_revs: Optional[Dict] = None) -> Dict:
    """NGOẠI TUYẾN 0 USD: câu trả lời của vai đang tới lượt → bộ kiểm của vai → bước sau (đo K3 + K4 khi cần). Xong → ghi stage_camera.
    Lỗi → {"ok": False, "errors"} (người viết sửa rồi đưa lại, state không đổi)."""
    import copy as _c
    from . import llm_io
    from . import stage_crew as sc
    ctx = _crew_ctx(conn, pid, seg, data_dir, log=log)
    res: Dict = {"ok": False, "errors": [], "phase": None}
    state = _crew_load(ctx)
    if state is None:
        state = sc.new_state(ctx["fp"])
    if ctx["missing"] or state["fp"] != ctx["fp"]:
        res["errors"] = ctx["missing"] or ["đầu vào đã đổi so với lượt chia vai đang dở — --crew-reset"]
        return res
    res["phase"] = state["phase"]
    if state["phase"] == "xong":
        res["errors"] = ["lượt chia vai đã xong — --crew-reset để làm lại"]
        return res
    if state["phase"] == "duyet" and sc.user_approves() and source != "nguoi_dung":
        # rà 16/10 (quyết định stage-crew-plan-2026-10-16 (1)): duyệt chốt chỉ do NGƯỜI DÙNG — phiên Claude không tự duyệt
        res["errors"] = ["bước duyệt chốt chỉ nhận từ người dùng (--crew-approve / --crew-tra-lai sau khi người dùng nói trong chat)"]
        return res
    gate = preflight(ctx["inputs"], ctx["st"].get("marks"))
    if gate:
        res["errors"] = [f"cổng 0 USD chưa qua — {g}" for g in gate]
        return res
    obj = _c.deepcopy(obj)
    try:
        sc.validator(state, ctx["inputs"], ctx["st"].get("marks"))(obj)
    except (llm_io.SchemaError, ValueError, KeyError, TypeError) as e:
        res["errors"] = [x for x in str(e).split("; ") if x]
        return res
    os.makedirs(ctx["crew"], exist_ok=True)
    with open(os.path.join(ctx["crew"], f"answer_{len(state['history']) + 1:02d}_{state['phase']}.json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    try:
        sc.ingest(state, obj, _crew_measure(ctx, log), source)
    except Exception as e:  # noqa: BLE001 - Blender đo lỗi: state cũ giữ nguyên (không lưu), nói rõ
        res["errors"] = [f"không đo được (K3 / K4): {type(e).__name__}: {e}"]
        return res
    _crew_save(ctx, state)
    res.update(ok=True, phase=state["phase"], measure=state.get("measure"))
    if state.get("can_hoi"):
        res["can_hoi"] = state["can_hoi"]
    if state["phase"] == "xong":
        res.update(_crew_finalize(conn, pid, seg, ctx, state, _worker(state), log, apply_now=True, who=who,
                                  expected_revs=expected_revs))
        held: Dict = {"held": []}
        _say_guides(conn, pid, seg, res["result"], held, log)
        res["held"] = held["held"]
    return res


def _worker(state: Dict) -> str:
    """Nguồn của các câu trả lời đã làm việc (không tính lượt duyệt của người dùng) — chi phí / nguồn ghi đúng khi người dùng duyệt
    sau lượt API."""
    srcs = [h.get("source") for h in state.get("history") or [] if h.get("source") and h.get("source") != "nguoi_dung"]
    return srcs[-1] if srcs else "claude_code"


CREW_PREVIEW = "xem_ghep"                                 # crew/xem_ghep/: lượt ghép tạm cho tấm ghép N5 TRƯỚC khi duyệt (không phải lượt chốt)


def _crew_assemble(out: str, state: Dict, v2: Dict, rd: str, inputs: Optional[Dict] = None) -> None:
    """Gom một lượt GHÉP theo shot vào `rd`: tệp sân khấu (nền, lưới, top_cut…) của lần đo đầy đủ + đặc tả / v2 của lần đo ĐƯỢC CHỌN
    từng shot (`v2` = _crew_merged(best=True)). crew/final (chốt) và crew/xem_ghep (N5 xem trước duyệt, 24/10) dựng CÙNG một cách →
    ảnh người duyệt xem đúng máy N6 sẽ ghi. `inputs` None (xem trước) → bỏ inputs.json / blocking.json (chỉ lượt chốt cần)."""
    import shutil
    from . import stage_crew as _sc
    os.makedirs(rd, exist_ok=True)
    src = os.path.join(out, state.get("full_measure") or state["measure"])
    for fn in ("stage.json", "grid.json", "cfg.json", "setups.json", "top_raw.png", "top_cut.png", "top_cut.json"):
        if os.path.exists(os.path.join(src, fn)):
            shutil.copyfile(os.path.join(src, fn), os.path.join(rd, fn))
    picked_spec = {e["shot"]: e.get("spec") for e in v2["shots"] if e.get("spec")}
    specs_ = [{k: v for k, v in (picked_spec.get(sp["shot"]) or sp).items() if k not in ("_near", "doi_phia")}
              for sp in state["specs"]]                   # rà 16/10: đặc tả của LẦN ĐO ĐƯỢC CHỌN (rerender giải lại đúng máy đã chốt)
    bl_ = _sc.measure_blocking(state)
    # 23/10: final là lượt result.json trỏ tới → phải có blocking.json + shot_specs.json như lượt đo m<n> (world_map / change_review /
    # shot_lessons đọc; thiếu thì cảnh chốt qua chia vai rơi khỏi bản đồ 3D — #31 cảnh 3)
    files = [("answer.json", {"blocking": bl_, "shot_specs": specs_})]
    if inputs is not None:
        files += [("inputs.json", inputs), ("blocking.json", round_blocking(bl_, inputs))]
    files += [("shot_specs.json", {"shots": specs_}),
              ("v2.json", {"shots": [{k: v for k, v in e.items() if not k.startswith("_")} for e in v2["shots"]],
                           "picked": {str(e["shot"]): e["_rel"] for e in v2["shots"]}})]
    for fn, data in files:
        with open(os.path.join(rd, fn), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)


def crew_preview(data_dir: str, pid: int, seg: Dict) -> Optional[Dict]:
    """N5 (24/10, #34): lượt chia vai ĐANG DỞ / chờ duyệt (đã có lần đo, phase chưa 'xong') → dựng crew/xem_ghep/ ghép từng shot theo
    ĐÚNG lần đo N6 / crew_user_verdict sẽ chốt (_crew_merged(best=True) → _crew_pick: lần chọn N14 / Quay phim duyệt, không có thì lần
    ít lỗi nhất) — không lấy lặng lần đo đầy đủ đầu. Trả {"dir", "picked": {shot: lần đo}, "notes"} hoặc None (không có lượt chia vai
    dở). Shot không xác định được lần đo → nêu trong notes."""
    import shutil
    out = os.path.join(base_dir(data_dir, pid, seg["stage"]), f"doan_{key_of(seg['scene'])}")
    ctx = {"out": out, "crew": os.path.join(out, CREW_DIR)}
    state = _crew_load(ctx)
    if not state or not state.get("measure") or state.get("phase") == "xong":
        return None
    v2 = _crew_merged(ctx, state, best=True)
    rd = os.path.join(ctx["crew"], CREW_PREVIEW)
    shutil.rmtree(rd, ignore_errors=True)                 # lượt ghép tạm: dựng lại sạch mỗi lần (không giữ top_cut / ảnh của lần trước)
    _crew_assemble(out, state, v2, rd)
    picked = {e["shot"]: e["_rel"] for e in v2["shots"]}
    errs = state.get("measure_errors") or {}
    staged = {int(sp["shot"]) for sp in state.get("specs") or []}
    notes = []
    for n in sorted(staged - set(picked)):
        notes.append(f"shot {n}: không xác định được lần đo ({errs.get(str(n)) or 'không có số đo trong lần đo nào'}) — tấm ghép "
                     "KHÔNG có máy shot này")
    for s in seg.get("shots") or []:
        if s["idx"] not in staged and s["idx"] not in picked:
            notes.append(f"shot {s['idx']}: không có trong đặc tả tổ sân khấu (bỏ qua / máy nền thường) — không có máy trên tấm ghép")
    return {"dir": rd, "picked": picked, "notes": notes}


def render_beats_sheet(data_dir: str, pid: int, seg: Dict, output: str,
                       log: Callable[[str], None] = lambda m: None) -> Dict:
    """Vẽ tấm ghép N5/CLI từ cùng lượt crew preview hoặc lượt đã lưu hiện hành (0 USD, không ghi CSDL)."""
    try:
        preview = crew_preview(data_dir, pid, seg)
    except Exception as exc:  # noqa: BLE001 - trạng thái crew không hợp lệ phải lỗi theo cảnh, không dừng CLI/N5
        return {"ok": False, "errors": [f"không ghép được lần đo từng shot của lượt chia vai "
                                          f"({type(exc).__name__}) — không dựng tấm ghép bằng lần đo khác"]}

    notes: List[str] = []
    picked = None
    if preview is not None:
        source_dir, picked = preview["dir"], preview["picked"]
        notes.extend(preview["notes"])
        if picked:
            notes.append("lần đo từng shot (máy N6 sẽ chốt): "
                         + ", ".join(f"shot {shot} ← {picked[shot]}" for shot in sorted(picked)))
    else:
        source_dir = result_round(data_dir, pid, seg)
    if source_dir is None or not os.path.isdir(source_dir):
        return {"ok": False, "errors": ["chưa có lượt đã lưu / lần đo nào để dựng tấm ghép"]}

    renderer = tool()
    if not os.path.exists(os.path.join(source_dir, "top_cut.png")):
        log("cắt mái (Blender)")
        try:
            renderer.top_cut(source_dir, log=log)
        except Exception as exc:  # noqa: BLE001 - vẫn vẽ trên ảnh chưa cắt (như CLI/N5)
            notes.append(f"không cắt được mái ({type(exc).__name__}: {exc}) — vẽ trên ảnh từ trên thường")
    try:
        log("vẽ nhịp + ghép")
        renderer.draw_beats(source_dir)
        os.makedirs(os.path.dirname(output), exist_ok=True)
        title = (f"#{pid} cảnh {seg['scene']} — {seg['id']} "
                 f"(shot {seg['shots'][0]['idx']}–{seg['shots'][-1]['idx']})")
        if picked:
            title += " · lần đo: " + ", ".join(
                f"{shot}←{os.path.basename(picked[shot])}" for shot in sorted(picked)
            )
        path = renderer.stage_sheet(source_dir, title, output)
    except Exception as exc:  # noqa: BLE001 - một cảnh lỗi không chặn các cảnh khác ở CLI
        return {"ok": False, "errors": [f"không vẽ được tấm ghép ({type(exc).__name__}: {exc})"]}
    result = {"ok": True, "path": path if isinstance(path, str) else output,
              "notes": notes, "nguon": "crew_preview" if preview is not None else "luot_hien_tai"}
    if picked is not None:
        result["lan_do"] = {str(shot): round_name for shot, round_name in sorted(picked.items())}
    return result


def _crew_finalize(conn, pid: int, seg: Dict, ctx: Dict, state: Dict, source: str, log: Callable[[str], None],
                   apply_now: bool, who: Optional[Dict] = None, expected_revs: Optional[Dict] = None) -> Dict:
    """Máy chốt TỪNG SHOT (tối ưu 16/10): lần đo Quay phim đã duyệt, không có thì lần đo ít lỗi nhất của shot; shot đạt Blender + luật
    kịch bản, không còn 'unresolved' → stage_camera. Gom vào crew/final/ (answer + inputs + v2 ghép + tệp sân khấu) để --beats /
    rerender dùng như một lượt; result.json như đường một vai."""
    inputs, st = ctx["inputs"], ctx["st"]
    v2 = _crew_merged(ctx, state, best=True)
    waived = {}
    for e in v2["shots"]:
        # Quay phim GIỮ LỆCH có chủ ý + nêu tên luật khung được miễn (bo_luat, trừ P1): lần đo chỉ hỏng đúng các luật đó → coi như đạt
        w = set((state.get("waive") or {}).get(str(e["shot"])) or [])
        b = e.get("best") or {}
        fails = list((b.get("check") or {}).get("fail") or []) + [f"cuoi:{f}" for f in (((b.get("end") or {}).get("check") or {})
                                                                                      .get("fail") or [])]
        if w and b and not b.get("ok") and b.get("c1_ok", True) and fails and all(f in w or f.split(":")[-1] in w for f in fails):
            b["ok"] = True
            waived[e["shot"]] = fails
    cams, bad = {}, {}
    for e in v2["shots"]:
        c_, b_ = cameras_from(st, {"shots": [e]}, seg["id"], e["_rd"], _crew_colours(ctx, e["_rd"]))
        cams.update(c_)
        bad.update(b_)
    rd = os.path.join(ctx["crew"], "final")
    _crew_assemble(ctx["out"], state, v2, rd, inputs)
    draw_beats(rd, log)
    for k, why in list(post_checks(inputs, v2).items()) + [(int(k), v) for k, v in (state.get("unresolved") or {}).items()]:
        if k in cams:
            cams.pop(k)
        bad[k] = why
    for s in seg["shots"]:
        if s["idx"] not in cams and s["idx"] not in bad and s["idx"] not in (inputs.get("bo_qua") or []):
            bad[s["idx"]] = "bộ giải không đặt được máy (lỗi yêu cầu khung)"
    for idx, cam in cams.items():
        cam["inputs_fp"] = ctx["fp"]
        cam["source"] += f" · tổ sân khấu (Đạo diễn + Quay phim, {source}; duyệt: {state.get('approved_by')})"
        if idx in waived:
            cam["source"] += f" · Quay phim giữ lệch, miễn {', '.join(waived[idx])}: {(state.get('keep') or {}).get(str(idx))}"
    res = {"cams": cams, "bad": bad, "missing": [], "state": end_state(st, {"blocking": state["blocking"], "shot_specs": state["specs"]},
                                                                      seg["scene"]),
           "fp": ctx["fp"], "guide_missing": guides_missing(cams), "round": f"{CREW_DIR}/final", "nguon": source,
           "soft": soft_checks(inputs, v2),
           "crew": {k: state.get(k) for k in ("verdicts", "keep", "replies", "unresolved", "approved_by", "reviews", "n_measure",
                                                 "accepted", "s0", "n_returns")} | {"picked": {str(e["shot"]): e["_rel"] for e in v2["shots"]}}}
    if source != "claude_api":
        res["usd"] = 0.0
    with open(os.path.join(ctx["out"], "inputs.json"), "w", encoding="utf-8") as f:
        json.dump(inputs, f, ensure_ascii=False, indent=1)
    _save(os.path.join(ctx["out"], "result.json"), res)
    out = {"result": res}
    if apply_now:
        changed = apply(conn, seg, cams, inputs.get("bo_qua") or [], who=who, expected_revs=expected_revs)
        out.update(applied=[i for i in changed if i in cams], removed=[i for i in changed if i not in cams], bad=bad)
        _say(conn, pid, "info", f"Sân khấu {seg['id']}: máy đặt bởi tổ sân khấu (Đạo diễn + Quay phim, {source}) — shot "
                                + ", ".join(map(str, sorted(cams))), log)
    return out


def crew_user_verdict(conn, pid: int, seg: Dict, data_dir: str, approve: bool, tra_lai: Sequence[Dict] = (),
                      log: Callable[[str], None] = lambda m: None, who: Optional[Dict] = None,
                      expected_revs: Optional[Dict] = None) -> Dict:
    """Bước duyệt chốt do NGƯỜI DÙNG (cờ stage_crew_user_approve; #31 — người dùng 16/10): Claude chỉ gọi khi người dùng đã nói duyệt /
    trả lại trong chat. `who` / `expected_revs`: bàn đạo diễn (M4.8) — máy ghi qua write guard với actor người bấm."""
    obj = {"duyet": True} if approve else {"duyet": False, "tra_lai": list(tra_lai)}
    return crew_answer(conn, pid, seg, data_dir, obj, source="nguoi_dung", log=log, who=who, expected_revs=expected_revs)


def run_segment_crew(conn, pid: int, seg: Dict, data_dir: str, client, prev_state: Optional[Dict] = None,
                     log: Callable[[str], None] = lambda m: None, force: bool = False) -> Dict:
    """Như run_segment nhưng CHIA VAI qua API (sổ chi theo từng vai). Bước duyệt chốt chờ người dùng (cờ stage_crew_user_approve) →
    shot giữ ở cổng, state lưu để làm tiếp."""
    from . import llm_runner
    from . import stage_crew as sc
    res: Dict = {"cams": {}, "bad": {}, "missing": [], "state": None, "reused": False}
    try:
        ensure_k1_seg(seg, base_dir(data_dir, pid, seg["stage"]), log)
    except Exception as e:  # noqa: BLE001 - Blender / model 3D: nói rõ, đoạn không chạy
        res["missing"].append(f"không đo được sân khấu K1 chỗ đứng '{seg['main_spot']}': {type(e).__name__}: {e}")
        return res
    ctx = _crew_ctx(conn, pid, seg, data_dir, prev_state, stored=False, log=log)
    inputs = ctx["inputs"]
    if ctx["missing"]:
        res["missing"], res["stale"] = ctx["missing"], True
        return res
    res["bo_qua"] = inputs["bo_qua"]
    if not inputs["shots"]:
        log(f"Sân khấu {seg['id']}: shot {', '.join(map(str, inputs['bo_qua']))} không người / đạo cụ — không dàn, dùng máy nền thường")
        res["skipped_all"] = True
        return res
    fp = ctx["fp"]
    res["stale"] = any((s["data"].get(FIELD) or {}).get("auto") and (s["data"].get(FIELD) or {}).get("inputs_fp") != fp
                       for s in seg["shots"])
    path = os.path.join(ctx["out"], "result.json")
    if os.path.exists(path) and not force:
        try:
            with open(path, encoding="utf-8") as f:
                old = json.load(f)
            if old.get("fp") == fp and "crew" in old:
                return dict(old, cams={int(k): v for k, v in old["cams"].items()}, bad={int(k): v for k, v in old["bad"].items()},
                            reused=True)
        except (OSError, ValueError, KeyError):
            pass
    gate = preflight(inputs, ctx["st"].get("marks"))
    if gate:
        res["missing"] += [f"cổng 0 USD chưa qua — {g}" for g in gate]
        return res
    if client is None:
        res["missing"].append("chưa cấu hình Claude (" + llm_runner.missing_hint() + ") — tổ sân khấu chưa dàn cảnh")
        return res
    state = _crew_load(ctx)
    if state is None or state["fp"] != fp or force or state["phase"] == "xong":
        if state is not None:
            _crew_reset(ctx)
        state = sc.new_state(fp)
    os.makedirs(ctx["crew"], exist_ok=True)
    _say(conn, pid, "info", f"Sân khấu {seg['id']} (chia vai): Đạo diễn + Quay phim — ước tính {_crew_estimate(conn)} / cảnh", log)
    measure = _crew_measure(ctx, log)
    for step in range(12):                                # chặn vòng: 1 + 1 + ≤ 2 duyệt + 1 trả lời + ≤ 2 duyệt chốt + dư
        if state["phase"] == "xong":
            break
        if state["phase"] == "duyet" and sc.user_approves():
            _crew_save(ctx, state)
            why = (f"chờ người dùng duyệt sân khấu (ảnh ghép: py tools/stage_auto.py --project {pid} --scene {seg['scene']} --beats "
                   f"<thư mục>) rồi --crew-approve / --crew-tra-lai")
            res["bad"] = {s["idx"]: why for s in seg["shots"] if s["idx"] not in (inputs.get("bo_qua") or [])}
            res["waiting"] = why
            return res
        stage = sc.ROLES[state["phase"]][0]
        review = state["phase"] in ("quay_phim_duyet", "duyet")
        table, extra, images = _crew_view(ctx, state, limit=llm_runner.MAX_IMAGES if review else None)
        text = sc.prompt_for(state, inputs, table, extra if review else [], cache_break=llm_runner.CACHE_BREAK)
        n = len(state["history"]) + 1
        with open(os.path.join(ctx["crew"], f"prompt_{n:02d}_{state['phase']}.md"), "w", encoding="utf-8") as f:
            f.write(text)
        imgs = images if review else []
        try:
            with llm_runner.tagged(stage, pid):
                obj, tin, tout = llm_runner.ask_json(client, text, sc.validator(state, inputs, ctx["st"].get("marks")), images=imgs,
                                                     note=log, bad_reply=_keep_reply(conn, pid, seg, ctx["crew"], n))
        except llm_runner.LlmError as e:
            _crew_save(ctx, state)
            if getattr(e, "code", None) != "bad_json":
                raise
            res["missing"].append(f"tổ sân khấu ({state['phase']}) trả lời sai mẫu 2 lần: {str(e)[:200]}")
            return _save(path, dict(res, fp=fp, crew={"failed": state["phase"]}))     # rà 16/10: lượt sau KHÔNG gọi lại (trả tiền lặp)
        with open(os.path.join(ctx["crew"], f"answer_{n:02d}_{state['phase']}.json"), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        log(f"Sân khấu {seg['id']} · {state['phase']}: vào {tin} / ra {tout} token")
        try:
            sc.ingest(state, obj, measure, "claude_api")
        except Exception as e:  # noqa: BLE001 - Blender đo lỗi: nói rõ, không gán máy chưa đo
            _crew_save(ctx, state)
            res["missing"].append(f"không đo được máy bằng Blender (K4): {type(e).__name__}: {e}")
            return _save(path, dict(res, fp=fp, crew={"failed": state["phase"]}))
        if state.get("can_hoi"):
            _say(conn, pid, "warn", f"Sân khấu {seg['id']}: Đạo diễn hỏi — {state.pop('can_hoi')}", log)
        _crew_save(ctx, state)
    if state["phase"] != "xong":
        res["missing"].append(f"tổ sân khấu chưa xong sau 12 bước (đang ở '{state['phase']}')")
        return res
    fin = _crew_finalize(conn, pid, seg, ctx, state, "claude_api", log, apply_now=False)["result"]
    return dict(fin, bo_qua=inputs["bo_qua"], stale=res["stale"], reused=False)


# dp_stage_review: mỗi lần NGƯỜI DÙNG trả lại thêm ≤ 1 lượt (không giới hạn số lần trả lại — sổ chi ghi thật, ước tính không tính)
CREW_CALLS = {"director_stage_blocking": (1, 2), "dp_stage_specs": (1, 1), "dp_stage_review": (1, 3), "director_stage_approve": (1, 2)}


def _crew_estimate(conn, worst: bool = False) -> str:
    usd = crew_usd(conn, worst)
    return f"≈ {usd:.3f} USD" if usd is not None else "chưa có giá Claude"


def crew_usd(conn, worst: bool = False) -> Optional[float]:
    """Ước tính một cảnh chia vai: thường = 1 lượt mỗi vai; xấu nhất = số lượt tối đa của máy trạng thái (× 2 khi sai mẫu)."""
    from . import cost
    from . import stage_crew as sc
    total = 0.0
    for stage, (one, most) in CREW_CALLS.items():
        if stage == "director_stage_approve" and sc.user_approves():
            continue
        try:
            u = cost.llm_estimate(conn, stage, most * 2 if worst else one)
        except Exception:  # noqa: BLE001 - bảng giá lỗi
            return None
        if u is None:
            return None
        total += u
    return total * cost.LLM_MARGIN


def score_saved(conn, pid: int, seg: Dict, data_dir: str) -> Dict:
    """0 USD: chấm MỌI lượt Đạo diễn đã lưu của đoạn (r*/answer.json) bằng bộ kiểm HIỆN TẠI (luật kịch bản + K3 khung) trên đề bài hiện
    tại — {lượt: [lỗi]} (rỗng = qua). Dùng trước khi trả tiền chạy lại: lỗi cũ phải bị bắt bằng code, không phải bằng mắt người."""
    from . import llm_io
    from . import stage_director as sd
    import copy as _c
    out_dir = os.path.join(base_dir(data_dir, pid, seg["stage"]), f"doan_{key_of(seg['scene'])}")
    k1 = ensure_k1_seg(seg, base_dir(data_dir, pid, seg["stage"]))
    inputs, missing = inputs_for(conn, pid, seg, k1, stored_state_before(data_dir, pid, seg, conn))
    with open(os.path.join(k1, "stage.json"), encoding="utf-8") as f:
        marks = json.load(f).get("marks")
    res: Dict = {"missing": missing, "gate": preflight(inputs, marks), "rounds": {}}
    found = []
    for x in sorted(os.listdir(out_dir) if os.path.isdir(out_dir) else []):
        if re.fullmatch(r"r[0-9]+", x):
            found.append(x)
        elif x.startswith("cu_") and os.path.isdir(os.path.join(out_dir, x)):
            found += [f"{x}/{y}" for y in sorted(os.listdir(os.path.join(out_dir, x))) if re.fullmatch(r"r[0-9]+", y)]
    from .llm_runner import extract_json
    for root, _dirs, files in os.walk(out_dir):          # câu trả lời SAI MẪU đã trả tiền (16/10 lần 4) cũng được chấm lại
        for fn in sorted(files):
            if fn.startswith("bad_reply_") and fn.endswith(".txt"):
                found.append(os.path.relpath(os.path.join(root, fn), out_dir).replace(os.sep, "/"))
    for d in found:
        path = os.path.join(out_dir, d) if d.endswith(".txt") else os.path.join(out_dir, d, "answer.json")
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                obj = extract_json(f.read()) if d.endswith(".txt") else json.load(f)
        except (ValueError, TypeError) as e:
            res["rounds"][d] = [f"không đọc được JSON: {e}"]
            continue
        try:
            sd.validate_answer(_c.deepcopy(obj), inputs, marks)
            res["rounds"][d] = []
        except (llm_io.SchemaError, ValueError, KeyError, TypeError) as e:
            res["rounds"][d] = [x for x in str(e).split("; ") if x]
    return res


def stored_state_before(data_dir: str, pid: int, seg: Dict, conn) -> Optional[Dict]:
    """Vị trí cuối đã lưu của đoạn TRƯỚC trên cùng sân khấu (để đầu vào dựng lại khớp vân tay của lần chạy trả tiền)."""
    prev = None
    for g in segments(conn, pid):
        if g["id"] == seg["id"]:
            return prev
        if g["stage"] == seg["stage"]:
            prev = stored_state(data_dir, pid, g) or prev
    return prev


def _save(path: str, res: Dict) -> Dict:
    """Kết quả một đoạn theo vân tay đầu vào — kể cả thất bại đã tốn lượt Claude (sai mẫu 2 lần) / Blender lỗi: lượt autopilot sau
    KHÔNG gọi lại (không trả tiền lặp mỗi nhịp); đổi đầu vào (kịch bản / Kho) hoặc `force` mới chạy lại."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in res.items() if k != "reused"}, f, ensure_ascii=False, indent=1)
    return res


# ---- cả dự án ------------------------------------------------------------------------------------------------------------
def stored_state(data_dir: str, pid: int, seg: Dict) -> Optional[Dict]:
    """Vị trí cuối đã lưu của một đoạn (result.json), không cần chạy lại — đoạn bị bỏ qua vẫn truyền chỗ người/vật cho đoạn sau."""
    path = os.path.join(base_dir(data_dir, pid, seg["stage"]), f"doan_{key_of(seg['scene'])}", "result.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("state")
    except (OSError, ValueError):
        return None


def run(conn, pid: int, data_dir: str, client=None, force: bool = False, again: bool = False,
        log: Callable[[str], None] = lambda m: None, scenes: Optional[set] = None, manual: bool = False,
        who: Optional[Dict] = None) -> Optional[Dict]:
    """Mọi đoạn của dự án, nối tiếp theo sân khấu (vị trí cuối đoạn trước → đầu đoạn sau). None khi cờ TẮT (không làm gì).
    Trả {"applied": [idx], "held": [(vân tay, câu)], "skipped": [đoạn]}: `held` = shot không đạt / đoạn thiếu đầu vào — autopilot
    giữ ở cổng nền 3D cho người xem (Tiếp tục = các shot đó dùng máy thường, VÀNG). `force` = cả đoạn có shot đã vẽ ảnh (máy mới làm
    ảnh cũ lệch nền — người chọn); `again` = bỏ kết quả đã lưu, gọi Đạo diễn lại (tốn tiền).
    `manual` (M4.8, kế hoạch bàn đạo diễn mục 2 điểm 1): NGƯỜI chọn chạy (nút / lệnh tay) — chạy cả khi cờ stage_auto TẮT mà KHÔNG đặt
    os.environ (đặt biến trong tiến trình Streamlit là bật cờ cho mọi phiên + autopilot). Cờ cần (REQUIRES) vẫn phải bật. `who` →
    apply qua write guard."""
    if not (enabled() or (manual and all(features.on(n) for n in features.REQUIRES.get(FLAG, ())))):
        return None
    if who is None:
        from . import crew, write_guard
        if write_guard.enabled() and crew.active() is not None:
            who = write_guard.actor("auto", "stage_auto", role="artist_3d")
    from .camera_plan import drawn_shots
    segs = segments(conn, pid)
    out: Dict = {"applied": [], "removed": [], "held": [], "skipped": []}
    for h in family_hints(segs):
        _say(conn, pid, "warn", h, log)
    state: Dict[str, Dict] = {}
    waiting: Dict[str, str] = {}
    for seg in segs:
        if scenes is not None and seg["scene"] not in scenes:
            state[seg["stage"]] = stored_state(data_dir, pid, seg) or state.get(seg["stage"])
            continue
        done = drawn_shots(conn, seg)
        if done and not force:
            state[seg["stage"]] = stored_state(data_dir, pid, seg) or state.get(seg["stage"])
            out["skipped"].append(seg["id"])
            if any(not s["data"].get(FIELD) for s in seg["shots"]):
                _say(conn, pid, "warn", f"Sân khấu {seg['id']}: shot {', '.join(map(str, done))} đã có ảnh — không đổi máy (ảnh đã vẽ "
                                        f"sẽ lệch nền 3D); muốn dàn lại cả cảnh: py tools/stage_auto.py --project {pid} --force --yes", log)
            continue
        from . import stage_crew                          # 16/10 chia vai (cờ stage_crew, TẮT mặc định): Đạo diễn + Quay phim
        seg_run = run_segment_crew if stage_crew.enabled() else run_segment
        if seg["stage"] in waiting:                       # rà 16/10: đoạn trước cùng sân khấu chờ người dùng duyệt → vị trí cuối chưa chốt
            line = f"sân khấu {seg['id']}: chờ người dùng duyệt đoạn trước cùng sân khấu ({waiting[seg['stage']]}) — chưa dàn cảnh"
            _say(conn, pid, "warn", line, log)
            out["held"].append(("stageauto:" + hashlib.sha1(line.encode("utf-8")).hexdigest()[:12], line))
            continue
        r = seg_run(conn, pid, seg, data_dir, client, state.get(seg["stage"]), log, force=again)
        if r.get("waiting"):
            waiting[seg["stage"]] = seg["id"]
            apply(conn, seg, {}, who=who)                 # máy tự động cũ theo dàn cảnh chưa duyệt không dùng tiếp
            line = f"sân khấu {seg['id']}: {r['waiting']}"
            _say(conn, pid, "warn", line, log)
            out["held"].append(("stageauto:" + hashlib.sha1(line.encode("utf-8")).hexdigest()[:12], line))
            continue
        if r["missing"]:
            if r.get("stale"):                            # rà 15/10: máy tự động theo dàn cảnh CŨ không được dùng tiếp
                gone = apply(conn, seg, {}, who=who)
                if gone:
                    _say(conn, pid, "warn", f"Sân khấu {seg['id']}: gỡ máy sân khấu cũ của shot {', '.join(map(str, gone))} "
                                            "(đầu vào đã đổi) — nền 3D dùng máy thường tới khi dàn cảnh lại", log)
            line = f"sân khấu {seg['id']} chưa chạy — thiếu: " + "; ".join(r["missing"])
            _say(conn, pid, "warn", line, log)
            out["held"].append(("stageauto:" + hashlib.sha1(line.encode("utf-8")).hexdigest()[:12], line))
            continue
        if r.get("reused"):                               # rà 16/10: kết quả lưu trước khi có kiểm tệp ảnh người nộm
            r["guide_missing"] = guides_missing(r["cams"])
        if r.get("state"):
            state[seg["stage"]] = r["state"]
        changed = apply(conn, seg, r["cams"], r.get("bo_qua") or [], who=who)
        out["applied"] += [i for i in changed if i in r["cams"]]
        out["removed"] += [i for i in changed if i not in r["cams"]]    # 16/10: máy tự động cũ bị GỠ ≠ đã gán máy
        _say_guides(conn, pid, seg, r, out, log)
        for idx, why in sorted((r.get("soft") or {}).items()):
            _say(conn, pid, "warn", f"Sân khấu {seg['id']} shot {idx}: {why}", log)
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
    from . import stage_crew
    n = len(segs)
    if stage_crew.enabled():                              # 16/10 chia vai: một lượt mỗi vai; xấu nhất = số lượt tối đa × 2 (sai mẫu)
        one, worst = crew_usd(conn), crew_usd(conn, worst=True)
        return {"segments": [g["id"] for g in segs], "shots": sum(len(g["shots"]) for g in segs), "crew": True,
                "usd": None if one is None else round(one * n, 3), "usd_max": None if worst is None else round(worst * n, 3)}
    one = cost.llm_estimate(conn, STAGE, 1)
    return {"segments": [g["id"] for g in segs], "shots": sum(len(g["shots"]) for g in segs),
            "usd": None if one is None else round(one * cost.LLM_MARGIN * n, 3),
            "usd_max": None if one is None else round(one * cost.LLM_MARGIN * n * 2 * MAX_ROUNDS, 3)}
