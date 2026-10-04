"""The first-time viewer (kế hoạch sau #8, S3.2 — lỗi 1.9: the story felt cut short; Maxim was hit and nobody saw a shooter).

One Claude call reads ONLY what will be on screen — each shot's size, who is in frame, the visible action, the lines heard, the text
shown — never the Director's intent, beats or notes, and tells the story back: what it understood, where it turned and why, and where
a first-time viewer would be lost. The Director's plan and this reading side by side show the gap before a picture is paid for.
Feature `story_check` (off until a real run shows it catches real gaps)."""
import json
import os
from typing import Dict, List, Optional

PROMPT = "22_first_viewer.md"


def digest(p, project_id: int) -> List[Dict]:
    """The film as a viewer gets it, in order — no intent fields."""
    out = []
    for r in p.conn.execute("SELECT idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall():
        d = json.loads(r["data"] or "{}")
        from .shots import label
        item = {"shot": label(d, r["idx"]), "size": d.get("size") or "", "in_frame": [str(c) for c in d.get("characters") or []],
                "action": str(d.get("action") or d.get("shot") or "")[:240]}
        lines = [f"{x.get('speaker') or '?'}: {x.get('text')}" for x in d.get("dialogue") or [] if isinstance(x, dict) and x.get("text")]
        if lines:
            item["heard"] = lines
        if d.get("on_screen_text"):
            item["text_on_screen"] = [str(t) for t in d["on_screen_text"]]
        if d.get("flashback"):
            item["shown_as"] = "flashback"
        out.append(item)
    return out


def _check(obj) -> None:
    from .llm_io import SchemaError
    if not isinstance(obj, dict) or not isinstance(obj.get("summary"), str):
        raise SchemaError("cần object {summary, who_wants_what, turns, confusing, ending, understood}")
    for key in ("turns", "confusing"):
        if not isinstance(obj.get(key) or [], list):
            raise SchemaError(f"{key}: cần danh sách")
    u = obj.get("understood")
    if not isinstance(u, (int, float)) or not 1 <= u <= 5:
        raise SchemaError("understood: cần số 1–5")


def path(data_dir: str, project_id: int) -> str:
    return os.path.join(data_dir, str(project_id), "story_check.json")


def load(data_dir: str, project_id: int) -> Optional[Dict]:
    try:
        with open(path(data_dir, project_id), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def fingerprint(film: List[Dict]) -> str:
    import hashlib
    return hashlib.sha1(json.dumps(film, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]


def run(p, project_id: int, client, data_dir: str) -> Dict:
    """Ask once per shot plan (cached by a fingerprint of what is on screen); returns the reading + {"fingerprint", "shots"}."""
    from . import claude_tasks
    film = digest(p, project_id)
    if not film:
        return {}
    key = fingerprint(film)
    old = load(data_dir, project_id)
    if old and old.get("fingerprint") == key:
        return old
    prompt = claude_tasks._read("prompts", PROMPT) + "\n\n---\n\n" + claude_tasks._block("Phim (theo thứ tự trên màn hình)", film)
    obj = claude_tasks._run(p, project_id, "director", prompt, _check, client)
    res = dict(obj, fingerprint=key, shots=len(film))
    os.makedirs(os.path.dirname(path(data_dir, project_id)), exist_ok=True)
    with open(path(data_dir, project_id), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    return res


def lines(res: Optional[Dict]) -> List[str]:
    """The reading as short lines for Step 1 / the log."""
    if not res:
        return []
    out = [f"👀 Người xem lần đầu ({res.get('understood', '?')}/5): {res.get('summary', '')}"]
    for c in res.get("confusing") or []:
        if isinstance(c, dict):
            out.append(f"❓ {c.get('at', '')}: {c.get('question', '')}")
    for t in res.get("turns") or []:
        if isinstance(t, dict) and t.get("understood") is False:
            out.append(f"⚠ cú xoay {t.get('at', '')} chưa hiểu: {t.get('what', '')} — {t.get('why', '')}")
    return out
