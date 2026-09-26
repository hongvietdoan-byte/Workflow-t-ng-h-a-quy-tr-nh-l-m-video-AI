# Đánh giá bộ kỹ năng 3 vai — kế hoạch V4 GĐ4 (2026-09-25)

> Bảng tổng kết gửi người dùng (kế hoạch V4 mục 4.2). Người viết: phiên Claude làm GĐ4. **Người chấm: một agent riêng** (không viết bộ nào),
> chấm theo thang cố định, tự đọc code trong repo và tự kiểm số liệu bên ngoài bằng WebSearch/WebFetch. Quy trình: nghiên cứu (3 agent) →
> viết → **chấm lần 1** → sửa 1 vòng → **chấm lần 2** → sửa các lỗi nhỏ lần 2 chỉ ra (không chấm lại).
> Bộ kỹ năng: `knowledge/roles/director.md`, `knowledge/roles/dp.md`, `knowledge/editor/editing.md` + `safe_zones.md`, trang tổng
> `knowledge/roles/README.md`. Nguồn: `knowledge/sources.md` mục GĐ4 (100 nguồn, có loại + mức tin cậy).

## 0. Chấm lại 2026-09-26/27 — mục tiêu ≥ 45/50 mỗi vai trước khi chạy thật (người dùng chốt)
Người chấm: agent độc lập (lần 0 một agent; lần 1–3 một agent khác, cùng thang, tự mở code, chạy test, tái hiện lỗi, kiểm file ra thật).
| Vai | Lần 0 | Lần 1 | Lần 2 | Lần 3 (`9c97886`) | Tối đa khi chưa chạy thật (lần 3) |
|---|---|---|---|---|---|
| Đạo diễn | 37 | 38 | 41 | **42,5** | ~45 (sát nút) |
| Quay phim | 38 | 37,5 | 40 | **41,5** | **~43 — không tới 45** |
| Dựng | 37 | 39,5 | 41 | **42,5** | ~45,5 nếu người dùng nghe/xem A/B 9 cờ Dựng trên clip #7 có sẵn |
Báo cáo chi tiết từng lần nằm ngoài repo (scratchpad phiên). Việc đã làm: commit `dde01f6`, `e307e79`, `9c97886` (tóm tắt trong TODO).
**Còn lại — miễn phí:** R1 `kind` lạ + chữ dự phòng nhận nhầm; R2 phủ định vượt dấu phẩy; R3 "thiếu money_shot" với phim không quảng bá;
R4 câu báo chuẩn hóa; sơ đồ máy cho nơi không 3D; vị trí người có cấu trúc; biến thể mở đầu; đo độ to từng lớp; mã hóa âm một lần; nguồn
nghề thay [Đ31]. **Cần người dùng (miễn phí):** nghe/xem A/B 9 cờ Dựng + `voice_direction`. **Cần tiền:** Director thật với `film_crew` /
hai lượt (~Claude), clip thật cho chuyển động máy / ghép nền / khớp môi / quay chậm (Quay phim chỉ lấy lại ~2 điểm cuối bằng cách này).

## 1. Điểm (mỗi tiêu chí /10; bản cũ = commit `533d230`)
Tiêu chí: **1** đầy đủ so với chuẩn nghề bên ngoài và mục 4.2 · **2** độ đúng · **3** áp dụng được vào pipeline AI · **4** kiểm chứng được
(bằng code/mắt — người chấm kiểm code có thật) · **5** nhất quán giữa các vai và với prompt/code.

| Vai | Tiêu chí | Cũ | Lần 1 | Lần 2 |
|---|---|---|---|---|
| **Đạo diễn** | 1 · 2 · 3 · 4 · 5 | 3 · 7 · 7 · 6 · 6 | 8 · 7 · 7 · 6 · 5 | 8 · 8 · 8 · 7 · 6 |
| | **Tổng /50** | **29** | **33** | **37** |
| **Quay phim** | 1 · 2 · 3 · 4 · 5 | 3 · 7 · 6 · 5 · 6 | 8 · 8 · 7 · 6 · 5 | 9 · 8 · 8 · 7 · 7 |
| | **Tổng /50** | **27** | **34** | **39** |
| **Dựng** | 1 · 2 · 3 · 4 · 5 | 3 · 6 · 6 · 6 · 6 | 8 · 8 · 5 · 6 · 6 | 8 · 8 · 6 · 7 · 7 |
| | **Tổng /50** | **27** | **33** | **36** |

