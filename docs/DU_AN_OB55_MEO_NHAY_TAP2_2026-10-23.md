# Dự án #34 "OB55 Halloween — Mèo nhảy tập 2: con rối nhảy theo 2 con mèo (Cổng Trời thế giới song song)" (23/10/2026)

Tập 1 = #33 (`docs/DU_AN_OB55_CON_ROI_2026-10-19.md`, lỗi gặp phải `docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md`).
**Trạng thái: đã chuẩn bị xong (0 USD), DỪNG trước cổng gen ảnh — chờ người dùng nói "gen".**

## 1. Đề bài người dùng
- 2 con rối nhảy AI theo 2 con mèo; nền Cổng Trời (hoặc cảnh team mình bắn nhau với team địch).
- Cạnh/dưới con rối chèn luôn 2 con mèo giống ref. Mèo + nhạc lấy từ TikTok
  `https://www.tiktok.com/@baloosilly/video/7683219461792337183`.
- Chữ phía trên (2 dòng): "Cốt tôi var cực mạnh với team địch" / "Tôi và Con Rối team địch kiểu:".

## 2. Phân tích ref (0 USD)
- Tải yt-dlp: `D:/AI-Video-Output/2026-10-23_meo-nhay-tap2/tiktok/tiktok_baloosilly_7683219461792337183.mp4` — 1080×1920, 60 fps,
  hình 12,60 s, tiếng AAC 12,585 s (đủ, không cụt). Cùng nội dung `video ref nhảy tập 2.mp4` trong thư mục tư liệu (bản 720p).
