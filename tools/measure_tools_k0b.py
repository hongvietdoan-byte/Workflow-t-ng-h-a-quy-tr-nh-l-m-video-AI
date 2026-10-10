"""K0b — đo công cụ đo K5 trên khung THẬT (0 USD, chạy cục bộ; thẩm định lần 4 lỗ hổng #4).

(a) MediaPipe Pose (Tasks, `data/models/pose_landmarker_full.task`): góc thân trên = góc của véc-tơ hông-giữa → vai-giữa so với phương
    thẳng đứng (0° đứng/ngồi thẳng, 90° nằm ngang, 180° lộn ngược), tính theo pixel (có tỉ lệ khung). So với nhãn người gán bằng mắt
    (`data_out/k0b_tools/labels.json`: {job: {"nhan": "nga" | "thang" | "khong_nguoi", "tu_the": "...", "ghi_chu": "..."}})
    → bảng đúng/sai theo ngưỡng + ngưỡng ít lỗi nhất. Nhãn "nga" = thân ngả / nằm (ngã ngửa, nằm, bò rạp); "thang" = đứng, ngồi thẳng,
    quỳ thẳng.
(b) YuNet (`text_placement.face_boxes`): số mặt mỗi khung (đối chiếu, không kết luận).
(c) Phát hiện vật OpenCV DNN: chỉ thử khi có sẵn trọng số trên máy — KHÔNG tải gì.

Bản chính `--main` (mặc định D:/AI-Video-Pipeline) CHỈ ĐỌC: CSDL mở `mode=ro`, ảnh đọc bằng đường dẫn tuyệt đối; kết quả ghi vào
`data_out/k0b_tools/` của thư mục đang chạy (worktree).

Chạy: PYTHONUTF8=1 py tools/measure_tools_k0b.py [--main D:/AI-Video-Pipeline] [--jobs 635,639,...]
"""
import argparse
import glob
import json
import math
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data_out", "k0b_tools")
LABELS = os.path.join(OUT, "labels.json")
SHOULDERS, HIPS = (11, 12), (23, 24)
MIN_VIS = 0.3


def _xyv(p):
    """(x, y, visibility) từ tuple giả hoặc NormalizedLandmark của MediaPipe."""
    if isinstance(p, (tuple, list)):
        return float(p[0]), float(p[1]), float(p[2])
    return float(p.x), float(p.y), float(getattr(p, "visibility", 1.0) or 0.0)


def torso_angle(landmarks, width, height):
    """Góc thân trên (độ) so với phương thẳng đứng; None khi không có landmark hoặc vai/hông khuất (visibility < MIN_VIS)."""
    if not landmarks or len(landmarks) < 25:
        return None
    pts = [_xyv(landmarks[i]) for i in SHOULDERS + HIPS]
    if min(v for _, _, v in pts) < MIN_VIS:
        return None
    sx = (pts[0][0] + pts[1][0]) / 2 * width
    sy = (pts[0][1] + pts[1][1]) / 2 * height
    hx = (pts[2][0] + pts[3][0]) / 2 * width
    hy = (pts[2][1] + pts[3][1]) / 2 * height
    dx, up = sx - hx, hy - sy                       # up > 0: vai nằm trên hông (trục y ảnh hướng xuống)
    if dx == 0 and up == 0:
        return None
    return math.degrees(math.atan2(abs(dx), up))


def torso_angle_3d(world, min_vis=MIN_VIS):
    """Góc thân trên (độ) từ pose_world_landmarks (mét, gốc ở hông, trục y hướng XUỐNG): tính cả độ ngả theo chiều sâu (về phía /
    ra xa máy) mà góc 2D bị nén. None khi thiếu / khuất. world: 33 điểm (x, y, z, visibility) hoặc Landmark của MediaPipe."""
    if not world or len(world) < 25:
        return None
    def g(p):
        if isinstance(p, (tuple, list)):
            return float(p[0]), float(p[1]), float(p[2]), float(p[3])
        return float(p.x), float(p.y), float(p.z), float(getattr(p, "visibility", 1.0) or 0.0)
    pts = [g(world[i]) for i in SHOULDERS + HIPS]
    if min(p[3] for p in pts) < min_vis:
        return None
    s = [(pts[0][k] + pts[1][k]) / 2 for k in range(3)]
    h = [(pts[2][k] + pts[3][k]) / 2 for k in range(3)]
    dx, up, dz = s[0] - h[0], h[1] - s[1], s[2] - h[2]
    side = math.hypot(dx, dz)
    if side == 0 and up == 0:
        return None
    return math.degrees(math.atan2(side, up))