Đọc bảng: tiêu chí 1 tăng mạnh nhất (bản cũ là luật chống lỗi, bản mới là kỹ năng nghề). Lần 1, tiêu chí 5 **giảm** vì trường mới sinh mâu
thuẫn mới (`beat` hai dạng, `intensity` hai nghĩa, bố cục máy ảo trái luật). Dựng tiêu chí 3 thấp nhất vì nhiều kỹ năng cốt lõi chưa có code.

## 2. Đã bổ sung
**Đạo diễn (Đ1–Đ8):** phân tích kịch bản (3 câu Mamet, giá trị đổi dấu McKee, động từ hành động Weston, gieo–gặt, ẩn ý, cung nhân vật); đường
cảm xúc + móc câu (số chính thức TikTok); kể bằng hình (hồi hộp/bất ngờ Hitchcock, tương phản Block, motif, thời tiết và khi nào thành sáo);
**chỉ đạo diễn xuất** — trường `performance` (cường độ 1–5, mặt/mắt/người/nhịp/người nghe/động cơ) đi vào prompt ảnh, motion, QC ảnh/clip,
dấu vân tay; **chỉ đạo giọng** — `delivery` → tham số TTS ElevenLabs v3 (cờ `voice_direction`); **ghi chú kịch bản** `script_notes` (cách
Yorke, chỉ đề xuất); luật N1–N5 cập nhật khớp môi / tuổi; bối cảnh + thời tiết. Code kiểm: `tradeoffs` thiếu khi đã hy sinh = lỗi; gặt không
có gieo; diễn đơ / đường phẳng / đỉnh lặp.
**Quay phim (Q1–Q10):** cỡ/góc kèm tâm lý và ngoại lệ ngữ cảnh; ống kính + bảng FOV khớp máy ảo (`lens_mm` mới); bố cục 9:16; giới hạn model
**sinh từ `provider_rules.json`**; chuyển động máy + từ vựng chính thức Kling/Seedance/Runway/Veo + **dữ liệu chạy thật** (handheld làm hỏng
nhận diện, push-in + bước tới → "đi tại chỗ"…); gói bối cảnh + shot khớp môi; `why` mỗi shot; ánh sáng (mẫu `lighting` = bảng tham chiếu);
coverage đối thoại / đấu súng / truy đuổi FF, trục 180°, luật 30°, cắt khớp.
**Dựng (E1–E9):** Murch, Dmytryk, J/L; giọng; âm nhiều lớp (quan hệ với `sfx_plan`); nhạc theo phách; sửa màu → khớp màu, ghép phông xanh;
hiệu ứng khi có lý do; vùng an toàn **số chính thức** (Meta 14/35/6%, Google Ads 288/672/48/192 px) — **code sửa lề phải phụ đề 6% → 18%**;
độ to: **không nền tảng nào công bố LUFS** (ghi rõ), mục tiêu −14 LUFS / −1,5 dBTP; hàm đo `measure_loudness` — đo thật bản giao #7:
**−14,7 LUFS, đỉnh thật −2,9 dBTP**; thông số xuất YouTube chính thức; tự rà có tiếng / không tiếng.
**Hồ sơ nhân vật:** KELLY #23, MAXIM #33 bỏ "17-year-old" (+ lịch sử sửa); `core/profile_digest.py` bản rút gọn 200/500 ký tự có kiểm.

## 3. Sửa theo người chấm
- **Lần 1 → 2 (đã chấm lại):** `beat` một dạng object (+ `value/plant/payoff`) ở prompt 01, validator, tài liệu; tách nghĩa `intensity`
  (độ mạnh khoảnh khắc; code vẽ cận nhỏ hơn 1 bậc); đường phẳng = 6 shot liền; bắt "tên cảm xúc" rộng hơn; Ekman đúng thuật ngữ; giọng:
  Creative chỉ cường độ 5, câu ≤ 3 chữ bỏ thẻ/nhấn; máy ảo: mắt MS/MCU ra khỏi thanh giao diện trên; `spot_problem` hiện ở autopilot; mẫu
  ánh sáng; chuyển động không có `camera_move` → ghi trong `why`; câu SQL đo lại dữ liệu model; cắt khớp + mẫu phủ FF; thang ưu tiên đủ 6 bậc
  ở mọi bộ; E3 đúng về `sfx_plan`; mức hạ nhạc tính từ tham số (~12 dB, chưa đo); 35/36% thống nhất; E8 ghi thẳng `_ENCODE` thiếu
  faststart/BT.709; AES −16/−17; prompt 17 +0,5 s; README thêm 4 dòng rà chéo.