- **Phông xanh** (#00FF00) — mèo tách nền sạch bằng ffmpeg `chromakey + despill` (thử: `thu_tach_meo_khung.jpg`) → không cần gen mèo.
- **MỘT cú máy tĩnh**, không cắt cảnh (ffmpeg scene > 0,05: 0 điểm cắt).
- Nhạc: 129,2 BPM (librosa + `tools/audio_listen.py`: nhạc điện tử 100 % thời gian), phách 0,09 · 0,53 · 0,98 … 12,17 s
  (≈ 0,465 s/phách); câu 8 phách ≈ 0,09 / 3,78 / 7,52 / 11,24 s.
- Hai vai: **mèo cam (trái) nhảy**, **mèo xám (phải) ngồi cầm điện thoại (vỏ xanh) quay mèo cam** suốt clip.
  | Giây | Mèo cam |
  |---|---|
  | 0–0,5 | dang tay chữ T |
  | 0,5–3,8 | nhảy lò cò, đá chân, tay đấm, lùi sang trái |
  | 3,8–4,7 | nghiêng người nhảy ngang |
  | 5–9 | dang hai tay lắc hông qua lại, sát lại mèo xám |
  | 9–10 | vẫy tay, bước |
  | 10,5 | giơ cao hai tay |
  | 11–12,6 | nhún nảy, hai tay lên mặt, xoay hông kết |

## 3. Người dùng chọn (23/10, câu hỏi có lựa chọn)
1. Nền **Cổng Trời** (tái dùng Kho #450 + mô hình 3D Kho #265 của #31) — không làm cảnh đấu súng.
2. Vai: **1 con nhảy + 1 con ngồi cầm điện thoại quay** (đúng ref).
3. Màu: **RỐI TÍM nhảy** (ảnh mẫu Kho #454) + **RỐI ĐỎ quay** (Kho #452) — ảnh mẫu tập 1 đã duyệt, không gen lại.
4. Bố cục 9:16: chữ 2 dòng trên cùng; 2 con rối to giữa khung; **2 con mèo thật tách phông xanh đặt nhỏ góc dưới**, cùng nền.

## 4. Đã làm (0 USD)
- Dự án **#34** (9:16, FF_INGAME, ảnh GPT Image 2.5, per_shot, `paused=1`, Claude = `claude_cli` theo dự án — tránh lỗi A2/A3 tập 1).
  Script `tools/experiments/ob55_meo_nhay_tap2_create.py` (theo script #33, dùng hàm lõi Dashboard); sao lưu
  `data/backup/manifest.before_meo_nhay_tap2_20261023.sqlite`.
- Tư liệu `data/projects/34/source/` (TikTok 1080p có nhạc, ref 720p, `các màu.png`); video ref
  `data/projects/34/motion_ref/shot_1_meo_0.00-12.60.mp4` (720×1280, 30 fps, SAR 1:1).
- Gắn Kho: 452, 454 (con rối), 265 (Cổng Trời 3D), 450 (trời/không khí Cổng Trời), 428 (trời thế giới song song).
- 2 nhân vật chép mô tả + Character Lock từ #33 (RỐI TÍM ← #33 RỐI TÍM, RỐI ĐỎ ← #33 RỐI ĐỎ A).
- **1 shot 12,6 s** (= trọn ref, ref là một cú máy; Seedance ≤ 15 s): WS ngang mắt, tĩnh; chỗ đứng 3D `trung_tam_me_cung`, nền
  `landmark` (biệt thự mái ngói đỏ cam sau hàng rào, như Kho 450/2); đêm, chỉ ánh trăng (`practical_lights: []`).
  Ảnh khung đầu = tư thế 0 s của ref (TÍM dang tay chữ T, ĐỎ ngồi giơ điện thoại). Prompt chừa 1/5 trên (chữ) + 1/4 dưới (mèo).
  Motion soạn sẵn (pending), `seedance-2.5`, ref `feature`. Chữ KHÔNG đưa vào prompt — chèn hậu kỳ như #33.
- Áp bài học #33: không có đoạn chuyển cảnh đầu ref (B8); không dùng chữ "cats" ngoài câu chặn (B10); trời/biệt thự đặt bằng nền 3D (B3);
  tên không dấu trong motion (B7); chặn "green screen" trong prompt ảnh + video.

## 5. pregen_check --project 34
Chạy 23/10 sau khi render nền 3D (`py tools/location_pack.py render --project 34`, Blender 0 USD, 2 góc máy: shot + wide;
`D:/AI-Video-Output/2026-10-23_meo-nhay-tap2/nen3d_shot1.jpg`). Mã thoát **1 = CÒN CHẶN**. Nguyên văn:
- Giá: **1 ảnh → ước tính 0.22 usd (tối đa 0.88)** — ảnh khung đầu 0.052 · Claude D6 0.088 · QC 0.065 · Claude khác 0.014
  (Claude chạy claude_cli nên thực tế ≈ 0 USD API, lỗi A9 tập 1 vẫn còn).
- Giá video (chỉ báo): bản cao còn phải gen 1 shot ≈ **7.84 USD**; cờ send_estimate TẮT. Tham khảo bảng giá: nháp Seedance 2.5 480p
  13 s × 0,103 ≈ 1,34 USD × hệ số ref thực tế 1,37 ≈ **1,8 USD**; 1080p 13 s × 0,52 ≈ 6,8 × 1,24 ≈ **8,4 USD** (A7 tập 1).
- Cổng nút Gen: không có. Nền 3D: 0 shot chưa sẵn.
- **CHẶN: Tổ rà soát tác động** shot 1: `LlmError: Claude Code báo lỗi: Failed to authenticate: OAuth session expired and could not be
  refreshed` → người dùng mở `claude` một lần ở terminal máy chính để đăng nhập lại, rồi ↻ Rà lại (hoặc Bỏ qua ở 📥 Việc cần bạn).

## 6. Rủi ro / còn chưa ổn
- Seedance ref-only có thể theo khoảng cách máy của ref (B9) → con rối nhỏ/to khác khung đầu; ref ở đây là cú máy tĩnh nên ít rủi ro hơn S6 #33.
- Phông xanh trong ref: có thể lọt nền xanh vào video → đã chặn bằng chữ; nếu lọt, phải làm ref thay nền (tách phông → nền xám) trước khi gửi.
- Điện thoại trên tay con rối gỗ là đạo cụ mới (không có ảnh mẫu) — kiểm ở ảnh khung đầu.
- Video 12,6 s một clip: Seedance tính ~13 s.

## 7. Bước kế (chờ người dùng)
1. Cổng gen ẢNH: 1 ảnh khung đầu (giá mục 5) → duyệt.
2. Cổng gen VIDEO riêng: nháp 480p → duyệt → 1080p.
3. Hậu kỳ (0 USD): ghép 2 mèo tách phông xanh góc dưới, chữ 2 dòng trên cùng (font UTM Impact như #33), nhạc gốc TikTok.
