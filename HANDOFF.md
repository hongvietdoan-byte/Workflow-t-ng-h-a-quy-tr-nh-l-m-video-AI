# Bàn giao K0a — kế hoạch kiểm soát (10/10/2026)

Nguồn: `docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md` mục 3.9 / 4 / 8 (K0a). 0 USD, không đổi hành vi pipeline (trừ ước chi qc).

## Đã làm
- `devsys/stages.json` (sổ khâu L1–L16, L14/L15 tách âm / phụ đề / dựng / popup) + `devsys/stages.py` (đọc + kiểm + bảng tóm tắt).
- `devsys/decisions.json`: thêm d84–d94 (prompt_formula, stage_facts derive + câu trái 'cau', change_audit, before_run, giải máy,
  render nền, end_popup, plate_layout_qc, kiểm yêu cầu khung, kiểm câu trả lời dàn cảnh).
- `devsys/error_types.json`: L1–L15, V1–V4, A1–A4 — code_do / claude_khai theo sản phẩm, trạng thái co / hoc_viec / xay + đợt.
- `core/shot_intent.py`: schema BYĐ tối thiểu + `validate(byd, conn)`; enum tái dùng stage_grid / stage_solver / plate_env. CHƯA nối (K1a).
- `tests/golden/` (README + loader + 8 ca chuyển từ `tests/fixtures/stage_facts_golden.json`, đã xóa tệp cũ).
- `core/cost.py` `LLM_STAGE_TOKENS["qc"]` (6000, 900) → (6000, 5200); `tools/experiments/qc_test_p24.py` bỏ hệ số ×2.
- `devsys/areas.json` khai file mới (không tăng version).

## Test
`tests/test_devsys_stages.py`, `tests/test_shot_intent.py`, `tests/test_cost.py::QcStageTokensTests` (mới); cùng nhóm devsys*, stage_facts,
ước chi: 360 passed. Bảng tóm tắt: `py -m pytest -s tests/test_devsys_stages.py -k summary`.

## Đợt 2 (cùng ngày)
- Trang devsys "Làm ↔ Kiểm" (`devsys/app.py:page_stages`): bảng khâu (đỏ = tốn tiền thiếu kiểm trước, vàng = đọc chữ tự do) + bảng
  23 loại lỗi (đỏ = chỉ đang xây). Điều kiện "xong" của K0a.
- Trường `co` ({khau|truoc|sau: cờ}) trên L2, L7, L15a, L16; `stages.effective` đọc `core.features.state` (lỗi → giữ ghi tay + `_co_ghi`).

## Việc mở
- Plan mục 3.9 đòi "mỗi ô BYĐ đủ 3 câu (dữ kiện / kiểm gói / mệnh đề QC)" — chưa có test (K0b/K1a).
- Dòng không có `co` (vd L9 kiểm sau gồm nhiều lớp khác cờ) vẫn ghi tay theo `docs/RA_SOAT…` 10/10.
