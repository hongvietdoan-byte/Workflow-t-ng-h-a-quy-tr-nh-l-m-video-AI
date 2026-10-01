# Rà soát toàn bộ Dashboard — 01/10/2026

Đầu vào: sơ đồ cây tính năng `docs/so_do/SO_DO_TINH_NANG.html` (+ `.md`, nguồn `docs/so_do/feature_map.json`), AI Development System
chấm 16 khu vực (người chấm Claude Code session, 0 USD, commit `35739fc`, 1667 test qua), rồi rà lại lần 2: đối chiếu từng tính năng
với code, CSDL thật (`data/manifest.sqlite`) và `dashboard.env` của máy chính; mọi bug dưới đây đều có **bằng chứng chạy được 0 USD**.

## 1. Tóm tắt
- **Điểm AI Dev System: trung bình 88,2/100** (26/09: 79,2 — lần đó do subagent chấm, so tương đối). Thấp nhất: Bước 1 (79), Bước 2 (79),
  Tài liệu (81, bị giới hạn vì không có test tài liệu). Cao nhất: Chẩn đoán (96), Devsys (95), Khớp môi (94).
- **3 bug thật đang tồn tại** (mục 3.1): khâu Claude "khác" luôn bị chặn khi dự án khóa ngân sách; công thức tin cậy QC sai có thể bỏ cổng
  storyboard; luật video không kiểm tỉ lệ ảnh tham chiếu.
- **Vấn đề lớn nhất không nằm ở code mà ở cấu hình máy chính:** 35/49 cờ đang BẬT, **31 cờ chưa thử thật**, trong đó 3 cờ lý do ghi rõ là
  **gây hại** (`setcheck_autofix`, `layout_to_model`, `chain_previous_auto`).
- **Giao diện:** khoảng 250 nút / ô / khối gập trên 5 bước + 11 mục menu ⚙ + 8 hộp thoại; tiền xem ở 3 chỗ; cờ chỉ bật/tắt được bằng sửa file.

## 2. Điểm 16 khu vực (AI Dev System, 6 tiêu chí — chi tiết từng khoản trừ trên web AI Dev System → "Chấm điểm AI khách quan")

| Khu vực | Điểm 01/10 | 26/09 | Chức năng /30 | Bằng chứng /20 | Test /15 | Tuân thủ /15 | Trải nghiệm /10 | Tài liệu /10 |
|---|---|---|---|---|---|---|---|---|
| Bước 1 · Kịch bản & Đạo diễn | **79** | 81 | 24 | 13 | 13 | 14 | 6 | 9 |
| Bước 2 · Ảnh + QC | **79** | 77 | 25 | 14 | 14 | 10 | 7 | 9 |
| Bước 3 · Motion & giọng | 85 | 86 | 28 | 14 | 15 | 13 | 7 | 8 |
| Bước 4 · Video + QC | 88 | 81 | 25 | 16 | 15 | 15 | 8 | 9 |
| Bước 5 · Âm thanh & xuất bản | 85 | 83 | 26 | 13 | 15 | 15 | 7 | 9 |
| Chạy tự động | 86 | 79 | 25 | 16 | 15 | 12 | 8 | 10 |
| Ngân sách & sổ chi | 88 | 79 | 22 | 20 | 15 | 15 | 7 | 9 |
| Kho tài nguyên | 88 | 79 | 27 | 18 | 15 | 13 | 6 | 9 |
| Gói bối cảnh 3D | 92 | 71 | 26 | 18 | 15 | 15 | 8 | 10 |
| Khớp môi | 94 | 69 | 28 | 18 | 15 | 15 | 10 | 8 |
| Dashboard chung | 92 | 84 | 28 | 18 | 15 | 15 | 7 | 9 |
| Kiến thức & 3 vai | 93 | 75 | 28 | 17 | 15 | 13 | 10 | 10 |
| Lõi pipeline | 90 | 86 | 25 | 19 | 15 | 15 | 8 | 8 |
| Chẩn đoán | 96 | 91 | 26 | 20 | 15 | 15 | 10 | 10 |
| Tài liệu | 81 | 69 | 28 | 20 | 3 (code giới hạn) | 15 | 8 | 7 |
| AI Dev System | 95 | 77 | 27 | 20 | 13 | 15 | 10 | 10 |

