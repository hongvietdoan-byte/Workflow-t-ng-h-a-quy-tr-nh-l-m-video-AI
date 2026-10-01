"""📥 Việc cần bạn (đợt 3, 01/10): everything that waits for a person, from every project, in one list — read from the database by
code (no model call). Screens: "script" | "storyboard" | "video" | "deliver" (dashboard/common.SCREENS).

Mine = projects this person created (or every project when sign-in is off / the project has no recorded creator and the person is the
Owner). The Owner can also list the whole team's. Services out of credit and people close to their limit are for the Owner / people with
the "settings" permission only.
"""
from typing import Dict, List, Optional

from . import archive, budget, project_budget, team

WAITING = ("waiting", "needs_attention")        # autopilot states that wait for a person (dashboard/next_step.py)

KINDS = ("Ảnh", "Video", "Ngân sách", "Tiền", "Chạy tự động", "Hạn mức")


def _mine(created_by: Optional[str], email: str, is_owner: bool, auth_on: bool) -> bool:
    if not auth_on:
        return True
    if created_by:
        return created_by.strip().lower() == (email or "").strip().lower()
    return is_owner


def items(conn, email: str, is_owner: bool = True, can_money: bool = True, auth_on: bool = False, team_wide: bool = False) -> List[Dict]:
    out: List[Dict] = []
    for pr in archive.active_projects(conn):
        pid, name = pr["id"], pr["name"]
        row = conn.execute("SELECT created_by, autopilot_state, autopilot_note FROM projects WHERE id=?", (pid,)).fetchone()
        mine = _mine(row["created_by"], email, is_owner, auth_on)
        if not mine and not team_wide:
            continue
        who = "" if mine else (row["created_by"] or "")

        def add(kind: str, text: str, screen: str, level: str = "todo", sub: str = ""):
            out.append({"kind": kind, "project_id": pid, "project": name, "text": text, "screen": screen, "level": level,
                        "who": who, "sub": sub})

        for kind, typ, screen, label in (("Ảnh", "image_gen", "storyboard", "ảnh"), ("Video", "video_gen", "video", "clip")):
            n = conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type=? AND state='pending_review'", (pid, typ)).fetchone()[0]
            if n:
                add(kind, f"Duyệt {n} {label} đang chờ", screen, "todo")
        if row["autopilot_state"] in WAITING and row["autopilot_note"]:
            add("Chạy tự động", f"Đang chờ bạn: {row['autopilot_note'][:160]}", "script", "wait")
        if row["autopilot_state"] == "error":
            add("Chạy tự động", f"Chạy tự động báo lỗi: {(row['autopilot_note'] or '')[:160]}", "script", "bad")
        finished = row["autopilot_state"] == "done" or conn.execute(
            "SELECT 1 FROM outputs WHERE project_id=? AND kind='final' LIMIT 1", (pid,)).fetchone()
        if project_budget.enabled() and not finished:
            has_plan = conn.execute("SELECT 1 FROM characters WHERE project_id=? AND TRIM(description)!='' LIMIT 1", (pid,)).fetchone()
            data = project_budget.get(conn, pid) or {}
            if has_plan and not data.get("locked"):
                add("Ngân sách", "Duyệt & khóa ngân sách dự án (💵 trên thanh trên)", "script", "todo")
    if can_money:
        s = budget.status(conn)
        for service in (s.get("out_of_credit") or {}):
            out.append({"kind": "Tiền", "project_id": None, "project": "", "text": f"{service} báo HẾT TIỀN — nạp xong bấm mở lại ở 💵",
                        "screen": None, "level": "bad", "who": "", "sub": ""})
        if s["llm_usd"] > 0 and s["llm_left"] <= 0:
            out.append({"kind": "Tiền", "project_id": None, "project": "", "text": "Claude API đã hết tiền — Dashboard ngừng gọi Claude",
                        "screen": None, "level": "bad", "who": "", "sub": ""})
        if is_owner:
            for u in conn.execute("SELECT email FROM users WHERE role!='owner' AND active=1").fetchall():
                st = team.limit_status(conn, u["email"])
                if st and st["share"] >= team.LIMIT_WARN:
                    out.append({"kind": "Hạn mức", "project_id": None, "project": "",
                                "text": f"{u['email']} đã dùng {st['share']:.0%} hạn mức ({st['spent']:.2f}/{st['limit']:.2f} USD / tháng)",
                                "screen": None, "level": "warn", "who": u["email"], "sub": ""})
    order = {"bad": 0, "wait": 1, "warn": 2, "todo": 3}
    out.sort(key=lambda x: (order.get(x["level"], 9), x["project_id"] or 0))
    return out
