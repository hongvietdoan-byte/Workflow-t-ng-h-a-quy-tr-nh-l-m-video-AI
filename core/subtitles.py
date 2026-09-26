"""Automatic subtitles from the script's dialogue, in the language and font the person chooses.

Where the text comes from: the dialogue lines of each scene ("LYRA: Có thứ gì đó đang theo chúng ta."), the same lines the
dialogue-length check uses. This is NOT speech recognition: when the video model speaks the lines itself, the exact moment
each word is said is not known, so timing is estimated (time inside each clip is shared out by syllable count).

Language: the script's own language, or a translation made by Claude (needs the API key).
Font: any installed / uploaded font. Default "GFF Latin Bold" (Garena's Free Fire font; Vietnamese-capable). A font that cannot
show the chosen language (e.g. GFF for Thai or Chinese) is swapped for one that can, and the person is told.
Output: an .srt file and a copy of the video with the subtitles burned in (ffmpeg + libass); the original is never changed.
"""
import glob
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Sequence, Tuple

from . import dialogue, ffmpeg_studio, final_cut, llm_runner
from .pipeline import Pipeline

LANGS = {"src": "Giữ nguyên ngôn ngữ kịch bản", "vi": "Tiếng Việt", "en": "English", "id": "Bahasa Indonesia", "th": "ไทย (Thái)",
         "pt": "Português (Brasil)", "es": "Español", "zh-tw": "中文 繁體", "zh-cn": "中文 简体", "ja": "日本語", "ko": "한국어",
         "ru": "Русский"}
# fraction of the shorter side of the picture. Measured 2026-09-26 (GFF Latin Bold, 1080×1920, ffmpeg/libass render): cap height ≈ 0,58 ×
# the size — "Vừa" was 0,065 → 40 px = 2,1 % of the height, under safe_zones.md's floor; now 0,08 → 50 px = 2,6 % (≈ 3,7 mm on a 6,1"
# phone). 3 % would need 0,092 (≈ 15 characters a line inside the safe box) — too big for two-line Vietnamese lines.
SIZES = {"S": ("Nhỏ", 0.065), "M": ("Vừa", 0.080), "L": ("Lớn", 0.095)}
POSITIONS = {"bottom": ("Dưới", 2), "middle": ("Giữa", 5), "top": ("Trên", 8)}
HUD = "__HUD__"         # speaker of an on-screen notice cue (shots' on_screen_text): drawn as a game notice at the top, not a subtitle
SAFE_BOTTOM, SAFE_TOP = 0.36, 0.15      # vertical frames: just inside Meta's official Reels safe zone (35 % bottom / 14 % top free)
# sides of a vertical frame (knowledge/editor/safe_zones.md, GĐ4): Meta keeps 6 % each side free; Google Ads' official vertical-video safe
# zone keeps 192 px of 1080 (17,8 %) free on the RIGHT — the like / comment / share column — the old 6 % put line ends under it
SAFE_LEFT, SAFE_RIGHT = 0.06, 0.18
COLORS = {"white": ("Trắng", "FFFFFF"), "yellow": ("Vàng", "FFE066")}
DEFAULT_FONT = os.environ.get("DEFAULT_SUBTITLE_FONT", "GFF Latin Bold")
DEFAULTS = {"enabled": False, "lang": "src", "font": "", "size": "M", "pos": "bottom", "color": "white", "speaker": False,
            "speaker_colors": False, "karaoke": False}
KARAOKE_WAIT = "B4B4B4"         # editing.md E7 (short-video captions): words not yet said are grey, each turns to the line's colour when said
SPEAKER_PALETTE = ("FFFFFF", "FFE066", "7FDBFF", "FFB38A", "B8F28C", "E3B5FF", "FF8FA3", "9DF2E0")
NAME_CARD_S = 1.8               # D10: how long a character's name card stays (game style, top of the safe box)
MAX_CPS = 17.0                  # characters per second a viewer can comfortably read (Netflix Timed Text Style Guide: 17 for children's
                                # programmes, 20 for adults — safe_zones.md [E23]; the same number as the auto-dialogue-generator skill)
MIN_CUE_S = 0.83                # safe_zones.md [E24]: a line stays at least 20 frames at 24 fps
MIN_GAP_S = 2 / 24              # ... and two lines are at least 2 frames apart, or the eye reads them as one flicker
_VN_TEST = "ếệỗơưăằẳẵặđĐẤỨ"

