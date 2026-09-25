# Vai Dựng (Editor hậu kỳ) — bộ kỹ năng nghề (V4 GĐ4, 2026-09-25 — chờ người dùng duyệt)

> Dựng nhận **clip đã duyệt + giọng + chữ trên màn hình + nhạc** và làm ra bản giao. Phần lớn là **code** (`core/delivery.py`,
> `final_cut.py`, `ffmpeg_studio.py`, `subtitles.py`, `text_placement.py`, `audio_lib.py`, `voice.py`, `music.py`, `music_timing.py`,
> `sound_ai.py`, `sfx_plan.py`, `composite.py`, `plate_env.py`, `formats.py`). Tài liệu này để code và (khi cần mắt) Claude/người biết **vì sao** và
> **đặt ở đâu**. Không đổi shot, không gen lại hình — lỗi hình trả Quay phim, lỗi diễn/giọng trả Đạo diễn.
> Mỗi kỹ năng: **Làm gì · vì sao** — **Trong pipeline** (✅ code có · ⚠ làm một phần · ❌ chưa có → việc code, README) — **Kiểm** — **Ví dụ FF**.
> Nguồn: `knowledge/sources.md` mục GĐ4 (số [En]). Vùng an toàn: `safe_zones.md`. **[KN]** = kinh nghiệm nghề chưa có nguồn chính thức —
> code coi là giá trị khởi điểm, đo lại được.

## Tầng 1 — Mục đích
Người xem hiểu và cảm được câu chuyện **trên điện thoại, trong app**: nghe rõ thoại, đọc kịp chữ không bị giao diện che, nhịp cắt theo cảm
xúc, âm thanh làm thế giới game "thật", màu các shot liền nhau như quay cùng một lúc.

## Tầng 2 — Cách nghĩ
1. Dựng theo **timeline của Đạo diễn** (thứ tự shot, độ dài đã chuẩn hóa); clip dài hơn shot → lấy đoạn có hành động chính (E1).
2. Đặt **giọng** (không chồng tiếng, đúng giây của shot) (E2), rồi **âm thanh** nhiều lớp (E3), rồi **nhạc** theo nhịp dựng (E4).
3. **Màu**: sửa từng shot → khớp màu các shot liền nhau/cùng nơi → look (E5); hiệu ứng khi có lý do (E6).
4. **Chữ** trong vùng an toàn chung, không đè mặt (E7); đo **độ to** và xuất theo nền tảng (E8).
5. **Tự rà như người xem thật** (E9) trước khi giao Đạo diễn duyệt.

## Tầng 3 — Kỹ năng

### E1. Nghệ thuật cắt
- **Làm gì · vì sao.** Thứ tự ưu tiên của một điểm cắt (Murch [E1]): **cảm xúc** (51%) > **câu chuyện** (23%) > **nhịp** (10%) > **hướng mắt**
  người xem (7%) > mặt phẳng 2D/trục (5%) > liền mạch không gian 3D (4%) — cảm xúc nặng hơn năm tiêu chí còn lại cộng lại; phải hy sinh thì
  bỏ từ dưới lên. Chỉ cắt khi có lý do; phân vân thì để dài hơn; cắt giữa một chuyển động để chuyển động che vết cắt (Dmytryk [E2]).
  Ở khâu dựng của pipeline, cảm xúc của điểm cắt đứng **dưới điều kiện nghe rõ thoại và đọc được chữ** (tầng 4): không cắt cho "đẹp nhịp"
  mà làm cụt câu hay mất chữ.
  - **Cắt J / L**: âm shot sau vào trước hình (J), hoặc âm shot trước kéo sang hình sau (L) [E3] — với giọng lồng: cho câu vào sớm 4–12
    khung ở chỗ đổi người nói [KN]. **Cắt khớp** (hình khối/chuyển động giống nhau), **cắt xen** (hai hành động cùng lúc), **dựng chuỗi**
    (nén thời gian trên nhạc).
  - **Nhịp**: độ dài shot liền nhau thay đổi theo **cụm** (cụm nhanh xen cụm chậm), không đều tăm tắp [E4]; cao trào ngắn, chỗ thở dài.
