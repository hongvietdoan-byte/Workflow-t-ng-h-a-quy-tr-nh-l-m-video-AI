# Kế hoạch S11 — Director mở rộng: ý tưởng → kịch bản, cover video ref, học trending (bản v2, 2026-10-01)

> **v2** thay hẳn v1 (cùng ngày). v1 nêu 7 câu hỏi; người dùng đã trả lời Q1–Q7, và cho thêm hai thông tin mới:
> (a) **Seedance báo lỗi khi video ref có mặt người** → clip nhảy phải chuyển sang dạng **không mặt** (mannequin hoặc depth map) mới dùng
> làm ref; (b) **Antigravity (Gemini 3.8 Flash)** phân tích video ref rồi viết prompt Seedance 2.5 khá ổn → rút bài học (mục 7).
>
> **Trạng thái: KẾ HOẠCH — chưa code, 0 USD đã chi.** Mọi bài thử tốn tiền ở đây chờ người dùng duyệt từng bài (luật chi phí
> `docs/CHUAN_XAY_DUNG.md`). Việc nằm ở đợt **S11** của `docs/KE_HOACH_SUA_SAU_DU_AN_8.md`.

## 0. Quyết định đã chốt (người dùng 01/10)

| # | Câu hỏi v1 | Người dùng trả lời | Ảnh hưởng tới plan |
|---|---|---|---|
| Q1 | Có luôn dùng trend? | **Không phải lúc nào cũng dùng** | Mỗi dự án có ô "Dùng trend: Tắt (mặc định) / Gợi ý / Ưu tiên" (mục 2, 3.5) |
| Q2 | Apify: 1 tài khoản Free? | **Đã có sẵn 1 tài khoản Free**, mục đích **thử độ hiệu quả**, chưa dùng thật | Trần 4,5 USD/tháng; sau 4–6 tuần đo theo bảng 3.9 rồi mới quyết mua gói |
| Q3 | Chính sách bản quyền khi dùng trend | **Được dùng trend vào sản phẩm**, chỉ tránh thứ có **mức bản quyền cao** | Thẻ trend có trường `copyright_level` (cao / vừa / thấp); code loại mức cao (mục 3.4) |
| Q4 | Nhạc trend | Hiểu vấn đề nhạc; có nghĩ tới Suno Pro để làm bản mới, nhưng **bán tự động thì để sau** | Không thêm việc Suno; nhạc vẫn Clip AI `music_v2` cùng BPM (mục 4) |
| Q5 | Clip nhảy để thử | **Có sẵn mẫu** — Google Drive `SeaTalk_VDO_20261001_111440.mp4` (mp4, 8 MB) | Bài thử A/B dùng clip này (mục 6.2) |
| Q6 | Hỏi ClipAI mở API Motion Control? | **Chưa hỏi** | Thành việc riêng S11.14 |
| Q7 | Tần suất quét TikTok | **3 ngày** | Lịch mặc định 3 ngày (mục 3.7) |

## 1. Hiện trạng code dùng lại (không làm lại)

| Đã có | Tệp | Dùng cho |
|---|---|---|
| Đọc kịch bản docx/xlsx/csv/txt/văn bản dán | `core/script_reader.py`, `core/script_parser.py` | I, R-A: đầu ra phải đúng khuôn này |
| Director hai lượt (Tầng A ý đồ, Tầng B quay phim từng cảnh, duyệt bằng code) | `core/director_two_pass.py`, `prompts/19`, `20`, `17` | I, R-A, T: chèn khối mới vào Tầng A |
| Cắt shot video ref → khung giữa → tờ 12 khung → Claude gắn nhãn cỡ/góc/chuyển động/vai trò | `core/reference_analysis.py` (`detect_cuts`, `shots_from_cuts`, `mid_frames`, `contact_sheets`, `label`), `prompts/16_reference_shots.md` | R-A, R-B: phần "bóc tách hình" có sẵn ~70 % |
| Đọc thông số video (độ dài, rộng, cao, fps) | `core/video_analysis.py::probe` | R-B: kiểm clip ref |
| Kiểm luật video ref từng nhà cung cấp (Kling 3–15,5 s, 1 video; Seedance 2–30 s, tổng ≤ 30 s; fps 24–60; SAR 1:1; cạnh/điểm ảnh) | `core/adapters/clipai.py::reference_video_problems` (S10.5) | R-B: không gửi video sai luật |
| Đếm mặt bằng YuNet | `core/clip_measure.py::_faces` (`data/models/`) | R-B: **bản không mặt phải còn 0 mặt** |
| MediaPipe đã cài (`requirements.txt`), đang dùng cho mốc môi | `core/clip_measure.py` | R-B: khung xương người nhảy (dựng mannequin) |
| White-model Blender: mỗi người một khối màu, câu vai trò "khối đỏ = KENTA…", video đạt luật ref của cả hai bên | `core/whitebox.py`, `tools/render_plates.py` | R-B: dựng **mannequin** từ khung xương; câu ánh xạ màu → nhân vật dùng chung |
| Ghép theo ảnh độ sâu | `core/composite.py::occluders` | (tham khảo cách đọc ảnh độ sâu) |
| Nghe thoại offline (faster-whisper, tiếng Việt) | `core/voice_check.py::transcribe` | R-A |
| Nghiên cứu định kỳ bằng Claude web search (0,01 USD/lượt), "đề xuất → người duyệt" | `core/research.py`, `tools/monthly_research.py`, tab 🎓 Bài học | T: cùng khuôn |
| Video ref chuyển động: Kling `refer_type=feature`, Seedance `role=reference_video`; chạy thật 30/09 (T1/T2) | `core/adapters/clipai.py`, `knowledge/reference_assets_prompting.md` | R-B |
| Kho chủ thể Seedance — ảnh nhân vật FF qua bộ lọc người thật 3/3 lần không cần dấu đỏ (S4.7, 01/10) | `core/adapters/clipai_subjects.py`, cờ `seedance_subjects` | R-B: ảnh Kelly/Maxim gửi qua kho chủ thể |
| Sổ chi + trần + ước tính trước | `core/cost.py`, `core/budget.py`, `core/project_budget.py` | Mọi lời gọi Apify/Claude mới |
| Tốc độ nói đo thật 2,86 âm tiết/s | `tools/measure_speech_rate.py` | I |
| Sổ kinh nghiệm nhà máy | `core/experience.py` | T: trend nào dùng tốt / hỏng |

