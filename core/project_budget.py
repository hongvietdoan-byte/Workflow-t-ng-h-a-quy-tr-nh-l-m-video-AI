"""The project's budget, split by stage and LOCKED once a person approves it (user 2026-09-28: "đặt trần rõ ràng, lock khoá lại, tránh
chi phí bị trôi không giới hạn"; trial #8: the run button estimated 12.45 USD, 16.38 were spent before any video — redraws, tests,
methods dropped half way, QC re-judging).

  propose   code (not Claude) computes it right after the Director's shot table: every stage's money already spent + what is left to
            make, with the measured redo share and a margin; video models whose price has no exact source get UNVERIFIED_MARGIN
  approve   the person approves → locked: every paid call checks its stage cap and the total BEFORE it is sent (images/clips in the
            runners, Claude in llm_runner with the holds of calls in flight); at a cap it stops — only a person raises a cap, with a
            reason that is kept
  target    optional: the money the person wants to spend; the Director gets it as an input (fewer lip-sync shots, fewer seconds …)
            and a proposal over it is said before any picture is paid

Test / acceptance runs (tools/experiments) are not production: they carry their own spend_cap and are counted under claude_other.
Audio has no USD price yet: it stays capped by count (core.budget.check_audio)."""
from . import access
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

from . import features

FEATURE = "project_budget"
STAGES = {"images": "Ảnh", "videos": "Video", "claude_director": "Claude — Director", "claude_qc": "Claude — QC",
          "claude_motion": "Claude — motion", "claude_other": "Claude — khác"}
IMAGE_REDO = 0.35          # #8: 11 of 33 frames redrawn in the first pass (+ scenes' wide pictures)
VIDEO_REDO = 0.30
LLM_MARGIN = 1.3
OTHER_CLAUDE_USD = 0.20    # translations, checks, small calls
UNVERIFIED_MARGIN = 1.25   # a price without an exact source (Seedance on ClipAI: the provider returns cost 0, finding 17)


def enabled() -> bool:
    return features.on(FEATURE)


def _key(pid: int) -> str:
    return f"project_budget:{pid}"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def get(conn, pid: int) -> Optional[Dict]:
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (_key(pid),)).fetchone()
    try:
        return json.loads(row[0]) if row else None
    except ValueError:
        return None


def _save(conn, pid: int, data: Dict) -> Dict:
    conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (_key(pid), json.dumps(data, ensure_ascii=False)))
    conn.commit()
    return data


def claude_stage(tag: Optional[str]) -> str:
    t = str(tag or "")
    if t.startswith("director") or t == "screenwriter":       # S11.1: the Biên kịch writes before the Director, same budget line
        return "claude_director"
    if t in ("qc", "qc_agent", "video", "video_qc", "video_analysis", "storyboard_review", "check", "scene_qc", "editor") or t.startswith("qc"):
        # "editor" (rough-cut review, P2): a check of the finished cut, same line as the other checks, not "khác" (cap 0.20)
        # 28/09: video_analysis (the clip QC) fell into claude_other (cap 0.20) and the lock refused every clip QC
        return "claude_qc"
    if t.startswith("motion") or t == "translate":
        return "claude_motion"
    return "claude_other"


def unverified(pricing: Dict, model: str) -> bool:
    return any(re.fullmatch(p.replace("*", ".*"), str(model or "")) for p in pricing.get("_unverified_models") or [])


def spent_by_stage(conn, pid: int) -> Dict[str, float]:
    """Money spent by this project per stage since its starting point: the ledger total minus the baseline an Owner reset set
    (core.money_reset), never below 0. Without a baseline it is the ledger total."""
    base = (get(conn, pid) or {}).get("baseline") or {}
    raw = ledger_by_stage(conn, pid)
    return {k: round(max(0.0, v - float(base.get(k) or 0.0)), 4) for k, v in raw.items()}


def ledger_by_stage(conn, pid: int) -> Dict[str, float]:
    """Money already spent by this project, per stage (the ledger rows carry the project), ignoring any reset baseline."""
    from . import budget, cost
    pricing = cost.load_pricing()
    out = {k: 0.0 for k in STAGES}
    for r in conn.execute("SELECT * FROM usage_events WHERE project_id=? AND provider NOT LIKE 'mock%'", (pid,)).fetchall():
        usd = budget.row_usd(pricing, r) or 0.0
        if r["kind"] == "image":
            out["images"] += usd
        elif r["kind"] == "llm":
            out[claude_stage(r["stage"] if "stage" in r.keys() else None)] += usd
        elif r["kind"] == "video":
            out["videos"] += usd
    return {k: round(v, 4) for k, v in out.items()}


