# Rà soát khâu làm việc ↔ khâu kiểm tra (10/10/2026)

Người dùng hỏi sau lỗi #24 shot 4 ("its dark mouth facing us" lọt qua mọi lớp): liệt kê khâu làm việc, vai kiểm soát, khâu chưa được
theo dõi, và khâu làm ↔ khâu kiểm đã đồng nhất chưa. Nguồn: sổ "Ai quyết" `devsys/decisions.json` (84 điểm), trạng thái cờ thật ở
`D:/AI-Video-Pipeline/data/feature_settings.json` lúc ghi, code `core/autoqc.py`, `core/runner.py`, sổ chi `usage_events` 10/10.

Ký hiệu trạng thái kiểm: ✅ chạy thật · 🎓 học việc (chạy, ghi, không tác động) · ⏸ có code nhưng cờ TẮT · 👤 chỉ người · ❌ không ai.

## 1. Các khâu làm việc (theo thứ tự sản xuất)

| # | Khâu làm | Ai làm | Sản phẩm | Tốn tiền |
|---|---|---|---|---|
| L1 | Ý tưởng → kịch bản (Biên kịch, chat) | Claude d04, s1447 | kịch bản | Claude |
| L2 | Bảng kê tài nguyên | Claude d07 (cờ asset_checklist TẮT) | danh sách vật/nơi | Claude |
| L3 | Chia shot, viết `image_prompt`, blocking, action… | Claude Director d09 (2 lượt) | bảng shot (CHỮ TỰ DO) | Claude |
| L4 | Thoại, chọn giọng | Claude d12, d15 + code d16 | thoại, giọng | Claude |
| L5 | Hồ sơ nhân vật / Lock / Bible | Claude d13, d14, d73 + người | hồ sơ Kho, ảnh mẫu | Claude |
| L6 | Sân khấu 3D: dàn cảnh + giải máy + render nền | Claude d82 + code (solver, Blender) | `stage_camera`, render nền | Claude nhỏ |
| L7 | Storyboard / ảnh neo | code + model ảnh (storyboard_api BẬT) | ảnh neo, phiên storyboard | Ảnh |
| L8 | **Lắp gói gửi model ảnh** (prompt cuối + ảnh tham chiếu + vai) | code `runner` | gói gửi | — |
| L9 | Gen ảnh khung đầu | model ảnh | ảnh | Ảnh |
| L10 | Gen lại ảnh (Đạo diễn viết lại prompt) | Claude d31 (BẬT) | prompt mới | Claude + Ảnh |
| L11 | Motion prompt + dịch | Claude d35, d37 | motion prompt | Claude |
| L12 | **Lắp gói gửi model video** (motion + khung đầu + ref + model) | code d41 | gói gửi | — |
| L13 | Gen video (2 bậc nháp → cao) | model video | clip | Video (đắt nhất) |
| L14 | TTS, nhạc, SFX, phụ đề | model + Claude d40, d51, d52 | âm thanh, chữ | có |
| L15 | Dựng, popup cuối, xuất bản | code + Claude d48 | bản giao | Claude |
| L16 | Thay đổi giữa chừng (sửa shot / Kho) | người + Claude | dữ liệu mới | — |

## 2. Các vai kiểm soát hiện có

