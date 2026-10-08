"""Apply the proposals the person approved to the rough cut and render again (docs/KE_HOACH_DUYET_BAN_THO_2026-10-02.md P3 — 0 USD, ffmpeg).

    editor_review.json (P2)  ->  the person ticks proposals  ->  code vets them AGAIN together (the real clock, the Director's `target_s`,
    the length of the source clip)  ->  durations / per-shot music cues  ->  delivery.render(durations=…, edits=…)  ->  final_qc before and
    after (rough cut alone)  ->  not worse: kept, the old cut stays beside it (A/B)   |   worse: the old cut is put back, the new one is kept
    only as a file in output/_editor/ (and in the log) for the person to look at.

What can be applied: `shorten_shot` (the clip's first seconds), `trim_head` (KLD-19: its first N seconds dropped — never a shot with speech /
lip sync / chained on the previous clip's last frame), `extend_hold` (its last frame held), `music_cue` (the shot's `sound.music` for THIS render — the
Director's plan in the database is not touched). Everything else the Editor proposes stays a suggestion (a transition style is one setting
of the whole film; flags unverified are never switched on here). The person decides: a proposal the Director contested is applied only if
the person ticks it.

Limits (CHUAN_XAY_DUNG luật 6): at most MAX_ATTEMPTS applications per review and MAX_ROUNDS kept rounds in a chain; the same render is never
repeated; a failed render puts the old cut back. File names stay the ones people know: FINAL_VIDEO.mp4 is always the current cut; the other
one is kept in output/_editor/.

    plan(p, project_id, data_dir, review, rc, ids) -> {"durations", "music", "fit", "clips", "applied", "refused", "base"}
    apply(p, project_id, data_dir, ids, render_fn=None, qc_fn=None) -> result      revert(p, project_id, data_dir) -> result
"""
import json
import os
import shutil
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

from . import access
from . import delivery, editor_review, final_qc, lineage, rough_cut, shots as shots_mod

MAX_ATTEMPTS = 2          # applications per review (kept or not) — luật 6: gen again only with a changed input, ≤ 2
MAX_ROUNDS = 2            # kept rounds one after another on the same film (review → apply → review → apply)
LOG = "editor_apply.json"
STASH = "_editor"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def log_path(data_dir: str, project_id: int) -> str:
    return os.path.join(data_dir, str(project_id), LOG)


def load_log(data_dir: str, project_id: int) -> List[Dict]:
    try:
        with open(log_path(data_dir, project_id), encoding="utf-8") as f:
            v = json.load(f)
        return v if isinstance(v, list) else []
    except (OSError, ValueError):
        return []


