# Đối soát khâu ↔ kế hoạch — 2026-10-23

Báo cáo chỉ đọc; không tự cập nhật kế hoạch hoặc sổ lỗi.

## Tổng hợp số khâu có vấn đề

| Loại | Số khâu |
|---|---:|
| LOI | 13 |
| LONG | 5 |
| THIEU | 7 |
| LECH | 4 |
| KHONG_VIEC | 4 |

## Chi tiết từng khâu, ô và nút

### L1 — Ý tưởng → kịch bản · Biên kịch Claude · chat

- Loại dòng: khâu
- Màu: xanh
- Khâu liên quan: L1
- Phân loại: Không có cảnh báo phân loại
- Lý do: L1: trước chay · sau khong_co · đọc từ ket_qua
- Việc kế hoạch: M1.4 (✅)

### L2 — Bảng kê tài nguyên · asset_checklist

- Loại dòng: khâu
- Màu: xanh
- Khâu liên quan: L2
- Phân loại: Không có cảnh báo phân loại
- Lý do: L2: trước chay · sau khong_co · đọc từ ket_qua (khau_trang_thai: ghi tay 'tat' → cờ asset_checklist = 'chay'; trang_thai_kiem: ghi tay 'tat' → cờ asset_checklist = 'chay')

### L5 — Hồ sơ nhân vật · Bible · ảnh mẫu Kho · dạng nhân vật khai bằng dòng chữ

- Loại dòng: khâu
- Màu: đỏ
- Khâu liên quan: L5
- Phân loại: LOI, THIEU, LECH
- Lý do: L5: trước khong_co · sau khong_co · đọc từ ket_qua
- Việc kế hoạch: M0.9 (✅), M2.2 (✅), M2.3 (✅)
- Lỗi đang mở: P31-G38 — Shot 35/36 tường keo đúng skin nhưng THẲNG hàng, không cong về phía người ném (`gloo-wall-curved` 14/10) — cả Kling lẫn Seedance [OPEN] → M2.3, P33-B1 — Ảnh mẫu thân dài (đầu ≈ 46 % thay vì ≈ 56 % như game), đầu đỏ/tím bẹt, màu áo sai mẫu [OPEN] → M2.3
- Việc đề xuất thêm vào plan: **Bổ sung việc xử lý phần còn lệch ở L5**
- Khâu đề xuất: L5
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; sơ đồ đang đỏ; cần xác định và bổ sung nút, hàm hoặc bước kiểm còn thiếu; trạng thái kế hoạch và màu/bằng chứng hiện tại chưa khớp; mã lỗi: P31-G38, P33-B1
- Bằng chứng: L5: trước khong_co · sau khong_co · đọc từ ket_qua; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:121 · cùng bảng; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:38 · đã xử lý trong dự án: Đo tỉ lệ ảnh góc → câu "1,8 đầu, đầu 55–58 %"; đỏ/tím lấy ảnh mẫu vàng làm ref dáng đầu; màu áo theo `các màu.png` (đỏ: áo trắng quần đỏ; tím: xanh dương đậm); xanh lơ không có ảnh áo → đổi sang vàng (đúng ảnh góc). GPT Image 2.5 vẫn kéo thân ~50 %

### L3 — Đạo diễn: chia shot · prompt · BYĐ · BYĐ #31 có 36/36 — khâu sau không đọc

- Loại dòng: khâu
- Màu: đỏ
- Khâu liên quan: L3
- Phân loại: LOI, THIEU, LECH
- Lý do: L3: trước chay · sau khong_co · đọc từ chu_tu_do (kiem_truoc: bỏ d86 (cờ stage_camera TẮT)) · L3b: trước khong_co · sau tat · đọc từ byd (khau_trang_thai: ghi tay 'chay' → cờ director_camera_plan = 'tat'; trang_thai_sau: ghi tay 'chay' → cờ director_camera_plan = 'tat')
- Việc kế hoạch: M1.4 (✅), M2.1 (✅), M2.4 (✅), M7.1 (✅)
- Lỗi đang mở: P31-G18 — BYĐ của shot mâu thuẫn trường khác của CHÍNH shot [OPEN] → M2.1, P31-G41 — Hướng chạy shot 35 ngược mạch: Kelly "chạy ra xa máy" vào nền, nơi có tường + tháp + địch (34: địch góc xa bên phải, tháp sau chúng) → chạy VỀ PHÍA địch, ngược "dựng keo định chuồn"; 36 lại chạy sang TRÁI khung → 35↔36 k [OPEN] → M3.3, P31-G43 — Kịch bản: "quay người rời khỏi cái xác và đi tiếp"; ảnh 1000 cái xác ở NỀN sau lưng → clip Kelly đi vào nền, VỀ PHÍA cái xác [IN_PROGRESS] → M3.3, P31-G44 — Kịch bản 26: Kelly bên trái, xác "phía trước" giữa-phải, cô "phát hiện" nó; ảnh 998 Kelly đi về phía máy, xác lơ lửng SAU LƯNG bên TRÁI → không thể "phát hiện phía trước"; 27 xác bên PHẢI → nhảy trục 26↔27 [OPEN] → M3.3, P31-G45 — Kịch bản: "bốn địch đứng tách biệt ở bốn góc xa", núp sau hàng rào cao; ảnh 994: bốn địch đứng gần nhau một hàng ở cuối, hàng rào trong thấp (G8 mô hình Kho #265) [OPEN] → M3.3, P31-G50 — 1017/1015 sai bố cục + phi thực tế: 17 Sứ giả đứng ngay đầu tường bắn thẳng vào Kelly (tường không chắn giữa), tường cong lồi ngược; 18 tường chắn ngang ở chỗ khác, Sứ giả đã gục từ đầu shot; hành lang bắc rộng 4 m = bề  [OPEN] → M3.3, P31-G9 — `shot_text_checks` khớp "whole body" trong câu tả SÚNG ("aura along its whole body") → chặn shot 17 [OPEN] → M2.7, P33-A12 — #33 không có BYĐ → `video_pregen` VÀNG "chưa có BYĐ" 22 lần, không kiểm được nhịp / khung cuối [OPEN] → M2.9, V31-GOC4 — BYĐ mâu thuẫn trường khác của shot / thiếu BYĐ [IN_PROGRESS] → M2.1
- Việc đề xuất thêm vào plan: **Bổ sung việc xử lý phần còn lệch ở L3**
- Khâu đề xuất: L3
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; sơ đồ đang đỏ; cần xác định và bổ sung nút, hàm hoặc bước kiểm còn thiếu; trạng thái kế hoạch và màu/bằng chứng hiện tại chưa khớp; mã lỗi: P31-G18, P31-G41, P31-G43, P31-G44, P31-G45, P31-G50, P31-G9, P33-A12, V31-GOC4
- Bằng chứng: L3: trước chay · sau khong_co · đọc từ chu_tu_do (kiem_truoc: bỏ d86 (cờ stage_camera TẮT)); L3b: trước khong_co · sau tat · đọc từ byd (khau_trang_thai: ghi tay 'chay' → cờ director_camera_plan = 'tat'; trang_thai_sau: ghi tay 'chay' → cờ director_camera_plan = 'tat'); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:73 · Shot 2: `byd.may.chuyen_dong = dung_yen` nhưng `camera_move = pan` + kịch bản "góc nhìn lia theo hướng quay" → mọi motion đều bị Tổ rà soát báo đỏ một phía. Không có kiểm code nào so BYĐ ↔ camera_move/action khi Đạo diễn khai; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:134 · shot 34 blocking; shot 35 blocking/motion "run away from camera", ảnh 976 tường ở nền; clip cuối 35 Kelly lao vào tường; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:143 · Kịch bản: "quay người rời khỏi cái xác và đi tiếp"; ảnh 1000 cái xác ở NỀN sau lưng → clip Kelly đi vào nền, VỀ PHÍA cái xác; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:144 · Kịch bản 26: Kelly bên trái, xác "phía trước" giữa-phải, cô "phát hiện" nó; ảnh 998 Kelly đi về phía máy, xác lơ lửng SAU LƯNG bên TRÁI → không thể "phát hiện phía trước"; 27 xác bên PHẢI → nhảy trục 26↔27; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:145 · Kịch bản: "bốn địch đứng tách biệt ở bốn góc xa", núp sau hàng rào cao; ảnh 994: bốn địch đứng gần nhau một hàng ở cuối, hàng rào trong thấp (G8 mô hình Kho #265); docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:565 · P2: Đạo diễn BYĐ phải chạy được qua `claude_cli`; docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:7 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0)

### L4 — Thoại · chọn giọng

- Loại dòng: khâu
- Màu: đỏ
- Khâu liên quan: L4
- Phân loại: THIEU, LECH
- Lý do: L4: trước tat · sau khong_co · đọc từ chu_tu_do
- Việc kế hoạch: M2.9 (✅)
- Việc đề xuất thêm vào plan: **Bổ sung việc xử lý phần còn lệch ở L4**
- Khâu đề xuất: L4
- Lý do đề xuất: sơ đồ đang đỏ; cần xác định và bổ sung nút, hàm hoặc bước kiểm còn thiếu; trạng thái kế hoạch và màu/bằng chứng hiện tại chưa khớp
- Bằng chứng: L4: trước tat · sau khong_co · đọc từ chu_tu_do

### L6 — Sân khấu 3D: dàn cảnh · máy · nền · #31 chạy tay bằng tools/stage_auto

- Loại dòng: khâu
- Màu: tím
- Khâu liên quan: L6
- Phân loại: LOI
- Lý do: L6: trước tat · sau tat · đọc từ byd (khau_trang_thai: ghi tay 'chay' → cờ stage_camera = 'tat'; trang_thai_kiem: ghi tay 'chay' → cờ stage_camera = 'tat') · đang sửa: M4.8
- Việc kế hoạch: M3.1 (✅), M3.2 (✅), M3.3 (✅), M4.8 (🔄), M6.7 (⬜), M7.5 (✅)
- Lỗi đang mở: P31-G1 — Khối giữ chỗ của sân khấu 3D bị mang sang cảnh khác [IN_PROGRESS] → M2.4, P31-G2 — Nền 3D không có mốc tỉ lệ người [OPEN] → M3.2, P31-G3 — Máy góc 'eye' mà ngước/chúi lớn, không kiểm nền bị tường che [IN_PROGRESS] → M3.2, P31-G46 — vị trí vật/nhân vật xuyên các shot liên quan (xác 26–29, keo + địch 34–38, mê cung 14) chỉ tả bằng chữ riêng từng shot; mỗi ảnh gen độc lập → model đặt lại mỗi lần; vá chữ shot này làm lệch shot kia (vd sửa 29 "tháp trái [IN_PROGRESS] → M3.1, P31-G47 — toạ độ chỗ đứng thật (stage inputs doan_4): shot 13 Kelly ở tâm (0,55; 0,1); 15–18 Kelly ở `me_cung_nga_re_bac` (−0,1; 14,3) = hành lang ngoài phía BẮC; 19 ở `me_cung_khe_tay` (−14,3; −0,1); biệt thự (mốc PKK_OUT_Buildin [OPEN] → M3.1, P31-G49 — "dưới chân Kelly có bậc cỏ cao tới đầu gối, mê cung làm gì có"): grid 3D tâm mê cung: ô cỏ (Fence001) cao hơn lối đi chỉ 0,13 m. Máy 16/10 của shot 13 đứng gần trên ô cỏ, cao 1,9 m, cúi −27°, cách Kelly 0,9 m (Tổ rà soát [OPEN] → M3.2, P31-G8 — Mô hình 3D Kho #265 hàng rào thấp ≈ 1,5 m → nhìn qua thấy nhiều lớp rào [FIXED_UNVERIFIED] → M3.2, P33-A10 — Góc `high` của plate cố định chúc 30° (`plate_camera.HIGH_TILT_DEG`) → nền chỉ còn sàn đá [IN_PROGRESS] → M3.2, P33-B4 — Nền ghép "như dán đè ảnh 3D" [OPEN] → M3.1, P33-B5 — Góc in-game chuẩn = máy thấp ở thềm nhìn lên cầu thang, tháp TRÁI bị cắt đỉnh; đổi sang EWS cho thấy đỉnh tháp là SAI bố cục [OPEN] → M3.2, V31-GOC1 — Vị trí vật/nhân vật không có MỘT nguồn sự thật xuyên shot [IN_PROGRESS] → M3.1, V31-GOC2 — Hình học máy ↔ người ↔ sàn bằng hằng số / chữ thay vì đo [IN_PROGRESS] → M3.2, V31-GOC5 — Kho: vật một dạng, tỉ lệ mô hình, nền ghép [OPEN] → M3.2
- Việc đề xuất thêm vào plan: **Tiếp tục M4.8 và chốt tiêu chí cho L6**
- Khâu đề xuất: L6
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G1, P31-G2, P31-G3, P31-G46, P31-G47, P31-G49, P31-G8, P33-A10, P33-B4, P33-B5, V31-GOC1, V31-GOC2, V31-GOC5
- Bằng chứng: L6: trước tat · sau tat · đọc từ byd (khau_trang_thai: ghi tay 'chay' → cờ stage_camera = 'tat'; trang_thai_kiem: ghi tay 'chay' → cờ stage_camera = 'tat'); đang sửa: M4.8; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:12 · `stage_camera.props` = trụ Ø0,5×1,75 m nhãn "XÁC ĐEN BIẾT BAY" (dàn cảnh cảnh 6) có ở shot 28/30 (`source: "cảnh 6 (cùng sân khấu)"`) và 34/35 (`"cảnh 7 (cùng sân khấu)"`), kể cả cảnh 8 = thế giới THỰC TẠI ban ngày (không có quái). Khối render vào nền (`plate.png`) → model vẽ thành cột đá; D6 shot 3; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:13 · Nền render trống người; cỡ người chỉ do câu % khung trong prompt (vd shot 23 *"her whole body about 60% of frame height … never resize her smaller for distance"*) — không ràng theo khoảng cách 3D. Shot 35 địch to như khổng lồ; shot 14 máy cao 3,6 m chúi −18° (meta `pitch_deg -18.2`) → hàng rào trông; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:14 · Shot 28 `angle: eye` nhưng máy thấp hơn cảnh 0,56 m (z 10,85 vs 11,41), meta `pitch_deg +17.3` → nền gần như chỉ tường trống, model tự bịa; shot 35 `pitch +11.1`; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:26 · G8 (xác nhận 18/10 bằng video in-game người dùng gửi `ScreenRecording_10-17-2026_08-33-20_1.mov`): trong game, hàng rào BÊN; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:32 · tạm: Dùng `eye` (máy ngang mắt người lớn ≈ chúc 5–10° xuống con rối chibi); docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:41 · đã xử lý trong dự án: Chuyển màu Lab theo ảnh in-game người dùng (`goc_chup_ingame_chuan.png`), mây in-game + vệt gió + sương theo `depth.png`, quầng đỏ sẫm; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:42 · đã xử lý trong dự án: Về WS góc thấp; docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:4 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0); docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:5 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0); docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:8 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0)

### L7 — Storyboard · ảnh neo · scene_storyboard

- Loại dòng: khâu
- Màu: đỏ
- Khâu liên quan: L7
- Phân loại: LOI, THIEU
- Lý do: L7: trước chay · sau chay · đọc từ chu_tu_do
- Việc kế hoạch: M2.2 (✅), M3.4 (✅), M6.6 (⬜), M6.9 (✅)
- Lỗi đang mở: P33-B2 — Ảnh trời tham chiếu dính đỉnh tháp → model vẽ tháp thứ hai [OPEN] → M2.7
- Việc đề xuất thêm vào plan: **Tiếp tục M6.6 và chốt tiêu chí cho L7**
- Khâu đề xuất: L7
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; sơ đồ đang đỏ; cần xác định và bổ sung nút, hàm hoặc bước kiểm còn thiếu; mã lỗi: P33-B2
- Bằng chứng: L7: trước chay · sau chay · đọc từ chu_tu_do; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:39 · đã xử lý trong dự án: Cắt ảnh trời chỉ phần mây/mắt xoáy

### L8 — Lắp GÓI ẢNH: prompt cuối + ảnh ref · runner._submit_args — dẫn thẳng tới tiền

- Loại dòng: khâu
- Màu: tím
- Khâu liên quan: L8
- Phân loại: LOI
- Lý do: L8: trước khong_co · sau khong_co · đọc từ chu_tu_do · đang sửa: M4.7, M2.10
- Việc kế hoạch: M1.9 (✅), M2.10 (🔄), M2.2 (✅), M2.6 (✅), M2.7 (✅), M3.3 (✅), M4.7 (🔄), M6.2 (⬜), M6.6 (⬜), M7.7 (⬜)
- Lỗi đang mở: P31-G4 — Chọn ảnh Kho bằng dò bí danh trong chữ, không đọc BYĐ [OPEN] → M2.2, P31-G5 — Sổ gói ghi nhãn ảnh sai [OPEN] → M2.6, P31-G7 — Shot POV bỏ ảnh súng [FIXED_UNVERIFIED] → M2.7, P33-B3 — Tả bằng chữ "mắt xoáy ngay trên đỉnh tháp" → model dời tháp ra giữa [OPEN] → M3.3
- Việc đề xuất thêm vào plan: **Tiếp tục M2.10 và chốt tiêu chí cho L8**
- Khâu đề xuất: L8
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G4, P31-G5, P31-G7, P33-B3
- Bằng chứng: L8: trước khong_co · sau khong_co · đọc từ chu_tu_do; đang sửa: M4.7, M2.10; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:15 · `core/assets.py:_named_extras` (1815–1855) khớp `names_of(a)` trong text + image_prompt. Bí danh #443 = *"flying black corpse, floating corpse, levitating corpse, cái xác biết bay"*. Phiên này bỏ "floating corpse" khỏi prompt shot 23 (để qua bộ lọc OpenAI) → job 993 KHÔNG gửi ảnh #443 (job 967 trước; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:16 · `core/sent_package.py:124 _meta_index` khóa theo basename — Kho đặt tên `1.png/2.png/3.png` ở mọi mục → ảnh #443/2.png ghi nhãn "SKORP", #367/2.png ghi "SKORP", #425/3.png ghi "KELLY". Prompt gửi model vẫn ĐÚNG (shot 24: *"Image 5 is the object XÁC ĐEN BIẾT BAY"*) — chỉ sổ sai; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:19 · `core/assets.py:1830` bỏ ref súng khi `prop_lock.is_pov` (luật #27 "FF không có POV cầm súng") → shot 15 POV bắn: model vẽ súng đen thường, mất hào quang đỏ. 16/17 có ref SKORP (#433/2.png là SKORP đen) nhưng câu prompt chỉ ghi "red-glowing" ngắn → màu đỏ yếu/mất; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:40 · đã xử lý trong dự án: Vị trí đặt bằng nền 3D, không bằng prompt: ghép trời in-game vào plate (alpha `raw.png`, mắt xoáy đặt theo đỉnh tháp đo trên ảnh) — script scratchpad `p33_sky_composite3.py`

### L9 — Gen ẢNH khung đầu · ClipAI

- Loại dòng: khâu
- Màu: đỏ
- Khâu liên quan: L9
- Phân loại: LOI, THIEU
- Lý do: L9: trước khong_co · sau chay · đọc từ ket_qua (kiem_sau: bỏ d92 (cờ director_camera_plan TẮT))
- Việc kế hoạch: M1.1 (✅), M1.2 (✅), M1.3 (✅), M1.6 (✅), M3.5 (✅), M4.1 (✅), M4.5 (✅), M4.6 (✅), M6.3 (✅), M6.6 (⬜), M7.4 (✅), M7.8 (⬜)
- Lỗi đang mở: P31-G19 — Ảnh khung đầu vẽ trạng thái CUỐI thay vì ĐẦU của shot [OPEN] → M2.7, P31-G40 — ảnh khung đầu đã duyệt 1000 vốn KHÔNG có trời và KHÔNG có tháp (tường sương dày) dù image_prompt ghi "tower visible in the background"; motion đòi trời nhưng Seedance bám ảnh. Thêm: shot 29 là shot 2 của nhóm nên clip kh [OPEN] → M3.3, P31-G48 — ảnh 1090 vẽ tường thành khối hộp hai mặt vuông góc, khác tấm cong ở 35 (1094) → chữ 36: "SAME curved wall … ONE thin continuous curved panel … never a box". [OPEN] → M3.4, P33-A5 — QC lớp 0 đo nhầm cỡ cảnh ảnh S2 (bố cục sau lưng nhóm: đo mặt con tím ở xa → "WS, shot xin MS") → tự tạo job gen lại ép "từ thắt lưng trở lên" [FIXED_UNVERIFIED] → M4.5
- Việc đề xuất thêm vào plan: **Tiếp tục M6.6 và chốt tiêu chí cho L9**
- Khâu đề xuất: L9
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; sơ đồ đang đỏ; cần xác định và bổ sung nút, hàm hoặc bước kiểm còn thiếu; mã lỗi: P31-G19, P31-G40, P31-G48, P33-A5
- Bằng chứng: L9: trước khong_co · sau chay · đọc từ ket_qua (kiem_sau: bỏ d92 (cờ director_camera_plan TẮT)); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:74 · Shot 1, 2: ảnh đã thấy 2 cửa trong khi shot là "quay người dần lộ 2 cửa"; shot 4: ý đồ qua vai thấy 2 cửa, ảnh không thấy. Gốc: prompt ảnh tả cả hành động ("camera turning to reveal two doors") → model vẽ kết quả. Liên quan G11; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:27 · tạm: Hủy job tự gen, đổi size shot sang WS

### L10 — Gen lại ảnh · Đạo diễn viết lại prompt

- Loại dòng: khâu
- Màu: đỏ
- Khâu liên quan: L10
- Phân loại: LOI, THIEU, LECH
- Lý do: L10: trước chay · sau khong_co · đọc từ chu_tu_do
- Việc kế hoạch: M1.4 (✅), M2.5 (✅), M5.1 (✅), M6.3 (✅)
- Lỗi đang mở: P33-A4 — Đạo diễn (director_rewrite, chạy claude_cli) tự viết lại image_prompt shot 1–3 khi loại ảnh, ép thấy đỉnh tháp + xoáy → ảnh bản 3 dời tháp vào giữa, thêm mặt đồng hồ [OPEN] → M2.5
- Việc đề xuất thêm vào plan: **Bổ sung việc xử lý phần còn lệch ở L10**
- Khâu đề xuất: L10
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; sơ đồ đang đỏ; cần xác định và bổ sung nút, hàm hoặc bước kiểm còn thiếu; trạng thái kế hoạch và màu/bằng chứng hiện tại chưa khớp; mã lỗi: P33-A4
- Bằng chứng: L10: trước chay · sau khong_co · đọc từ chu_tu_do; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:26 · tạm: Khôi phục prompt từ sao lưu; tắt `director_rewrite` + `chat_prompts` CHỈ trong tiến trình gen

### L11 — Motion prompt + dịch

- Loại dòng: khâu
- Màu: tím
- Khâu liên quan: L11
- Phân loại: LOI
- Lý do: L11: trước chay · sau khong_co · đọc từ chu_tu_do · đang sửa: M2.10
- Việc kế hoạch: M1.4 (✅), M2.10 (🔄), M6.5 (⬜), M7.1 (✅)
- Lỗi đang mở: P31-G11 — Motion prompt mô tả cảnh khác khung đầu (ảnh đã duyệt) [OPEN] → M2.9, P31-G26 — Câu chữ nói "nhìn về tháp" nhưng máy 3D của shot quay về phía khác → model tự vẽ tháp sai chỗ [OPEN] → M3.3, P33-B10 — Chữ "cats" trong motion ngoài câu chặn → nguy cơ vẽ mèo (Tổ rà soát bắt) [OPEN] → M2.8, P33-B7 — Cổng video chặn: motion còn tiếng Việt (tên RỐI … có dấu, "Tháp Đồng Hồ") [OPEN] → M2.8, V31-GOC3 — Chữ viết tự do không khớp cái máy 3D thấy [IN_PROGRESS] → M3.3
- Việc đề xuất thêm vào plan: **Tiếp tục M2.10 và chốt tiêu chí cho L11**
- Khâu đề xuất: L11
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G11, P31-G26, P33-B10, P33-B7, V31-GOC3
- Bằng chứng: L11: trước chay · sau khong_co · đọc từ chu_tu_do; đang sửa: M2.10; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:59 · Shot 2: motion "chưa thấy cửa, quay mới lộ" — ảnh 987 đã thấy 2 cửa; shot 4: "2 cửa phía trước" — ảnh 948 là tường kệ sách; shot 35/36: "tường keo cong" — ảnh tường thẳng. Claude viết motion bám chữ kịch bản hơn ảnh, không có kiểm code nào so motion ↔ khung đầu; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:87 · S31: nền 3D là tường / lan can không có tháp; motion + D6 viết "the tower rising in the background" → clip có tháp đen ở chỗ không có; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:47 · đã xử lý trong dự án: Đổi "like the reference video"; giữ câu chặn "the cats in the reference only give the motion…"; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:44 · đã xử lý trong dự án: Tên không dấu (ROI DO A…) + "the Clock Tower"; docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:6 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0)

### L12 — Lắp GÓI VIDEO · motion + khung đầu + ref + model

