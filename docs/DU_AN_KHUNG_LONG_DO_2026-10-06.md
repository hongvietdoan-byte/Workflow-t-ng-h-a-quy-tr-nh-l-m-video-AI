# Dự án "Khủng Long Đỏ" — quảng bá cặp trang phục + nhảy trend (06/10/2026)

Người dùng 06/10: 1 kịch bản Maxim vào phòng có giường ở tầng 2 nhà to gần Tháp Đồng Hồ, thấy bộ đồ nam trên giường, cầm lên → "hô biến"
mặc vào; Kelly vào thấy → "hô biến" mặc bộ nữ (cặp đôi); chuyển cảnh hai người nhảy trước căn nhà theo đúng động tác clip trend.
**Chạy thử qua Dashboard (UI v2, bấm nút như người dùng). Người dùng duyệt mọi chi phí** (vẫn ghi sổ chi + ước tính trước).

## 1. Quyết định người dùng (06/10)
| Câu | Chốt |
|---|---|
| Phòng | **Nhà lớn phía đông (hai tầng)** — Kho 263 Tháp Đồng Hồ, điểm 3D `trong_nha_dong_t2` (giường gỗ + ghế bành xanh, thảm xanh xám; render `data/_plates3d/indoor/ct_r2/plate_nha_dong_t2.png`). Cảnh nhảy: điểm `nha_lon_dong` (trước chính căn nhà). |
| Đoạn nhảy | **Thử trọn 34,4 s** + thử thêm cách "nhảy theo video" đã thử lần trước (#20: Seedance 2.5 + video mannequin không mặt). |
| Hô biến | **Cùng một khung, cùng chỗ đứng**: shot bộ cũ → shot bộ mới, nối bằng **rung + chớp sáng ở hậu kỳ** (không dựng hiệu ứng biến đồ trong clip). |
| Nhạc nhảy | **Tiếng gốc của clip trend** (`nhac_goc_34s.m4a`). |

## 2. Tư liệu (đã chuẩn bị, 0 USD)
- Trang phục: `D:\2026\OB55\Thao\KHỦNG LONG ĐỎ\Male_Cos_Flamedino.png` (nam: hoodie đỏ in khủng long xanh phun lửa, tay áo đen, quần jean đen rách, mũ đỏ có sừng, khẩu trang đen răng cá mập, dép khủng long đỏ) · `Female_Cos_Flamedino.png` (nữ: áo croptop đỏ in khủng long xanh, áo khoác đỏ tay sọc đen, váy da đen ngắn có móc khủng long bông xanh, mũ đen, khẩu trang răng cá mập, tất đỏ/đen, dép quỷ đỏ).
  → đưa vào Kho qua màn Kịch bản (loại **Trang phục** / `outfit`, S14.28) rồi gán cho nhân vật trong dự án (`assets.set_outfit`). Kho nhân vật đã đủ 6 ảnh nên KHÔNG gắn skin vào Maxim/Kelly.
- Clip nhảy: 1 người thật, toàn thân, máy đứng yên, 34,43 s, 576×1024 30 fps. Đã cắt + nâng 720×1280 (Kling cần cạnh ≥ 700, 3–15,5 s):
  `KHO TÀI NGUYÊN\video ref test\khung_long_do\nhay_doan1.mp4` (0–11,5) · `nhay_doan2.mp4` (11,5–23) · `nhay_doan3.mp4` (23–34,43) · `nhac_goc_34s.m4a`.

## 2b. Thử trước khi chạy thật (06/10 tối, `tools/experiments/dance_ref_test.py`, dự án thử #21, đã chi 2,76 USD)
| Bài | Kết quả |
|---|---|
| 1 · clip trend người THẬT (đoạn 9–14 s, 576×1024) → Seedance 2.5, 1 nhân vật Maxim, `reference_only` (bối cảnh + ảnh nhân vật) + video ref `feature` | **ĐẠT** — ClipAI nhận (không bị lọc người thật), Maxim nhảy khớp từng giây với mẫu, đúng mặt/đồ, máy đứng yên, toàn thân. 1,38 USD. Clip: `data/projects/21/experiments/multishot_seq1_1_cgt-20261006221505-1drvn.mp4` |
| 2 · bản đen trắng không mặt | **KHÔNG CẦN** (bài 1 đạt). Ghi chú: trừ nền bằng trung vị khung HỎNG (người luôn ở giữa khung, áo trắng trùng tủ) — muốn làm thì cần mô hình tách người (MediaPipe segmenter, phải tải ~5–10 MB) |
| 3 · 1 người mẫu → 2 nhân vật Maxim (trái) + Kelly (phải) | **ĐẠT** — cả hai cùng nhảy đồng đều theo mẫu (giơ tay, đặt tay ngực, dang tay cùng nhịp), không đổi mặt/đồ/chỗ; Maxim đôi lúc biên độ tay thấp hơn mẫu. 1,38 USD. Clip: `…/multishot_seq1_2_cgt-20261006222020-iezzk.mp4` |

**Hệ quả cho bản chạy thật:** phần nhảy dùng **Seedance 2.5 + video ref người thật** (không cần Kling, không cần chuyển không mặt), 2 nhân vật giữ nguyên.
Seedance 2.5 nhận video ref 2–30 s / cạnh 300–6000 → cắt 3 đoạn ~11,5 s dùng thẳng bản gốc 576×1024. Đổi ước tính mục 5: nhảy 34,4 s
Seedance 2.5 ≈ 0,277 USD/s (công thức giá web có tính giây ref) ≈ 9,5 dự tính (× 1,3 gen lại ≈ 12,4) thay cho dòng Kling + bỏ dòng thử (B).
Dashboard: Bước 3 "🎥 Video tham chiếu chuyển động" hiện gửi theo đường Kling — cần kiểm khi chạy thật xem ô này có đi được Seedance 2.5
không; nếu không → ghi việc code nhỏ (cho phép video ref ở Seedance 2.5 trong Bước 3).

## 3. Kịch bản (dán vào khung chat Bước 1 — có tiêu đề CẢNH nên được nhận là kịch bản, không bị hỏi lại)
```
KHỦNG LONG ĐỎ — khoảng 50 giây, dọc 9:16, look in-game Free Fire. Nhân vật: MAXIM, KELLY.

CẢNH 1 - NGÀY, PHÒNG NGỦ TẦNG 2 NHÀ LỚN PHÍA ĐÔNG (THÁP ĐỒNG HỒ)
1. (0–3 s) Maxim (đồ thường) mở cửa bước vào phòng ngủ, khựng lại nhìn về phía giường.
2. (3–5 s) Cận giường: bộ đồ Khủng Long Đỏ nam xếp gọn trên giường — chỉ có quần áo, không có người.
3. (5–8 s) Trung cảnh: Maxim cầm áo hoodie đỏ lên ướm vào người, mắt sáng rỡ.
   MAXIM: Đồ khủng long xịn vậy! Hô biến!
4. (8–10,5 s) Cùng khung, cùng chỗ đứng: Maxim đã mặc nguyên bộ Khủng Long Đỏ nam, xoay người ngắm áo, gật gù.
5. (10,5–13 s) Kelly (đồ thường) đứng ở cửa phòng, khoanh tay nhìn Maxim.
   KELLY: Mặc đồ đôi mà không rủ tớ à? Hô biến!
6. (13–16 s) Cùng khung, cùng chỗ đứng: Kelly đã mặc nguyên bộ Khủng Long Đỏ nữ, chống hông cười.

CẢNH 2 - NGÀY, TRƯỚC NHÀ LỚN PHÍA ĐÔNG (THÁP ĐỒNG HỒ)
7. (16–27,5 s) Toàn thân, máy đứng yên: Maxim và Kelly mặc bộ Khủng Long Đỏ đứng cạnh nhau, nhảy đồng đều theo video tham chiếu đoạn 1.
8. (27,5–39 s) Như trên, nhảy theo đoạn 2.
9. (39–50,4 s) Như trên, nhảy theo đoạn 3; kết thúc hai người tạo dáng.
```
Hậu kỳ: 3→4 và 5→6 nối bằng rung (`impact_shake`) + chớp trắng (`shot_transitions` flash); cảnh 2 dùng nhạc gốc làm nhạc nền, không lồng
giọng; thoại cảnh 1 TTS (Maxim giọng 72, Kelly giọng 70).

## 4. Điểm Dashboard CHƯA hỗ trợ — cách xử lý khi chạy
1. **Trang phục theo cảnh** (bộ cũ shot 1/3/5, bộ mới shot 2/4/6–9): Dashboard chỉ gán trang phục theo DỰ ÁN (`characters.outfit_image_ids`).
   Cách thử không sửa code: trong Character Bible có 2 dòng cho mỗi người — `MAXIM` (Kho 33, không trang phục) và `MAXIM KHỦNG LONG` (chọn
   "ảnh tham chiếu lấy từ" Kho 33 + gán trang phục nam); tương tự `KELLY` / `KELLY KHỦNG LONG`. Kịch bản đổi tên ở shot sau hô biến. Ghi lại
   nếu Dashboard không cho làm → việc code "trang phục theo cảnh" (đề nghị, người dùng chưa duyệt).
2. **Nhảy theo video**: (A) Bước 3 → "🎥 Video tham chiếu chuyển động" cho shot 7/8/9 (Kling, kiểu `feature`, 3 đoạn trên) — đường có sẵn;
   (B) thử lại cách #20 (Seedance 2.5 + video KHÔNG MẶT): clip là người thật → phải chuyển sang mannequin/depth trước (S11.9 chưa làm —
   tạm dùng khung xương MediaPipe vẽ dày trên nền xám, 0 USD) — chỉ thử 1 đoạn để so với (A).