def _save_log(data_dir: str, project_id: int, log: List[Dict]) -> None:
    os.makedirs(os.path.dirname(log_path(data_dir, project_id)), exist_ok=True)
    with open(log_path(data_dir, project_id), "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=1)


def _manifest(row) -> Dict:
    try:
        v = json.loads(row["manifest"] or "{}")
    except (TypeError, ValueError):
        return {}
    return v if isinstance(v, dict) else {}


def base_durations(man: Dict) -> List[float]:
    """The cut lengths the render was given. The manifest timeline is what was cut — the last shot already holds `end_hold`'s extra
    seconds, which the next render would add again, so they are taken off."""
    secs = [float(t.get("seconds") or 0) for t in man.get("timeline") or []]
    held = (man.get("end_hold") or {}).get("held_s")
    if secs and isinstance(held, (int, float)):
        secs[-1] = round(secs[-1] - float(held), 2)
    return secs


# ---- the plan -------------------------------------------------------------------------------------------------------------------------
def plan(p, project_id: int, data_dir: str, review: Dict, rc: Dict, ids: List[str], row=None) -> Dict:
    """What would be rendered for these ids, and what is refused (with the reason). Raises ValueError when nothing can be applied."""
    row = row if row is not None else lineage.latest_output(p.conn, project_id, "final")
    man = _manifest(row)
    clips = [c.get("path") for c in man.get("clips") or []]
    base = base_durations(man)
    if not base or len(clips) != len(base):
        raise ValueError("bản dựng này không ghi đủ clip / thời lượng từng shot — dựng lại ở Bước 5 rồi duyệt lại")
    by_id = {f["id"]: f for f in review.get("proposals") or []}
    refused: List[Dict] = []
    chosen: List[Dict] = []
    for i in ids:
        f = by_id.get(i)
        if f is None:
            refused.append({"id": i, "reason": "không có trong kết quả duyệt"})
        elif not f.get("applicable"):
            refused.append({"id": i, "reason": "chỉ là gợi ý — chưa áp được tự động"})
        else:
            chosen.append(f)
    ok, rejected = editor_review.vet(chosen, rc)                 # again, TOGETHER: the scene totals add up across the ticked proposals
    gone = {r["finding"]["id"]: r["reason"] for r in rejected}
    refused += [{"id": i, "reason": r} for i, r in gone.items()]
    chosen = [f for f in chosen if f["id"] not in gone]
    clock = {s["n"]: s for s in rc.get("shots") or []}
    durations, music, fit, applied, head = list(base), {}, [], [], {}
    for f in chosen:
        n = f["target_shot"]
        sid = (clock.get(n) or {}).get("scene_id")
        if not sid:
            refused.append({"id": f["id"], "reason": f"shot {n} không có dòng cảnh trong CSDL"})
            continue
        if f["action"] in ("shorten_shot", "trim_head", "extend_hold"):
            delta = f["amount"] if f["action"] == "extend_hold" else -f["amount"]
            new = round(durations[n - 1] + delta, 2)
            if new < shots_mod.MIN_SHOT:
                refused.append({"id": f["id"], "reason": f"shot {n} sẽ ngắn hơn {shots_mod.MIN_SHOT:g} s"})
                continue
            durations[n - 1] = new
            if f["action"] == "trim_head":
                head[sid] = round(head.get(sid, 0.0) + f["amount"], 2)   # the render drops these first seconds before fitting the length
            fit.append(sid)                      # the clip of this shot gets a copy of the new length (trim, or its last frame held)
        elif f["action"] == "music_cue":
            music[sid] = f["value"]
        applied.append({k: f[k] for k in ("id", "action", "target_shot", "amount", "value", "observed", "why")})
    if not applied:
        raise ValueError("không còn đề xuất nào áp được: " + "; ".join(f"{r['id']} ({r['reason']})" for r in refused) if refused else
                         "chưa chọn đề xuất nào")
    return {"durations": durations, "music": music, "fit": fit, "head": head, "clips": clips, "applied": applied, "refused": refused,
            "base": base}


# ---- quality gate ---------------------------------------------------------------------------------------------------------------------
def _counts(qc: Dict) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for i in qc.get("issues") or []:
        if i.get("level") in ("block", "warn"):
            out[i["code"]] = out.get(i["code"], 0) + 1
    return out


def _blocks(qc: Dict) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for i in qc.get("issues") or []:
        if i.get("level") == "block":
            out[i["code"]] = out.get(i["code"], 0) + 1
    return out


def qc_worse(before: Dict, after: Dict) -> Tuple[bool, List[str]]:
    """The new cut is worse when any check (blocking or warning) fires more often than on the old one — new kinds count as more —
    or (S14.4 C1b) when a check fires at a heavier level: more BLOCKING ones of a code, even with the same total (warn → block)."""
    a, b = _counts(before), _counts(after)
    why = [f"{code}: {a.get(code, 0)} → {n}" for code, n in sorted(b.items()) if n > a.get(code, 0)]
    ab, bb = _blocks(before), _blocks(after)
    why += [f"{code}: mức chặn {ab.get(code, 0)} → {n}" for code, n in sorted(bb.items())
            if n > ab.get(code, 0) and not b.get(code, 0) > a.get(code, 0)]
    return bool(why), why


# ---- files: FINAL_VIDEO.mp4 is the current cut, the other one waits in output/_editor ----------------------------------------------------
def _stash(p, data_dir: str, project_id: int, row, tag: str, drop: bool = False) -> str:
    """Copy the file of an output row aside. The row is pointed at the copy (a later render overwrites the original name), or, with
    `drop`, removed — `outputs.kind` is a closed list, so a cut that is not kept lives only as the file in output/_editor/ + the log."""
    d = os.path.join(delivery.output_dir(data_dir, project_id), STASH)
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, f"{tag}_{row['id']}.mp4")
    shutil.copy2(row["path"], dst)
    if drop:
        p.conn.execute("DELETE FROM outputs WHERE id=?", (row["id"],))
    else:
        p.conn.execute("UPDATE outputs SET path=? WHERE id=?", (dst, row["id"]))
    p.conn.commit()
    return dst


