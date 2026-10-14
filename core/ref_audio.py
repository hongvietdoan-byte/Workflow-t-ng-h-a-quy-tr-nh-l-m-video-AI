"""Tiếng của video tham chiếu → âm hiệu ứng của shot (F5-B, 09/10; người dùng #24 08/10: "video ref hành động có sound riêng → lúc dựng
ghép khớp động tác").

- `propose(p, data_dir, pid)`: mỗi shot gắn video ref (`motion_prompts.ref_video_path`) có luồng âm thanh → tách tiếng (ffmpeg, 0 USD) thành
  một tệp trong `<data>/<pid>/audio_assets/` qua `audio_lib.add_local`, ở trạng thái ĐỀ XUẤT: `use: False`, nhãn "Tiếng video ref shot N",
  neo vào shot (`anchor_idx`, `offset` 0) để khi dựng nó đi theo shot. Không tự bật — người tích ở Bước 5. Gọi lại không tách trùng.
- `fit(directory, entry, shot_seconds)`: khi dựng (sfx_plan.place_on_timeline), tiếng đã được tích nén/giãn `atempo` cho khớp độ dài
  clip thật của shot nếu chênh ≤ 40 %; chênh hơn → giữ tốc độ gốc và ghi lý do (`fit_skipped`), không im lặng (CHUAN luật 1).
"""
import os
import json
import math
import hashlib
import re
import subprocess
import tempfile
from typing import Dict, Optional

from . import audio_lib, ffmpeg_studio

SOURCE = "ref_video"
LABEL = "Tiếng video ref shot {n}"
MAX_STRETCH = 0.40          # người dùng 08/10: nén/giãn khi chênh ≤ 40 %; hơn thì méo tiếng — giữ nguyên
MIN_STRETCH = 0.02          # chênh dưới 2 % không đáng một lượt ffmpeg
MAX_SOURCE_BYTES = 512 * 1024 * 1024  # hash hữu hạn, không đọc vô hạn tệp người dùng
SOURCE_INPUT_GUARDS = ["-protocol_whitelist", "file,pipe", "-format_whitelist", "mov,matroska,webm,wav"]


