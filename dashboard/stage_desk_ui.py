"""C-M48-DESK-UI (V3.1 M4.8 Đợt 1, 22/10) — "Bàn đạo diễn 3D": hàng nút trong expander từng cảnh của màn XEM sân khấu 3D (Bước 2,
dashboard/stage_view_ui.py gọi render_scene ở cuối expander). Cờ `stage_desk_ui` (TẮT = render_scene trả về ngay, không đọc / không vẽ gì;
REQUIRES stage_view_ui). Kế hoạch docs/KE_HOACH_BAN_DAO_DIEN_3D_DASHBOARD_2026-10-21.md mục 3, 4, 9; sổ quyết định
v31-ep-stage-desk-actions-2026-10-21 (S-A … S-G).

Mỗi nút gọi ĐÚNG MỘT hàm công khai của core/stage_desk (lõi C-M48-DESK-CORE: khóa S, luồng nền, write guard, quyền EP đều ở lõi — lõi kiểm
lại mọi điều kiện khi bấm, giao diện chỉ ẩn / khóa / hỏi xác nhận):
  N1 check_inputs · N2 estimate · N3 write_prompt · N4 load_answer · N5 build_sheet · N6 approve · N7 return_ · N8 reset · N9 rerender ·
  N10 score · N11 render_plates. Không có N12 previs (Đợt 2) / N13 API (Đợt 3) → 0 USD, không gọi Claude.
Danh sách nút = scene_status()["buttons"] (hợp phase). Đang chạy / khóa S của người khác → mọi nút trừ 💲 Ước tính bị khóa + hiện tiến độ
(desk_progress.json qua scene_status()["progress"]). Thao tác đổi dữ liệu (N4 nạp trả lời, N6 duyệt, N8 làm lại, N9 dựng lại, N11 render
nền) phải tích xác nhận; N8 xem trước (S-D) rồi mới xác nhận; shot đã vẽ ảnh → xác nhận riêng (Q-D).
Quyền (S-B): ✅ Duyệt / ↩ Trả lại chỉ hiện cho Executive Producer (stage_desk.is_executive_producer với common.access_user()) và chỉ khi
người bấm là NGƯỜI — phiên Claude thao tác Dashboard (`?op=claude`) bấm các nút khác với actor "ai", không thấy Duyệt / Trả lại."""
import json
import os
from typing import Dict, Optional

import streamlit as st

FLAG = "stage_desk_ui"
ORDER = ("N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8", "N9", "N10", "N11")
SIMPLE = ("N1", "N2", "N3", "N5", "N10")              # nút một chạm: đọc / ghi tệp trong thư mục đoạn, không đổi CSDL
EP_ONLY = ("N6", "N7")
CONFIRM = {"N4": "Xác nhận nạp câu trả lời vai (có thể đo K3 + K4 bằng Blender; tới phase xong thì ghi máy các shot)",
           "N6": "Tôi đã xem tấm ghép / số đo — DUYỆT sân khấu cảnh này (ghi máy các shot qua write guard)",
           "N9": "Xác nhận dựng lại từ câu trả lời đã lưu (đo K3 + K4, ghi máy các shot)",
           "N11": "Xác nhận render lại nền 3D cảnh này (Blender, 0 USD — quên bản render hỏng của các shot)"}


def enabled() -> bool:
    from core import features
    return features.on(FLAG) and features.on("stage_view_ui")


def _label(code: str) -> str:
    from core import stage_desk
    return stage_desk.ACTIONS.get(code, code)


def _identity():
    """(who = write_guard.actor của người / phiên bấm, user = common.access_user(), là phiên Claude?)."""
    from core import write_guard
    from dashboard import common
    user = common.access_user()
    if common.op_source() == "claude":
        return write_guard.actor("ai", "phien_claude_dashboard"), user, True
    email = (user or {}).get("email") or (common.me() or {}).get("email") or "chu_may"
    return write_guard.actor("human", email), user, False


def _show_progress(pr: Optional[Dict]) -> None:
    if not pr:
        return
    lab = pr.get("label") or pr.get("action") or "tác vụ"
    state = pr.get("state")
    if state == "running":
        st.info(f"⏳ {lab} đang chạy — {pr.get('step') or 'chờ bắt đầu'}")
        log = [str(x) for x in (pr.get("log") or [])][-5:]
        if log:
            st.caption(" · ".join(log))
    elif state == "done":
        st.success(f"✓ {lab} xong ({pr.get('updated') or ''}) — {pr.get('step') or ''}")
        res = pr.get("result") or {}
        for m in list(res.get("missing") or []) + list(res.get("gate") or []):
            st.warning(f"{lab}: {m}")
        for n in res.get("notes") or []:
            st.caption(f"ℹ {n}")
    elif state == "error":
        st.error(f"✗ {lab} lỗi: {pr.get('error') or 'không rõ lý do'}")
    elif state == "interrupted":
        st.warning(f"⚠ {lab}: {pr.get('error') or 'tác vụ bị ngắt'}")


