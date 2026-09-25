# Tổ làm phim — trang tổng (V4 GĐ4, 2026-09-25 — chờ người dùng duyệt rồi bật `film_crew`)

Ba vai, mỗi vai một bộ kỹ năng nghề: **Đạo diễn** (`director.md`), **Quay phim** (`dp.md`), **Dựng** (`knowledge/editor/editing.md` +
`safe_zones.md`). Nguồn bên ngoài: `knowledge/sources.md` mục GĐ4. Khi cờ `film_crew` bật, Director (Claude) đọc `director.md` + `dp.md`
(dự án chia shot) thay cho 3 tài liệu rải rác (`cinematography_basics`, `film_director_method`, `dialogue_craft` — vẫn còn cho luồng cũ).
Vai Dựng phần lớn là code; tài liệu của nó dành cho người sửa code và cho Claude khi phải nhìn khung hình.

## Ai làm gì, bàn giao gì
| Vai | Nhận | Làm | Giao cho | Trường / sản phẩm |
|---|---|---|---|---|
| **Đạo diễn** | Kịch bản, hồ sơ nhân vật (Kho), thể loại, khung hình | Phân tích kịch bản, đường cảm xúc, cách kể bằng hình, diễn xuất, giọng, ghi chú kịch bản; duyệt chốt | Quay phim (cùng một lần gọi Director); người dùng (ghi chú) | cảnh: `beat`, `emotional_intent`, `time`, `mood`, `lighting`, `weather`; shot: `performance`, `role`, `hero`; câu: `delivery`; gốc: `tradeoffs`, `script_notes` |
| **Quay phim** | Ý đồ + diễn xuất của Đạo diễn | Vị trí máy, cỡ/góc/ống kính, chuyển động, bố cục, ánh sáng, gói bối cảnh, khớp môi; lý do | Motion (prompt video), ảnh (prompt khung đầu), máy ảo Blender | shot: `size`, `angle`, `camera_move`, `lens_mm`, `start_frame`, `end_state`, `image_prompt`, `camera_setup`, `plate_spot`, `plate_mode`, `lip_sync`, `why` |
| **Dựng** | Clip đã duyệt, giọng, chữ, nhạc, SFX | Cắt, giọng, âm nhiều lớp, nhạc, màu + khớp màu, hiệu ứng, chữ + vùng an toàn, độ to, tự rà | Người dùng (bản giao) | bản dựng, phụ đề, bản xuất theo nền tảng |
Trả ngược: lỗi hình → Quay phim (gen lại có đổi đầu vào, ≤ 2 lần); lỗi diễn/giọng → Đạo diễn; kịch bản yếu → người viết (chỉ đề xuất).

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
| Chữ và bố cục | Quay phim: chừa chỗ cho chữ, mắt dưới thanh giao diện | Dựng: vùng an toàn trên 15% / dưới 35% (code 36%, đệm) / phải 18% | Máy ảo đặt mắt ~21–28% (`plate_camera.HEADROOM`); một bộ số (`safe_zones.md`), code dùng chung (`subtitles.SAFE_*`) |
| Thời tiết | Đạo diễn: mang cảm xúc (Đ3) | Quay phim: ánh sáng có nguồn (Q8); Dựng: âm + hiệu ứng thời tiết | Một trường `weather` → nền (`plate_env`), màu người (`composite`), lớp rơi, (âm: việc code D4) |
| Tiêu cự | Quay phim: bảng mm theo cảm xúc | Máy ảo: `FRAMING` theo cỡ | Mặc định theo `FRAMING`; `lens_mm` ghi đè, máy ảo giữ cỡ người và tự lùi/tiến |
| Độ dài shot | Đạo diễn N2: thoại đủ thời gian nói | Dựng E1: cắt ngắn ở cao trào | Thoại thắng (ưu tiên 2); cao trào ngắn ở shot không thoại |
| Thời gian nói | Đạo diễn N2, prompt 01 | prompt 17, code | Một số: âm tiết ÷ 3,5 + 0,5 s (`dialogue.BREATH`) — prompt 17 sửa từ 0,4 |
| `beat` | Đạo diễn Đ1 (giá trị đổi, gieo–gặt) | prompt 01 (object) | Một dạng object: `want, obstacle, turn, value, plant, payoff`; code kiểm gặt có gieo |
| Âm nền | Dựng E3 (nền không khí liên tục) | `sfx_plan` (chỉ điểm nhấn) | Hai lớp riêng: `sfx_plan` = điểm nhấn; nền không khí = việc code D5 |
| Móc câu | Đạo diễn N5 / Đ2 | TikTok chính thức | Mốc dự án 1–3 s (giả thuyết); nguồn chính thức: ý chính ≤ 3 s, móc ≤ 6 s |

