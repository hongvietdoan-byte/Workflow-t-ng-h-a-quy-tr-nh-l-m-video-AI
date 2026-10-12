# Báo cáo kết thúc dự án #24 — "Teasing HĐ Trồi lên & HĐ Khóc ai oán" (12/10/2026)

- **Bản giao:** `D:\AI-Video-Output\2026-10-11_du-an-24\24_final_1080p_v4.mp4` (nhạc hài H2) và `24_final_1080p_v4_nhacH1.mp4` (nhạc H1). Mỗi bản có thêm bản 720p để xem. Video 9:16, dài 44,4 s, 12 shot.
- **Thời gian:** tạo dự án 08/10, bản cuối v4 ngày 12/10, tổng cộng 5 ngày.
- **Nguồn số liệu:** sổ chi `usage_events` (project_id 24, 468 dòng, dòng nào cũng có giá) và bảng `jobs`.
  - Các con số cộng tay trước đây trong TODO ra ≈ 45,6 USD vì có khoản bị cộng trùng giữa các đợt. **Số đúng là 42,30 USD theo sổ chi.**
  - Token của phiên Claude Code (tính theo gói) không nằm trong sổ chi.

## 1. Chi phí

**Tổng: 42,30 USD**, tức ≈ 0,95 USD cho mỗi giây video giao. Vượt trần "< 1 phút < 30 USD"; người dùng đã chấp nhận khi duyệt nâng 1080p.

| Loại | USD | Tỉ lệ | Ghi chú |
|---|---:|---:|---|
| Video (ClipAI) | 34,38 | 81 % | Seedance 2.5: 25,64 · Seedance 2.0: 8,10 |
| Claude (Sonnet 5) | 4,05 | 10 % | xem tách nhỏ bên dưới |
| Ảnh (GPT Image 2.5) | 3,48 | 8 % | |
| Âm thanh | 1,03 | 2 % | nhạc 1,00 · hiệu ứng 0,02 · TTS 0,02 |

**Theo ngày** (giờ UTC, nên phần rạng sáng 12/10 giờ VN được tính vào ngày 11/10):

| Ngày | USD | Nội dung |
|---|---:|---|
| 08/10 | 10,10 | Gồm lượt video Seedance 2.0 bị bỏ: 8,10 |
| 09/10 | 2,17 | |
| 10/10 | 1,48 | |
| 11/10 – rạng sáng 12/10 | 28,56 | Nháp 2.5, nâng 1080p, shot 11–12, nhạc |

**Video — tiền đã dùng và tiền mất:**

| | Khoản | USD |
|---|---|---:|
| Dùng được | Seedance 2.5 bản 1080p | 20,28 |
| Dùng được | Seedance 2.5 nháp 480p đã duyệt | 4,22 |
| Mất | Lượt Seedance 2.0 ngày 08/10, bỏ cả lượt (480p 4,05 + 720p 4,05) | 8,10 |
| Mất | Nháp 2.5 bị loại | 1,13 |

Tổng tiền video mất: **9,23 USD**, tức 27 % tiền video.

**Ảnh:**

| Nhóm | USD |
|---|---:|
| Ảnh đã duyệt (26 ảnh) | 1,35 |
| Ảnh bị loại (18 ảnh) | 0,94 |
| Ảnh gen xong nhưng không dùng / còn chờ duyệt | 0,94 |
| Khung cuối và mẫu chuẩn | 0,26 |

**Claude (4,05 USD):**

| Khâu | USD |
|---|---:|
| Tổ rà soát tác động | 1,14 |
| Đạo diễn và các khâu con (sân khấu 0,53 · Đạo diễn 0,47 · máy quay 0,22 · BYĐ 0,10 · viết lại / duyệt nền 0,06) | 1,37 |
| QC (QC 0,26 + Tổ QC học việc 0,36) | 0,62 |
| Motion | 0,25 |
| Còn lại | 0,67 |

**Đếm job:**

| | Đã duyệt | Bị loại | Hỏng | Huỷ | Thành công nhưng không dùng | Còn chờ duyệt |
|---|---:|---:|---:|---:|---:|---:|
| Ảnh | 26 | 18 | 1 | 2 | 11 | 7 |
| Video | 14 | 22 | 8 | 3 | 7 | — |

