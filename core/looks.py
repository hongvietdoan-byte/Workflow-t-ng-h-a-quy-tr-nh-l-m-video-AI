"""The two picture looks the team makes (decided 2026-09-24, PLAN.md section 5): ANIME, and FF_INGAME = exactly like the Free Fire
in-game character art. A project property, separate from the editing style (style_profile = rhythm/shot sizes of a Free Fire video
style). It reaches every step: the image prompt's render sentence, which library pictures are preferred (asset_images.look), the
Director and QC, and the video model choice (W11)."""
import re
from typing import Dict, Optional

LOOKS: Dict[str, Dict] = {
    "FF_INGAME": {
        "label": "Giống y hệt in-game Free Fire",
        "asset_look": "ingame",
        "image": ("Render style: Garena Free Fire in-game 3D character art — match the reference images exactly (same proportions, "
                  "materials, shading, colours and level of detail); not anime, not a realistic photo, not a different 3D style. "
                  # knowledge/ff_gameplay_visual.md: words alone drift to a realistic shooter (PUBG / Call of Duty look)
                  "Stylized mobile-game proportions, moderate texture detail, clear gameplay lighting, background in focus; "
                  "not a cinematic movie still, no depth-of-field blur, no film colour grading, not a realistic military shooter."),
        "director": ("Look của dự án: GIỐNG Y HỆT ảnh in-game Free Fire. Ảnh tài nguyên là chuẩn tuyệt đối về ngoại hình và chất liệu; "
                     "prompt ảnh không thêm phong cách vẽ khác (không anime, không ảnh thật). Không viết chữ phong cách kéo về tả thực "
                     "trong `image_prompt` (cinematic, photorealistic, bokeh, depth of field, film grain…) — xem mục \"Free Fire gameplay "
                     "thật trông thế nào\"; tả vật thể cụ thể của game thay cho không khí chung chung."),
        "qc": ("Look: in-game Free Fire — trừ điểm `character`/`consistency` nếu ảnh ra kiểu anime, ảnh thật hoặc 3D khác ảnh tài nguyên; "
               "trừ điểm nếu ảnh trông như game bắn súng tả thực (PUBG / Call of Duty: da thật, đồ quân sự tả thực, vân bề mặt dày, "
               "hậu cảnh mờ nhòe kiểu ống kính, chỉnh màu kiểu phim)."),
    },
    "ANIME": {
        "label": "Anime",
        "asset_look": "anime",
        "image": ("Render style: 2D anime illustration (clean line art, cel shading) of these exact characters — keep every person's "
                  "identity, hairstyle, outfit colours and accessories from the reference images; only the drawing style changes."),
        "director": ("Look của dự án: ANIME. Nhân vật giữ đúng nhận diện theo ảnh tài nguyên (tóc, màu trang phục, phụ kiện), chỉ đổi nét vẽ "
                     "sang anime; mọi prompt ảnh dùng cùng một cách tả phong cách anime để các shot đồng đều."),
        "qc": "Look: anime — nét vẽ anime đồng đều giữa các shot; nhân vật vẫn phải nhận ra đúng người theo ảnh tài nguyên.",
    },
}


def of(project_row) -> Optional[str]:
    try:
        value = project_row["look"]
    except (KeyError, IndexError, TypeError):
        return None
    return value if value in LOOKS else None


def image_sentence(project_row) -> str:
    look = of(project_row)
    return (" " + LOOKS[look]["image"]) if look else ""


# S4.3 (after #8: a close-up of Kelly came out as anime): the video model is told the look in EVERY video prompt, not only the picture
# model. Short — it goes into prompts with a hard length limit — and without the realism words clean_prompt removes.
VIDEO_SENTENCE = {
    "FF_INGAME": ("Style lock: Garena Free Fire in-game 3D character render, exactly like the reference pictures — not anime, not 2D, "
                  "not cel-shaded, not live action."),
    "ANIME": "Style lock: 2D anime illustration, the same drawing style in every frame — not 3D, not live action.",
}