- **Trong pipeline.** ✅ Cắt theo `duration_s`, lấy đầu clip (Quay phim dặn hành động xảy ra sớm); ✅ một vị trí máy nhiều shot: cắt clip dài
  thành đoạn (`shots.setup_motion`, H5); ✅ chuyển cảnh cắt/mờ chồng/mờ đen (`ffmpeg_studio.OVERLAP_STYLES`). ❌ **Cắt J/L** cho giọng
  (việc code D1). ❌ Chọn điểm cắt theo chuyển động trong clip (đo bằng khác biệt khung — việc code D2).
- **Kiểm.** Code: `final_cut.render_problems` (tổng thời lượng, mờ chồng dài hơn shot). Người: xem bản dựng.
- **Ví dụ FF.** ✔ 519 shot FF: trung vị ~2 s/shot, ~24 shot/phút (`ff_directing.md`). ✘ Lần chạy 4: shot im lặng 0,5 s cắt quá nhanh, người
  xem không kịp đọc.

### E2. Giọng và thoại
- **Làm gì · vì sao.** Thoại là thứ người xem cần nghe rõ nhất. Không chồng tiếng: câu sau bắt đầu sau câu trước + nghỉ 0,12–0,15 s; clip
  kéo dài theo độ dài giọng thật. Có giọng lồng thì tắt tiếng gốc của clip (model không nói đúng tiếng Việt), trừ shot khớp môi đã tạo kèm giọng.
  **Dọn thoại**: lọc cắt trầm ~80 Hz, khử xì nhẹ, khử ồn nhẹ 6–12 dB để giọng không méo (ffmpeg: `highpass` mặc định 3000 Hz → phải đặt
  `f=80`; `deesser` mặc định không làm gì tới khi đặt cường độ [E22][E29]).
- **Trong pipeline.** ✅ `voice.fit_durations`, `audio_lib.schedule_by_cues` (không chồng tiếng); ✅ giữ giọng đúng giây shot đã khớp môi
  (GĐ3); ✅ kiểm giọng bị cắt/thiếu chữ (`voice_check`); ✅ chỉ đạo giọng `delivery` (Đạo diễn Đ5, cờ `voice_direction`). ❌ Dọn thoại
  (lọc 80 Hz + khử xì) trên giọng TTS — việc code D3 (giọng TTS sạch sẵn; cần khi có giọng thu).
- **Kiểm.** Code: `audio_lib.overlapping_tts`; `voice_check`. Người: nghe có tiếng.
- **Ví dụ FF.** ✔ 2A: câu "Không liên quan đến ông." bị cắt giữa chữ (0,64 s) → tạo lại có "…" ở cuối → 1,12 s, kết tự nhiên. ✔ 2A: giọng
  lồng chạm 0,0 dBFS → thêm bộ giới hạn, đo −1,3 dBFS.

### E3. Âm thanh nhiều lớp
- **Làm gì · vì sao.** Thế giới game thành "thật" nhờ âm: **nền không khí** chạy liên tục dưới thoại (gió, trận đánh xa) để vết cắt không
  "hụt hơi", chuyển nền bằng mờ chồng âm; **foley** theo hành động (bước chân, áo, vũ khí); **hiệu ứng nhiều lớp** — một phát súng = đầu
  (transient) + thân + đuôi vang theo môi trường; va chạm = đập + mảnh vỡ + trầm; **vút/dâng** dẫn vào cú chuyển, **cú đập** rơi đúng khung của
  cú đánh; **không gian**: gần thì khô, đủ trầm; xa thì bớt cao tần, thêm vang; **thời tiết** (mưa, sấm, gió) khớp hình [KN].
- **Trong pipeline.** ✅ Tạo SFX bằng ClipAI (`audio_lib.submit_sfx`, sổ chi lượt âm thanh); ✅ nghe clip để biết âm có sẵn (`sound_ai` YAMNet,
  chỉ dùng tự động khi tin ≥ 0,40); ✅ trộn lớp phụ (`ffmpeg_studio.build_extras_mix_cmd`); ✅ **Claude đặt hiệu ứng** theo cảnh + thư viện âm
  của người dùng (`core/sfx_plan.py`, nút ở Bước 5, autopilot tự đề xuất rồi áp dụng) — cố ý chỉ cho **điểm nhấn** (đập, vút, va chạm) và
  chuyển cảnh, không làm nền liên tục. ❌ Âm theo **thời tiết** tự động (mưa/sấm theo `weather`, sấm đúng giây chớp của
  `plate_env.flash_times`) — việc code D4. ❌ **Nền không khí liên tục** cả cảnh — việc code D5, là lớp **riêng** dưới lớp điểm nhấn của
  `sfx_plan` (hai lớp không thay nhau).
