"""V3.1 M3.1 (DP8, cờ world_map — TẮT): `scene_world_map` THỬ NGHIỆM OFFLINE — bản đồ theo CẢNH có version + provenance + invalidation
(thiết kế docs/V3_1_M3_THIET_KE_WORLD_MAP_2026-10-20.md mục 2; D06 v31-d06-scene-world-map-flexible-2026-10-20; G2-4).

Map là bản TỔNG HỢP ĐỌC từ dữ liệu sẵn có, không thay K1–K5, không bắt buộc 3D:
- "3d"       — sân khấu đã đo: `stage.json` (+ grid.json) của K1 khai thẳng, không có thì của lượt; `doan_<cảnh>/<round>/blocking.json`
               (+ shot_specs.json), `<round>` = `doan_<cảnh>/result.json` trường round (đường cũ `doan_<cảnh>/blocking.json` dự phòng;
               refresh mặc định tự tìm `stage/*/doan_<cảnh>`; không ra 3D → `why` nói vì sao). Tọa độ lấy
               nguyên từ blocking (so với gốc O), mốc từ `stage.json.marks`; thiếu số → transform None + confidence "unknown" (KHÔNG bịa).
- "2d"       — sơ đồ người vẽ (`world/plan2d_<cảnh>.json`: {"by", "points": [{"entity_id", "xy", "valid_from", "valid_to"}]}): z UNKNOWN.
- "relative" — chỉ quan hệ trong khung rút từ BYĐ (`thanh_phan[].vung` trái/phải theo máy của shot) + vật cầm (`vat[].nguoi`, BYĐ v2).
- "unknown"  — không có gì đủ: `why` nói thiếu gì; map vẫn ghi (để người thấy), không đoán.
Map `approved_by = None` KHÔNG chặn gen; KHÔNG ai trong luồng gen đọc map (cờ TẮT; chỉ công cụ offline / test gọi `refresh`).

Lưu: `<data_dir>/<pid>/world/scene_<cảnh>.json` (tệp — không đổi `scenes`, không migration). Mỗi lần nguồn đổi (sha stage.json / grid.json /
blocking.json / shot_specs.json / BYĐ từng shot / sơ đồ 2D) → `map_revision` + 1; bản cũ chép sang `world/history/scene_<cảnh>_r<n>.json` với
`invalidated = {"why", "at", "by_revision"}` (bản cũ không xóa). Nguồn không đổi → giữ revision (không tăng vô cớ)."""
import copy
import hashlib
import json
import os
import re
import time
from typing import Dict, List, Optional, Tuple

FLAG = "world_map"
SCHEMA_VERSION = 1
KINDS = ("3d", "2d", "relative", "unknown")
RELS = ("truoc_mat", "sau_lung", "trai_cua", "phai_cua", "gan", "xa")
CONFIDENCE = ("do", "uoc", "tuong_doi", "unknown")
SOURCES = ("stage_blocking", "stage_marks", "nguoi_ve_2d", "byd", "code_suy")
_ZONE_GAP = 1 / 3 - 1e-6          # hai vùng trái/giữa/phải khác nhau ít nhất một cột mới nói "trái của"


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def scene_key(story_scene) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "_", str(story_scene)).strip("_") or "x"


def world_dir(data_dir: str, pid: int) -> str:
    return os.path.join(data_dir, str(pid), "world")


def path(data_dir: str, pid: int, story_scene) -> str:
    return os.path.join(world_dir(data_dir, pid), f"scene_{scene_key(story_scene)}.json")


def plan2d_path(data_dir: str, pid: int, story_scene) -> str:
    return os.path.join(world_dir(data_dir, pid), f"plan2d_{scene_key(story_scene)}.json")


# ---- nguồn + sha (invalidation) ---------------------------------------------------------------------------------------------
def _read(p: Optional[str]) -> Optional[Dict]:
    if not p or not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _sha_obj(obj) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _sha_file(p: Optional[str]) -> Optional[str]:
    if not p or not os.path.exists(p):
        return None
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def sources(k1_dir: Optional[str] = None, seg_dir: Optional[str] = None, byd: Optional[Dict] = None,
            plan2d_file: Optional[str] = None) -> Dict:
    """sha của mọi nguồn map đọc (None = không có). So hai lần gọi để biết map cũ còn hiệu lực không (`stale`)."""
    j = lambda d, n: os.path.join(d, n) if d else None    # noqa: E731
    return {"stage_json_sha": _sha_file(j(k1_dir, "stage.json")), "grid_json_sha": _sha_file(j(k1_dir, "grid.json")),
            "blocking_json_sha": _sha_file(j(seg_dir, "blocking.json")), "shot_specs_sha": _sha_file(j(seg_dir, "shot_specs.json")),
            "byd": {str(k): _sha_obj(v) for k, v in sorted((byd or {}).items(), key=lambda kv: str(kv[0]))},
            "plan2d_sha": _sha_file(plan2d_file)}