def video_sentence(project_row) -> str:
    return VIDEO_SENTENCE.get(of(project_row) or "", "")


def director_note(project_row) -> str:
    look = of(project_row)
    return ("# Look hình của dự án\n" + LOOKS[look]["director"]) if look else ""


def motion_note(project_row) -> str:
    """The motion writer's words land in the video prompt: an in-game project keeps realism words out of them too."""
    if of(project_row) != "FF_INGAME":
        return ""
    return ("# Look hình của dự án\nIn-game Free Fire (knowledge/ff_gameplay_visual.md): chuyển động và ánh sáng kiểu game; KHÔNG viết chữ "
            "phong cách kéo về tả thực (cinematic, photorealistic, realistic skin, bokeh, depth of field, film grain, color grading) — "
            "code gỡ các chữ này trước khi gửi và báo lại. Không bắt model vẽ giao diện game (HUD); tả hành động và vật thể cụ thể.")


def qc_note(project_row) -> str:
    look = of(project_row)
    return ("# Look hình của dự án\n" + LOOKS[look]["qc"]) if look else ""


def asset_look(project_row) -> Optional[str]:
    look = of(project_row)
    return LOOKS[look]["asset_look"] if look else None


# Words that pull an image / video model from the Free Fire render towards a realistic shooter (knowledge/ff_gameplay_visual.md §3,
# Free Fire In-Game Visual Replication Plan v1.0 §6.3). Only for FF_INGAME: an anime or realistic-CGI project may want some of them.
# A negated form ("not photorealistic") goes too: the look's own sentence already says it.
_REALISM = re.compile(
    r"\b(?:(?:not|no|non)[- ](?:an? )?)?(?:"
    r"(?:ultra[- ]?|hyper[- ]?|photo[- ]?)?realistic(?: skin(?: texture)?)?|photoreal(?:ism)?|"
    r"cinematic(?: (?:movie still|still|look|style|quality|lighting|colou?r grading|frame))?|(?:film|movie) still|bokeh|"
    r"shallow (?:depth of field|focus)|depth[- ]of[- ]field(?: blur)?|anamorphic(?: lens)?|film grain|"
    r"(?:filmic |film )?colou?r grading|8k|unreal engine(?: \d)?|AAA|gritty realism|hyper[- ]detailed)\b", re.IGNORECASE)
VIDEO_NEGATIVE = ("photorealistic, realistic military shooter, PUBG style, Call of Duty style, realistic skin, cinematic depth of "
                  "field, bokeh, film grain, film colour grading")


def clean_prompt(project_row, text: str):
    """(the prompt without realism words, the words removed) for an FF_INGAME project; any other project: unchanged. Only the
    Director's own words go through it (the look's sentence names these words on purpose, as things to avoid); the runner reports what
    it removed (CHUAN_XAY_DUNG luật 1: never change a prompt without saying so)."""
    if of(project_row) != "FF_INGAME" or not text:
        return text, []
    removed = [m.group(0) for m in _REALISM.finditer(text)]
    if not removed:
        return text, []
    out = _REALISM.sub("", text)
    out = re.sub(r"\b(?:of|with)\s+(?=[,.;:]|$)", "", out)          # "... still of" / "with" left hanging
    out = re.sub(r"^\s*(?:of|with)\b", "", out)
    out = re.sub(r"\s+([,.;:])", r"\1", out)
    out = re.sub(r"([,;:])(?:\s*[,;:])+", r"\1", out)
    out = re.sub(r"[,;:]+\s*\.", ".", out)
    out = re.sub(r"\s{2,}", " ", out).strip(" ,;:")
    return out, removed


