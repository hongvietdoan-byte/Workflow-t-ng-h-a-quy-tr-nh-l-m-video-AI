"""S0.12 v2: phan tich 1 doan video da tai (ffmpeg/ffprobe). In JSON ra stdout.
Usage: py analyze.py <video.mp4/webm> <out_prefix> [scene_thr=0.25]
"""
import sys, subprocess, json, re, os, statistics

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"

def probe(path):
    out = subprocess.run([FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
                          capture_output=True, text=True).stdout
    d = json.loads(out)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    dur = float(d["format"].get("duration") or v.get("duration") or 0)
    return {"duration": dur, "width": v["width"], "height": v["height"],
            "fps": eval(v.get("r_frame_rate", "25/1")), "has_audio": a is not None}

PTS_RE = re.compile(r"pts_time:(\d+(?:\.\d+)?)")

def cuts(path, thr):
    proc = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", path, "-an",
                            "-vf", f"scale=192:-2,select='gt(scene,{thr})',showinfo", "-f", "null", "-"],
                           capture_output=True, text=True)
    return sorted(float(m.group(1)) for m in PTS_RE.finditer(proc.stderr or ""))

def shots_from_cuts(cs, dur, min_shot=0.3):
    b = [0.0]
    for c in sorted(cs):
        if min_shot <= c <= dur - min_shot and c - b[-1] >= min_shot:
            b.append(round(c, 2))
    b.append(round(dur, 2))
    return [{"i": i, "start": a, "end": bb, "dur": round(bb - a, 2)} for i, (a, bb) in enumerate(zip(b, b[1:]), 1)]

def audio_loudness(path):
    """Chay ebur128 metadata=1, doc dong 'M:' (momentary loudness ~ moi 100ms) va gio 't:'."""
    proc = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", path, "-filter_complex",
                            "ebur128=metadata=1:peak=true", "-f", "null", "-"],
                           capture_output=True, text=True)
    err = proc.stderr or ""
    # summary block at the end
    summary = {}
    m = re.search(r"Integrated loudness:\s*\n\s*I:\s*(-?\d+\.?\d*) LUFS.*?\n\s*Threshold:.*?\n\s*Loudness range:\s*\n\s*LRA:\s*(-?\d+\.?\d*) LU.*?Peak:\s*\n(.*?)Peak:\s*(-?\d+\.?\d*) dBFS",
                  err, re.S)
    im = re.search(r"I:\s*(-?\d+\.?\d*) LUFS", err)
    lram = re.search(r"LRA:\s*(-?\d+\.?\d*) LU", err)
    summary["integrated_LUFS"] = float(im.group(1)) if im else None
    summary["LRA_LU"] = float(lram.group(1)) if lram else None
    # KHONG bao dinh (true peak) nua: do tren WebM/Opus tai ve, giai ma nen ton hao co the vuot dinh goc
    # (ghi chu phien chinh) -> khong dung duoc de ket luan. Chi bao LUFS/LRA/quang lang tu nay.
    return summary

def rms_curve(path, window_sec=1.0):
    """RMS (dBFS) moi ~1s qua astats+ametadata (dang chuoi, khong co mốc t chinh xac tu ffmpeg -> tu gan theo thu tu)."""
    n = int(48000 * window_sec)
    proc = subprocess.run([FFMPEG, "-v", "info", "-i", path, "-af",
                            f"asetnsamples=n={n},astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
                            "-f", "null", "-"], capture_output=True, text=True)
    vals = [float(x) for x in re.findall(r"RMS_level=(-?\d+\.?\d*|-inf)", proc.stderr or "") if x != "-inf"]
    return [(round(i * window_sec, 2), v) for i, v in enumerate(vals)]

def silences(path, noise_db=-35, min_dur=0.3):
    proc = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", path, "-af",
                            f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"],
                           capture_output=True, text=True)
    err = proc.stderr or ""
    starts = [float(x) for x in re.findall(r"silence_start:\s*(-?\d+\.?\d*)", err)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*(-?\d+\.?\d*)", err)]
    return list(zip(starts, ends[:len(starts)]))

def mid_frames(path, shots, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    out = []
    for s in shots:
        t = s["start"] + s["dur"] / 2
        dest = os.path.join(out_dir, f"shot_{s['i']:03d}.jpg")
        subprocess.run([FFMPEG, "-y", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1", "-vf", "scale=280:-2",
                         "-q:v", "5", dest], capture_output=True, text=True)
        out.append(dest if os.path.exists(dest) else "")
    return out

FONT = "C\\:/Windows/Fonts/arial.ttf"

def contact_sheet(frames, shots, dest, cols=6, portrait=False):
    cell_w, cell_h = (110, 196) if portrait else (200, 113)
    valid = [(f, s) for f, s in zip(frames, shots) if f]
    n = len(valid)
    if n == 0:
        return None, "no frames"
    inputs = []
    for f, s in valid:
        inputs += ["-i", f]
    fc_parts = []
    for idx, (f, s) in enumerate(valid):
        label = f"#{s['i']} {s['start']:.1f}-{s['end']:.1f}"
        fc_parts.append(
            f"[{idx}:v]scale={cell_w}:{cell_h},drawtext=fontfile='{FONT}':text='{label}':x=2:y=2:fontsize=11:fontcolor=yellow:box=1:boxcolor=black@0.6[v{idx}]")
    if n == 1:
        fc = fc_parts[0].replace("[v0]", "[out]")
    else:
        stack_inputs = "".join(f"[v{idx}]" for idx in range(n))
        xs, ys = [], []
        for idx in range(n):
            r, c = idx // cols, idx % cols
            xs.append(str(c * cell_w)); ys.append(str(r * cell_h))
        layout_str = "|".join(f"{x}_{y}" for x, y in zip(xs, ys))
        fc = ";".join(fc_parts) + f";{stack_inputs}xstack=inputs={n}:layout={layout_str}[out]"
    cmd = [FFMPEG, "-y"] + inputs + ["-filter_complex", fc, "-map", "[out]", dest]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return dest if os.path.exists(dest) else None, proc.stderr[-800:] if proc.returncode != 0 else ""

if __name__ == "__main__":
    path = sys.argv[1]
    prefix = sys.argv[2]
    thr = float(sys.argv[3]) if len(sys.argv) > 3 else 0.25
    meta = probe(path)
    cs = cuts(path, thr)
    shots = shots_from_cuts(cs, meta["duration"])
    frames = mid_frames(path, shots, prefix + "_frames")
    portrait = meta["height"] > meta["width"]
    sheets = []
    per = 30
    for k in range(0, len(shots), per):
        dest = f"{prefix}_sheet_{k//per+1:02d}.jpg"
        cols = 6
        r, err = contact_sheet(frames[k:k+per], shots[k:k+per], dest, cols=cols, portrait=portrait)
        sheets.append(r)
        if err:
            print("SHEET_ERR", err, file=sys.stderr)
    aud_summary = (audio_loudness(path) if meta["has_audio"] else {})
    sil = silences(path) if meta["has_audio"] else []
    curve = rms_curve(path) if meta["has_audio"] else []
    result = {"meta": meta, "cuts": cs, "shots": shots, "sheets": sheets,
              "audio_summary": aud_summary, "silences": sil, "rms_curve": curve}
    with open(prefix + "_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(json.dumps({"n_shots": len(shots), "sheets": sheets, "audio_summary": aud_summary,
                       "n_silences": len(sil), "duration": meta["duration"], "wh": [meta["width"], meta["height"]],
                       "rms_n": len(curve)},
                      ensure_ascii=False, indent=1))
