"""Tiếng của video tham chiếu → âm hiệu ứng của shot (F5-B, 09/10; người dùng #24 08/10: "video ref hành động có sound riêng → lúc dựng
ghép khớp động tác").

- `propose(p, data_dir, pid)`: mỗi shot gắn video ref (`motion_prompts.ref_video_path`) có luồng âm thanh → tách tiếng (ffmpeg, 0 USD) thành
  một tệp trong `<data>/<pid>/audio_assets/` qua `audio_lib.add_local`, ở trạng thái ĐỀ XUẤT: `use: False`, nhãn "Tiếng video ref shot N",
  neo vào shot (`anchor_idx`, `offset` 0) để khi dựng nó đi theo shot. Không tự bật — người tích ở Bước 5. Gọi lại không tách trùng.
- `fit(directory, entry, shot_seconds)`: khi dựng (sfx_plan.place_on_timeline), tiếng đã được tích nén/giãn `atempo` cho khớp độ dài
  clip thật của shot nếu chênh ≤ 40 %; chênh hơn → giữ tốc độ gốc và ghi lý do (`fit_skipped`), không im lặng (CHUAN luật 1).
"""
import os
import subprocess
import tempfile
from typing import Dict, Optional

from . import audio_lib, ffmpeg_studio

SOURCE = "ref_video"
LABEL = "Tiếng video ref shot {n}"
MAX_STRETCH = 0.40          # người dùng 08/10: nén/giãn khi chênh ≤ 40 %; hơn thì méo tiếng — giữ nguyên
MIN_STRETCH = 0.02          # chênh dưới 2 % không đáng một lượt ffmpeg


def _extract(src: str, dst: str, ffmpeg: str) -> None:
    subprocess.run([ffmpeg, "-y", "-v", "error", "-i", src, "-vn", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", dst],
                   check=True, capture_output=True)


def propose(p, data_dir: str, pid: int) -> Dict:
    """Tách tiếng các video ref có âm thanh thành đề xuất SFX của shot. Returns {"added": [idx], "no_audio": [idx], "missing": [idx],
    "already": [idx]} — mọi shot có video ref đều được kể (không im lặng khi bỏ qua)."""
    directory = audio_lib.assets_dir(data_dir, pid)
    have = {(e.get("anchor_idx"), e.get("ref_video")) for e in audio_lib.load(directory) if e.get("source") == SOURCE}
    out = {"added": [], "no_audio": [], "missing": [], "already": []}
    rows = p.conn.execute("SELECT s.idx, m.ref_video_path FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id "
                          "WHERE s.project_id=? AND m.ref_video_path IS NOT NULL AND m.ref_video_path != '' ORDER BY s.idx",
                          (pid,)).fetchall()
    ffmpeg = None
    for r in rows:
        idx, ref = r["idx"], r["ref_video_path"]
        if (idx, ref) in have:
            out["already"].append(idx)
            continue
        if not os.path.exists(ref):
            out["missing"].append(idx)
            continue
        if not ffmpeg_studio.has_audio(ref):
            out["no_audio"].append(idx)
            continue
        ffmpeg = ffmpeg or ffmpeg_studio.find_ffmpeg()
        tmp_dir = tempfile.mkdtemp()
        tmp = os.path.join(tmp_dir, "ref_audio.wav")
        try:
            _extract(ref, tmp, ffmpeg)
            seconds = ffmpeg_studio.probe_duration(tmp) or 0.0
            audio_lib.add_local(directory, tmp, LABEL.format(n=idx), duration_ms=int(round(seconds * 1000)) or None,
                                extra={"anchor_idx": idx, "offset": 0.0, "use": False, "source": SOURCE, "ref_video": ref,
                                       "ref_seconds": round(seconds, 3)})
            out["added"].append(idx)
        finally:
            try:
                os.remove(tmp)
                os.rmdir(tmp_dir)
            except OSError:
                pass
    return out


def tempo(ref_seconds: float, shot_seconds: float) -> Optional[float]:
    """atempo factor that makes `ref_seconds` last `shot_seconds`; None = no change needed (≤ 2 %) or too far (> 40 %, see fit)."""
    if not ref_seconds or not shot_seconds or ref_seconds <= 0 or shot_seconds <= 0:
        return None
    factor = float(ref_seconds) / float(shot_seconds)
    if abs(factor - 1.0) < MIN_STRETCH or abs(factor - 1.0) > MAX_STRETCH:
        return None
    return round(factor, 4)


def fit(directory: str, entry: Dict, shot_seconds: float, ffmpeg: Optional[str] = None) -> Dict:
    """Mutates `entry` (one ref-audio row switched on): `fit_file` + `fit_tempo` when stretched, `fit_skipped` (Vietnamese reason)
    when not. The original file is never changed."""
    entry.pop("fit_skipped", None)
    ref_s = float(entry.get("ref_seconds") or (entry.get("duration_ms") or 0) / 1000.0)
    shot_s = float(shot_seconds or 0)
    if ref_s <= 0 or shot_s <= 0:
        entry.pop("fit_file", None)
        entry["fit_skipped"] = "không đo được độ dài tiếng ref hoặc clip — giữ tốc độ gốc"
        return entry
    factor = ref_s / shot_s
    if abs(factor - 1.0) > MAX_STRETCH:
        entry.pop("fit_file", None)
        entry["fit_skipped"] = (f"tiếng ref {ref_s:.2f} s, clip {shot_s:.2f} s — chênh {abs(factor - 1) * 100:.0f} % > "
                                f"{MAX_STRETCH * 100:.0f} %, giữ tốc độ gốc (chỉnh tay giây bắt đầu nếu cần)")
        return entry
    t = tempo(ref_s, shot_s)
    if t is None:                                   # already the same length
        entry.pop("fit_file", None)
        entry.pop("fit_tempo", None)
        return entry
    if entry.get("fit_file") and entry.get("fit_tempo") == t and os.path.exists(os.path.join(directory, entry["fit_file"])):
        return entry
    name = os.path.splitext(entry["file"])[0] + "_fit.wav"
    subprocess.run([ffmpeg or ffmpeg_studio.find_ffmpeg(), "-y", "-v", "error", "-i", os.path.join(directory, entry["file"]),
                    "-filter:a", f"atempo={t}", "-c:a", "pcm_s16le", os.path.join(directory, name)], check=True, capture_output=True)
    entry.update(fit_file=name, fit_tempo=t)
    return entry
