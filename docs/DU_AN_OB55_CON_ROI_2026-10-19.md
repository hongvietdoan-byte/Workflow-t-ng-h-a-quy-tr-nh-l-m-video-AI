# Dự án #33 "OB55 Halloween — Con rối nhảy Tháp đồng hồ (thế giới song song)" (19/10/2026)

Người dùng 19/10: clip các con rối nhảy theo video ref mèo; gen lại ảnh con rối chất lượng; 3 màu (được lặp 2 màu); nền = vị trí nhảy ở
Tháp đồng hồ **thế giới song song**; học cách làm từ #22 Khủng Long Đỏ. **Trạng thái: đã chuẩn bị xong (0 USD), DỪNG trước cổng gen ảnh.**

## 1. Đã làm (0 USD)
- Dự án **#33** (dọc 9:16, FF_INGAME, ảnh GPT Image 2.5, per_shot, `paused=1`). Tạo bằng chính các hàm lõi Dashboard gọi
  (`Pipeline.create_project`, `assets.add_reference_images`, `llm_io.add_character`, `create_scene`) — script
  `tools/experiments/ob55_con_roi_create.py`; sao lưu `data/backup/manifest.before_ob55_con_roi_20261019.sqlite`.
- Tư liệu chép vào `data/projects/33/source/` (6 ảnh góc, `các màu.png`, video ref, 3 ảnh cắt màu `mau_do/xanh_lo/tim.png`, 3 prompt ảnh mẫu).
- Kho **#451** "CON RỐI OB55 (ảnh góc in-game)" (riêng dự án, 6 ảnh góc) gắn cho 5 nhân vật; gắn Kho **#263** Tháp Đồng Hồ + **#428** Trời thế giới song song.
- 5 nhân vật + Character Lock: RỐI ĐỎ A, RỐI XANH LƠ A, RỐI TÍM, RỐI XANH LƠ B, RỐI ĐỎ B (hàng ngang trái→phải, tím ở giữa).
- 6 shot (tổng 30,07 s = trọn video ref), mỗi shot gắn đoạn ref cắt đúng điểm cắt cảnh (ffmpeg scene > 0,12), `feature`, SAR 1:1, 768×576:
  | Shot | Ref (s) | Nội dung | Cỡ/góc |
  |---|---|---|---|
  | 1 | 0–2,95 | nhìn thẳng từ trên xuống, 5 con đứng vòng tròn ngước nhìn máy | WS overhead |
  | 2 | 2,96–6,33 | máy thấp len giữa nhóm (ĐỎ A, TÍM, XANH LƠ A) nhún lắc | MS low, đẩy vào |
  | 3 | 6,33–9,54 | cận RỐI TÍM giơ tay vẫy, thanh điều khiển nghiêng theo tay | MCU low |
  | 4 | 9,54–17,67 | hàng 3 con (XANH LƠ A, TÍM, XANH LƠ B) nhảy đồng đều | WS eye, đẩy vào + lượn |
  | 5 | 17,67–25,0 | cận solo ĐỎ A → lia nhanh sang XANH LƠ A dang tay | MCU, whip |
  | 6 | 25,0–30,07 | cả 5 con hàng ngang nhảy, kết tư thế chung; máy lùi thấy cả tháp | WS eye, lùi |
- Nền 3D: chỗ đứng `bac_thang_giua` (chân cầu thang, tháp trái, đầu hồi nhà phải), hướng 124°, `night`/`cloudy`, render Blender xong 6/6
  (shot 4 nâng MS→WS để tháp vào khung). Motion soạn sẵn (state pending) + video model `seedance-2.5`.

