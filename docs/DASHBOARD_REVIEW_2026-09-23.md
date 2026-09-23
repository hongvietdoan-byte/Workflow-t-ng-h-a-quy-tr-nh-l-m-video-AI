# Rà soát tổng thể Dashboard — từ kịch bản đến clip hoàn thiện (2026-09-23)

> Người rà: Claude (Opus 5.5). Phạm vi: toàn bộ `dashboard/app.py` (3 128 dòng) + các module lõi liên quan (`core/autopilot.py`, `pipeline.py`, `llm_io.py`, `runner.py`, `autoqc`, `ffmpeg_studio.py`, prompt Director), chạy thử Dashboard với dữ liệu demo + nhà cung cấp giả lập (không tốn credit) qua trình duyệt, đối chiếu với 6 sản phẩm làm video AI trên thị trường. Bản này **chỉ ghi nhận và đề xuất, chưa sửa code**. Tiếp nối `docs/UI_AUDIT.md` (2026-09-20) — những điểm đã sửa từ đợt đó không nhắc lại.

---

## 0. Tóm tắt

**Kết luận:** Dashboard đã **phủ đủ chuỗi sản xuất** (kịch bản → Character Bible → layout → ảnh + QC → motion prompt → video → nhạc/SFX/giọng → ghép → phụ đề → xuất bản), có nhiều thứ mà công cụ thương mại không có: kho tài nguyên Free Fire chính thức, QC Agent tự chấm và tự sửa, máy trạng thái có nhật ký, sổ chi phí, giám sát lỗi âm thầm. **Điểm yếu lớn nhất không nằm ở tính năng mà ở tính nhất quán:** dữ liệu giữa các bước không "biết" nhau đã cũ, hai luồng (tự động / từng bước) cho ra kết quả khác nhau, và bước cuối để ra *một* clip hoàn chỉnh vẫn phải ghép tay.

**5 vấn đề nên sửa trước (xếp theo mức ảnh hưởng):**
1. **Không lan truyền thay đổi**: sửa cảnh / bỏ duyệt ảnh / đổi World Bible thì motion prompt, video, video cuối cũ vẫn được coi là "xong" → video sai mà không ai biết (B1).
2. **Chạy lại Director ghi đè chỉnh tay**, kể cả ô 🏞 Background đã chọn (bị đặt lại `null`) và kể cả khi Character Bible đã khóa (B2).
3. **Không có tỉ lệ khung hình ở cấp dự án**: mọi thứ gen ở 16:9; xuất 9:16 cho TikTok/Reels chỉ thu nhỏ + thêm viền đen (A7).
4. **Đầu ra cuối bị phân mảnh**: video cuối, bản phụ đề, bản đổi kích thước (lấy từ bản *không* phụ đề), card chữ cuối (chưa có nút) là 3–4 file rời (A6).
5. **Không có QC cho video**, trong khi lỗi nặng nhất của video thật (xuyên tường, biến dạng, lệch nhân vật) xuất hiện ở khâu video (C3).

**Chấm điểm nhanh (1–5, chủ quan, dựa trên code + chạy demo):**

| Khía cạnh | Điểm | Ghi chú ngắn |
|---|---|---|
| Độ phủ quy trình | **4,5** | Đủ 5 bước + nhánh phụ; thiếu card chữ cuối, tỉ lệ khung |
| Nhất quán dữ liệu giữa các bước | **2,5** | Không có cờ "lỗi thời", Director ghi đè, thiết lập render không lưu |
| Kiểm soát chất lượng | **3** | QC ảnh mạnh nhưng cấu hình rối; chưa QC video |
| Trải nghiệm người dùng | **2,5** | Nhiều chữ, ngôn từ Anh–Việt lẫn lộn, ~40% màn hình đầu là "hạ tầng" |
| Độ tin cậy vận hành | **3,5** | Máy trạng thái, retry, giám sát tốt; phụ thuộc hạn mức Claude cá nhân |
| Minh bạch chi phí | **3** | Có sổ + ước tính; giá ảnh/âm thanh vẫn trống |
| Khả năng bảo trì | **2,5** | 1 file giao diện 215 KB, đã từng trùng key widget |

