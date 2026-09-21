"""Recognising what a sound IS (so a sound effect is never chosen from its file name alone).

Uses Google's YAMNet (Apache-2.0, 521 AudioSet classes: whoosh, explosion, thump, glass breaking, gunshot, click, speech...) through
onnxruntime on this PC: nothing is uploaded, no API and no credit. The 16 MB model is downloaded once into data/models/.

Only the first seconds of a file are decoded (ffmpeg), so a large library is listened to in about a minute. The score of a class is
its strongest moment in the clip. Generic labels ("Silence", "Sound effect"...) are ignored, and human voices are kept apart:
a voice clip is never picked as an accent. If the model or onnxruntime is missing the sound is simply "not listened to" and the
automatic effects stay off (`available()` is False).
"""
import csv
import os
import subprocess
import urllib.request
from typing import Dict, List, Optional, Tuple

from . import ffmpeg_studio

MODEL_URL = "https://huggingface.co/zeropointnine/yamnet-onnx/resolve/main/yamnet.onnx"
CLASSES_URL = "https://huggingface.co/zeropointnine/yamnet-onnx/resolve/main/yamnet_class_map.csv"
TRUST = 0.40                     # a sound is used automatically only when its best class scores at least this
LISTEN_SECONDS = 10
GENERIC = {"silence", "sound effect", "noise", "inside, small room", "inside, large room or hall", "inside, public space", "outside, urban or manmade",
           "outside, rural or natural", "static", "white noise", "pink noise", "environmental noise", "reverberation", "echo", "music", "musical instrument"}
VOICE = {"speech", "child speech, kid speaking", "conversation", "narration, monologue", "babbling", "speech synthesizer", "shout", "bellow", "whoop",
         "yell", "children shouting", "screaming", "whispering", "laughter", "baby laughter", "giggle", "snicker", "belly laugh", "chuckle, chortle",
         "crying, sobbing", "baby cry, infant cry", "whimper", "wail, moan", "sigh", "groan", "grunt", "singing", "male singing", "female singing",
         "child singing", "male speech, man speaking", "female speech, woman speaking", "human voice", "gasp", "cough", "sneeze", "burping, eructation",
         "hiccup", "humming", "chant", "yodeling", "rapping", "choir"}

# Kinds of sound that make a good accent or transition in a video. Anything else recognised (a chewing sound, a toilet flush, a cartoon
# "boing", a phone ring) is real but not an accent, so it is never picked automatically.
ACCENT = {"whoosh, swoosh, swish", "explosion", "boom", "thump, thud", "whack, thwack", "crack", "slap, smack", "bang", "gunshot, gunfire",
          "machine gun", "artillery fire", "timpani", "bass drum", "drum", "snare drum", "cymbal", "crash cymbal", "gong", "tam-tam", "bell",
          "church bell", "chime", "ding", "ding-dong", "tubular bells", "alarm", "siren", "thunder", "thunderstorm", "breaking", "shatter", "glass",
          "whip", "arrow", "clang", "slam", "camera", "click", "beep, bleep", "buzzer", "sonar", "fire", "fireworks", "firecracker", "burst, pop",
          "crushing", "rumble", "roar", "air horn, truck horn", "foghorn", "smash, crash", "crumpling, crinkling", "scrape", "thunk", "clatter", "hiss",
          "steam whistle", "whistle", "laser", "swoosh", "impact"}

_session = None
_names: List[str] = []


class SoundAiError(Exception):
    """A message that can be shown to the person."""


def model_dir() -> str:
    return os.environ.get("SOUND_MODEL_DIR") or os.path.join("data", "models")


def _paths() -> Tuple[str, str]:
    return os.path.join(model_dir(), "yamnet.onnx"), os.path.join(model_dir(), "yamnet_class_map.csv")


def _download(url: str, dest: str) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    req = urllib.request.Request(url, headers={"User-Agent": "AIVideoPipeline-Sound/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as f:
            while True:
                block = resp.read(1 << 20)
                if not block:
                    break
                f.write(block)
        os.replace(tmp, dest)
    except OSError as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise SoundAiError(f"Không tải được mô hình nhận dạng âm thanh ({e}). Đặt file yamnet.onnx và yamnet_class_map.csv vào {model_dir()}.") from None


def available(download: bool = False) -> bool:
    """True when onnxruntime and the model are ready (download=True fetches the model when it is missing)."""
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return False
    model, classes = _paths()
    if not (os.path.exists(model) and os.path.exists(classes)):
        if not download:
            return False
        try:
            _download(MODEL_URL, model)
            _download(CLASSES_URL, classes)
        except SoundAiError:
            return False
    return True


def _load():
    global _session, _names
    if _session is None:
        if not available(download=True):
            raise SoundAiError("Chưa có mô hình nhận dạng âm thanh (cần `pip install onnxruntime` và file yamnet.onnx trong data/models).")
        import onnxruntime as ort
        model, classes = _paths()
        _session = ort.InferenceSession(model, providers=["CPUExecutionProvider"])
        with open(classes, encoding="utf-8") as f:
            _names = [r["display_name"] for r in csv.DictReader(f)]
    return _session, _names


def decode(path: str, seconds: int = LISTEN_SECONDS):
    """First `seconds` of the file as 16 kHz mono float samples (None when ffmpeg cannot read it)."""
    import numpy as np
    try:
        proc = subprocess.run([ffmpeg_studio.find_ffmpeg(), "-v", "error", "-t", str(seconds), "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                              capture_output=True, timeout=90)
    except (ffmpeg_studio.FFmpegNotFound, OSError, subprocess.TimeoutExpired):
        return None
    wave = np.frombuffer(proc.stdout, dtype=np.float32)
    return wave if len(wave) else None


def hear(path: str) -> Optional[List[Tuple[str, float]]]:
    """The classes heard in the file, strongest first: [(label, score)], generic labels removed. None when it cannot be read."""
    import numpy as np
    session, names = _load()
    wave = decode(path)
    if wave is None:
        return None
    if len(wave) < 16000:
        wave = np.pad(wave, (0, 16000 - len(wave)))
    scores = session.run(None, {session.get_inputs()[0].name: wave})[0]
    best = scores.max(axis=0) if scores.ndim == 2 else scores
    order = np.argsort(best)[::-1]
    return [(names[i], float(best[i])) for i in order[:12] if names[i].lower() not in GENERIC][:5]


def summary(heard: Optional[List[Tuple[str, float]]]) -> Dict:
    """What is stored for a sound: label (best class), score, and `voice` = "not for automatic use" (a human voice, or not an accent-type sound)."""
    if not heard:
        return {"label": "", "score": 0.0, "voice": False, "text": ""}
    label, score = heard[0]
    return {"label": label, "score": round(score, 3), "voice": label.lower() in VOICE or label.lower() not in ACCENT,
            "text": "; ".join(f"{n} {s:.2f}" for n, s in heard[:3])}
