"""C-STAGE-VIEW (V3.1, cloud-C 21/10) — XEM sân khấu 3D trên Bước 2, CHỈ ĐỌC, 0 USD. Cờ `stage_view_ui` (TẮT = render() trả về ngay, không đọc
gì, Bước 2 y cũ). Người dùng 21/10: Dashboard chưa xem được sân khấu 3D — mọi thứ chạy CLI (tools/stage_auto.py, tools/stage_previs.py,
tools/location_pack.py), ảnh nằm trong thư mục.

Mỗi cảnh truyện (`story_scene`) một expander:
  1. tấm clay / khối đã render: `<data>/<pid>/stage/<stage>/doan_<cảnh>/r*/blockout_sheet.png`, `*_clay.mp4`; mặt cắt K1 `k1_*/top_cut.png`
  2. ảnh nền 3D từng shot + hướng máy (core/location_pack.index → plates/index.json: plate, camera; trường shot plate_view)
  3. sơ đồ world map 2D (core/world_map.load + entities_at, SVG tĩnh — không gọi Blender)
  4. người nộm đúng chiều cao (cờ whitebox_height_dummy: core/whitebox.heights_of) + câu vị trí gợi ý (cờ world_map_sentences:
     core/world_map.position_sentence) — chỉ hiện
  5. cảnh báo bằng ĐÚNG hàm cổng hiện có: nền cũ (core/place_refs.stale — hàm của cổng Bước 2 batch.image_gates), nền hỏng / chờ hướng
     (location_pack.plate_failed / plate_needs), world map cũ (world_map.stale + `invalidated`), plate_view (core/plate_view_check.warnings);
     thiếu tệp → "chưa có <gì> — chạy <lệnh>" (không im lặng).
KHÔNG nút render / gen / ghi; không ghi data/ hay CSDL; đường dẫn theo `data_dir` của pipeline (không theo cwd); ảnh đọc có giới hạn
(MAX_BYTES, thu nhỏ THUMB_PX trong bộ nhớ)."""
import glob
import json
import os
from html import escape
from typing import Dict, List, Optional, Tuple

import streamlit as st

from dashboard import stage_desk_ui

FLAG = "stage_view_ui"
THUMB_PX = 480
MAX_BYTES = 25 * 1024 * 1024
MAX_FILES = 6


def enabled() -> bool:
    from core import features
    return features.on(FLAG)


def thumb(path: Optional[str]) -> Tuple[Optional[object], Optional[str]]:
    """(ảnh PIL thu nhỏ trong bộ nhớ | None, lý do | None). Không ghi tệp."""
    if not path or not os.path.isfile(path):
        return None, f"không có tệp {path}"
    size = os.path.getsize(path)
    if size > MAX_BYTES:
        return None, f"tệp quá lớn ({size // (1024 * 1024)} MB > {MAX_BYTES // (1024 * 1024)} MB) — mở ngoài Dashboard: {path}"
    try:
        from PIL import Image
        with Image.open(path) as im:
            im.thumbnail((THUMB_PX, THUMB_PX))
            return im.copy(), None
    except Exception as e:  # noqa: BLE001 - một ảnh hỏng không làm hỏng màn xem
        return None, f"không đọc được ảnh {os.path.basename(path)} ({type(e).__name__})"


def _scene_key(data: Dict, idx) -> str:
    s = data.get("story_scene")
    return str(s) if s not in (None, "") else f"shot{idx}"


def _latest(paths: List[str]) -> List[str]:
    return sorted(paths, key=lambda x: (os.path.getmtime(x) if os.path.exists(x) else 0), reverse=True)[:MAX_FILES]


