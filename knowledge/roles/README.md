# Tổ làm phim — trang tổng (V4 GĐ4, 2026-09-25 — cờ `film_crew` đang BẬT qua `dashboard.env`, chưa verified)

Ba vai, mỗi vai một bộ kỹ năng nghề: **Đạo diễn** (`director.md`), **Quay phim** (`dp.md`), **Dựng** (`knowledge/editor/editing.md` +
`safe_zones.md` — hai file này **không nạp vào prompt nào**: `role_text` chỉ đọc `director.md` và `dp.md`). Nguồn bên ngoài: `knowledge/sources.md` mục GĐ4. Khi cờ `film_crew` bật, Director (Claude) đọc `director.md` + `dp.md`
(dự án chia shot) thay cho 3 tài liệu rải rác (`cinematography_basics`, `film_director_method`, `dialogue_craft` — vẫn còn cho luồng cũ;
nhãn cờ ở `core/features.py` ghi cùng 3 tên). Hai lượt: Tầng A đọc `director.md` bản đã cắt các khối "Trong pipeline" mức shot
(đánh dấu `<!-- shot -->`, `prompts.role_text(..., intent_only=True)`) — phần "vì sao" và "kiểm" vẫn giữ nên vẫn nhắc tên trường shot.
Vai Dựng phần lớn là code; tài liệu của nó dành cho người sửa code và cho Claude khi phải nhìn khung hình.

## Ai làm gì, bàn giao gì
| Vai | Nhận | Làm | Giao cho | Trường / sản phẩm |
|---|---|---|---|---|
| **Đạo diễn** | Kịch bản, hồ sơ nhân vật (Kho), thể loại, khung hình | Phân tích kịch bản, đường cảm xúc, cách kể bằng hình, diễn xuất, giọng, ghi chú kịch bản; duyệt chốt | Quay phim (cùng một lần gọi Director; cờ `director_two_pass`: lượt riêng — xem mục "Hai lượt"); người dùng (ghi chú) | cảnh: `beat`, `emotional_intent`, `time`, `mood`, `lighting`, `weather`; shot: `performance`, `role`, `hero`; câu: `delivery`; gốc: `tradeoffs`, `script_notes` |
| **Quay phim** | Ý đồ + diễn xuất của Đạo diễn | Vị trí máy, cỡ/góc/ống kính, chuyển động, bố cục, ánh sáng, gói bối cảnh, khớp môi; lý do | Motion (prompt video), ảnh (prompt khung đầu), máy ảo Blender | shot: `size`, `angle`, `camera_move`, `lens_mm`, `start_frame`, `end_state`, `image_prompt`, `camera_setup`, `plate_spot`, `plate_mode`, `plate_view`, `practical_lights`, `lip_sync`, `why` |
| **Dựng** | Clip đã duyệt, giọng, chữ, nhạc, SFX | Cắt, giọng, âm nhiều lớp, nhạc, màu + khớp màu, hiệu ứng, chữ + vùng an toàn, độ to, tự rà | Người dùng (bản giao) | bản dựng, phụ đề, bản xuất theo nền tảng |
Trả ngược: lỗi hình → Quay phim (gen lại có đổi đầu vào, ≤ 2 lần); lỗi diễn/giọng → Đạo diễn; kịch bản yếu → người viết (chỉ đề xuất).