Giới hạn đã biết: Motion Control ClipAI **chỉ có trên web** (tra 23/09); Kling video ref 3–15,5 s, giá ×1,5, có video thì `sound` = off;
Seedance 2.5 video ref ≥ 2 s, ≤ 10 video, clip ra 4–30 s, **bám mốc giây** (2.0/Fast thì không — viết "Shot n", S4.8). Giá đang dùng
(`data/pricing.json`): Kling 3.0 Omni 0,08 USD/s (×1,5 = 0,12 khi có video vào), Seedance 2.5 720p 0,23 USD/s + phần video vào ≈ 0,138 USD/s,
Claude Sonnet 5: 2 / 10 USD mỗi 1M token vào/ra, web search 0,01 USD/lượt.

## 2. Tính năng I — 💡 Ý tưởng thô → kịch bản chi tiết

**Vấn đề (bằng chứng):** Bước 1 chỉ nhận kịch bản đã viết (`dashboard/steps/step1.py`: tab "📎 Tải file" / "✍ Gõ / dán"). Ý tưởng 2–3 dòng
đưa thẳng vào thì `split_scenes` ra 1 cảnh không thoại, Director phải bịa toàn bộ trong cùng lời gọi viết Bible + ý đồ, không có chỗ cho người
duyệt phần bịa thêm. Lỗi "truyện cụt / hồi tưởng không dấu hiệu" và "83 s vs ~58 s" của #8 (`docs/TONG_KET_DU_AN_8_2026-09-28.md`) đều sinh
ở khâu kịch bản — chặn sớm ở đây rẻ nhất (chữ, không ảnh).

**Luồng (tab thứ 3 ở Bước 1: "💡 Ý tưởng thô"):**
1. **Nhập:** ô ý tưởng + ô có mặc định: thời lượng (15/30/60 s), khung (9:16), nền tảng, giọng điệu, nhân vật (chọn từ Kho FF, để trống
   được), CTA, **Dùng trend: Tắt (mặc định) / Gợi ý / Ưu tiên** (Q1).
2. **Lượt 1 — Hỏi lại:** Director liệt kê có gì / thiếu gì, hỏi **≤ 5 câu**, mỗi câu có **đáp án mặc định**; câu nào lấy mặc định được ghi
   lại (luật 1 "không im lặng khi thiếu đầu vào").
3. **Lượt 2 — 3 hướng:** 3 logline + hook 3 s đầu. Khi ô trend = Gợi ý/Ưu tiên, 1 hướng dùng thẻ trend đã duyệt (mục 3); khi Tắt, không
   đưa thẻ nào vào prompt.
4. **Lượt 3 — Dàn ý theo giây:** hook → dựng → điểm xoay → cao trào → kết/CTA; tổng khớp thời lượng ± 10 %; thoại tính 2,86 âm tiết/s → code
   báo nhịp nào thoại dài hơn khung.
5. **Lượt 4 — Kịch bản đầy đủ** đúng khuôn `CẢNH n - <thời gian>, <nơi>` / mô tả / `NHÂN VẬT: lời`; code chạy lại `script_parser`, không
   tách được → báo lỗi, không cho đi tiếp.
6. **Duyệt 2 cột:** trái ý tưởng gốc, phải kịch bản; **tô màu phần Director thêm** (nhân vật / nơi / câu thoại mới). Sửa tay được; "Dùng kịch
   bản này" → vào Bước 1 như kịch bản tải lên (mọi cổng Bible / storyboard / ngân sách giữ nguyên).