def stale(old: Optional[Dict], now: Dict) -> Optional[str]:
    """Lý do map cũ hết hiệu lực (geometry_changed / blocking_changed / byd_changed / plan2d_changed), None = còn hiệu lực."""
    if old is None:
        return None
    was = old.get("sources") or {}
    for keys, why in ((("stage_json_sha", "grid_json_sha"), "geometry_changed"), (("blocking_json_sha", "shot_specs_sha"), "blocking_changed"),
                      (("byd",), "byd_changed"), (("plan2d_sha",), "plan2d_changed")):
        if any(was.get(k) != now.get(k) for k in keys):
            return why
    return None


# ---- dựng ---------------------------------------------------------------------------------------------------------------------
def _base(story_scene, kind: str, world_id, src: Dict, frm: List[str], by: str) -> Dict:
    return {"schema_version": SCHEMA_VERSION, "scene": str(story_scene), "world_id": world_id, "kind": kind, "unit": "m",
            "axes": None, "origin": None, "map_revision": 1, "sources": src, "entities": [], "landmarks": [], "occluders": [],
            "relations": [], "approved_by": None, "approved_at": None,
            "provenance": {"by": by, "from": frm, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}, "invalidated": None, "why": None}


def _beat_states(blocking: Dict, specs: List[Dict]) -> List[Tuple[Optional[int], Dict[str, Dict]]]:
    """[(shot, {khóa: vật thô của nhịp})] theo thứ tự shot; không có shot_specs → [(None, objects gốc)]."""
    from .stage_solver import beat_raw
    rows = [s for s in specs or [] if isinstance(s, dict) and s.get("shot") is not None]
    if not rows:
        return [(None, beat_raw(blocking))]
    out = []
    for s in sorted(rows, key=lambda s: s["shot"]):
        nhip = s.get("nhip")
        out.append((s["shot"], beat_raw(blocking, nhip if nhip in (blocking.get("beats") or {}) else None)))
    return out


def _entity_3d(key: str, o: Dict, marks: Dict) -> Dict:
    kind = {"nguoi": "nguoi", "moc": "moc"}.get(o.get("kind"), "vat")
    xyz, src, conf = None, "stage_blocking", "do"
    if kind == "moc":
        name = o.get("from_marks", key)
        foot, top = (marks.get(f"{name}_chan") or {}).get("xyz"), (marks.get(f"{name}_dinh") or {}).get("xyz")
        src = "stage_marks"
        if foot:
            xyz = [float(v) for v in foot[:3]]
        dims = {"h": round(float(top[2]) - float(foot[2]), 3)} if foot and top else {}
    else:
        at = o.get("at")
        if isinstance(at, (list, tuple)) and len(at) >= 2:
            xyz = [float(at[0]), float(at[1]), float(o.get("z", 0.0))]
        dims = {k: float(o[s]) for k, s in (("h", "H"), ("w", "w"), ("d", "d")) if isinstance(o.get(s), (int, float))}
        if kind != "nguoi" and isinstance(o.get("h"), (int, float)):
            dims["h"] = float(o["h"])
    if xyz is None:
        conf = "unknown"                                 # thiếu số đo: không bịa vị trí
    state = {k: o[k] for k in ("tu_the", "in", "cam_tay") if o.get(k) not in (None, "")}
    return {"entity_id": key, "label": o.get("label", key), "kho_id": o.get("kho_id"), "kind": kind,
            "transform": None if xyz is None else {"xyz": xyz, "yaw_deg": o.get("facing")}, "dimensions": dims or None,
            "valid_from": None, "valid_to": None, "state": state or None, "source": src, "confidence": conf}


def build_3d(story_scene, k1_dir: str, seg_dir: str, world_id=None, by: str = "code", byd: Optional[Dict] = None) -> Dict:
    """3D từ stage.json + blocking.json (+ shot_specs.json: thực thể theo nhịp → valid_from/valid_to theo shot; cùng trạng thái liền
    nhau gộp một dòng). Vật vắng ở một nhịp (`hidden`) = dòng trước kết thúc ở shot trước đó."""
    stage = _read(os.path.join(k1_dir, "stage.json")) or {}
    blocking = _read(os.path.join(seg_dir, "blocking.json")) or {}
    specs = (_read(os.path.join(seg_dir, "shot_specs.json")) or {}).get("shots") or []
    m = _base(story_scene, "3d", world_id, sources(k1_dir, seg_dir, byd), ["stage.json", "blocking.json"]   # C-FIX-THAP-5: BYĐ đổi → byd_changed
              + (["shot_specs.json"] if specs else []), by)
    m["axes"] = stage.get("axes") or ({k: stage[k] for k in ("axis", "east", "north") if k in stage} or None)   # K1 thật ghi axis/east/north
    m["origin"] = {"stage": stage_name(k1_dir), "xyz": [0.0, 0.0, 0.0],
                   "model_xyz": stage.get("origin_model")}
    marks = stage.get("marks") or {}
    open_rows: Dict[str, Dict] = {}
    for shot, raw in _beat_states(blocking, specs):
        for key in list(open_rows):
            if key not in raw:                           # vắng ở nhịp này
                open_rows.pop(key)
        for key, o in raw.items():
            e = _entity_3d(key, o, marks)
            last = open_rows.get(key)
            same = last is not None and all(last[f] == e[f] for f in ("transform", "state", "dimensions"))
            if same:
                last["valid_to"] = shot
                continue
            e["valid_from"], e["valid_to"] = shot, shot
            m["entities"].append(e)
            open_rows[key] = e
    for e in m["entities"]:
        if e["kind"] == "moc":
            m["landmarks"].append({"entity_id": e["entity_id"], "xyz": (e["transform"] or {}).get("xyz"), "visible_from": None})
    return m