---

## 1. Bản đồ luồng hiện tại

```
Bước 1  ① Kịch bản ─ 🧰 Tài nguyên ─ ② Chọn cách chạy ─┬─ 🚀 Tự động: Director → layout → ảnh+QC → motion → video → nhạc → SFX → render → phụ đề
                                                       └─ 🧭 Từng bước: ③ Director → ④ Character Bible → ⑤ Storyboard → Duyệt & khóa
                                                          (+ World Bible "tùy chọn nâng cao" ở cuối trang)
Bước 2  Tạo job → Submit/Poll → Claude tự QC (+ tự gen lại) → người duyệt
Bước 3  Claude viết motion prompt → người duyệt
Bước 4  Chọn model → Tạo job → Submit/Poll → clip
Bước 5  Clip theo thứ tự → [Preview] → Phụ đề → Nhạc nền → SFX/giọng đọc ‖ Tùy chọn render → Render Final
Ngoài luồng: card chữ cuối (ffmpeg tay), bản đổi kích thước, bản phụ đề
```

---

## 2. Phát hiện chi tiết

Mức độ: 🔴 cao (ra sai sản phẩm / mất công sức) · 🟠 trung bình (gây nhầm, tốn thao tác) · 🟡 thấp (chữ, hiển thị).

### A. Thứ tự luồng và các bước

| # | Mức | Vấn đề | Bằng chứng | Đề xuất |
|---|---|---|---|---|
| A1 | 🟠 | **World Bible (phong cách) nằm cuối Bước 1** nhưng là đầu vào của Director và Motion; lưu xong còn nhắc "chạy lại Director/Motion". Người dùng làm đúng thứ tự trên màn hình sẽ phải chạy Director 2 lần. | `app.py:1509` (gọi cuối `step1`), `app.py:946` | Đưa World Bible lên ngay sau ① Kịch bản, trước Director (gộp với 🧰 Tài nguyên thành "Chuẩn bị"). |
| A2 | 🟠 | **🧰 Tài nguyên đi kèm kịch bản không có số thứ tự**, trong khi nó quyết định ảnh tham chiếu, Background và nội dung Director. | `app.py:1422` | Đánh số và coi là bước bắt buộc xem (có thể bỏ qua) trước Director. |
| A3 | 🟠 | **Hai tính năng cùng tên "Storyboard"**: "⑤ 🎬 Dựng storyboard" (previz layout) và "📽 Chế độ Storyboard" (gửi ảnh cảnh trước làm tham chiếu) — cái sau **giấu trong expander World Bible**, mặc định tắt. Ô "Nhóm cảnh" (Director điền) chỉ có tác dụng nối ảnh khi bật chế độ này. | `app.py:901`, `app.py:1517`, `app.py:1725`, `runner.py:257-264` | Đổi tên cái sau thành "🔗 Nối ảnh cảnh trước (giữ liên tục)", để cạnh "Nhóm cảnh", bật mặc định khi Director trả `sequence`. |
| A4 | 🟡 | **Số ①–⑤ trong Bước 1 trùng với Bước 1–5** ("② Chọn cách chạy" ≠ "Bước 2"). Nút "✔ Duyệt & khóa → Bước 2" chỉ khóa, **không chuyển sang Bước 2**; nút "⏭ Sang Bước 2" ở chỗ khác thì chuyển. | `app.py:1506`, `app.py:1431` | Dùng chữ cái (1a, 1b…) hoặc bỏ số; nút khóa thì khóa + chuyển bước. |
| A5 | 🟠 | **Bước 5 sắp ngược thứ tự làm việc**: Phụ đề (cần video cuối) đứng trước Nhạc nền (cần chọn trước khi render); nút Render ở cột phải tách khỏi phần âm thanh. Nhiều chỗ vẫn ghi "Bước 5a/5b" dù 2 bước đã gộp. | `app.py:2609-2610`; chữ cũ ở `app.py:2162, 2472, 2620, 2628` | Thứ tự: Clip → Âm thanh (nhạc, SFX, giọng) → Render → Hậu kỳ (phụ đề, card cuối, xuất định dạng). Sửa chữ "5a/5b". |
| A6 | 🔴 | **Không có "một bản giao hoàn chỉnh"**: `FINAL_VIDEO.mp4` → `FINAL_VIDEO_sub_<lang>.mp4` (bản sao có phụ đề) → `FINAL_VIDEO_<W>x<H>.mp4` được tạo **từ bản không phụ đề** → card chữ cuối **không có nút**, video 46s thật đã phải ghép bằng ffmpeg tay. | `app.py:2608` (resize lấy `out`), `app.py:2968`; TODO mục chạy thật 2026-09-23 | Một "Bản giao" duy nhất: render → (phụ đề) → (card mở/đóng) → (các tỉ lệ), mỗi lớp là tùy chọn, bản đổi kích thước luôn lấy lớp mới nhất. |
| A7 | 🔴 | **Tỉ lệ khung hình không phải thiết lập của dự án**: ảnh Deepix cố định `2048x1152` (16:9), Clip AI đọc `CLIPAI_ASPECT_RATIO` từ biến môi trường; "Dọc 1080×1920" ở bước xuất chỉ **thu nhỏ + thêm viền đen** (`pad`). Nội dung FF phần lớn phát trên TikTok/Reels/Shorts. | `core/adapters/deepix.py:25`, `core/adapters/clipai.py:116`, `core/ffmpeg_studio.py:163` | Thêm "Tỉ lệ khung" (16:9 / 9:16 / 1:1) khi tạo dự án, truyền xuống kích thước ảnh, `aspect_ratio` video, layout previz và render. |
| A8 | 🟠 | **Giọng nhân vật (TTS) chỉ làm tay**: chế độ tự động không tạo giọng đọc; video thật phải tạo 14 dòng thủ công. Trong khi đó, theo blog chính thức Kling, **giọng tự sinh của Kling 3.0 Omni chỉ hỗ trợ 5 ngôn ngữ (Trung, Anh, Nhật, Hàn, Tây Ban Nha)** — *không có tiếng Việt* (cần kiểm chứng thật), nên tùy chọn "🔊 Model tự tạo lời thoại" khó là đường chính cho kịch bản tiếng Việt. | `core/autopilot.py:457` (không có phase TTS); `app.py:2277` | Gán giọng cho từng nhân vật ngay trong Character Bible; tạo TTS tự động từ thoại, xếp theo `schedule_by_cues` (đã có), chạy cả trong chế độ tự động. |

