"""🎓 Học việc (B2, 08/10 — docs/KE_HOACH_HOC_VIEC_2026-10-08.md mục 2–3): a role whose flag is in the "trainee" state still decides,
but only writes its decision here (`trainee_log`); it never blocks, redraws or changes what is sent. Its decisions are compared with the
person's own (review_log of the person, decided AFTER the role; or a one-click 👍/👎 card; or the storyboard gate fingerprint).

`agreement()` says "🎓 đủ chuẩn — chờ duyệt" (`ready`) only when: ≥ 2 projects, each ≥ 80 % and pooled ≥ 80 %, enough samples per flag,
balanced agreement ≥ 75 % and ≥ 5 points better than always saying the most common label (on #22 'always block' scored 76 %).
`ready` NEVER changes `verified` — the person approves that by hand."""
import json
from datetime import datetime, timezone
from typing import Dict, Iterable, Optional

# Each role answers in two classes: `pos` (it acts: block / redraw / group …) and `neg` (it lets things be). `pred` maps its decision
# to one of the two; `truth` = review_log ("review"), a 👍/👎 card ("card") or the storyboard gate fingerprint ("gate_fingerprint").
RULES: Dict[str, Dict] = {
    "qc_team": {"pos": "reject", "neg": "approve", "pred": {"block": "reject", "pass": "approve"}, "truth": "review",
                "min_per_project": 15, "min_pos": 5, "min_neg": 5, "unit": "khung"},
    "scene_qc": {"pos": "reject", "neg": "approve", "pred": {"redraw": "reject", "flag": "reject", "pass": "approve"}, "truth": "review",
                 "min_per_project": 15, "min_pos": 5, "min_neg": 5, "min_decision": {"redraw": 8}, "unit": "khung"},
    "scene_establishing": {"pos": "establish", "neg": "skip", "pred": {"establish": "establish", "skip": "skip"}, "truth": "card",
                           "min_per_project": 3, "unit": "cảnh"},
    "camera_setups": {"pos": "group", "neg": "single", "pred": {"group": "group", "skip": "single"}, "truth": "card",
                      "min_per_project": 3, "unit": "nhóm"},
    "continuous_takes": {"pos": "stretch", "neg": "cut", "pred": {"stretch": "stretch", "skip": "cut"}, "truth": "card",
                         "min_per_project": 2, "unit": "đoạn"},
    "end_frames": {"pos": "need_end", "neg": "no_end", "pred": {"need_end": "need_end", "skip": "no_end"}, "truth": "card",
                   "min_per_project": 3, "unit": "shot"},
    "storyboard_auto_trust": {"pos": "skip_gate", "neg": "hold_gate", "pred": {"skip_gate": "skip_gate", "hold_gate": "hold_gate"},
                              "truth": "gate_fingerprint", "min_per_project": 1, "min_total": 4, "min_decision": {"skip_gate": 2},
                              "needs_look_trust": True, "unit": "sự kiện"},
}
DECISIONS = ("block", "pass", "redraw", "flag", "group", "stretch", "need_end", "skip_gate", "hold_gate", "establish", "skip")
MIN_PROJECTS, MIN_RATE, MIN_BALANCED, MIN_OVER_BASELINE = 2, 0.80, 0.75, 0.05
BULK_N, BULK_S = 3, 2.0          # ≥ 3 approvals of one project within 2 s = a "Duyệt tất cả" click (gate_bulk), reported apart


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _t(s: str) -> Optional[datetime]:
    try:
        d = datetime.fromisoformat(str(s))
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def record(conn, feature: str, project_id: int, subject: str, decision: str, would_do=None, detail=None, cost_usd: float = 0.0,
           scene_id: Optional[int] = None, job_id: Optional[int] = None, story_scene: Optional[int] = None, at: Optional[str] = None) -> int:
    """Write one decision of a 🎓 role. Nothing else: the caller must not act on it."""
    rule = RULES.get(feature)
    if rule is None:
        raise ValueError(f"'{feature}' không có chế độ học việc")
    if decision not in DECISIONS or decision not in rule["pred"]:
        raise ValueError(f"quyết định '{decision}' không hợp với '{feature}' (có: {', '.join(rule['pred'])})")
    js = lambda v: None if v is None else json.dumps(v, ensure_ascii=False)     # noqa: E731
    cur = conn.execute(
        "INSERT INTO trainee_log (at, feature, project_id, scene_id, job_id, story_scene, subject, decision, would_do, detail, cost_usd)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (at or _now(), feature, project_id, scene_id, job_id, story_scene, subject, decision, js(would_do), js(detail), float(cost_usd or 0)))
    conn.commit()
    return cur.lastrowid


def label(conn, log_id: int, agree, source: str = "card") -> Dict:
    """The person's answer in one click: `agree` True (👍 the role was right) / False (👎) — or a class name of the rule."""
    row = conn.execute("SELECT feature, decision FROM trainee_log WHERE id=?", (log_id,)).fetchone()
    if row is None:
        raise ValueError(f"không có dòng học việc {log_id}")
    rule = RULES[row["feature"]]
    pred = rule["pred"][row["decision"]]
    if isinstance(agree, bool):
        truth = pred if agree else (rule["neg"] if pred == rule["pos"] else rule["pos"])
    elif agree in (rule["pos"], rule["neg"]):
        truth = agree
    else:
        raise ValueError(f"nhãn '{agree}' không hợp với '{row['feature']}'")
    conn.execute("UPDATE trainee_log SET truth=?, truth_source=?, match=?, scored_at=? WHERE id=?",
                 (truth, source, int(truth == pred), _now(), log_id))
    conn.commit()
    return {"truth": truth, "match": truth == pred}


def _bulk_ids(conn, project_id: int) -> set:
    """review_log ids of the person's approvals that came in a burst (≥ BULK_N within BULK_S seconds) = a bulk approve click."""
    rows = conn.execute("SELECT r.id, r.decided_at, r.note FROM review_log r JOIN jobs j ON j.id=r.job_id WHERE j.project_id=? "
                        "AND r.reviewer_type='user' AND r.decision='approve' ORDER BY r.decided_at, r.id", (project_id,)).fetchall()
    out = {r["id"] for r in rows if r["note"] == "gate_bulk"}      # B7: the "Duyệt tất cả" buttons write note='gate_bulk'
    times = [(r["id"], _t(r["decided_at"])) for r in rows]
    times = [(i, t) for i, t in times if t is not None]
    for k, (i, t) in enumerate(times):
        near = [j for j, u in times if abs((u - t).total_seconds()) <= BULK_S]
        if len(near) >= BULK_N:
            out.add(i)
    return out


def score_project(conn, project_id: int, features: Optional[Iterable[str]] = None) -> Dict[str, Dict]:
    """Fill truth/match for the review-based roles from the PERSON's first review_log decision on the job made AFTER the role decided
    (0 USD; at delivery and from the "Chấm lại" button). A person who decided first → truth_source 'human_first', not counted."""
    out = {}
    names = [f for f in (features or RULES) if RULES.get(f, {}).get("truth") == "review"]
    bulk = _bulk_ids(conn, project_id) if names else set()
    for feat in names:
        rule = RULES[feat]
        stat = {"scored": 0, "human_first": 0, "waiting": 0, "gate_bulk": 0}
        rows = conn.execute("SELECT id, at, job_id, decision FROM trainee_log WHERE feature=? AND project_id=? AND job_id IS NOT NULL "
                            "AND (truth_source IS NULL OR truth_source IN ('review','gate_bulk','human_first'))",
                            (feat, project_id)).fetchall()
        for r in rows:
            at = _t(r["at"])
            revs = conn.execute("SELECT id, decision, decided_at FROM review_log WHERE job_id=? AND reviewer_type='user' ORDER BY decided_at, id",
                                (r["job_id"],)).fetchall()
            after = [v for v in revs if at is not None and _t(v["decided_at"]) is not None and _t(v["decided_at"]) > at]
            if after:
                v = after[0]
                pred = rule["pred"][r["decision"]]
                src = "gate_bulk" if v["id"] in bulk else "review"
                conn.execute("UPDATE trainee_log SET truth=?, truth_source=?, match=?, scored_at=? WHERE id=?",
                             (v["decision"], src, int(v["decision"] == pred), _now(), r["id"]))
                stat["scored"] += 1
                stat["gate_bulk"] += src == "gate_bulk"
            elif revs:
                conn.execute("UPDATE trainee_log SET truth=NULL, truth_source='human_first', match=NULL, scored_at=? WHERE id=?",
                             (_now(), r["id"]))
                stat["human_first"] += 1
            else:
                stat["waiting"] += 1
        out[feat] = stat
    conn.commit()
    return out


def agreement(conn, feature: str, project_ids: Optional[Iterable[int]] = None, look_trusted: Optional[bool] = None) -> Dict:
    """How well the 🎓 role agrees with the person, and whether it is "🎓 đủ chuẩn — chờ duyệt" (`ready`). `missing` lists, in
    Vietnamese, every condition not met. `ready` never switches the flag on and never touches `verified`."""
    rule = RULES[feature]
    pos, neg = rule["pos"], rule["neg"]
    q = "SELECT project_id, decision, truth, truth_source, match, cost_usd FROM trainee_log WHERE feature=?"
    args = [feature]
    if project_ids is not None:
        ids = list(project_ids)
        q += f" AND project_id IN ({','.join('?' * len(ids)) or 'NULL'})"
        args += ids
    rows = conn.execute(q, args).fetchall()
    cost = round(sum(float(r["cost_usd"] or 0) for r in rows), 4)
    scored = [r for r in rows if r["match"] is not None and r["truth"] in (pos, neg)]
    per: Dict[int, Dict] = {}
    for r in scored:
        d = per.setdefault(r["project_id"], {"n": 0, "matched": 0})
        d["n"] += 1
        d["matched"] += int(r["match"])
    for d in per.values():
        d["rate"] = d["matched"] / d["n"]
    n = len(scored)
    matched = sum(int(r["match"]) for r in scored)
    rate = matched / n if n else None
    by_truth = {c: [r for r in scored if r["truth"] == c] for c in (pos, neg)}
    recalls = [sum(int(r["match"]) for r in v) / len(v) for v in by_truth.values() if v]
    balanced = sum(recalls) / 2 if len(recalls) == 2 else None
    baseline = max(len(v) for v in by_truth.values()) / n if n else None
    too_strict = sum(1 for r in scored if rule["pred"][r["decision"]] == pos and r["truth"] == neg)
    too_loose = sum(1 for r in scored if rule["pred"][r["decision"]] == neg and r["truth"] == pos)
    unit = rule["unit"]
    missing = []
    good = [p for p, d in per.items() if d["n"] >= rule["min_per_project"]]
    if len(good) < MIN_PROJECTS:
        missing.append(f"cần ≥ {MIN_PROJECTS} dự án có ≥ {rule['min_per_project']} {unit} đã chấm (có {len(good)})")
    low = [p for p, d in per.items() if d["rate"] < MIN_RATE]
    if low:
        missing.append(f"dự án dưới 80 % khớp: {', '.join('#' + str(p) for p in sorted(low))}")
    if rate is None or rate < MIN_RATE:
        missing.append(f"khớp gộp {0 if rate is None else rate:.0%} < 80 %")
    if rule.get("min_pos") and len(by_truth[pos]) < rule["min_pos"]:
        missing.append(f"cần ≥ {rule['min_pos']} {unit} người '{pos}' (có {len(by_truth[pos])})")
    if rule.get("min_neg") and len(by_truth[neg]) < rule["min_neg"]:
        missing.append(f"cần ≥ {rule['min_neg']} {unit} người '{neg}' (có {len(by_truth[neg])})")
    if rule.get("min_total") and n < rule["min_total"]:
        missing.append(f"cần ≥ {rule['min_total']} {unit} đã chấm (có {n})")
    for dec, k in (rule.get("min_decision") or {}).items():
        have = sum(1 for r in scored if r["decision"] == dec)
        if have < k:
            missing.append(f"cần ≥ {k} lần '{dec}' đã chấm (có {have})")
    if balanced is None or balanced < MIN_BALANCED:
        missing.append("khớp cân bằng " + ("chưa tính được (thiếu một loại nhãn của người)" if balanced is None
                                            else f"{balanced:.0%} < 75 %"))
    if rate is None or baseline is None or rate - baseline < MIN_OVER_BASELINE:
        missing.append(f"chưa hơn chiến lược 'luôn nói nhãn đông nhất' ≥ 5 điểm (nền {0 if baseline is None else baseline:.0%})")
    if rule.get("needs_look_trust") and not look_trusted:
        missing.append("look chưa đủ tin cậy (effectiveness.look_trust.trusted)")
    return {"feature": feature, "n": n, "matched": matched, "rate": rate, "balanced": balanced, "baseline": baseline,
            "per_project": per, "too_strict": too_strict, "too_loose": too_loose,
            "n_bulk": sum(1 for r in scored if r["truth_source"] == "gate_bulk"),
            "n_human_first": sum(1 for r in rows if r["truth_source"] == "human_first"),
            "n_waiting": sum(1 for r in rows if r["match"] is None and r["truth_source"] != "human_first"),
            "cost_usd": cost, "missing": missing, "ready": not missing}