def remaining(p, pid: int) -> Dict[str, float]:
    """What is still to make, priced by code from the shot table and the price table (cost.estimate_run's parts), with the redo shares
    and margins — per stage."""
    from . import cost, model_router, qc_agent, qc_scene
    pricing = cost.load_pricing()
    conn = p.conn
    est = cost.estimate_run(p, pid, pricing)
    rows = model_router.plan(conn, pid, pricing)
    made = {r["scene_id"] for r in conn.execute("SELECT scene_id FROM jobs WHERE project_id=? AND type='video_gen' AND state IN"
                                                " ('succeeded','approved','running','queued','pending_review')", (pid,))}
    vid = sum((r["cost"] or 0) * (UNVERIFIED_MARGIN if unverified(pricing, r["model"]) else 1.0)
              for r in rows if r["scene_id"] not in made)
    director_done = bool(conn.execute("SELECT 1 FROM characters WHERE project_id=? AND TRIM(description)!=''", (pid,)).fetchone())
    n_img = est["counts"]["images"]
    qc = cost.llm_estimate(conn, "qc", cost._picture_qc_calls(conn, pid, n_img) + est["counts"]["clips"], pricing, images=2) or 0.0
    if n_img and qc_agent.enabled():
        qc += sum(qc_agent.scene_cap(n) for n in _frames_per_scene(conn, pid)) if qc_scene.enabled() else 0.0
    from . import qc_team
    if n_img and qc_team.enabled() and qc_scene.enabled():
        qc += qc_team.FRAME_USD * n_img * (1 + IMAGE_REDO)
    return {"images": round((est["images"] or 0.0) * (1 + IMAGE_REDO), 2),
            "videos": round(vid * (1 + VIDEO_REDO), 2),
            "claude_director": 0.0 if director_done else round((cost.llm_estimate(conn, "director", 1, pricing) or 0.0) * LLM_MARGIN, 2),
            "claude_qc": round(qc * LLM_MARGIN, 2),
            "claude_motion": round(((cost.llm_estimate(conn, "motion", 1 if est["counts"]["clips"] else 0, pricing) or 0.0)
                                    + (_translate_worst(conn, pid) if est["counts"]["clips"] else 0.0)) * LLM_MARGIN, 2),
            "claude_other": OTHER_CLAUDE_USD}


def _translate_worst(conn, pid: int) -> float:
    """The one translation call of the motion stage (claude_tasks.translate_motion_fields) at its WORST case — the lock checks the
    worst case, so a cap below it refuses the call (#8 2026-09-28: cap 0.10, the call's worst case 0.33, clips then refused for
    Vietnamese text)."""
    from . import claude_tasks, llm_runner
    todo = 0
    for (raw,) in conn.execute("SELECT data FROM scenes WHERE project_id=?", (pid,)):
        d = json.loads(raw or "{}")
        if any(d.get(k) and claude_tasks._vi(d[k]) for k in claude_tasks.TRANSLATE_KEYS):
            todo += 1
    if not todo:
        return 0.0
    model = cost_model()
    out = int(llm_runner.stage_settings("translate").get("max_tokens") or 8000)
    return round(llm_runner._price(model, "input", todo * 400) * 1.25 + llm_runner._price(model, "output", out), 3)


def cost_model() -> str:
    from . import cost
    return cost.llm_model()


def _frames_per_scene(conn, pid: int) -> List[int]:
    n: Dict = {}
    for (raw,) in conn.execute("SELECT data FROM scenes WHERE project_id=?", (pid,)):
        s = json.loads(raw or "{}").get("story_scene")
        n[s] = n.get(s, 0) + 1
    return list(n.values())


def propose(p, pid: int) -> Dict:
    """{stage: {"spent", "left_estimate", "cap"}, "total": …} — not saved (see approve)."""
    spent = spent_by_stage(p.conn, pid)
    left = remaining(p, pid)
    stages = {k: {"spent": spent[k], "left_estimate": left[k], "cap": round(spent[k] + left[k], 2)} for k in STAGES}
    return {"stages": stages, "total": round(sum(v["cap"] for v in stages.values()), 2)}


def approve(p, pid: int, who: str, proposal: Optional[Dict] = None) -> Dict:
    access.need_edit(p, pid, "duyệt & khóa ngân sách")
    prop = proposal or propose(p, pid)
    old = get(p.conn, pid) or {}
    data = {"caps": {k: v["cap"] for k, v in prop["stages"].items()}, "total": prop["total"], "approved_by": who, "approved_at": _now(),
            "locked": True, "raises": old.get("raises") or [], "target": old.get("target"), "proposal": prop,
            "baseline": old.get("baseline") or {}, "baseline_at": old.get("baseline_at"), "resets": old.get("resets") or []}
    return _save(p.conn, pid, data)


