# Kiểm kê điều khiển Dashboard (M81) — đọc code `main` @ 3b58812b, 21/10

Thứ tự: mục 2–5 (số liệu, luồng, thuật ngữ, mã lỗi) ở trên; mục 1 (bảng đầy đủ từng điều khiển, 853 dòng) ở cuối tệp.

Phạm vi: `dashboard/steps/*.py`, `dashboard/header.py`, `dashboard/design/screens/*.py`, các màn phụ trong `dashboard/*.py` (send_preview_ui, quality_ui, reject_reason_ui, readiness_ui, video_gate_ui, end_frame_ui, continuity_ui, change_review_ui, before_run_ui, home, team_screen, limits_ui, access_ui, admin…). Bỏ `design/preview.py` (trang mẫu `?step=design`).
Cách đếm: quét AST mọi lời gọi `st.button / form_submit_button / toggle / checkbox / radio / selectbox / multiselect / slider / number_input / text_input / text_area / chat_input / file_uploader / download_button / segmented_control` + mỗi lần gọi `confirm_all(...)` (nút + hộp Có/Không) tính 1. Một dòng code = 1 điều khiển (dòng nằm trong vòng lặp vẽ nhiều lần — vd nút ✔ Duyệt trên mỗi thẻ ảnh — vẫn tính 1).
Trạng thái cờ dùng để nói "đang hiện/ẩn": `data/flag_baseline.json` (chụp 21/10): `ui_v2`, `chat_first`, `idea_to_script`, `asset_checklist`, `director_two_pass`, `two_tier_quality`, `project_budget`, `end_frames`, `video_gate`, `seedance_sample_mode`, `bg_autoqc`, `chat_prompts` (D6) = ON; `send_preview_panel`, `release_gate` = OFF. Mức tự động mặc định dự án mới = "Duyệt cổng chính" (`human_qc`, cổng Bible + storyboard).

Ký hiệu cột "Giá / xác nhận": **giá trên nút** = `cost.price_tag / llm_tag / llm_button_tag / image_button_tag / video_batch_tag / audio_tag` hoặc số USD ghép vào nhãn; **giá ở dòng ngay trên** = `st.caption("↻ Vẽ lại 1 ảnh" + retake)` đặt trước nút; **hỏi Có/Không** = `confirm_all` (2 bước); **ô tick xác nhận** = `_confirm_big_batch` ("Tôi xác nhận batch N mục này sẽ tốn credit", khi provider thật và lô ≥ `confirm_batch_at` = 10) hoặc ô "Tôi đồng ý trả ≈ N credit" (Meshy).
Cột "Ai dùng" là ước đoán theo vị trí: **người mới** = nút chính của luồng; **chuyên gia/người quen** = thẻ phụ, nút gen lại, ô sửa trường; **chuyên gia** = chỉ hiện khi bật 🧠 Chế độ chuyên gia; **quản trị** = hộp thoại ⚙/💵/Phân quyền/Kho/Nhóm.

## 2. Số liệu

| Màn | Tổng điều khiển | Nút (kể cả Có/Không, tải) | Ô nhập / chọn | Đang ẩn (chỉ UI cũ, ui_v2 tắt) | Nút TỐN TIỀN | Tốn tiền KHÔNG có giá/xác nhận | Ô thiết lập làm đổi chi phí |
|---|---|---|---|---|---|---|---|
| ① Kịch bản (step1*, before_run_ui) | 241 | 110 | 131 | 0 | 25 (*) | 3 | 3 |
| ② Storyboard · Ảnh (step2, storyboard_cards, older_take, prompt_versions, continuity, change_review, reject_reason) | 97 | 73 | 24 | 25 | 21 | 4 (2 đang ẩn) | 1 |
| ③ Storyboard · Motion & giọng (step3) | 20 | 15 | 5 | 0 | 5 | 0 | 0 |
| ④ Video (step4, quality_ui, video_gate_ui, end_frame_ui, send_preview_ui, widgets) | 54 | 40 | 14 | 0 | 19 | 1 | 4 |
| ⑤ Bản giao (step5, motion_sfx_ui) | 117 | 48 | 69 | 0 | 8 | 0 | 0 |
| ⑥ Thanh trên · ⚙ Cài đặt · 💵 · 🧪 cờ (header, shell_parts, money_days, glow_ui, limits_ui, access_ui, app, ui, common, components, chat_start) | 124 | 65 | 59 | 0 | 0 | 0 | 2 |
| ⑦ ⌂ Tất cả dự án (home, overview) | 14 | 6 | 8 | 0 | 0 | 0 | 0 |
| ⑧ 👥 Nhóm · 🧪 học việc (team_screen, trainee_ui) | 22 | 11 | 11 | 0 | 0 | 0 | 0 |
| ⑨ Hộp thoại quản trị (admin.py: Kho tài nguyên/chủ thể/3D/Meshy, Kho kiến thức, Bài học, Lịch sử, Bảng giá, Theo dõi, Phân quyền) | 164 | 71 | 93 | 0 | 8 | 0 | 1 |
| **Tổng** | **853** | **439** | **414** | **25** | **86** | **8** (6 đang hiện) | **11** |

(*) `step1_idea._paid` là MỘT dòng code nhưng vẽ 4 nút trả tiền (Lượt 1–4) → thực tế ≈ 89 nút tốn tiền. Riêng 5 màn sản xuất ①–⑤: 529 điều khiển, 78 nút tốn tiền.

**Nút / lối tốn tiền KHÔNG có giá trên nút và không hỏi lại (đang hiện):**
1. `steps/step1_box.py:418` — khung chat Kịch bản: câu gõ bị `script_chat.intent` xếp loại `chat` (câu hỏi, có "?", câu bắt đầu "bạn/tại sao/…") → **gửi Claude ngay khi Enter** (`Chat.send`), không nút, không giá (chỉ lời chào chung "chat tự do gửi ngay tới Claude (chi phí ở 💵)").
2. `steps/step1_prep.py:345` "🎬 Dựng storyboard" — `previz.plan_layouts` gọi Claude (đọc ảnh nền), không giá (chuyên gia).
3. `steps/step1_prep.py:356` "🔍 Claude rà storyboard" — `previz.review_storyboard`, không giá (chuyên gia).
4. `change_review_ui.py:40` "↻ Rà lại" — `change_review.rerun_failed` cho Tổ rà soát rà lại (Claude) sau lỗi/nạp tiền, không giá.
5. `steps/step2.py:89` "↻ Thử kiểm tra lại" — `autoqc.clear_error` → vòng tự kiểm ảnh (Claude QC) chạy lại, không giá.
6. `steps/step4.py:272` "↻ Thử kiểm tra lại" — `clear_video_error` → tự kiểm clip (Claude) chạy lại, không giá.
(Đang ẩn — chỉ UI cũ: `step2.py:458` "✖ Loại" (loại & gen lại ảnh), `step2.py:480` "↻ Gửi lại".)

**Nút tốn tiền chỉ có giá, KHÔNG hỏi lại dù chi lớn:** `step1_v2.py:166` "🤖 Lập kế hoạch (≈ USD)" (Director, lần đầu không hỏi; chạy lại khi Bible đã khóa mới hỏi), `storyboard_cards.py:439` "✔ Duyệt storyboard → gửi video" (mở cổng → chạy tự động gen TOÀN BỘ video, chỉ có giá), `step1_run.py:48` "▶ Tiếp tục · phần còn lại ≈ USD", `step5.py:1143` "📦 Xuất bản đầy đủ". `step2.py:241` "▶ Gen ảnh" và `step4.py:205` "▶ Gen video" chỉ thêm ô tick khi lô ≥ 10 mục.

**Ô thiết lập làm đổi chi tiêu về sau (không phải nút nhưng quyết định tiền):** 🎚 Mức tự động (`header.py:101`), 🧪 Thử rẻ (`header.py:484`, bị vô hiệu khi `two_tier_quality` ON), 3 ô cổng chạy tự động (`step1_run.py:212/214/216`), "Claude tự gen lại ảnh dưới ngưỡng (mỗi lần tốn credit)" (`step2.py:617`, chuyên gia), "🔊 Model tự tạo âm thanh" + "🔍 Claude kiểm tra từng clip" (`step4.py:134/139`, chuyên gia), Model / Chất lượng từng shot (`step4.py:425/444`), "Tự nghiên cứu hàng tháng" (`admin.py:1325`).

## 3. Luồng tối thiểu ra video đầu tiên từ MỘT ý tưởng (theo code, cờ như trên, mức "Duyệt cổng chính")

### 3A. Đi tay theo "nút chính" (glow / hero / bong bóng chat)
| # | Màn | Thao tác (file:dòng) | Cú bấm | Quyết định | Tiền |
|---|---|---|---|---|---|
| 1 | ⌂ | Gõ ý tưởng vào "Bắt đầu dự án mới…" + Enter (`chat_start.py:54` → `chat_flow.start_project`, tự sang Kịch bản; tên dự án = dòng đầu, khung 9:16 mặc định) | 1 | nội dung ý tưởng | 0 |
| 2 | ① | Câu ý tưởng ngắn thường bị xếp `ask` → thẻ hỏi lại: "💡 Dùng làm ý tưởng" (`step1_box.py:370`). Bỏ qua được nếu câu bắt đầu "ý tưởng…/viết kịch bản…/dàn ý…" | 1 | ý tưởng hay kịch bản | 0 |
| 3 | ① | Form ⚙ Thiết lập (`step1_idea.py:56-95`): 6 điểm then chốt BẮT BUỘC (nhân vật trong Kho, trang phục, nơi quay map+khu vực, diễn biến, cú chốt, có gameplay?) — thiếu là `idea_buildable.gate` chặn Lượt 1; 6 ô còn lại có mặc định → "💡 Bắt đầu" (`:96`) | ~6 ô + 1 | ≥ 6 | 0 |
| 4 | ① | "▶ Lượt 1: Biên kịch đọc ý tưởng + hỏi lại (≈ 0.045 USD …)" (`step1_idea.py:117`); trả lời câu hỏi (để trống = mặc định) | 1 (+0..N ô) | 0..N | $ Claude |
| 5 | ① | "▶ Lượt 2: 3 hướng" (`:138`) → chọn hướng ở radio (`:148`) | 2 | 1 (chọn hướng) | $ Claude |
| 6 | ① | "▶ Lượt 3: dàn ý theo giây" (`:166`) | 1 | — | $ Claude |
| 7 | ① | "▶ Lượt 4: viết kịch bản đầy đủ" (`:190`) | 1 | — | $ Claude (trần 0.40 USD/ý tưởng) |
| 8 | ① | "✔ Dùng kịch bản này" (`:227`) — `use_script` tạo cảnh luôn (không cần ▶ Phân tích) | 1 | duyệt kịch bản | 0 |
| 9 | ① | Bong bóng Đạo diễn: "🤖 Lập kế hoạch (≈ USD, ước tính)" (`step1_v2.py:166`, qua `step1_intake.guide_bubble`) — Director chia shot + Character Bible (2 lượt, cờ director_two_pass). Cùng chỗ có "📋 Lập bảng kê tài nguyên" (tùy chọn, $ Claude) | 1 | chi Director | $ Claude |
| 10 | ① | "✔ Duyệt & khóa → Storyboard" (`step1_v2.py:173`) — khóa Bible, tự sang màn Storyboard (ảnh mốc chưa duyệt chỉ cảnh báo). Nếu nhân vật không có ảnh chuẩn Kho & chưa có Lock → bước 11 bị chặn, phải thêm "🤖 Claude viết Lock từ ảnh" | 1 | duyệt nhân vật/Bible | 0 |
| 11 | ② | "▶ Gen ảnh các cảnh chưa có / đã cũ · ≈ USD" (`step2.py:241`); lô ≥ 10 ảnh → thêm ô "Tôi xác nhận batch…" (`common.py:176`). Có cổng đỏ (nền 3D cũ, Bible mâu thuẫn) → phải tick "Tôi đã xem, vẫn gen ảnh" hoặc sửa | 1 (+1) | chi ảnh | $ ảnh + Claude QC + D6 |
| 12 | ② | Chờ ảnh về (tự làm mới) → "✔ Duyệt tất cả (N ảnh)" + "Có, duyệt hết" ở thanh dính (`storyboard_cards.py:445`) — hoặc ✔ Duyệt từng ảnh | 2 (hoặc N) | duyệt ảnh | 0 |
| 13 | ③ | Mở tab Motion của Storyboard → "🤖 Viết motion prompt (…) · ≈ USD" (`step3.py:64`) | 2 | chi motion | $ Claude |
| 14 | ③ | "✔ Duyệt tất cả (N prompt)" + "Có" (`step3.py:85`) — `queue_videos` chỉ nhận cảnh có ảnh + motion ĐÃ duyệt | 2 | duyệt motion | 0 |
| (14b) | ③ | Nếu có thoại: "🎙 Tạo giọng cho N câu" (`step3.py:269`) → "⟳ Kiểm tra + tải về" (`:276`) → có thể "⏱ Đặt thời lượng clip theo giọng thật" (`:289`) | +2..3 | +1 | $ âm thanh |
| 15 | ④ | Sang màn Video → "▶ Gen video (N cảnh mới) · ≈ USD" (`step4.py:205`); lô ≥ 10 → ô tick xác nhận | 2 (+1) | chi video | $ video (bản nháp, two_tier) |
| 16 | ④ | Chờ clip → "✔ Duyệt tất cả (N clip)" + "Có" (`step4.py:262`) | 2 | duyệt clip | 0 |
| (16b) | ④ | Không bắt buộc: "⬆ Gen bản cao N cảnh — ≈ USD" + "Có" (`quality_ui.py:329`); bỏ qua thì bản giao bị ghi DRAFT (cảnh báo, không chặn) | +2 | +1 | $ video |
| 17 | ⑤ | Sang Bản giao → "📦 Xuất bản đầy đủ · ≈ 0.00 USD" (`step5.py:1143`) — dựng + phụ đề + card + kích thước (không có nhạc nếu chưa chọn) | 2 | xuất bản | 0 (Claude chỉ khi dịch phụ đề) |
| 18 | ⑤ | "⬇ Tải …" (`step5.py:1198`) hoặc ⌂ "⬇ Tải FINAL_VIDEO.mp4" (`home.py:291`) | 1 | — | 0 |

**Tổng 3A ≈ 27 cú bấm + ~6 ô nhập bắt buộc (≈ 33 thao tác), tối thiểu ~19 quyết định** (ý tưởng, loại, 6 điểm then chốt, hướng, duyệt kịch bản, chi Director, duyệt Bible, chi ảnh, duyệt ảnh, chi motion, duyệt motion, chi video, duyệt clip, xuất bản); có thoại +3 bấm/+1 quyết định; muốn bản cao +2/+1; lô ≥ 10 mục +2 ô tick. 6 lần bấm trả tiền Claude trước khi có ảnh đầu tiên (4 lượt Biên kịch + Director + … motion sau ảnh).

### 3B. Chạy tự động (nút "🚀 Tự động hoàn toàn", nằm trong fold "⚙ Chi tiết" khi chat_first ON)
Bước 1–8 như trên (≈ 15 thao tác) → mở "⚙ Chi tiết" (1) → "✔ Duyệt phân cảnh & chạy tự động (≈ USD)" + "Có, chạy" (`step1_run.py:246`, 2) → dừng ở cổng Bible: "✔ Đã duyệt — tiếp tục · phần còn lại ≈ USD" (`step1_run.py:48`, 1) → dừng ở cổng storyboard: sang Storyboard (1) "✔ Duyệt storyboard → gửi video · ≈ USD" (`storyboard_cards.py:439`, 1) → tự chạy motion, giọng, video + QC, nhạc/SFX, bản giao → "⬇ Tải" (1). **≈ 22 thao tác, ~13 quyết định**; trong lúc chạy dự án chuyển "QC tự duyệt theo ngưỡng" nên không phải duyệt từng ảnh/clip.

## 4. Thuật ngữ chuyên môn trên nhãn / caption / tooltip nút

| Thuật ngữ | Nơi xuất hiện (file:dòng) |
|---|---|
| Director, Biên kịch, Quay phim, Tầng A / Tầng B | `step1_v2.py:166` (help), `step1_director.py:61,63,85/89`, `step1.py:167,296`, `step1_prep.py:232,301,323`, `step1_checklist.py:65` |
| Character Bible, Character Lock, Lock, World Bible | `step1_characters.py:270,273,488,505`, `step1_run.py:212`, `step2.py:230` (help), `step1_prep.py:69`, `header.py:409` (help) |
| ảnh mốc | `step1_characters.py:312,319,323`, `step1_run.py:212`, `step1_v2.py:179,283` |
| motion prompt / Motion | `step1.py:180,182`, `step3.py:64,89,103,148`, `step4.py:110,621,635` |
| storyboard, animatic, layout | `storyboard_cards.py:439`, `step2.py:698,787`, `step1_prep.py:345,356`, `step1_run.py:216` |
| plate / nền 3D, Background, HDRI, Blender, MODEL3D_DIR | `step2.py:120` ("↻ Render lại nền 3D shot N"), `step1.py:272`, `admin.py:450,466,475`, `video_gate_ui.py:22` |
| BYĐ | `motion_sfx_ui.py:13,29`, `step5.py:474` |
| nháp / bản cao / DRAFT / 480p·720p·1080p | `quality_ui.py:292,303,329`, `step4.py:444,736`, `header.py:484` |
| multi-shot (Kling Omni), nhóm cảnh, clip nhóm, scdet | `step4.py:338,382,874`, `step4.py:689` (GROUP_CUT_BY "dò được bằng scdet"), `step1_prep.py:304` |
| Seedance, Kling, Deepix, Clip AI/ClipAI, Meshy, ElevenLabs model id (`eleven_v3`, `music_v2` qua audio_tag) | `header.py:484`, `step4.py:134,147,659`, `step3.py:204`, `step1_prep.py:274`, `step1_characters.py:122,154,190`, `admin.py:563,586` |
| Kho, Kho chủ thể, chủ thể active | `step1_refs.py:124,143`, `step1_characters.py:176,202`, `step4.py:147`, `admin.py:347,374` |
| cổng (cổng storyboard, Cổng ảnh → video, mục đỏ cổng) | `storyboard_cards.py:428`, `video_gate_ui.py:16,22,30,47`, `step2.py:230` |
| QC, chấm điểm, ngưỡng, mức sàn, vùng chờ review | `step2.py:538,601-630,839`, `step4.py:139,682`, `trainee_ui.py:167` |
| D6 (Claude viết lại prompt trước khi gửi) | trong ⓘ ước tính của "▶ Gen ảnh/Gen video" (`core/cost.py:196`) |
| Tổ rà soát | `storyboard_cards.py:333-334` (help "Duyệt lại"), `change_review_ui.py` |
| end_state / khung cuối | `step1.py:229,243`, `step3.py:152`, `end_frame_ui.py:44,59` |
| blocking, face/eyes/body/timing/listener, Mood, shot_role, sequence, video_route | `step1.py:158-261` (trình sửa cảnh: nhãn VN + tên trường tiếng Anh) |
| SFX, TTS, persona, SRT/xlsx | `step5.py:211,234,256,418,420`, `step1_characters.py:292` |
| JSON (dán tay kết quả Claude) | `step1_director.py:98`, `step2.py:538`, `step3.py:103` (chuyên gia) |
| tên cờ thô hiển thị: `asset_checklist`, `director_two_pass`, `two_tier_quality`, `lesson_judge`, `chat_first`, `idea_to_script` | `step1_checklist.py:25` ("🧪 cờ `asset_checklist`, chưa thử thật"), `step1_director.py:63`, `quality_ui.py:8`, `admin.py:1267` |
| preset Ổn định/Thử nghiệm, trần, sổ chi, đợt, Owner, credit | `header.py:682,739,860-888`, `money_days.py:17,149,170`, `step1_run.py:178-181`, `limits_ui.py:132-149` |
| CTA, trend, map + khu vực | `step1_idea.py:59,63,77` |

## 5. Chỗ hiện mã lỗi / tên exception kỹ thuật cho người dùng

| Vị trí | Hiện gì |
|---|---|
| `common.py:224-225` `act()` — **mọi** nút đi qua `act` (≈ 124 nút) | `st.error(str(e))` + `st.caption("Mã lỗi kỹ thuật: <TênException>")` (vd ValueError, SchemaError, ProviderError) |
| `video_gate_ui.py:16` | "🚧 Cổng ảnh → video: không đọc được (<Exception>: <msg>)" |
| `before_run_ui.py:13,19` | "🧭 Trước khi chạy / 🩹 Cờ sửa lỗi: không đọc được (<Exception>: …)" |
| `step1_director.py:75` | "💵 Chưa ước tính được chi phí Director (<Exception>: <msg>)" |
| `step1_run.py:137,231` | "Không tính được ngân sách / Không ước tính được chi phí chạy tự động (<Exception>: …)" |
| `step1_run.py:88,149`, `step1_v2.py:199`, `header.py:625`, `shell_parts.py:190` | "Chưa tính được …: <str(e) hoặc tên Exception>. Cách xử lý: …" |
| `step5.py:668` | "⚠ Không dựng được timeline tổng: <Exception>: <msg>" |
| `step1_intake.py:40`, `step1_chatrefs.py:19` | "⚠ Không xem trước được ảnh (<Exception>)" |
| `next_step.py:116` | băng "⚠ Không đọc được việc tiếp theo (<Exception>)" |
| `batch.image_gates` → `step2.py` dòng đỏ "Gen ảnh bị chặn: không đọc được kết quả kiểm Bible (<Exception>: …)" (`core/batch.py:119`) | tên exception trong lý do chặn |
| Thông điệp provider thô: `common.py:110,119,137` ("Clip AI: <e>", "Deepix … : <e>", "Claude: <e>"), `step3.py:247`/`step5.py:81` ("Clip AI audio: <e>"), `step1_characters.py:165`, `step4.py:586` (error_message kiểm duyệt nội dung của provider), `step5.py:221,558,616` | chuỗi lỗi gốc của nhà cung cấp |
| `admin.py:1242` (📊 Theo dõi › Chẩn đoán) | bảng sự kiện chẩn đoán có cột **mã** (`diag_events.code`, vd `change_review_hold`, `plate_stale`, `stale_code`) |
| `header.py:1169-1172`, `:1237-1241`, `_other_ports_stale` (`header.py:1263`) | "Code đã đổi sau khi Dashboard khởi động (`core/xxx.py`)" + băng sha/cổng 8503/8504 (cờ stale_code_alarm) — tên file code |
| `prompt_versions_ui.py:50-52`, `common.py:296-299` | in nguyên `diag_events.message` (mã `prop_reference_dropped`, FALLBACK_CODE) |
| `storyboard_cards.py:182` | "Lý do gen lại: <retry_reason>" (chuỗi nội bộ của runner/QC) |

