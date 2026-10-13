"""#27 — dựng video tổng 9:16 có lời dẫn (giọng 72) + nhạc nền, 0 USD.

Chỉ ĐỌC CSDL (data/manifest.sqlite, mode=ro) và tệp có sẵn; không gọi API trả tiền.

Luồng:
  1. Chuẩn hóa từng shot 1..N về <size>, 30 fps, yuv420p (shot thiếu + --allow-missing → khung đen
     + chữ 'thiếu shot N' dài đúng duration_s trong CSDL). Shot có clip dùng độ dài thật của clip.
  2. Nối cứng (concat demuxer, -c copy) → 1 luồng hình dùng chung cho cả 2 bản.
  3. Âm thanh mỗi bản: lời dẫn L1..L9 (đặt đầu shot + 0,2 s, tự dời nếu chồng) + nhạc A (shot 2→hết 11)
     + nhạc B (shot 12→hết phim), nhạc ≈10 dB dưới lời dẫn + sidechaincompress theo bus lời dẫn,
     loudnorm 2 lượt −14 LUFS / TP −1,5 (≤ −1 dBTP), AAC 192k, +faststart.
  4. Ghi mix_moc[_tag].md (bảng mốc giây shot + lời dẫn + cảnh báo) cạnh tệp ra.

Ánh xạ câu ↔ shot (ưu tiên giảm dần):
  --vo-map 2,4,6,...  (ép tay)  >  khớp chữ câu với dialogue LỜI DẪN của scenes trong CSDL
  >  assets.json scene_idx (số shot cũ, cũ ≥ 7 cộng 1)  >  bảng mặc định DEFAULT_VO_SHOTS.

Ví dụ (PowerShell):
  $env:PYTHONUTF8=1
  py tools/experiments/p27_final_mix.py --allow-missing --tag nhap
  py tools/experiments/p27_final_mix.py            # khi đủ 22 clip 1080p
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path


def _find_root() -> Path:
    """Thư mục dự án có data/manifest.sqlite (worktree không có CSDL → về bản checkout chính)."""
    env = os.environ.get("P27_ROOT")
    cands = ([Path(env)] if env else []) + [Path(__file__).resolve().parents[2], Path(r"D:\AI-Video-Pipeline")]
    for c in cands:
        if (c / "data" / "manifest.sqlite").exists():
            return c
    raise SystemExit("Không tìm thấy data/manifest.sqlite (đặt P27_ROOT)")


ROOT = _find_root()
PID = 27
PROJ = ROOT / "data" / "projects" / str(PID)
AUDIO = PROJ / "audio_trial"
DB = ROOT / "data" / "manifest.sqlite"
OUT_DIR_DEFAULT = Path(r"D:\AI-Video-Output\2026-10-13_du-an-27")
FPS = 30
GATES_APPEAR = 2          # shot 2 cổng hiện ra
DARK_OUT = 4               # shot 4 tối dần sang thế giới song song
FLASH = "0xFFE4EE"         # trắng hồng ánh cổng
DEFAULT_VO_SHOTS = [2, 4, 6, 8, 10, 12, 14, 17, 20]  # bảng trong đề bài (số shot mới)
SPLIT_OLD_SHOT = 7  # tách shot 6 → số shot cũ >= 7 cộng 1
VERSIONS = [("ban1_A1B1", "draft_31501.mp3", "draft_31503.mp3"),
            ("ban2_A2B2", "draft_31502.mp3", "draft_31504.mp3")]
FONT = Path(r"C:\Windows\Fonts\arial.ttf")

VO_SHOT_OVERRIDE = {1: 1}  # 13/10 người dùng: L1 ('…đồng đội bị hạ gục…') đọc SỚM cùng shot 1
AMB_SHOTS = (1, 2)         # lớp âm nền ngoài trời (gió + súng xa) cho cảnh đồng đội gục
AMB_WIND_SOUND = 307       # Kho âm thanh (bảng sounds): 'gio rit' 11,4 s — Wind
AMB_GUN_SOUND = 309        # Kho âm thanh: 'gun 1' 1,7 s — Gunshot (làm xa bằng lowpass + echo)
AMB_GUN_AT = (0.7, 1.05, 3.6, 7.9, 8.2, 11.4)  # giây (tính từ đầu shot 1) các loạt súng xa

DARK_OUT_2 = 11            # 13/10: hết nhánh song song (shot 11) — tối dần về đen 0,6 s
DARK_OUT_2_S = 0.6
# SFX (13/10): (shot, giây từ đầu shot | "mid", nguồn, nhóm, lặp [giây cộng thêm]). Nguồn: tên tệp trong audio_trial/sfx
# hoặc "kho:<id>" (bảng sounds). Nhóm → mức (LU so với lời dẫn): mạnh −6, ui −9, foley −10, đệm −14, xa −24.
# Mốc theo bang_am_thanh_ke_hoach.md mục "Hiệu ứng" (số shot đã đổi sang số mới, cũ ≥ 7 cộng 1).
SFX_GROUP_LU = {"manh": -6.0, "ui": -9.0, "foley": -10.0, "dem": -14.0, "xa": -24.0}
SFX_PLAN = [
    (2, 0.9, "sound_effect_1821.mp3", "dem", [0.0]),                  # F3 hai cổng hiện ra — ngân/rít
    (3, 0.3, "sound_effect_31494.mp3", "dem", [0.0]),                 # rền trầm khi qua cổng phải (không có tệp sấm → drone trầm)
    (4, 0.8, "sound_effect_31493.mp3", "dem", [0.0, 2.6]),            # F6 xúc tu đỏ rít lan
    (5, 0.0, "sound_effect_31495.mp3", "dem", [0.0]),                 # F8 hộp nhạc rè (mặt nạ)
    (9, 0.3, "sound_effect_31496.mp3", "foley", [0.0, 1.5, 3.0]),     # F10 vệt đỏ xì dưới chân (3 lần)
    (11, 0.2, "sound_effect_31497.mp3", "foley", [0.0]),              # F13 Kelly quỵ (thịch)
    (11, 0.9, "sound_effect_1822.mp3", "ui", [0.0]),                  # F13 âm thông báo hệ thống lạnh
    (15, 1.5, "sound_effect_31498.mp3", "ui", [0.0]),                 # F16 nhặt SKORP
    (16, 0.1, "sound_effect_31499.mp3", "manh", [0.0]),               # F17 ném bom keo + tường keo dựng
    (17, 0.2, "kho:309", "xa", [0.0, 0.35, 1.0]),                     # F18 súng xa
    (18, 0.3, "kho:310", "xa", [0.0, 1.4, 1.7, 2.9]),                 # F18 súng xa
    (19, 0.2, "sound_effect_31500.mp3", "manh", [0.0, 0.7]),          # F19 đạn găm tường kim loại
    (21, 0.6, "kho:309", "manh", [0.0, 0.14, 0.28, 0.42, 1.6, 1.74, 1.88, 2.02, 2.16]),  # F21 SKORP xả liên tiếp
    (21, 3.2, "sound_effect_31497.mp3", "foley", [0.0]),              # F21 địch gục (thịch)
    (22, 0.0, "sound_effect_1823.mp3", "manh", [0.0]),                # F23 BOOYAH stinger (khớp popup)
]
POPUP_SHOT = 22            # popup chữ BOOYAH (#27 không có icon prop ICON* cho core/end_popup)
POPUP_TEXT = "BOOYAH!"
POPUP_ASSET_IMG = "data/assets/431/1.png"   # 13/10 người dùng: popup = banner BOOYAH đỏ Kho #431 (hình khung booyah), không chữ tự vẽ
SUB_MAX_CHARS = 32         # phụ đề: mỗi dòng ≤ 32 ký tự, ≤ 2 dòng/lần hiện

WARN: list[str] = []


def warn(msg: str) -> None:
    if msg not in WARN:
        WARN.append(msg)
        print("CẢNH BÁO:", msg, flush=True)


def run(cmd: list[str], capture: bool = False) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        sys.stderr.write(p.stderr[-4000:])
        raise SystemExit(f"Lệnh lỗi ({p.returncode}): {' '.join(cmd[:8])} ...")
    return p.stderr if capture else p.stdout


def probe(path: Path) -> dict:
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
               "-of", "json", str(path)])
    j = json.loads(out)
    return {"dur": float(j["format"]["duration"]),
            "audio": any(s.get("codec_type") == "audio" for s in j.get("streams", []))}


def norm_text(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "").lower()
    s = re.sub(r"\[[^\]]*\]", " ", s)
    return re.sub(r"[^\w]+", " ", s).strip()


def load_scenes() -> list[dict]:
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    try:
        rows = con.execute("SELECT idx, data FROM scenes WHERE project_id=? ORDER BY idx", (PID,)).fetchall()
    finally:
        con.close()
    scenes = []
    for idx, data in rows:
        d = json.loads(data or "{}")
        vo = " ".join(x.get("text", "") for x in (d.get("dialogue") or [])
                      if "DẪN" in (x.get("speaker") or "").upper())
        scenes.append({"idx": int(idx), "duration_s": float(d.get("duration_s") or 0), "vo_text": vo})
    return scenes


def load_vo_lines() -> list[dict]:
    files = []
    for line in (AUDIO / "list_72.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*file\s+'(.+)'\s*$", line)
        if m and Path(m.group(1)).name.startswith("tts_"):
            files.append(Path(m.group(1)))
    assets = {}
    aj = AUDIO / "tts_72" / "assets.json"
    if aj.exists():
        for a in json.loads(aj.read_text(encoding="utf-8")):
            assets[a.get("file")] = a
    lines = []
    for i, f in enumerate(files, 1):
        if not f.exists():
            f = AUDIO / "tts_72" / f.name
        a = assets.get(f.name, {})
        lines.append({"n": i, "file": f, "dur": probe(f)["dur"], "text": a.get("text", ""),
                      "asset_scene_old": a.get("scene_idx")})
    return lines


def map_vo(lines: list[dict], scenes: list[dict], forced: list[int] | None) -> str:
    if forced:
        if len(forced) != len(lines):
            raise SystemExit(f"--vo-map cần {len(lines)} số, nhận {len(forced)}")
        for ln, s in zip(lines, forced):
            ln["shot"], ln["src"] = s, "--vo-map"
        return "ép tay --vo-map"
    by_text = {norm_text(s["vo_text"]): s["idx"] for s in scenes if s["vo_text"]}
    srcs = set()
    for ln, dflt in zip(lines, DEFAULT_VO_SHOTS + [None] * len(lines)):
        t = norm_text(ln["text"])
        if t and t in by_text:
            ln["shot"], ln["src"] = by_text[t], "CSDL dialogue"
        elif ln["asset_scene_old"]:
            o = int(ln["asset_scene_old"])
            ln["shot"], ln["src"] = (o + 1 if o >= SPLIT_OLD_SHOT else o), "assets.json(+1 sau tách)"
        else:
            ln["shot"], ln["src"] = dflt, "bảng mặc định"
        srcs.add(ln["src"])
        if dflt and ln["shot"] != dflt:
            warn(f"L{ln['n']}: đặt ở shot {ln['shot']} theo {ln['src']} (bảng đề bài ghi shot {dflt})")
    for n, shot in VO_SHOT_OVERRIDE.items():
        for ln in lines:
            if ln["n"] == n and ln["shot"] != shot:
                warn(f"L{n}: dời từ shot {ln['shot']} → shot {shot} (người dùng 13/10: đọc sớm cùng shot {shot})")
                ln["shot"], ln["src"] = shot, "người dùng 13/10"
                srcs.add(ln["src"])
    return ", ".join(sorted(srcs))


def ff_path(p: Path) -> str:
    """Đường dẫn dùng trong filtergraph (escape ':')."""
    return p.as_posix().replace(":", r"\:")


def build_segments(args, scenes, tmp: Path) -> list[dict]:
    W, H = map(int, args.size.lower().split("x"))
    common = ["-c:v", "libx264", "-preset", args.preset, "-crf", "18", "-pix_fmt", "yuv420p",
              "-r", str(FPS), "-video_track_timescale", "15360",
              "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
    segs, todo = [], []
    args.seg_cache.mkdir(parents=True, exist_ok=True)
    for s in scenes:
        n = s["idx"]
        clip = Path(args.clips_dir) / f"{n:02d}.mp4"
        seg = tmp / f"seg_{n:02d}.mp4"
        info = None
        if clip.exists():
            try:
                info = probe(clip)
            except SystemExit:
                if not args.allow_missing:
                    raise
                warn(f"shot {n}: clip {clip.name} đọc lỗi (đang ghi dở?) → coi như thiếu")
        if info is not None:
            frames = max(1, round(info["dur"] * FPS))
            dur = frames / FPS
            vf = (f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,"
                  f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={FPS},"
                  f"tpad=stop_mode=clone:stop_duration=1")
            # 13/10 người dùng: 2 cổng phải có hiệu ứng xuất hiện, không cắt giật shot 1 → 2 — loá trắng hồng
            if n == GATES_APPEAR - 1:
                vf += f",fade=t=out:st={max(0.0, dur - 0.12):.3f}:d=0.12:color={FLASH}"
            elif n == GATES_APPEAR:
                vf += f",fade=t=in:st=0:d=0.35:color={FLASH}"
            if n == DARK_OUT:              # 13/10: Kelly bước vào thế giới song song — tối dần về đen
                vf += f",fade=t=out:st={max(0.0, dur - 0.5):.3f}:d=0.5:color=black"
            if n == DARK_OUT_2:
                vf += f",fade=t=out:st={max(0.0, dur - DARK_OUT_2_S):.3f}:d={DARK_OUT_2_S}:color=black"
            cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(clip)]
            if info["audio"] and args.clip_audio_db is not None:
                af = f"[0:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:{dur:.6f}[a]"
            else:
                cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
                af = f"[1:a]atrim=0:{dur:.6f}[a]"
            cmd += ["-filter_complex", f"[0:v]{vf}[v];{af}", "-map", "[v]", "-map", "[a]",
                    "-frames:v", str(frames)] + common + [str(seg)]
            kind = f"clip {clip.name} ({info['dur']:.2f}s)"
        else:
            if not args.allow_missing:
                raise SystemExit(f"Thiếu clip shot {n}: {clip} (thêm --allow-missing để dựng thử)")
            dur_db = s["duration_s"] or 2.0
            frames = max(1, round(dur_db * FPS))
            dur = frames / FPS
            txt = args.seg_cache / f"miss_{n:02d}.txt"       # đường cố định → khóa đệm ổn định giữa các lần chạy
            txt.write_text(f"thiếu shot {n}", encoding="utf-8")
            vf = (f"drawtext=fontfile='{ff_path(FONT)}':textfile='{ff_path(txt)}':fontcolor=white:"
                  f"fontsize={H // 20}:x=(w-tw)/2:y=(h-th)/2")
            cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={FPS}",
                   "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                   "-filter_complex", f"[0:v]{vf},setsar=1[v];[1:a]atrim=0:{dur:.6f}[a]",
                   "-map", "[v]", "-map", "[a]", "-frames:v", str(frames)] + common + [str(seg)]
            kind = f"THIẾU → đen {dur_db:.2f}s (CSDL)"
            warn(f"shot {n} thiếu clip → khung đen {dur:.2f}s")
        # 13/10 người dùng 'dựng mất nhiều thời gian': đệm theo dấu (lệnh + kích thước/mtime clip) ở args.seg_cache — đổi 1 shot
        # chỉ mã hóa lại shot đó; các shot cần làm chạy song song (--jobs)
        st_ = clip.stat() if info is not None else None
        key = hashlib.sha1(json.dumps([cmd[:-1], st_.st_size if st_ else 0, st_.st_mtime_ns if st_ else 0,
                                       txt.read_text(encoding="utf-8") if info is None else ""]).encode("utf-8")).hexdigest()[:16]
        seg = args.seg_cache / f"seg_{n:02d}_{key}.mp4"
        hit = seg.exists()
        if not hit:
            todo.append((cmd[:-1] + [str(seg.with_suffix(".part.mp4"))], seg))
        segs.append({"n": n, "file": seg, "frames": frames, "dur": dur, "kind": kind + (" · đệm" if hit else "")})
    if todo:
        from concurrent.futures import ThreadPoolExecutor
        def one(job):
            c, final = job
            run(c)
            os.replace(c[-1], final)
        with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as ex:
            list(ex.map(one, todo))
    for sg in segs:
        print(f"  shot {sg['n']:2d}: {sg['dur']:6.3f}s  {sg['kind']}", flush=True)
    t = 0.0
    for sg in segs:
        sg["start"], t = t, t + sg["dur"]
        sg["end"] = t
    return segs


def lufs_of(path: Path) -> float:
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
               "loudnorm=print_format=json", "-f", "null", "-"], capture=True)
    j = json.loads(err[err.rindex("{"):err.rindex("}") + 1])
    v = float(j["input_i"])
    return v if v > -70 else -70.0


def place_vo(lines, segs) -> None:
    by_n = {s["n"]: s for s in segs}
    prev_end = -1.0
    for ln in lines:
        sg = by_n.get(ln["shot"])
        if sg is None:
            raise SystemExit(f"L{ln['n']} gắn shot {ln['shot']} không tồn tại")
        st = sg["start"] + 0.2
        if st < prev_end + 0.15:
            warn(f"L{ln['n']} ({ln['dur']:.2f}s) chồng câu trước (kết thúc {prev_end:.2f}s) → dời "
                 f"{st:.2f}s → {prev_end + 0.15:.2f}s")
            st = prev_end + 0.15
        ln["start"], ln["end"] = st, st + ln["dur"]
        prev_end = ln["end"]
    total = segs[-1]["end"]
    if lines and lines[-1]["end"] > total:
        warn(f"L{lines[-1]['n']} kết thúc {lines[-1]['end']:.2f}s > hết phim {total:.2f}s (bị cắt)")


def _leaf(src_args: list[str], chain: str, total: float, args) -> list[str]:
    """13/10 (lượt dựng treo ở 10,4 s): MỘT đồ thị ffmpeg 29 đầu vào + asplit + adelay tới 83 s tự khóa (chạy hết CPU, không tiến).
    Mỗi lớp tiếng (1 câu thoại / 1 nhạc / 1 lần SFX) được làm riêng thành WAV dài đúng bằng phim (trễ nằm sẵn trong WAV), đồ thị
    trộn cuối chỉ còn các WAV thẳng hàng từ 0 → không khóa được. Dùng chung giữa 2 bản (cùng khóa → cùng tệp)."""
    key = hashlib.sha1(json.dumps([src_args, chain, round(total, 6)]).encode("utf-8")).hexdigest()[:16]
    out = args._leaf_dir / f"leaf_{key}.wav"
    if not out.exists():
        run(["ffmpeg", "-y", "-v", "error"] + src_args
            + ["-filter_complex", f"[0:a]{chain},apad,atrim=0:{total:.6f}[o]", "-map", "[o]",
               "-c:a", "pcm_f32le", "-ar", "48000", "-ac", "2", str(out)])
    return ["-i", str(out)]


def _extend_music(f: Path, span: float, args) -> Path:
    """13/10 người dùng 'kéo dài thêm nhạc': nhạc ngắn hơn đoạn → bản dài hơn = phần đầu (bỏ 4 s đuôi) nối mềm 3 s vào một bản sao
    bắt đầu giữa bài, GIỮ đoạn kết gốc ở cuối (không lặp lại từ đầu, không im)."""
    mdur = probe(f)["dur"]
    head, xf = mdur - 4.0, 3.0
    start = max(0.0, mdur - (span + 0.2 - head + xf))            # head + (mdur - start) - xf = span + 0,2
    out = args._leaf_dir / f"ext_{f.stem}_{int(span * 1000)}.wav"
    if not out.exists():
        run(["ffmpeg", "-y", "-v", "error", "-i", str(f), "-i", str(f), "-filter_complex",
             f"[0:a]atrim=0:{head:.6f}[a];[1:a]atrim=start={start:.6f},asetpts=PTS-STARTPTS[b];"
             f"[a][b]acrossfade=d={xf}:c1=tri:c2=tri[o]", "-map", "[o]", "-c:a", "pcm_f32le", "-ar", "48000", str(out)])
    return out


def audio_graph(lines, segs, mA: Path, mB: Path, vo_lufs: float, args) -> tuple[list[str], str]:
    """Trả (inputs, filter_complex); input 0 = video nối (kèm audio im/clip); input 1.. = WAV lớp tiếng (_leaf), cùng dài = phim."""
    by_n = {s["n"]: s for s in segs}
    total = segs[-1]["end"]
    inputs, parts, vo_labels = [], [], []
    k = 1
    for ln in lines:
        d = int(round(ln["start"] * 1000))
        inputs += _leaf(["-i", str(ln["file"])], f"aresample=48000,aformat=channel_layouts=stereo,adelay={d}|{d}", total, args)
        vo_labels.append(f"[{k}:a]")
        k += 1
    parts.append(f"{''.join(vo_labels)}amix=inputs={len(vo_labels)}:normalize=0:duration=longest,"
                 f"atrim=0:{total:.6f},asplit=2[vobus][vosc]")
    last = segs[-1]["n"]
    specs = [("A", mA, by_n[2]["start"], by_n[11]["end"]),
             ("B", mB, by_n[12]["start"], by_n[last]["end"])]
    m_labels = []
    args._music_info = []
    for name, f, t0, t1 in specs:
        span = t1 - t0
        mdur = probe(f)["dur"]
        if mdur < span and name in args.extend_music:
            f = _extend_music(f, span, args)
            args._music_ext = getattr(args, "_music_ext", []) + [f"{name}: {mdur:.2f}s → {probe(f)['dur']:.2f}s (nối mềm 3 s, giữ đoạn kết gốc)"]
            mdur = probe(f)["dur"]
        loop = mdur < span and args.music_fill == "loop"
        play = span if (mdur >= span or loop) else mdur
        if mdur < span:
            warn(f"nhạc {name} {f.name} dài {mdur:.2f}s < đoạn {span:.2f}s → "
                 + ("lặp" if loop else f"im {span - mdur:.2f}s cuối đoạn (nhạc tự tắt dần)"))
        # gain riêng từng đoạn nhạc: LUFS nhạc = LUFS lời dẫn − 10 (hoặc ép --music-gain)
        music_gain_db = args.music_gain if args.music_gain is not None else (vo_lufs - 10.0) - lufs_of(f)
        d = int(round(t0 * 1000))
        src = (["-stream_loop", str(math.ceil(span / mdur) - 1)] if loop else []) + ["-i", str(f)]
        inputs += _leaf(src, f"aresample=48000,aformat=channel_layouts=stereo,atrim=0:{play:.6f},"
                             f"asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.5,afade=t=out:st={max(0, play - 0.8):.6f}:d=0.8,"
                             f"volume={music_gain_db:.2f}dB,adelay={d}|{d}", total, args)
        m_labels.append(f"[{k}:a]")
        args._music_info.append((name, f.name, t0, t1, mdur, play, music_gain_db))
        k += 1
    parts.append(f"{''.join(m_labels)}amix=inputs={len(m_labels)}:normalize=0:duration=longest,"
                 f"atrim=0:{total:.6f}[mus]")
    # hạ nhạc thêm khi có lời dẫn (~4–6 dB lúc đang nói)
    parts.append("[mus][vosc]sidechaincompress=threshold=0.03:ratio=4:attack=30:release=400[musd]")
    mix_in = ["[vobus]", "[musd]"]
    k = _ambience(parts, inputs, k, by_n, vo_lufs, args, mix_in)
    k = _sfx(parts, inputs, k, by_n, vo_lufs, args, mix_in)
    if args.clip_audio_db is not None:
        parts.append(f"[0:a]volume={args.clip_audio_db}dB[clipa]")
        mix_in.append("[clipa]")
    parts.append(f"{''.join(mix_in)}amix=inputs={len(mix_in)}:normalize=0:duration=first,"
                 f"atrim=0:{total:.6f}[pre]")
    return inputs, ";".join(parts)


def _sound_path(sound_id: int) -> Path | None:
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    try:
        row = con.execute("SELECT path FROM sounds WHERE id=?", (sound_id,)).fetchone()
    finally:
        con.close()
    p = Path(row[0]) if row and row[0] else None
    return p if p and p.exists() else None


def _ambience(parts, inputs, k, by_n, vo_lufs, args, mix_in) -> int:
    """Lớp âm nền shot 1–2: gió (Kho #307, lặp cho đủ) + súng xa (Kho #309 qua lowpass + echo), fade 0,5 s."""
    args._amb_info = []
    if not args.ambience:
        return k
    t0, t1 = by_n[AMB_SHOTS[0]]["start"], by_n[AMB_SHOTS[-1]]["end"]
    span, total = t1 - t0, by_n[max(by_n)]["end"]
    wind, gun = _sound_path(AMB_WIND_SOUND), _sound_path(AMB_GUN_SOUND)
    if wind is None:
        warn(f"không thấy tệp gió Kho #{AMB_WIND_SOUND} → bỏ lớp gió")
    else:
        g = (vo_lufs + args.amb_wind_db) - lufs_of(wind)
        reps = max(0, math.ceil(span / probe(wind)["dur"]) - 1)   # lặp HỮU HẠN (-stream_loop -1 / aloop -1 làm ffmpeg treo)
        d = int(round(t0 * 1000))
        inputs += _leaf(["-stream_loop", str(reps), "-i", str(wind)],
                        f"aresample=48000,aformat=channel_layouts=stereo,atrim=0:{span:.6f},asetpts=PTS-STARTPTS,"
                        f"afade=t=in:st=0:d=0.5,afade=t=out:st={span - 0.5:.6f}:d=0.5,volume={g:.2f}dB,adelay={d}|{d}",
                        total, args)
        mix_in.append(f"[{k}:a]")
        args._amb_info.append(f"gió {wind.name} {t0:.2f}–{t1:.2f}s gain {g:+.1f} dB (≈{args.amb_wind_db:+.0f} LU dưới lời dẫn)")
        k += 1
    if gun is None:
        warn(f"không thấy tệp súng Kho #{AMB_GUN_SOUND} → bỏ lớp súng xa")
    else:
        g = (vo_lufs + args.amb_gun_db) - lufs_of(gun)
        at = [t for t in AMB_GUN_AT if t < span - 1.0]
    if gun is not None and not at:
        warn("đoạn âm nền quá ngắn cho súng xa → bỏ lớp súng xa")
    elif gun is not None:
        gl = []
        for t in at:
            d = int(round((t0 + t) * 1000))
            inputs += _leaf(["-i", str(gun)], f"aresample=48000,aformat=channel_layouts=stereo,lowpass=f=1100,highpass=f=120,"
                                              f"aecho=0.8:0.6:90|240:0.35|0.2,volume={g:.2f}dB,adelay={d}|{d}", total, args)
            gl.append(f"[{k}:a]")
            k += 1
        k -= 1                                     # the k += 1 below counts the last one
        parts.append(f"{''.join(gl)}amix=inputs={len(gl)}:normalize=0:duration=longest,"
                     f"afade=t=out:st={t1 - 0.5:.6f}:d=0.5,atrim=0:{total:.6f}[ambg]")
        mix_in.append("[ambg]")
        args._amb_info.append(f"súng xa {gun.name} ×{len(at)} lúc {', '.join(f'{t0 + t:.1f}' for t in at)}s "
                              f"gain {g:+.1f} dB (≈{args.amb_gun_db:+.0f} LU dưới lời dẫn)")
        k += 1
    return k


def _sfx(parts, inputs, k, by_n, vo_lufs, args, mix_in) -> int:
    """Hiệu ứng theo SFX_PLAN: mỗi tiếng 1 đầu vào, asplit theo số lần lặp, mức theo nhóm (LUFS tệp → lời dẫn + LU nhóm)."""
    args._sfx_info = []
    if not args.sfx:
        return k
    total = by_n[max(by_n)]["end"]
    labels, cache = [], {}
    for j, (shot, off, src, grp, reps) in enumerate(SFX_PLAN):
        if shot not in by_n:
            continue
        f = _sound_path(int(src[4:])) if src.startswith("kho:") else (AUDIO / "sfx" / src)
        if f is None or not f.exists():
            warn(f"SFX {src} (shot {shot}) không thấy tệp → bỏ")
            continue
        if str(f) not in cache:
            cache[str(f)] = lufs_of(f)
        sg = by_n[shot]
        t = sg["start"] + (sg["dur"] / 2 if off == "mid" else float(off))
        g = (vo_lufs + SFX_GROUP_LU[grp]) - cache[str(f)]
        pre = "lowpass=f=1100,highpass=f=120,aecho=0.8:0.6:90|240:0.35|0.2," if grp == "xa" else ""
        for r in reps:
            d = int(round((t + r) * 1000))
            inputs += _leaf(["-i", str(f)], f"aresample=48000,aformat=channel_layouts=stereo,{pre}volume={g:.2f}dB,adelay={d}|{d}",
                            total, args)
            labels.append(f"[{k}:a]")
            k += 1
        args._sfx_info.append(f"shot {shot}: {f.name} ({grp}, {g:+.1f} dB) lúc " + ", ".join(f"{t + r:.2f}" for r in reps) + " s")
    if labels:
        parts.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=longest,atrim=0:{total:.6f}[sfxbus]")
        mix_in.append("[sfxbus]")
    return k


def _wrap_words(text: str, n: int) -> list[str]:
    out, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > n:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return out + ([cur] if cur else [])


def overlay_video(video: Path, lines, segs, args, tmp: Path) -> Path:
    """Phụ đề lời dẫn (trắng viền đen, tâm ≈ 68 % chiều cao, ≤ 2 dòng × 32 ký tự, chia khối theo số ký tự trong thời lượng
    câu) + popup BOOYAH (chữ vàng viền đen, nảy 1 s ở ≈ 40 % chiều cao) — 1 lần mã hóa lại hình, dùng chung cho cả 2 bản."""
    args._sub_info, args._popup_info = [], ""
    if not (args.subs or args.popup):
        return video
    W, H = map(int, args.size.lower().split("x"))
    font = ff_path(FONT)
    fs, bw = round(H / 30), max(2, round(H / 400))
    filt = []
    if args.subs:
        for ln in lines:
            text = ln.get("sub_text") or ln["text"] or ""
            if not text:
                warn(f"L{ln['n']} không có chữ → không phụ đề")
                continue
            rows = _wrap_words(text, SUB_MAX_CHARS)
            chunks = [rows[i:i + 2] for i in range(0, len(rows), 2)]
            weights = [sum(len(r) for r in c) for c in chunks]
            t = ln["start"]
            for ci, c in enumerate(chunks):
                d = ln["dur"] * weights[ci] / sum(weights)
                tf = tmp / f"sub_{ln['n']}_{ci}.txt"
                tf.write_text("\n".join(c), encoding="utf-8")
                filt.append(f"drawtext=fontfile='{font}':textfile='{ff_path(tf)}':fontsize={fs}:fontcolor=white:"
                            f"borderw={bw}:bordercolor=black:line_spacing={round(fs * 0.25)}:text_align=C:"
                            f"x=(w-tw)/2:y=h*0.68-th/2:enable='between(t,{t:.3f},{t + d:.3f})'")
                t += d
            args._sub_info.append(f"L{ln['n']} {ln['start']:.2f}–{ln['end']:.2f}s, {len(chunks)} khối")
    banner = None
    if args.popup:
        sg = {s["n"]: s for s in segs}.get(POPUP_SHOT)
        img = ROOT / POPUP_ASSET_IMG
        if sg and img.exists():
            t0, t1 = sg["start"], sg["end"]
            banner = (_banner_png(img, tmp), t0, t1)
            args._popup_info = f"banner Kho #431 {t0:.2f}–{t1:.2f}s (shot {POPUP_SHOT}), hiện dần 0,25 s + trượt xuống"
        elif sg:
            warn(f"không thấy {img} → popup chữ tự vẽ")
            t0, t1 = sg["start"], sg["end"]
            pf = tmp / "popup.txt"
            pf.write_text(POPUP_TEXT, encoding="utf-8")
            amp = round(H * 0.03)
            filt.append(f"drawtext=fontfile='{font}':textfile='{ff_path(pf)}':fontsize={round(H / 9)}:fontcolor=0xFFD21F:"
                        f"borderw={max(3, round(H / 200))}:bordercolor=black:x=(w-tw)/2:"
                        f"y=h*0.40-th/2-if(lt(t-{t0:.3f}\\,1)\\,{amp}*abs(sin(3*PI*(t-{t0:.3f})))*(1-(t-{t0:.3f}))\\,0):"
                        f"enable='between(t,{t0:.3f},{t1:.3f})'")
            args._popup_info = f"{POPUP_TEXT} {t0:.2f}–{t1:.2f}s (shot {POPUP_SHOT}; #27 không có icon ICON* cho core/end_popup)"
    if not filt and banner is None:
        return video
    out = tmp / "video_ov.mp4"
    vf = tmp / "ov_filter.txt"
    graph = f"[0:v]{','.join(filt) if filt else 'null'}[v0]"
    extra = []
    if banner is not None:
        png, t0, t1 = banner
        bw_px, drop = round(W * 0.98), round(H * 0.025)
        graph += (f";[1:v]format=rgba,scale={bw_px}:-1,fade=t=in:st={t0:.3f}:d=0.25:alpha=1[bn];"
                  f"[v0][bn]overlay=x=(W-w)/2:y=H*0.68-{drop}*max(0\\,1-(t-{t0:.3f})/0.25):shortest=1:"
                  f"enable='between(t,{t0:.3f},{t1:.3f})'[v]")
        extra = ["-loop", "1", "-framerate", str(FPS), "-i", str(png)]
    else:
        graph += ";[v0]null[v]"
    vf.write_text(graph, encoding="utf-8")
    run(["ffmpeg", "-y", "-v", "error", "-i", str(video)] + extra + ["-/filter_complex", str(vf), "-map", "[v]", "-map", "0:a",
         "-c:v", "libx264", "-preset", args.preset, "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy", str(out)])
    return out


def _banner_png(img: Path, tmp: Path) -> Path:
    """Banner Kho #431 là ảnh đặc (dải đỏ đè cảnh game): giữ dải đỏ + chữ trắng giữa + lõi băng, mép trái/phải mờ dần."""
    import numpy as np
    from PIL import Image
    im = np.asarray(Image.open(img).convert("RGB")).astype(np.float32)
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    h, w = R.shape
    red = np.clip((R - np.maximum(G, B) - 8) / 45, 0, 1)
    white = np.clip((np.minimum(np.minimum(R, G), B) - 150) / 60, 0, 1)
    mid = np.zeros_like(white)
    mid[:, int(w * 0.3):int(w * 0.7)] = 1
    y, x = np.linspace(0, 1, h)[:, None], np.linspace(0, 1, w)[None, :]
    core = np.clip(1 - np.abs(y - 0.55) / 0.35, 0, 1) * np.clip(1 - np.abs(x - 0.5) / 0.3, 0, 1)
    a = np.maximum(np.maximum(red, white * mid), np.clip(core * 1.6, 0, 0.9))
    a = np.clip(a * np.clip(np.minimum(x, 1 - x) / 0.06, 0, 1), 0, 1)
    out = tmp / "popup_banner.png"
    Image.fromarray(np.dstack([im, a * 255]).astype(np.uint8), "RGBA").save(out)
    return out


def mix_version(video: Path, lines, segs, mA, mB, vo_lufs, out: Path, args) -> dict:
    inputs, fc = audio_graph(lines, segs, mA, mB, vo_lufs, args)
    base = ["ffmpeg", "-y", "-hide_banner", "-nostats", "-i", str(video)] + inputs
    err = run(base + ["-filter_complex", fc + ";[pre]loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json[o]",
                      "-map", "[o]", "-f", "null", "-"], capture=True)
    m = json.loads(err[err.rindex("{"):err.rindex("}") + 1])
    ln2 = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
           f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
           f"linear=true:print_format=summary,aresample=48000")
    run(base + ["-filter_complex", fc + f";[pre]{ln2}[o]", "-map", "0:v", "-map", "[o]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-movflags", "+faststart", "-shortest", str(out)])
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(out), "-map", "0:a",
               "-af", "ebur128=peak=true", "-f", "null", "-"], capture=True)
    i_m = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    tp_m = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", err)
    return {"in_I": float(m["input_i"]), "I": float(i_m[-1]) if i_m else None,
            "TP": float(tp_m[-1]) if tp_m else None, "dur": probe(out)["dur"]}


