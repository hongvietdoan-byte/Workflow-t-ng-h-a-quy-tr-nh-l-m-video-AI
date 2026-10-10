# HANDOFF — K0b phần 2, nhánh A: bộ kỹ năng kiểm (10/10)

## Đã xong
- `knowledge/checks/<ID>.md` × 23 (L1–L15, V1–V4, A1–A4) + `knowledge/checks/README.md` (mục đích, khuôn, ai đọc, thêm loại theo mục 10).
- `tests/test_knowledge_checks.py`: đủ 23 tệp đúng id `devsys/error_types.json`, 4 mục bắt buộc, enum `claude_khai` có trong tệp,
  `where` của code_do / claude_khai được nhắc, mọi cờ được ghi tên, cách kiểm `xay` ghi đợt. Đỏ (2 failed) → xanh (2 passed).
- `devsys/areas.json` khu vực `devsys`: thêm test + `knowledge/checks/*` (không tăng version).

## Việc mở (chưa làm, ghi lại để nhánh khác / phiên sau)
- `devsys/error_types.json` L9 thiếu enum `horizon_not_visible` mà `core/stage_facts.py` (pitch_horizon) có.
- L6: `stage_facts` có câu observe vị trí theo phần ba (`in_frame`, cờ `scene_qc`) trái N5 — bảng không tính; cần quyết giữ / bỏ.
- L8: BYĐ có `GAME_TPS`, enum khai cỡ cảnh không có. L12: BYĐ dawn / dusk, enum khai chỉ ngay / dem; hướng nguồn sáng (trăng #24) chưa
  có sự thật hình học.
- L11: `core/plate_layout_qc.py:compare` trả `mismatch: false` khi không đọc được ảnh (có lý do) — theo chuẩn phải thành VÀNG.
- Ca hồi quy âm/chữ/dựng (thoại sai người nói, popup không giữ khung cuối) chưa có tệp trong `tests/golden/cases/`.

## Bước kế
- Nhánh điều phối: gộp nhánh này vào main, cập nhật TODO.md (nhánh này không sửa TODO, không push).
