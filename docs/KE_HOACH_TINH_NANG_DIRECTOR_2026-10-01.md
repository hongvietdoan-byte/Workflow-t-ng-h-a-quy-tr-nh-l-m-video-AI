# Kế hoạch 3 tính năng mới cho Director (2026-10-01)

> Người dùng yêu cầu 01/10: (1) **Cover video ref** — nhập video tham chiếu, Director viết lại thành kịch bản giống vậy nhưng bằng nhân
> vật + bối cảnh Free Fire; hoặc nhập clip nhảy TikTok → nhân vật FF nhảy giống ref. (2) **Ý tưởng thô → kịch bản chi tiết**. (3) **Học
> trending** (TikTok chính, Facebook phụ), đặt lịch 1–3 ngày, làm rõ công cụ tìm/lọc, Director học và dùng thế nào, có cần Apify không,
> tốn bao nhiêu, kế hoạch 1–5 tài khoản free rồi mới mua gói. (4) Plan chi tiết, có bằng chứng.
>
> **Trạng thái: KẾ HOẠCH — chưa code, 0 USD đã chi.** Mọi bài thử tốn tiền ở đây đều chờ người dùng duyệt từng bài (luật chi phí
> `docs/CHUAN_XAY_DUNG.md`).

## 0. Tóm tắt cho người bận

| # | Tính năng | Làm thế nào (một câu) | Tiền chạy mỗi lần | Rủi ro chính | Đề xuất thứ tự |
|---|---|---|---|---|---|
| I | 💡 Ý tưởng thô → kịch bản | Director hỏi ≤ 5 câu còn thiếu → 3 hướng hook → dàn ý theo giây → kịch bản đúng khuôn Bước 1 | ≈ 0,05–0,15 USD Claude | Director "bịa" quá tay → tô màu phần Director thêm | **1** (rẻ nhất, R và T đều dùng lại) |
| T | 📈 Học trending | Lịch 1–3 ngày gom dữ liệu (nguồn miễn phí + Apify) → Claude lọc thành **thẻ trend** → người duyệt → Director đọc thẻ đã duyệt khi viết | Apify ≈ 3,5–4,5 USD/tháng (vừa gói Free 5 USD) + Claude ≈ 1,5 USD/tháng | Bản quyền nhạc trend; trend nhạy cảm; điều khoản Apify cấm nhiều tài khoản free | **2** |
| R-A | 🎬 Cover kịch bản từ video ref | Cắt shot + nghe thoại (offline) → Claude bóc tách cấu trúc → ghép vai/nơi FF → kịch bản + nhịp shot bám ref | ≈ 0,1–0,2 USD Claude/video ref (rồi đi pipeline thường) | Chép y lời / ý của người khác → chỉ giữ cấu trúc, viết lại lời | **3** |
| R-B | 💃 Cover nhảy | Đo nhịp → chia đoạn theo phách → khung đầu nhân vật FF đúng tư thế → chuyển động từ video ref (Kling/Seedance; Motion Control nếu ClipAI mở API) | Thử A/B ≈ 2,5 USD; 1 bài 30 s ≈ 3,6 USD (Kling) – 11 USD (Seedance 2.5) | Người thật trong video ref có thể bị bộ lọc chặn; tay/chân biến dạng; nhạc gốc không được dùng thương mại | **4** (sau bài thử) |

**Câu trả lời ngắn cho câu hỏi Apify:** *có nên dùng* — Apify là cách hợp lệ, rẻ, không cần tài khoản TikTok để lấy bảng xếp hạng
Creative Center (hashtag, bài hát, video, nhà sáng tạo) theo **Việt Nam** và video theo hashtag; API chính thức của TikTok (Research API)
**cấm dùng thương mại** nên không dùng được. **Nhưng không nên tạo 1–5 tài khoản Apify free**: điều khoản chung của Apify cấm một người
tạo/dùng nhiều tài khoản cá nhân, kể cả bằng email khác [S4]. Phương án thay: **1 tài khoản Apify Free (5 USD/tháng) + các nguồn miễn
phí hợp lệ khác** (mục 3.3), đo 4–6 tuần theo chỉ số ở mục 3.9, đạt thì nâng **Starter** (một số nguồn báo 29 USD, nguồn khác báo đã
giảm còn 19 USD — kiểm trên console trước khi mua [S1][S2]).

## 1. Hiện trạng code liên quan (để tính năng mới dùng lại, không làm lại)

| Đã có | Tệp | Dùng cho |
|---|---|---|
| Đọc kịch bản từ docx/xlsx/csv/txt/văn bản dán | `core/script_reader.py`, `core/script_parser.py` | I, R-A: đầu ra phải đúng khuôn này |
| Director hai lượt (Tầng A ý đồ, Tầng B quay phim từng cảnh, Đạo diễn duyệt bằng code) | `core/director_two_pass.py`, `prompts/19`, `20`, `17` | I, R-A, T: chèn khối mới vào Tầng A |
| Cắt shot video tham chiếu (ffmpeg scene score) → khung giữa → tờ 12 khung → Claude gắn nhãn cỡ/góc/chuyển động/vai trò shot | `core/reference_analysis.py`, `prompts/16_reference_shots.md` | R-A: phần "bóc tách hình" có sẵn ~70% |
| Nghe thoại offline (faster-whisper, tiếng Việt, không tốn tiền) | `core/voice_check.py::transcribe` | R-A: lấy lời thoại video ref |
| Nghiên cứu định kỳ bằng Claude web search (0,01 USD/lượt tìm), kết quả thành "bài học đề xuất" chờ người duyệt; chạy bằng Task Scheduler | `core/research.py`, `tools/monthly_research.py`, tab 🎓 Bài học | T: cùng khuôn "đề xuất → người duyệt → mới dùng" |
| Video tham chiếu chuyển động: Kling `video_list refer_type=feature`, Seedance `role=reference_video`; đã chạy thật 30/09 (T1/T2) | `core/adapters/clipai.py`, `knowledge/reference_assets_prompting.md` | R-B: đường gửi video ref đã chứng minh |
| Mẫu prompt chính thức chép động tác: *"Animate the character in @Image 1 with the same motion as the character in @Video"* | `docs/NGHIEN_CUU_PROMPT_THAM_CHIEU_2026-09-30.md` mục 1.1-5 | R-B |
| Hồ sơ nhân vật FF + Kho tài nguyên (ảnh in-game, bối cảnh, 3D) | `core/assets.py`, `data/skills/`, `profile_digest.py` | R-A/R-B ghép vai, nơi |
| Sổ chi + trần + ước tính trước | `core/cost.py`, `core/budget.py`, `core/project_budget.py` | Mọi lời gọi Apify/Claude mới |
| Đo tốc độ nói thật 2,86 âm tiết/s | `tools/measure_speech_rate.py` | I: tính độ dài thoại theo giây |
| Sổ kinh nghiệm nhà máy | `core/experience.py` | T: ghi trend nào dùng tốt / hỏng |