- **Kiểm.** Code: YAMNet nghe lại bản trộn. Người: nghe có tiếng, bằng tai nghe điện thoại.
- **Ví dụ FF.** ✔ Video FF gốc: hiệu ứng kỹ năng có ở ~38% shot — là "chất Free Fire", cần âm đi kèm. ✘ Cảnh đêm tuyết im lặng hoàn toàn
  (không nền không khí) nghe như chưa làm xong.

### E4. Nhạc nền
- **Làm gì · vì sao.** Nhạc chọn theo **cảm xúc từng đoạn** (ưu tiên 51% của Murch [E1]); dựng theo phách: 1 phách = 60/BPM giây; cắt mỗi ô nhịp
  = thong thả, mỗi 1–2 phách = căng [E31]; **điểm rơi** của nhạc trùng cú ngoặt (hạ gục, lộ mặt); **hạ nhạc khi có thoại** (sidechain); không
  nhả hạ nhạc giữa hai câu cách nhau < 0,5 s để tránh "bơm"; **khoảng lặng có chủ ý** 0,3–1 s ngay trước cú ngoặt tăng lực cú đập [KN].
- **Trong pipeline.** ✅ `music_timing`: đoạn nhạc theo nhịp dựng, BPM 70–140 hợp mốc cắt, chấm bản nháp theo độ to ở mốc ngoặt, giữ bản khớp
  nhất (autopilot + Bước 5); ✅ hạ nhạc khi có giọng (`ffmpeg_studio.DUCK`: ngưỡng 0,02 ≈ −34 dBFS, tỉ lệ 8, attack 20 ms, release 400 ms →
  **tính từ tham số**, giọng ở −20 dBFS hạ nhạc ~12 dB, giọng to hơn hạ nhiều hơn; nguồn thứ cấp khuyên 6–10 dB [E32] — **chưa đo trên bản
  trộn thật**); ✅ nhạc mờ vào 0,3 s. ❌ Khoảng lặng trước cú ngoặt — việc code D6.
- **Kiểm.** Code: `music_timing.score_draft` (độ to tại mốc ngoặt). Người: nghe.
- **Ví dụ FF.** ✔ 2A: model nhạc luôn mờ 5 s cuối → xin dài thêm 4 s rồi cắt ở cuối phim (`TAIL_PAD_MS`).

### E5. Chỉnh màu và khớp màu giữa các shot
- **Làm gì · vì sao.** **Sửa trước, look sau**: cân bằng trắng, phơi sáng, tương phản từng shot, rồi mới đặt look chung (Resolve Colorist Guide
  [E27]). **Khớp màu** các shot liền nhau/cùng nơi: điểm đen, điểm trắng, màu trung tính — người xem thấy ngay khi hai shot cùng chỗ khác
  tông. **Shot ghép phông xanh**: khớp mức đen/trắng của người với nền, khử viền xanh, **light wrap** (ánh sáng nền tràn lên viền người,
  áp trước khi ghép — Nuke [E26]), **khớp hạt** (thêm nhiễu cùng mức nền) [KN]. **Màu da**: vạch màu da trên vectorscope chỉ để tham khảo,
  sửa cả shot trước [E27][E28]. Vignette nhẹ dẫn mắt, không làm tối vùng có chữ.
- **Trong pipeline.** ✅ Ghép: `composite.match_colour` (màu người về phía ánh sáng quanh, 35%), `light_wrap` (0,28), cùng độ chỉnh màu giờ/thời
  tiết cho người và nền (`plate_env.grade`, 60%). ❌ **Khớp màu giữa các shot** trong bản dựng (đo trung bình vùng tối/sáng mỗi shot, chỉnh
  shot lệch về shot neo cùng `sequence`) — việc code D7 (quan trọng nhất khi bật gói bối cảnh). ❌ Khớp hạt người–nền — việc code D8.
- **Kiểm.** Code (D7 khi có): độ lệch màu giữa shot cùng nơi. Người: xem liền các shot cùng cảnh.
- **Ví dụ FF.** ✔ GĐ2: người sáng quá trên nền đêm → chỉnh màu người theo giờ. ✘ Job 165/197: màu áo Kenta trôi/nhấp nháy trong clip — lỗi hình
  (trả Quay phim gen lại), không sửa bằng màu.

