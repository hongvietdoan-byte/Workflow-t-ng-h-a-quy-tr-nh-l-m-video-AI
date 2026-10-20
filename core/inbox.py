"""📥 Việc cần bạn (đợt 3, 01/10): everything that waits for a person, from every project, in one list — read from the database by
code (no model call). Screens: "script" | "storyboard" | "video" | "deliver" (dashboard/common.SCREENS).

Mine = projects this person created (or every project when sign-in is off / the project has no recorded creator and the person is the
Owner). The Owner can also list the whole team's. Services out of credit and people close to their limit are for the Owner / people with
the "settings" permission only.
"""
from typing import Dict, List, Optional

from . import access, archive, budget, delivered, money_policy, team

WAITING = ("waiting", "needs_attention")        # autopilot states that wait for a person (dashboard/next_step.py)

KINDS = ("Rà soát", "Ảnh", "Video", "Lỗi gen", "Ngân sách", "Tiền", "Chạy tự động", "Hạn mức", "Yêu cầu", "Bản giao")


def _mine(created_by: Optional[str], email: str, is_owner: bool, auth_on: bool) -> bool:
    if not auth_on:
        return True
    if created_by:
        return created_by.strip().lower() == (email or "").strip().lower()
    return is_owner


def _final_hold(conn, job_id: int) -> bool:
    from . import quality_tier
    row = conn.execute("SELECT note FROM job_events WHERE job_id=? AND to_state='failed' ORDER BY id DESC LIMIT 1", (job_id,)).fetchone()
    return bool(row) and quality_tier.final_hold_note(row["note"])


def _skip(conn, pid: int) -> Dict:
    from . import inbox_clean
    try:
        return inbox_clean.skip_sets(conn, pid)
    except Exception:  # noqa: BLE001 - a broken leftover check never hides real work: count everything as before
        return {"jobs": set(), "failed": set(), "findings": set()}


def _shots(idx: List[int]) -> str:
    return ", ".join(str(i) for i in idx[:8]) + ("…" if len(idx) > 8 else "")


def _direct_waiting(conn, pid: int, skip) -> int:
    """Rà gop-1510 r2 (người dùng 15/10): clip gen thẳng 720p (cờ two_tier_quality, không làm từ nháp) mà QC không đưa vào
    'pending_review' (qc_video TẮT / QC lỗi riêng clip) nằm 'succeeded' — vẫn chờ NGƯỜI duyệt (autopilot._drafts_waiting đợi nó)."""
    from . import quality_tier
    if not quality_tier.enabled():
        return 0
    n = 0
    for r in conn.execute("SELECT j.id, j.scene_id FROM jobs j WHERE j.project_id=? AND j.type='video_gen' AND j.quality_tier='direct'"
                          " AND j.draft_job_id IS NULL AND j.state='succeeded'", (pid,)).fetchall():
        if r["id"] in skip:
            continue
        try:
            if quality_tier.state(conn, r["scene_id"]) == "final_review":   # shot đã có clip dùng (direct_ok …) → bản thừa, không đếm
                n += 1
        except Exception:  # noqa: BLE001 - one unreadable shot never hides the list
            continue
    return n


