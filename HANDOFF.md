# Bàn giao ĐỢT 19 việc 1

Nhánh `codex/d19-viec1-narration`, nền `c32162dc`, chưa commit theo chỉ đạo. File: tests/test_narration_regression.py, devsys/areas.json (version87 giữ), docs/RA_D19_VIEC1_CODEX_2026-10-20.md, HANDOFF.md.

Đã xong test ngoại tuyến: đỏ 21/35, cuối 42 passed +21 xfailed strict (G15/G16/G17/G53). Xem RA cho map ca và cô lập an toàn. _take_segments thuộc VideoRunner. Không sửa production/TODO/PLAN, không push/main/live/data/API.

Đã rà độc lập và sửa: xfail chỉ nhận sai lệch KnownNarrationBug ở đầu ra gốc (assert khác vẫn đỏ), winreg giả trên nền tảng khác Windows, chặn provider/model loader trước import caller. Bước kế: phiên điều phối đọc diff sửa, sau đó Claude rà quy ước7 và chạy cả bộ Windows theo lịch gộp. Không chạy pytest rộng thêm tại nhánh này. Chưa xác minh dữ liệu thật/chất lượng; 4 lỗi gốc chờ M2.9.

Bằng chứng sau rà: targeted 42 passed +21 xfailed /8,40s; diff check sạch; 4 kiểm teardown môi trường giả (thiếu/có provider × đóng thường/lỗi) đạt. Chưa chạy Linux thực tế.
# Chốt root Đ19v1

- Root đã đọc sửa lần hai; 42passed/21xfailed strict /8,40s, không sửa lỗi sản xuất. Chỉ push nhánh riêng; Claude rà/gộp và chạy cả bộ Windows. M1.1/M1.4a giữ owner Claude; không merge/pull/restart live.