**Kiểm bằng code (0 USD):** nhân vật có trong Kho FF (không có → cờ "nhân vật mới — cần ảnh"); nơi ưu tiên có trong Kho (không có → cờ "AI vẽ,
~70 % giống"); tổng giây, giây thoại từng nhịp, có hook 3 s đầu, có kết, CTA đúng; không ghi số tuổi < 18.

**Kiến thức:** `prompts/23_idea_to_script.md` + `knowledge/roles/screenwriter.md` (vai **Biên kịch**, cạnh Đạo diễn/Quay phim/Dựng): cấu
trúc video ngắn (hook – giữ chân – trả thưởng), công thức tiểu phẩm Kelly Show, `knowledge/dialogue_craft.md`, `knowledge/genre_guides.md`.

**Chi phí:** 4 lời gọi Sonnet 5 ≈ 25k token vào (cache phần luật) × 2 USD/1M + 6k ra × 10 USD/1M ≈ **0,1 USD/kịch bản**; trần cứng 0,3 USD/lần,
stage `screenwriter`. **Bộ đo:** 5 ý tưởng thô → người dùng chấm 1–5 (giữ ý, hook, logic, độ dài, quay được) — cổng bật: TB ≥ 4, 0 lỗi kiểm
code; ≈ 0,75 USD.

## 3. Tính năng T — 📈 Học trending (TikTok chính, Facebook phụ)

### 3.1 Bằng chứng nhu cầu và rủi ro
- "Ông chã húi, bà chả hơm": biến âm của "ông xã / bà xã"; khởi phát từ video "Bà chả húi, ăm chả húi ơi" của TikToker Kiệt Hà Tịnh (> 10 triệu
  theo dõi) **đầu tháng 6/2026**, > 3 triệu lượt xem; sau đó bài hát "Ăm chã húi" (Lâm Thằn Lằn) viral [S9][S10].
- **Cùng trend đó bị báo gọi là "thảm họa mới của nhạc Việt"** và "hứng trọn gạch đá vì ca từ nhảm nhí" (Kenh14 / Việt Giải Trí 20/09/2026;
  Docnhanh) [S11][S12] → trend **không tự động an toàn**: cụm từ dùng được (đùa cặp đôi Kelly – Kenta), bài hát thì rủi ro → cần cờ rủi ro + người duyệt.
- Tuổi thọ: nổi tháng 6 → bị chê tháng 9 ≈ **3–4 tháng** → thẻ cần vòng đời + hạn dùng.

### 3.2 Công cụ — đã so sánh

| Nguồn | Lấy được gì | Hợp lệ? | Tiền | Kết luận |
|---|---|---|---|---|
| TikTok Research API (chính thức) | video, bình luận, người dùng | **Không** — chỉ học thuật/phi lợi nhuận; nhà quảng cáo, đơn vị thương mại không đủ điều kiện; 1000 lượt/ngày [S6][S7] | Free | ❌ Loại |
| TikTok Creative Center (web công khai) | hashtag, bài hát, nhà sáng tạo, video top; lọc **quốc gia** + 7/30/120 ngày; xem không cần đăng nhập [S8] | Có | Free | ✅ Nguồn chính (đọc qua Apify) |
| Apify actor đọc Creative Center (`clockworks/tiktok-trends-scraper`, `crawloop/tiktok-trending-hashtags-scraper`, `automation-lab/tiktok-creative-center-scraper`) | hạng, lượt xem, số bài, đường cong phổ biến, nhà sáng tạo dẫn đầu; quốc gia, cửa sổ 7/30/90 ngày; **không cần tài khoản TikTok** [S3][S13] | Có (dữ liệu công khai) | **0,99–1,70 USD/1000 dòng**; bản hashtag+sound+creator 8,20 USD/1000 [S3][S13] | ✅ |
| Apify `clockworks/tiktok-scraper` | video theo hashtag / từ khóa: caption, hashtag, nhạc, lượt xem/thích/chia sẻ, ngày | Có | ~1,70 USD/1000 (gói trả phí) [S5]; **gói Free ≈ 0,003 USD/kết quả** [S14] | ✅ ví dụ thật cho mỗi trend |
| Apify Facebook Posts Scraper | bài đăng trang công khai | Có | 0,65–2,00 USD/1000 bài [S15] | ✅ phụ — 5–10 trang meme/game VN + fanpage FF |
| Claude web search (`core/research.py`) | báo/blog viết về trend: **nghĩa, nguồn gốc, phản ứng dư luận** | Có | 0,01 USD/lượt + token | ✅ chính cách tìm ra bằng chứng ở 3.1 |
| kworb.net TikTok VN [S8b] | bảng bài hát trend VN | Trang công khai | Free | ✅ kiểm chéo bài hát |
| Nhập tay | cụm từ / link người dùng thấy trên điện thoại | Có | Free | ✅ |

**Vì sao cần cả Apify lẫn web search:** web search chỉ thấy trend **khi báo đã viết** (trễ 1–3 tuần — ví dụ trên: video đầu tháng 6, báo cuối
tháng 6); Creative Center cho số liệu 7 ngày, bắt trend đang lên; scraper video cho ví dụ thật (caption, nhạc) để Director thấy cách người ta dùng.

**Tài khoản:** dùng **đúng 1 tài khoản Apify Free người dùng đã có** (Q2). Điều khoản Apify cấm một người tạo/dùng nhiều tài khoản cá nhân,
kể cả bằng email khác [S4] — không lập thêm.

### 3.3 Kiến trúc

```
Lịch (Windows Task Scheduler, mặc định mỗi 3 ngày — chỉnh 1–3 ngày trong ⚙)   ← giống tools/monthly_research.py
   └─ tools/trend_scan.py
        1. GOM (core/trends/sources/*.py — mỗi nguồn 1 adapter, đều qua sổ chi + trần tháng)
           ├─ apify_creative_center: hashtag top 50 + bài hát top 50, VN, 7 ngày        (tuần 1 lần)
           ├─ apify_tiktok_videos:  8 hashtag/cụm đang lên × 10 video                  (mỗi 3 ngày)
           ├─ apify_facebook:       5 trang × 10 bài                                     (tuần 1 lần)
           ├─ claude_web_search:    "trend TikTok Việt Nam tuần này", "<cụm từ> là gì"  (≤ 5 lượt)
           └─ nhập tay
           → bảng trend_raw (nguồn, loại, nội dung, số liệu, url, lúc lấy) — chỉ chữ + số + URL, KHÔNG lưu video người khác
        2. LỌC BẰNG CODE (0 USD): bỏ trùng; tốc độ tăng giữa 2 lần quét; bỏ hashtag quảng cáo thương hiệu khác; danh sách đen
           (chính trị, tôn giáo, tai nạn, bạo lực thật, 18+); giữ ~20 ứng viên
        3. CHẮT LỌC (1 lời gọi Claude ≈ 0,09 USD): mỗi ứng viên → THẺ TREND đề xuất (3.4)
   └─ Dashboard ⚙ → "📈 Trend": duyệt / sửa / loại thẻ (giống tab 🎓 Bài học)
   └─ Director (Tầng A + Biên kịch + Cover) đọc ≤ 8 thẻ ĐÃ DUYỆT, còn hạn, hợp thể loại — CHỈ khi ô "Dùng trend" ≠ Tắt
```

### 3.4 Thẻ trend (bảng `trend_cards`)

| Trường | Ví dụ ("ông chã húi") |
|---|---|
| `kind` | cụm_từ / âm_thanh / định_dạng / hashtag / meme_hình / điệu_nhảy |
| `title`, `meaning_vi`, `origin` | cách gọi đùa ông xã / bà xã; gốc video Kiệt Hà Tịnh 06/2026 |
| `how_used` | 3 ví dụ caption/thoại thật (từ scraper) |
| `fit_ff` (0–1) + gợi ý | 0,8 — Kelly gọi Kenta "ông chã húi" khi cãi yêu; hợp tiểu phẩm cặp đôi, không hợp trailer hành động |
| `tone` | hài, dễ thương, Gen Z |
| **`copyright_level`** (Q3) | phần cụm từ: **thấp**; bài hát "Ăm chã húi": **cao** → tách thành 2 thẻ |
| `risk_flags` | `song_criticized`, `overused` |
| `lifecycle`, `expires_at` | đang_lên / đỉnh / đang_xuống / hết_hạn; mặc định +21 ngày, tự gia hạn nếu lần quét sau còn tăng |
| `evidence` | URL + số liệu tại lúc quét |
| `status` | đề_xuất → đã_duyệt / loại (người, kèm lý do) |

**Mức bản quyền** (xếp từ cao xuống thấp — Claude đề xuất, người duyệt chốt):

| Mức | Gồm | Xử lý |
|---|---|---|
| **Cao** | bài hát của hãng đĩa / ca sĩ; đoạn phim, show, MV có bản quyền; nhân vật / thương hiệu IP khác | **Code loại khỏi prompt Director** (vẫn lưu thẻ để biết) |
| **Vừa** | điệu nhảy do creator biên đạo; âm thanh gốc do người dùng TikTok tự tạo | Dùng được; Director phải ghi lý do trong `trend_refs`; người dùng thấy huy hiệu ⚠ ở cảnh đó |
| **Thấp** | cụm từ, câu nói, meme chữ, khuôn định dạng ("POV…", "trước/sau"), hashtag | Dùng tự do |

### 3.5 Director "học" thế nào (không fine-tune — đúng quyết định PLAN Mục 5)
1. Khối **"Xu hướng dùng được"** vào prompt Tầng A (`prompts/19`), Biên kịch (I), Cover (R-A): ≤ 8 thẻ đã duyệt, còn hạn, `copyright_level ≠
   cao`, lọc theo thể loại + giọng điệu bằng code. **Chỉ chèn khi ô "Dùng trend" của dự án là Gợi ý hoặc Ưu tiên** (Q1); Gợi ý = được phép
   không dùng; Ưu tiên = cố đặt 1 trend nếu hợp, không hợp thì nói lý do.
2. **Luật dùng** (`knowledge/trend_usage.md`, mỗi luật có lý do): ≤ 2 trend / 60 s; đặt ở hook hoặc câu chốt; hợp tính cách nhân vật (hồ sơ chuẩn);
   `đang_xuống` → chỉ kiểu nhại/tự giễu; `hết_hạn` không đưa vào prompt; có `risk_flags` → chỉ dùng phần an toàn.
3. Đầu ra Director thêm `trend_refs: [{card_id, where, why}]` → code kiểm thẻ còn hạn + đã duyệt + không phải mức cao; huy hiệu "📈 trend X" ở cảnh.
4. **Vòng phản hồi:** bảng `trend_usage` (dự án, thẻ, chỗ dùng); số liệu đăng bài (nhập tay ở tab 📊, sau này kéo bằng chính scraper theo tài
   khoản kênh) → `core/experience.py` ghi "trend X ở hook → giữ chân tốt / kém".

### 3.6 Lịch và chi phí — vừa gói Free 5 USD/tháng

Giá tính: Creative Center 1,70 USD/1000 dòng [S3]; video TikTok **0,003 USD/kết quả gói Free** (lấy mức cao cho an toàn) [S14]; Facebook 2 USD/1000
[S15]. **Chưa kiểm trên console** (máy dựng plan bị chặn apify.com) → lần chạy đầu đo số thật, ghi vào `data/pricing.json` rồi mới bật lịch.

| Việc | Tần suất | Dòng/lần | USD/lần | Lần/tháng | USD/tháng |
|---|---|---|---|---|---|
| Creative Center VN: hashtag 50 + bài hát 50 (7 ngày) | tuần 1 lần (cửa sổ 7 ngày, quét dày không thêm tin) | 100 | 0,17 | 4,3 | 0,73 |
| Video TikTok: 8 hashtag × 10 video | **mỗi 3 ngày** (Q7) | 80 | 0,24 | 10 | 2,40 |
| Facebook 5 trang × 10 bài | tuần 1 lần | 50 | 0,10 | 4,3 | 0,43 |
| **Tổng Apify** | | | | | **≈ 3,6** (< 5 Free; chừa ~1,4 cho phí nền tảng / chạy lại) |
| Claude chắt lọc (~25k vào + 4k ra) | mỗi lần quét video | | 0,09 | 10 | 0,9 |
| Claude web search (≤ 5 lượt) | mỗi lần quét | | 0,05 | 10 | 0,5 |
| **Tổng Claude** | | | | | **≈ 1,4** |

Khóa cứng: trần Apify tháng **4,5 USD** (stage `trend_apify`), mỗi lần ≤ 0,5 USD; hết trần → lịch tự dừng + báo trên dashboard. Đặt thêm giới
hạn chi trên console Apify làm lớp thứ hai. Dữ liệu: chỉ công khai, chỉ chữ + số + URL.

### 3.7 Đo hiệu quả để quyết mua gói (Q2 — mục đích là THỬ)
Sau 4–6 tuần, nâng **Apify Starter** (29 USD theo đa số nguồn, có nguồn báo 19 USD — kiểm console [S1][S2]) khi **cả 3** đúng: (a) ≥ 5 thẻ được
duyệt/tuần trong 3 tuần liên tiếp; (b) ≥ 40 % kịch bản **có bật trend** giữ lại `trend_refs` (người dùng không gỡ); (c) Free hết trần ≥ 2 tháng
hoặc cần quét hằng ngày. Không đạt (a)/(b) → giữ Free hoặc chỉ dùng nguồn miễn phí. Báo cáo tuần tự sinh trên tab 📈.

## 4. Nhạc (Q4)
- Nhạc trend **không** chèn vào bản giao: tài khoản doanh nghiệp TikTok chỉ dùng Commercial Music Library; phần lớn nhạc trend không có trong đó
  [S16][S17]. Thẻ trend nhạc mức **cao** bị loại khỏi Director (3.4).
- Trước mắt nhạc giữ cách hiện tại: Clip AI `music_v2`, **cùng BPM** với video (bản nhảy khớp phách nên vẫn khớp).
- **Suno Pro — tạm gác** (người dùng: bán tự động thì chưa cần). Ghi chú để làm sau: theo điều khoản 03/09/2026, bài tải về trong lúc còn gói
  Pro/Premier được dùng thương mại, nhưng quyền thương mại ≠ bảo hộ bản quyền [S19]; Suno không có API chính thức; không upload bài có bản quyền
  lên Suno để "cover" vì giai điệu vẫn thuộc chủ cũ.

## 5. Tính năng R-A — 🎬 Cover kịch bản từ video ref

1. **Nhập video:** tải tệp lên (khuyến nghị) hoặc link (chỉ tải khi người dùng tick "có quyền dùng để tham khảo"); lưu ở thư mục dữ liệu dự án,
   **không commit**.
2. **Bóc tách hình + tiếng (0 USD):** `probe` → `detect_cuts` → `mid_frames` → `contact_sheets`; thoại `voice_check.transcribe`; nhịp nhạc bằng DSP.
3. **Claude bóc cấu trúc** (`prompts/24_reference_breakdown.md`, 1 lời gọi có ảnh ≈ 0,06 USD cho 60 s ≈ 3 tờ khung) — khuôn đầu ra học từ
   Antigravity (mục 7):
   - `duration`, `aspect`; `segments[]`: `{start, end, size, angle, move, what}` theo **mốc giây**;
   - `cast[]`: `{role, gender_look, entrance_at, entrance_from, blocking, performance}` (vai trò, **không** nhận dạng người thật);
   - `beats[]`: hook, điểm xoay, **điểm chạm cảm xúc**, cú chốt (mốc giây); chữ trên màn hình; chỗ nhạc đổi.
4. **Ghép FF (người duyệt):** vai → nhân vật FF theo hồ sơ; nơi → nơi trong Kho (ưu tiên có 3D/ảnh in-game); đạo cụ → vật phẩm FF.
5. **Viết lại (≈ 0,05 USD):** kịch bản đúng khuôn Bước 1, **giữ cấu trúc + nhịp + cú chốt, viết lại lời** (câu trùng > 70 % so với bản nghe được →
   cờ); kèm `ref_shots` để Tầng B Quay phim bám. Shot cần chép **đường máy** → cắt đoạn ref làm Kling `feature` ("follow the camera movement of @video").
6. **Pipeline thường** + xem song song ref ↔ animatic (`core/animatic.py`) trước khi chi tiền video.

**Chi phí** ≈ 0,1–0,2 USD Claude/video ref. **Bộ đo:** 3 video ref; người dùng chấm "giống tinh thần ref" + "ra chất FF" 1–5; TB ≥ 4 mới bật cờ
`ref_cover`.

## 6. Tính năng R-B — 💃 Cover nhảy

### 6.1 Chuyển video ref sang dạng KHÔNG MẶT (bước bắt buộc, mới)
**Vì sao:** người dùng gửi video nhảy có mặt người → Seedance báo lỗi. Khớp với lỗi đã gặp: Seedance từ chối ảnh "may contain real person"
(`InputImageSensitiveContentDetected.PrivacyInformation`, `docs/CHAY_THU_2026-09-27_NHAT_KY.md` phát hiện 9; S4.6). Người dùng đã thử 2 dạng không
mặt dùng được làm ref: **mannequin** (người gỗ đỏ / xám trên phông xanh) và **depth map** (bản đồ độ sâu đen trắng).

| Dạng | Cách làm | Ưu | Nhược | Tiền |
|---|---|---|---|---|
| **(a) Depth map — After Effects** (người dùng đã làm được) | effect **Instant Depth Map** trên AE. Tự động hóa: bản mẫu `.aep` có effect sẵn + script **ExtendScript ES3** (`tools/ae/depth_ref.jsx`: nhập clip, comp đúng luật ref — cạnh ≥ 704 px, 24–60 fps, SAR 1:1, trong `app.beginUndoGroup`/`endUndoGroup`, kiểm có comp/layer) + render dòng lệnh `aerender` gọi từ dashboard | Đã chứng minh trên máy người dùng; giữ khối người + chiều sâu, nhiều người cũng được | Cần máy có AE; **việc đầu tiên: đọc `matchName` của Instant Depth Map bằng script chỉ đọc** (tên hiển thị có thể khác `matchName`) rồi mới viết script áp effect | 0 |
| **(a') Depth map — local tự động** | **Video Depth Anything Small** (28,4M tham số). **Chỉ bản Small giấy phép Apache-2.0**; Base/Large là CC-BY-NC-4.0 → không dùng thương mại [S20] | Chạy không cần AE; nhất quán theo thời gian | Thêm phụ thuộc + tải model; chậm trên CPU | 0 |
| **(b) Mannequin** (công cụ người dùng đã dùng: không rõ) | MediaPipe Pose (đã cài) lấy 33 điểm khung xương / khung hình → Blender dựng người gỗ trên phông xanh, **mỗi người một màu** (mở rộng `core/whitebox.py`, dùng bảng màu `COLORS` của nó); bản đầu ≤ 2 người, theo dõi người bằng vị trí gần nhất | Màu = định danh nhân vật (đỏ → Kelly, xám → Maxim) — đúng kiểu ref người dùng đưa và đúng câu vai trò white-model đã chạy thật S10.6 | Tay/ngón kém chính xác; người che nhau dễ nhảy khung xương | 0 |
| (c) Dự phòng: khung xương vẽ thẳng từ MediaPipe | nét xương trên nền đen | rẻ nhất | Seedance chưa chắc hiểu | 0 |

**Kiểm trước khi gửi (code, 0 USD):** YuNet đếm mặt trên mẫu khung → **còn mặt thì không gửi** (báo khung nào); `reference_video_problems`
theo nhà cung cấp; độ dài làm tròn lên số giây nguyên.

### 6.2 Clip mẫu và bài thử A/B
**Clip mẫu (Q5):** Google Drive `SeaTalk_VDO_20261001_111440.mp4` (id `1FcuhjmDvKexgH96wqj-s1p_ax1LcAVVp`, mp4, 8 028 435 byte, tạo 01/10).
Đã đọc được metadata qua Drive; **chưa tải được nội dung** từ máy dựng plan (kết nối Drive hết phiên, tải trực tiếp bị proxy chặn) → đo trên
máy người dùng (0 USD) ở S11.9 và ghi "hồ sơ clip thử" vào đây:
```
py -c "from core.video_analysis import probe; print(probe(r'D:\…\SeaTalk_VDO_20261001_111440.mp4'))"
```
cộng đếm mặt YuNet trên 10 khung mẫu và `reference_video_problems('omni'|'seedance', …)` → biết clip đạt hay phải cắt / đổi tỉ lệ / đổi fps.

**Bài thử (≈ 2,5–3 USD, chờ duyệt):** cùng 1 đoạn 5 s của clip mẫu, Kelly in-game qua Kho chủ thể, cùng 1 khung đầu Deepix (≈ 0,05):

| Ô | Đầu vào ref | Model | Ước tính |
|---|---|---|---|
| 1 | gốc có mặt (đối chứng) | Seedance 2.5 | 0 USD nếu bị từ chối lúc tạo (như các lần trước) |
| 2 | depth (AE Instant Depth Map) | Seedance 2.5 720p | 5 × 0,37 ≈ 1,85 |
| 3 | mannequin (MediaPipe + Blender) | Seedance 2.5 720p | (chỉ chạy nếu ô 2 hỏng hoặc người dùng muốn so) ≈ 1,85 |
| 4 | dạng thắng ô 2/3 | Kling Omni `feature` ("Animate the character in @Image 1 with the same motion as the character in @Video") | 5 × 0,12 = 0,60 |
| 5 | (người dùng tự chạy) | Motion Control trên web ClipAI | ghi giá web |

Chấm: đúng động tác (người dùng 1–5); mặt/trang phục giữ (Tổ QC tầng 0); lệch nhịp (code: đỉnh năng lượng chuyển động so với phách); có bị chặn không;
nền xanh/xám của ref có lọt vào clip không.

### 6.3 Luồng đầy đủ (sau khi có cách thắng)
1. Nhập clip → kiểm 6.1 → chuyển dạng không mặt.
2. Đo BPM + phách mạnh (DSP) → **cắt đoạn tại phách** (Kling ≤ 15,5 s; Seedance 2.5 ≤ 30 s/clip).
3. Khung đầu: Deepix vẽ nhân vật FF **đúng tư thế khung đầu ref** trên nền FF (render 3D / ảnh in-game); cổng duyệt khung đầu.
4. Chuyển động từng đoạn; đoạn n+1 dùng **khung cuối thật** của đoạn n làm khung đầu.
5. QC nhảy: lệch nhịp, số người, mặt đúng nhân vật, tay chân biến dạng (Claude QC video chỉ khi tầng code nghi).
6. Nhạc theo mục 4.

**Chi phí 1 bài 30 s:** Kling 30 × 0,12 = **3,6 USD**; Seedance 2.5 30 × 0,37 ≈ **11 USD**; + khung đầu ≈ 0,05/đoạn.

### 6.4 Việc với ClipAI (Q6 — phần ref không mặt ĐÃ CÓ câu trả lời 01/10)
**01/10 tối:** Seedance 2.5 nhận ref depth map / mannequin cả trên web (người dùng) lẫn qua API (thử thật dự án #20, 1,38 USD — ánh xạ màu → nhân vật đúng, động tác đúng, khung máy chưa theo ref; chi tiết `knowledge/reference_assets_prompting.md` mục Kết quả thử thật). Người dùng: "dùng được là ok, lỗi fix sau". Còn hỏi ClipAI: API Motion Control.

Gửi team ClipAI: "Có mở API cho **Kling Motion Control** (ảnh nhân vật + video nhảy 3–30 s → nhân vật nhảy theo) không? Có nhận video ref dạng
depth / mannequin không?" — gộp với câu hỏi Bàn đạo diễn đang chờ. Có API thì thêm ô thứ 6 vào bài thử.

## 7. Học từ Antigravity (ảnh chụp người dùng gửi 01/10)

Tình huống: người dùng đưa `Video ref3.mp4` (mannequin đỏ + xám trên phông xanh, 14,08 s), nhờ viết prompt Seedance 2.5 thay **đỏ → Kelly**,
**xám → Maxim**, clip 15 s. Antigravity (Gemini 3.8 Flash High) trả về: (1) phân tích điện ảnh, (2) bảng gán tài sản, (3) prompt hoàn chỉnh.

| Antigravity làm tốt | Áp vào đâu ở dự án |
|---|---|
| **Phân đoạn máy theo mốc giây**: 00:00–00:09 toàn cảnh trực diện ngang mắt, máy tĩnh; 00:09–00:14 đẩy máy mượt vào trung cận hai người | `segments[]` trong `prompts/24` (5.3); prompt Seedance 2.5 viết theo mốc giây (2.5 bám mốc giây — `docs/CAP_NHAT_CLIPAI_2026-09-28.md`); 2.0/Fast viết "Shot n" (S4.8) |
| **Mỗi nhân vật có thời điểm + hướng xuất hiện** (nam vào từ sau bên trái ở 00:02) | `cast[].entrance_at`, `entrance_from` |
| **Điểm chạm cảm xúc** (00:09–00:14: nữ quay sang chống hông, nam nghiêng đầu mỉm cười) | `beats[]` loại `emotional_touch`; đúng chỗ đặt cận / đẩy máy |
| **Màu mannequin = định danh nhân vật** | Trùng `core/whitebox.py` ("khối đỏ = KENTA") → một hàm sinh câu ánh xạ dùng chung cho white-model và mannequin |
| **Độ dài clip làm tròn lên theo ref** (14,08 s → 15 s) | Code tính `ceil(duration)` trong giới hạn 4–30 s của Seedance 2.5 |
| **Bảng gán tài sản**: @Image1 Kelly, @Image2 Maxim, @Image3 bối cảnh, @Video1 chuyển động — mỗi tài sản đúng một việc | Đúng luật `knowledge/reference_assets_prompting.md` (mẫu chính thức sd25-pe) — giữ |

| Chỗ cần làm khác Antigravity | Vì sao (căn cứ) |
|---|---|
| Bối cảnh "Japan scene" anime (đường hoa anh đào, cổng Torii) | Dự án dùng nơi trong **Kho FF** (render 3D / ảnh in-game) — quyết định gói bối cảnh V4 |
| Tả "nụ cười anime" cho Kelly in-game | Chỉ 2 look đã chốt (anime **hoặc** giống in-game) — không trộn trong một prompt (PLAN Mục 5, 2026-09-24) |
| Không thấy câu "không lấy danh tính, trang phục, bối cảnh từ @Video1" | Luật chính thức Seedance 2.5: phải nói **không lấy** gì từ video (`NGHIEN_CUU_PROMPT_THAM_CHIEU` 1.2-3); thiếu → nền xanh / da mannequin có thể lọt vào clip |
| Tả lại vũ đạo khá chi tiết trong prompt dù đã có video | Seedance: video đã có động tác thì **không tả lại từng động tác** (1.2-4) — chỉ nói thừa hưởng chiều nào (động tác, nhịp, đường máy) |
| Nhắc "giai điệu J-Pop" của ref | Không chép nhạc (mục 4) |
| Ảnh Kelly/Maxim gửi thẳng | Gửi qua **Kho chủ thể** (S4.7: 3/3 lần qua bộ lọc người thật) |

**Prompt đầy đủ của Antigravity (ảnh chụp thứ 2 người dùng gửi 01/10) — khuôn 5 khối:**
`VIDEO` (tỉ lệ 16:9, 15 s, phong cách hình) → `REFERENCE ASSETS` (@Image1 Kelly thay mannequin đỏ, @Image2 Maxim thay mannequin trắng xám,
@Image3 bố cục cảnh, @Video1 "vũ đạo, đường đi, tương tác, đẩy máy") → `CHARACTERS & BLOCKING` ("Only two characters… Zero extra background
people") → `CAMERA & PERFORMANCE PRINCIPLE` (một cảnh liền 15 s: 9 s toàn thân trực diện → đẩy máy liền vào trung cận hai người 6 s cuối) →
`TIMELINE` 4 đoạn `[0-4s] [4-8s] [8-11s] [11-15s]`, **mỗi đoạn đủ 4 dòng `Camera / Action & Performance / Dialogue / Sound`**.

| Thêm điểm nên học | Áp vào |
|---|---|
| Khuôn 5 khối + mỗi đoạn mốc giây có đủ Camera / Action / Dialogue / Sound (kể cả "Dialogue: None") | Khuôn đầu ra của prompt video cho shot từ video ref (người viết prompt Bước 3, nhánh Seedance 2.5); code kiểm đủ 4 dòng mỗi đoạn |
| Câu chặn người thừa "Only two characters… Zero extra background people" | Câu cố định khi có `cast` đếm được (đã gặp lỗi thừa người ở storyboard, S4.6) |
| Một nguyên tắc máy cho cả clip trước khi chia đoạn | Trường `camera_principle` trong bóc tách |

| Thêm chỗ cần sửa | Căn cứ |
|---|---|
| Mốc đẩy máy lệch giữa phân tích (00:09) và timeline (bắt đầu 8 s, rõ ở 11 s) | Code lấy mốc từ `segments[]` đo được, không để model tự chia đều 4 đoạn |
| Phong cách gọi tên "Makoto Shinkai" + cel-shaded | Dùng mô tả look anime đã chốt của dự án, không gọi tên tác giả thật |
| Dòng `Sound` bịa nhạc (J-pop, synth, vocal hook) | Nhạc do bước âm thanh lo; prompt video ghi "no music" hoặc chỉ âm thực tế |
| @Video1 vẫn chỉ nói lấy gì, không nói **không lấy** gì (da mannequin, phông xanh) | Luật sd25-pe (1.2-3) — thêm câu bắt buộc |

**Cách học:** dựng lại phân tích của Antigravity thành **1 ví dụ mẫu** (few-shot, đã sửa 6 chỗ trên) trong `prompts/24`. **Đo:** cùng `Video ref3.mp4`
(người dùng gửi file) → prompt của dự án vs prompt Antigravity, chạy Seedance 2.5 cả hai (≈ 2 × 15 × 0,37 ≈ 11 USD — chỉ khi người dùng duyệt;
bản rẻ: 5 s đầu mỗi bên ≈ 3,7 USD) → người dùng chấm.

## 8. Ma trận kế thừa (luật 2 — `docs/CHUAN_XAY_DUNG.md`)

| Biện pháp | Ý tưởng → kịch bản | Cover kịch bản | Cover nhảy | Test |
|---|---|---|---|---|
| Ảnh tham chiếu đúng người / đúng look | kế thừa (qua Bước 1) | kế thừa | khung đầu riêng → cùng hàm chọn ảnh; ảnh qua Kho chủ thể | test chọn ảnh luồng nhảy |
| Cổng Bible / storyboard / không tự duyệt dưới sàn | kế thừa | kế thừa | cổng khung đầu + cổng đoạn đầu | test cổng |
| Luật chọn model | kế thừa | + Kling `feature` cho đường máy | cố định theo kết quả A/B | test router |
| Gen lại phải đổi đầu vào, ≤ 2 lần | — | kế thừa | từng đoạn | test |
| Sổ chi + trần + ước tính trước | stage `screenwriter` | stage `reference_breakdown` | ước tính cả bài trước đoạn 1 | test ước tính |
| Giữ phần người sửa tay | kịch bản sửa tay | bảng ghép vai | khung đầu đã duyệt | test |
| Không im lặng khi thiếu đầu vào | câu mặc định được ghi | không cắt được shot / không nghe được thoại → báo | video sai luật → báo | test |
| **Video ref không mặt (YuNet = 0 mặt)** | — | đoạn ref làm Kling `feature` cũng kiểm | bắt buộc | test chặn gửi khi còn mặt |
| **Thẻ trend: đã duyệt + còn hạn + không mức cao + ô dự án ≠ Tắt** | có | có | — | test lọc thẻ |

## 9. Lộ trình S11 (thứ tự đã chốt Q1: rẻ trước, dùng lại nhiều trước)

| Việc | Nội dung | Tiền | Công (ngày) | Phụ thuộc |
|---|---|---|---|---|
| S11.0 | Chốt Q1–Q7 | 0 | — | ✅ 01/10 |
| S11.1 | I: prompt 23 + vai Biên kịch + 4 lượt + ô "Dùng trend" + kiểm code + màn 2 cột | 0 | 2–3 | — |
| S11.2 | I: bộ đo 5 ý tưởng | ≈ 0,75 | 0,5 | S11.1 |
| S11.3 | T1: `trend_raw` / `trend_cards` (có `copyright_level`), nguồn miễn phí, tab ⚙ 📈 Trend | ≈ 0,15/lần | 2 | — |
| S11.4 | T2: adapter Apify (`apify-client`, `APIFY_TOKEN` trong `dashboard.env`, tài khoản Free có sẵn), sổ chi + trần 4,5 USD/tháng, lịch 3 ngày | lần đo đầu ≈ 0,5 | 1,5 | — |
| S11.5 | T3: khối "Xu hướng" (chỉ khi ô ≠ Tắt) + `knowledge/trend_usage.md` + `trend_refs` + huy hiệu | 0 | 1 | S11.3 |
| S11.6 | T4: vòng phản hồi + báo cáo tuần chỉ số 3.7 | 0 | 1 | S11.5 |
| S11.7 | R-A: prompt 24 (khuôn học từ Antigravity + few-shot đã sửa) + ghép vai/nơi + viết lại + `ref_shots` + xem song song | ≈ 0,2/video | 3 | S11.1 |
| S11.8 | R-A: bộ đo 3 video ref | ≈ 0,6 | 0,5 | S11.7 |
| S11.9 | R-B: đo clip mẫu (probe + YuNet + luật ref) + chuyển không mặt local: Video Depth Anything Small, mannequin MediaPipe + Blender, kiểm 0 mặt | 0 | 2 | — |
| S11.10 | R-B: script AE Instant Depth Map (đọc `matchName` trước) + `aerender` từ dashboard | 0 | 1 | máy có AE |
| S11.11 | R-B: bài thử A/B 6.2 | ≈ 2,5–3 | 0,5 | S11.9, S11.10 |
| S11.12 | R-B: luồng đầy đủ + QC nhảy + nhạc cùng BPM | 1 bài 30 s ≈ 3,6–11 | 3 | S11.11 |
| S11.13 | Đánh giá sau 4–6 tuần: nâng Apify hay không | 0 | — | S11.4 + 4 tuần |
| S11.14 | Hỏi ClipAI mở API Motion Control (ref depth/mannequin: ĐÃ xác nhận qua API 01/10) | 0 | — | — |

Tổng tiền thử trước khi dùng thật ≈ **5–6 USD** (I 0,75 + T ≈ 0,65 + R-A 0,6 + R-B 2,5–3); so prompt với Antigravity (7) tính riêng nếu duyệt.
Cờ mới đều **TẮT** tới khi qua bộ đo: `idea_to_script`, `trend_feed`, `trend_apify`, `ref_cover`, `dance_cover`.

## 10. Còn mở
| # | Việc | Ai |
|---|---|---|
| M1 | Gửi file `Video ref3.mp4` để đo ở mục 7 (prompt đầy đủ đã nhận 01/10 — ảnh chụp thứ 2; dòng cuối "Dialogue" của đoạn 11–15 s bị che) | Người dùng |
| M2 | Hỏi ClipAI (S11.14) | Người dùng |
| M3 | Công cụ đã tạo bản mannequin (để so với bản MediaPipe + Blender) | Người dùng nếu nhớ ra |

## 11. Nguồn

Ghi chú độ tin: máy dựng plan **bị chặn** apify.com, docs.apify.com, kling.ai, clipai, tuoitre → số liệu Apify / Kling lấy từ **đoạn trích kết quả
tìm kiếm** của chính trang đó hoặc trang thứ ba; kiểm lại trên console ở lần chạy đầu (S11.4).

- [S1] Apify pricing — https://apify.com/pricing ; https://scrapegraphai.com/blog/apify-pricing ; https://use-apify.com/docs/what-is-apify/apify-pricing
- [S2] Starter 29 → 19 USD (nguồn thứ ba, cần kiểm) — https://scrapewise.ai/blogs/apify-pricing-compute-units-cost-2026
- [S3] https://apify.com/clockworks/tiktok-trends-scraper · https://apify.com/crawloop/tiktok-trending-hashtags-scraper · https://apify.com/automation-lab/tiktok-creative-center-scraper · https://apify.com/automation-lab/tiktok-trends-scraper
- [S4] Apify General Terms (cấm nhiều tài khoản cá nhân) — https://docs.apify.com/legal/general-terms-and-conditions ; https://docs.apify.com/legal/acceptable-use-policy
- [S5] https://apify.com/clockworks/tiktok-scraper
- [S6] TikTok Research API — https://tokconnect.com/guides/tiktok-research-api/ ; https://www.keyapi.ai/blog/tiktok-research-api-commercial-trend-scanning/
- [S7] https://www.xpoz.ai/blog/guides/tiktok-research-api-limits-access-and-alternatives/
- [S8] TikTok Creative Center — https://bir.ch/blog/tiktok-creative-center ; [S8b] https://kworb.net/charts/tiktok/vn.html
- [S9] https://cuoi.tuoitre.vn/ong-cha-hui-ba-cha-hom-la-gi-ma-nghe-mac-cuoi-vay-may-ni-100260629085401026.htm
- [S10] https://ai-hay.vn/ong-cha-hui-la-gi-pN1UmIco4tC
- [S11] https://kenh14.vn/tham-hoa-moi-cua-nhac-viet-21526092009290863.chn ; https://vietgiaitri.com/tham-hoa-moi-cua-nhac-viet-20260920i7775631/
- [S12] https://docnhanh.vn/giai-tri/am-cha-hui-va-chieu-tro-bam-trend-tiktok-hien-tuong-mang-gay-sot-roi-hung-tron-gach-da-vi-ca-tu-nham-nhi-tintuc1052091
- [S13] https://apify.com/dami_studio/tiktok-creative-center-trends ; https://apify.com/memo23/tiktok-trending-hashtags-scraper/api
- [S14] Apify Free ≈ 1 666 kết quả TikTok Scraper / 5 USD — https://use-apify.com/docs/what-is-apify/apify-free-plan
- [S15] https://apify.com/apify/facebook-posts-scraper ; https://apify.com/dami_studio/facebook-posts-scraper
- [S16] https://www.soundstripe.com/blogs/why-can-i-only-use-commercial-sounds-on-tiktok ; https://sriplaw.com/blog/tiktoks-2025-commercial-music-library-what-brands-still-get-wrong/
- [S17] https://usethirdchair.com/blog/tiktok-commercial-music-library-what-it-covers-and-what-it-doesn-t
- [S18] Kling 3.0 Motion Control (3–30 s, chép điệu nhảy/cử chỉ) — https://kling.ai/document-api/api/video/motion-control ; https://replicate.com/kwaivgi/kling-v3-motion-control
- [S19] Suno — quyền thương mại theo gói (điều khoản 03/09/2026) — https://terms.law/ai-output-rights/suno/ ; https://www.veena.studio/blog/suno-commercial-use-rules ; https://aireiter.com/blog/suno-v6-commercial-use-copyright
- [S20] Video Depth Anything (Small Apache-2.0; Base/Large CC-BY-NC-4.0) — https://github.com/DepthAnything/Video-Depth-Anything ; https://huggingface.co/papers/2501.12375
- Người dùng 01/10: ảnh chụp video mannequin (0:02, 0:11 / 0:14), ảnh depth map nhóm nhảy, ảnh chụp phiên Antigravity "Video Analysis And Prompt Generation"; trả lời Q1–Q7.
- Trong repo: `docs/NGHIEN_CUU_PROMPT_THAM_CHIEU_2026-09-30.md`, `docs/CLIPAI_FEATURES.md`, `docs/CAP_NHAT_CLIPAI_2026-09-28.md`, `docs/CHAY_THU_2026-09-27_NHAT_KY.md`,
  `docs/KET_QUA_S4_7_S4_10_2026-10-01.md`, `data/pricing.json`, `core/reference_analysis.py`, `core/whitebox.py`, `core/clip_measure.py`, `core/research.py`.
