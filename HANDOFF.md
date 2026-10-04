# HANDOFF — S14.19 Bộ não prompt, Đợt 0 + Đợt 1 (nhánh `s14-19-feedback-baseline`)

Kế hoạch: `docs/KE_HOACH_BO_NAO_PROMPT_TU_HOC_2026-10-04.md` (Đợt 0, Đợt 1). 0 USD, không gọi API.

## Đã làm
- **Đợt 0** — `core/db.py` SCHEMA: 3 bảng `lesson_reviews`, `effectiveness_snapshots`, `user_feedback` (đúng SQL kế hoạch, `CREATE TABLE IF NOT EXISTS`; `schema_stamp` tự đổi nên CSDL cũ được migrate một lần).
  - `core/feedback.py`: `add` (ValueError khi loại/khâu/điểm sai hoặc góp ý trống — không im lặng), `list`, `summary`, `satisfaction` (0..1), `detach`.
  - Xóa cảnh / chia shot lại / xóa dự án: góp ý được giữ, bỏ liên kết (FK); mốc của dự án bị xóa thì xóa theo (`core/pipeline.py`, `core/shots.py`).
  - Bước 5 (cả UI v2 lẫn cổ điển): khối "Bản này dùng được chứ?" 👍/🤔/👎 + "Chỗ nào chưa ổn?" + chọn khâu, chỉ hiện khi đã có bản giao (`step5.delivery_feedback`, key `fb_verdict_/fb_text_/fb_stage_/fb_send_{pid}`).
  - Thanh trên: 💬 "Góp ý màn này" (v2: mục gập trong "⋯ Thêm"; cổ điển: popover cạnh ⚠ Rủi ro), kind='screen', stage mặc định 'ui', screen = màn đang mở.
  - `compare.save_scores` ghi `user_feedback` (kind 'delivery', screen 'compare', text = JSON điểm); `get_scores` đọc bản mới, không có thì đọc `app_settings['eval:<pid>']` cũ.
- **Đợt 1** — `core/effectiveness.py`: `snapshot` (phút làm tròn, chống bấm 2 lần cả khi project_id NULL), `history`, `trend`, `delta` (chỉ số + cờ bật/tắt + bài học thêm/bớt + knowledge đổi), `report_all` (toàn hệ = gộp các dự án đã xong có trọng số), `finished_projects` (có output 'final'), `flags_on`, `knowledge_fp`.
  - Tự chụp khi xuất bản xong (`_deliver_button` chỉ thêm 1 dòng `snapshot_after_delivery`; lỗi thì cảnh báo, không làm hỏng việc xuất bản).
  - Nút "📌 Lưu mốc" + biểu đồ + "Giữa 2 mốc gần nhất: …" trong `effectiveness_panel` (`dashboard/admin.py`). Mở trang KHÔNG chụp.
- `tools/effectiveness_baseline.py [--db PATH] [--data DIR] [--project N] [--env FILE] [--yes]` — không `--yes` chỉ in; `--yes` ghi 1 mốc toàn hệ + 1 mốc mỗi dự án đã xong. CSDL không tồn tại thì báo, không tạo mới.

## Sửa sau phiên rà độc lập (05/10)
1. Lệnh baseline nạp `dashboard.env` (`--env`, mặc định gốc repo) → đọc đúng cờ Dashboard đang bật.
2. `knowledge_fp` băm MỌI file trong `knowledge.GROUPS[g]` (prompt 01/03, `ff_gameplay_visual.md`, `eval/golden.json`…), sách vai film_crew, thư mục `knowledge/genre/`, tài liệu người dùng đang bật, bản chắt lọc.
3. "Đã xong" tính cả `data/projects/<id>/output/FINAL_VIDEO.mp4` kiểu cũ (`--data`); `--project N` (lặp được) thêm dự án; mốc toàn hệ gộp đúng danh sách đó.
4. ↺ Làm lại (`step1.reset_unworked_scenes`) và `tools/pilot_setup.py` gỡ liên kết góp ý trước khi xóa cảnh.
5. Khối "Bản này dùng được chứ?" mở cho người "Chỉ xem" (mọi key `fb_*`), `tests/test_access_ui.py` cập nhật.
6. ⚖ Lưu điểm lại cùng dự án → cập nhật dòng cũ (`feedback.upsert`), không đếm lặp.

## Người điều phối làm sau khi gộp
1. Ở `D:\AI-Video-Pipeline`: `py tools/effectiveness_baseline.py --db data\manifest.sqlite --data data\projects` (xem trước) rồi thêm `--yes` — đây là **mốc nền** của kế hoạch.
2. Nghiệm thu Đợt 0 trên Dashboard thật: gửi 1 góp ý Bước 5 + 1 góp ý màn → `SELECT * FROM user_feedback`.
3. Cập nhật TODO.md (phiên con không sửa).

## Rủi ro / ghi chú
- Kế hoạch ghi "bấm 📌 hai lần → 2 dòng"; theo yêu cầu điều phối, 2 lần **cùng phút** → 1 dòng (khác phút → 2 dòng).
- Dự án "đã xong" = có dòng `outputs` kind 'final' hoặc FINAL_VIDEO.mp4 kiểu cũ.
- Điểm ⚖ So sánh cũng là kind 'delivery' nên được tính vào "hài lòng" của dự án đó.
- Nút 💬 và khối góp ý Bước 5 mở cho cả người "Chỉ xem" (góp ý không đổi gì trong dự án).
