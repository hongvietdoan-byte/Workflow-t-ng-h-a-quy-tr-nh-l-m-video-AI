"""C-M48-DESK-UI (V3.1 M4.8 Đợt 1, 22/10) — "Bàn đạo diễn 3D": hàng nút trong expander từng cảnh của màn XEM sân khấu 3D (Bước 2,
dashboard/stage_view_ui.py gọi render_scene ở cuối expander). Cờ `stage_desk_ui` (TẮT = render_scene trả về ngay, không đọc / không vẽ gì;
REQUIRES stage_view_ui). Kế hoạch docs/KE_HOACH_BAN_DAO_DIEN_3D_DASHBOARD_2026-10-21.md mục 3, 4, 9; sổ quyết định
v31-ep-stage-desk-actions-2026-10-21 (S-A … S-G).

Mỗi nút gọi ĐÚNG MỘT hàm công khai của core/stage_desk (lõi C-M48-DESK-CORE: khóa S, luồng nền, write guard, quyền EP đều ở lõi — lõi kiểm
lại mọi điều kiện khi bấm, giao diện chỉ ẩn / khóa / hỏi xác nhận):
  N1 check_inputs · N2 estimate · N3 write_prompt · N4 load_answer · N5 build_sheet · N6 approve · N7 return_ · N8 reset · N9 rerender ·
  N10 score · N11 render_plates · N12 previs · N14 crew_user_pick · N15 refresh_world_map · N16 set_family.
N12 dựng previs cục bộ; N13 API chưa nằm trong ORDER. Các nút hiện có không gọi Claude trả phí.
Danh sách nút = scene_status()["buttons"] (hợp phase). Đang chạy / khóa S của người khác → mọi nút trừ 💲 Ước tính bị khóa + hiện tiến độ
(desk_progress.json qua scene_status()["progress"]). Thao tác đổi dữ liệu (N4 nạp trả lời, N6 duyệt, N8 làm lại, N9 dựng lại, N11 render
nền) phải tích xác nhận; N8 xem trước (S-D) rồi mới xác nhận; shot đã vẽ ảnh → xác nhận riêng (Q-D).
Quyền (S-B): ✅ Duyệt / ↩ Trả lại chỉ hiện cho Executive Producer (stage_desk.is_executive_producer với common.access_user()) và chỉ khi
người bấm là NGƯỜI — phiên Claude thao tác Dashboard (`?op=claude`, CHỐT MỘT CHIỀU common.op_claude_seen — đổi `?op=nguoi` không hạ xuống) bấm các nút khác
với actor "ai", không thấy Duyệt / Trả lại. Nút GHI (N4 / N8 / N9 / N11) truyền user = common.access_user() để lõi kiểm quyền SỬA dự án.
Rà kỹ 22/10: mọi lời gọi lõi qua run() — bắt ngoại lệ thành câu lỗi (không làm sập Bước 2), BỎ TÍCH các ô xác nhận đã dùng (bấm lần
sau phải xác nhận lại) rồi st.rerun() để trạng thái / nút vẽ lại theo lõi; kết quả hiện MỘT lần."""
import json
import os
from typing import Dict, Optional

import streamlit as st

FLAG = "stage_desk_ui"
ORDER = ("N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8", "N9", "N10", "N11", "N12", "N14", "N15", "N16")
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
    if common.op_claude_seen():
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
        if pr.get("action") == "N12" and res.get("ok"):
            shots = (res.get("summary") or {}).get("shots") or []
            if shots:
                st.caption("Các shot đã đưa vào previs: " + ", ".join(map(str, shots)))
            for title, key in (("Video clay", "path"), ("Video depth", "depth_path"), ("Kế hoạch", "plan_path")):
                if res.get(key):
                    st.caption(title)
                    st.code(str(res[key]))
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
    """(obj | None, lỗi | None). Ô trống → đọc crew/tra_loi_<phase>.json trong thư mục đoạn. data_dir của Dashboard là đường TƯƠNG ĐỐI
    (common.DATA = data/projects, theo thư mục chạy Streamlit) → câu báo in đường tuyệt đối để người đọc tìm đúng tệp."""
    from core import stage_desk
    if not (text or "").strip():
        try:
            path = os.path.abspath(os.path.join(stage_desk.seg_dir(data_dir, pid, stage_desk.segment(conn, pid, scene)), "crew",
                                                f"tra_loi_{phase}.json"))
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


