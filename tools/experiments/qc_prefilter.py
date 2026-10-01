r"""Lọc trước bộ độc lập của Tổ QC bằng các tầng MIỄN PHÍ (0 USD, không gọi model) — docs/THIET_KE_TO_QC_2026-10-01.md mục 21.

    py tools/experiments/qc_prefilter.py                      134 khung (#1 #2 #3 #4 #7 #10 #11 #12 #13, ảnh image_gen trừ job hủy)
    py tools/experiments/qc_prefilter.py --db D:/AI-Video-Pipeline/data/manifest.sqlite

Mỗi khung: tầng 0 (khung trống, số mặt so bảng shot, hướng mắt chắc chắn sai, màu trời so giờ) + bộ dịch đặc tả (bảng shot tự mâu thuẫn)
+ lịch sử có sẵn (quyết định duyệt / loại kèm ghi chú trong review_log — nguồn: người / phiên vận hành / [thử tự động]).
Ra NHÃN GỢI Ý (Đạt / Chặn / để trống) + loại lỗi + lý do + độ tin — chỉ để người dùng xác nhận, không phải nhãn. Điểm QC cũ (qc_results)
chỉ in kèm, không dùng để gợi ý (tự QC cũ báo nhầm nhiều — S7.1).
Ra: data/qc_golden/prefilter.json + prefilter.csv (cột khớp Google Sheet) — CSDL chỉ đọc.
"""
import argparse
import csv
import glob
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
PROJECTS = (1, 2, 3, 4, 7, 10, 11, 12, 13)
CATEGORIES = ("Nhân vật", "Hướng nhìn / diễn xuất", "Liền mạch / ánh sáng", "Bối cảnh / kiến trúc", "Kỹ thuật", "Khác")
# reject note → category: the category whose words come earliest in the note wins
NOTE_CATEGORY = (
    (r"semi-realistic|cel-shading|no (black )?outlines?|same .{0,30}style|phong cách", "Kỹ thuật"),
    (r"hair|\bcap\b|outfit|tracksuit|jacket|hoodie|tank top|sneakers|shoes|glove|scar|stubble|beard|topknot|identity|character [0-9.]|missing|extra|"
     r"wrong person|must (have|wear|match)|ponytail|redraw (kelly|maxim|kenta)|tóc|trang phục|nhận diện|nhân vật", "Nhân vật"),
    (r"look(s|ing)? (at|toward)|gaze|eyeline|hướng nhìn|\bpose\b|diễn", "Hướng nhìn / diễn xuất"),
    (r"reframe|framing|close-up|wide shot|cỡ cảnh", "Kỹ thuật"),
    (r"\bnight\b|void|black background|\blight(ing)?\b|daylight|\btint\b|ánh sáng|đêm|liền mạch", "Liền mạch / ánh sáng"),
    (r"background|tower|tháp|place|render reference|wall|barn|reference photo|bối cảnh|kiến trúc|nền", "Bối cảnh / kiến trúc"),
)
# notes that redraw for a reason outside the frame (profile changed, a planned retake) — not evidence of a defect
NOT_A_DEFECT = re.compile(r"gen lại có chủ đích|vẽ lại sau khi sửa hồ sơ|sau khi sửa", re.I)
BLANK_STD = 6.0          # grey-level spread below this = an empty / one-colour frame
NIGHT = ("night", "midnight", "đêm", "dusk")
DAYTIME = ("day", "noon", "midday", "morning", "afternoon", "ngày", "trưa", "sáng")


def source_of(note: str) -> str:
    n = str(note or "")
    if "[thử tự động]" in n:
        return "thử tự động"
    if "phiên vận hành" in n:
        return "phiên vận hành"
    if n.startswith("Đồng bộ cả bộ"):          # core/claude_tasks.redo_from_set_check: Claude's set QC wrote it, the person pressed redo
        return "người bấm theo QC đồng bộ"
    return "người"


def category_of_note(note: str) -> str:
    """The category whose words come EARLIEST in the note (the first sentence names the main fault)."""
    t = str(note or "").lower()
    if t.startswith("đồng bộ cả bộ") and not re.search(r"\bmust\b|\bredraw\b|re-render|\bwrong\b", t):
        return "Khác"                            # a whole new description of the shot, no defect named
    t = re.sub(r"\bkeep\b[^.]*\.", "", t)      # "Keep the composition, lighting…" names what is right, not the fault
    hits = [(m.start(), c) for pat, c in NOTE_CATEGORY for m in [re.search(pat, t)] if m]
    return min(hits)[1] if hits else "Khác"