### B. Nhất quán dữ liệu và trạng thái

| # | Mức | Vấn đề | Bằng chứng | Đề xuất |
|---|---|---|---|---|
| B1 | 🔴 | **Không có cờ "lỗi thời" (stale)**. Sửa cảnh → ảnh cũ giữ nguyên; "↩ Bỏ duyệt & gen lại ảnh" → motion prompt vẫn *đã duyệt* (viết cho ảnh cũ) và video cũ vẫn *xong*; khi ảnh mới được duyệt, Bước 4 coi cảnh "sẵn sàng" với prompt cũ; video cuối vẫn là bản cũ. Hệ thống chỉ **ghi chú bằng chữ** ("Video đã làm từ ảnh này không tự đổi"). | `app.py:1740`, `app.py:2145`, `core/pipeline.py` (`reopen_approved` không đụng `motion_prompts`/video) | Mỗi sản phẩm lưu "làm từ phiên bản nào" (ảnh ← spec cảnh, motion ← ảnh, video ← ảnh+motion, final ← danh sách clip). Khác phiên bản thì hiện badge "⚠ cũ" + nút "Làm lại phần bị ảnh hưởng"; stepper không tick ✓ khi còn mục cũ. |
| B2 | 🔴 | **Chạy lại Director ghi đè mọi chỉnh tay** của cảnh (địa điểm, cỡ cảnh, prompt ảnh, blocking) và **đặt lại Background về `null`** (mẫu JSON của prompt luôn có `"location_asset": null`). "Khóa" chỉ bảo vệ nhân vật, không bảo vệ cảnh; nút Director vẫn bấm được sau khi khóa. | `core/llm_io.py:105-117`, `prompts/01_director_scene_analysis.md:27` | Đánh dấu trường người dùng đã sửa và không ghi đè (hoặc hiện bảng "Director đề xuất thay đổi" để chọn); không cho ghi `null` đè lên Background người dùng đã chọn; sau khi khóa thì hỏi trước khi chạy lại. |
| B3 | 🟠 | **Thiết lập render không được lưu** (chuyển cảnh, thời gian fade, âm lượng nhạc, giữ âm thanh gốc chỉ nằm trong phiên trình duyệt). Chế độ tự động luôn dùng `cut` + âm lượng 0,6. Mốc thời gian phụ đề cũng tính theo kiểu chuyển cảnh đang chọn trong phiên → cùng dự án có thể ra 2 kết quả khác nhau. | `app.py:2613-2621`, `core/autopilot.py:56`, `core/autopilot.py:65` | Lưu thành "Thiết lập dựng" của dự án; chế độ tự động và tay dùng chung. |
| B4 | 🟠 | **Bấm chạy tự động làm đổi cấu hình dự án mà không báo**: `operating_mode` thành `auto` vĩnh viễn và xóa "vùng chờ review". Làm tay tiếp sau đó sẽ chạy theo QC tự duyệt. | `core/autopilot.py:161-162` | Ghi rõ trong câu xác nhận, hoặc lưu cấu hình cũ và trả lại khi dừng. |
| B5 | 🟡 | **Tiến độ đếm theo 2 kiểu**: Bước 2 và 4 đếm theo *số job* ("1 / 3 hoàn thành" trong khi dự án có 8 cảnh), stepper và chế độ tự động đếm theo *số cảnh*. Trạng thái cảnh chỉ có `ready`/`needs_attention` nhưng vẫn in ra dạng `[ready]` ở mỗi dòng cảnh. | `app.py:1842`, `app.py:2333`, `app.py:1415` | Mọi thanh tiến độ tính theo cảnh (x/N cảnh); bỏ `[ready]` hoặc thay bằng trạng thái tổng hợp thật (ảnh ✓ · prompt ✓ · video ✓). |
| B6 | 🟡 | **Hai hệ danh tính**: e-mail đăng nhập và ô "👤 Tên của bạn" (`?user=`); bảng "Số video theo người dùng" ghi "tính theo tên nhập ở góc trên" kể cả khi đang dùng đăng nhập e-mail. | `app.py:3081`, `app.py:2724` | Khi đăng nhập bật chỉ dùng e-mail; sửa chú thích. |