3. Hai người nhảy theo **một** người mẫu: prompt "cả hai nhảy cùng động tác, đồng đều, đứng cạnh nhau" — rủi ro chỉ 1 người theo đúng.

## 5. Ước tính (tính dư; giá theo `data/pricing.json`, hệ số an toàn Seedance 1,25, gen lại ảnh × 1,35 / video × 1,3)
| Việc | Dự tính (USD) | Trần (USD) |
|---|---|---|
| Ảnh storyboard + toàn cảnh + khung cuối (≈ 13 ảnh Deepix 0,052) | 0,9 | 2,7 |
| Video cảnh 1: 6 shot ≈ 16 s Seedance 2.5 (0,23/s, khớp môi 2 câu) | 6,0 | 13,8 |
| Video nhảy (A): 3 clip Kling + video tham chiếu ≈ 34,4 s (0,12/s; ref làm giá ≈ 1,5×) | 9,2 | 21 |
| Thử (B): 1 đoạn 11,5 s Seedance 2.5 + mannequin (0,37/s) | 5,3 | 5,3 |
| TTS 2 câu + Claude (Director, QC, motion, chat) | 2,5 | 5 |
| **Tổng** | **≈ 24** | **≈ 48** |
Mức dự tính đợt ngân sách: **25 USD** (vượt chỉ cảnh báo). Không có nhạc AI (dùng nhạc gốc).

