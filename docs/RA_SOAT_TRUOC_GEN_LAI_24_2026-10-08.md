# Rà soát quy trình nhà máy trước khi gen lại #24 và trước khi chia sẻ Dashboard — 08–09/10/2026

Người dùng 08–09/10: bản cao #24 tệ hơn nháp; **quy trình phải chuẩn và đúng trước, không sửa theo từng dự án**. Khâu nào làm tốt
(ví dụ #22) phải thành **công thức chính** áp cho mọi dự án Free Fire. Trạng thái: **ĐỀ XUẤT — chờ duyệt**. Chi cho rà soát: 0 USD.

Người dùng đã chốt (09/10):
- Ảnh toàn cùng trục mỗi shot: **ưu tiên render 3D** (0 USD); ảnh AI vẽ lại chỉ xét khi đo được giống ≥ 80–90 %.
- Tiết chế chi tiết ghê: **cho mọi dự án Free Fire** (không để Đạo diễn tự chọn).

## 1. Phát hiện chính: #22 đẹp nhờ sửa tay, công thức không quay về hệ thống

| Đo trên CSDL | #22 Khủng Long Đỏ | #24 Teasing |
|---|---|---|
| Image prompt người/Claude **viết tay khóa lại** (`_user_locked`) | **8/9 shot** | 1/9 |
| Độ dài image prompt TB (phần Đạo diễn viết) | 779 ký tự | 493 |
| Độ dài motion prompt TB | 885 (lượt 2–3 sửa tay) | 558 (Đạo diễn + code) |
| Có `spatial_state` | 9/9 | 0/9 |

Các câu viết tay ở #22 làm nên chất lượng — **không câu nào có trong code tạo prompt** (đã grep `core/`, `prompts/`):
- Khóa nền: *"exactly as the 3D render, same camera and same spot as the previous shot"*.
- Khóa trang phục kể **từng món** theo ảnh OUTFIT + trạng thái phụ kiện (*"mask worn UP … never pulled down"*).
- Khóa tóc riêng của nhân vật khi ảnh OUTFIT có người mẫu (*"keeps Kelly's OWN hair … one solid colour"*).
- Ràng buộc vật lý động tác (*"feet never slide"*), máy quay nói rõ (*"Static camera"*), điểm kết.

Còn trong #24 (prompt thực gửi đi, dựng lại bằng `runner.build_image_prompt`):
- Câu địa điểm chung chung *"grass, palms, sea around"* trái với render 3D đang gửi kèm; prompt **không gọi tên ảnh render** là chuẩn nền.
- Mâu thuẫn trong cùng một prompt: shot 4 "trung cận, không thấy chân" + "ngồi bệt chống tay" + "khung đầu đang ngã, khuỵu gối".
- Motion shot 5: Đạo diễn ghi "mắt đỏ phát sáng" (yêu nữ), code tự gắn thêm *"Natural human eyes, no glowing eyes."* (`seedance_refs.py:673`, luật chống mắt phát sáng cho **người** áp mù cho **quái**) — một luật cũ đúng ở dự án cũ, sai ở dự án mới.
- Đạo diễn tự thêm "tóc + vết máu trên miệng giếng, everything in focus" (không luật tiết chế).
- 30 thay đổi rút từ #22 (KLD-1…34): khoảng 20 đã vào code ở mức nào đó, ~10 chưa (KLD-9/10/13/25/26/27-hồ sơ/30–34); bảng `lessons` chỉ 12 dòng; 84 ca kinh nghiệm #22 nằm trong `experience_cases` nhưng không thành công thức.

**Kết luận:** prompt hiện là **nhiều câu nối dần theo từng lỗi** (mỗi lỗi một câu thêm vào), không có **khuôn chuẩn** quy định "một prompt ảnh / motion phải có những phần nào, lấy từ đâu, kiểm bằng gì". Vì thế sửa lỗi ở dự án này không làm dự án sau tốt lên, và câu thêm cho dự án cũ có thể phá dự án mới.

## 2. Vì sao sửa nhiều mà vẫn lỗi (trả lời thẳng)
1. Sửa theo triệu chứng của shot đang thấy; test dựng từ dữ liệu shot đó → lỗi cùng gốc ở chỗ khác không bị bắt.
2. Không có **khuôn chuẩn** cho prompt → chất lượng phụ thuộc người sửa tay (#22) chứ không phụ thuộc hệ thống.
3. Không có **cổng kiểm đầu vào trước khi chi tiền**: thiếu nền 3D, mâu thuẫn trong prompt, đường nâng bản cao — chỉ ghi diag rồi vẫn gửi.
4. Luật mềm trong prompt Đạo diễn không có code kiểm; luật cứng của dự án cũ áp mù cho dự án mới.
5. Tính năng mới chạy thật lần đầu trên dự án thật, chưa chạy thử toàn tuyến 0 USD.
6. Bài học chỉ ghi lại (memory, báo cáo) chứ không thành công thức trong code.

## 3. Kế hoạch: "Công thức chuẩn" cho từng khâu (mọi dự án Free Fire)

### F0 — Sổ công thức (nguồn duy nhất), 0 USD
`knowledge/formula/` — mỗi khâu một file: **phần bắt buộc · lấy từ trường nào · câu mẫu · lý do · bằng chứng (dự án/shot) · cách code kiểm**. Rút từ: 8 image prompt viết tay #22, motion lượt 2–3 #22, 84 ca kinh nghiệm #22, bài học L1–L19, góp ý #24. Người dùng duyệt sổ trước khi code.

**Công thức ảnh khung đầu (dự kiến 9 phần):**
1. Phong cách FF in-game (cố định).
2. Khung hình: cỡ cảnh + góc + ống kính — **khớp** với tư thế (không "MCU" + "ngồi bệt thấy chân").
3. **Khóa nền**: "nền đúng ảnh render 3D số N (cùng máy quay); ảnh toàn cùng trục số M"; tỉ lệ vật mốc đo trên map (thành giếng cao bao nhiêu so với người); bỏ câu địa điểm chung khi có render.
4. Nối tiếp: shot cùng setup → "cùng máy, cùng chỗ đứng như shot trước".
5. Mỗi nhân vật: mặt/tóc từ hồ sơ chuẩn; trang phục **kể từng món** từ ảnh OUTFIT + trạng thái phụ kiện; vị trí trái/phải, hướng mặt, hướng nhìn.
6. Khoảnh khắc khung đầu: **một** trạng thái, khớp khung hình.
7. Luật FF cố định: tiết chế ghê (máu/tóc/xác chỉ gợi, trong tối, ngoài nét), không dưới 18 tuổi.
8. Ánh sáng theo cảnh, mặt đọc được.
9. Câu phủ định chuẩn (không phải still điện ảnh…).

**Công thức motion (dự kiến 8 phần):** máy quay (kiểu + khung giây đầu/cuối) · hành động từng nhân vật **điểm đầu → điểm cuối**, nhịp · đường đi vật chuyển động gần người (không chạm / không xuyên) · ràng buộc vật lý (chân không trượt…) · thứ đứng yên · khóa nhận dạng (đường ref-only) · trạng thái cuối · luật theo **loại nhân vật** (người / quái / thú — không áp luật của người cho quái).

Tương tự cho: Đạo diễn (trường bắt buộc mỗi shot), Quay phim (plate_view, trục, camera 3D hợp lý), QC ảnh/clip, nhạc, SFX, dựng, popup.

### F1 — Code theo công thức  — **phần 1 ✅ 09/10** (kiểm + chặn + sửa ghép; xem TODO); phần 2 ⬜ (ghép theo khuôn, prompt Đạo diễn)
- Prompt **được ghép từ khuôn** (từng phần một hàm, mỗi phần từ trường dữ liệu), thay cho nối câu dần; câu cũ rà một lượt: giữ / chuyển thành phần khuôn / bỏ (có lý do).
- **Kiểm công thức** trước khi gửi: thiếu phần bắt buộc, mâu thuẫn (khung ↔ tư thế, luật người ↔ quái, câu địa điểm ↔ render), từ ghê không tiết chế → báo đỏ ở thẻ shot, không gửi.
- Người sửa tay prompt → hệ thống so với khuôn, ghi phần nào người thêm/đổi vào **sổ đề xuất công thức** (học từ sửa tay, như #22) → người dùng duyệt → vào khuôn cho dự án sau.

### F2 — Nền 3D đúng trước khi gen (0 USD)
- Camera 3D vô lý (trong/sát vật, sát đất mà ngửa cao, chân trời ngoài khung) → tự đặt lại theo trục hoặc báo chọn lại.
- **Mỗi shot 3D: render ảnh toàn cùng trục** (lùi máy dọc trục, ống rộng) gửi kèm; thiếu render → không gửi ảnh.
- Kiểm tỉ lệ vật mốc giữa các shot.

### F3 — 2 bậc chất lượng đúng
- Nháp Seedance = **Seedance 2.5 chế độ nháp** để nâng 1080p giữ nội dung; không nâng được → hỏi rõ trước khi gen mới.
- Không để bản cao ghi đè clip nháp của shot trong nhóm.

### F4 — Màn chọn model gọn
Mỗi shot một dòng "model · nháp → cao · giữ nội dung? · ≈ $"; một nút "Đổi" (model + độ phân giải + đường chất lượng gộp chung).

### F5 — Cổng "sẵn sàng gen" + chạy thử toàn tuyến
- Mỗi shot một ô kiểm (công thức đủ, nền 3D, ảnh toàn, tỉ lệ, model, giá) cạnh nút gen.
- **Chạy lại #22 và #24 bằng provider giả (0 USD)**: so prompt hệ thống tạo ra với prompt viết tay #22 — mục tiêu hệ thống tự tạo được prompt đạt mức #22 không cần sửa tay. Chạy Dashboard bằng trình duyệt như người dùng thật, sửa tới sạch.
- Danh sách "Còn tồn" + ~10 thay đổi KLD chưa làm: làm hoặc ghi rõ lý do để lại.
- Chuẩn bị nhiều người dùng: quyền, chạy đồng thời, trần tiền theo người, hướng dẫn 1 trang.

### Sau F0–F5 — gen lại #24
Đạo diễn chạy lại theo công thức (≈ 0,5–0,7 USD) hoặc giữ kịch bản và chỉ dựng lại prompt; nháp Seedance 2.5 480p → duyệt → nâng 1080p. Báo giá trước.

## 4. Cần người dùng chốt
1. Duyệt hướng F0 → F5 (sổ công thức duyệt trước, rồi mới code)?
2. F5: lấy **#22 viết tay làm chuẩn so** cho công thức ảnh/motion — đồng ý?