### C. Kiểm soát chất lượng (QC)

| # | Mức | Vấn đề | Bằng chứng | Đề xuất |
|---|---|---|---|---|
| C1 | 🟠 | **Cấu hình QC quá nhiều nút và nằm 2 nơi**: chế độ (auto/human_qc), ngưỡng, số lần retry ở ⚙ dự án; mức tự loại, tự sửa bằng Claude, vùng chờ review (chỉ auto) ở Bước 2. Khi *human_qc + tự sửa* bật, mọi ảnh dưới ngưỡng đều tự gen lại → "mức tự loại" không còn tác dụng. Chú thích "Ảnh mới chỉ được gen khi bạn bấm chạy" **sai** khi tự sửa đang bật (trang tự gửi job sửa). | `app.py:735-745`, `app.py:1917-1945`, `app.py:1924` vs `app.py:1789-1792`, `core/pipeline.py:278-305` | Gộp thành 1 "Chính sách QC" với 3 mức đặt sẵn (Chặt / Cân bằng / Tiết kiệm credit) + "Tùy chỉnh"; hiện 1 câu mô tả hệ quả ("ảnh < 0,85 sẽ tự gen lại tối đa 3 lần, rồi chờ bạn"). |
| C2 | 🟠 | **Điểm tổng là trung bình 8 tiêu chí**: ảnh sai nhân vật (0,3) vẫn có thể đạt ~0,8 nhờ 7 tiêu chí còn lại cao. Nhóm lỗi nghiêm trọng nhất theo hậu kiểm là *sai nhân vật / trang phục*. | `core/pipeline.py:~279` (trung bình), `data/qc_checklist.json` v0.2 | Thêm "tiêu chí chặn cứng" (character, hands_face, grounding): dưới mức sàn riêng thì trượt bất kể điểm trung bình. |
| C3 | 🔴 | **Không có QC video, không có bước duyệt video**: `autoqc` chỉ xử lý ảnh; clip `succeeded` đi thẳng vào bản ghép. Chế độ tự động còn tự duyệt motion prompt mà không kiểm tra gì. | `core/autoqc.py`, `core/autopilot.py:315-318`, `app.py:2337-2363` | Claude xem 4–6 khung hình/clip (đã có `video_analysis.extract_frames`), chấm 3–4 tiêu chí (giữ nhân vật, vật lý/xuyên tường, khớp motion, biến dạng); thêm trạng thái "chờ duyệt video". |
| C4 | 🟠 | **Nút "↻ Retry" vẫn hiện cho clip bị risk control chặn** → gen lại nguyên prompt bị chặn, tốn credit; chế độ tự động thì cố ý *không* retry các job này. | `app.py:2349` vs `core/autopilot.py:360-362` | Job bị chặn: ẩn Retry, thay bằng "✏ Sửa prompt rồi gen lại" (mở thẳng motion prompt của cảnh). |
| C5 | 🟠 | **Chế độ tự động chỉ cho duyệt "phân cảnh thô"**: Character Bible + ảnh tham chiếu không ai xem trước khi gen hàng loạt — đúng dạng nguyên nhân gốc #4 của lần hậu kiểm (mô tả nhân vật sai lan ra mọi cảnh). | `core/autopilot.py:231-237` | Thêm 1 điểm dừng tùy chọn (mặc định bật): "Duyệt Character Bible + ảnh tham chiếu" rồi mới gen. |

