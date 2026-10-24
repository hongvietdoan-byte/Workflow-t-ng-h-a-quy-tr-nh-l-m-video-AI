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

## 8. Đổi góc nền (người dùng 23/10, sau mục 5)
- Người dùng hỏi góc chính diện đoạn đường dài ở Cổng Trời → shot 1 đổi chỗ đứng `trung_tam_me_cung` → **`duong_truoc_cong`**
  (nhìn 89,8° dọc đường về biệt thự, biệt thự giữa khung cuối đường, hàng cây cao hai bên; con rối đứng trên bãi đá nứt đầu đường).
  Thời tiết `fog` → `cloudy` (sương che mất biệt thự ở xa). Sửa image_prompt + motion theo nền mới (bỏ hàng rào mê cung).
  Render 0 USD: `D:/AI-Video-Output/2026-10-23_meo-nhay-tap2/so_sanh_2_goc.jpg` (trái cũ, phải mới).
- `pregen_check --project 34` lần 2: vẫn **1 ảnh ≈ 0.22 usd (tối đa 0.88)**, video bản cao ≈ 7.84 USD, cổng không có, nền 3D sẵn;
  mã thoát 1 vì Tổ rà soát đang rà thay đổi #1767 (nếu lại lỗi OAuth → đăng nhập `claude` rồi ↻ Rà lại).
- 24/10 người dùng: góc `duong_truoc_cong` "cam thấp và quá xa" → thử `san_truoc` + `high` (chúc 30°: chỉ thấy sàn — lỗi A10 tập 1, bỏ) →
  **chốt thử `san_truoc` + `eye`**: sân trước biệt thự ở cuối đường dài, biệt thự chính diện gần (mái + 3 cửa mái), trời phía trên cho chữ,
  sân lát gạch xương cá phía dưới cho mèo. Sửa image_prompt/motion theo sân trước. Ảnh `so_sanh_duong_vs_san_truoc.jpg`.
  Chỗ đứng GIỮA đường (gần hơn `duong_truoc_cong`, xa hơn `san_truoc`) chưa có trong Kho 265 — muốn thì phải thêm spot vào Kho dùng chung
  với #31 (chưa làm). Máy "hơi cao" (`slightly_high`) nằm sau cờ `whitebox_height_dummy` đang TẮT.
- `pregen_check` lần 3: 1 ảnh ≈ 0.22 usd (tối đa 0.88); CHẶN vì Tổ rà soát: mọi change_events #1761–#1772 của #34 `failed` = OAuth
  Claude Code hết hạn.

## 9. Bàn đạo diễn 3D (người dùng 24/10: "phải dựng khối ở bàn đạo diễn mới có góc hợp lý")
- Bật 2 cờ `stage_view_ui` + `stage_desk_ui` (Dashboard ⚙ Cài đặt → Hệ thống → Tính năng thử, người dùng duyệt).
- Con rối thiếu `height_m` → người dùng: ~0,6 m. Không sửa Kho #452/#454 của #33: tạo bản Kho riêng **#456 "RỐI TÍM (tập 2)"**, **#457
  "RỐI ĐỎ (tập 2)"** (ảnh đã duyệt chép từ 454/452, hồ sơ approved, `height_m` 0,6), nối lại nhân vật, gỡ 452/454 khỏi #34.
- Luồng tổ làm phim offline 0 USD trên Dashboard (🗑 Làm lại → Đạo diễn → Quay phim → Quay phim duyệt ×2):
  - Đạo diễn: RỐI TÍM đứng (0; 0,45) mặt về máy (270°), lưng về biệt thự phía đông; RỐI ĐỎ ngồi (H 0,35) ở (0,25; −0,55) quay 3/4 về TÍM; trục TÍM→ĐỎ.
  - Quay phim: WS, s₀ = phải. Lần đo 1 máy sát 0,7 m (TÍM bị cắt, biệt thự 13 %) → sửa máy 1,1 m bị P3 (chúc 28°) → **lần đo 3: máy 0,75 m,
    chúc 7,6°, 24 mm, TÍM 26 % khung giữa-trái, ĐỎ 11 % bên phải, biệt thự phía sau** (24/28 phương án đạt). Ảnh
    `D:/AI-Video-Output/2026-10-23_meo-nhay-tap2/ban_dao_dien_m3.jpg`. Đã chọn lần đo `crew/m3`.
  - **Lỗi code (đã báo phiên chính qua hộp thư):** N5 "Dựng tấm ghép" luôn lấy `full_measure` (m1) → tấm ghép hiện máy cũ; ảnh m3 ghép tay.
  - Đang **chờ EP duyệt** (người dùng nói "duyệt" trong chat → `py tools/stage_auto.py --project 34 --scene 1 --crew-approve`), rồi render lại
    nền + `pregen_check`.