## 2. Số lần phải sửa qua chat

Hệ thống chưa tự xử lý được nên phần lớn việc phải qua chat với Claude:

- **Ảnh:** 18 vòng vẽ lại / sửa (r1–r18). Ngoài ra có vòng ảnh riêng cho shot 11–12.
- **Video:**
  - Lượt Seedance 2.0 ngày 08/10, bỏ cả lượt.
  - P1: loại 14 clip cũ.
  - Chuẩn bị v2: bật khung cuối, vẽ lại khung cuối shot 7, tách shot 4, kéo dài shot 3.
  - Nháp 2.5, rồi nâng 1080p.
  - Shot 11–12 làm sau cùng.
- **Dựng:** 3 bản nháp (v1–v3) và 4 bản cuối (v1–v4). Phải sửa tay:
  - canh giọng theo môi;
  - chọn nhạc hài;
  - cân mức hiệu ứng;
  - vị trí popup ba lần: v1 che mặt, v2 rơi xuống hông, v3 lấn vùng tab TikTok, v4 đạt;
  - nhiễu sóng cuối video.

**Loại lỗi gặp khi làm** (nhóm theo nguyên nhân):

1. **Nền / bối cảnh:**
   - nền không khớp map 3D;
   - góc thấp vẫn thấy miệng giếng;
   - khoanh trên ảnh bị hiểu nhầm thành chỗ đặt máy;
   - 2 nền lệch nhau giữa các shot liền.
2. **Ảnh mẫu Kho:** thiếu ảnh mẫu hoặc ảnh mẫu bẩn, lan vào mọi shot. Riêng yêu nữ dạng 2 bị QC chấm sai.
3. **Khung đầu / khung cuối:** khung cuối không theo động tác, phải vẽ lại; bố cục không giữ như ảnh đã duyệt.
4. **QC / Tổ rà soát báo nhầm:**
   - so khung đầu với trạng thái cuối;
   - "4 s chỉ một pha" dù motion đã chia 4 nhịp;
   - Claude nhìn đúng nhưng kết luận sai trái/phải.
5. **Ước tính tiền sai:**
   - coi job cũ là "đã làm" nên báo 3,11 USD thay vì ~27;
   - bản cao tính lẻ từng shot;
   - đơn giá 1080p chưa đo (đo thật: 0,5254 USD/s).
6. **Video đơ:** cảnh thiếu chuyển động nền.
7. **Âm thanh:** chỉ 1–2 hiệu ứng mỗi shot, không có mốc giây; câu đồng thanh bị nhỏ; giọng lệch môi.
8. **Dựng:** popup đặt sai chỗ; runner cắt bản cao sai đoạn; ffmpeg trên ổ G:.
9. **Vận hành:** job tự sửa bị kẹt ở hàng chờ; tên nhân vật có dấu làm lệch khối thoại.

## 3. Đã vào hệ thống / chưa

| Bài học | Trạng thái |
|---|---|
| Vị trí sau động tác, giữ bố cục ảnh duyệt, nhịp ref, cỡ khung theo nhịp (`shot_lessons`) | ✅ đã gộp 11/10 |
| Mặt phẳng nền theo sơ đồ cảnh, không vượt trục 180° | ✅ |
| Khung cuối `end_frames` theo BYĐ | ✅ (vẫn còn ca vẽ lại) |
| Tên nhân vật không dấu trong khối thoại | ✅ 12/10 |
| Cảnh không đơ (`ambient_motion`) | ✅ code xong, **cờ TẮT** — cần bật thử ở #27 |
| QC khai quan sát dạng enum, code áp luật (`qc_observe_enum`) | ✅ code xong, **cờ TẮT** |
| Tổ rà soát phân biệt khung đầu và trạng thái cuối (`change_review_frames`) | ✅ code xong, **cờ TẮT** |
| Job tự sửa không kẹt (`auto_send_self_fix`) | ✅ code xong, **cờ TẮT** |
| Ước tính video: job cũ, bản cao, đơn giá 1080p | ⏳ Codex (ĐỢT 10 việc 3 / Đợt 8 việc 3) |
| Âm thanh theo từng chuyển động (mốc giây, theo nhịp BYĐ) | ⏳ chưa có, chỉ làm tay (`bang_am_thanh.md`) |
| Câu đồng thanh | ⏳ Codex ĐỢT 12 việc 5 |
| Vai dựng tự canh giọng theo môi | ⏳ chỉ có script tay (`final_v2/align.py`) |
| Luật vùng an toàn TikTok / Reels cho chữ, popup, HUD | ⏳ hộp thư 12/10 07:00 — CHỜ |
| Popup đặt theo vị trí mặt (dưới cằm, không lấn vùng an toàn) | ⏳ làm tay ở v4 (script `final_v4/build_video_v4.py`) |
| Runner cắt bản cao sai đoạn | ⏳ để sau #24 (file runner) |
| ffmpeg trên ổ G: | ⏳ Codex ĐỢT 14 việc 3 |