### D. Giao diện và ngôn từ

| # | Mức | Vấn đề | Bằng chứng | Đề xuất |
|---|---|---|---|---|
| D1 | 🟠 | **~40% màn hình đầu là "hạ tầng"** (chạy demo 1440×900): hàng danh tính, ô tên, thanh dự án, dòng chi tiêu, banner giám sát đỏ, rồi mới đến thanh bước. Có **2 nút ⚙ giống hệt nhau** (cài đặt chung / cài đặt dự án) cách nhau 1 hàng. | Chạy demo; `app.py:618`, `app.py:779` | Gộp 1 thanh: Dự án ▾ · trạng thái · ⏸ ■ · ⚙ (một menu có 2 nhóm "Dự án này" / "Hệ thống"). Banner giám sát chuyển thành chấm đỏ trên tab 📊. |
| D2 | 🟠 | **Cùng một trạng thái có 3 cách gọi**: bảng "Đã duyệt / Chờ bạn duyệt / Lỗi", thẻ ảnh "approved / chờ duyệt / failed", bộ lọc "FAIL", Bước 4 "succeeded / failed", chế độ "human_qc", nút "cảnh READY". | Chạy demo Bước 2, 4; `app.py:1850`, `app.py:1910`, `app.py:1888` | Một từ điển nhãn tiếng Việt duy nhất cho mọi trạng thái (dùng chung trong `ui.state_badge`). |
| D3 | 🟡 | Nút chỉ có biểu tượng (✔ ✖ 🔍 ↻ ■) ở thẻ ảnh; ý nghĩa chỉ có khi rê chuột. | `app.py:2047-2069` | Thêm chữ ngắn ("Duyệt", "Loại", "Chi tiết"). |
| D4 | 🟠 | **Thao tác xóa không nhất quán**: "↺ Reset" ở Bước 1 xóa nhân vật chưa khóa + cảnh chưa có job **không hỏi lại**, trong khi xóa 1 cảnh thì phải xác nhận. | `app.py:1387-1394` vs `app.py:1741` | Dùng `confirm_all` cho Reset, nói rõ sẽ xóa gì. |
| D5 | 🟡 | **Chữ hướng dẫn lỗi thời** về Claude: World Bible "Cần ANTHROPIC_API_KEY", Nghiên cứu "Cần ANTHROPIC_API_KEY", lỗi chế độ tự động "Chưa có Claude API (ANTHROPIC_API_KEY)" — trong khi `claude_cli` cũng dùng được. World Bible và Bài học gọi `client_from_env()` trực tiếp (không bọc lỗi như `llm_client()`), lỗi cấu hình Claude có thể làm hỏng cả trang. | `app.py:912-914`, `app.py:2804-2810`, `core/autopilot.py:86` | Dùng chung `llm_client()` + `llm_label()`. |
| D6 | 🟡 | **Chế độ từng bước cần 2 cú nhấp** cho việc lẽ ra là 1 ("Tạo job" rồi "Submit + Poll"); nút "Chạy heartbeat tới khi xong" khóa cả trang trong khi đã có tự cập nhật nền. | `app.py:1888`, `1952-1959`, `2302-2316` | Một nút "▶ Gen ảnh các cảnh chưa có" (tạo + gửi, có ước tính chi phí); bỏ heartbeat chặn trang. |
| D7 | 🟡 | Preset xuất "Ngang 1558×720" lạ; mục "Tắt Dashboard" nằm cuối mọi trang. | `app.py:955`, `app.py:3118` | Bỏ/đổi preset; chuyển "Tắt" vào ⚙. |
| D8 | 🟠 | **Toàn bộ giao diện trong 1 file 215 KB / 3 128 dòng** — khó rà, dễ trùng key widget (đã gây crash Bước 5 ngày 2026-09-22). | `dashboard/app.py` | Tách theo bước (`dashboard/steps/step1.py`…) + module nhãn/trạng thái dùng chung; không đổi hành vi. |