def classify(angle, threshold):
    if angle is None:
        return "khong_do"
    return "nga" if angle >= threshold else "thang"


def score(rows, threshold):
    """rows: [{nhan: nga|thang, goc}] → đếm đúng / sai / báo nhầm (thẳng mà báo ngã) / bỏ sót (ngã mà báo thẳng) / không đo."""
    s = {"nguong": threshold, "do_duoc": 0, "khong_do": 0, "dung": 0, "sai": 0, "bao_nham": 0, "bo_sot": 0}
    for r in rows:
        got = classify(r["goc"], threshold)
        if got == "khong_do":
            s["khong_do"] += 1
            continue
        s["do_duoc"] += 1
        if got == r["nhan"]:
            s["dung"] += 1
        else:
            s["sai"] += 1
            s["bao_nham" if got == "nga" else "bo_sot"] += 1
    return s


def best_threshold(rows, candidates):
    """Ngưỡng ít lỗi nhất; hòa → ngưỡng lớn hơn (ít báo nhầm hơn)."""
    best = None
    for t in candidates:
        s = score(rows, t)
        if best is None or s["sai"] < best["sai"] or (s["sai"] == best["sai"] and s["bao_nham"] <= best["bao_nham"]):
            best = s
    return best


# --------------------------------------------------------------------------- phần chạy thật (cần mediapipe / cv2 / ảnh)

def _pose_detector(main):
    import mediapipe as mp  # noqa: F401
    from mediapipe.tasks.python import BaseOptions, vision
    model = os.path.join(main, "data", "models", "pose_landmarker_full.task")
    if not os.path.isfile(model):
        return None, f"thiếu {model}"
    det = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model), running_mode=vision.RunningMode.IMAGE, num_poses=2,
        min_pose_detection_confidence=0.3, min_pose_presence_confidence=0.3))
    return det, model


def _measure_pose(det, path):
    import cv2
    import mediapipe as mp
    import numpy as np
    img = cv2.imread(path)
    if img is None:
        return None, []
    h, w = img.shape[:2]
    rgb = np.ascontiguousarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    res = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    found = res.pose_landmarks or []
    worlds = res.pose_world_landmarks or []
    people = []
    for k, lm in enumerate(found):
        xs = [p.x for p in lm]
        ys = [p.y for p in lm]
        people.append({"goc": None if torso_angle(lm, w, h) is None else round(torso_angle(lm, w, h), 1),
                       "goc_3d": (lambda v: None if v is None else round(v, 1))(
                           torso_angle_3d(worlds[k]) if k < len(worlds) else None),
                       "vis_than": round(min(_xyv(lm[i])[2] for i in SHOULDERS + HIPS), 2),
                       "hop": [round(min(xs), 3), round(min(ys), 3), round(max(xs), 3), round(max(ys), 3)]})
    return (w, h), people