### E6. Hiệu ứng
- **Làm gì · vì sao.** Hiệu ứng chỉ khi **có lý do** (quy tắc "cắt phải có lý do" áp cho hiệu ứng [E2]); không dùng khi nó che mặt, che chữ, hay
  làm giảm độ rõ của truyện. Thời tiết, phát sáng, lóa: **cùng hướng nguồn sáng** với nền; hạt phủ cuối, đều cả khung để "dán" lớp ghép; rung
  máy khi va chạm 3–8 khung, giảm dần, bắt đầu đúng khung va chạm; chuyển cảnh mặc định **cắt thẳng** — lia nhanh/zoom chỉ khi đổi cảnh hay
  nhảy thời gian, kèm âm vút [KN]. **Chữ động kiểu game FF**: thông báo hạ gục, bảng tên — trong vùng an toàn, đủ lâu để đọc.
- **Trong pipeline.** ✅ Thời tiết rơi (mưa/tuyết/bụi) + chớp trên ảnh và clip (`plate_env.overlay_still/overlay_video`); ✅ thông báo game
  kiểu riêng (vàng trên nền tối, dải trên — `subtitles` HUD); ✅ card cuối. ❌ Rung máy khi va chạm, hạt, lóa — việc code D9. ❌ Bảng tên
  nhân vật động — việc code D10.
- **Kiểm.** Người: có hiệu ứng nào không cần? Code: chữ HUD trong vùng an toàn.
- **Ví dụ FF.** ✔ #6 "HỆ THỐNG: Maxim đã bị hạ." thành thông báo game trên màn hình, không phải giọng đọc.

### E7. Chữ và vùng an toàn
- **Làm gì · vì sao.** Xem `safe_zones.md` (số chính thức + nguồn). Chữ nằm trong **vùng an toàn chung** mọi nền tảng sẽ đăng; không đè mặt;
  phụ đề một vị trí cố định, chỉ dời khi đè mặt (dời cả câu); đủ lâu để đọc: tối đa **17 ký tự/giây** (mức Netflix cho trẻ em, chặt hơn mức
  người lớn 20 [E23]), tối thiểu ~0,83 s, cách nhau ≥ 2 khung [E24]. Khung dọc hẹp: ~20–28 ký tự/dòng, 2 dòng [KN].
- **Trong pipeline.** ✅ Lề trên 15% / dưới 36% (chính thức 35%, code thêm 1% đệm) / trái 6% / **phải 18%** khung dọc (`subtitles.SAFE_*`; phải sửa từ 6% lên 18% ở GĐ4 theo số
  chính thức Google Ads); ✅ dò mặt YuNet trên khung thật, dời câu (`text_placement`); ✅ `MAX_CPS = 17` + bảng mật độ (`subtitles.density`).
- **Kiểm.** Code: test vùng an toàn; mật độ chữ. Người: bảng khung có chữ.

### E8. Độ to và xuất bản
- **Làm gì · vì sao.** Nền tảng tự chuẩn hóa độ to — bản quá to bị hạ (mất lực), quá nhỏ nghe yếu so với video bên cạnh. **Số chính thức:**
  Spotify −14 LUFS, đỉnh thật < −1 dBTP (< −2 nếu bản master to) [E17]; AES TD1008: thoại ~−18 LUFS, nhạc −16, nội dung trộn −17, đỉnh
  thật ≤ −1 dBTP trước bộ mã hóa nén [E18][E19]; EBU R128 −23 LUFS (phát sóng) [E20]. **YouTube, TikTok, Instagram, Facebook không công bố số LUFS** — YouTube chỉ xác nhận có
  "Stable volume" [E15]; mức −14 của YouTube là số đo của bên thứ ba [E16]. → Mục tiêu pipeline: **−14 LUFS tích hợp, đỉnh thật −1,5 đến
  −2 dBTP** (chừa đệm cho AAC) [KN]. **Thông số xuất YouTube (chính thức)** [E13]: MP4 faststart, H.264 High 4:2:0, BT.709, 1080p 8 Mbps
  (24–30 fps), AAC-LC 48 kHz stereo 384 kbps. TikTok quảng cáo: 9:16 ≥ 540×960, phải có tiếng [E6][E7].