### E. Vận hành và chi phí

| # | Mức | Vấn đề | Đề xuất |
|---|---|---|---|
| E1 | 🟠 | Giá ảnh Deepix và âm thanh vẫn `null` → chỉ số "chi phí/giây video" của báo cáo hiệu quả sẽ thiếu. | Lấy 1 hóa đơn/số dư trước–sau 1 lô nhỏ để suy ra giá thực. |
| E2 | 🟠 | Director/QC/Motion phụ thuộc `claude_cli` dùng chung hạn mức cá nhân (đã hết giữa chừng 2026-09-22). | API key riêng (đã có trong TODO) — là điều kiện để chế độ tự động đáng tin. |
| E3 | 🟡 | Banner "🔴 Giám sát: N vấn đề nghiêm trọng" hiện trên mọi trang, kể cả khi lỗi thuộc dự án khác. | Lọc theo dự án đang mở; phần còn lại để ở tab 📊. |

---

## 3. Điểm mạnh nên giữ

- **Kho tài nguyên FF chính thức** (65 nhân vật, bản đồ, ảnh in-game, mô tả skill → hình ảnh): không công cụ thương mại nào có sẵn dữ liệu IP nội bộ như vậy.
- **QC Agent tự chấm + tự sửa kèm lý do cụ thể**, so ảnh với ảnh tham chiếu: đối thủ phần lớn để người tự xem.
- **Máy trạng thái + nhật ký + thùng rác 30 ngày + lịch sử phiên bản**: truy vết được "ai duyệt gì, khi nào".
- **Sổ chi phí, ước tính trước khi chạy, trần job/ngày, tự học mức song song**: kiểm soát credit tốt hơn giao diện web của nhà cung cấp.
- **Previz 2D bằng code** (cỡ người theo phối cảnh, chân trên mặt đất): cách tiếp cận đúng cho lỗi tỉ lệ/lơ lửng.
- **Giám sát lỗi âm thầm + báo cáo chẩn đoán**, **học từ lỗi lặp lại** có người duyệt.
- Đa model (Kling / Seedance) và không bị khóa vào một nhà cung cấp.

---

## 4. So sánh với các phần mềm làm video AI khác

Thông tin đối thủ lấy từ trang chính thức / bài đánh giá năm 2026 (nguồn ở cuối), **chưa dùng thử trực tiếp**.