def _vung_u(c: Dict) -> Optional[float]:
    from . import stage_grid as sg
    try:
        u = sg.parse_zone(c.get("vung")).get("u")
    except ValueError:
        return None
    return None if u is None else (u[0] + u[1]) / 2


def build_relative(story_scene, byd: Dict, world_id=None, by: str = "code") -> Dict:
    """Quan hệ trong khung rút từ BYĐ từng shot ({shot: byd}): `thanh_phan[].vung` khác cột → trai_cua / phai_cua (theo MÁY của shot đó,
    `frame: "may_shot"`), `vat[]` dạng v2 có `nguoi` → state.cam của người đó. Không có cặp nào → kind "unknown"."""
    m = _base(story_scene, "relative", world_id, sources(byd=byd), ["byd"], by)
    seen: Dict[str, Dict] = {}
    for shot in sorted(byd, key=lambda s: (str(type(s)), s)):
        b = byd[shot] or {}
        tp = [c for c in b.get("thanh_phan") or [] if isinstance(c, dict) and c.get("vat")]
        for c in tp:
            e = seen.setdefault(c["vat"], {"entity_id": c["vat"], "label": c["vat"], "kho_id": c.get("kho_id"), "kind": "vat", "transform": None,
                                           "dimensions": None, "valid_from": shot, "valid_to": shot, "state": None, "source": "byd",
                                           "confidence": "tuong_doi"})
            e["valid_to"] = shot
        us = [(c["vat"], _vung_u(c)) for c in tp]
        us = [(n, u) for n, u in us if u is not None]
        for i, (a, ua) in enumerate(us):
            for b2, ub in us[i + 1:]:
                if abs(ua - ub) >= _ZONE_GAP:
                    left, right = (a, b2) if ua < ub else (b2, a)
                    m["relations"].append({"a": left, "rel": "trai_cua", "b": right, "frame": "may_shot", "valid_from": shot, "valid_to": shot,
                                           "source": "byd"})
        for v in b.get("vat") or []:
            if isinstance(v, dict) and v.get("nguoi") and v.get("ten"):
                who = seen.setdefault(v["nguoi"], {"entity_id": v["nguoi"], "label": v["nguoi"], "kho_id": None, "kind": "vat",
                                                   "transform": None, "dimensions": None, "valid_from": shot, "valid_to": shot,
                                                   "state": None, "source": "byd", "confidence": "tuong_doi"})
                who["state"] = dict(who["state"] or {}, cam=sorted(set((who["state"] or {}).get("cam", [])) | {v["ten"]}))
    for e in seen.values():
        if any(r["a"] == e["entity_id"] or r["b"] == e["entity_id"] for r in m["relations"]) or (e["state"] or {}).get("cam"):
            e["kind"] = "nguoi" if (e["state"] or {}).get("cam") else e["kind"]
    m["entities"] = list(seen.values())
    if not m["relations"] and not any((e["state"] or {}).get("cam") for e in m["entities"]):
        m["kind"] = "unknown"
        m["why"] = "BYĐ không có hai thứ ở hai vùng khung khác nhau, không có vật cầm — chưa rút được quan hệ (không đoán)"
    return m


def build_2d(story_scene, plan: Dict, plan_file: Optional[str] = None, world_id=None) -> Dict:
    m = _base(story_scene, "2d", world_id, sources(plan2d_file=plan_file), ["plan2d"], "human")
    m["provenance"]["by"] = "human"
    m["provenance"]["who"] = plan.get("by")
    for p in plan.get("points") or []:
        xy = p.get("xy")
        ok = isinstance(xy, (list, tuple)) and len(xy) >= 2
        m["entities"].append({"entity_id": p.get("entity_id"), "label": p.get("label", p.get("entity_id")), "kho_id": p.get("kho_id"),
                              "kind": p.get("kind", "vat"), "transform": {"xyz": [float(xy[0]), float(xy[1]), None], "yaw_deg": p.get("yaw_deg")}
                              if ok else None, "dimensions": None, "valid_from": p.get("valid_from"), "valid_to": p.get("valid_to"),
                              "state": None, "source": "nguoi_ve_2d", "confidence": "uoc" if ok else "unknown"})
    return m


