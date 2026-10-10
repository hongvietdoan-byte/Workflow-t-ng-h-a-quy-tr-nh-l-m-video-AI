"""K0b phần 1 — CHẠY KHÔ trên dự án #24 / #22 (0 USD, không gọi model, CHỈ ĐỌC bản chính D:/AI-Video-Pipeline).

Kế hoạch: docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md (A14, A18, A20, A25, mục 3.1, dòng K0b). Kết quả: data_out/k0b_p<id>/ neo
theo gốc repo (worktree), không ghi gì vào bản chính. Tái chạy được:

    PYTHONUTF8=1 py tools/dryrun_k0b_p24.py [--project 24|22] [--main D:/AI-Video-Pipeline]

Tham số dự án (A25: ngưỡng A18 đo trên ≥ 2 dự án): cấu hình mỗi dự án ở PROJECTS. #22 KHÔNG có shot_specs viết tay → BYĐ dựng từ chữ
kịch bản (`spec_from_scene`: size / angle / characters / blocking của scenes.data, mọi ô ghi vào `suy_tu_chu`) rồi CÙNG đường
`shot_intent.from_shot_spec` → `build_byd` như #24. #22 không có prompt cũ shot 4 / khoảng job đo mặt → ghi rõ trong summary.
Mục 1–4 dưới đây là cách chạy #24:

1. BYĐ 9 shot: shot_specs viết tay (tools/experiments/stage_v2_p24/shot_specs.json) + quyết định người dùng 09/10 (TODO "người dùng CHỐT
   #24") → core.shot_intent.from_shot_spec; bổ sung hanh_dong / noi_chon từ chữ kịch bản (đánh dấu `suy_tu_chu`) → validate.
2. Khóa nhận diện A18/A20 (core.identity_declare) trên image_prompt thật — Kelly theo must_keep, yêu nữ 418/419 chưa có must_keep → mô tả Kho.
3. Hình học core.stage_facts trên stage_camera thật + prompt CŨ shot 4 (bản sao lưu 10/10 'mouth').
4. Công cụ đo: YuNet đếm mặt trên ảnh job 623–640 + render nền đã gửi; MediaPipe Pose nếu có model.
"""
import argparse
import glob
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # đường dẫn neo theo repo, không theo cwd
sys.path.insert(0, ROOT)
from core import identity_declare as idd  # noqa: E402
from core import shot_intent, stage_facts  # noqa: E402

