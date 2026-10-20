"""QC logic CẢ CHUỖI clip theo thứ tự truyện (cờ `qc_sequence_logic`, TẮT mặc định).

QC từng clip (claude_tasks.qc_video) và QC đồng bộ cả bộ (clip_set_consistency: màu / ánh sáng / điểm nối) không thấy lỗi GIỮA các
shot: #31 (19/10, người dùng) — Kelly nhặt súng trên "thềm cỏ" nâng cao (S10/S11/S13) trong khi chỗ đó ở mặt đất như S8; S18 địch đã
gục mà Kelly vẫn xả súng vào tường keo; S19 nói "vừa hạ gục Xúc Tu Đỏ" mà không shot nào cho thấy; chuỗi 15→19 nhảy vị trí.

Mỗi nhóm `sequence` → các tờ ghép (mỗi hàng = MỘT shot: khung đầu / giữa / cuối clip, hoặc ảnh đã duyệt khi chưa có clip) + bảng câu
hành động theo thứ tự → MỘT lời gọi Claude (prompts/22_sequence_logic.md) trả {ok, summary, issues: [{idx, problem, fix}]}. Gọi qua
claude_tasks._run (client có sổ chi, nhãn công đoạn `qc_sequence`); ước tính trước bằng `estimate()`. Cờ tắt → không dựng gì, không gọi.
"""
import json
import os
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from . import claude_tasks, features, llm_io, prompts
from .llm_runner import LlmError
from .pipeline import Pipeline

FLAG = "qc_sequence_logic"
STAGE = "qc_sequence"
SHOTS_PER_SHEET = 4          # 4 hàng × 3 khung: tờ bị thu về cạnh 1024 px khi gửi — nhiều hơn thì khung quá nhỏ để thấy độ cao nền
NO_GROUP = "—"
_FIELDS = ("location", "plate_spot", "action", "end_state", "spatial_state", "characters")


def _group(data: Dict) -> str:
    return str(data["sequence"]) if data.get("sequence") not in (None, "") else NO_GROUP