## Hai lượt: Đạo diễn → Quay phim → Đạo diễn duyệt (cờ `director_two_pass`, V4 GĐ5 — BẬT, người dùng duyệt 29/09/2026, S6.5)
Vì sao: một lượt Director viết cả Bible, cảnh và mọi shot (~30k ký tự) — luật máy quay làm loãng phần nghĩ về câu chuyện, và lỗi ở một cảnh
phải trả tiền hỏi lại cả kịch bản. Chỉ áp dụng cho dự án chia shot (dự án mỗi cảnh một clip vẫn một lượt). Code: `core/director_two_pass.py`.
| Lượt | Ai | Đọc | Viết | Lỗi thì |
|---|---|---|---|---|
| **Tầng A** (1 lượt, prompt 19) | Đạo diễn | `director.md` (cờ `film_crew`) hoặc 3 tài liệu cũ trừ `cinematography_basics`; thể loại, look, `ff_gameplay_visual`, Kho, hồ sơ chuẩn, Bible hiện có, trường đã khóa | Bible + mỗi cảnh: `emotional_intent`, `beat`, câu thoại giữ (nguyên văn, đúng thứ tự; bỏ chỉ khi ✂), `target_s`, `focus`, `peak`, `sound` mức cảnh, `dp_notes`, `editor_notes`; `tradeoffs`, `script_notes` | hỏi lại một lần kèm lỗi (câu bịa/sai thứ tự/sai người nói/thiếu câu, thiếu cảnh, `target_s`) |
| **Tầng B** (mỗi cảnh 1 lượt, prompt 20 + 17) | Quay phim | `dp.md` (cờ `film_crew`) hoặc `cinematography_basics`; luật chia shot, dựng FF, phong cách, khớp môi / vị trí máy, gói bối cảnh, Bible Tầng A, ý đồ mọi cảnh | `shots` của MỘT cảnh (+ `tradeoffs` của cảnh) | chỉ hỏi lại cảnh đó; cảnh đã đạt được giữ, lần sau chỉ hỏi cảnh lỗi |
| **Đạo diễn duyệt** (code, không gọi Claude) | — | ý đồ + bảng shot | cờ từng cảnh: thoại lệch, tổng giây ngoài khung ±max(1 s, 15%), trọng tâm không có trong khung, `peak` ≥ 4 mà không shot ≥ 2 s; kèm cảnh báo diễn xuất/âm thanh | hiện ở Bước 1 (🎬) — người xem quyết, không tự hỏi lại |
Phần chung của Tầng B đặt trước dấu cache: cảnh đầu chạy một mình (ghi cache), các cảnh sau chạy song song (đọc cache ~1/10 giá). Kết quả ghép
lại đúng dạng một lượt rồi qua cùng bộ chuẩn hóa + kiểm thoại + lưu (giữ trường người sửa tay, Bible đã khóa). "↻ Chia shot lại cảnh này" dùng
ý đồ đã lưu, chỉ hỏi Quay phim. Ước tính tiền hai cách hiện trên nút Director. Chưa làm: lượt Claude nhỏ để Đạo diễn đọc bản tóm tắt cảnh bị cờ.

## Bảng ưu tiên chung (một thang cho cả tổ — người dùng chốt 2026-09-25)
**Luật cứng, đứng ngoài thang:** giới hạn model (`provider_rules.json`, code kiểm trước khi gửi), sổ chi/trần tiền, không tuổi < 18. Vi phạm
thì model từ chối hoặc tốn tiền vô ích — không phải "ít quan trọng" mà là "chọn cách khác bên trong giới hạn", rồi ghi `tradeoffs`.
Bên trong luật cứng:
1. **Mạch truyện & cảm xúc** (gồm rõ không gian: người xem hiểu ai ở đâu, nhìn ai) — Đạo diễn: ý đồ, diễn xuất; Quay phim: trục, hướng.
2. **Thoại nguyên văn + cặp đối đáp; thoại nghe rõ; chữ đọc được** — Đạo diễn N1; Dựng E2, E7.
3. **Góc máy kịch bản ghi.**
4. **Thời lượng kịch bản.**
5. **Tiết kiệm tiền video** (ít clip, gộp theo vị trí máy).
6. **Phong cách / thẩm mỹ / hiệu ứng.**
Mỗi bộ vai ghi thang này theo việc của mình: Quay phim "ý đồ > rõ không gian > ít clip > đẹp"; Dựng "thoại rõ > chữ đọc được > nhịp cắt >
liền mạch > đẹp" — ở khâu dựng, cảm xúc đã được Đạo diễn đặt vào shot và diễn xuất; thoại rõ và chữ đọc được là điều kiện để cảm xúc đó tới
người xem, nên đứng trước nhịp cắt. Hy sinh mục thấp hơn → `tradeoffs` (code kiểm).