_SYSTEM_FALLBACK = ("arial.ttf", "arialbd.ttf", "tahoma.ttf", "tahomabd.ttf", "segoeui.ttf", "segoeuib.ttf", "leelawui.ttf",
                    "leelawad.ttf", "msyh.ttc", "msjh.ttc", "malgun.ttf", "yugothr.ttc", "msgothic.ttc", "seguisym.ttf")


class SubtitleError(ValueError):
    """Shown to the person as it is."""


# ---- fonts -------------------------------------------------------------------------------------------------
@dataclass
class Font:
    path: str
    family: str                 # the full name libass matches, e.g. "GFF Latin Bold"
    label: str
    vietnamese: bool
    source: str = ""
    cmap: frozenset = field(default_factory=frozenset, repr=False)
    ass_name: str = ""          # the name that made libass pick THIS file (see resolve_ass_name)
    names: tuple = ()           # candidate names to try: full name, PostScript name, family


_CACHE: Dict[Tuple[str, float], Optional[Font]] = {}


def uploads_dir() -> str:
    return os.environ.get("FONT_DIR") or os.path.join("data", "fonts")


def _read_font(path: str, source: str) -> Optional[Font]:
    try:
        stamp = (path, os.path.getmtime(path))
    except OSError:
        return None
    if stamp in _CACHE:
        return _CACHE[stamp]
    font = None
    try:
        from fontTools.ttLib import TTFont
        t = TTFont(path, fontNumber=0, lazy=True)
        names = {}
        for rec in t["name"].names:
            if rec.nameID in (1, 2, 4, 6) and rec.nameID not in names:
                try:
                    names[rec.nameID] = rec.toUnicode()
                except UnicodeError:
                    pass
        full = names.get(4) or " ".join(x for x in (names.get(1), names.get(2)) if x) or os.path.splitext(os.path.basename(path))[0]
        cmap = frozenset((t.getBestCmap() or {}).keys())
        font = Font(path, full, full, all(ord(c) in cmap for c in _VN_TEST), source, cmap, names.get(6) or names.get(1) or full,
                    tuple(dict.fromkeys(n for n in (full, names.get(6), names.get(1)) if n)))
    except Exception:  # noqa: BLE001 - a broken or unusual font file is just left out
        font = None
    _CACHE[stamp] = font
    return font


def _windows_font_dirs() -> List[str]:
    dirs = []
    if os.environ.get("WINDIR"):
        dirs.append(os.path.join(os.environ["WINDIR"], "Fonts"))
    if os.environ.get("LOCALAPPDATA"):
        dirs.append(os.path.join(os.environ["LOCALAPPDATA"], "Microsoft", "Windows", "Fonts"))
    return [d for d in dirs if os.path.isdir(d)]


def discover() -> List[Font]:
    """Fonts the person can choose: uploaded fonts, GFF fonts found on this machine, and a few safe system fonts."""
    found: Dict[str, Font] = {}
    custom = [uploads_dir()] + [d for d in os.environ.get("FONT_DIRS", "").split(os.pathsep) if d]
    for directory in custom:
        for path in sorted(glob.glob(os.path.join(directory, "**", "*"), recursive=True)):
            if path.lower().endswith((".ttf", ".otf", ".ttc")):
                f = _read_font(path, "tải lên / thư mục riêng")
                if f:
                    found.setdefault(f.family, f)
    for directory in _windows_font_dirs():
        for name in sorted(os.listdir(directory)):
            low = name.lower()
            if low.startswith("gff") or low in _SYSTEM_FALLBACK:
                f = _read_font(os.path.join(directory, name), "GFF (Free Fire)" if low.startswith("gff") else "hệ thống")
                if f:
                    found.setdefault(f.family, f)
    return sorted(found.values(), key=lambda f: (not f.family.lower().startswith("gff"), f.family.lower()))


def default_font(fonts: List[Font]) -> Optional[Font]:
    for f in fonts:
        if f.family.lower() == DEFAULT_FONT.lower() and f.vietnamese:
            return f
    return next((f for f in fonts if f.vietnamese), fonts[0] if fonts else None)


