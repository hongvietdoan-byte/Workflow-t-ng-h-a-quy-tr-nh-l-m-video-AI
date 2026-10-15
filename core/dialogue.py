"""Does the dialogue of a scene fit into its clip?

Lines like "LYRA: Có thứ gì đó đang theo chúng ta." are taken from the scene text. A clip that is shorter than the
time needed to say them gets a cut-off or rushed line, and the credit for that clip is wasted. No model is called:
speaking time is estimated from the number of syllables (Vietnamese: about one word per syllable).

  ok      fits with a little room
  tight   fits, barely
  extend  too long for the planned duration but the model can make a longer clip -> raise the duration
  split   too long even for the model's longest clip -> the scene has to be split (or the lines shortened)
"""
import json
import math
import os
import re
from typing import Dict, List, Optional, Tuple

RATE = float(os.environ.get("DIALOGUE_SYLLABLES_PER_SEC", "3.5"))     # comfortable speaking speed
BREATH = 0.5                                                          # seconds of room around the lines
DEFAULT_PLANNED = 5.0
_LINE = re.compile(r"^\s*([^:\n]{1,30}?)\s*:\s*(.+?)\s*$")


NOT_SPEAKERS = {"TEXT CUỐI", "CARD CUỐI", "CHỮ CUỐI", "END CARD", "GHI CHÚ", "LƯU Ý", "THỜI LƯỢNG", "NHÂN VẬT", "BỐI CẢNH",
                "ĐỊA ĐIỂM", "THỜI GIAN", "GÓC MÁY", "MÔ TẢ", "KỊCH BẢN", "NOTE", "CAMERA",
                "HỆ THỐNG", "SYSTEM", "THÔNG BÁO", "HUD", "CẤU TRÚC", "FLASHBACK", "FLASHBACK NGẮN",   # on-screen text, not a voice
                "TEXT", "CHỮ", "CAPTION", "ON-SCREEN TEXT", "ON SCREEN TEXT",
                # S14.4 C1b (04/10): text cards of a short ad are not a voice either (one list for every reader)
                "CTA", "CTA TEXT", "CTA_TEXT", "TITLE", "SUPER", "SUBTITLE", "LOGO", "CHỮ TRÊN MÀN", "CHỮ MÀN HÌNH",
                "CHỮ TRÊN MÀN HÌNH", "TIÊU ĐỀ", "PHỤ ĐỀ",
                # S14.34: scene-description labels the Biên kịch writes (not a voice)
                "HẬU KỲ", "ĐIỂM XOAY", "HOOK"}
# Names that only mean "on-screen text" WITH their accents: 'CHỮ' folds to 'chu', which is also a person's name (Chu).
_ACCENT_ONLY = {"chu"}


