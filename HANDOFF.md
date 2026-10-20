# Bàn giao Đ20 việc 1

- Xong công cụ đề xuất sổ lỗi chỉ đọc + 9 test xanh; báo cáo `docs/RA_D20_VIEC1_CODEX_2026-10-20.md`.
- Nhánh `codex/d20-viec1-so-loi`, nền `51acfea1`; commit cuối xem git log. Không push, không sửa TODO/kế hoạch/version.
- Rà độc lập đã sửa 2 P2 (mất lịch sử retry, USD vô hạn), đỏ 2 failed → xanh 9 passed. Tiếp: tích hợp chạy cả bộ Windows kể cả test chậm theo related_areas. Không chạy dữ liệu thật/API.
- Mở: ledger native thiếu giá USD → UNKNOWN; Không coi đây là tiền thực đã đối soát.