Điểm trừ lặp lại nhiều nhất: **Bằng chứng** (cờ BẬT mà chưa thử thật — 12/16 khu vực) và **Trải nghiệm** (file > 900 dòng, màn quá nhiều nút).

## 3. Lỗi tìm ra khi rà soát lần 2

### 3.1 Bug code (đã chứng minh, 0 USD)
| # | Mức | Bug | Bằng chứng | Sửa |
|---|---|---|---|---|
| B1 | 🔴 | **11 khâu Claude dòng "Claude — khác" không bao giờ chạy được khi dự án đã khóa ngân sách**: nhạc nền (brief), hiệu ứng âm thanh AI, phân tích phong cách, layout/previz, đọc ảnh nền, phụ đề, bài học, chắt lọc, đọc ảnh Kho, nghiên cứu. Khâu không có `max_tokens` riêng → mặc định 32k → ước tính xấu nhất ≈ 0,36 USD/lượt > trần cả dòng 0,20 USD/dự án. | Chạy thử CSDL tạm: duyệt ngân sách → `sfx`, `music`, `style`, `subtitles`, `layout` đều "chạm trần khâu 'Claude — khác' … lần này ≈ $0.36, trần $0.20"; `screenwriter` (đã sửa hôm nay) cho qua. Cùng gốc với 3 lỗi trước: `video_analysis` 28/09, `translate` 28/09, `screenwriter` 01/10. | Một bảng `STAGES` duy nhất (dòng ngân sách + max_tokens + effort + giá/lượt) cho mọi khâu; test quét mọi `tagged("…")` / `_run(…, "stage")` trong code: phải có trong bảng và ước tính xấu nhất < trần. `core/llm_runner.py:58`, `core/project_budget.py:59`. |
| B2 | 🔴 | **Số đo "QC đủ tin cậy" sai công thức** → cổng duyệt storyboard (trước khi chi tiền video) có thể bị tự bỏ qua. `lenient` chia cho TỔNG số ảnh, chú thích nói chia cho số ảnh người loại. | 50 ảnh, người loại 1, QC cho qua cả 50 (bỏ sót 100 % lỗi): agreement 98 %, lenient(code) 2 % → `trusted = True`. `core/effectiveness.py:85-107`; cờ `storyboard_auto_trust` đang BẬT. | `lenient = (QC qua & người loại) / (người loại)` + tối thiểu 5 ảnh bị loại; test hồi quy. |
| B3 | 🟠 | **Luật model video không kiểm tỉ lệ ảnh tham chiếu** → Seedance từ chối sau khi gửi (ảnh 3,74 ngoài 0,39–2,50). | diag 30/09 `InvalidParameter … aspect ratio 3.74`; `core/video_rules.py` không có kiểm tỉ lệ. | Thêm min/max tỉ lệ vào `data/provider_rules.json`, kiểm (hoặc đệm ảnh) trước khi gửi. |
| B4 | 🟡 | Biên kịch viết lời kêu gọi cuối video thành dòng thoại `CTA_TEXT:` → kiểm code báo "nhân vật mới — cần ảnh". | Phiếu đo thật `docs/DO_S11_2_Y_TUONG_2026-10-01.md` ý tưởng 1. | prompt 23: CTA là dòng chữ trên màn; `check_script` bỏ qua người nói dạng CTA/CHỮ/TEXT. |
| B5 | 🟡 | 6 ảnh Kho mất file (vd. A PATROA `data\assets\1\1.png`) báo lỗi ~30 lần từ 28/09 mà không có cách sửa trên giao diện. | diag `missing_asset_file`; thư mục `data/assets/1/` không tồn tại. | Sức khỏe kho: nút "gỡ liên kết / tải lại từ nguồn". |
| B6 | 🟡 | AI Dev System dò nơi dùng cờ sai: module viết `features.on(FEATURE)` bị báo "không thấy features.on(...)". | `devsys/collect.py:630-656` (vd. `director_two_pass`, `qc_team`, `project_budget`). | Dò thêm hằng `FEATURE = "…"` trong module. |