def _camera_controls(text, key, busy):
    """Lựa chọn chỉ áp vào JSON N4, còn quyền/khóa/đo/duyệt do lõi hiện có kiểm."""
    from dashboard.stage_camera_controls import answer_specs, controls_revision
    try:
        answer = json.loads(text)
        specs = answer_specs(answer)
        revision = controls_revision(answer)
    except (ValueError, TypeError):
        specs = []
    if not specs:
        st.caption("Dán JSON yêu cầu khung để chọn phía máy và ngưỡng thấy của từng vật phụ trước khi nạp.")
        return {}
    seen = set()
    for spec in specs:
        shot = spec.get("shot")
        components = spec.get("thanh_phan")
        if type(shot) is not int or shot in seen or not isinstance(components, list):
            st.caption("JSON cần mỗi shot_spec một số shot duy nhất và danh sách thanh_phan; sửa JSON trước khi chọn máy.")
            return {}
        seen.add(shot)
        keys = [c.get("vat") for c in components if isinstance(c, dict) and c.get("vai") == "phu"]
        if any(not isinstance(k, str) for k in keys) or len(set(keys)) != len(keys):
            st.caption("JSON cần khóa vật phụ duy nhất trong từng shot; sửa JSON trước khi chọn ngưỡng.")
            return {}
    labels = {None: "Giữ yêu cầu trong JSON", "front": "Trước (+ hướng A→B)", "back": "Sau (− hướng A→B)",
              "left": "Trái (nhìn từ A sang B)", "right": "Phải (nhìn từ A sang B)"}
    st.caption("Phía máy theo trục có hướng A→B của nhịp: trước/sau tính từ trung điểm; trái/phải giữ quy ước trục 180°. "
               "Thiếu trục hoặc không đạt ngưỡng sẽ báo lỗi, không tự bỏ ý đồ. Chỉ có hiệu lực khi nạp JSON qua N4.")
    key = f"{key}_intent_{revision}"
    choices = {}
    for spec in specs:
        shot = spec.get("shot")
        side = st.selectbox(f"Phía máy shot {shot}", options=list(labels), format_func=labels.get,
                            key=f"{key}_camera_side_{shot}", disabled=busy)
        minimums = {}
        for component in spec.get("thanh_phan") or []:
            if not isinstance(component, dict) or component.get("vai") != "phu":
                continue
            obj = component.get("vat")
            if st.checkbox(f"Ép ngưỡng thấy vật phụ {obj} — shot {shot}", key=f"{key}_min_on_{shot}_{obj}", disabled=busy):
                minimums[obj] = st.number_input(f"Tối thiểu thấy {obj} (%) — shot {shot}", min_value=0.0, max_value=100.0,
                                                value=50.0, step=5.0, key=f"{key}_min_{shot}_{obj}", disabled=busy)
        if side is not None or minimums:
            choices[shot] = {"camera_side": side, "minimums": minimums}
    return choices