## 1. Bảng điều khiển theo màn

### ① Kịch bản — 241 điều khiển

| file:dòng | Nhãn | Loại | Việc làm | Tiền | Giá / xác nhận | Ai dùng | Điều kiện hiện |
|---|---|---|---|---|---|---|---|
| before_run_ui.py:30 | 🩹 Bật các cờ sửa lỗi ({len(free)}, 0 USD) | nút | (_fix_flag_controls) | 0 USD | — | chuyên gia/người quen | _fix_flag_controls |
| before_run_ui.py:39 | Cờ | hộp chọn | Chọn: Cờ | 0 USD | — | chuyên gia/người quen | _fix_flag_controls |
| before_run_ui.py:40 | Lý do bỏ qua (bắt buộc) | ô chữ | Nhập: Lý do bỏ qua (bắt buộc) | 0 USD | — | chuyên gia/người quen | _fix_flag_controls |
| before_run_ui.py:41 | Bỏ qua có lý do | nút | (_fix_flag_controls) | 0 USD | — | chuyên gia/người quen | _fix_flag_controls |
| steps/step1.py:77 | Kịch bản | tải tệp | Tải tệp lên | 0 USD | — | chuyên gia/người quen | script_input |
| steps/step1.py:82 | Gõ hoặc dán kịch bản | ô chữ lớn | Nhập: Gõ hoặc dán kịch bản | 0 USD | — | chuyên gia/người quen | script_input |
| steps/step1.py:91 | ▶ Phân tích (tách cảnh) | nút | Tách cảnh | 0 USD | — | chuyên gia/người quen | script_input · xám khi: not has_input |
| steps/step1.py:115 | ↺ Làm lại (tách kịch bản lại) | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | chuyên gia/người quen | reset_script_button |
| steps/step1.py:158 | Cường độ | hộp chọn | Chọn: Cường độ | 0 USD | — | chuyên gia/người quen | _acting_inputs |
| steps/step1.py:160 | Mặt (face) | ô chữ | Nhập: Mặt (face) | 0 USD | — | chuyên gia/người quen | _acting_inputs |
| steps/step1.py:161 | Mắt (eyes) | ô chữ | Nhập: Mắt (eyes) | 0 USD | — | chuyên gia/người quen | _acting_inputs |
| steps/step1.py:163 | Người (body) | ô chữ | Nhập: Người (body) | 0 USD | — | chuyên gia/người quen | _acting_inputs |
| steps/step1.py:164 | Nhịp (timing) | ô chữ | Nhập: Nhịp (timing) | 0 USD | — | chuyên gia/người quen | _acting_inputs |
| steps/step1.py:165 | Người nghe (listener) | ô chữ | Nhập: Người nghe (listener) | 0 USD | — | chuyên gia/người quen | _acting_inputs |
| steps/step1.py:166 | Động cơ (vì sao — tiếng Việt) | ô chữ | Nhập: Động cơ (vì sao — tiếng Việt) | 0 USD | — | chuyên gia/người quen | _acting_inputs |
| steps/step1.py:167 | 🎥 Vì sao chọn góc/chuyển động này (Quay phim)" + lk("why") | ô chữ | Nhập: 🎥 Vì sao chọn góc/chuyển động này (Quay phim)" + l… | 0 USD | — | chuyên gia/người quen | _acting_inputs |
| steps/step1.py:180 | 🎬 Motion prompt (cùng ô ở Storyboard › Motion)" + (" · ✔ đã duyệt" if … | ô chữ lớn | Nhập: 🎬 Motion prompt (cùng ô ở Storyboard › Motion)" + … | 0 USD | — | chuyên gia/người quen | motion_box |
| steps/step1.py:182 | 💾 Lưu motion prompt | nút | Lưu motion prompt | 0 USD | — | chuyên gia/người quen | motion_box · xám khi: new == row["motion_prompt"] |
| steps/step1.py:198 | Nội dung kịch bản của cảnh | ô chữ lớn | Nhập: Nội dung kịch bản của cảnh | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:200 | Địa điểm" + lk("location") | ô chữ | Nhập: Địa điểm" + lk("location") | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:201 | Thời gian" + lk("time") | ô chữ | Nhập: Thời gian" + lk("time") | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:202 | Cỡ cảnh / góc máy" + lk("shot") | ô chữ | Nhập: Cỡ cảnh / góc máy" + lk("shot") | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:210 | label + lk(key) | hộp chọn | Chọn: label + lk(key) | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:214 | 🎬 Đường gen video" + lk("video_route") | hộp chọn | Chọn: 🎬 Đường gen video" + lk("video_route") | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:224 | ✨ Chuyển cảnh vào shot" + lk("transition_in") | hộp chọn | Chọn: ✨ Chuyển cảnh vào shot" + lk("transition_in") | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:227 | 📳 Rung khung khi vào shot" + lk("shake_in") | ô tick | Bật/tắt: 📳 Rung khung khi vào shot" + lk("shake_in") | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:229 | 🔗 Clip bắt đầu từ khung cuối clip của shot trước" + lk("start_from_pre… | ô tick | Bật/tắt: 🔗 Clip bắt đầu từ khung cuối clip của shot trước" … | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:233 | Mood" + lk("mood") | ô chữ | Nhập: Mood" + lk("mood") | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:234 | Ánh sáng" + lk("lighting") | ô chữ | Nhập: Ánh sáng" + lk("lighting") | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:235 | 💡 Ý đồ cảm xúc (người xem phải cảm thấy gì)" + lk("emotional_intent") | ô chữ | Nhập: 💡 Ý đồ cảm xúc (người xem phải cảm thấy gì)" + lk(… | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:237 | Nhân vật trong cảnh" + lk("characters") | chọn nhiều | Chọn: Nhân vật trong cảnh" + lk("characters") | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:240 | 🧍 Vị trí nhân vật (blocking)" + lk("blocking") | ô chữ | Nhập: 🧍 Vị trí nhân vật (blocking)" + lk("blocking") | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:243 | 🏁 Trạng thái cuối shot (khung cuối)" + lk("end_state") | ô chữ | Nhập: 🏁 Trạng thái cuối shot (khung cuối)" + lk("end_sta… | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:247 | Nhóm cảnh" + lk("sequence") | ô số | Nhập: Nhóm cảnh" + lk("sequence") | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:251 | Độ phức tạp máy/hành động" + lk("camera_complexity") | hộp chọn | Chọn: Độ phức tạp máy/hành động" + lk("camera_complexity… | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:256 | Vai trò cảnh" + lk("shot_role") | hộp chọn | Chọn: Vai trò cảnh" + lk("shot_role") | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:261 | Thời lượng đề xuất (giây)" + lk("duration_s") | ô số | Nhập: Thời lượng đề xuất (giây)" + lk("duration_s") | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:272 | 🏞 Background (ảnh in-game gửi kèm khi gen ảnh)" + lk("location_asset") | hộp chọn | Chọn: 🏞 Background (ảnh in-game gửi kèm khi gen ảnh)" + … | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:292 | Prompt ảnh" + lk("image_prompt") | ô chữ lớn | Nhập: Prompt ảnh" + lk("image_prompt") | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:296 | 🔓 Cho Director điền lại các trường 🔒 của cảnh này | nút | Mở khóa trường cảnh | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:301 | 💾 Lưu cảnh | nút | Lưu trường cảnh | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:335 | 🗑 Xóa cảnh này | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | chuyên gia/người quen | scene_editor |
| steps/step1.py:346 | ✏ Mở trình sửa của cảnh này | công tắc | Bật/tắt: ✏ Mở trình sửa của cảnh này | 0 USD | — | chuyên gia/người quen | scene_editor_box |
| steps/step1.py:367 | Chọn shot | chọn nhiều | Chọn: Chọn shot | 0 USD | — | chuyên gia | bulk_editor |
| steps/step1.py:376 | 🎬 Đường gen video | hộp chọn | Chọn: 🎬 Đường gen video | 0 USD | — | chuyên gia | bulk_editor |
| steps/step1.py:377 | ✨ Chuyển cảnh vào | hộp chọn | Chọn: ✨ Chuyển cảnh vào | 0 USD | — | chuyên gia | bulk_editor |
| steps/step1.py:379 | 📳 Rung khi vào | hộp chọn | Chọn: 📳 Rung khi vào | 0 USD | — | chuyên gia | bulk_editor |
| steps/step1.py:380 | 🔗 Nối clip shot trước | hộp chọn | Chọn: 🔗 Nối clip shot trước | 0 USD | — | chuyên gia | bulk_editor |
| steps/step1.py:383 | ✔ Áp cho {len(pick)} shot | nút | Sửa hàng loạt shot | 0 USD | — | chuyên gia | bulk_editor · xám khi: not (pick and fields) |
| steps/step1.py:418 | 🔗 Nối ảnh cảnh trước (giữ liên tục ánh sáng/vị trí khi gen ảnh) | radio | Chọn: 🔗 Nối ảnh cảnh trước (giữ liên tục ánh sáng/vị trí… | 0 USD | — | chuyên gia/người quen | scene_list |
| steps/step1.py:493 | ➕ Thêm cảnh | nút | Thêm cảnh | 0 USD | — | chuyên gia/người quen | scene_list |
| steps/step1_box.py:125 | ✍ Có, viết bổ sung chi tiết | nút | (sparse_offer) | 0 USD | — | chuyên gia/người quen | sparse_offer |
| steps/step1_box.py:126 | Không, giữ nguyên | nút | (sparse_offer) | 0 USD | — | chuyên gia/người quen | sparse_offer |
| steps/step1_box.py:293 | 📜 Đây là kịch bản | nút | Người chọn: chữ là kịch bản | 0 USD | — | người mới | _verdict |
| steps/step1_box.py:294 | 💡 Đây là ý tưởng | nút | Người chọn: chữ là ý tưởng | 0 USD | — | người mới | _verdict |
| steps/step1_box.py:300 | không phải, đây là " + ("ý tưởng" if other == "idea" else "kịch bản") | nút | Đổi cách hiểu kịch bản ↔ ý tưởng | 0 USD | — | người mới | _verdict |
| steps/step1_box.py:345 | Thay | nút | (_cards) | 0 USD | — | chuyên gia/người quen | _cards |
| steps/step1_box.py:348 | Hủy | nút | (_cards) | 0 USD | — | chuyên gia/người quen | _cards |
| steps/step1_box.py:354 | label | nút | (_cards) | 0 USD | — | chuyên gia/người quen | _cards |
| steps/step1_box.py:357 | Hủy | nút | (_cards) | 0 USD | — | chuyên gia/người quen | _cards |
| steps/step1_box.py:370 | 💡 Dùng làm ý tưởng | nút | Coi câu vừa gõ là ý tưởng | 0 USD | — | người mới | _chat_ask |
| steps/step1_box.py:373 | 💬 Hỏi Claude · ≈ ${est:.2f} | nút | Gửi câu không rõ ý cho Claude trả lời | $ Claude | giá trên nút | người mới | _chat_ask |
| steps/step1_box.py:377 | 📜 Đây là kịch bản | nút | Coi câu vừa gõ là kịch bản | 0 USD | — | người mới | _chat_ask |
| steps/step1_box.py:380 | Hủy | nút | (_chat_ask) | 0 USD | — | chuyên gia/người quen | _chat_ask |
| steps/step1_box.py:418 | Dán kịch bản, gõ ý tưởng, hỏi Claude, hoặc thả ảnh · video · nhạc · fi… | khung chat | Khung chat duy nhất: dán kịch bản / gõ ý tưởng / hỏi Claude / thả file | $ Claude (khi câu gõ bị xếp loại 'chat') | KHÔNG | người mới | luôn (cờ chat_first ON: nhận cả ảnh/video/nhạc) |
| steps/step1_box.py:502 | ✕ Bỏ file này | nút | (script_box) | 0 USD | — | chuyên gia/người quen | script_box |
| steps/step1_box.py:523 | ✕ Bỏ lời này | nút | (script_box) | 0 USD | — | chuyên gia/người quen | script_box |
| steps/step1_box.py:524 | ↪ Không, đây là ý tưởng mới | nút | (script_box) | 0 USD | — | chuyên gia/người quen | script_box |
| steps/step1_box.py:528 | ✕ Đã hiểu | nút | (script_box) | 0 USD | — | chuyên gia/người quen | script_box |
| steps/step1_box.py:547 | ▶ Phân tích (tách cảnh) · 0 USD | nút | Tách kịch bản thành cảnh bằng code | 0 USD | — | người mới | có chữ/file được hiểu là kịch bản; cờ chat_first ON + chưa có cảnh → tự tách khi gửi, không cần bấm |
| steps/step1_box.py:595 | ↩ Hoàn tác · 0 USD | nút | Hoàn tác đề xuất thoại | 0 USD | — | chuyên gia/người quen | _messages |
| steps/step1_characters.py:38 | Ảnh tham chiếu lấy từ | hộp chọn | Chọn: Ảnh tham chiếu lấy từ | 0 USD | — | chuyên gia/người quen | character_reference_panel |
| steps/step1_characters.py:49 | Dùng ảnh số (chọn 1-2 ảnh rõ mặt, nhiều góc/chi tiết thì càng chuẩn) | chọn nhiều | Chọn: Dùng ảnh số (chọn 1-2 ảnh rõ mặt, nhiều góc/chi ti… | 0 USD | — | chuyên gia/người quen | character_reference_panel |
| steps/step1_characters.py:76 | 🔫 Súng khóa cho nhân vật | hộp chọn | Chọn: 🔫 Súng khóa cho nhân vật | 0 USD | — | chuyên gia/người quen | weapon_select |
| steps/step1_characters.py:111 | Ảnh trang phục | chọn nhiều | Chọn: Ảnh trang phục | 0 USD | — | chuyên gia/người quen | outfit_panel |
| steps/step1_characters.py:117 | 💾 Lưu trang phục | nút | (outfit_panel) | 0 USD | — | chuyên gia/người quen | outfit_panel |
| steps/step1_characters.py:122 | 🧍 Tạo bộ ảnh nhân vật mặc trang phục này (2 ảnh Deepix)" + cost.image_… | nút | (outfit_panel) | $ ảnh (2 ảnh Deepix) | giá trên nút | chuyên gia/người quen | outfit_panel · xám khi: runner is None |
| steps/step1_characters.py:140 | Game / loại nội dung của dự án | hộp chọn | Chọn: Game / loại nội dung của dự án | 0 USD | — | chuyên gia/người quen | subject_panel |
| steps/step1_characters.py:152 | Mã ngắn (vd AOV, MV_CA_SI) | ô chữ | Nhập: Mã ngắn (vd AOV, MV_CA_SI) | 0 USD | — | chuyên gia/người quen | subject_panel |
| steps/step1_characters.py:153 | Tên hiển thị | ô chữ | Nhập: Tên hiển thị | 0 USD | — | chuyên gia/người quen | subject_panel |
| steps/step1_characters.py:154 | Đã ký thỏa thuận bản quyền với Clip AI | ô tick | Bật/tắt: Đã ký thỏa thuận bản quyền với Clip AI | 0 USD | — | chuyên gia/người quen | subject_panel |
| steps/step1_characters.py:156 | Thêm | nút | (subject_panel) | 0 USD | — | chuyên gia/người quen | subject_panel · xám khi: not (g_key.strip() and g_label.strip()) |
| steps/step1_characters.py:170 | Nhân vật | hộp chọn | Chọn: Nhân vật | 0 USD | — | chuyên gia/người quen | subject_panel |
| steps/step1_characters.py:171 | Ảnh nhân vật (JPG / PNG / WebP) | tải tệp | Tải tệp lên | 0 USD | — | chuyên gia/người quen | subject_panel |
| steps/step1_characters.py:174 | Tên trên kho | ô chữ | Nhập: Tên trên kho | 0 USD | — | chuyên gia/người quen | subject_panel |
| steps/step1_characters.py:176 | ⬆ Tải lên kho chủ thể | nút | Gắn chủ thể Kho | 0 USD | — | chuyên gia/người quen | subject_panel · xám khi: up is None |
| steps/step1_characters.py:187 | ⟳ Cập nhật trạng thái | nút | Hỏi trạng thái + tải kết quả | 0 USD | — | chuyên gia/người quen | subject_panel |
| steps/step1_characters.py:190 | Gỡ liên kết | nút | (subject_panel) | 0 USD | — | chuyên gia/người quen | subject_panel |
| steps/step1_characters.py:202 | Chủ thể trên kho | hộp chọn | Chọn: Chủ thể trên kho | 0 USD | — | chuyên gia/người quen | subject_panel |
| steps/step1_characters.py:204 | Gắn cho {who} | nút | Gắn chủ thể Kho | 0 USD | — | chuyên gia/người quen | subject_panel |
| steps/step1_characters.py:230 | 🔈 Nghe thử câu mẫu tiếng Việt" + budget.audio_tag(p.conn, 1, "eleven_v… | nút | (voice_preview_row) | $ âm thanh (ElevenLabs/ClipAI) | giá trên nút | chuyên gia/người quen | voice_preview_row |
| steps/step1_characters.py:266 | Bắt buộc giữ | ô chữ lớn | Nhập: Bắt buộc giữ | 0 USD | — | chuyên gia/người quen | character_detail_panel · xám khi: locked |
| steps/step1_characters.py:267 | Được đổi giữa các cảnh | ô chữ | Nhập: Được đổi giữa các cảnh | 0 USD | — | chuyên gia/người quen | character_detail_panel · xám khi: locked |
| steps/step1_characters.py:268 | Cấm lệch | ô chữ lớn | Nhập: Cấm lệch | 0 USD | — | chuyên gia/người quen | character_detail_panel · xám khi: locked |
| steps/step1_characters.py:270 | 💾 Lưu Lock | nút | Lưu Character Lock | 0 USD | — | chuyên gia/người quen | character_detail_panel · xám khi: locked |
| steps/step1_characters.py:273 | 🤖 Claude viết Lock từ ảnh" + cost.llm_button_tag(p.conn, "director", 1… | nút | (character_detail_panel) | $ Claude | giá trên nút | chuyên gia/người quen | character_detail_panel · xám khi: locked or client is None |
| steps/step1_characters.py:290 | Giọng | hộp chọn | Chọn: Giọng | 0 USD | — | chuyên gia/người quen | character_detail_panel |
| steps/step1_characters.py:292 | Cách nói (persona) | ô chữ | Nhập: Cách nói (persona) | 0 USD | — | chuyên gia/người quen | character_detail_panel |
| steps/step1_characters.py:295 | Tốc độ đọc | ô số | Nhập: Tốc độ đọc | 0 USD | — | chuyên gia/người quen | character_detail_panel |
| steps/step1_characters.py:300 | 💾 Lưu giọng | nút | Lưu hồ sơ | 0 USD | — | chuyên gia/người quen | character_detail_panel |
| steps/step1_characters.py:312 | ↩ Bỏ duyệt ảnh mốc | nút | (character_detail_panel) | 0 USD | — | chuyên gia/người quen | character_detail_panel |
| steps/step1_characters.py:319 | Vẫn vẽ theo mô tả chữ — bỏ qua ảnh mốc | nút | (character_detail_panel) | 0 USD | — | chuyên gia/người quen | character_detail_panel |
| steps/step1_characters.py:323 | ✔ Ảnh tham chiếu ở trên là đúng — duyệt ảnh mốc | nút | (character_detail_panel) | 0 USD | — | chuyên gia/người quen | character_detail_panel |
| steps/step1_characters.py:368 | 🎙 Gắn giọng theo luật cho {len(todo)} vai (0 USD, data/voices_vi.json) | nút | Áp đề xuất | 0 USD | — | chuyên gia/người quen | voice_rule_box |
| steps/step1_characters.py:399 | ✖ Cờ này sai — bỏ | nút | (bible_check_box) | 0 USD | — | chuyên gia/người quen | bible_check_box |
| steps/step1_characters.py:410 | ✔ Dùng đề xuất này | nút | Sửa nhân vật | 0 USD | — | chuyên gia/người quen | bible_check_box |
| steps/step1_characters.py:413 | 🔍 Kiểm mô tả nhân vật với ảnh tài nguyên (1 lượt Claude, chỉ nhân vật … | nút | (bible_check_box) | $ Claude | giá trên nút | chuyên gia/người quen | bible_check_box |
| steps/step1_characters.py:473 | 🤖 Claude chọn giọng cho {len(no_voice)} nhân vật có thoại" + cost.llm_… | nút | (character_bible_panel) | $ Claude | giá trên nút | chuyên gia/người quen | character_bible_panel |
| steps/step1_characters.py:488 | 🔓 Mở khóa để sửa | nút | (character_bible_panel) | 0 USD | — | chuyên gia/người quen | character_bible_panel |
| steps/step1_characters.py:492 | Chọn mục cần sửa | hộp chọn | Chọn: Chọn mục cần sửa | 0 USD | — | chuyên gia/người quen | character_bible_panel |
| steps/step1_characters.py:494 | Tên | ô chữ | Nhập: Tên | 0 USD | — | chuyên gia/người quen | character_bible_panel |
| steps/step1_characters.py:495 | Mô tả | ô chữ lớn | Nhập: Mô tả | 0 USD | — | chuyên gia/người quen | character_bible_panel |
| steps/step1_characters.py:496 | Trang phục / dấu hiệu | ô chữ | Nhập: Trang phục / dấu hiệu | 0 USD | — | chuyên gia/người quen | character_bible_panel |
| steps/step1_characters.py:497 | Lưu | nút | Sửa nhân vật | 0 USD | — | chuyên gia/người quen | character_bible_panel |
| steps/step1_characters.py:502 | Tên | ô chữ | Nhập: Tên | 0 USD | — | chuyên gia/người quen | character_bible_panel |
| steps/step1_characters.py:503 | Mô tả ngoại hình | ô chữ lớn | Nhập: Mô tả ngoại hình | 0 USD | — | chuyên gia/người quen | character_bible_panel |
| steps/step1_characters.py:504 | Trang phục / dấu hiệu (tùy chọn) | ô chữ | Nhập: Trang phục / dấu hiệu (tùy chọn) | 0 USD | — | chuyên gia/người quen | character_bible_panel |
| steps/step1_characters.py:505 | Thêm vào Character Bible | nút | (character_bible_panel) | 0 USD | — | chuyên gia/người quen | character_bible_panel · xám khi: not (a_name.strip() and a_desc.strip()) |
| steps/step1_chatrefs.py:65 | 🗑 | nút | (ref_list) | 0 USD | — | chuyên gia/người quen | ref_list |
| steps/step1_chatrefs.py:83 | Hủy | nút | (ref_cards) | 0 USD | — | chuyên gia/người quen | ref_cards |
| steps/step1_chatrefs.py:87 | Nhãn (tên bối cảnh / đồ vật / nhân vật / video) | ô chữ | Nhập: Nhãn (tên bối cảnh / đồ vật / nhân vật / video) | 0 USD | — | chuyên gia/người quen | ref_cards |
| steps/step1_chatrefs.py:91 | page_label(p.conn) | nút | (ref_cards) | $ Claude (đọc chữ trên ảnh) | giá trên nút | chuyên gia/người quen | ref_cards |
| steps/step1_chatrefs.py:95 | lab | nút | (ref_cards) | 0 USD | — | chuyên gia/người quen | ref_cards |
| steps/step1_chatrefs.py:97 | Hủy | nút | (ref_cards) | 0 USD | — | chuyên gia/người quen | ref_cards |
| steps/step1_chatrefs.py:100 | 🎬 Video tham khảo | nút | (ref_cards) | 0 USD | — | chuyên gia/người quen | ref_cards |
| steps/step1_chatrefs.py:102 | Hủy | nút | (ref_cards) | 0 USD | — | chuyên gia/người quen | ref_cards |
| steps/step1_checklist.py:28 | ("📋 Lập bảng kê tài nguyên" if res is None else "↻ Lập lại bảng kê") +… | nút | (checklist_panel) | $ Claude | giá trên nút | người mới | cờ asset_checklist (ON) — hiện ngay trong hero lúc kind=plan |
| steps/step1_checklist.py:55 | Xác nhận | nút | (checklist_panel) | 0 USD | — | chuyên gia/người quen | checklist_panel |
| steps/step1_checklist.py:58 | Thu hồi | nút | Thu hồi | 0 USD | — | chuyên gia/người quen | checklist_panel |
| steps/step1_checklist.py:65 | Gắn | nút | Gắn tài nguyên | 0 USD | — | chuyên gia/người quen | checklist_panel |
| steps/step1_director.py:78 | label | nút | (director_panel) | $ Claude (Director) | giá trên nút | chuyên gia/người quen | director_panel · xám khi: True |
| steps/step1_director.py:80 | 🤖 Chạy Director … (chạy lại) · Claude ≈ USD | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | $ Claude (Director chạy lại) | giá trên nút, hỏi Có/Không | chuyên gia/người quen | director_panel |
| steps/step1_director.py:83 | label | nút | (director_panel) | $ Claude (Director) | giá trên nút | chuyên gia/người quen | director_panel |
| steps/step1_director.py:85 | ↻ Chỉ hỏi lại {len(pending)} cảnh lỗi (cảnh {', '.join(map(str, pendin… | nút | (director_panel) | $ Claude | giá trên nút | chuyên gia/người quen | director_panel · xám khi: bool(running) |
| steps/step1_director.py:98 | Dán JSON kết quả từ Claude | ô chữ lớn | Nhập: Dán JSON kết quả từ Claude | 0 USD | — | chuyên gia | director_panel |
| steps/step1_director.py:99 | Lưu phân tích | nút | Lưu JSON Director dán tay | 0 USD | — | chuyên gia/người quen | director_panel · xám khi: not raw.strip() |
| steps/step1_director.py:134 | ⏱ Tự tăng thời lượng {len(fixable)} clip cho vừa thoại | nút | Tăng thời lượng clip | 0 USD | — | chuyên gia/người quen | dialogue_review_panel |
| steps/step1_director.py:138 | 🤖 Claude rà thoại (6 lỗi thoại + độ dài)" + cost.llm_button_tag(p.conn… | nút | (dialogue_review_panel) | $ Claude | giá trên nút | chuyên gia/người quen | dialogue_review_panel · xám khi: client is None |
| steps/step1_director.py:149 | Đề xuất | ô chữ | Nhập: Đề xuất | 0 USD | — | chuyên gia/người quen | dialogue_review_panel |
| steps/step1_director.py:150 | Áp dụng câu này | nút | Áp câu thoại đề xuất | 0 USD | — | chuyên gia/người quen | dialogue_review_panel |
| steps/step1_director.py:173 | ↻ Chia shot lại cảnh này" + cost.llm_button_tag(p.conn, "director", 1) | nút | (_replan_button) | $ Claude | giá trên nút | chuyên gia/người quen | _replan_button · xám khi: bool(running) |
| steps/step1_idea.py:34 | {label} (≈ {I.TURN_USD:g} USD · còn {left:.2f} / {I.RUN_CAP_USD:g} USD… | nút | Lượt Biên kịch: 1 hỏi lại · 2 ba hướng · 3 dàn ý · 4 viết kịch bản | $ Claude (4 lượt Biên kịch: dùng chung hàm _paid ở dòng 117/138/166/190) | giá trên nút | người mới | cờ idea_to_script; sau 💡 Bắt đầu |
| steps/step1_idea.py:56 | Thời lượng (s) | hộp chọn | Chọn: Thời lượng (s) | 0 USD | — | chuyên gia/người quen | idea_settings_form |
| steps/step1_idea.py:57 | Khung | hộp chọn | Chọn: Khung | 0 USD | — | chuyên gia/người quen | idea_settings_form |
| steps/step1_idea.py:58 | Nền tảng | hộp chọn | Chọn: Nền tảng | 0 USD | — | chuyên gia/người quen | idea_settings_form |
| steps/step1_idea.py:59 | Dùng trend | hộp chọn | Chọn: Dùng trend | 0 USD | — | chuyên gia/người quen | idea_settings_form |
| steps/step1_idea.py:62 | Giọng điệu | ô chữ | Nhập: Giọng điệu | 0 USD | — | chuyên gia/người quen | idea_settings_form |
| steps/step1_idea.py:63 | CTA (đúng chữ, cảnh cuối) | ô chữ | Nhập: CTA (đúng chữ, cảnh cuối) | 0 USD | — | chuyên gia/người quen | idea_settings_form |
| steps/step1_idea.py:74 | Nhân vật (chỉ nhân vật có ảnh chuẩn trong Kho) | chọn nhiều | Chọn: Nhân vật (chỉ nhân vật có ảnh chuẩn trong Kho) | 0 USD | — | chuyên gia/người quen | idea_settings_form |
| steps/step1_idea.py:75 | Trang phục | ô chữ | Nhập: Trang phục | 0 USD | — | chuyên gia/người quen | idea_settings_form |
| steps/step1_idea.py:77 | Nơi quay (map có 3D / nền trong Kho) | hộp chọn | Chọn: Nơi quay (map có 3D / nền trong Kho) | 0 USD | — | chuyên gia/người quen | idea_settings_form |
| steps/step1_idea.py:80 | …hoặc nơi KHÔNG có trong danh sách (ngoài game) | ô chữ | Nhập: …hoặc nơi KHÔNG có trong danh sách (ngoài game) | 0 USD | — | chuyên gia/người quen | idea_settings_form |
| steps/step1_idea.py:85 | Loại nơi vừa nhập | radio | Chọn: Loại nơi vừa nhập | 0 USD | — | chuyên gia/người quen | idea_settings_form |
| steps/step1_idea.py:88 | Cách tạo bối cảnh (nơi đời thường) | radio | Chọn: Cách tạo bối cảnh (nơi đời thường) | 0 USD | — | chuyên gia/người quen | idea_settings_form |
| steps/step1_idea.py:91 | Có cảnh gameplay / giao diện game? | radio | Chọn: Có cảnh gameplay / giao diện game? | 0 USD | — | chuyên gia/người quen | idea_settings_form |
| steps/step1_idea.py:94 | Diễn biến chính / mâu thuẫn | ô chữ | Nhập: Diễn biến chính / mâu thuẫn | 0 USD | — | chuyên gia/người quen | idea_settings_form |
| steps/step1_idea.py:95 | Cú chốt / kết | ô chữ | Nhập: Cú chốt / kết | 0 USD | — | chuyên gia/người quen | idea_settings_form |
| steps/step1_idea.py:96 | 💡 Ý tưởng mới (bắt đầu lại từ lượt 1)" if inp else "💡 Bắt đầu | nút form | Lưu 6 thiết lập ý tưởng, bắt đầu lượt Biên kịch (0 USD) | 0 USD | — | người mới | cờ idea_to_script; chữ được hiểu là ý tưởng |
| steps/step1_idea.py:127 | {q['q']} — mặc định: {q['default']} | ô chữ | Nhập: {q['q']} — mặc định: {q['default']} | 0 USD | — | chuyên gia/người quen | turn_questions |
| steps/step1_idea.py:148 | Chọn hướng | radio | Chọn 1 trong 3 hướng kịch bản | 0 USD | — | người mới | turn_directions |
| steps/step1_idea.py:149 | Ghi chú cho hướng đã chọn (không bắt buộc) | ô chữ | Nhập: Ghi chú cho hướng đã chọn (không bắt buộc) | 0 USD | — | chuyên gia/người quen | turn_directions |
| steps/step1_idea.py:151 | ↻ Hỏi lại 3 hướng khác (≈ {I.TURN_USD:g} USD) | nút | Hỏi lại 3 hướng | $ Claude | giá trên nút | chuyên gia/người quen | turn_directions · xám khi: not changed |
| steps/step1_idea.py:212 | Sửa tay kịch bản (giữ khuôn CẢNH n - …) | ô chữ lớn | Nhập: Sửa tay kịch bản (giữ khuôn CẢNH n - …) | 0 USD | — | chuyên gia/người quen | turn_script |
| steps/step1_idea.py:213 | 💾 Lưu bản sửa + kiểm lại | nút | Lưu bản sửa | 0 USD | — | chuyên gia/người quen | turn_script |
| steps/step1_idea.py:227 | ✔ Dùng kịch bản này" + (" (dự án đã có cảnh — bấm ↺ Làm lại ở trên trư… | nút | Nhập kịch bản Biên kịch viết vào dự án (tạo cảnh luôn) | 0 USD | — | người mới | turn_script · xám khi: not chk.get("ok") or has_scenes |
| steps/step1_intake.py:69 | Dùng làm | radio | Chọn: Dùng làm | 0 USD | — | chuyên gia/người quen | pending_cards |
| steps/step1_intake.py:74 | Tên | hộp chọn | Chọn: Tên | 0 USD | — | chuyên gia/người quen | pending_cards |
| steps/step1_intake.py:78 | Của nhân vật | hộp chọn | Chọn: Của nhân vật | 0 USD | — | chuyên gia/người quen | pending_cards |
| steps/step1_intake.py:82 | Tên bộ đồ (để trống: “<nhân vật> — trang phục”) | ô chữ | Nhập: Tên bộ đồ (để trống: “<nhân vật> — trang phục”) | 0 USD | — | chuyên gia/người quen | pending_cards |
| steps/step1_intake.py:84 | Cho cảnh | hộp chọn | Chọn: Cho cảnh | 0 USD | — | chuyên gia/người quen | pending_cards |
| steps/step1_intake.py:89 | page_label(p.conn) | nút | (pending_cards) | $ Claude (đọc chữ trên ảnh) | giá trên nút | chuyên gia/người quen | pending_cards |
| steps/step1_intake.py:91 | ✔ Gắn | nút | Áp đề xuất | 0 USD | — | chuyên gia/người quen | pending_cards · xám khi: role is None |
| steps/step1_intake.py:99 | ✖ Bỏ tệp | nút | (pending_cards) | 0 USD | — | chuyên gia/người quen | pending_cards |
| steps/step1_intake.py:115 | 🤖 Phân tích ảnh phong cách" + cost.llm_tag(cost.llm_estimate(p.conn, "… | nút | (style_offer) | $ Claude | giá trên nút | chuyên gia/người quen | style_offer · xám khi: llm is None |
| steps/step1_prep.py:23 | Dùng mẫu phong cách đã lưu | hộp chọn | Chọn: Dùng mẫu phong cách đã lưu | 0 USD | — | chuyên gia | world_bible_panel |
| steps/step1_prep.py:25 | Áp dụng mẫu | nút | (world_bible_panel) | 0 USD | — | chuyên gia | world_bible_panel |
| steps/step1_prep.py:30 | Ảnh tham khảo phong cách | tải tệp | Tải tệp lên | 0 USD | — | chuyên gia | world_bible_panel |
| steps/step1_prep.py:34 | 🤖 Phân tích ảnh phong cách bằng Claude" + cost.llm_tag(cost.llm_estima… | nút | (world_bible_panel) | $ Claude | giá trên nút | chuyên gia | world_bible_panel · xám khi: not uploads or llm is None |
| steps/step1_prep.py:60 | {el.get('label', '')}: {el.get('prose', '')} | ô tick | Bật/tắt: {el.get('label', '')}: {el.get('prose', '')} | 0 USD | — | chuyên gia | world_bible_panel |
| steps/step1_prep.py:67 | label | ô chữ lớn | Nhập: label | 0 USD | — | chuyên gia | world_bible_panel |
| steps/step1_prep.py:69 | 💾 Lưu World Bible | nút | Lưu | 0 USD | — | chuyên gia | world_bible_panel |
| steps/step1_prep.py:72 | Xóa | nút | Lưu | 0 USD | — | chuyên gia | world_bible_panel |
| steps/step1_prep.py:77 | Lưu làm mẫu dùng lại (tên mẫu) | ô chữ | Nhập: Lưu làm mẫu dùng lại (tên mẫu) | 0 USD | — | chuyên gia | world_bible_panel |
| steps/step1_prep.py:78 | ⭐ Lưu làm mẫu phong cách | nút | (world_bible_panel) | 0 USD | — | chuyên gia | world_bible_panel |
| steps/step1_prep.py:107 | ➕ Dùng | nút | Gắn tài nguyên | 0 USD | — | chuyên gia/người quen | assets_panel |
| steps/step1_prep.py:111 | ➕ Dùng tất cả gợi ý | nút | Gắn tài nguyên | 0 USD | — | chuyên gia/người quen | assets_panel |
| steps/step1_prep.py:124 | ✖ Bỏ | nút | Bỏ tài nguyên | 0 USD | — | chuyên gia/người quen | assets_panel |
| steps/step1_prep.py:131 | Thêm từ kho | hộp chọn | Chọn: Thêm từ kho | 0 USD | — | chuyên gia/người quen | assets_panel |
| steps/step1_prep.py:133 | ➕ Thêm vào dự án | nút | Gắn tài nguyên | 0 USD | — | chuyên gia/người quen | assets_panel |
| steps/step1_prep.py:143 | Tên | ô chữ | Nhập: Tên | 0 USD | — | chuyên gia/người quen | assets_panel |
| steps/step1_prep.py:144 | Loại | hộp chọn | Chọn: Loại | 0 USD | — | chuyên gia/người quen | assets_panel |
| steps/step1_prep.py:145 | Mô tả ngắn (tùy chọn) | ô chữ | Nhập: Mô tả ngắn (tùy chọn) | 0 USD | — | chuyên gia/người quen | assets_panel |
| steps/step1_prep.py:151 | Tên tiếng Anh (bắt buộc nếu tên chính là tiếng Việt) | ô chữ | Nhập: Tên tiếng Anh (bắt buộc nếu tên chính là tiếng Việ… | 0 USD | — | chuyên gia/người quen | assets_panel |
| steps/step1_prep.py:153 | Ảnh (JPG/PNG/WebP, tối đa 10 MB mỗi ảnh) | tải tệp | Tải tệp lên | 0 USD | — | chuyên gia/người quen | assets_panel |
| steps/step1_prep.py:155 | Lưu cả vào kho dùng chung | ô tick | Bật/tắt: Lưu cả vào kho dùng chung | 0 USD | — | chuyên gia/người quen | assets_panel |
| steps/step1_prep.py:156 | Lưu vào dự án | nút | Gắn tài nguyên | 0 USD | — | chuyên gia/người quen | assets_panel · xám khi: not (name.strip() and files) |
| steps/step1_prep.py:180 | Tỉ lệ khung | hộp chọn | Chọn: Tỉ lệ khung | 0 USD | — | chuyên gia/người quen | project_format_panel |
| steps/step1_prep.py:184 | Thể loại (hướng dẫn đạo diễn) | hộp chọn | Chọn: Thể loại (hướng dẫn đạo diễn) | 0 USD | — | chuyên gia/người quen | project_format_panel |
| steps/step1_prep.py:189 | Ưu tiên model video | hộp chọn | Chọn: Ưu tiên model video | 0 USD | — | chuyên gia/người quen | project_format_panel |
| steps/step1_prep.py:204 | Đổi tỉ lệ khung | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | chuyên gia/người quen | project_format_panel |
| steps/step1_prep.py:217 | Dùng ưu tiên đã chọn ở trên | nút | Lưu trường dự án | 0 USD | — | chuyên gia/người quen | project_format_panel |
| steps/step1_prep.py:232 | ⏱ Nhịp phim | radio | Chọn: ⏱ Nhịp phim | 0 USD | — | chuyên gia/người quen | pacing_control |
| steps/step1_prep.py:254 | 🎙 Tốc độ đọc lời dẫn | hộp chọn | Chọn: 🎙 Tốc độ đọc lời dẫn | 0 USD | — | chuyên gia/người quen | narration_speed_control |
| steps/step1_prep.py:274 | 🖼 Model ảnh (Deepix) | hộp chọn | Chọn: 🖼 Model ảnh (Deepix) | 0 USD | — | chuyên gia/người quen | image_model_control |
| steps/step1_prep.py:290 | 🎨 Look hình | radio | Chọn: 🎨 Look hình | 0 USD | — | chuyên gia/người quen | shot_format_controls |
| steps/step1_prep.py:301 | Cách chia cảnh | hộp chọn | Chọn: Cách chia cảnh | 0 USD | — | chuyên gia/người quen | shot_format_controls |
| steps/step1_prep.py:306 | Phong cách tham khảo (chọn một hoặc nhiều — trộn được) | chọn nhiều | Chọn: Phong cách tham khảo (chọn một hoặc nhiều — trộn đ… | 0 USD | — | chuyên gia/người quen | shot_format_controls |
| steps/step1_prep.py:323 | ✂ Cho phép Director bỏ bớt câu thoại để shot đủ dài (không thêm, không… | ô tick | Bật/tắt: ✂ Cho phép Director bỏ bớt câu thoại để shot đủ dà… | 0 USD | — | chuyên gia/người quen | shot_format_controls |
| steps/step1_prep.py:345 | 🎬 Dựng storyboard | nút | (storyboard_panel) | $ Claude | KHÔNG | chuyên gia | Chuyên gia + có nhân vật |
| steps/step1_prep.py:356 | 🔍 Claude rà storyboard | nút | (storyboard_panel) | $ Claude | KHÔNG | chuyên gia | Chuyên gia + đã dựng storyboard |
| steps/step1_refs.py:39 | title | nút | (modes_line) | 0 USD | — | chuyên gia/người quen | modes_line · xám khi: True |
| steps/step1_refs.py:106 | Gắn cho (đã nhận ra) | hộp chọn | Chọn: Gắn cho (đã nhận ra) | 0 USD | — | chuyên gia/người quen | attach_form |
| steps/step1_refs.py:109 | Ảnh (JPG / PNG / WebP) | tải tệp | Tải tệp lên | 0 USD | — | chuyên gia/người quen | attach_form |
| steps/step1_refs.py:111 | Là | hộp chọn | Chọn: Là | 0 USD | — | chuyên gia/người quen | attach_form |
| steps/step1_refs.py:112 | Tên bộ trang phục (vd: Kelly đồ bơi)" if kind == "outfit" else "Tên (v… | ô chữ | Nhập: Tên bộ trang phục (vd: Kelly đồ bơi)" if kind == "… | 0 USD | — | chuyên gia/người quen | attach_form |
| steps/step1_refs.py:118 | cho nhân vật … | hộp chọn | Chọn: cho nhân vật … | 0 USD | — | chuyên gia/người quen | attach_form |
| steps/step1_refs.py:124 | Lưu vào Kho chung (dùng lại ở mọi dự án — ảnh chờ duyệt trước khi pipe… | ô tick | Bật/tắt: Lưu vào Kho chung (dùng lại ở mọi dự án — ảnh chờ … | 0 USD | — | chuyên gia/người quen | attach_form |
| steps/step1_refs.py:126 | ➕ Gắn vào dự án | nút | (attach_form) | 0 USD | — | chuyên gia/người quen | attach_form · xám khi: not (files and name.strip()) |
| steps/step1_refs.py:143 | 📁 Mở Kho tài nguyên (duyệt ảnh chờ, nhân vật 3D, âm thanh) | nút | Mở hộp thoại | 0 USD | — | chuyên gia/người quen | attach_form |
| steps/step1_run.py:32 | ■ Bỏ khỏi hàng đợi | nút | Dừng chạy tự động | 0 USD | — | chuyên gia/người quen | autopilot_progress |
| steps/step1_run.py:37 | ⏸ Tạm dừng | nút | Tạm dừng/tiếp tục dự án | 0 USD | — | chuyên gia/người quen | autopilot_progress |
| steps/step1_run.py:39 | ■ Dừng hẳn | nút | Dừng chạy tự động | 0 USD | — | chuyên gia/người quen | autopilot_progress |
| steps/step1_run.py:48 | label | nút | Tiếp tục chạy tự động sau cổng/lỗi | $ ảnh + $ video + $ Claude (phần còn lại của chuỗi) | giá trên nút | người mới | chạy tự động đang chờ/dừng/lỗi |
| steps/step1_run.py:104 | Số trích (USD) | ô số | Nhập: Số trích (USD) | 0 USD | — | chuyên gia/người quen | reserve_box |
| steps/step1_run.py:105 | Lý do sửa | ô chữ | Nhập: Lý do sửa | 0 USD | — | chuyên gia/người quen | reserve_box |
| steps/step1_run.py:106 | 💾 Lưu số trích | nút | Lưu số trích | 0 USD | — | chuyên gia/người quen | reserve_box · xám khi: r is not None and abs(val - float(r["usd… |
| steps/step1_run.py:161 | Ngân sách mục tiêu (USD, để Director chia shot trong mức này; 0 = khôn… | ô số | Nhập: Ngân sách mục tiêu (USD, để Director chia shot tro… | 0 USD | — | chuyên gia/người quen | project_budget_panel |
| steps/step1_run.py:172 | ⚠ Đặt trần cảnh báo ≈ USD | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | chuyên gia/người quen | project_budget_panel |
| steps/step1_run.py:178 | Nâng trần khâu | hộp chọn | Chọn: Nâng trần khâu | 0 USD | — | chuyên gia/người quen | project_budget_panel |
| steps/step1_run.py:179 | Thêm (USD) | ô số | Nhập: Thêm (USD) | 0 USD | — | chuyên gia/người quen | project_budget_panel |
| steps/step1_run.py:180 | Lý do (bắt buộc) | ô chữ | Nhập: Lý do (bắt buộc) | 0 USD | — | chuyên gia/người quen | project_budget_panel |
| steps/step1_run.py:181 | Nâng trần | nút | Nâng trần khâu | 0 USD | — | chuyên gia/người quen | project_budget_panel · xám khi: not (add > 0 and why.strip()) |
| steps/step1_run.py:201 | ↺ Đặt lại chế độ tự động | nút | Đặt lại | 0 USD | — | chuyên gia/người quen | autopilot_panel |
| steps/step1_run.py:212 | Dừng để duyệt Character Bible + Character Lock + giọng + ảnh mốc trước… | ô tick | Bật/tắt: Dừng để duyệt Character Bible + Character Lock + g… | cổng dừng chạy tự động (ảnh hưởng chi) | KHÔNG | chuyên gia/người quen | autopilot_panel |
| steps/step1_run.py:214 | Gen thử 2–3 cảnh đại diện trước, dừng để bạn xem rồi mới gen hết | ô tick | Bật/tắt: Gen thử 2–3 cảnh đại diện trước, dừng để bạn xem r… | cổng dừng chạy tự động (ảnh hưởng chi) | KHÔNG | chuyên gia/người quen | autopilot_panel |
| steps/step1_run.py:216 | Dừng ở **storyboard** (xem cả bộ ảnh khung đầu) trước khi gen video | ô tick | Bật/tắt: Dừng ở **storyboard** (xem cả bộ ảnh khung đầu) tr… | cổng dừng chạy tự động (ảnh hưởng chi) | KHÔNG | chuyên gia/người quen | autopilot_panel |
| steps/step1_run.py:246 | ✔ Duyệt phân cảnh & chạy tự động (≈ USD) | nút + Có/Không | Bắt đầu chạy tự động cả chuỗi (Director → ảnh → motion → video → nhạc → bản giao) | $ ảnh + $ video + $ Claude + $ âm thanh (cả chuỗi) | giá trên nút, hỏi Có/Không | người mới | ⚙ Chi tiết › 🚀 Tự động hoàn toàn; chưa chạy; không có mục đỏ |
| steps/step1_v2.py:166 | label | nút | Chạy Director: chia shot + Character Bible | $ Claude (Director) | giá trên nút | người mới | hero/bong bóng chat, khi đã tách cảnh, chưa có nhân vật (kind=plan) |
| steps/step1_v2.py:173 | ✔ Duyệt & khóa → Storyboard | nút | Khóa Character Bible và sang màn Storyboard | 0 USD | — | người mới | kind=lock (có nhân vật, Bible chưa khóa) |
| steps/step1_v2.py:184 | Sang Storyboard → | nút | Chuyển sang màn Storyboard | 0 USD | — | người mới | kind=next (Bible đã khóa) |
| steps/step1_v2.py:287 | ✔ Duyệt & khóa → Storyboard | nút | Khóa Character Bible và sang màn Storyboard | 0 USD | — | người mới | thẻ ② (chỉ khi cờ chat_first TẮT) |

### ② Storyboard · Ảnh — 97 điều khiển

| file:dòng | Nhãn | Loại | Việc làm | Tiền | Giá / xác nhận | Ai dùng | Điều kiện hiện |
|---|---|---|---|---|---|---|---|
| change_review_ui.py:34 | ✓ Đã sửa | nút | Đóng mục Tổ rà soát | 0 USD | — | chuyên gia/người quen | render |
| change_review_ui.py:37 | Bỏ qua | nút | Đóng mục Tổ rà soát | 0 USD | — | chuyên gia/người quen | render |
| change_review_ui.py:40 | ↻ Rà lại | nút | (render) | $ Claude (rà lại thay đổi) | KHÔNG | chuyên gia/người quen | render |
| continuity_ui.py:49 | 'Giữ bố cục theo shot …' | hộp chọn | Chọn: 'Giữ bố cục theo shot …' | 0 USD | — | chuyên gia/người quen | render · xám khi: disabled |
| continuity_ui.py:52 | 'Bỏ' | nút | Lưu | 0 USD | — | chuyên gia/người quen | render · xám khi: disabled or current is None |
| continuity_ui.py:56 | 'Lưu bố cục' | nút | Lưu | 0 USD | — | chuyên gia/người quen | render · xám khi: disabled |
| design/screens/older_take_ui.py:36 | label | nút | (use_button) | 0 USD | — | chuyên gia/người quen | use_button |
| design/screens/older_take_ui.py:45 | Có, dùng bản này | nút | (use_button) | 0 USD | — | chuyên gia/người quen | use_button |
| design/screens/older_take_ui.py:47 | Không | nút | (use_button) | 0 USD | — | chuyên gia/người quen | use_button |
| design/screens/prompt_versions_ui.py:72 | Tôi hiểu, vẫn dùng lại prompt cũ | ô tick | Bật/tắt: Tôi hiểu, vẫn dùng lại prompt cũ | 0 USD | — | chuyên gia/người quen | panel |
| design/screens/prompt_versions_ui.py:73 | ↩ Dùng lại prompt cũ | nút | Quay về bản trước | 0 USD | — | chuyên gia/người quen | panel · xám khi: not ok |
| design/screens/storyboard_cards.py:199 | ‹ | nút | (_version_strip) | 0 USD | — | chuyên gia/người quen | _version_strip · xám khi: pointer == 0 |
| design/screens/storyboard_cards.py:203 | v{i + 1} | nút | (_version_strip) | 0 USD | — | chuyên gia/người quen | _version_strip |
| design/screens/storyboard_cards.py:206 | › | nút | (_version_strip) | 0 USD | — | chuyên gia/người quen | _version_strip · xám khi: pointer == n - 1 |
| design/screens/storyboard_cards.py:268 | 🔍 Chi tiết | nút | (image_group_v2) | 0 USD | — | chuyên gia/người quen | image_group_v2 |
| design/screens/storyboard_cards.py:273 | Câu sửa (tiếng Anh) | ô chữ | Nhập: Câu sửa (tiếng Anh) | 0 USD | — | chuyên gia/người quen | image_group_v2 |
| design/screens/storyboard_cards.py:278 | ✔ Duyệt | nút | Duyệt 1 ảnh | 0 USD | — | người mới | image_group_v2 |
| design/screens/storyboard_cards.py:282 | ✖ Loại | nút | Loại ảnh (không vẽ lại), cần lý do | 0 USD | — | người mới | image_group_v2 · xám khi: bool(rerr) |
| design/screens/storyboard_cards.py:287 | ↻ Vẽ lại | nút | Loại & vẽ lại 1 ảnh (cần lý do) | $ ảnh | giá ở dòng ngay trên nút | người mới | image_group_v2 · xám khi: bool(rerr) |
| design/screens/storyboard_cards.py:294 | ✎ Sửa | nút | (image_group_v2) | 0 USD | — | chuyên gia/người quen | image_group_v2 |
| design/screens/storyboard_cards.py:298 | ✔ Duyệt | nút | (image_group_v2) | 0 USD | — | chuyên gia/người quen | image_group_v2 · xám khi: True |
| design/screens/storyboard_cards.py:299 | ■ Hủy | nút | Hủy job | 0 USD | — | chuyên gia/người quen | image_group_v2 |
| design/screens/storyboard_cards.py:303 | ↻ Vẽ lại | nút | (image_group_v2) | 0 USD | — | chuyên gia/người quen | image_group_v2 · xám khi: True |
| design/screens/storyboard_cards.py:304 | ✎ Sửa | nút | (image_group_v2) | 0 USD | — | chuyên gia/người quen | image_group_v2 |
| design/screens/storyboard_cards.py:307 | Câu sửa (tiếng Anh) | ô chữ | Nhập: Câu sửa (tiếng Anh) | 0 USD | — | chuyên gia/người quen | image_group_v2 |
| design/screens/storyboard_cards.py:310 | ✔ Duyệt | nút | (image_group_v2) | 0 USD | — | chuyên gia/người quen | image_group_v2 · xám khi: True |
| design/screens/storyboard_cards.py:311 | ✖ Loại | nút | (image_group_v2) | 0 USD | — | chuyên gia/người quen | image_group_v2 · xám khi: True |
| design/screens/storyboard_cards.py:313 | ↻ Vẽ lại | nút | Gửi lại job | $ ảnh | giá ở dòng ngay trên nút | chuyên gia/người quen | image_group_v2 |
| design/screens/storyboard_cards.py:320 | ✎ Sửa | nút | (image_group_v2) | 0 USD | — | chuyên gia/người quen | image_group_v2 |
| design/screens/storyboard_cards.py:323 | Lý do bỏ duyệt | ô chữ | Nhập: Lý do bỏ duyệt | 0 USD | — | chuyên gia/người quen | image_group_v2 |
| design/screens/storyboard_cards.py:333 | ✔ Duyệt lại | nút | (image_group_v2) | 0 USD | — | chuyên gia/người quen | image_group_v2 |
| design/screens/storyboard_cards.py:339 | ✔ Duyệt | nút | (image_group_v2) | 0 USD | — | chuyên gia/người quen | image_group_v2 · xám khi: True |
| design/screens/storyboard_cards.py:340 | ✖ Loại | nút | (image_group_v2) | 0 USD | — | chuyên gia/người quen | image_group_v2 · xám khi: True |
| design/screens/storyboard_cards.py:344 | ↻ Vẽ lại | nút | Bỏ duyệt & gen lại | $ ảnh | giá ở dòng ngay trên nút | chuyên gia/người quen | image_group_v2 · xám khi: bool(oerr) |
| design/screens/storyboard_cards.py:352 | ✎ Sửa | nút | (image_group_v2) | 0 USD | — | chuyên gia/người quen | image_group_v2 |
| design/screens/storyboard_cards.py:354 | ↻ Gen lại theo nội dung mới" + retake | nút | Bỏ duyệt & gen lại | $ ảnh | giá trên nút | chuyên gia/người quen | image_group_v2 |
| design/screens/storyboard_cards.py:361 | ✔ Duyệt | nút | (image_group_v2) | 0 USD | — | chuyên gia/người quen | image_group_v2 · xám khi: True |
| design/screens/storyboard_cards.py:362 | ✖ Loại | nút | (image_group_v2) | 0 USD | — | chuyên gia/người quen | image_group_v2 · xám khi: True |
| design/screens/storyboard_cards.py:365 | ↺ Làm lại | nút | Làm lại job từ đầu | $ ảnh | giá ở dòng ngay trên nút | chuyên gia/người quen | image_group_v2 |
| design/screens/storyboard_cards.py:370 | ↻ Vẽ lại | nút | (image_group_v2) | 0 USD | — | chuyên gia/người quen | image_group_v2 · xám khi: True |
| design/screens/storyboard_cards.py:371 | ✎ Sửa | nút | (image_group_v2) | 0 USD | — | chuyên gia/người quen | image_group_v2 |
| design/screens/storyboard_cards.py:439 | ✔ Duyệt storyboard → gửi video" + board_tag | nút | Duyệt storyboard → chạy tự động gửi video | $ video (mở cổng → chạy tự động gen video) | giá trên nút | người mới | chỉ khi chạy tự động đang CHỜ ở cổng storyboard |
| design/screens/storyboard_cards.py:445 | ✔ Duyệt tất cả (N ảnh) | nút + Có/Không | Duyệt mọi ảnh đang chờ | 0 USD | — | người mới | action_bar |
| reject_reason_ui.py:16 | label | hộp chọn | Chọn: label | 0 USD | — | chuyên gia/người quen | pick |
| reject_reason_ui.py:21 | Ghi rõ lý do 'Khác' | ô chữ | Nhập: Ghi rõ lý do 'Khác' | 0 USD | — | chuyên gia/người quen | pick |
| steps/step2.py:89 | ↻ Thử kiểm tra lại | nút | (image_progress) | $ Claude (khởi động lại tự kiểm ảnh) | KHÔNG | chuyên gia/người quen | image_progress |
| steps/step2.py:120 | ↻ Render lại nền 3D shot {idx} (0 USD) | nút | (plate_retry_buttons) | 0 USD | — | chuyên gia/người quen | plate_retry_buttons |
| steps/step2.py:230 | Tôi đã xem, vẫn gen ảnh (ghi lại vào 📊 Theo dõi) | ô tick | Bật/tắt: Tôi đã xem, vẫn gen ảnh (ghi lại vào 📊 Theo dõi) | 0 USD | — | chuyên gia/người quen | step2 |
| steps/step2.py:235 | Tôi đã xem, vẫn gen ảnh (ghi lại vào 📊 Theo dõi) | ô tick | Bật/tắt: Tôi đã xem, vẫn gen ảnh (ghi lại vào 📊 Theo dõi) | 0 USD | — | chuyên gia/người quen | step2 |
| steps/step2.py:241 | ▶ Gen ảnh các cảnh chưa có / đã cũ" + (f" · gửi {queued} ảnh đang chờ"… | nút | Xếp hàng + gửi gen ảnh mọi cảnh chưa có/đã cũ | $ ảnh (+ Claude QC + D6) | giá trên nút, ô tick xác nhận (lô ≥ ngưỡng / credit) | người mới | luôn (xám khi bị cổng chặn & chưa tick 'vẫn gen') |
| steps/step2.py:263 | ✔ Duyệt tất cả (N ảnh) [UI cũ] | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:269 | ↻ Gửi lại ảnh lỗi ({len(failed)}){cost.price_tag(None if unit is None … | nút | Gửi lại job | $ ảnh | giá trên nút | chuyên gia/người quen | step2 · xám khi: not failed |
| steps/step2.py:324 | Lọc | radio | Chọn: Lọc | 0 USD | — | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:371 | Lọc | radio | Chọn: Lọc | 0 USD | — | chuyên gia/người quen | grid_v2 |
| steps/step2.py:404 | ‹ | nút | (image_card_group) | 0 USD | — | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:409 | › | nút | (image_card_group) | 0 USD | — | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:447 | 🔍 Chi tiết | nút | (image_card) | 0 USD | — | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:455 | ✔ Duyệt | nút | Duyệt | 0 USD | — | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:458 | ✖ Loại | nút | Loại | $ ảnh (Loại = loại & gen lại) | KHÔNG | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:466 | 🔍 Xem | nút | (image_card) | 0 USD | — | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:471 | ■ Hủy | nút | Hủy job | 0 USD | — | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:474 | 🔍 Xem | nút | (image_card) | 0 USD | — | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:480 | ↻ Gửi lại | nút | Gửi lại job | $ ảnh (gửi lại) | KHÔNG | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:483 | 🔍 Xem | nút | (image_card) | 0 USD | — | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:487 | ↻ Gen lại theo nội dung mới" + retake | nút | Bỏ duyệt & gen lại | $ ảnh | giá trên nút | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:491 | ↺ Làm lại từ đầu" + retake | nút | Làm lại job từ đầu | $ ảnh | giá trên nút | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:494 | 🔍 Xem | nút | (image_card) | 0 USD | — | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:520 | Nhập ảnh thủ công | tải tệp | Tải tệp lên | 0 USD | — | chuyên gia/người quen | image_detail |
| steps/step2.py:521 | Xác nhận ảnh đã có | nút | Bắt đầu | 0 USD | — | chuyên gia/người quen | image_detail |
| steps/step2.py:538 | JSON điểm QC từ Claude | ô chữ lớn | Nhập: JSON điểm QC từ Claude | 0 USD | — | chuyên gia | image_detail |
| steps/step2.py:539 | Chấm điểm | nút | (image_detail) | 0 USD | — | chuyên gia/người quen | image_detail · xám khi: not raw.strip() |
| steps/step2.py:550 | chat_prompt.note_label("Câu sửa cho lần gen lại (đưa vào prompt — nên … | ô chữ | Nhập: chat_prompt.note_label("Câu sửa cho lần gen lại (đ… | 0 USD | — | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:555 | ✖ Loại & gen lại" + retake | nút | Loại | $ ảnh | giá trên nút | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:561 | ✔ Duyệt | nút | Duyệt | 0 USD | — | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:564 | 🗑 Xóa (vào thùng rác, không gen lại) | nút | Loại | 0 USD | — | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:568 | Câu sửa cho model (tiếng Anh) — để trống = gửi lại y nguyên (chỉ khi l… | ô chữ | Nhập: Câu sửa cho model (tiếng Anh) — để trống = gửi lại… | 0 USD | — | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:570 | ("↻ Gen lại với câu sửa" if fix.strip() else "↻ Gửi lại (lỗi nhà cung … | nút | Gửi lại job | $ ảnh | giá trên nút | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:575 | ↺ Làm lại từ đầu" + retake | nút | Làm lại job từ đầu | $ ảnh | giá trên nút | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:579 | Lý do bỏ duyệt (đưa vào prompt gen lại) | ô chữ | Nhập: Lý do bỏ duyệt (đưa vào prompt gen lại) | 0 USD | — | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:583 | ↩ Bỏ duyệt & gen lại ảnh" + retake | nút | Bỏ duyệt & gen lại | $ ảnh | giá trên nút | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:601 | Chính sách QC ảnh | hộp chọn | Chọn: Chính sách QC ảnh | 0 USD | — | chuyên gia | qc_policy_panel |
| steps/step2.py:611 | Ngưỡng đạt | thanh trượt | Chọn: Ngưỡng đạt | 0 USD | — | chuyên gia | qc_policy_panel |
| steps/step2.py:614 | Gen lại tối đa mỗi cảnh (rồi báo bạn) | thanh trượt | Chọn: Gen lại tối đa mỗi cảnh (rồi báo bạn) | 0 USD | — | chuyên gia | qc_policy_panel |
| steps/step2.py:617 | Claude tự gen lại ảnh dưới ngưỡng trước khi đến bạn (mỗi lần tốn credi… | ô tick | Bật/tắt: Claude tự gen lại ảnh dưới ngưỡng trước khi đến bạ… | bật tự gen lại ảnh (tốn credit về sau) | KHÔNG | chuyên gia | qc_policy_panel |
| steps/step2.py:621 | Tự loại ảnh rất tệ | ô tick | Bật/tắt: Tự loại ảnh rất tệ | 0 USD | — | chuyên gia | qc_policy_panel |
| steps/step2.py:622 | Mức loại ngay | thanh trượt | Chọn: Mức loại ngay | 0 USD | — | chuyên gia | qc_policy_panel · xám khi: not floor_on |
| steps/step2.py:628 | Vùng chờ review (giữa mức sàn và ngưỡng: chờ bạn thay vì tự loại) | ô tick | Bật/tắt: Vùng chờ review (giữa mức sàn và ngưỡng: chờ bạn t… | 0 USD | — | chuyên gia | qc_policy_panel |
| steps/step2.py:630 | Mức sàn | thanh trượt | Chọn: Mức sàn | 0 USD | — | chuyên gia | qc_policy_panel · xám khi: not zone_on |
| steps/step2.py:654 | 🧪 Bật gen thử trước | nút | Bắt đầu | 0 USD | — | người mới | ≥ MIN_SCENES cảnh và chưa có ảnh |
| steps/step2.py:677 | ✔ Mẫu thử ổn — gen phần còn lại | nút | Mở gen cả lô sau mẫu thử | 0 USD | — | người mới | đã bật 🧪 gen thử; xám tới khi ảnh thử duyệt xong |
| steps/step2.py:681 | Bỏ gen thử | nút | Lưu | 0 USD | — | chuyên gia/người quen | pilot_panel |
| steps/step2.py:698 | 🎬 Xem nhịp cả phim (animatic · 0 USD)" if not done else "🔄 Dựng lại an… | nút | Dựng/đo | 0 USD | — | chuyên gia/người quen | animatic_box |
| steps/step2.py:711 | ▶ Mở bản đã dựng | nút | (animatic_box) | 0 USD | — | chuyên gia/người quen | animatic_box |
| steps/step2.py:715 | ✖ Thu gọn | nút | (animatic_box) | 0 USD | — | chuyên gia/người quen | animatic_box |
| steps/step2.py:787 | ✔ Duyệt storyboard — gen video" + cost.video_batch_tag(p, pid) | nút | Bắt đầu | $ video (mở cổng → chạy tự động gen video) | giá trên nút | chuyên gia/người quen | CHỈ UI cũ (ui_v2 tắt) — đang ẩn |
| steps/step2.py:839 | 🤖 Kiểm tra {approved} ảnh đã duyệt" + cost.llm_tag(cost.llm_estimate(p… | nút | (set_check_panel) | $ Claude | giá trên nút | chuyên gia | set_check_panel · xám khi: client is None |
| steps/step2.py:858 | ↻ Gen lại cảnh này" + cost.price_tag(img_unit) | nút | (set_check_panel) | $ ảnh | giá trên nút | chuyên gia | set_check_panel |

### ③ Storyboard · Motion & giọng — 20 điều khiển

| file:dòng | Nhãn | Loại | Việc làm | Tiền | Giá / xác nhận | Ai dùng | Điều kiện hiện |
|---|---|---|---|---|---|---|---|
| steps/step3.py:64 | 🤖 Viết motion prompt ({len(missing)} chưa có · {len(stale_idx)} đã cũ{… | nút | Claude (hoặc code) viết motion prompt các shot | $ Claude | giá trên nút | người mới | step3 · xám khi: (client is None and not by_code_n) or no… |
| steps/step3.py:85 | ✔ Duyệt tất cả (N prompt) | nút + Có/Không | Duyệt mọi motion prompt đang chờ | 0 USD | — | người mới | step3 |
| steps/step3.py:89 | 🔍 Rà motion prompt ({len(rows)}){cost.llm_tag(cost.llm_estimate(p.conn… | nút | (step3) | $ Claude | giá trên nút | chuyên gia/người quen | step3 · xám khi: client is None or not rows |
| steps/step3.py:103 | Dán JSON motion prompts từ Claude | ô chữ lớn | Nhập: Dán JSON motion prompts từ Claude | 0 USD | — | chuyên gia | step3 |
| steps/step3.py:104 | ▶ Lưu motion prompts | nút | Lưu motion prompt | 0 USD | — | chuyên gia/người quen | step3 · xám khi: not raw.strip() |
| steps/step3.py:148 | Motion prompt | ô chữ lớn | Nhập: Motion prompt | 0 USD | — | chuyên gia/người quen | step3 |
| steps/step3.py:152 | 🏁 Trạng thái cuối shot (khung cuối) | ô chữ | Nhập: 🏁 Trạng thái cuối shot (khung cuối) | 0 USD | — | chuyên gia/người quen | step3 |
| steps/step3.py:157 | Lưu chỉnh sửa | nút | Lưu motion prompt | 0 USD | — | chuyên gia/người quen | step3 |
| steps/step3.py:166 | ✔ Duyệt | nút | Lưu motion prompt | 0 USD | — | chuyên gia/người quen | step3 · xám khi: r["state"] == "approved" and not srow.ge… |
| steps/step3.py:178 | Dùng bản sửa của rà prompt | nút | (step3) | 0 USD | — | chuyên gia/người quen | step3 |
| steps/step3.py:190 | Dùng bản sửa | nút | (step3) | 0 USD | — | chuyên gia/người quen | step3 |
| steps/step3.py:200 | ✖ Bỏ video tham chiếu | nút | Đặt/bỏ video tham chiếu | 0 USD | — | chuyên gia/người quen | step3 |
| steps/step3.py:203 | Tải video tham chiếu (MP4) | tải tệp | Tải tệp lên | 0 USD | — | chuyên gia/người quen | step3 |
| steps/step3.py:204 | Kiểu tham chiếu (chỉ Kling) | radio | Chọn: Kiểu tham chiếu (chỉ Kling) | 0 USD | — | chuyên gia/người quen | step3 |
| steps/step3.py:205 | ⬆ Lưu video tham chiếu | nút | Đặt/bỏ video tham chiếu | 0 USD | — | chuyên gia/người quen | step3 · xám khi: up is None |
| steps/step3.py:269 | 🎙 Tạo giọng cho {todo} câu" + budget.audio_tag(p.conn, todo, "eleven_v… | nút | Tạo giọng thoại TTS cho các câu | $ âm thanh (TTS) | giá trên nút | người mới | voice_panel · xám khi: provider is None or not todo |
| steps/step3.py:276 | ⟳ Kiểm tra + tải về | nút | Hỏi trạng thái + tải kết quả | 0 USD | — | chuyên gia/người quen | voice_panel · xám khi: provider is None |
| steps/step3.py:289 | ⏱ Đặt thời lượng clip theo giọng thật" + (f" (làm lại {len(late)} clip… | nút | Đặt thời lượng theo giọng | $ video (chỉ khi phải làm lại clip đã có) | giá trên nút | chuyên gia/người quen | voice_panel |
| steps/step3.py:301 | 🎧 Kiểm giọng (miễn phí, chạy trên máy) | nút | Kiểm giọng cục bộ | 0 USD | — | chuyên gia/người quen | voice_panel · xám khi: not done |
| steps/step3.py:315 | 🔁 Tạo lại N câu nghi lỗi + giá âm thanh | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | $ âm thanh | giá trên nút, hỏi Có/Không | chuyên gia/người quen | voice_panel |

### ④ Video — 54 điều khiển

| file:dòng | Nhãn | Loại | Việc làm | Tiền | Giá / xác nhận | Ai dùng | Điều kiện hiện |
|---|---|---|---|---|---|---|---|
| end_frame_ui.py:44 | label | nút | (card_block) | $ ảnh (khung cuối) | giá trên nút | chuyên gia/người quen | card_block |
| end_frame_ui.py:59 | ▶ Gửi clip KHÔNG kèm khung cuối" + tag | nút | (_send_without) | $ video | giá trên nút | chuyên gia/người quen | _send_without |
| quality_ui.py:292 | ⬆ Gen bản cao" + cost.price_tag(price) | nút | (card_block) | $ video | giá trên nút | người mới | cờ two_tier_quality ON, cảnh có nháp đã duyệt |
| quality_ui.py:303 | Gen MỚI bản cao (không nâng được từ nháp) | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | $ video | giá trên nút, hỏi Có/Không | chuyên gia/người quen | card_block |
| quality_ui.py:329 | ⬆ Gen bản cao N cảnh — ≈ USD | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | $ video | giá trên nút, hỏi Có/Không | chuyên gia/người quen | batch_block |
| quality_ui.py:341 | Gen mới bản cao N cảnh | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | $ video | giá trên nút, hỏi Có/Không | chuyên gia/người quen | batch_block |
| send_preview_ui.py:28 | Dựng gói (0 USD) | nút | (card_block) | 0 USD | — | chuyên gia/người quen | card_block |
| steps/step4.py:110 | ✏ Mở Motion prompt (tab Motion) | nút | (step4_v2) | 0 USD | — | chuyên gia/người quen | step4_v2 |
| steps/step4.py:134 | 🔊 Model tự tạo âm thanh (tiếng động, không khí) | ô tick | Bật/tắt: 🔊 Model tự tạo âm thanh (tiếng động, không khí) | bật âm thanh do model tạo (đổi giá clip) | KHÔNG | chuyên gia/người quen | _video_settings |
| steps/step4.py:139 | 🔍 Claude kiểm tra từng clip (giữ nhân vật, vật lý, khớp prompt, biến d… | ô tick | Bật/tắt: 🔍 Claude kiểm tra từng clip (giữ nhân vật, vật lý,… | bật Claude QC từng clip (tốn Claude về sau) | KHÔNG | chuyên gia/người quen | _video_settings |
| steps/step4.py:147 | 🧩 Gắn ảnh chủ thể nhân vật vào video (Seedance) — {n_subj} nhân vật có… | ô tick | Bật/tắt: 🧩 Gắn ảnh chủ thể nhân vật vào video (Seedance) — … | 0 USD | — | chuyên gia/người quen | _video_settings · xám khi: not works |
| steps/step4.py:178 | Cảnh mới sẽ gửi ({all_new}) — bỏ bớt để gen thử vài cảnh trước | chọn nhiều | Chọn: Cảnh mới sẽ gửi ({all_new}) — bỏ bớt để gen thử và… | 0 USD | — | chuyên gia/người quen | _video_batch |
| steps/step4.py:186 | Làm lại cảnh đã cũ ({len(stale_rows)}) — chỉ cảnh bạn chọn mới được gử… | chọn nhiều | Chọn: Làm lại cảnh đã cũ ({len(stale_rows)}) — chỉ cảnh … | 0 USD | — | chuyên gia/người quen | _video_batch |
| steps/step4.py:205 | label | nút | Xếp hàng + gửi gen video các cảnh đã chọn | $ video (+ Claude QC/D6) | giá trên nút, ô tick xác nhận (lô ≥ ngưỡng / credit) | người mới | luôn; xám khi chưa có runner / chưa tick lô lớn / không có gì để gửi |
| steps/step4.py:221 | ↻ Gửi lại clip lỗi ({len(failed)}){cost.price_tag(total, len(failed))} | nút | Gửi lại job | $ video | giá trên nút | chuyên gia/người quen | _video_batch · xám khi: not failed |
| steps/step4.py:235 | ↻ Xếp hàng lại từ đầu vào mới ({len(stale_failed)}){cost.price_tag(s_t… | nút | (_video_batch) | $ video | giá trên nút | chuyên gia/người quen | _video_batch · xám khi: runner is None |
| steps/step4.py:262 | ✔ Duyệt tất cả (N clip) | nút + Có/Không | Duyệt mọi clip chờ | 0 USD | — | người mới | _video_batch |
| steps/step4.py:272 | ↻ Thử kiểm tra lại | nút | (_video_batch) | $ Claude (khởi động lại tự kiểm clip) | KHÔNG | chuyên gia/người quen | _video_batch |
| steps/step4.py:291 | 🤖 Kiểm tra {usable} clip" + cost.llm_tag(cost.llm_estimate(p.conn, "cl… | nút | (clip_set_panel) | $ Claude | giá trên nút | chuyên gia/người quen | clip_set_panel · xám khi: client is None |
| steps/step4.py:312 | ↻ Gen lại clip này" + cost.price_tag(cost.clip_estimate(p.conn, p.job(… | nút | Gen lại video | $ video | giá trên nút | chuyên gia/người quen | clip_set_panel |
| steps/step4.py:338 | 🤖 Kiểm {calls} nhóm cảnh" + cost.llm_tag(usd, calls) | nút | (sequence_logic_panel) | $ Claude | giá trên nút | chuyên gia/người quen | sequence_logic_panel · xám khi: client is None |
| steps/step4.py:388 | Dùng đề xuất theo cảnh (ưu tiên Cân bằng) | nút | Lưu trường dự án | 0 USD | — | chuyên gia/người quen | model_plan_panel |
| steps/step4.py:393 | Bỏ model chung — dùng đề xuất theo cảnh | nút | Đặt model video | 0 USD | — | chuyên gia/người quen | model_plan_panel |
| steps/step4.py:425 | Model | hộp chọn | Chọn: Model | đổi model/độ phân giải → đổi giá lần gen sau | KHÔNG | chuyên gia/người quen | _model_change |
| steps/step4.py:444 | Chất lượng | hộp chọn | Chọn: Chất lượng | đổi model/độ phân giải → đổi giá lần gen sau | KHÔNG | chuyên gia/người quen | _model_change · xám khi: not levels |
| steps/step4.py:589 | chat_prompt.note_label("Câu sửa cho lần gen lại (nên viết tiếng Anh)") | ô chữ | Nhập: chat_prompt.note_label("Câu sửa cho lần gen lại (n… | 0 USD | — | chuyên gia/người quen | video_card_v2 |
| steps/step4.py:602 | Câu sửa (tiếng Anh) — trống = gửi lại y nguyên, chỉ khi lỗi do nhà cun… | ô chữ | Nhập: Câu sửa (tiếng Anh) — trống = gửi lại y nguyên, ch… | 0 USD | — | chuyên gia/người quen | video_card_v2 |
| steps/step4.py:606 | ✔ Duyệt clip | nút | Duyệt 1 clip | 0 USD | — | người mới | video_card_v2 · xám khi: not reviewable |
| steps/step4.py:612 | ("↻ Gen lại với câu sửa" if vfix.strip() else "↻ Gửi lại") + tag | nút | Gửi lại job | $ video | giá trên nút | chuyên gia/người quen | video_card_v2 |
| steps/step4.py:621 | ("↻ Gen lại theo ảnh/prompt mới" if stale_reason else "↻ Gen lại video… | nút | Gen lại video | $ video | giá trên nút | chuyên gia/người quen | video_card_v2 · xám khi: bool(gerr) |
| steps/step4.py:631 | ↻ Gen lại | nút | (video_card_v2) | 0 USD | — | chuyên gia/người quen | video_card_v2 · xám khi: True |
| steps/step4.py:635 | ✏ Sửa motion prompt | nút | (video_card_v2) | 0 USD | — | chuyên gia/người quen | video_card_v2 |
| steps/step4.py:639 | ✖ Loại & gen lại" + tag | nút | Loại | $ video | giá trên nút | chuyên gia/người quen | video_card_v2 · xám khi: not reviewable or bool(rerr) |
| steps/step4.py:655 | ■ Hủy | nút | Hủy job | 0 USD | — | chuyên gia/người quen | video_card_v2 |
| steps/step4.py:659 | 🔎 Tìm task thật (không gửi lại) | nút | Tìm task thật | 0 USD | — | chuyên gia/người quen | video_card_v2 |
| steps/step4.py:668 | ↺ Làm lại từ đầu" + tag | nút | Làm lại job từ đầu | $ video | giá trên nút | chuyên gia/người quen | video_card_v2 |
| steps/step4.py:682 | ✔ Vẫn dùng bản này | nút | Giữ clip QC đã loại | 0 USD | — | chuyên gia/người quen | video_card_v2 |
| steps/step4.py:720 | S{members[k]['idx']:02d} → S{members[k + 1]['idx']:02d} (giây) | ô số | Nhập: S{members[k]['idx']:02d} → S{members[k + 1]['idx']… | 0 USD | — | chuyên gia/người quen | group_cut_panel |
| steps/step4.py:723 | ✂ Cắt lại theo số giây này (0 USD) | nút | Cắt lại clip nhóm | 0 USD | — | chuyên gia/người quen | group_cut_panel |
| steps/step4.py:736 | 🎞 Ghép xem bản nháp (0 USD) | nút | Ghép bản nháp | 0 USD | — | chuyên gia/người quen | _draft_preview |
| steps/step4.py:747 | ✖ Thu gọn | nút | (_draft_preview) | 0 USD | — | chuyên gia/người quen | _draft_preview |
| steps/step4.py:834 | v{n} | nút | (_take_strip) | 0 USD | — | chuyên gia/người quen | _take_strip |
| steps/step4.py:849 | ✔ Dùng bản này cho shot | nút | Chọn bản clip | 0 USD | — | chuyên gia/người quen | _take_strip |
| steps/step4.py:870 | Nhóm cảnh | hộp chọn | Chọn: Nhóm cảnh | 0 USD | — | chuyên gia | experiments_panel |
| steps/step4.py:874 | 🧪 Gen thử multi-shot (s, ≈ $) | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | $ video | giá trên nút, hỏi Có/Không | chuyên gia | Chuyên gia, cờ thử nghiệm multi-shot |
| steps/step4.py:879 | ⟳ Kiểm tra thử nghiệm | nút | Hỏi trạng thái + tải kết quả | 0 USD | — | chuyên gia | experiments_panel |
| steps/step4.py:899 | Shot thử độ nét | hộp chọn | Chọn: Shot thử độ nét | 0 USD | — | chuyên gia/người quen | quality_samples_panel |
| steps/step4.py:911 | Gen <A/B/C độ nét> · ≈ $ | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | $ video | giá trên nút, hỏi Có/Không | người mới | cờ seedance_sample_mode (ON) |
| steps/step4.py:919 | ⟳ Lấy kết quả thử độ nét | nút | Hỏi trạng thái + tải kết quả | 0 USD | — | chuyên gia/người quen | quality_samples_panel |
| video_gate_ui.py:29 | Lý do bỏ qua | ô chữ | Nhập: Lý do bỏ qua | 0 USD | — | chuyên gia/người quen | render |
| video_gate_ui.py:30 | Bỏ qua kiểm nền | nút | Bỏ qua cổng có lý do | 0 USD | — | chuyên gia/người quen | render · xám khi: len(reason.strip()) < 3 |
| video_gate_ui.py:45 | Lý do gửi không chờ nhóm | ô chữ | Nhập: Lý do gửi không chờ nhóm | 0 USD | — | chuyên gia/người quen | _render_groups |
| video_gate_ui.py:47 | Bỏ qua chờ nhóm | nút | Bỏ qua cổng có lý do | 0 USD | — | chuyên gia/người quen | _render_groups · xám khi: len(reason.strip()) < 3 |
| widgets.py:113 | ⏱ Tự tăng thời lượng {len(fixable)} clip cho vừa thoại | nút | Tăng thời lượng clip | 0 USD | — | chuyên gia/người quen | dialogue_panel |

### ⑤ Bản giao — 117 điều khiển

| file:dòng | Nhãn | Loại | Việc làm | Tiền | Giá / xác nhận | Ai dùng | Điều kiện hiện |
|---|---|---|---|---|---|---|---|
| motion_sfx_ui.py:10 | 'Lập gợi ý theo nhịp · code 0 USD' | nút | (render) | 0 USD | — | chuyên gia/người quen | render · xám khi: not editable |
| steps/step5.py:30 | Tìm trong Kho âm thanh / thư mục dự án | ô chữ | Nhập: Tìm trong Kho âm thanh / thư mục dự án | 0 USD | — | chuyên gia/người quen | music_pick_box |
| steps/step5.py:36 | Chọn bản nhạc | hộp chọn | Chọn: Chọn bản nhạc | 0 USD | — | chuyên gia/người quen | music_pick_box |
| steps/step5.py:37 | Dùng làm nhạc đoạn 2" if second else "Dùng làm nhạc nền | nút | Chọn nhạc nền | 0 USD | — | chuyên gia/người quen | music_pick_box |
| steps/step5.py:52 | Nhạc đoạn 2 vào ở giây | ô số | Nhập: Nhạc đoạn 2 vào ở giây | 0 USD | — | chuyên gia/người quen | second_music_box |
| steps/step5.py:56 | Bỏ nhạc đoạn 2 | nút | (second_music_box) | 0 USD | — | chuyên gia/người quen | second_music_box |
| steps/step5.py:60 | ↪ Chuyển nhạc nền đang chọn thành nhạc đoạn 2 | nút | (second_music_box) | 0 USD | — | chuyên gia/người quen | second_music_box |
| steps/step5.py:65 | Tải nhạc đoạn 2 | tải tệp | Tải tệp lên | 0 USD | — | chuyên gia/người quen | second_music_box |
| steps/step5.py:66 | Dùng làm nhạc đoạn 2 | nút | (second_music_box) | 0 USD | — | chuyên gia/người quen | second_music_box |
| steps/step5.py:97 | 🎬 Xem thử với video | nút | Ghép xem thử nhạc | 0 USD | — | chuyên gia/người quen | step5a |
| steps/step5.py:101 | Tải nhạc nền | tải tệp | Tải tệp lên | 0 USD | — | chuyên gia/người quen | step5a |
| steps/step5.py:102 | Dùng bản này | nút | Tắt nhạc | 0 USD | — | chuyên gia/người quen | step5a |
| steps/step5.py:108 | Không dùng nhạc | nút | Tắt nhạc | 0 USD | — | chuyên gia/người quen | step5a · xám khi: off and not files |
| steps/step5.py:131 | 🤖 Claude viết brief nhạc" + cost.llm_tag(cost.llm_estimate(p.conn, "mu… | nút | (step5a) | $ Claude | giá trên nút | chuyên gia/người quen | step5a · xám khi: client is None |
| steps/step5.py:152 | Prompt nhạc (≤ 2000 ký tự) | ô chữ lớn | Nhập: Prompt nhạc (≤ 2000 ký tự) | 0 USD | — | chuyên gia/người quen | step5a |
| steps/step5.py:154 | Độ dài (giây) | ô số | Nhập: Độ dài (giây) | 0 USD | — | chuyên gia/người quen | step5a |
| steps/step5.py:155 | Không lời (instrumental) | ô tick | Bật/tắt: Không lời (instrumental) | 0 USD | — | chuyên gia/người quen | step5a |
| steps/step5.py:156 | Số bản nháp | ô số | Nhập: Số bản nháp | 0 USD | — | chuyên gia/người quen | step5a |
| steps/step5.py:158 | ✨ Tạo {int(count)} bản nháp" + budget.audio_tag(p.conn, int(count), "m… | nút | Tạo nhạc nháp | $ âm thanh | giá trên nút | chuyên gia/người quen | step5a · xám khi: not prompt.strip() |
| steps/step5.py:163 | ⟳ Kiểm tra + tải nhạc về | nút | (step5a) | 0 USD | — | chuyên gia/người quen | step5a |
| steps/step5.py:182 | 🎬 Xem thử với video | nút | Ghép xem thử nhạc | 0 USD | — | chuyên gia/người quen | step5a |
| steps/step5.py:184 | Chọn bản này | nút | Chọn bản nhạc | 0 USD | — | chuyên gia/người quen | step5a |
| steps/step5.py:190 | Xóa danh sách bản nháp | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | chuyên gia/người quen | step5a |
| steps/step5.py:206 | Mô tả hiệu ứng (≤ 2000 ký tự) | ô chữ | Nhập: Mô tả hiệu ứng (≤ 2000 ký tự) | 0 USD | — | chuyên gia | extras_section |
| steps/step5.py:209 | Độ dài (giây, 0.5–30) | ô số | Nhập: Độ dài (giây, 0.5–30) | 0 USD | — | chuyên gia | extras_section |
| steps/step5.py:210 | Loop | ô tick | Bật/tắt: Loop | 0 USD | — | chuyên gia | extras_section |
| steps/step5.py:211 | ✨ Tạo SFX" + budget.audio_tag(p.conn, 1, "eleven_text_to_sound_v2") | nút | Tạo SFX | $ âm thanh | giá trên nút | chuyên gia | extras_section · xám khi: not s_prompt.strip() |
| steps/step5.py:227 | Giọng | hộp chọn | Chọn: Giọng | 0 USD | — | chuyên gia | extras_section |
| steps/step5.py:229 | Nội dung (≤ 2000 ký tự) | ô chữ lớn | Nhập: Nội dung (≤ 2000 ký tự) | 0 USD | — | chuyên gia | extras_section |
| steps/step5.py:231 | Model | hộp chọn | Chọn: Model | 0 USD | — | chuyên gia | extras_section |
| steps/step5.py:233 | Mã ngôn ngữ (tùy chọn, vd vi, en) | ô chữ | Nhập: Mã ngôn ngữ (tùy chọn, vd vi, en) | 0 USD | — | chuyên gia | extras_section |
| steps/step5.py:234 | ✨ Tạo giọng đọc" + budget.audio_tag(p.conn) | nút | Tạo giọng | $ âm thanh | giá trên nút | chuyên gia | extras_section · xám khi: not t_text.strip() |
| steps/step5.py:239 | ⟳ Kiểm tra + tải về | nút | Hỏi trạng thái + tải kết quả | 0 USD | — | chuyên gia | extras_section |
| steps/step5.py:247 | 🗓 Xếp lại theo thoại (hết chồng tiếng) | nút | (extras_section) | 0 USD | — | chuyên gia | extras_section |
| steps/step5.py:256 | 🎥 Lấy tiếng {n_ref} video tham chiếu làm SFX của shot (0 USD, chỉ đề x… | nút | Đề xuất | 0 USD | — | chuyên gia | extras_section |
| steps/step5.py:295 | Đưa vào bản ghép | ô tick | Bật/tắt: Đưa vào bản ghép | 0 USD | — | chuyên gia | extras_section · xám khi: e["state"] != "succeeded |
| steps/step5.py:296 | Bắt đầu (giây) | ô số | Nhập: Bắt đầu (giây) | 0 USD | — | chuyên gia | extras_section |
| steps/step5.py:297 | Âm lượng | thanh trượt | Chọn: Âm lượng | 0 USD | — | chuyên gia | extras_section |
| steps/step5.py:298 | Xóa | nút | (extras_section) | 0 USD | — | chuyên gia | extras_section |
| steps/step5.py:339 | Ngôn ngữ phụ đề | hộp chọn | Chọn: Ngôn ngữ phụ đề | 0 USD | — | chuyên gia/người quen | subtitle_panel |
| steps/step5.py:343 | Font | hộp chọn | Chọn: Font | 0 USD | — | chuyên gia/người quen | subtitle_panel |
| steps/step5.py:345 | Cỡ chữ | hộp chọn | Chọn: Cỡ chữ | 0 USD | — | chuyên gia/người quen | subtitle_panel |
| steps/step5.py:348 | Vị trí | hộp chọn | Chọn: Vị trí | 0 USD | — | chuyên gia/người quen | subtitle_panel |
| steps/step5.py:350 | Màu chữ | hộp chọn | Chọn: Màu chữ | 0 USD | — | chuyên gia/người quen | subtitle_panel |
| steps/step5.py:352 | Ghi tên người nói trước câu | ô tick | Bật/tắt: Ghi tên người nói trước câu | 0 USD | — | chuyên gia/người quen | subtitle_panel |
| steps/step5.py:353 | Mỗi nhân vật một màu | ô tick | Bật/tắt: Mỗi nhân vật một màu | 0 USD | — | chuyên gia/người quen | subtitle_panel |
| steps/step5.py:355 | Vùng an toàn theo nền tảng đăng | hộp chọn | Chọn: Vùng an toàn theo nền tảng đăng | 0 USD | — | chuyên gia/người quen | subtitle_panel |
| steps/step5.py:359 | Chữ sáng dần theo giọng (kiểu video ngắn) | ô tick | Bật/tắt: Chữ sáng dần theo giọng (kiểu video ngắn) | 0 USD | — | chuyên gia/người quen | subtitle_panel |
| steps/step5.py:361 | SUB_AUTO_LABEL | ô tick | Bật/tắt: SUB_AUTO_LABEL | 0 USD | — | chuyên gia/người quen | subtitle_panel |
| steps/step5.py:366 | Thêm font riêng (.ttf / .otf) | tải tệp | Tải tệp lên | 0 USD | — | chuyên gia/người quen | subtitle_panel |
| steps/step5.py:367 | Thêm font này | nút | (subtitle_panel) | 0 USD | — | chuyên gia/người quen | subtitle_panel |
| steps/step5.py:377 | 📝 Tạo danh sách phụ đề" + (cost.llm_tag(cost.llm_estimate(p.conn, "sub… | nút | (subtitle_panel) | $ Claude (chỉ khi dịch phụ đề) | giá trên nút | chuyên gia/người quen | subtitle_panel · xám khi: lang != "src" and llm is None |
| steps/step5.py:418 | ⬇ File .srt | nút tải | Tải file về máy | 0 USD | — | chuyên gia/người quen | subtitle_panel |
| steps/step5.py:420 | ⬇ Bảng duyệt .xlsx | nút tải | Tải file về máy | 0 USD | — | chuyên gia/người quen | subtitle_panel |
| steps/step5.py:422 | 🔥 In phụ đề vào video | nút | In phụ đề | 0 USD | — | chuyên gia/người quen | subtitle_panel · xám khi: not has_final or bool(bad) |
| steps/step5.py:453 | Yêu cầu thêm (không bắt buộc) | ô chữ | Nhập: Yêu cầu thêm (không bắt buộc) | 0 USD | — | chuyên gia/người quen | sfx_assistant |
| steps/step5.py:459 | 🤖 AI tự đề xuất hiệu ứng" + cost.llm_tag(cost.llm_estimate(p.conn, "sf… | nút | Đề xuất | $ Claude | giá trên nút | chuyên gia/người quen | sfx_assistant |
| steps/step5.py:492 | ✅ Thêm các hiệu ứng đã chọn vào video | nút | Áp đề xuất | 0 USD | — | chuyên gia/người quen | sfx_assistant · xám khi: stale or not access.can_edit(p.conn, pid… |
| steps/step5.py:509 | Bỏ đề xuất | nút | (sfx_assistant) | 0 USD | — | chuyên gia/người quen | sfx_assistant |
| steps/step5.py:514 | Nhạc nền: ưu tiên lấy từ kho của tôi thay vì để AI tạo (tiết kiệm cred… | ô tick | Bật/tắt: Nhạc nền: ưu tiên lấy từ kho của tôi thay vì để AI… | 0 USD | — | chuyên gia/người quen | sfx_assistant · xám khi: music.is_off(p, pid) |
| steps/step5.py:586 | SUB_AUTO_LABEL | ô tick | Bật/tắt: SUB_AUTO_LABEL | 0 USD | — | chuyên gia/người quen | step5_v2 |
| steps/step5.py:587 | CARD_ON_LABEL | ô tick | Bật/tắt: CARD_ON_LABEL | 0 USD | — | chuyên gia/người quen | step5_v2 |
| steps/step5.py:588 | Kích thước | hộp chọn | Chọn: Kích thước | 0 USD | — | chuyên gia/người quen | step5_v2 |
| steps/step5.py:718 | label + note + (" · ⚠ cũ" if srow.get("video_stale") else "") | ô tick | Bật/tắt: label + note + (" · ⚠ cũ" if srow.get("video_stale… | 0 USD | — | chuyên gia | clips_panel |
| steps/step5.py:719 | Giây | ô số | Nhập: Giây | 0 USD | — | chuyên gia | clips_panel |
| steps/step5.py:720 | Xem | ô tick | Bật/tắt: Xem | 0 USD | — | chuyên gia | clips_panel |
| steps/step5.py:729 | Clip .mp4 | tải tệp | Tải tệp lên | 0 USD | — | chuyên gia | clips_panel |
| steps/step5.py:730 | Lưu clip | nút | (clips_panel) | 0 USD | — | chuyên gia | clips_panel |
| steps/step5.py:753 | Chuyển cảnh | radio | Chọn: Chuyển cảnh | 0 USD | — | chuyên gia/người quen | render_panel |
| steps/step5.py:755 | Thời gian chuyển cảnh (giây) | thanh trượt | Chọn: Thời gian chuyển cảnh (giây) | 0 USD | — | chuyên gia/người quen | render_panel · xám khi: transition == "cut |
| steps/step5.py:756 | Âm lượng nhạc nền | thanh trượt | Chọn: Âm lượng nhạc nền | 0 USD | — | chuyên gia/người quen | render_panel · xám khi: not track |
| steps/step5.py:757 | Nhạc bắt đầu ở giây | ô số | Nhập: Nhạc bắt đầu ở giây | 0 USD | — | chuyên gia/người quen | render_panel · xám khi: not track |
| steps/step5.py:759 | 🥁 Máy nhún theo nhịp nhạc (zoom vào nhẹ + rung nhẹ ở mỗi nhịp) | ô tick | Bật/tắt: 🥁 Máy nhún theo nhịp nhạc (zoom vào nhẹ + rung nhẹ… | 0 USD | — | chuyên gia/người quen | render_panel · xám khi: not track |
| steps/step5.py:762 | 🔊 Giữ âm thanh gốc của clip (tiếng động do model tạo) | ô tick | Bật/tắt: 🔊 Giữ âm thanh gốc của clip (tiếng động do model t… | 0 USD | — | chuyên gia/người quen | render_panel |
| steps/step5.py:784 | ▶ Dựng video cuối | nút | Dựng video (ffmpeg) | 0 USD | — | chuyên gia/người quen | render_panel · xám khi: bool(problems) |
| steps/step5.py:806 | 🧐 Tự rà như người xem (chồng vùng giao diện app + bản cỡ điện thoại) | nút | (viewer_check_panel) | 0 USD | — | chuyên gia/người quen | viewer_check_panel |
| steps/step5.py:836 | 📏 Đo bản dựng thô so với ý đồ Đạo diễn | nút | Dựng/đo | 0 USD | — | chuyên gia/người quen | rough_cut_panel |
| steps/step5.py:861 | label | nút | (editor_review_panel) | $ Claude | giá trên nút | chuyên gia/người quen | editor_review_panel · xám khi: not n_img |
| steps/step5.py:897 | label | ô tick | Bật/tắt: label | 0 USD | — | chuyên gia/người quen | editor_apply_panel |
| steps/step5.py:899 | ▶ Áp {len(chosen)} đề xuất đã chọn và dựng lại (miễn phí) | nút | Áp đề xuất | 0 USD | — | chuyên gia/người quen | editor_apply_panel · xám khi: not chosen |
| steps/step5.py:927 | ↩️ Quay về bản trước (A) | nút | Quay về bản trước | 0 USD | — | chuyên gia/người quen | editor_apply_state |
| steps/step5.py:959 | 🖼 Lấy ảnh bìa từ bản dựng mới nhất (miễn phí) | nút | Lấy ảnh bìa | 0 USD | — | chuyên gia/người quen | cover_panel |
| steps/step5.py:972 | CARD_ON_LABEL | ô tick | Bật/tắt: CARD_ON_LABEL | 0 USD | — | chuyên gia/người quen | end_card_panel |
| steps/step5.py:973 | Dòng chính | ô chữ | Nhập: Dòng chính | 0 USD | — | chuyên gia/người quen | end_card_panel |
| steps/step5.py:974 | Dòng phụ (tùy chọn) | ô chữ | Nhập: Dòng phụ (tùy chọn) | 0 USD | — | chuyên gia/người quen | end_card_panel |
| steps/step5.py:976 | Thời lượng (giây) | ô số | Nhập: Thời lượng (giây) | 0 USD | — | chuyên gia/người quen | end_card_panel |
| steps/step5.py:982 | 🪧 Thêm card vào bản mới nhất | nút | Thêm card cuối | 0 USD | — | chuyên gia/người quen | end_card_panel · xám khi: not (title or subtitle) |
| steps/step5.py:1001 | 'Chọn shot' | hộp chọn | Chọn: 'Chọn shot' | 0 USD | — | chuyên gia/người quen | shot_popup_panel |
| steps/step5.py:1014 | 'Bật popup' | ô tick | Bật/tắt: 'Bật popup' | 0 USD | — | chuyên gia/người quen | shot_popup_panel · xám khi: readonly |
| steps/step5.py:1019 | 'Ảnh Kho' | hộp chọn | Chọn: 'Ảnh Kho' | 0 USD | — | chuyên gia/người quen | shot_popup_panel · xám khi: readonly or not enabled |
| steps/step5.py:1028 | 'Giây' | ô số | Nhập: 'Giây' | 0 USD | — | chuyên gia/người quen | shot_popup_panel · xám khi: readonly or not enabled |
| steps/step5.py:1030 | 'Tách nền xanh nối với viền ảnh' | ô tick | Bật/tắt: 'Tách nền xanh nối với viền ảnh' | 0 USD | — | chuyên gia/người quen | shot_popup_panel · xám khi: readonly |
| steps/step5.py:1037 | Lưu popup shot {row['idx']}" if enabled else f"Bỏ popup shot {row['idx… | nút | Lưu | 0 USD | — | chuyên gia/người quen | shot_popup_panel · xám khi: readonly or (enabled and not asset_id) |
| steps/step5.py:1053 | ✨ Lấy từ icon của dự án | nút | Lưu thiết lập | 0 USD | — | chuyên gia/người quen | end_popup_panel |
| steps/step5.py:1064 | Chữ dưới icon {i + 1}" + (f" (#{it['asset_id']})" if it.get("asset_id"… | ô chữ | Nhập: Chữ dưới icon {i + 1}" + (f" (#{it['asset_id']})" … | 0 USD | — | chuyên gia/người quen | end_popup_panel |
| steps/step5.py:1068 | Dòng lớn | ô chữ | Nhập: Dòng lớn | 0 USD | — | chuyên gia/người quen | end_popup_panel |
| steps/step5.py:1069 | Giây cuối | ô số | Nhập: Giây cuối | 0 USD | — | chuyên gia/người quen | end_popup_panel |
| steps/step5.py:1071 | VIẾT HOA (giữ dấu) | ô tick | Bật/tắt: VIẾT HOA (giữ dấu) | 0 USD | — | chuyên gia/người quen | end_popup_panel |
| steps/step5.py:1072 | Cỡ chữ × | ô số | Nhập: Cỡ chữ × | 0 USD | — | chuyên gia/người quen | end_popup_panel |
| steps/step5.py:1076 | Tiếng pop | ô tick | Bật/tắt: Tiếng pop | 0 USD | — | chuyên gia/người quen | end_popup_panel |
| steps/step5.py:1078 | File tiếng pop (để trống = tự lấy tiếng pop ≤ 0,5 s trong Kho âm thanh… | ô chữ | Nhập: File tiếng pop (để trống = tự lấy tiếng pop ≤ 0,5 … | 0 USD | — | chuyên gia/người quen | end_popup_panel · xám khi: not pop_on |
| steps/step5.py:1080 | Âm lượng pop | ô số | Nhập: Âm lượng pop | 0 USD | — | chuyên gia/người quen | end_popup_panel · xám khi: not pop_on |
| steps/step5.py:1091 | ✖ Bỏ popup | nút | Lưu thiết lập | 0 USD | — | chuyên gia/người quen | end_popup_panel |
| steps/step5.py:1112 | Bỏ | nút | Lưu thiết lập | 0 USD | — | chuyên gia/người quen | exports_panel |
| steps/step5.py:1116 | Kích thước | hộp chọn | Chọn: Kích thước | 0 USD | — | chuyên gia/người quen | exports_panel |
| steps/step5.py:1117 | Cách vừa khung | hộp chọn | Chọn: Cách vừa khung | 0 USD | — | chuyên gia/người quen | exports_panel |
| steps/step5.py:1119 | Tối đa MB (0 = không) | ô số | Nhập: Tối đa MB (0 = không) | 0 USD | — | chuyên gia/người quen | exports_panel |
| steps/step5.py:1122 | ➕ Thêm vào danh sách xuất bản | nút | Lưu thiết lập | 0 USD | — | chuyên gia/người quen | exports_panel |
| steps/step5.py:1125 | Xuất ngay bản này | nút | Xuất kích thước khác | 0 USD | — | chuyên gia/người quen | exports_panel |
| steps/step5.py:1143 | label | nút | Dựng → phụ đề → card → các kích thước (một bản giao) | $ Claude (chỉ dịch phụ đề; còn lại ffmpeg 0 USD) | giá trên nút | người mới | luôn (xám khi chưa chọn clip) |
| steps/step5.py:1198 | ⬇ Tải {name} | nút tải | Tải file bản giao | 0 USD | — | người mới | _deliver_files |
| steps/step5.py:1204 | ⬇ Tải | nút tải | Tải file bản giao | 0 USD | — | người mới | _deliver_files |
| steps/step5.py:1249 | Bản này dùng được chứ? | radio | Chọn: Bản này dùng được chứ? | 0 USD | — | chuyên gia/người quen | _delivery_feedback_form |
| steps/step5.py:1252 | Chỗ nào chưa ổn? | ô chữ lớn | Nhập: Chỗ nào chưa ổn? | 0 USD | — | chuyên gia/người quen | _delivery_feedback_form |
| steps/step5.py:1253 | Khâu | hộp chọn | Chọn: Khâu | 0 USD | — | chuyên gia/người quen | _delivery_feedback_form |
| steps/step5.py:1255 | 💬 Gửi góp ý | nút form | (_delivery_feedback_form) | 0 USD | — | chuyên gia/người quen | _delivery_feedback_form |
| steps/step5.py:1273 | 🔎 Kiểm bản dựng (miễn phí, ~30 s) | nút | (_final_qc) | 0 USD | — | chuyên gia/người quen | _final_qc |

### ⑥ Thanh trên · ⚙ Cài đặt · 💵 · 🧪 — 124 điều khiển

| file:dòng | Nhãn | Loại | Việc làm | Tiền | Giá / xác nhận | Ai dùng | Điều kiện hiện |
|---|---|---|---|---|---|---|---|
| access_ui.py:128 | Mức | hộp chọn | Chọn: Mức | 0 USD | — | quản trị | watchers_editor |
| access_ui.py:132 | Bỏ | nút | (watchers_editor) | 0 USD | — | quản trị | watchers_editor |
| access_ui.py:141 | Thêm người theo dõi | hộp chọn | Chọn: Thêm người theo dõi | 0 USD | — | quản trị | watchers_editor |
| access_ui.py:142 | Mức | hộp chọn | Chọn: Mức | 0 USD | — | quản trị | watchers_editor |
| access_ui.py:144 | Thêm | nút | (watchers_editor) | 0 USD | — | quản trị | watchers_editor |
| access_ui.py:173 | Dự án | hộp chọn | Chọn: Dự án | 0 USD | — | quản trị | team_panel |
| access_ui.py:181 | Dự án cũ | hộp chọn | Chọn: Dự án cũ | 0 USD | — | quản trị | team_panel |
| access_ui.py:183 | Gán chủ | hộp chọn | Chọn: Gán chủ | 0 USD | — | quản trị | team_panel |
| access_ui.py:184 | Gán | nút | (team_panel) | 0 USD | — | quản trị | team_panel |
| app.py:201 | Màn | radio | Chọn: Màn | 0 USD | — | mọi người | main |
| chat_start.py:54 | Bắt đầu dự án mới… | khung chat | Nhập: Bắt đầu dự án mới… | 0 USD | — | mọi người | start_box |
| common.py:176 | Tôi xác nhận batch {est['items']} mục này sẽ tốn credit | ô tick | Bật/tắt: Tôi xác nhận batch {est['items']} mục này sẽ tốn c… | 0 USD | — | mọi người | _confirm_big_batch |
| design/components.py:284 | label | nút | (confirm_all) | 0 USD | — | mọi người | confirm_all · xám khi: not ids |
| design/components.py:289 | label | nút | (confirm_all) | 0 USD | — | mọi người | confirm_all · xám khi: not ids |
| design/components.py:295 | yes_label | nút | (confirm_all) | 0 USD | — | mọi người | confirm_all |
| design/components.py:298 | Không | nút | (confirm_all) | 0 USD | — | mọi người | confirm_all |
| design/components.py:316 | label | nút | (cta) | 0 USD | — | mọi người | cta |
| design/screens/money_days.py:17 | 📅 Mức dùng theo ngày · đợt ngân sách | nút | Mở hộp thoại | 0 USD | — | quản trị | open_button |
| design/screens/money_days.py:82 | Tên đợt mới | ô chữ | Nhập: Tên đợt mới | 0 USD | — | quản trị | new_round_block |
| design/screens/money_days.py:84 | Mức dự tính tổng (USD) | ô số | Nhập: Mức dự tính tổng (USD) | 0 USD | — | quản trị | new_round_block |
| design/screens/money_days.py:85 | Mức dự tính Claude API (USD) | ô số | Nhập: Mức dự tính Claude API (USD) | 0 USD | — | quản trị | new_round_block |
| design/screens/money_days.py:89 | Đặt lại thanh của {len(targets['projects'])} dự án đang có ngân sách | ô tick | Bật/tắt: Đặt lại thanh của {len(targets['projects'])} dự án… | 0 USD | — | quản trị | new_round_block |
| design/screens/money_days.py:91 | Mức dự tính dự án #{tpid} (USD) | ô số | Nhập: Mức dự tính dự án #{tpid} (USD) | 0 USD | — | quản trị | new_round_block |
| design/screens/money_days.py:95 | Đặt lại thanh theo người ({len(targets['users'])} người) | ô tick | Bật/tắt: Đặt lại thanh theo người ({len(targets['users'])} … | 0 USD | — | quản trị | new_round_block |
| design/screens/money_days.py:97 | Lý do (bắt buộc) | ô chữ | Nhập: Lý do (bắt buộc) | 0 USD | — | quản trị | new_round_block |
| design/screens/money_days.py:104 | ▶ Đóng đợt hiện tại & mở đợt mới | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | quản trị | new_round_block |
| design/screens/money_days.py:121 | ▶ Bắt đầu đợt thử (tính từ bây giờ) | nút | (trial_start_button) | 0 USD | — | quản trị | trial_start_button · xám khi: True |
| design/screens/money_days.py:126 | Lý do mở đợt thử mới (bắt buộc) | ô chữ | Nhập: Lý do mở đợt thử mới (bắt buộc) | 0 USD | — | quản trị | trial_start_button |
| design/screens/money_days.py:128 | ▶ Bắt đầu đợt thử (tính từ bây giờ) | nút | (trial_start_button) | 0 USD | — | quản trị | trial_start_button |
| design/screens/money_days.py:149 | Đợt | hộp chọn | Chọn: Đợt | 0 USD | — | quản trị | body |
| design/screens/money_days.py:155 | Dự án | hộp chọn | Chọn: Dự án | 0 USD | — | quản trị | body |
| design/screens/money_days.py:170 | Xem từng dòng sổ chi của ngày | hộp chọn | Chọn: Xem từng dòng sổ chi của ngày | 0 USD | — | quản trị | body |
| design/screens/shell_parts.py:216 | ↺ Đặt lại 2 thanh về 0 | nút | (reset_two_button) | 0 USD | — | quản trị | reset_two_button · xám khi: True |
| design/screens/shell_parts.py:219 | ↺ Đặt lại 2 thanh về 0 (Owner) | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | quản trị | reset_two_button |
| glow_ui.py:59 | ✨ Nút bước kế sáng xanh | công tắc | Bật/tắt: ✨ Nút bước kế sáng xanh | 0 USD | — | mọi người | person_switch |
| header.py:28 | Phạm vi | radio | Chọn: Phạm vi | 0 USD | — | mọi người | inbox_card |
| header.py:33 | Loại việc | hộp chọn | Chọn: Loại việc | 0 USD | — | mọi người | inbox_card |
| header.py:47 | Mở → | nút | (draw) | 0 USD | — | mọi người | draw |
| header.py:101 | Mức tự động | radio | Chọn: Mức tự động | Mức tự động: quyết định cổng dừng/QC tự duyệt → ảnh hưởng chi | KHÔNG | mọi người | level_bar · xám khi: busy or not can |
| header.py:159 | Màn “{screen or 'này'}” chưa ổn chỗ nào? | ô chữ lớn | Nhập: Màn “{screen or 'này'}” chưa ổn chỗ nào? | 0 USD | — | mọi người | _screen_feedback_body |
| header.py:160 | Khâu | hộp chọn | Chọn: Khâu | 0 USD | — | mọi người | _screen_feedback_body |
| header.py:162 | 💬 Gửi góp ý | nút form | (_screen_feedback_body) | 0 USD | — | mọi người | _screen_feedback_body |
| header.py:208 | E-mail của bạn | ô chữ | Nhập: E-mail của bạn | 0 USD | — | mọi người | login_screen |
| header.py:211 | Mã Owner (khi đăng nhập Owner từ máy khác) | ô chữ | Nhập: Mã Owner (khi đăng nhập Owner từ máy khác) | 0 USD | — | mọi người | login_screen |
| header.py:212 | Vào Dashboard | nút | (login_screen) | 0 USD | — | mọi người | login_screen |
| header.py:290 | Tên dự án | ô chữ | Nhập: Tên dự án | 0 USD | — | mọi người | new_project_control |
| header.py:292 | Tỉ lệ khung | hộp chọn | Chọn: Tỉ lệ khung | 0 USD | — | mọi người | new_project_control |
| header.py:295 | Thể loại | hộp chọn | Chọn: Thể loại | 0 USD | — | mọi người | new_project_control |
| header.py:299 | Ưu tiên model video | hộp chọn | Chọn: Ưu tiên model video | 0 USD | — | mọi người | new_project_control |
| header.py:303 | Game / nội dung | hộp chọn | Chọn: Game / nội dung | 0 USD | — | mọi người | new_project_control |
| header.py:305 | Tạo dự án | nút | (new_project_control) | 0 USD | — | mọi người | new_project_control · xám khi: not (st.session_state.get("new_name") or… |
| header.py:351 | ↩ Khôi phục | nút | (_archived_rows) | 0 USD | — | mọi người | _archived_rows |
| header.py:362 | 🗑 Xóa hẳn dự án | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | mọi người | archived_list |
| header.py:398 | 📁 Kho tài nguyên | nút | Mở hộp thoại | 0 USD | — | mọi người | settings_menu |
| header.py:400 | 📚 Kho kiến thức | nút | Mở hộp thoại | 0 USD | — | mọi người | settings_menu |
| header.py:402 | 🎓 Bài học | nút | Mở hộp thoại | 0 USD | — | mọi người | settings_menu |
| header.py:405 | 🌙 Nền tối | công tắc | Bật/tắt: 🌙 Nền tối | 0 USD | — | mọi người | settings_menu |
| header.py:409 | 🧠 Chế độ chuyên gia | công tắc | Bật/tắt: 🧠 Chế độ chuyên gia | 0 USD | — | mọi người | settings_menu |
| header.py:414 | 🧪 Tính năng thử | nút | Mở hộp thoại | 0 USD | — | mọi người | settings_menu |
| header.py:417 | 📏 Giới hạn hệ thống | nút | Mở hộp thoại | 0 USD | — | mọi người | settings_menu |
| header.py:420 | 🗒 Lịch sử & thùng rác | nút | Mở hộp thoại | 0 USD | — | mọi người | settings_menu |
| header.py:422 | 👥 Phân quyền | nút | Mở hộp thoại | 0 USD | — | mọi người | settings_menu |
| header.py:425 | ⏻ Tắt Dashboard | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | mọi người | settings_menu |
| header.py:468 | Ai duyệt ảnh/clip | radio | Chọn: Ai duyệt ảnh/clip | 0 USD | — | mọi người | _settings_project_body |
| header.py:484 | 🧪 Thử rẻ" if v2 else "🧪 Thử rẻ (ảnh cỡ nhỏ nhất · 720p · Kling std · S… | ô tick | Bật/tắt: 🧪 Thử rẻ" if v2 else "🧪 Thử rẻ (ảnh cỡ nhỏ nhất · … | Thử rẻ: đổi mức giá (bị vô hiệu khi two_tier_quality bật) | KHÔNG | người mới | ⚙ › Dự án; xám khi cờ two_tier_quality ON |
| header.py:492 | 🧬 Nhân bản dự án (để so sánh cách làm) | nút | Mở hộp thoại | 0 USD | — | mọi người | _settings_project_body |
| header.py:497 | 📦 Cất dự án này | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | mọi người | _settings_project_body |
| header.py:556 | Đã nạp tiền — mở lại {service} | nút | (money_card) | 0 USD | — | mọi người | money_card |
| header.py:567 | Gói / tài khoản dùng được rồi — mở lại Claude ({kind}) | nút | (money_card) | 0 USD | — | mọi người | money_card |
| header.py:655 | ⚙ Đợt thử & Claude | nút | Mở hộp thoại | 0 USD | — | mọi người | money_card |
| header.py:657 | 💲 Bảng giá | nút | Mở hộp thoại | 0 USD | — | mọi người | money_card |
| header.py:664 | ⚙ Đợt thử & Claude | nút | Mở hộp thoại | 0 USD | — | mọi người | money_card |
| header.py:666 | 💲 Bảng giá | nút | Mở hộp thoại | 0 USD | — | mọi người | money_card |
| header.py:682 | Preset | radio | Chọn: Preset | 0 USD | — | quản trị | _dialog_features |
| header.py:697 | Tìm | ô chữ | Nhập: Tìm | 0 USD | — | quản trị | _dialog_features |
| header.py:698 | Chỉ tính năng chưa thử thật | ô tick | Bật/tắt: Chỉ tính năng chưa thử thật | 0 USD | — | quản trị | _dialog_features |
| header.py:723 | 🔒 Bật | công tắc | Bật/tắt: 🔒 Bật | 0 USD | — | quản trị | _dialog_features · xám khi: True |
| header.py:729 | Bật | công tắc | Bật/tắt: Bật | 0 USD | — | quản trị | _dialog_features |
| header.py:739 | ↺ Bỏ mọi lựa chọn riêng (theo preset) | nút | (_dialog_features) | 0 USD | — | quản trị | _dialog_features |
| header.py:749 | Có — sao lưu rồi bỏ | nút | (_dialog_features) | 0 USD | — | quản trị | _dialog_features |
| header.py:754 | Không | nút | (_dialog_features) | 0 USD | — | quản trị | _dialog_features |
| header.py:760 | Bản sao lưu | hộp chọn | Chọn: Bản sao lưu | 0 USD | — | quản trị | _dialog_features |
| header.py:762 | ↩ Khôi phục bản này (bản đang dùng được sao lưu trước) | nút | (_dialog_features) | 0 USD | — | quản trị | _dialog_features |
| header.py:811 | Ước tính cho video dài (giây) | ô số | Nhập: Ước tính cho video dài (giây) | 0 USD | — | quản trị | _dialog_limits |
| header.py:845 | Đã nạp tiền — mở lại {service} | nút | (_dialog_budget) | 0 USD | — | quản trị | _dialog_budget |
| header.py:860 | Trần (USD) | ô số | Nhập: Trần (USD) | 0 USD | — | quản trị | _dialog_budget |
| header.py:861 | Tối đa số ảnh Deepix (ảnh có giá tạm — cũng tính vào trần USD) | ô số | Nhập: Tối đa số ảnh Deepix (ảnh có giá tạm — cũng tính v… | 0 USD | — | quản trị | _dialog_budget |
| header.py:862 | Tối đa số âm thanh — giọng/nhạc/SFX (chưa có giá) | ô số | Nhập: Tối đa số âm thanh — giọng/nhạc/SFX (chưa có giá) | 0 USD | — | quản trị | _dialog_budget |
| header.py:867 | ■ Tắt giới hạn | nút | Dừng chạy tự động | 0 USD | — | quản trị | _dialog_budget |
| header.py:871 | 💾 Lưu trần mới (giữ mốc bắt đầu) | nút | Lưu | 0 USD | — | quản trị | _dialog_budget |
| header.py:882 | Số tiền đang có trên tài khoản Claude API (USD) | ô số | Nhập: Số tiền đang có trên tài khoản Claude API (USD) | 0 USD | — | quản trị | _dialog_budget |
| header.py:885 | 💾 Vừa nạp tiền — tính lại từ bây giờ | nút | (_dialog_budget) | 0 USD | — | quản trị | _dialog_budget |
| header.py:888 | 💾 Chỉ đổi trần (giữ số đã dùng) | nút | Lưu | 0 USD | — | quản trị | _dialog_budget |
| header.py:901 | Tên dự án mới | ô chữ | Nhập: Tên dự án mới | 0 USD | — | quản trị | _dialog_clone |
| header.py:903 | Cách chia cảnh của bản sao | hộp chọn | Chọn: Cách chia cảnh của bản sao | 0 USD | — | quản trị | _dialog_clone |
| header.py:905 | Giữ nguyên các cảnh/shot hiện tại (cùng kế hoạch của Director) | ô tick | Bật/tắt: Giữ nguyên các cảnh/shot hiện tại (cùng kế hoạch c… | 0 USD | — | quản trị | _dialog_clone |
| header.py:907 | 🧬 Tạo bản sao | nút | Nhân bản dự án | 0 USD | — | quản trị | _dialog_clone · xám khi: not name.strip() |
| header.py:958 | Đăng xuất | nút | Đăng xuất | 0 USD | — | mọi người | account_section |
| header.py:972 | 👤 Tên của bạn | ô chữ | Nhập: 👤 Tên của bạn | 0 USD | — | mọi người | user_bar |
| header.py:1018 | Dự án | hộp chọn | Chọn: Dự án | 0 USD | — | mọi người | global_bar |
| header.py:1029 | ▶ Tiếp tục | nút | Tạm dừng/tiếp tục dự án | 0 USD | — | mọi người | global_bar |
| header.py:1032 | ⏸ Tạm dừng | nút | Tạm dừng/tiếp tục dự án | 0 USD | — | mọi người | global_bar |
| header.py:1035 | ■ Hủy việc | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | mọi người | global_bar |
| header.py:1086 | Dự án | hộp chọn | Chọn: Dự án | 0 USD | — | mọi người | _global_bar_v2 |
| header.py:1099 | ▶ Tiếp tục | nút | Tạm dừng/tiếp tục dự án | 0 USD | — | mọi người | _global_bar_v2 |
| header.py:1104 | ⏸ Tạm dừng dự án | nút | Tạm dừng/tiếp tục dự án | 0 USD | — | mọi người | _global_bar_v2 |
| header.py:1107 | ■ Hủy việc đang chờ / đang gen | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | mọi người | _global_bar_v2 |
| limits_ui.py:124 | ↩ GIỮ — làm tiếp | nút | (panel) | 0 USD | — | quản trị | panel |
| limits_ui.py:126 | 📦 BỎ — cất | nút | (panel) | 0 USD | — | quản trị | panel |
| limits_ui.py:131 | Lý do cần thêm dự án hôm nay | ô chữ | Nhập: Lý do cần thêm dự án hôm nay | 0 USD | — | quản trị | panel |
| limits_ui.py:132 | 📨 Gửi yêu cầu cho Owner | nút | (panel) | 0 USD | — | quản trị | panel |
| limits_ui.py:139 | ↩ Khôi phục để làm | nút | (panel) | 0 USD | — | quản trị | panel |
| limits_ui.py:142 | Có, xóa hẳn | nút | (panel) | 0 USD | — | quản trị | panel |
| limits_ui.py:144 | 🗑 Xóa hẳn | nút | (panel) | 0 USD | — | quản trị | panel |
| limits_ui.py:148 | Hoặc xin Owner cho cất thêm — lý do | ô chữ | Nhập: Hoặc xin Owner cho cất thêm — lý do | 0 USD | — | quản trị | panel |
| limits_ui.py:149 | 📨 Xin Owner duyệt | nút | (panel) | 0 USD | — | quản trị | panel |
| limits_ui.py:150 | Đóng | nút | (panel) | 0 USD | — | quản trị | panel |
| limits_ui.py:188 | Duyệt | nút | Duyệt | 0 USD | — | quản trị | team_block |
| limits_ui.py:191 | Từ chối | nút | Loại | 0 USD | — | quản trị | team_block |
| limits_ui.py:205 | Dở cùng lúc | ô số | Nhập: Dở cùng lúc | 0 USD | — | quản trị | team_block |
| limits_ui.py:206 | Mới / ngày | ô số | Nhập: Mới / ngày | 0 USD | — | quản trị | team_block |
| limits_ui.py:207 | Dở đang cất | ô số | Nhập: Dở đang cất | 0 USD | — | quản trị | team_block |
| limits_ui.py:208 | 💾 | nút | (team_block) | 0 USD | — | quản trị | team_block |
| ui.py:329 | ▾ Thu gọn" if opened else "▸ Mở | nút | (fold) | 0 USD | — | mọi người | fold |

### ⑦ ⌂ Tất cả dự án — 14 điều khiển

| file:dòng | Nhãn | Loại | Việc làm | Tiền | Giá / xác nhận | Ai dùng | Điều kiện hiện |
|---|---|---|---|---|---|---|---|
| home.py:150 | 🧹 Dọn việc thừa của dự án | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | mọi người | _card |
| home.py:171 | Mở → | nút | (_card) | 0 USD | — | mọi người | _card |
| home.py:210 | Phạm vi | radio | Chọn: Phạm vi | 0 USD | — | mọi người | home |
| home.py:215 | Tìm | ô chữ | Nhập: Tìm | 0 USD | — | mọi người | home |
| home.py:216 | Sắp xếp | hộp chọn | Chọn: Sắp xếp | 0 USD | — | mọi người | home |
| home.py:218 | Trạng thái | radio | Chọn: Trạng thái | 0 USD | — | mọi người | home |
| home.py:219 | Bước | hộp chọn | Chọn: Bước | 0 USD | — | mọi người | home |
| home.py:221 | Người tạo | hộp chọn | Chọn: Người tạo | 0 USD | — | mọi người | home |
| home.py:223 | ⚠ Chỉ dự án có cảnh báo | ô tick | Bật/tắt: ⚠ Chỉ dự án có cảnh báo | 0 USD | — | mọi người | home |
| home.py:224 | ✕ Xóa lọc | nút | (home) | 0 USD | — | mọi người | home |
| home.py:272 | Mở → | nút | (_rows) | 0 USD | — | mọi người | _rows |
| home.py:285 | Xem dự án | hộp chọn | Chọn: Xem dự án | 0 USD | — | mọi người | _finished |
| home.py:291 | ⬇ Tải FINAL_VIDEO.mp4 | nút tải | Tải file về máy | 0 USD | — | mọi người | _finished |
| overview.py:77 | Mở → | nút | (cards) | 0 USD | — | mọi người | cards |

### ⑧ 👥 Nhóm · 🧪 học việc — 22 điều khiển

| file:dòng | Nhãn | Loại | Việc làm | Tiền | Giá / xác nhận | Ai dùng | Điều kiện hiện |
|---|---|---|---|---|---|---|---|
| design/screens/trainee_ui.py:40 | Chế độ | nút đoạn | Chọn: Chế độ | 0 USD | — | mọi người | mode_control |
| design/screens/trainee_ui.py:157 | icon | nút | (render_cards) | 0 USD | — | mọi người | render_cards |
| design/screens/trainee_ui.py:167 | ↻ Chấm lại (0 USD) | nút | (render_panel) | 0 USD | — | mọi người | render_panel |
| team_screen.py:138 | ↺ Đặt lại | nút | (user_reset_block) | 0 USD | — | quản trị | user_reset_block |
| team_screen.py:148 | Lý do (bắt buộc) | ô chữ | Nhập: Lý do (bắt buộc) | 0 USD | — | quản trị | user_reset_block |
| team_screen.py:153 | ↺ Đặt lại thanh này | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | quản trị | user_reset_block |
| team_screen.py:165 | ⊘ Bỏ mốc 0 | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | quản trị | user_reset_block |
| team_screen.py:176 | Đóng | nút | (user_reset_block) | 0 USD | — | quản trị | user_reset_block |
| team_screen.py:210 | Duyệt | nút | Duyệt | 0 USD | — | quản trị | machines_block |
| team_screen.py:213 | Từ chối | nút | Loại | 0 USD | — | quản trị | machines_block |
| team_screen.py:216 | Thu hồi | nút | Thu hồi | 0 USD | — | quản trị | machines_block |
| team_screen.py:234 | Khoảng | hộp chọn | Chọn: Khoảng | 0 USD | — | quản trị | team_screen |
| team_screen.py:235 | Tìm | ô chữ | Nhập: Tìm | 0 USD | — | quản trị | team_screen |
| team_screen.py:236 | Lọc | hộp chọn | Chọn: Lọc | 0 USD | — | quản trị | team_screen |
| team_screen.py:278 | Vai | hộp chọn | Chọn: Vai | 0 USD | — | quản trị | team_screen |
| team_screen.py:280 | Hạn mức | ô số | Nhập: Hạn mức | 0 USD | — | quản trị | team_screen |
| team_screen.py:282 | Được vào | ô tick | Bật/tắt: Được vào | 0 USD | — | quản trị | team_screen |
| team_screen.py:283 | 💾 Lưu | nút | (team_screen) | 0 USD | — | quản trị | team_screen |
| team_screen.py:298 | E-mail | ô chữ | Nhập: E-mail | 0 USD | — | quản trị | team_screen |
| team_screen.py:299 | Vai | hộp chọn | Chọn: Vai | 0 USD | — | quản trị | team_screen |
| team_screen.py:300 | Hạn mức USD/tháng | ô số | Nhập: Hạn mức USD/tháng | 0 USD | — | quản trị | team_screen |
| team_screen.py:301 | Mời | nút | (team_screen) | 0 USD | — | quản trị | team_screen · xám khi: not email.strip() |

### ⑨ Hộp thoại quản trị (admin.py: Kho, Kiến thức, Bài học, Lịch sử, Bảng giá, Theo dõi, Phân quyền) — 164 điều khiển

| file:dòng | Nhãn | Loại | Việc làm | Tiền | Giá / xác nhận | Ai dùng | Điều kiện hiện |
|---|---|---|---|---|---|---|---|
| admin.py:17 | Gồm cả tài liệu kiến thức có sẵn (giảm thêm token mỗi lần chạy) | ô tick | Bật/tắt: Gồm cả tài liệu kiến thức có sẵn (giảm thêm token … | 0 USD | — | quản trị | distill_panel |
| admin.py:36 | 🤖 Chắt lọc bằng {llm_label(client)}" + price | nút | (distill_panel) | $ Claude | giá trên nút | quản trị | distill_panel |
| admin.py:48 | Dán cẩm nang Claude trả về (Markdown, các mục `## `) | ô chữ lớn | Nhập: Dán cẩm nang Claude trả về (Markdown, các mục `## … | 0 USD | — | quản trị | distill_panel |
| admin.py:49 | Lưu cẩm nang | nút | (distill_panel) | 0 USD | — | quản trị | distill_panel · xám khi: not raw.strip() |
| admin.py:54 | Dùng cẩm nang thay cho tài liệu gốc | ô tick | Bật/tắt: Dùng cẩm nang thay cho tài liệu gốc | 0 USD | — | quản trị | distill_panel |
| admin.py:59 | Nội dung (sửa được) | ô chữ lớn | Nhập: Nội dung (sửa được) | 0 USD | — | quản trị | distill_panel |
| admin.py:60 | Lưu chỉnh sửa | nút | (distill_panel) | 0 USD | — | quản trị | distill_panel · xám khi: edited == d["text"] |
| admin.py:63 | (xóa/gỡ/gộp — hỏi Có/Không) | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | quản trị | admin |
| admin.py:73 | Bước dùng Claude | hộp chọn | Chọn: Bước dùng Claude | 0 USD | — | quản trị | knowledge_panel |
| admin.py:98 | Bật (gửi kèm mỗi lần chạy) | ô tick | Bật/tắt: Bật (gửi kèm mỗi lần chạy) | 0 USD | — | quản trị | knowledge_panel |
| admin.py:102 | (xóa/gỡ/gộp — hỏi Có/Không) | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | quản trị | admin |
| admin.py:112 | Tài liệu | tải tệp | Tải tệp lên | 0 USD | — | quản trị | knowledge_panel |
| admin.py:114 | Tên hiển thị (tùy chọn) | ô chữ | Nhập: Tên hiển thị (tùy chọn) | 0 USD | — | quản trị | knowledge_panel |
| admin.py:115 | Ghi chú (tùy chọn) | ô chữ | Nhập: Ghi chú (tùy chọn) | 0 USD | — | quản trị | knowledge_panel |
| admin.py:116 | ⬆ Thêm vào kho | nút | (knowledge_panel) | 0 USD | — | quản trị | knowledge_panel · xám khi: up is None |
| admin.py:137 | 💾 Lưu bảng phân quyền | nút | (users_tab) | 0 USD | — | quản trị | users_tab |
| admin.py:153 | E-mail | ô chữ | Nhập: E-mail | 0 USD | — | quản trị | users_tab |
| admin.py:154 | Quyền thêm | chọn nhiều | Chọn: Quyền thêm | 0 USD | — | quản trị | users_tab |
| admin.py:155 | Thêm | nút | (users_tab) | 0 USD | — | quản trị | users_tab |
| admin.py:165 | E-mail | hộp chọn | Chọn: E-mail | 0 USD | — | quản trị | users_tab |
| admin.py:166 | (xóa/gỡ/gộp — hỏi Có/Không) | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | quản trị | admin |
| admin.py:176 | Tên miền e-mail được tự vào làm Thành viên (cách nhau bằng dấu phẩy; đ… | ô chữ | Nhập: Tên miền e-mail được tự vào làm Thành viên (cách n… | 0 USD | — | quản trị | users_tab |
| admin.py:178 | Lưu tên miền | nút | (users_tab) | 0 USD | — | quản trị | users_tab |
| admin.py:248 | ☑ Chọn hết | nút | (library_review_box) | 0 USD | — | quản trị | library_review_box |
| admin.py:249 | ☐ Bỏ chọn | nút | (library_review_box) | 0 USD | — | quản trị | library_review_box |
| admin.py:250 | ✔ Duyệt {len(picked)} ảnh đã chọn | nút | (library_review_box) | 0 USD | — | quản trị | library_review_box · xám khi: not picked |
| admin.py:256 | ✔ Duyệt cả {len(waiting)} ảnh (giữ vai trò) | nút | (library_review_box) | 0 USD | — | quản trị | library_review_box |
| admin.py:266 | Có, bỏ | nút | (library_review_box) | 0 USD | — | quản trị | library_review_box |
| admin.py:272 | Không | nút | (library_review_box) | 0 USD | — | quản trị | library_review_box |
| admin.py:275 | 🗑 Bỏ {len(picked)} ảnh đã chọn | nút | (library_review_box) | 0 USD | — | quản trị | library_review_box · xám khi: not picked |
| admin.py:280 | Chọn | ô tick | Bật/tắt: Chọn | 0 USD | — | quản trị | library_review_box |
| admin.py:287 | Vai trò | hộp chọn | Chọn: Vai trò | 0 USD | — | quản trị | library_review_box |
| admin.py:289 | Look | hộp chọn | Chọn: Look | 0 USD | — | quản trị | library_review_box |
| admin.py:292 | ✔ | nút | (library_review_box) | 0 USD | — | quản trị | library_review_box |
| admin.py:296 | (xóa/gỡ/gộp — hỏi Có/Không) | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | quản trị | admin |
| admin.py:303 | … còn {more} ảnh — hiện thêm {min(more, REVIEW_PAGE)} | nút | (library_review_box) | 0 USD | — | quản trị | library_review_box |
| admin.py:318 | ↻ Tải lại | nút | (library_lost_box) | 0 USD | — | quản trị | library_lost_box · xám khi: not w["can_reload"] |
| admin.py:328 | 🔗 Gỡ liên kết | nút | (library_lost_box) | 0 USD | — | quản trị | library_lost_box |
| admin.py:332 | (xóa/gỡ/gộp — hỏi Có/Không) | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | quản trị | admin |
| admin.py:347 | 🔄 Đọc Kho chủ thể | nút | (subject_library_box) | 0 USD | — | quản trị | subject_library_box |
| admin.py:370 | Chọn theo gợi ý ({len(ov['suggested'])}) | nút | (subject_library_box) | 0 USD | — | quản trị | subject_library_box · xám khi: not ov["suggested"] |
| admin.py:372 | Asset sẽ xóa (asset dự án đang làm dùng không có trong danh sách) | chọn nhiều | Chọn: Asset sẽ xóa (asset dự án đang làm dùng không có t… | 0 USD | — | quản trị | subject_library_box |
| admin.py:374 | (xóa/gỡ/gộp — hỏi Có/Không) | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | quản trị | admin |
| admin.py:409 | label | ô tick | Bật/tắt: label | 0 USD | — | quản trị | profile_form |
| admin.py:415 | Lấy nháp từ Lock của dự án | hộp chọn | Chọn: Lấy nháp từ Lock của dự án | 0 USD | — | quản trị | profile_form |
| admin.py:416 | ↧ Dùng làm nháp | nút | Lưu hồ sơ | 0 USD | — | quản trị | profile_form |
| admin.py:420 | Nhận diện (mô tả ngắn, tiếng Anh cho model) | ô chữ lớn | Nhập: Nhận diện (mô tả ngắn, tiếng Anh cho model) | 0 USD | — | quản trị | profile_form |
| admin.py:421 | Luôn giữ (mặt, tóc, màu trang phục, phụ kiện) | ô chữ lớn | Nhập: Luôn giữ (mặt, tóc, màu trang phục, phụ kiện) | 0 USD | — | quản trị | profile_form |
| admin.py:422 | Được đổi (tư thế, biểu cảm…) | ô chữ | Nhập: Được đổi (tư thế, biểu cảm…) | 0 USD | — | quản trị | profile_form |
| admin.py:423 | Cấm lệch | ô chữ | Nhập: Cấm lệch | 0 USD | — | quản trị | profile_form |
| admin.py:425 | Chiều cao thật (m) | ô số | Nhập: Chiều cao thật (m) | 0 USD | — | quản trị | profile_form |
| admin.py:427 | Vóc dáng | ô chữ | Nhập: Vóc dáng | 0 USD | — | quản trị | profile_form |
| admin.py:428 | ✔ Duyệt — mọi dự án dùng hồ sơ này (thắng Lock của từng dự án) | ô tick | Bật/tắt: ✔ Duyệt — mọi dự án dùng hồ sơ này (thắng Lock của… | 0 USD | — | quản trị | profile_form |
| admin.py:429 | 💾 Lưu hồ sơ chuẩn | nút | Lưu hồ sơ | 0 USD | — | quản trị | profile_form |
| admin.py:443 | Mở công cụ | công tắc | Bật/tắt: Mở công cụ | 0 USD | — | quản trị | plates3d_panel |
| admin.py:450 | Thư mục file 3D (MODEL3D_DIR) | ô chữ | Nhập: Thư mục file 3D (MODEL3D_DIR) | 0 USD | — | quản trị | plates3d_panel |
| admin.py:455 | File 3D | hộp chọn | Chọn: File 3D | 0 USD | — | quản trị | plates3d_panel |
| admin.py:458 | Tên bối cảnh trong Kho | ô chữ | Nhập: Tên bối cảnh trong Kho | 0 USD | — | quản trị | plates3d_panel |
| admin.py:459 | Look | hộp chọn | Chọn: Look | 0 USD | — | quản trị | plates3d_panel |
| admin.py:460 | Bầu trời | radio | Chọn: Bầu trời | 0 USD | — | quản trị | plates3d_panel |
| admin.py:462 | Độ cao mặt trời (°) | thanh trượt | Chọn: Độ cao mặt trời (°) | 0 USD | — | quản trị | plates3d_panel |
| admin.py:463 | Hướng nắng (°) | thanh trượt | Chọn: Hướng nắng (°) | 0 USD | — | quản trị | plates3d_panel |
| admin.py:464 | Chiều cao thật phần cao nhất (m, 0 = tự đoán đơn vị) | ô số | Nhập: Chiều cao thật phần cao nhất (m, 0 = tự đoán đơn v… | 0 USD | — | quản trị | plates3d_panel |
| admin.py:466 | File HDRI (.hdr/.exr) cho cách B, hoặc ánh sáng cho cách C (để trống =… | ô chữ | Nhập: File HDRI (.hdr/.exr) cho cách B, hoặc ánh sáng ch… | 0 USD | — | quản trị | plates3d_panel |
| admin.py:468 | Ảnh trời chụp in-game để ghép (cách C) | tải tệp | Tải tệp lên | 0 USD | — | quản trị | plates3d_panel |
| admin.py:470 | Góc máy | chọn nhiều | Chọn: Góc máy | 0 USD | — | quản trị | plates3d_panel |
| admin.py:473 | Giữ lại % tam giác (map nặng: giảm) | thanh trượt | Chọn: Giữ lại % tam giác (map nặng: giảm) | 0 USD | — | quản trị | plates3d_panel |
| admin.py:474 | Khung | hộp chọn | Chọn: Khung | 0 USD | — | quản trị | plates3d_panel |
| admin.py:475 | ▶ Render nền (Blender, không tốn credit) | nút | Dựng video (ffmpeg) | 0 USD | — | quản trị | plates3d_panel · xám khi: not (blender and presets) |
| admin.py:492 | 📥 Đưa vào hộp chờ duyệt của Kho | nút | (plates3d_panel) | 0 USD | — | quản trị | plates3d_panel |
| admin.py:514 | Mở công cụ | công tắc | Bật/tắt: Mở công cụ | 0 USD | — | quản trị | meshy_panel |
| admin.py:525 | Trần Meshy của đợt (USD) | ô số | Nhập: Trần Meshy của đợt (USD) | 0 USD | — | quản trị | meshy_panel |
| admin.py:526 | Lưu trần | nút | Lưu thiết lập | 0 USD | — | quản trị | meshy_panel |
| admin.py:533 | Nhân vật | hộp chọn | Chọn: Nhân vật | 0 USD | — | quản trị | meshy_panel |
| admin.py:539 | Bảng nhiều góc để cắt 4 hướng | hộp chọn | Chọn: Bảng nhiều góc để cắt 4 hướng | 0 USD | — | quản trị | meshy_panel |
| admin.py:556 | gửi | ô tick | Bật/tắt: gửi | 0 USD | — | quản trị | meshy_panel |
| admin.py:560 | Tự viết câu texture (để trống = lấy từ hồ sơ; dùng cho skin hồ sơ chưa… | ô chữ lớn | Nhập: Tự viết câu texture (để trống = lấy từ hồ sơ; dùng… | 0 USD | — | quản trị | meshy_panel |
| admin.py:562 | Tôi đồng ý trả ≈ {plan['credits']} credit cho lần dựng này | ô tick | Bật/tắt: Tôi đồng ý trả ≈ {plan['credits']} credit cho lần … | 0 USD | — | quản trị | meshy_panel |
| admin.py:563 | ▶ Dựng 3D (Meshy) | nút | (meshy_panel) | $ 3D Meshy (credit) | ô tick xác nhận (lô ≥ ngưỡng / credit) | quản trị | meshy_panel · xám khi: not (client and ok and keep and not plan… |
| admin.py:574 | 🔄 Cập nhật + tải về | nút | Hỏi trạng thái + tải kết quả | 0 USD | — | quản trị | meshy_panel · xám khi: not client |
| admin.py:583 | 📥 Ảnh 4 hướng vào hộp chờ duyệt | nút | (meshy_panel) | 0 USD | — | quản trị | meshy_panel |
| admin.py:586 | 🦴 Gắn khung xương (≈ {meshy.CREDITS['rig']} credit) | nút | (meshy_panel) | $ 3D Meshy (credit) | giá trên nút | quản trị | meshy_panel · xám khi: not client |
| admin.py:609 | Loại mặc định | hộp chọn | Chọn: Loại mặc định | 0 USD | — | quản trị | lib_sources_box |
| admin.py:611 | Bỏ qua file/thư mục có từ (cách nhau bằng dấu phẩy) | ô chữ | Nhập: Bỏ qua file/thư mục có từ (cách nhau bằng dấu phẩy… | 0 USD | — | quản trị | lib_sources_box |
| admin.py:612 | Tự động | ô tick | Bật/tắt: Tự động | 0 USD | — | quản trị | lib_sources_box |
| admin.py:616 | Xóa ảnh không còn trong thư mục | ô tick | Bật/tắt: Xóa ảnh không còn trong thư mục | 0 USD | — | quản trị | lib_sources_box |
| admin.py:617 | 🔄 Đồng bộ ngay | nút | (lib_sources_box) | 0 USD | — | quản trị | lib_sources_box |
| admin.py:624 | (xóa/gỡ/gộp — hỏi Có/Không) | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | quản trị | admin |
| admin.py:637 | Đường dẫn thư mục | ô chữ | Nhập: Đường dẫn thư mục | 0 USD | — | quản trị | lib_sources_box |
| admin.py:640 | Loại mặc định (khi thư mục không nói rõ) | hộp chọn | Chọn: Loại mặc định (khi thư mục không nói rõ) | 0 USD | — | quản trị | lib_sources_box |
| admin.py:642 | Bỏ qua file/thư mục có từ | ô chữ | Nhập: Bỏ qua file/thư mục có từ | 0 USD | — | quản trị | lib_sources_box |
| admin.py:643 | Thêm và đồng bộ ngay | nút | (lib_sources_box) | 0 USD | — | quản trị | lib_sources_box · xám khi: not path.strip() |
| admin.py:666 | 🌐 Cập nhật ngay | nút | (lib_ff_site_box) | 0 USD | — | quản trị | lib_ff_site_box · xám khi: info["running"] |
| admin.py:688 | ↻ Thử lại | nút | (lib_vision_box) | 0 USD | — | quản trị | lib_vision_box |
| admin.py:692 | 🤖 Đọc mô tả ngoại hình" + cost.llm_tag(vision_usd, n_pending) | nút | Bắt đầu | $ Claude | giá trên nút | quản trị | lib_vision_box · xám khi: not n_pending or asset_vision.active(gam… |
| admin.py:710 | Nhân vật / thú cưng | hộp chọn | Chọn: Nhân vật / thú cưng | 0 USD | — | quản trị | lib_video_box |
| admin.py:711 | Video gameplay (mp4/mov/webm/mkv, tối đa 200 MB) | tải tệp | Tải tệp lên | 0 USD | — | quản trị | lib_video_box |
| admin.py:712 | Ghi chú thêm cho Claude (tuỳ chọn) | ô chữ | Nhập: Ghi chú thêm cho Claude (tuỳ chọn) | 0 USD | — | quản trị | lib_video_box |
| admin.py:714 | Số khung hình lấy mẫu | thanh trượt | Chọn: Số khung hình lấy mẫu | 0 USD | — | quản trị | lib_video_box |
| admin.py:715 | 🎬 Phân tích video" + cost.llm_tag(cost.llm_estimate(p.conn, "video_ana… | nút | (lib_video_box) | $ Claude | giá trên nút | quản trị | lib_video_box · xám khi: not va_video |
| admin.py:741 | Thêm làm ảnh tham chiếu | ô tick | Bật/tắt: Thêm làm ảnh tham chiếu | 0 USD | — | quản trị | lib_video_box |
| admin.py:743 | Nội dung (sửa được trước khi lưu) | ô chữ lớn | Nhập: Nội dung (sửa được trước khi lưu) | 0 USD | — | quản trị | lib_video_box |
| admin.py:745 | 💾 Lưu vào mô tả | nút | (lib_video_box) | 0 USD | — | quản trị | lib_video_box |
| admin.py:752 | 🖼 Thêm {len(keep)} ảnh đã tick vào tài nguyên | nút | Thêm ảnh vào Kho | 0 USD | — | quản trị | lib_video_box · xám khi: not keep |
| admin.py:770 | Loại | hộp chọn | Chọn: Loại | 0 USD | — | quản trị | lib_bulk_box |
| admin.py:771 | Ảnh | tải tệp | Tải tệp lên | 0 USD | — | quản trị | lib_bulk_box |
| admin.py:772 | Thêm vào kho | nút | (lib_bulk_box) | 0 USD | — | quản trị | lib_bulk_box · xám khi: not bulk |
| admin.py:795 | ✔ Xác nhận cả {len(imgs)} ảnh | nút | Xác nhận ảnh Kho | 0 USD | — | quản trị | claude_review_box · xám khi: not imgs |
| admin.py:809 | ✔ | nút | Xác nhận ảnh Kho | 0 USD | — | quản trị | claude_review_box |
| admin.py:812 | ↩ | nút | Thu hồi | 0 USD | — | quản trị | claude_review_box |
| admin.py:823 | ✔ | nút | Xác nhận ảnh Kho | 0 USD | — | quản trị | claude_review_box |
| admin.py:826 | ↩ | nút | Thu hồi | 0 USD | — | quản trị | claude_review_box |
| admin.py:844 | Bỏ qua thư mục có từ | ô chữ | Nhập: Bỏ qua thư mục có từ | 0 USD | — | quản trị | lib_sound_box |
| admin.py:845 | Tự động | ô tick | Bật/tắt: Tự động | 0 USD | — | quản trị | lib_sound_box |
| admin.py:848 | 🔄 Quét ngay | nút | (lib_sound_box) | 0 USD | — | quản trị | lib_sound_box |
| admin.py:855 | (xóa/gỡ/gộp — hỏi Có/Không) | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | quản trị | admin |
| admin.py:859 | Thêm thư mục âm thanh | ô chữ | Nhập: Thêm thư mục âm thanh | 0 USD | — | quản trị | lib_sound_box |
| admin.py:860 | Thêm và quét | nút | (lib_sound_box) | 0 USD | — | quản trị | lib_sound_box · xám khi: not snd_path.strip() |
| admin.py:875 | Tên | ô chữ | Nhập: Tên | 0 USD | — | quản trị | lib_new_item_box |
| admin.py:876 | Loại | hộp chọn | Chọn: Loại | 0 USD | — | quản trị | lib_new_item_box |
| admin.py:877 | Tên gọi khác trong kịch bản (cách nhau bằng dấu phẩy) | ô chữ | Nhập: Tên gọi khác trong kịch bản (cách nhau bằng dấu ph… | 0 USD | — | quản trị | lib_new_item_box |
| admin.py:878 | Mô tả (ngoại hình, đặc điểm để Director dùng) | ô chữ lớn | Nhập: Mô tả (ngoại hình, đặc điểm để Director dùng) | 0 USD | — | quản trị | lib_new_item_box |
| admin.py:883 | Tên tiếng Anh (bắt buộc nếu tên chính là tiếng Việt) | ô chữ | Nhập: Tên tiếng Anh (bắt buộc nếu tên chính là tiếng Việ… | 0 USD | — | quản trị | lib_new_item_box |
| admin.py:886 | Ảnh tham khảo | tải tệp | Tải tệp lên | 0 USD | — | quản trị | lib_new_item_box |
| admin.py:887 | Vẫn tạo dù Kho báo trùng — lý do (để trống = không tạo trùng) | ô chữ | Nhập: Vẫn tạo dù Kho báo trùng — lý do (để trống = không… | 0 USD | — | quản trị | lib_new_item_box |
| admin.py:888 | Thêm vào kho | nút | Thêm ảnh vào Kho | 0 USD | — | quản trị | lib_new_item_box · xám khi: not name.strip() |
| admin.py:912 | ↩ Khôi phục | nút | (lib_removed_images) | 0 USD | — | quản trị | lib_removed_images · xám khi: not r["exists"] |
| admin.py:934 | (xóa/gỡ/gộp — hỏi Có/Không) | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | quản trị | admin |
| admin.py:943 | ✏️ Sửa, gộp hoặc xóa mục này | ô tick | Bật/tắt: ✏️ Sửa, gộp hoặc xóa mục này | 0 USD | — | quản trị | lib_asset_card |
| admin.py:944 | Tên | ô chữ | Nhập: Tên | 0 USD | — | quản trị | lib_asset_card |
| admin.py:945 | Tên gọi khác | ô chữ | Nhập: Tên gọi khác | 0 USD | — | quản trị | lib_asset_card |
| admin.py:946 | Mô tả | ô chữ lớn | Nhập: Mô tả | 0 USD | — | quản trị | lib_asset_card |
| admin.py:949 | Chiều cao thật (m) — vật mốc, 0 = chưa đo | ô số | Nhập: Chiều cao thật (m) — vật mốc, 0 = chưa đo | 0 USD | — | quản trị | lib_asset_card |
| admin.py:953 | Thêm ảnh | tải tệp | Tải tệp lên | 0 USD | — | quản trị | lib_asset_card |
| admin.py:958 | Gộp mục này vào mục khác (ảnh chuyển sang, tên này thành tên gọi khác) | hộp chọn | Chọn: Gộp mục này vào mục khác (ảnh chuyển sang, tên này… | 0 USD | — | quản trị | lib_asset_card |
| admin.py:960 | (xóa/gỡ/gộp — hỏi Có/Không) | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | quản trị | admin |
| admin.py:970 | 💾 Lưu | nút | Thêm ảnh vào Kho | 0 USD | — | quản trị | lib_asset_card |
| admin.py:981 | (xóa/gỡ/gộp — hỏi Có/Không) | nút + Có/Không | Nút + hỏi Có/Không trước khi làm | 0 USD | — | quản trị | admin |
| admin.py:992 | Game / loại nội dung | hộp chọn | Chọn: Game / loại nội dung | 0 USD | — | quản trị | asset_library_panel |
| admin.py:1009 | Xem | radio | Chọn: Xem | 0 USD | — | quản trị | asset_library_panel |
| admin.py:1011 | Tìm theo tên | ô chữ | Nhập: Tìm theo tên | 0 USD | — | quản trị | asset_library_panel |
| admin.py:1017 | Trang (có {len(shown)} mục, {pages} trang) | ô số | Nhập: Trang (có {len(shown)} mục, {pages} trang) | 0 USD | — | quản trị | asset_library_panel |
| admin.py:1047 | ↩ Khôi phục | nút | Khôi phục | 0 USD | — | quản trị | trash_section |
| admin.py:1075 | Làm tay mất bao nhiêu phút cho 1 giây video (mặc định chung 30 phút — … | ô số | Nhập: Làm tay mất bao nhiêu phút cho 1 giây video (mặc đ… | 0 USD | — | quản trị | effectiveness_panel |
| admin.py:1095 | 📌 Lưu mốc | nút | (effectiveness_history) | 0 USD | — | quản trị | effectiveness_history |
| admin.py:1120 | Chọn 2–3 dự án | chọn nhiều | Chọn: Chọn 2–3 dự án | 0 USD | — | quản trị | compare_panel |
| admin.py:1135 | label | thanh trượt | Chọn: label | 0 USD | — | quản trị | compare_panel |
| admin.py:1137 | Nhận xét | ô chữ lớn | Nhập: Nhận xét | 0 USD | — | quản trị | compare_panel |
| admin.py:1138 | 💾 Lưu điểm | nút | (compare_panel) | 0 USD | — | quản trị | compare_panel |
| admin.py:1189 | ↻ Làm mới | nút | (_monitor_v2) | 0 USD | — | quản trị | _monitor_v2 |
| admin.py:1249 | ⬇ Tải báo cáo (.md) | nút tải | Tải file về máy | 0 USD | — | quản trị | _monitor_v2 |
| admin.py:1275 | 🤖 Chấm {n} bài học" + cost.llm_button_tag(conn, lesson_judge.STAGE, n) | nút | (lesson_judge_panel) | $ Claude | giá trên nút | quản trị | lesson_judge_panel · xám khi: llm is None or n == 0 |
| admin.py:1309 | 🔎 Rút bài học từ các lỗi đã gặp" + cost.llm_tag(cost.llm_estimate(conn… | nút | Đề xuất | $ Claude | giá trên nút | quản trị | lessons_tab |
| admin.py:1316 | 🌐 Nghiên cứu tài liệu mới ngay" + cost.llm_tag(research.estimate(conn)… | nút | (lessons_tab) | $ Claude | giá trên nút | quản trị | lessons_tab · xám khi: llm is None |
| admin.py:1325 | Tự nghiên cứu hàng tháng (khi mở Dashboard và đã đến hạn) | ô tick | Bật/tắt: Tự nghiên cứu hàng tháng (khi mở Dashboard và đã đ… | bật tự nghiên cứu hằng tháng ($ Claude về sau) | KHÔNG | quản trị | lessons_tab |
| admin.py:1342 | Tiêu đề | ô chữ | Nhập: Tiêu đề | 0 USD | — | quản trị | lessons_tab |
| admin.py:1343 | Nội dung quy tắc | ô chữ lớn | Nhập: Nội dung quy tắc | 0 USD | — | quản trị | lessons_tab |
| admin.py:1345 | 👍 Duyệt | nút | Duyệt/bỏ bài học | 0 USD | — | quản trị | lessons_tab |
| admin.py:1349 | 👎 Bỏ | nút | Duyệt/bỏ bài học | 0 USD | — | quản trị | lessons_tab |
| admin.py:1356 | Gỡ bài học này | nút | Duyệt/bỏ bài học | 0 USD | — | quản trị | lessons_tab |
| admin.py:1386 | Cảnh | hộp chọn | Chọn: Cảnh | 0 USD | — | quản trị | history |
| admin.py:1422 | Đơn vị tiền/credit | ô chữ | Nhập: Đơn vị tiền/credit | 0 USD | — | quản trị | price_editor |
| admin.py:1423 | Xác nhận khi lô từ … mục trở lên | ô số | Nhập: Xác nhận khi lô từ … mục trở lên | 0 USD | — | quản trị | price_editor |
| admin.py:1434 | 💾 Lưu bảng giá | nút | (price_editor) | 0 USD | — | quản trị | price_editor |