def font_by_family(fonts: List[Font], family: str) -> Optional[Font]:
    return next((f for f in fonts if f.family == family), None)


def missing_chars(font: Font, text: str) -> str:
    return "".join(sorted({c for c in text if c.isalnum() and ord(c) not in font.cmap}))


def font_for_text(preferred: Optional[Font], fonts: List[Font], text: str) -> Tuple[Optional[Font], Optional[str]]:
    """The preferred font when it can draw every letter, else the first installed font that can (with a note for the person)."""
    if preferred is not None and not missing_chars(preferred, text):
        return preferred, None
    for f in fonts:
        if not missing_chars(f, text):
            note = (f"Font “{preferred.family}” không có một số chữ của ngôn ngữ này ({missing_chars(preferred, text)[:12]}…): dùng “{f.family}”."
                    if preferred else f"Dùng font “{f.family}”.")
            return f, note
    return preferred, "Không có font nào trên máy hiển thị đủ chữ của ngôn ngữ này: hãy tải một font hỗ trợ (ví dụ Noto Sans)."


def save_uploaded_font(filename: str, data: bytes) -> Font:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in (".ttf", ".otf"):
        raise SubtitleError("Chỉ nhận font .ttf hoặc .otf")
    if not data or len(data) > 30 * 1024 * 1024:
        raise SubtitleError("File font rỗng hoặc lớn hơn 30 MB")
    os.makedirs(uploads_dir(), exist_ok=True)
    path = os.path.join(uploads_dir(), re.sub(r"[^\w.\- ]", "_", os.path.basename(filename)))
    with open(path, "wb") as f:
        f.write(data)
    font = _read_font(path, "tải lên")
    if font is None:
        os.remove(path)
        raise SubtitleError("Không đọc được file font này")
    return font


# ---- settings per project ---------------------------------------------------------------------------------------
def get_settings(pipeline: Pipeline, project_id: int) -> Dict:
    row = pipeline.project(project_id)
    try:
        saved = json.loads((row["sub_settings"] if "sub_settings" in row.keys() else None) or "{}")
    except ValueError:
        saved = {}
    return {**DEFAULTS, **{k: v for k, v in saved.items() if k in DEFAULTS}}


def save_settings(pipeline: Pipeline, project_id: int, settings: Dict) -> None:
    clean = {k: settings.get(k, DEFAULTS[k]) for k in DEFAULTS}
    pipeline.conn.execute("UPDATE projects SET sub_settings=? WHERE id=?", (json.dumps(clean, ensure_ascii=False), project_id))
    pipeline.conn.commit()


# ---- cues ---------------------------------------------------------------------------------------------------------
@dataclass
class Cue:
    start: float
    end: float
    text: str
    speaker: str = ""
    scene: Optional[int] = None


def build_cues(pipeline: Pipeline, data_dir: str, project_id: int, transition: str = "cut", fade: float = 1.0,
               timeline: Optional[List[Dict]] = None) -> List[Cue]:
    """One cue per dialogue line, timed inside its clip on the final video's timeline.
    D2: `timeline` = the clips of the render as it was made ([{"idx", "seconds"}], chosen clips + edited seconds, from the final
    render's manifest); without it, the clips a default render would use (usable ones only, like the render)."""
    if timeline is None:
        timeline = [{"idx": c["idx"], "seconds": final_cut.clip_seconds(c["path"], c["requested_sec"])}
                    for c in final_cut.collect_clips_for_render(pipeline.conn, data_dir, project_id)]
    datas = {r["idx"]: json.loads(r["data"] or "{}") for r in
             pipeline.conn.execute("SELECT idx, data FROM scenes WHERE project_id=?", (project_id,))}
    overlap = fade if transition in ffmpeg_studio.OVERLAP_STYLES else 0.0
    cues: List[Cue] = []
    hud: List[Cue] = []
    t = 0.0
    from . import features
    named = set() if features.on("name_cards") else None     # D10 (editing.md E6): a name card the first time someone is seen
    for clip in timeline:
        length = float(clip["seconds"])
        if named is not None and clip.get("idx") is not None:
            for who in datas.get(clip["idx"], {}).get("characters") or []:
                if who not in named and str(who).strip():
                    named.add(who)
                    hud.append(Cue(round(t + 0.2, 2), round(t + min(max(length - 0.1, 1.0), NAME_CARD_S), 2), str(who).strip().upper(),
                                   HUD, clip["idx"]))
        for text in (datas.get(clip["idx"], {}).get("on_screen_text") or []) if clip.get("idx") is not None else []:
            if str(text).strip():                         # a game notice / system text is shown, never voiced (kịch bản "ANH CHỌN AI?")
                hud.append(Cue(round(t + 0.1, 2), round(t + max(length - 0.1, 1.0), 2), str(text).strip(), HUD, clip["idx"]))
        rows = dialogue.scene_lines(datas.get(clip["idx"], {})) if clip.get("idx") is not None else []
        if rows:
            lead, tail = min(0.3, length * 0.08), 0.25
            avail = max(length - lead - tail, 0.6)
            weights = [max(dialogue.syllables(said), 1) for _, said in rows]
            floor = min(0.8, avail / len(rows))
            spare = max(avail - floor * len(rows), 0.0)
            cursor = t + lead
            for (who, said), w in zip(rows, weights):
                span = floor + spare * w / sum(weights)
                cues.append(Cue(round(cursor, 2), round(cursor + span - 0.05, 2), said, who, clip["idx"]))
                cursor += span
        t += length - overlap
    from . import voice                                   # voiced lines carry their real timing: use it for those scenes
    spoken = voice.cues(pipeline.conn, project_id, data_dir)
    if spoken:
        voiced = {c.scene for c in spoken}
        cues = [c for c in cues if c.scene not in voiced] + spoken
    return sorted(cues + hud, key=lambda c: c.start)