def set_target(conn, pid: int, usd: Optional[float]) -> Dict:
    data = get(conn, pid) or {}
    data["target"] = float(usd) if usd else None
    return _save(conn, pid, data)


def raise_cap(conn, pid: int, stage: str, add_usd: float, who: str, why: str) -> Dict:
    """Only a person raises a locked cap, with a reason (kept)."""
    if stage not in STAGES:
        raise ValueError(f"không có khâu {stage}")
    if not str(why or "").strip():
        raise ValueError("nâng trần phải có lý do")
    data = get(conn, pid)
    if not data or not data.get("locked"):
        raise ValueError("dự án chưa có ngân sách đã duyệt")
    data["caps"][stage] = round(data["caps"][stage] + float(add_usd), 2)
    data["total"] = round(sum(data["caps"].values()), 2)
    data["raises"].append({"at": _now(), "who": who, "stage": stage, "add_usd": float(add_usd), "why": why})
    return _save(conn, pid, data)


def check(conn, pid: Optional[int], stage: str, usd: float) -> Optional[str]:
    """A reason not to pay `usd` more for this stage of the project (its approved, locked budget; Claude calls in flight count), else
    None. No approved budget → no project lock (the global caps still apply)."""
    if pid is None or not enabled():
        return None
    data = get(conn, pid)
    if not data or not data.get("locked"):
        return None
    from . import budget
    spent = spent_by_stage(conn, pid)
    inflight = budget.held(conn, pid, stage) if stage.startswith("claude") else 0.0
    cap = float(data["caps"].get(stage, 0.0))
    if spent.get(stage, 0.0) + inflight + usd > cap + 1e-9:
        return (f"chạm trần khâu '{STAGES.get(stage, stage)}' của dự án: đã chi ≈ ${spent.get(stage, 0.0):.2f}"
                + (f" + đang chạy ≈ ${inflight:.2f}" if inflight else "") + f", lần này ≈ ${usd:.2f}, trần ${cap:.2f} — dừng. "
                "Chỉ người được nâng trần (Bước 1 → 💵 Ngân sách dự án, kèm lý do)")
    if sum(spent.values()) + budget.held(conn, pid) + usd > float(data["total"]) + 1e-9:
        return (f"chạm TỔNG ngân sách dự án: đã chi ≈ ${sum(spent.values()):.2f}, lần này ≈ ${usd:.2f}, tổng ${data['total']:.2f} — dừng")
    return None


def gate_reason(p, pid: int) -> Optional[str]:
    """Why the automatic run must wait before paying for pictures: the budget is not approved yet, or the proposal is over the
    person's target."""
    if not enabled():
        return None
    data = get(p.conn, pid)
    if data and data.get("locked"):
        return None
    prop = propose(p, pid)
    over = ""
    if data and data.get("target") and prop["total"] > float(data["target"]):
        over = f" — đề xuất ≈ ${prop['total']:.2f} VƯỢT mục tiêu ${float(data['target']):.2f}: bớt shot khớp môi / giây video / shot, rồi tính lại"
    return f"Chờ duyệt ngân sách dự án (đề xuất ≈ ${prop['total']:.2f}){over} — Bước 1 → 💵 Ngân sách dự án"


def director_note(conn, pid: int) -> str:
    """The budget as an input of the Director (a sentence for its prompt), or ''."""
    data = get(conn, pid) or {}
    target = data.get("target")
    if not target:
        return ""
    from . import cost
    pricing = cost.load_pricing()
    per_s = cost.clip_price(pricing, "dreamina-seedance-2-0-fast-260128", "720p", 1) or 0.12
    return (f"\n\n# Ngân sách (người dùng đặt)\nTổng ≈ {float(target):.2f} USD cho cả dự án (ảnh, video, Claude). Video ≈ {per_s:.2f} USD mỗi giây "
            f"đã trả tiền (+ ~30 % làm lại); ảnh ≈ 0,05 USD mỗi khung (+ ~35 % vẽ lại); shot khớp môi đắt hơn và hay phải làm lại. "
            "Chia shot sao cho tổng nằm trong ngân sách: ít shot khớp môi, gộp shot liền mạch, không kéo dài giây thừa. Ghi vào "
            "tradeoffs những gì đã bớt vì ngân sách.")
