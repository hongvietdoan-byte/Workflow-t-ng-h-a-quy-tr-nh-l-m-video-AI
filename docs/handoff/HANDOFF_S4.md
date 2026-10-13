# HANDOFF S4 — Rà soát + cổng duyệt ảnh + QC video (13/10)

Nhánh `claude/sua-s4-ra-soat-duyet` (chưa push, chưa gộp main).

## Đã xong
- **C4** sửa motion prompt → Tổ rà soát rà lại: trigger `trg_change_motion` (core/db.py, kind `motion`, mọi đường ghi motion_prompts);
  `core/change_review.py` gộp lần sửa motion với lần sửa shot theo TỪNG nguồn (một lời gọi/shot), `WATCH["motion_prompt"]`, cờ
  `change_review_motion` (TẮT mặc định — tắt: sự kiện motion bị đánh `skipped`, không giữ gen, 0 lời gọi). Claude thấy khớp → mục Claude
  cũ của shot tự đóng (cơ chế cũ). Chèn shot: dời số trong motion prompt cũng `skipped` (core/llm_io.py). Khung 🔎 Rà soát hiện ở tab
  Motion (Bước 3) với khóa nút `cr3_*` (`change_review_ui.render(key=…)`).
- **C9** bản cao nâng từ nháp NGƯỜI đã duyệt: `change_review.blocking(since=, notes=)` chỉ giữ mục đỏ mới hơn lúc duyệt nháp và thuộc
  khâu video/motion/khung_cuoi; còn lại ghi VÀNG `change_review_upgrade` (core/runner.py `_draft_approved_at`). Sửa lỗi rõ, không cờ.
- **Lỗi 6** ô 🏁 end_state Bước 3: hiện khi cờ `end_state_fresh` bật (cả bật qua 🧪 tệp cài đặt), cả shot không có số shot mà có
  end_state; nhãn khung gập motion nhắc "(cả 🏁 trạng thái cuối)".
- **V7** cổng ảnh → video `core/video_gate.py` (cờ `video_gate`, TẮT): runner GIỮ job (WAIT_REASONS + diag `video_gate_hold`, không hỏng)
  khi ảnh khung đầu có render 3D mà kiểm nền `plate_layout` ĐỎ (chưa có kết quả → đo ngay 0 USD, ghi diag) và chưa ai "Bỏ qua" có lý
  do (bảng mới `video_gate_skips`); hoặc nhóm liền mạch (story_scene + sequence > 0) còn shot chưa duyệt ảnh / đang vẽ lại ảnh. Bản cao
  nâng từ nháp đã duyệt không qua cổng. Bước 4: khung `dashboard/video_gate_ui.py` (ô lý do + nút Bỏ qua kiểm nền).
- **V11** QC video `core/claude_tasks.py` (cờ `qc_framing_cap`, TẮT): thêm khung CUỐI clip cạnh ảnh đầu, render 3D, khung cuối dự kiến
  + khối "Kiểm bố cục"; framing_guard đo thấy đổi bố cục → code hạ trần motion_match/artifacts về 0,5 (diag `qc_framing_cap`).
- CSDL: bảng `video_gate_skips` + trigger `trg_change_motion` (CREATE IF NOT EXISTS, chạy lại an toàn; test CSDL cũ ở test_video_gate).
- areas.json: khai core/video_gate.py, dashboard/video_gate_ui.py, tests/test_video_gate.py, tests/test_qc_video.py, 3 cờ mới (không tăng version).

## Test
Đỏ (mã cũ) → xanh: test_change_review (3 ca C4), test_video_gate (V7 6 ca, C9 2 ca, migration), test_qc_video (3 ca V11),
test_ui_storyboard::test_motion_tab_shows_end_state_box_and_review_frame_when_flags_on_in_settings. Bộ liên quan 27 tệp: 513 passed.