- **Trong pipeline.** ✅ Giới hạn đỉnh −2 dBFS cuối mọi bước trộn (`ffmpeg_studio.PEAK_LIMIT` — `alimiter` chỉ giới hạn đỉnh **mẫu**, không
  phải đỉnh thật); âm 48 kHz stereo; ✅ xuất theo kích thước/dung lượng (`resize_to_size`, 2 lượt). ✅ **Đo** LUFS + đỉnh thật của một file
  (`ffmpeg_studio.measure_loudness`, thước EBU R128 của ffmpeg; `loudness_problems` so với mục tiêu — GĐ4). ❌ **Chuẩn hóa** LUFS (`loudnorm`
  2 lượt, I=−14, TP=−1,5; mặc định ffmpeg là I=−24 [E22]) và hiện số đo ở Bước 5 — việc code D11. ❌ `_ENCODE` ép `-r 24`, **thiếu
  `+faststart` và thẻ màu BT.709** so với bảng YouTube — việc code D12.
- **Kiểm.** Code: `measure_loudness` + `loudness_problems` (mục tiêu −14 ± 2 LUFS, đỉnh thật ≤ −1,5 dBTP) — **mới là hàm, chưa nối vào Bước 5
  / autopilot** (việc D11). Người: nghe cạnh một video FF chính thức trên điện thoại.
- **Ví dụ FF.** ✔ 2A: đỉnh 0,0 → −1,3 dBFS sau khi thêm bộ giới hạn. ✔ Đo thật bản giao #7 (2026-09-25): **−14,7 LUFS, đỉnh thật −2,9 dBTP,
  LRA 5,1** — nằm trong mục tiêu dù chưa chuẩn hóa (một lần đo, chưa phải bảo đảm cho mọi dự án).

### E9. Tự rà như người xem thật
- **Làm gì · vì sao.** Không có số chính thức về tỉ lệ người xem tắt tiếng (con số "85%" hay nhắc không có nguồn gốc Meta; Facebook IQ 2017 chỉ
  khuyên làm video hiểu được khi tắt tiếng [E35]; Reels mặc định bật tiếng [E10]; TikTok–Kantar: 88% người dùng coi âm thanh là thiết yếu [E8]).
  → Rà cả hai: (1) **tắt tiếng** — truyện hiểu được nhờ hình + phụ đề + chữ; (2) **bật tiếng** — thoại rõ trên nhạc; (3) chồng lớp giao diện app
  lên từng khung — chữ/mặt không lọt vào vùng bị che; (4) thu nhỏ ~360×640 — chữ còn đọc được; (5) đo lại độ to sau mã hóa [KN].
- **Trong pipeline.** ✅ Bảng khung có chữ, dò mặt; ✅ animatic (Bước 1, `delivery.animatic`). ❌ Ảnh chồng lớp giao diện app lên khung — việc code D13.
- **Kiểm.** Người xem cuối (người dùng) + Đạo diễn duyệt.

## Tầng 4 — Ưu tiên khi xung đột
Nghe rõ thoại > đọc được chữ (không bị che) > cảm xúc/nhịp cắt theo Đạo diễn > liền mạch (màu, hướng) > đẹp/hiệu ứng. Đây là thang chung
(`knowledge/roles/README.md`) chiếu vào việc dựng: cảm xúc đã được Đạo diễn đặt vào shot và diễn xuất; thoại rõ và chữ đọc được là điều kiện để
cảm xúc đó tới người xem. Không sửa được bằng dựng → trả lại vai phụ trách kèm lý do (hình → Quay phim; diễn/giọng → Đạo diễn).

## Tầng 5 — Tự rà (trên bản dựng thật)
- Tắt tiếng có hiểu không? Bật tiếng có nghe rõ từng câu không, câu nào bị chồng/cắt cụt, hình đổi trước khi câu nói xong?
- Có chữ nào ngoài hộp an toàn, đè mặt, hiện quá nhanh? Có phân biệt được thoại với thông báo game không?
- Hai shot cùng nơi có cùng tông màu không? Người ghép có "dính" nền không (viền, bóng, hạt)?
- Có điểm cắt nào làm mất hành động chính, có chỗ nào im lặng hụt hơi, có hiệu ứng nào không cần?
- Độ to bản giao bao nhiêu LUFS, đỉnh bao nhiêu?