## 6. Kết quả chạy
_(điền sau khi chạy: mã dự án, chi thật theo sổ chi, cách A/B nhảy nào đạt, lỗi Dashboard gặp)_
**06/10 tối — lượt 1 qua Dashboard (dự án #22, đã chi ≈ 0,99 USD Claude; chưa gen ảnh/video):**
- Bước 1: kịch bản nhận đúng là KỊCH BẢN (0 USD). Director lần 1 ở chế độ mặc định "mỗi cảnh một clip" → 2 clip 15 s + tự bịa áo liền thân thú bông.
  Đổi "Cách chia cảnh" = Chia shot + thêm mô tả 2 bộ đồ vào đầu kịch bản → Director (2 lượt) ra 10 shot, mô tả đúng bộ đồ.
- Character Bible 4 dòng: MAXIM / KELLY (đồ thường) + MAXIM KL / KELLY KL (tự lấy ảnh Kho 33/23 + trang phục riêng dự án Kho 416/417).
  Shot 4, 6 → KL; shot 7–9 → MAXIM KL + KELLY KL, mỗi shot 11,5 s; gộp shot 10 (3,4 s) vào shot 9; tổng 9 shot · 51 s. Kelly giọng 70.
- Gỡ đạo cụ "mũ" (mũ bảo hiểm) Director tự gắn chỉ vì chữ "mũ đỏ có sừng".
- Người dùng đồng ý BẬT cờ `place_render_refs` → shot 1–6 đứng `trong_nha_dong_t2`, shot 7–9 `nha_lon_dong`.
- **Lỗi Dashboard đã sửa (main):** ô "Thời lượng đề xuất" chỉ nhận số nguyên (Lưu cảnh cắt 2,5 → 2 s); chọn chỗ đứng 3D bỏ chữ "đông"
  và "tầng 2" (phòng ngủ phía Đông lạc sang nhà quảng trường / tầng 1). Cả bộ 2771 qua.
- **Vướng chưa sửa (ghi lại):** tin bot trong khung chat bị lặp đôi; bấm ▶ Phân tích trước "Thay" hiện `ValueError` thô; các mục mở
  (sửa/thêm nhân vật, tham chiếu) tự đóng sau mỗi lần lưu; form thêm nhân vật/ô upload giữ giá trị cũ sau khi lưu (dễ gắn trùng);
  mở lại Dashboard vào "Test 1/10" thay vì dự án vừa làm; Director gắn đạo cụ theo một chữ trùng; ô video tham chiếu chỉ hiện ở chế độ chuyên gia;
  ước tính Dashboard 13,86 USD (kế hoạch tính dư ≈ 24) — có thể chưa tính giá video ref Seedance 2.5.
- **Dừng ở:** khóa ngân sách dự án (≈ 13,86 USD) — người dùng tự bấm. Tiếp: Storyboard ▶ Gen ảnh (≈ 0,6 USD) → motion prompt →
  bật chế độ chuyên gia, gắn `nhay_doan1/2/3.mp4` vào shot 7/8/9 (chưa thử: khung đầu + video ref trên Seedance 2.5) → gen video → dựng.
