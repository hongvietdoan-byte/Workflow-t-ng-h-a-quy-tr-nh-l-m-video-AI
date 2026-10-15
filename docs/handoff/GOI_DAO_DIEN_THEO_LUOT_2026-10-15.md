# Chia gói Đạo diễn theo lượt (người dùng DUYỆT 15/10, làm ngay sau Đạo diễn #31)

## Vì sao
Lượt Đạo diễn (Tầng A, `director_two_pass`) #31 chậm và tốn gấp đôi các dự án trước (sổ `llm_calls`, Sonnet 5):

| Dự án | vào | ra | thời gian TB |
|---|---|---|---|
| #22 | ~32k | ~7,7k | ~1,5 phút |
| #24 | ~25k | ~11k | ~2,2 phút |
| #27 | ~14k | ~11k | ~2,2 phút |
| #30 | ~30k | ~7,5k | ~1,5 phút |
| **#31** | **~66k** | **~22–25k** | **~4,6 phút** |

Gốc: #31 là đợt thử cờ (bật thêm 38 cờ) → gói Tầng A 104.031 ký tự. Đo gói (dry-run 0 USD, `tools/replay_payload.py` + script dry_p31):
- `## Tầng 3 — Kỹ năng` (Đ1–Đ12, knowledge/roles/director.md…) **26.916 ký tự (26 %)** — Tầng A chỉ chốt ý đồ / cảm xúc / target_s / câu giữ / Bible; Đ3 kể bằng hình, Đ4 diễn xuất (`performance`), Đ7 luật sản xuất, Đ8 bối cảnh 3D, Đ12 kỹ thuật ClipAI là việc Quay phim (gói DP `dp_common` ĐÃ có Tầng 3).
- `# Bối cảnh có mô hình 3D` 6.847 — Tầng A cần tên + mô tả ngắn; tọa độ/chỗ đứng/hướng cho Quay phim + Đặt máy 3D.
- `# Tài nguyên có sẵn` 7.074 — giữ, bỏ mô tả dài thứ cảnh không dùng (nếu đo được an toàn).
- `llm_runner.STAGE_SETTINGS["director"]` = effort medium, max_tokens 64000 (dùng chung một lượt cũ + Tầng A).

## Việc (một phiên con, rà KỸ vì đổi gói gửi model trả tiền)
1. **Chia gói theo lượt**: mỗi mục kiến thức/khối gói khai dùng cho `intent` (Tầng A), `dp` (Tầng B) hay cả hai — một nguồn khai (không cắt tay từng file). Tầng A bỏ Đ3/Đ4/Đ7/Đ8/Đ12 + khối tọa độ 3D (giữ tên + mô tả ngắn bối cảnh). Đường một-lượt cũ (`build_director_bundle`) giữ nguyên.
2. **Trần suy nghĩ Tầng A riêng**: đo phần ra là suy nghĩ vs JSON (#31: ~22k ra cho Tầng A); đặt khâu/thiết lập riêng cho Tầng A nếu cần (memory reference_stage_max_tokens_vs_caps: khâu mới cần max_tokens riêng trong STAGE_SETTINGS), không làm cụt JSON.
3. **Trần cỡ gói bằng test + before_run**: mỗi lượt có trần ký tự; vượt → test đỏ + "Trước khi chạy" báo VÀNG có số (không lặng lẽ phình khi bật cờ).
4. **Kiểm trên gói thật #31 (0 USD)**: dựng gói Tầng A trước/sau từ CSDL thật (`tools/replay_payload.py`), liệt kê mục bị bỏ, xác nhận không mục nào Tầng A dùng (trường bắt buộc của validate_intent: emotional_intent, target_s, focus, peak, beat, sound, dp_notes, editor_notes, dialogue + delivery, Bible/lock). Ước tính `director_two_pass.estimate` phải giảm tương ứng.
5. Mục tiêu: Tầng A ~104k → ~60–65k ký tự; thời gian ~4,6 → ~2–2,5 phút; tiền mỗi lần Đạo diễn −30–40 %. Đo thật ở lần chạy Đạo diễn kế tiếp (ghi vào bảng trên).

Luật: docs/CHUAN_XAY_DUNG.md; quy ước 7 (agent rà khâu liên quan); cả bộ test trước khi gộp; không gọi API tốn tiền.

## Liên quan đã sửa 15/10 (main bfe0e72c)
Tầng A #31 lần 1 hỏng 2 lượt (≈ 0,76 USD): kịch bản "LỜI DẪN" vs Đạo diễn "NGƯỜI DẪN CHUYỆN" → `_unify_narrator` + `_check_kept`/`check_scene` coi là một người dẫn. **Việc mở (đề xuất, chưa duyệt):** lưu câu trả lời bị bộ kiểm từ chối để sửa bộ kiểm xong kiểm lại 0 USD thay vì gọi lại trả tiền.

## Đo thật lần chạy #31 thành công (15/10 14:29 → 14:50, **≈ 21 phút**)
- Tầng A: 1 lượt 66k vào / 22,5k ra, 242 s (đạt ngay, sau bản sửa người dẫn).
- Tầng B (Quay phim) 8 cảnh: mỗi lượt ~2k vào + 94k đọc cache / 11–23k ra, **128–248 s mỗi lượt, KHÔNG thật sự song song** (sổ ghi xong lần lượt cách 0,5–2 phút; 1 lượt viết cache 94k) + 1 lần hỏi lại cảnh 8 (image_prompt rỗng) + 2 lượt BYĐ. → **Thêm việc 6:** đo vì sao Tầng B tuần tự (ThreadPoolExecutor số luồng? khóa lượt `runner._turn`? giới hạn tốc độ API?) — 8 lượt song song thật thì Tầng B ≈ 4 phút thay vì ~16.
- Tiền lần này ≈ 2,42 USD (Tầng A 0,36 + Tầng B ≈ 2,0 + BYĐ 0,06); cộng lần hỏng 0,76 → #31 Đạo diễn ≈ 3,18 USD (ước 3,39).
- Phần ra Tầng B 11–23k / cảnh cho 2–5 shot → nhiều suy nghĩ; cân nhắc trần riêng cho Tầng B như việc 2.