def shot_rows(p: Pipeline, project_id: int, sequence: Optional[str] = None) -> List[Dict]:
    """The shots in story order (scene idx) with what the check reads: label, group, place, action, end state, dialogue."""
    from . import dialogue, shots
    out = []
    for r in p.conn.execute("SELECT idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)):
        d = json.loads(r["data"] or "{}")
        if sequence is not None and _group(d) != str(sequence):
            continue
        row = {"idx": r["idx"], "label": shots.label(d, r["idx"]), "sequence": _group(d)}
        row.update({k: d[k] for k in _FIELDS if d.get(k) not in (None, "", [], {})})
        lines = dialogue.scene_lines(d)
        if lines:
            row["dialogue"] = [f"{who}: {text}" for who, text in lines]
        out.append(row)
    return out


def _media(p: Pipeline, project_id: int, data_dir: str) -> Dict[int, Tuple[str, str]]:
    """{scene idx: ('clip', path) | ('image', path)} — the clip of the shot (a draft waiting for review counts: this check is for
    drafts), else its newest approved picture."""
    from . import final_cut
    out: Dict[int, Tuple[str, str]] = {}
    for c in final_cut.collect_clips(p, data_dir, project_id):
        if c.get("idx") and c.get("path") and c.get("state") != "rejected":
            out[c["idx"]] = ("clip", c["path"])
    for r in p.conn.execute("SELECT s.idx, (SELECT j.id FROM jobs j WHERE j.scene_id=s.id AND j.type='image_gen'"
                            " AND j.state='approved' ORDER BY j.id DESC LIMIT 1) AS jid FROM scenes s WHERE s.project_id=?",
                            (project_id,)):
        path = r["jid"] and os.path.join(data_dir, str(project_id), "images", f"job_{r['jid']}.png")
        if r["idx"] not in out and path and os.path.exists(path):
            out[r["idx"]] = ("image", path)
    return out


def _grab(ffmpeg: str, path: str, t: float, dest: str) -> str:
    subprocess.run([ffmpeg, "-y", "-ss", f"{max(t, 0):.2f}", "-i", path, "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "4", dest],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
    return dest if os.path.exists(dest) else ""


def _shot_frames(kind: str, path: str, row: Dict, folder: str) -> List[Tuple[str, str]]:
    """Three cells of one sheet row: start / middle / end of the clip, or the approved picture + two empty cells."""
    # captions in plain ASCII: layout.storyboard draws with PIL's default font, which breaks Vietnamese letters ("đầu" → boxes)
    label = row["label"].replace("·", ".")
    lab = label if row["label"] == f"S{row['idx']:02d}" else f"{label} (#{row['idx']})"
    if kind == "image":
        return [(path, f"{lab} ANH DUYET (chua co clip)"), ("", ""), ("", "")]
    from .ffmpeg_studio import find_ffmpeg, probe_duration
    ffmpeg = find_ffmpeg()
    dur = probe_duration(path) or 2.0
    return [(_grab(ffmpeg, path, t, os.path.join(folder, f"{row['idx']:03d}_{name}.jpg")), f"{lab} {cap}")
            for t, name, cap in ((0.05, "start", "dau"), (dur / 2, "mid", "giua"), (dur - 0.1, "end", "cuoi"))]


def _plan(p: Pipeline, project_id: int, data_dir: str, sequence: Optional[str] = None) -> Dict[str, Dict]:
    """{group: {"rows": shots in order, "media": {idx: (kind, path)}}} for the groups with ≥ 2 shots that have a clip or picture."""
    media = _media(p, project_id, data_dir)
    groups: Dict[str, Dict] = {}
    for row in shot_rows(p, project_id, sequence):
        g = groups.setdefault(row["sequence"], {"rows": [], "media": {}})
        g["rows"].append(row)
        if row["idx"] in media:
            g["media"][row["idx"]] = media[row["idx"]]
    return {k: g for k, g in groups.items() if len(g["media"]) >= 2}


def _sheet_count(n_shots: int) -> int:
    return -(-n_shots // SHOTS_PER_SHEET)


def sequence_sheets(p: Pipeline, project_id: int, data_dir: str, sequence: Optional[str] = None,
                    out_dir: Optional[str] = None) -> Dict[str, Dict]:
    """{group: {"rows": [...], "sheets": [png paths, story order]}} — each sheet row = one shot (đầu / giữa / cuối); a shot without
    clip nor approved picture is left out of the sheets but stays in "rows" (the check is told it has no picture)."""
    from . import formats, layout
    folder = out_dir or os.path.join(data_dir, str(project_id), "qc_set", "sequence")
    os.makedirs(folder, exist_ok=True)
    cell = formats.spec(formats.project_aspect(p.project(project_id)))["cell"]
    out = {}
    for g, plan in _plan(p, project_id, data_dir, sequence).items():
        shown = [r for r in plan["rows"] if r["idx"] in plan["media"]]
        safe = "".join(ch if ch.isalnum() else "_" for ch in g)
        sheets = []
        for k in range(_sheet_count(len(shown))):
            frames = []
            for row in shown[k * SHOTS_PER_SHEET:(k + 1) * SHOTS_PER_SHEET]:
                kind, path = plan["media"][row["idx"]]
                frames += _shot_frames(kind, path, row, folder)
            sheets.append(layout.storyboard(frames, os.path.join(folder, f"seq_{safe}_{k + 1}.png"), cols=3, cell=cell))
        out[g] = {"rows": plan["rows"], "sheets": sheets, "shown": [r["idx"] for r in shown]}
    return out


def estimate(p: Pipeline, project_id: int, data_dir: str, sequence: Optional[str] = None) -> Tuple[int, Optional[float]]:
    """(calls, USD ước tính — tính dư; None = chưa có giá) of `check`, without extracting any frame: one call per group, its sheets as
    pictures (cost.llm_estimate: measured average of the stage once the ledger has calls, else LLM_STAGE_TOKENS)."""
    from . import cost
    plan = _plan(p, project_id, data_dir, sequence)
    total = 0.0
    for g in plan.values():
        one = cost.llm_estimate(p.conn, STAGE, 1, images=_sheet_count(len(g["media"])))
        if one is None:
            return len(plan), None
        total += one
    return len(plan), total


def _validator(known: List[int]):
    def check(obj) -> None:
        claude_tasks._check_set(obj)
        for i, it in enumerate(obj["issues"]):
            if it["idx"] not in known:
                raise llm_io.SchemaError(f"issues[{i}].idx={it['idx']} không thuộc nhóm này (các idx hợp lệ: {known})")
            if not isinstance(it.get("fix", ""), str):
                raise llm_io.SchemaError(f"issues[{i}].fix phải là chuỗi")
    return check


def result_path(data_dir: str, project_id: int) -> str:
    return os.path.join(data_dir, str(project_id), "qc_set", "sequence", "result.json")


def check(p: Pipeline, project_id: int, client, data_dir: str, sequence: Optional[str] = None) -> Dict:
    """Run the logic check (one Claude call per group). Flag off → {"skipped": "flag_off"}: nothing built, nothing called, no file."""
    if not features.on(FLAG):
        return {"skipped": "flag_off"}
    groups = sequence_sheets(p, project_id, data_dir, sequence)
    if not groups:
        raise LlmError("cần ít nhất 2 shot có clip hoặc ảnh đã duyệt trong cùng nhóm để kiểm logic chuỗi", code="not_enough")
    base = [claude_tasks._read("prompts", "22_sequence_logic.md"), prompts.world_bible_text(p, project_id)]
    out = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sequences": {}}
    for g, grp in groups.items():
        rows = [dict(r, has_picture=r["idx"] in grp["shown"]) for r in grp["rows"]]
        prompt = "\n\n---\n\n".join(x for x in base + [claude_tasks._block(f"Các shot của nhóm {g} theo thứ tự truyện", rows)] if x)
        n = len(grp["sheets"])
        images = [(f"Tờ ghép {k + 1}/{n} của nhóm {g} — mỗi hàng là một shot (khung đầu · giữa · cuối), theo thứ tự truyện:", s)
                  for k, s in enumerate(grp["sheets"])]
        obj = claude_tasks._run(p, project_id, STAGE, prompt, _validator([r["idx"] for r in grp["rows"]]), client, images)
        obj["sheets"] = grp["sheets"]
        out["sequences"][g] = obj
    out["ok"] = all(o.get("ok") and not o.get("issues") for o in out["sequences"].values())
    path = result_path(data_dir, project_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    from . import continuity_shadow          # V3.1 M4.3 (cờ continuity_shadow, TẮT): expected + đồ thị phụ thuộc, chỉ ghi — never raises
    continuity_shadow.run(p, project_id, data_dir, out)
    from . import continuity_state           # V3.1 M3.4 (cờ continuity_state, TẮT): expected/observed/resolved, chỉ ghi — never raises
    continuity_state.run(p, project_id, data_dir)
    return out


def last_result(data_dir: str, project_id: int) -> Optional[Dict]:
    try:
        with open(result_path(data_dir, project_id), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None
