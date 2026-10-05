# HANDOFF — S14.20 Bộ não prompt Đợt 2 (knowledge) — nhánh `s14-20-knowledge-murch`

## Đã xong
- **2a trục Murch**: `knowledge/craft/uu_tien_cam_xuc.md` (giữ nguyên 2 câu đã chốt; thang 6 mức; gợi ý có lý do, không trần số). Nạp cho
  Director (`build_director_bundle`, `build_intent_bundle`) và motion (`build_motion_bundle`) qua `knowledge.murch_blocks(group)`.
  Bổ sung prompt motion ở file riêng `prompts/03_video_motion_murch.md` (giữ trước, xếp theo trục Murch, check_flags bắt đầu bằng tag rủi ro).
  Người xem lần đầu: `prompts/22_first_viewer_murch.md` thêm `cam_xuc` 1–5; `story_check._check` kiểm khi có; `lines()` hiện "cảm xúc N/5".
- **2b tag rủi ro**: `core/lessons.py` `RISK_TAGS` (6 trục + identity/physics/lipsync/audio, kèm cách chữa), `active_tags()`; cờ bật → bỏ
  tag `motion`, lỗi không khớp tag nào vào nhóm `unclassified` / "Chưa phân loại" (không bao giờ `ready`) + `diag` warn mã
  `lesson_unclassified`. Bảng ở tab Bài học (`dashboard/admin.py`) tự hiện dòng này (không sửa UI). Chưa hạ `MIN_EVENTS`/`MIN_PROJECTS`.
- **2c** `knowledge/i2v_motion_discipline.md` đúng 3 mục (bảng 6 rủi ro = từ điển tag, preservation-first, giảm chuyển động P0→P5; ghi rõ heuristic).
- **2d** `knowledge/sound_design_method.md` 4 mục (dẫn→đập→đuôi, 16 ý đồ → chất âm không tên file, khoảng lặng, chống lạm dụng trích nhac_nen.md), nhóm director.
- **Cờ mới** (`core/features.py`, `verified=False`, TẮT): `murch_knowledge` (2a/2c/2d + addendum 03/22), `risk_tags` (2b). Khai ở `devsys/areas.json`
  (khu knowledge; `prompts/22_*` vào step2), không tăng `version`.
- **Cờ tắt → prompt y hệt**: test `test_bundles_identical_with_flag_off`, `test_first_viewer_prompt_identical_with_flag_off`; và đo hash
  trước/sau code (director/intent/motion/first-viewer, film_crew 0 và 1): 8/8 khớp.
- Tổng ký tự nhóm motion khi bật cờ (+ film_crew): 85 662 < `MAX_USER_CHARS` 150 000 (test `test_motion_group_stays_under_the_char_limit`).
  Lưu ý: nhóm director (film_crew bật + murch) 141 240 ký tự gửi / 180 517 thô — đã sát 150 000, chưa có test chặn cho nhóm director.

## Cố ý không làm / lệch kế hoạch
- **Không sửa `knowledge/editor/editing.md`** (kế hoạch: thêm tham chiếu sang file mới) — file này được gửi ở khâu Editor, sửa là đổi prompt
  khi cờ tắt. File mới tham chiếu ngược về E1 thay vào đó.
- **Không sửa trực tiếp `prompts/03` / `prompts/22`** — phần thêm nằm ở file `_murch.md` riêng, chỉ ghép khi cờ bật (evalset `motion_bundle` đọc 03 gốc).
- DP (`dp_common`, Tầng B) không đọc trục Murch / âm thanh — chỉ Đạo diễn (Tầng A + một lượt). Cân nhắc khi thử thật.
- Tài liệu I2V gốc người dùng đưa không có trong repo: thứ tự P0→P5 viết lại theo bảng rủi ro + luật gen lại của dự án — cần người dùng đối chiếu.
- Từ khóa `RISK_TAGS` là dự đoán, chưa đo trên lỗi thật (bảng lessons 0 bài học).

## Việc mở (cần Claude thật / người dùng — không chạy, 0 USD)
1. Nghiệm thu Đợt 2: bật `murch_knowledge`, chạy Bước 3 (motion) trên một dự án cũ, so prompt mới vs cũ — kỳ vọng nêu rõ cái giữ nguyên,
   số chuyển động giảm, `check_flags` bắt đầu bằng tên tag rủi ro. Tốn tiền Claude → cần người dùng duyệt.
2. `py -m core.evalset score <outputs.json>` trước/sau: lệnh 0 USD nhưng chỉ chấm file đầu ra đã có — cần đầu ra Claude mới chạy với cờ
   bật mới so được (bundle của evalset không đọc knowledge mới). Chưa chạy.
3. Bật `risk_tags` trên DB thật, xem mục "Chưa phân loại" bao nhiêu lỗi → chỉnh từ khóa; Đợt 5 quyết ngưỡng.

## Bước kế
- Phiên chính: rà + gộp nhánh vào main (bỏ HANDOFF.md khi gộp), cập nhật TODO (S14.20), push.
