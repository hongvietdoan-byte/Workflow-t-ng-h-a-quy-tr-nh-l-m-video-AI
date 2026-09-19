"""Waveform peaks for the music cards (a row of bars like the mockup).

Uses the `wave` module for .wav files and ffmpeg (decoding to raw 8 kHz mono PCM) for everything else.
Returns [] when the audio cannot be read; callers then show a plain placeholder.
"""
import array
import subprocess
import wave
from typing import List

from . import ffmpeg_studio


def _bars(samples, bars: int) -> List[float]:
    n = len(samples)
    if n == 0:
        return []
    size = max(n // bars, 1)
    peaks = [max((abs(v) for v in samples[i:i + size]), default=0) for i in range(0, size * bars, size)]
    top = max(peaks) or 1
    return [round(p / top, 3) for p in peaks[:bars]]


def _wav_samples(path: str):
    with wave.open(path, "rb") as w:
        if w.getsampwidth() != 2:
            return None
        frames = w.readframes(w.getnframes())
        channels = w.getnchannels()
    data = array.array("h")
    data.frombytes(frames[: len(frames) - len(frames) % 2])
    return data[::channels] if channels > 1 else data


def _ffmpeg_samples(path: str):
    try:
        cmd = [ffmpeg_studio.find_ffmpeg(), "-v", "error", "-i", path, "-ac", "1", "-ar", "8000", "-f", "s16le", "-"]
        proc = subprocess.run(cmd, capture_output=True, timeout=60)
    except (ffmpeg_studio.FFmpegNotFound, OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or not proc.stdout:
        return None
    data = array.array("h")
    data.frombytes(proc.stdout[: len(proc.stdout) - len(proc.stdout) % 2])
    return data


def peaks(path: str, bars: int = 64) -> List[float]:
    """`bars` values in 0..1 (relative loudness over time), or [] when unreadable."""
    samples = None
    if path.lower().endswith(".wav"):
        try:
            samples = _wav_samples(path)
        except (OSError, EOFError, wave.Error):
            samples = None
    if samples is None:
        samples = _ffmpeg_samples(path)
    return _bars(samples, bars) if samples is not None else []