- Loại dòng: khâu
- Màu: tím
- Khâu liên quan: L12
- Phân loại: LOI
- Lý do: L12: trước khong_co · sau khong_co · đọc từ chu_tu_do · đang sửa: M4.7, M2.10
- Việc kế hoạch: M1.5 (✅), M1.9 (✅), M2.10 (🔄), M2.6 (✅), M2.8 (✅), M2.9 (✅), M3.4 (✅), M4.7 (🔄), M6.2 (⬜), M6.5 (⬜), M6.9 (✅), M7.3 (✅), M7.4 (✅), M7.7 (⬜)
- Lỗi đang mở: P31-G10 — Lời người dẫn chuyện (LỜI DẪN) bị coi là lời thoại phải KHỚP MÔI [FIXED_UNVERIFIED] → M2.9, P31-G12 — Tên địa danh có dấu trong câu tiếng Anh làm chặn gói [OPEN] → M2.8, P31-G13 — Gói nhóm vượt 5000 ký tự [OPEN] → M2.8, P31-G23 — Công cụ kiểm gói video thiếu [OPEN] → M1.9, P31-G24 — 7 shot cận (9, 10, 12, 19, 24, 28, 32) đi Kling trái quyết định `video-route-2026-10-13` ("video hết Seedance 2.5, Kling chỉ đường lùi") [FIXED_UNVERIFIED] → M2.8, P31-G27 — Gói VIDEO chỉ gửi 1 ảnh khuôn mặt mỗi nhân vật — không gửi ảnh DẠNG (bóng mờ, Kho #427) và không gửi ảnh VẬT Kho (Bom keo skin thang máy #367, SKORP #433, XÁC ĐEN #443), trong khi gói ẢNH có đủ [FIXED_UNVERIFIED] → M2.3, P31-G29 — Bước kiểm gói của phiên này bỏ qua D6 (chat_prompts BẬT ở máy chính: Claude viết lại prompt video lúc gửi) và không đối chiếu ảnh cần (dạng/vật) với "Image N" trong prompt [OPEN] → M1.9, P31-G30 — Kho chủ thể ClipAI đầy 100/100 → ảnh không tải lên, gửi ảnh đánh dấu [FIXED_UNVERIFIED] → M1.5, P31-G53 — `speaker_no_identity` vẫn báo cho LỜI DẪN tới 19/10 13:52 (sau sửa G10 ngày 18/10) — `core/seedance_refs.py:546` chưa bỏ người dẫn chuyện [OPEN] → M2.9, P31-G54 — Trần độ dài prompt chặn câu cần thiết: D6 bị từ chối (3256 > 3192; 4096 > 4000), `gore_restraint` "không thêm được câu … quá 4000 ký tự" [OPEN] → M2.8, P31-G58 — Kho chủ thể đầy lặp lại ở #33 (13 lần, 20/10) — G30 chưa sửa nên dự án sau gặp lại [FIXED_UNVERIFIED] → M1.5, P33-B8 — Seedance ref-only chép cả đoạn chuyển cảnh đầu đoạn ref: lộ con mèo (S5), góc trống (S6), mở bằng một con ở xa (S4) [OPEN] → M2.8
- Việc đề xuất thêm vào plan: **Tiếp tục M2.10 và chốt tiêu chí cho L12**
- Khâu đề xuất: L12
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G10, P31-G12, P31-G13, P31-G23, P31-G24, P31-G27, P31-G29, P31-G30, P31-G53, P31-G54, P31-G58, P33-B8
- Bằng chứng: L12: trước khong_co · sau khong_co · đọc từ chu_tu_do; đang sửa: M4.7, M2.10; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:58 · `core/lipsync.py:_method` so người nói với `characters`; shot POV không có cast → điều kiện "người nói ngoài khung" không bao giờ đúng → "post" → (cờ dialogue_take) "take" → gói nhóm S01–S03, S05–S06 ghi *"LOI DAN speak Audio1… Sync the mouth, jaw…"* + gửi reference_audio. Model có thể vẽ thêm người; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:60 · "the Cổng Trời hedge maze" (S05), "LỜI DẪN narrates" (S39) → `lint` "prompt còn chữ tiếng Việt" chặn cả clip nhóm. Motion writer không được dặn viết tên riêng không dấu; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:61 · S01–S03 = 5173 ký tự: motion mỗi shot có câu giải thích "because…" (viết cho người đọc), khối khớp môi G10 cộng thêm; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:78 · Phải viết script tạm (thư mục thử + provider giả có chữ ký ClipAI) mới thấy G10–G13; sổ gói ghi `reference_only` không nhãn; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:79 · `core/model_router.py` nhánh `seedance_refs` (chỉ chạy khi `FEATURE_SEEDANCE_REF_GROUPS=1` — cờ nằm trong `dashboard.env`): shot cận thấy mặt không vào nhóm tham chiếu → cờ `closeup_start_frame` (S4.1, 29/09, `verified: False`) → Kling từ khung đầu, TRƯỚC luật E1 (E1 chỉ đổi model họ Seedance). Chạy; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:85 · `core/seedance_refs.py:314 identity_pictures`: lấy ảnh danh tính (Kelly = ảnh áo vàng 23/10.png) + bỏ ảnh trang phục khi nhân vật ở dạng, KHÔNG thêm ảnh dạng; không có nhánh ảnh vật. Gói thật job 1045 (S28–29): "Image 3 is Kelly: identity only — NOT the clothes … ghost form" + ảnh áo vàng → cận mặt; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:89 · Script chạy thử tắt D6 như replay_payload; phiên đọc danh sách ảnh của sổ gói (có dạng/vật) thay vì ánh xạ Image N (không có) — bỏ sót G27; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:90 · diag `subjects` jobs 1047, 1049–1051, 1054 (code 1110); docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:558 · N6 (dùng `speaker_lint.is_narrator`); docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:559 · N4 cùng G13: ngân sách ký tự theo khối, ưu tiên câu bắt buộc; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:563 · N1 (G30); docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:45 · đã xử lý trong dự án: Cắt đầu clip khi dựng; S4/S6 làm file ref mới: thay khúc chuyển cảnh bằng khung đội hình tua ngược, giữ độ dài/nhịp nhạc

### L13 — Gen VIDEO (nháp → cao) · Seedance / Kling

- Loại dòng: khâu
- Màu: xanh
- Khâu liên quan: L13
- Phân loại: LOI
- Lý do: L13: trước chay · sau chay · đọc từ ket_qua
- Việc kế hoạch: M1.2 (✅), M1.3 (✅), M1.5 (✅), M1.6 (✅), M2.8 (✅), M4.1 (✅), M4.2 (✅), M4.3 (✅), M4.6 (✅), M5.1 (✅), M6.3 (✅), M7.1 (✅), M7.3 (✅), M7.4 (✅)
- Lỗi đang mở: P31-G15 — Mục cũ trong lipsync index không dọn khi method đổi về "skip" [OPEN] → M2.9, P31-G16 — QC đo clip coi shot chỉ có lời dẫn là "đang nói" [OPEN] → M2.9, P31-G17 — `quality_tier.py:177` coi `lip_sync is True` là có khớp môi trước `method_for` [OPEN] → M2.9, P31-G20 — Cổng ảnh→video báo nhầm "lệch nền 3D" khi ảnh không có/ít trời [OPEN] → M3.5, P31-G28 — Clip Seedance chế độ ảnh tham chiếu không bắt đầu đúng khung đầu đã duyệt; video prompt không mang câu bầu trời [OPEN] → M2.8, P31-G32 — Seedance chặn 6/8 job "real person" (ảnh `content[5..7]`) → tự lùi sang Kling (1067–1072, 31 s ≈ 2,70 USD) [FIXED_UNVERIFIED] → M1.5, P31-G36 — Tạm dừng dự án không chặn job đang chuẩn bị dở; thử lại sau khi bị từ chối lần đầu vẫn đi Seedance [IN_PROGRESS] → M1.3, P31-G37 — Shot 28 (nhóm 28+29) Seedance vẽ Kelly áo vàng, mất dạng bóng mờ ngay khung đầu; Kling cùng đầu vào giữ bóng mờ [OPEN] → M2.8, P31-G51 — Chấm 12 clip nháp 19/10 tối: 13 đơ 6 s; 16 địch không phản ứng, Kelly đơ; 18 máy Kling xuyên rào + địch gục vẫn bắn; 19 xoay 180° lố + áo đổi sọc; 29 súng biến mất 1–2,5 s; 35 mặt anime + 1 s cuối trống; 36 chạy tại chỗ, [OPEN] → M4.2, P31-G52 — QC logic chuỗi 39 clip (`scripts_19-10/qc_sequence/result.json`): độ cao nền đổi giữa shot 9→13; S10/11/13 nhặt súng trên thềm cỏ cao; bắn khi đã hết địch (18, 19); tường keo có trước khi ném (35); cửa shot 24 khác 23/25 [OPEN] → M4.3, P33-A1 — Job ảnh/clip succeeded 2 lần (`InvalidTransition succeeded -> succeeded`), lần sau đọc ảnh chưa ghi xong → QC lớp 0 `FileNotFoundError` → tự gen lại (thừa 0,05 USD job 1162→1163) [FIXED_UNVERIFIED] → M1.2, P33-A11 — `end_frame_skill_object` báo "ném keo" 28 lần ở #33 (không có tường keo): thông điệp viết cứng ở `core/runner.py:1433`, nhận mọi lý do từ `end_frames.skip_reason` [OPEN] → M2.9, P33-A15 — `download_error` PermissionError WinError 32 (tệp bị tiến trình khác giữ) [FIXED_UNVERIFIED] → M1.2, P33-B9 — Seedance ref-only không giữ khung ảnh đầu, theo khoảng cách máy của ref → S6 hàng con rối nhỏ hơn mèo [OPEN] → M2.8, V21-R3 — `qc_observe` raise khi `vat` là chuỗi (qc_observe.py:62–64) [FIXED_UNVERIFIED] → M1.1
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G15, P31-G16, P31-G17, P31-G20, P31-G28, P31-G32, P31-G36, P31-G37, P31-G51, P31-G52, P33-A1, P33-A11, P33-A15, P33-B9, V21-R3**
- Khâu đề xuất: L13
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G15, P31-G16, P31-G17, P31-G20, P31-G28, P31-G32, P31-G36, P31-G37, P31-G51, P31-G52, P33-A1, P33-A11, P33-A15, P33-B9, V21-R3
- Bằng chứng: L13: trước chay · sau chay · đọc từ ket_qua; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:63 · `runner.py:2214–2250`, `lipsync.mark` chỉ ghi thêm → `synced_scene_ids` sai khi gen lại; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:64 · `core/claude_tasks.py:323` `speaking = bool(data.get("dialogue"))`; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:65 · shot chỉ lời dẫn mà Đạo diễn gắn lip_sync → tính shot khó; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:75 · S22 (trong phòng) và S39 (từ trên cao): cổng so đường chân trời ở 7 % / 14 % khung — ảnh khớp bố cục nền 3D (xem ảnh so sánh) nhưng không lộ trời; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:86 · `framing_guard` ĐỎ nhiều clip (vd job 1043 "khung 0 khác hẳn ảnh đầu, khớp 22/3232 điểm"); S16 mở đầu Kelly nằm ở xa, mất trời có bóng ma; S29 trời sương xám như nền 3D; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:101 · `job_events` 1057/1058/1059/1060/1063/1064/1065/1066: `InputImageSensitiveContentDetected.PrivacyInformation`; diag `subjects`: "Kho chủ thể ClipAI đầy (100/100) … gửi ảnh như cũ (đánh dấu)"; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:110 · Tạm dừng 03:42:31 (`ui_actions`), job 1075 running Kling 03:42:41; 1061→1073 và 1062→… lần thử lại đầu vẫn bị Seedance chặn real_person rồi mới sang Kling (sáng: 1057→1065→1071); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:120 · bảng `p31_kling_vs_seedance_8shot.jpg`; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:556 · N7; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:557 · N3 + E cross-shot (`qc_sequence_logic`, cờ TẮT); docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:23 · tạm: Tiến trình riêng chỉ `submit_pending`, để Dashboard poll; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:564 · N4: thông điệp theo lý do thật; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:568 · N1 cùng A1; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:46 · đã xử lý trong dự án: Câu khóa cỡ khung chỉ giúp S4; S6 CHƯA đạt; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:260 · ĐANG XẢY RA (18/10: `qc_observe_enum` BẬT ở máy chính; #31 shot 30 `vat=["AWM"]`)

### L14 — TTS · nhạc · SFX · phụ đề

- Loại dòng: khâu
- Màu: đỏ
- Khâu liên quan: L14
- Phân loại: LOI, THIEU, KHONG_VIEC
- Lý do: L14a: trước khong_co · sau chay · đọc từ ket_qua · L14b: trước khong_co · sau khong_co · đọc từ chu_tu_do · L14c: trước khong_co · sau khong_co · đọc từ chu_tu_do · L14d: trước khong_co · sau khong_co · đọc từ chu_tu_do
- Lỗi đang mở: P31-G14 — Nút "⏱ Đặt thời lượng theo giọng thật" kéo dài MỌI shot có lời dẫn [OPEN] → M2.9, P31-G42 — Lời dẫn đi trước hình: shot 36 đọc "…tụi nó thì đứng cười hở nách ăn mừng" khi Kelly còn chạy; ngã ở 37, ăn mừng ở 38 (38 không có lời) [OPEN] → M4.3
- Việc đề xuất thêm vào plan: **Bổ sung việc vào plan cho L14**
- Khâu đề xuất: L14
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; sơ đồ đang đỏ; cần xác định và bổ sung nút, hàm hoặc bước kiểm còn thiếu; khoảng trống hoặc lỗi chưa có việc kế hoạch được gắn trực tiếp; mã lỗi: P31-G14, P31-G42
- Bằng chứng: L14a: trước khong_co · sau chay · đọc từ ket_qua; L14b: trước khong_co · sau khong_co · đọc từ chu_tu_do; L14c: trước khong_co · sau khong_co · đọc từ chu_tu_do; L14d: trước khong_co · sau khong_co · đọc từ chu_tu_do; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:62 · `voice.fit_durations` kéo 17 shot (S10 1,3→8 s, S24 1→7 s) — đổi nhịp phim + tăng tiền video, không hỏi; chỉ 3 shot (6, 12, 31) thật sự bị chặn đỏ; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:135 · dialogue 36/38

### L15 — Dựng · bản thô · popup cuối · ffmpeg — 0 USD

- Loại dòng: khâu
- Màu: xanh
- Khâu liên quan: L15
- Phân loại: LOI
- Lý do: L15a: trước khong_co · sau chay · đọc từ ket_qua (trang_thai_sau: ghi tay 'tat' → cờ rough_cut_review = 'chay') · L15b: trước khong_co · sau khong_co · đọc từ ket_qua
- Lỗi đang mở: P33-B11 — Bản ghép ref 1080×2730 quá khung TikTok; cắt khung con rối quá cao → thấp đầu [OPEN] → M5.2
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P33-B11**
- Khâu đề xuất: L15
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P33-B11
- Bằng chứng: L15a: trước khong_co · sau chay · đọc từ ket_qua (trang_thai_sau: ghi tay 'tat' → cờ rough_cut_review = 'chay'); L15b: trước khong_co · sau khong_co · đọc từ ket_qua; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:48 · đã xử lý trong dự án: 1080×1920: ref 760×570 + nền mờ, con rối 1080×1350 cắt theo từng shot

### L16 — Thay đổi giữa chừng · sửa shot / Kho

- Loại dòng: khâu
- Màu: tím
- Khâu liên quan: L16
- Phân loại: LOI
- Lý do: L16: trước tat · sau khong_co · đọc từ chu_tu_do (trang_thai_kiem: ghi tay 'chay' → cờ change_review = 'tat') · đang sửa: M4.7, M4.8
- Việc kế hoạch: M0.10 (✅), M1.4 (✅), M1.7 (✅), M2.4 (✅), M2.5 (✅), M4.5 (✅), M4.7 (🔄), M4.8 (🔄), M6.10 (⬜), M6.4 (⬜), M6.9 (✅), M7.1 (✅), M7.2 (✅), M7.5 (✅), M7.6 (✅), M7.7 (⬜), M7.8 (⬜), M8.0 (✅), M8.1 (⬜), M8.2 (⬜), M8.3 (⬜), M8.4 (⬜)
- Lỗi đang mở: P31-G21 — Shot chèn tay không có BYĐ [OPEN] → M2.4, P31-G22 — BYĐ không cập nhật khi đổi nội dung shot [OPEN] → M2.2, P31-G34 — Job 1061/1062 (shot 30, 31 nhóm) kẹt `queued` từ 08:00 [OPEN] → M4.5, P31-G35 — Tổ rà soát tác động LỖI (Claude hết tiền) mà cổng giữ vẫn MỞ → job 1061 tự gửi ngay khi chưa được rà, trước khi kịp tạm dừng dự án [FIXED_UNVERIFIED] → M1.4, P31-G6 — Shot chèn tay (`llm_io.insert_scene_after`) không thừa kế bối cảnh [OPEN] → M2.4, P33-A2 — Vòng nền Tổ rà soát của Dashboard (anthropic hết tiền) chộp `change_events` pending → `failed` → giữ job [IN_PROGRESS] → M1.4, P33-A6 — Tổ rà soát báo nhầm shot 6 "không có video tham chiếu" (#877) [OPEN] → M4.5
- Việc đề xuất thêm vào plan: **Tiếp tục M4.7 và chốt tiêu chí cho L16**
- Khâu đề xuất: L16
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G21, P31-G22, P31-G34, P31-G35, P31-G6, P33-A2, P33-A6
- Bằng chứng: L16: trước tat · sau khong_co · đọc từ chu_tu_do (trang_thai_kiem: ghi tay 'chay' → cờ change_review = 'tat'); đang sửa: M4.7, M4.8; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:76 · S15–17: `video_pregen` VÀNG "chưa có BYĐ — chưa kiểm được nhịp đầu–đỉnh–cuối" (G6 mở rộng); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:77 · S18: BYĐ vẫn "Lính áo choàng đổi tư thế" sau khi đổi thành hạ Sứ giả; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:103 · `change_review_hold` ×221: motion mới bỏ tháp ("No tower is in this frame") nhưng mô tả shot 30 + `plate_view` landmark vẫn giữ Clock Tower; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:109 · `change_events` 1400/1403 state `failed` (LlmError hết tiền); `change_review.blocking` trả None; job 1061 running 03:38:13 → Seedance chặn real_person → retry 1073 (Kling); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:18 · Shot 15–17 chèn 18/10 thiếu `location_asset/location/time/weather/lighting/mood` → `place_refs.wants_render` = False ("không còn ở bối cảnh có mô hình 3D") → gói KHÔNG có nền 3D, chỉ ảnh Kho #265/#450 — im lặng; sau khi chép `location_asset` thì nền render ra day-clear (thiếu time/weather); docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:24 · tạm: Rà từng shot bằng `review_scene_now` + client claude_cli ngay sau khi đặt pending; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:28 · tạm: Đóng `dismissed` kèm lý do

### kb.idea — 💡 Ý tưởng / 📜 Đây là kịch bản

- Loại dòng: ô Dashboard
- Màu: xanh
- Khâu liên quan: L1
- Phân loại: Không có cảnh báo phân loại
- Lý do: có bằng chứng

### kb.analyse — ▶ Phân tích (tách cảnh) · 0 USD

- Loại dòng: ô Dashboard
- Màu: xanh
- Khâu liên quan: L1
- Phân loại: Không có cảnh báo phân loại
- Lý do: có bằng chứng

### kb.director — 🤖 Lập kế hoạch (≈ x USD)

- Loại dòng: ô Dashboard
- Màu: xanh
- Khâu liên quan: L3
- Phân loại: LOI
- Lý do: có bằng chứng
- Lỗi đang mở: P31-G18 — BYĐ của shot mâu thuẫn trường khác của CHÍNH shot [OPEN] → M2.1, P31-G41 — Hướng chạy shot 35 ngược mạch: Kelly "chạy ra xa máy" vào nền, nơi có tường + tháp + địch (34: địch góc xa bên phải, tháp sau chúng) → chạy VỀ PHÍA địch, ngược "dựng keo định chuồn"; 36 lại chạy sang TRÁI khung → 35↔36 k [OPEN] → M3.3, P31-G43 — Kịch bản: "quay người rời khỏi cái xác và đi tiếp"; ảnh 1000 cái xác ở NỀN sau lưng → clip Kelly đi vào nền, VỀ PHÍA cái xác [IN_PROGRESS] → M3.3, P31-G44 — Kịch bản 26: Kelly bên trái, xác "phía trước" giữa-phải, cô "phát hiện" nó; ảnh 998 Kelly đi về phía máy, xác lơ lửng SAU LƯNG bên TRÁI → không thể "phát hiện phía trước"; 27 xác bên PHẢI → nhảy trục 26↔27 [OPEN] → M3.3, P31-G45 — Kịch bản: "bốn địch đứng tách biệt ở bốn góc xa", núp sau hàng rào cao; ảnh 994: bốn địch đứng gần nhau một hàng ở cuối, hàng rào trong thấp (G8 mô hình Kho #265) [OPEN] → M3.3, P31-G50 — 1017/1015 sai bố cục + phi thực tế: 17 Sứ giả đứng ngay đầu tường bắn thẳng vào Kelly (tường không chắn giữa), tường cong lồi ngược; 18 tường chắn ngang ở chỗ khác, Sứ giả đã gục từ đầu shot; hành lang bắc rộng 4 m = bề  [OPEN] → M3.3, P31-G9 — `shot_text_checks` khớp "whole body" trong câu tả SÚNG ("aura along its whole body") → chặn shot 17 [OPEN] → M2.7, P33-A12 — #33 không có BYĐ → `video_pregen` VÀNG "chưa có BYĐ" 22 lần, không kiểm được nhịp / khung cuối [OPEN] → M2.9, V31-GOC4 — BYĐ mâu thuẫn trường khác của shot / thiếu BYĐ [IN_PROGRESS] → M2.1
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G18, P31-G41, P31-G43, P31-G44, P31-G45, P31-G50, P31-G9, P33-A12, V31-GOC4**
- Khâu đề xuất: L3
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G18, P31-G41, P31-G43, P31-G44, P31-G45, P31-G50, P31-G9, P33-A12, V31-GOC4
- Bằng chứng: có bằng chứng; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:73 · Shot 2: `byd.may.chuyen_dong = dung_yen` nhưng `camera_move = pan` + kịch bản "góc nhìn lia theo hướng quay" → mọi motion đều bị Tổ rà soát báo đỏ một phía. Không có kiểm code nào so BYĐ ↔ camera_move/action khi Đạo diễn khai; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:134 · shot 34 blocking; shot 35 blocking/motion "run away from camera", ảnh 976 tường ở nền; clip cuối 35 Kelly lao vào tường; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:143 · Kịch bản: "quay người rời khỏi cái xác và đi tiếp"; ảnh 1000 cái xác ở NỀN sau lưng → clip Kelly đi vào nền, VỀ PHÍA cái xác; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:144 · Kịch bản 26: Kelly bên trái, xác "phía trước" giữa-phải, cô "phát hiện" nó; ảnh 998 Kelly đi về phía máy, xác lơ lửng SAU LƯNG bên TRÁI → không thể "phát hiện phía trước"; 27 xác bên PHẢI → nhảy trục 26↔27; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:145 · Kịch bản: "bốn địch đứng tách biệt ở bốn góc xa", núp sau hàng rào cao; ảnh 994: bốn địch đứng gần nhau một hàng ở cuối, hàng rào trong thấp (G8 mô hình Kho #265); docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:565 · P2: Đạo diễn BYĐ phải chạy được qua `claude_cli`; docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:7 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0)

### kb.byd — BYĐ không hiện trên Dashboard

- Loại dòng: ô Dashboard
- Màu: đỏ
- Khâu liên quan: L3
- Phân loại: LOI, THIEU
- Lý do: thiếu bằng chứng: 'shot_intent.read(' trong dashboard/**/*.py
- Việc kế hoạch: M2.1 (✅), M4.7 (🔄)
- Lỗi đang mở: P31-G18 — BYĐ của shot mâu thuẫn trường khác của CHÍNH shot [OPEN] → M2.1, P31-G41 — Hướng chạy shot 35 ngược mạch: Kelly "chạy ra xa máy" vào nền, nơi có tường + tháp + địch (34: địch góc xa bên phải, tháp sau chúng) → chạy VỀ PHÍA địch, ngược "dựng keo định chuồn"; 36 lại chạy sang TRÁI khung → 35↔36 k [OPEN] → M3.3, P31-G43 — Kịch bản: "quay người rời khỏi cái xác và đi tiếp"; ảnh 1000 cái xác ở NỀN sau lưng → clip Kelly đi vào nền, VỀ PHÍA cái xác [IN_PROGRESS] → M3.3, P31-G44 — Kịch bản 26: Kelly bên trái, xác "phía trước" giữa-phải, cô "phát hiện" nó; ảnh 998 Kelly đi về phía máy, xác lơ lửng SAU LƯNG bên TRÁI → không thể "phát hiện phía trước"; 27 xác bên PHẢI → nhảy trục 26↔27 [OPEN] → M3.3, P31-G45 — Kịch bản: "bốn địch đứng tách biệt ở bốn góc xa", núp sau hàng rào cao; ảnh 994: bốn địch đứng gần nhau một hàng ở cuối, hàng rào trong thấp (G8 mô hình Kho #265) [OPEN] → M3.3, P31-G50 — 1017/1015 sai bố cục + phi thực tế: 17 Sứ giả đứng ngay đầu tường bắn thẳng vào Kelly (tường không chắn giữa), tường cong lồi ngược; 18 tường chắn ngang ở chỗ khác, Sứ giả đã gục từ đầu shot; hành lang bắc rộng 4 m = bề  [OPEN] → M3.3, P31-G9 — `shot_text_checks` khớp "whole body" trong câu tả SÚNG ("aura along its whole body") → chặn shot 17 [OPEN] → M2.7, P33-A12 — #33 không có BYĐ → `video_pregen` VÀNG "chưa có BYĐ" 22 lần, không kiểm được nhịp / khung cuối [OPEN] → M2.9, V31-GOC4 — BYĐ mâu thuẫn trường khác của shot / thiếu BYĐ [IN_PROGRESS] → M2.1
- Việc đề xuất thêm vào plan: **Tiếp tục M4.7 và chốt tiêu chí cho kb.byd**
- Khâu đề xuất: L3
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; sơ đồ đang đỏ; cần xác định và bổ sung nút, hàm hoặc bước kiểm còn thiếu; mã lỗi: P31-G18, P31-G41, P31-G43, P31-G44, P31-G45, P31-G50, P31-G9, P33-A12, V31-GOC4
- Bằng chứng: thiếu bằng chứng: 'shot_intent.read(' trong dashboard/**/*.py; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:73 · Shot 2: `byd.may.chuyen_dong = dung_yen` nhưng `camera_move = pan` + kịch bản "góc nhìn lia theo hướng quay" → mọi motion đều bị Tổ rà soát báo đỏ một phía. Không có kiểm code nào so BYĐ ↔ camera_move/action khi Đạo diễn khai; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:134 · shot 34 blocking; shot 35 blocking/motion "run away from camera", ảnh 976 tường ở nền; clip cuối 35 Kelly lao vào tường; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:143 · Kịch bản: "quay người rời khỏi cái xác và đi tiếp"; ảnh 1000 cái xác ở NỀN sau lưng → clip Kelly đi vào nền, VỀ PHÍA cái xác; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:144 · Kịch bản 26: Kelly bên trái, xác "phía trước" giữa-phải, cô "phát hiện" nó; ảnh 998 Kelly đi về phía máy, xác lơ lửng SAU LƯNG bên TRÁI → không thể "phát hiện phía trước"; 27 xác bên PHẢI → nhảy trục 26↔27; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:145 · Kịch bản: "bốn địch đứng tách biệt ở bốn góc xa", núp sau hàng rào cao; ảnh 994: bốn địch đứng gần nhau một hàng ở cuối, hàng rào trong thấp (G8 mô hình Kho #265); docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:565 · P2: Đạo diễn BYĐ phải chạy được qua `claude_cli`; docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:7 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0)

### kb.fixflags — 🩹 Bật cờ sửa lỗi · Bỏ qua có lý do

- Loại dòng: ô Dashboard
- Màu: xanh
- Khâu liên quan: L16
- Phân loại: LOI
- Lý do: có bằng chứng, việc kế hoạch xong
- Việc kế hoạch: M7.1 (✅)
- Lỗi đang mở: P31-G21 — Shot chèn tay không có BYĐ [OPEN] → M2.4, P31-G22 — BYĐ không cập nhật khi đổi nội dung shot [OPEN] → M2.2, P31-G34 — Job 1061/1062 (shot 30, 31 nhóm) kẹt `queued` từ 08:00 [OPEN] → M4.5, P31-G35 — Tổ rà soát tác động LỖI (Claude hết tiền) mà cổng giữ vẫn MỞ → job 1061 tự gửi ngay khi chưa được rà, trước khi kịp tạm dừng dự án [FIXED_UNVERIFIED] → M1.4, P31-G6 — Shot chèn tay (`llm_io.insert_scene_after`) không thừa kế bối cảnh [OPEN] → M2.4, P33-A2 — Vòng nền Tổ rà soát của Dashboard (anthropic hết tiền) chộp `change_events` pending → `failed` → giữ job [IN_PROGRESS] → M1.4, P33-A6 — Tổ rà soát báo nhầm shot 6 "không có video tham chiếu" (#877) [OPEN] → M4.5
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G21, P31-G22, P31-G34, P31-G35, P31-G6, P33-A2, P33-A6**
- Khâu đề xuất: L16
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G21, P31-G22, P31-G34, P31-G35, P31-G6, P33-A2, P33-A6
- Bằng chứng: có bằng chứng, việc kế hoạch xong; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:76 · S15–17: `video_pregen` VÀNG "chưa có BYĐ — chưa kiểm được nhịp đầu–đỉnh–cuối" (G6 mở rộng); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:77 · S18: BYĐ vẫn "Lính áo choàng đổi tư thế" sau khi đổi thành hạ Sứ giả; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:103 · `change_review_hold` ×221: motion mới bỏ tháp ("No tower is in this frame") nhưng mô tả shot 30 + `plate_view` landmark vẫn giữ Clock Tower; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:109 · `change_events` 1400/1403 state `failed` (LlmError hết tiền); `change_review.blocking` trả None; job 1061 running 03:38:13 → Seedance chặn real_person → retry 1073 (Kling); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:18 · Shot 15–17 chèn 18/10 thiếu `location_asset/location/time/weather/lighting/mood` → `place_refs.wants_render` = False ("không còn ở bối cảnh có mô hình 3D") → gói KHÔNG có nền 3D, chỉ ảnh Kho #265/#450 — im lặng; sau khi chép `location_asset` thì nền render ra day-clear (thiếu time/weather); docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:24 · tạm: Rà từng shot bằng `review_scene_now` + client claude_cli ngay sau khi đặt pending; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:28 · tạm: Đóng `dismissed` kèm lý do

### kb.dialogue — 🤖 Rà thoại · ↻ Chia shot lại cảnh

- Loại dòng: ô Dashboard
- Màu: vàng
- Khâu liên quan: L4
- Phân loại: LONG, KHONG_VIEC
- Lý do: lỏng: chỉ người / chỉ theo nút / bỏ qua được (mốc 17/10)
- Việc đề xuất thêm vào plan: **Bổ sung việc vào plan cho kb.dialogue**
- Khâu đề xuất: L4
- Lý do đề xuất: khâu đang vàng (chỉ người, cờ tắt hoặc thiếu bước kiểm tự động); khoảng trống hoặc lỗi chưa có việc kế hoạch được gắn trực tiếp
- Bằng chứng: lỏng: chỉ người / chỉ theo nút / bỏ qua được (mốc 17/10)

### kb.characters — Nhân vật: duyệt ảnh mốc · Lock · giọng

- Loại dòng: ô Dashboard
- Màu: xanh
- Khâu liên quan: L5
- Phân loại: LOI
- Lý do: có bằng chứng, việc kế hoạch xong
- Việc kế hoạch: M2.3 (✅)
- Lỗi đang mở: P31-G38 — Shot 35/36 tường keo đúng skin nhưng THẲNG hàng, không cong về phía người ném (`gloo-wall-curved` 14/10) — cả Kling lẫn Seedance [OPEN] → M2.3, P33-B1 — Ảnh mẫu thân dài (đầu ≈ 46 % thay vì ≈ 56 % như game), đầu đỏ/tím bẹt, màu áo sai mẫu [OPEN] → M2.3
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G38, P33-B1**
- Khâu đề xuất: L5
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G38, P33-B1
- Bằng chứng: có bằng chứng, việc kế hoạch xong; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:121 · cùng bảng; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:38 · đã xử lý trong dự án: Đo tỉ lệ ảnh góc → câu "1,8 đầu, đầu 55–58 %"; đỏ/tím lấy ảnh mẫu vàng làm ref dáng đầu; màu áo theo `các màu.png` (đỏ: áo trắng quần đỏ; tím: xanh dương đậm); xanh lơ không có ảnh áo → đổi sang vàng (đúng ảnh góc). GPT Image 2.5 vẫn kéo thân ~50 %

### kb.lock — ✔ Duyệt & khóa → Storyboard

- Loại dòng: ô Dashboard
- Màu: vàng
- Khâu liên quan: L5
- Phân loại: LOI, LONG, KHONG_VIEC
- Lý do: lỏng: chỉ người / chỉ theo nút / bỏ qua được (mốc 17/10)
- Lỗi đang mở: P31-G38 — Shot 35/36 tường keo đúng skin nhưng THẲNG hàng, không cong về phía người ném (`gloo-wall-curved` 14/10) — cả Kling lẫn Seedance [OPEN] → M2.3, P33-B1 — Ảnh mẫu thân dài (đầu ≈ 46 % thay vì ≈ 56 % như game), đầu đỏ/tím bẹt, màu áo sai mẫu [OPEN] → M2.3
- Việc đề xuất thêm vào plan: **Bổ sung việc vào plan cho kb.lock**
- Khâu đề xuất: L5
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; khâu đang vàng (chỉ người, cờ tắt hoặc thiếu bước kiểm tự động); khoảng trống hoặc lỗi chưa có việc kế hoạch được gắn trực tiếp; mã lỗi: P31-G38, P33-B1
- Bằng chứng: lỏng: chỉ người / chỉ theo nút / bỏ qua được (mốc 17/10); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:121 · cùng bảng; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:38 · đã xử lý trong dự án: Đo tỉ lệ ảnh góc → câu "1,8 đầu, đầu 55–58 %"; đỏ/tím lấy ảnh mẫu vàng làm ref dáng đầu; màu áo theo `các màu.png` (đỏ: áo trắng quần đỏ; tím: xanh dương đậm); xanh lơ không có ảnh áo → đổi sang vàng (đúng ảnh góc). GPT Image 2.5 vẫn kéo thân ~50 %

### sb.stage3d — Sân khấu 3D: KHÔNG có nút

- Loại dòng: ô Dashboard
- Màu: tím
- Khâu liên quan: L6
- Phân loại: LOI
- Lý do: việc M4.8 đang làm
- Việc kế hoạch: M4.8 (🔄)
- Lỗi đang mở: P31-G1 — Khối giữ chỗ của sân khấu 3D bị mang sang cảnh khác [IN_PROGRESS] → M2.4, P31-G2 — Nền 3D không có mốc tỉ lệ người [OPEN] → M3.2, P31-G3 — Máy góc 'eye' mà ngước/chúi lớn, không kiểm nền bị tường che [IN_PROGRESS] → M3.2, P31-G46 — vị trí vật/nhân vật xuyên các shot liên quan (xác 26–29, keo + địch 34–38, mê cung 14) chỉ tả bằng chữ riêng từng shot; mỗi ảnh gen độc lập → model đặt lại mỗi lần; vá chữ shot này làm lệch shot kia (vd sửa 29 "tháp trái [IN_PROGRESS] → M3.1, P31-G47 — toạ độ chỗ đứng thật (stage inputs doan_4): shot 13 Kelly ở tâm (0,55; 0,1); 15–18 Kelly ở `me_cung_nga_re_bac` (−0,1; 14,3) = hành lang ngoài phía BẮC; 19 ở `me_cung_khe_tay` (−14,3; −0,1); biệt thự (mốc PKK_OUT_Buildin [OPEN] → M3.1, P31-G49 — "dưới chân Kelly có bậc cỏ cao tới đầu gối, mê cung làm gì có"): grid 3D tâm mê cung: ô cỏ (Fence001) cao hơn lối đi chỉ 0,13 m. Máy 16/10 của shot 13 đứng gần trên ô cỏ, cao 1,9 m, cúi −27°, cách Kelly 0,9 m (Tổ rà soát [OPEN] → M3.2, P31-G8 — Mô hình 3D Kho #265 hàng rào thấp ≈ 1,5 m → nhìn qua thấy nhiều lớp rào [FIXED_UNVERIFIED] → M3.2, P33-A10 — Góc `high` của plate cố định chúc 30° (`plate_camera.HIGH_TILT_DEG`) → nền chỉ còn sàn đá [IN_PROGRESS] → M3.2, P33-B4 — Nền ghép "như dán đè ảnh 3D" [OPEN] → M3.1, P33-B5 — Góc in-game chuẩn = máy thấp ở thềm nhìn lên cầu thang, tháp TRÁI bị cắt đỉnh; đổi sang EWS cho thấy đỉnh tháp là SAI bố cục [OPEN] → M3.2, V31-GOC1 — Vị trí vật/nhân vật không có MỘT nguồn sự thật xuyên shot [IN_PROGRESS] → M3.1, V31-GOC2 — Hình học máy ↔ người ↔ sàn bằng hằng số / chữ thay vì đo [IN_PROGRESS] → M3.2, V31-GOC5 — Kho: vật một dạng, tỉ lệ mô hình, nền ghép [OPEN] → M3.2
- Việc đề xuất thêm vào plan: **Tiếp tục M4.8 và chốt tiêu chí cho sb.stage3d**
- Khâu đề xuất: L6
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G1, P31-G2, P31-G3, P31-G46, P31-G47, P31-G49, P31-G8, P33-A10, P33-B4, P33-B5, V31-GOC1, V31-GOC2, V31-GOC5
- Bằng chứng: việc M4.8 đang làm; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:12 · `stage_camera.props` = trụ Ø0,5×1,75 m nhãn "XÁC ĐEN BIẾT BAY" (dàn cảnh cảnh 6) có ở shot 28/30 (`source: "cảnh 6 (cùng sân khấu)"`) và 34/35 (`"cảnh 7 (cùng sân khấu)"`), kể cả cảnh 8 = thế giới THỰC TẠI ban ngày (không có quái). Khối render vào nền (`plate.png`) → model vẽ thành cột đá; D6 shot 3; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:13 · Nền render trống người; cỡ người chỉ do câu % khung trong prompt (vd shot 23 *"her whole body about 60% of frame height … never resize her smaller for distance"*) — không ràng theo khoảng cách 3D. Shot 35 địch to như khổng lồ; shot 14 máy cao 3,6 m chúi −18° (meta `pitch_deg -18.2`) → hàng rào trông; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:14 · Shot 28 `angle: eye` nhưng máy thấp hơn cảnh 0,56 m (z 10,85 vs 11,41), meta `pitch_deg +17.3` → nền gần như chỉ tường trống, model tự bịa; shot 35 `pitch +11.1`; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:26 · G8 (xác nhận 18/10 bằng video in-game người dùng gửi `ScreenRecording_10-17-2026_08-33-20_1.mov`): trong game, hàng rào BÊN; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:32 · tạm: Dùng `eye` (máy ngang mắt người lớn ≈ chúc 5–10° xuống con rối chibi); docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:41 · đã xử lý trong dự án: Chuyển màu Lab theo ảnh in-game người dùng (`goc_chup_ingame_chuan.png`), mây in-game + vệt gió + sương theo `depth.png`, quầng đỏ sẫm; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:42 · đã xử lý trong dự án: Về WS góc thấp; docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:4 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0); docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:5 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0); docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:8 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0)

### sb.replate — ↻ Render lại nền 3D shot N · 0 USD

- Loại dòng: ô Dashboard
- Màu: xanh
- Khâu liên quan: L6
- Phân loại: LOI
- Lý do: có bằng chứng
- Lỗi đang mở: P31-G1 — Khối giữ chỗ của sân khấu 3D bị mang sang cảnh khác [IN_PROGRESS] → M2.4, P31-G2 — Nền 3D không có mốc tỉ lệ người [OPEN] → M3.2, P31-G3 — Máy góc 'eye' mà ngước/chúi lớn, không kiểm nền bị tường che [IN_PROGRESS] → M3.2, P31-G46 — vị trí vật/nhân vật xuyên các shot liên quan (xác 26–29, keo + địch 34–38, mê cung 14) chỉ tả bằng chữ riêng từng shot; mỗi ảnh gen độc lập → model đặt lại mỗi lần; vá chữ shot này làm lệch shot kia (vd sửa 29 "tháp trái [IN_PROGRESS] → M3.1, P31-G47 — toạ độ chỗ đứng thật (stage inputs doan_4): shot 13 Kelly ở tâm (0,55; 0,1); 15–18 Kelly ở `me_cung_nga_re_bac` (−0,1; 14,3) = hành lang ngoài phía BẮC; 19 ở `me_cung_khe_tay` (−14,3; −0,1); biệt thự (mốc PKK_OUT_Buildin [OPEN] → M3.1, P31-G49 — "dưới chân Kelly có bậc cỏ cao tới đầu gối, mê cung làm gì có"): grid 3D tâm mê cung: ô cỏ (Fence001) cao hơn lối đi chỉ 0,13 m. Máy 16/10 của shot 13 đứng gần trên ô cỏ, cao 1,9 m, cúi −27°, cách Kelly 0,9 m (Tổ rà soát [OPEN] → M3.2, P31-G8 — Mô hình 3D Kho #265 hàng rào thấp ≈ 1,5 m → nhìn qua thấy nhiều lớp rào [FIXED_UNVERIFIED] → M3.2, P33-A10 — Góc `high` của plate cố định chúc 30° (`plate_camera.HIGH_TILT_DEG`) → nền chỉ còn sàn đá [IN_PROGRESS] → M3.2, P33-B4 — Nền ghép "như dán đè ảnh 3D" [OPEN] → M3.1, P33-B5 — Góc in-game chuẩn = máy thấp ở thềm nhìn lên cầu thang, tháp TRÁI bị cắt đỉnh; đổi sang EWS cho thấy đỉnh tháp là SAI bố cục [OPEN] → M3.2, V31-GOC1 — Vị trí vật/nhân vật không có MỘT nguồn sự thật xuyên shot [IN_PROGRESS] → M3.1, V31-GOC2 — Hình học máy ↔ người ↔ sàn bằng hằng số / chữ thay vì đo [IN_PROGRESS] → M3.2, V31-GOC5 — Kho: vật một dạng, tỉ lệ mô hình, nền ghép [OPEN] → M3.2
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G1, P31-G2, P31-G3, P31-G46, P31-G47, P31-G49, P31-G8, P33-A10, P33-B4, P33-B5, V31-GOC1, V31-GOC2, V31-GOC5**
- Khâu đề xuất: L6
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G1, P31-G2, P31-G3, P31-G46, P31-G47, P31-G49, P31-G8, P33-A10, P33-B4, P33-B5, V31-GOC1, V31-GOC2, V31-GOC5
- Bằng chứng: có bằng chứng; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:12 · `stage_camera.props` = trụ Ø0,5×1,75 m nhãn "XÁC ĐEN BIẾT BAY" (dàn cảnh cảnh 6) có ở shot 28/30 (`source: "cảnh 6 (cùng sân khấu)"`) và 34/35 (`"cảnh 7 (cùng sân khấu)"`), kể cả cảnh 8 = thế giới THỰC TẠI ban ngày (không có quái). Khối render vào nền (`plate.png`) → model vẽ thành cột đá; D6 shot 3; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:13 · Nền render trống người; cỡ người chỉ do câu % khung trong prompt (vd shot 23 *"her whole body about 60% of frame height … never resize her smaller for distance"*) — không ràng theo khoảng cách 3D. Shot 35 địch to như khổng lồ; shot 14 máy cao 3,6 m chúi −18° (meta `pitch_deg -18.2`) → hàng rào trông; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:14 · Shot 28 `angle: eye` nhưng máy thấp hơn cảnh 0,56 m (z 10,85 vs 11,41), meta `pitch_deg +17.3` → nền gần như chỉ tường trống, model tự bịa; shot 35 `pitch +11.1`; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:26 · G8 (xác nhận 18/10 bằng video in-game người dùng gửi `ScreenRecording_10-17-2026_08-33-20_1.mov`): trong game, hàng rào BÊN; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:32 · tạm: Dùng `eye` (máy ngang mắt người lớn ≈ chúc 5–10° xuống con rối chibi); docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:41 · đã xử lý trong dự án: Chuyển màu Lab theo ảnh in-game người dùng (`goc_chup_ingame_chuan.png`), mây in-game + vệt gió + sương theo `depth.png`, quầng đỏ sẫm; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:42 · đã xử lý trong dự án: Về WS góc thấp; docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:4 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0); docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:5 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0); docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:8 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0)

### sb.package — Xem GÓI trước khi gửi: KHÔNG có

- Loại dòng: ô Dashboard
- Màu: tím
- Khâu liên quan: L8
- Phân loại: LOI
- Lý do: việc M4.7 đang làm
- Việc kế hoạch: M4.7 (🔄)
- Lỗi đang mở: P31-G4 — Chọn ảnh Kho bằng dò bí danh trong chữ, không đọc BYĐ [OPEN] → M2.2, P31-G5 — Sổ gói ghi nhãn ảnh sai [OPEN] → M2.6, P31-G7 — Shot POV bỏ ảnh súng [FIXED_UNVERIFIED] → M2.7, P33-B3 — Tả bằng chữ "mắt xoáy ngay trên đỉnh tháp" → model dời tháp ra giữa [OPEN] → M3.3
- Việc đề xuất thêm vào plan: **Tiếp tục M4.7 và chốt tiêu chí cho sb.package**
- Khâu đề xuất: L8
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G4, P31-G5, P31-G7, P33-B3
- Bằng chứng: việc M4.7 đang làm; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:15 · `core/assets.py:_named_extras` (1815–1855) khớp `names_of(a)` trong text + image_prompt. Bí danh #443 = *"flying black corpse, floating corpse, levitating corpse, cái xác biết bay"*. Phiên này bỏ "floating corpse" khỏi prompt shot 23 (để qua bộ lọc OpenAI) → job 993 KHÔNG gửi ảnh #443 (job 967 trước; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:16 · `core/sent_package.py:124 _meta_index` khóa theo basename — Kho đặt tên `1.png/2.png/3.png` ở mọi mục → ảnh #443/2.png ghi nhãn "SKORP", #367/2.png ghi "SKORP", #425/3.png ghi "KELLY". Prompt gửi model vẫn ĐÚNG (shot 24: *"Image 5 is the object XÁC ĐEN BIẾT BAY"*) — chỉ sổ sai; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:19 · `core/assets.py:1830` bỏ ref súng khi `prop_lock.is_pov` (luật #27 "FF không có POV cầm súng") → shot 15 POV bắn: model vẽ súng đen thường, mất hào quang đỏ. 16/17 có ref SKORP (#433/2.png là SKORP đen) nhưng câu prompt chỉ ghi "red-glowing" ngắn → màu đỏ yếu/mất; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:40 · đã xử lý trong dự án: Vị trí đặt bằng nền 3D, không bằng prompt: ghép trời in-game vào plate (alpha `raw.png`, mắt xoáy đặt theo đỉnh tháp đo trên ảnh) — script scratchpad `p33_sky_composite3.py`

### sb.pregate — Cổng trước gen: ⚠ lưu ý (ẩn trong ⓘ)

- Loại dòng: ô Dashboard
- Màu: xanh
- Khâu liên quan: L8
- Phân loại: LOI
- Lý do: có bằng chứng, việc kế hoạch xong
- Việc kế hoạch: M2.7 (✅)
- Lỗi đang mở: P31-G4 — Chọn ảnh Kho bằng dò bí danh trong chữ, không đọc BYĐ [OPEN] → M2.2, P31-G5 — Sổ gói ghi nhãn ảnh sai [OPEN] → M2.6, P31-G7 — Shot POV bỏ ảnh súng [FIXED_UNVERIFIED] → M2.7, P33-B3 — Tả bằng chữ "mắt xoáy ngay trên đỉnh tháp" → model dời tháp ra giữa [OPEN] → M3.3
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G4, P31-G5, P31-G7, P33-B3**
- Khâu đề xuất: L8
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G4, P31-G5, P31-G7, P33-B3
- Bằng chứng: có bằng chứng, việc kế hoạch xong; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:15 · `core/assets.py:_named_extras` (1815–1855) khớp `names_of(a)` trong text + image_prompt. Bí danh #443 = *"flying black corpse, floating corpse, levitating corpse, cái xác biết bay"*. Phiên này bỏ "floating corpse" khỏi prompt shot 23 (để qua bộ lọc OpenAI) → job 993 KHÔNG gửi ảnh #443 (job 967 trước; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:16 · `core/sent_package.py:124 _meta_index` khóa theo basename — Kho đặt tên `1.png/2.png/3.png` ở mọi mục → ảnh #443/2.png ghi nhãn "SKORP", #367/2.png ghi "SKORP", #425/3.png ghi "KELLY". Prompt gửi model vẫn ĐÚNG (shot 24: *"Image 5 is the object XÁC ĐEN BIẾT BAY"*) — chỉ sổ sai; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:19 · `core/assets.py:1830` bỏ ref súng khi `prop_lock.is_pov` (luật #27 "FF không có POV cầm súng") → shot 15 POV bắn: model vẽ súng đen thường, mất hào quang đỏ. 16/17 có ref SKORP (#433/2.png là SKORP đen) nhưng câu prompt chỉ ghi "red-glowing" ngắn → màu đỏ yếu/mất; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:40 · đã xử lý trong dự án: Vị trí đặt bằng nền 3D, không bằng prompt: ghép trời in-game vào plate (alpha `raw.png`, mắt xoáy đặt theo đỉnh tháp đo trên ảnh) — script scratchpad `p33_sky_composite3.py`

### sb.gen — ▶ Gen ảnh các cảnh chưa có / đã cũ · $

- Loại dòng: ô Dashboard
- Màu: xanh
- Khâu liên quan: L9
- Phân loại: LOI
- Lý do: có bằng chứng
- Lỗi đang mở: P31-G19 — Ảnh khung đầu vẽ trạng thái CUỐI thay vì ĐẦU của shot [OPEN] → M2.7, P31-G40 — ảnh khung đầu đã duyệt 1000 vốn KHÔNG có trời và KHÔNG có tháp (tường sương dày) dù image_prompt ghi "tower visible in the background"; motion đòi trời nhưng Seedance bám ảnh. Thêm: shot 29 là shot 2 của nhóm nên clip kh [OPEN] → M3.3, P31-G48 — ảnh 1090 vẽ tường thành khối hộp hai mặt vuông góc, khác tấm cong ở 35 (1094) → chữ 36: "SAME curved wall … ONE thin continuous curved panel … never a box". [OPEN] → M3.4, P33-A5 — QC lớp 0 đo nhầm cỡ cảnh ảnh S2 (bố cục sau lưng nhóm: đo mặt con tím ở xa → "WS, shot xin MS") → tự tạo job gen lại ép "từ thắt lưng trở lên" [FIXED_UNVERIFIED] → M4.5
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G19, P31-G40, P31-G48, P33-A5**
- Khâu đề xuất: L9
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G19, P31-G40, P31-G48, P33-A5
- Bằng chứng: có bằng chứng; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:74 · Shot 1, 2: ảnh đã thấy 2 cửa trong khi shot là "quay người dần lộ 2 cửa"; shot 4: ý đồ qua vai thấy 2 cửa, ảnh không thấy. Gốc: prompt ảnh tả cả hành động ("camera turning to reveal two doors") → model vẽ kết quả. Liên quan G11; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:27 · tạm: Hủy job tự gen, đổi size shot sang WS

### sb.card — Thẻ ảnh: ✔ Duyệt · ✖ Loại & gen lại

- Loại dòng: ô Dashboard
- Màu: xanh
- Khâu liên quan: L9, L10
- Phân loại: LOI
- Lý do: có bằng chứng
- Lỗi đang mở: P31-G19 — Ảnh khung đầu vẽ trạng thái CUỐI thay vì ĐẦU của shot [OPEN] → M2.7, P31-G40 — ảnh khung đầu đã duyệt 1000 vốn KHÔNG có trời và KHÔNG có tháp (tường sương dày) dù image_prompt ghi "tower visible in the background"; motion đòi trời nhưng Seedance bám ảnh. Thêm: shot 29 là shot 2 của nhóm nên clip kh [OPEN] → M3.3, P31-G48 — ảnh 1090 vẽ tường thành khối hộp hai mặt vuông góc, khác tấm cong ở 35 (1094) → chữ 36: "SAME curved wall … ONE thin continuous curved panel … never a box". [OPEN] → M3.4, P33-A4 — Đạo diễn (director_rewrite, chạy claude_cli) tự viết lại image_prompt shot 1–3 khi loại ảnh, ép thấy đỉnh tháp + xoáy → ảnh bản 3 dời tháp vào giữa, thêm mặt đồng hồ [OPEN] → M2.5, P33-A5 — QC lớp 0 đo nhầm cỡ cảnh ảnh S2 (bố cục sau lưng nhóm: đo mặt con tím ở xa → "WS, shot xin MS") → tự tạo job gen lại ép "từ thắt lưng trở lên" [FIXED_UNVERIFIED] → M4.5
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G19, P31-G40, P31-G48, P33-A4, P33-A5**
- Khâu đề xuất: L9
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G19, P31-G40, P31-G48, P33-A4, P33-A5
- Bằng chứng: có bằng chứng; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:74 · Shot 1, 2: ảnh đã thấy 2 cửa trong khi shot là "quay người dần lộ 2 cửa"; shot 4: ý đồ qua vai thấy 2 cửa, ảnh không thấy. Gốc: prompt ảnh tả cả hành động ("camera turning to reveal two doors") → model vẽ kết quả. Liên quan G11; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:26 · tạm: Khôi phục prompt từ sao lưu; tắt `director_rewrite` + `chat_prompts` CHỈ trong tiến trình gen; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:27 · tạm: Hủy job tự gen, đổi size shot sang WS

### sb.motion — 🤖 Viết motion · 🔍 Rà motion

- Loại dòng: ô Dashboard
- Màu: vàng
- Khâu liên quan: L11
- Phân loại: LOI, LONG, KHONG_VIEC
- Lý do: lỏng: chỉ người / chỉ theo nút / bỏ qua được (mốc 17/10)
- Lỗi đang mở: P31-G11 — Motion prompt mô tả cảnh khác khung đầu (ảnh đã duyệt) [OPEN] → M2.9, P31-G26 — Câu chữ nói "nhìn về tháp" nhưng máy 3D của shot quay về phía khác → model tự vẽ tháp sai chỗ [OPEN] → M3.3, P33-B10 — Chữ "cats" trong motion ngoài câu chặn → nguy cơ vẽ mèo (Tổ rà soát bắt) [OPEN] → M2.8, P33-B7 — Cổng video chặn: motion còn tiếng Việt (tên RỐI … có dấu, "Tháp Đồng Hồ") [OPEN] → M2.8, V31-GOC3 — Chữ viết tự do không khớp cái máy 3D thấy [IN_PROGRESS] → M3.3
- Việc đề xuất thêm vào plan: **Bổ sung việc vào plan cho sb.motion**
- Khâu đề xuất: L11
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; khâu đang vàng (chỉ người, cờ tắt hoặc thiếu bước kiểm tự động); khoảng trống hoặc lỗi chưa có việc kế hoạch được gắn trực tiếp; mã lỗi: P31-G11, P31-G26, P33-B10, P33-B7, V31-GOC3
- Bằng chứng: lỏng: chỉ người / chỉ theo nút / bỏ qua được (mốc 17/10); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:59 · Shot 2: motion "chưa thấy cửa, quay mới lộ" — ảnh 987 đã thấy 2 cửa; shot 4: "2 cửa phía trước" — ảnh 948 là tường kệ sách; shot 35/36: "tường keo cong" — ảnh tường thẳng. Claude viết motion bám chữ kịch bản hơn ảnh, không có kiểm code nào so motion ↔ khung đầu; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:87 · S31: nền 3D là tường / lan can không có tháp; motion + D6 viết "the tower rising in the background" → clip có tháp đen ở chỗ không có; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:47 · đã xử lý trong dự án: Đổi "like the reference video"; giữ câu chặn "the cats in the reference only give the motion…"; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:44 · đã xử lý trong dự án: Tên không dấu (ROI DO A…) + "the Clock Tower"; docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:6 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0)

### sb.voice — 🎙 Tạo giọng · 🎧 Kiểm giọng · 0 USD

- Loại dòng: ô Dashboard
- Màu: xanh
- Khâu liên quan: L14
- Phân loại: LOI
- Lý do: có bằng chứng
- Lỗi đang mở: P31-G14 — Nút "⏱ Đặt thời lượng theo giọng thật" kéo dài MỌI shot có lời dẫn [OPEN] → M2.9, P31-G42 — Lời dẫn đi trước hình: shot 36 đọc "…tụi nó thì đứng cười hở nách ăn mừng" khi Kelly còn chạy; ngã ở 37, ăn mừng ở 38 (38 không có lời) [OPEN] → M4.3
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G14, P31-G42**
- Khâu đề xuất: L14
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G14, P31-G42
- Bằng chứng: có bằng chứng; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:62 · `voice.fit_durations` kéo 17 shot (S10 1,3→8 s, S24 1→7 s) — đổi nhịp phim + tăng tiền video, không hỏi; chỉ 3 shot (6, 12, 31) thật sự bị chặn đỏ; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:135 · dialogue 36/38

### sb.approve — ✔ Duyệt storyboard → gửi video

- Loại dòng: ô Dashboard
- Màu: xanh
- Khâu liên quan: L9
- Phân loại: LOI
- Lý do: có bằng chứng
- Lỗi đang mở: P31-G19 — Ảnh khung đầu vẽ trạng thái CUỐI thay vì ĐẦU của shot [OPEN] → M2.7, P31-G40 — ảnh khung đầu đã duyệt 1000 vốn KHÔNG có trời và KHÔNG có tháp (tường sương dày) dù image_prompt ghi "tower visible in the background"; motion đòi trời nhưng Seedance bám ảnh. Thêm: shot 29 là shot 2 của nhóm nên clip kh [OPEN] → M3.3, P31-G48 — ảnh 1090 vẽ tường thành khối hộp hai mặt vuông góc, khác tấm cong ở 35 (1094) → chữ 36: "SAME curved wall … ONE thin continuous curved panel … never a box". [OPEN] → M3.4, P33-A5 — QC lớp 0 đo nhầm cỡ cảnh ảnh S2 (bố cục sau lưng nhóm: đo mặt con tím ở xa → "WS, shot xin MS") → tự tạo job gen lại ép "từ thắt lưng trở lên" [FIXED_UNVERIFIED] → M4.5
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G19, P31-G40, P31-G48, P33-A5**
- Khâu đề xuất: L9
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G19, P31-G40, P31-G48, P33-A5
- Bằng chứng: có bằng chứng; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:74 · Shot 1, 2: ảnh đã thấy 2 cửa trong khi shot là "quay người dần lộ 2 cửa"; shot 4: ý đồ qua vai thấy 2 cửa, ảnh không thấy. Gốc: prompt ảnh tả cả hành động ("camera turning to reveal two doors") → model vẽ kết quả. Liên quan G11; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:27 · tạm: Hủy job tự gen, đổi size shot sang WS

### vd.model — Dùng đề xuất model theo cảnh

- Loại dòng: ô Dashboard
- Màu: xanh
- Khâu liên quan: L12
- Phân loại: LOI
- Lý do: có bằng chứng, việc kế hoạch xong
- Việc kế hoạch: M2.8 (✅)
- Lỗi đang mở: P31-G10 — Lời người dẫn chuyện (LỜI DẪN) bị coi là lời thoại phải KHỚP MÔI [FIXED_UNVERIFIED] → M2.9, P31-G12 — Tên địa danh có dấu trong câu tiếng Anh làm chặn gói [OPEN] → M2.8, P31-G13 — Gói nhóm vượt 5000 ký tự [OPEN] → M2.8, P31-G23 — Công cụ kiểm gói video thiếu [OPEN] → M1.9, P31-G24 — 7 shot cận (9, 10, 12, 19, 24, 28, 32) đi Kling trái quyết định `video-route-2026-10-13` ("video hết Seedance 2.5, Kling chỉ đường lùi") [FIXED_UNVERIFIED] → M2.8, P31-G27 — Gói VIDEO chỉ gửi 1 ảnh khuôn mặt mỗi nhân vật — không gửi ảnh DẠNG (bóng mờ, Kho #427) và không gửi ảnh VẬT Kho (Bom keo skin thang máy #367, SKORP #433, XÁC ĐEN #443), trong khi gói ẢNH có đủ [FIXED_UNVERIFIED] → M2.3, P31-G29 — Bước kiểm gói của phiên này bỏ qua D6 (chat_prompts BẬT ở máy chính: Claude viết lại prompt video lúc gửi) và không đối chiếu ảnh cần (dạng/vật) với "Image N" trong prompt [OPEN] → M1.9, P31-G30 — Kho chủ thể ClipAI đầy 100/100 → ảnh không tải lên, gửi ảnh đánh dấu [FIXED_UNVERIFIED] → M1.5, P31-G53 — `speaker_no_identity` vẫn báo cho LỜI DẪN tới 19/10 13:52 (sau sửa G10 ngày 18/10) — `core/seedance_refs.py:546` chưa bỏ người dẫn chuyện [OPEN] → M2.9, P31-G54 — Trần độ dài prompt chặn câu cần thiết: D6 bị từ chối (3256 > 3192; 4096 > 4000), `gore_restraint` "không thêm được câu … quá 4000 ký tự" [OPEN] → M2.8, P31-G58 — Kho chủ thể đầy lặp lại ở #33 (13 lần, 20/10) — G30 chưa sửa nên dự án sau gặp lại [FIXED_UNVERIFIED] → M1.5, P33-B8 — Seedance ref-only chép cả đoạn chuyển cảnh đầu đoạn ref: lộ con mèo (S5), góc trống (S6), mở bằng một con ở xa (S4) [OPEN] → M2.8
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G10, P31-G12, P31-G13, P31-G23, P31-G24, P31-G27, P31-G29, P31-G30, P31-G53, P31-G54, P31-G58, P33-B8**
- Khâu đề xuất: L12
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G10, P31-G12, P31-G13, P31-G23, P31-G24, P31-G27, P31-G29, P31-G30, P31-G53, P31-G54, P31-G58, P33-B8
- Bằng chứng: có bằng chứng, việc kế hoạch xong; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:58 · `core/lipsync.py:_method` so người nói với `characters`; shot POV không có cast → điều kiện "người nói ngoài khung" không bao giờ đúng → "post" → (cờ dialogue_take) "take" → gói nhóm S01–S03, S05–S06 ghi *"LOI DAN speak Audio1… Sync the mouth, jaw…"* + gửi reference_audio. Model có thể vẽ thêm người; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:60 · "the Cổng Trời hedge maze" (S05), "LỜI DẪN narrates" (S39) → `lint` "prompt còn chữ tiếng Việt" chặn cả clip nhóm. Motion writer không được dặn viết tên riêng không dấu; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:61 · S01–S03 = 5173 ký tự: motion mỗi shot có câu giải thích "because…" (viết cho người đọc), khối khớp môi G10 cộng thêm; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:78 · Phải viết script tạm (thư mục thử + provider giả có chữ ký ClipAI) mới thấy G10–G13; sổ gói ghi `reference_only` không nhãn; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:79 · `core/model_router.py` nhánh `seedance_refs` (chỉ chạy khi `FEATURE_SEEDANCE_REF_GROUPS=1` — cờ nằm trong `dashboard.env`): shot cận thấy mặt không vào nhóm tham chiếu → cờ `closeup_start_frame` (S4.1, 29/09, `verified: False`) → Kling từ khung đầu, TRƯỚC luật E1 (E1 chỉ đổi model họ Seedance). Chạy; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:85 · `core/seedance_refs.py:314 identity_pictures`: lấy ảnh danh tính (Kelly = ảnh áo vàng 23/10.png) + bỏ ảnh trang phục khi nhân vật ở dạng, KHÔNG thêm ảnh dạng; không có nhánh ảnh vật. Gói thật job 1045 (S28–29): "Image 3 is Kelly: identity only — NOT the clothes … ghost form" + ảnh áo vàng → cận mặt; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:89 · Script chạy thử tắt D6 như replay_payload; phiên đọc danh sách ảnh của sổ gói (có dạng/vật) thay vì ánh xạ Image N (không có) — bỏ sót G27; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:90 · diag `subjects` jobs 1047, 1049–1051, 1054 (code 1110); docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:558 · N6 (dùng `speaker_lint.is_narrator`); docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:559 · N4 cùng G13: ngân sách ký tự theo khối, ưu tiên câu bắt buộc; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:563 · N1 (G30); docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:45 · đã xử lý trong dự án: Cắt đầu clip khi dựng; S4/S6 làm file ref mới: thay khúc chuyển cảnh bằng khung đội hình tua ngược, giữ độ dài/nhịp nhạc

### vd.package — Xem GÓI video trước khi gửi: KHÔNG

- Loại dòng: ô Dashboard
- Màu: tím
- Khâu liên quan: L12
- Phân loại: LOI
- Lý do: việc M4.7 đang làm
- Việc kế hoạch: M4.7 (🔄)
- Lỗi đang mở: P31-G10 — Lời người dẫn chuyện (LỜI DẪN) bị coi là lời thoại phải KHỚP MÔI [FIXED_UNVERIFIED] → M2.9, P31-G12 — Tên địa danh có dấu trong câu tiếng Anh làm chặn gói [OPEN] → M2.8, P31-G13 — Gói nhóm vượt 5000 ký tự [OPEN] → M2.8, P31-G23 — Công cụ kiểm gói video thiếu [OPEN] → M1.9, P31-G24 — 7 shot cận (9, 10, 12, 19, 24, 28, 32) đi Kling trái quyết định `video-route-2026-10-13` ("video hết Seedance 2.5, Kling chỉ đường lùi") [FIXED_UNVERIFIED] → M2.8, P31-G27 — Gói VIDEO chỉ gửi 1 ảnh khuôn mặt mỗi nhân vật — không gửi ảnh DẠNG (bóng mờ, Kho #427) và không gửi ảnh VẬT Kho (Bom keo skin thang máy #367, SKORP #433, XÁC ĐEN #443), trong khi gói ẢNH có đủ [FIXED_UNVERIFIED] → M2.3, P31-G29 — Bước kiểm gói của phiên này bỏ qua D6 (chat_prompts BẬT ở máy chính: Claude viết lại prompt video lúc gửi) và không đối chiếu ảnh cần (dạng/vật) với "Image N" trong prompt [OPEN] → M1.9, P31-G30 — Kho chủ thể ClipAI đầy 100/100 → ảnh không tải lên, gửi ảnh đánh dấu [FIXED_UNVERIFIED] → M1.5, P31-G53 — `speaker_no_identity` vẫn báo cho LỜI DẪN tới 19/10 13:52 (sau sửa G10 ngày 18/10) — `core/seedance_refs.py:546` chưa bỏ người dẫn chuyện [OPEN] → M2.9, P31-G54 — Trần độ dài prompt chặn câu cần thiết: D6 bị từ chối (3256 > 3192; 4096 > 4000), `gore_restraint` "không thêm được câu … quá 4000 ký tự" [OPEN] → M2.8, P31-G58 — Kho chủ thể đầy lặp lại ở #33 (13 lần, 20/10) — G30 chưa sửa nên dự án sau gặp lại [FIXED_UNVERIFIED] → M1.5, P33-B8 — Seedance ref-only chép cả đoạn chuyển cảnh đầu đoạn ref: lộ con mèo (S5), góc trống (S6), mở bằng một con ở xa (S4) [OPEN] → M2.8
- Việc đề xuất thêm vào plan: **Tiếp tục M4.7 và chốt tiêu chí cho vd.package**
- Khâu đề xuất: L12
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G10, P31-G12, P31-G13, P31-G23, P31-G24, P31-G27, P31-G29, P31-G30, P31-G53, P31-G54, P31-G58, P33-B8
- Bằng chứng: việc M4.7 đang làm; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:58 · `core/lipsync.py:_method` so người nói với `characters`; shot POV không có cast → điều kiện "người nói ngoài khung" không bao giờ đúng → "post" → (cờ dialogue_take) "take" → gói nhóm S01–S03, S05–S06 ghi *"LOI DAN speak Audio1… Sync the mouth, jaw…"* + gửi reference_audio. Model có thể vẽ thêm người; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:60 · "the Cổng Trời hedge maze" (S05), "LỜI DẪN narrates" (S39) → `lint` "prompt còn chữ tiếng Việt" chặn cả clip nhóm. Motion writer không được dặn viết tên riêng không dấu; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:61 · S01–S03 = 5173 ký tự: motion mỗi shot có câu giải thích "because…" (viết cho người đọc), khối khớp môi G10 cộng thêm; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:78 · Phải viết script tạm (thư mục thử + provider giả có chữ ký ClipAI) mới thấy G10–G13; sổ gói ghi `reference_only` không nhãn; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:79 · `core/model_router.py` nhánh `seedance_refs` (chỉ chạy khi `FEATURE_SEEDANCE_REF_GROUPS=1` — cờ nằm trong `dashboard.env`): shot cận thấy mặt không vào nhóm tham chiếu → cờ `closeup_start_frame` (S4.1, 29/09, `verified: False`) → Kling từ khung đầu, TRƯỚC luật E1 (E1 chỉ đổi model họ Seedance). Chạy; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:85 · `core/seedance_refs.py:314 identity_pictures`: lấy ảnh danh tính (Kelly = ảnh áo vàng 23/10.png) + bỏ ảnh trang phục khi nhân vật ở dạng, KHÔNG thêm ảnh dạng; không có nhánh ảnh vật. Gói thật job 1045 (S28–29): "Image 3 is Kelly: identity only — NOT the clothes … ghost form" + ảnh áo vàng → cận mặt; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:89 · Script chạy thử tắt D6 như replay_payload; phiên đọc danh sách ảnh của sổ gói (có dạng/vật) thay vì ánh xạ Image N (không có) — bỏ sót G27; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:90 · diag `subjects` jobs 1047, 1049–1051, 1054 (code 1110); docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:558 · N6 (dùng `speaker_lint.is_narrator`); docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:559 · N4 cùng G13: ngân sách ký tự theo khối, ưu tiên câu bắt buộc; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:563 · N1 (G30); docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:45 · đã xử lý trong dự án: Cắt đầu clip khi dựng; S4/S6 làm file ref mới: thay khúc chuyển cảnh bằng khung đội hình tua ngược, giữ độ dài/nhịp nhạc

### vd.gate — Cổng K3: 'Bỏ qua kiểm nền'

- Loại dòng: ô Dashboard
- Màu: tím
- Khâu liên quan: L13
- Phân loại: LOI
- Lý do: việc M4.7 đang làm
- Việc kế hoạch: M4.7 (🔄)
- Lỗi đang mở: P31-G15 — Mục cũ trong lipsync index không dọn khi method đổi về "skip" [OPEN] → M2.9, P31-G16 — QC đo clip coi shot chỉ có lời dẫn là "đang nói" [OPEN] → M2.9, P31-G17 — `quality_tier.py:177` coi `lip_sync is True` là có khớp môi trước `method_for` [OPEN] → M2.9, P31-G20 — Cổng ảnh→video báo nhầm "lệch nền 3D" khi ảnh không có/ít trời [OPEN] → M3.5, P31-G28 — Clip Seedance chế độ ảnh tham chiếu không bắt đầu đúng khung đầu đã duyệt; video prompt không mang câu bầu trời [OPEN] → M2.8, P31-G32 — Seedance chặn 6/8 job "real person" (ảnh `content[5..7]`) → tự lùi sang Kling (1067–1072, 31 s ≈ 2,70 USD) [FIXED_UNVERIFIED] → M1.5, P31-G36 — Tạm dừng dự án không chặn job đang chuẩn bị dở; thử lại sau khi bị từ chối lần đầu vẫn đi Seedance [IN_PROGRESS] → M1.3, P31-G37 — Shot 28 (nhóm 28+29) Seedance vẽ Kelly áo vàng, mất dạng bóng mờ ngay khung đầu; Kling cùng đầu vào giữ bóng mờ [OPEN] → M2.8, P31-G51 — Chấm 12 clip nháp 19/10 tối: 13 đơ 6 s; 16 địch không phản ứng, Kelly đơ; 18 máy Kling xuyên rào + địch gục vẫn bắn; 19 xoay 180° lố + áo đổi sọc; 29 súng biến mất 1–2,5 s; 35 mặt anime + 1 s cuối trống; 36 chạy tại chỗ, [OPEN] → M4.2, P31-G52 — QC logic chuỗi 39 clip (`scripts_19-10/qc_sequence/result.json`): độ cao nền đổi giữa shot 9→13; S10/11/13 nhặt súng trên thềm cỏ cao; bắn khi đã hết địch (18, 19); tường keo có trước khi ném (35); cửa shot 24 khác 23/25 [OPEN] → M4.3, P33-A1 — Job ảnh/clip succeeded 2 lần (`InvalidTransition succeeded -> succeeded`), lần sau đọc ảnh chưa ghi xong → QC lớp 0 `FileNotFoundError` → tự gen lại (thừa 0,05 USD job 1162→1163) [FIXED_UNVERIFIED] → M1.2, P33-A11 — `end_frame_skill_object` báo "ném keo" 28 lần ở #33 (không có tường keo): thông điệp viết cứng ở `core/runner.py:1433`, nhận mọi lý do từ `end_frames.skip_reason` [OPEN] → M2.9, P33-A15 — `download_error` PermissionError WinError 32 (tệp bị tiến trình khác giữ) [FIXED_UNVERIFIED] → M1.2, P33-B9 — Seedance ref-only không giữ khung ảnh đầu, theo khoảng cách máy của ref → S6 hàng con rối nhỏ hơn mèo [OPEN] → M2.8, V21-R3 — `qc_observe` raise khi `vat` là chuỗi (qc_observe.py:62–64) [FIXED_UNVERIFIED] → M1.1
- Việc đề xuất thêm vào plan: **Tiếp tục M4.7 và chốt tiêu chí cho vd.gate**
- Khâu đề xuất: L13
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G15, P31-G16, P31-G17, P31-G20, P31-G28, P31-G32, P31-G36, P31-G37, P31-G51, P31-G52, P33-A1, P33-A11, P33-A15, P33-B9, V21-R3
- Bằng chứng: việc M4.7 đang làm; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:63 · `runner.py:2214–2250`, `lipsync.mark` chỉ ghi thêm → `synced_scene_ids` sai khi gen lại; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:64 · `core/claude_tasks.py:323` `speaking = bool(data.get("dialogue"))`; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:65 · shot chỉ lời dẫn mà Đạo diễn gắn lip_sync → tính shot khó; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:75 · S22 (trong phòng) và S39 (từ trên cao): cổng so đường chân trời ở 7 % / 14 % khung — ảnh khớp bố cục nền 3D (xem ảnh so sánh) nhưng không lộ trời; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:86 · `framing_guard` ĐỎ nhiều clip (vd job 1043 "khung 0 khác hẳn ảnh đầu, khớp 22/3232 điểm"); S16 mở đầu Kelly nằm ở xa, mất trời có bóng ma; S29 trời sương xám như nền 3D; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:101 · `job_events` 1057/1058/1059/1060/1063/1064/1065/1066: `InputImageSensitiveContentDetected.PrivacyInformation`; diag `subjects`: "Kho chủ thể ClipAI đầy (100/100) … gửi ảnh như cũ (đánh dấu)"; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:110 · Tạm dừng 03:42:31 (`ui_actions`), job 1075 running Kling 03:42:41; 1061→1073 và 1062→… lần thử lại đầu vẫn bị Seedance chặn real_person rồi mới sang Kling (sáng: 1057→1065→1071); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:120 · bảng `p31_kling_vs_seedance_8shot.jpg`; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:556 · N7; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:557 · N3 + E cross-shot (`qc_sequence_logic`, cờ TẮT); docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:23 · tạm: Tiến trình riêng chỉ `submit_pending`, để Dashboard poll; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:564 · N4: thông điệp theo lý do thật; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:568 · N1 cùng A1; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:46 · đã xử lý trong dự án: Câu khóa cỡ khung chỉ giúp S4; S6 CHƯA đạt; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:260 · ĐANG XẢY RA (18/10: `qc_observe_enum` BẬT ở máy chính; #31 shot 30 `vat=["AWM"]`)

### vd.gen — Gen video · ↻ Gửi lại clip lỗi · $$

- Loại dòng: ô Dashboard
- Màu: xanh
- Khâu liên quan: L13
- Phân loại: LOI
- Lý do: có bằng chứng
- Lỗi đang mở: P31-G15 — Mục cũ trong lipsync index không dọn khi method đổi về "skip" [OPEN] → M2.9, P31-G16 — QC đo clip coi shot chỉ có lời dẫn là "đang nói" [OPEN] → M2.9, P31-G17 — `quality_tier.py:177` coi `lip_sync is True` là có khớp môi trước `method_for` [OPEN] → M2.9, P31-G20 — Cổng ảnh→video báo nhầm "lệch nền 3D" khi ảnh không có/ít trời [OPEN] → M3.5, P31-G28 — Clip Seedance chế độ ảnh tham chiếu không bắt đầu đúng khung đầu đã duyệt; video prompt không mang câu bầu trời [OPEN] → M2.8, P31-G32 — Seedance chặn 6/8 job "real person" (ảnh `content[5..7]`) → tự lùi sang Kling (1067–1072, 31 s ≈ 2,70 USD) [FIXED_UNVERIFIED] → M1.5, P31-G36 — Tạm dừng dự án không chặn job đang chuẩn bị dở; thử lại sau khi bị từ chối lần đầu vẫn đi Seedance [IN_PROGRESS] → M1.3, P31-G37 — Shot 28 (nhóm 28+29) Seedance vẽ Kelly áo vàng, mất dạng bóng mờ ngay khung đầu; Kling cùng đầu vào giữ bóng mờ [OPEN] → M2.8, P31-G51 — Chấm 12 clip nháp 19/10 tối: 13 đơ 6 s; 16 địch không phản ứng, Kelly đơ; 18 máy Kling xuyên rào + địch gục vẫn bắn; 19 xoay 180° lố + áo đổi sọc; 29 súng biến mất 1–2,5 s; 35 mặt anime + 1 s cuối trống; 36 chạy tại chỗ, [OPEN] → M4.2, P31-G52 — QC logic chuỗi 39 clip (`scripts_19-10/qc_sequence/result.json`): độ cao nền đổi giữa shot 9→13; S10/11/13 nhặt súng trên thềm cỏ cao; bắn khi đã hết địch (18, 19); tường keo có trước khi ném (35); cửa shot 24 khác 23/25 [OPEN] → M4.3, P33-A1 — Job ảnh/clip succeeded 2 lần (`InvalidTransition succeeded -> succeeded`), lần sau đọc ảnh chưa ghi xong → QC lớp 0 `FileNotFoundError` → tự gen lại (thừa 0,05 USD job 1162→1163) [FIXED_UNVERIFIED] → M1.2, P33-A11 — `end_frame_skill_object` báo "ném keo" 28 lần ở #33 (không có tường keo): thông điệp viết cứng ở `core/runner.py:1433`, nhận mọi lý do từ `end_frames.skip_reason` [OPEN] → M2.9, P33-A15 — `download_error` PermissionError WinError 32 (tệp bị tiến trình khác giữ) [FIXED_UNVERIFIED] → M1.2, P33-B9 — Seedance ref-only không giữ khung ảnh đầu, theo khoảng cách máy của ref → S6 hàng con rối nhỏ hơn mèo [OPEN] → M2.8, V21-R3 — `qc_observe` raise khi `vat` là chuỗi (qc_observe.py:62–64) [FIXED_UNVERIFIED] → M1.1
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G15, P31-G16, P31-G17, P31-G20, P31-G28, P31-G32, P31-G36, P31-G37, P31-G51, P31-G52, P33-A1, P33-A11, P33-A15, P33-B9, V21-R3**
- Khâu đề xuất: L13
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G15, P31-G16, P31-G17, P31-G20, P31-G28, P31-G32, P31-G36, P31-G37, P31-G51, P31-G52, P33-A1, P33-A11, P33-A15, P33-B9, V21-R3
- Bằng chứng: có bằng chứng; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:63 · `runner.py:2214–2250`, `lipsync.mark` chỉ ghi thêm → `synced_scene_ids` sai khi gen lại; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:64 · `core/claude_tasks.py:323` `speaking = bool(data.get("dialogue"))`; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:65 · shot chỉ lời dẫn mà Đạo diễn gắn lip_sync → tính shot khó; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:75 · S22 (trong phòng) và S39 (từ trên cao): cổng so đường chân trời ở 7 % / 14 % khung — ảnh khớp bố cục nền 3D (xem ảnh so sánh) nhưng không lộ trời; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:86 · `framing_guard` ĐỎ nhiều clip (vd job 1043 "khung 0 khác hẳn ảnh đầu, khớp 22/3232 điểm"); S16 mở đầu Kelly nằm ở xa, mất trời có bóng ma; S29 trời sương xám như nền 3D; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:101 · `job_events` 1057/1058/1059/1060/1063/1064/1065/1066: `InputImageSensitiveContentDetected.PrivacyInformation`; diag `subjects`: "Kho chủ thể ClipAI đầy (100/100) … gửi ảnh như cũ (đánh dấu)"; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:110 · Tạm dừng 03:42:31 (`ui_actions`), job 1075 running Kling 03:42:41; 1061→1073 và 1062→… lần thử lại đầu vẫn bị Seedance chặn real_person rồi mới sang Kling (sáng: 1057→1065→1071); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:120 · bảng `p31_kling_vs_seedance_8shot.jpg`; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:556 · N7; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:557 · N3 + E cross-shot (`qc_sequence_logic`, cờ TẮT); docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:23 · tạm: Tiến trình riêng chỉ `submit_pending`, để Dashboard poll; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:564 · N4: thông điệp theo lý do thật; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:568 · N1 cùng A1; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:46 · đã xử lý trong dự án: Câu khóa cỡ khung chỉ giúp S4; S6 CHƯA đạt; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:260 · ĐANG XẢY RA (18/10: `qc_observe_enum` BẬT ở máy chính; #31 shot 30 `vat=["AWM"]`)

### vd.qc — 🤖 Kiểm tra N clip · ✔ Duyệt clip

- Loại dòng: ô Dashboard
- Màu: xanh
- Khâu liên quan: L13
- Phân loại: LOI
- Lý do: có bằng chứng
- Lỗi đang mở: P31-G15 — Mục cũ trong lipsync index không dọn khi method đổi về "skip" [OPEN] → M2.9, P31-G16 — QC đo clip coi shot chỉ có lời dẫn là "đang nói" [OPEN] → M2.9, P31-G17 — `quality_tier.py:177` coi `lip_sync is True` là có khớp môi trước `method_for` [OPEN] → M2.9, P31-G20 — Cổng ảnh→video báo nhầm "lệch nền 3D" khi ảnh không có/ít trời [OPEN] → M3.5, P31-G28 — Clip Seedance chế độ ảnh tham chiếu không bắt đầu đúng khung đầu đã duyệt; video prompt không mang câu bầu trời [OPEN] → M2.8, P31-G32 — Seedance chặn 6/8 job "real person" (ảnh `content[5..7]`) → tự lùi sang Kling (1067–1072, 31 s ≈ 2,70 USD) [FIXED_UNVERIFIED] → M1.5, P31-G36 — Tạm dừng dự án không chặn job đang chuẩn bị dở; thử lại sau khi bị từ chối lần đầu vẫn đi Seedance [IN_PROGRESS] → M1.3, P31-G37 — Shot 28 (nhóm 28+29) Seedance vẽ Kelly áo vàng, mất dạng bóng mờ ngay khung đầu; Kling cùng đầu vào giữ bóng mờ [OPEN] → M2.8, P31-G51 — Chấm 12 clip nháp 19/10 tối: 13 đơ 6 s; 16 địch không phản ứng, Kelly đơ; 18 máy Kling xuyên rào + địch gục vẫn bắn; 19 xoay 180° lố + áo đổi sọc; 29 súng biến mất 1–2,5 s; 35 mặt anime + 1 s cuối trống; 36 chạy tại chỗ, [OPEN] → M4.2, P31-G52 — QC logic chuỗi 39 clip (`scripts_19-10/qc_sequence/result.json`): độ cao nền đổi giữa shot 9→13; S10/11/13 nhặt súng trên thềm cỏ cao; bắn khi đã hết địch (18, 19); tường keo có trước khi ném (35); cửa shot 24 khác 23/25 [OPEN] → M4.3, P33-A1 — Job ảnh/clip succeeded 2 lần (`InvalidTransition succeeded -> succeeded`), lần sau đọc ảnh chưa ghi xong → QC lớp 0 `FileNotFoundError` → tự gen lại (thừa 0,05 USD job 1162→1163) [FIXED_UNVERIFIED] → M1.2, P33-A11 — `end_frame_skill_object` báo "ném keo" 28 lần ở #33 (không có tường keo): thông điệp viết cứng ở `core/runner.py:1433`, nhận mọi lý do từ `end_frames.skip_reason` [OPEN] → M2.9, P33-A15 — `download_error` PermissionError WinError 32 (tệp bị tiến trình khác giữ) [FIXED_UNVERIFIED] → M1.2, P33-B9 — Seedance ref-only không giữ khung ảnh đầu, theo khoảng cách máy của ref → S6 hàng con rối nhỏ hơn mèo [OPEN] → M2.8, V21-R3 — `qc_observe` raise khi `vat` là chuỗi (qc_observe.py:62–64) [FIXED_UNVERIFIED] → M1.1
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G15, P31-G16, P31-G17, P31-G20, P31-G28, P31-G32, P31-G36, P31-G37, P31-G51, P31-G52, P33-A1, P33-A11, P33-A15, P33-B9, V21-R3**
- Khâu đề xuất: L13
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G15, P31-G16, P31-G17, P31-G20, P31-G28, P31-G32, P31-G36, P31-G37, P31-G51, P31-G52, P33-A1, P33-A11, P33-A15, P33-B9, V21-R3
- Bằng chứng: có bằng chứng; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:63 · `runner.py:2214–2250`, `lipsync.mark` chỉ ghi thêm → `synced_scene_ids` sai khi gen lại; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:64 · `core/claude_tasks.py:323` `speaking = bool(data.get("dialogue"))`; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:65 · shot chỉ lời dẫn mà Đạo diễn gắn lip_sync → tính shot khó; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:75 · S22 (trong phòng) và S39 (từ trên cao): cổng so đường chân trời ở 7 % / 14 % khung — ảnh khớp bố cục nền 3D (xem ảnh so sánh) nhưng không lộ trời; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:86 · `framing_guard` ĐỎ nhiều clip (vd job 1043 "khung 0 khác hẳn ảnh đầu, khớp 22/3232 điểm"); S16 mở đầu Kelly nằm ở xa, mất trời có bóng ma; S29 trời sương xám như nền 3D; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:101 · `job_events` 1057/1058/1059/1060/1063/1064/1065/1066: `InputImageSensitiveContentDetected.PrivacyInformation`; diag `subjects`: "Kho chủ thể ClipAI đầy (100/100) … gửi ảnh như cũ (đánh dấu)"; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:110 · Tạm dừng 03:42:31 (`ui_actions`), job 1075 running Kling 03:42:41; 1061→1073 và 1062→… lần thử lại đầu vẫn bị Seedance chặn real_person rồi mới sang Kling (sáng: 1057→1065→1071); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:120 · bảng `p31_kling_vs_seedance_8shot.jpg`; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:556 · N7; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:557 · N3 + E cross-shot (`qc_sequence_logic`, cờ TẮT); docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:23 · tạm: Tiến trình riêng chỉ `submit_pending`, để Dashboard poll; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:564 · N4: thông điệp theo lý do thật; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:568 · N1 cùng A1; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:46 · đã xử lý trong dự án: Câu khóa cỡ khung chỉ giúp S4; S6 CHƯA đạt; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:260 · ĐANG XẢY RA (18/10: `qc_observe_enum` BẬT ở máy chính; #31 shot 30 `vat=["AWM"]`)

### vd.cut — ✂ Cắt lại · 🎞 Ghép bản nháp · 0 USD

- Loại dòng: ô Dashboard
- Màu: xanh
- Khâu liên quan: L15
- Phân loại: LOI
- Lý do: có bằng chứng
- Lỗi đang mở: P33-B11 — Bản ghép ref 1080×2730 quá khung TikTok; cắt khung con rối quá cao → thấp đầu [OPEN] → M5.2
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P33-B11**
- Khâu đề xuất: L15
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P33-B11
- Bằng chứng: có bằng chứng; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:48 · đã xử lý trong dự án: 1080×1920: ref 760×570 + nền mờ, con rối 1080×1350 cắt theo từng shot

### bg.music — 🤖 Brief nhạc · ✨ Tạo nháp · Chọn

- Loại dòng: ô Dashboard
- Màu: vàng
- Khâu liên quan: L14
- Phân loại: LOI, LONG
- Lý do: lỏng: chỉ người / chỉ theo nút / bỏ qua được (mốc 17/10)
- Việc kế hoạch: M6.8 (⬜)
- Lỗi đang mở: P31-G14 — Nút "⏱ Đặt thời lượng theo giọng thật" kéo dài MỌI shot có lời dẫn [OPEN] → M2.9, P31-G42 — Lời dẫn đi trước hình: shot 36 đọc "…tụi nó thì đứng cười hở nách ăn mừng" khi Kelly còn chạy; ngã ở 37, ăn mừng ở 38 (38 không có lời) [OPEN] → M4.3
- Việc đề xuất thêm vào plan: **Tiếp tục M6.8 và chốt tiêu chí cho bg.music**
- Khâu đề xuất: L14
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; khâu đang vàng (chỉ người, cờ tắt hoặc thiếu bước kiểm tự động); mã lỗi: P31-G14, P31-G42
- Bằng chứng: lỏng: chỉ người / chỉ theo nút / bỏ qua được (mốc 17/10); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:62 · `voice.fit_durations` kéo 17 shot (S10 1,3→8 s, S24 1→7 s) — đổi nhịp phim + tăng tiền video, không hỏi; chỉ 3 shot (6, 12, 31) thật sự bị chặn đỏ; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:135 · dialogue 36/38

### bg.sfx — ✨ Tạo SFX · 🎥 Tiếng video ref → SFX

- Loại dòng: ô Dashboard
- Màu: vàng
- Khâu liên quan: L14
- Phân loại: LOI, LONG
- Lý do: lỏng: chỉ người / chỉ theo nút / bỏ qua được (mốc 17/10)
- Việc kế hoạch: M6.8 (⬜)
- Lỗi đang mở: P31-G14 — Nút "⏱ Đặt thời lượng theo giọng thật" kéo dài MỌI shot có lời dẫn [OPEN] → M2.9, P31-G42 — Lời dẫn đi trước hình: shot 36 đọc "…tụi nó thì đứng cười hở nách ăn mừng" khi Kelly còn chạy; ngã ở 37, ăn mừng ở 38 (38 không có lời) [OPEN] → M4.3
- Việc đề xuất thêm vào plan: **Tiếp tục M6.8 và chốt tiêu chí cho bg.sfx**
- Khâu đề xuất: L14
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; khâu đang vàng (chỉ người, cờ tắt hoặc thiếu bước kiểm tự động); mã lỗi: P31-G14, P31-G42
- Bằng chứng: lỏng: chỉ người / chỉ theo nút / bỏ qua được (mốc 17/10); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:62 · `voice.fit_durations` kéo 17 shot (S10 1,3→8 s, S24 1→7 s) — đổi nhịp phim + tăng tiền video, không hỏi; chỉ 3 shot (6, 12, 31) thật sự bị chặn đỏ; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:135 · dialogue 36/38

### bg.subs — 📝 Phụ đề · ⬇ .srt/.xlsx · 🔥 In phụ đề

- Loại dòng: ô Dashboard
- Màu: vàng
- Khâu liên quan: L14
- Phân loại: LOI, LONG, KHONG_VIEC
- Lý do: lỏng: chỉ người / chỉ theo nút / bỏ qua được (mốc 17/10)
- Lỗi đang mở: P31-G14 — Nút "⏱ Đặt thời lượng theo giọng thật" kéo dài MỌI shot có lời dẫn [OPEN] → M2.9, P31-G42 — Lời dẫn đi trước hình: shot 36 đọc "…tụi nó thì đứng cười hở nách ăn mừng" khi Kelly còn chạy; ngã ở 37, ăn mừng ở 38 (38 không có lời) [OPEN] → M4.3
- Việc đề xuất thêm vào plan: **Bổ sung việc vào plan cho bg.subs**
- Khâu đề xuất: L14
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; khâu đang vàng (chỉ người, cờ tắt hoặc thiếu bước kiểm tự động); khoảng trống hoặc lỗi chưa có việc kế hoạch được gắn trực tiếp; mã lỗi: P31-G14, P31-G42
- Bằng chứng: lỏng: chỉ người / chỉ theo nút / bỏ qua được (mốc 17/10); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:62 · `voice.fit_durations` kéo 17 shot (S10 1,3→8 s, S24 1→7 s) — đổi nhịp phim + tăng tiền video, không hỏi; chỉ 3 shot (6, 12, 31) thật sự bị chặn đỏ; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:135 · dialogue 36/38

### bg.fx — 🤖 AI đề xuất hiệu ứng · ✅ Thêm

- Loại dòng: ô Dashboard
- Màu: vàng
- Khâu liên quan: L14
- Phân loại: LOI, LONG, KHONG_VIEC
- Lý do: lỏng: chỉ người / chỉ theo nút / bỏ qua được (mốc 17/10)
- Lỗi đang mở: P31-G14 — Nút "⏱ Đặt thời lượng theo giọng thật" kéo dài MỌI shot có lời dẫn [OPEN] → M2.9, P31-G42 — Lời dẫn đi trước hình: shot 36 đọc "…tụi nó thì đứng cười hở nách ăn mừng" khi Kelly còn chạy; ngã ở 37, ăn mừng ở 38 (38 không có lời) [OPEN] → M4.3
- Việc đề xuất thêm vào plan: **Bổ sung việc vào plan cho bg.fx**
- Khâu đề xuất: L14
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; khâu đang vàng (chỉ người, cờ tắt hoặc thiếu bước kiểm tự động); khoảng trống hoặc lỗi chưa có việc kế hoạch được gắn trực tiếp; mã lỗi: P31-G14, P31-G42
- Bằng chứng: lỏng: chỉ người / chỉ theo nút / bỏ qua được (mốc 17/10); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:62 · `voice.fit_durations` kéo 17 shot (S10 1,3→8 s, S24 1→7 s) — đổi nhịp phim + tăng tiền video, không hỏi; chỉ 3 shot (6, 12, 31) thật sự bị chặn đỏ; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:135 · dialogue 36/38

### bg.popup — Popup cuối clip: không có kiểm

- Loại dòng: ô Dashboard
- Màu: xanh
- Khâu liên quan: L15
- Phân loại: LOI
- Lý do: có bằng chứng, việc kế hoạch xong
- Việc kế hoạch: M4.4 (✅)
- Lỗi đang mở: P33-B11 — Bản ghép ref 1080×2730 quá khung TikTok; cắt khung con rối quá cao → thấp đầu [OPEN] → M5.2
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P33-B11**
- Khâu đề xuất: L15
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P33-B11
- Bằng chứng: có bằng chứng, việc kế hoạch xong; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:48 · đã xử lý trong dự án: 1080×1920: ref 760×570 + nền mờ, con rối 1080×1350 cắt theo từng shot

### t.writer — BIÊN KỊCH (CLAUDE)

- Loại dòng: nút trường
- Màu: xanh
- Khâu liên quan: L1
- Phân loại: Không có cảnh báo phân loại
- Lý do: có bằng chứng

### t.director — ĐẠO DIỄN (CLAUDE API)

- Loại dòng: nút trường
- Màu: xanh
- Khâu liên quan: L3
- Phân loại: LOI
- Lý do: có bằng chứng
- Lỗi đang mở: P31-G18 — BYĐ của shot mâu thuẫn trường khác của CHÍNH shot [OPEN] → M2.1, P31-G41 — Hướng chạy shot 35 ngược mạch: Kelly "chạy ra xa máy" vào nền, nơi có tường + tháp + địch (34: địch góc xa bên phải, tháp sau chúng) → chạy VỀ PHÍA địch, ngược "dựng keo định chuồn"; 36 lại chạy sang TRÁI khung → 35↔36 k [OPEN] → M3.3, P31-G43 — Kịch bản: "quay người rời khỏi cái xác và đi tiếp"; ảnh 1000 cái xác ở NỀN sau lưng → clip Kelly đi vào nền, VỀ PHÍA cái xác [IN_PROGRESS] → M3.3, P31-G44 — Kịch bản 26: Kelly bên trái, xác "phía trước" giữa-phải, cô "phát hiện" nó; ảnh 998 Kelly đi về phía máy, xác lơ lửng SAU LƯNG bên TRÁI → không thể "phát hiện phía trước"; 27 xác bên PHẢI → nhảy trục 26↔27 [OPEN] → M3.3, P31-G45 — Kịch bản: "bốn địch đứng tách biệt ở bốn góc xa", núp sau hàng rào cao; ảnh 994: bốn địch đứng gần nhau một hàng ở cuối, hàng rào trong thấp (G8 mô hình Kho #265) [OPEN] → M3.3, P31-G50 — 1017/1015 sai bố cục + phi thực tế: 17 Sứ giả đứng ngay đầu tường bắn thẳng vào Kelly (tường không chắn giữa), tường cong lồi ngược; 18 tường chắn ngang ở chỗ khác, Sứ giả đã gục từ đầu shot; hành lang bắc rộng 4 m = bề  [OPEN] → M3.3, P31-G9 — `shot_text_checks` khớp "whole body" trong câu tả SÚNG ("aura along its whole body") → chặn shot 17 [OPEN] → M2.7, P33-A12 — #33 không có BYĐ → `video_pregen` VÀNG "chưa có BYĐ" 22 lần, không kiểm được nhịp / khung cuối [OPEN] → M2.9, V31-GOC4 — BYĐ mâu thuẫn trường khác của shot / thiếu BYĐ [IN_PROGRESS] → M2.1
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G18, P31-G41, P31-G43, P31-G44, P31-G45, P31-G50, P31-G9, P33-A12, V31-GOC4**
- Khâu đề xuất: L3
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G18, P31-G41, P31-G43, P31-G44, P31-G45, P31-G50, P31-G9, P33-A12, V31-GOC4
- Bằng chứng: có bằng chứng; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:73 · Shot 2: `byd.may.chuyen_dong = dung_yen` nhưng `camera_move = pan` + kịch bản "góc nhìn lia theo hướng quay" → mọi motion đều bị Tổ rà soát báo đỏ một phía. Không có kiểm code nào so BYĐ ↔ camera_move/action khi Đạo diễn khai; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:134 · shot 34 blocking; shot 35 blocking/motion "run away from camera", ảnh 976 tường ở nền; clip cuối 35 Kelly lao vào tường; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:143 · Kịch bản: "quay người rời khỏi cái xác và đi tiếp"; ảnh 1000 cái xác ở NỀN sau lưng → clip Kelly đi vào nền, VỀ PHÍA cái xác; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:144 · Kịch bản 26: Kelly bên trái, xác "phía trước" giữa-phải, cô "phát hiện" nó; ảnh 998 Kelly đi về phía máy, xác lơ lửng SAU LƯNG bên TRÁI → không thể "phát hiện phía trước"; 27 xác bên PHẢI → nhảy trục 26↔27; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:145 · Kịch bản: "bốn địch đứng tách biệt ở bốn góc xa", núp sau hàng rào cao; ảnh 994: bốn địch đứng gần nhau một hàng ở cuối, hàng rào trong thấp (G8 mô hình Kho #265); docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:565 · P2: Đạo diễn BYĐ phải chạy được qua `claude_cli`; docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:7 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0)

### t.kho — KHO TÀI NGUYÊN

- Loại dòng: nút trường
- Màu: xanh
- Khâu liên quan: L5
- Phân loại: LOI
- Lý do: có bằng chứng
- Lỗi đang mở: P31-G38 — Shot 35/36 tường keo đúng skin nhưng THẲNG hàng, không cong về phía người ném (`gloo-wall-curved` 14/10) — cả Kling lẫn Seedance [OPEN] → M2.3, P33-B1 — Ảnh mẫu thân dài (đầu ≈ 46 % thay vì ≈ 56 % như game), đầu đỏ/tím bẹt, màu áo sai mẫu [OPEN] → M2.3
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G38, P33-B1**
- Khâu đề xuất: L5
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G38, P33-B1
- Bằng chứng: có bằng chứng; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:121 · cùng bảng; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:38 · đã xử lý trong dự án: Đo tỉ lệ ảnh góc → câu "1,8 đầu, đầu 55–58 %"; đỏ/tím lấy ảnh mẫu vàng làm ref dáng đầu; màu áo theo `các màu.png` (đỏ: áo trắng quần đỏ; tím: xanh dương đậm); xanh lơ không có ảnh áo → đổi sang vàng (đúng ảnh góc). GPT Image 2.5 vẫn kéo thân ~50 %

### t.dang — thanh_phan[].dang

- Loại dòng: nút trường
- Màu: xanh
- Khâu liên quan: L5, L12
- Phân loại: LOI
- Lý do: có bằng chứng, việc kế hoạch xong
- Việc kế hoạch: M2.1 (✅), M2.3 (✅)
- Lỗi đang mở: P31-G10 — Lời người dẫn chuyện (LỜI DẪN) bị coi là lời thoại phải KHỚP MÔI [FIXED_UNVERIFIED] → M2.9, P31-G12 — Tên địa danh có dấu trong câu tiếng Anh làm chặn gói [OPEN] → M2.8, P31-G13 — Gói nhóm vượt 5000 ký tự [OPEN] → M2.8, P31-G23 — Công cụ kiểm gói video thiếu [OPEN] → M1.9, P31-G24 — 7 shot cận (9, 10, 12, 19, 24, 28, 32) đi Kling trái quyết định `video-route-2026-10-13` ("video hết Seedance 2.5, Kling chỉ đường lùi") [FIXED_UNVERIFIED] → M2.8, P31-G27 — Gói VIDEO chỉ gửi 1 ảnh khuôn mặt mỗi nhân vật — không gửi ảnh DẠNG (bóng mờ, Kho #427) và không gửi ảnh VẬT Kho (Bom keo skin thang máy #367, SKORP #433, XÁC ĐEN #443), trong khi gói ẢNH có đủ [FIXED_UNVERIFIED] → M2.3, P31-G29 — Bước kiểm gói của phiên này bỏ qua D6 (chat_prompts BẬT ở máy chính: Claude viết lại prompt video lúc gửi) và không đối chiếu ảnh cần (dạng/vật) với "Image N" trong prompt [OPEN] → M1.9, P31-G30 — Kho chủ thể ClipAI đầy 100/100 → ảnh không tải lên, gửi ảnh đánh dấu [FIXED_UNVERIFIED] → M1.5, P31-G38 — Shot 35/36 tường keo đúng skin nhưng THẲNG hàng, không cong về phía người ném (`gloo-wall-curved` 14/10) — cả Kling lẫn Seedance [OPEN] → M2.3, P31-G53 — `speaker_no_identity` vẫn báo cho LỜI DẪN tới 19/10 13:52 (sau sửa G10 ngày 18/10) — `core/seedance_refs.py:546` chưa bỏ người dẫn chuyện [OPEN] → M2.9, P31-G54 — Trần độ dài prompt chặn câu cần thiết: D6 bị từ chối (3256 > 3192; 4096 > 4000), `gore_restraint` "không thêm được câu … quá 4000 ký tự" [OPEN] → M2.8, P31-G58 — Kho chủ thể đầy lặp lại ở #33 (13 lần, 20/10) — G30 chưa sửa nên dự án sau gặp lại [FIXED_UNVERIFIED] → M1.5, P33-B1 — Ảnh mẫu thân dài (đầu ≈ 46 % thay vì ≈ 56 % như game), đầu đỏ/tím bẹt, màu áo sai mẫu [OPEN] → M2.3, P33-B8 — Seedance ref-only chép cả đoạn chuyển cảnh đầu đoạn ref: lộ con mèo (S5), góc trống (S6), mở bằng một con ở xa (S4) [OPEN] → M2.8
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G10, P31-G12, P31-G13, P31-G23, P31-G24, P31-G27, P31-G29, P31-G30, P31-G38, P31-G53, P31-G54, P31-G58, P33-B1, P33-B8**
- Khâu đề xuất: L5
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G10, P31-G12, P31-G13, P31-G23, P31-G24, P31-G27, P31-G29, P31-G30, P31-G38, P31-G53, P31-G54, P31-G58, P33-B1, P33-B8
- Bằng chứng: có bằng chứng, việc kế hoạch xong; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:58 · `core/lipsync.py:_method` so người nói với `characters`; shot POV không có cast → điều kiện "người nói ngoài khung" không bao giờ đúng → "post" → (cờ dialogue_take) "take" → gói nhóm S01–S03, S05–S06 ghi *"LOI DAN speak Audio1… Sync the mouth, jaw…"* + gửi reference_audio. Model có thể vẽ thêm người; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:60 · "the Cổng Trời hedge maze" (S05), "LỜI DẪN narrates" (S39) → `lint` "prompt còn chữ tiếng Việt" chặn cả clip nhóm. Motion writer không được dặn viết tên riêng không dấu; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:61 · S01–S03 = 5173 ký tự: motion mỗi shot có câu giải thích "because…" (viết cho người đọc), khối khớp môi G10 cộng thêm; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:78 · Phải viết script tạm (thư mục thử + provider giả có chữ ký ClipAI) mới thấy G10–G13; sổ gói ghi `reference_only` không nhãn; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:79 · `core/model_router.py` nhánh `seedance_refs` (chỉ chạy khi `FEATURE_SEEDANCE_REF_GROUPS=1` — cờ nằm trong `dashboard.env`): shot cận thấy mặt không vào nhóm tham chiếu → cờ `closeup_start_frame` (S4.1, 29/09, `verified: False`) → Kling từ khung đầu, TRƯỚC luật E1 (E1 chỉ đổi model họ Seedance). Chạy; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:85 · `core/seedance_refs.py:314 identity_pictures`: lấy ảnh danh tính (Kelly = ảnh áo vàng 23/10.png) + bỏ ảnh trang phục khi nhân vật ở dạng, KHÔNG thêm ảnh dạng; không có nhánh ảnh vật. Gói thật job 1045 (S28–29): "Image 3 is Kelly: identity only — NOT the clothes … ghost form" + ảnh áo vàng → cận mặt; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:89 · Script chạy thử tắt D6 như replay_payload; phiên đọc danh sách ảnh của sổ gói (có dạng/vật) thay vì ánh xạ Image N (không có) — bỏ sót G27; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:90 · diag `subjects` jobs 1047, 1049–1051, 1054 (code 1110); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:121 · cùng bảng; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:558 · N6 (dùng `speaker_lint.is_narrator`); docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:559 · N4 cùng G13: ngân sách ký tự theo khối, ưu tiên câu bắt buộc; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:563 · N1 (G30); docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:38 · đã xử lý trong dự án: Đo tỉ lệ ảnh góc → câu "1,8 đầu, đầu 55–58 %"; đỏ/tím lấy ảnh mẫu vàng làm ref dáng đầu; màu áo theo `các màu.png` (đỏ: áo trắng quần đỏ; tím: xanh dương đậm); xanh lơ không có ảnh áo → đổi sang vàng (đúng ảnh góc). GPT Image 2.5 vẫn kéo thân ~50 %; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:45 · đã xử lý trong dự án: Cắt đầu clip khi dựng; S4/S6 làm file ref mới: thay khúc chuyển cảnh bằng khung đội hình tua ngược, giữ độ dài/nhịp nhạc

### t.vat — vat[] {kho_id, nguoi, cach}

- Loại dòng: nút trường
- Màu: xanh
- Khâu liên quan: L7, L8
- Phân loại: LOI
- Lý do: có bằng chứng, việc kế hoạch xong
- Việc kế hoạch: M2.1 (✅)
- Lỗi đang mở: P31-G4 — Chọn ảnh Kho bằng dò bí danh trong chữ, không đọc BYĐ [OPEN] → M2.2, P31-G5 — Sổ gói ghi nhãn ảnh sai [OPEN] → M2.6, P31-G7 — Shot POV bỏ ảnh súng [FIXED_UNVERIFIED] → M2.7, P33-B2 — Ảnh trời tham chiếu dính đỉnh tháp → model vẽ tháp thứ hai [OPEN] → M2.7, P33-B3 — Tả bằng chữ "mắt xoáy ngay trên đỉnh tháp" → model dời tháp ra giữa [OPEN] → M3.3
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G4, P31-G5, P31-G7, P33-B2, P33-B3**
- Khâu đề xuất: L7
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G4, P31-G5, P31-G7, P33-B2, P33-B3
- Bằng chứng: có bằng chứng, việc kế hoạch xong; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:15 · `core/assets.py:_named_extras` (1815–1855) khớp `names_of(a)` trong text + image_prompt. Bí danh #443 = *"flying black corpse, floating corpse, levitating corpse, cái xác biết bay"*. Phiên này bỏ "floating corpse" khỏi prompt shot 23 (để qua bộ lọc OpenAI) → job 993 KHÔNG gửi ảnh #443 (job 967 trước; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:16 · `core/sent_package.py:124 _meta_index` khóa theo basename — Kho đặt tên `1.png/2.png/3.png` ở mọi mục → ảnh #443/2.png ghi nhãn "SKORP", #367/2.png ghi "SKORP", #425/3.png ghi "KELLY". Prompt gửi model vẫn ĐÚNG (shot 24: *"Image 5 is the object XÁC ĐEN BIẾT BAY"*) — chỉ sổ sai; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:19 · `core/assets.py:1830` bỏ ref súng khi `prop_lock.is_pov` (luật #27 "FF không có POV cầm súng") → shot 15 POV bắn: model vẽ súng đen thường, mất hào quang đỏ. 16/17 có ref SKORP (#433/2.png là SKORP đen) nhưng câu prompt chỉ ghi "red-glowing" ngắn → màu đỏ yếu/mất; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:39 · đã xử lý trong dự án: Cắt ảnh trời chỉ phần mây/mắt xoáy; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:40 · đã xử lý trong dự án: Vị trí đặt bằng nền 3D, không bằng prompt: ghép trời in-game vào plate (alpha `raw.png`, mắt xoáy đặt theo đỉnh tháp đo trên ảnh) — script scratchpad `p33_sky_composite3.py`

### t.noichon — noi_chon {kho_id, spot}

- Loại dòng: nút trường
- Màu: xanh
- Khâu liên quan: L8
- Phân loại: LOI
- Lý do: có bằng chứng, việc kế hoạch xong
- Việc kế hoạch: M2.1 (✅), M2.2 (✅)
- Lỗi đang mở: P31-G4 — Chọn ảnh Kho bằng dò bí danh trong chữ, không đọc BYĐ [OPEN] → M2.2, P31-G5 — Sổ gói ghi nhãn ảnh sai [OPEN] → M2.6, P31-G7 — Shot POV bỏ ảnh súng [FIXED_UNVERIFIED] → M2.7, P33-B3 — Tả bằng chữ "mắt xoáy ngay trên đỉnh tháp" → model dời tháp ra giữa [OPEN] → M3.3
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G4, P31-G5, P31-G7, P33-B3**
- Khâu đề xuất: L8
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G4, P31-G5, P31-G7, P33-B3
- Bằng chứng: có bằng chứng, việc kế hoạch xong; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:15 · `core/assets.py:_named_extras` (1815–1855) khớp `names_of(a)` trong text + image_prompt. Bí danh #443 = *"flying black corpse, floating corpse, levitating corpse, cái xác biết bay"*. Phiên này bỏ "floating corpse" khỏi prompt shot 23 (để qua bộ lọc OpenAI) → job 993 KHÔNG gửi ảnh #443 (job 967 trước; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:16 · `core/sent_package.py:124 _meta_index` khóa theo basename — Kho đặt tên `1.png/2.png/3.png` ở mọi mục → ảnh #443/2.png ghi nhãn "SKORP", #367/2.png ghi "SKORP", #425/3.png ghi "KELLY". Prompt gửi model vẫn ĐÚNG (shot 24: *"Image 5 is the object XÁC ĐEN BIẾT BAY"*) — chỉ sổ sai; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:19 · `core/assets.py:1830` bỏ ref súng khi `prop_lock.is_pov` (luật #27 "FF không có POV cầm súng") → shot 15 POV bắn: model vẽ súng đen thường, mất hào quang đỏ. 16/17 có ref SKORP (#433/2.png là SKORP đen) nhưng câu prompt chỉ ghi "red-glowing" ngắn → màu đỏ yếu/mất; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:40 · đã xử lý trong dự án: Vị trí đặt bằng nền 3D, không bằng prompt: ghép trời in-game vào plate (alpha `raw.png`, mắt xoáy đặt theo đỉnh tháp đo trên ảnh) — script scratchpad `p33_sky_composite3.py`

### t.mocnen — khung.moc_nen

- Loại dòng: nút trường
- Màu: xanh
- Khâu liên quan: L6
- Phân loại: LOI
- Lý do: có bằng chứng, việc kế hoạch xong
- Việc kế hoạch: M2.1 (✅)
- Lỗi đang mở: P31-G1 — Khối giữ chỗ của sân khấu 3D bị mang sang cảnh khác [IN_PROGRESS] → M2.4, P31-G2 — Nền 3D không có mốc tỉ lệ người [OPEN] → M3.2, P31-G3 — Máy góc 'eye' mà ngước/chúi lớn, không kiểm nền bị tường che [IN_PROGRESS] → M3.2, P31-G46 — vị trí vật/nhân vật xuyên các shot liên quan (xác 26–29, keo + địch 34–38, mê cung 14) chỉ tả bằng chữ riêng từng shot; mỗi ảnh gen độc lập → model đặt lại mỗi lần; vá chữ shot này làm lệch shot kia (vd sửa 29 "tháp trái [IN_PROGRESS] → M3.1, P31-G47 — toạ độ chỗ đứng thật (stage inputs doan_4): shot 13 Kelly ở tâm (0,55; 0,1); 15–18 Kelly ở `me_cung_nga_re_bac` (−0,1; 14,3) = hành lang ngoài phía BẮC; 19 ở `me_cung_khe_tay` (−14,3; −0,1); biệt thự (mốc PKK_OUT_Buildin [OPEN] → M3.1, P31-G49 — "dưới chân Kelly có bậc cỏ cao tới đầu gối, mê cung làm gì có"): grid 3D tâm mê cung: ô cỏ (Fence001) cao hơn lối đi chỉ 0,13 m. Máy 16/10 của shot 13 đứng gần trên ô cỏ, cao 1,9 m, cúi −27°, cách Kelly 0,9 m (Tổ rà soát [OPEN] → M3.2, P31-G8 — Mô hình 3D Kho #265 hàng rào thấp ≈ 1,5 m → nhìn qua thấy nhiều lớp rào [FIXED_UNVERIFIED] → M3.2, P33-A10 — Góc `high` của plate cố định chúc 30° (`plate_camera.HIGH_TILT_DEG`) → nền chỉ còn sàn đá [IN_PROGRESS] → M3.2, P33-B4 — Nền ghép "như dán đè ảnh 3D" [OPEN] → M3.1, P33-B5 — Góc in-game chuẩn = máy thấp ở thềm nhìn lên cầu thang, tháp TRÁI bị cắt đỉnh; đổi sang EWS cho thấy đỉnh tháp là SAI bố cục [OPEN] → M3.2, V31-GOC1 — Vị trí vật/nhân vật không có MỘT nguồn sự thật xuyên shot [IN_PROGRESS] → M3.1, V31-GOC2 — Hình học máy ↔ người ↔ sàn bằng hằng số / chữ thay vì đo [IN_PROGRESS] → M3.2, V31-GOC5 — Kho: vật một dạng, tỉ lệ mô hình, nền ghép [OPEN] → M3.2
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G1, P31-G2, P31-G3, P31-G46, P31-G47, P31-G49, P31-G8, P33-A10, P33-B4, P33-B5, V31-GOC1, V31-GOC2, V31-GOC5**
- Khâu đề xuất: L6
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G1, P31-G2, P31-G3, P31-G46, P31-G47, P31-G49, P31-G8, P33-A10, P33-B4, P33-B5, V31-GOC1, V31-GOC2, V31-GOC5
- Bằng chứng: có bằng chứng, việc kế hoạch xong; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:12 · `stage_camera.props` = trụ Ø0,5×1,75 m nhãn "XÁC ĐEN BIẾT BAY" (dàn cảnh cảnh 6) có ở shot 28/30 (`source: "cảnh 6 (cùng sân khấu)"`) và 34/35 (`"cảnh 7 (cùng sân khấu)"`), kể cả cảnh 8 = thế giới THỰC TẠI ban ngày (không có quái). Khối render vào nền (`plate.png`) → model vẽ thành cột đá; D6 shot 3; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:13 · Nền render trống người; cỡ người chỉ do câu % khung trong prompt (vd shot 23 *"her whole body about 60% of frame height … never resize her smaller for distance"*) — không ràng theo khoảng cách 3D. Shot 35 địch to như khổng lồ; shot 14 máy cao 3,6 m chúi −18° (meta `pitch_deg -18.2`) → hàng rào trông; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:14 · Shot 28 `angle: eye` nhưng máy thấp hơn cảnh 0,56 m (z 10,85 vs 11,41), meta `pitch_deg +17.3` → nền gần như chỉ tường trống, model tự bịa; shot 35 `pitch +11.1`; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:26 · G8 (xác nhận 18/10 bằng video in-game người dùng gửi `ScreenRecording_10-17-2026_08-33-20_1.mov`): trong game, hàng rào BÊN; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:32 · tạm: Dùng `eye` (máy ngang mắt người lớn ≈ chúc 5–10° xuống con rối chibi); docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:41 · đã xử lý trong dự án: Chuyển màu Lab theo ảnh in-game người dùng (`goc_chup_ingame_chuan.png`), mây in-game + vệt gió + sương theo `depth.png`, quầng đỏ sẫm; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:42 · đã xử lý trong dự án: Về WS góc thấp; docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:4 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0); docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:5 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0); docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:8 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0)

### t.gate — CỔNG KIỂM SCHEMA

- Loại dòng: nút trường
- Màu: xanh
- Khâu liên quan: L3
- Phân loại: LOI
- Lý do: có bằng chứng
- Lỗi đang mở: P31-G18 — BYĐ của shot mâu thuẫn trường khác của CHÍNH shot [OPEN] → M2.1, P31-G41 — Hướng chạy shot 35 ngược mạch: Kelly "chạy ra xa máy" vào nền, nơi có tường + tháp + địch (34: địch góc xa bên phải, tháp sau chúng) → chạy VỀ PHÍA địch, ngược "dựng keo định chuồn"; 36 lại chạy sang TRÁI khung → 35↔36 k [OPEN] → M3.3, P31-G43 — Kịch bản: "quay người rời khỏi cái xác và đi tiếp"; ảnh 1000 cái xác ở NỀN sau lưng → clip Kelly đi vào nền, VỀ PHÍA cái xác [IN_PROGRESS] → M3.3, P31-G44 — Kịch bản 26: Kelly bên trái, xác "phía trước" giữa-phải, cô "phát hiện" nó; ảnh 998 Kelly đi về phía máy, xác lơ lửng SAU LƯNG bên TRÁI → không thể "phát hiện phía trước"; 27 xác bên PHẢI → nhảy trục 26↔27 [OPEN] → M3.3, P31-G45 — Kịch bản: "bốn địch đứng tách biệt ở bốn góc xa", núp sau hàng rào cao; ảnh 994: bốn địch đứng gần nhau một hàng ở cuối, hàng rào trong thấp (G8 mô hình Kho #265) [OPEN] → M3.3, P31-G50 — 1017/1015 sai bố cục + phi thực tế: 17 Sứ giả đứng ngay đầu tường bắn thẳng vào Kelly (tường không chắn giữa), tường cong lồi ngược; 18 tường chắn ngang ở chỗ khác, Sứ giả đã gục từ đầu shot; hành lang bắc rộng 4 m = bề  [OPEN] → M3.3, P31-G9 — `shot_text_checks` khớp "whole body" trong câu tả SÚNG ("aura along its whole body") → chặn shot 17 [OPEN] → M2.7, P33-A12 — #33 không có BYĐ → `video_pregen` VÀNG "chưa có BYĐ" 22 lần, không kiểm được nhịp / khung cuối [OPEN] → M2.9, V31-GOC4 — BYĐ mâu thuẫn trường khác của shot / thiếu BYĐ [IN_PROGRESS] → M2.1
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G18, P31-G41, P31-G43, P31-G44, P31-G45, P31-G50, P31-G9, P33-A12, V31-GOC4**
- Khâu đề xuất: L3
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G18, P31-G41, P31-G43, P31-G44, P31-G45, P31-G50, P31-G9, P33-A12, V31-GOC4
- Bằng chứng: có bằng chứng; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:73 · Shot 2: `byd.may.chuyen_dong = dung_yen` nhưng `camera_move = pan` + kịch bản "góc nhìn lia theo hướng quay" → mọi motion đều bị Tổ rà soát báo đỏ một phía. Không có kiểm code nào so BYĐ ↔ camera_move/action khi Đạo diễn khai; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:134 · shot 34 blocking; shot 35 blocking/motion "run away from camera", ảnh 976 tường ở nền; clip cuối 35 Kelly lao vào tường; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:143 · Kịch bản: "quay người rời khỏi cái xác và đi tiếp"; ảnh 1000 cái xác ở NỀN sau lưng → clip Kelly đi vào nền, VỀ PHÍA cái xác; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:144 · Kịch bản 26: Kelly bên trái, xác "phía trước" giữa-phải, cô "phát hiện" nó; ảnh 998 Kelly đi về phía máy, xác lơ lửng SAU LƯNG bên TRÁI → không thể "phát hiện phía trước"; 27 xác bên PHẢI → nhảy trục 26↔27; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:145 · Kịch bản: "bốn địch đứng tách biệt ở bốn góc xa", núp sau hàng rào cao; ảnh 994: bốn địch đứng gần nhau một hàng ở cuối, hàng rào trong thấp (G8 mô hình Kho #265); docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:565 · P2: Đạo diễn BYĐ phải chạy được qua `claude_cli`; docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:7 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0)

### t.forms — NHÂN VẬT & DẠNG

- Loại dòng: nút trường
- Màu: xanh
- Khâu liên quan: L5, L12
- Phân loại: LOI
- Lý do: có bằng chứng, việc kế hoạch xong
- Việc kế hoạch: M2.2 (✅), M2.3 (✅)
- Lỗi đang mở: P31-G10 — Lời người dẫn chuyện (LỜI DẪN) bị coi là lời thoại phải KHỚP MÔI [FIXED_UNVERIFIED] → M2.9, P31-G12 — Tên địa danh có dấu trong câu tiếng Anh làm chặn gói [OPEN] → M2.8, P31-G13 — Gói nhóm vượt 5000 ký tự [OPEN] → M2.8, P31-G23 — Công cụ kiểm gói video thiếu [OPEN] → M1.9, P31-G24 — 7 shot cận (9, 10, 12, 19, 24, 28, 32) đi Kling trái quyết định `video-route-2026-10-13` ("video hết Seedance 2.5, Kling chỉ đường lùi") [FIXED_UNVERIFIED] → M2.8, P31-G27 — Gói VIDEO chỉ gửi 1 ảnh khuôn mặt mỗi nhân vật — không gửi ảnh DẠNG (bóng mờ, Kho #427) và không gửi ảnh VẬT Kho (Bom keo skin thang máy #367, SKORP #433, XÁC ĐEN #443), trong khi gói ẢNH có đủ [FIXED_UNVERIFIED] → M2.3, P31-G29 — Bước kiểm gói của phiên này bỏ qua D6 (chat_prompts BẬT ở máy chính: Claude viết lại prompt video lúc gửi) và không đối chiếu ảnh cần (dạng/vật) với "Image N" trong prompt [OPEN] → M1.9, P31-G30 — Kho chủ thể ClipAI đầy 100/100 → ảnh không tải lên, gửi ảnh đánh dấu [FIXED_UNVERIFIED] → M1.5, P31-G38 — Shot 35/36 tường keo đúng skin nhưng THẲNG hàng, không cong về phía người ném (`gloo-wall-curved` 14/10) — cả Kling lẫn Seedance [OPEN] → M2.3, P31-G53 — `speaker_no_identity` vẫn báo cho LỜI DẪN tới 19/10 13:52 (sau sửa G10 ngày 18/10) — `core/seedance_refs.py:546` chưa bỏ người dẫn chuyện [OPEN] → M2.9, P31-G54 — Trần độ dài prompt chặn câu cần thiết: D6 bị từ chối (3256 > 3192; 4096 > 4000), `gore_restraint` "không thêm được câu … quá 4000 ký tự" [OPEN] → M2.8, P31-G58 — Kho chủ thể đầy lặp lại ở #33 (13 lần, 20/10) — G30 chưa sửa nên dự án sau gặp lại [FIXED_UNVERIFIED] → M1.5, P33-B1 — Ảnh mẫu thân dài (đầu ≈ 46 % thay vì ≈ 56 % như game), đầu đỏ/tím bẹt, màu áo sai mẫu [OPEN] → M2.3, P33-B8 — Seedance ref-only chép cả đoạn chuyển cảnh đầu đoạn ref: lộ con mèo (S5), góc trống (S6), mở bằng một con ở xa (S4) [OPEN] → M2.8
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G10, P31-G12, P31-G13, P31-G23, P31-G24, P31-G27, P31-G29, P31-G30, P31-G38, P31-G53, P31-G54, P31-G58, P33-B1, P33-B8**
- Khâu đề xuất: L5
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G10, P31-G12, P31-G13, P31-G23, P31-G24, P31-G27, P31-G29, P31-G30, P31-G38, P31-G53, P31-G54, P31-G58, P33-B1, P33-B8
- Bằng chứng: có bằng chứng, việc kế hoạch xong; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:58 · `core/lipsync.py:_method` so người nói với `characters`; shot POV không có cast → điều kiện "người nói ngoài khung" không bao giờ đúng → "post" → (cờ dialogue_take) "take" → gói nhóm S01–S03, S05–S06 ghi *"LOI DAN speak Audio1… Sync the mouth, jaw…"* + gửi reference_audio. Model có thể vẽ thêm người; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:60 · "the Cổng Trời hedge maze" (S05), "LỜI DẪN narrates" (S39) → `lint` "prompt còn chữ tiếng Việt" chặn cả clip nhóm. Motion writer không được dặn viết tên riêng không dấu; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:61 · S01–S03 = 5173 ký tự: motion mỗi shot có câu giải thích "because…" (viết cho người đọc), khối khớp môi G10 cộng thêm; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:78 · Phải viết script tạm (thư mục thử + provider giả có chữ ký ClipAI) mới thấy G10–G13; sổ gói ghi `reference_only` không nhãn; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:79 · `core/model_router.py` nhánh `seedance_refs` (chỉ chạy khi `FEATURE_SEEDANCE_REF_GROUPS=1` — cờ nằm trong `dashboard.env`): shot cận thấy mặt không vào nhóm tham chiếu → cờ `closeup_start_frame` (S4.1, 29/09, `verified: False`) → Kling từ khung đầu, TRƯỚC luật E1 (E1 chỉ đổi model họ Seedance). Chạy; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:85 · `core/seedance_refs.py:314 identity_pictures`: lấy ảnh danh tính (Kelly = ảnh áo vàng 23/10.png) + bỏ ảnh trang phục khi nhân vật ở dạng, KHÔNG thêm ảnh dạng; không có nhánh ảnh vật. Gói thật job 1045 (S28–29): "Image 3 is Kelly: identity only — NOT the clothes … ghost form" + ảnh áo vàng → cận mặt; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:89 · Script chạy thử tắt D6 như replay_payload; phiên đọc danh sách ảnh của sổ gói (có dạng/vật) thay vì ánh xạ Image N (không có) — bỏ sót G27; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:90 · diag `subjects` jobs 1047, 1049–1051, 1054 (code 1110); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:121 · cùng bảng; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:558 · N6 (dùng `speaker_lint.is_narrator`); docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:559 · N4 cùng G13: ngân sách ký tự theo khối, ưu tiên câu bắt buộc; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:563 · N1 (G30); docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:38 · đã xử lý trong dự án: Đo tỉ lệ ảnh góc → câu "1,8 đầu, đầu 55–58 %"; đỏ/tím lấy ảnh mẫu vàng làm ref dáng đầu; màu áo theo `các màu.png` (đỏ: áo trắng quần đỏ; tím: xanh dương đậm); xanh lơ không có ảnh áo → đổi sang vàng (đúng ảnh góc). GPT Image 2.5 vẫn kéo thân ~50 %; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:45 · đã xử lý trong dự án: Cắt đầu clip khi dựng; S4/S6 làm file ref mới: thay khúc chuyển cảnh bằng khung đội hình tua ngược, giữ độ dài/nhịp nhạc

### t.props — ĐẠO CỤ CẦM / ĐEO

- Loại dòng: nút trường
- Màu: xanh
- Khâu liên quan: L7, L8
- Phân loại: LOI
- Lý do: có bằng chứng, việc kế hoạch xong
- Việc kế hoạch: M2.2 (✅)
- Lỗi đang mở: P31-G4 — Chọn ảnh Kho bằng dò bí danh trong chữ, không đọc BYĐ [OPEN] → M2.2, P31-G5 — Sổ gói ghi nhãn ảnh sai [OPEN] → M2.6, P31-G7 — Shot POV bỏ ảnh súng [FIXED_UNVERIFIED] → M2.7, P33-B2 — Ảnh trời tham chiếu dính đỉnh tháp → model vẽ tháp thứ hai [OPEN] → M2.7, P33-B3 — Tả bằng chữ "mắt xoáy ngay trên đỉnh tháp" → model dời tháp ra giữa [OPEN] → M3.3
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G4, P31-G5, P31-G7, P33-B2, P33-B3**
- Khâu đề xuất: L7
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G4, P31-G5, P31-G7, P33-B2, P33-B3
- Bằng chứng: có bằng chứng, việc kế hoạch xong; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:15 · `core/assets.py:_named_extras` (1815–1855) khớp `names_of(a)` trong text + image_prompt. Bí danh #443 = *"flying black corpse, floating corpse, levitating corpse, cái xác biết bay"*. Phiên này bỏ "floating corpse" khỏi prompt shot 23 (để qua bộ lọc OpenAI) → job 993 KHÔNG gửi ảnh #443 (job 967 trước; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:16 · `core/sent_package.py:124 _meta_index` khóa theo basename — Kho đặt tên `1.png/2.png/3.png` ở mọi mục → ảnh #443/2.png ghi nhãn "SKORP", #367/2.png ghi "SKORP", #425/3.png ghi "KELLY". Prompt gửi model vẫn ĐÚNG (shot 24: *"Image 5 is the object XÁC ĐEN BIẾT BAY"*) — chỉ sổ sai; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:19 · `core/assets.py:1830` bỏ ref súng khi `prop_lock.is_pov` (luật #27 "FF không có POV cầm súng") → shot 15 POV bắn: model vẽ súng đen thường, mất hào quang đỏ. 16/17 có ref SKORP (#433/2.png là SKORP đen) nhưng câu prompt chỉ ghi "red-glowing" ngắn → màu đỏ yếu/mất; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:39 · đã xử lý trong dự án: Cắt ảnh trời chỉ phần mây/mắt xoáy; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:40 · đã xử lý trong dự án: Vị trí đặt bằng nền 3D, không bằng prompt: ghép trời in-game vào plate (alpha `raw.png`, mắt xoáy đặt theo đỉnh tháp đo trên ảnh) — script scratchpad `p33_sky_composite3.py`

### t.place — BỐI CẢNH & ÁNH SÁNG

- Loại dòng: nút trường
- Màu: xanh
- Khâu liên quan: L8
- Phân loại: LOI
- Lý do: có bằng chứng, việc kế hoạch xong
- Việc kế hoạch: M2.2 (✅)
- Lỗi đang mở: P31-G4 — Chọn ảnh Kho bằng dò bí danh trong chữ, không đọc BYĐ [OPEN] → M2.2, P31-G5 — Sổ gói ghi nhãn ảnh sai [OPEN] → M2.6, P31-G7 — Shot POV bỏ ảnh súng [FIXED_UNVERIFIED] → M2.7, P33-B3 — Tả bằng chữ "mắt xoáy ngay trên đỉnh tháp" → model dời tháp ra giữa [OPEN] → M3.3
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G4, P31-G5, P31-G7, P33-B3**
- Khâu đề xuất: L8
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G4, P31-G5, P31-G7, P33-B3
- Bằng chứng: có bằng chứng, việc kế hoạch xong; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:15 · `core/assets.py:_named_extras` (1815–1855) khớp `names_of(a)` trong text + image_prompt. Bí danh #443 = *"flying black corpse, floating corpse, levitating corpse, cái xác biết bay"*. Phiên này bỏ "floating corpse" khỏi prompt shot 23 (để qua bộ lọc OpenAI) → job 993 KHÔNG gửi ảnh #443 (job 967 trước; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:16 · `core/sent_package.py:124 _meta_index` khóa theo basename — Kho đặt tên `1.png/2.png/3.png` ở mọi mục → ảnh #443/2.png ghi nhãn "SKORP", #367/2.png ghi "SKORP", #425/3.png ghi "KELLY". Prompt gửi model vẫn ĐÚNG (shot 24: *"Image 5 is the object XÁC ĐEN BIẾT BAY"*) — chỉ sổ sai; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:19 · `core/assets.py:1830` bỏ ref súng khi `prop_lock.is_pov` (luật #27 "FF không có POV cầm súng") → shot 15 POV bắn: model vẽ súng đen thường, mất hào quang đỏ. 16/17 có ref SKORP (#433/2.png là SKORP đen) nhưng câu prompt chỉ ghi "red-glowing" ngắn → màu đỏ yếu/mất; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:40 · đã xử lý trong dự án: Vị trí đặt bằng nền 3D, không bằng prompt: ghép trời in-game vào plate (alpha `raw.png`, mắt xoáy đặt theo đỉnh tháp đo trên ảnh) — script scratchpad `p33_sky_composite3.py`

### t.plate — NỀN 3D & MỐC

- Loại dòng: nút trường
- Màu: xanh
- Khâu liên quan: L6
- Phân loại: LOI
- Lý do: có bằng chứng, việc kế hoạch xong
- Việc kế hoạch: M2.2 (✅)
- Lỗi đang mở: P31-G1 — Khối giữ chỗ của sân khấu 3D bị mang sang cảnh khác [IN_PROGRESS] → M2.4, P31-G2 — Nền 3D không có mốc tỉ lệ người [OPEN] → M3.2, P31-G3 — Máy góc 'eye' mà ngước/chúi lớn, không kiểm nền bị tường che [IN_PROGRESS] → M3.2, P31-G46 — vị trí vật/nhân vật xuyên các shot liên quan (xác 26–29, keo + địch 34–38, mê cung 14) chỉ tả bằng chữ riêng từng shot; mỗi ảnh gen độc lập → model đặt lại mỗi lần; vá chữ shot này làm lệch shot kia (vd sửa 29 "tháp trái [IN_PROGRESS] → M3.1, P31-G47 — toạ độ chỗ đứng thật (stage inputs doan_4): shot 13 Kelly ở tâm (0,55; 0,1); 15–18 Kelly ở `me_cung_nga_re_bac` (−0,1; 14,3) = hành lang ngoài phía BẮC; 19 ở `me_cung_khe_tay` (−14,3; −0,1); biệt thự (mốc PKK_OUT_Buildin [OPEN] → M3.1, P31-G49 — "dưới chân Kelly có bậc cỏ cao tới đầu gối, mê cung làm gì có"): grid 3D tâm mê cung: ô cỏ (Fence001) cao hơn lối đi chỉ 0,13 m. Máy 16/10 của shot 13 đứng gần trên ô cỏ, cao 1,9 m, cúi −27°, cách Kelly 0,9 m (Tổ rà soát [OPEN] → M3.2, P31-G8 — Mô hình 3D Kho #265 hàng rào thấp ≈ 1,5 m → nhìn qua thấy nhiều lớp rào [FIXED_UNVERIFIED] → M3.2, P33-A10 — Góc `high` của plate cố định chúc 30° (`plate_camera.HIGH_TILT_DEG`) → nền chỉ còn sàn đá [IN_PROGRESS] → M3.2, P33-B4 — Nền ghép "như dán đè ảnh 3D" [OPEN] → M3.1, P33-B5 — Góc in-game chuẩn = máy thấp ở thềm nhìn lên cầu thang, tháp TRÁI bị cắt đỉnh; đổi sang EWS cho thấy đỉnh tháp là SAI bố cục [OPEN] → M3.2, V31-GOC1 — Vị trí vật/nhân vật không có MỘT nguồn sự thật xuyên shot [IN_PROGRESS] → M3.1, V31-GOC2 — Hình học máy ↔ người ↔ sàn bằng hằng số / chữ thay vì đo [IN_PROGRESS] → M3.2, V31-GOC5 — Kho: vật một dạng, tỉ lệ mô hình, nền ghép [OPEN] → M3.2
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G1, P31-G2, P31-G3, P31-G46, P31-G47, P31-G49, P31-G8, P33-A10, P33-B4, P33-B5, V31-GOC1, V31-GOC2, V31-GOC5**
- Khâu đề xuất: L6
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G1, P31-G2, P31-G3, P31-G46, P31-G47, P31-G49, P31-G8, P33-A10, P33-B4, P33-B5, V31-GOC1, V31-GOC2, V31-GOC5
- Bằng chứng: có bằng chứng, việc kế hoạch xong; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:12 · `stage_camera.props` = trụ Ø0,5×1,75 m nhãn "XÁC ĐEN BIẾT BAY" (dàn cảnh cảnh 6) có ở shot 28/30 (`source: "cảnh 6 (cùng sân khấu)"`) và 34/35 (`"cảnh 7 (cùng sân khấu)"`), kể cả cảnh 8 = thế giới THỰC TẠI ban ngày (không có quái). Khối render vào nền (`plate.png`) → model vẽ thành cột đá; D6 shot 3; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:13 · Nền render trống người; cỡ người chỉ do câu % khung trong prompt (vd shot 23 *"her whole body about 60% of frame height … never resize her smaller for distance"*) — không ràng theo khoảng cách 3D. Shot 35 địch to như khổng lồ; shot 14 máy cao 3,6 m chúi −18° (meta `pitch_deg -18.2`) → hàng rào trông; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:14 · Shot 28 `angle: eye` nhưng máy thấp hơn cảnh 0,56 m (z 10,85 vs 11,41), meta `pitch_deg +17.3` → nền gần như chỉ tường trống, model tự bịa; shot 35 `pitch +11.1`; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:26 · G8 (xác nhận 18/10 bằng video in-game người dùng gửi `ScreenRecording_10-17-2026_08-33-20_1.mov`): trong game, hàng rào BÊN; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:32 · tạm: Dùng `eye` (máy ngang mắt người lớn ≈ chúc 5–10° xuống con rối chibi); docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:41 · đã xử lý trong dự án: Chuyển màu Lab theo ảnh in-game người dùng (`goc_chup_ingame_chuan.png`), mây in-game + vệt gió + sương theo `depth.png`, quầng đỏ sẫm; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:42 · đã xử lý trong dự án: Về WS góc thấp; docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:4 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0); docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:5 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0); docs/RA_CLOUD_3D_GOC_A_2026-10-22.md:8 · gom từ các lỗi trỏ root_cause_id về mục này (C-3D-GOC-A bước 0)

### t.pick — CHỌN ẢNH KHO

- Loại dòng: nút trường
- Màu: xanh
- Khâu liên quan: L8
- Phân loại: LOI
- Lý do: có bằng chứng, việc kế hoạch xong
- Việc kế hoạch: M2.2 (✅)
- Lỗi đang mở: P31-G4 — Chọn ảnh Kho bằng dò bí danh trong chữ, không đọc BYĐ [OPEN] → M2.2, P31-G5 — Sổ gói ghi nhãn ảnh sai [OPEN] → M2.6, P31-G7 — Shot POV bỏ ảnh súng [FIXED_UNVERIFIED] → M2.7, P33-B3 — Tả bằng chữ "mắt xoáy ngay trên đỉnh tháp" → model dời tháp ra giữa [OPEN] → M3.3
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G4, P31-G5, P31-G7, P33-B3**
- Khâu đề xuất: L8
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G4, P31-G5, P31-G7, P33-B3
- Bằng chứng: có bằng chứng, việc kế hoạch xong; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:15 · `core/assets.py:_named_extras` (1815–1855) khớp `names_of(a)` trong text + image_prompt. Bí danh #443 = *"flying black corpse, floating corpse, levitating corpse, cái xác biết bay"*. Phiên này bỏ "floating corpse" khỏi prompt shot 23 (để qua bộ lọc OpenAI) → job 993 KHÔNG gửi ảnh #443 (job 967 trước; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:16 · `core/sent_package.py:124 _meta_index` khóa theo basename — Kho đặt tên `1.png/2.png/3.png` ở mọi mục → ảnh #443/2.png ghi nhãn "SKORP", #367/2.png ghi "SKORP", #425/3.png ghi "KELLY". Prompt gửi model vẫn ĐÚNG (shot 24: *"Image 5 is the object XÁC ĐEN BIẾT BAY"*) — chỉ sổ sai; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:19 · `core/assets.py:1830` bỏ ref súng khi `prop_lock.is_pov` (luật #27 "FF không có POV cầm súng") → shot 15 POV bắn: model vẽ súng đen thường, mất hào quang đỏ. 16/17 có ref SKORP (#433/2.png là SKORP đen) nhưng câu prompt chỉ ghi "red-glowing" ngắn → màu đỏ yếu/mất; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:40 · đã xử lý trong dự án: Vị trí đặt bằng nền 3D, không bằng prompt: ghép trời in-game vào plate (alpha `raw.png`, mắt xoáy đặt theo đỉnh tháp đo trên ảnh) — script scratchpad `p33_sky_composite3.py`

### t.regex — LUẬT REGEX TRÊN CHỮ

- Loại dòng: nút trường
- Màu: xanh
- Khâu liên quan: L8
- Phân loại: LOI
- Lý do: có bằng chứng, việc kế hoạch xong
- Việc kế hoạch: M2.2 (✅)
- Lỗi đang mở: P31-G4 — Chọn ảnh Kho bằng dò bí danh trong chữ, không đọc BYĐ [OPEN] → M2.2, P31-G5 — Sổ gói ghi nhãn ảnh sai [OPEN] → M2.6, P31-G7 — Shot POV bỏ ảnh súng [FIXED_UNVERIFIED] → M2.7, P33-B3 — Tả bằng chữ "mắt xoáy ngay trên đỉnh tháp" → model dời tháp ra giữa [OPEN] → M3.3
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G4, P31-G5, P31-G7, P33-B3**
- Khâu đề xuất: L8
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G4, P31-G5, P31-G7, P33-B3
- Bằng chứng: có bằng chứng, việc kế hoạch xong; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:15 · `core/assets.py:_named_extras` (1815–1855) khớp `names_of(a)` trong text + image_prompt. Bí danh #443 = *"flying black corpse, floating corpse, levitating corpse, cái xác biết bay"*. Phiên này bỏ "floating corpse" khỏi prompt shot 23 (để qua bộ lọc OpenAI) → job 993 KHÔNG gửi ảnh #443 (job 967 trước; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:16 · `core/sent_package.py:124 _meta_index` khóa theo basename — Kho đặt tên `1.png/2.png/3.png` ở mọi mục → ảnh #443/2.png ghi nhãn "SKORP", #367/2.png ghi "SKORP", #425/3.png ghi "KELLY". Prompt gửi model vẫn ĐÚNG (shot 24: *"Image 5 is the object XÁC ĐEN BIẾT BAY"*) — chỉ sổ sai; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:19 · `core/assets.py:1830` bỏ ref súng khi `prop_lock.is_pov` (luật #27 "FF không có POV cầm súng") → shot 15 POV bắn: model vẽ súng đen thường, mất hào quang đỏ. 16/17 có ref SKORP (#433/2.png là SKORP đen) nhưng câu prompt chỉ ghi "red-glowing" ngắn → màu đỏ yếu/mất; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:40 · đã xử lý trong dự án: Vị trí đặt bằng nền 3D, không bằng prompt: ghép trời in-game vào plate (alpha `raw.png`, mắt xoáy đặt theo đỉnh tháp đo trên ảnh) — script scratchpad `p33_sky_composite3.py`

### t.package — GÓI GỬI MODEL

- Loại dòng: nút trường
- Màu: xanh
- Khâu liên quan: L8, L12
- Phân loại: LOI
- Lý do: có bằng chứng
- Lỗi đang mở: P31-G10 — Lời người dẫn chuyện (LỜI DẪN) bị coi là lời thoại phải KHỚP MÔI [FIXED_UNVERIFIED] → M2.9, P31-G12 — Tên địa danh có dấu trong câu tiếng Anh làm chặn gói [OPEN] → M2.8, P31-G13 — Gói nhóm vượt 5000 ký tự [OPEN] → M2.8, P31-G23 — Công cụ kiểm gói video thiếu [OPEN] → M1.9, P31-G24 — 7 shot cận (9, 10, 12, 19, 24, 28, 32) đi Kling trái quyết định `video-route-2026-10-13` ("video hết Seedance 2.5, Kling chỉ đường lùi") [FIXED_UNVERIFIED] → M2.8, P31-G27 — Gói VIDEO chỉ gửi 1 ảnh khuôn mặt mỗi nhân vật — không gửi ảnh DẠNG (bóng mờ, Kho #427) và không gửi ảnh VẬT Kho (Bom keo skin thang máy #367, SKORP #433, XÁC ĐEN #443), trong khi gói ẢNH có đủ [FIXED_UNVERIFIED] → M2.3, P31-G29 — Bước kiểm gói của phiên này bỏ qua D6 (chat_prompts BẬT ở máy chính: Claude viết lại prompt video lúc gửi) và không đối chiếu ảnh cần (dạng/vật) với "Image N" trong prompt [OPEN] → M1.9, P31-G30 — Kho chủ thể ClipAI đầy 100/100 → ảnh không tải lên, gửi ảnh đánh dấu [FIXED_UNVERIFIED] → M1.5, P31-G4 — Chọn ảnh Kho bằng dò bí danh trong chữ, không đọc BYĐ [OPEN] → M2.2, P31-G5 — Sổ gói ghi nhãn ảnh sai [OPEN] → M2.6, P31-G53 — `speaker_no_identity` vẫn báo cho LỜI DẪN tới 19/10 13:52 (sau sửa G10 ngày 18/10) — `core/seedance_refs.py:546` chưa bỏ người dẫn chuyện [OPEN] → M2.9, P31-G54 — Trần độ dài prompt chặn câu cần thiết: D6 bị từ chối (3256 > 3192; 4096 > 4000), `gore_restraint` "không thêm được câu … quá 4000 ký tự" [OPEN] → M2.8, P31-G58 — Kho chủ thể đầy lặp lại ở #33 (13 lần, 20/10) — G30 chưa sửa nên dự án sau gặp lại [FIXED_UNVERIFIED] → M1.5, P31-G7 — Shot POV bỏ ảnh súng [FIXED_UNVERIFIED] → M2.7, P33-B3 — Tả bằng chữ "mắt xoáy ngay trên đỉnh tháp" → model dời tháp ra giữa [OPEN] → M3.3, P33-B8 — Seedance ref-only chép cả đoạn chuyển cảnh đầu đoạn ref: lộ con mèo (S5), góc trống (S6), mở bằng một con ở xa (S4) [OPEN] → M2.8
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G10, P31-G12, P31-G13, P31-G23, P31-G24, P31-G27, P31-G29, P31-G30, P31-G4, P31-G5, P31-G53, P31-G54, P31-G58, P31-G7, P33-B3, P33-B8**
- Khâu đề xuất: L8
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G10, P31-G12, P31-G13, P31-G23, P31-G24, P31-G27, P31-G29, P31-G30, P31-G4, P31-G5, P31-G53, P31-G54, P31-G58, P31-G7, P33-B3, P33-B8
- Bằng chứng: có bằng chứng; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:58 · `core/lipsync.py:_method` so người nói với `characters`; shot POV không có cast → điều kiện "người nói ngoài khung" không bao giờ đúng → "post" → (cờ dialogue_take) "take" → gói nhóm S01–S03, S05–S06 ghi *"LOI DAN speak Audio1… Sync the mouth, jaw…"* + gửi reference_audio. Model có thể vẽ thêm người; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:60 · "the Cổng Trời hedge maze" (S05), "LỜI DẪN narrates" (S39) → `lint` "prompt còn chữ tiếng Việt" chặn cả clip nhóm. Motion writer không được dặn viết tên riêng không dấu; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:61 · S01–S03 = 5173 ký tự: motion mỗi shot có câu giải thích "because…" (viết cho người đọc), khối khớp môi G10 cộng thêm; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:78 · Phải viết script tạm (thư mục thử + provider giả có chữ ký ClipAI) mới thấy G10–G13; sổ gói ghi `reference_only` không nhãn; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:79 · `core/model_router.py` nhánh `seedance_refs` (chỉ chạy khi `FEATURE_SEEDANCE_REF_GROUPS=1` — cờ nằm trong `dashboard.env`): shot cận thấy mặt không vào nhóm tham chiếu → cờ `closeup_start_frame` (S4.1, 29/09, `verified: False`) → Kling từ khung đầu, TRƯỚC luật E1 (E1 chỉ đổi model họ Seedance). Chạy; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:85 · `core/seedance_refs.py:314 identity_pictures`: lấy ảnh danh tính (Kelly = ảnh áo vàng 23/10.png) + bỏ ảnh trang phục khi nhân vật ở dạng, KHÔNG thêm ảnh dạng; không có nhánh ảnh vật. Gói thật job 1045 (S28–29): "Image 3 is Kelly: identity only — NOT the clothes … ghost form" + ảnh áo vàng → cận mặt; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:89 · Script chạy thử tắt D6 như replay_payload; phiên đọc danh sách ảnh của sổ gói (có dạng/vật) thay vì ánh xạ Image N (không có) — bỏ sót G27; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:90 · diag `subjects` jobs 1047, 1049–1051, 1054 (code 1110); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:15 · `core/assets.py:_named_extras` (1815–1855) khớp `names_of(a)` trong text + image_prompt. Bí danh #443 = *"flying black corpse, floating corpse, levitating corpse, cái xác biết bay"*. Phiên này bỏ "floating corpse" khỏi prompt shot 23 (để qua bộ lọc OpenAI) → job 993 KHÔNG gửi ảnh #443 (job 967 trước; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:16 · `core/sent_package.py:124 _meta_index` khóa theo basename — Kho đặt tên `1.png/2.png/3.png` ở mọi mục → ảnh #443/2.png ghi nhãn "SKORP", #367/2.png ghi "SKORP", #425/3.png ghi "KELLY". Prompt gửi model vẫn ĐÚNG (shot 24: *"Image 5 is the object XÁC ĐEN BIẾT BAY"*) — chỉ sổ sai; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:558 · N6 (dùng `speaker_lint.is_narrator`); docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:559 · N4 cùng G13: ngân sách ký tự theo khối, ưu tiên câu bắt buộc; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:563 · N1 (G30); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:19 · `core/assets.py:1830` bỏ ref súng khi `prop_lock.is_pov` (luật #27 "FF không có POV cầm súng") → shot 15 POV bắn: model vẽ súng đen thường, mất hào quang đỏ. 16/17 có ref SKORP (#433/2.png là SKORP đen) nhưng câu prompt chỉ ghi "red-glowing" ngắn → màu đỏ yếu/mất; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:40 · đã xử lý trong dự án: Vị trí đặt bằng nền 3D, không bằng prompt: ghép trời in-game vào plate (alpha `raw.png`, mắt xoáy đặt theo đỉnh tháp đo trên ảnh) — script scratchpad `p33_sky_composite3.py`; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:45 · đã xử lý trong dự án: Cắt đầu clip khi dựng; S4/S6 làm file ref mới: thay khúc chuyển cảnh bằng khung đội hình tua ngược, giữ độ dài/nhịp nhạc

### t.regress — BỘ HỒI QUY GÓI THẬT

- Loại dòng: nút trường
- Màu: xanh
- Khâu liên quan: L8, L12
- Phân loại: LOI
- Lý do: có bằng chứng, việc kế hoạch xong
- Việc kế hoạch: M1.9 (✅)
- Lỗi đang mở: P31-G10 — Lời người dẫn chuyện (LỜI DẪN) bị coi là lời thoại phải KHỚP MÔI [FIXED_UNVERIFIED] → M2.9, P31-G12 — Tên địa danh có dấu trong câu tiếng Anh làm chặn gói [OPEN] → M2.8, P31-G13 — Gói nhóm vượt 5000 ký tự [OPEN] → M2.8, P31-G23 — Công cụ kiểm gói video thiếu [OPEN] → M1.9, P31-G24 — 7 shot cận (9, 10, 12, 19, 24, 28, 32) đi Kling trái quyết định `video-route-2026-10-13` ("video hết Seedance 2.5, Kling chỉ đường lùi") [FIXED_UNVERIFIED] → M2.8, P31-G27 — Gói VIDEO chỉ gửi 1 ảnh khuôn mặt mỗi nhân vật — không gửi ảnh DẠNG (bóng mờ, Kho #427) và không gửi ảnh VẬT Kho (Bom keo skin thang máy #367, SKORP #433, XÁC ĐEN #443), trong khi gói ẢNH có đủ [FIXED_UNVERIFIED] → M2.3, P31-G29 — Bước kiểm gói của phiên này bỏ qua D6 (chat_prompts BẬT ở máy chính: Claude viết lại prompt video lúc gửi) và không đối chiếu ảnh cần (dạng/vật) với "Image N" trong prompt [OPEN] → M1.9, P31-G30 — Kho chủ thể ClipAI đầy 100/100 → ảnh không tải lên, gửi ảnh đánh dấu [FIXED_UNVERIFIED] → M1.5, P31-G4 — Chọn ảnh Kho bằng dò bí danh trong chữ, không đọc BYĐ [OPEN] → M2.2, P31-G5 — Sổ gói ghi nhãn ảnh sai [OPEN] → M2.6, P31-G53 — `speaker_no_identity` vẫn báo cho LỜI DẪN tới 19/10 13:52 (sau sửa G10 ngày 18/10) — `core/seedance_refs.py:546` chưa bỏ người dẫn chuyện [OPEN] → M2.9, P31-G54 — Trần độ dài prompt chặn câu cần thiết: D6 bị từ chối (3256 > 3192; 4096 > 4000), `gore_restraint` "không thêm được câu … quá 4000 ký tự" [OPEN] → M2.8, P31-G58 — Kho chủ thể đầy lặp lại ở #33 (13 lần, 20/10) — G30 chưa sửa nên dự án sau gặp lại [FIXED_UNVERIFIED] → M1.5, P31-G7 — Shot POV bỏ ảnh súng [FIXED_UNVERIFIED] → M2.7, P33-B3 — Tả bằng chữ "mắt xoáy ngay trên đỉnh tháp" → model dời tháp ra giữa [OPEN] → M3.3, P33-B8 — Seedance ref-only chép cả đoạn chuyển cảnh đầu đoạn ref: lộ con mèo (S5), góc trống (S6), mở bằng một con ở xa (S4) [OPEN] → M2.8
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G10, P31-G12, P31-G13, P31-G23, P31-G24, P31-G27, P31-G29, P31-G30, P31-G4, P31-G5, P31-G53, P31-G54, P31-G58, P31-G7, P33-B3, P33-B8**
- Khâu đề xuất: L8
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G10, P31-G12, P31-G13, P31-G23, P31-G24, P31-G27, P31-G29, P31-G30, P31-G4, P31-G5, P31-G53, P31-G54, P31-G58, P31-G7, P33-B3, P33-B8
- Bằng chứng: có bằng chứng, việc kế hoạch xong; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:58 · `core/lipsync.py:_method` so người nói với `characters`; shot POV không có cast → điều kiện "người nói ngoài khung" không bao giờ đúng → "post" → (cờ dialogue_take) "take" → gói nhóm S01–S03, S05–S06 ghi *"LOI DAN speak Audio1… Sync the mouth, jaw…"* + gửi reference_audio. Model có thể vẽ thêm người; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:60 · "the Cổng Trời hedge maze" (S05), "LỜI DẪN narrates" (S39) → `lint` "prompt còn chữ tiếng Việt" chặn cả clip nhóm. Motion writer không được dặn viết tên riêng không dấu; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:61 · S01–S03 = 5173 ký tự: motion mỗi shot có câu giải thích "because…" (viết cho người đọc), khối khớp môi G10 cộng thêm; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:78 · Phải viết script tạm (thư mục thử + provider giả có chữ ký ClipAI) mới thấy G10–G13; sổ gói ghi `reference_only` không nhãn; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:79 · `core/model_router.py` nhánh `seedance_refs` (chỉ chạy khi `FEATURE_SEEDANCE_REF_GROUPS=1` — cờ nằm trong `dashboard.env`): shot cận thấy mặt không vào nhóm tham chiếu → cờ `closeup_start_frame` (S4.1, 29/09, `verified: False`) → Kling từ khung đầu, TRƯỚC luật E1 (E1 chỉ đổi model họ Seedance). Chạy; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:85 · `core/seedance_refs.py:314 identity_pictures`: lấy ảnh danh tính (Kelly = ảnh áo vàng 23/10.png) + bỏ ảnh trang phục khi nhân vật ở dạng, KHÔNG thêm ảnh dạng; không có nhánh ảnh vật. Gói thật job 1045 (S28–29): "Image 3 is Kelly: identity only — NOT the clothes … ghost form" + ảnh áo vàng → cận mặt; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:89 · Script chạy thử tắt D6 như replay_payload; phiên đọc danh sách ảnh của sổ gói (có dạng/vật) thay vì ánh xạ Image N (không có) — bỏ sót G27; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:90 · diag `subjects` jobs 1047, 1049–1051, 1054 (code 1110); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:15 · `core/assets.py:_named_extras` (1815–1855) khớp `names_of(a)` trong text + image_prompt. Bí danh #443 = *"flying black corpse, floating corpse, levitating corpse, cái xác biết bay"*. Phiên này bỏ "floating corpse" khỏi prompt shot 23 (để qua bộ lọc OpenAI) → job 993 KHÔNG gửi ảnh #443 (job 967 trước; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:16 · `core/sent_package.py:124 _meta_index` khóa theo basename — Kho đặt tên `1.png/2.png/3.png` ở mọi mục → ảnh #443/2.png ghi nhãn "SKORP", #367/2.png ghi "SKORP", #425/3.png ghi "KELLY". Prompt gửi model vẫn ĐÚNG (shot 24: *"Image 5 is the object XÁC ĐEN BIẾT BAY"*) — chỉ sổ sai; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:558 · N6 (dùng `speaker_lint.is_narrator`); docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:559 · N4 cùng G13: ngân sách ký tự theo khối, ưu tiên câu bắt buộc; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:563 · N1 (G30); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:19 · `core/assets.py:1830` bỏ ref súng khi `prop_lock.is_pov` (luật #27 "FF không có POV cầm súng") → shot 15 POV bắn: model vẽ súng đen thường, mất hào quang đỏ. 16/17 có ref SKORP (#433/2.png là SKORP đen) nhưng câu prompt chỉ ghi "red-glowing" ngắn → màu đỏ yếu/mất; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:40 · đã xử lý trong dự án: Vị trí đặt bằng nền 3D, không bằng prompt: ghép trời in-game vào plate (alpha `raw.png`, mắt xoáy đặt theo đỉnh tháp đo trên ảnh) — script scratchpad `p33_sky_composite3.py`; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:45 · đã xử lý trong dự án: Cắt đầu clip khi dựng; S4/S6 làm file ref mới: thay khúc chuyển cảnh bằng khung đội hình tua ngược, giữ độ dài/nhịp nhạc

### t.genimg — GEN ẢNH (CLIPAI)

- Loại dòng: nút trường
- Màu: xanh
- Khâu liên quan: L9
- Phân loại: LOI
- Lý do: có bằng chứng, việc kế hoạch xong
- Việc kế hoạch: M2.7 (✅)
- Lỗi đang mở: P31-G19 — Ảnh khung đầu vẽ trạng thái CUỐI thay vì ĐẦU của shot [OPEN] → M2.7, P31-G40 — ảnh khung đầu đã duyệt 1000 vốn KHÔNG có trời và KHÔNG có tháp (tường sương dày) dù image_prompt ghi "tower visible in the background"; motion đòi trời nhưng Seedance bám ảnh. Thêm: shot 29 là shot 2 của nhóm nên clip kh [OPEN] → M3.3, P31-G48 — ảnh 1090 vẽ tường thành khối hộp hai mặt vuông góc, khác tấm cong ở 35 (1094) → chữ 36: "SAME curved wall … ONE thin continuous curved panel … never a box". [OPEN] → M3.4, P33-A5 — QC lớp 0 đo nhầm cỡ cảnh ảnh S2 (bố cục sau lưng nhóm: đo mặt con tím ở xa → "WS, shot xin MS") → tự tạo job gen lại ép "từ thắt lưng trở lên" [FIXED_UNVERIFIED] → M4.5
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G19, P31-G40, P31-G48, P33-A5**
- Khâu đề xuất: L9
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G19, P31-G40, P31-G48, P33-A5
- Bằng chứng: có bằng chứng, việc kế hoạch xong; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:74 · Shot 1, 2: ảnh đã thấy 2 cửa trong khi shot là "quay người dần lộ 2 cửa"; shot 4: ý đồ qua vai thấy 2 cửa, ảnh không thấy. Gốc: prompt ảnh tả cả hành động ("camera turning to reveal two doors") → model vẽ kết quả. Liên quan G11; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:27 · tạm: Hủy job tự gen, đổi size shot sang WS

### t.genvid — GEN VIDEO (CLIPAI)

- Loại dòng: nút trường
- Màu: xanh
- Khâu liên quan: L13
- Phân loại: LOI
- Lý do: có bằng chứng, cờ bật
- Lỗi đang mở: P31-G15 — Mục cũ trong lipsync index không dọn khi method đổi về "skip" [OPEN] → M2.9, P31-G16 — QC đo clip coi shot chỉ có lời dẫn là "đang nói" [OPEN] → M2.9, P31-G17 — `quality_tier.py:177` coi `lip_sync is True` là có khớp môi trước `method_for` [OPEN] → M2.9, P31-G20 — Cổng ảnh→video báo nhầm "lệch nền 3D" khi ảnh không có/ít trời [OPEN] → M3.5, P31-G28 — Clip Seedance chế độ ảnh tham chiếu không bắt đầu đúng khung đầu đã duyệt; video prompt không mang câu bầu trời [OPEN] → M2.8, P31-G32 — Seedance chặn 6/8 job "real person" (ảnh `content[5..7]`) → tự lùi sang Kling (1067–1072, 31 s ≈ 2,70 USD) [FIXED_UNVERIFIED] → M1.5, P31-G36 — Tạm dừng dự án không chặn job đang chuẩn bị dở; thử lại sau khi bị từ chối lần đầu vẫn đi Seedance [IN_PROGRESS] → M1.3, P31-G37 — Shot 28 (nhóm 28+29) Seedance vẽ Kelly áo vàng, mất dạng bóng mờ ngay khung đầu; Kling cùng đầu vào giữ bóng mờ [OPEN] → M2.8, P31-G51 — Chấm 12 clip nháp 19/10 tối: 13 đơ 6 s; 16 địch không phản ứng, Kelly đơ; 18 máy Kling xuyên rào + địch gục vẫn bắn; 19 xoay 180° lố + áo đổi sọc; 29 súng biến mất 1–2,5 s; 35 mặt anime + 1 s cuối trống; 36 chạy tại chỗ, [OPEN] → M4.2, P31-G52 — QC logic chuỗi 39 clip (`scripts_19-10/qc_sequence/result.json`): độ cao nền đổi giữa shot 9→13; S10/11/13 nhặt súng trên thềm cỏ cao; bắn khi đã hết địch (18, 19); tường keo có trước khi ném (35); cửa shot 24 khác 23/25 [OPEN] → M4.3, P33-A1 — Job ảnh/clip succeeded 2 lần (`InvalidTransition succeeded -> succeeded`), lần sau đọc ảnh chưa ghi xong → QC lớp 0 `FileNotFoundError` → tự gen lại (thừa 0,05 USD job 1162→1163) [FIXED_UNVERIFIED] → M1.2, P33-A11 — `end_frame_skill_object` báo "ném keo" 28 lần ở #33 (không có tường keo): thông điệp viết cứng ở `core/runner.py:1433`, nhận mọi lý do từ `end_frames.skip_reason` [OPEN] → M2.9, P33-A15 — `download_error` PermissionError WinError 32 (tệp bị tiến trình khác giữ) [FIXED_UNVERIFIED] → M1.2, P33-B9 — Seedance ref-only không giữ khung ảnh đầu, theo khoảng cách máy của ref → S6 hàng con rối nhỏ hơn mèo [OPEN] → M2.8, V21-R3 — `qc_observe` raise khi `vat` là chuỗi (qc_observe.py:62–64) [FIXED_UNVERIFIED] → M1.1
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G15, P31-G16, P31-G17, P31-G20, P31-G28, P31-G32, P31-G36, P31-G37, P31-G51, P31-G52, P33-A1, P33-A11, P33-A15, P33-B9, V21-R3**
- Khâu đề xuất: L13
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G15, P31-G16, P31-G17, P31-G20, P31-G28, P31-G32, P31-G36, P31-G37, P31-G51, P31-G52, P33-A1, P33-A11, P33-A15, P33-B9, V21-R3
- Bằng chứng: có bằng chứng, cờ bật; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:63 · `runner.py:2214–2250`, `lipsync.mark` chỉ ghi thêm → `synced_scene_ids` sai khi gen lại; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:64 · `core/claude_tasks.py:323` `speaking = bool(data.get("dialogue"))`; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:65 · shot chỉ lời dẫn mà Đạo diễn gắn lip_sync → tính shot khó; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:75 · S22 (trong phòng) và S39 (từ trên cao): cổng so đường chân trời ở 7 % / 14 % khung — ảnh khớp bố cục nền 3D (xem ảnh so sánh) nhưng không lộ trời; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:86 · `framing_guard` ĐỎ nhiều clip (vd job 1043 "khung 0 khác hẳn ảnh đầu, khớp 22/3232 điểm"); S16 mở đầu Kelly nằm ở xa, mất trời có bóng ma; S29 trời sương xám như nền 3D; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:101 · `job_events` 1057/1058/1059/1060/1063/1064/1065/1066: `InputImageSensitiveContentDetected.PrivacyInformation`; diag `subjects`: "Kho chủ thể ClipAI đầy (100/100) … gửi ảnh như cũ (đánh dấu)"; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:110 · Tạm dừng 03:42:31 (`ui_actions`), job 1075 running Kling 03:42:41; 1061→1073 và 1062→… lần thử lại đầu vẫn bị Seedance chặn real_person rồi mới sang Kling (sáng: 1057→1065→1071); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:120 · bảng `p31_kling_vs_seedance_8shot.jpg`; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:556 · N7; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:557 · N3 + E cross-shot (`qc_sequence_logic`, cờ TẮT); docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:23 · tạm: Tiến trình riêng chỉ `submit_pending`, để Dashboard poll; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:564 · N4: thông điệp theo lý do thật; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:568 · N1 cùng A1; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:46 · đã xử lý trong dự án: Câu khóa cỡ khung chỉ giúp S4; S6 CHƯA đạt; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:260 · ĐANG XẢY RA (18/10: `qc_observe_enum` BẬT ở máy chính; #31 shot 30 `vat=["AWM"]`)

### t.qc — QC + DUYỆT NGƯỜI DÙNG

- Loại dòng: nút trường
- Màu: xanh
- Khâu liên quan: L9, L13
- Phân loại: LOI
- Lý do: có bằng chứng
- Lỗi đang mở: P31-G15 — Mục cũ trong lipsync index không dọn khi method đổi về "skip" [OPEN] → M2.9, P31-G16 — QC đo clip coi shot chỉ có lời dẫn là "đang nói" [OPEN] → M2.9, P31-G17 — `quality_tier.py:177` coi `lip_sync is True` là có khớp môi trước `method_for` [OPEN] → M2.9, P31-G19 — Ảnh khung đầu vẽ trạng thái CUỐI thay vì ĐẦU của shot [OPEN] → M2.7, P31-G20 — Cổng ảnh→video báo nhầm "lệch nền 3D" khi ảnh không có/ít trời [OPEN] → M3.5, P31-G28 — Clip Seedance chế độ ảnh tham chiếu không bắt đầu đúng khung đầu đã duyệt; video prompt không mang câu bầu trời [OPEN] → M2.8, P31-G32 — Seedance chặn 6/8 job "real person" (ảnh `content[5..7]`) → tự lùi sang Kling (1067–1072, 31 s ≈ 2,70 USD) [FIXED_UNVERIFIED] → M1.5, P31-G36 — Tạm dừng dự án không chặn job đang chuẩn bị dở; thử lại sau khi bị từ chối lần đầu vẫn đi Seedance [IN_PROGRESS] → M1.3, P31-G37 — Shot 28 (nhóm 28+29) Seedance vẽ Kelly áo vàng, mất dạng bóng mờ ngay khung đầu; Kling cùng đầu vào giữ bóng mờ [OPEN] → M2.8, P31-G40 — ảnh khung đầu đã duyệt 1000 vốn KHÔNG có trời và KHÔNG có tháp (tường sương dày) dù image_prompt ghi "tower visible in the background"; motion đòi trời nhưng Seedance bám ảnh. Thêm: shot 29 là shot 2 của nhóm nên clip kh [OPEN] → M3.3, P31-G48 — ảnh 1090 vẽ tường thành khối hộp hai mặt vuông góc, khác tấm cong ở 35 (1094) → chữ 36: "SAME curved wall … ONE thin continuous curved panel … never a box". [OPEN] → M3.4, P31-G51 — Chấm 12 clip nháp 19/10 tối: 13 đơ 6 s; 16 địch không phản ứng, Kelly đơ; 18 máy Kling xuyên rào + địch gục vẫn bắn; 19 xoay 180° lố + áo đổi sọc; 29 súng biến mất 1–2,5 s; 35 mặt anime + 1 s cuối trống; 36 chạy tại chỗ, [OPEN] → M4.2, P31-G52 — QC logic chuỗi 39 clip (`scripts_19-10/qc_sequence/result.json`): độ cao nền đổi giữa shot 9→13; S10/11/13 nhặt súng trên thềm cỏ cao; bắn khi đã hết địch (18, 19); tường keo có trước khi ném (35); cửa shot 24 khác 23/25 [OPEN] → M4.3, P33-A1 — Job ảnh/clip succeeded 2 lần (`InvalidTransition succeeded -> succeeded`), lần sau đọc ảnh chưa ghi xong → QC lớp 0 `FileNotFoundError` → tự gen lại (thừa 0,05 USD job 1162→1163) [FIXED_UNVERIFIED] → M1.2, P33-A11 — `end_frame_skill_object` báo "ném keo" 28 lần ở #33 (không có tường keo): thông điệp viết cứng ở `core/runner.py:1433`, nhận mọi lý do từ `end_frames.skip_reason` [OPEN] → M2.9, P33-A15 — `download_error` PermissionError WinError 32 (tệp bị tiến trình khác giữ) [FIXED_UNVERIFIED] → M1.2, P33-A5 — QC lớp 0 đo nhầm cỡ cảnh ảnh S2 (bố cục sau lưng nhóm: đo mặt con tím ở xa → "WS, shot xin MS") → tự tạo job gen lại ép "từ thắt lưng trở lên" [FIXED_UNVERIFIED] → M4.5, P33-B9 — Seedance ref-only không giữ khung ảnh đầu, theo khoảng cách máy của ref → S6 hàng con rối nhỏ hơn mèo [OPEN] → M2.8, V21-R3 — `qc_observe` raise khi `vat` là chuỗi (qc_observe.py:62–64) [FIXED_UNVERIFIED] → M1.1
- Việc đề xuất thêm vào plan: **Xác minh lỗi mở bằng bằng chứng chạy thật: P31-G15, P31-G16, P31-G17, P31-G19, P31-G20, P31-G28, P31-G32, P31-G36, P31-G37, P31-G40, P31-G48, P31-G51, P31-G52, P33-A1, P33-A11, P33-A15, P33-A5, P33-B9, V21-R3**
- Khâu đề xuất: L9
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G15, P31-G16, P31-G17, P31-G19, P31-G20, P31-G28, P31-G32, P31-G36, P31-G37, P31-G40, P31-G48, P31-G51, P31-G52, P33-A1, P33-A11, P33-A15, P33-A5, P33-B9, V21-R3
- Bằng chứng: có bằng chứng; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:63 · `runner.py:2214–2250`, `lipsync.mark` chỉ ghi thêm → `synced_scene_ids` sai khi gen lại; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:64 · `core/claude_tasks.py:323` `speaking = bool(data.get("dialogue"))`; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:65 · shot chỉ lời dẫn mà Đạo diễn gắn lip_sync → tính shot khó; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:74 · Shot 1, 2: ảnh đã thấy 2 cửa trong khi shot là "quay người dần lộ 2 cửa"; shot 4: ý đồ qua vai thấy 2 cửa, ảnh không thấy. Gốc: prompt ảnh tả cả hành động ("camera turning to reveal two doors") → model vẽ kết quả. Liên quan G11; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:75 · S22 (trong phòng) và S39 (từ trên cao): cổng so đường chân trời ở 7 % / 14 % khung — ảnh khớp bố cục nền 3D (xem ảnh so sánh) nhưng không lộ trời; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:86 · `framing_guard` ĐỎ nhiều clip (vd job 1043 "khung 0 khác hẳn ảnh đầu, khớp 22/3232 điểm"); S16 mở đầu Kelly nằm ở xa, mất trời có bóng ma; S29 trời sương xám như nền 3D; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:101 · `job_events` 1057/1058/1059/1060/1063/1064/1065/1066: `InputImageSensitiveContentDetected.PrivacyInformation`; diag `subjects`: "Kho chủ thể ClipAI đầy (100/100) … gửi ảnh như cũ (đánh dấu)"; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:110 · Tạm dừng 03:42:31 (`ui_actions`), job 1075 running Kling 03:42:41; 1061→1073 và 1062→… lần thử lại đầu vẫn bị Seedance chặn real_person rồi mới sang Kling (sáng: 1057→1065→1071); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:120 · bảng `p31_kling_vs_seedance_8shot.jpg`; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:556 · N7; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:557 · N3 + E cross-shot (`qc_sequence_logic`, cờ TẮT); docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:23 · tạm: Tiến trình riêng chỉ `submit_pending`, để Dashboard poll; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:564 · N4: thông điệp theo lý do thật; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:568 · N1 cùng A1; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:27 · tạm: Hủy job tự gen, đổi size shot sang WS; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:46 · đã xử lý trong dự án: Câu khóa cỡ khung chỉ giúp S4; S6 CHƯA đạt; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:260 · ĐANG XẢY RA (18/10: `qc_observe_enum` BẬT ở máy chính; #31 shot 30 `vat=["AWM"]`)

### t.audio — ÂM THANH & DỰNG

- Loại dòng: nút trường
- Màu: vàng
- Khâu liên quan: L14, L15
- Phân loại: LOI, LONG
- Lý do: lỏng: chỉ người / chỉ theo nút / bỏ qua được (mốc 17/10)
- Việc kế hoạch: M6.8 (⬜)
- Lỗi đang mở: P31-G14 — Nút "⏱ Đặt thời lượng theo giọng thật" kéo dài MỌI shot có lời dẫn [OPEN] → M2.9, P31-G42 — Lời dẫn đi trước hình: shot 36 đọc "…tụi nó thì đứng cười hở nách ăn mừng" khi Kelly còn chạy; ngã ở 37, ăn mừng ở 38 (38 không có lời) [OPEN] → M4.3, P33-B11 — Bản ghép ref 1080×2730 quá khung TikTok; cắt khung con rối quá cao → thấp đầu [OPEN] → M5.2
- Việc đề xuất thêm vào plan: **Tiếp tục M6.8 và chốt tiêu chí cho t.audio**
- Khâu đề xuất: L14
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; khâu đang vàng (chỉ người, cờ tắt hoặc thiếu bước kiểm tự động); mã lỗi: P31-G14, P31-G42, P33-B11
- Bằng chứng: lỏng: chỉ người / chỉ theo nút / bỏ qua được (mốc 17/10); docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:62 · `voice.fit_durations` kéo 17 shot (S10 1,3→8 s, S24 1→7 s) — đổi nhịp phim + tăng tiền video, không hỏi; chỉ 3 shot (6, 12, 31) thật sự bị chặn đỏ; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:135 · dialogue 36/38; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:48 · đã xử lý trong dự án: 1080×1920: ref 760×570 + nền mờ, con rối 1080×1350 cắt theo từng shot

### t.measure — ĐO TRƯỚC / SAU

- Loại dòng: nút trường
- Màu: tím
- Khâu liên quan: NEN
- Phân loại: LOI
- Lý do: việc M5.3 đang làm
- Việc kế hoạch: M5.3 (🔄)
- Lỗi đang mở: P31-G31 — Chi Claude vượt mức dự tính dự án [OPEN] → M1.6, P31-G33 — Claude API hết tiền giữa đợt (01:08) [IN_PROGRESS] → M1.4, P31-G39 — Sửa lỗi của phiên: gọi `regen.regenerate_video(p, 'data', …)` sai data_dir → thùng rác tạo ở `data/31/trash` [OPEN] → M1.7, P31-G55 — Dashboard cũ (8503/8504) chạy core cũ sau khi cập nhật code → lỗi `FAIL_SOURCE` (TODO 19/10) [OPEN] → M1.7, P31-G56 — Diag lặp gây nhiễu: `change_review_hold` 4 435 lần, `plate_stale` 337 lần (15–18/10) [OPEN] → M1.7, P31-G57 — Tiến trình riêng không có provider: `director_rewrite_fallback` "Chưa cấu hình Claude" (18/10), `bg_autoqc_stuck` 13 lần [IN_PROGRESS] → M1.4, P33-A13 — Claude Code hết lượt gói ("You've hit your session limit · resets 4:20am") — 18 lần D6 lỗi, xử lý như lỗi thường [FIXED_UNVERIFIED] → M1.4, P33-A14 — Ngân sách: trích riêng dự án #33 = 0 USD (hàng chung đợt thử đã hết), cảnh báo "mức dự tính $0.00"; đợt thử 480p vượt trần 90 USD — chỉ cảnh báo [OPEN] → M1.7, P33-A3 — `claude -p` báo "Credit balance is too low" / "session limit" [FIXED_UNVERIFIED] → M1.4, P33-A7 — Giá lệch: video nháp sổ chi ≈ 1,37 × bảng giá (phụ phí video ref chưa có trong `cost.clip_price`); bản cao 1080p sổ chi cao hơn `final_estimate` ~24 % → chạm trần `--max-usd` giữa chừng [OPEN] → M1.6, P33-A8 — Nút Gen video báo 9,13 USD (tính mức 720p + D6 Claude API) trong khi gửi nháp 480p [OPEN] → M1.6, P33-A9 — `pregen_check` cộng ≈ 1 USD Claude (D6 + QC) theo giá API dù chạy claude_cli; không ước tính giá video [OPEN] → M1.6, V31-R2 — Gọi Anthropic API ngoài ý muốn / Tổ rà soát lỗi [FIXED_UNVERIFIED] → M1.4
- Việc đề xuất thêm vào plan: **Tiếp tục M5.3 và chốt tiêu chí cho t.measure**
- Khâu đề xuất: chưa xác định
- Lý do đề xuất: còn lỗi chưa được xác minh; cần đối chiếu trạng thái lỗi với bằng chứng chạy thật; mã lỗi: P31-G31, P31-G33, P31-G39, P31-G55, P31-G56, P31-G57, P33-A13, P33-A14, P33-A3, P33-A7, P33-A8, P33-A9, V31-R2
- Bằng chứng: việc M5.3 đang làm; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:91 · `money_warning`: Claude ≈ 25,5 USD / mức 14,5 (D6 ≈ 0,04–0,09 USD/job) — chỉ cảnh báo; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:102 · `chat_prompt_fail` 1058/1069: HTTP 400 credit balance too low; đã chi ≈ 26,31 USD / mức 14,5; docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:122 · đã chuyển về đúng chỗ + gộp trash.json; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:560 · N1: Dashboard ghi sha code lúc khởi động, lệch HEAD → băng cảnh báo "khởi động lại" · 20/10 thực tế: 2 Dashboard cũ cổng 8503/8504 chạy code cũ cả ngày; tools/stop_dashboard.ps1 chỉ tắt 8501 → phiên chính tắt tay lúc C3-0 (hộp thư 20/10 18:08); docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:561 · N1: gộp theo (code, scene) như `_diag_once`; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:562 · N1 cùng A2; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:566 · N1: coi như `out_of_credit` có giờ mở lại, dừng khâu Claude tới giờ đó; docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md:567 · N2: trích dự án thiếu → chặn kèm lý do, không cảnh báo mãi; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:25 · tạm: `os.environ.pop('ANTHROPIC_API_KEY')` sau `load_env`; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:29 · tạm: Báo giá theo hệ số thực tế; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:30 · tạm: Tính tay theo 480p; docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md:31 · tạm: Ghi chú khi báo giá; docs/V3_1_GOI_SUA_VA_RUI_RO_2026-10-20.md:215 · Claude (audit, gói) · người dùng (env máy chính, không mở chặn hết tiền)

## Rà bằng chứng code thật và lưu ý diễn giải

Bản này được dựng chỉ đọc từ sơ đồ, kế hoạch và sổ lỗi trong worktree; không ghi ngược vào kế hoạch hoặc sổ lỗi.

- **Lỗ còn thật:** `kb.byd` vẫn đỏ vì dashboard chưa gọi `shot_intent.read`; hàm nguồn có tại `core/shot_intent.py:117`, nhưng bằng chứng đó chưa chứng minh đã nối vào giao diện. M4.7 còn hoạt động, nên giữ cảnh báo và đề xuất tiếp tục việc hiện có thay vì báo đã xong.
- **Bằng chứng sơ đồ đã hiệu chỉnh:** `t.writer` trỏ `core/idea_to_script.py:584` (`write`); `t.forms` trỏ `core/character_forms.py:66` (`for_shot`) và `core/seedance_refs.py:418`; `t.plate` trỏ `core/plate_anchor.py:107` (`landmark_facts`).
- **Lệch chưa được tự xóa:** L3, L4, L5 và L10 vẫn đỏ dù các việc gắn đã hoàn tất; cần kiểm tra các điều kiện/kiểm chứng còn thiếu trước khi đổi màu. L14 và các ô `kb.dialogue`, `kb.lock`, `sb.motion`, `bg.subs`, `bg.fx` chưa gắn việc kế hoạch; giữ trạng thái hiện tại và đề xuất bổ sung có chủ đích.
- **Cờ `loose`:** 14 ô vàng nay có `loose_until_plan`; chỉ hết vàng khi ít nhất một việc liên kết có trạng thái `✅`. Mục không có việc liên kết vẫn vàng để không tự xóa cảnh báo. Logic nằm tại `devsys/pipeline_maps.py:107`.
- **Phạm vi đề xuất:** đây là đầu vào để phiên chính xem xét cập nhật plan; báo cáo và trang Đối soát không tự sửa plan hay đóng lỗi.
