# Báo cáo chạy thử 2A — "ANH CHỌN AI?" 0–20 s (dự án thử #7, 2026-09-25)

> Kế hoạch `docs/KE_HOACH_2026-09-25.md` Bậc 2A. Người dùng cho tự chạy trong trần: $8 tiền có giá · $1 Claude API · 32 ảnh · 25 lượt
> âm thanh · gen lại ≤ 2 lần/shot. Phiên Claude Code vận hành từng bước bằng `tools/pilot_setup.py` + `tools/pilot_run.py` (autopilot chấm
> QC mọi ảnh bằng Claude — không vừa $1).

## 1. Phạm vi
CINEMATIC MỞ ĐẦU (0–8 s) + CẢNH 1 (8–20 s) của #6 → bản sao #7: 10 shot, 20,3 s phim, 7 câu thoại, 3 nhân vật (KELLY, KENTA, MAXIM),
look FF in-game, ảnh GPT Image 2.5 Sunburst, video Kling 3.0 Omni, giọng 4 giọng clone VN + `eleven_v3`. Không nhạc trả tiền, không card cuối.
Bộ chuẩn hóa shot sửa 1 chỗ (toàn cảnh 0,6 → 1,5 s).

## 2. Diễn biến và lỗi tìm ra (theo thứ tự)
| # | Bước | Chuyện gì xảy ra | Chẩn đoán | Đã sửa |
|---|---|---|---|---|
| 1 | Chuẩn bị | Chưa nhân vật nào có giọng | dự án tạo trước khi chốt 4 giọng VN | gán KELLY=Voice Kelly VN, KENTA=voice Hip VN, MAXIM=voice boy ingame VN (#6, #7) |
| 2 | Kiểm Bible (Claude) | Lần kiểm cũ báo KENTA sai bên găng, MAXIM "mũ đội xuôi" | **Claude đọc sai hướng mũ**: ảnh chuẩn MAXIM đội ngược (khóa mũ trên trán). Găng: đúng một nửa | sửa theo **mắt người + ảnh chuẩn**: KENTA găng hở ngón + băng cổ tay tay phải, găng giáp cánh tay trái; MAXIM mũ đen xám đội ngược. Sửa cả **Character Lock** (lượt kiểm Bible không so Lock — lỗ hổng) |
| 3 | Ảnh shot 1 | GPT Image 2.5 **từ chối** (safety system) | prompt ghi "17-year-old young woman … bóng tối, mắt đỏ"; shot 2 cùng nhân vật không ghi tuổi thì qua | code `runner.no_minor_age`: không gửi tuổi < 18 cho model ảnh/video; gửi lại → **qua** |
| 4 | Ảnh shot 4 | Model vẽ **2 khung ghép** (Kelly nói + Kelly quay lưng bước đi) | prompt khung đầu kể nhiều nhịp | gen lại 1 lần với "one single frame, one moment only" → đạt. Luật đưa vào `knowledge/roles/dp.md` |
| 5 | Sau khi sửa mô tả | **Mọi ảnh bị coi "cũ"** → motion cũ → video bị chặn; autopilot sẽ gen lại ảnh tới trần shot | **lỗi thật trong code**: dấu vân tay lúc gửi có look, lúc kiểm không có (mọi dự án có look) | `lineage._image_hash` dùng chung; test hồi quy (đỏ với code cũ) |
| 6 | QC ảnh mẫu (Claude) | 4 ảnh 0,75–0,94, không ảnh nào bị loại; QC đòi "thấy chân chạm đất" ở shot trung cảnh | tiêu chí `grounding` áp cả cỡ cảnh không có chân | ghi việc: QC bỏ `grounding` khi cỡ cảnh ≤ MS |
| 7 | Phụ đề | Mặc định khung dọc cách đáy 12% → nằm trong 35% đáy bị app che (Meta chính thức) | nguồn: Meta Ads Guide Reels | mặc định khung dọc: đáy 36%, đỉnh 15% (`subtitles.SAFE_*`), test |

| 8 | Video (10 clip Kling) | Chỉ 2/10 "thành công", 8 bị đánh "không tìm thấy" | **lỗi thật (W12b)**: quá 2 task chạy song song, ClipAI trả **mã chờ tạm** (12 chữ số, không bao giờ có trong danh sách) rồi tạo task thật với **mã mới** khi có chỗ. Cả 10 clip đã được làm và tính tiền. Nhánh "không được tạo" còn sẽ **gửi lại + xóa khỏi sổ chi** → trả 2 lần mà sổ ghi thiếu | `ClipAIVideoProvider.find_by_prompt` + `VideoRunner._relink/relink_failed`: tìm task thật theo đúng prompt đã gửi, tạo sau lúc gửi, chưa gắn job khác → theo mã thật, không gửi lại. **Lấy lại cả 8 clip, không tốn thêm.** 3 test. Nghi vấn: 16 task "not_found" ở GĐ6 có thể cùng nguyên nhân (khi đó chỉ tra theo mã) |
| 9 | QC video (Claude, 2 clip mẫu) | Clip shot 6 bị nêu lỗi ở "giây 3–5, 5–6" trong khi clip chỉ 3,1 s | QC video bịa/đọc nhầm mốc thời gian (M12 đã có trong danh sách) | người vận hành xem bảng khung: không lỗi nặng → duyệt. Việc: QC video không dùng mốc giây, chỉ số khung |
| 10 | Dựng | Bản giao 22,3 s (kế hoạch 20,3 s); đỉnh âm 0,0 dB | clip kéo dài theo giọng thật (đúng ưu tiên thoại > thời lượng); chưa có giới hạn đỉnh | việc cho vai Dựng: limiter đỉnh ≤ −1 dB |

## 3. Chi phí (sổ chi đợt thử, đối chiếu `cost` thật của ClipAI)
| Khoản | Số lượng | Tiền |
|---|---|---|
| Video Kling 3.0 Omni pro | 10 clip · 31 s trả tiền (phim 20,3 s → bản giao 22,3 s) | $2,48 |
| Thử vị trí máy (H5) | 1 clip · 4 s | $0,32 |
| Claude API | Bible $0,008 · motion 1 lượt $0,10 · QC ảnh 4 mẫu $0,057 · QC clip 2 mẫu $0,038 | **$0,20 / trần $1** |
| Ảnh GPT Image 2.5 Sunburst | 12 ảnh (10 shot + 1 bị từ chối gửi lại + 1 gen lại S4) | chưa có giá (Deepix không trả giá qua API) |
| Giọng `eleven_v3` | 7 câu | chưa có giá |
| **Tổng có giá** | | **$3,00 / trần $8** |
- **Đối chiếu ClipAI (C11 xong):** `cost` 24 cho clip 3 s, 32 cho 4 s = 8 đơn vị/giây; 35 s = 280 đơn vị = đúng $2,80 trong sổ → **1 đơn vị `cost` ≈ $0,01**.
- Gen lại: 1 ảnh (S4, lỗi bố cục) + 1 ảnh gửi lại (S1, bị từ chối trước khi tạo). **0 video gen lại.** Tỉ lệ tiền gửi lại ≈ 0% video (GĐ6: 59%).

## 4. Thử nghiệm "quay theo vị trí máy" (Q2/H5) — shot 9 + 10 (Kelly và Kenta chạy cạnh nhau, mỗi người một câu)
| | Từng shot | Một clip cho 2 shot |
|---|---|---|
| Giây trả tiền | 6 s | **4 s (−33%)** |
| Nhân vật | đúng | đúng, giữ ổn trong 4 s |
| Khung | S10 có khung riêng nhấn Kenta | một khung hai người suốt → mất khung nhấn Kenta |
| Cuối clip | đều | chất lượng giảm nhẹ ở giây 3–4 (người nhỏ hơn) |
**Kết luận:** hợp với đoạn thoại kịch bản muốn giữ một khung; tiết kiệm rõ; không thay shot cần đổi góc nhấn nhân vật. Giữ clip vị trí máy ≤ 4–6 s,
để Quay phim quyết định từng cảnh (Q1 của `roles/dp.md`). Làm tiếp 1.5 (code `camera_setup` sau cờ, TẮT mặc định).

## 5. Kết quả
- **Video 22,3 s** có giọng Việt 3 nhân vật + phụ đề (trong vùng an toàn mới): `data/projects/7/output/FINAL_VIDEO_sub_src.mp4`
  (bản không phụ đề: `FINAL_VIDEO.mp4`). Cả 10 clip giữ đúng nhân vật từ đầu tới cuối clip (bảng khung). Người dùng xem để quyết định 2B.
- Kiểm giọng tự động: 7/7 câu đạt (chưa có nghe lại thành chữ — máy chưa cài faster-whisper).

## 6. Bài học → đã đưa vào đâu
- Ảnh chuẩn + mắt người là trọng tài cuối về ngoại hình; Claude đọc ảnh có thể sai chi tiết nhỏ (hướng mũ) → `knowledge/roles/director.md` N4.
- Không ghi tuổi < 18 vào prompt hình → code + `roles/director.md` N4 + `roles/dp.md` Q4.
- Khung đầu = một khoảnh khắc → `roles/dp.md` Q2.
- Chạy thật lộ ra lỗi mà 830 test không thấy (dấu vân tay look) → giữ nhịp "chạy thử nhỏ có trần" trước mỗi đợt lớn.