def _show_result(code: str, res: Dict) -> None:
    lab = _label(code)
    if code == "N2" and res.get("ok"):
        if res.get("usd") is None:
            st.caption(f"💲 {res.get('note') or 'chưa có giá Claude cho model đang dùng (bảng giá)'}")
        else:
            st.caption(f"💲 Ước tính Claude cảnh này ≈ {res.get('usd')} USD (tối đa {res.get('usd_max')} USD) — chỉ để xem; Đợt 1 không "
                       "có nút gọi API")
        return
    if not res.get("ok"):
        st.error(f"{lab}: " + "; ".join(str(e) for e in (res.get("errors") or ["lỗi không rõ (lõi không trả câu)"])))
        return
    if res.get("started"):
        st.info(f"⏳ {lab}: đã chạy nền — bấm 🔄 Xem tiến độ để cập nhật")
        return
    bits = []
    if res.get("path"):
        bits.append(f"tệp {res['path']}")
    if res.get("problems"):
        bits.append("lưu ý: " + "; ".join(map(str, res["problems"])))
    if res.get("bad"):
        bits.append("dùng máy thường: " + ", ".join(f"shot {k} ({v})" for k, v in res["bad"].items()))
    if res.get("forgot"):
        bits.append("quên render hỏng shot " + ", ".join(map(str, res["forgot"])))
    st.success(f"✓ {lab} xong" + (" — " + " · ".join(bits) if bits else ""))


def _answer_obj(conn, pid: int, data_dir: str, scene, phase: Optional[str], text: str):
    """(obj | None, lỗi | None). Ô trống → đọc crew/tra_loi_<phase>.json trong thư mục đoạn (đường của data_dir, không theo cwd)."""
    from core import stage_desk
    if not (text or "").strip():
        try:
            path = os.path.join(stage_desk.seg_dir(data_dir, pid, stage_desk.segment(conn, pid, scene)), "crew", f"tra_loi_{phase}.json")
        except Exception as e:  # noqa: BLE001 - nói lý do, không ném
            return None, f"không tìm được thư mục đoạn ({type(e).__name__}: {e})"
        if not os.path.isfile(path):
            return None, f"chưa dán câu trả lời JSON và chưa có tệp {path}"
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            return None, f"không đọc được {path} ({type(e).__name__})"
    try:
        return json.loads(text), None
    except ValueError as e:
        return None, f"câu trả lời không phải JSON hợp lệ ({e})"