def _video_waits(conn, pid: int, final_hold: List[int]) -> List[str]:
    """C7 (13/10, U2): clips that wait for the PERSON with no other line in 📥 — queued clips the runner keeps (kiểm trước gen ĐỎ / bản
    cao chờ — Tổ rà soát has its own line), finals waiting for a confirmation, drafts the person approved still without their final
    (flag two_tier_quality)."""
    from .runner import held_reason
    out = []
    held = {}
    for r in conn.execute("SELECT j.id, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.project_id=? AND j.type='video_gen'"
                          " AND j.state='queued' AND EXISTS (SELECT 1 FROM diag_events d WHERE d.job_id=j.id AND d.code IN"
                          " ('video_pregen_hold','final_wait','QUEUE_CAPACITY','QUEUE_UNKNOWN_CAPACITY','QUEUE_CONFIG')) ORDER BY s.idx", (pid,)).fetchall():
        why = held_reason(conn, r["id"])
        if why:
            held.setdefault(why, []).append(r["idx"])
    for why, idx in held.items():
        out.append(f"Clip bị giữ chưa gửi ở shot {_shots(idx)}: {why[:180]}")
    if final_hold:
        out.append(f"Bản cao chờ bạn xác nhận gen mới ở shot {_shots(final_hold)} — bấm “⬆ Gen MỚI bản cao” trên thẻ (không xếp hàng lại)")
    from . import quality_tier
    if quality_tier.enabled():
        cand = [r for r in conn.execute(
            "SELECT DISTINCT s.id, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id JOIN review_log l ON l.job_id=j.id WHERE "
            "j.project_id=? AND j.type='video_gen' AND j.quality_tier='draft' AND j.state='approved' AND l.reviewer_type='user' "
            "AND l.decision='approve' ORDER BY s.idx", (pid,)).fetchall()]
        ready = []
        for r in cand:
            try:
                if quality_tier.state(conn, r["id"]) == "draft_ok":
                    ready.append(r["idx"])
            except Exception:  # noqa: BLE001 - one unreadable shot never hides the list
                continue
        if ready:
            out.append(f"{len(ready)} nháp đã duyệt chờ gen bản cao: shot {_shots(ready)} — bấm “⬆ Gen bản cao” ở màn Video")
    return out


