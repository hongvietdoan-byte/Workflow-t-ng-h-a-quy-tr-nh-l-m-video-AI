# CX21-M23 — checkpoint 21/10/2026 (CHƯA HOÀN TẤT)

- Nhánh `codex/v31-m23`, base `3c55a7ff`. Không push/gộp/main/live/TODO/dữ liệu thật, 0 USD.
- Có adapter Kho v1/v2, cờ `kho_forms_v2` OFF (`costs=False`, `verified=False`), chuyển các caller module sang adapter, chọn ảnh v2 và bảo vệ ghi v2 bằng actor + CAS theo mẫu `package_overrides` (M0.10 chỉ có đặc tả, chưa có module write_guard).
- ĐỎ: 3/3 test provenance trước module mới. XANH run gom: 55/55 (provenance, v2, AST readers, forms/render, golden DB replay) 37.69s. Các sửa sau run (nested lock, malformed, profile trong asset dict, flag fixture) CẦN chạy lại.
- Còn BẮT BUỘC trước nghiệm thu: test matrix luồng thật bấm tay/autopilot/v2/v3/multi/clone/Director; end-to-end cùng revision qua Director/image/video/QC + lineage; API BYĐ tích hợp cloud-C (không sửa `core/shot_intent.py`); kiểm identity_declare/director_byd/context; UI lưu hồ sơ v2 actor/revision; test tools draft/finalize v2; provenance outfit items; fixture OFF full golden; tự rà related areas + parent fresh review; targeted regressions và cả bộ tại main trước gộp.
- `kho_profile.validate_dang(conn, project_id, name, dang)` API tạm đã nhắn root/cloud-C; enum chưa khai → VÀNG, không bịa.
- Không tuyên bố reader coverage hoàn tất: AST hiện kiểm các lệnh gọi API cũ, chưa phủ raw SQL profile và reader không nhận conn.
