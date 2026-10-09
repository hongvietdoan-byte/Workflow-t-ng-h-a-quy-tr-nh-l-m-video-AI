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


def _drop_files(directory: str, entry: Dict, keys=("file", "fit_file")) -> None:
    for key in keys:
        if entry.get(key):
            try:
                os.remove(os.path.join(directory, entry[key]))
            except OSError:
                pass


def _prune(directory: str, current: Dict[int, str], out: Dict) -> None:
    """Rà F5 mục 7 (09/10): đề xuất tiếng của video ref ĐÃ ĐỔI / ĐÃ BỎ khỏi shot. Chưa tích → gỡ (cả tệp + bản nén/giãn); người đã tích
    → giữ (người quyết) nhưng ghi `ref_stale` để Bước 5 nói rõ đó là tiếng của video cũ."""
    items, keep, changed = audio_lib.load(directory), [], False
    for e in items:
        if e.get("source") == SOURCE and current.get(e.get("anchor_idx")) != e.get("ref_video"):
            if not e.get("use"):
                _drop_files(directory, e)
                out["removed"].append(e.get("anchor_idx"))
                changed = True
                continue
            if not e.get("ref_stale"):
                e["ref_stale"] = "video ref của shot đã đổi / đã bỏ — đây là tiếng của video cũ"
                out["stale_used"].append(e.get("anchor_idx"))
                changed = True
        keep.append(e)
    if changed:
        audio_lib._save(directory, keep)


def propose(p, data_dir: str, pid: int) -> Dict:
    """Tách tiếng các video ref có âm thanh thành đề xuất SFX của shot. Returns {"added", "no_audio", "missing", "already", "failed":
    [(idx, lý do)], "removed", "stale_used": [idx]} — mọi shot có video ref đều được kể (không im lặng khi bỏ qua); lỗi ffmpeg một shot
    không dừng các shot khác (rà F5 mục 6); đề xuất của video ref cũ được dọn trước (`_prune`)."""
    directory = audio_lib.assets_dir(data_dir, pid)
    out = {"added": [], "no_audio": [], "missing": [], "already": [], "failed": [], "removed": [], "stale_used": []}
    rows = p.conn.execute("SELECT s.idx, m.ref_video_path FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id "
                          "WHERE s.project_id=? AND m.ref_video_path IS NOT NULL AND m.ref_video_path != '' ORDER BY s.idx",
                          (pid,)).fetchall()
    _prune(directory, {r["idx"]: r["ref_video_path"] for r in rows}, out)
    have = {(e.get("anchor_idx"), e.get("ref_video")) for e in audio_lib.load(directory) if e.get("source") == SOURCE}
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
        except (subprocess.CalledProcessError, OSError) as ex:      # rà F5 mục 6: một shot lỗi không dừng cả lượt
            err = getattr(ex, "stderr", None)
            why = (err.decode("utf-8", "replace").strip().splitlines() or [""])[-1] if isinstance(err, bytes) else str(ex)
            out["failed"].append((idx, why[:200] or type(ex).__name__))
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
    old_fit = entry.get("fit_file")
    try:
        return _fit(directory, entry, shot_seconds, ffmpeg)
    finally:                                        # rà F5 mục 7: bản nén/giãn không còn dùng thì xóa (không để tệp cũ tích lại)
        if old_fit and entry.get("fit_file") != old_fit:
            _drop_files(directory, {"fit_file": old_fit}, keys=("fit_file",))


def _fit(directory: str, entry: Dict, shot_seconds: float, ffmpeg: Optional[str]) -> Dict:
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
