# HANDOFF — nhánh claude/fix-d6-image3 (14/10)

## Đã xong
- Gốc "mất mã Image 3" (#30): Image 3 = ảnh KELLY thứ 2 (12.png; Image 2 = 10.png, khác ảnh, KHÔNG thừa). Bản code ghép viết
  "Images 2/3 show KELLY"; sau commit 1271e8a5 (đề bài "mỗi mã viết riêng, không gộp") Claude viết "Images 2 and 3 show KELLY" —
  `_ref_units` chỉ đọc ra Image 2 → `check` chặn nhầm. Bằng chứng: jobs.sent_package 937 (bản D6 duy nhất qua, có cả "Images 2 and 3"
  lẫn "Images 2/3"); #29 (trước 1271e8a5) Claude giữ "Images 2/3". Bản bị từ chối KHÔNG được lưu ở đâu (nay đã lưu).
- Sửa: `_ref_units` đọc danh từ số nhiều "Images 2 and 3 / 2, 3 and 4 / 2-4"; đề bài cho phép nhóm, cấm bỏ số. Số ít "Image 2 and 3" vẫn chặn.
- Việc 5: 1 lượt sửa/job kèm đúng lỗi (estimate trước, tagged → sổ chi), trượt → bản code ghép + diag; bản bị từ chối lưu
  `app_settings chat_prompt_refused:<job>`; cùng đầu vào đã bị từ chối → không gọi lại (nếu check sau này chấp nhận bản đã lưu → dùng, 0 USD).
- Việc 4: `cost.chat_prompt_estimate` = sends × 1 lượt × (1 + 1 lượt sửa); cộng vào estimate_images (ảnh shot), estimate_videos(_by_scene),
  estimate_run, project_budget.remaining, image_button_tag(shot=True), video_button_tag; cờ tắt → 0.
- Ledger stage `chat_prompt` chuyển từ dòng ngân sách claude_other (trần 0,20) sang claude_director.
- Test: tests/test_chat_prompt_image3.py (fixture thật tests/fixtures/d6_p30_job93{6,7}_*.txt) — đỏ 8 → xanh; bộ liên quan 271 qua.

## Dở / bước kế
- Chưa chạy thật (0 USD). Lần chạy D6 kế: đọc `chat_prompt_refused:<job>` nếu còn bị chặn — giờ có bản gốc để tìm gốc.
- #29 video "mất Shot 1, Shot 2" chưa có bản gốc → chờ dữ liệu lần sau (lượt sửa sẽ xử lý nếu lặp lại).
- Chưa merge/push; TODO.md chưa sửa (theo đề bài).
