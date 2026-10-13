"""#27 shot 2 — chữ tên 2 cổng trên nóc mỗi cổng, hiện đúng lúc lời dẫn L1 đọc "Một, thế giới thực tại" / "Hai, thế giới song song"
(người dùng 13/10). 0 USD: bám nóc cổng bằng optical flow (điểm đặc trưng nửa trên khung — không dính tay POV; ước lượng tỉ lệ + dịch
vì máy tiến/ngóc), rồi ghi chữ vào clip. So pha (phaseCorrelate) đã thử: trôi vì cổng phóng to — đừng dùng lại.

    PYTHONUTF8=1 py tools/experiments/p27_gate_labels.py --src clips_cuoi/02_goc.mp4 --out clips_cuoi/02.mp4

Mốc mặc định: L1 giọng 30169 (tts_1827) — "Một" 7,88 s, "Hai" 9,74 s trong câu; câu bắt đầu ở phim 0,2 s, shot 2 bắt đầu ở phim 2,0 s
→ trong clip shot 2: 6,08 s / 7,94 s (đổi giọng/đổi shot 1 thì đo lại bằng faster-whisper word_timestamps).
Neo nóc cổng đo trên khung 6,08 s của 02_goc.mp4: trái (288, 235), phải (907, 235).
"""
import argparse
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def track(frames, r0, anchors):
    """Ma trận tích lũy (tỉ lệ + xoay + dịch) từ khung r0 tới từng khung sau; trả [n_anchor, n, (x, y, scale)]."""
    H = frames[0].shape[0]
    mask = np.zeros(frames[0].shape[:2], np.uint8)
    mask[0:int(H * 0.42)] = 255                       # cổng + trời; tay POV ở nửa dưới
    acc = np.eye(3)
    prev = cv2.cvtColor(frames[r0], cv2.COLOR_BGR2GRAY)
    out = [[] for _ in anchors]
    for i in range(r0, len(frames)):
        if i > r0:
            g = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            p0 = cv2.goodFeaturesToTrack(prev, 400, 0.01, 8, mask=mask)
            p1, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, p0, None, winSize=(31, 31), maxLevel=4)
            ok = st.ravel() == 1
            m, _ = cv2.estimateAffinePartial2D(p0[ok], p1[ok], method=cv2.RANSAC, ransacReprojThreshold=2.0)
            acc = np.vstack([m, [0, 0, 1]]) @ acc
            prev = g
        s = float(np.sqrt(abs(np.linalg.det(acc[:2, :2]))))
        for k, (x, y) in enumerate(anchors):
            v = acc @ np.array([x, y, 1.0])
            out[k].append((v[0], v[1], s))
    arr = np.array(out)
    k = 3                                             # làm mượt nhẹ
    for a in range(arr.shape[0]):
        p = np.pad(arr[a], ((k, k), (0, 0)), mode="edge")
        arr[a] = np.array([p[i:i + 2 * k + 1].mean(0) for i in range(arr.shape[1])])
    return arr


def label(text, font):
    tw = int(font.getlength(text)) + 40
    im = Image.new("RGBA", (tw, 76), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20, 14), text, font=font, fill=(255, 255, 255, 255), stroke_width=5, stroke_fill=(60, 10, 30, 255))
    return Image.alpha_composite(im.filter(ImageFilter.GaussianBlur(7)), im)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--t1", type=float, default=6.08)
    ap.add_argument("--t2", type=float, default=7.94)
    ap.add_argument("--left", default="288,235")
    ap.add_argument("--right", default="907,235")
    ap.add_argument("--font", default=r"C:\Windows\Fonts\arialbd.ttf")
    args = ap.parse_args()
    cap = cv2.VideoCapture(args.src)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    H, W = frames[0].shape[:2]
    r0 = int(round(args.t1 * fps))
    anchors = [tuple(map(float, args.left.split(","))), tuple(map(float, args.right.split(",")))]
    tr = track(frames, r0, anchors)
    font = ImageFont.truetype(args.font, 38)
    labs = [(label("1. THẾ GIỚI THỰC TẠI", font), 0, args.t1), (label("2. THẾ GIỚI SONG SONG", font), 1, args.t2)]
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps),
                             "-i", "-", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", args.out], stdin=subprocess.PIPE)
    for i, f in enumerate(frames):
        t = i / fps
        im = Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)).convert("RGBA")
        for lab, gi, t0 in labs:
            if t >= t0 and i >= r0:
                x, y, s = tr[gi][i - r0]
                a = min(1.0, (t - t0) / 0.25)             # hiện dần 0,25 s + thu từ 1,2× về 1×
                z = s * (1 + 0.2 * (1 - a))
                lab_ = lab.resize((int(lab.width * z), int(lab.height * z)), Image.LANCZOS)
                lab_.putalpha(lab_.getchannel("A").point(lambda v, a=a: int(v * a)))
                x = min(max(x, lab_.width / 2 + 8), W - lab_.width / 2 - 8)
                im.alpha_composite(lab_, (int(x - lab_.width / 2), int(y - lab_.height / 2)))
        proc.stdin.write(cv2.cvtColor(np.asarray(im.convert("RGB")), cv2.COLOR_RGB2BGR).tobytes())
    proc.stdin.close()
    proc.wait()


if __name__ == "__main__":
    main()