## 2. Lấy lại từ #22 / khác #22
- **Lấy lại:** cùng chỗ đứng 3D `bac_thang_giua` cho mọi shot nhảy (góc này trùng đúng ảnh in-game thế giới song song Kho 428/1);
  Seedance 2.5 + video ref `feature` (#22 bài thử: ref người thật qua bộ lọc, nhảy khớp từng nhịp); câu "người/vật trong ref chỉ cho động
  tác"; khóa nền "BACKGROUND LOCK" theo render 3D; nhạc = tiếng gốc video ref phủ cả clip; không rung/nhún hậu kỳ khi chưa vào nhạc.
- **Tránh lỗi #22:** chỗ nối 2 clip nhảy lệch động tác/trang phục → ở đây mỗi shot là một cú cắt cảnh có sẵn trong ref (đổi cỡ/góc), mỗi
  con rối có Lock màu riêng + cùng bộ ảnh mẫu; máy có chuyển động (đẩy/lượn/lia/lùi) theo ref; tháp giữ đúng map 3D (plate + lock).
- **Khác:** 5 con rối thay 2 người (≥ 3 nhân vật → shot KHÓ: nháp 480p trước); con rối treo dây — thanh chữ thập lơ lửng nghiêng/nhún theo
  động tác, dây căng kéo đầu/tay/gối; nền thế giới song song (trời xoáy mây giông 428, xe/hòm lơ lửng vệt đỏ, đêm nhìn rõ).

## 3. Chọn màu: ĐỎ ×2, XANH LƠ ×2, TÍM ×1
Ba màu tương phản rõ trên nền đêm xanh xám; xanh lơ nổi trên trời tối, đỏ hợp đốm cam đỏ giữa xoáy mây và vệt đỏ xe lơ lửng; tím là màu
DUY NHẤT → con giữa / con solo giơ tay (shot 3). Đội hình đối xứng ĐỎ–XANH LƠ–TÍM–XANH LƠ–ĐỎ. Không có màu thứ 4 (bỏ hồng, trắng ma).

## 4. Điểm cần người dùng xác nhận
1. Viền VÀNG ở 6 ảnh góc phủ cả thanh điều khiển gỗ → Claude hiểu là hiệu ứng chọn trong game, không phải màu thân (prompt cấm vàng).
2. Ảnh in-game tháp thế giới song song (428/1): xoáy mây tối + đốm cam đỏ, xe/hòm lơ lửng, vệt gió trắng, móng quỷ đỏ trên mái — KHÔNG
   thấy "bàn tay ma khổng lồ trong mây" (đó là Cổng Trời, Kho 450). Prompt theo 428.
3. Tay điều khiển: in-game thanh chữ thập lơ lửng, không có tay người cầm → không vẽ người điều khiển.

## 5. Giá
- `pregen_check --project 33`: **6 ảnh → ước tính 1.32 usd (tối đa 5.28)** — ảnh khung đầu 0.312 · Claude D6 0.527 · QC 0.391 · Claude khác 0.090.
  Cổng nút Gen: không có. **CÒN CHẶN:** Tổ rà soát không chạy được — Anthropic API báo HẾT TIỀN từ 19/10 01:08 → nạp tiền rồi ↻ Rà lại.
- Ảnh mẫu 3 màu (trước storyboard): `tools/asset_polish.py draw` × 3 GPT Image 2.5 (giá tool 0,052/ảnh) — chưa gen.
- Video: pregen_check chưa tính (chưa có ảnh duyệt); số chính thức lấy từ nút Gen video sau cổng ảnh. Tham khảo bảng giá
  (`data/pricing.json`, chưa phải số Dashboard): nháp Seedance 2.5 480p 30,07 s × 0,103 ≈ 3,1 USD (chưa tính phụ phí giây ref);
  nâng 1080p × 0,52 ≈ 15,6 USD.

## 6. Bước kế (chờ người dùng)
1. Duyệt màu + xác nhận 3 điểm mục 4 → gen 3 ảnh mẫu (prompt `data/projects/33/source/prompt_mau_*.txt`, ref = 6 ảnh góc + ảnh cắt màu) →
   duyệt → thêm vào Kho riêng từng màu, gắn lại cho nhân vật.
2. Nạp tiền Anthropic → `pregen_check` lại → xin duyệt gen ảnh storyboard 6 shot.
3. Sau ảnh: duyệt motion, cổng video riêng (nháp 480p → duyệt → 1080p), dựng với nhạc gốc ref.