def render_scene(p, pid: int, data_dir: str, scene) -> None:
    """Hàng nút của MỘT cảnh, vẽ trong expander của màn XEM. Cờ tắt → không đọc / không vẽ gì."""
    if not enabled():
        return
    from core import stage_desk
    conn = p.conn
    key = f"desk_{pid}_{scene}"
    try:
        s = stage_desk.scene_status(conn, pid, data_dir, scene)
    except stage_desk.DeskError as e:
        st.caption(f"🎬 Bàn đạo diễn 3D: {e}")
        return
    except Exception as e:  # noqa: BLE001 - bàn thao tác không làm hỏng màn XEM: nói lý do
        st.warning(f"🎬 Bàn đạo diễn 3D: không đọc được trạng thái cảnh {scene} ({type(e).__name__}: {e})")
        return
    who, user, is_claude = _identity()
    st.markdown(f"**🎬 Bàn đạo diễn 3D** — {s.get('seg_id')} · {s.get('label')} (0 USD)")
    if not s.get("k1"):
        st.caption("ℹ chưa có K1 (mặt cắt bối cảnh) — bấm 🔍 Kiểm đầu vào trước; nút khác có thể phải đo K1 bằng Blender ≈ 20 s")
    if s.get("inputs_changed"):
        st.warning("Đầu vào đã đổi so với lượt chia vai — lượt dở không dùng được, chỉ còn 🗑 Làm lại từ Đạo diễn")
    h = s.get("lock")
    if h:
        if h.get("stale"):
            st.warning(f"🔓 Khóa sân khấu cũ ({h['stale']}) — sẽ tự gỡ ở lần bấm kế")
        else:
            st.warning("🔒 " + stage_desk.lock_line(s.get("seg_id"), h))
    pr = s.get("progress")
    _show_progress(pr)
    if s.get("approved_by"):
        st.caption(f"Đã duyệt bởi: {s['approved_by']}" + (f" · máy ghi shot {', '.join(map(str, s['cams_this_stage']))}"
                                                         if s.get("cams_this_stage") else ""))
    if s.get("bad"):
        st.caption("Shot dùng máy thường: " + "; ".join(f"shot {k} — {v}" for k, v in s["bad"].items()))
    if s.get("reset"):
        st.caption(f"↺ Đã làm lại lúc {s['reset'].get('at')} — {s['reset'].get('say') or 'máy cũ giữ tới khi duyệt lượt mới'}")
    rs = s.get("reset_stale") or {}
    if rs.get("plates_stale"):
        st.warning("Sau làm lại, máy đổi ở shot " + ", ".join(map(str, rs["plates_stale"])) + " — nền 3D cũ (bấm ↻ Render lại nền 3D)"
                   + (f"; ảnh đã vẽ cũ: shot {', '.join(map(str, rs['images_stale']))}" if rs.get("images_stale") else ""))
    busy = bool(h and not h.get("stale")) or bool(s.get("running")) or (pr or {}).get("state") == "running"
    codes = [c for c in ORDER if c in (s.get("buttons") or [])]
    if any(c in codes for c in EP_ONLY) and not (s.get("user_approves") and not is_claude
                                                 and stage_desk.is_executive_producer(conn, pid, user)):
        codes = [c for c in codes if c not in EP_ONLY]
        st.caption("✅ Duyệt / ↩ Trả lại: chỉ Executive Producer (người — Owner / chủ dự án) bấm; Director / phiên Claude chỉ đề xuất "
                   "(S-B)")
    if s.get("phase") == "duyet" and not s.get("user_approves"):
        st.caption("Duyệt chốt do Đạo diễn (cờ stage_crew_user_approve TẮT) — không có bước người duyệt")

    res_key = f"{key}_res"
    clicked = None

    def run(code: str, fn):
        st.session_state[res_key] = (code, fn() or {})

    simple = [c for c in codes if c in SIMPLE]
    if simple:
        cols = st.columns(len(simple))
        calls = {"N1": lambda: stage_desk.check_inputs(conn, pid, data_dir, scene, who),
                 "N2": lambda: stage_desk.estimate(conn, pid, data_dir, scene),
                 "N3": lambda: stage_desk.write_prompt(conn, pid, data_dir, scene, who),
                 "N5": lambda: stage_desk.build_sheet(conn, pid, data_dir, scene, who),
                 "N10": lambda: stage_desk.score(conn, pid, data_dir, scene, who)}
        for col, code in zip(cols, simple):
            with col:
                if st.button(_label(code), key=f"{key}_{code}", disabled=busy and code != "N2"):
                    clicked = code
        if clicked:
            run(clicked, calls[clicked])

    if "N4" in codes:
        st.text_area("📥 Câu trả lời vai (JSON) — dán vào đây, hoặc để trống để đọc crew/tra_loi_<phase>.json của đoạn",
                     key=f"{key}_N4_json", height=120, disabled=busy)
        ok = st.checkbox(CONFIRM["N4"], key=f"{key}_N4_ok", disabled=busy)
        if st.button(_label("N4"), key=f"{key}_N4", disabled=busy):
            if not ok:
                st.session_state[res_key] = ("N4", {"ok": False, "errors": ["tích ô xác nhận trước khi nạp"]})
            else:
                obj, err = _answer_obj(conn, pid, data_dir, scene, s.get("phase"), st.session_state.get(f"{key}_N4_json") or "")
                if err:
                    st.session_state[res_key] = ("N4", {"ok": False, "errors": [err]})
                else:
                    run("N4", lambda: stage_desk.load_answer(conn, pid, data_dir, scene, obj, who))

    if "N6" in codes:
        marks_key = f"{key}_marks"
        if marks_key not in st.session_state:          # dấu máy lúc MỞ màn duyệt — máy đổi xen giữa thì lõi từ chối
            st.session_state[marks_key] = dict(s.get("marks") or {})
        ok = st.checkbox(CONFIRM["N6"], key=f"{key}_N6_ok", disabled=busy)
        drawn = list(s.get("drawn") or [])
        drawn_ok = st.checkbox(f"Shot {', '.join(map(str, drawn))} đã vẽ ảnh — vẫn đổi máy (ảnh sẽ lệch nền 3D mới)",
                               key=f"{key}_N6_drawn", disabled=busy) if drawn else False
        if st.button(_label("N6") + f" {scene}", key=f"{key}_N6", disabled=busy, type="primary"):
            if not ok:
                st.session_state[res_key] = ("N6", {"ok": False, "errors": ["tích ô xác nhận duyệt trước"]})
            elif drawn and not drawn_ok:
                st.session_state[res_key] = ("N6", {"ok": False, "errors": [f"shot {', '.join(map(str, drawn))} đã vẽ ảnh — tích ô xác "
                                                                            "nhận riêng để vẫn đổi máy"]})
            else:
                run("N6", lambda: stage_desk.approve(conn, pid, data_dir, scene, who, user=user, confirm_drawn=bool(drawn_ok),
                                                     expected_marks=st.session_state[marks_key]))
                res = st.session_state[res_key][1]
                if res.get("ok") or res.get("stale"):
                    st.session_state.pop(marks_key, None)

    if "N7" in codes:
        st.caption("↩ Trả lại: mỗi shot một câu ý đồ (vd \"Kelly lùi 1 m\", \"xe nôi phải đọc được\") — Quay phim chọn số đo")
        for i in s.get("shots") or []:
            st.text_input(f"Ý đồ shot {i}", key=f"{key}_N7_y_{i}", disabled=busy)
        if st.button(_label("N7"), key=f"{key}_N7", disabled=busy):
            tra = [{"shot": i, "y_do": str(st.session_state.get(f"{key}_N7_y_{i}") or "").strip()} for i in s.get("shots") or []]
            tra = [x for x in tra if x["y_do"]]
            if not tra:
                st.session_state[res_key] = ("N7", {"ok": False, "errors": ["trả lại cần ít nhất một câu ý đồ cho một shot"]})
            else:
                run("N7", lambda: stage_desk.return_(conn, pid, data_dir, scene, tra, who, user=user))

    if "N8" in codes:
        prev_key = f"{key}_N8_preview"
        if st.button(_label("N8"), key=f"{key}_N8", disabled=busy):
            r = stage_desk.reset(conn, pid, data_dir, scene, who, confirm=False)
            if r.get("needs_confirm") and r.get("preview"):
                st.session_state[prev_key] = r["preview"]
            else:
                st.session_state[res_key] = ("N8", r)
        pv = st.session_state.get(prev_key)
        if pv:
            st.warning("🗑 Xem trước Làm lại từ Đạo diễn: " + str(pv.get("say") or "")
                       + (f" · cất thư mục {pv['archive']}" if pv.get("archive") else ""))
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Xác nhận làm lại", key=f"{key}_N8_go", disabled=busy):
                    st.session_state.pop(prev_key, None)
                    run("N8", lambda: stage_desk.reset(conn, pid, data_dir, scene, who, confirm=True))
            with c2:
                if st.button("Hủy", key=f"{key}_N8_cancel"):
                    st.session_state.pop(prev_key, None)

    if "N9" in codes:
        ok = st.checkbox(CONFIRM["N9"], key=f"{key}_N9_ok", disabled=busy)
        drawn = list(s.get("drawn") or [])
        drawn_ok = st.checkbox(f"Shot {', '.join(map(str, drawn))} đã vẽ ảnh — vẫn dựng lại (ảnh sẽ lệch nền)",
                               key=f"{key}_N9_drawn", disabled=busy) if drawn else False
        if st.button(_label("N9"), key=f"{key}_N9", disabled=busy):
            if not ok or (drawn and not drawn_ok):
                st.session_state[res_key] = ("N9", {"ok": False, "errors": ["tích ô xác nhận trước khi dựng lại"]})
            else:
                run("N9", lambda: stage_desk.rerender(conn, pid, data_dir, scene, who, confirm_drawn=bool(drawn_ok)))

    if "N11" in codes:
        ok = st.checkbox(CONFIRM["N11"], key=f"{key}_N11_ok", disabled=busy)
        if st.button(_label("N11"), key=f"{key}_N11", disabled=busy):
            if not ok:
                st.session_state[res_key] = ("N11", {"ok": False, "errors": ["tích ô xác nhận trước khi render lại nền 3D"]})
            else:
                run("N11", lambda: stage_desk.render_plates(conn, pid, data_dir, scene, who))

    if busy or (pr or {}).get("state") == "running":
        st.button("🔄 Xem tiến độ", key=f"{key}_refresh")
    got = st.session_state.get(res_key)
    if got:
        _show_result(*got)