- 24/10 người dùng: "Sao cột đỏ thấp thế?" (RỐI ĐỎ ngồi, H 0,35, xa máy 2,1 m → 11 % khung) → "thử theo đề xuất": vẫn ngồi, dời lại gần.
  Làm lại 3 lần từ Đạo diễn: (−0,45; −0,25) → biệt thự chính diện nhưng RỐI ĐỎ sát máy hơn TÍM, bị cắt mép phải (thấy 39–54 %, sửa máy
  không cứu được); (0,1; −0,45) → máy về lại phía tây-bắc, ĐỎ vẫn nhỏ; **chốt (−0,3; −0,05)**, cách TÍM ~0,6 m: ĐỎ 15 % khung, thấy trọn,
  máy 0,75 m chúc 7,8°, biệt thự nửa trái phía sau. Quay phim "khop". Ảnh `ban_dao_dien_roi_do_gan.png`. Chờ EP duyệt.
- 24/10 người dùng **"duyệt"** (EP, trong chat) → `stage_auto.py --project 34 --scene 1 --crew-approve`: phase `xong`, máy shot 1 từ `crew/m1`.
  Render lại nền (`location_pack.py render`, 0 USD): máy 0,75 m trên chỗ đứng, pitch −7,8°, yaw 119,7°, 24 mm →
  `D:/AI-Video-Output/2026-10-23_meo-nhay-tap2/nen3d_ban_dao_dien.jpg`.
- `pregen_check` lần 4 (`pregen_check_4.txt`): 1 ảnh ≈ 0.22 usd (tối đa 0.88); video bản cao 1 shot ≈ 7.84 USD; cổng không có; nền 3D 0 shot
  chưa sẵn; **CÒN CHẶN** duy nhất: Tổ rà soát lỗi OAuth Claude Code hết hạn. Còn phải khóa Character Bible trước khi gen
  (`image_model` CSDL = gpt-image-2.5-sunburst; "Ảnh: deepix" trên Dashboard là nhà cung cấp).
- 24/10 người dùng "đã đăng nhập claude, rà lại và khóa Character Bible": **khóa Character Bible** (nút ✔ Duyệt & khóa → Storyboard,
  0 USD; RỐI TÍM/ĐỎ locked = 1, dự án vẫn paused). Đóng 3 mục cũ của Tổ rà soát (✓ Đã sửa). **Rà lại** 13 lần lỗi (gọi đúng hàm nút
  ↻ Rà lại vì Dashboard không hiện nút — xem `docs/DASHBOARD_CHUA_TU_LAM_DUOC_2026-10-24.md` mục 1) → vẫn LỖI OAuth: `claude auth status`
  của pipeline = `loggedIn: false` (tệp đăng nhập vẫn 23/10 23:03). `pregen_check` lần 5 (`pregen_check_5.txt`): 1 ảnh ≈ 0.22 usd (tối đa
  0.88), CÒN CHẶN duy nhất vì Tổ rà soát.
- 24/10 người dùng `/login` trong terminal máy chính → `claude auth status` (môi trường pipeline) `loggedIn: true` (claude.ai). Rà lại 13 thay
  đổi: reviewed 13, failed 0, sổ chi ghi 0.253 USD (claude_cli). Còn 2 mục vàng báo SAI (luật dò tên Kho — DASHBOARD_CHUA_TU_LAM_DUOC mục 6).
- **`pregen_check` lần 6 (`pregen_check_6.txt`): mã thoát 0 — "GEN ĐƯỢC — xin duyệt với giá ≈ 0.22 usd"** (tối đa 0.88): ảnh khung đầu
  0.052 · D6 0.088 · QC 0.065 · Claude khác 0.014. Video bản cao (cổng riêng) ≈ 7.84 USD. **DỪNG ở cổng gen ảnh, chờ người dùng "gen".**
- **24/10 12:46 người dùng "Chấp nhận duyệt" → gen ảnh khung đầu trên Dashboard** (▶ Tiếp tục bỏ tạm dừng → ▶ Gen ảnh … ≈ 0.22 USD →
  Có, chạy). Job 1197 `succeeded` 12:51 → `data/projects/34/images/job_1197.png` (gpt-image-2.5-sunburst, 1152×2048), sổ chi ghi 1 ảnh
  (deepix). Bản sao gửi người dùng: `D:/AI-Video-Output/2026-10-23_meo-nhay-tap2/anh_khung_dau_job1197.png`. Ảnh: RỐI TÍM đứng một chân
  dang tay, RỐI ĐỎ ngồi cầm điện thoại, biệt thự trái, cây phải, 1/3 dưới nền đá trống (chỗ ghép mèo thật). Claude tự kiểm ảnh còn
  "đang tự kiểm tra" sau > 6 phút (chưa có qc_results). **Chờ người dùng duyệt ảnh; gen video là cổng riêng (≈ 7.84 USD bản cao).**
