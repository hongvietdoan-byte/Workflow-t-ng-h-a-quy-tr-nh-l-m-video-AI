# HANDOFF — S14.42 duyệt Kho 3 tầng (05/10/2026)

- Trạng thái ảnh: `pending` → `claude_ok` (dùng được, hiện dấu "Claude duyệt") → `approved` (= người dùng xác nhận). Không cần migration cột; chỉ thêm bảng nhẹ `kho_review_log` (CREATE IF NOT EXISTS trong core/db.py). Âm thanh không có cổng duyệt: trạng thái = dòng cuối của `kho_review_log`; bài `reject` không được gợi ý nhạc nền.
- Code: core/kho_review.py (claude_approve, confirm, revoke, reject, rejected, claude_only_images/sounds, delivery_warnings); assets.USABLE/USABLE_SQL; asset_checklist, asset_vision, meshy, scene_establish, sound_lib, delivery (cảnh báo, không chặn); UI: dashboard/admin.py `claude_review_box` (lưới + Thu hồi/Xác nhận), dashboard/steps/step1_checklist.py (dấu + nút).
- Test: tests/test_kho_review.py (12 ca). Chưa sửa: tools/library_tidy.py, tools/experiments/* vẫn đọc `status='approved'` (cố ý, công cụ rà tay).
- Áp dụng thật máy chính: sao lưu data/backup/manifest.before_s14_42_2026-10-05.sqlite; 23 ảnh + 14 âm thanh claude_ok; 10 ảnh + 3 âm thanh bị loại → docs/KHO_TAI_NGUYEN_LOI_2026-10-05.md.
- Khôi phục: 33 file ảnh mục 396–413 mất trên đĩa → đã chép lại từ src_path (sha256 khớp).
- Việc tiếp: người dùng mở Kho → "Claude duyệt sơ bộ" để xem mẫu/xác nhận; gom thêm lỗi rồi làm lại các ảnh/âm thanh bị loại; chưa push, chưa sửa TODO.md.