def _stage_files(conn, pid: int, data_dir: str, scene: str) -> Tuple[Dict, List[Dict]]:
    """Tệp sân khấu đã render của cảnh (chỉ glob + exists) và các đoạn sân khấu ({stage, k1_dirs, seg_dir})."""
    from core import stage_auto
    files: Dict[str, List[str]] = {"blockout": [], "top_cut": [], "clay": []}
    segs = []
    try:
        all_segs = stage_auto.segments(conn, pid)
    except Exception:  # noqa: BLE001 - không đọc được kế hoạch sân khấu: cảnh hiện "chưa có sân khấu"
        all_segs = []
    for seg in all_segs:
        if str(seg.get("scene")) != scene:
            continue
        base = stage_auto.base_dir(data_dir, pid, seg["stage"])
        seg_dir = os.path.join(base, f"doan_{stage_auto.key_of(seg['scene'])}")
        k1_dirs = sorted(d for d in glob.glob(os.path.join(base, "k1_*")) if os.path.isdir(d))
        files["top_cut"] += [p for p in (os.path.join(d, "top_cut.png") for d in k1_dirs) if os.path.isfile(p)]
        files["blockout"] += glob.glob(os.path.join(seg_dir, "r*", "blockout_sheet.png"))
        files["clay"] += glob.glob(os.path.join(seg_dir, "**", "*_clay.mp4"), recursive=True) + glob.glob(os.path.join(base, "*_clay.mp4"))
        segs.append({"stage": seg["stage"], "k1_dirs": k1_dirs, "seg_dir": seg_dir if os.path.isdir(seg_dir) else None})
    return {k: _latest(v) for k, v in files.items()}, segs


def _world(data_dir: str, pid: int, scene: str, segs: List[Dict], warnings: List[str], missing: List[str]) -> Optional[Dict]:
    from core import world_map
    key = int(scene) if scene.isdigit() else scene
    try:
        m = world_map.load(data_dir, pid, key)
    except (OSError, ValueError) as e:
        warnings.append(f"world map cảnh {scene} đọc lỗi ({type(e).__name__}) — mở tệp {world_map.path(data_dir, pid, key)}")
        return None
    if not m:
        missing.append(f"chưa có world map cảnh {scene} — dựng bằng core.world_map.refresh (cờ world_map, offline 0 USD)")
        return None
    why = (m.get("invalidated") or {}).get("why")
    if not why:
        seg = next((s for s in segs if s["seg_dir"]), None)
        if seg and m.get("kind") == "3d":           # world_map.stale: so nguồn hiện có với nguồn lúc dựng map
            was = m.get("sources") or {}
            k1 = next((d for d in seg["k1_dirs"] if world_map.sources(d)["stage_json_sha"] == was.get("stage_json_sha")),
                      seg["k1_dirs"][0] if seg["k1_dirs"] else None)
            now = dict(world_map.sources(k1, seg["seg_dir"], plan2d_file=world_map.plan2d_path(data_dir, pid, key)),
                       byd=was.get("byd"))                       # BYĐ không so ở màn xem (map 3D không dựng từ BYĐ)
            why = world_map.stale(m, now)
    if why:
        warnings.append(f"world map cảnh {scene} đã cũ ({why}) — số đo dưới đây có thể không còn đúng; dựng lại bằng core.world_map.refresh")
    points = [{"label": str(e.get("label") or e.get("entity_id")), "kind": e.get("kind"), "xy": e["transform"]["xyz"][:2]}
              for e in world_map.entities_at(dict(m, invalidated=None), None)
              if isinstance(e.get("transform"), dict) and e["transform"].get("xyz")]
    return {"kind": m.get("kind"), "revision": m.get("map_revision"), "points": points, "cameras": [], "map": m, "stale": why}


