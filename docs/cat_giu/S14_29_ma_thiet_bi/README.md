# S14.29 — Đăng nhập LAN bằng MÃ THIẾT BỊ (CẤT, không dùng)

**Trạng thái:** người dùng BỎ (05/10: IT hỗ trợ mạng, không cần làm; xác nhận lại 06/10: "loại hẳn ra trong plan … hoặc cất đi phòng khi sau
này dùng lại"). Đã gỡ khỏi `docs/KE_HOACH_SUA_SAU_DU_AN_8.md` và `TODO.md`; code KHÔNG có trên `main`. Thư mục này giữ đủ để làm lại.

## Đã làm (cloud 06/10, nhánh `claude/read-s14-45-cloud-tasks-ngb0q2`, commit 832a711 — không gộp)
- `core/machine_auth.py`: `identify()` — có tên DNS thì dùng DNS; không có thì mã thiết bị của trình duyệt (`secrets.token_urlsafe(32)`, cookie
  `vdp_device` dài hạn); máy = `DEV-<6 ký tự đầu sha256("vdp-device:"+mã)>`; CSDL chỉ lưu băm (`machine_approvals.kind` / `device_hash`);
  cùng tên DEV- mà băm khác → từ chối; cùng luật máy đầu tự duyệt / máy sau chờ Owner / thu hồi; mã không lên URL, không vào nhật ký.
- `core/db.py`: 2 cột `machine_approvals.kind`, `device_hash` (V2_COLUMNS).
- `dashboard/common.py`: `request_device()` (đọc `st.context.cookies`), `ensure_device_cookie()` (script nhỏ ghi cookie rồi tải lại 1 lần);
  `dashboard/header.py` truyền mã vào `sign_in` / `session_refusal`; `dashboard/team_screen.py` ghi "(mã thiết bị trong trình duyệt)".
- `tests/test_s1429_device_code.py` (9 test đỏ → xanh); 156 test liên quan qua.
- **Thử thật bằng Chromium trong cloud** (`DASHBOARD_LAN=1`, IP không có PTR): cookie 43 ký tự, tải lại 1 lần, mã không lên URL; máy đầu
  `DEV-AD1E83` tự duyệt; trình duyệt thứ hai `DEV-C5DA3E` chờ Owner duyệt. Chưa thử trong mạng công ty.

## Dùng lại
`git apply --3way docs/cat_giu/S14_29_ma_thiet_bi/S14_29.patch` từ gốc repo (patch làm trên `main` 06/10 sáng: `core/db.py` /
`dashboard/header.py` có thể đã đổi — gỡ xung đột tay), rồi chạy `tests/test_s1429_device_code.py tests/test_machine_auth.py`, rà KỸ (quyền).

## Dòng việc cũ trong kế hoạch (nguyên văn)
- [ ] S14.29 · Đăng nhập LAN: nhận diện dự phòng bằng MÃ THIẾT BỊ khi IP không có tên DNS ngược (người dùng chọn phương án b 05/10) — thử thật: dải 10.7.168.x chỉ 1/39 IP có PTR (dải 10.7.30.x đủ) → `core/machine_auth.machine_of` trả 'không xác định được tên máy'. Thiết kế: không tra được tên → trình duyệt nhận mã ngẫu nhiên (`secrets.token_urlsafe`, lưu cookie/localStorage dài hạn qua component nhỏ; đọc lại bằng `st.context.cookies` hoặc tham số an toàn) → 'máy' = `DEV-<6 ký tự đầu mã>` (lưu băm mã, không lưu mã thô) trong `machine_approvals` + cột loại (dns/device); cùng luật: máy đầu của người đã có vai trò tự duyệt (nhật ký), máy sau chờ Owner, Owner thu hồi được; có tên DNS thì vẫn dùng tên DNS; xóa dữ liệu trình duyệt/đổi trình duyệt = máy mới (báo rõ trên màn đăng nhập); mã không được lộ trong URL (không dùng `?…`), không ghi vào nhật ký; test: không PTR → cấp mã → lần sau cùng mã vào được, mã lạ/giả → chờ duyệt, mã thu hồi → từ chối · nặng:2 · ✖ · BỎ (người dùng 05/10 trên trang 📋: IT hỗ trợ mạng, không cần làm nữa) · TẠM GÁC (người dùng 05/10: bỏ qua đăng nhập máy đồng nghiệp, đã nhờ IT mở mạng dải 10.7.168.x) — S14.18 làm trước, dựa trên tên DNS; người dùng DUYỆT thiết kế 05/10; ban đầu định làm TRƯỚC S14.18 (giới hạn theo người gắn vào máy) — RÀ KỸ

## Ghi chú cũ trong TODO.md (nguyên văn)
- **05/10 chiều — S14.29 TẠM GÁC ⏸** (người dùng: bỏ qua đăng nhập máy đồng nghiệp, đã nhờ IT mở TCP 8501 dải 10.7.168.x). Việc kế S14: **S14.18** giới hạn theo người (RÀ KỸ, dựa trên tên DNS) → S14.26 → S14.27 → S14.28.
- **05/10 ~13:00 — máy đồng nghiệp thứ 2 (IP 10.7.168.226, dây mạng công ty):** (1) không kết nối tới máy chủ 10.7.30.23:8501 (ERR_CONNECTION_TIMED_OUT) — tường lửa máy chủ cho python.exe mọi địa chỉ (đã kiểm) → nghi mạng công ty chặn giữa dải 10.7.168.x ↔ 10.7.30.x; KẾT QUẢ từ 10.7.168.226: ping True (1 ms) nhưng TCP 445 False + 8501 False → định tuyến thông, TCP bị chặn giữa dải (ACL mạng hoặc CrowdStrike; tường lửa Windows máy chủ cho python.exe mọi địa chỉ) → người dùng nhờ IT mở TCP 8501 từ 10.7.168.0/24 tới 10.7.30.23 (`6GYQ2G3`); thử mở cổng thăm dò 80/443 bị chặn quyền (Expose Local Services) — không làm; (2) dải 10.7.168.x hầu như không có DNS ngược (1/39) → người dùng chọn phương án b: S14.29 mã thiết bị.