### 3.2 Cấu hình máy chính nguy hiểm (người dùng quyết — chỉ sửa `dashboard.env`)
| Cờ | Đang | Lý do cờ tự ghi | Đề xuất |
|---|---|---|---|
| `setcheck_autofix` | BẬT | "chuẩn theo số đông, sửa sai người (Kenta→Maxim) rồi **tự trả tiền gen lại**" | **TẮT** |
| `layout_to_model` | BẬT | "model chép góc máy từ trên cao và cỡ người tí hon" — diag 29–30/09: 5 ảnh đo WS khi shot xin MS/MCU | **TẮT** |
| `chain_previous_auto` | BẬT | "shot cận kéo theo bố cục toàn cảnh của shot trước" | **TẮT** (hoặc chỉ nối khi cùng cỡ cảnh) |
| 10 cờ dựng/âm thanh (`shot_transitions`, `impact_shake`, `music_breath`, `sound_intent`, `flashback_fx`, `end_hold`, `music_fit`, `ambience_bed`, `motion_trim`, `shot_color_match`) | BẬT | "chưa xem/nghe trên bản dựng thật" | Dựng 2 bản #8 có/không (0 USD) → xem → quyết từng cờ |
| Còn lại (Director, QC, video, giọng) | BẬT | chưa thử thật | Giữ cho dự án thử, nhưng autopilot chỉ nên dùng cờ đã `verified` |

