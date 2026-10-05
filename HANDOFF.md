# HANDOFF — S14.23 Bộ não prompt Đợt 4: bảng kê tài nguyên trước Director

Nhánh `s14-23-asset-checklist` (từ origin/main 43f5162). Chưa push, chưa sửa TODO.md.

## Đã làm
- Cờ `asset_checklist` (`core/features.py`, TẮT, `verified: False`).
- `prompts/27_asset_checklist.md` (số 26 đã dùng — đúng khối sửa 04/10 của kế hoạch).
- `core/asset_checklist.py`: một lượt Claude (không ảnh), khâu `asset_checklist` qua `llm_runner.tagged` + `ask_json` (sổ chi của client),
  `STAGE_SETTINGS["asset_checklist"] = effort low, max_tokens 6000`, `cost.LLM_STAGE_TOKENS` (12000, 2500), ngân sách dự án dòng
  `claude_director` (`project_budget.claude_stage`). Kho gửi kèm: tên + tên khác + loại + số ảnh + đã gắn (cả loại `outfit` Trang phục, có câu
  "trang phục, không phải nhân vật"); Kho trống → nói rõ với model và trên màn.
- Code không tin id của model: id không có trong Kho / khác loại → bỏ + ghi chú; tên trùng khớp (tên/tên khác, cùng loại; đạo cụ↔vũ khí coi là
  một) → code tự ghép + ghi chú; danh sách thiếu do code tính lại; trạng thái đọc lại mỗi lần (gắn xong → ✅). Kịch bản đổi → `stale`.
- Luật 1: cờ tắt / chưa có Claude / chưa có kịch bản → `ChecklistError` rõ, không gọi; lỗi Claude → diag `asset_checklist_failed` (warn);
  chạy xong → diag `asset_checklist` (info) ghi số thứ cần/thiếu + "đã gửi Kho N mục, kịch bản X ký tự". Stage diag = `director`.
- Màn hình: `dashboard/steps/step1_checklist.py` `checklist_panel(p, pid, scope)` — nút "📋 Lập bảng kê tài nguyên · Claude ≈ … USD (ước tính)",
  bảng ✅ đã gắn / ✅ có trong Kho (nút **Gắn**) / ⚠️ thiếu (hướng dẫn tạo ở Kho). Gọi ở 2 chỗ, ngay trên nút chạy Director:
  `dashboard/steps/step1_director.py` `director_panel` (scope "dir") và `dashboard/steps/step1_v2.py` `_primary_action` nhánh `plan` (scope "hero").
  KHÔNG chạm `step1_box.py` / khung nhập kịch bản (S14.21).
- `MockLlm` có nhánh "# Bảng kê tài nguyên" (LLM_PROVIDER=mock).
- `tests/test_price_label_scan.py`: thêm `asset_checklist.run` vào PAID (nút phải có giá).
- `devsys/areas.json`: 2 file code, `prompts/27_*`, test, cờ vào khu `step1` (không tăng version).

## Cờ tắt = y hệt
Không vẽ gì (test chặn mọi `st.*`), không gọi Claude; prompt Director y hệt khi bật/tắt (module không ghi vào prompt Director).

## Test
`tests/test_asset_checklist.py` 18 test (đỏ trước ở commit đầu, xanh sau). Bộ liên quan (16 file) 268 qua.

## Gộp / còn mở
- Gộp với S14.21: nếu S14.21 sửa `step1_v2.py` `_primary_action` nhánh `plan` hoặc `step1_director.py` gần `client = llm_client()` → giữ 2 dòng gọi `checklist_panel`.
- Chưa chụp giao diện thật (bảng trong ô hero v2 có thể chật — nếu chật, bỏ lời gọi scope "hero", giữ ở 1d).
- Nghiệm thu cần Claude thật (tốn tiền, hỏi người dùng): 2 kịch bản thật — Kho đủ / Kho thiếu — báo đúng thiếu, không báo nhầm thứ đã có.
- Bảng kê chỉ để xem + gắn nhanh; chưa đưa vào prompt Director (kế hoạch không yêu cầu). Nút "tạo mới" chỉ là hướng dẫn sang Kho.
- Đạo cụ/vũ khí vẫn chưa có trường `prop_asset` trong schema cảnh (lỗ nhỏ kế hoạch nêu) — chưa làm, ngoài phạm vi.