def _fold(text: str) -> str:
    """'Chữ trên màn' -> 'chu tren man'; 'CTA_TEXT' / 'CTA-TEXT' -> 'cta text' (same words, no accents, no case)."""
    import unicodedata
    text = unicodedata.normalize("NFD", (text or "").replace("đ", "d").replace("Đ", "D"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[\W_]+", " ", text.lower())).strip()


_NOT_SPEAKERS_FOLDED = {_fold(n) for n in NOT_SPEAKERS} - _ACCENT_ONLY


def is_non_speaker(name: str) -> bool:
    """True for a heading / on-screen text label ('CTA_TEXT', 'Chữ trên màn', 'TITLE'), compared without accents — except
    the words in `_ACCENT_ONLY`, matched with their accents only so a character named 'CHU' still speaks."""
    raw = re.sub(r"\s+", " ", str(name or "")).strip()
    return raw.upper() in NOT_SPEAKERS or _fold(raw) in _NOT_SPEAKERS_FOLDED


def _is_speaker(name: str) -> bool:
    """'KELLY' (capitals, the usual script style) or 'Kelly' / 'Ông Lão Orin' (every word capitalised, at most 3 words) — not a
    heading such as 'Ghi chú' or 'TEXT CUỐI'."""
    if not name or not any(ch.isalpha() for ch in name) or is_non_speaker(name):
        return False
    if name == name.upper():
        return True
    words = name.split()
    return len(words) <= 3 and all(w[0].isupper() for w in words if w)


def lines(text: str) -> List[Tuple[str, str]]:
    """(speaker, line) for every 'NAME: words' row. Speakers written in capitals ('KELLY:') or capitalised ('Kelly:');
    the speaker is returned in capitals so it matches the Character Bible."""
    out = []
    for row in (text or "").splitlines():
        m = _LINE.match(row)
        if not m:
            continue
        name, said = m.group(1).strip(), m.group(2).strip().strip('"“”')
        name = re.sub(r"\s*\(.*?\)\s*", "", name).strip()
        if _is_speaker(name) and said:
            out.append((name.upper(), said))
    return out


def scene_lines(scene_data: Dict) -> List[Tuple[str, str]]:
    """The scene's dialogue: the Director's structured `dialogue` list when there is one (v2), else the 'NAME: words' rows of
    the script text. Used by the length check, subtitles, voice-over and the motion prompt hint alike."""
    structured = scene_data.get("dialogue")
    if scene_data.get("shot_no") and not structured:
        return []            # v3 shot row: its lines are exactly `dialogue` (an action line must never be read as speech)
    if isinstance(structured, list) and structured:
        return [(str(d.get("speaker") or "").strip(), str(d.get("text") or "").strip()) for d in structured
                if isinstance(d, dict) and str(d.get("text") or "").strip()]
    return lines(scene_data.get("text", ""))


def norm(text: str) -> str:
    """A line compared as words only: quotes, case and spacing do not matter (the Director's copy vs the script's)."""
    return " ".join(re.sub(r"[\"“”'‘’«»]", "", str(text or "")).lower().split())


def syllables(said: str) -> int:
    return len(re.findall(r"\w+", said, re.UNICODE))


# ---- 15/10: giây đọc theo (giọng, tốc độ) — MỘT chỗ cho mọi nơi ước giây (Đạo diễn, chuẩn hoá shot, báo cáo, nhịp nhanh, motion) ----
# Số đo thật (tools/measure_speech_rate.py --write → data/speech_rates.json): theo giọng = âm tiết/giây TRUNG VỊ (p50) đo trên GIÂY NÓI
# (đã cắt lặng đầu/cuối — phần lặng là BREATH, không đếm hai lần), sàn RATE_FLOOR × RATE. Rà vòng gop-1510 (15/10, mục 1 CAO — tiền):
# trước đây p10 trên độ dài cả FILE + BREATH → giọng 70 câu 23 âm tiết ước 14,4 s (thật ~8 s), shot dài ra = tiền gen. Kiểm bằng mẫu đo
# thật tests/fixtures/speech_samples_1510.json: mỗi giọng đủ mẫu trung vị (ước − file thật) ≤ +0,5 s;
# "speed_follows": model nào thật sự đọc nhanh/chậm theo speed gửi đi — chưa đo được thì hệ số tốc độ = 1 (ước như tốc độ 1,0).
LINE_GAP = 0.15            # giữa hai câu liền nhau trong một shot = voice.GAP (khâu dựng đặt câu y như vậy); nhịp nhanh: pacing.FAST_LINE_GAP
_RATES_FILE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "speech_rates.json"))
_RATES_CACHE: Dict = {}
RATES_DEFAULT: Dict = {"min_n": 8, "voices": {}, "speed_follows": {}}   # = công thức cũ (RATE, tốc độ không đổi ước tính)
RATE_FLOOR = 0.8          # tốc độ giọng dùng để ước không chậm hơn 0,8 × RATE (một bảng lệch / ít câu dài không làm phình giây)