def round_dir(seg_dir: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """(thư mục chứa blocking.json của đoạn, lý do khi không có). Dữ liệu thật (stage_auto): `doan_<cảnh>/result.json` trường `round`
    (cc_<giờ> / r<n> / crew/final) → `doan_<cảnh>/<round>/blocking.json`; đường cũ `doan_<cảnh>/blocking.json` giữ làm dự phòng."""
    if not seg_dir:
        return None, None
    if not os.path.isdir(seg_dir):
        return None, f"không có thư mục đoạn {os.path.basename(os.path.normpath(seg_dir))}"
    if os.path.exists(os.path.join(seg_dir, "blocking.json")) and not os.path.exists(os.path.join(seg_dir, "result.json")):
        return seg_dir, None                              # đường cũ (fixture / dữ liệu trước stage_auto)
    why = []
    try:
        rnd = (_read(os.path.join(seg_dir, "result.json")) or {}).get("round")
    except (OSError, ValueError) as e:
        rnd = None
        why.append(f"result.json đọc lỗi ({type(e).__name__})")
    if rnd:
        rd = os.path.normpath(os.path.join(seg_dir, str(rnd)))
        if os.path.exists(os.path.join(rd, "blocking.json")):
            return rd, None
        why.append(f"lượt «{rnd}» (result.json round) " + ("không có blocking.json" if os.path.isdir(rd) else "không có trên đĩa"))
    elif not why:
        why.append("không có result.json" if not os.path.exists(os.path.join(seg_dir, "result.json")) else "result.json không có round")
    if os.path.exists(os.path.join(seg_dir, "blocking.json")):
        return seg_dir, None                              # dự phòng: blocking.json ở gốc đoạn
    return None, f"{os.path.basename(os.path.normpath(seg_dir))}: " + "; ".join(why)


def stage_dir(k1_dir: Optional[str], rd: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """(thư mục chứa stage.json, lý do khi không có). K1 khai thẳng có stage.json → dùng; không thì stage.json của LƯỢT (K3/K4 chép
    stage.json đã đo vào lượt — cùng hình học blocking được giải trên đó; #31 cảnh 4: K1 theo chỗ đứng chính HIỆN TẠI chưa từng đo)."""
    if k1_dir and os.path.exists(os.path.join(k1_dir, "stage.json")):
        return k1_dir, None
    if rd and os.path.exists(os.path.join(rd, "stage.json")):
        return rd, None
    bits = []
    if k1_dir:
        bits.append(f"{os.path.basename(os.path.normpath(k1_dir))} không có stage.json")
    if rd:
        bits.append(f"lượt {os.path.basename(os.path.normpath(rd))} không có stage.json")
    return None, "; ".join(bits) or None


def stage_name(path_: str) -> str:
    """Tên sân khấu (thư mục cha của k1_* / doan_*) từ thư mục K1 hoặc thư mục lượt bên trong doan_<cảnh>."""
    start = p = os.path.abspath(path_)
    while not os.path.basename(p).startswith(("k1_", "doan_")):
        parent = os.path.dirname(p)
        if parent == p:                                   # không nằm trong k1_* / doan_*: như cũ (thư mục cha)
            return os.path.basename(os.path.dirname(start))
        p = parent
    return os.path.basename(os.path.dirname(p))


def locate(data_dir: str, pid: int, story_scene) -> Tuple[Optional[str], Optional[str]]:
    """(thư mục `stage/<sân khấu>/doan_<cảnh>`, lý do khi không có) — refresh mặc định tự tìm (không cần người truyền seg_dir)."""
    import glob
    from .stage_auto import key_of
    key = key_of(str(story_scene))
    hits = sorted(d for d in glob.glob(os.path.join(data_dir, str(pid), "stage", "*", f"doan_{key}")) if os.path.isdir(d))
    if len(hits) > 1:
        used = [d for d in hits if os.path.exists(os.path.join(d, "result.json"))]
        hits = used if len(used) == 1 else hits
    if not hits:
        return None, f"không có thư mục stage/*/doan_{key} (cảnh chưa dàn sân khấu 3D)"
    if len(hits) > 1:
        return None, (f"cảnh {story_scene} có đoạn ở {len(hits)} sân khấu (" + ", ".join(stage_name(d) for d in hits)
                      + ") — map một cảnh chưa gộp nhiều sân khấu, không chọn bừa")
    return hits[0], None


def build(story_scene, k1_dir: Optional[str] = None, seg_dir: Optional[str] = None, byd: Optional[Dict] = None,
          plan2d_file: Optional[str] = None, world_id=None, notes: Optional[str] = None) -> Dict:
    """Adapter (D06): 3D khi có đủ stage.json + blocking.json → 2D khi có sơ đồ người vẽ → tương đối từ BYĐ → UNKNOWN (why = thiếu gì).
    `seg_dir` = doan_<cảnh> (đọc result.json → round) hoặc thẳng thư mục có blocking.json. Không ra 3D → `why` nói RÕ vì sao (cả khi
    map tương đối), không im lặng."""
    missing = []
    rd, why_seg = round_dir(seg_dir)
    sd, why_stage = stage_dir(k1_dir, rd)
    if rd and sd:
        m = build_3d(story_scene, sd, rd, world_id, byd=byd)
        m["provenance"]["round"] = None if os.path.normpath(rd) == os.path.normpath(seg_dir) else os.path.relpath(rd, seg_dir)
        m["provenance"]["stage_json_from"] = "k1" if sd == k1_dir else "round"
        return m
    reason = "; ".join(x for x in (notes, why_seg, why_stage) if x)
    no3d = "sân khấu 3D (stage.json + blocking.json" + (f": {reason}" if reason else "") + ")"
    missing.append(no3d)
    plan = _read(plan2d_file)
    if plan and plan.get("points"):
        m = build_2d(story_scene, plan, plan2d_file, world_id)
        m["why"] = "không 3D — thiếu " + no3d
        return m
    missing.append("sơ đồ 2D người vẽ")
    if byd:
        m = build_relative(story_scene, byd, world_id)
        if m["kind"] == "relative":
            m["why"] = "không 3D — thiếu " + no3d + "; quan hệ trái/phải rút từ BYĐ theo máy từng shot"
            return m
        missing.append("quan hệ trong BYĐ")
    else:
        missing.append("BYĐ")
    m = _base(story_scene, "unknown", world_id, sources(sd or k1_dir, rd or seg_dir, byd, plan2d_file), [], "code")
    m["why"] = "thiếu " + ", ".join(missing) + " — map UNKNOWN, không bịa tọa độ (cần người duyệt / dựng sân khấu)"
    return m


# ---- kiểm + lưu ---------------------------------------------------------------------------------------------------------------
def check(m: Dict) -> List[str]:
    """Lỗi hợp đồng ([] = hợp lệ)."""
    out = []
    if m.get("schema_version") != SCHEMA_VERSION:
        out.append(f"schema_version {m.get('schema_version')!r} (cần {SCHEMA_VERSION})")
    if m.get("kind") not in KINDS:
        out.append(f"kind {m.get('kind')!r} ∉ {KINDS}")
    if not isinstance(m.get("map_revision"), int) or m["map_revision"] < 1:
        out.append("map_revision phải là số nguyên ≥ 1")
    if not (m.get("provenance") or {}).get("by"):
        out.append("thiếu provenance.by")
    if m.get("kind") == "unknown" and not m.get("why"):
        out.append("kind unknown phải nói why (thiếu gì)")
    for e in m.get("entities") or []:
        t = f"entity {e.get('entity_id')!r}"
        if e.get("confidence") not in CONFIDENCE:
            out.append(f"{t}: confidence {e.get('confidence')!r}")
        if e.get("source") not in SOURCES:
            out.append(f"{t}: source {e.get('source')!r}")
        if e.get("transform") is None and e.get("confidence") in ("do", "uoc"):
            out.append(f"{t}: không có tọa độ mà confidence {e.get('confidence')}")
        xyz = (e.get("transform") or {}).get("xyz")
        if m.get("kind") == "relative" and xyz:
            out.append(f"{t}: map tương đối không được có tọa độ")
        if m.get("kind") == "2d" and xyz and xyz[2] is not None:
            out.append(f"{t}: map 2D phải để z = None (UNKNOWN)")
        vf, vt = e.get("valid_from"), e.get("valid_to")
        if isinstance(vf, (int, float)) and isinstance(vt, (int, float)) and vt < vf:
            out.append(f"{t}: valid_to trước valid_from")
    for r in m.get("relations") or []:
        if r.get("rel") not in RELS:
            out.append(f"quan hệ {r.get('rel')!r} ∉ {RELS}")
    return out


def load(data_dir: str, pid: int, story_scene) -> Optional[Dict]:
    return _read(path(data_dir, pid, story_scene))


def _write(p: str, obj: Dict) -> None:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def _body(m: Dict) -> Dict:
    return {k: v for k, v in m.items() if k not in ("map_revision", "provenance", "invalidated", "approved_by", "approved_at")}


def save(data_dir: str, pid: int, m: Dict) -> Dict:
    """Ghi map; giữ revision khi nội dung + nguồn y như bản đang có, khác → revision + 1 và bản cũ sang history có `invalidated`
    (why = stale(...) hoặc "rebuilt"). Map lỗi hợp đồng → ValueError (không ghi)."""
    bad = check(m)
    if bad:
        raise ValueError("world map không hợp lệ: " + "; ".join(bad))
    p = path(data_dir, pid, m["scene"])
    old = _read(p)
    m = copy.deepcopy(m)
    if old is not None:
        if _body(old) == _body(m):
            return old
        m["map_revision"] = int(old.get("map_revision") or 1) + 1
        old["invalidated"] = {"why": stale(old, m.get("sources") or {}) or "rebuilt", "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                              "by_revision": m["map_revision"]}
        _write(os.path.join(world_dir(data_dir, pid), "history", f"scene_{scene_key(m['scene'])}_r{old.get('map_revision', 1)}.json"), old)
    _write(p, m)
    return m


def refresh(data_dir: str, pid: int, story_scene, **inputs) -> Optional[Dict]:
    """Công cụ offline (cờ world_map): dựng lại + lưu. Cờ TẮT → None, không đọc / ghi gì."""
    if not enabled():
        return None
    inputs.setdefault("plan2d_file", plan2d_path(data_dir, pid, story_scene))
    if "seg_dir" not in inputs and "k1_dir" not in inputs:   # MẶC ĐỊNH: tự tìm stage/*/doan_<cảnh> (result.json → round), không đoán
        seg, why = locate(data_dir, pid, story_scene)
        inputs["seg_dir"] = seg
        if why:
            inputs["notes"] = why
    return save(data_dir, pid, build(story_scene, **inputs))


def entities_at(m: Dict, shot) -> List[Dict]:
    """Thực thể có hiệu lực ở shot (valid_from ≤ shot ≤ valid_to; None = cả cảnh). Map đã invalidated → [] (không dùng số cũ).
    shot None (C-FIX-THAP-5) → mọi thực thể của cảnh."""
    if not m or m.get("invalidated"):
        return []
    if shot is None:
        return list(m.get("entities") or [])
    out = []
    for e in m.get("entities") or []:
        vf, vt = e.get("valid_from"), e.get("valid_to")
        if (vf is None or shot >= vf) and (vt is None or shot <= vt):
            out.append(e)
    return out


# ---- M3.3 (DP11, cờ world_map_sentences — TẮT): câu vị trí sinh từ map, CHỈ ĐỀ XUẤT + so câu hiện tại (REVIEW) ---------------------------
SENTENCE_FLAG = "world_map_sentences"
CENTRE_DEG = 8.0           # |góc ngang| dưới mức này = giữa khung
BEHIND_GAP_M = 1.5         # hai người cùng phía khung, xa hơn ≥ chừng này = "phía sau"
_SIDE_EN = {"left": "frame left", "centre": "frame centre", "right": "frame right"}
_CLAUSE = re.compile(r"[.;,:\n]|\bwhile\b|\band\b|\bbut\b|\bvà\b|\bcòn\b|\btrong khi\b", re.I)   # ':' — phần liệt kê sau là vế riêng
# R1-SIDE báo nhầm #31 (22/10: shot 18 "behind Kelly's right shoulder", shot 34 "toward frame-right where three enemies stand"):
# trái/phải chỉ là CHỖ TRONG KHUNG khi không phải bộ phận cơ thể / phía của chính người đó / một đầu của vật, và chỉ gán cho ĐÚNG chủ
# thể của vế — mệnh đề "where X stand(s)" → X; còn lại → tên đứng gần nhất TRƯỚC chữ, không có thì tên đầu tiên SAU chữ.
_SIDE_TOKEN = re.compile(r"\b(left|right)\b|(?:bên|phía|sang)\s+(trái|phải)|\bkhung\s+(trái|phải)", re.I)
# C-R1-REL (22/10): "right of X" / "bên phải (của) X" là quan hệ TƯƠNG ĐỐI giữa hai thực thể, không phải bên KHUNG → không gán ở đây;
# core/position_invariants.relative_claims kiểm nó bằng góc hai thực thể. "of the frame" / "khung" vẫn là bên khung.
_FRAME_NOUN = r"(?:the\s+)?(?:frame|screen|image|shot|picture|khung)\b"
_REL_OF_AFTER = re.compile(r"^\s*of\s+(?!" + _FRAME_NOUN + r")", re.I)
_REL_VI_AFTER = re.compile(r"^\s*(?:của\s+)?(?!" + _FRAME_NOUN + r")", re.I)
_BODY_AFTER = re.compile(r"^[\s-]*(?:hand(?:ed)?|arms?|shoulders?|legs?|foot|feet|knees?|hips?|elbows?|wrists?|fists?|palms?|thumbs?|"
                         r"fingers?|eyes?|ears?|cheeks?|temples?|brows?|eyebrows?|thighs?|ankles?|gloves?|sleeves?|pockets?|holsters?|"
                         r"(?:side|half)\s+of\s+(?:her|his|its|their|the|\w+['’]s)\s+(?:face|head|body|neck|chest|waist|torso))\b", re.I)
_POSS_BEFORE = re.compile(r"(?:['’]s|\b(?:her|his|its|their|my|your))\s*$", re.I)          # "Kelly's right" / "to her left": phía của người
_PART_AFTER = re.compile(r"^[\s-]*(?:end|side|edge|half|part|corner|wing|tip|flank)\s+of\s+(?!(?:the\s+)?(?:frame|screen|image|shot|picture)\b)",
                         re.I)                                                          # "the RIGHT end of the wall": một đầu của vật
_FRAME_BEFORE = re.compile(r"\b(?:frame|screen)[\s-]*$", re.I)
_WHERE_AFTER = re.compile(r"^[\s-]*(?:(?:corner|side|edge)\s+(?:of\s+the\s+\w+\s+)?)?where\s+(.+?)(?=\s+(?:stand|stands|standing|is|are|sit|"
                          r"sits|sitting|wait|waits|waiting|crouch|crouches|lie|lies|lying|hide|hides|appear|appears|gather|gathers|lurk|"
                          r"lurks)\b|$)", re.I)


def _side_claims(clause: str, names: List[str]) -> Dict[str, set]:
    """{tên: {"left" / "right"}} mà vế chữ đặt CHO TÊN ĐÓ (theo chủ thể đúng của chữ trái/phải). Bộ phận cơ thể / phía của người / một đầu
    của vật → không phải chỗ trong khung, bỏ (không gán cho ai)."""
    spots = sorted((mt.start(), n) for n in names if n for mt in re.finditer(re.escape(str(n)), clause, re.I))
    out: Dict[str, set] = {}
    for tok in _SIDE_TOKEN.finditer(clause):
        word = (tok.group(1) or tok.group(2) or tok.group(3) or "").lower()
        side = "left" if word in ("left", "trái") else "right"
        before, after = clause[:tok.start()], clause[tok.end():]
        if tok.group(1):                                  # tiếng Anh: bộ phận cơ thể / sở hữu / một đầu của vật / "right of X"
            if _BODY_AFTER.match(after) or _POSS_BEFORE.search(before):
                continue
            if _PART_AFTER.match(after) and not _FRAME_BEFORE.search(before):
                continue
            if _REL_OF_AFTER.match(after):
                continue
        elif tok.group(2):                                # "bên phải (của) <tên>" → tương đối; "bên phải khung" → bên khung
            lead = _REL_VI_AFTER.match(after)
            if lead and (any(p == tok.end() + lead.end() for p, _ in spots) or re.match(r"\s*của\s+(?!khung\b)", after, re.I)):
                continue
        where = _WHERE_AFTER.match(after)
        if where:                                         # "frame-right where X stand(s)" → chủ thể là X (có thể không là ai trên map)
            lo, hi = tok.end() + where.start(1), tok.end() + where.end(1)
            inside = [n for p, n in spots if lo <= p < hi]
            if inside:
                out.setdefault(inside[0], set()).add(side)
            continue
        prev = [n for p, n in spots if p < tok.start()]
        nxt = [n for p, n in spots if p >= tok.end()]
        who = prev[-1] if prev else (nxt[0] if nxt else None)
        if who is not None:
            out.setdefault(who, set()).add(side)
    return out


def sentences_enabled() -> bool:
    from . import features
    return features.on(SENTENCE_FLAG) and enabled()


def _cam_rel(m: Dict, camera: Optional[Dict]) -> Optional[Tuple[List[float], List[float]]]:
    """stage_camera (tọa độ MODEL: location / look_at) → so với gốc O của map. Thiếu gì → None (không đoán máy)."""
    o = (m.get("origin") or {}).get("model_xyz")
    if not camera or not o or not camera.get("location") or not camera.get("look_at"):
        return None
    sub = lambda v: [float(v[k]) - float(o[k]) for k in range(2)]    # noqa: E731 — mặt sàn đủ cho trái / phải / xa gần
    return sub(camera["location"]), sub(camera["look_at"])


def frame_xy(loc: List[float], look: List[float], xy: List[float]) -> Optional[Tuple[float, float]]:
    """(ngang m — dương = phải khung, sâu m — dương = trước máy) của điểm xy trong hệ của máy; máy không có hướng → None.
    Một phép chiếu cho câu vị trí (M3.3) và bất biến R1 (core/position_invariants)."""
    import math
    fx, fy = look[0] - loc[0], look[1] - loc[1]
    n = math.hypot(fx, fy)
    if n < 1e-6:
        return None
    fx, fy = fx / n, fy / n
    dx, dy = xy[0] - loc[0], xy[1] - loc[1]
    return dx * fy - dy * fx, dx * fx + dy * fy          # phải của hướng nhìn (x Đông, y Bắc, z lên)


def _place(loc: List[float], look: List[float], xy: List[float]) -> Optional[Tuple[str, float]]:
    """(trái | giữa | phải khung, độ sâu m) của điểm xy nhìn từ máy; sau lưng máy → None."""
    import math
    got = frame_xy(loc, look, xy)
    if got is None:
        return None
    lateral, depth = got
    if depth <= 0.05:
        return None
    ang = math.degrees(math.atan2(lateral, depth))
    return ("centre" if abs(ang) < CENTRE_DEG else "right" if ang > 0 else "left"), depth


def position_sentence(m: Optional[Dict], shot, camera: Optional[Dict] = None) -> Tuple[Optional[str], Dict]:
    """(câu tiếng Anh | None, provenance). 3D: mọi thực thể có hiệu lực ở shot → trái / giữa / phải khung theo máy, người cùng phía xa hơn
    ≥ BEHIND_GAP_M = "behind", mốc = "in the distance"; ngoài khung (sau máy) ghi provenance.out_of_frame. Tương đối: quan hệ trái/phải +
    vật cầm của shot. Map unknown / invalidated / thiếu máy (3D) → None + why (đường cũ giữ nguyên)."""
    prov = {"map_revision": (m or {}).get("map_revision"), "kind": (m or {}).get("kind"), "shot": shot, "from": []}
    if not m or m.get("invalidated"):
        return None, dict(prov, why="không có map còn hiệu lực")
    if m.get("kind") == "unknown":
        return None, dict(prov, why=m.get("why") or "map UNKNOWN")
    ents = entities_at(m, shot)
    if m.get("kind") in ("3d", "2d"):
        cam = _cam_rel(m, camera)
        if cam is None:
            return None, dict(prov, why="thiếu máy của shot (stage_camera location / look_at) hoặc gốc O của map — không đoán khung")
        placed, out = [], []
        for e in ents:
            xyz = (e.get("transform") or {}).get("xyz")
            if not xyz:
                continue
            got = _place(cam[0], cam[1], xyz[:2])
            if got is None:
                out.append(e["entity_id"])
                continue
            placed.append((e, got[0], got[1]))
        if not placed:
            return None, dict(prov, why="không thực thể nào trong khung theo máy này", out_of_frame=out)
        people = [x for x in placed if x[0]["kind"] == "nguoi"]
        bits = []
        for e, side, depth in sorted(placed, key=lambda x: x[2]):
            label = e.get("label") or e["entity_id"]
            if e["kind"] == "moc":
                bits.append(f"{label} in the distance at {_SIDE_EN[side]}")
                continue
            front = [q for q in people if q[0] is not e and q[1] == side and depth - q[2] >= BEHIND_GAP_M]
            tail = f", behind {front[0][0].get('label') or front[0][0]['entity_id']}" if e["kind"] == "nguoi" and front else ""
            bits.append(f"{label} at {_SIDE_EN[side]}{tail}")
        prov.update({"from": ["entities", "stage_camera"], "out_of_frame": out,
                     "placed": {e["entity_id"]: side for e, side, _ in placed}})
        return "; ".join(bits) + ".", prov
    rel = [r for r in m.get("relations") or [] if r.get("valid_from") in (None, shot) or
           (isinstance(r.get("valid_from"), (int, float)) and r["valid_from"] <= shot <= (r.get("valid_to") or r["valid_from"]))]
    bits = [f"{r['a']} at frame left of {r['b']}" if r["rel"] == "trai_cua" else f"{r['a']} {r['rel'].replace('_', ' ')} {r['b']}" for r in rel]
    bits += [f"{e['entity_id']} holding {', '.join(e['state']['cam'])}" for e in ents if (e.get("state") or {}).get("cam")]
    if not bits:
        return None, dict(prov, why="map tương đối không có quan hệ nào ở shot này")
    placed = {}
    for r in rel:
        if r["rel"] == "trai_cua":
            placed.setdefault(r["a"], "left")
            placed.setdefault(r["b"], "right")
    prov.update({"from": ["relations"], "placed": placed})
    return "; ".join(bits) + ".", prov


def review(m: Optional[Dict], shot, current_text: str, camera: Optional[Dict] = None) -> Optional[Dict]:
    """REVIEW (cờ world_map_sentences + world_map; TẮT → None, không đọc gì): câu đề xuất + chỗ câu hiện tại (image_prompt / blocking) nói
    trái/phải NGƯỢC map cho cùng tên. Không sửa prompt, không chặn gen."""
    if not sentences_enabled():
        return None
    return side_review(m, shot, current_text, camera)


def side_review(m: Optional[Dict], shot, current_text: str, camera: Optional[Dict] = None) -> Dict:
    """Phần thuần của review (không đọc cờ): câu đề xuất + vế chữ nói trái/phải NGƯỢC map. Bất biến R1 (core/position_invariants) gọi
    trực tiếp — một cách đọc trái/phải cho cả REVIEW M3.3 và kiểm offline."""
    suggested, prov = position_sentence(m, shot, camera)
    out = {"level": "REVIEW", "shot": shot, "suggested": suggested, "provenance": prov, "mismatches": []}
    text = current_text or ""
    labels = {}
    for e in (m or {}).get("entities") or []:
        labels[e["entity_id"]] = e.get("label") or e["entity_id"]
    clauses = [c.strip() for c in _CLAUSE.split(text) if c and c.strip()]
    placed = prov.get("placed") or {}
    claims = [(c, _side_claims(c, [str(labels.get(eid, eid)) for eid in placed])) for c in clauses]
    for eid, side in placed.items():
        name = str(labels.get(eid, eid))
        other = "right" if side == "left" else "left" if side == "right" else None
        for c, got in claims:                      # trái/phải gán cho ĐÚNG chủ thể của vế (không vớ chữ của người khác / bộ phận cơ thể)
            sides = got.get(name) or set()
            if other and other in sides and side not in sides:
                out["mismatches"].append({"entity": name, "map": side, "text": c})
                break
    return out
