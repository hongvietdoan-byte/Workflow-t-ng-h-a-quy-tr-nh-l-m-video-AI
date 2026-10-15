# Rà quyết định bị ghi lệch + lỗi lặp qua dự án — 15/10/2026

Phiên rà chỉ đọc (0 USD). Kích hoạt: quyết định 13/10 "shot đơn giản gen thẳng 2.5 720p + phóng ffmpeg 1080, shot khó nháp 480 → 1080"
bị ghi thành "MỌI shot nháp 480 → 1080" và lan sang memory, TODO, code (`core/quality_tier.py` e1_choice). Người dùng: "đã làm liên tục
3–4 dự án thật nhưng vẫn chưa thực sự cải thiện từ những lỗi sai".

Phiên chính đã kiểm lại trên máy chính: 7 cờ ở A1 đều TẮT (`features.on`); bảng `mistakes` có 0 dòng cho #24 và #27. Mục "Mê Cung #31
chưa ghi từ chối" của phiên rà là SAI (`project_assets_declined` #31 có 3 dòng) → đã bỏ.

## A) Quyết định ghi lệch / chưa vào code / memory mâu thuẫn

| # | Quyết định | Kết luận | Bằng chứng |
|---|---|---|---|
| A1 | 13/10: cờ sửa lỗi tập 1 #27 bật để kiểm thật ở tập 2 | **SAI** | 7 cờ `video_gate`, `qc_framing_cap`, `plate_view_sentence`, `character_state_lock`, `ref_rule_early`, `motion_consistency_lint`, `group_keep_approved` (core/features.py:489,496,661,668,674,680,686) đều TẮT, chưa từng có trong `data/feature_settings.json` lẫn 13 bản sao lưu 09–14/10 |
| A2 | Chạy thật không lỗi → `verified: True` | **CHƯA LÀM** | `ambient_motion`, `video_pregen`, `change_review_frames`, `qc_observe_enum`, `stage_camera`, `p24_lessons`, `project_prop_lock`, `two_tier_quality` vẫn `verified: False`; chỉ BẬT nhờ tệp cài đặt máy chính |
| A3 | Duyệt nháp qua chat | **SAI (lan từ vụ 720p)** | memory + nhãn cờ `two_tier_quality` (features.py:700) ghi "MỌI shot nháp"; autopilot.py:1036 |
| A4 | Không bao giờ phóng 480p | code ĐÚNG, memory SAI | Chặn ở `final_cut.require_delivery_resolution` (final_cut.py:135–149); memory còn ghi "CHƯA chặn" + "Seedance 2.0 720p" |
| A5 | decision_kld10 | SAI (cũ) | còn "gen thẳng 2.0 720p" |
| A6 | 13/10 QC tự chấm + autopilot | MÂU THUẪN | bị 14/10 (qc_team TẮT, không tự duyệt nháp) thay nhưng không đánh dấu |
| A7 | 06/10 bỏ cổng khóa ngân sách | MÂU THUẪN memory ↔ code | core/project_budget.py:44–52, 300–316, 470–490 còn cổng "Tự chạy trong trần" (ghi "user 08/10") — **cần người dùng xác nhận** |
| A8 | Trần tập 2 = 80 USD | CHƯA LÀM | #31 không có `project_budget`; trần chung 74,5; #28/#29/#30 còn giữ quỹ dự phòng 11,15 + 10,74 + 20,61 USD |
| A9 | Sân khấu 3D chung theo đoạn | CHƯA LÀM | `director_camera_plan` TẮT, `camera_setups` học việc, `video_gate` TẮT |
| A10 | Dùng lại tài nguyên tập trước | CHƯA LÀM | không có code tìm; dựa vào Claude nhớ |
| A11 | Popup không che mặt | một phần | có vùng an toàn TikTok, chưa né mặt (#24, #27 làm tay) |
| A12 | Thoại sạch | một phần | chỉ kiểm ở Biên kịch AI; kịch bản dán tay (#22, #31) không kiểm (`kld_lessons_prompts` TẮT) |
| A14 | qc_team TẮT | ĐÚNG nhưng 2 nguồn | `dashboard.env` còn `FEATURE_QC_TEAM=1` |

ĐÚNG (9): qc_team tắt/scene_qc học việc · nhạc theo đường cảm xúc · ambient_motion bật · travel_truth (chưa gen thật) · popup shot cuối ·
vùng an toàn TikTok · chặn 480p bản giao · ảnh GPT Image 2.5 · trần tự gen lại.

## B) Lỗi lặp

Số liệu CSDL: ảnh bị loại #22 56 %, #24 44 %, #27 64 %; video bị loại #22 50 %, #24 42 %, #27 42 %; giây video trả tiền rồi bỏ #22 78 %,
#27 52 % (216 s). #27: 53/78 lần loại ảnh không ghi lý do; `mistakes` 0 dòng #24/#27; `lessons` 12 dòng, đều cũ.

| Lỗi lặp | Dự án | Đã "sửa" thế nào | Gốc vì sao lặp |
|---|---|---|---|
| Nền lệch map 3D | #22, #24, #27, #30 | prompt Đạo diễn, `plate_view_sentence`/`video_gate` TẮT | Đạo diễn tả nền bằng chữ; sửa sau cờ tắt; không kiểm sau vẽ có quyền chặn |
| Bố cục/chỗ đứng trôi, máy lùi | #24, #27, #30 | `continuity_from` vá, `qc_framing_cap`/`director_camera_plan` TẮT | sân khấu chung chưa làm; QC không kiểm bố cục |
| Đạo cụ Kho vẽ sai | #22, #27, #28, #30 | sửa tay Kho, memory, `skill_object_guard` | dạng/skin ở cảnh không được code mang xuống shot |
| Trạng thái/trang phục không giữ | #22, #27, #31 | memory, `character_state_lock` TẮT | trạng thái chỉ nằm trong chữ |
| Gen video khi ảnh chưa đạt | #24, #27 | `video_pregen` BẬT, `video_gate` TẮT | cổng đúng gốc vẫn tắt |
| Code có nhưng cờ TẮT ở dự án mới | #24→#27 (6/16), #27→#31 (7/7) | ghi memory "đã bật" | không có bước bắt buộc kiểm cờ trước dự án |
| Khâu cuối bằng script riêng | #24, #27 | sửa tay từng dự án | không vào Dashboard |
| Quyết định người dùng bị ghi lệch | 720p, A1, A7 | memory | memory là nơi ghi duy nhất, không đối chiếu code/cờ |

## C) Nguyên nhân hệ thống + đề xuất (theo tác động tiền/chất lượng)

1. **Sửa sau cờ TẮT, memory ghi "đã bật"** (lặp 2 lần). → Mỗi cờ khai `fixes_project`; `before_run` báo ĐỎ trước Bước 1 khi cờ sửa lỗi
   dự án trước còn TẮT, có nút bật hàng loạt; báo cáo kết thúc sinh từ `features.state()`.
2. **Bài học ở memory Claude, không ở chỗ pipeline đọc; vòng học đã chết.** → Bắt buộc chọn lý do loại (enum) ở nút Loại, kể cả khi Claude
   bấm; bật `feedback_to_mistakes` (0 USD); chỉ số chính = tỷ lệ loại theo lý do × dự án.
3. **Một sự thật nhiều nguồn, quyết định sau không thay hẳn quyết định trước.** → `data/decisions.json` (id, ngày, thay_thế, giữ/đổi,
   file:dòng thi hành) + test đối chiếu code/cờ; memory chỉ trỏ id.
4. **"Đã sửa" chỉ bằng test giả thuyết / sửa tay dữ liệu một dự án.** → `verified` cần `evidence_job_ids` dự án thật; mỗi lỗi lặp có bộ
   phát lại 0 USD dựng gói gửi model từ CSDL thật.
5. **Đạo diễn viết bằng chữ sự thật code đã biết.** → hướng D1–D6 (`docs/DANH_GIA_VAI_DAO_DIEN_2026-10-14.md`): code mang dạng Kho,
   trạng thái, hướng lên/xuống xuống từng shot; gọn 165 KB luật.

Chưa chắc (cần chạy thật / người dùng): A7, A8, hiệu quả `travel_truth` / `ambient_motion` / `chat_prompts` trên #31.
