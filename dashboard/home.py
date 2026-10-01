"""⌂ Tất cả dự án (đợt 3, 01/10): every active project on one page, one row each — status, where it is, money, what waits for you, who
has it open. Mine by default; "Cả nhóm" lists everyone's (projects of other people are for looking — the 🔒 / "việc của …" notes say who
works on them). One filter box (search + ⛃ Bộ lọc: status / step / creator / warnings), one sort. Open a row → the project on the
right screen. Data: core/perf.portfolio_rows + project_budget + core/team (presence)."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from core import archive, project_budget, team

STATUS = {"err": "🔴 Lỗi", "wait": "🖐 Chờ bạn", "run": "🚀 Đang chạy", "pause": "⏸ Tạm dừng", "done": "✔ Xong", "idle": "· Chưa chạy"}
STEP_SCREEN = {0: "script", 1: "storyboard", 2: "storyboard", 3: "video", 4: "deliver", 5: "deliver"}
STEP_NAME = {"script": "Kịch bản", "storyboard": "Storyboard", "video": "Video", "deliver": "Bản giao"}
SORTS = {"wait": "Cần bạn trước", "new": "Mới nhất", "cost": "Tốn nhiều nhất"}


def status_of(r: dict, waiting_note: bool) -> str:
    if r["paused"]:
        return "pause"
    if r.get("autopilot_state") == "error":
        return "err"
    if r["done"]:
        return "done"
    if r["needs_review"] or waiting_note:
        return "wait"
    if r["active"] or r["running_auto"]:
        return "run"
    return "idle"


def rows(p: Pipeline, email: str, is_owner: bool) -> list:
    """Active projects with the fields the page filters and sorts on."""
    from core import perf
    active = {r["id"] for r in archive.active_projects(p.conn)}
    out = []
    for r in perf.portfolio_rows(p.conn, C.DATA):
        if r["id"] not in active:
            continue
        data = project_budget.get(p.conn, r["id"]) if project_budget.enabled() else None
        spent = 0.0
        try:
            spent = sum(project_budget.spent_by_stage(p.conn, r["id"]).values())
        except Exception:  # noqa: BLE001 - a money cell must never break the page
            pass
        waiting = r["autopilot_state"] in ("waiting", "needs_attention")
        creator = (r["created_by"] or "").strip()
        mine = (not auth_on()) or (creator.lower() == (email or "").lower() if creator else is_owner)
        out.append({**r, "status": status_of(r, waiting), "screen": STEP_SCREEN.get(r["step"], "script"), "spent": spent,
                    "cap": float((data or {}).get("total") or 0) if (data or {}).get("locked") else None,
                    "mine": mine, "creator": creator or "—", "open_by": team.open_by(p.conn, r["id"], exclude=email),
                    "warn": bool(waiting or r["autopilot_state"] == "error")})
    return out


def _sort(rs: list, key: str) -> list:
    order = {"err": 0, "wait": 1, "run": 2, "idle": 3, "pause": 4, "done": 5}
    if key == "new":
        return sorted(rs, key=lambda r: -r["id"])
    if key == "cost":
        return sorted(rs, key=lambda r: -r["spent"])
    return sorted(rs, key=lambda r: (order[r["status"]], -r["id"]))


def apply_filters(rs: list, scope: str, q: str, status: str, step: str, creator: str, warn: bool) -> list:
    out = []
    for r in rs:
        if scope == "mine" and not r["mine"]:
            continue
        if q and q.lower() not in (r["name"] + " " + r["creator"]).lower():
            continue
        if status and r["status"] != status:
            continue
        if step and r["screen"] != step:
            continue
        if creator and r["creator"] != creator:
            continue
        if warn and not r["warn"]:
            continue
        out.append(r)
    return out


def home(p: Pipeline, pid: int):
    st.markdown("### ⌂ Tất cả dự án")
    who = me()
    email = who.get("email", "") if auth_on() else ""
    is_owner = who.get("role") == "owner"
    allrows = rows(p, email, is_owner)
    if not allrows:
        st.info("Chưa có dự án nào đang dùng. Bấm “➕ Dự án mới” ở thanh trên (dự án đã cất khôi phục ở ⚙ → Dự án).")
        return
    top = st.columns([1.3, 3, 1.3, 1.8], vertical_alignment="center")
    scope = "team" if (auth_on() and top[0].radio("Phạm vi", ["Của tôi", "Cả nhóm"], horizontal=True, label_visibility="collapsed",
                                                  key="home_scope") == "Cả nhóm") else "mine"
    if not auth_on():
        top[0].caption("Đăng nhập tắt: mọi dự án")
        scope = "team"
    q = top[1].text_input("Tìm", placeholder="🔎 Tìm tên dự án hoặc người tạo…", label_visibility="collapsed", key="home_q").strip()
    sort = top[3].selectbox("Sắp xếp", list(SORTS), format_func=SORTS.get, label_visibility="collapsed", key="home_sort")
    with top[2].popover("⛃ Bộ lọc", width="stretch"):
        status = st.radio("Trạng thái", [""] + list(STATUS), format_func=lambda k: "Tất cả" if not k else STATUS[k], key="home_status")
        step = st.selectbox("Bước", [""] + list(STEP_NAME), format_func=lambda k: "Tất cả" if not k else STEP_NAME[k], key="home_step")
        creators = sorted({r["creator"] for r in allrows})
        creator = st.selectbox("Người tạo", [""] + creators, format_func=lambda k: "Tất cả" if not k else k,
                               key="home_creator") if is_owner or scope == "team" else ""
        warn = st.checkbox("⚠ Chỉ dự án có cảnh báo", key="home_warn")
        if st.button("✕ Xóa lọc", key="home_reset"):
            for k in ("home_q", "home_status", "home_step", "home_creator", "home_warn"):
                st.session_state.pop(k, None)
            st.rerun()
    shown = _sort(apply_filters(allrows, scope, q, status, step, creator, warn), sort)
    active_filters = [x for x in (STATUS.get(status), STEP_NAME.get(step), creator, "có cảnh báo" if warn else "", f"“{q}”" if q else "") if x]
    st.caption(f"Hiện **{len(shown)}** / {len(allrows)} dự án" + (" · đang lọc: " + ", ".join(active_filters) if active_filters else "")
               + f" · tổng chi các dự án đang hiện ≈ {sum(r['spent'] for r in shown):.2f} USD")
    if not shown:
        st.info("Không có dự án nào khớp bộ lọc.")
        return
    head = st.columns([2.6, 1.3, 2, 1.5, 0.9, 1.4], vertical_alignment="center")
    for c, t in zip(head, ["Dự án", "Trạng thái", "Tiến độ", "Tiền / trần", "Chờ bạn", ""]):
        c.caption(t.upper())
    for r in shown:
        c = st.columns([2.6, 1.3, 2, 1.5, 0.9, 1.4], vertical_alignment="center")
        tags = []
        if not r["mine"]:
            tags.append(f"của {r['creator']}")
        elif auth_on():
            tags.append("của bạn")
        if r["open_by"]:
            tags.append("🔒 " + ", ".join(x.split("@")[0] for x in r["open_by"]) + " đang mở")
        c[0].markdown(f"**#{r['id']} {escape(r['name'])}**" + (f"  \n<small>{escape(' · '.join(tags))}</small>" if tags else ""),
                      unsafe_allow_html=True)
        c[1].markdown(STATUS[r["status"]])
        total = max(r["scenes"], 1)
        done_units = (r["images"] + r["motion"] + r["videos"]) / (3 * total) if r["scenes"] else 0.0
        c[2].progress(min(done_units, 1.0), text=f"{r['step_label']} · ảnh {r['images']}/{r['scenes']} · clip {r['videos']}/{r['scenes']}")
        c[3].caption(f"{r['spent']:.2f} / {r['cap']:.2f}" if r["cap"] else f"{r['spent']:.2f} / —")
        c[4].markdown(f":red[**{r['needs_review']}**]" if r["needs_review"] else "0")
        c[5].button("Mở →", key=f"home_open_{r['id']}", on_click=C.go_screen, args=(r["id"], r["screen"]), width="stretch",
                    type="primary" if r["status"] == "wait" and r["mine"] else "secondary")
        if r["autopilot_note"] and r["status"] in ("wait", "run"):
            c[0].caption("🚀 " + r["autopilot_note"][:110])
    finished = [r for r in shown if r["done"] and r["final_video"] and os.path.exists(r["final_video"])]
    if finished:
        with st.expander(f"🎬 Sản phẩm đã hoàn tất ({len(finished)})", expanded=False):
            for r in finished:
                st.markdown(f"**#{r['id']} {r['name']}**")
                show_video(r["final_video"], "Nhỏ")
                with open(r["final_video"], "rb") as f:
                    st.download_button("⬇ Tải FINAL_VIDEO.mp4", f, file_name=f"{r['name']}_FINAL_VIDEO.mp4", key=f"home_dl_{r['id']}")
    st.caption("“Của tôi” = dự án bạn tạo. Dự án của người khác mở được để xem; chỉ thao tác (duyệt, gen) khi chủ dự án nhờ hoặc bạn là Owner — hệ thống ghi tên người gửi mỗi job. 🔒 = người đó vừa "
               "mở dự án (trong 2 phút) — chỉ báo để hai người không duyệt chồng nhau, không khóa.")