def _put_back(p, data_dir: str, project_id: int, old_row, old_path: str, out_path: str) -> int:
    """The old cut becomes the current one again: its file back under the known name, a new `final` record with its manifest."""
    shutil.copy2(old_path, out_path)
    return delivery.record(p, project_id, "final", out_path, None, _manifest(old_row))


def _total(man: Dict) -> float:
    return round(sum(float(t.get("seconds") or 0) for t in man.get("timeline") or []), 2)


# ---- apply / revert -------------------------------------------------------------------------------------------------------------------
def apply(p, project_id: int, data_dir: str, ids: List[str], render_fn: Optional[Callable] = None, qc_fn: Optional[Callable] = None) -> Dict:
    """Apply the ticked proposals. Raises ValueError (nothing changed) when the review is old, the limits are used up, or nothing can be
    applied; a render that fails puts the old cut back and raises. Returns the outcome (also appended to data/<pid>/editor_apply.json)."""
    access.need_edit(p, project_id, "áp đề xuất dựng")
    render_fn = render_fn or delivery.render
    qc_fn = qc_fn or (lambda: final_qc.run(p, project_id, data_dir, layers=False))
    with delivery.render_lock(data_dir, project_id):
        review = editor_review.load(data_dir, project_id)
        if not review or not review.get("proposals"):
            raise ValueError("chưa có kết quả duyệt bản thô để áp")
        rc = rough_cut.build(p, project_id, data_dir)
        if review.get("rough_cut") != rc["fingerprint"]:
            raise ValueError("kết quả duyệt thuộc bản dựng / ý đồ cũ — duyệt lại trước khi áp")
        old = lineage.latest_output(p.conn, project_id, "final")
        meta = _manifest(old).get("editor_apply") or {}
        if int(meta.get("round") or 0) >= MAX_ROUNDS:
            raise ValueError(f"đã áp {MAX_ROUNDS} vòng liên tiếp trên phim này — dừng; xem hai bản và chọn, hoặc dựng lại từ Bước 5")
        log = load_log(data_dir, project_id)
        if sum(1 for e in log if e.get("review") == review["fingerprint"]) >= MAX_ATTEMPTS:
            raise ValueError(f"đã áp {MAX_ATTEMPTS} lần cho kết quả duyệt này — đổi đầu vào (duyệt lại) trước khi áp tiếp")
        pl = plan(p, project_id, data_dir, review, rc, ids, old)
        before = qc_fn()
        out_path = old["path"]
        old_path = _stash(p, data_dir, project_id, old, "A")
        info = {"round": int(meta.get("round") or 0) + 1, "from_output": old["id"], "root_output": meta.get("root_output", old["id"]),
                "review": review["fingerprint"], "applied": pl["applied"], "durations_before": pl["base"], "durations_after": pl["durations"]}
        try:
            new = render_fn(p, project_id, data_dir, "auto", clips=pl["clips"], durations=pl["durations"], edits={"music": pl["music"], "fit": pl["fit"], "head": pl.get("head") or {}, "meta": info})
        except Exception as e:  # noqa: BLE001 - whatever stopped the render: the old cut goes back, nothing half-applied stays current
            restored = _put_back(p, data_dir, project_id, old, old_path, out_path)
            log.append({"at": _now(), "review": review["fingerprint"], "ids": ids, "kept": False, "error": str(e)[:300], "restored_output": restored})
            _save_log(data_dir, project_id, log)
            raise
        after = qc_fn()
        worse, why = qc_worse(before, after)
        new_row = p.conn.execute("SELECT * FROM outputs WHERE id=?", (new["output_id"],)).fetchone()
        result = {"round": info["round"], "kept": not worse, "worse": worse, "why": why, "applied": pl["applied"], "refused": pl["refused"],
                  "before": {"blocks": before.get("blocks"), "warns": before.get("warns"), "seconds": _total(_manifest(old))},
                  "after": {"blocks": after.get("blocks"), "warns": after.get("warns"), "seconds": _total(_manifest(new_row))},
                  "from_output": old["id"], "to_output": new["output_id"], "a_path": old_path}
        if worse:                                     # not better, so not kept: the old cut is current again, the new one waits as a file in output/_editor/
            result["b_path"] = _stash(p, data_dir, project_id, new_row, "B", drop=True)
            result["restored_output"] = _put_back(p, data_dir, project_id, old, old_path, out_path)
            result["to_output"] = None            # the row is gone (SQLite may give its number to the restored one): the file is `b_path`
        else:
            result["b_path"] = out_path
        log.append({"at": _now(), "review": review["fingerprint"], "ids": ids, "kept": not worse, "round": info["round"],
                    "from_output": old["id"], "to_output": new["output_id"], "why": why})
        _save_log(data_dir, project_id, log)
        return result