def wrap_text(text: str, max_chars: int) -> str:
    """Break a long line into at most three balanced lines at spaces."""
    words = text.split()
    if len(text) <= max_chars or len(words) < 2:
        return text
    parts = min(3, math.ceil(len(text) / max_chars))
    target = len(text) / parts
    lines, cur = [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > target * 1.15 and len(lines) < parts - 1:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    return "\n".join(lines)


def _clock(seconds: float, sep: str) -> str:
    ms = int(round(max(seconds, 0) * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}{sep}{ms % 1000:03d}"


def to_srt(cues: List[Cue], show_speaker: bool = False) -> str:
    out = []
    for i, c in enumerate(cues, 1):
        text = f"{c.speaker.title()}: {c.text}" if show_speaker and c.speaker and c.speaker != HUD else c.text
        out.append(f"{i}\n{_clock(c.start, ',')} --> {_clock(c.end, ',')}\n{text}\n")
    return "\n".join(out)


def speaker_colors(cues: List[Cue]) -> Dict[str, str]:
    """One colour per speaker, in order of first appearance (auto-dialogue-generator skill: each character keeps a colour)."""
    out: Dict[str, str] = {}
    for c in cues:
        if c.speaker and c.speaker != HUD and c.speaker not in out:
            out[c.speaker] = SPEAKER_PALETTE[len(out) % len(SPEAKER_PALETTE)]
    return out


def density(cues: List[Cue], cuts: Sequence[float] = ()) -> List[Dict]:
    """Lines a viewer cannot read (safe_zones.md rule 5): more than MAX_CPS characters per second, on screen less than MIN_CUE_S,
    overlapping the next line or closer to it than MIN_GAP_S, or — given the render's cut times — running across a cut by more than
    half a second on each side (the line then reads as belonging to the wrong shot; a J-cut's early start is under that). Game
    notices sit apart and are not counted."""
    cues = [c for c in cues if c.speaker != HUD]
    out = []
    for i, c in enumerate(cues):
        span = max(c.end - c.start, 0.01)
        cps = len(c.text) / span
        nxt = cues[i + 1] if i + 1 < len(cues) else None
        overlap = bool(nxt and nxt.start < c.end - 1e-6)
        close = bool(nxt and not overlap and nxt.start - c.end < MIN_GAP_S - 1e-6)
        brief = span < MIN_CUE_S - 1e-6
        across = next((t for t in cuts if c.start + 0.5 < t < c.end - 0.5), None)
        if cps > MAX_CPS or overlap or close or brief or across is not None:
            out.append({"i": i, "scene": c.scene, "text": c.text, "cps": round(cps, 1), "overlap": overlap, "close": close,
                        "brief": brief, "across_cut": across})
    return out


def to_xlsx(cues: List[Cue]) -> bytes:
    """Review sheet (scene, speaker, start, end, text, chars/second, ⚠) to check or edit the lines before burning them in."""
    import io
    from openpyxl import Workbook
    flagged = {d["i"] for d in density(cues)}
    wb = Workbook()
    ws = wb.active
    ws.title = "Phụ đề"
    ws.append(["Cảnh", "Người nói", "Bắt đầu (s)", "Kết thúc (s)", "Nội dung", "Ký tự/giây", "Cần xem"])
    for i, c in enumerate(cues):
        cps = round(len(c.text) / max(c.end - c.start, 0.01), 1)
        ws.append([c.scene, c.speaker, c.start, c.end, c.text, cps, "⚠" if i in flagged else ""])
    for col, width in zip("ABCDEFG", (7, 16, 11, 11, 70, 11, 9)):
        ws.column_dimensions[col].width = width
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def karaoke_text(text: str, seconds: float) -> str:
    """ASS karaoke of one line (already wrapped, \\N between rows): each word gets {\\kf N} centiseconds in proportion to its letters,
    over 90 % of the line's time (the voice ends a little before the subtitle does)."""
    parts = re.split(r"(\\N| )", text)
    words = [p for p in parts if p not in ("\\N", " ", "")]
    letters = sum(len(w) for w in words) or 1
    budget = max(int(seconds * 90), len(words))
    out = []
    for p in parts:
        if p in ("\\N", " ", ""):
            out.append(p)
        else:
            out.append(f"{{\\kf{max(int(budget * len(p) / letters), 1)}}}{p}")
    return "".join(out)


def to_ass(cues: List[Cue], width: int, height: int, font: Font, size: str = "M", pos: str = "bottom", color: str = "white",
           show_speaker: bool = False, by_speaker: bool = False, margin_pct: Optional[float] = None,
           zones: Optional[Dict[int, Tuple[float, float]]] = None, seen: Optional[Dict[int, Tuple[float, float]]] = None,
           karaoke: bool = False) -> str:
    """zones: scene idx -> (top, bottom) of the face area a subtitle must not cover (core/text_placement.py); a bottom subtitle of
    such a shot moves, whole line, to the top of the safe box."""
    short = min(width, height)
    fontsize = max(int(short * SIZES.get(size, SIZES["M"])[1]), 14)
    align = POSITIONS.get(pos, POSITIONS["bottom"])[1]
    if margin_pct is not None:
        margin_v = int(height * margin_pct / 100)
    elif height > width:
        # vertical video is watched inside an app: Meta's Reels guide keeps the bottom 35 % and top 14 % free of text (captions, buttons,
        # tabs cover them; knowledge/editor/safe_zones.md) — the old 12 % put every subtitle under the app's caption bar
        margin_v = int(height * (SAFE_BOTTOM if align == 2 else SAFE_TOP))
    else:
        margin_v = int(height * 0.08) if align == 2 else int(height * 0.06)
    rgb = COLORS.get(color, COLORS["white"])[1]
    bgr = rgb[4:6] + rgb[2:4] + rgb[0:2]
    outline = max(int(fontsize * 0.07), 2)
    ml, mr = (int(width * SAFE_LEFT), int(width * SAFE_RIGHT)) if height > width else (int(width * 0.06), int(width * 0.06))
    max_chars = max(int((width - ml - mr) / (fontsize * 0.55)), 12)
    lines = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {width}", f"PlayResY: {height}", "WrapStyle: 0", "",
             "[V4+ Styles]",
             "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
             "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
             f"Style: Default,{font.ass_name or font.family},{fontsize},&H00{bgr},&H00{_bgr(KARAOKE_WAIT) if karaoke else bgr},"
             f"&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,{outline},1,"
             f"{align},{ml},{mr},{margin_v},1"]
    palette = speaker_colors(cues) if by_speaker else {}
    style_of = {}
    for n, (who, hexrgb) in enumerate(palette.items(), 1):
        c_bgr = hexrgb[4:6] + hexrgb[2:4] + hexrgb[0:2]
        style_of[who] = f"S{n}"
        lines.append(f"Style: S{n},{font.ass_name or font.family},{fontsize},&H00{c_bgr},&H00{_bgr(KARAOKE_WAIT) if karaoke else c_bgr},"
                     "&H00000000,&H80000000,0,0,0,0,"
                     f"100,100,0,0,1,{outline},1,{align},{ml},{mr},{margin_v},1")
    if any(c.speaker == HUD for c in cues):
        # a game notice (knowledge/editor/safe_zones.md: game-notice style at the top of the safe zone, unlike a subtitle): smaller,
        # yellow on a dark box, centred just inside the top safe margin
        hud_size = max(int(fontsize * 0.8), 12)
        hud_margin = int(height * SAFE_TOP) if height > width else int(height * 0.06)
        lines.append(f"Style: Hud,{font.ass_name or font.family},{hud_size},&H0000D7FF,&H0000D7FF,&H00000000,&HA0000000,1,0,0,0,"
                     f"100,100,0,0,3,{max(int(hud_size * 0.25), 3)},0,8,{ml},{mr},{hud_margin},1")
        style_of[HUD] = "Hud"
    lines += ["", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    moved = {}
    if (zones or seen) and align == 2 and height > width and margin_pct is None:
        from . import text_placement
        said = lambda c: f"{c.speaker.title()}: {c.text}" if show_speaker and c.speaker and c.speaker != HUD else c.text  # noqa: E731
        spoken = [c for c in cues if c.speaker != HUD]
        index = {id(c): i for i, c in enumerate(cues)}
        seen_spoken = {j: seen[index[id(c)]] for j, c in enumerate(spoken) if seen and index[id(c)] in seen}
        where = text_placement.placements(spoken, zones or {}, height, fontsize, lambda c: wrap_text(said(c), max_chars).count("\n") + 1,
                                          SAFE_BOTTOM, SAFE_TOP, seen=seen_spoken)
        moved = {id(spoken[i]) for i in where}
    for c in cues:
        text = f"{c.speaker.title()}: {c.text}" if show_speaker and c.speaker and c.speaker != HUD else c.text
        text = wrap_text(text, max_chars).replace("{", "(").replace("}", ")").replace("\n", "\\N")
        if karaoke and c.speaker != HUD:
            text = karaoke_text(text, c.end - c.start)
        style = style_of.get(c.speaker, "Default")
        margin = 0
        if id(c) in moved:                  # a face in the bottom band: this line goes to the top of the safe box
            text, margin = "{\\an8}" + text, int(height * SAFE_TOP)
        lines.append(f"Dialogue: 0,{_clock(c.start, '.')[:-1]},{_clock(c.end, '.')[:-1]},{style},,0,0,{margin},,{text}")
    return "\n".join(lines) + "\n"


def _bgr(rgb: str) -> str:
    return rgb[4:6] + rgb[2:4] + rgb[0:2]


def _uuencode(data: bytes) -> str:
    """The ASS flavour of uuencode used by the [Fonts] section (6 bits per character, offset 33, lines of 80)."""
    out = []
    for i in range(0, len(data), 3):
        chunk = data[i:i + 3]
        n = len(chunk)
        b = chunk + bytes(3 - n)
        v = (b[0] << 16) | (b[1] << 8) | b[2]
        out.append("".join(chr(33 + c) for c in [(v >> 18) & 63, (v >> 12) & 63, (v >> 6) & 63, v & 63][:n + 1]))
    text = "".join(out)
    return "\n".join(text[i:i + 80] for i in range(0, len(text), 80))


EMBED_MAX_BYTES = 8 * 1024 * 1024


def embed_font(font: Font) -> str:
    """[Fonts] section that carries the chosen font inside the subtitle file, so libass uses exactly that file (a font name
    alone is looked up among system fonts and silently falls back to Arial when the style is not a plain Bold/Regular).
    Very large fonts (CJK collections) are left to the system lookup."""
    ext = os.path.splitext(font.path)[1].lower()
    if ext not in (".ttf", ".otf") or os.path.getsize(font.path) > EMBED_MAX_BYTES:
        return ""
    with open(font.path, "rb") as f:
        return "\n[Fonts]\nfontname: font_0" + ext + "\n" + _uuencode(f.read()) + "\n"


_NAME_CACHE: Dict[Tuple[str, float], str] = {}


def _selected_by_libass(ass_text: str) -> str:
    """PostScript name of the face libass really used for this subtitle file ('' when unknown)."""
    work = tempfile.mkdtemp()
    try:
        with open(os.path.join(work, "t.ass"), "w", encoding="utf-8") as f:
            f.write(ass_text)
        proc = subprocess.run([ffmpeg_studio.find_ffmpeg(), "-v", "verbose", "-y", "-f", "lavfi", "-i", "color=c=black:s=640x360:d=0.5",
                               "-vf", "ass=t.ass", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=work)
        for line in (proc.stderr or "").splitlines():
            if "fontselect" in line.lower() and "->" in line:
                return line.split("->")[-1].split(",")[0].strip()
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return ""


def resolve_ass_name(font: Font) -> Tuple[str, bool]:
    """The font name to write in the subtitle file so libass draws with exactly this font. libass matches names differently
    for .otf and .ttf files, so each candidate name is tried once (cached) and the one that selects this file is kept.
    Returns (name, verified)."""
    key = (font.path, os.path.getmtime(font.path))
    if key in _NAME_CACHE:
        return _NAME_CACHE[key], True
    want = re.sub(r"[^a-z0-9]", "", (font.names[1] if len(font.names) > 1 else font.ass_name).lower())
    for cand in font.names or (font.ass_name,):
        trial = to_ass([Cue(0, 0.4, "Xin chao", "", 1)], 640, 360, replace(font, ass_name=cand)) + embed_font(font)
        got = re.sub(r"[^a-z0-9]", "", _selected_by_libass(trial).lower())
        if got and got == want:
            _NAME_CACHE[key] = cand
            return cand, True
    return font.ass_name or font.family, False


# ---- translation --------------------------------------------------------------------------------------------------
def translate(client, cues: List[Cue], lang: str) -> List[Cue]:
    """Same cues and timing, text translated by Claude. `lang` is a key of LANGS (not 'src')."""
    if lang == "src" or not cues:
        return cues
    if client is None:
        raise SubtitleError("Dịch phụ đề cần Claude API (ANTHROPIC_API_KEY).")
    label = LANGS.get(lang, lang)
    out: List[Cue] = []
    for i in range(0, len(cues), 40):
        chunk = cues[i:i + 40]
        payload = [{"id": n, "speaker": c.speaker, "text": c.text} for n, c in enumerate(chunk, 1)]
        prompt = ("Dịch phụ đề cho video game. Dịch các câu thoại sau sang " + label + ". Giữ nguyên tên nhân vật, tên kỹ năng và thuật ngữ "
                  "game; giọng tự nhiên như người bản xứ nói; ngắn gọn, không dài hơn câu gốc quá 25% vì phải vừa màn hình; "
                  "không thêm ý. Trả về **một JSON duy nhất**: {\"cues\": [{\"id\": 1, \"text\": \"...\"}]} đủ và đúng thứ tự id.\n\n"
                  "# Phụ đề cần dịch\n```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```")

        def validate(obj, n=len(chunk)):
            if not isinstance(obj, dict) or not isinstance(obj.get("cues"), list) or len(obj["cues"]) != n:
                raise ValueError(f"cần đúng {n} câu dịch")
            if any(not str(x.get("text", "")).strip() for x in obj["cues"]):
                raise ValueError("có câu dịch trống")

        with llm_runner.tagged("subtitles"):
            obj, _, _ = llm_runner.ask_json(client, prompt, validate)
        by_id = {int(x["id"]): str(x["text"]).strip() for x in obj["cues"]}
        for n, c in enumerate(chunk, 1):
            out.append(Cue(c.start, c.end, by_id.get(n, c.text), c.speaker, c.scene))
    return out


# ---- saved translations + hand fixes (D8) ----------------------------------------------------------------------------
def _store_path(data_dir: str, project_id: int) -> str:
    return os.path.join(data_dir, str(project_id), "subtitles", "texts.json")


def _key(lang: str, cue: Cue) -> str:
    return f"{lang}\x1f{cue.speaker or ''}\x1f{cue.text}"


def load_texts(data_dir: str, project_id: int) -> Dict[str, Dict]:
    """{key: {"text", "manual"}} — a line's shown text per language: Claude's translation, or the person's own fix (manual)."""
    try:
        with open(_store_path(data_dir, project_id), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_texts(data_dir: str, project_id: int, store: Dict[str, Dict]) -> None:
    path = _store_path(data_dir, project_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def localize(client, cues: List[Cue], lang: str, data_dir: str, project_id: int) -> List[Cue]:
    """D8: the cues as they should be shown — the person's fixes first, then translations made before; Claude translates only
    lines never translated (a changed line counts as new). Same timing as `cues`."""
    store = load_texts(data_dir, project_id)
    shown: List[Optional[str]] = [(store.get(_key(lang, c)) or {}).get("text") for c in cues]
    missing = [c for c, t in zip(cues, shown) if t is None]
    if lang != "src" and missing:
        done = translate(client, missing, lang)
        for c, t in zip(missing, done):
            store[_key(lang, c)] = {"text": t.text, "manual": False}
        _save_texts(data_dir, project_id, store)
    return [replace(c, text=(store.get(_key(lang, c)) or {}).get("text") or c.text) for c in cues]


def remember_edits(data_dir: str, project_id: int, lang: str, pairs: List[Tuple[Cue, str]]) -> int:
    """Keep hand fixes (source cue, text shown) so the next subtitles (Step 5 again, automatic run, other formats) reuse them
    instead of a new translation. Returns how many changed."""
    store = load_texts(data_dir, project_id)
    changed = 0
    for src, text in pairs:
        text = (text or "").strip()
        key = _key(lang, src)
        now = (store.get(key) or {}).get("text") or src.text
        if text and text != now:
            store[key] = {"text": text, "manual": True}
            changed += 1
    if changed:
        _save_texts(data_dir, project_id, store)
    return changed


# ---- burn into the video --------------------------------------------------------------------------------------------
def probe_size(path: str) -> Tuple[int, int]:
    proc = subprocess.run([ffmpeg_studio.find_ffmpeg(), "-hide_banner", "-i", path], capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (proc.stderr or "").splitlines():
        if "Video:" in line:
            m = re.search(r",\s*(\d{2,5})x(\d{2,5})[\s,\[]", line)
            if m:
                return int(m.group(1)), int(m.group(2))
    raise SubtitleError("Không đọc được kích thước video")


def burn(video: str, cues: List[Cue], out_path: str, font: Font, size: str = "M", pos: str = "bottom", color: str = "white",
         show_speaker: bool = False, by_speaker: bool = False, zones: Optional[Dict[int, Tuple[float, float]]] = None,
         karaoke: bool = False) -> Dict:
    """Write <out>.srt and a copy of `video` with the subtitles drawn in. Returns {'video', 'srt', 'cues'}."""
    if not cues:
        raise SubtitleError("Chưa có dòng phụ đề nào (kịch bản cần có dòng thoại dạng “TÊN: lời”).")
    if font is None:
        raise SubtitleError("Chưa có font để in phụ đề.")
    width, height = probe_size(video)
    ffmpeg = ffmpeg_studio.find_ffmpeg()
    name, verified = resolve_ass_name(font)
    font = replace(font, ass_name=name)
    srt_path = os.path.splitext(out_path)[0] + ".srt"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(to_srt(cues, show_speaker))
    work = tempfile.mkdtemp()
    try:
        # ffmpeg runs inside this folder so the filter needs no drive-letter escaping on Windows
        with open(os.path.join(work, "sub.ass"), "w", encoding="utf-8") as f:
            seen = {}
            if height > width and pos == "bottom":            # faces on the real frames of each line (YuNet, when installed)
                from . import text_placement
                seen = text_placement.video_spans(os.path.abspath(video), cues, ffmpeg)
            f.write(to_ass(cues, width, height, font, size, pos, color, show_speaker, by_speaker, zones=zones, seen=seen,
                           karaoke=karaoke)
                    + embed_font(font))
        cmd = [ffmpeg, "-y", "-i", os.path.abspath(video), "-vf", "ass=sub.ass", "-c:v", "libx264", "-crf", "18",
               "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "copy", os.path.abspath(out_path)]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=work)
        if proc.returncode != 0:
            tail = (proc.stderr or "")[-600:]
            if "No such filter" in tail:
                raise SubtitleError("Bản ffmpeg này không có bộ vẽ phụ đề (libass). Cài bản “full” (vd Gyan.FFmpeg).")
            raise ffmpeg_studio.FFmpegError(tail)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return {"video": out_path, "srt": srt_path, "cues": len(cues), "font": font.family, "font_verified": verified}
