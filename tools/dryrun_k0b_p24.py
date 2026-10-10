"""K0b phần 1 — CHẠY KHÔ trên dự án #24 (0 USD, không gọi model, CHỈ ĐỌC bản chính D:/AI-Video-Pipeline).

Kế hoạch: docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md (A14, A18, A20, mục 3.1, dòng K0b). Kết quả: data_out/k0b_p24/ trong thư mục
đang chạy (worktree), không ghi gì vào bản chính. Tái chạy được:

    PYTHONUTF8=1 py tools/dryrun_k0b_p24.py [--main D:/AI-Video-Pipeline]

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

PID = 24
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


def build_byd(spec, data, conn):
    b = shot_intent.from_shot_spec(spec)
    dec = USER_DECISIONS.get(spec["shot"], {})
    if dec.get("may") and b["may"]["chuyen_dong"] == "dung_yen":
        b["may"]["chuyen_dong"] = dec["may"]
    suy = []
    nc = b["noi_chon"]
    nc["kho_id"] = KHO_LOCATION
    nc["spot"] = data.get("plate_spot")
    t = str(data.get("time") or "").lower()
    nc["thoi_gian"] = next((v for k, v in TIME.items() if k in t), None)
    w = str(data.get("weather") or "").lower()
    nc["thoi_tiet"] = w if w in shot_intent.THOI_TIET else None
    suy.append("noi_chon.thoi_gian/thoi_tiet ← scenes.data time/weather")
    names = {c["vat"] for c in b["thanh_phan"]}
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


def identity_rows(conn, chars, prompt, in_frame=None, byd=None):
    """Chỉ nhân vật có trong khung theo BYĐ (in_frame = khóa sân khấu); chữ của mỗi nhân vật = đoạn prompt nói về nó (segment).
    `byd` (thẩm định 4 #1) → món lọc theo cỡ cảnh / mặt-lưng / có trong khung của BYĐ (idd.byd_view): món máy không thấy = 'khong_can'
    kèm lý do; không có BYĐ → không lọc (như trước)."""
    out = []
    if in_frame is not None:                   # nhân vật không có khóa sân khấu → báo, không lọc im lặng
        out += [{"nhan_vat": c, "kho_id": CHAR_ASSET.get(c), "loi": "khong_co_STAGE_KEY", "tong": {}, "mon": []}
                for c in chars if c not in STAGE_KEY]
    chars = [c for c in chars if in_frame is None or STAGE_KEY.get(c) in in_frame]
    seg = idd.segment(prompt, {c: MARKERS.get(c, [c.lower()]) for c in chars})
    for name in chars:
        aid = CHAR_ASSET.get(name)
        row = conn.execute("SELECT profile, description FROM assets WHERE id=?", (aid,)).fetchone() if aid else None
        if row is None:                        # không có trong Kho → ĐỎ rõ ràng, không trả tổng 0 (trông như đạt)
            out.append({"nhan_vat": name, "kho_id": aid, "loi": "khong_co_trong_Kho", "nguon_khoa": None,
                        "tong": idd.summary(idd.check([], "")), "mon": idd.check([], "")})
            continue
        prof = json.loads(row[0]) if row[0] else {}
        mk = prof.get("must_keep")
        mk = ", ".join(map(str, mk)) if isinstance(mk, list) else mk
        src = "must_keep" if mk else "mo_ta_kho"
        decl, kbc_issues = idd.declare_from_profile(dict(prof, must_keep=mk), row[1] or "")   # K0b p2: ô khai_bao_chu thắng must_keep
        if any(d.get("nguon") == idd.KBC_KEY for d in decl):
            src = idd.KBC_KEY
        view = idd.byd_view(byd, STAGE_KEY.get(name)) if byd is not None else None
        rows = idd.check(decl, seg.get(name, ""), view=view)
        out.append({"nhan_vat": name, "kho_id": aid, "nguon_khoa": src, "thieu_must_keep": not mk, "loc_byd": view,
                    "khai_bao_chu_loi": kbc_issues, "mau_mo_ta_lech": idd.color_conflicts(row[1] or "", decl),
                    "loi": "khong_co_khoa" if any(r["trang_thai"] == "khong_co_khoa" for r in rows) else None,
                    "khong_nhan_ra": idd.unrecognized(decl), "tong": idd.summary(rows), "mon": rows})
    return out


def geometry(conn, data, prompt=None):
    res = stage_facts.for_shot(conn, PID, data)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", default="D:/AI-Video-Pipeline")
    ap.add_argument("--out", default=os.path.join(ROOT, "data_out/k0b_p24"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    conn = ro(a.main)
    specs = {s["shot"]: s for s in json.load(open(SPECS, encoding="utf-8"))["shots"]}
    scenes = {r[0]: (r[1], json.loads(r[2])) for r in conn.execute(
        "SELECT idx, id, data FROM scenes WHERE project_id=? ORDER BY idx", (PID,))}
    jobs = {}
    for jid, sid, res, refs in conn.execute("SELECT id, scene_id, result_path, sent_refs FROM jobs WHERE project_id=? AND "
                                            "type='image_gen' AND id BETWEEN 623 AND 640 AND result_path IS NOT NULL", (PID,)):
        jobs.setdefault(sid, []).append((jid, res, json.loads(refs or "[]")))
    pose_mode, pose_note = pose_tool(a.main)
    report = {"pose_tool": pose_note, "shots": []}
    byds = {}
    for idx, (sid, data) in scenes.items():
        spec = specs.get(idx)
        byd, issues, suy, note = build_byd(spec, data, conn) if spec else (None, [{"muc": "do", "truong": "", "loi": "không có spec"}], [], None)
        byds[idx] = byd
        with open(os.path.join(a.out, f"byd_shot{idx}.json"), "w", encoding="utf-8") as f:
            json.dump({"byd": byd, "issues": issues, "suy_tu_chu": suy, "quyet_dinh_nguoi_dung": note}, f, ensure_ascii=False, indent=1)
        people = [c["vat"] for c in (spec or {}).get("thanh_phan", []) if c["vat"] not in PROPS and c.get("vai") != "khong_duoc_co"]
        shot = {"shot": idx, "scene_id": sid, "byd_hop_le": not any(i["muc"] == "do" for i in issues),
                "byd_loi": issues, "suy_tu_chu": suy, "nguoi_trong_khung": people,
                "nhan_dien": identity_rows(conn, data.get("characters") or [], data.get("image_prompt") or "", set(people), byd=byd),
                "hinh_hoc": geometry(conn, data), "do": []}
        for jid, res, refs in sorted(jobs.get(sid, [])):
            plate = next((r for r in refs if r.get("role") == "place_render"), None)
            ppath = None
            if plate and plate.get("plate_key"):
                ppath = f"{a.main}/data/_plates3d/cache/{plate['plate_key']}/{plate.get('file') or 'plate.png'}"
            shot["do"].append({"job": jid, "mat_anh": faces(a.main, os.path.join(a.main, res)),
                               "mat_render": faces(a.main, ppath) if ppath else None, "render": plate and plate.get("file")})
        report["shots"].append(shot)
    # shot 4 prompt CŨ (trước câu sửa 10/10 'mouth')
    old = json.load(open(f"{a.main}/data/projects/{PID}/stage_v2/scene4_backup_20261010_mouth.json", encoding="utf-8"))
    report["shot4_prompt_cu"] = {"hinh_hoc": geometry(conn, old), "nhan_dien": old_prompt_identity(conn, old, byds.get(4))}
    with open(os.path.join(a.out, "summary.json"), "w", encoding="utf-8") as f:
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
    print("S4 cu:", report["shot4_prompt_cu"]["hinh_hoc"])


if __name__ == "__main__":
    main()
