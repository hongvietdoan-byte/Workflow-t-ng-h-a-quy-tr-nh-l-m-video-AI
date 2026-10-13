# Bàn giao Đ13 việc 2 — 14/10/2026
- Đã commit code `bad2a535`; root đọc diff vòng sửa và hồi quy, không thấy lỗi còn mở trong phạm vi. Nhánh chỉ push riêng; cả bộ Windows thuộc phiên gộp, không gộp main/live.
- DONE triển khai, chưa commit/push; nhánh codex/d13-viec2-goi-blockout từ 2c43a28f.
- Đổi core/blockout_sheet.py, tests/test_blockout_sheet.py, skill vòng làm việc (câu K/CX + ví dụ).
- Schema 2: SHA chuẩn hóa số hình học exact ratio, ngày ISO aware; schema 1 SHA raw + naive đọc được có cảnh báo duyệt lại.
- Font Pillow cũ: thử size rồi fallback không size; dependency giữ nguyên.
- Đỏ→xanh: 5 failed/88 passed → 93 passed; bổ sung test bắt thiếu huong_sang → 95 passed cuối (3.33 s).
- Lệnh nhóm: py -m pytest tests/test_blockout_sheet.py tests/test_blockout.py tests/test_blockout_facts.py tests/test_d11_clay.py tests/test_d11_clay_review.py -q -p no:cacheprovider --tb=no.
- Proof cuối 95 passed/3.29s qua pytest.main dưới patch.object(os, "environ", fake_dict) trước import pytest/test, stop teardown; các proof patch.dict cũ không đáp ứng object security, đã thay.
- Có 5 lượt pytest tổng (thêm proof patch.object theo root), lượt thêm do mở rộng allgeometry regression tìm lỗi; không đổi assert cũ.
- RA: docs/RA_D13_VIEC2_CODEX_2026-10-14.md; related_areas không yêu cầu test chậm.
- Không test code mới dạng file nên areas registry giữ sẵn tests/test_blockout_sheet.py, version 74.
- Bước kế: phiên chính RÀ KỸ dataformat/caller; sửa mọi lỗi nếu có, cả bộ Windows trước commit/gộp.
- Chưa thử Pillow cũ cài thật; đã giả lập signature cũ + PNG thật; không API/dữ liệu thật.

## Sau rà độc lập và vòng sửa gom
- Đã đóng 2 P2: bitmap thiếu glyph tiếng Việt gây UnicodeEncodeError; canonical SHA lọt metadata lồng có tên trường trùng geometry.
- Hai hồi quy ĐỎ **2 failed / 29 deselected** → sửa exact geometry paths + font Unicode local/fail rõ trước PNG → **97 passed / 3,43 s** nhóm 5 file; không đổi assert cũ.
- Security: toàn lượt sửa/test dùng patch.object(os, "environ", dict giả) trước import/call, context manager khôi phục; không đọc/sao chép môi trường thật, không API/model/provider thật/subprocess. Proof patch.dict cũ không được dùng làm bằng chứng security.
- Thiếu mọi font Unicode: ValueError actionable, không bỏ dấu/âm thầm thay nhãn; Arial/DejaVu bình thường giữ nguyên, thêm Tahoma/Segoe UI local; root đã đồng ý.
- git diff --check sạch; chưa commit/push/cả bộ Windows. Root đọc diff vòng sửa và kiểm tích hợp trước gộp.

## QA bổ sung HEAD ef9178bb
- QA actual Pillow 10.0.1 còn mở: automatic policy chặn ProcessStartInfo whitelist env + pip isolated/binary-only/target TEMP trước chạy; `blocked by policy`, không lý do chi tiết. Chưa chạy pip/cài/probe/PNG/actual proof; không bypass/đổi runtime/test lại/commit/push. Root đọc RA giới hạn rồi quyết bước kế.
