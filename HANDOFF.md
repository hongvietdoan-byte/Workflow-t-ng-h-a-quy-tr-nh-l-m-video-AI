# HANDOFF — S14.7 (Gói D1: quyền + đăng nhập LAN theo máy được duyệt), nhánh s14-7-d1-access

## Đã xong (mọi việc A–E)
- A (3.5 ý 1): nút mở lại dịch vụ hết tiền (thẻ 💵 + hộp ⚙ Ngân sách) chỉ cho quyền "settings"; hộp Ngân sách + Bảng giá kiểm lại quyền khi dựng;
  thùng rác: `trash.restore_as(p, …)` (need_edit) + `admin.trash_section(pid, p)` vẽ trong `access_ui.read_only`.
- B (3.5 ý 2): need_edit đầu llm_io (6 hàm), previz.plan_layouts, qc_agent.review_scene, costume.make_character_set, editor_review.run,
  editor_apply.apply, experiments.kling_multishot, claude_tasks._run; `p=None` cho voice.generate, voice_check.redo, model_router.set_override,
  project_budget.set_target/raise_cap, music.submit_drafts + audio_lib.submit_sfx/tts (kèm `project_id=None`); dashboard truyền p=p.
  Test quét `WriteFunctionScanTests` (danh sách KNOWN = 16 hàm cũ chưa kiểm, chỉ được co lại).
- C (3.5 ý 3): `access.user_of` đóng khi có danh tính thiếu e-mail; `Pipeline.history` → need_view.
- D (3.5 ý 4): `streamlit>=1.64` + test thông điệp tự dựng gửi giá trị cho widget disabled.
- E (6b ý 2): `core/machine_auth.py` + bảng `machine_approvals`, `login_attempts`; `header.sign_in` (một lối vào cho form và ?login=)
  → `machine_auth.sign_in`; `require_login` kiểm lại máy mỗi lần tải trang; khối "Máy được duyệt" ở 👥 Nhóm (`team_screen.machines_block`).

## Việc mở / bước kế
- Chưa thử thật trên mạng công ty với DASHBOARD_LAN=1 (cần người dùng: mở từ một máy đồng nghiệp, duyệt ở 👥 Nhóm).
- Lỗi có sẵn (không thuộc D1): người "Chỉ xem" mở màn Kịch bản thấy lỗi đỏ "không thể đổi cài đặt dự án" vì
  `dashboard/steps/step1_prep.py::project_format_panel` tự ghi tỉ lệ khung khi dự án chưa có `aspect`.