| Vai kiểm | Loại | Kiểm cái gì | Trạng thái |
|---|---|---|---|
| K1 Kiểm dựng được (d06), IP (d18) | code | kịch bản: nơi có trong Kho, tên bị chặn | ✅ |
| K2 Đạo diễn duyệt bảng shot (d10), chuẩn hóa (d11) | code | trường bắt buộc, độ dài, cỡ | ✅ |
| K3 Người xem lần đầu (d17), story_check | Claude | truyện có hiểu được | ⏸ (story_check TẮT) |
| K4 Công thức prompt (`prompt_formula`) | code | prompt **đủ phần** (cấu trúc), không kiểm nghĩa | ✅ — *không có trong sổ "Ai quyết"* |
| K5 Sự thật hình học (`stage_facts`, 10/10) | code | câu trái hình học máy 3D; câu nối vào prompt | ✅ mới — *chưa có trong sổ* |
| K6 Bộ kiểm tác động (`change_audit`) + Tổ rà soát (`change_review`, d83) | code + Claude | khi CÓ THAY ĐỔI: trường shot có khớp nhau | ✅ (bật 10/10) |
| K7 Khung "Trước khi chạy" (`before_run`) | code | cờ tốn tiền, thứ giữ việc, đầu vào thiếu | ✅ mới — *chưa có trong sổ* |
| K8 Rà storyboard previz (d22) | Claude | trục, liên tục, bố cục | theo nút |
| K9 Cổng tiền (d54), ngân sách dự án | code | ước tính + cảnh báo | ✅ (chỉ cảnh báo) |
| K10 QC ảnh lớp 0 (d24) | code | cỡ cảnh, mặt, sáng | ⏸ (scene_qc TẮT) |
| K11 QC ảnh lớp 1 theo cảnh (d28) | Claude | ảnh ↔ bảng shot | ⏸ (scene_qc_claude TẮT) |
| K12 Tổ QC (d26, d79) | Claude enum + code | mệnh đề từ bảng shot | 🎓 / ⏸ (qc_team TẮT) |
| K13 QC tự động từng ảnh (`autoqc`, d28 cũ) | Claude | ảnh ↔ ảnh mẫu | không chạy khi dự án ở chế độ `human_qc` (#24) |
| K14 QC bố cục so render (`plate_layout_qc`) | code | chân trời, nét kiến trúc | ✅ nhưng MÙ với render đêm (sửa 10/10) |
| K15 Rà motion prompt (d36) | Claude | chữ motion | theo nút Bước 3, không phải cổng |
| K16 Đo clip (d42), QC clip (d43), chọn ⭐ (d45) | code + Claude | clip sau khi gen | ✅ (QC video tự chạy khi mở Bước 4) |
| K17 Kiểm TTS (d39) | code | cắt, im lặng, độ dài | ✅ |
| K18 Bản thô (d48, d49) | Claude + code | dựng | ⏸ (rough_cut_review TẮT) |
| K19 Người dùng (d05, d19, d33, d34, d46, d50) | người | mọi thứ | 👤 — **thực tế là cổng duy nhất của ảnh và video** |
| K20 Agent rà khâu liên quan (CLAUDE.md quy ước 7) | Claude | **CODE** khi Claude sửa code | ✅ — không nhìn dữ liệu sản xuất |

## 3. Bản đồ làm ↔ kiểm (khâu nào chưa được theo dõi)

| Khâu làm | Kiểm TRƯỚC khi trả tiền | Kiểm SAU khi có kết quả | Đánh giá |
|---|---|---|---|
| L1 kịch bản | K1 | 👤 d05 | đủ |
| L3 bảng shot / `image_prompt` | K2 (trường), K4 (cấu trúc), K5 (chỉ hình học, từ 10/10) | — | **❌ không ai kiểm NGHĨA prompt ↔ ý đồ kịch bản** (gốc lỗi shot 4) |
| L5 ảnh mẫu Kho | 👤 duyệt Kho | — | ⚠ ảnh mẫu đúng hình nhưng góc nhìn của ảnh mẫu không ai đối chiếu với máy của shot (sửa một phần bằng K5 `ref_viewpoint`) |
| L6 render nền 3D | code luật P/S/C của solver | director_plate_review (⏸) | ⚠ render có khối thay thế — chỉ K5 gọi tên (10/10) |
| L8 gói gửi model ảnh | K4 + K5 | — | **❌ không ai nhìn ĐÚNG gói sẽ gửi (prompt cuối + ảnh tham chiếu + vai)** |
| L9 ảnh | — | K10–K13 đều TẮT / không chạy ở human_qc; K14 mù với ảnh đêm | **❌ thực tế chỉ người (👤)** |
| L10 gen lại | K4 | 👤 so cũ/mới | ⚠ prompt viết lại không ai rà nghĩa |
| L11 motion prompt | K15 theo nút | — | ⚠ không phải cổng, không thấy khung đầu |
| L12 gói gửi model video | — | — | **❌ không ai kiểm (khâu ĐẮT nhất)** |
| L13 clip | — | K16 + 👤 | có, nhưng là SAU khi đã trả tiền |
| L14 âm thanh, chữ | K17 (TTS) | 👤 | phụ đề / SFX chỉ người |
| L15 dựng, popup | — | K18 TẮT, 👤 | chỉ người |
| L16 thay đổi | K6 (từ 10/10) | — | có — nhưng không xem gói cuối, không xem ảnh |

**Khâu chưa được theo dõi / quản lý:** (1) nghĩa của prompt ảnh so với ý đồ; (2) gói gửi model ảnh; (3) gói gửi model video;
(4) kết quả ảnh — không có QC máy nào đang chạy thật; (5) prompt viết lại khi gen lại; (6) dựng/phụ đề/SFX. Và **sổ "Ai quyết" thiếu**
các khâu code mới: `prompt_formula`, `stage_facts`, `before_run`, giải máy sân khấu 3D, render nền, `end_popup` — test của sổ chỉ bắt
buộc liệt kê khâu Claude, không bắt buộc khâu code.

## 4. Làm và kiểm đã đồng nhất chưa — CHƯA

1. **Khác ngôn ngữ.** Đạo diễn viết **chữ tự do** (`image_prompt`, `blocking`, `action`); mỗi lớp kiểm tự đọc lại chữ bằng mẫu từ riêng
   (`prompt_formula`, `qc_spec`, `stage_facts.contradictions`, `change_audit`) → mỗi nơi một cách hiểu, hay bắt nhầm hoặc lọt
   (vd mẫu 'into' bắt nhầm "looking into the camera", 10/10). Không có **bảng ý đồ có cấu trúc** chung cho cả người làm lẫn người kiểm.
2. **Kiểm sai đối tượng.** Thứ thật sự gửi cho model là *gói* (prompt cuối + ảnh + vai); các lớp kiểm nhìn *một phần*: `change_review`
   xem trường shot, `prompt_formula` xem chữ không xem ảnh, QC xem kết quả không xem prompt.
3. **Kiểm sau khi đã trả tiền.** Lớp kiểm mạnh nhất (QC) đứng sau gen; trước gen chỉ có kiểm cấu trúc.
4. **Kiểm đang tắt.** Các QC máy cho ảnh đều TẮT/học việc → người dùng là cổng duy nhất; mỗi lỗi người bắt được lại sửa thành một
   luật lẻ thay vì một loại kiểm có đủ "làm ↔ kiểm".
5. **Bài học không thành cơ chế.** Cách "model khai điều thấy, code kết luận" (01/10) chỉ áp cho trái/phải và mũ; 10/10 mới thành sổ FACTS.

## 5. Đề xuất để đồng nhất (thứ tự)

1. **Bảng ý đồ shot có cấu trúc** (Đạo diễn điền: ai trong khung, làm gì, thấy vật nào / phần nào, cảm xúc, máy) — chữ prompt SINH từ bảng
   + câu sự thật code nối; mọi lớp kiểm đọc CÙNG bảng (không đọc lại chữ tự do). Chữ tự do chỉ còn là phần mô tả không kiểm được.
2. **Người duyệt gói gửi** (đã chốt: cả 2 lớp, học việc trước) — trước MỌI gen ảnh và video, nhìn đúng gói sẽ gửi, so với bảng ý đồ.
   **Gen lại (L10) đi qua cùng người duyệt** (người dùng 10/10: "tôi không thể đi soi từng chữ trong lệnh prompt"). Hiện
   `prompt_rewrite.propose_rewrite` chỉ kiểm: khác bản cũ, không thêm người lạ, gỡ chữ tả thực; từ 10/10 việc ghi `image_prompt` mới kích
   Tổ rà soát tác động (luật code + `stage_facts` + agent so trường/shot kề). CHƯA kiểm: (a) sửa đúng lỗi — tách ghi chú người dùng / lỗi
   QC thành ý, model khai đã xử lý / chưa / một phần, code quyết; (b) không thoái lui — code so bảng ý đồ + ý đã đạt ở ảnh trước với gói
   mới; (c) đổi đúng chỗ — lỗi do ảnh tham chiếu / render thì phải đổi ảnh hoặc vai ảnh, không chỉ đổi chữ. Người dùng chỉ thấy MỘT dòng
   tiếng Việt ("Gen lại lần 2 · sửa 'tư thế ngã' ✅ · giữ 7/7 ý ✅ · 0 câu trái hình học ✅"), không phải so chữ prompt; đỏ → Đạo diễn tự
   viết lại ≤ 2 lần rồi giữ, hỏi bằng nút kèm lý do.
3. **Mỗi khâu làm phải có một dòng "kiểm trước / kiểm sau / trạng thái"** trong sổ "Ai quyết" — mở rộng `devsys/decisions.json` thêm
   trường `checked_by` + test: khâu tốn tiền không có lớp kiểm TRƯỚC (đang chạy hoặc học việc) → test đỏ; thêm các khâu code đang thiếu.
4. **Bật lại QC máy cho ảnh theo lộ trình đo**: Tổ QC học việc trên dự án mới + bộ ca vàng (lỗi người dùng đã bắt), đạt ngưỡng mới chặn.
5. **Trang devsys "Làm ↔ Kiểm"**: hiện bảng mục 3 từ sổ, tự đỏ khi khâu không có kiểm.