# F1-B — luật tầng 1 (người dùng chốt 09/10, #24 teaser kinh dị): in a Free Fire project blood, matted hair, wounds and corpses are
# only HINTED (deep shadow, out of focus, partly hidden), never shown clearly — the picture's "everything in focus" does not reach them.
# English words whole (\b: "bloodline" is not blood, "blood-red jacket" is a colour); Vietnamese with accents, never folded ("máu" ≠
# "màu", "xác chết" ≠ "chính xác"). F1 sửa (09/10): the ONE gore word list — prompt_formula checks with it too ("a wound" was caught by
# the check but not by the restraint sentence).
_GORE = re.compile(
    r"\b(?:blood(?![- ]red\b)(?:y|ied|stains?|[- ]stained|[- ]soaked)?|blood (?:stains?|spatters?|splatters?|pools?|drips?|smears?)"
    r"|bleed(?:s|ing)?|gore|gory|gruesome|wounds?|wounded|gash(?:es)?|corpses?|cadavers?|dead bod(?:y|ies)"
    r"|carcass(?:es)?|severed|dismember\w*|decapitat\w*|guts|entrails|intestines|innards|mangled|mutilat\w*"
    r"|(?:wet|matted|clumped|soaked|dripping) (?:\w+ )?hair|hair strands? (?:on|over|across|stuck|clinging|draped|hanging))\b"
    r"|(?<!\w)(?:máu|xác chết|thi thể|thây|vết thương|tóc rối bết|tóc bết|nội tạng|đứt lìa|chặt đầu)(?!\w)", re.IGNORECASE)
_IN_FOCUS = re.compile(r"\beverything (?:is )?(?:sharp(?:ly)? )?in (?:sharp )?focus\b", re.IGNORECASE)
_GORE_TAG = "Gore restraint:"
GORE_VIDEO_MAX = 200     # the video sentence is never longer (seedance_refs._estimated_len counts it before a group is closed)


def gore_words(text: str):
    """The gore words of a text, lower case, once each, in order."""
    import unicodedata
    found = [m.group(0).lower() for m in _GORE.finditer(unicodedata.normalize("NFC", text or ""))]
    return list(dict.fromkeys(found))


def gore_search(text: str):
    """The first gore word of a text (re.Match) or None — NFC, no accent folding."""
    import unicodedata
    return _GORE.search(unicodedata.normalize("NFC", text or ""))


def is_ff(project_row) -> bool:
    try:
        return str(project_row["game"] or "").strip().upper() == "FF"
    except (KeyError, IndexError, TypeError):
        return False


def gore_restraint(project_row, text: str, video: bool = False, scan: Optional[str] = None) -> str:
    """`text` with the restraint sentence added when it (or, given, only `scan`: the Director's own words of the shot — so a costume
    profile in the Lock does not trigger it) names blood / gore / wounds /
    corpses and the project is a Free Fire one; any other project or a clean shot: unchanged. Image prompt: "everything in focus"
    becomes "everything in focus except those hinted details". Short (≤ ~170 characters) — video prompts have a hard limit."""
    if not text or not is_ff(project_row) or _GORE_TAG in text:
        return text
    words = gore_words(text if scan is None else scan)
    if not words:
        return text
    # English only: a Vietnamese word in a Seedance prompt blocks the send (seedance_refs lint "prompt còn chữ tiếng Việt")
    what = (", ".join([w for w in words if w.isascii()][:4]) or "the blood and wounds")[:90]
    if video:
        return f"{text.rstrip()} {_GORE_TAG} {what} only hinted — deep shadow, out of focus or partly hidden, never shown clearly."
    out = _IN_FOCUS.sub("everything in focus except those hinted details", text)
    return (f"{out.rstrip()} {_GORE_TAG} {what} are only hinted — in deep shadow, out of focus or partly hidden, never shown clearly; "
            "they stay out of focus even where the rest of the picture is sharp.")


def video_negative(project_row, negative: str = "") -> str:
    """The motion prompt's negative with the anti-realism words of an FF_INGAME project added (once)."""
    if of(project_row) != "FF_INGAME":
        return negative or ""
    base = (negative or "").strip().rstrip(",")
    return f"{base}, {VIDEO_NEGATIVE}" if base and VIDEO_NEGATIVE not in base else (base or VIDEO_NEGATIVE)