## Việc code còn thiếu (kỹ năng có trong bộ nhưng pipeline chưa làm — không để im)
Đã làm trong GĐ4: trường `performance` (ảnh + motion + QC + dấu vân tay + cảnh báo), `delivery` → tham số TTS (cờ `voice_direction`),
`why`, `lens_mm` → máy ảo, `script_notes` + kiểm `tradeoffs` (bàn đo + Bước 1), khối "Gói bối cảnh" cho Director + báo chỗ đứng lạ
(autopilot), Q4 sinh từ `provider_rules.json`, lề phải phụ đề 18%, mắt dưới thanh giao diện (máy ảo), hồ sơ rút gọn (`profile_digest`, cờ),
**V1 kiểm gieo–gặt** (`beat.plant/payoff`, bàn đo), **đo LUFS + đỉnh thật** (`ffmpeg_studio.measure_loudness` — phần đo của D11).
| Mã | Việc | Vai | Tốn tiền? |
|---|---|---|---|
| V1 | ✅ Đã làm: cảnh có `beat.payoff` mà không cảnh trước nào có `beat.plant` → ⚠ | Đạo diễn | — |
| V2 | Ô sửa `performance` / `delivery` / `why` trong ô sửa shot (Bước 1) | Đạo diễn/Quay phim | Không |
| V3 | Nghe thử `delivery` với giọng Việt (thẻ âm có bị đọc thành chữ không) rồi bật `voice_direction` | Đạo diễn | Vài lượt âm thanh |
| V4 | Sơ đồ vị trí máy nhìn từ trên (từ `camera_setup` + `start_frame`) | Quay phim | Không |
| V5 | Kiểm trục 180° / hướng màn hình từ `start_frame` các shot liền nhau | Quay phim | Không |
| V6 | Trường motif (`motif_of: <shot>`) + ai-biết-gì để Dựng/QC đối chiếu | Đạo diễn | Không |
| V7 | Kiểm giọng đúng `delivery` bằng máy (hiện chỉ có người nghe theo bảng kiểm) | Đạo diễn | Chưa rõ |
| D1 | Cắt J/L: giọng vào sớm 4–12 khung ở chỗ đổi người nói | Dựng | Không |
| D2 | Điểm cắt theo chuyển động trong clip (khác biệt khung) | Dựng | Không |
| D3 | Dọn thoại (lọc 80 Hz, khử xì) khi có giọng thu | Dựng | Không |
| D4 | Âm theo `weather` (mưa/gió/sấm đúng giây chớp `plate_env.flash_times`) | Dựng | Lượt âm thanh (hoặc thư viện) |
| D5 | Nền không khí liên tục cả cảnh | Dựng | Lượt âm thanh (hoặc thư viện) |
| D6 | Khoảng lặng nhạc 0,3–1 s trước cú ngoặt | Dựng | Không |
| D7 | **Khớp màu giữa các shot** cùng `sequence`/nơi (đo vùng tối/sáng, chỉnh về shot neo) — cần nhất khi bật gói bối cảnh | Dựng | Không |
| D8 | Khớp hạt người–nền khi ghép | Dựng | Không |
| D9 | Rung máy khi va chạm, hạt, lóa | Dựng | Không |
| D10 | Bảng tên nhân vật động kiểu game | Dựng | Không |
| D11 | ✅ Đo độ to mọi bản dựng (manifest + Bước 5); chuẩn hóa −14 LUFS / −1,5 dBTP sau cờ `loudness_normalize` (TẮT) | Dựng | — |
| D12 | ✅ `_ENCODE` có `+faststart` + thẻ màu BT.709 | Dựng | — |
| D14 | ✅ Đo: nhạc hạ 14,5–22,8 dB dưới giọng thật #7 (khuyên 6–10) → **người dùng quyết** có nhẹ tay hơn | Dựng | — |
| D13 | Ảnh chồng lớp giao diện app lên khung để tự rà | Dựng | Không |
| P1 | `lock_short`/`lock_medium` do Claude viết cho hồ sơ dài (KENTA: bản code 500 ký tự mất áo khoác xanh + găng tay trái) | Hồ sơ | ~$0,01/nhân vật |