def _cli_proposal_controls(conn, pid, data_dir, scene, key, who, user, busy):
    from core import stage_cli_proposal
    from dashboard import paid_confirm
    revision_key = f"{key}_N4_proposal_revision"
    if st.session_state.get(revision_key):
        st.caption("JSON đề xuất đã ghim vào đúng đầu vào/vai lúc tạo. Chưa nạp; vẫn cần xác nhận N4 bên dưới.")
        if st.button("Bỏ ghim đề xuất để dùng JSON nhập tay", key=f"{key}_N4_manual", disabled=busy):
            st.session_state.pop(revision_key, None)
            st.session_state[f"{key}_N4_ok"] = False
    quoted = stage_cli_proposal.quote(conn, pid, data_dir, scene, user=user)
    if not quoted.get("ok"):
        st.caption("Giao vai CLI chưa sẵn sàng: " + "; ".join(quoted.get("errors") or []))
        return
    suffix = quoted["revision"][:24]
    consent = st.checkbox("Tôi đồng ý dùng hạn mức gói Claude CLI để tạo đề xuất; chưa nạp hay duyệt máy",
                          key=f"{key}_N4_cli_consent_{suffix}", disabled=busy)
    if paid_confirm.paid_button("Giao vai cho Claude", key=f"{key}_N4_cli_{suffix}", tag=quoted["tag"],
                                disabled=busy or not consent,
                                question="Tạo JSON đề xuất bằng CLI của dự án, dùng hạn mức gói. CLI có thể hỏi lại khi lỗi định dạng/thời gian chờ. "
                                         "Chưa nạp N4 hay duyệt máy; tiếp tục?"):
        result = stage_cli_proposal.generate(conn, pid, data_dir, scene, who, user=user,
                                              expected_revision=quoted["revision"], confirmed=consent)
        if result.get("ok"):
            # Đặt TRƯỚC khi tạo text_area/checkbox N4 trong lượt vẽ hiện tại.
            st.session_state[f"{key}_N4_json"] = json.dumps(result["answer"], ensure_ascii=False, indent=2)
            st.session_state[revision_key] = result["revision"]
            st.session_state[f"{key}_N4_ok"] = False
            st.rerun()
        else:
            st.error("; ".join(result.get("errors") or ["Không tạo được đề xuất CLI."]))


def _height_fix_panel(conn, pid, shots, key, user, busy):
    from core import assets, library_height
    from dashboard import common
    import hashlib
    if not common.allowed('assets'):
        return
    try:
        entries, problems = library_height.missing_heights(conn, pid, shots)
    except Exception:
        st.caption('Không đọc được chiều cao Kho cho cảnh này; mở Kho để kiểm tra hồ sơ.')
        return
    for problem in problems:
        st.caption(problem)
    if not entries:
        return
    with st.expander('Bổ sung chiều cao còn thiếu — sửa Kho CHUNG'):
        st.caption('Nhập số đo theo mét. Lưu vào hồ sơ Kho chung, ảnh hưởng mọi dự án dùng hồ sơ này; không tạo bản sao dự án.')
        for entry in entries:
            revision = hashlib.sha256(entry['snapshot'].encode('utf-8')).hexdigest()[:24]
            prefix = f"{key}_height_{entry['id']}_{revision}"
            height = st.number_input(f"Chiều cao {entry['name']} — Kho #{entry['id']} (m)", min_value=0.0,
                                     max_value=30.0, value=0.0, step=0.01, key=prefix, disabled=busy)
            confirmed = st.checkbox('Tôi xác nhận sửa Kho CHUNG, ảnh hưởng mọi dự án dùng hồ sơ này',
                                    key=f'{prefix}_confirm', disabled=busy)
            if st.button('Lưu chiều cao vào Kho chung', key=f'{prefix}_save', disabled=busy or not confirmed or height < .2):
                try:
                    library_height.save_height(conn, entry['id'], height, user=user, confirmed=confirmed,
                                               expected_profile_snapshot=entry['snapshot'])
                except assets.AssetError as error:
                    st.error(str(error))
                except Exception:
                    st.error('Không lưu được chiều cao; tải lại để kiểm tra quyền và hồ sơ Kho.')
                else:
                    st.success('Đã lưu chiều cao vào Kho chung.')
                    st.rerun()


