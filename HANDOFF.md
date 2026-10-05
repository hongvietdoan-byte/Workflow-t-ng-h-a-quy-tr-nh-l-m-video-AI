# HANDOFF — S14.7 (Gói D1: quyền + đăng nhập LAN theo máy được duyệt), nhánh s14-7-d1-access

## Đã xong
- A (3.5 ý 1): nút mở lại dịch vụ hết tiền (thẻ 💵 + hộp ⚙ Ngân sách) chỉ cho quyền "settings"; hộp Ngân sách + Bảng giá kiểm lại quyền khi dựng;
  thùng rác: `trash.restore_as(p, …)` (need_edit) + `admin.trash_section(pid, p)` vẽ trong `access_ui.read_only`.
  Test: test_access_ui.py::UiHoleTests (5), test_trash.py::test_restore_as_checks_the_edit_right.

## Đang dở / bước kế
- B (need_edit lớp lõi), C (user_of đóng khi thiếu e-mail + history need_view), D (ghim streamlit + test disabled), E (đăng nhập theo máy).
