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

## Vòng sửa `claude/tap2-a-fix` (14/10, sau rà)
- "So sánh tổng" Bước 4 (chuyên gia): mới `model_router.compare_total()` = tổng `plan` + `quality_tier.run_estimate` (nháp 480p + bản
  cao 1080p) khi cờ bật; None nếu có hàng chưa biết giá; step4 dùng hàm này.
- Prompt 01 / 17 / 20: nhãn easy/complex chỉ để thông tin/thống kê, mọi shot nháp 480p trước; bỏ các vế "gen thẳng".
- Test mới lớp chặn 896/901: job gen thẳng đã vào hàng, người đặt `draft_first` → lúc gửi `draft=True`, bậc ghi lại 'draft'
  (kiểm: tắt `draft_resolution_sent` thì test đỏ).
- Mục 4 (nháp 480p vào bản giao?): KHÔNG thủng với dự án có khung (v2+): `final_cut.require_delivery_resolution` đo clip gốc ở
  render / deliver / export_layer / editor_apply / autopilot (autopilot → ERROR có ghi chú "nâng 1080p", không lặp). Thêm test
  `DraftsNeverDelivered`. Lỗ nhỏ còn: dự án trước v2 (không aspect) mà clip đầu 480p → khung đo < 1080 → bỏ qua kiểm; thử vá thì vỡ
  2 test c5_post_fx_delivery (clip mẫu 128×72, dự án không aspect) → chưa vá, không ảnh hưởng tập 2 (dự án mới luôn có aspect).

## Dở / việc mở
- Autopilot: mọi shot giờ là nháp → chạy tự động dừng chờ người duyệt nháp ở MỌI shot (C2, `_drafts_waiting`) — đúng quyết định nhưng
  nhiều cổng người hơn; chưa có tự gửi bản cao sau duyệt nháp hàng loạt (nút gom bản cao có sẵn).
- Kling vẫn chọn sẵn (không phải đường lùi) ở: dự án Kling multi-shot, dự án cũ chưa chọn ưu tiên (legacy), cờ closeup_start_frame
  (shot cận mặt), shot đã bị Seedance từ chối (video_route='kling') — giữ vì là chế độ / cờ riêng hoặc chính là đường lùi.
- Chưa kiểm thật trên Dashboard (0 USD, không gọi API).

## Bước kế
- Rà + gộp vào main, chạy cả bộ test ở bước gộp; mở Dashboard dự án #28 xem shot lẻ (S05) hiện "Đề xuất: nháp 480p → 1080p".