def render_scene(p, pid: int, data_dir: str, scene) -> None:
    """Hàng nút của MỘT cảnh, vẽ trong expander của màn XEM. Cờ tắt → không đọc / không vẽ gì."""
    if not enabled():
        return
    from core import stage_desk
    conn = p.conn
    key = f"desk_{pid}_{scene}"
    for k in st.session_state.pop(f"{key}_clear", None) or []:     # rà kỹ mục 1: bỏ tích ô xác nhận TRƯỚC khi vẽ widget (lượt sau bấm)
        st.session_state[k] = False
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
    _height_fix_panel(conn, pid, s.get('shots') or [], key, user, busy)
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

    def run(code: str, fn, clear=(), after=None):
        """Gọi lõi: ngoại lệ → câu lỗi (rà kỹ mục 2); bỏ tích ô xác nhận `clear` (mục 1); vẽ lại theo trạng thái mới (mục 6)."""
        try:
            res = fn() or {}
        except Exception as e:  # noqa: BLE001 - lõi ném (sqlite / segment / luồng nền): nói lý do, không làm sập Bước 2
            res = {"ok": False, "errors": [f"lõi lỗi {type(e).__name__}: {e}"]}
        st.session_state[res_key] = (code, res)
        if after:
            after(res)
        st.session_state[f"{key}_clear"] = [f"{key}_{c}" for c in clear]
        st.rerun()

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

    if "N12" in codes:
        st.caption("Previs cục bộ bằng Blender; mặc định dừng nếu đường đi không tìm được lối. Sản phẩm ghi vào thư mục lượt mới, không thay lượt cũ.")
        selected_shots = st.multiselect("Shot đưa vào previs", options=list(s.get("shots") or []),
                                        default=list(s.get("shots") or []), key=f"{key}_N12_shots", disabled=busy)
        uniform_run = st.checkbox("Chạy đều, giữ tổng thời lượng kịch bản", key=f"{key}_N12_uniform", disabled=busy)
        lens_range = st.slider("Dải tiêu cự (mm)", min_value=24, max_value=35, value=(24, 35),
                               key=f"{key}_N12_lens", disabled=busy)
        orbit = st.slider("Góc vòng quanh nhân vật (độ)", min_value=0, max_value=180, value=0,
                          key=f"{key}_N12_orbit", disabled=busy)
        if st.button(_label("N12"), key=f"{key}_N12", disabled=busy):
            if not selected_shots:
                st.session_state[res_key] = ("N12", {"ok": False, "errors": ["chọn ít nhất một shot có máy đo được"]})
            else:
                run("N12", lambda: stage_desk.previs(conn, pid, data_dir, scene, shots=set(selected_shots),
                                                       opts={"uniform_run": uniform_run,
                                                             "lens_range": tuple(lens_range), "orbit": float(orbit)},
                                                       who=who, user=user))

    if "N14" in codes:
        st.caption("Chỉ chọn trong những lần đo đã ghi cho đúng shot; lựa chọn có hiệu lực ở lượt chốt kế tiếp.")
        for shot in s.get("shots") or []:
            history = list((s.get("shot_hist") or {}).get(str(shot)) or [])
            if not history:
                continue
            chosen = (s.get("accepted") or {}).get(str(shot))
            index = history.index(chosen) if chosen in history else len(history) - 1
            pick = st.selectbox(f"Lần đo cho shot {shot}", options=history, index=index,
                                key=f"{key}_N14_pick_{shot}", disabled=busy)
            if st.button(f"Chọn lần đo cho shot {shot}", key=f"{key}_N14_{shot}", disabled=busy):
                run("N14", lambda shot=shot, pick=pick: stage_desk.crew_user_pick(
                    conn, pid, data_dir, scene, shot, pick, who=who, user=user))

    if "N15" in codes and st.button(_label("N15"), key=f"{key}_N15", disabled=busy):
        run("N15", lambda: stage_desk.refresh_world_map(conn, pid, data_dir, scene, who=who, user=user))

    if "N16" in codes:
        for i, suggestion in enumerate(s.get("family_suggestions") or []):
            members = suggestion.get("members") or []
            evidence = "; ".join(
                f"Kho #{m['place_id']} ({m.get('stage') or 'chưa rõ'}): đã khai {m.get('declared') or 'chưa khai'}"
                for m in members)
            observed = json.dumps(suggestion.get("spots") or {}, ensure_ascii=False, sort_keys=True)
            st.warning(f"VÀNG — vị trí quan sát trùng nhau ({observed}); {evidence}. Đây chỉ là gợi ý, không tự gộp.")
            family = st.text_input("Tên họ sân khấu cần khai", value=suggestion.get("family") or "",
                                   key=f"{key}_N16_family_{i}", disabled=busy)
            if st.button(f"Khai họ cho {', '.join('#'+str(x) for x in suggestion.get('place_ids') or [])}",
                         key=f"{key}_N16_{i}", disabled=busy):
                run("N16", lambda suggestion=suggestion, family=family: stage_desk.set_family(
                    conn, pid, data_dir, scene, suggestion.get("place_ids") or [], family, who=who, user=user))

    if "N4" in codes:
        _cli_proposal_controls(conn, pid, data_dir, scene, key, who, user, busy)
        answer_text = st.text_area("📥 Câu trả lời vai (JSON) — dán vào đây, hoặc để trống để đọc crew/tra_loi_<phase>.json của đoạn",
                     key=f"{key}_N4_json", height=120, disabled=busy)
        camera_choices = _camera_controls(answer_text, key, busy) if s.get("phase") in ("quay_phim", "quay_phim_duyet") else {}
        ok = st.checkbox(CONFIRM["N4"], key=f"{key}_N4_ok", disabled=busy)
        if st.button(_label("N4"), key=f"{key}_N4", disabled=busy):
            if not ok:
                st.session_state[res_key] = ("N4", {"ok": False, "errors": ["tích ô xác nhận trước khi nạp"]})
            else:
                obj, err = _answer_obj(conn, pid, data_dir, scene, s.get("phase"), st.session_state.get(f"{key}_N4_json") or "")
                if err:
                    st.session_state[res_key] = ("N4", {"ok": False, "errors": [err]})
                else:
                    from dashboard.stage_camera_controls import apply_camera_controls
                    try:
                        obj = apply_camera_controls(obj, camera_choices)
                    except ValueError as e:
                        st.session_state[res_key] = ("N4", {"ok": False, "errors": [str(e)]})
                    else:
                        run("N4", lambda: stage_desk.load_answer(conn, pid, data_dir, scene, obj, who, user=user,
                            expected_proposal_revision=st.session_state.get(f"{key}_N4_proposal_revision")), clear=("N4_ok",))

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
                def forget_marks(res):
                    if res.get("ok") or res.get("stale"):
                        st.session_state.pop(marks_key, None)
                run("N6", lambda: stage_desk.approve(conn, pid, data_dir, scene, who, user=user, confirm_drawn=bool(drawn_ok),
                                                     expected_marks=st.session_state[marks_key]),
                    clear=("N6_ok", "N6_drawn"), after=forget_marks)

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
            try:
                r = stage_desk.reset(conn, pid, data_dir, scene, who, confirm=False, user=user)
            except Exception as e:  # noqa: BLE001 - xem trước lỗi: nói lý do
                r = {"ok": False, "errors": [f"lõi lỗi {type(e).__name__}: {e}"]}
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
                    run("N8", lambda: stage_desk.reset(conn, pid, data_dir, scene, who, confirm=True, user=user))
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
                run("N9", lambda: stage_desk.rerender(conn, pid, data_dir, scene, who, confirm_drawn=bool(drawn_ok), user=user),
                    clear=("N9_ok", "N9_drawn"))

    if "N11" in codes:
        ok = st.checkbox(CONFIRM["N11"], key=f"{key}_N11_ok", disabled=busy)
        if st.button(_label("N11"), key=f"{key}_N11", disabled=busy):
            if not ok:
                st.session_state[res_key] = ("N11", {"ok": False, "errors": ["tích ô xác nhận trước khi render lại nền 3D"]})
            else:
                run("N11", lambda: stage_desk.render_plates(conn, pid, data_dir, scene, who, user=user), clear=("N11_ok",))

    if busy or (pr or {}).get("state") == "running":
        st.button("🔄 Xem tiến độ", key=f"{key}_refresh")
    got = st.session_state.pop(res_key, None)                       # rà kỹ mục 6: kết quả hiện một lần (tiến độ nền ở khối trên)
    if got:
        _show_result(*got)
