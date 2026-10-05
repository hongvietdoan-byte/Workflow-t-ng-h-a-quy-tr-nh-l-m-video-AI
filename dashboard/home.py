"""⌂ Tất cả dự án (đợt 3, 01/10): every active project on one page, one row each — status, where it is, money, what waits for you, who
has it open. Mine by default; "Cả nhóm" lists everyone's (projects of other people are for looking — the 🔒 / "việc của …" notes say who
works on them). One filter box (search + ⛃ Bộ lọc: status / step / creator / warnings), one sort. Open a row → the project on the
right screen. Data: core/perf.portfolio_rows + project_budget + core/team (presence)."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from core import access, archive, project_budget, team
from dashboard.design import components as D

STATUS = {"err": "🔴 Lỗi", "wait": "🖐 Chờ bạn", "run": "🚀 Đang chạy", "pause": "⏸ Tạm dừng", "done": "✔ Xong", "idle": "· Chưa chạy"}
STEP_SCREEN = {0: "script", 1: "storyboard", 2: "storyboard", 3: "video", 4: "deliver", 5: "deliver"}
STEP_NAME = {"script": "Kịch bản", "storyboard": "Storyboard", "video": "Video", "deliver": "Bản giao"}
PILL = {"err": ("Lỗi", "bad"), "wait": ("Chờ bạn", "warn"), "run": ("Đang chạy", "info"), "pause": ("Tạm dừng", "mute"),
        "done": ("Xong", "ok"), "idle": ("Chưa chạy", "mute")}                       # v2: the same states as STATUS, as pills
GRID_COLS = 3
SCOPE_NOTE = ("Bạn chỉ thấy dự án DO BẠN TẠO và dự án chủ dự án / Owner cho bạn theo dõi (thẻ ghi “theo dõi · chỉ xem” hoặc “theo dõi · được sửa”). "
              "“Chỉ xem” = xem được nhưng mọi nút ghi bị khóa; “Được sửa” = duyệt, gen, sửa như chủ. Owner thấy và làm được mọi dự án. "
              "🔒 = người đó vừa mở dự án (trong 2 phút) — chỉ báo để hai người không duyệt chồng nhau, không khóa.")
SORTS = {"wait": "Cần bạn trước", "new": "Mới nhất", "cost": "Tốn nhiều nhất"}


def status_of(r: dict, waiting_note: bool) -> str:
    if r["paused"]:
        return "pause"
    if r.get("autopilot_state") == "error":
        return "err"
    if r["done"]:                       # S14.30: "✔ Xong" only once the delivery was exported; a final cut alone waits for the person
        return "done" if r.get("delivered", True) else "wait"
    if r["needs_review"] or waiting_note:
        return "wait"
    if r["active"] or r["running_auto"]:
        return "run"
    return "idle"


def rows(p: Pipeline, email: str, is_owner: bool) -> list:
    """Active projects the signed-in person may see (core/access.py: their own, the ones they watch, everything for the Owner), with the
    fields the page filters and sorts on. `access` = 'admin' | 'own' | 'edit' | 'view'."""
    from core import perf
    active = {r["id"] for r in archive.active_projects(p.conn, C.access_user())}
    levels = access.levels_for(p.conn, C.access_user()) if auth_on() else {}
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
        out.append({**r, "access": levels.get(r["id"], "admin"), "status": status_of(r, waiting), "screen": STEP_SCREEN.get(r["step"], "script"), "spent": spent,
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


def progress_of(r: dict) -> float:
    total = max(r["scenes"], 1)
    return min((r["images"] + r["motion"] + r["videos"]) / (3 * total), 1.0) if r["scenes"] else 0.0


def tags_of(r: dict) -> list:
    if r.get("access") in ("view", "edit"):
        return ["của " + r["creator"].split("@")[0], "theo dõi · " + ("chỉ xem" if r["access"] == "view" else "được sửa")]
    if not r["mine"]:
        return ["của " + r["creator"].split("@")[0]]
    return ["của bạn"] if auth_on() else []


def _money_text(r: dict) -> str:
    return f"{r['spent']:.2f}/{r['cap']:.2f} USD" if r["cap"] else f"{r['spent']:.2f} USD"


def _details_html(r: dict) -> str:
    """P3 of a project card (inside its ⓘ): everything the old card showed outside, in full."""
    lines = [("Người tạo", escape(r["creator"]))]
    if tags_of(r) and r["creator"] != "—":
        lines.append(("Của ai", escape(" · ".join(tags_of(r)))))
    if r["open_by"]:
        lines.append(("🔒 Đang mở", escape(", ".join(x.split("@")[0] for x in r["open_by"])) + " (trong 2 phút)"))
    lines += [("Bước", escape(STEP_NAME.get(r["screen"], r["screen"]))),
              ("Tiến độ", escape(f"{r['step_label']} · ảnh {r['images']}/{r['scenes']} · chuyển động {r['motion']}/{r['scenes']} · clip {r['videos']}/{r['scenes']}")),
              ("Tiền", escape(f"{r['spent']:.2f} / {r['cap']:.2f} USD" if r["cap"] else f"{r['spent']:.2f} / — USD (chưa khóa trần)")),
              ("Chờ bạn", f"{r['needs_review']} mục cần duyệt")]
    if r["autopilot_note"]:
        lines.append(("🚀 Tự động", escape(r["autopilot_note"])))
    return "".join(f"<div><b>{k}:</b> {v}</div>" for k, v in lines)


def _card(r: dict) -> None:
    """v2: one project = one glass card: P1 (name, state pill, progress bar, open button) + ONE summary line; the rest is in its ⓘ."""
    label, kind = PILL[r["status"]]
    with D.card(f"home-{r['id']}"):
        with D.info(f"home-{r['id']}", anchor=f'<div class="home-name">#{r["id"]} {escape(r["name"])}</div>',
                    help_text="Người tạo, tiến độ, tiền, việc chờ bạn — bấm để xem"):
            st.markdown(_details_html(r), unsafe_allow_html=True)
        st.markdown(D.pill(label, kind, running=r["status"] == "run"), unsafe_allow_html=True)
        st.markdown(D.meter(progress_of(r)), unsafe_allow_html=True)
        summary = " · ".join([r["step_label"], _money_text(r)] + ([f"{r['needs_review']} chờ bạn"] if r["needs_review"] else []))
        st.markdown(f'<div class="home-sub home-sum" title="{escape(summary)}">{escape(summary)}</div>', unsafe_allow_html=True)
        st.button("Mở →", key=f"home_open_{r['id']}", on_click=C.go_screen, args=(r["id"], r["screen"]), width="stretch",
                  type="primary" if r["status"] == "wait" and r["mine"] else "secondary")


def _grid(shown: list) -> None:
    for col, r in zip(D.grid(len(shown), GRID_COLS), shown):       # 02/10: shared n-column card grid (components.grid)
        with col:
            _card(r)


def _hero(slot, shown: list, allrows: list) -> None:
    with slot:
        with D.hero("home"):
            st.markdown(D.hero_html("Tất cả dự án", "Mọi dự án đang dùng trên một trang — bấm “Mở →” để vào đúng màn đang chờ."),
                        unsafe_allow_html=True)
            sc = st.columns(4)
            sc[0].markdown(D.stat("Số dự án", f"{len(shown)} / {len(allrows)}", "đang hiện / tất cả"), unsafe_allow_html=True)
            sc[1].markdown(D.stat("Đang chạy", str(sum(1 for r in shown if r["status"] == "run"))), unsafe_allow_html=True)
            sc[2].markdown(D.stat("Chờ bạn", str(sum(1 for r in shown if r["status"] == "wait")),
                                  f"{sum(r['needs_review'] for r in shown)} mục cần duyệt"), unsafe_allow_html=True)
            sc[3].markdown(D.stat("Tổng chi", f"{sum(r['spent'] for r in shown):.2f} USD", "các dự án đang hiện"), unsafe_allow_html=True)


def home(p: Pipeline, pid: int):
    v2 = ui.v2_on()
    if not v2:
        st.markdown("### ⌂ Tất cả dự án")
    hero_slot = st.container() if v2 else None
    who = me()
    email = who.get("email", "") if auth_on() else ""
    is_owner = who.get("role") == "owner"
    allrows = rows(p, email, is_owner)
    if not allrows:
        st.info("Chưa có dự án nào đang dùng. Bấm “➕ Dự án mới” ở thanh trên (dự án đã cất khôi phục ở ⚙ → Dự án).")
        return
    top = st.columns([1.3, 3, 1.3, 1.8, 0.9] if v2 else [1.3, 3, 1.3, 1.8], vertical_alignment="center")
    if auth_on() and is_owner:                 # only the Owner has a wider view to switch to; a member's list is already "theirs + shared with them"
        scope = "team" if top[0].radio("Phạm vi", ["Của tôi", "Cả nhóm"], horizontal=True, label_visibility="collapsed",
                                       key="home_scope") == "Cả nhóm" else "mine"
    else:
        scope = "team"
        top[0].caption("Của bạn + được chia sẻ" if auth_on() else "Đăng nhập tắt: mọi dự án")
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
    if v2:
        with top[4]:
            with D.info("home-scope", label="Chú thích", help_text=D.md_plain(SCOPE_NOTE)):
                st.markdown(SCOPE_NOTE)
    shown = _sort(apply_filters(allrows, scope, q, status, step, creator, warn), sort)
    active_filters = [x for x in (STATUS.get(status), STEP_NAME.get(step), creator, "có cảnh báo" if warn else "", f"“{q}”" if q else "") if x]
    st.caption(f"Hiện **{len(shown)}** / {len(allrows)} dự án" + (" · đang lọc: " + ", ".join(active_filters) if active_filters else "")
               + ("" if v2 else f" · tổng chi các dự án đang hiện ≈ {sum(r['spent'] for r in shown):.2f} USD"))   # v2: total = hero stat
    if not shown:
        st.info("Không có dự án nào khớp bộ lọc.")
        return
    if v2:
        _hero(hero_slot, shown, allrows)
        _grid(shown)
    else:
        _rows(shown)
    _finished(shown)
    if not v2:
        st.caption(SCOPE_NOTE)


def _rows(shown: list) -> None:
    head = st.columns([2.6, 1.3, 2, 1.5, 0.9, 1.4], vertical_alignment="center")
    for c, t in zip(head, ["Dự án", "Trạng thái", "Tiến độ", "Tiền / trần", "Chờ bạn", ""]):
        c.caption(t.upper())
    for r in shown:
        c = st.columns([2.6, 1.3, 2, 1.5, 0.9, 1.4], vertical_alignment="center")
        tags = []
        if r.get("access") in ("view", "edit"):
            tags.append(f"của {r['creator']} · theo dõi, " + ("chỉ xem" if r["access"] == "view" else "được sửa"))
        elif not r["mine"]:
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
        c[2].markdown(ui.pbar(min(done_units, 1.0), text=f"{r['step_label']} · ảnh {r['images']}/{r['scenes']} · clip {r['videos']}/{r['scenes']}"), unsafe_allow_html=True)
        c[3].caption(f"{r['spent']:.2f} / {r['cap']:.2f}" if r["cap"] else f"{r['spent']:.2f} / —")
        c[4].markdown(colored("bad", f"**{r['needs_review']}**") if r["needs_review"] else "0", unsafe_allow_html=True)
        c[5].button("Mở →", key=f"home_open_{r['id']}", on_click=C.go_screen, args=(r["id"], r["screen"]), width="stretch",
                    type="primary" if r["status"] == "wait" and r["mine"] else "secondary")
        if r["autopilot_note"] and r["status"] in ("wait", "run"):
            c[0].caption("🚀 " + r["autopilot_note"][:110])


def _finished(shown: list) -> None:
    finished = [r for r in shown if r["done"] and r.get("delivered", True) and r["final_video"] and os.path.exists(r["final_video"])]
    if finished:
        # S14.8 U1: st.video đọc cả file mỗi lượt vẽ, kể cả trong expander gập → 20 dự án xong làm ⌂ chậm +78 %. Chỉ dựng player
        # và nút tải (đọc file) cho MỘT dự án người dùng chọn; mặc định trống.
        by_id = {r["id"]: r for r in finished}
        with st.expander(f"🎬 Sản phẩm đã hoàn tất ({len(finished)})", expanded=False):
            pick = st.selectbox("Xem dự án", [""] + list(by_id), key="home_finished_pick",
                                format_func=lambda k: "— chọn một dự án để xem / tải video —" if k == "" else f"#{k} {by_id[k]['name']}")
            r = by_id.get(pick)
            if r:
                show_video(r["final_video"], "Nhỏ")
                with open(r["final_video"], "rb") as f:
                    st.download_button("⬇ Tải FINAL_VIDEO.mp4", f, file_name=f"{r['name']}_FINAL_VIDEO.mp4", key=f"home_dl_{r['id']}")