## 4. Dashboard / Tiểu Nhị cần gì để đồng nghiệp tự làm (không phải chat)

1. **Sửa shot bằng lời trên Dashboard** (trợ lý sửa shot): đổi chỗ đứng, góc, khung cuối. Mọi trường liên quan sửa đồng bộ, kèm báo giá trước khi vẽ lại.
2. **Vai dựng cuối có giao diện:**
   - chọn nhạc theo đoạn cảm xúc;
   - cân hiệu ứng;
   - canh giọng theo môi tự động;
   - popup đặt theo mặt + vùng an toàn nền tảng, có xem trước khung.
3. **Báo giá đúng trước mỗi lần gen**, gồm cả bản cao. Hiện ước tính còn sai thì người dùng phải nhờ Claude tính tay.
4. **Gói chẩn đoán và phiếu chuyển lên** khi QC hoặc Tổ rà soát báo nhầm. Người làm không gỡ được thì có đường báo, kèm bài học quay về hệ thống.
5. **Bật dần các cờ đã có** (ambient_motion, qc_observe_enum, change_review_frames, auto_send_self_fix) trên dự án mới, đo kết quả rồi mới chính thức.

## 5. Rút kinh nghiệm chi phí

- **Không gen video trước khi ảnh và khung cuối đạt.** Lượt Seedance 2.0 ngày 08/10 bỏ trắng 8,10 USD, chiếm 19 % cả dự án.
- **Thấp trước, cao sau** đã hiệu quả ở 11/10: nháp 480p (4,22) rồi mới nâng 1080p (20,28). Nháp bị loại chỉ mất 1,13 USD.
- **Nâng 1080p là khoản lớn nhất** (≈ 48 % tổng). Dự án sau nên chỉ nâng các shot then chốt (phương án B, như ước giá #27).
- **Tổ rà soát (1,14 USD) báo nhầm nhiều.** Bật `change_review_frames` sẽ giảm cả tiền lẫn số lần phải sửa qua chat.

## 6. Lọc lại: học được gì → đã khắc phục chưa → dự án mới (#27) đã tránh được chưa

Trạng thái cờ đọc THẬT trên máy chính lúc 12/10 ~10:00 (`features.state`). "Đã tránh" chỉ khi code có VÀ đang chạy cho dự án mới; code có mà cờ TẮT = **chưa tránh**.

| # | Học được (lỗi #24) | Đã khắc phục trong code? | #27 tránh được chưa | Cần làm để tránh |
|---|---|---|---|---|
| 1 | Gen video khi ảnh/khung cuối chưa đạt → mất 8,10 USD | ✅ lớp kiểm video TRƯỚC gen `video_pregen` (K3) | ❌ cờ **TẮT** | Bật `video_pregen` trước khi gen video #27 |
| 2 | Nền không khớp map 3D, nền lệch giữa shot liền, vượt trục | ✅ nền 3D + máy quay sân khấu (`stage_camera`), bài học shot trong công thức prompt | ✅ cờ BẬT (`stage_camera`, `prompt_formula`) | — (#27 có 3D Tháp #263) |
| 3 | Bố cục không giữ như ảnh duyệt, vị trí sau động tác | ✅ `shot_lessons` qua `prompt_formula` / `stage_solver` | ✅ BẬT (phần cảnh báo lệch bố cục `layout_drift_review` TẮT) | Bật `layout_drift_review` nếu muốn Tổ rà soát báo |
| 4 | Khung cuối không theo động tác | ✅ `end_frames` + BYĐ | ⚠ `end_frames` BẬT, nhưng BYĐ (`shot_intent`) **TẮT** | Bật `shot_intent` (Đạo diễn điền BYĐ; tốn thêm ≈ 0,1–0,2 USD Claude) |
| 5 | Ảnh mẫu Kho bẩn / thiếu lan vào mọi shot | ⚠ một phần: Kho có trạng thái duyệt, nhãn "có HUD = chỉ ref" | ⚠ #27: ảnh Halloween mới ở `claude_ok` — người dùng cần xác nhận; trang phục khóa theo hồ sơ (`short_lock_outfit`) TẮT | Người dùng xem Kho #423–#433; bật `short_lock_outfit` |
| 6 | QC chấm sai (nhìn đúng, kết luận sai) | ✅ `qc_observe_enum` | ❌ TẮT | Bật `qc_observe_enum` |
| 7 | Tổ rà soát báo nhầm khung đầu ↔ trạng thái cuối (1,14 USD) | ✅ `change_review_frames` | ❌ TẮT (Tổ rà soát BẬT → vẫn báo nhầm) | Bật `change_review_frames` |
| 8 | Video đơ, thiếu chuyển động nền | ✅ `ambient_motion` | ❌ TẮT | Bật `ambient_motion` |
| 9 | Job tự sửa kẹt hàng chờ | ✅ `auto_send_self_fix` | ❌ TẮT | Bật nếu dùng tự sửa |
| 10 | Ước tính tiền sai (job cũ, bản cao, đơn giá 1080p) | ⏳ Codex chưa gộp | ❌ | Báo giá #27 tôi tính tay theo đơn giá đo thật 0,5254 USD/s |
| 11 | Âm thanh theo từng chuyển động, đồng thanh | ⏳ chưa có / Codex | ❌ | Làm tay ở vai dựng như #24 |
| 12 | Giọng lệch môi | ⏳ script tay | ⚠ #27 chỉ có lời dẫn (không nhép) → không áp dụng | — |
| 13 | Popup / chữ / HUD lấn vùng an toàn TikTok, che mặt | ⏳ chưa vào code (CHỜ Codex) | ❌ — #27 có nhiều chữ hậu kỳ (tên cổng, đếm ngược, thông báo kẹt, BOOYAH) | Làm tay theo luật v4: dưới cằm, trên 8 % / dưới 75 % / lề phải ≥ 130 px |
| 14 | Tên nhân vật có dấu lệch khối thoại | ✅ | ✅ (đã gộp) | — |
| 15 | Đạo diễn hỏng định dạng khóa nhân vật (#27 hôm nay, mất 0,93 USD) | ✅ sửa 12/10 (chuẩn hóa list → chữ), chờ cả bộ test | ⏳ dùng được sau khi gộp + khởi động lại Dashboard | — |
| 16 | Báo "thiếu" tài nguyên đã có trong thư mục | ✅ quy trình: xem từng tài nguyên trước khi hỏi | ✅ #27 đã xem hết, tự dùng Gloowall/cổng portal | — |

**Tóm lại:** code đã có cho phần lớn lỗi #24 (1, 4, 6, 7, 8, 9), nhưng **đang TẮT** → nếu gen #27 ngay thì vẫn lặp lại. Việc chưa có code (10, 11, 13) phải làm tay như #24.
**Đề xuất trước khi gen #27:** bật `video_pregen`, `change_review_frames`, `qc_observe_enum`, `ambient_motion` (bật cờ 0 USD; chi phí khi chạy chưa đo — sẽ ghi sổ chi); cân nhắc `shot_intent` (+≈ 0,1–0,2 USD) và `short_lock_outfit`. Theo luật học việc, cờ mới bật trên dự án mới được đo và báo lại kết quả.