def revert(p, project_id: int, data_dir: str) -> Dict:
    """The person looked at both cuts and wants the old one: put it back as the current cut (the new one stays as a file in output/_editor/)."""
    with delivery.render_lock(data_dir, project_id):
        cur = lineage.latest_output(p.conn, project_id, "final")
        meta = _manifest(cur).get("editor_apply") if cur is not None else None
        if not meta:
            raise ValueError("bản dựng hiện tại không phải bản đã áp đề xuất — không có gì để quay về")
        old = p.conn.execute("SELECT * FROM outputs WHERE id=?", (meta["from_output"],)).fetchone()
        if old is None or not os.path.exists(old["path"]):
            raise ValueError("không còn file của bản trước — dựng lại ở Bước 5")
        out_path = cur["path"]
        b_path = _stash(p, data_dir, project_id, cur, "B", drop=True)
        restored = _put_back(p, data_dir, project_id, old, old["path"], out_path)
        log = load_log(data_dir, project_id)
        log.append({"at": _now(), "review": meta.get("review"), "reverted_by_person": True, "from_output": cur["id"], "restored_output": restored})
        _save_log(data_dir, project_id, log)
        return {"restored_output": restored, "b_path": b_path}


def lines(res: Optional[Dict]) -> List[str]:
    """What the screen says about one application."""
    if not res:
        return []
    b, a = res["before"], res["after"]
    out = [("✅ Đã áp " if res["kept"] else "↩️ Không giữ (tệ hơn) — đã trả lại bản cũ · ") + f"{len(res['applied'])} đề xuất (vòng {res['round']}) · "
           f"{b['seconds']:g} s → {a['seconds']:g} s · kiểm bản dựng: {b['blocks']} chặn / {b['warns']} cần xem → {a['blocks']} / {a['warns']}"]
    out += [f"   tệ hơn ở: {w}" for w in res.get("why") or []]
    out += [f"   không áp được {r['id']}: {r['reason']}" for r in res.get("refused") or []]
    return out
