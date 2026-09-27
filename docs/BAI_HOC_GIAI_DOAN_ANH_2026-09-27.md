# Bài học giai đoạn Kế hoạch → Ảnh — chạy thử #8 (2026-09-27)

Nguồn: `docs/CHAY_THU_2026-09-27_NHAT_KY.md` (phát hiện 1–32, theo dòng thời gian), `docs/PHAN_TICH_GOP_SHOT_2026-09-27.md` (gộp shot).
Tài liệu này sắp lại theo **nguyên nhân gốc** và **ai phải sửa** để dùng khi tổng hợp sửa bộ kỹ năng sau lần chạy thật (người dùng chốt
2026-09-27: sửa ngay cái chặn phần còn lại của #8; sửa bộ kỹ năng Director / Quay phim / Dựng / QC sau khi test hết chặng video + dựng).

Ký hiệu trạng thái: ✅ đã sửa + test · 🔧 sửa ngay (chặn phần còn lại #8) · ⏳ để đợt sửa gộp sau lần chạy thật · 📝 chỉ ghi nhận.

## 1. Bài học lớn nhất: cách tạo khung đầu
| | Ghép phông xanh lên nền 3D (`location_plates`, #8 lần đầu) | Model tự vẽ cả cảnh + ảnh tham chiếu (4 frame #7, thử cảnh 1 #8) |
|---|---|---|
| Tháp giống game | đúng hình học, nhưng máy cách 1–2 m → chỉ thấy chân tháp, **mất dáng tháp** | dáng tháp (chóp, cửa sổ, bậc, dừa) nhận ra ngay; ước lượng bằng mắt ~85–90 % |
| Tiếp đất, bóng, bụi | bóng của khối trụ thay người; không có bụi / cỏ lún; dễ "dán" | model vẽ bóng, tiếp đất, bụi (ảnh 221 #7) |
| Ánh sáng | lớp màu đêm 60 % + kéo màu → mặt bẹt, tối | đèn đường ấm lên mặt + trăng viền, mặt đọc được |
| Rủi ro riêng | phông xanh ăn đồ xanh lá; model bỏ phông xanh vẽ cả cảnh (12/33); mép cắt; vật che sai | tháp không chính xác từng góc; cỡ cảnh có thể lệch (S1·1 CU → MCU) |
| Chi phí | 1 ảnh / shot + Blender (miễn phí) | 1 ảnh / shot + 1 ảnh toàn cảnh ngang / cảnh |

**Quyết định (người dùng, 2026-09-27):** dùng cách tự vẽ cả cảnh, mỗi cảnh một **ảnh toàn cảnh ngang** 2048×1152 làm tham chiếu bối cảnh chung
(người dùng đề xuất "gen khổ rộng"; không cắt khung video vì 16:9→9:16 chỉ giữ 32 % bề ngang — 720p phóng ×2,7). Ghép phông xanh giữ cho
trường hợp cần đúng hình học tuyệt đối (sau này), với các bản sửa ở mục 3.
**Sai của ghi chú cũ:** 25/09 "ảnh tham chiếu chỉ ~70 %" đo trước khi có storyboard Deepix → không còn đúng (phát hiện 32).

## 2. Theo người / khâu phải sửa
### Director / Quay phim (bộ kỹ năng + prompt 19/20) — ⏳ sửa gộp
- Không làm theo trường mới: `hook_mid`, `money_shot`, mẫu `lighting`, trái/phải khung trong `start_frame` (PH 4); ý đồ nhạc Tầng B đặt `cut`/`in` sai logic.
- Ánh sáng đêm xin "most of the frame sunk in deep shadow" → nhân vật tối; luật cần: **tối nhưng mặt phải đọc được** (key ấm + viền lạnh) — 🔧 tạm bù bằng câu ánh sáng trong prompt ảnh.
- Chữ nơi chốn viết cứng vào `image_prompt` (khu nhà, nhà kho…); đổi bối cảnh sau Director không sửa theo (PH 18–19). Luật: tách "nơi chốn" khỏi "người + hành động" (trường riêng), để đổi bối cảnh / nền không phải sửa chữ.
- Gắn bối cảnh: chỉ khớp tên trong kịch bản → cảnh ở tháp bị gắn "Đảo Quân Sự" (PH 13). Cần hiểu mốc (tháp đồng hồ = asset 263).
- 33 shot TB 1,9 s, 30/33 < 3 s → tiền video theo mức tối thiểu model (PH gộp shot). Luật nhịp: shot ngắn gom theo cảnh / Seedance nhóm.
- Ước tính Director hai lượt thấp ~2,6 lần (ra ~94k token vs ~30k) (PH 3).

### QC (Claude) — ⏳ sửa gộp, 🔧 phần code
- **Duyệt nhiều ảnh lỗi ghép** (khung chữ nhật dán, thân lơ lửng, đè cột) — QC nhìn nội dung, không nhìn lỗi kỹ thuật ghép (PH 24). Bài học: **lỗi kỹ thuật bắt bằng code** (đo phông xanh, mép cắt, vật che, cỡ cảnh bằng dò mặt), QC Claude chỉ chấm nội dung / diễn xuất.
- Kiểm Bible với ảnh **báo sai** chi tiết nhỏ (mũ MAXIM đội ngược đọc thành xuôi) (PH 21). Luật: cờ về chi tiết nhỏ phải kèm ảnh cắt sát vùng đó cho người xem; không tự đề xuất sửa Bible chỉ bằng lời Claude.
- QC tự gen lại hợp lý 2 ảnh (mặt mờ, hướng nhìn) — cơ chế tự sửa có câu sửa hoạt động.

### Chọn model / ước tính tiền — ⏳ (một phần ✅)
- Ước tính trước Director tính theo cảnh, không theo shot → thấp ~3 lần (PH 2). Ước tính "gom multi-shot" sai luật Kling ≥ 3 s/shot (PH 7).
- "Cảnh thường" chọn Seedance Fast dù Kling rẻ hơn (PH 5) — nay người dùng chốt **ưu tiên Seedance** (P2m nhóm → Seedance từng shot → Kling) ✅.
- `cost.spend_summary` tính dòng Claude như clip ✅ (PH 10). Giá Kling std thật ~0,06/s vs bảng 0,08 (PH 12) ⏳. `video-list` trả `cost`=0 cho Seedance (PH 17) 📝.

### Video — ✅ đã chuẩn bị, chưa chạy luồng chính
- Seedance từ chối ảnh in-game (người thật) → **đánh dấu "CHARACTER SHEET REFERENCE" + dấu cộng đỏ trên mắt, chỉ ảnh tham chiếu** qua được, cắt 3 shot đúng storyboard (P2m). Cờ `seedance_ref_groups` ✅.
- Kling gộp shot (multi-shot, đầu–cuối) hỏng: bịa shot, không cắt, biến hình → bỏ.
- `find_by_prompt` so 200 ký tự đầu → nối nhầm clip (câu look chung > 200 ký tự) ✅ (PH 15).

### Gói bối cảnh 3D / ghép (code) — ✅ đã sửa (dù đổi hướng, giữ cho lần sau)
- Máy góc cao cố định "đầu + 1,6 m" → chúc 56–62°, nền là sàn ✅ chúc 30° (PH 22).
- Chữ nơi chốn lọt vào prompt ảnh phông xanh + ảnh neo storyboard là bản đã ghép → model vẽ cả cảnh, 12/33 dán khung chữ nhật ✅ (`place_free`, ảnh neo `_green`, `green_share` chặn + vẽ lại có câu sửa) (PH 24).
- Thân lơ lửng khi nhân vật bị cắt mép dưới ✅; mép trái/phải/trên thành đường cắt giữa khung ✅; sàn trước chân bị coi là vật che (depth 8-bit ~0,8 m/bậc) ✅ (PH 27–29).
- Chỗ đứng mặc định sát cột → toàn cảnh chồng cột → chọn `level_26_0` cho 3 shot WS ✅ (PH 31). Bài học: chỗ đứng phải kiểm vật che trước khi dùng.
- Phông xanh cố định `#00FF00` → nhân vật có đồ xanh lá cần phông khác ⏳. Bóng = khối trụ thay người ⏳.

### Dashboard / vận hành — ⏳
- Dự án mới không kế thừa cách làm đã chốt (chia shot, look) (PH 1).
- Sửa code mà không khởi động lại dashboard → pha nền của chạy tự động render lại bằng code cũ (PH 30). Quy tắc: sửa code → khởi động lại trước khi chạy tiếp.
- Khi chạy tự động chờ ở cổng, job ảnh mới không tự gửi (PH 25). Nút ⚙ khó bấm trong khung trình duyệt (PH 14).
- E-mail đăng nhập nằm trên URL `?login=` (PH 20) — riêng tư.
- Trần Claude tính tổng từ đầu đợt (đã tiêu 1,27 cho Director) → "còn 3 USD" thực tế chỉ còn 1,73.

## 3. Việc sửa ngay (chặn phần còn lại của #8)
1. 🔧 Chế độ **ảnh toàn cảnh ngang mỗi cảnh** trong luồng chính (dashboard): vẽ trước, làm ảnh tham chiếu bối cảnh chung cho storyboard của cảnh; tắt ghép phông xanh cho dự án.
2. 🔧 Câu ánh sáng theo giờ (đêm: đèn ấm lên mặt + trăng viền; ngày: bóng rõ dưới chân) vào prompt ảnh.
3. Sau đó: vẽ lại 33 khung (34 ảnh ≈ 1,8 USD, trần ảnh ~100) → cổng storyboard → người dùng duyệt → video.
