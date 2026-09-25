# Báo cáo lỗi người dùng phát hiện khi xem video 2A + cách sửa (2026-09-25)

Người dùng xem video 0–20 s ("ANH CHỌN AI?", dự án thử #7) và báo 4 điểm. Mỗi điểm: chẩn đoán bằng số liệu → sửa gốc (code/luật) →
chạy thật lại → bằng chứng.

| # | Người dùng thấy | Chẩn đoán (số đo) | Nguyên nhân gốc | Sửa | Bằng chứng sau sửa |
|---|---|---|---|---|---|
| 1 | Giọng Kenta (**"voice Hip VN", id 69**, `eleven_v3`) cụt hơi ở cuối | "Không liên quan đến ông." 0,64 s = 7,8 âm tiết/s, 80 ms cuối **−1,1 dB** (dừng giữa chữ); "Bây giờ chưa được." 80 ms cuối −12 dB rồi tắt phụt. Câu tốt: −20 tới −91 dB | `eleven_v3` thỉnh thoảng cắt câu ngắn (thử lại cùng câu: 0,88 s, đuôi −28,8 dB — ngẫu nhiên); bộ kiểm giọng cho qua vì ngưỡng 8 âm tiết/s quá rộng và không đo đuôi | `voice_check`: ngưỡng 6,5 âm tiết/s + **đo 80 ms cuối (> −15 dB = cụt)**, phiên bản kiểm (câu cũ được kiểm lại); `voice_check.redo` tạo lại câu cờ lỗi **kèm "…" cuối** (`voice.slow_end`) | Cờ đúng 2/7 câu (không báo nhầm). Tạo lại: 2 câu mỗi câu 1,04 s, 3,8–4,8 âm tiết/s, đuôi −18 / −35 dB → đạt |
| 2 | Mấy cảnh đầu không có background, nền đen | Director ghi `location: "dark cinematic void / abstract emotional space"`, prompt "deep black background" cho 4 shot mở đầu (+ 5 shot cảnh kết ở #6) | Director hiểu "Kelly đứng một mình trong bóng tối" thành không gian trừu tượng | Luật: "bóng tối" = cảnh đêm **trong bối cảnh thật** của dự án (`prompts/17`, `roles/dp.md`); `director_report` báo shot "void"; #6/#7 đặt cảnh cinematic ở quảng trường Tháp Đồng Hồ ban đêm | 4 shot mở đầu có nền quảng trường đêm |
| 3 | Bối cảnh chưa giống Tháp Đồng Hồ trong Free Fire | Kho "Đảo Quân Sự" không có ảnh tháp; mục "Tháp Đồng Hồ" (#263) chỉ có ảnh chụp từ trên cao + bản đồ (luật R7 cấm làm nền) → với shot cận/trung chỉ có **chữ** → model vẽ tháp châu Âu chung chung | Không có ảnh mốc ngang tầm mắt + code không gửi ảnh bối cảnh cho shot cận/trung | **Render mô hình 3D FF** (`model 3D/free_fire_clocktower…glb`) bằng Blender 5.0.1 bản Microsoft Store (`plates3d.store_blender`, chạy nền qua `Invoke-CommandInDesktopPackage`), camera đặt trong quảng trường ngang tầm mắt → ảnh vai trò **"chi tiết / mốc"** + 2 nền ngang tầm mắt vào Kho #263; code mới `assets.location_landmark`: shot cận/trung gửi ảnh mốc kèm lời dặn "chép hình dáng/chất liệu/màu, KHÔNG chép góc máy/giờ/ánh sáng"; mô tả tháp bằng chữ đúng mô hình | Ảnh + clip mới: tháp gạch đá thon, đỉnh chuông bát giác sẫm, chóp nhọn, bậc thang — giống mô hình FF, giữ ổn định suốt clip |
| 4 | Chưa có nhạc nền theo nhịp của clip | 2A cố ý tắt nhạc (tiết kiệm); kho nhạc chỉ có meme/SFX/bài có bản quyền; brief nhạc cũ dựa trên giây **dự kiến** | Không có nhạc bám timeline thật | `core/music_timing.py`: phần/ranh giới lấy từ **timeline thật**, **tự chọn BPM** để điểm chuyển rơi đúng vạch ô nhịp (112 BPM, lệch 0,03 s), brief theo mốc giây (không gọi Claude), xin dài thêm 4 s (model luôn tắt dần ~5 s cuối), **chấm bản nháp** (nhảy độ to ở điểm chuyển, không tắt sớm) để chọn; **hạ nhạc khi có thoại** (sidechain, `ffmpeg_studio.build_extras_mix_cmd(duck=True)`) | 3 bản nháp: bản chọn nhảy +27,6 dB đúng 8,6 s, cuối phim chỉ giảm 7 dB. Bản giao: nhạc lên đúng ~8,5 s, đỉnh −2,9 dB |

## Chi phí đợt sửa (trần đợt thử $8 / Claude $1)
Video 4 clip mở đầu làm lại ≈ $0,96 · Claude motion 4 shot $0,05 · 8 ảnh (4 tháp chung chung + 3 tháp đúng + 1 ECU) · 5 lượt âm thanh
(3 thử giọng + 2 tạo lại) · 3 bản nhạc. Tổng đợt thử: **$4,02 / $8**, Claude **$0,26 / $1**, ảnh 20/32, âm thanh 15/25.
**Ghi nhận:** shot 1 và 4 đã gửi ảnh lần thứ 4 (vượt giới hạn "gen lại ≤ 2") vì đầu vào đổi theo yêu cầu người dùng (nền + tháp), không phải QC
sửa lỗi — báo rõ để người dùng quyết định có tính gộp hay không.

## W12b chạy thật lần 2
Khi gen lại 4 clip, ClipAI trả mã chờ tạm cho 2 clip → code **tự nối** vào task thật (`relinked`), không gửi lại, không mất clip.

## Còn lại
- Đoạn mở đầu nhạc piano thưa → giữa hai câu thoại (5–7 s) nhạc gần như im; cân nhắc tăng mức nhạc phần cinematic hoặc dặn "sustained pad".
- Nhạc có fade-in 1,5 s → giây đầu im lặng; video ngắn cần có tiếng ngay khung đầu (hook) → rút fade-in còn ~0,3 s.
- Khóa dấu lấy vị trí camera 3D (trừ 2,16 m nâng mô hình) nên đưa vào `plates3d` (tham số `cameras` theo tọa độ gốc của mô hình).