def _rates() -> Dict:
    """data/speech_rates.json (đọc một lần, theo gốc dự án — không theo thư mục đang chạy). Thiếu / hỏng → RATES_DEFAULT và lý do
    nằm ở _RATES_CACHE["problem"] — speech_ctx ghi diag VÀNG (luật 1: không im lặng khi thiếu đầu vào)."""
    if "v" not in _RATES_CACHE:
        try:
            with open(_RATES_FILE, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("không phải bảng JSON")
            _RATES_CACHE["v"] = data
        except OSError as e:
            _RATES_CACHE["v"], _RATES_CACHE["problem"] = dict(RATES_DEFAULT), f"thiếu {_RATES_FILE} ({e.__class__.__name__})"
        except ValueError as e:
            _RATES_CACHE["v"], _RATES_CACHE["problem"] = dict(RATES_DEFAULT), f"{_RATES_FILE} hỏng ({e})"
    return _RATES_CACHE["v"]


def _say_rates_problem(conn, project_id: int) -> None:
    """Bảng tốc độ giọng thiếu / hỏng → diag VÀNG cho dự án đang ước giây (diag gộp lặp trong 10 phút)."""
    _rates()
    why = _RATES_CACHE.get("problem")
    if why:
        from . import diag
        diag.record(conn, "director", "warn", f"bảng tốc độ giọng: {why} — ước giây đọc theo công thức mặc định (÷ {RATE:g} âm "
                    "tiết/giây, tốc độ không đổi ước tính); chạy tools/measure_speech_rate.py --write data/speech_rates.json",
                    code="speech_rates_missing", project_id=project_id)


def voice_rate(voice_id=None) -> float:
    """Âm tiết/giây dùng để ƯỚC cho giọng này: max(p50 đo trên giây nói, RATE_FLOOR × RATE) khi giọng có ≥ min_n câu đo, else RATE.
    Giọng đọc nhanh hơn RATE được ước ngắn hơn (đo thật: trung vị lệch ≤ +0,5 s nhờ BREATH); bảng thiếu p50 → RATE."""
    table = _rates()
    v = (table.get("voices") or {}).get(str(voice_id)) if voice_id is not None else None
    try:
        if v and int(v.get("n") or 0) >= int(table.get("min_n") or 8) and float(v.get("p50") or 0) > 0:
            return max(float(v["p50"]), RATE_FLOOR * RATE)
    except (TypeError, ValueError):
        pass
    return RATE


def speed_factor(model: Optional[str], speed) -> float:
    """Hệ số tốc độ của ước tính: = speed chỉ khi model ĐÃ ĐO là đọc theo speed (data/speech_rates.json speed_follows), else 1,0.
    Model trống = model mặc định của voice (eleven_v3)."""
    try:
        sp = float(speed) if speed not in (None, "") else 1.0
    except (TypeError, ValueError):
        return 1.0
    if sp <= 0 or sp == 1.0:
        return 1.0
    follows = (_rates().get("speed_follows") or {}).get(model or "eleven_v3")
    return sp if follows is True else 1.0


def line_seconds(said: str, voice: Optional[Dict] = None) -> float:
    """Giây ĐỌC một câu (không gồm nghỉ): âm tiết (pacing.syllables — số đọc thành chữ) ÷ (tốc độ của giọng × hệ số tốc độ).
    voice = {voice_id, model, speed} (hồ sơ giọng / speech_ctx); None = RATE, tốc độ 1,0."""
    from .pacing import syllables as _syl
    n = _syl(said)
    if not n:
        return 0.0
    v = voice or {}
    return n / (voice_rate(v.get("voice_id")) * speed_factor(v.get("model"), v.get("speed")))


def _key(name) -> str:
    return " ".join(str(name or "").upper().split())


def voice_of(ctx: Optional[Dict], speaker) -> Optional[Dict]:
    """Giọng của người nói trong ctx (speech_ctx): hồ sơ giọng của nhân vật; người dẫn chưa có hồ sơ → tốc độ lời dẫn của dự án."""
    if not ctx:
        return None
    hit = (ctx.get("voices") or {}).get(_key(speaker))
    if hit is not None:
        return hit
    if ctx.get("narration_speed"):
        from .speaker_lint import is_narrator
        if is_narrator(str(speaker or "")):
            return {"speed": ctx["narration_speed"]}
    return None


def speech_ctx(conn, project_id: int) -> Dict:
    """Những gì ước giây cần biết về dự án: giọng từng người nói (hồ sơ Bible: voice_id, model, tốc độ = riêng × biến thể), tốc độ lời
    dẫn của dự án (projects.narration_speed, khi Bible chưa có) và khoảng giữa hai câu (nhịp nhanh 0,2 s, thường 0,15 s)."""
    from . import pacing, voice
    voices = {}
    try:
        for name, prof in voice.profiles(conn, project_id).items():
            sp = pacing.voice_speed(prof)
            voices[_key(name)] = {"voice_id": prof.get("voice_id"), "model": voice.vi_model(prof.get("model")),
                                  "speed": None if sp == 1.0 else sp}
    except Exception:  # noqa: BLE001 - an old database without characters / profiles: no voices, the old estimate
        voices = {}
    narration = None
    try:
        row = conn.execute("SELECT narration_speed FROM projects WHERE id=?", (project_id,)).fetchone()
        narration = voice.clamp_speed(row["narration_speed"])[0] if row is not None and row["narration_speed"] is not None else None
    except Exception:  # noqa: BLE001 - before the column
        narration = None
    fast = pacing.project_fast(conn, project_id)
    _say_rates_problem(conn, project_id)
    return {"voices": voices, "narration_speed": narration, "gap": pacing.FAST_LINE_GAP if fast else LINE_GAP}


def needed_seconds(rows: List[Tuple[str, str]], ctx: Optional[Dict] = None, gap: Optional[float] = None) -> float:
    """Giây một shot cần cho các câu của nó: giây đọc từng câu (line_seconds theo giọng/tốc độ) + BREATH một lần cho shot + khoảng
    thật giữa hai câu liền nhau — trong MỘT clip khâu dựng đặt câu sau cách câu trước voice.GAP (= LINE_GAP, cả nhịp nhanh:
    voice.layout `cursor += dài + GAP`). gap: scene_seconds truyền khoảng của dự án (câu của một lượt có thể sang shot sau)."""
    by_rate: Dict[float, int] = {}
    said = 0
    from .pacing import syllables as _syl
    for who, text in rows:
        n = _syl(text)
        if not n:
            continue
        said += 1
        v = voice_of(ctx, who) or {}
        r = voice_rate(v.get("voice_id")) * speed_factor(v.get("model"), v.get("speed"))
        by_rate[r] = by_rate.get(r, 0) + n           # same rate summed first: one line = exactly the old n / RATE + BREATH
    if not said:
        return 0.0
    gap = LINE_GAP if gap is None else float(gap)
    return round(sum(n / r for r, n in by_rate.items()) + BREATH + gap * (said - 1), 1)


def scene_seconds(rows: List[Tuple[str, str]], ctx: Optional[Dict] = None) -> float:
    """Giây nói của các câu một cảnh kịch bản (chưa chia shot): mỗi LƯỢT LỜI (các câu liền nhau của cùng một người nói — vd lời dẫn đã
    tách theo câu) một BREATH + khoảng thật giữa các câu; người nói đổi = lượt mới. Trước 15/10: mỗi câu một BREATH (lời dẫn 28 câu
    #31 bị cộng ~10 s nghỉ không có thật). Hai câu của một lượt có thể sang shot sau: khoảng = của dự án (nhịp nhanh
    pacing.FAST_LINE_GAP 0,2 s qua cú cắt, thường LINE_GAP)."""
    gap = float((ctx or {}).get("gap") or LINE_GAP)
    total, run = 0.0, []
    for who, text in rows:
        if run and _key(run[-1][0]) != _key(who):
            total += needed_seconds(run, ctx, gap)
            run = []
        run.append((who, text))
    if run:
        total += needed_seconds(run, ctx, gap)
    return round(total, 1)


def max_clip_seconds(pipeline, project_id: int, scene_id=None) -> int:
    """Longest clip the scene's video model can make (per-scene model choice in v2; 15 s when unknown)."""
    from .adapters.clipai import effective_duration, resolve_model
    from .providers import ProviderError
    try:
        model = pipeline.project(project_id)["video_model"]
        if scene_id is not None:
            from . import model_router
            model = model_router.scene_choice(pipeline.conn, scene_id)["model"]
        canonical, family = resolve_model(model)[:2]
        return effective_duration(canonical, family, 999)
    except (ProviderError, ValueError, TypeError, KeyError):
        return 15


def voiced_seconds(voice: Dict[int, float], scene_id: int) -> float:
    """Real length of the scene's generated voice lines (seconds, gaps included) when all are made, else 0."""
    return float(voice.get(scene_id) or 0.0)


def check(pipeline, project_id: int, voice: Dict[int, float] = None) -> List[Dict]:
    """One entry per scene that has dialogue. `voice` = {scene_id: seconds of the real generated voice lines}: when known it
    replaces the syllable estimate (the clip is then sized to the actual voice)."""
    voice = voice or {}
    ctx = speech_ctx(pipeline.conn, project_id)
    out = []
    for r in pipeline.conn.execute(
            "SELECT s.id, s.idx, s.data, m.duration_sec FROM scenes s LEFT JOIN motion_prompts m ON m.scene_id=s.id"
            " WHERE s.project_id=? ORDER BY s.idx", (project_id,)).fetchall():
        data = json.loads(r["data"] or "{}")
        rows = scene_lines(data)
        if not rows:
            continue
        longest = max_clip_seconds(pipeline, project_id, r["id"])
        real = voiced_seconds(voice, r["id"])
        need = round(real + BREATH, 1) if real else needed_seconds(rows, ctx)
        planned = float(r["duration_sec"] or data.get("duration_s") or DEFAULT_PLANNED)
        if need > longest:
            status, advice = "split", f"Thoại cần ~{need:g}s nhưng model chỉ làm clip tối đa {longest}s: rút gọn thoại hoặc tách cảnh" \
                + (" (hoặc đổi cảnh này sang Seedance 2.5 — tối đa 30s — ở Bước 4)." if longest < 30 and need <= 30 else ".")
        elif need > planned:
            status, advice = "extend", f"Thoại cần ~{need:g}s, clip đang {planned:g}s: tăng lên {math.ceil(need)}s."
        elif need > planned * 0.9:
            status, advice = "tight", "Vừa khít, nên chừa thêm chút thời gian."
        else:
            status, advice = "ok", ""
        out.append({"scene_id": r["id"], "idx": r["idx"], "speakers": sorted({n for n, _ in rows if n}),
                    "syllables": sum(syllables(s) for _, s in rows), "needed": need, "planned": planned, "max": longest,
                    "target": min(math.ceil(need), longest), "status": status, "advice": advice, "measured": bool(real)})
    return out


def problems(entries: List[Dict]) -> List[Dict]:
    return [e for e in entries if e["status"] in ("extend", "split")]


def extend(pipeline, entries: List[Dict]) -> int:
    """Raise the planned duration of every 'extend' scene: the motion prompt's duration when the scene has one, and the
    scene's `duration_s` (marked as set by the person, so a motion prompt written later keeps it). Returns how many."""
    n = 0
    for e in entries:
        if e["status"] != "extend":
            continue
        cur = pipeline.conn.execute("UPDATE motion_prompts SET duration_sec=? WHERE scene_id=?", (e["target"], e["scene_id"]))
        row = pipeline.conn.execute("SELECT data FROM scenes WHERE id=?", (e["scene_id"],)).fetchone()
        if row is not None:
            data = json.loads(row["data"] or "{}")
            data["duration_s"] = e["target"]
            data["_user_locked"] = sorted(set(data.get("_user_locked") or []) | {"duration_s"})
            pipeline.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), e["scene_id"]))
        n += 1 if (cur.rowcount or row is not None) else 0
    pipeline.conn.commit()
    return n
