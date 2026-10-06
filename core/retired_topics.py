"""S14.46 (người dùng 06/10: "bài học nào không dùng đến cũng nên loại bỏ, tránh gây nhầm lẫn cho Đạo diễn"): topics of features the
pipeline no longer has. A lesson / mistake / experience case about one of them must not reach a prompt any more.

Two layers, both here:
  1. storage — `retired_at` / `retired_why` columns on `mistakes`, `lessons`, `experience_cases`. A retired row stays in its table (the
     importers are keyed INSERT OR IGNORE: a deleted row would be imported again at the next refresh), readers skip it, and
     `tools/lessons_retire.py --restore` gives it back. Nothing is deleted.
  2. read-time filter — `matches()` on the text of every lesson / case / auto lesson line before it is put into a prompt, so a lesson
     about a removed topic written LATER does not slip in either. What is filtered is said once per call (diag), never silently.

The topic list is edited by hand: TOPICS below (one per removed flag of `features.REMOVED` + the other removed features), and an
optional JSON file (`RETIRED_TOPICS_FILE`, default data/retired_topics.json) {"topic": {"why": "...", "patterns": [...], "keep": [...]}}
— `null` for a topic switches it off. Patterns are regular expressions matched case-insensitively on the text as written (accents
kept: stripping them makes short Vietnamese words collide), with word edges where a short word could hit inside another one
("plated boots" is not a plate). `keep` = a text matching one of these stays even when it names the topic (a fault that can still
happen, e.g. QC D3 "ghép lộ").
"""
import json
import os
import re
import unicodedata
from typing import Dict, Iterable, List, Optional

from . import features

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLES = {"mistakes": "text", "lessons": "title || ' — ' || body", "experience_cases": "coalesce(kind,'') || ' — ' || coalesce(note,'')"}
COLUMNS = (("retired_at", "TEXT"), ("retired_why", "TEXT"))

# topic -> why (shown in the archive list) + patterns. A removed flag takes its reason from features.REMOVED.
_BASE: Dict[str, Dict] = {
    "location_plates": {"patterns": [r"phông\s*xanh", r"green[\s_-]?screen", r"plate_mode", r"location_plates?\b", r"chroma[\s_-]?key",
                                     r"ghép\s+(?:lên\s+)?nền\s+3d"],
                        # kept: a fault that can still happen (QC D3 "ghép lộ"), and the mannequin / depth reference videos (01/10)
                        # whose green backdrop must be named as "not taken" — a live lesson, not the removed plate workflow
                        "keep": [r"ghép\s+lộ", r"mannequin", r"depth[\s_-]?map"]},
    "layout_to_model": {"patterns": [r"layout_to_model"]},
    "chain_previous_auto": {"patterns": [r"chain_previous_auto"]},
    "setcheck_autofix": {"patterns": [r"setcheck_autofix"]},
    # only the flag's name: "bản mẫu 480p" (a cheap test render first) is still craft advice (knowledge/roles/dp.md)
    "seedance_sample_mode": {"patterns": [r"seedance_sample_mode"]},
    "sync_so": {"why": "sync.so: người dùng chốt 26/09 không mở tài khoản — khớp môi chỉ bằng video kèm giọng (Seedance reference_audio)",
                "patterns": [r"sync\.so\b", r"\bsyncso\b", r"\bsync\s+labs\b"]},
    "ff_site_vm": {"why": "S14.5: ff_site bỏ sandbox `vm` (Node) — không còn chạy mã trang web",
                   "patterns": [r"\bnode:vm\b", r"\bvm\.(?:runIn\w+|Script|createContext)\b", r"sandbox\s+`?vm`?\b", r"\bvm\s+sandbox\b"]},
    "autopilot_daily_jobs": {"why": "S14.18: bỏ trần job/ngày AUTOPILOT_DAILY_JOBS — thay bằng giới hạn theo người (core/person_limits)",
                             "patterns": [r"autopilot_daily_jobs"]},
}


def file_path() -> str:
    return os.environ.get("RETIRED_TOPICS_FILE") or os.path.join(ROOT, "data", "retired_topics.json")


_CACHE = {"stamp": None, "path": None, "topics": None}


