# Bàn giao Đ11 việc 4

Nhánh `codex/d11-viec4-luat-quay`, nền `771b96b6`, chưa commit/push theo chỉ đạo root.
Code/test/ca vàng/areas đã viết, 52 test liên quan xanh 2,27 s; chi tiết `docs/RA_D11_VIEC4_CODEX_2026-10-13.md`.
Root đã bắt 2 lỗi góc theo actor trước/seek sai; đã có đỏ→xanh. Subject render chưa có ID: UI giữ VÀNG thiếu gán, không sửa schema upstream.
Hai cờ TẮT + OPT_IN_ONLY; chưa thử thật/GUI, chưa nối blocking K2 vào luồng report; màn camera thật thuộc bàn dựng sau.
Bước kế: root rà diff/caller, quyết phần thiếu adapter upstream, chạy cả bộ Windows trước gộp. Không bật cờ/khởi động lại/pull/live/API.

Vòng sửa rà độc lập: 3 P2 (NaN/Inf actor/đích, chủ thể BYĐ thiếu đúng người, actor khung cuối dùng trạng thái đầu) đã sửa.
7 ca mới đỏ → xanh, nhóm cuối **59 passed / 1,88 s**; chưa commit. UI thật/adapter blocking/subject ID vẫn còn mở.