def _object_weights(main):
    pats = ("*.caffemodel", "*.pb", "*.weights", "*.onnx", "*.tflite", "*.pt")
    found = []
    for base in {main, ROOT}:
        for pat in pats:
            found += glob.glob(os.path.join(base, "data", "models", pat))
            found += glob.glob(os.path.join(base, "models", pat))
    known_not_object = ("face_detection_yunet", "yamnet")       # mặt / âm thanh — không phải bộ phát hiện vật
    return sorted({f for f in found if not any(k in os.path.basename(f) for k in known_not_object)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", default="D:/AI-Video-Pipeline")
    ap.add_argument("--jobs", default="")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    labels = {}
    if os.path.isfile(LABELS):
        with open(LABELS, encoding="utf-8") as f:
            labels = json.load(f)
    jobs = [int(x) for x in a.jobs.split(",") if x.strip()] or sorted(int(k) for k in labels if k.isdigit())
    if not jobs:
        print("không có job: truyền --jobs hoặc điền", LABELS)
        return 2
    conn = sqlite3.connect(f"file:{a.main}/data/manifest.sqlite?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    sys.path.insert(0, ROOT)
    from core import text_placement
    yunet = os.path.join(a.main, "data", "models", "face_detection_yunet_2023mar.onnx")
    det, pose_note = _pose_detector(a.main)
    frames, rows, rows3, sit2, sit3 = [], [], [], [], []
    for jid in jobs:
        r = conn.execute("SELECT j.id, j.project_id, s.idx, j.result_path FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.id=?",
                         (jid,)).fetchone()
        if r is None or not r["result_path"]:
            frames.append({"job": jid, "loi": "không có job / ảnh"})
            continue
        path = os.path.join(a.main, r["result_path"].replace("\\", "/"))
        size, people = _measure_pose(det, path) if det else (None, [])
        faces = text_placement.face_boxes(path, yunet)
        lab = labels.get(str(jid), {})
        main_goc = main_3d = None
        if people:                                   # người chính = hộp lớn nhất
            big = max(people, key=lambda p: (p["hop"][2] - p["hop"][0]) * (p["hop"][3] - p["hop"][1]))
            main_goc, main_3d = big["goc"], big["goc_3d"]
        fr = {"job": jid, "du_an": r["project_id"], "shot": r["idx"], "anh": path, "co": size, "so_nguoi_pose": len(people),
              "nguoi": people, "goc_chinh": main_goc, "goc_3d_chinh": main_3d, "so_mat_yunet": None if faces is None else len(faces),
              "nhan": lab.get("nhan"), "tu_the_that": lab.get("tu_the"), "ghi_chu": lab.get("ghi_chu")}
        frames.append(fr)
        if lab.get("nhan") in ("nga", "thang"):
            rows.append({"job": jid, "nhan": lab["nhan"], "goc": main_goc})
            rows3.append({"job": jid, "nhan": lab["nhan"], "goc": main_3d})
            if lab.get("tu_the") in ("nga_ngua", "ngoi"):        # câu hỏi thật của #24: ngã ngửa vs ngồi
                sit2.append({"job": jid, "nhan": "nga" if lab["tu_the"] == "nga_ngua" else "thang", "goc": main_goc})
                sit3.append({"job": jid, "nhan": "nga" if lab["tu_the"] == "nga_ngua" else "thang", "goc": main_3d})
    people_frames = [f for f in frames if f.get("nhan") in ("nga", "thang")]
    report = {
        "pose_model": pose_note,
        "so_khung": len(frames),
        "so_khung_co_nguoi_gan_nhan": len(people_frames),
        "pose_nhan_ra_nguoi": sum(1 for f in people_frames if f["so_nguoi_pose"] > 0),
        "pose_do_duoc_goc": sum(1 for r in rows if r["goc"] is not None),
        "nguong": [score(rows, t) for t in range(15, 80, 5)],
        "nguong_tot_nhat": best_threshold(rows, range(15, 80, 5)) if rows else None,
        "nguong_3d": [score(rows3, t) for t in range(15, 80, 5)],
        "nguong_tot_nhat_3d": best_threshold(rows3, range(15, 80, 5)) if rows3 else None,
        "nga_ngua_vs_ngoi": {"mau": sit2, "tot_nhat_2d": best_threshold(sit2, range(10, 60, 2)) if sit2 else None,
                             "mau_3d": sit3, "tot_nhat_3d": best_threshold(sit3, range(10, 60, 2)) if sit3 else None},
        "yunet_khung_co_mat": sum(1 for f in frames if f.get("so_mat_yunet")),
        "phat_hien_vat": (lambda w: {"trong_so": w, "ket_qua": "chưa thử: thiếu trọng số bộ phát hiện vật trên máy (không tải theo đề "
                                     "bài) — cần người dùng duyệt tải (tên, nguồn, cỡ)" if not w else "có trọng số — chưa viết bộ đọc"})(
            _object_weights(a.main)),
        "khung": frames,
    }
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print(f"khung {report['so_khung']} · gán nhãn có người {report['so_khung_co_nguoi_gan_nhan']} · Pose nhận người "
          f"{report['pose_nhan_ra_nguoi']} · đo được góc {report['pose_do_duoc_goc']}")
    print("ngưỡng tốt nhất 2D:", report["nguong_tot_nhat"])
    print("ngưỡng tốt nhất 3D:", report["nguong_tot_nhat_3d"])
    print("ngã ngửa vs ngồi:", report["nga_ngua_vs_ngoi"]["tot_nhat_2d"], report["nga_ngua_vs_ngoi"]["tot_nhat_3d"])
    for f in frames:
        print(f.get("job"), f.get("shot"), f.get("nhan"), f.get("tu_the_that"), f.get("goc_chinh"), f.get("goc_3d_chinh"),
              "mặt", f.get("so_mat_yunet"))
    print("phát hiện vật:", report["phat_hien_vat"]["ket_qua"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
