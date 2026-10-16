"""Previs one-shot từ sân khấu 3D (người dùng 16/10 + tài liệu "Quy trình AI Video One-shot Blender"): một cú máy LIỀN MẠCH qua các shot
của một cảnh — người nộm (khối) đi theo lối thật trên lưới sàn K1 (A*, không xuyên hàng rào), máy bám theo nhân vật chính bằng độ lệch
máy↔nhân vật của từng shot đã đo (K4), chuyển mượt sang shot sau; Empty + Track To như tài liệu. Ra: video hình khối (clay) + video
DEPTH (gần trắng, xa đen) làm video tham chiếu cho bước AI Video-to-Video. 0 USD (Blender cục bộ), không ghi CSDL.

    py tools/stage_previs.py --project 31 --scene 2 --out D:/AI-Video-Output/2026-10-15_du-an-31/previs
        [--shots 6-9] [--duration 17.7 | --speed 1.4] [--lens-range 24 35] [--fps 24] [--plan-only]

Thời lượng: mặc định = tổng thời lượng kịch bản các shot (người nộm đi nhanh hơn thật nếu đường dài); --speed m/s = mỗi đoạn ít nhất
quãng đường / tốc độ (cú máy dài hơn bản dựng); --duration = ép tổng.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

CAM_SAMPLE_S = 0.25          # khóa máy mỗi bấy nhiêu giây (nội suy Bezier giữa các khóa)
BLEND_FRAC = 0.4             # phần cuối mỗi đoạn máy chuyển sang độ lệch của shot sau
MOVE_FRAC = 0.6              # máy chạy trong shot (tiến / lùi): đi hết trong phần đầu này của shot
DEPTH_FAR_M = 20.0           # tài liệu: From Max 15–20 m
RUN_MIN_M = 2.0              # đoạn đi dài hơn bấy nhiêu = chạy (chế độ uniform_run; máy xoay theo hướng chạy)
FOCUS_Z_M = 1.2              # điểm nhìn khi nhân vật chạy: ngực (≈ 0,7 × 1,7 m)
TURN_FRAC = 0.2              # phần cuối đoạn di chuyển: người nộm xoay dần về hướng đứng của shot sau
HEDGE_CLEAR_M = 0.4          # máy rơi vào ô hàng rào → cao hơn ngọn rào bấy nhiêu


def _secs(v, default=3.0) -> float:
    m = re.search(r"[\d.]+", str(v or ""))
    return float(m.group(0)) if m else default


def _smooth(u: float) -> float:
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def _lerp(a, b, u):
    return [x + (y - x) * u for x, y in zip(a, b)]


def _polyline_at(pts, d):
    """Điểm cách đầu đường `d` mét dọc polyline + hướng đi (độ từ Bắc)."""
    for a, b in zip(pts, pts[1:]):
        seg = math.dist(a, b)
        if d <= seg or b is pts[-1]:
            u = 0.0 if seg < 1e-9 else min(d / seg, 1.0)
            heading = math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) if seg > 1e-9 else None
            return [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u], heading
        d -= seg
    return list(pts[-1]), None


def _unwrap(prev, f):
    if prev is None or f is None:
        return f
    while f - prev > 180:
        f -= 360
    while f - prev < -180:
        f += 360
    return f


def plan(rd: str, shots=None, duration=None, speed=None, fps=24, res=(720, 1280), lens_range=None, depth_far=DEPTH_FAR_M,
         uniform_run=False, orbit=0.0):
    """Kế hoạch previs (thuần, 0 USD) từ thư mục lượt K4 `rd`: {"previs": cấu hình Blender, "summary": số liệu cho người đọc}."""
    import stage_grid as sgt
    from core import stage_solver as ss
    load = lambda fn: json.load(open(os.path.join(rd, fn), encoding="utf-8"))
    v2, answer, inputs = load("v2.json"), load("answer.json"), load("inputs.json")
    cells = load("grid.json").get("cells") or []
    walk = sgt.walk_grid(cells)
    floor = {(math.floor(c["x"]), math.floor(c["y"])): float(c.get("floor_z") or 0.0) for c in cells}
    fz = lambda p: floor.get((math.floor(p[0]), math.floor(p[1])), 0.0)
    info = {s["shot"]: s for s in inputs.get("shots") or []}
    vs = [s for s in sorted(v2.get("shots") or [], key=lambda x: x["shot"]) if (shots is None or s["shot"] in shots)
          and (s.get("best") or {}).get("m")]
    if not vs:
        raise ValueError("không có shot nào có máy đo được trong lượt này")
    bl = answer["blocking"]
    people = sorted({k for s in vs for k, o in s["objs"].items() if o.get("kind") == "nguoi"})
    # đường đi từng người trong từng shot: đầu shot → (den) → chỗ đầu shot sau
    legs = {k: [] for k in people}
    for i, s in enumerate(vs):
        raw = ss.beat_raw(bl, s["spec"].get("nhip")) if s["spec"].get("nhip") else ss.beat_raw(bl)
        nxt = vs[i + 1]["objs"] if i + 1 < len(vs) else {}
        for k in people:
            o = s["objs"].get(k)
            if not o:
                legs[k].append(None)
                continue
            way = [list(o["xy"])]
            if (raw.get(k) or {}).get("den"):
                way.append(list(raw[k]["den"][:2]))
            if k in nxt and math.dist(nxt[k]["xy"], way[-1]) > 0.05:
                way.append(list(nxt[k]["xy"]))
            pts, ok = [way[0]], True
            for a, b in zip(way, way[1:]):
                p = sgt.walk_path(walk, a, b) if walk else None
                ok = ok and p is not None
                pts += (p or [a, b])[1:]
            legs[k].append({"pts": pts, "len": sum(math.dist(a, b) for a, b in zip(pts, pts[1:])), "routed": ok,
                            "facing": o.get("facing"), "prop": o.get("prop"), "end_facing": (nxt.get(k) or {}).get("facing")})
    base = [_secs(info.get(s["shot"], {}).get("do_dai")) for s in vs]
    lens_ = [max([(legs[k][i] or {}).get("len", 0.0) for k in people] + [0.0]) for i in range(len(vs))]
    run_v = None
    if speed:
        T = [max(b, L / speed) for b, L in zip(base, lens_)]
    elif uniform_run:
        # người dùng 16/10: thế giới song song buff tốc độ ×1,3–1,5 + Kelly nội tại chạy nhanh → CHẠY ĐỀU một tốc độ trên các đoạn
        # đường dài (> RUN_MIN_M), giữ tổng thời lượng kịch bản; đoạn ngắn (bước lại gần, chạm) giữ nhịp kịch bản
        moving = [i for i, L in enumerate(lens_) if L > RUN_MIN_M]
        left = sum(base) - sum(b for i, b in enumerate(base) if i not in moving)
        run_v = sum(lens_[i] for i in moving) / left if moving and left > 0 else None
        T = [lens_[i] / run_v if run_v and i in moving else b for i, b in enumerate(base)]
    else:
        T = list(base)
    if duration:
        T = [t * duration / sum(T) for t in T]
    T = [max(t, 1.0 / fps) for t in T]                  # rà 16/10: thời lượng 0 → chia cho 0
    starts = [sum(T[:i]) for i in range(len(vs))]
    total = sum(T)
    # người nộm: khóa [t, x, y, z sàn, facing] mỗi ~0,25 s dọc đường; biến thể (tư thế) theo shot — vắng ở shot nào thì biến thể ĐÓNG
    # (rà 16/10: trước đây người nộm vẫn hiện / trượt xuyên tường qua chỗ hở), z0 = sàn ở đầu biến thể (Blender cộng chênh sàn vào
    # chỗ đặt đo bằng tia — không bật người trong giếng lên mặt sàn)
    out_people = []
    for k in people:
        keys, variants, prev_f = [], [], None
        for i, leg in enumerate(legs[k]):
            if leg is None:
                if variants and variants[-1]["to"] > starts[i]:
                    variants[-1]["to"] = round(starts[i], 3)
                continue
            n = max(2, int(T[i] / CAM_SAMPLE_S) + 1)
            moving = leg["len"] >= 0.05
            for j in range(n):
                u = j / (n - 1)
                p, h = _polyline_at(leg["pts"], leg["len"] * _smooth(u))
                if not moving or h is None:
                    h = leg["facing"] if u < 0.5 or leg["end_facing"] is None else leg["end_facing"]
                elif leg["end_facing"] is not None and u > 1 - TURN_FRAC:   # rà 16/10: xoay dần về hướng đứng của shot sau
                    h0 = _unwrap(h, leg["end_facing"])
                    h = h + (h0 - h) * _smooth((u - (1 - TURN_FRAC)) / TURN_FRAC)
                h = _unwrap(prev_f, h if h is not None else 0.0)
                prev_f = h
                keys.append([round(starts[i] + u * T[i], 3), round(p[0], 3), round(p[1], 3), round(fz(p), 3), round(h, 2)])
            if variants and variants[-1]["name"] == leg["prop"] and abs(variants[-1]["to"] - starts[i]) < 1e-6:
                variants[-1]["to"] = round(starts[i] + T[i], 3)
            else:
                variants.append({"name": leg["prop"], "at": leg["pts"][0], "facing": leg["facing"], "z0": round(fz(leg["pts"][0]), 3),
                                 "from": round(starts[i], 3), "to": round(starts[i] + T[i], 3)})
        if variants:
            if abs(variants[-1]["to"] - total) < 1e-6:
                variants[-1]["to"] = round(total + 1.0, 3)
            out_people.append({"key": k, "variants": variants, "keys": keys})
    pos = {p["key"]: p["keys"] for p in out_people}

    def _at(k, t, idx):
        ks = pos.get(k) or []
        if not ks:
            return None
        pick = (lambda key: key[idx]) if isinstance(idx, int) else (lambda key: list(key[idx]))
        if t <= ks[0][0]:                                 # rà 16/10: trước khóa đầu → khóa ĐẦU (không phải khóa cuối)
            return pick(ks[0])
        for a, b in zip(ks, ks[1:]):
            if a[0] <= t <= b[0]:
                u = 0.0 if b[0] == a[0] else (t - a[0]) / (b[0] - a[0])
                if isinstance(idx, int):
                    return a[idx] + (b[idx] - a[idx]) * u
                return [x + (y - x) * u for x, y in zip(a[idx], b[idx])]
        return pick(ks[-1])

    where = lambda k, t: _at(k, t, slice(1, 4))
    heading = lambda k, t: _at(k, t, 4) or 0.0

    hedge_top = {}
    for c in cells:
        h = (c.get("top_z") or 0.0) - (c.get("floor_z") or 0.0)
        if c.get("obstacle") or (c.get("covered") and h < sgt.LOW_COVER_M and c.get("top_group") in sgt.HEDGE_GROUPS):
            hedge_top[(math.floor(c["x"]), math.floor(c["y"]))] = float(c.get("top_z") or 0.0)

    # máy: mỗi shot một "giàn" neo vào nhân vật chính CỦA SHOT ĐÓ — độ lệch máy↔nhân vật (đầu shot; cuối shot khi máy chạy, so với chỗ
    # nhân vật lúc máy chạy xong), cùng mặt sàn với nhân vật; nhân vật chạy thì độ lệch xoay theo hướng chạy (+ `orbit`). Ở ranh giới trộn
    # VỊ TRÍ TUYỆT ĐỐI của giàn shot này với giàn shot sau (rà 16/10: trộn độ lệch rồi cộng vào nhân vật shot này → giật khi đổi nhân vật)
    rigs = []
    for i, s in enumerate(vs):
        b = s["best"]
        mains = [c["vat"] for c in s["spec"].get("thanh_phan") or [] if c.get("vai") == "chinh" and c["vat"] in s["objs"]
                 and c["vat"] in people]
        subj = (mains or [k for k in people if k in s["objs"]] or [None])[0]

        def off(m, t_ref, subj=subj):
            sp_ = where(subj, t_ref) if subj else None
            ref = sp_ if sp_ else [0.0, 0.0, 0.0]
            return [a - r for a, r in zip(m["at"], ref)], [a - r for a, r in zip(m["aim"], ref)], float(m["lens"])
        st_ = off(b["m"], starts[i])
        en_ = off(b["end"]["m"], starts[i] + T[i] * MOVE_FRAC) if b.get("end") and (b["end"].get("m") or {}).get("at") else st_
        leg = (legs.get(subj) or [None] * len(vs))[i] if subj else None
        rigs.append({"subj": subj, "start": st_, "end": en_, "run": bool(leg and leg["len"] > RUN_MIN_M)})
    runs = [i for i, r in enumerate(rigs) if r["run"]]

    def rig_at(i, t):
        """(máy, điểm nhìn, ống) tuyệt đối của giàn shot i tại thời điểm t (t có thể trước đầu shot — lúc trộn)."""
        r = rigs[i]
        u = min(max((t - starts[i]) / T[i], 0.0), 1.0)
        w = _smooth(u / MOVE_FRAC)
        c_off, a_off = _lerp(r["start"][0], r["end"][0], w), _lerp(r["start"][1], r["end"][1], w)
        lens = r["start"][2] + (r["end"][2] - r["start"][2]) * w
        if r["run"]:
            spin = (orbit or 0.0) * _smooth(u) * (1 if runs.index(i) % 2 == 0 else -1)
            d = math.radians(heading(r["subj"], max(t, starts[i])) - heading(r["subj"], starts[i]) + spin)
            rot = lambda v: [v[0] * math.cos(d) + v[1] * math.sin(d), -v[0] * math.sin(d) + v[1] * math.cos(d), v[2]]
            # người dùng 16/10 "miễn là máy vẫn focus theo Kelly": khi chạy, điểm nhìn KHÓA vào ngực nhân vật (bản nháp: điểm nhìn đo của
            # shot 7 nhắm khoảng trống phía trước → xoay theo → Kelly trôi ra khỏi khung)
            c_off, a_off = rot(c_off), [0.0, 0.0, FOCUS_Z_M]
        anchor = where(r["subj"], t) if r["subj"] else [0.0, 0.0, 0.0]
        return [a + o for a, o in zip(anchor, c_off)], [a + o for a, o in zip(anchor, a_off)], lens

    cam = []
    n = max(2, int(total / CAM_SAMPLE_S) + 1)
    lo, hi = (lens_range or (None, None))
    for j in range(n):
        t = total * j / (n - 1)
        i = max(x for x in range(len(vs)) if starts[x] <= t + 1e-9)
        at, aim, lens = rig_at(i, t)
        u = (t - starts[i]) / T[i]
        if i + 1 < len(vs) and u > 1 - BLEND_FRAC:
            w = _smooth((u - (1 - BLEND_FRAC)) / BLEND_FRAC)
            at2, aim2, lens2 = rig_at(i + 1, t)
            if rigs[i]["subj"] and rigs[i]["subj"] == rigs[i + 1]["subj"]:
                # cùng nhân vật: chuyển theo CUNG TRÒN quanh nhân vật (góc, khoảng cách, độ cao) — nháp 3 (16/10): nội suy thẳng từ máy
                # cao sau lưng (shot 7) sang máy trước mặt (shot 8) đi xuyên ngay trên đầu Kelly
                c = where(rigs[i]["subj"], t)
                pol = lambda p: (math.dist(p[:2], c[:2]), math.atan2(p[0] - c[0], p[1] - c[1]), p[2])
                (r1, a1, z1), (r2, a2, z2) = pol(at), pol(at2)
                da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
                r_, a_, z_ = r1 + (r2 - r1) * w, a1 + da * w, z1 + (z2 - z1) * w
                at = [c[0] + r_ * math.sin(a_), c[1] + r_ * math.cos(a_), z_]
            else:
                at = _lerp(at, at2, w)
            aim, lens = _lerp(aim, aim2, w), lens + (lens2 - lens) * w
        top = hedge_top.get((math.floor(at[0]), math.floor(at[1])))
        if top is not None and at[2] < top + HEDGE_CLEAR_M:  # máy trong ô hàng rào → nâng qua ngọn rào
            at[2] = top + HEDGE_CLEAR_M
        lens = lens if lo is None else min(max(lens, lo), hi)
        cam.append([round(t, 3), [round(v, 3) for v in at], [round(v, 3) for v in aim], round(lens, 2)])
    unrouted = [f"{k} shot {vs[i]['shot']}" for k in people for i, leg in enumerate(legs[k]) if leg and not leg["routed"]]
    summary = {"shots": [s["shot"] for s in vs], "script_s": [round(b, 2) for b in base], "segment_s": [round(t, 2) for t in T],
               "total_s": round(total, 2), "run_m_per_s": None if run_v is None else round(run_v, 2),
               "paths": {k: [None if leg is None else {"m": round(leg["len"], 1), "routed": leg["routed"],
                                                       "m_per_s": round(leg["len"] / T[i], 2)} for i, leg in enumerate(legs[k])]
                         for k in people},
               "lens": [round(r["start"][2], 1) for r in rigs], "orbit_deg": orbit, "orbit_shots": [vs[i]["shot"] for i in runs], "lens_range": lens_range, "subjects": [r["subj"] for r in rigs],
               "unrouted": unrouted}
    return {"previs": {"fps": fps, "res": list(res), "duration": round(total, 3), "people": out_people, "camera": cam,
                       "depth_far": depth_far}, "summary": summary}


def ref_problems(p: Dict) -> List[str]:
    """Luật video tham chiếu ClipAI (core/adapters/clipai.py: ≥ MIN_REFERENCE_VIDEO_S, rộng trong REFERENCE_VIDEO_WIDTH) — kiểm TRƯỚC khi
    render (rà 16/10: một shot ngắn ra video < 3 s mà không ai báo)."""
    from core.adapters import clipai
    out = []
    lo_w, hi_w = clipai.REFERENCE_VIDEO_WIDTH
    if p["previs"]["duration"] < clipai.MIN_REFERENCE_VIDEO_S:
        out.append(f"video {p['previs']['duration']:.1f} s < {clipai.MIN_REFERENCE_VIDEO_S} s tối thiểu của video tham chiếu")
    if not lo_w <= p["previs"]["res"][0] <= hi_w:
        out.append(f"rộng {p['previs']['res'][0]} px ngoài {lo_w}–{hi_w} px của video tham chiếu")
    return out


def encode(frames_dir: str, prefix: str, fps: int, path: str) -> str:
    """Chuỗi PNG → MP4 H.264 yuv420p, SAR 1:1 (luật video tham chiếu ClipAI: rộng 700–4553 px, ≥ 3 s, PAR 1:1)."""
    from core.ffmpeg_studio import find_ffmpeg
    cmd = [find_ffmpeg(), "-y", "-loglevel", "error", "-framerate", str(fps), "-i", os.path.join(frames_dir, f"{prefix}%04d.png"),
           "-vf", "setsar=1,format=yuv420p", "-c:v", "libx264", "-crf", "18", "-movflags", "+faststart", path]
    subprocess.run(cmd, check=True)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(prog="stage_previs.py")
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--scene", required=True, help="cảnh truyện (story_scene)")
    ap.add_argument("--shots", help="vd 6-9 (mặc định mọi shot có máy của cảnh)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--duration", type=float)
    ap.add_argument("--speed", type=float, help="m/s tối thiểu cho mỗi đoạn (cú máy có thể dài hơn kịch bản)")
    ap.add_argument("--uniform-run", action="store_true", help="chạy đều trên đoạn đường dài, giữ tổng thời lượng kịch bản")
    ap.add_argument("--orbit", type=float, default=0.0, help="độ máy vòng quanh nhân vật trong mỗi đoạn chạy (vd 160: sau lưng → trước mặt)")
    ap.add_argument("--lens-range", type=float, nargs=2, metavar=("MIN", "MAX"), help="kẹp tiêu cự (tài liệu: 24–35 mm)")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--allow-straight", action="store_true", help="cho người nộm đi thẳng khi không tìm được lối (mặc định: dừng)")
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))
    ap.add_argument("--data-dir", default=os.environ.get("PIPELINE_DATA", os.path.join("data", "projects")))
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from core import stage_auto
    from core.db import connect
    import stage_grid as sgt
    conn = connect(os.path.abspath(a.db))
    seg = next((g for g in stage_auto.segments(conn, a.project) if g["scene"] == a.scene), None)
    if seg is None:
        sys.exit(f"không có cảnh {a.scene}")
    rd = stage_auto.result_round(a.data_dir, a.project, seg)
    if rd is None:
        sys.exit(f"cảnh {a.scene}: chưa có lượt sân khấu đã lưu")
    shots = None
    if a.shots:
        lo_, _, hi_ = a.shots.partition("-")
        shots = set(range(int(lo_), int(hi_ or lo_) + 1))
    p = plan(rd, shots, a.duration, a.speed, a.fps, lens_range=a.lens_range, uniform_run=a.uniform_run, orbit=a.orbit)
    problems = ref_problems(p)
    if p["summary"]["unrouted"] and not a.allow_straight:
        problems.append("không tìm được lối trên lưới sàn (người nộm sẽ đi thẳng xuyên vật): " + ", ".join(p["summary"]["unrouted"])
                        + " — sửa chỗ đứng hoặc thêm --allow-straight")
    if problems:
        print(json.dumps(p["summary"], ensure_ascii=False, indent=1))
        sys.exit("DỪNG — " + "; ".join(problems))
    os.makedirs(a.out, exist_ok=True)
    name = f"previs_canh{a.scene}" + (f"_shot{a.shots}" if a.shots else "") + (f"_xoay{a.orbit:g}" if a.orbit else "")
    with open(os.path.join(a.out, name + "_plan.json"), "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=1)
    print(json.dumps(p["summary"], ensure_ascii=False, indent=1))
    if a.plan_only:
        return
    with open(os.path.join(rd, "cfg.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    work = os.path.join(a.out, name + "_blender")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)                     # 16/10: tệp còn khóa (Blender bản Store của lượt bị dừng) → không sập
    cfg = dict(cfg, out_dir=work, cameras=[], v2=None, skip_grid=True, previs=p["previs"])
    sgt.run_blender_safe(cfg, work, timeout=3600)
    clay = encode(os.path.join(work, "frames"), "f_", a.fps, os.path.join(a.out, name + "_clay.mp4"))
    print("clay:", clay)
    if os.path.isdir(os.path.join(work, "frames_depth")) and os.listdir(os.path.join(work, "frames_depth")):
        print("depth:", encode(os.path.join(work, "frames_depth"), "d_", a.fps, os.path.join(a.out, name + "_depth.mp4")))


if __name__ == "__main__":
    main()