PID = 24                                   # mặc định (tương thích người gọi cũ: tools/nhan_bao_nham_a18.py, tests)
KHO_LOCATION = 263
CHAR_ASSET = {"KELLY": 23, "YÊU NỮ TÀ LINH DẠNG 1": 418, "YÊU NỮ TÀ LINH DẠNG 2": 419}
STAGE_KEY = {"KELLY": "kelly", "YÊU NỮ TÀ LINH DẠNG 1": "yeunu", "YÊU NỮ TÀ LINH DẠNG 2": "yeunu"}
MARKERS = {"KELLY": ["kelly"], "YÊU NỮ TÀ LINH DẠNG 1": ["creature", "yêu nữ"], "YÊU NỮ TÀ LINH DẠNG 2": ["creature", "yêu nữ"]}
PROPS = ("gieng", "thap")
SPECS = os.path.join(ROOT, "tools/experiments/stage_v2_p24/shot_specs.json")
# Quyết định người dùng 09/10 (TODO.md khối "người dùng CHỐT #24") — chỗ shot_specs chưa ghi.
USER_DECISIONS = {
    4: {"note": "phương án 43: sau lưng-chéo Kelly ngã ngửa, máy thấp 0,6 m"},
    5: {"note": "máy sát đất 0,5 m, yêu nữ thò tay bám MÉP GẦN giếng"},
    6: {"note": "GÓC NHÌN Kelly ngồi (mắt 0,93 m), máy lùi 1 m rung nhẹ", "may": {"kieu": "lui", "m": 1.0, "rung": "nhe"}},
    7: {"note": "góc nhìn Kelly ngước lên, máy lùi tiếp 1 m rung nhẹ", "may": {"kieu": "lui", "m": 1.0, "rung": "nhe"}},
}
# Món NHẬN DIỆN của chính nhân vật (không đổi khi thay trang phục): nhân vật mặc trang phục Kho (#22 'MAXIM KL') giữ các món này từ hồ
# sơ nhân vật, mọi món khác lấy từ trang phục — CSDL #22 characters.description "Chính là MAXIM (cùng mặt, cùng tóc) … sau khi mặc bộ
# Khủng Long Đỏ nam"; mô tả Kho #416/#417 "tóc, mặt, dáng lấy theo NHÂN VẬT đang mặc, không theo người mẫu".
IDENTITY_ITEMS = ("hair", "face", "eyes")
PROJECTS = {
    24: {"kho_location": KHO_LOCATION, "char_asset": CHAR_ASSET, "outfit": {}, "stage_key": STAGE_KEY, "markers": MARKERS,
         "specs": SPECS, "user_decisions": USER_DECISIONS, "jobs": (623, 640),
         "old_prompt": "stage_v2/scene4_backup_20261010_mouth.json"},
    # #22 Khủng Long Đỏ: mã Kho theo project_assets (23 Kelly, 33 Maxim, 416/417 bộ KL); trang phục 'KL' = characters.outfit_image_ids
    # 1116 / 1117 → asset_images.asset_id 416 / 417 (CSDL 10/10). Không có shot_specs / prompt cũ / khoảng job đo mặt.
    22: {"kho_location": None, "char_asset": {"MAXIM": 33, "KELLY": 23, "MAXIM KL": 33, "KELLY KL": 23},
         "outfit": {"MAXIM KL": 416, "KELLY KL": 417},
         "stage_key": {"MAXIM": "maxim", "MAXIM KL": "maxim", "KELLY": "kelly", "KELLY KL": "kelly"},
         "markers": {"MAXIM": ["maxim"], "MAXIM KL": ["maxim kl", "maxim khủng long", "maxim"],
                     "KELLY": ["kelly"], "KELLY KL": ["kelly kl", "kelly khủng long", "kelly"]},
         "specs": None, "user_decisions": {}, "jobs": None, "old_prompt": None},
}
# scenes.data.angle (core/camera_plan.ANGLES) → (may.do_cao, may.goc) của BYĐ; 'ots' (qua vai) không nói độ cao / góc → không suy
ANGLE_TO_MAY = {"eye": ("ngang", "ngang"), "high": ("cao", "cui"), "overhead": ("tren_dau", "cui"), "low": ("thap", "ngua")}
ZONE_WORDS = [(r"frame[- ]left|left of (?:the )?frame|on the left", "trai"),
              (r"frame[- ]right|right of (?:the )?frame|on the right", "phai"),
              (r"frame[- ]cent(?:er|re)|cent(?:er|re)[- ]frame|in the cent(?:er|re)", "giua")]
VIEW_WORDS = [(r"back to (?:the )?camera|from behind|back view|rear view", "lung"),
              (r"facing (?:the )?camera|faces (?:the )?camera", "mat")]


def out_dir(pid) -> str:
    """data_out/k0b_p<pid> NEO THEO GỐC REPO (không theo cwd)."""
    return os.path.join(ROOT, "data_out", f"k0b_p{int(pid)}")