| Tiêu chí | **Dashboard này** | LTX Studio | Google Flow (Veo) | Higgsfield Cinema Studio | Runway | Kling web (3.0 Omni) | InVideo AI |
|---|---|---|---|---|---|---|---|
| Kịch bản → tách cảnh/shot tự động | ✅ (Director) | ✅ kịch bản → storyboard | ⚠ nhập prompt từng shot | ✅ AI Director tách shot | ⚠ qua Agent | ⚠ multi-shot trong 1 lần gen (≤15s) | ✅ tự viết kịch bản |
| Khóa nhân vật | ✅ ảnh tham chiếu + trang phục + QC | ✅ Elements | ✅ Ingredients | ✅ AI Cast | ✅ tham chiếu | ✅ Elements, tham chiếu bằng video 3–8s (cả giọng) | ❌ chủ yếu stock |
| Khóa bối cảnh | ✅ ảnh in-game + previz layout | ✅ Elements (địa điểm) | ✅ Ingredients | ✅ Cinematic Locations | ⚠ | ⚠ | ❌ |
| Storyboard / animatic trước khi tốn credit video | ⚠ tấm layout tĩnh, chưa có animatic | ✅ storyboard + animatic | ⚠ | ✅ | ⚠ | ❌ | ⚠ |
| Liên tục giữa các shot | ⚠ nối ảnh cảnh trước (ẩn, mặc định tắt) | ✅ | ✅ SceneBuilder: nối/kéo dài shot | ✅ Montage pacing | ✅ | ✅ multi-shot 1 lần gen | ❌ |
| Timeline / sửa trực quan | ❌ (danh sách clip + ô số giây) | ✅ | ✅ | ✅ Canvas | ✅ timeline trong Agent | ⚠ | ✅ |
| Thoại / khớp môi | ⚠ TTS làm tay + tiếng tự sinh (không có tiếng Việt*) | ✅ | ✅ âm thanh gốc Veo 3.1 | ✅ | ✅ lip sync | ✅ 5 ngôn ngữ | ✅ giọng AI |
| QC tự động có lý do | ✅ **ảnh** (❌ video) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Dữ liệu IP nội bộ | ✅ **kho FF** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Đa model | ✅ Kling, Seedance | ⚠ | ❌ chỉ Veo | ✅ nhiều model | ⚠ Gen-4 + đối tác | ❌ | ⚠ |
| Kiểm soát chi phí / trần | ✅ sổ, ước tính, trần | ⚠ credit | ⚠ credit | ⚠ credit | ⚠ credit | ⚠ credit | ⚠ |
| Làm việc nhóm / phân quyền | ⚠ đăng nhập e-mail không mật khẩu | ✅ | ⚠ | ✅ đồng đạo diễn | ✅ | ⚠ | ✅ |
| Xuất nhiều tỉ lệ (dọc/ngang) | ❌ chỉ viền đen | ✅ | ✅ | ✅ | ✅ tự đổi khung (Aleph) | ✅ chọn khi gen | ✅ |
| Sửa 1 phần video đã gen | ❌ gen lại cả clip | ⚠ | ✅ Extend | ⚠ | ✅ Aleph (sửa 1 khung, lan ra cả clip) | ✅ Omni Edit | ❌ |

\* Theo blog chính thức Kling, cần xác nhận bằng một lần gen thật.

**Đọc bảng:** Dashboard **thắng ở những thứ riêng của công ty** (kho IP, QC có lý do, kiểm soát credit, truy vết), **thua ở phần "dựng phim"** mà công cụ thương mại coi là cơ bản: animatic trước khi tốn credit, timeline, khớp môi, xuất nhiều tỉ lệ, sửa một phần clip. Hướng hợp lý **không phải xây lại những thứ đó**, mà là (1) bịt các lỗ nhất quán ở mục 2 và (2) lấy những năng lực nhà cung cấp *đã có qua API* (Kling multi-shot / Elements, video tham chiếu) thay vì tự làm.

---

## 5. Lộ trình đề xuất (chờ bạn chọn)

