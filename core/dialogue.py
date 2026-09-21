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
from typing import Dict, List, Tuple

RATE = float(os.environ.get("DIALOGUE_SYLLABLES_PER_SEC", "3.5"))     # comfortable speaking speed
BREATH = 0.5                                                          # seconds of room around the lines
DEFAULT_PLANNED = 5.0
_LINE = re.compile(r"^\s*([^:\n]{1,30}?)\s*:\s*(.+?)\s*$")


def lines(text: str) -> List[Tuple[str, str]]:
    """(speaker, line) for every 'NAME: words' row; speaker names are written in capitals in the script."""
    out = []
    for row in (text or "").splitlines():
        m = _LINE.match(row)
        if not m:
            continue
        name, said = m.group(1).strip(), m.group(2).strip().strip('"“”')
        name = re.sub(r"\s*\(.*?\)\s*", "", name).strip()
        if name and name == name.upper() and any(ch.isalpha() for ch in name) and said:
            out.append((name, said))
    return out


def syllables(said: str) -> int:
    return len(re.findall(r"\w+", said, re.UNICODE))


def needed_seconds(rows: List[Tuple[str, str]]) -> float:
    total = sum(syllables(said) for _, said in rows)
    return round(total / RATE + BREATH, 1) if total else 0.0


def max_clip_seconds(pipeline, project_id: int) -> int:
    """Longest clip the project's video model can make (15 s when the model is not set)."""
    from .adapters.clipai import effective_duration, resolve_model
    from .providers import ProviderError
    try:
        canonical, family = resolve_model(pipeline.project(project_id)["video_model"])[:2]
        return effective_duration(canonical, family, 999)
    except (ProviderError, ValueError, TypeError):
        return 15


def check(pipeline, project_id: int) -> List[Dict]:
    """One entry per scene that has dialogue."""
    longest = max_clip_seconds(pipeline, project_id)
    out = []
    for r in pipeline.conn.execute(
            "SELECT s.id, s.idx, s.data, m.duration_sec FROM scenes s LEFT JOIN motion_prompts m ON m.scene_id=s.id"
            " WHERE s.project_id=? ORDER BY s.idx", (project_id,)).fetchall():
        rows = lines(json.loads(r["data"] or "{}").get("text", ""))
        if not rows:
            continue
        need = needed_seconds(rows)
        planned = float(r["duration_sec"] or DEFAULT_PLANNED)
        if need > longest:
            status, advice = "split", f"Thoại cần ~{need:g}s nhưng model chỉ làm clip tối đa {longest}s: rút gọn thoại hoặc tách cảnh."
        elif need > planned:
            status, advice = "extend", f"Thoại cần ~{need:g}s, clip đang {planned:g}s: tăng lên {math.ceil(need)}s."
        elif need > planned * 0.9:
            status, advice = "tight", "Vừa khít, nên chừa thêm chút thời gian."
        else:
            status, advice = "ok", ""
        out.append({"scene_id": r["id"], "idx": r["idx"], "speakers": sorted({n for n, _ in rows}),
                    "syllables": sum(syllables(s) for _, s in rows), "needed": need, "planned": planned, "max": longest,
                    "target": min(math.ceil(need), longest), "status": status, "advice": advice})
    return out


def problems(entries: List[Dict]) -> List[Dict]:
    return [e for e in entries if e["status"] in ("extend", "split")]


def extend(pipeline, entries: List[Dict]) -> int:
    """Raise the planned duration of every 'extend' scene (only scenes that already have a motion prompt). Returns how many."""
    n = 0
    for e in entries:
        if e["status"] != "extend":
            continue
        cur = pipeline.conn.execute("UPDATE motion_prompts SET duration_sec=? WHERE scene_id=?", (e["target"], e["scene_id"]))
        n += cur.rowcount
    pipeline.conn.commit()
    return n
