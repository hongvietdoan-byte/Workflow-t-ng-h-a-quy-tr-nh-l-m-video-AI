import os
import re
import shutil
import subprocess
import tempfile
from typing import List, Optional, Sequence


class FFmpegNotFound(Exception):
    pass


class FFmpegError(Exception):
    pass


def find_ffmpeg() -> str:
    path = os.environ.get("FFMPEG_PATH") or shutil.which("ffmpeg")
    if not path:
        raise FFmpegNotFound("ffmpeg not found: install it or set FFMPEG_PATH")
    return path


_ENCODE = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "24"]


def write_concat_list(clips: Sequence[str], directory: Optional[str] = None) -> str:
    fd, path = tempfile.mkstemp(suffix=".txt", dir=directory)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for clip in clips:
            escaped = os.path.abspath(clip).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")
    return path


def build_concat_cmd(list_file: str, output: str, ffmpeg: str = "ffmpeg") -> List[str]:
    return [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_file, *_ENCODE, "-an", output]


def build_crossfade_cmd(clips: Sequence[str], durations: Sequence[float], output: str,
                        fade: float = 1.0, ffmpeg: str = "ffmpeg") -> List[str]:
    if len(clips) != len(durations) or len(clips) < 2:
        raise ValueError("need >= 2 clips and one duration per clip")
    if any(d <= fade for d in durations):
        raise ValueError("every clip must be longer than the crossfade")
    cmd = [ffmpeg, "-y"]
    for clip in clips:
        cmd += ["-i", clip]
    parts, prev, elapsed = [], "[0:v]", durations[0]
    for i in range(1, len(clips)):
        offset = round(elapsed - fade, 3)
        label = f"[v{i}]"
        parts.append(f"{prev}[{i}:v]xfade=transition=fade:duration={fade}:offset={offset}{label}")
        prev = label
        elapsed += durations[i] - fade
    return cmd + ["-filter_complex", ";".join(parts), "-map", prev, *_ENCODE, "-an", output]


def build_mux_music_cmd(video: str, music: str, output: str, video_duration: float,
                        fade: float = 1.5, volume: float = 0.6, ffmpeg: str = "ffmpeg") -> List[str]:
    fade_out_start = max(video_duration - fade, 0)
    audio = (f"[1:a]atrim=0:{video_duration},afade=t=in:d={fade},"
             f"afade=t=out:st={fade_out_start}:d={fade},volume={volume},apad[a]")  # apad: music shorter than video
    return [ffmpeg, "-y", "-i", video, "-i", music, "-filter_complex", audio,
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-shortest", output]


def run(cmd: List[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise FFmpegError(proc.stderr[-2000:])


_DURATION = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


def probe_duration(path: str) -> Optional[float]:
    """Length in seconds read from `ffmpeg -i` (no ffprobe needed); None when it cannot be determined."""
    try:
        proc = subprocess.run([find_ffmpeg(), "-hide_banner", "-i", path], capture_output=True, text=True)
    except (FFmpegNotFound, OSError):
        return None
    m = _DURATION.search(proc.stderr or "")
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else None


def render_final(clips: Sequence[str], output: str, durations: Optional[Sequence[float]] = None,
                 transition: str = "cut", fade: float = 1.0, music: Optional[str] = None,
                 music_volume: float = 0.6) -> str:
    """Concat approved clips (in scene order), optionally crossfade and mux music."""
    ffmpeg = find_ffmpeg()
    silent = output if music is None else output + ".silent.mp4"
    if transition == "crossfade":
        if durations is None:
            raise ValueError("durations required for crossfade")
        run(build_crossfade_cmd(clips, durations, silent, fade, ffmpeg))
    else:
        list_file = write_concat_list(clips)
        try:
            run(build_concat_cmd(list_file, silent, ffmpeg))
        finally:
            os.remove(list_file)
    if music is not None:
        if durations is None:
            raise ValueError("durations required to fit music")
        total = sum(durations) - (fade * (len(clips) - 1) if transition == "crossfade" else 0)
        try:
            run(build_mux_music_cmd(silent, music, output, total, volume=music_volume, ffmpeg=ffmpeg))
        finally:
            os.remove(silent)
    return output