def validate_metadata(value, allowed_root=None):
    """Nguồn GỐC, giây [start,end], speed là tốc độ phát (0,5 = chậm ×2)."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            raise ValueError("VÀNG: metadata tiếng ref không hợp lệ") from None
    if not isinstance(value, dict) or not isinstance(value.get("source_path"), str):
        raise ValueError("VÀNG: thiếu metadata nguồn GỐC/giây đầu-cuối/tốc độ tiếng ref")
    path = value["source_path"]
    validate_local_path(path, allowed_root)
    numbers = [value.get(k) for k in ("start", "end", "speed")]
    if any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) for n in numbers):
        raise ValueError("VÀNG: giây đầu-cuối/tốc độ tiếng ref phải là số hữu hạn")
    start, end, speed = map(float, numbers)
    duration = _source_duration(path)
    if start < 0 or end <= start or not .01 <= speed <= 100 or end - start > 600 or (end - start) / speed > 600 or not duration or not math.isfinite(duration) or end > duration + .01:
        raise ValueError("VÀNG: đoạn nguồn/tốc độ tiếng ref ngoài phạm vi đo được")
    return dict(source_path=path, start=start, end=end, speed=speed)


def validate_local_path(path, allowed_root):
    if path.startswith(("\\\\", "//")) or not os.path.isabs(path):
        raise ValueError("VÀNG: nguồn ref phải là tệp cục bộ trong dự án")
    if allowed_root:
        try:
            inside = os.path.commonpath([os.path.realpath(path), os.path.realpath(allowed_root)]) == os.path.realpath(allowed_root)
        except ValueError:
            inside = False
        if not inside:
            raise ValueError("VÀNG: nguồn GỐC phải nằm trong thư mục dự án")
    if not os.path.isfile(path):
        raise ValueError("VÀNG: không thấy tệp nguồn GỐC cục bộ của tiếng ref")


def _source_fingerprint(path):
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as source:
            if os.fstat(source.fileno()).st_size > MAX_SOURCE_BYTES:
                raise ValueError("VÀNG: nguồn GỐC vượt giới hạn 512 MiB")
            total = 0
            while chunk := source.read(min(1024 * 1024, MAX_SOURCE_BYTES - total + 1)):
                total += len(chunk)
                if total > MAX_SOURCE_BYTES:
                    raise ValueError("VÀNG: nguồn GỐC vượt giới hạn 512 MiB")
                digest.update(chunk)
    except OSError:
        raise ValueError("VÀNG: không đọc được nguồn GỐC để kiểm thay đổi") from None
    return digest.hexdigest()


def _source_probe(path):
    try:
        result = subprocess.run([ffmpeg_studio.find_ffmpeg(), "-hide_banner", *SOURCE_INPUT_GUARDS, "-i", path], capture_output=True,
                                text=True, encoding="utf-8", errors="replace", env=_native_env(), timeout=15)
        return result.stderr or ""
    except (OSError, subprocess.TimeoutExpired, ffmpeg_studio.FFmpegNotFound):
        return ""


def _source_duration(path):
    found = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", _source_probe(path))
    return int(found[1]) * 3600 + int(found[2]) * 60 + float(found[3]) if found else None


def _tempo_chain(speed):
    parts = []
    while speed < .5:
        parts.append("atempo=0.5")
        speed *= 2
    while speed > 2:
        parts.append("atempo=2.0")
        speed /= 2
    return ",".join(parts + [f"atempo={speed}"])


def _native_env():
    return {"SYSTEMROOT": "C:\\Windows", "WINDIR": "C:\\Windows"} if os.name == "nt" else {}


def _extract_segment(meta, dst, ffmpeg):
    spec = f"atrim=start={meta['start']}:end={meta['end']},asetpts=PTS-STARTPTS," + _tempo_chain(meta['speed'])
    subprocess.run([ffmpeg, "-y", "-v", "error", *SOURCE_INPUT_GUARDS, "-i", meta["source_path"], "-vn", "-af", spec,
                    "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", dst], check=True, capture_output=True, env=_native_env(), timeout=60)


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
    from . import features
    sync = features.on("ref_audio_sync")
    column = ", m.ref_audio_metadata" if sync else ""
    rows = p.conn.execute("SELECT s.idx, m.ref_video_path" + column + " FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id "
                          "WHERE s.project_id=? AND m.ref_video_path IS NOT NULL AND m.ref_video_path != '' ORDER BY s.idx",
                          (pid,)).fetchall()
    metadata = {}
    fingerprints = {}
    identities = {}
    for row in rows:
        ref = row["ref_video_path"]
        if sync:
            try:
                meta = validate_metadata(row["ref_audio_metadata"], os.path.join(data_dir, str(pid)))
                fingerprint = _source_fingerprint(meta["source_path"])
                metadata[row["idx"]] = meta
                fingerprints[row["idx"]] = fingerprint
                ref += "#" + hashlib.sha256(json.dumps(meta, sort_keys=True).encode()).hexdigest() + "#" + fingerprint
            except ValueError as ex:
                out["failed"].append((row["idx"], str(ex)))
        identities[row["idx"]] = ref
    _prune(directory, identities, out)
    have = {(e.get("anchor_idx"), e.get("ref_video")) for e in audio_lib.load(directory) if e.get("source") == SOURCE}
    ffmpeg = None
    for r in rows:
        idx, ref = r["idx"], r["ref_video_path"]
        if sync and idx not in metadata:
            continue
        identity = identities[idx]
        source = metadata[idx]["source_path"] if sync else ref
        if (idx, identity) in have:
            out["already"].append(idx)
            continue
        if not os.path.exists(source):
            out["missing"].append(idx)
            continue
        if not (bool(ffmpeg_studio._AUDIO_STREAM.search(_source_probe(source))) if sync else ffmpeg_studio.has_audio(source)):
            out["no_audio"].append(idx)
            continue
        ffmpeg = ffmpeg or ffmpeg_studio.find_ffmpeg()
        tmp_dir = tempfile.mkdtemp()
        tmp = os.path.join(tmp_dir, "ref_audio.wav")
        try:
            if sync:
                if _source_fingerprint(source) != fingerprints[idx]:
                    raise ValueError("VÀNG: nguồn GỐC đã đổi trước khi tách tiếng")
                _extract_segment(metadata[idx], tmp, ffmpeg)
            else:
                _extract(ref, tmp, ffmpeg)
            seconds = (_source_duration(tmp) if sync else ffmpeg_studio.probe_duration(tmp)) or 0.0
            if sync and _source_fingerprint(source) != fingerprints[idx]:
                raise ValueError("VÀNG: nguồn GỐC đã đổi trong khi tách tiếng")
            audio_lib.add_local(directory, tmp, LABEL.format(n=idx), duration_ms=int(round(seconds * 1000)) or None,
                                extra={"anchor_idx": idx, "offset": 0.0, "use": False, "source": SOURCE, "ref_video": identity,
                                       "ref_seconds": round(seconds, 3), **({"ref_audio_metadata": metadata[idx]} if sync else {})})
            out["added"].append(idx)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, ValueError) as ex:      # một shot lỗi không dừng cả lượt
            err = getattr(ex, "stderr", None)
            why = (err.decode("utf-8", "replace").strip().splitlines() or [""])[-1] if isinstance(err, bytes) else str(ex)
            out["failed"].append((idx, "VÀNG: không tách được tiếng nguồn GỐC" if sync else why[:200] or type(ex).__name__))
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
    from . import features
    if entry.get("ref_audio_metadata") and features.on("ref_audio_sync"):
        shot_s = float(shot_seconds or 0)
        if not math.isfinite(shot_s) or not 0 < shot_s <= 600:
            entry.pop("fit_file", None)
            entry["fit_skipped"] = "VÀNG: độ dài shot phải hữu hạn trong (0,600] giây"
            return entry
        # Đã atempo theo ref khi tách: chỉ giới hạn/pad im lặng tới cuối shot, không đổi tốc độ lần hai.
        name = os.path.splitext(entry["file"])[0] + "_sync.wav"
        if entry.get("fit_file") == name and entry.get("fit_shot_seconds") == shot_s and os.path.isfile(os.path.join(directory, name)):
            return entry
        fd, temporary = tempfile.mkstemp(prefix="ref_sync_", suffix=".wav", dir=directory)
        os.close(fd)
        try:
            subprocess.run([ffmpeg or ffmpeg_studio.find_ffmpeg(), "-y", "-v", "error", "-i", os.path.join(directory, entry["file"]),
                            "-af", f"apad,atrim=duration={shot_s},asetpts=PTS-STARTPTS", "-c:a", "pcm_s16le", temporary],
                           check=True, capture_output=True, env=_native_env(), timeout=60)
            os.replace(temporary, os.path.join(directory, name))
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)
        entry.update(fit_file=name, fit_shot_seconds=shot_s)
        entry.pop("fit_tempo", None)
        return entry
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