def collect(p, pid: int, data_dir: str) -> List[Dict]:
    """Dữ liệu màn xem, theo cảnh truyện: [{scene, shots, files, world, dummies, warnings, missing}]. CHỈ ĐỌC."""
    from core import features, location_pack, place_refs, plate_view_check, world_map
    conn = p.conn
    rows = conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
    index = location_pack.index(data_dir, pid)
    stale: Dict = {}
    stale_note = None
    if place_refs.enabled():                          # cùng hàm cổng Bước 2 (batch.image_gates → place_refs.stale)
        try:
            stale = dict(place_refs.stale(conn, data_dir, pid, place_refs.resolution_of(p.project(pid))))
        except Exception as e:  # noqa: BLE001
            stale_note = f"không so được nền 3D với kế hoạch ({type(e).__name__}: {e})"
        broken = stale.pop(-1, None)
        if broken:
            stale_note = f"không so được nền 3D với kế hoạch — {broken['why']}"
    else:
        stale_note = "cờ place_render_refs tắt — không so nền 3D với kế hoạch máy"
    scenes: Dict[str, Dict] = {}
    for r in rows:
        try:
            data = json.loads(r["data"] or "{}")
        except ValueError:
            data = {}
        key = _scene_key(data, r["idx"])
        sc = scenes.setdefault(key, {"scene": key, "shots": [], "warnings": [], "missing": [], "_datas": []})
        rec = index.get(str(r["id"])) or {}
        plate = rec.get("plate") if rec.get("plate") and os.path.isfile(rec["plate"]) else None
        shot = {"scene_id": r["id"], "idx": r["idx"], "shot_no": data.get("shot_no"), "plate": plate, "plate_view": data.get("plate_view"),
                "camera": rec.get("camera"), "place": rec.get("place"), "characters": list(data.get("characters") or [])}
        failed = location_pack.plate_failed(data_dir, pid, r["id"])
        needs = location_pack.plate_needs(data_dir, pid, r["id"])
        if r["id"] in stale:
            sc["warnings"].append(f"shot {r['idx']}: nền 3D CŨ — {stale[r['id']].get('why')} (ảnh vẽ trên nền này sẽ sai bối cảnh)")
        if failed:
            sc["warnings"].append(f"shot {r['idx']}: nền 3D hỏng — {failed}")
        if needs:
            sc["warnings"].append(f"shot {r['idx']}: nền 3D chờ hướng máy — {needs}")
        if plate is None and not failed and not needs:
            sc["missing"].append(f"chưa có nền 3D shot {r['idx']} — chạy `py tools/location_pack.py render --project {pid}` (Blender, 0 USD)")
        sc["shots"].append(shot)
        sc["_datas"].append((key, data.get("shot_no") or r["idx"], data))
    dummy_on = features.on("whitebox_height_dummy")
    out = []
    for key, sc in scenes.items():
        files, segs = _stage_files(conn, pid, data_dir, key)
        if not segs:
            sc["missing"].append(f"chưa có sân khấu 3D cảnh {key} — chạy `py tools/stage_auto.py --project {pid} --scene {key} --dry` "
                                 "(đo K1, 0 USD)")
        elif not files["blockout"] and not files["clay"]:
            sc["missing"].append(f"chưa có tấm clay / khối cảnh {key} — chạy `py tools/stage_previs.py` hoặc tools/stage_auto.py (Blender, "
                                 "0 USD)")
        sc["files"] = files
        try:
            sc["warnings"] += plate_view_check.warnings(sc.pop("_datas"))
        except Exception as e:  # noqa: BLE001
            sc["warnings"].append(f"không kiểm được hướng nền (plate_view) — {type(e).__name__}")
        if stale_note:
            sc["warnings"].append(stale_note)
        sc["world"] = _world(data_dir, pid, key, segs, sc["warnings"], sc["missing"])
        if sc["world"]:
            sc["world"]["cameras"] = [s["camera"] for s in sc["shots"] if isinstance(s.get("camera"), dict)]
            if world_map.sentences_enabled():
                for s in sc["shots"]:
                    # valid_from / valid_to của map = scenes.idx (stage_auto shot_specs 'shot'), không phải shot_no trong cảnh (gộp GOC-B 22/10)
                    s["sentence"], _ = world_map.position_sentence(sc["world"]["map"], s["idx"], s["camera"])
            sc["world"].pop("map", None)
        sc["dummies"] = None
        if dummy_on:
            from core import whitebox
            names = sorted({n for s in sc["shots"] for n in s["characters"]})
            got, lack = whitebox.heights_of(conn, pid, names)
            sc["dummies"] = got
            if lack:
                sc["warnings"].append("người nộm: thiếu chiều cao hồ sơ Kho (height_m) của " + ", ".join(lack))
        out.append(sc)
    return out