Giới hạn đã biết (bằng chứng trong repo):
- **Motion Control của ClipAI chỉ có trên web**, API không có (tra 23/09, `TODO.md` dòng "Bỏ qua tới khi API có…"). Quyết định đã chốt
  "chỉ dùng tính năng có API" (PLAN Mục 5) → R-B **không** dựa vào Motion Control cho tới khi ClipAI mở API.
- Kling video tham chiếu: **3–15,5 s, 1 video, 24–60 fps, cạnh 700–4553 px, giá ×1,5**, có video thì `sound` = off (tài liệu Kling Omni,
  ghi ở `NGHIEN_CUU_PROMPT_THAM_CHIEU` 1.1-6/7). Seedance 2.5: video ref ≥ 2 s, ≤ 10 video, clip ra 4–30 s.
- Giá đang dùng (`data/pricing.json`): Kling 3.0 Omni 0,08 USD/s (×1,5 khi có video vào = 0,12), Seedance 2.5 720p 0,23 USD/s + phần
  video vào ≈ 0,138 USD/s (công thức token của web ClipAI, ghi chú `_note_seedance_2_5_web`), Claude Sonnet 5: 2 USD/1M token vào,
  10 USD/1M token ra, Claude web search 0,01 USD/lượt.

## 2. Tính năng I — 💡 Ý tưởng thô → kịch bản chi tiết

### 2.1 Vấn đề và bằng chứng
- Bước 1 hiện chỉ nhận **kịch bản đã viết** (tab "📎 Tải file" / "✍ Gõ / dán văn bản" ở `dashboard/steps/step1.py`). Ý tưởng 2–3 dòng
  đưa thẳng vào thì `script_parser.split_scenes` ra 1 cảnh không có thoại, Director Tầng A phải tự bịa toàn bộ trong cùng lời gọi viết
  Bible + ý đồ — không có chỗ cho người duyệt phần bịa thêm.
- Bài học #8 (`docs/TONG_KET_DU_AN_8_2026-09-28.md`): lỗi "truyện cụt / hồi tưởng không có dấu hiệu" và "dài 83 s vs ~58 s" đều sinh
  ở khâu **kịch bản**, trước Director. Một bước viết kịch bản có cấu trúc (hook, điểm xoay, kết, tính giây) chặn được loại lỗi này sớm
  với giá rẻ nhất (chữ, không ảnh).

### 2.2 Luồng (tab thứ 3 ở Bước 1: "💡 Ý tưởng thô")
1. **Nhập:** ô văn bản ý tưởng + các ô có mặc định: thời lượng (15/30/60 s), khung (9:16), nền tảng (TikTok/Reels/FB), giọng điệu
   (hài/cảm động/hành động/drama), nhân vật muốn dùng (chọn từ Kho FF, có thể để trống), CTA (tải game/sự kiện/không).
2. **Lượt 1 — Hỏi lại (1 lời gọi Claude, ~0,01–0,02 USD):** Director đọc ý tưởng, liệt kê *có gì / thiếu gì* (xung đột, nhân vật,
   nơi, kết, CTA) và hỏi **≤ 5 câu**, mỗi câu có **đáp án mặc định**. Người dùng trả lời hoặc bấm "Dùng mặc định" — câu nào lấy mặc định
   được ghi lại (luật 1 "không im lặng khi thiếu đầu vào").
3. **Lượt 2 — 3 hướng (1 lời gọi):** 3 logline + hook 3 giây đầu khác nhau (ví dụ: 1 hướng bám ý gốc, 1 hướng bất ngờ hơn, 1 hướng dùng
   **thẻ trend đã duyệt** nếu tính năng T đã có). Người dùng chọn 1 (hoặc trộn bằng ghi chú).
4. **Lượt 3 — Dàn ý theo giây (1 lời gọi):** hook (0–3 s) → dựng tình huống → điểm xoay → cao trào → kết/CTA; mỗi nhịp có số giây, tổng
   khớp thời lượng ± 10 %. Thoại tính theo **2,86 âm tiết/s** (đo thật) → code kiểm "thoại nhịp này cần X s > khung Y s" và báo.
5. **Lượt 4 — Kịch bản đầy đủ:** viết đúng khuôn `CẢNH n - <thời gian>, <nơi>` / mô tả / `NHÂN VẬT: lời` mà `script_reader` hiểu
   (code chạy lại `script_parser` lên đầu ra; không tách được → báo lỗi, không cho đi tiếp).
6. **Duyệt:** màn hình 2 cột — trái ý tưởng gốc, phải kịch bản; **phần Director thêm được tô màu** (nhân vật mới, nơi mới, câu thoại không
   có trong ý tưởng) để người dùng biết cái gì là của mình, cái gì là của máy. Sửa tay được; bấm "Dùng kịch bản này" → vào Bước 1 như kịch
   bản tải lên (từ đây mọi cổng Bible / storyboard / ngân sách giữ nguyên).

### 2.3 Kiểm bằng code (không tốn tiền)
- Nhân vật được nêu phải có trong Kho FF (hoặc gắn cờ "nhân vật mới — cần ảnh").
- Nơi chốn: ưu tiên nơi có trong Kho (có render 3D / ảnh trong game); nơi không có → cờ "AI vẽ, ~70 % giống" (theo bài học gói bối cảnh).
- Tổng giây, giây thoại từng nhịp, có hook trong 3 s đầu, có kết (không cụt), CTA đúng ô đã chọn.
- Không ghi số tuổi < 18 (luật hồ sơ nhân vật đã chốt 25/09).