def items(conn, email: str, is_owner: bool = True, can_money: bool = True, auth_on: bool = False, team_wide: bool = False) -> List[Dict]:
    """Rights (core/access.py): a person gets the items of the projects they made and of projects where they are a watcher with the
    "Được sửa" level (they can act on those). A "Chỉ xem" watcher gets none (nothing there is theirs to do). Only the Owner can widen
    to the whole team with `team_wide`; for anyone else `team_wide` changes nothing."""
    out: List[Dict] = []
    levels = access.levels_for(conn, {"email": email, "role": "owner" if is_owner else "member"}) if auth_on else {}
    for pr in archive.active_projects(conn):
        pid, name = pr["id"], pr["name"]
        row = conn.execute("SELECT created_by, autopilot_state, autopilot_note FROM projects WHERE id=?", (pid,)).fetchone()
        mine = _mine(row["created_by"], email, is_owner, auth_on)
        if auth_on and not is_owner:
            lv = levels.get(pid)
            if lv not in ("own", "edit"):
                continue
            mine = True                                # a watcher with "Được sửa" acts on it like on their own
        elif not mine and not team_wide:
            continue
        creator = (row["created_by"] or "").strip()
        who = creator if auth_on and creator and creator.lower() != (email or "").strip().lower() else ""

        def add(kind: str, text: str, screen: str, level: str = "todo", sub: str = ""):
            out.append({"kind": kind, "project_id": pid, "project": name, "text": text, "screen": screen, "level": level,
                        "who": who, "sub": sub})

        # C2 (14/10): leftovers (an older take when the shot already uses another, an old error when the shot has a usable take, a
        # Tổ rà soát item older than the shot's approved result, anything of a delivered project) are not counted — core/inbox_clean
        sk = _skip(conn, pid)
        # 10/10 Tổ rà soát tác động: mục còn mở sau một thay đổi (đỏ = gen tốn tiền của shot đang bị giữ)
        try:
            rv = conn.execute("SELECT f.id, f.level, s.idx FROM change_findings f LEFT JOIN scenes s ON s.id=f.scene_id WHERE "
                              "f.project_id=? AND f.status='open' ORDER BY s.idx", (pid,)).fetchall()
        except Exception:  # noqa: BLE001 - an old database without the table: nothing to list
            rv = []
        by_level: Dict[str, List] = {}
        for f in rv:
            if f["id"] not in sk["findings"]:
                by_level.setdefault(f["level"], []).append(f["idx"])
        for lv in sorted(by_level):
            shots = ",".join(str(i) for i in dict.fromkeys(i for i in by_level[lv] if i is not None))
            add("Rà soát", f"{'🔴 Giữ gen — ' if lv == 'do' else ''}{len(by_level[lv])} mục lệch sau thay đổi"
                + (f" (shot {shots})" if shots else ""), "storyboard", "wait" if lv == "do" else "todo")
        for kind, typ, screen, label in (("Ảnh", "image_gen", "storyboard", "ảnh"), ("Video", "video_gen", "video", "clip")):
            n = sum(1 for r in conn.execute("SELECT id FROM jobs WHERE project_id=? AND type=? AND state='pending_review'", (pid, typ))
                    if r[0] not in sk["jobs"])
            if typ == "video_gen":
                n += _direct_waiting(conn, pid, sk["jobs"])
            if n:
                add(kind, f"Duyệt {n} {label} đang chờ", screen, "todo")
        for kind, typ, screen, label in (("Ảnh", "image_gen", "storyboard", "ảnh"), ("Video", "video_gen", "video", "clip")):
            # S14.16: the automatic regeneration limit (pipeline.AUTO_REGEN_LIMIT) reached — ONLY that reason (the diag line the
            # pipeline writes at the limit, pipeline.AUTO_LIMIT_CODE), for the shot's latest job still waiting (escalated, or finished
            # and kept as it is); a job held for another reason (QC without a fix, a failure not temporary) is not listed here
            for j in conn.execute("SELECT DISTINCT j.retry_count, s.idx FROM diag_events d JOIN jobs j ON j.id=d.job_id"
                                  " JOIN scenes s ON s.id=j.scene_id WHERE d.code='auto_regen_limit' AND j.project_id=? AND j.type=?"
                                  " AND (j.escalated=1 OR j.state IN ('succeeded','approved'))"
                                  " AND NOT EXISTS (SELECT 1 FROM jobs k WHERE k.scene_id=j.scene_id AND k.type=j.type AND k.id>j.id)"
                                  " ORDER BY s.idx", (pid, typ)).fetchall():
                add(kind, f"Cần bạn quyết — đã tự gen lại {j['retry_count']} lần: {label} shot {j['idx']} (máy không tự gen thêm)",
                    screen, "wait")
        # S14.8 U4: the LATEST job of a shot failed (failed / retryable, core/states.JobState) — only image_gen / video_gen
        # (pipeline.create_job makes only these two); a shot that already has a newer job is not listed (storyboard_cards.board_stats).
        # One query for both types (⌂ / every page draws this for every project).
        failed = {"image_gen": [], "video_gen": []}
        final_hold = []
        for r in conn.execute("SELECT j.id, j.type, j.quality_tier, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.project_id=?"
                              " AND j.type IN ('image_gen','video_gen') AND j.state IN ('failed','retryable')"
                              " AND NOT EXISTS (SELECT 1 FROM jobs k WHERE k.scene_id=j.scene_id AND k.type=j.type AND k.id>j.id)"
                              " ORDER BY s.idx", (pid,)).fetchall():
            if r["quality_tier"] == "final" and _final_hold(conn, r["id"]):
                final_hold.append(r["idx"])           # C3/C7: waits for the person's confirmation — not a generation error
                continue
            if r["id"] in sk["failed"]:
                continue                              # C2: the shot already has a usable take / the project was delivered
            failed[r["type"]].append(r["idx"])
        for line in _video_waits(conn, pid, final_hold):
            add("Video", line, "video", "wait")
        for typ, screen, label in (("image_gen", "storyboard", "ảnh"), ("video_gen", "video", "clip")):
            idx = failed[typ]
            if idx:
                shots = ", ".join(str(i) for i in idx[:8]) + ("…" if len(idx) > 8 else "")
                add("Lỗi gen", f"Gen {label} lỗi ở {len(idx)} shot — mở để vẽ lại / xem lý do: {label} shot {shots}", screen, "bad")
        if row["autopilot_state"] in WAITING and row["autopilot_note"]:
            add("Chạy tự động", f"Đang chờ bạn: {row['autopilot_note'][:160]}", "script", "wait")
        if row["autopilot_state"] == "stopped" and "trần job do máy" in (row["autopilot_note"] or ""):
            # S14.16: the product job cap stopped the run (autopilot._job_cap_reason) — only something abnormal reaches it
            add("Chạy tự động", f"Cần bạn xem: {(row['autopilot_note'] or '')[:220]}", "script", "bad")
        if row["autopilot_state"] == "error":
            add("Chạy tự động", f"Chạy tự động báo lỗi: {(row['autopilot_note'] or '')[:160]}", "script", "bad")
        if delivered.rendered_not_delivered(conn, pid):  # S14.30: "hoàn thiện" = đã xuất bản giao, bản ghép cuối chưa tính
            add("Bản giao", "Đã có bản cuối nhưng chưa xuất bản giao — bấm “📦 Xuất bản đầy đủ” ở bước Bản giao: "
                f"{delivered.HINT} (dự án còn tính vào giới hạn dự án dở)", "deliver", "todo")
        # 15/10 (người dùng bỏ cổng "Tự chạy trong trần"): no "Duyệt & khóa ngân sách" reminder — nothing waits for it any more
    if can_money:
        s = budget.status(conn)
        for service in (s.get("out_of_credit") or {}):
            out.append({"kind": "Tiền", "project_id": None, "project": "", "text": f"{service} báo HẾT TIỀN — nạp xong bấm mở lại ở 💵",
                        "screen": None, "level": "bad", "who": "", "sub": ""})
        warns = money_policy.recent(conn, hours=24)
        if warns:                       # S14.16: the caps warn instead of refusing — one line, the newest warning with its numbers
            last = warns[0]["message"]
            out.append({"kind": "Tiền", "project_id": None, "project": "",
                        "text": f"Cảnh báo tiền ({len(warns)} trong 24 giờ, vẫn gửi): {last[:200]}", "screen": None, "level": "warn",
                        "who": "", "sub": ""})
        elif s["llm_usd"] > 0 and s["llm_left"] <= 0:
            out.append({"kind": "Tiền", "project_id": None, "project": "",
                        "text": f"Claude API đã vượt mức dự tính (${s['llm_spent']:.2f} / ${s['llm_usd']:.2f}) — vẫn gọi, xem 💵",
                        "screen": None, "level": "warn", "who": "", "sub": ""})
        if is_owner:
            for u in conn.execute("SELECT email FROM users WHERE role!='owner' AND active=1").fetchall():
                st = team.limit_status(conn, u["email"])
                if st and st["share"] >= team.LIMIT_WARN:
                    out.append({"kind": "Hạn mức", "project_id": None, "project": "",
                                "text": f"{u['email']} đã dùng {st['share']:.0%} hạn mức ({st['spent']:.2f}/{st['limit']:.2f} USD / tháng)",
                                "screen": None, "level": "warn", "who": u["email"], "sub": ""})
    if is_owner and auth_on:            # S14.18: a person asks for one project more (3rd of the day / 2nd unfinished 📦) → Owner decides
        from . import person_limits
        waiting = person_limits.requests(conn, "pending")
        if waiting:
            names = ", ".join(sorted({r["email"] for r in waiting}))
            out.append({"kind": "Yêu cầu", "project_id": None, "project": "",
                        "text": f"{len(waiting)} yêu cầu vượt mức dự án chờ bạn duyệt ở 👥 Nhóm ({names})", "screen": None,
                        "level": "wait", "who": "", "sub": ""})
    if is_owner:
        # C3-3: cả dự án đã cất vẫn có một dòng chờ duyệt; không có nút apply.
        for r in conn.execute("SELECT p.id, p.name, d.message FROM projects p JOIN diag_events d ON d.project_id=p.id "
                              "WHERE d.code='subject_cleanup_plan' AND d.id=(SELECT MAX(x.id) FROM diag_events x "
                              "WHERE x.project_id=p.id AND x.code='subject_cleanup_plan')"):
            out.append({'kind': 'Kho chủ thể', 'project_id': r['id'], 'project': r['name'], 'text': r['message'],
                        'screen': None, 'level': 'wait', 'who': '', 'sub': 'DRY-RUN — chờ duyệt riêng từng lần'})
    order = {"bad": 0, "wait": 1, "warn": 2, "todo": 3}
    out.sort(key=lambda x: (order.get(x["level"], 9), x["project_id"] or 0))
    return out
