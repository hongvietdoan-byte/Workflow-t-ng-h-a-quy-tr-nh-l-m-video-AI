"""Lỗi 9 (#27 tổng kết 13/10, cờ `tts_lowercase_caps`): TTS tiếng Việt đọc SAI THANH chữ IN HOA ("BÌNH TĨNH" → "bình tỉnh"; đo F0
chữ 'tĩnh': bản in hoa võng xuống rồi vọt = thanh hỏi, bản chữ thường giữ cao đi lên = ngã — Whisper không phân biệt được dấu).
Trước khi gửi TTS: từ tiếng Việt viết hoa toàn bộ → chữ thường. Giữ nguyên:
  - tên riêng / từ game: tên nhân vật dự án, tên Kho, khóa từ điển phát âm (data/pronunciation_vi.json) — cả cụm, đúng nguyên từ
    (tên CÓ dấu tiếng Việt như "XÚC TU ĐỎ" vẫn hạ: in hoa sai thanh y như từ thường — chính là lỗi này);
  - từ IN HOA không dấu không có dáng âm tiết tiếng Việt (BOOYAH, SKORP, HAWK, RPK, OK…);
  - từ IN HOA không dấu có dáng âm tiết Việt ("NHANH") chỉ hạ khi đi cùng cụm IN HOA có từ có dấu ("NHANH LÊN") — đứng một mình
    không đoán.
Chỉ chữ GỬI TTS đổi; phụ đề / CSDL giữ chữ gốc. 0 USD."""
import re
import unicodedata
from typing import Iterable, List, Optional

FLAG = "tts_lowercase_caps"

# chữ có dấu tiếng Việt (kể cả Đ) — viết hoa
_VI_MARK = re.compile(r"[ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ]")
# dáng một âm tiết tiếng Việt không dấu: phụ âm đầu + vần + phụ âm cuối
_SYLLABLE = re.compile(r"^(?:NGH|NG|NH|CH|GH|GI|KH|PH|QU|TH|TR|[BCDGHKLMNPRSTVX])?"
                       r"(?:UYE|UYA|IEU|YEU|UOI|UOU|OAI|OAY|OEO|UAY|UYU|IE|YE|UO|UA|IA|UI|OI|AI|AO|AU|AY|EO|EU|IU|OA|OE|UE|UY|"
                       r"[AEIOUY])(?:CH|NG|NH|[CMNPT])?$")
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def enabled() -> bool:
    from . import features
    try:
        return features.on(FLAG)
    except KeyError:
        return False


def _caps(w: str) -> bool:
    return len(w) >= 2 and w.isupper()


def _vi_shaped(w: str) -> bool:
    return bool(_SYLLABLE.match(w))


def lower_caps(text: str, keep: Iterable[str] = ()) -> str:
    """`text` with its Vietnamese all-caps words in lower case (rules in the module note); `keep` = names / game words left as written
    (matched as whole words, any case)."""
    if not text:
        return text
    text = unicodedata.normalize("NFC", text)
    # a name WITH Vietnamese marks ("XÚC TU ĐỎ") is not kept in capitals: it is mis-toned exactly like any other word (the bug);
    # lower case is read right and the subtitles keep the name as written
    names = sorted({str(k).strip() for k in keep if str(k or "").strip() and not _VI_MARK.search(str(k).upper())},
                   key=len, reverse=True)
    held: List[str] = []

    def _hold(m):
        held.append(m.group(0))
        return f"\x00{len(held) - 1}\x00"
    for n in names:
        text = re.sub(r"(?<![\w])" + re.escape(unicodedata.normalize("NFC", n)) + r"(?![\w])", _hold, text, flags=re.IGNORECASE)
    # runs of all-caps words (separated by spaces / punctuation within a phrase, not by a held name)
    tokens = list(_WORD.finditer(text))
    out, last = [], 0
    i = 0
    while i < len(tokens):
        if not _caps(tokens[i].group(0)):
            i += 1
            continue
        j = i
        while j + 1 < len(tokens) and _caps(tokens[j + 1].group(0)) \
                and re.fullmatch(r"[\s,!?.…\-–]*", text[tokens[j].end():tokens[j + 1].start()]):
            j += 1
        run = tokens[i:j + 1]
        marked = any(_VI_MARK.search(t.group(0)) for t in run)
        for t in run:
            w = t.group(0)
            if _VI_MARK.search(w) or (marked and _vi_shaped(w)):
                out.append(text[last:t.start()])
                out.append(w.lower())
                last = t.end()
        i = j + 1
    out.append(text[last:])
    text = "".join(out)
    return re.sub(r"\x00(\d+)\x00", lambda m: held[int(m.group(1))], text)


def keep_words(conn, project_id: Optional[int]) -> List[str]:
    """Names left as written: the project's characters + speakers, every Kho name, the pronunciation dictionary's words."""
    out: List[str] = []
    if conn is not None and project_id is not None:
        try:
            out += [str(r[0]) for r in conn.execute("SELECT name FROM characters WHERE project_id=?", (project_id,))]
        except Exception:  # noqa: BLE001 - a bare database: no names to keep
            pass
        try:
            out += [str(r[0]) for r in conn.execute("SELECT name FROM assets")]
        except Exception:  # noqa: BLE001
            pass
    try:
        from .voice import pronunciation
        out += list(pronunciation())
    except Exception:  # noqa: BLE001
        pass
    return out