## Rà chéo — những chỗ có thể mâu thuẫn và cách đã giải
| Chỗ | Vai A | Vai B | Giải |
|---|---|---|---|
| Cận mặt người nói | Đạo diễn: cận = cảm xúc | N3: không cận mặt người nói khi khớp môi tắt | Khớp môi tắt: cận dành cho im lặng; bật: cận câu then chốt `lip_sync: true` |
| Cường độ diễn ở cận | Đạo diễn Đ2: `intensity` là đường cảm xúc (5 = đỉnh) | Đạo diễn Đ4: cận phóng đại biểu cảm | Đạo diễn ghi độ mạnh của khoảnh khắc; code vẽ ở CU/ECU thấp hơn một bậc (`performance.shown_intensity`) — một số, hai việc tách nhau |
| Chuyển động máy | Đạo diễn: cảm xúc cần đẩy vào | Dữ liệu thật: push_in + nhân vật bước tới → "đi tại chỗ" | Nhân vật di chuyển → máy bám theo; đẩy vào khi nhân vật đứng |
| Chữ và bố cục | Quay phim: chừa chỗ cho chữ, mắt dưới thanh giao diện | Dựng: vùng an toàn trên 15% / dưới 35% (code 36%, đệm) / phải 18% | Vị trí mắt: **một luật ở `dp.md` Q3** (dải 18–35%, máy ảo ~20/23/28/33% theo cỡ — `plate_camera.HEADROOM`); vùng chữ: một bộ số (`safe_zones.md`), code dùng chung (`subtitles.SAFE_*`) |
| Thời tiết | Đạo diễn: mang cảm xúc (Đ3) | Quay phim: ánh sáng có nguồn (Q8); Dựng: âm + hiệu ứng thời tiết | Một trường `weather` → nền (`plate_env`), màu người (`composite`), lớp rơi, âm thời tiết (D4 ✅ `core/ambience.py`, cờ `ambience_bed`) |
| Tiêu cự | Quay phim: bảng mm theo cảm xúc | Máy ảo: `FRAMING` theo cỡ | Mặc định theo `FRAMING`; `lens_mm` ghi đè, máy ảo giữ cỡ người và tự lùi/tiến |
| Độ dài shot | Đạo diễn N2: thoại đủ thời gian nói | Dựng E1: cắt ngắn ở cao trào | Thoại thắng (ưu tiên 2); cao trào ngắn ở shot không thoại |
| Thời gian nói | Đạo diễn N2, prompt 01 | prompt 17, code | Một số: âm tiết ÷ 3,5 + 0,5 s (`dialogue.BREATH`) — prompt 17 sửa từ 0,4 |
| `beat` | Đạo diễn Đ1 (giá trị đổi, gieo–gặt) | prompt 01 (object) | Một dạng object: `want, obstacle, turn, value, plant, payoff, cause`; code kiểm gặt có gieo |
| Âm nền | Dựng E3 (nền không khí liên tục) | `sfx_plan` (chỉ điểm nhấn) | Hai lớp riêng: `sfx_plan` = điểm nhấn; nền không khí = D5 ✅ (`core/ambience.py`, không đè nhạc) |
| Móc câu | Đạo diễn N5 / Đ2 | TikTok chính thức | Mốc dự án 1–3 s (giả thuyết); nguồn chính thức: ý chính ≤ 3 s, móc ≤ 6 s |
| Vị trí người | Đạo diễn: ai gần/xa ai vì truyện (`dp_notes`) | Quay phim: `start_frame` (trái/phải, tiền/hậu) | Một trường: `start_frame` lưu thành `blocking` của shot (prompt 01 một lượt: `blocking` của cảnh); code trục 180° đọc cả hai tên |
| Quay chậm | Đạo diễn Đ11 chọn khoảnh khắc | Quay phim Q11 `speed`/`freeze_end_s`; Dựng E10 làm khi cắt | Chỉ shot không thoại (code bỏ ở shot thoại/khớp môi); 1–2 lần mỗi phim; cờ `speed_ramp` |
| Lặng nhạc | Dựng D6 (`music_breath`, trước TWIST) | Đạo diễn Đ9 (`sound.breath`) | Hai khoảng lặng cách nhau ≤ 1 s là một: giữ cái Đạo diễn đặt (`delivery.merge_breaths`) |
| Ảnh bìa / ⭐ | Đạo diễn Đ10: khoảnh khắc sản phẩm = `money_shot` | Prompt 01/17/19: `hero` ⭐ = cao trào, model video tốt nhất | Hai trường riêng: ảnh bìa lấy `money_shot` → ⭐ → diễn mạnh nhất (`delivery.cover_image`); D6 lặng nhạc vẫn theo ⭐ |