def svg(points: List[Dict], cameras: List[Dict], size: int = 360) -> str:
    """Sơ đồ nhìn từ trên (mét) — người chấm cam, vật ô vuông xám, mốc tam giác, máy chấm xanh + tia nhìn. Chuỗi SVG tĩnh."""
    xs = [p["xy"][0] for p in points] + [c["location"][0] for c in cameras if c.get("location")]
    ys = [p["xy"][1] for p in points] + [c["location"][1] for c in cameras if c.get("location")]
    if not xs:
        return ""
    lo_x, hi_x, lo_y, hi_y = min(xs) - 2, max(xs) + 2, min(ys) - 2, max(ys) + 2
    span = max(hi_x - lo_x, hi_y - lo_y, 1.0)

    def at(x, y):
        return round((x - lo_x) / span * (size - 20) + 10, 1), round(size - 10 - (y - lo_y) / span * (size - 20), 1)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
             f'style="background:#f6f6f2;border:1px solid #ccc">']
    for c in cameras:
        if not c.get("location"):
            continue
        cx, cy = at(*c["location"][:2])
        if c.get("look_at"):
            tx, ty = at(*c["look_at"][:2])
            parts.append(f'<line x1="{cx}" y1="{cy}" x2="{tx}" y2="{ty}" stroke="#3a7bd5" stroke-width="1.5" stroke-dasharray="4 2"/>')
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="5" fill="#3a7bd5"/>')
    for p in points:
        x, y = at(*p["xy"])
        if p.get("kind") == "nguoi":
            parts.append(f'<circle cx="{x}" cy="{y}" r="6" fill="#e8833a"/>')
        elif p.get("kind") == "moc":
            parts.append(f'<polygon points="{x},{y - 7} {x - 6},{y + 5} {x + 6},{y + 5}" fill="#7a5cc4"/>')
        else:
            parts.append(f'<rect x="{x - 5}" y="{y - 5}" width="10" height="10" fill="#999"/>')
        parts.append(f'<text x="{x + 8}" y="{y + 4}" font-size="11" fill="#333">{escape(p["label"])}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _show_picture(path: str, caption: str) -> None:
    img, why = thumb(path)
    if img is not None:
        st.image(img, caption=caption)
    else:
        st.caption(f"⚠ {why}")


def render(p, pid: int, data_dir: str) -> None:
    """Bước 2, ngay trên khối gen ảnh. Cờ tắt → không đọc / không vẽ gì."""
    if not enabled():
        return
    try:
        scenes = collect(p, pid, data_dir)
    except Exception as e:  # noqa: BLE001 - màn xem không làm hỏng Bước 2: nói lý do
        st.warning(f"🧊 Xem sân khấu 3D: không đọc được dữ liệu ({type(e).__name__}: {e})")
        return
    st.markdown("**🧊 Sân khấu 3D (chỉ xem)** — dữ liệu đã render; muốn render / sửa dùng CLI ghi bên dưới")
    for sc in scenes:
        bad = len(sc["warnings"]) + len(sc["missing"])
        with st.expander(f"Cảnh {sc['scene']} · {len(sc['shots'])} shot" + (f" · ⚠ {bad}" if bad else ""), expanded=False):
            for w in sc["warnings"]:
                st.warning(w)
            for m in sc["missing"]:
                st.caption(f"ℹ {m}")
            pics = [(f, "tấm khối (blockout)") for f in sc["files"]["blockout"][:2]] + [(f, "mặt cắt K1") for f in sc["files"]["top_cut"][:2]]
            if pics:
                cols = st.columns(len(pics))
                for col, (f, cap) in zip(cols, pics):
                    with col:
                        _show_picture(f, f"{cap} · {os.path.basename(os.path.dirname(f))}")
            for clip in sc["files"]["clay"][:1]:
                if os.path.getsize(clip) <= MAX_BYTES:
                    st.video(clip)
                else:
                    st.caption(f"⚠ clip clay quá lớn để hiện — {clip}")
            if sc.get("world") and sc["world"]["points"]:
                st.markdown(svg(sc["world"]["points"], sc["world"]["cameras"]), unsafe_allow_html=True)
                st.caption(f"World map {sc['world']['kind']} · rev {sc['world']['revision'] or 1} · chấm xanh = máy, cam = người, xám = vật")
            if sc.get("dummies"):
                from core import whitebox
                st.caption("Người nộm: " + " · ".join(f"{n} {h:.2f} m (mắt {whitebox.eye_height(h):.2f} m)" for n, h in sc["dummies"].items()))
            shots = [s for s in sc["shots"] if s["plate"]]
            if shots:
                n = min(len(shots), 4)
                cols = st.columns(n)
                for i, s in enumerate(shots):
                    with cols[i % n]:
                        cam = s.get("camera") or {}
                        _show_picture(s["plate"], f"shot {s['idx']} · hướng {s.get('plate_view') or 'mặc định'}"
                                      + (f" · máy {cam.get('location')}" if cam.get("location") else ""))
                        if s.get("sentence"):
                            st.caption(f"Câu vị trí gợi ý (chỉ xem): {s['sentence']}")
            stage_desk_ui.render_scene(p, pid, data_dir, sc["scene"])   # C-M48-DESK-UI: cờ stage_desk_ui TẮT → trả ngay, không vẽ gì