### 3.3 Trạng thái ghi sai (tài liệu ≠ thật)
- `director_two_pass`, `voice_direction`, `project_budget`, `loudness_normalize`: `verified=True` nhưng lý do cờ vẫn "chưa chạy thật".
- `dialogue_take`: đã chạy thật 01/10 (S4.2, 2,82 USD, dự án #14) nhưng vẫn `verified=False`.
- TODO: "tính năng mới có cờ đều TẮT" (`TODO.md:296`, `:351`), "284 unit test pass" (`:628`) — đã lỗi thời.

## 4. Đánh giá từng khâu (ngắn)
| Khâu | Mạnh | Yếu chính | Điểm |
|---|---|---|---|
| Bước 1 Kịch bản & Đạo diễn | Director 2 lượt + chuẩn hóa shot + bàn đo bằng code; Biên kịch 4 lượt có trần | 3 cờ Director BẬT chưa đo; lỗi Director còn tiếng Anh; 6 khối gập + 3 tab + nhiều nút "🤖" riêng | 79 |
| Bước 2 Ảnh + QC | QC nhiều tầng (code đo → model → luật), storyboard Deepix, render 3D tham chiếu | Cờ gây hại đang BẬT; QC mới chưa đo trên bộ nhãn; nền render lệch (0,16–0,29) | 79 |
| Bước 3 Motion & giọng | Kiểm giọng miễn phí trên máy, animatic 0 USD | Nút TTS không có giá; `audio_first` (sửa gốc lỗi 58→83 s) chưa chạy thật | 85 |
| Bước 4 Video + QC | Đề xuất model theo cảnh, đo lớp 0, nhiều A/B chạy thật có báo cáo | Thiếu kiểm tỉ lệ ảnh; 4 cờ chia clip BẬT chưa A/B | 88 |
| Bước 5 Âm thanh & xuất bản | Dựng ffmpeg 0 USD, kiểm bản dựng như người xem, −14 LUFS | ~40 điều khiển; 10 hiệu ứng BẬT chưa duyệt; nhạc/SFX AI dính bug B1 | 85 |
| Chạy tự động | Đủ pha, dừng sạch khi chạm trần | Bug B2; tự gen lại theo QC đồng bộ | 86 |
| Ngân sách | Khóa 4 lớp chạy đúng thật | Gốc lỗi B1; âm thanh/ảnh chưa có giá USD; tiền xem ở 3 chỗ | 88 |
| Kho tài nguyên | Rất đầy đủ (thư mục, website, 3D, Meshy, âm thanh) | Một hộp thoại ~30 khối; nội dung web chưa coi là dữ liệu không tin cậy | 88 |

## 5. Đề xuất sửa, tích hợp, tối ưu — ít nút, ít gõ tay

### 5.1 Đổi cấu trúc: 5 bước → 4 màn + 1 hộp "Việc cần bạn"
Hiện người dùng phải đi qua 5 bước và bấm rải rác ~250 điều khiển. Đề xuất (code đã có gần đủ, chủ yếu là sắp lại giao diện):
1. **Kịch bản** — một ô nhập duy nhất nhận *file, văn bản dán hoặc ý tưởng thô* (tự nhận dạng: có "CẢNH n" → kịch bản; ngắn → Biên kịch).
   Thời lượng / nền tảng / look / khổ hình là 4 chip có mặc định theo dự án trước. Nút duy nhất: **"Lập kế hoạch (≈ X USD)"** = Director +
   Bible + rà thoại + người xem lần đầu + đề xuất ngân sách.
2. **Storyboard** (gộp Bước 2 + 3) — ảnh, motion, giọng, animatic chạy liền sau khi duyệt kế hoạch; người dùng chỉ xem **animatic + lưới
   khung** và duyệt / sửa bằng 1 câu từng khung. Một cổng duyệt duy nhất trước khi chi tiền video.
3. **Video** — chạy theo model đề xuất; chỉ hiện clip *cần người xem* (QC có ghi chú hoặc đo lớp 0 lỗi).
4. **Bản giao** — mặc định 1 nút **"📦 Xuất bản đầy đủ"** + 3 chip (phụ đề, card cuối, khổ phụ); mọi thiết lập dựng/nhạc/SFX vào "Tinh chỉnh".
- **Hộp "Việc cần bạn"** trên thanh trên: gom mọi thứ đang chờ người (ảnh chờ duyệt, clip chờ, ngân sách chờ khóa, cảnh báo rủi ro,
  dịch vụ hết tiền) thành một hàng đợi duyệt bằng phím (✔ / ✖ / sửa 1 câu). Thay cho việc phải mở từng bước để tìm.

### 5.2 Gom nút / tự động hóa (cụ thể)
| Hiện tại | Đề xuất | Bớt thao tác |
|---|---|---|
| ~12 nút "🤖 Claude …" riêng (chọn giọng, kiểm Bible, rà thoại, rà motion, brief nhạc, AI hiệu ứng, phân tích phong cách…) | Chạy tự động trong "Lập kế hoạch" / "Storyboard" với một ước tính tổng; nút riêng chỉ còn trong "Tinh chỉnh" | ~10 cú bấm/dự án |
| Tiền ở ⚙ Ngân sách thử, ⚙ Bảng giá, Bước 1 → 💵 Ngân sách dự án, 📊 Theo dõi | **Một thẻ "💵 Tiền"** trên thanh trên: còn lại theo dịch vụ + dự án, bấm mở chi tiết; duyệt ngân sách dự án ngay trong thẻ | 3 chỗ → 1 |
| 49 cờ sửa trong `dashboard.env` rồi mở lại | **⚙ → 🧪 Tính năng thử**: danh sách cờ, trạng thái, lý do, bằng chứng; 2 preset **Ổn định** (chỉ cờ verified) / **Thử nghiệm**; bật theo *dự án* | sửa file → 1 chọn |
| Menu ⚙ 11 mục + 8 hộp thoại | 3 nhóm: **Dự án** (chế độ duyệt, thử rẻ, nhân bản) · **Tài nguyên & kiến thức** (Kho, Kiến thức, Bài học) · **Hệ thống** (Tiền, Giới hạn, Quyền, Lịch sử) | 11 → 3 |
| Hộp Kho tài nguyên ~30 khối | 4 tab: Mục kho · Nhập & đồng bộ · 3D · Âm thanh; đặt chỗ đứng 3D bằng bấm trên ảnh (bỏ lệnh dòng lệnh) | cuộn dài → tab |
| Duyệt ảnh từng tấm, sửa câu bằng tay | Lưới khung + phím tắt; câu sửa có gợi ý sẵn từ Tổ QC (bấm chọn thay vì gõ) | gõ tay → chọn |
| Chế độ "Ai duyệt" + "Thử rẻ" + "Chuyên gia" rời rạc | 1 chọn "Mức tự động": **Tôi duyệt hết / Duyệt cổng chính / Tự chạy trong trần** | 3 → 1 |
| Ô "sửa bằng câu" chỉ có ở ảnh | **Ô lệnh chung** (như Invideo "conversational editing"): "đổi nhạc vui hơn", "shot 5 cận hơn" → hệ thống tìm khâu, báo giá, chờ bấm | dò khâu → 1 câu |

### 5.3 Sửa gốc trong code (miễn phí, làm trước)
1. B1 bảng `STAGES` chung + test quét (chặn cả lớp lỗi lặp 4 lần).
2. B2 công thức `look_trust`; B3 kiểm tỉ lệ ảnh; B4 CTA; B5 nút sửa ảnh Kho mất file; B6 dò cờ.
3. Autopilot chỉ dùng cờ `verified` trừ khi dự án bật "Thử nghiệm".
4. Đồng bộ `verified`/`why` của 6 cờ ở mục 3.3; tách lịch sử khỏi `TODO.md`; trạng thái cờ trong TODO sinh tự động từ `tools/feature_map_build.py`.
5. Tách file > 900 dòng: `runner.py` (1715), `assets.py` (1433), `autopilot.py` (1370), `llm_runner.py` (1213), `admin.py` (1019).
6. Giá USD cho TTS/nhạc/SFX (lấy `cost` ClipAI trả về) và ảnh Deepix → mọi nút có giá.

## 6. So sánh với công cụ ngoài cùng mục đích
Thông tin công cụ ngoài lấy từ trang giới thiệu / bài đánh giá 2026 (chưa tự dùng thử; giá gói khởi điểm theo nguồn, có thể đã đổi).

| Tiêu chí | **Dashboard của mình** | LTX Studio | Katalist AI | Higgsfield (Popcorn + Cinema Studio) | Runway | Invideo AI | CapCut |
|---|---|---|---|---|---|---|---|
| Kịch bản → cảnh/shot | ✅ Director 2 lượt + chuẩn hóa bằng code + bàn đo | ✅ tự tách cảnh, gợi ý khung máy | ✅ Script Assistant tách cảnh, nhân vật | ◐ | ✗ | ✅ agent hội thoại | ◐ gợi ý hình |
| Ý tưởng thô → kịch bản | ◐ Biên kịch 4 lượt (cờ TẮT, đang đo) | ◐ | ◐ | ✗ | ✗ | ✅ | ✅ |
| Nhân vật nhất quán | ✅ Bible + ảnh chuẩn Kho + chủ thể Seedance + hồ sơ bất đối xứng | ✅ Elements tự trích từ kịch bản | ✅ | ✅ Soul ID (huấn luyện danh tính) | ✅ Gen-4 References | ◐ | ✗ |
| Storyboard / animatic trước khi tốn tiền video | ✅ cổng storyboard + animatic 0 USD | ✅ storyboard-first | ✅ animatic tích hợp | ✅ | ◐ | ✗ | ✗ |
| Chọn model theo shot | ✅ model_router theo slide ClipAI | ◐ đổi model từng shot | ✅ Runway / Veo / Kling | ◐ | ✗ (model riêng) | ✅ "Agent Two" chọn model | ✗ |
| Khớp môi tiếng Việt | ◐ Seedance kèm giọng (đã chạy thật 1 nhóm) | ◐ | ◐ | ◐ (khuyên Kling 3.0) | ✅ Act-Two + voice, nhiều ngôn ngữ | ✅ AI Twins | ◐ |
| QC tự động ảnh/clip | ✅ nhiều tầng, đo bằng code | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Khóa chi phí cứng (mỗi lời gọi / khâu / dự án) | ✅ (điểm mạnh riêng) | ✗ (credit gói) | ✗ | ✗ | ✗ (credit gói) | ✗ | ✗ |
| Dựng / timeline / phụ đề | ✅ ffmpeg, phụ đề tránh mặt, −14 LUFS; chưa có timeline kéo-thả | ✅ timeline editor + nhạc, VFX, lồng tiếng | ✅ xuất sang Premiere Pro | ◐ | ✅ | ✅ VFX House | ✅ phụ đề 130+ ngôn ngữ, mạnh nhất |
| Tài nguyên riêng của game (FF) | ✅ Kho nhân vật/nơi chốn, website FF, map 3D, hồ sơ kỹ năng | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Dùng nhiều người / quyền | ✅ đăng nhập email + quyền | ✅ | ✅ | ◐ | ✅ | ✅ | ✅ |
| Độ gọn giao diện | ✗ ~250 điều khiển | ✅ | ✅ | ✅ | ✅ | ✅ hội thoại | ✅ |
| Giá | trả theo lượt API (ClipAI/Deepix/Claude) | từ ~15 USD/tháng | từ ~19 USD/tháng | từ ~9 USD/tháng | từ ~15 USD/tháng | gói tháng | miễn phí / gói |

**Kết luận so sánh**
- Mình **hơn** ở 3 điểm không công cụ nào có: QC tự động nhiều tầng đo bằng code, khóa chi phí cứng nhiều lớp, và tài nguyên riêng
  Free Fire (Kho, map 3D, hồ sơ kỹ năng). Đây là lý do nên giữ pipeline riêng thay vì chuyển hẳn sang công cụ ngoài.
- Mình **kém** ở độ gọn: các công cụ ngoài đi theo 1 luồng *storyboard-first* với ít thao tác. Đó chính là hướng của mục 5.1.
- **Nên học:** (1) LTX "Elements" — tự trích nhân vật/vật từ kịch bản thành thẻ dùng lại (mình đã có Kho, chỉ cần tự gắn khi dán
  kịch bản); (2) Katalist xuất timeline sang Premiere Pro (mình có thể xuất EDL/XML từ `ffmpeg_studio` để người dựng tinh chỉnh);
  (3) Invideo sửa bằng hội thoại → ô lệnh chung ở 5.2; (4) Runway Act-Two — chuyển diễn xuất từ video người thật sang nhân vật: hợp với
  hướng cover nhảy S11.9–S11.12; (5) CapCut phụ đề có kiểu trình bày sẵn — thêm preset kiểu phụ đề.

## 7. Thứ tự làm đề xuất
| Đợt | Việc | Tiền | Ai |
|---|---|---|---|
| 0 | Tắt 3 cờ gây hại (mục 3.2) | 0 | 👤 người dùng duyệt |
| 1 | Sửa B1–B6 + đồng bộ trạng thái cờ (mục 5.3 ý 1–4) | 0 | 💻 |
| 2 | Màn 🧪 Tính năng thử + thẻ 💵 Tiền + gom menu ⚙ | 0 | 💻 |
| 3 | Gộp 5 bước → 4 màn + hộp "Việc cần bạn" (thiết kế mockup trước, người dùng duyệt) | 0 | 💻 + 👤 duyệt mockup |
| 4 | Xem 2 bản dựng #8 có/không 10 hiệu ứng → quyết cờ | 0 | 👤 |
| 5 | Đo các cờ còn lại trong 1 dự án thử có trần (chạy nốt S11.2 trước) | 💵 hỏi trước | 👤 duyệt |

## Nguồn công cụ ngoài
- LTX Studio: [ltx.studio — Storyboard Generator](https://ltx.studio/blog/ltx-storyboard-generator-update), [Script to Video](https://ltx.io/studio/platform/script-to-video), [Dupple review](https://dupple.com/reviews/ltx-studio)
- Katalist / Higgsfield / Runway so sánh: [Higgsfield — AI previsualization tools 2026](https://higgsfield.ai/blog/ai-previsualization-tools), [Higgsfield — consistent characters](https://higgsfield.ai/blog/tools-for-consistent-ai-characters)
- Runway: [Act-Two multi-character](https://help.runwayml.com/hc/en-us/articles/41748090660499-Creating-Multi-Character-Dialogues-with-Act-Two), [Runway Gen-4 (aiwiki)](https://aiwiki.ai/wiki/runway_gen_4)
- Invideo AI: [Invideo v4.0 AI Twins](https://www.businesswire.com/news/home/20250617793841/en/Invideo-Launches-v4.0-With-AI-Twins-Letting-Anyone-Clone-Themselves-and-Their-Products-to-Create-Studio-Quality-Videos-at-Scale), [InVideo AI review 2026](https://yespress.io/products/invideo-ai)
- CapCut: [CapCut script-to-video 2026](https://www.capcut.com/resource/top-6-ai-video-generators-for-script-to-video), [CapCut AI review](https://pexo.ai/blog/capcut-ai-video-generator-review-4093)
