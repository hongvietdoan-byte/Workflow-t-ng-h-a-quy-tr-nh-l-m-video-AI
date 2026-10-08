# Rà soát trước khi gen lại #24 và trước khi chia sẻ Dashboard — 08/10/2026

Người dùng 08/10 khuya: bản cao #24 tệ hơn nháp; cần sửa **mọi lỗi trước khi gen lại**, rồi rà soát để nhiều người cùng dùng được.
Trạng thái: **ĐỀ XUẤT — chờ người dùng duyệt**. Chưa sửa code ngoài phần nhạc kinh dị (commit 70fd1a9). Đã chi cho việc này: 0 USD.

## 1. Năm góp ý và nguyên nhân đo trên dữ liệu thật

| # | Góp ý | Nguyên nhân (bằng chứng) |
|---|---|---|
| 1a | Bóng đen bay xuyên vào người Kelly (shot 3 bản cao) | Motion/image prompt chỉ ghi "streaking fast across the well mouth right in front of her face" — không nói đường bay, không cấm chạm/xuyên người. Không có luật nào kiểm đường đi của vật chuyển động so với nhân vật. |
| 1b | Miệng giếng thấy rõ tóc + máu, ghê | Đạo diễn tự viết vào image_prompt shot 2: "black hair strands and blood stains on the rim … everything in focus". Không có luật tiết chế chi tiết ghê (máu, tóc rối, xác) — phải gợi, mờ, trong tối. |
| 2 | Shot 4 (Kelly ngã) thành giếng thấp hơn các shot khác | Job ảnh 579 **không gửi render 3D** (sent_refs không có place_render). Máy quay 3D đặt ở chỗ vô lý: cách Kelly 0,97 m về phía giếng, cao 0,45 m trên đất, ngửa 45° → render chỉ thấy trời (horizon_y 1,9); bị đánh "nền một màu" (diag plate_flat 11:59) → bỏ, ảnh vẫn được gửi **không có nền 3D**, model tự đoán tỉ lệ giếng. |
| 3 | Mỗi shot cần ảnh toàn cùng trục/góc với shot để nền giống 3D ~90 % | Kỹ năng **có một phần**: (a) mỗi shot có render 3D riêng theo camera của shot (#24 có 9/9, trừ shot 4 hỏng); (b) ảnh toàn cảnh chỉ **một ảnh cho cả cảnh kịch bản** = render của shot rộng nhất (KLD-18, `place_refs.scene_render_rec`), cờ `scene_establishing` đang TẮT → #24 **không gửi ảnh toàn nào**. Luật "mỗi shot một ảnh toàn cùng trục" ghi ở memory 07/10 nhưng **chưa thành code**. |
| 4 | Chọn model: người dùng phải thấy model gì, chất lượng bao nhiêu, tự đổi được, không thêm rối | Bản nháp #24 làm bằng alias `seedance` = **Seedance 2.0** → bản cao không nâng được từ nháp, hệ thống **tự gen mới** (diag `final_resend` mức info, không hỏi) → nội dung khác nháp, 720p. Màn Model (Bước 4) không nói "nháp này nâng lên bản cao được hay không". |
| 5 | Sửa nhiều mà vẫn lỗi, sản phẩm chưa đạt | Xem mục 2. |

## 2. Vì sao sửa nhiều mà vẫn phát sinh lỗi và sản phẩm chưa đạt (trả lời thẳng)

1. **Sửa theo triệu chứng của shot đang thấy.** 08/10 có 111 commit, 21 commit cho #24; mỗi lỗi có test, nhưng test dựng từ dữ liệu của chính shot đó. Một lỗi cùng gốc ở chỗ khác (shot 4 không có nền 3D, đường nâng bản cao) không bị bắt.
2. **Chưa có cổng kiểm "đầu vào đủ chưa" trước khi chi tiền.** Ảnh shot 4 được gửi khi thiếu nền 3D; bản cao được gửi khi không nâng được từ nháp — cả hai chỉ ghi một dòng diag rồi vẫn chạy. Lỗi chất lượng (tỉ lệ, ghê, xuyên người) không phải lỗi code nên test không bắt; phải kiểm **từng shot trước khi gen**.
3. **Luật mềm trong prompt Đạo diễn không có code kiểm** (đã ghi 25/09: "luật mềm không có code kiểm thì không có tác dụng"). Luật tiết chế ghê, đường đi vật chuyển động, ảnh toàn cùng trục chưa có code.
4. **Nhiều tính năng chạy thật lần đầu trên #24**: 2 bậc chất lượng, hướng nền `plate_view`, popup cuối, ghép tiếng ref. Lần đầu chạy thật luôn lộ lỗi; đáng lẽ phải chạy thử toàn tuyến **0 USD** (provider giả) trên Dashboard trước khi gen thật.
5. **Bài học nằm ở memory nhưng không vào hệ thống**: "ảnh toàn cùng trục" (07/10), "nháp rẻ rồi gen cao đúng cách đã đạt" (07/10) — ghi lại nhưng code không áp.

## 3. Kế hoạch (đề xuất)

### Đợt R0 — sửa đúng 5 góp ý, có test, 0 USD
- **R0.1 Tiết chế chi tiết ghê** (máu, tóc rối, vết thương, xác): Đạo diễn + `knowledge/roles/director.md` có luật (lý do: quảng bá game cho mọi lứa tuổi; ghê thì gợi bằng bóng tối, mờ, ngoài nét, khung che); code kiểm image/motion prompt có từ ghê mà thiếu cách tiết chế → tự thêm câu "chỉ thấy lờ mờ trong bóng tối, ngoài nét" + bỏ "everything in focus" ở shot đó; cảnh báo ở báo cáo Đạo diễn.
- **R0.2 Đường đi vật chuyển động gần nhân vật**: shot có vật/bóng lao qua sát nhân vật → motion prompt phải ghi điểm đầu → điểm cuối, khoảng cách, "không chạm / không xuyên qua người"; `motion_lint` kiểm, thiếu thì báo đỏ trước khi gửi.
- **R0.3 Máy quay 3D vô lý**: camera nằm trong / sát vật thể, cao < 0,8 m mà ngửa > 30°, horizon ngoài khung → tự đặt lại (lùi theo trục, hạ góc ngửa) hoặc báo người dùng chọn lại; **không gửi ảnh shot 3D khi thiếu render** (đợi / báo đỏ, không im lặng gửi trơn).
- **R0.4 Ảnh toàn cùng trục cho MỖI shot** (luật người dùng): mỗi shot 3D render thêm một ảnh toàn từ cùng trục, cùng hướng, camera lùi lại + ống kính rộng (0 USD, Blender) và gửi kèm như tham chiếu địa điểm; thay cách một ảnh cho cả cảnh. Ghi vào kỹ năng (`knowledge/craft/goc_may.md` + prompt) và thẻ ảnh Bước 2 hiện ảnh toàn của shot.
- **R0.5 Kiểm tỉ lệ vật mốc**: câu "Camera and scale, measured on the 3D map" (độ cao thành giếng so với người) gửi cho mọi shot có vật mốc; QC ảnh so tỉ lệ với render.

### Đợt R1 — 2 bậc chất lượng làm đúng
- Shot đi "nháp trước" mà model là Seedance → nháp bằng **Seedance 2.5 chế độ nháp** (nâng lên 1080p giữ nội dung).
- "⬆ Gen bản cao" khi không nâng được từ nháp: **hỏi rõ** "gen mới — nội dung sẽ khác nháp — X USD", không tự gửi.
- Clip nháp của shot thứ 2, 3 trong nhóm bị file bản cao ghi đè (cùng đường dẫn) → giữ lại nháp để "↩ Dùng bản này" dùng được.

### Đợt R2 — chọn model gọn (không thêm nút)
- Mỗi shot một dòng: **"Seedance 2.5 · nháp 480p → cao 1080p (giữ nội dung) · ≈ $X"**; một nút "Đổi" mở ô chọn model + độ phân giải (có ghi chú từng lựa chọn). Bỏ trùng lặp giữa ô Model và ô "Đường chất lượng" (gộp vào cùng ô Đổi).

### Đợt R3 — rà soát toàn tuyến trước khi chia sẻ
- **Cổng "sẵn sàng gen" cho từng shot** (code kiểm, hiện lý do đỏ cạnh nút gen): nền 3D có + đúng hướng, ảnh toàn cùng trục, tỉ lệ, luật ghê, đường đi, model nâng cấp được, ước giá.
- **Chạy thử toàn tuyến #24 bằng provider giả (0 USD) bằng trình duyệt như người dùng thật**: Kịch bản → Đạo diễn → ảnh → motion → video → âm thanh → nhạc → bản giao; ghi mọi lỗi, sửa, chạy lại tới sạch.
- Danh sách "Còn tồn" trong TODO (giá nút Gen video theo clip nhóm, test chập chờn Blender, ...) xử lý hết hoặc ghi rõ lý do để lại.
- Chuẩn bị nhiều người dùng: quyền, chạy đồng thời 2 người, trần tiền theo người, hướng dẫn ngắn 1 trang.

### Sau R0–R3 — gen lại #24
Nháp Seedance 2.5 480p cho các shot đổi đầu vào (ít nhất 2, 3, 4) → người dùng duyệt → nâng 1080p giữ nội dung. Báo giá trước khi gửi.

## 4. Cần người dùng chốt
1. Duyệt thứ tự R0 → R1 → R2 → R3 rồi mới gen lại #24?
2. R0.4: ảnh toàn cùng trục = **render 3D lùi camera** (0 USD, giống map 100 % hình khối nhưng không có ánh sáng/vật liệu đẹp) hay **ảnh AI vẽ từ render đó** (đẹp hơn, tốn tiền ảnh, ~70–90 % giống)?
3. R0.1: mức tiết chế — "gợi, không thấy rõ máu" cho mọi dự án, hay để Đạo diễn chọn theo độ tuổi/kênh?
