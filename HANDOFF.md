# HANDOFF — nhánh `s14-c1a-kho` (S14.4 phần C1a: dữ liệu Kho tài nguyên), 04/10

## Đã xong
- `core/assets.py`
  - `merge`: đọc mọi dòng `asset_images` bằng SQL (approved/pending/redundant/removed/mất file); đếm chỗ bằng `_count` (như `add_image`,
    không tính thùng rác); đích không đủ chỗ → `AssetError` "còn N chỗ" trước khi đổi gì; file mất → chỉ `UPDATE` dòng (đường dẫn trỏ
    vào thư mục đích để ↻ Tải lại ghi đúng chỗ); hồ sơ chuẩn: chép nguyên JSON (kèm `history`) khi đích chưa có; từ chối khi hai bên
    khác nhau (trừ đích đã duyệt + nguồn là nháp → giữ đích); chỉ `delete()` nguồn khi nguồn hết dòng ảnh; vẫn trả `int`.
  - `unlink_missing(conn, only_unreloadable=True)`: chỉ gỡ dòng `can_reload=False`; sao lưu JSON vào `<Kho>/_backup/unlink_missing_<ngày giờ>.json`.
  - Thùng rác Kho: `trash_image`, `restore_image` (trả lại status cũ; từ chối khi file mất / mục đủ 6 ảnh), `removed_images`,
    `purge_removed(days)` (xóa file + dòng quá `trash_days()` = `TRASH_DAYS`, mặc định 30), `trash_days()`. `remove_image` KHÔNG đổi.
  - Ảnh `removed` bị loại khỏi: `missing_files(_detail)`, đếm chỗ `add_image`, `outfit_images`, kiểm trùng khi tải lên (`add_files`, tải ảnh ở màn kịch bản).
- `core/db.py`: cột mới `asset_images.removed_at`, `removed_from` (V2_COLUMNS).
- `core/llm_runner.py` (Director "có ảnh nhưng không đọc được"), `core/meshy.py` (`_images`), `tools/library_audit.py`: bỏ qua ảnh `removed`.
- `dashboard/admin.py`: "Xóa ảnh" (thẻ mục), 🗑 từng ảnh chờ duyệt → `confirm_all` + `trash_image`; bỏ hàng loạt → `trash_image`;
  danh sách ảnh đã xóa + nút "↩ Khôi phục" (`lib_img_restore_<id>`) trong thẻ mục; "Gộp" → `confirm_all`; "Gỡ liên kết" hàng loạt →
  `confirm_all`, chỉ dòng không tải lại được; "↻ Tải lại" bắt `AssetError`/`OSError` → `st.error` tiếng Việt.
- `dashboard/app.py`: `periodic("purge_asset_trash", purge_removed, every=3600)`.
- Test: `tests/test_assets.py` (MergeKeepsEveryPictureTests, LibraryTrashTests, LibraryKhoUiTests — ui_v2 bật), sửa `tests/test_b3_b4_fixes_2026_10_01.py::B5Tests`.

## Dở / chưa làm
- Chưa chạy thật trên Dashboard với Kho thật (chỉ AppTest + CSDL tạm).
- Đồng bộ thư mục: ảnh trong thùng rác vẫn giữ `src_path` → sync không nhập lại khi còn trong thùng; sau 30 ngày dọn thì sync nhập lại (chờ duyệt).

## Bước kế
- Người điều phối: rà, gộp main, chạy cả bộ test, cập nhật TODO.
