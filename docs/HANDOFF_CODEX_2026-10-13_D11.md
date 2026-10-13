# Bàn giao sau lượt Đ11 — 13/10/2026

- Đ11 việc 2 đã push `codex/d11-viec2-clay`: code `b4e97fa1`, kết quả `b255fed3`. 158 test xanh, Blender local ba bối cảnh giả và 6 PNG. Backend/V3 CLI sẵn; chưa Dashboard/autopilot, chưa nghiệm thu ca thật/cả bộ. Xem RA/HANDOFF riêng trên worktree d11-viec2-clay.
- Đ11 việc 4 code `3716cace` trên `codex/d11-viec4-luat-quay`: 59 test xanh / 1,88 s; hai lỗi root + ba P2 rà độc lập đã có đỏ→xanh. Hai cờ OFF. Còn GUI, nối objects blocking đã duyệt vào report/màn camera, danh tính subject và trạng thái actor cuối, hiệu chỉnh ca thật. Không ghi hoàn tất toàn việc.
- Đ12v6 HEAD50724044/code7f497699 (90 test/4 PNG), Đ13v4 HEAD496e6805/code3752329d (357 test/1 xfail/10 subtests +70 sửa), các phần cũ đã push không làm lại. Đ13 cost O(n²) chờ project_budget27c2e9f3/HEAD84507f59 gộp main; seedance_refs thuộc máy chính, chỉ nhận khi hộp thư chốt.
- Bước kế: fetch origin, đọc HỘP THƯ/Sổ việc TODO và bảng ưu tiên CODEX_TASKS mới. Chốt QA/adapter Đ11v4 nếu upstream đã có; nếu chưa thì tiếp Đ12 việc 2–4, Đ13 việc 1–3, Đ11 việc 5. Đ11v1b mockup9c và Đ18v4 chờ người dùng duyệt; runner sau #24 vẫn chờ chốt. Không tự nhận im lặng là duyệt.

## Luật giữ nguyên

Không gộp main/pull/checkout/restart live D:/AI-Video-Pipeline, không API tốn tiền/data thật/dashboard.env/secrets/admin_auth.py/maintenance worker. Mỗi việc nhánh/worktree riêng, test đỏ→xanh nhóm liên quan, rà độc lập tiền/dữ liệu/quyền, đăng ký areas giữ version68, widget keys giữ nguyên, ghi kết quả/RA và commit tiếng Việt trailer Codex, push nhánh.

Test môi trường/token/credential/loader phải thay os.environ bằng dict giả trước import/gọi code và mock registry/credential/model. Kiểm teardown thiếu/có. Không in/assert/repr môi trường, headers, token hay payload bí mật; không đọc lại khóa thật. Pytest --tb=no, không --showlocals; chẩn đoán chỉ trong fixture cách ly và lỗi đã lọc. Đưa quy tắc vào mọi prompt con/rà.

Đầu lượt get_usage_limits, phân biệt ĐÃ DÙNG/còn. ≥60% một child; 70–90% việc nhỏ; ≥80% thu nhỏ; ≥90% lưu/push/nghỉ. Chỉ lịch tiếp tục sau reset tự nhiên, không monitor định kỳ, không mua/reset credit.