- **Sau lần 2 (chưa chấm lại):** prompt 17 bỏ câu "cận hạ một bậc" (tránh hạ hai lần), Motion + QC nhận `shown_intensity`; cảnh báo gặt không
  có gieo hiện ở Bước 1 và tính vào bàn đo; `beat` không bao giờ làm từ chối câu trả lời (khóa lạ bỏ, `null` = rỗng); prompt 01 móc câu 1–3 s +
  mẫu `lighting`; ví dụ "Kenta!" sửa theo luật câu ngắn; số % mắt trong Q3 theo số đo của người chấm, MLS nâng khoảng trống đầu; đỉnh thật
  một mục tiêu −1,5 dBTP ở code và tài liệu. Toàn bộ **972 test qua**.

## 4. Còn thiếu và vì sao
> **Cập nhật 2026-09-26 (điểm ở mục 1 là điểm lịch sử, không chấm lại):** sau GĐ4, các đợt tự chạy 1–7 đã **code xong** V2, V4, V5, V6
> và D1, D2, D4–D14 (trừ D3 cố ý không làm) — xem bảng "Việc code còn thiếu" ở `knowledge/roles/README.md` (dòng có ✅) và mục "Việc tự
> chạy sau GĐ4" trong `TODO.md`. Các tính năng có cờ vẫn TẮT tới khi thử thật. Còn mở thật sự: V3 (nghe thử `delivery`), V7, P1, và hai dòng
> cuối bảng (nguồn, mẫu nhỏ). Các dòng "Chưa code" trong bảng dưới **đã thay** bởi ghi chú này.

| Còn thiếu | Vì sao chưa | Việc |
|---|---|---|
| Kiểm gieo–gặt chỉ biết *có* gieo, không biết gieo *đúng điều* | Cần hiểu nghĩa — để Claude/người đọc | ghi nhận |
| Kiểm giọng đúng `delivery` bằng máy | Cần mô hình nghe cảm xúc tiếng Việt | V7 |
| Thẻ âm / chữ hoa với giọng Việt chưa nghe thử | Tốn lượt âm thanh — cần người dùng cho phép | V3 |
| Motif, ai-biết-gì chưa có trường riêng | Mở rộng dữ liệu cảnh | V6 |
| Sơ đồ vị trí máy, kiểm trục 180° | Chưa code | V4, V5 |
| Chuẩn hóa LUFS + hiện số đo ở Bước 5 | Chưa code (phần đo đã có) | D11 |
| Khớp màu giữa các shot, khớp hạt | Chưa code — cần nhất khi bật gói bối cảnh | D7, D8 |
| Cắt J/L, điểm cắt theo chuyển động, khoảng lặng nhạc, nền không khí, âm thời tiết | Chưa code | D1, D2, D6, D5, D4 |
| faststart/BT.709, đo mức hạ nhạc thật | Chưa code/đo | D12, D14 |
| Bản rút gọn hồ sơ KENTA thiếu áo khoác xanh + găng tay trái | Hồ sơ dài hơn 500 ký tự, code chỉ chọn cụm | P1 (viết tay hoặc Claude ~$0,01) |
| Nguồn: nhiều sách chỉ đọc qua tóm lược; Kling/Seedance một phần chỉ đọc qua bên thứ ba (trang chạy JavaScript) | Không truy cập được bản gốc | ghi mức tin cậy |
| Số liệu "model làm tốt/hỏng" là mẫu nhỏ (≤ 20 clip mỗi kiểu) | Mới 2 dự án chạy thật | đo lại bằng câu SQL trong dp.md Q5 |

## 5. Người dùng quyết
1. Duyệt 3 bộ kỹ năng → bật cờ `film_crew` (Director đọc bộ mới).
2. Cho nghe thử `delivery` (V3) → bật `voice_direction`.
3. Thử bản rút gọn hồ sơ trong prompt ảnh (GĐ8) → bật `profile_digest`; KENTA: viết tay hay Claude soạn.
