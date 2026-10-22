# C-CLONE-INTENT — bản sao "chạy lại Đạo diễn" không mang ý đồ + mốc dựng dự án cũ (cloud-E, 22/10)

Nhánh `cloud/v31-clone-intent`. Cấp 1 sửa lỗi, 0 USD, không đụng `data/` thật, không đổi cờ.

## Lỗi
`core/compare.clone_project(..., with_rows=False)` ("chạy lại Đạo diễn") chỉ bỏ `director_raw`; vẫn chép `director_intent_raw`
(ý đồ Tầng A của phim cũ) và `render_settings` nguyên vẹn (mốc nhạc `music_start`/`music2_start`, popup cuối, chữ card cuối) —
trái quyết định người dùng 13/10 (TODO 🐞 "tập 2 = dự án mới sạch", ý 3 + 5: KHÔNG mang `director_intent_raw`, `render_settings` mốc nhạc + popup).

## Sửa (`core/compare.py`)
- with_rows=False: bỏ thêm `director_intent_raw`.
- with_rows=False: `render_settings` đi qua `core/project_defaults._carried("render_settings", …)` — đúng luật dự án mới: giữ CÁCH DỰNG
  (`RENDER_WAY`: transition, fade, music_volume, beat_pulse, keep_audio, exports; kiểu card `END_CARD_STYLE`), bỏ mốc riêng của phim
  (music_start, music2_start, end_popup, title/subtitle card). Nguồn trống → None (mọi chỗ đọc đều `or "{}"`: delivery.py:37,
  script_parser.py:164, music_intent.py:108, pilot_setup.py:62).
- with_rows=True: không đổi.

## Test (`tests/test_clone_intent.py`, CSDL tạm `kenta_project`)
- Trên code cũ: 1 đỏ (`test_rerun_director_clone_drops_old_intent_and_film_marks`); trên code mới: 3/3 xanh.
- Có test with_rows=True giữ nguyên director_raw, director_intent_raw, render_settings.
- Bộ liên quan (compare, project_defaults, delivery, director_two_pass, v3…): 252 passed.

## Rà caller (quy ước 7 — agent rà, không có lỗi CAO)
| Caller | with_rows | Ảnh hưởng |
|---|---|---|
| dashboard/header.py:910 | người dùng chọn | đúng ý "chạy lại Đạo diễn" |
| dashboard/admin.py, tools/experiments/* | True (mặc định) | không đổi |
| core/director_two_pass.py:659 | — | chỉ đọc intent khi resume + fp_a khớp; intent_all (:541) raw rỗng → lấy story_scenes (được chép) → không gãy |
| tools/pilot_setup.py:51 | False | render_settings: không đổi (tool tự chép đè từ nguồn :61-63). **Ý đồ:** trước đây dự án thử mang `director_intent_raw` của phim gốc (focus/peak/target_s); nay không (tool chỉ ghi lại director_raw :66) → duyệt bản thô (`core/editor_review.py:318`) của dự án thử chỉ còn emotional_intent/beat từ story_scenes. Theo đề bài KHÔNG tự đổi luồng này — **CÂU HỎI phiên chính:** dự án thử (cùng phim, cắt bớt phần) có cần giữ ý đồ gốc không? Nếu có: pilot_setup tự chép `director_intent_raw` (lọc scene ≤ sections) như đang làm với render_settings. |

Lưu ý (agent rà, mức VỪA): bản sao "chạy lại Đạo diễn" cùng kịch bản nên card cuối có thể enabled=True mà không có chữ (kịch bản
không parse lại → `store_end_card` không điền title). Đây đúng quyết định 13/10 (không mang mốc phim cũ); nếu người dùng muốn giữ chữ
card khi chạy lại cùng phim thì đổi riêng phần title/subtitle.

## Rollback
`git revert <commit>` — một file code + một file test, không đổi lược đồ/dữ liệu/cờ.
