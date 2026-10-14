# HANDOFF — nhánh `claude/tap2-a-draft-seedance25`

Quyết định người dùng 13/10: video hết Seedance 2.5, mọi shot nháp 480p → duyệt → bản cao 1080p (bỏ E1 "shot dễ gen thẳng").

## Xong
- `core/quality_tier.py`: `path()` — cờ `two_tier_quality` bật thì tự động LUÔN `draft_first` (nhãn Đạo diễn không quyết đường nữa);
  ghi đè `motion_prompts.quality_path` vẫn thắng; mới `on_direct_route()` — job video mới nhất là gen thẳng (bậc direct / NULL) đang
  chờ / chạy / chờ duyệt / đã duyệt thì giữ tuyến `direct` (không đổi giữa chừng, clip 720p đã duyệt không bị bắt gen lại). Bị loại → về nháp.
  Cờ tắt: logic cũ giữ nguyên. Lý do / dòng ước tính (`e1_estimate.line`) không còn nói "2.0 720p".
- `core/model_router.py`: `recommend()` cờ bật → mọi ưu tiên + mọi nhánh (kể cả FF_INGAME, ≥3 nhân vật, đối thoại nhiều người) =
  `seedance-2.5`; Kling chỉ còn là đường lùi tự động (`VideoRunner._on_refused` đặt override Kling khi Seedance từ chối người thật /
  bản quyền). Cờ tắt: thang cũ. `plan(priority=…)` (dòng so sánh ưu tiên) áp `e1_choice` khi cờ bật → giá nháp 2.5 480p.
  Ô Chất lượng Seedance 2.5: 480p = "nháp → duyệt → nâng 1080p" (set_resolution ghi `draft_first`), 720p = gen thẳng.
- Dashboard: `quality_ui.TWO_TIER_FULL`, nhãn độ khó "chỉ để tham khảo", `model_line` (gen thẳng 480p ghi "chỉ xem nháp"), help ô
  Chất lượng ở `step4.py`; nhãn cờ ở `core/features.py`.
- Test: mới `tests/test_tap2_all_draft_seedance25.py` (đỏ 7 → xanh); sửa kỳ vọng E1 cũ trong test_cost_route_e1, test_quality_tier,
  test_regen_draft_route, test_model_line_f4, test_two_tier_labels_estimate. 27 file test liên quan: 444 passed, 2 skipped.
- `devsys/areas.json`: thêm test mới vào khu vực step4 (không tăng version).

## Dở / việc mở
- Autopilot: mọi shot giờ là nháp → chạy tự động dừng chờ người duyệt nháp ở MỌI shot (C2, `_drafts_waiting`) — đúng quyết định nhưng
  nhiều cổng người hơn; chưa có tự gửi bản cao sau duyệt nháp hàng loạt (nút gom bản cao có sẵn).
- Prompt Đạo diễn (`prompts/01_…`, `17_director_shots.md`, `20_dp_scene_shots.md`) còn câu "easy → gen thẳng bản cao" — không còn đúng,
  chưa sửa (đổi prompt cần rà riêng).
- Kling vẫn chọn sẵn (không phải đường lùi) ở: dự án Kling multi-shot, dự án cũ chưa chọn ưu tiên (legacy), cờ closeup_start_frame
  (shot cận mặt), shot đã bị Seedance từ chối (video_route='kling') — giữ vì là chế độ / cờ riêng hoặc chính là đường lùi.
- Chưa kiểm thật trên Dashboard (0 USD, không gọi API).

## Bước kế
- Rà + gộp vào main, chạy cả bộ test ở bước gộp; mở Dashboard dự án #28 xem shot lẻ (S05) hiện "Đề xuất: nháp 480p → 1080p".