def write_moc(path: Path, segs, lines, results, map_src, music_info, args) -> None:
    L = [f"# #27 — mốc dựng video tổng ({time.strftime('%Y-%m-%d %H:%M')})", "",
         f"- Khung {args.size}, {FPS} fps, nối cứng; tổng {segs[-1]['end']:.2f} s; tag: {args.tag or '(bản chính)'}",
         f"- Ánh xạ lời dẫn ↔ shot: {map_src}",
         f"- Nhạc: ≈10 dB dưới lời dẫn (gain tự đo theo LUFS) + sidechaincompress theo bus lời dẫn; "
         f"âm thanh gốc clip: {'giữ ' + str(args.clip_audio_db) + ' dB' if args.clip_audio_db is not None else 'bỏ'}",
         "", "## Shot", "", "| Shot | Bắt đầu (s) | Kết thúc (s) | Dài (s) | Nguồn |", "|---|---|---|---|---|"]
    for s in segs:
        L.append(f"| {s['n']} | {s['start']:.2f} | {s['end']:.2f} | {s['dur']:.2f} | {s['kind']} |")
    L += ["", "## Lời dẫn (giọng 72)", "",
          "| Câu | Shot | Bắt đầu (s) | Kết thúc (s) | Dài (s) | Tệp | Căn cứ | Chữ |", "|---|---|---|---|---|---|---|---|"]
    for ln in lines:
        L.append(f"| L{ln['n']} | {ln['shot']} | {ln['start']:.2f} | {ln['end']:.2f} | {ln['dur']:.2f} | "
                 f"{ln['file'].name} | {ln['src']} | {ln['text']} |")
    L += ["", "## Nhạc", "", "| Bản | Đoạn | Tệp | Từ (s) | Đến (s) | Nhạc dài (s) | Phát (s) | Gain (dB) |",
          "|---|---|---|---|---|---|---|---|"]
    for ver, info in music_info:
        for name, fn, t0, t1, md, play, gain in info:
            L.append(f"| {ver} | {name} | {fn} | {t0:.2f} | {t1:.2f} | {md:.2f} | {play:.2f} | {gain:+.1f} |")
    L += ["", "## Âm nền shot 1–2", ""] + ([f"- {x}" for x in getattr(args, "_amb_info", [])] or ["- (tắt)"])
    L += ["", "## Hiệu ứng (SFX)", ""] + ([f"- {x}" for x in getattr(args, "_sfx_info", [])] or ["- (tắt)"])
    L += ["", "## Phụ đề + popup", ""] + [f"- {x}" for x in getattr(args, "_sub_info", [])] + \
         ([f"- popup {args._popup_info}"] if getattr(args, "_popup_info", "") else [])
    L += ["", "## Tệp ra", "", "| Tệp | Dài (s) | LUFS trước chuẩn hóa | LUFS ra | True peak (dBFS) |",
          "|---|---|---|---|---|"]
    for name, r in results.items():
        L.append(f"| {name} | {r['dur']:.2f} | {r['in_I']:.1f} | {r['I']} | {r['TP']} |")
    L += ["", "## Cảnh báo", ""] + ([f"- {w}" for w in WARN] or ["- (không)"])
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clips-dir", default=str(PROJ / "videos"))
    ap.add_argument("--allow-missing", action="store_true")
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--tag", default="")
    ap.add_argument("--out-dir", default=str(OUT_DIR_DEFAULT))
    ap.add_argument("--vo-map", default="", help="ép shot cho L1..L9, vd 2,4,6,8,10,12,14,17,20")
    ap.add_argument("--music-gain", type=float, default=None, help="dB cho nhạc (mặc định tự đo = lời dẫn −10 LU)")
    ap.add_argument("--music-fill", choices=["silence", "loop"], default="silence")
    ap.add_argument("--extend-music", default="", help="kéo dài nhạc ngắn bằng nối mềm (giữ đoạn kết): A, B hoặc AB")
    ap.add_argument("--clip-audio-db", type=float, default=None, help="giữ tiếng gốc clip ở mức dB (vd -30); mặc định bỏ")
    ap.add_argument("--preset", default="fast", help="x264 preset cho hình")
    ap.add_argument("--jobs", type=int, default=4, help="số shot chuẩn hóa song song")
    ap.add_argument("--seg-cache", default="", help="thư mục đệm shot đã chuẩn hóa (mặc định <out-dir>/_dem_shot)")
    ap.add_argument("--only", default="", help="chỉ dựng bản: ban1 | ban2")
    ap.add_argument("--vo-file", action="append", default=[], help="thay tệp một câu: 9=đường/dẫn.mp3 (lặp được)")
    ap.add_argument("--no-sfx", dest="sfx", action="store_false", help="tắt hiệu ứng âm thanh")
    ap.add_argument("--no-subs", dest="subs", action="store_false", help="tắt phụ đề lời dẫn")
    ap.add_argument("--no-popup", dest="popup", action="store_false", help="tắt popup BOOYAH")
    ap.add_argument("--no-ambience", dest="ambience", action="store_false", help="tắt lớp gió + súng xa shot 1–2")
    ap.add_argument("--amb-wind-db", type=float, default=-29.0, help="gió: LU dưới lời dẫn (mặc định −29)")
    ap.add_argument("--amb-gun-db", type=float, default=-32.0, help="súng xa: LU dưới lời dẫn (mặc định −32)")
    args = ap.parse_args()
    t_start = time.time()
    if not shutil.which("ffmpeg"):
        raise SystemExit("Không thấy ffmpeg trong PATH")

    scenes = load_scenes()
    lines = load_vo_lines()
    for spec in args.vo_file:
        n, _, f = spec.partition("=")
        f = Path(f)
        if not f.exists():
            raise SystemExit(f"--vo-file {spec}: không thấy tệp")
        for ln in lines:
            if ln["n"] == int(n):
                warn(f"L{n}: dùng tệp thay {f.name} (thay {ln['file'].name})")
                ln["file"], ln["dur"] = f, probe(f)["dur"]
    forced = [int(x) for x in args.vo_map.split(",") if x.strip()] if args.vo_map else None
    map_src = map_vo(lines, scenes, forced)
    vo_by_shot = {sc["idx"]: sc["vo_text"] for sc in scenes if sc["vo_text"]}
    for ln in lines:            # phụ đề theo CHỮ trong CSDL (đã sửa, vd 'gạt giò'); không có thì chữ của tệp TTS
        ln["sub_text"] = next((t for t in vo_by_shot.values() if norm_text(t)[:25] == norm_text(ln["text"])[:25]), "")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    args.seg_cache = Path(args.seg_cache) if args.seg_cache else out_dir / "_dem_shot"
    suffix = f"_{args.tag}" if args.tag else ""

    with tempfile.TemporaryDirectory(prefix="p27mix_") as td:
        tmp = Path(td)
        print(f"[1/3] Chuẩn hóa {len(scenes)} shot → {args.size} {FPS}fps", flush=True)
        segs = build_segments(args, scenes, tmp)
        lst = tmp / "concat.txt"
        lst.write_text("".join(f"file '{s['file'].as_posix()}'\n" for s in segs), encoding="utf-8")
        video = tmp / "video.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(video)])
        place_vo(lines, segs)
        video = overlay_video(video, lines, segs, args, tmp)

        vo_lufs = max(lufs_of(ln["file"]) for ln in lines)
        args._leaf_dir = tmp
        results, music_info = {}, []
        print("[2/3] Trộn âm thanh + loudnorm 2 lượt", flush=True)
        for name, fa, fb in VERSIONS:
            if args.only and not name.startswith(args.only):
                continue
            mA, mB = AUDIO / "music_A" / fa, AUDIO / "music_B" / fb
            out = out_dir / f"27_final_{name}{suffix}.mp4"
            r = mix_version(video, lines, segs, mA, mB, vo_lufs, out, args)
            music_info.append((name, args._music_info))
            gains = '/'.join(f'{x[6]:+.1f}' for x in args._music_info)
            results[out.name] = r
            print(f"  {out}  dài {r['dur']:.2f}s  LUFS {r['I']}  TP {r['TP']} dBFS  (nhạc A/B {gains} dB)", flush=True)
            if r["TP"] is not None and r["TP"] > -1.0:
                warn(f"{out.name}: true peak {r['TP']} > -1 dBTP")
            if r["I"] is not None and abs(r["I"] + 14) > 1.0:
                warn(f"{out.name}: LUFS {r['I']} lệch -14 quá 1 LU")
        moc = out_dir / f"mix_moc{suffix}.md"
        write_moc(moc, segs, lines, results, map_src, music_info, args)
    print(f"[3/3] Mốc: {moc}\nXong trong {time.time() - t_start:.0f}s; cảnh báo: {len(WARN)}")


if __name__ == "__main__":
    main()