def frames(conn, data_dir):
    out = []
    for pid in PROJECTS:
        files = {}
        for f in glob.glob(os.path.join(data_dir, str(pid), "trash", "images", "job_*.png")):
            files.setdefault(int(re.search(r"job_(\d+)", os.path.basename(f)).group(1)), []).append(f)
        for f in glob.glob(os.path.join(data_dir, str(pid), "images", "job_*.png")):
            files[int(re.search(r"job_(\d+)", os.path.basename(f)).group(1))] = [f]     # the live picture wins
        for job in sorted(files):
            row = conn.execute("SELECT j.state, s.idx, s.data FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.id=?", (job,)).fetchone()
            if row is None or row["state"] == "cancelled":
                continue
            out.append({"pid": pid, "job": job, "state": row["state"], "path": sorted(files[job])[-1],
                        "data": json.loads(row["data"] or "{}"), "idx": row["idx"]})
    return out


def blank(path):
    try:
        import numpy as np
        from PIL import Image
        a = np.asarray(Image.open(path).convert("L").resize((128, 128)), dtype=float)
    except Exception:  # noqa: BLE001
        return None
    return round(float(a.std()), 1)


def history(conn, job):
    rows = conn.execute("SELECT reviewer_type, decision, note, decided_at FROM review_log WHERE job_id=? ORDER BY decided_at, id",
                        (job,)).fetchall()
    qc = conn.execute("SELECT criterion, score, threshold_at_time FROM qc_results WHERE job_id=? AND criterion<>'scene_qc_hold'",
                      (job,)).fetchall()
    low = sorted(((r["score"], r["criterion"]) for r in qc if r["score"] < r["threshold_at_time"]))[:3]
    mod = conn.execute("SELECT COUNT(*) FROM content_moderation_failures WHERE job_id=?", (job,)).fetchone()[0]
    return {"reviews": [{"by": r["reviewer_type"], "decision": r["decision"], "source": source_of(r["note"]) if r["reviewer_type"] == "user"
                         else "agent", "note": r["note"] or ""} for r in rows],
            "qc_low": [f"{c} {s:.2f}" for s, c in low], "moderation": mod}


def tier0(conn, f):
    from core import qc_measure, qc_spec
    d = f["data"]
    spec = qc_spec.compile_frame(conn, f["pid"], f["job"], d)
    code = qc_measure.measure_frame(f["path"], d, spec["assertions"])
    flags = []
    std = blank(f["path"])
    if std is not None and std < BLANK_STD:
        flags.append({"kind": "blank", "sure": True, "category": "Kỹ thuật", "text": f"khung gần như một màu (độ lệch xám {std})"})
    cast = [str(c).upper() for c in d.get("characters") or []]
    nf = (code.get("_faces") or {}).get("count")
    if nf is not None:
        if cast and nf == 0 and not any(qc_spec.view_of(d, n) == "behind" for n in cast) \
                and str(d.get("size") or "").upper() in ("ECU", "CU", "MCU", "MS"):
            flags.append({"kind": "no_face", "sure": False, "category": "Nhân vật",
                          "text": f"bảng shot {len(cast)} người ({', '.join(cast)}), cỡ {d.get('size')}, nhìn máy — code không thấy mặt nào"})
        elif nf > len(cast) and nf - len(cast) >= 2:
            flags.append({"kind": "extra_faces", "sure": False, "category": "Nhân vật",
                          "text": f"{nf} mặt, bảng shot {len(cast)} người — có thể thừa người (bộ dò đôi khi nhầm)"})
        elif not cast and nf > 0:
            flags.append({"kind": "extra_faces", "sure": False, "category": "Nhân vật",
                          "text": f"bảng shot không có ai nhưng thấy {nf} mặt"})
    for a in spec["assertions"]:
        c = code.get(a["id"]) or {}
        if a["type"] == "gaze" and c.get("status") == "certain_fail":
            flags.append({"kind": "gaze", "sure": a["severity_if_false"] == "block", "category": "Hướng nhìn / diễn xuất",
                          "text": f"{a['subject']}: {c.get('note')} (cần nhìn {a['expected']})"
                                  + ("" if a["severity_if_false"] == "block" else " — shot không thoại, mức nhỏ")})
    sk = code.get("_sky") or {}
    want = str(d.get("time") or "").lower()
    if sk and want:
        if any(w in want for w in NIGHT) and sk.get("reading") == "day" and sk.get("brightness", 0) > 120:
            flags.append({"kind": "sky", "sure": False, "category": "Liền mạch / ánh sáng",
                          "text": f"bảng shot giờ '{d.get('time')}' mà dải trời sáng (độ sáng {sk['brightness']}, B−R {sk['b_minus_r']})"})
        elif any(w in want for w in DAYTIME) and sk.get("reading") == "dark":
            flags.append({"kind": "sky", "sure": False, "category": "Liền mạch / ánh sáng",
                          "text": f"bảng shot giờ '{d.get('time')}' mà dải trời tối (độ sáng {sk['brightness']})"})
    for pc in spec["plan_conflicts"]:
        flags.append({"kind": "plan_conflict", "sure": False, "category": "Khác", "text": "bảng shot tự mâu thuẫn: " + pc})
    return flags, {"faces": nf, "sky": sk, "blank_std": std, "cast": cast, "size": d.get("size"), "time": d.get("time"),
                   "missing_profiles": spec["missing_profiles"]}