def project_config(pid) -> dict:
    """Cấu hình chạy khô của dự án `pid` (+ pid, out). Dự án chưa khai → SystemExit nói rõ, không chạy nhầm cấu hình #24."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        raise SystemExit(f"--project phải là số dự án, nhận {pid!r}")
    if pid not in PROJECTS:
        raise SystemExit(f"dự án #{pid} chưa có cấu hình chạy khô (PROJECTS chỉ có {sorted(PROJECTS)}) — khai mã Kho / từ đánh dấu trước")
    return dict(PROJECTS[pid], pid=pid, out=out_dir(pid))


def _first(patterns, text):
    low = str(text or "").lower()
    for pat, val in patterns:
        m = re.search(pat, low)
        if m:
            return val, m.group(0)
    return None, None


def spec_from_scene(idx, data, cfg):
    """Dự án KHÔNG có shot_specs viết tay (#22): dựng một mục shot_specs từ chữ kịch bản → (spec, suy). Cỡ = assets.shot_size (size /
    chữ shot); do_cao + goc ← angle (ANGLE_TO_MAY; góc lạ → để trống, ghi suy); thanh_phan = mỗi nhân vật trong `characters` có khóa sân
    khấu (vai chinh; trùng khóa — Maxim / Maxim KL — gộp một); vùng + mặt/lưng suy từ đoạn `blocking` nói về nhân vật đó
    (identity_declare.segment). Chữ không nói → không đoán. Không có nhân vật → thanh_phan rỗng (validate báo ĐỎ, không bịa)."""
    from core import assets
    suy = []
    co = assets.shot_size(data)
    suy.append(f"may.co ← scenes.data size/shot = {co!r}")
    angle = str(data.get("angle") or "").strip().lower()
    do_cao, goc = ANGLE_TO_MAY.get(angle, (None, None))
    suy.append(f"may.do_cao/goc ← angle {angle!r} = {do_cao}/{goc}" + ("" if do_cao else " (góc không quy được — goc trống, do_cao theo mặc định from_shot_spec 'ngang')"))
    chars = [c for c in data.get("characters") or [] if c in cfg["stage_key"]]
    seg = idd.segment(data.get("blocking") or "", {c: cfg["markers"].get(c, [c.lower()]) for c in chars}) if chars else {}
    tp, seen = [], set()
    for c in chars:
        key = cfg["stage_key"][c]
        if key in seen:
            continue
        seen.add(key)
        item = {"vat": key, "vai": "chinh"}
        vung, w1 = _first(ZONE_WORDS, seg.get(c))
        thay, w2 = _first(VIEW_WORDS, seg.get(c))
        if vung:
            item["vung"] = vung
        if thay:
            item["thay"] = thay
        tp.append(item)
        suy.append(f"thanh_phan[{key}] ← characters; vung={vung} ({w1!r}), thay={thay} ({w2!r}) từ blocking")
    if not chars:
        suy.append("thanh_phan rỗng: scenes.data.characters không có nhân vật có khóa sân khấu (shot không người?)")
    return {"shot": int(idx), "co": co, "do_cao": do_cao, "goc": goc, "thanh_phan": tp,
            "muc_dich": str(data.get("action") or "")}, suy
POSE_WORDS = [  # (regex trên chữ hành động tiếng Anh, tu_the, cham_dat) — thứ tự ưu tiên
    (r"\blying\b|\blies (?:flat|on)|\blaid out", "nam", ["lung"]),
    (r"fallen backward|fall(?:s|en)? back|sprawl|on (?:her|his) back", "nga_ngua", ["mong", "ban_tay"]),   # K0b p2: enum có nga_ngua
    (r"\bkneel", "quy", ["dau_goi"]),
    (r"\bcrawl", "bo", ["ban_tay", "dau_goi"]),
    (r"\bsit|\bseated|\bsitting|on the ground", "ngoi", ["mong"]),
    (r"\bstand|\bwalk|\blean|\bstep|\brun", "dung", ["ban_chan"]),
]
TIME = {"đêm": "night", "night": "night", "ngày": "day", "day": "day", "dusk": "dusk", "dawn": "dawn"}


def ro(main):
    c = sqlite3.connect(f"file:{main}/data/manifest.sqlite?mode=ro", uri=True)
    c.row_factory = sqlite3.Row               # core.assets / place_refs đọc theo tên cột
    return c


def pose_from_text(text):
    low = str(text or "").lower()
    for pat, tu_the, cham in POSE_WORDS:
        m = re.search(pat, low)
        if m:
            return {"tu_the": tu_the, "cham_dat": cham}, m.group(0)
    return None, None


def build_byd(spec, data, conn, cfg=None):
    cfg = cfg or project_config(PID)
    b = shot_intent.from_shot_spec(spec)
    dec = cfg["user_decisions"].get(spec["shot"], {})
    if dec.get("may") and b["may"]["chuyen_dong"] == "dung_yen":
        b["may"]["chuyen_dong"] = dec["may"]
    suy = []
    nc = b["noi_chon"]
    nc["kho_id"] = cfg["kho_location"] or data.get("location_asset")
    nc["spot"] = data.get("plate_spot")
    t = str(data.get("time") or "").lower()
    nc["thoi_gian"] = next((v for k, v in TIME.items() if k in t), None)
    w = str(data.get("weather") or "").lower()
    nc["thoi_tiet"] = w if w in shot_intent.THOI_TIET else None
    suy.append("noi_chon.thoi_gian/thoi_tiet ← scenes.data time/weather")
    names = list(dict.fromkeys(c["vat"] for c in b["thanh_phan"]))   # thứ tự thanh_phan (set làm tệp ra đổi thứ tự mỗi lần chạy)
    text = " ".join(str(data.get(k) or "") for k in ("action", "end_state", "image_prompt"))
    for who in [c for c in names if c not in PROPS]:
        st, phrase = pose_from_text(data.get("action") if data.get("action") else text)
        if st is None:
            st, phrase = pose_from_text(text)
        if st:
            b["hanh_dong"].append({"ai": who, "bat_dau": st, "suy_tu_chu": True, "cum_tu": phrase})
            suy.append(f"hanh_dong[{who}].bat_dau ← chữ '{phrase}'")
    issues = shot_intent.validate(b, conn)
    return b, issues, suy, dec.get("note")


def _kho_decl(conn, aid):
    """Khóa của một mã Kho → (decl, lỗi khai_bao_chu, nguồn, có must_keep, mô tả) hoặc None nếu không có trong Kho."""
    row = conn.execute("SELECT profile, description FROM assets WHERE id=?", (aid,)).fetchone() if aid else None
    if row is None:
        return None
    prof = json.loads(row[0]) if row[0] else {}
    mk = prof.get("must_keep")
    mk = ", ".join(map(str, mk)) if isinstance(mk, list) else mk
    src = "must_keep" if mk else "mo_ta_kho"
    decl, kbc_issues = idd.declare_from_profile(dict(prof, must_keep=mk), row[1] or "")   # K0b p2: ô khai_bao_chu thắng must_keep
    if any(d.get("nguon") == idd.KBC_KEY for d in decl):
        src = idd.KBC_KEY
    return decl, kbc_issues, src, bool(mk), row[1] or ""


def identity_rows(conn, chars, prompt, in_frame=None, byd=None, cfg=None):
    """Chỉ nhân vật có trong khung theo BYĐ (in_frame = khóa sân khấu); chữ của mỗi nhân vật = đoạn prompt nói về nó (segment).
    `byd` (thẩm định 4 #1) → món lọc theo cỡ cảnh / mặt-lưng / có trong khung của BYĐ (idd.byd_view): món máy không thấy = 'khong_can'
    kèm lý do; không có BYĐ → không lọc (như trước). `cfg` = project_config (mặc định #24). Nhân vật mặc trang phục Kho (cfg outfit,
    #22 'MAXIM KL') → khóa = món IDENTITY_ITEMS của nhân vật + mọi món khác của trang phục; trang phục không có trong Kho → ĐỎ."""
    cfg = cfg or project_config(PID)
    char_asset, stage_key, markers, outfit = cfg["char_asset"], cfg["stage_key"], cfg["markers"], cfg.get("outfit") or {}
    out = []
    if in_frame is not None:                   # nhân vật không có khóa sân khấu → báo, không lọc im lặng
        out += [{"nhan_vat": c, "kho_id": char_asset.get(c), "loi": "khong_co_STAGE_KEY", "tong": {}, "mon": []}
                for c in chars if c not in stage_key]
    chars = [c for c in chars if in_frame is None or stage_key.get(c) in in_frame]
    seg = idd.segment(prompt, {c: markers.get(c, [c.lower()]) for c in chars})
    for name in chars:
        aid = char_asset.get(name)
        got = _kho_decl(conn, aid)
        oid = outfit.get(name)
        got_o = _kho_decl(conn, oid) if oid else None
        if got is None or (oid and got_o is None):   # không có trong Kho → ĐỎ rõ ràng, không trả tổng 0 (trông như đạt)
            out.append({"nhan_vat": name, "kho_id": aid if got is None else oid, "loi": "khong_co_trong_Kho", "nguon_khoa": None,
                        "tong": idd.summary(idd.check([], "")), "mon": idd.check([], "")})
            continue
        decl, kbc_issues, src, has_mk, mo_ta = got
        if got_o is not None:
            def key(d):
                return idd._item_key(d) or d["mon"]
            decl = [d for d in decl if key(d) in IDENTITY_ITEMS] + [d for d in got_o[0] if key(d) not in IDENTITY_ITEMS]
            kbc_issues = kbc_issues + got_o[1]
            src, mo_ta = f"{src}[{'+'.join(IDENTITY_ITEMS)}]+trang_phuc_{oid}:{got_o[2]}", got_o[4]
        view = idd.byd_view(byd, stage_key.get(name)) if byd is not None else None
        rows = idd.check(decl, seg.get(name, ""), view=view)
        out.append({"nhan_vat": name, "kho_id": aid, "trang_phuc_kho_id": oid, "nguon_khoa": src, "thieu_must_keep": not has_mk,
                    "loc_byd": view, "khai_bao_chu_loi": kbc_issues, "mau_mo_ta_lech": idd.color_conflicts(mo_ta, decl),
                    "loi": "khong_co_khoa" if any(r["trang_thai"] == "khong_co_khoa" for r in rows) else None,
                    "khong_nhan_ra": idd.unrecognized(decl), "tong": idd.summary(rows), "mon": rows})
    return out


def geometry(conn, data, prompt=None, pid=None):
    res = stage_facts.for_shot(conn, PID if pid is None else pid, data)
    facts = res["facts"]
    contra = stage_facts.contradictions(prompt if prompt is not None else data.get("image_prompt") or "", facts)
    return {"missing": res.get("missing"), "notes": res.get("notes"),
            "facts": {f["id"]: f["value"] for f in facts},
            "contradictions": [{"fact": c["fact"], "phrase": c["phrase"], "level": c["level"]} for c in contra]}


def faces(main, path):
    from core import text_placement
    os.environ.setdefault("FACE_MODEL", f"{main}/data/models/face_detection_yunet_2023mar.onnx")
    if not os.path.exists(path):
        return None
    b = text_placement.face_boxes(path, os.environ["FACE_MODEL"])
    return None if b is None else len(b)


def pose_tool(main):
    """MediaPipe Pose: chỉ dùng thứ đã có — mediapipe.solutions (bản cũ, model kèm gói) hoặc Tasks + data/models/pose_landmarker*.task."""
    try:
        import mediapipe as mp
    except Exception as e:  # noqa: BLE001
        return None, f"không import được mediapipe: {e}"
    if hasattr(mp, "solutions"):
        return "solutions", f"mediapipe {mp.__version__} có solutions.pose"
    models = glob.glob(f"{main}/data/models/pose_landmarker*.task")
    if models:
        return models[0], f"mediapipe {mp.__version__} Tasks + {os.path.basename(models[0])}"
    return None, (f"mediapipe {mp.__version__} KHÔNG có mp.solutions (bỏ ở 1.x) và KHÔNG có data/models/pose_landmarker*.task "
                  "→ chưa đo được tư thế (cần tải model ≈ 5–30 MB — hỏi người dùng)")


def old_prompt_identity(conn, old, byd):
    """Khóa nhận diện trên prompt CŨ shot 4 — lọc bằng CÙNG BYĐ shot 4 như prompt mới (rà độc lập #5: so cũ ↔ mới không lẫn hiệu ứng
    lọc). Không có BYĐ shot 4 → không lọc (byd None), như identity_rows."""
    return identity_rows(conn, old.get("characters") or [], old.get("image_prompt") or "", {"kelly"}, byd=byd)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int, default=PID, help=f"dự án có cấu hình ({sorted(PROJECTS)})")
    ap.add_argument("--main", default="D:/AI-Video-Pipeline")
    ap.add_argument("--out", default=None, help="mặc định data_out/k0b_p<project> neo theo gốc repo")
    a = ap.parse_args(argv)
    cfg = project_config(a.project)
    pid, out = cfg["pid"], a.out or cfg["out"]
    os.makedirs(out, exist_ok=True)
    conn = ro(a.main)
    scenes = {r[0]: (r[1], json.loads(r[2])) for r in conn.execute(
        "SELECT idx, id, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,))}
    if not scenes:
        raise SystemExit(f"dự án #{pid}: CSDL {a.main} không có scenes — không có gì để chạy khô")
    specs, spec_src = {}, "shot_specs viết tay"
    if cfg["specs"]:
        specs = {s["shot"]: (s, []) for s in json.load(open(cfg["specs"], encoding="utf-8"))["shots"]}
    else:
        spec_src = "suy từ chữ kịch bản (scenes.data) — KHÔNG có shot_specs viết tay"
        specs = {idx: spec_from_scene(idx, data, cfg) for idx, (_sid, data) in scenes.items()}
    jobs, jobs_note = {}, None
    if cfg["jobs"]:
        lo, hi = cfg["jobs"]
        for jid, sid, res, refs in conn.execute("SELECT id, scene_id, result_path, sent_refs FROM jobs WHERE project_id=? AND "
                                                "type='image_gen' AND id BETWEEN ? AND ? AND result_path IS NOT NULL", (pid, lo, hi)):
            jobs.setdefault(sid, []).append((jid, res, json.loads(refs or "[]")))
    else:
        jobs_note = (f"#{pid} chưa khai khoảng job ảnh để đếm mặt YuNet ở đây — 'do' để trống (đo công cụ #22 ở "
                     "tools/measure_tools_k0b.py → data_out/k0b_tools)")
    pose_mode, pose_note = pose_tool(a.main)
    report = {"project": pid, "nguon_byd": spec_src, "pose_tool": pose_note, "do_ghi_chu": jobs_note, "shots": []}
    byds = {}
    for idx, (sid, data) in scenes.items():
        spec, spec_suy = specs.get(idx) or (None, [])
        if spec:
            byd, issues, suy, note = build_byd(spec, data, conn, cfg)
            suy = spec_suy + suy
        else:
            byd, issues, suy, note = None, [{"muc": "do", "truong": "", "loi": "không có spec"}], [], None
        byds[idx] = byd
        with open(os.path.join(out, f"byd_shot{idx}.json"), "w", encoding="utf-8") as f:
            json.dump({"byd": byd, "issues": issues, "suy_tu_chu": suy, "quyet_dinh_nguoi_dung": note}, f, ensure_ascii=False, indent=1)
        people = [c["vat"] for c in (spec or {}).get("thanh_phan", []) if c["vat"] not in PROPS and c.get("vai") != "khong_duoc_co"]
        shot = {"shot": idx, "scene_id": sid, "byd_hop_le": not any(i["muc"] == "do" for i in issues),
                "byd_loi": issues, "suy_tu_chu": suy, "nguoi_trong_khung": people,
                "nhan_dien": identity_rows(conn, data.get("characters") or [], data.get("image_prompt") or "", set(people), byd=byd,
                                           cfg=cfg),
                "hinh_hoc": geometry(conn, data, pid=pid), "do": []}
        for jid, res, refs in sorted(jobs.get(sid, [])):
            plate = next((r for r in refs if r.get("role") == "place_render"), None)
            ppath = None
            if plate and plate.get("plate_key"):
                ppath = f"{a.main}/data/_plates3d/cache/{plate['plate_key']}/{plate.get('file') or 'plate.png'}"
            shot["do"].append({"job": jid, "mat_anh": faces(a.main, os.path.join(a.main, res)),
                               "mat_render": faces(a.main, ppath) if ppath else None, "render": plate and plate.get("file")})
        report["shots"].append(shot)
    if cfg["old_prompt"]:                      # #24: shot 4 prompt CŨ (trước câu sửa 10/10 'mouth')
        old = json.load(open(f"{a.main}/data/projects/{pid}/{cfg['old_prompt']}", encoding="utf-8"))
        report["shot4_prompt_cu"] = {"hinh_hoc": geometry(conn, old, pid=pid), "nhan_dien": old_prompt_identity(conn, old, byds.get(4))}
    else:
        report["shot4_prompt_cu"] = None
        report["prompt_cu_ghi_chu"] = f"#{pid} không có bản sao lưu prompt cũ để so (chỉ #24 shot 4)"
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    # in gọn
    print("pose:", pose_note)
    for s in report["shots"]:
        ids = "; ".join(f"{n['nhan_vat'][:12]}({n.get('nguon_khoa') or n.get('loi')}) " + ",".join(f"{m['mon']}={m['trang_thai']}" for m in n["mon"])
                        for n in s["nhan_dien"])
        g = s["hinh_hoc"]
        print(f"S{s['shot']} byd={'OK' if s['byd_hop_le'] else 'DO'} loi={[i['truong'] + ':' + i['loi'][:40] for i in s['byd_loi']]} "
              f"suy={len(s['suy_tu_chu'])} | {ids} | facts={g['facts']} contra={g['contradictions']} | "
              f"do={[(d['job'], d['mat_anh'], d['mat_render']) for d in s['do']]} nguoi={s['nguoi_trong_khung']}")
    print("S4 cu:", (report["shot4_prompt_cu"] or {}).get("hinh_hoc") or report.get("prompt_cu_ghi_chu"))
    print("ghi", out, "| BYĐ:", spec_src, "|", jobs_note or "")


if __name__ == "__main__":
    main()