## Việc code còn thiếu (kỹ năng có trong bộ nhưng pipeline chưa làm — không để im)
Đã làm trong GĐ4: trường `performance` (ảnh + motion + QC + dấu vân tay + cảnh báo), `delivery` → tham số TTS (cờ `voice_direction`),
`why`, `lens_mm` → máy ảo, `script_notes` + kiểm `tradeoffs` (bàn đo + Bước 1), khối "Gói bối cảnh" cho Director + báo chỗ đứng lạ
(autopilot), Q4 sinh từ `provider_rules.json`, lề phải phụ đề 18%, mắt dưới thanh giao diện (máy ảo), hồ sơ rút gọn (`profile_digest`, cờ),
**V1 kiểm gieo–gặt** (`beat.plant/payoff`, bàn đo), **đo LUFS + đỉnh thật** (`ffmpeg_studio.measure_loudness` — phần đo của D11).
| Mã | Việc | Vai | Tốn tiền? |
|---|---|---|---|
| V1 | ✅ Đã làm: cảnh có `beat.payoff` mà không cảnh trước nào có `beat.plant` → ⚠ | Đạo diễn | — |
| V2 | ✅ Ô sửa diễn xuất (`performance`), `why`, chỉ đạo giọng (nhịp/cường độ/ngắt) ở ô sửa shot Bước 1; lưu tay giữ `delivery` của Director | Đạo diễn/Quay phim | — |
| V3 | ✅ (S6.5: `voice_direction` đã kiểm chứng, verified) Nghe thử `delivery` với giọng Việt (thẻ âm có bị đọc thành chữ không) rồi bật `voice_direction` | Đạo diễn | Vài lượt âm thanh |
| V4 | ✅ Sơ đồ máy nhìn từ trên cho shot ở nơi có mô hình 3D (`location_pack.top_view`, lệnh `topview`); nơi không có 3D: chưa | Quay phim | — |
| V5 | ✅ Kiểm trục 180° / hướng màn hình từ `start_frame` (`core/continuity.py`, bàn đo + Bước 1 🧭) | Quay phim | — |
| V6 | ✅ Trường `motif` + báo motif chỉ xuất hiện một lần; ai-biết-gì: trường cảnh `knowledge_gap` (2026-09-26), `emotional_intent` nói biết điều gì | Đạo diễn | — |
| V7 | Kiểm giọng đúng `delivery` bằng máy (hiện chỉ có người nghe theo bảng kiểm) | Đạo diễn | Chưa rõ |
| D1 | ✅ Cắt J 0,25 s khi đổi người nói (cờ `j_cut` TẮT mặc định — `verified` False) | Dựng | — |
| D2 | ✅ Điểm cắt theo chuyển động, dời ≤ 1 s (cờ `motion_trim`, TẮT mặc định — `verified` False) | Dựng | — |
| D3 | ⏸ Cố ý chưa làm: chỉ cần khi có giọng thu (giọng TTS đã sạch) | Dựng | — |
| D4 | ✅ Âm thời tiết từ thư viện (cờ `ambience_bed`, BẬT — duyệt 01/10/2026); sấm đúng giây chớp: chưa | Dựng | — (thư viện của bạn) |
| D5 | ✅ Nền không khí mỗi cảnh từ thư viện, không đè nhạc (cờ `ambience_bed`, BẬT) | Dựng | — |
| D6 | ✅ Nhạc lặng 0,6 s trước TWIST / shot ⭐ (cờ `music_breath` BẬT — người dùng duyệt 01/10/2026) | Dựng | — |
| D7 | ✅ Khớp màu giữa các shot cùng nơi/cảnh/nhóm cỡ: luôn đo (🎨 Bước 5), sửa bản sao sau cờ `shot_color_match` (BẬT — duyệt 01/10/2026) — `core/color_match.py` | Dựng | — |
| D8 | ✅ Khớp hạt người–nền khi ghép (hạt mới mỗi khung) | Dựng | — |
| D9 | ✅ Rung máy 0,25 s ở hiệu ứng va chạm (cờ `impact_shake`, BẬT — duyệt 01/10/2026); lóa / hạt toàn khung: chưa (ít cần) | Dựng | — |
| D10 | ❌ Bảng tên nhân vật — đã bỏ 2026-09-28 (người dùng, sau #8); luật nếu dùng lại ở `knowledge/editor/editing.md` | Dựng | — |
| D11 | ✅ Đo độ to mọi bản dựng (manifest + Bước 5); chuẩn hóa −14 LUFS / −1,5 dBTP sau cờ `loudness_normalize` (BẬT — duyệt 29/09/2026) | Dựng | — |
| D12 | ✅ `_ENCODE` có `+faststart` + thẻ màu BT.709 | Dựng | — |
| D13 | ✅ Bảng tự rà: vùng giao diện app + bản cỡ điện thoại + mặt bị che (nút 🧐 Bước 5) | Dựng | — |
| D14 | ✅ Đo: nhạc hạ 14,5–22,8 dB dưới giọng thật #7 (khuyên 6–10) → người dùng đã quyết: hạ 8–12 dB (Đợt 11) | Dựng | — |
| S1 | ✅ 2026-09-26 (người chấm lần 0): quay chậm / dừng hình (`speed`, `freeze_end_s`, cờ `speed_ramp` TẮT); phụ đề động; ảnh bìa; kiểm chữ dưới giao diện; phụ đề 0,83 s / 2 khung / điểm cắt; cỡ chữ đo thật; BT.709 cho ảnh tĩnh; CRF 18 + AAC 256k; test mức hạ nhạc; gộp hai khoảng lặng nhạc | Dựng | — |
| S2 | ✅ 2026-09-26: kiểm trục cả shot qua vai + báo "không kiểm được"; mẫu `lighting`; MLS vào từ vựng; `why`/tiêu cự/thời tiết/chỗ đứng vào dấu vân tay | Quay phim | — |
| S3 | ✅ 2026-09-26: `tradeoffs` đối chiếu theo từng loại + dò góc máy kịch bản ghi; `why` "cố ý dồn nhịp" được đọc; "liền nhau" đúng nghĩa; `knowledge_gap`; `hook_mid` + kiểm móc giữa; Tầng A không đọc lệnh shot; thẻ ngắt v3; đo tốc độ nói (`tools/measure_speech_rate.py`) | Đạo diễn | — |
| S4 | Sơ đồ máy nhìn từ trên cho nơi **không** có mô hình 3D; dựng biến thể mở đầu; speed ramp mượt trong một shot; mã hóa âm một lần duy nhất | Quay phim / Dựng | — |
| P1 | `lock_short`/`lock_medium` do Claude viết cho hồ sơ dài (KENTA: bản code 500 ký tự mất áo khoác xanh + găng tay trái) | Hồ sơ | ~$0,01/nhân vật |