**Đợt 1 — sửa nhanh, ít rủi ro (~1–2 ngày, không tốn credit):**
1. Director không ghi đè trường đã sửa tay, không đặt Background về `null`; hỏi trước khi chạy lại sau khóa (B2).
2. Clip bị risk control: ẩn Retry, thay bằng "Sửa prompt rồi gen lại" (C4).
3. Xác nhận cho "↺ Reset"; nút "Duyệt & khóa → Bước 2" chuyển bước thật (D4, A4).
4. Lưu thiết lập render vào dự án, chế độ tự động dùng chung (B3).
5. Bản đổi kích thước lấy bản có phụ đề nếu có; sửa mọi chữ "Bước 5a/5b", chữ "ANTHROPIC_API_KEY" (A6, A5, D5).
6. Một từ điển nhãn trạng thái tiếng Việt (D2); tiến độ đếm theo cảnh (B5).

**Đợt 2 — nhất quán và chất lượng (~1–2 tuần):**
7. Cờ "⚠ cũ" lan truyền cảnh → ảnh → motion → video → video cuối + nút "làm lại phần bị ảnh hưởng" (B1).
8. Tỉ lệ khung hình ở cấp dự án (A7).
9. QC video bằng khung hình + trạng thái chờ duyệt video (C3); tiêu chí chặn cứng cho QC ảnh (C2).
10. "Chính sách QC" 3 mức đặt sẵn thay cho 6 nút rời (C1).
11. Sắp lại Bước 5: Âm thanh → Render → Hậu kỳ (phụ đề, card mở/đóng, đa tỉ lệ) → 1 "Bản giao" (A5, A6).
12. Giọng nhân vật gán trong Character Bible, TTS tự động + xếp theo thoại, chạy cả trong chế độ tự động (A8).
13. Điểm dừng "duyệt Character Bible + ảnh tham chiếu" trong chế độ tự động (C5).

**Đợt 3 — tiến gần công cụ thương mại (khi quy trình đã ổn):**
14. Animatic: ghép ảnh đã duyệt + giọng đọc + nhạc thành video nháp *trước* khi gen video → duyệt nhịp phim mà chưa tốn credit video.
15. Thử Kling 3.0 multi-shot cho mỗi "nhóm cảnh" (liền mạch hơn gen từng cảnh rời) — gắn với P1 "hồ sơ model video" trong TODO.
16. Tách `dashboard/app.py` theo bước; gọn thanh đầu trang; kiểm tra màn hình điện thoại (D1, D8).

---

## 6. Giới hạn của lần rà này

- Chạy thử bằng **dữ liệu demo + nhà cung cấp giả lập**; không gọi Deepix/Clip AI/Claude thật, không thử chế độ tự động với API thật.
- Chưa kiểm tra màn hình điện thoại và dự án > 12 cảnh.
- So sánh đối thủ dựa trên tài liệu công khai, chưa dùng thử; mục "Kling không có tiếng Việt" cần một lần gen thật để xác nhận.

## Nguồn tham khảo (đối thủ)
- LTX Studio: https://ltx.studio/blog/ltx-storyboard-generator-update · https://lumalabs.ai/news/ltx-studio-review · https://ltx.io/blog/top-ltx-studio-features
- Google Flow / Veo: https://blog.google/technology/ai/google-flow-veo-ai-filmmaking-tool/ · https://blog.google/innovation-and-ai/products/flow-video-tips/ · https://aividpipeline.com/blog/google-flow-veo-3-1-guide-2026
- Higgsfield Cinema Studio: https://higgsfield.ai/blog/cinema-studio-3 · https://higgsfield.ai/cinematic-video-generator
- Runway: https://runway.com/changelog · https://x.com/runwayml/status/2057530497597600169
- Kling 3.0 Omni: https://kling.ai/blog/kling-video-3-omni-multi-shot-native-audio-guide · https://kling.ai/blog/kling-video-3-omni-native-lip-sync-audio-guide
- Tổng quan thị trường: https://www.hedra.com/blog/best-ai-video-generators · https://mstudio.ai/insights/best-ai-video-generator-2026