def topics() -> Dict[str, Dict]:
    """topic -> {"why", "patterns": [compiled], "keep": [compiled]}: the built-in list + the hand-edited file (re-read when it changes).
    A broken file is reported by the caller's diag (`file_error`), the built-in list is still used — never silently nothing."""
    path = file_path()
    try:
        stamp = os.stat(path).st_mtime_ns
    except OSError:
        stamp = None
    if _CACHE["topics"] is not None and _CACHE["stamp"] == stamp and _CACHE["path"] == path:
        return _CACHE["topics"]
    raw = {k: dict(v) for k, v in _BASE.items()}
    _CACHE["error"] = None
    if stamp is not None:
        try:
            with open(path, encoding="utf-8") as f:
                extra = json.load(f)
            for name, spec in (extra or {}).items():
                if spec is None:
                    raw.pop(name, None)
                else:
                    raw[name] = {"why": spec.get("why"), "patterns": list(spec.get("patterns") or []), "keep": list(spec.get("keep") or [])}
        except (OSError, ValueError, AttributeError, TypeError) as e:
            _CACHE["error"] = f"{path}: {e}"
    out = {}
    for name, spec in raw.items():
        why = spec.get("why") or features.REMOVED.get(name) or name
        out[name] = {"why": why, "patterns": [re.compile(p, re.I) for p in spec.get("patterns") or []],
                     "keep": [re.compile(p, re.I) for p in spec.get("keep") or []]}
    _CACHE.update(stamp=stamp, path=path, topics=out)
    return out


def file_error() -> Optional[str]:
    topics()
    return _CACHE.get("error")


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", str(text or ""))


def matches(text: str) -> List[str]:
    """The retired topics `text` is about ([] = keep it)."""
    t = _norm(text)
    if not t:
        return []
    out = []
    for name, spec in topics().items():
        if any(p.search(t) for p in spec["patterns"]) and not any(k.search(t) for k in spec["keep"]):
            out.append(name)
    return out


def why(topic: str) -> str:
    spec = topics().get(topic)
    return spec["why"] if spec else topic


# ---- storage ------------------------------------------------------------------------------------------------------------------
def _cols(conn, table: str) -> set:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def ensure_columns(conn, tables: Iterable[str] = tuple(TABLES)) -> None:
    """Add retired_at / retired_why to the tables that exist (idempotent; old rows get NULL = not retired)."""
    for table in tables:
        have = _cols(conn, table)
        if not have:
            continue                      # experience_cases is created lazily by core/experience.ensure
        for col, typ in COLUMNS:
            if col not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")


def has_columns(conn, table: str) -> bool:
    return "retired_at" in _cols(conn, table)


# ---- read-time filter + one diag per call -----------------------------------------------------------------------------------------
def split(items: List[Dict], text_of) -> tuple:
    """(kept, n dropped by topic, {topic: count}). Rows with retired_at set are left out too but not counted: they were retired on
    purpose with a written list (docs/BAI_HOC_DA_CAT_*.md) — counting them would add a diag row to every call forever. What IS counted
    = a row about a removed topic not retired yet (written after the clean-up): the sign to run tools/lessons_retire.py again."""
    kept, dropped, n = [], {}, 0
    for it in items:
        if it.get("retired_at"):
            continue
        hit = matches(text_of(it))
        if hit:
            n += 1
            for h in hit:
                dropped[h] = dropped.get(h, 0) + 1
            continue
        kept.append(it)
    return kept, n, dropped


def report(conn, stage: str, what: str, n: int, dropped: Dict[str, int]) -> None:
    """One diag row for everything one call left out (no row when nothing was)."""
    err = file_error()
    if conn is None or not (n or err):
        return
    from . import diag
    if n:
        detail = ", ".join(f"{k} ×{v}" for k, v in sorted(dropped.items()))
        diag.record(conn, stage, "info", f"Không đưa vào prompt {n} {what} thuộc chủ đề đã bỏ ({detail}) — S14.46; "
                    "chạy py tools/lessons_retire.py để xem / cất hẳn", code="lesson_retired_topic")
    if err:
        diag.record(conn, stage, "warn", f"Không đọc được danh sách chủ đề đã bỏ ({err}) — dùng danh sách có sẵn trong core/retired_topics.py",
                    code="retired_topics_file")
