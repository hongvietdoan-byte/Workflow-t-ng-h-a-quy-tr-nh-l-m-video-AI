"""S9.6 / S6.2 (after #8: the effects played at 43 s instead of shot 26, the music was silent 39–65 s, and nobody could see it before
the render): the whole film on one timeline — shots, voice lines, music on/off, effects, subtitles — read from what the render will
use, no AI, nothing generated. Step 5 draws it (dashboard/steps/step5.timeline_panel).

Every track says where its numbers come from; a track that cannot be read is empty with a note (never a guessed position)."""
import json
from typing import Dict, List

from . import audio_lib, sfx_plan, sound_intent, subtitles
from .pipeline import Pipeline


def tracks(p: Pipeline, data_dir: str, pid: int) -> Dict:
    """{"total", "shots": [{start, end, label, idx}], "voice": [...], "music": [...on segments], "sfx": [...], "subs": [...],
    "notes": [str]} — seconds on the final video's timeline (the clips a default render uses, their cut lengths)."""
    notes: List[str] = []
    shots = sfx_plan.timeline(p, data_dir, pid)
    total = round(max((s["start"] + s["length"] for s in shots), default=0.0), 2)
    out = {"total": total, "notes": notes,
           "shots": [{"start": s["start"], "end": round(s["start"] + s["length"], 2), "idx": s["idx"],
                      "label": f"{s['idx']:02d}" if s["idx"] is not None else "·", "title": s.get("title") or ""} for s in shots]}
    items = audio_lib.load(audio_lib.assets_dir(data_dir, pid))
    used = [e for e in items if e.get("use") and e.get("start") is not None and e.get("state") == "succeeded"]

    def span(e):
        start = float(e["start"])
        return start, round(start + float(e.get("duration_ms") or 0) / 1000.0, 2)

    out["voice"] = [dict(zip(("start", "end"), span(e)), label=str(e.get("speaker") or ""), title=str(e.get("text") or "")[:80])
                    for e in used if e.get("kind") == "tts"]
    out["sfx"] = [dict(zip(("start", "end"), span(e)), label=str(e.get("label") or "").replace("AI: ", "")[:24],
                       title=f"shot {e.get('anchor_idx')}" if e.get("anchor_idx") is not None else "")
                  for e in used if e.get("kind") == "sound_effect"]
    if not items:
        notes.append("chưa có giọng / hiệu ứng nào trong kho âm thanh của dự án")
    datas = {r["idx"]: json.loads(r["data"] or "{}") for r in p.conn.execute("SELECT idx, data FROM scenes WHERE project_id=?", (pid,))}
    try:
        plan = sound_intent.music_plan([datas.get(s["idx"], {}) for s in shots], [s["length"] for s in shots])
        on, t = [], 0.0
        for a, b in sorted(plan.get("off") or []):
            if a > t:
                on.append({"start": round(t, 2), "end": round(a, 2), "label": "nhạc"})
            t = max(t, b)
        if t < total:
            on.append({"start": round(t, 2), "end": total, "label": "nhạc"})
        out["music"] = on
        out["music_off"] = [{"start": a, "end": b} for a, b in plan.get("off") or []]
    except Exception as e:  # noqa: BLE001 - said, not guessed
        out["music"], out["music_off"] = [], []
        notes.append(f"không đọc được ý đồ nhạc: {type(e).__name__}")
    try:
        cues = subtitles.build_cues(p, data_dir, pid, timeline=[{"idx": s["idx"], "seconds": s["length"]} for s in shots])
        out["subs"] = [{"start": round(c.start, 2), "end": round(c.end, 2), "label": c.speaker or "", "title": c.text[:80]} for c in cues]
    except Exception as e:  # noqa: BLE001
        out["subs"] = []
        notes.append(f"không dựng được phụ đề: {type(e).__name__}")
    return out


TRACKS = (("shots", "🎬 Shot", "#4f7cff"), ("voice", "🗣 Thoại", "#2eaa6a"), ("music", "🎵 Nhạc", "#b36ae2"),
          ("sfx", "💥 Hiệu ứng", "#e2842e"), ("subs", "🔤 Phụ đề", "#7a8594"))


def html(data: Dict, px_per_s: float = 14.0) -> str:
    """The tracks as one horizontally scrolling strip (inline HTML, no script): hover a block for its text."""
    import html as h
    total = max(float(data.get("total") or 0), 1.0)
    width = int(total * px_per_s) + 10
    rows = []
    ticks = "".join(f'<div style="position:absolute;left:{int(t * px_per_s)}px;top:0;font-size:10px;color:#889">{t}s</div>'
                    for t in range(0, int(total) + 1, 5))
    rows.append(f'<div style="position:relative;height:14px;width:{width}px;margin-left:92px">{ticks}</div>')
    for key, name, colour in TRACKS:
        blocks = []
        for b in data.get(key) or []:
            left, w = int(b["start"] * px_per_s), max(int((b["end"] - b["start"]) * px_per_s), 2)
            tip = h.escape(f"{b['start']:.2f}–{b['end']:.2f}s {b.get('label', '')} {b.get('title', '')}".strip())
            blocks.append(f'<div title="{tip}" style="position:absolute;left:{left}px;width:{w}px;top:2px;height:20px;background:{colour};'
                          f'opacity:.85;border-radius:3px;overflow:hidden;white-space:nowrap;font-size:10px;color:#fff;padding:2px 3px;'
                          f'box-sizing:border-box">{h.escape(str(b.get("label", "")))}</div>')
        if key == "music":
            for b in data.get("music_off") or []:
                left, w = int(b["start"] * px_per_s), max(int((b["end"] - b["start"]) * px_per_s), 2)
                blocks.append(f'<div title="nhạc tắt {b["start"]:.1f}–{b["end"]:.1f}s" style="position:absolute;left:{left}px;width:{w}px;'
                              f'top:10px;height:4px;background:repeating-linear-gradient(90deg,#b36ae2 0 4px,transparent 4px 8px)"></div>')
        rows.append(f'<div style="display:flex;align-items:center;margin:2px 0"><div style="width:92px;flex:none;font-size:12px">{name}</div>'
                    f'<div style="position:relative;height:24px;width:{width}px;background:rgba(128,128,128,.12);border-radius:3px">'
                    + "".join(blocks) + "</div></div>")
    return (f'<div style="overflow-x:auto;padding:4px 0">' + "".join(rows) + "</div>")
