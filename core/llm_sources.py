"""Which built-in skill / prompt files went into a Claude call (rà soát 2026-09-27: "đã add nhiều kĩ năng … không biết có thực sự sử dụng
hay không"). Found in the TEXT really sent — a file counts when a distinctive slice of it is in the request — so a file read for
another purpose never counts; the ledger writes the list with the call's tokens into `llm_calls`."""
import os
from typing import Dict, List, Optional

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_FOLDERS = ("prompts", "knowledge")
_SLICES: Optional[Dict[str, List[str]]] = None


def _slices() -> Dict[str, List[str]]:
    """file -> 2 distinctive pieces (a long line from the first and the second half of the file)."""
    global _SLICES
    if _SLICES is None:
        out: Dict[str, List[str]] = {}
        for folder in _FOLDERS:
            for base, _, files in os.walk(os.path.join(_ROOT, folder)):
                for name in files:
                    if not name.endswith(".md"):
                        continue
                    path = os.path.join(base, name)
                    try:
                        lines = [ln.strip() for ln in open(path, encoding="utf-8").read().splitlines() if len(ln.strip()) >= 40]
                    except OSError:
                        continue
                    if not lines:
                        continue
                    half = len(lines) // 2
                    pick = [max(lines[:half] or lines, key=len)[:120], max(lines[half:] or lines, key=len)[:120]]
                    out[os.path.relpath(path, _ROOT).replace("\\", "/")] = pick
        _SLICES = out
    return _SLICES


def in_text(text: str) -> List[str]:
    """The skill / prompt files whose content is in this request text."""
    if not text:
        return []
    return sorted(f for f, pieces in _slices().items() if any(p in text for p in pieces))