def suggest(f, flags, hist):
    """(label, category, reason, confidence). A human reject with a defect note → Chặn; a sure code finding → Chặn; a final approve
    with no flag → Đạt; anything else → empty (the person decides)."""
    users = [r for r in hist["reviews"] if r["by"] == "user"]
    last = users[-1] if users else None
    sure = [x for x in flags if x["sure"]]
    if sure:
        return "Chặn", sure[0]["category"], "tầng 0 chắc chắn: " + sure[0]["text"], "cao"
    rejects = [r for r in users if r["decision"] == "reject" and r["note"].strip() and not NOT_A_DEFECT.search(r["note"])]
    if rejects and (last is None or last["decision"] == "reject"):
        r = rejects[-1]
        conf = {"người": "cao", "người bấm theo QC đồng bộ": "vừa", "phiên vận hành": "vừa", "thử tự động": "thấp"}[r["source"]]
        return "Chặn", category_of_note(r["note"]), f"đã bị loại ({r['source']}): {r['note'][:160]}", conf
    if last and last["decision"] == "approve" and f["state"] == "approved":
        if flags:
            return "", flags[0]["category"], f"đã duyệt ({last['source']}) nhưng tầng 0 báo: {flags[0]['text']}", "thấp"
        conf = {"người": "vừa"}.get(last["source"], "thấp")
        return "Đạt", "", f"đã duyệt ({last['source']}), tầng 0 không báo gì", conf
    agent = [r for r in hist["reviews"] if r["by"] == "ai_agent"]
    if not users and agent and not flags:       # only the old automatic QC spoke (S7.1: it passed real faults) — weakest hint
        r = agent[-1]
        if r["decision"] == "reject":
            return "Chặn", category_of_note(r["note"]), f"QC tự động cũ loại: {r['note'][:160]}", "thấp"
        return "Đạt", "", "QC tự động cũ duyệt, tầng 0 không báo gì", "thấp"
    if flags:
        return "", flags[0]["category"], "tầng 0 nghi: " + flags[0]["text"], "thấp"
    return "", "", "chưa có bằng chứng miễn phí — cần mắt người", ""


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.join("data", "manifest.sqlite"))
    ap.add_argument("--out", default=None, help="thư mục ra (mặc định data/qc_golden cạnh CSDL)")
    a = ap.parse_args(argv)
    db = os.path.abspath(a.db)
    models = os.path.join(os.path.dirname(db), "models")              # a worktree has no data/models: read the main checkout's
    os.environ.setdefault("FACE_MODEL", os.path.join(models, "face_detection_yunet_2023mar.onnx"))
    os.environ.setdefault("LIP_MODEL", os.path.join(models, "face_landmarker.task"))
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    data_dir = os.path.join(os.path.dirname(db), "projects")
    out_dir = a.out or os.path.join(os.path.dirname(db), "qc_golden")
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    fs = frames(conn, data_dir)
    print(f"{len(fs)} khung")
    for f in fs:
        flags, meas = tier0(conn, f)
        hist = history(conn, f["job"])
        label, cat, why, conf = suggest(f, flags, hist)
        d = f["data"]
        rows.append({"id": f"P{f['pid']}-J{f['job']}", "project": f["pid"], "job": f["job"], "shot": f"S{d.get('story_scene')}·{d.get('shot_no')}" if d.get("story_scene") else f"cảnh {f['idx']}",
                     "state": f["state"], "path": f["path"], "suggest": label, "category": cat, "confidence": conf, "why": why,
                     "flags": flags, "measure": meas, "history": hist})
        print(f"{rows[-1]['id']:<10} {rows[-1]['shot']:<8} {label or '—':<5} {conf or '':<4} {cat:<24} {why[:90]}", flush=True)
    json.dump(rows, open(os.path.join(out_dir, "prefilter.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(out_dir, "prefilter.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "shot", "gợi ý", "loại lỗi", "độ tin", "lý do", "cờ tầng 0", "QC cũ thấp"])
        for r in rows:
            w.writerow([r["id"], r["shot"], r["suggest"], r["category"], r["confidence"], r["why"],
                        " | ".join(x["text"] for x in r["flags"]), ", ".join(r["history"]["qc_low"])])
    tally = {}
    for r in rows:
        k = (r["suggest"] or "trống", r["confidence"] or "-")
        tally[k] = tally.get(k, 0) + 1
    print(json.dumps({f"{k[0]}/{k[1]}": v for k, v in sorted(tally.items())}, ensure_ascii=False))
    print("ghi:", out_dir)


if __name__ == "__main__":
    main()