- 24/10 người dùng so ảnh 1197 với 2 con mèo: mèo xám có di chuyển (nghiêng, nhổm dậy bước theo ở ~3 s) → **RỐI ĐỎ ngồi XỔM** (không
  ngồi bệt duỗi chân), quay lưng nửa về máy, nhìn RỐI TÍM; **điện thoại thường** (vỏ xanh đậm, 1 ống kính, không logo, KHÔNG iPhone).
  Giữ chỗ đứng sân khấu đã duyệt. Ảnh so sánh `so_sanh_meo_vs_anh1197.jpg`. Sửa `scenes.data` (image_prompt, action, performance.body)
  + `motion_prompts` (vai ĐỎ: ngồi xổm, nghiêng, nhổm dậy bước theo, về lại thế xổm; negative thêm "no iPhone, no brand logo")
  — sao lưu `data/_luu_tru_manifest_truoc_p34_ngoi_xom_1314.sqlite`. Tổ rà soát rà 2 thay đổi (0.12 USD), 0 chặn; mục vàng #903/#905
  lại là luật dò tên Kho #454 (báo sai). QC tự kiểm ảnh 1197 = giữ (0.00). `pregen_check_7`: mã 0. Vẽ lại 1 ảnh ≈ 0.16 USD chờ duyệt.
- 24/10 người dùng "Vẽ lại … dáng ngồi", rồi nói rõ **ngồi xổm = mông không chạm đất**. Vẽ lại trên Dashboard (Câu sửa tiếng Anh + Lý do
  "Nhân vật sai" — nút ↻ Vẽ lại bị khóa tới khi chọn lý do) → job 1197 `rejected`, **job 1198 `succeeded`** (`job_1198.png`, bản sao
  `anh_khung_dau_job1198_ngoi_xom.png`, so sánh `so_sanh_1197_vs_1198.jpg`): RỐI ĐỎ ngồi xổm, mông không chạm đất, lưng nửa về máy, điện
  thoại đen trơn. Khác bản cũ: RỐI TÍM mặc áo xanh + quần xanh đậm (đúng must_keep Kho), góc phải trời có trăng. Chờ người dùng duyệt ảnh.

## 10. Video + hậu kỳ (24/10, người dùng "Duyệt làm đến video cuối cùng")
- Trên Dashboard: ✔ Duyệt ảnh 1198 → (sửa motion: "colours fixed … no other colour" → "colours, clothes and the phone exactly as in
  the first image" vì Tổ rà soát #903/#905 cảnh báo nhuộm đồ xanh RỐI TÍM; rà lại 0.10 USD) → ✔ Duyệt tất cả (1 prompt) → Có (chờ 30 s)
  → ▶ Gen video (ước tính 2 clip ≈ 6.16 vì shot ⭐ hero, thực tế gửi 1) → **job 1199 nháp 480p** (Dashboard "đã chi 1.34 USD"): RỐI ĐỎ
  ngồi xổm, nhổm dậy đá chân/bước theo ở ~3 s, về lại thế xổm; RỐI TÍM theo đúng bài mèo cam → ✔ Duyệt clip → ⬆ Gen bản cao (≈ 6.85 USD)
  → **job 1200 bản cao 1080×1920** 24 fps 12,6 s (sổ chi 13,04 s 1080p). Bản sao `clip_ai_1080p_job1200.mp4`.
- Hậu kỳ (ngoài Dashboard, 0 USD) `hau_ky/hau_ky.sh`: nền = clip AI phóng 1080×1920 30 fps; mèo = TikTok cắt vùng 880×900 (x 100, y 640 —
  khung bao mèo cả clip x 120–961, y 662–1528), `chromakey 0x00FF00:0.16:0.08 + despill`, thu 480 px rộng, giữa đáy; chữ UTM Impact 64
  viền đen 5: dòng 1 trắng "Cốt tôi var cực mạnh với team địch", dòng 2 vàng "Tôi và Con Rối team địch kiểu:" (y 120 / 205); tiếng gốc
  TikTok; cắt 12,6 s. **Bản giao `D:/AI-Video-Output/2026-10-23_meo-nhay-tap2/MEO_NHAY_TAP2_FINAL.mp4`** (12,5 MB) — đã gửi người dùng.
- Chi phí lượt này: ảnh 2 × gpt-image (job 1197, 1198) + nháp 1.34 + bản cao ≈ 6.85 (ước tính) + Claude rà soát 0.12 + 0.10.
