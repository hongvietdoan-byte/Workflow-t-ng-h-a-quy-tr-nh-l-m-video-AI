"""Chuyen dong may tung shot bang OpenCV: goodFeaturesToTrack + calcOpticalFlowPyrLK + estimateAffinePartial2D.
Che dai duoi khung (phu de) truoc khi tinh feature. Lay mau cap khung cach ~0.2s trong moi shot, gop trung vi ca shot.
Output moi shot: {i, n_pairs, tx, ty, scale, rot_deg, mag_px (theo % chieu rong khung), class, note}
"""
import sys, json, cv2, numpy as np

def analyze(path, shots, sub_crop=0.78, step_sec=0.2, max_pairs=12):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    mask_h = int(H * sub_crop)  # chi dung phan tren (bo dai duoi co phu de)
    out = []
    for s in shots:
        t0, t1 = s["start"], s["end"]
        dur = t1 - t0
        n = min(max_pairs, max(1, int(dur / step_sec)))
        times = [t0 + (dur * k / (n + 1)) for k in range(1, n + 1)]
        frames = []
        for t in times:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, fr = cap.read()
            if ok:
                gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)[:mask_h, :]
                frames.append(gray)
        txs, tys, scales, rots, ninliers = [], [], [], [], []
        for a, b in zip(frames, frames[1:]):
            p0 = cv2.goodFeaturesToTrack(a, maxCorners=200, qualityLevel=0.01, minDistance=8)
            if p0 is None or len(p0) < 10:
                continue
            p1, st, err = cv2.calcOpticalFlowPyrLK(a, b, p0, None, winSize=(21, 21), maxLevel=3)
            if p1 is None:
                continue
            st = st.reshape(-1).astype(bool)
            good0, good1 = p0[st], p1[st]
            if len(good0) < 8:
                continue
            M, inliers = cv2.estimateAffinePartial2D(good0, good1, method=cv2.RANSAC,
                                                       ransacReprojThreshold=3.0)
            if M is None:
                continue
            a_, b_, tx, ty = M[0, 0], M[1, 0], M[0, 2], M[1, 2]
            scale = float(np.hypot(a_, b_))
            rot = float(np.degrees(np.arctan2(b_, a_)))
            txs.append(float(tx)); tys.append(float(ty)); scales.append(scale); rots.append(rot)
            ninliers.append(int(inliers.sum()) if inliers is not None else 0)
        if not txs:
            out.append({"i": s["i"], "n_pairs": 0, "class": "khong_du_du_lieu", "note": "khong track duoc dac trung (qua toi/qua mo/qua ngan)"})
            continue
        mtx, mty = float(np.median(txs)), float(np.median(tys))
        mscale, mrot = float(np.median(scales)), float(np.median(rots))
        mag_pct_w = 100.0 * np.hypot(mtx, mty) / W  # % chieu rong khung / cap khung (~0.2s)
        scale_dev = abs(mscale - 1.0)
        cls, note = classify(mag_pct_w, scale_dev, mrot, mscale)
        out.append({"i": s["i"], "n_pairs": len(txs), "tx": round(mtx, 2), "ty": round(mty, 2),
                     "scale": round(mscale, 4), "rot_deg": round(mrot, 2),
                     "mag_pct_w_per_pair": round(mag_pct_w, 3), "class": cls, "note": note})
    cap.release()
    return out

def classify(mag_pct_w, scale_dev, rot_deg, mscale=1.0):
    # nguong da hieu chinh sau khi doi chieu voi anh mid-frame video 04 (nguong cu 0.15%/0.004/0.3do qua nhay,
    # goi hau het shot tinh thanh "co chuyen dong" do nhieu track nho); nguong moi khop ty le ~76% tinh / 22%
    # tinh tien / <2% xoay, gan voi 98% tinh cua DRAMA_DOC tham khao.
    mag_thr, scale_thr, rot_thr = 1.0, 0.01, 0.5
    if mag_pct_w < mag_thr and scale_dev < scale_thr and abs(rot_deg) < rot_thr:
        return "static", "gan tinh (duoi nguong ca 3 truc)"
    dom = max([("translate", mag_pct_w / mag_thr), ("scale", scale_dev / scale_thr), ("rot", abs(rot_deg) / rot_thr)],
              key=lambda x: x[1])[0]
    if dom == "translate":
        return "pan_hoac_truck_hoac_tilt_hoac_pedestal", f"tinh tien noi bat (mag={mag_pct_w:.2f}%/cap) — khong tach duoc pan/truck hay tilt/pedestal neu khong co thi sai ro"
    if dom == "scale":
        direction = "zoom_in_hoac_dolly_in" if mscale > 1 else "zoom_out_hoac_dolly_out"
        return direction, f"doi ty le noi bat (scale_dev={scale_dev:.4f}) — khong tach duoc zoom/dolly neu khong co parallax ro"
    return "roll", f"xoay truc ong kinh noi bat (rot={rot_deg:.2f} do/cap)"

if __name__ == "__main__":
    path, result_json = sys.argv[1], sys.argv[2]
    d = json.load(open(result_json, encoding="utf-8"))
    m = analyze(path, d["shots"])
    d["motion_cv2"] = m
    json.dump(d, open(result_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(json.dumps(dict(Counter(x["class"] for x in m)), ensure_ascii=False))