### 2.4 Kiến thức cho Director
Tạo `prompts/23_idea_to_script.md` + `knowledge/roles/screenwriter.md` (vai **Biên kịch** — vai thứ 4 cạnh Đạo diễn/Quay phim/Dựng):
cấu trúc video ngắn (hook – giữ chân – trả thưởng), công thức tiểu phẩm Kelly Show, luật thoại (`knowledge/dialogue_craft.md` đã có),
hướng dẫn thể loại (`knowledge/genre_guides.md` đã có). Mỗi luật có lý do + nguồn như bộ kỹ năng 3 vai.

### 2.5 Đo hiệu quả (bộ đo cố định)
5 ý tưởng thô mẫu (người dùng đưa, hoặc lấy từ các dự án #1–#8) → chạy I → người dùng chấm 1–5 cho: giữ đúng ý, hook, logic, độ dài,
"quay được bằng pipeline". Cổng bật mặc định: trung bình ≥ 4 và 0 kịch bản fail kiểm code. Chi phí đo ≈ 5 × 0,15 = **0,75 USD**.

### 2.6 Chi phí
4 lời gọi Sonnet 5, ước ~25k token vào (có cache phần luật) + ~6k token ra ≈ 0,05 + 0,06 = **≈ 0,1 USD/kịch bản** (trần cứng 0,3 USD/lần
qua sổ chi, stage `screenwriter`).

## 3. Tính năng T — 📈 Học trending (TikTok chính, Facebook phụ)

### 3.1 Bằng chứng nhu cầu và rủi ro (ví dụ người dùng nêu)
- "Ông chã húi, bà chả hơm": biến âm của "ông xã / bà xã" (xã → chã/chả; thúi/thơm → húi/hơm); khởi phát từ video "Bà chả húi, ăm chả húi
  ơi" của TikToker Kiệt Hà Tịnh (> 10 triệu theo dõi) **đầu tháng 6/2026**, > 3 triệu lượt xem; sau đó bài hát "Ăm chã húi" (Lâm Thằn Lằn)
  viral [S9][S10].
- **Cùng trend đó đã bị báo chí gọi là "thảm họa mới của nhạc Việt"** và "hứng trọn gạch đá vì ca từ nhảm nhí" (Kenh14 / 24h / Việt Giải
  Trí ngày 20/09/2026; Docnhanh) [S11][S12]. → Bằng chứng trực tiếp rằng **trend không tự động an toàn cho thương hiệu**: cụm từ có thể
  dùng (đùa vợ chồng/cặp đôi Kelly – Kenta), nhưng bài hát thì rủi ro. Vì thế mỗi trend phải qua **thẻ có cờ rủi ro + người duyệt**.
- Tuổi thọ: trend khởi phát tháng 6, lên báo tháng 6 → tháng 9 đã bị chê → **3–4 tháng** từ nổi tới bão hòa/phản ứng ngược. Thẻ trend
  phải có **trạng thái vòng đời** (đang lên / đỉnh / đang xuống / hết hạn).

### 3.2 Công cụ — đã so sánh

| Nguồn | Lấy được gì | Hợp lệ? | Tiền | Kết luận |
|---|---|---|---|---|
| **TikTok Research API** (chính thức) | Video, bình luận, người dùng | **Không** — chỉ cho học thuật/phi lợi nhuận ở vùng được phép; FAQ nói nhà sáng tạo, nhà quảng cáo, đơn vị thương mại **không** đủ điều kiện; 1000 lượt/ngày [S6][S7] | Free | ❌ Loại |
| **TikTok Creative Center** (web công khai cho nhà quảng cáo) | Hashtag top, bài hát top, nhà sáng tạo, video top; lọc **quốc gia** + 7/30/120 ngày; xem không cần đăng nhập [S8] | Có (công cụ công khai của TikTok) | Free | ✅ Nguồn chính — nhưng không có API, phải đọc tay **hoặc** qua Apify |
| **Apify actor đọc Creative Center** (ví dụ `clockworks/tiktok-trends-scraper`, `crawloop/tiktok-trending-hashtags-scraper`, `automation-lab/tiktok-creative-center-scraper`) | Hashtag + hạng + lượt xem + số bài + đường cong phổ biến + nhà sáng tạo dẫn đầu; lọc quốc gia, cửa sổ 7/30/90 ngày; **không cần tài khoản TikTok** [S3][S13] | Có (dữ liệu công khai; người dùng chịu trách nhiệm tuân thủ — xem 3.8) | **0,99–1,70 USD / 1000 dòng** (rẻ nhất); bản "hashtag + sound + creator" 8,20 USD/1000 [S3][S13] | ✅ Dùng — thay việc đọc tay |
| **Apify `clockworks/tiktok-scraper`** | Video theo hashtag / từ khóa / tài khoản: caption, hashtag, **nhạc (tên, tác giả, bản gốc?)**, lượt xem/thích/chia sẻ, thời gian; tải video tùy chọn | Có (như trên) | ~1,70 USD/1000 kết quả (giá "từ", gói trả phí) [S5]; **gói Free ≈ 0,003 USD/kết quả** (~1 666 kết quả cho 5 USD) [S14] | ✅ Dùng — lấy **ví dụ cụ thể** cho mỗi trend |
| **Apify Facebook Posts Scraper** (`apify/facebook-posts-scraper` và bản khác) | Bài đăng trang công khai: chữ, media, lượt tương tác | Có | 0,65–2,00 USD/1000 bài [S15] | ✅ Phụ — theo dõi 5–10 trang meme/game VN + fanpage FF |
| **Claude web search** (đã có trong `core/research.py`) | Báo/blog VN viết về trend ("… là gì mà hot vậy") — chính là cách tìm ra bằng chứng "ông chã húi" ở mục 3.1 | Có | 0,01 USD/lượt tìm + token | ✅ Dùng — giải thích **nghĩa + nguồn gốc + phản ứng dư luận**, thứ số liệu Apify không có |
| **kworb.net/charts/tiktok/vn.html** | Bảng bài hát trend TikTok VN [S8b] | Trang công khai | Free | ✅ Kiểm chéo bài hát (đọc qua Claude web fetch) |
| Nhập tay (người dùng dán link/cụm từ thấy trên điện thoại) | Bất cứ gì | Có | Free | ✅ Luôn có — trend người làm nội dung thấy trước máy |

**Vì sao vẫn cần Apify dù có Claude web search:** web search chỉ thấy trend **khi báo đã viết** (trễ 1–3 tuần — ví dụ ông chã húi: video
đầu tháng 6, báo viết cuối tháng 6). Creative Center cho số liệu **trong 7 ngày**, bắt được trend đang lên trước khi lên báo; scraper video
cho ví dụ thật (caption, nhạc đi kèm) để Director thấy *cách người ta dùng*. Hai nguồn bổ sung nhau.

### 3.3 Chuyện "1–5 tài khoản free"
- **Apify:** điều khoản chung **cấm tạo hoặc dùng nhiều tài khoản cá nhân**, trực tiếp hay qua người khác, kể cả bằng email khác, trừ khi
  Apify cho phép; Acceptable Use Policy cấm tạo tài khoản giả [S4]. Hậu quả có thể là khóa cả tài khoản đang dùng → mất dữ liệu đã gom.
  **Không đưa vào kế hoạch.** (Nếu cần nhiều người dùng chung: Apify có tài khoản tổ chức — kiểm điều kiện trên console.)
- **Cách hợp lệ để "dùng nhiều gói free" đúng tinh thần yêu cầu:** mỗi **dịch vụ khác nhau** một tài khoản free:
  1 Apify Free (5 USD/tháng) · TikTok Creative Center (free, không cần API) · Claude web search (đã trả qua khóa Anthropic) · kworb (free)
  · (tùy chọn, cần kiểm điều khoản/giá trước khi đăng ký) một dịch vụ API TikTok khác có gói free để dự phòng khi actor Apify hỏng.
  Đây là 3–5 nguồn free hợp lệ.

### 3.4 Kiến trúc

```
Lịch (Windows Task Scheduler, mỗi 1–3 ngày, chỉnh trong ⚙)   ← giống tools/monthly_research.py
   └─ tools/trend_scan.py
        1. GOM  (core/trends/sources/*.py — mỗi nguồn 1 adapter, đều qua sổ chi + trần tháng)
           ├─ apify_creative_center: hashtag top 50 + bài hát top 50, quốc gia VN, cửa sổ 7 ngày
           ├─ apify_tiktok_videos:  8–10 hashtag/cụm từ đang lên → 10 video/hashtag (caption, nhạc, lượt xem, ngày)
           ├─ apify_facebook:       5–10 trang theo dõi → 10 bài mới/trang (tuần 1 lần)
           ├─ claude_web_search:    "trend TikTok Việt Nam tuần này", "<cụm từ> là gì"  (≤ 5 lượt tìm)
           └─ nhập tay:             ô dán link / cụm từ trên dashboard
           → bảng trend_raw (nguồn, loại, nội dung, số liệu, url, lúc lấy)  — chỉ chữ + số, KHÔNG lưu video người khác
        2. LỌC BẰNG CODE (0 USD): bỏ trùng; tính tốc độ tăng giữa 2 lần quét (hạng, lượt xem); bỏ hashtag quảng cáo/thương hiệu khác;
           bỏ từ khóa nhạy cảm theo danh sách đen (chính trị, tôn giáo, tai nạn, bạo lực thật, 18+); giữ ~20 ứng viên
        3. CHẮT LỌC (1 lời gọi Claude ~0,1 USD): mỗi ứng viên → THẺ TREND đề xuất (dưới)
   └─ Dashboard ⚙ → "📈 Trend": người duyệt / sửa / loại thẻ (giống tab 🎓 Bài học)
   └─ Director (Tầng A + Biên kịch I + Cover R-A) đọc ≤ 8 thẻ ĐÃ DUYỆT, còn hạn, hợp thể loại
```

**Thẻ trend** (bảng `trend_cards`):

| Trường | Ví dụ ("ông chã húi") |
|---|---|
| `kind` | cụm_từ / âm_thanh / định_dạng (khuôn video, ví dụ "POV…", "trước/sau") / hashtag / meme_hình / điệu_nhảy |
| `title`, `meaning_vi`, `origin` | "Ông chã húi / bà chả hơm" = cách gọi đùa ông xã / bà xã; gốc video Kiệt Hà Tịnh 06/2026 |
| `how_used` | 3 ví dụ caption/thoại thật (từ scraper) + cách dùng phổ biến (gọi người yêu, cà khịa cặp đôi) |
| `fit_ff` (0–1) + gợi ý | 0,8 — Kelly gọi Kenta "ông chã húi" khi cãi yêu; hợp tiểu phẩm cặp đôi, KHÔNG hợp trailer hành động |
| `tone` | hài, dễ thương, Gen Z |
| `risk_flags` | `song_criticized` (bài hát bị chê trên báo 09/2026), `overused` |
| `music_license` | `cml` (có trong Commercial Music Library) / `unknown` / `not_cleared` |
| `lifecycle` | đang_lên / đỉnh / đang_xuống / hết_hạn (code tính từ số liệu 2 lần quét + ngày báo viết) |
| `expires_at` | mặc định +21 ngày, tự gia hạn nếu lần quét sau còn tăng |
| `evidence` | URL nguồn + số liệu tại thời điểm quét |
| `status` | đề_xuất → đã_duyệt / loại (người, kèm lý do) |

### 3.5 Director "học" thế nào (không train model — đúng quyết định đã chốt "không fine-tune", PLAN Mục 5)
"Học" = **đưa thẻ đã duyệt vào ngữ cảnh** khi viết, có luật dùng:
1. Khối mới **"Xu hướng dùng được (đã duyệt, còn hạn)"** trong prompt Tầng A (`prompts/19`), prompt Biên kịch (I) và Cover (R-A): ≤ 8 thẻ,
   chọn theo thể loại + giọng điệu của dự án (code lọc, không để Claude tự chọn trong 100 thẻ).
2. **Luật dùng trend** (`knowledge/trend_usage.md`, mỗi luật có lý do):
   - Không bắt buộc; ≤ 2 trend / 60 s — nhồi trend làm kịch bản thành chuỗi meme, mất câu chuyện.
   - Đặt ở **hook (3 s đầu)** hoặc **câu chốt**; hợp tính cách nhân vật (hồ sơ chuẩn KELLY/KENTA/MAXIM) — Maxim ham ăn nói "chã húi" thì
     hợp, nhưng cảnh bi không dùng.
   - Thẻ `lifecycle = đang_xuống` → chỉ dùng kiểu **nhại/tự giễu**; `hết_hạn` → không đưa vào prompt.
   - Có `risk_flags` → chỉ dùng phần an toàn (cụm từ, không dùng bài hát), Director phải ghi lý do.
   - **Nhạc trend:** chỉ dùng bản gốc khi `music_license = cml` hoặc Garena có quyền. Còn lại → chỉ học **nhịp/BPM/không khí** đưa vào
     brief nhạc Clip AI (`music_v2`) để tạo nhạc mới cùng cảm giác, **không chép giai điệu**.
3. Đầu ra Director thêm trường `trend_refs: [{card_id, where: "scene 1 line 2", why}]` → code kiểm card còn hạn + đã duyệt; dashboard hiện
   huy hiệu "📈 dùng trend X" ở cảnh đó để người dùng gỡ được.
4. **Vòng phản hồi:** ghi `trend_usage` (dự án, thẻ, chỗ dùng). Khi người dùng nhập số liệu đăng bài (tab 📊, sau này kéo tự động bằng
   chính scraper TikTok theo tài khoản kênh) → sổ kinh nghiệm `core/experience.py` ghi "trend X ở hook → giữ chân tốt / kém". Đây là
   phần "Director trẻ dần lên" có bằng chứng, không chỉ cảm giác.

### 3.6 Bản quyền nhạc — rủi ro lớn nhất, phải nói rõ
- Tài khoản **doanh nghiệp** trên TikTok **không** dùng được thư viện âm thanh thường, chỉ dùng **Commercial Music Library** (> 1 triệu bản
  đã cấp phép); phần lớn nhạc trend **không** có trong CML vì quyền thương mại phải xin riêng từng chủ sở hữu [S16][S17].
- Thư viện nhạc chung của TikTok chỉ cấp phép cho giải trí cá nhân, loại trừ dùng thương mại; tick "xác nhận sở hữu nhạc" khi không có
  quyền tạo bằng chứng vi phạm cố ý (mức bồi thường luật định Mỹ tới 150 000 USD/bản) [S16].
- → Video của Garena/Free Fire là nội dung thương hiệu: **pipeline không tự chèn nhạc trend vào bản giao**. Dashboard ghi rõ "nhạc trend:
  chỉ gợi ý — gắn trên app TikTok nếu có trong CML" hoặc dùng nhạc tạo mới. Người dùng/pháp chế Garena chốt chính sách (câu hỏi mở Q4).

### 3.7 Lịch và chi phí — vừa gói Free 5 USD/tháng

Giá dùng để tính: Creative Center 1,70 USD/1000 dòng (bản rẻ 0,99) [S3][S13]; video TikTok **0,003 USD/kết quả ở gói Free** (lấy mức cao
để an toàn) [S14]; Facebook 2 USD/1000 bài [S15]. **Chưa kiểm trên console Apify** (máy dựng plan bị chặn truy cập apify.com) → lần chạy
đầu đo số thật, ghi vào `data/pricing.json` rồi mới bật lịch.

| Việc | Tần suất | Số dòng/lần | USD/lần | Lần/tháng | USD/tháng |
|---|---|---|---|---|---|
| Creative Center VN: hashtag top 50 + bài hát top 50 (7 ngày) | 1 tuần/lần (cửa sổ 7 ngày, quét dày hơn không thêm tin) | 100 | 0,17 | 4,3 | **0,73** |
| Video TikTok theo 8 hashtag/cụm đang lên × 10 video | **mỗi 3 ngày** (chỉnh 1–3 ngày) | 80 | 0,24 | 10 | **2,40** |
| Facebook 5 trang × 10 bài | 1 tuần/lần | 50 | 0,10 | 4,3 | **0,43** |
| **Tổng Apify** | | | | | **≈ 3,6 USD** (< 5 USD Free; chừa ~1,4 USD cho phí nền tảng/chạy lại) |
| Claude chắt lọc thẻ (~25k token vào + 4k ra) | mỗi lần quét video | — | ≈ 0,09 | 10 | 0,9 |
| Claude web search (≤ 5 lượt) | mỗi lần quét | — | 0,05 | 10 | 0,5 |
| **Tổng Claude** | | | | | **≈ 1,4 USD** |

- Chạy **mỗi ngày** cùng cấu hình: Apify ≈ 0,73 + 7,2 + 0,43 ≈ **8,4 USD** → vượt Free → chỉ khi đã lên Starter.
- Khóa cứng trong code: trần Apify tháng = **4,5 USD** (sổ chi stage `trend_apify`), trần mỗi lần 0,5 USD; hết trần → lịch tự dừng + báo
  trên dashboard, không chạy tiếp lặng lẽ. Đặt thêm **giới hạn chi trên chính console Apify** làm lớp thứ hai.

### 3.8 Pháp lý dữ liệu
- Chỉ lấy **dữ liệu công khai**, chỉ lưu **chữ + số + URL**; không lưu video/ảnh của người khác (giống luật `reference_analysis`: "only
  TEXT data is kept"). Không lấy dữ liệu cá nhân ngoài tên kênh công khai.
- Người dùng Apify chịu trách nhiệm tính hợp pháp khi thu thập — cần **pháp chế Garena xác nhận** việc dùng scraper cho nghiên cứu trend
  nội bộ (câu hỏi mở Q3). Đây là lý do T1 (nguồn miễn phí, không scraper) đi trước T2.

### 3.9 Khi nào nâng gói (tiêu chí đo được, sau 4–6 tuần)
Nâng **Apify Starter** khi **cả 3** đúng: (a) ≥ 5 thẻ được duyệt/tuần trong 3 tuần liên tiếp; (b) ≥ 40 % kịch bản mới có `trend_refs`
mà người dùng giữ lại (không gỡ); (c) Free hết trần ≥ 2 tháng hoặc cần quét hằng ngày. Không đạt (a)/(b) → giữ Free, giảm nguồn.
Giá Starter: 29 USD (đa số nguồn) hoặc 19 USD (một nguồn báo đã giảm) — phí gói = tiền dùng trả trước tương ứng [S1][S2]; kiểm trên
console trước khi mua.

## 4. Tính năng R-A — 🎬 Cover kịch bản từ video ref

### 4.1 Luồng ("🎬 Cover video ref" ở Bước 1, chọn loại "Tiểu phẩm / kịch bản")
1. **Nhập video:** tải tệp mp4 lên (khuyến nghị). Dán link TikTok → chỉ tải khi người dùng tick "tôi có quyền dùng video này để tham
   khảo" (qua Apify `tiktok-scraper` tùy chọn tải video, hoặc người dùng tự tải). Video ref lưu ở thư mục dữ liệu dự án, **không commit**.
2. **Bóc tách — phần lớn đã có code, 0 USD:** `probe` → `detect_cuts` → khung giữa từng shot → tờ 12 khung (`core/reference_analysis.py`);
   thoại: `voice_check.transcribe` (faster-whisper offline); nhịp nhạc/điểm nhấn âm: DSP (theo skill `motion-engine-dsp`, không AI).
3. **Claude bóc cấu trúc (1 lời gọi có ảnh, ≈ 0,06 USD cho video 60 s ≈ 3 tờ khung):** prompt mới `prompts/24_reference_breakdown.md`:
   - từng shot: giây bắt đầu/kết thúc, cỡ, góc, chuyển động máy, hành động, vai trò (hook/dựng/hành động/phản ứng/chèn/thoại/kết), cảm xúc;
   - toàn video: hook là gì, điểm xoay, cú chốt, nhịp (giây TB/shot), chữ trên màn hình, nhạc đổi ở đâu;
   - **vai trò** người trong video (A: người yêu đanh đá, B: người bị cà khịa…), **không** nhận dạng người thật.
4. **Ghép FF (người dùng duyệt):** code gợi ý vai → nhân vật FF theo hồ sơ (tính cách, giới, độ tuổi tả chữ), nơi → nơi trong Kho (ưu
   tiên có 3D/ảnh trong game), đạo cụ → vật phẩm FF; người dùng đổi trong bảng thả xuống.
5. **Viết lại (1 lời gọi, ≈ 0,05 USD):** kịch bản đúng khuôn Bước 1, **giữ cấu trúc + nhịp + cú chốt**, **viết lại lời** cho hợp nhân
   vật FF (không chép nguyên văn lời người khác — câu nào trùng > 70 % so với bản nghe được thì code gắn cờ). Kèm `ref_shots`: danh sách
   shot đích (giây, cỡ, góc, chuyển động) để Tầng B Quay phim **bám** thay vì tự nghĩ.
6. **Đi pipeline thường** (Bible, cổng storyboard, ngân sách…). Thêm: **xem song song** ref ↔ animatic của mình (`core/animatic.py` có sẵn)
   để người dùng so nhịp trước khi chi tiền video. Shot nào cần chép **đường máy** → cắt đoạn ref tương ứng làm Kling `feature` (mẫu
   chính thức "follow the camera movement of @video") — đường gửi đã chạy thật 30/09.

### 4.2 Chi phí
Phân tích + viết lại ≈ **0,1–0,2 USD Claude/video ref**; phần ảnh/video như dự án thường. Bộ đo: 3 video ref (người dùng chọn) → người
dùng chấm "giống tinh thần ref" + "ra chất FF" 1–5; cổng bật: TB ≥ 4.

## 5. Tính năng R-B — 💃 Cover nhảy (nhân vật FF nhảy theo clip TikTok)

### 5.1 Ba cách làm — so sánh có bằng chứng

| Cách | Bằng chứng khả năng | Có qua API ClipAI? | Giá 30 s | Ghi chú |
|---|---|---|---|---|
| **(1) Kling 3.0 Omni + video ref `feature`** — prompt "Animate the character in @Image 1 with the same motion as the character in @Video" | Mẫu chính thức của Kling cho chép **động tác cơ thể**; dự án đã gửi video ref Kling thật 30/09 (T2: "gọi tên `<<<video_1>>>` rõ hơn hẳn") | **Có** | 30 × 0,08 × 1,5 = **3,6 USD** (3 đoạn ≤ 15,5 s) | Video ref 3–15,5 s/lần → phải chia đoạn |
| **(2) Seedance 2.5 + `reference_video`** | Video ref mang được "động tác, máy quay, nhịp, thời gian" (tài liệu chính thức, `NGHIEN_CUU…` 1.2-3); T1 30/09 chép hiệu ứng kỹ năng tốt nhất | **Có** | 30 × (0,23 + 0,138) ≈ **11 USD** | Clip tới 30 s một lần; đắt gấp ~3 |
| **(3) Kling 3.0 Motion Control** | Sản phẩm **chuyên** chép điệu nhảy/cử chỉ từ video sang ảnh nhân vật, video ref 3–30 s, giữ tay và toàn thân tốt hơn [S18] | **Không** — ClipAI chỉ có trên web (tra 23/09) | chưa có giá ClipAI | Hỏi ClipAI mở API; trong lúc chờ: người dùng chạy trên web, nhập kết quả vào dashboard (bán tự động) |

→ Không đoán trước cách nào tốt hơn: **thử A/B trước khi build** (luật 5 "thang kiểm thật").

### 5.2 Luồng (khi đã chọn được cách)
1. **Nhập + kiểm video ref (code, 0 USD):** độ dài, fps 24–60, cạnh ≥ 700 px, SAR 1:1 (adapter Kling đã kiểm 3 luật), **1 người nhảy**,
   thấy toàn thân, máy ít rung (đếm người bằng YuNet có sẵn; người dùng xác nhận nếu code không chắc). Video không đạt → báo rõ lý do.
2. **Nhịp:** đo BPM + phách mạnh bằng DSP → **cắt đoạn tại phách** (Kling ≤ 15,5 s/đoạn) để chỗ nối rơi vào phách, đỡ lộ.
3. **Khung đầu:** Deepix vẽ nhân vật FF (ảnh in-game trong Kho làm chuẩn) **đúng tư thế khung đầu video ref**, trên nền FF (render 3D / ảnh
   trong game). Người duyệt khung đầu (cổng storyboard giữ nguyên).
4. **Chuyển động từng đoạn:** đoạn n+1 dùng **khung cuối thật** của đoạn n làm khung đầu (liền mạch tư thế, nền).
5. **QC nhảy (mới, code trước, Claude sau):** độ lệch nhịp (đỉnh năng lượng chuyển động của clip so với phách — đo bằng hiệu khung, 0 USD);
   số người; mặt còn đúng nhân vật (tầng 0 Tổ QC đã có); tay/chân biến dạng (Claude QC video chỉ khi tầng code nghi ngờ).
6. **Âm thanh:** bản giao **không** dùng nhạc gốc của clip ref trừ khi có quyền (CML/Garena) — mục 3.6. Mặc định: nhạc Clip AI `music_v2`
   **cùng BPM** (điệu nhảy khớp phách nên vẫn khớp), hoặc để trống cho người dùng gắn nhạc CML trên app TikTok.

### 5.3 Rủi ro đã biết
- **Người thật trong video ref:** bộ lọc "người thật" của Seedance từng chặn ảnh nhân vật; video ref có người thật có thể bị chặn
  (`NGHIEN_CUU…` 3.2 ghi "[chưa kiểm với Seedance]") → bài thử phải gồm 1 video có người thật.
- Biên đạo/nhạc của người sáng tạo gốc: ghi nguồn khi đăng; tránh clip của thương hiệu khác.
- Nhân vật FF có trang phục rộng/vũ khí → tay chân dễ dính; chọn trang phục gọn cho bản đầu.

### 5.4 Bài thử A/B (chờ duyệt — **≈ 2,5 USD**)
1 đoạn nhảy 5 s (người dùng chọn clip có quyền dùng), Kelly in-game, cùng khung đầu (1 ảnh Deepix ≈ 0,05):
(1) Kling feature 5 × 0,12 = 0,60 USD · (2) Seedance 2.5 720p 5 × 0,37 ≈ 1,85 USD · (3) Motion Control trên web ClipAI (người dùng tự
chạy, ghi giá). Chấm: đúng động tác (người dùng 1–5), mặt/trang phục giữ (Tổ QC tầng 0), lệch nhịp (code), có bị chặn không.

## 6. Ma trận kế thừa (luật 2 — `docs/CHUAN_XAY_DUNG.md`)

Ba luồng mới đều **đổ về Bước 1 như kịch bản thường** nên kế thừa các biện pháp sau Bước 1. Bảng điền trước khi merge mỗi đợt:

| Biện pháp | Ý tưởng → kịch bản | Cover kịch bản | Cover nhảy | Test |
|---|---|---|---|---|
| Ảnh tham chiếu đúng người/đúng look | kế thừa (qua Bước 1) | kế thừa | **khung đầu riêng** → dùng cùng hàm chọn ảnh | test chọn ảnh cho luồng nhảy |
| Cổng Bible / storyboard / không tự duyệt dưới sàn | kế thừa | kế thừa | cổng khung đầu + cổng đoạn đầu | test cổng |
| Luật chọn model | kế thừa | kế thừa + Kling `feature` cho đường máy | cố định theo kết quả A/B | test router |
| Gen lại phải đổi đầu vào, ≤ 2 lần | — (chữ) | kế thừa | kế thừa từng đoạn | test |
| Sổ chi + trần + ước tính trước | stage `screenwriter` | stage `reference_breakdown` | ước tính cả bài trước khi gửi đoạn 1 | test ước tính |
| Giữ phần người sửa tay | kịch bản sửa tay không bị ghi đè khi bấm lại | bảng ghép vai | khung đầu đã duyệt | test |
| Không im lặng khi thiếu đầu vào | câu hỏi dùng mặc định được ghi | video không cắt được shot / không nghe được thoại → báo | video không đạt luật → báo | test |
| Thẻ trend chỉ dùng khi đã duyệt + còn hạn | có | có | — | test lọc thẻ |

## 7. Lộ trình — đợt và việc (đề xuất thêm vào `docs/KE_HOACH_SUA_SAU_DU_AN_8.md` thành đợt S11)

| Việc | Nội dung | Tiền | Công (ngày) | Phụ thuộc |
|---|---|---|---|---|
| **S11.0** | Người dùng chốt câu hỏi mở Q1–Q6 (mục 8) | 0 | — | — |
| **S11.1** | I: prompt 23 + vai Biên kịch + 4 lượt + kiểm code + màn 2 cột tô phần Director thêm | 0 (code) | 2–3 | — |
| **S11.2** | I: bộ đo 5 ý tưởng, người dùng chấm | ≈ 0,75 | 0,5 | S11.1 |
| **S11.3** | T1: bảng `trend_raw`/`trend_cards`, nguồn **miễn phí** (Claude web search, kworb, nhập tay), tab ⚙ 📈 Trend, duyệt thẻ | ≈ 0,15/lần | 2 | — |
| **S11.4** | T2: adapter Apify (`apify-client`, `APIFY_TOKEN` trong `dashboard.env`), sổ chi + trần tháng, lịch Task Scheduler 1–3 ngày | lần đo đầu ≈ 0,5 | 1,5 | Q2, Q3 |
| **S11.5** | T3: khối "Xu hướng" vào Tầng A / Biên kịch / Cover + `knowledge/trend_usage.md` + `trend_refs` + huy hiệu | 0 | 1 | S11.3 |
| **S11.6** | T4: vòng phản hồi số liệu đăng bài → sổ kinh nghiệm; báo cáo tuần chỉ số 3.9 | 0 | 1 | S11.5 |
| **S11.7** | R-A: prompt 24 bóc tách + ghép vai/nơi + viết lại + `ref_shots` cho Tầng B + xem song song | ≈ 0,2/video | 3 | S11.1 |
| **S11.8** | R-A: bộ đo 3 video ref | ≈ 0,6 | 0,5 | S11.7 |
| **S11.9** | R-B: kiểm video ref + nhịp/cắt đoạn + **bài thử A/B 3 cách** | ≈ 2,5 | 1,5 | Q5 |
| **S11.10** | R-B: luồng đầy đủ theo cách thắng + QC nhảy + âm thanh cùng BPM | 1 bài 30 s ≈ 3,6–11 | 3 | S11.9 |
| **S11.11** | Đánh giá sau 4–6 tuần: quyết nâng Apify Starter theo 3.9 | 0 | — | S11.4 + 4 tuần |

Tổng tiền thử trước khi dùng thật: **≈ 5 USD** (I 0,75 + T ≈ 0,7 + R-A 0,6 + R-B 2,5), chưa tính Apify Free (0 USD trả thêm).
Mọi cờ mới **TẮT** tới khi qua bộ đo: `idea_to_script`, `trend_feed`, `trend_apify`, `ref_cover`, `dance_cover`.

## 8. Câu hỏi mở — cần người dùng chốt

| # | Câu hỏi | Đề xuất của Claude |
|---|---|---|
| Q1 | Thứ tự làm | I → T1 → T2 → R-A → R-B (rẻ trước, dùng lại nhiều trước) |
| Q2 | Apify: 1 tài khoản Free (đúng điều khoản) thay cho 1–5 tài khoản free? | Đồng ý 1 Free + nguồn free khác; không lập nhiều tài khoản Apify |
| Q3 | Pháp chế Garena cho phép scraper dữ liệu công khai TikTok/FB cho nghiên cứu nội bộ? | Hỏi trước S11.4; S11.3 (không scraper) làm được ngay |
| Q4 | Chính sách nhạc: video giao có được dùng nhạc trend không? | Mặc định không; chỉ CML/nhạc Garena có quyền; còn lại tạo nhạc cùng BPM |
| Q5 | Clip nhảy dùng cho bài thử — người dùng chọn clip có quyền dùng (ví dụ clip nội bộ/nhân viên tự quay) | Clip tự quay là an toàn nhất, đồng thời thử luôn bộ lọc người thật |
| Q6 | Hỏi ClipAI mở API Motion Control? | Có — gửi kèm câu hỏi Bàn đạo diễn đang chờ |
| Q7 | Tần suất quét video TikTok: 1, 2 hay 3 ngày? | 3 ngày ở gói Free (bảng 3.7); 1 ngày khi lên Starter |

## 9. Nguồn

Ghi chú độ tin: máy dựng plan **bị chặn truy cập** apify.com, docs.apify.com, kling.ai, clipai.ingarena.net, tuoitre.vn → các số dưới đây
lấy từ **đoạn trích kết quả tìm kiếm** của chính trang Apify Store / trang thứ ba; phải kiểm lại trên console Apify ở lần chạy đầu (S11.4).

- [S1] Apify pricing (Free 0 USD kèm 5 USD dùng/tháng; Starter/Scale/Business; phí gói = tiền dùng trả trước; 1 CU = 1 GB RAM × 1 giờ) —
  https://apify.com/pricing ; tổng hợp: https://scrapegraphai.com/blog/apify-pricing , https://use-apify.com/docs/what-is-apify/apify-pricing
- [S2] Báo Starter giảm 29 → 19 USD — https://scrapewise.ai/blogs/apify-pricing-compute-units-cost-2026 (nguồn thứ ba, cần kiểm)
- [S3] Actor Creative Center: https://apify.com/clockworks/tiktok-trends-scraper (từ 1,70 USD/1000), https://apify.com/crawloop/tiktok-trending-hashtags-scraper
  (từ 0,99 USD/1000), https://apify.com/automation-lab/tiktok-creative-center-scraper (từ 1,62 USD/1000; quốc gia + cửa sổ 7/30/90 ngày,
  không cần đăng nhập), https://apify.com/automation-lab/tiktok-trends-scraper (hashtag + sound + creator, từ 8,20 USD/1000)
- [S4] Apify General Terms and Conditions (cấm nhiều tài khoản cá nhân) — https://docs.apify.com/legal/general-terms-and-conditions ;
  Acceptable Use Policy — https://docs.apify.com/legal/acceptable-use-policy
- [S5] TikTok Scraper (clockworks), 1,70 USD/1000 kết quả — https://apify.com/clockworks/tiktok-scraper
- [S6] TikTok Research API — điều kiện + cấm thương mại: https://tokconnect.com/guides/tiktok-research-api/ ,
  https://www.keyapi.ai/blog/tiktok-research-api-commercial-trend-scanning/
- [S7] https://www.xpoz.ai/blog/guides/tiktok-research-api-limits-access-and-alternatives/ (1000 lượt/ngày)
- [S8] TikTok Creative Center (hashtag/bài hát top theo vùng, 24 giờ/30/120 ngày, phần lớn xem không cần đăng nhập) — https://bir.ch/blog/tiktok-creative-center ;
  [S8b] https://kworb.net/charts/tiktok/vn.html
- [S9] Tuổi Trẻ Cười, "'Ông chả húi, bà chả hơm' là gì…" — https://cuoi.tuoitre.vn/ong-cha-hui-ba-cha-hom-la-gi-ma-nghe-mac-cuoi-vay-may-ni-100260629085401026.htm
- [S10] https://ai-hay.vn/ong-cha-hui-la-gi-pN1UmIco4tC
- [S11] "Thảm họa mới của nhạc Việt" — https://kenh14.vn/tham-hoa-moi-cua-nhac-viet-21526092009290863.chn ,
  https://vietgiaitri.com/tham-hoa-moi-cua-nhac-viet-20260920i7775631/
- [S12] Docnhanh, "'Ăm chã húi' và chiêu trò bám trend TikTok…" — https://docnhanh.vn/giai-tri/am-cha-hui-va-chieu-tro-bam-trend-tiktok-hien-tuong-mang-gay-sot-roi-hung-tron-gach-da-vi-ca-tu-nham-nhi-tintuc1052091
- [S13] https://apify.com/dami_studio/tiktok-creative-center-trends , https://apify.com/memo23/tiktok-trending-hashtags-scraper/api
- [S14] Apify Free: 5 USD ≈ 1 666 kết quả TikTok Scraper (0,003 USD/kết quả), CU 0,2 USD ở gói Free — https://use-apify.com/docs/what-is-apify/apify-free-plan
- [S15] Facebook Posts Scraper 0,65–2,00 USD/1000 bài — https://apify.com/apify/facebook-posts-scraper , https://apify.com/dami_studio/facebook-posts-scraper
- [S16] Commercial Music Library / tài khoản doanh nghiệp — https://www.soundstripe.com/blogs/why-can-i-only-use-commercial-sounds-on-tiktok ,
  https://sriplaw.com/blog/tiktoks-2025-commercial-music-library-what-brands-still-get-wrong/
- [S17] https://usethirdchair.com/blog/tiktok-commercial-music-library-what-it-covers-and-what-it-doesn-t
- [S18] Kling 3.0 Motion Control (chép điệu nhảy/cử chỉ từ video sang ảnh nhân vật, 3–30 s) — https://kling.ai/document-api/api/video/motion-control ,
  https://replicate.com/kwaivgi/kling-v3-motion-control
- Trong repo: `docs/NGHIEN_CUU_PROMPT_THAM_CHIEU_2026-09-30.md` (luật video ref Kling/Seedance, kết quả T1–T3), `docs/CLIPAI_FEATURES.md`,
  `data/pricing.json`, `core/reference_analysis.py`, `core/research.py`, `core/voice_check.py`, `docs/TONG_KET_DU_AN_8_2026-09-28.md`.