## Đang dở / bước kế
- V7 mục (2) checklist trạng thái nhân vật theo nhóm liền mạch (bóng mờ/giày/đạo cụ) do QC ảnh chấm — chưa làm (cần tiêu chí QC + tốn Claude).
- Chạy cả bộ test ở bước gộp; bật thử 3 cờ mới trên dự án mới rồi mới đặt verified.
- Đụng runner.py chỉ ở vòng gửi (sau kiểm change_review) + VideoRunner thêm 2 hàm mới đặt đầu lớp — không đụng `_wait`/`_end_frame`/`_skill_reserve`.
  Đọc (không sửa) `end_frames.current` và `framing_guard` kết quả trong claude_tasks.

## Vòng sửa sau rà (13/10, RA_S3_S4 mục S4)
- **R9** `change_review.claude_review`: rà lại một shot chỉ tự đóng mục Claude thuộc khâu mà các khóa VỪA ĐỔI chạm tới (`WATCH`) — sửa
  motion không đóng mục `anh`/`nen`/`thoai` cũ (áp cả kind `scene`). Test `test_change_review::test_motion_edit_keeps_open_image_finding`.
- **R10** hàm module `runner.draft_approved_at(conn, job)` (VideoRunner dùng lại); `autopilot._review_wait` lặp theo JOB với `since` → bản
  cao nâng từ nháp người duyệt không bị dừng "CHỜ người" vì mục đỏ cũ. Test `test_video_gate::test_autopilot_review_wait_lets_upgrade_from_approved_draft`.
- **R11** `autopilot._gate_wait` (sau `_review_wait`): cổng V7 giữ MỌI clip đang chờ + không clip nào chạy → `_Wait("video_gate", lý do
  + "xử lý ở Bước 4 rồi Tiếp tục")`; một clip gửi được thì không dừng. `video_gate.group_missing`: take mới `succeeded`/`pending_review` =
  "có ảnh mới chờ duyệt" (chỉ `queued/running/retryable` là "đang vẽ lại"). Nút **Bỏ qua chờ nhóm** (bắt buộc lý do) ở khung 🚧 Bước 4:
  `video_gate.skip(..., group=True)` ghi chung bảng `video_gate_skips`, lý do tiền tố `[nhóm] ` (không đổi lược đồ CSDL); `skipped(group=)`
  tách hai loại bỏ qua; `group_waits()` cho màn. Test `test_autopilot_waits_with_gate_reason`, `test_unreviewed_newer_take_is_not_called_redrawing`.
- **R13** `before_run._review_items` không đếm sự kiện `motion` đang chờ khi cờ `change_review_motion` tắt (lọc khi đếm; trigger SQL không
  đọc được cờ). Test `test_change_review::test_before_run_does_not_count_motion_when_flag_off`.
- **R14 — QUYẾT MẶC ĐỊNH, CHỜ NGƯỜI DÙNG**: bản viết lại motion prompt TỰ ĐỘNG của Đạo diễn (`prompt_rewrite.save_rewrite`, kind video)
  KHÔNG qua Tổ rà soát motion: sự kiện vừa sinh đánh `skipped` (không giữ chính lần gen lại, 0 lời gọi Claude). Người sửa tay / "↩ Dùng
  lại prompt cũ" vẫn rà. Người dùng muốn rà cả bản viết lại tự động → bỏ khối R14 trong `save_rewrite`. Test `test_director_rewrite_event_handling`.
- **R15** `cap_for_framing` không sửa `criteria` nữa. framing_guard bật (đường thật — số đo bố cục chỉ có khi cờ này bật, và
  `_framing_hold` đã giữ clip) → `qc_results` + `note_case` giữ điểm GỐC Claude, trần chỉ ghi diag `qc_framing_cap` + `out["capped"]`.
  framing_guard tắt mà vẫn có số đo (chỉ gặp trong test) → điểm sau trần vào quyết định như V11 (giữ test cũ). Bỏ chữ "tin được" (ghi
  "số đo mới chưa kiểm chứng thật"). Khung cuối clip = khung N/N đã gửi, chỉ gắn nhãn "KHUNG CUỐI clip" (không gửi trùng ảnh; chưa trích
  khung cuối thật bằng clip_measure — khung N/N cách cuối ≤ 0,5 s). Test `test_qc_video::test_cap_keeps_original_scores_for_trust`.
- **R12** chưa làm (để bước gộp S3+S4).
- Bộ liên quan (related_areas, 93 tệp trừ test chậm): 1468 passed, 4 skipped.
