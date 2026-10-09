"""The project's budget, split by stage and LOCKED once a person approves it (user 2026-09-28: "đặt trần rõ ràng, lock khoá lại, tránh
chi phí bị trôi không giới hạn"; trial #8: the run button estimated 12.45 USD, 16.38 were spent before any video — redraws, tests,
methods dropped half way, QC re-judging).

  propose   code (not Claude) computes it right after the Director's shot table: every stage's money already spent + what is left to
            make, with the measured redo share and a margin; video models whose price has no exact source get UNVERIFIED_MARGIN
  approve   the person approves → locked: every paid call compares its stage line and the total BEFORE it is sent (images/clips
            in the runners, Claude in llm_runner with the holds of calls in flight). Chính sách tiền 04/10 (S14.16): past a line the
            send WARNS (`warning`, core.money_policy) and goes — nothing is refused for money; the Owner sets the planned amount
            (core.money_reset.set_planned); a person may still raise a line, with a reason that is kept
  target    optional: the money the person wants to spend; the Director gets it as an input (fewer lip-sync shots, fewer seconds …)
            and a proposal over it is said before any picture is paid
  levels    (user 08/10) only "Tự chạy trong trần" (core.automation 'auto' — nobody approves pictures) asks for the approval & lock
            (`needs_lock`): the run waits for it before the first picture and, once locked, WAITS again when a stage line or the total
            is reached (`run_over`, a person raises the line with a reason). "Tôi duyệt hết" / "Duyệt cổng chính" only SHOW the
            estimate (`estimate_view`) — no button, no gate. A finished project asks for nothing (`finished`).
  redo      the redo share of pictures / clips is MEASURED from the machine retries of the other projects (`redo_shares`: jobs with
            retry_count > 0 per approved shot), between the old fixed share and the automatic regeneration limit — enough for the run
            to finish, far below the worst case of every shot redone to its limit.

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
          "claude_motion": "Claude — motion", "claude_other": "Claude — khác", "claude_chat": "chat Kịch bản"}
IMAGE_REDO = 0.35          # #8: 11 of 33 frames redrawn in the first pass (+ scenes' wide pictures) — the FLOOR of the measured share
VIDEO_REDO = 0.30
REDO_MIN_SAMPLE = 10       # approved shots of other projects needed before the measured share replaces the fixed one
LLM_MARGIN = 1.3
OTHER_CLAUDE_USD = 0.20    # translations, checks, small calls
UNVERIFIED_MARGIN = 1.25   # a price without an exact source (Seedance on ClipAI: the provider returns cost 0, finding 17)


def enabled() -> bool:
    return features.on(FEATURE)


def needs_lock(p, pid: int) -> bool:
    """Only the level "Tự chạy trong trần" (the person's operating mode is automatic QC) asks for the approval & lock (user 08/10)."""
    if not enabled():
        return False
    from . import automation
    try:
        return automation.effective_mode(p, pid) == "auto"
    except Exception:  # noqa: BLE001 - a project row that cannot be read asks for nothing
        return False


def finished(conn, pid: int) -> bool:
    """Every shot has an up-to-date clip that can be used: nothing left to pay for, so nothing to approve."""
    from . import lineage
    s = lineage.summary(conn, pid)
    return bool(s["total"]) and s["videos"][0] >= s["total"]


def redo_shares(conn, exclude_pid: Optional[int] = None) -> Dict:
    """Machine retries per approved shot, measured on the other projects (retry_count rises only for machine-made tries, core.pipeline
    AUTO_REGEN_LIMIT), kept between the fixed share and the regeneration limit. {"images", "videos", "measured": {kind: (retries,
    approved) or None}}."""
    from .pipeline import AUTO_REGEN_LIMIT
    out, measured = {}, {}
    for key, kind, floor in (("images", "image_gen", IMAGE_REDO), ("videos", "video_gen", VIDEO_REDO)):
        row = conn.execute("SELECT SUM(retry_count > 0), SUM(state='approved') FROM jobs WHERE type=? AND project_id != ?",
                           (kind, -1 if exclude_pid is None else exclude_pid)).fetchone()
        retries, ok = int(row[0] or 0), int(row[1] or 0)
        if ok >= REDO_MIN_SAMPLE:
            measured[key] = (retries, ok)
            out[key] = round(min(float(AUTO_REGEN_LIMIT[kind]), max(floor, retries / ok)), 2)
        else:
            measured[key] = None
            out[key] = floor
    out["measured"] = measured
    return out


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
    if t == "script_chat":
        return "claude_chat"
    if t.startswith("director") or t in ("screenwriter", "asset_checklist", "script_ocr"):   # S11.1 Biên kịch / S14.23 bảng kê: before the Director, same line
        return "claude_director"
    if t in ("qc", "qc_agent", "video", "video_qc", "video_analysis", "storyboard_review", "check", "scene_qc", "editor") or t.startswith("qc") \
            or t.startswith("trainee_qc"):     # 🎓 Tổ QC học việc (B5 08/10): same QC line, its own tag in the ledger
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


def _stage_of(r) -> Optional[str]:
    if r["kind"] == "image":
        return "images"
    if r["kind"] == "llm":
        return claude_stage(r["stage"] if "stage" in r.keys() else None)
    if r["kind"] == "video":
        return "videos"
    return None


def _ledger(conn, pid: int, since: Optional[str] = None):
    """(USD per stage, count of rows WITHOUT a price per stage) — a row the price table does not know is not $0 (T6, S14.1)."""
    from . import budget, cost
    pricing = cost.load_pricing()
    out = {k: 0.0 for k in STAGES}
    unpriced = {k: 0 for k in STAGES}
    for r in conn.execute("SELECT * FROM usage_events WHERE project_id=? AND provider NOT LIKE 'mock%'", (pid,)).fetchall():
        stage = _stage_of(r)
        if stage is None:
            continue
        usd = budget.row_usd(pricing, r)
        if usd is None:
            if not since or str(r["at"] or "") > str(since):
                unpriced[stage] += 1
            continue
        out[stage] += usd
    return {k: round(v, 4) for k, v in out.items()}, unpriced


def ledger_by_stage(conn, pid: int) -> Dict[str, float]:
    """Money already spent by this project, per stage (the ledger rows carry the project), ignoring any reset baseline. Rows without
    a price add nothing here — they are counted by unpriced_by_stage and a locked project refuses that stage (check)."""
    return _ledger(conn, pid)[0]


def unpriced_by_stage(conn, pid: int) -> Dict[str, int]:
    """How many ledger rows of this project have NO price in data/pricing.json, per stage (their money is unknown, not 0) — since the
    Owner's reset point (core.money_reset baseline_at) when there is one: a reset also clears the rows before it."""
    return _ledger(conn, pid, since=(get(conn, pid) or {}).get("baseline_at"))[1]


def remaining(p, pid: int, shares: Optional[Dict] = None) -> Dict[str, float]:
    """What is still to make, priced by code from the shot table and the price table (cost.estimate_run's parts), with the MEASURED
    redo shares (`redo_shares`) and margins — per stage. Nothing left to make → no Claude "other" money either."""
    from . import cost, model_router, qc_agent, qc_scene
    pricing = cost.load_pricing()
    conn = p.conn
    shares = shares or redo_shares(conn, pid)
    ri, rv = shares["images"], shares["videos"]
    est = cost.estimate_run(p, pid, pricing)
    rows = model_router.plan(conn, pid, pricing)
    made = {r["scene_id"] for r in conn.execute("SELECT scene_id FROM jobs WHERE project_id=? AND type='video_gen' AND state IN"
                                                " ('succeeded','approved','running','queued','pending_review')", (pid,))}
    vid = sum((r["cost"] or 0) * (UNVERIFIED_MARGIN if unverified(pricing, r["model"]) else 1.0)
              for r in rows if r["scene_id"] not in made)
    director_done = bool(conn.execute("SELECT 1 FROM characters WHERE project_id=? AND TRIM(description)!=''", (pid,)).fetchone())
    n_img, n_clips = est["counts"]["images"], est["counts"]["clips"]
    qc_calls = round(cost._picture_qc_calls(conn, pid, n_img) * (1 + ri) + n_clips * (1 + rv))      # every retake is judged again
    qc = cost.llm_estimate(conn, "qc", qc_calls, pricing, images=2) or 0.0
    if n_img and qc_agent.enabled():
        qc += sum(qc_agent.scene_cap(n) for n in _frames_per_scene(conn, pid)) if qc_scene.active() else 0.0
    from . import qc_team
    if n_img and qc_team.active() and qc_scene.active():             # 🎓 học việc spends the same
        qc += qc_team.FRAME_USD * n_img * (1 + ri)
    return {"images": round((est["images"] or 0.0) * (1 + ri), 2),
            "videos": round(vid * (1 + rv), 2),
            "claude_director": round((0.0 if director_done else (cost.llm_estimate(conn, "director", 1, pricing) or 0.0) * LLM_MARGIN)
                                     + (est.get("rewrite") or 0.0), 2),     # S14.17: the Director's rewrites before retakes (flag on)
            "claude_qc": round(qc * LLM_MARGIN, 2),
            "claude_motion": round(((cost.llm_estimate(conn, "motion", 1 if n_clips else 0, pricing) or 0.0)
                                    + (_translate_worst(conn, pid) if n_clips else 0.0)) * LLM_MARGIN, 2),
            "claude_other": OTHER_CLAUDE_USD if (n_img or n_clips or not director_done) else 0.0,
            "claude_chat": cost.llm_estimate(conn, "script_chat", 1, pricing) or 0.0}


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
    """{stage: {"spent", "left_estimate", "cap"}, "total": …, "shares": redo_shares} — not saved (see approve)."""
    spent = spent_by_stage(p.conn, pid)
    shares = redo_shares(p.conn, pid)
    left = remaining(p, pid, shares)
    stages = {k: {"spent": spent[k], "left_estimate": left[k], "cap": round(spent[k] + left[k], 2)} for k in STAGES}
    return {"stages": stages, "total": round(sum(v["cap"] for v in stages.values()), 2), "shares": shares}


def shares_text(shares: Dict) -> str:
    """'ảnh +76 % (đo 68/90 lượt), video +92 % (đo 59/64)' — where the redo share comes from."""
    parts = []
    for key, name in (("images", "ảnh"), ("videos", "video")):
        m = (shares.get("measured") or {}).get(key)
        src = f"đo từ dự án trước: {m[0]} lượt tự gen lại / {m[1]} shot đạt" if m else "mặc định, chưa đủ dữ liệu đo"
        parts.append(f"{name} +{shares[key] * 100:.0f} % ({src})")
    return ", ".join(parts)


def estimate_view(p, pid: int) -> Dict:
    """The ONE estimate shown everywhere (user 08/10): {"total" (= the cap proposed / locked: spent + what is left with the measured
    redo), "base" (one take of everything, cost_summary), "spent", "shares", "prop", "summary", "md" (an explanation of the two
    numbers, Markdown-safe), "line"}."""
    prop = propose(p, pid)
    try:
        cs = cost_summary(p, pid)
    except Exception:  # noqa: BLE001 - the estimate still shows; only the one-take figure is missing
        cs = None
    spent = round(sum(v["spent"] for v in prop["stages"].values()), 2)
    text = (f"Dự tính cả dự án ≈ ${prop['total']:.2f} = đã chi ${spent:.2f} + phần còn lại có cộng gen lại theo tỷ lệ "
            f"{shares_text(prop['shares'])}, Claude ×{LLM_MARGIN}")
    if cs is not None:
        text += (f". Nếu mọi ảnh / clip đạt ngay lần đầu: ≈ ${cs['total']:.2f} (Ảnh ${cs['images']:.2f} · Video ${cs['videos']:.2f} · "
                 f"Claude ${cs['claude']:.2f}" + (f" · Âm thanh ${cs['audio']:.2f}" if cs.get("audio") is not None
                                                 else f" · Âm thanh {cs['audio_items']} lượt chưa có giá") + ")")
    return {"total": prop["total"], "base": None if cs is None else cs["total"], "spent": spent, "shares": prop["shares"], "prop": prop,
            "summary": cs, "text": text, "md": md_safe(text), "line": f"Dự tính tổng ≈ ${prop['total']:.2f} · đã chi ${spent:.2f}"}


def run_over(p, pid: int, stage: str) -> Optional[str]:
    """At "Tự chạy trong trần" with the budget locked: why the automatic run must WAIT before sending more of `stage` — the stage line
    or the total is reached (user 08/10: "đúng cơ chế duyệt và khóa trần"). A person raises the line (with a reason) and presses
    Tiếp tục. Sends a person asks for are not stopped here (they warn, S14.16)."""
    if not needs_lock(p, pid):
        return None
    data = get(p.conn, pid)
    if not data or not data.get("locked"):
        return None
    spent = spent_by_stage(p.conn, pid)
    cap = float((data.get("caps") or {}).get(stage, 0.0))
    how = " — chạy tự động dừng trước khi gửi thêm. Nâng trần (kèm lý do) ở Bước 1 → 💵 Ngân sách dự án rồi bấm Tiếp tục"
    if spent.get(stage, 0.0) >= cap:
        return f"Chạm trần khâu {STAGES.get(stage, stage)}: đã chi ${spent.get(stage, 0.0):.2f} / trần ${cap:.2f}" + how
    total = planned(p.conn, pid)
    if total is not None and sum(spent.values()) >= total:
        return f"Chạm trần TỔNG dự án: đã chi ${sum(spent.values()):.2f} / trần ${total:.2f}" + how
    return None


def approve(p, pid: int, who: str, proposal: Optional[Dict] = None) -> Dict:
    access.need_edit(p, pid, "duyệt & khóa ngân sách")
    prop = proposal or propose(p, pid)
    old = get(p.conn, pid) or {}
    data = {"caps": {k: v["cap"] for k, v in prop["stages"].items()}, "total": prop["total"], "approved_by": who, "approved_at": _now(),
            "locked": True, "raises": old.get("raises") or [], "target": old.get("target"), "proposal": prop,
            "baseline": old.get("baseline") or {}, "baseline_at": old.get("baseline_at"), "resets": old.get("resets") or []}
    return _save(p.conn, pid, data)


def set_target(conn, pid: int, usd: Optional[float], p=None) -> Dict:
    if p is not None:
        access.need_edit(p, pid, "đặt mục tiêu ngân sách")
    data = get(conn, pid) or {}
    data["target"] = float(usd) if usd else None
    return _save(conn, pid, data)


def raise_cap(conn, pid: int, stage: str, add_usd: float, who: str, why: str, p=None) -> Dict:
    """Only a person raises a locked cap, with a reason (kept)."""
    if p is not None:
        access.need_edit(p, pid, "nâng trần ngân sách")
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


PRICE_TABLE_HINT = "thêm giá ở ⚙ → 💵 Tiền → 💲 Bảng giá (hoặc chọn model có giá)"


def check(conn, pid: Optional[int], stage: str, usd: Optional[float]) -> Optional[str]:
    """Kept for the callers' API. Chính sách tiền 04/10 (S14.16, core.money_policy): the project's budget is a PLANNED amount that
    warns (see `warning`) — it never refuses a send any more, so this is always None."""
    return None


def planned(conn, pid: int) -> Optional[float]:
    """The project's planned amount (mức dự tính): the one the Owner set (core.money_reset.set_planned), else the approved total."""
    data = get(conn, pid) or {}
    for key in ("planned", "total"):
        if data.get(key) not in (None, ""):
            return float(data[key])
    return None


def set_planned(conn, pid: int, usd: float) -> Dict:
    """Store the project's planned amount (warning line of the 💵 bar). Used through core.money_reset.set_planned (Owner + reason)."""
    data = get(conn, pid) or {"caps": {}, "locked": False, "raises": [], "resets": []}
    data["planned"] = round(float(usd), 2)
    return _save(conn, pid, data)


def warning(conn, pid: Optional[int], stage: str, usd: Optional[float]) -> Optional[str]:
    """A warning with numbers when paying `usd` more for this stage passes the project's approved amount (stage line or the planned
    total; Claude calls in flight count), or when the price is not known (usd None / ledger rows of this stage without a price), else
    None. The send goes (S14.16)."""
    if pid is None or not enabled():
        return None
    data = get(conn, pid)
    if not data or not data.get("locked"):
        return None
    from . import budget, money_policy
    name = STAGES.get(stage, stage)
    spent = spent_by_stage(conn, pid)
    inflight = budget.held(conn, pid, stage) if stage.startswith("claude") else 0.0
    cap = float((data.get("caps") or {}).get(stage, 0.0))
    here = spent.get(stage, 0.0) + inflight
    unpriced = unpriced_by_stage(conn, pid).get(stage)
    missing = []
    if usd is None:
        missing.append(f"lượt này (khâu {name})")
    if unpriced:
        missing.append(f"{unpriced} dòng sổ chi khâu {name}")
    if missing or money_policy.over(here, cap, usd or 0.0):
        return money_policy.warning_text(f"dự án — khâu '{name}'", here, cap, usd, missing,
                                         extra=PRICE_TABLE_HINT if missing else "")
    total = planned(conn, pid)
    if total is not None and money_policy.over(sum(spent.values()) + budget.held(conn, pid), total, usd or 0.0):
        return money_policy.warning_text("dự án — TỔNG", sum(spent.values()) + budget.held(conn, pid), total, usd)
    return None


def md_safe(text: str) -> str:
    """S14.39: a sentence with USD amounts for st.markdown. Streamlit reads `$a ... $b` as a formula (the 05/10 screenshot showed
    code-like fragments between two amounts), so every `$` is escaped."""
    return str(text).replace("\\$", "$").replace("$", "\\$")


def cost_summary(p, pid: int) -> Dict:
    """Người dùng 04/10 (S14.16): "Đã chi + ước tính phần còn lại" for the approval gate — spent (ledger) + what is left (images,
    videos, audio, Claude), total,
    estimated HIGH (cost.estimate_run + money_policy.estimate: an item without a price at the highest known price × 1,5).
    {"images", "videos", "audio" (None = audio has no price at all: counted by sends), "audio_items", "claude", "total",
    "unpriced" (items estimated without their own price), "text"}."""
    from . import cost, money_policy, voice
    run = cost.estimate_run(p, pid)
    images, videos, claude = float(run["images"] or 0), float(run["videos"] or 0), float(run["llm"] or 0)
    try:
        audio_items = len(voice.planned_lines(p.conn, pid)) + 1          # every voiced line + the music
    except Exception:  # noqa: BLE001 - no voice plan yet: the music only
        audio_items = 1
    audio = money_policy.estimate("audio", None, None, audio_items)["usd"]
    chat_est = cost.llm_estimate(p.conn, "script_chat", 1) or 0.0
    claude += chat_est
    unpriced = len(run.get("unknown") or [])
    remaining = round(images + videos + claude + (audio or 0.0), 2)
    spent = round(sum(ledger_by_stage(p.conn, pid).values()), 2)          # from the ledger (all the project's paid rows)
    total = round(spent + remaining, 2)
    text = (f"Đã chi + ước tính phần còn lại ≈ ${total:.2f}: đã chi ${spent:.2f} (theo sổ chi) + còn lại ≈ ${remaining:.2f} "
            f"(ước tính, tính dư): Ảnh ≈ ${images:.2f} · Video ≈ ${videos:.2f} · "
            + (f"Âm thanh ≈ ${audio:.2f}" if audio is not None else f"Âm thanh {audio_items} lượt (chưa có giá USD, tính theo lượt)")
            + f" · Claude ≈ ${claude:.2f} (chat Kịch bản lượt kế ≈ ${chat_est:.2f}) · Tổng ≈ ${total:.2f}")
    if unpriced:
        text += (f" — {unpriced} mục chưa có giá được ước bằng giá cao nhất × 1,5 ({', '.join(run['unknown'])})")
    else:
        text += " — mọi mục đều có giá (giá cao nhất × 1,5 chỉ dùng khi thiếu giá)"
    return {"images": round(images, 2), "videos": round(videos, 2), "audio": None if audio is None else round(audio, 2),
            "audio_items": audio_items, "claude": round(claude, 2), "chat_est": chat_est,
            "chat_spent": ledger_by_stage(p.conn, pid)["claude_chat"], "remaining": remaining, "spent": spent, "total": total,
            "unpriced": unpriced, "text": text, "md": md_safe(text),
            "line": f"Đã chi ${spent:.2f} · còn lại ≈ ${remaining:.2f} · tổng ≈ ${total:.2f}"}


def approval_pending(p, pid: int) -> bool:
    """Only yes / no: the automatic run must wait for the person to approve the project's budget (no estimate computed — cheap,
    for checks that run every poll, e.g. autopilot.serve_waiting). The sentence with the numbers is gate_reason. Only the level
    "Tự chạy trong trần" waits for it (needs_lock, user 08/10)."""
    if not needs_lock(p, pid):
        return False
    data = get(p.conn, pid)
    return not (data and data.get("locked"))


def gate_reason(p, pid: int) -> Optional[str]:
    """Why the automatic run must wait before paying for pictures: the budget is not approved yet, or the proposal is over the
    person's target. Only at "Tự chạy trong trần" (needs_lock, user 08/10); the other levels never wait for it."""
    if not needs_lock(p, pid):
        return None
    data = get(p.conn, pid)
    if data and data.get("locked"):
        return None
    prop = propose(p, pid)
    over = ""
    if data and data.get("target") and prop["total"] > float(data["target"]):
        over = f" — đề xuất ≈ ${prop['total']:.2f} VƯỢT mục tiêu ${float(data['target']):.2f}: bớt shot khớp môi / giây video / shot, rồi tính lại"
    try:
        summary = " " + cost_summary(p, pid)["text"] + "."
    except Exception as e:  # noqa: BLE001 - the gate still waits; the missing estimate is said
        summary = (f" (chưa tính được đã chi + ước tính phần còn lại: {str(e)[:160] or type(e).__name__}. Cách xử lý: kiểm tra "
                   "bảng giá ở ⚙ Cài đặt rồi tải lại; vẫn lỗi thì gửi báo cáo ở ⚙ Chẩn đoán)")
    return f"Chờ duyệt ngân sách dự án (đề xuất ≈ ${prop['total']:.2f}){over}.{summary} — Bước 1 → 💵 Ngân sách dự án"


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
