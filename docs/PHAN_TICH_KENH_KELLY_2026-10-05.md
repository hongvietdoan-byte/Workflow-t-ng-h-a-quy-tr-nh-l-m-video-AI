# Báo cáo phân tích kênh `@freefire_kelly_official` — Đợt 1 (05/10/2026)

> Việc **S14.32**, kế hoạch `docs/KE_HOACH_PHAN_TICH_KENH_KELLY_2026-10-05.md`. Chi phí **0 USD** (không gọi Claude API / dịch vụ trả tiền; gán nhãn trong phiên Claude Code). Chờ người dùng duyệt trước khi đưa luật vào prompt nào.
> Đầu ra: `knowledge/ff_styles/kelly_official.md` (phong cách, luật GỢI Ý) · `knowledge/craft/ne_canh_kho_dung.md` (kỹ thuật né cảnh khó dựng) · `research/kelly_official/phieu_40_clip.md` (phiếu từng clip) · `research/kelly_official/ghi_chu_hinh.md` (ghi chú hình) · `research/kelly_official_records/KELLY_SHOW/*.json` (nhãn từng shot, 33 clip).

## 1. Phạm vi và cách làm
- **40/40 clip đọc xong, không clip nào lỗi / bị chặn.** Mỗi clip: `reference_video.py sheets` (cắt shot + bảng khung) + bảng 6–12 khung đều theo thời gian (vì bộ cắt bỏ sót cắt khi hậu cảnh giống) + `audio_listen.py` (demucs + AudioSet + whisper). Video, khung hình, work_dir ở thư mục tạm ngoài git; repo chỉ giữ chữ + số đo; không cắt ghép / dùng lại hình của kênh.
- 33 clip ngắn (5–27 s) có nhãn từng shot; 7 clip tổng kết ~60 s (K04, K07, K08, K16, K18, K19, K20) chỉ đọc 12 khung đều + số đo âm thanh (bộ cắt bỏ sót nhiều cắt ở đây).
- Giới hạn: MỘT kênh; mốc giây ± 1 bước khung; âm thanh "nghe bằng số", lời whisper phần lớn là lời hát nhạc trend; chưa kiểm khớp môi.

## 2. Số đo chung (33 clip ngắn, 202 shot, 468 s)
- Clip: trung vị **14,3 s** (5,0–27,4 s); **9/33 là một cú máy liền**; clip nhiều shot: shot trung vị **1,5 s**, ≈ 10 % shot ≥ 4 s; 26 shot/phút (cận dưới).
- Cỡ cảnh: trung 36 %, cận 29 %, trung cận 15 %, toàn 15 %. Máy **tĩnh 91 %**, track 4 %. Ngang mắt 79 %.
- Chữ trên hình 21 % shot; HUD/giao diện game 17 % shot (20/33 clip có ít nhất một lần); 15/33 clip có chữ hoặc HUD **ngay shot đầu**.
- Âm thanh: nhạc trend ≥ 90 % thời lượng ở **38/40** clip; thoại gốc của nhân vật gần như không có (chỉ "What?" [K02], "Hmm" [K01]); hiệu ứng game thay thoại [K14 giọng thông báo kill].
- Nhóm view cao (13 clip ngắn): trung vị 3 shot/clip, 10/13 có HUD; nhóm mới nhất (10 clip): 7 shot/clip, 3/10 có HUD, view trung vị ≈ 107 nghìn so với ≈ 13 triệu (không suy ra nhân quả).

## 3. Năm phát hiện chính
1. **"Trong game" luôn được thể hiện bằng lớp thông tin, không bằng cảnh đánh trận:** HUD số đội + tên + thanh máu + đầu lâu trên đầu [K01, K11, K34], bảng đội + bộ đếm kill [K14, K18], icon hạng / kỹ năng [K03, K32, K35], thẻ UI [K17, K20, K34]. Người xem hiểu "sắp chết / thua / quadra" mà không có một khung hình gameplay nào.
2. **Bối cảnh là cảnh đời thường (văn phòng, canteen, bếp, công viên, lớp học…), không phải map FF.** Map chỉ là đạo cụ (TV bản đồ [K33], bản đồ dán tường [K02]).
3. **Định dạng dựng dễ nhất lại chiếm vị trí cao:** 1 shot cận Kelly + đồ hoạ trend (ống ngắm "Shooting Age Test" [K27], "My rank" [K40], STOP [K15], thanh emoji [K12], nhãn + gem [K31]) — 1 nhân vật, 1 nền, 5–12 s.
4. **Gag theo mẫu "tình huống → insert cận vật từ trên xuống → phản ứng mặt"** [K13, K22, K39]; cú chốt là phản ứng, hiếm CTA (2/40: [K21, K37]).
5. **Âm thanh = nhạc trend + hiệu ứng game, không thoại.** Với pipeline: khớp môi gần như không cần cho dạng này; nhạc trend cần giải bài toán bản quyền riêng.

## 4. Định dạng kịch bản "dựng chắc được" (đề xuất đưa vào S14.31 + bộ ý tưởng đo lại S14.22)
| Mức | Định dạng | Mẫu | Điều kiện chắc |
|---|---|---|---|
| Chắc | **A. 1 cận + đồ hoạ trend** (5–12 s) | K12, K27, K15, K40, K31, K34, K05 | 1 nhân vật có ảnh Kho, 1 nền đơn giản, đồ hoạ làm hậu kỳ |
| Chắc | **B. Tiểu phẩm 2–4 shot tĩnh + HUD** (8–15 s) | K01 (lia 1 cú: cần tách 3 shot), K06, K11, K14, K33, K36 | ≤ 2 nhân vật cùng khung, 1 nền đời thường, HUD / bảng kill làm hậu kỳ |
| Khá | **C. Quảng bá sự kiện** (17 s) | K21 | nền cửa hàng + chữ bong bóng + poster do đội thiết kế |
| Vừa | **D. Gag nhiều shot ngắn "insert + phản ứng"** (10–16 shot) | K13, K22, K39 | ≥ 3 nhân vật + đồ vật 3D (đĩa, nồi…) + nhất quán mặt qua nhiều shot — chi phí gen cao |
| Khó | **E. Chuỗi chạy / nhảy / rượt** | K30, K32, K35, K26 | chuyển động mạnh, nhiều nền — dễ lỗi |
| Ngoài pipeline | **F.** hợp tác người thật [K25]; cận điện thoại thật [K09, K10, K28]; tổng kết ghép cảnh cũ [K07…]; video bên thứ ba [K24] | — | cần footage thật / thư viện cảnh |

## 5. Tài nguyên còn thiếu (để dựng A–D)
- **Bối cảnh đời thường nhất quán** (văn phòng sọc đỏ, canteen, bếp, công viên + ghế đá, lớp học, phòng chờ, hành lang): chưa có trong Kho; cần ảnh / 3D từng nơi + câu bố cục.
- **Lớp HUD hoạt hình hậu kỳ:** thanh máu + chip số đội + tên + đầu lâu; bảng đội 4 dòng + bộ đếm kill; icon hạng / kỹ năng; thẻ TEAM INVITE / SUPER REVIVAL / hòm loot; thanh emoji; ống ngắm — cần module hậu kỳ (hiện chưa kiểm công cụ Dựng có hỗ trợ).
- **Tư liệu giao diện chính thức** (huy hiệu hạng, icon kỹ năng, thẻ UI đúng phiên bản) để làm HUD đúng; không có → HUD giản lược, ghi rõ.
- **Nhân vật phụ trong Kho:** Maxim, Alvaro, Shirou, Hayato / Tatsuya, nữ tai mèo, chim cánh cụt kính đen (pet), ALOK; biểu cảm mặt (sốc, bịt miệng, vùi mặt).
- **Đồ vật đời thường 3D:** cốc, đĩa, chảo, hộp quà, bóng rổ, túi đá…
- **Nhạc / hiệu ứng được phép dùng** (giọng thông báo kill, tiếng súng, chuông): hỏi bản quyền trước khi dùng nhạc trend.
→ Việc tạo tài nguyên sau, **hỏi tiền trước**.

## 6. Việc mở
- Người dùng duyệt luật (`kelly_official.md`) và danh mục (`ne_canh_kho_dung.md`) trước khi nạp vào prompt Biên kịch / Đạo diễn (qua cờ TẮT mặc định, như S14.20).
- Bổ sung định dạng A–D vào S14.31, đo lại 5 ý tưởng S14.22 bằng khuôn A/B.
- Đợt 2 (40 clip thêm theo dạng còn thiếu) chỉ khi Đợt 1 có ích; cần cân nhắc vì mẫu "view cao" lệch theo thời gian — nên lấy thêm clip 2026 nhiều view.
- Nghe tai các chỗ "nghe bằng số" (nhạc to lên giây 3–4, khoảng lặng K10).

---

# Đợt 2 (S14.33, 05/10/2026) — 40 clip bổ sung + thu tài nguyên

> Người dùng duyệt 05/10: kênh thuộc quyền dùng của họ. **Mục đích:** (1) mở rộng phong cách làm + dựng, mở rộng Kho tài nguyên FF dùng lại được (ưu tiên âm thanh, HUD / icon, nền, đồ vật, biểu cảm); (2) mọi quy định né tránh / việc có thể làm chỉ là **GỢI Ý** — trong knowledge viết "có thể / khi nào hợp / điều kiện", không "cấm / bắt buộc". Chi phí **0 USD** (không gọi Claude API / dịch vụ trả phí; gán nhãn trong phiên).

## Tải về
- **40 clip** từ `@freefire_kelly_official` bằng yt-dlp (2026.08.19): 32 clip 2026 nhiều view (4,8 triệu … 381 nghìn) + 8 clip theo dạng còn thiếu (collab Jujutsu / Naruto / Gintama, bóng đá, quiz Solo/Duo, ghép khán đài, gift drop…). Tổng **92,8 MB**, 519 s, không clip nào lỗi. Lưu `D:\AI-Video-Pipeline\data\ref_kelly\<id>.mp4` (ngoài git), nối `list.tsv` (cột lý do `dot2`), thư mục làm việc `data/ref_kelly/work/E01…E40` (bảng khung đều, bảng shot, nghe bằng số).
- Đã kiểm độ dài tiếng ≈ độ dài hình ở cả 40 clip (lệch ≤ 0,04 s; không có hiện tượng tiếng cụt như S0.12).
- Danh sách id / view / tiêu đề + ghi chú hình + âm thanh từng clip: `research/kelly_official/phieu_dot2_40_clip.md`.

## Số đo (cận dưới do bộ cắt tự động bỏ sót cắt)
Trung vị 13,0 s (5–30 s); 4 shot / clip (8/40 là một cú máy); shot TB ≈ 2,4 s; ≈ 25 shot/phút; nhạc có ở 40/40 clip (46–100 % thời lượng).

## Phát hiện mới (chi tiết + clip dẫn chứng: `knowledge/ff_styles/kelly_official.md` mục "Đợt 2" và `knowledge/craft/ne_canh_kho_dung.md` mục 12–20)
1. 2026 vẫn dùng lớp đồ hoạ trạng thái làm cách kể "trong trận": 17/40 tiểu phẩm 3D có HUD / icon / thẻ / huy hiệu / tỉ số; thêm 5/40 xen UI / gameplay quay màn hình (E32 bản đồ, E39 gameplay, E29 TikTok / redeem, E16 chế độ chibi, E03 hồ sơ ĐT).
2. **Tỉ số / bộ đếm / dải DEFEAT** là đồ hoạ dễ làm (E38, E40, E12, E07, E01); **huy hiệu hạng đổi theo hành động** (E14, E15, E17, E18, E19).
3. **Đạo cụ lớn làm tâm điểm gag** (E27, E25, E26, E24, E11, E21); **khuôn A vs B chia dọc** (E07, E27, E33); **cú chốt glitch / emoji** (8 clip).
4. **Quảng bá collab / sự kiện** có khuôn riêng (logo cố định + nhân vật 2D ghép 3D + thẻ chốt: E02, E21, E26, E36) và tập trung ở nửa view thấp của mẫu 2026 (8/20 so với 1/20) — số đo, không phải nhân quả.
5. **Giọng thông báo kill** có thêm ở E01 (Double / Triple kill) và E12 (Unstoppable) ngoài K14 → ≥ 3 clip, đủ làm gợi ý.
6. Cơ cấu định dạng gần Đợt 1: "một cận + đồ hoạ" và "tiểu phẩm 2–4 shot + HUD" vẫn là hai nhóm dễ dựng nhất; ngoài pipeline: sự kiện thật (E31), bicycle kick / chuyển động mạnh (E34), ghép khán đài thật (E33).

## Tài nguyên đã thu về Kho (CHỜ DUYỆT, không tự duyệt)
- **Kho âm thanh:** nguồn mới `D:\AI-Video-Pipeline\data\ref_kelly\kho_am_thanh` (sound_sources id 2, quét bằng `core/sound_lib`): **14 nhạc trend** (nguyên mix, kèm lời hát; mood theo tên) + **3 giọng thông báo kill** (E01 4,3–5,8 s Double kill; E01 10,4–11,5 s Triple kill; E12 10,2–12,4 s Unstoppable — cắt từ stem giọng demucs, CHƯA nghe tai). Nguồn id clip + mốc giây + ghi "người dùng xác nhận quyền dùng 05/10/2026" ở `kho_am_thanh/NGUON.tsv`. Không tách sạch nhạc khỏi lời hát → nhạc là bản gốc kèm lời.
- **Kho ảnh:** **18 mục / 33 ảnh** (kind prop / location / character / style; status `pending`; created_by `S14.33`): HUD ô vũ khí + đếm đạn (3), kill + chip tên (2), thẻ Revival / Super Revival (2), BOOYAH (2), Solo / Duo (2), TEAM INVITE (1), icon kỹ năng giày (1), huy hiệu hạng (4), pin yếu (2), UI hồ sơ + phần thưởng (2), bản đồ + vòng bo (1), bảng điểm + DEFEAT (3), nền bãi cỏ + hòm đạn (1), nền khung thành (1), lựu đạn xanh (1), máy đấm hơi BOOYAH (1), Top Criminal (1), biểu cảm Kelly / Maxim (3). Cắt từ khung 1080×1920, lưu `data/ref_kelly/khung_sach/` + bản trong `data/assets/<id>/`. Vài HUD còn dính phần nhân vật phía sau — người duyệt nên xem. Ảnh `pending` tổng: 37 → 70.
- Sao lưu `data/backup/manifest.before_s14_33_2026-10-05.sqlite` trước khi ghi.

## Tài nguyên nên tạo 3D (chỉ liệt kê, KHÔNG tạo; chờ hỏi tiền)
Ước theo `docs/RESEARCH_3D_PREVIZ.md` (ảnh → 3D có texture ≈ 30 credit / vật, rig ≈ 5; Pro 1.000 credit / tháng): ~10 vật ≈ 300 credit (~1/3 hạn mức Pro tháng), chưa gồm làm lại.
1. Đồ vật đời thường (≈ 8): cốc minh hoạ nhân vật, đĩa khoai + bao lì xì F, burger, bóng rổ / bóng đá, vali nhiều màu, bao rác + túi xu, ghế đá công viên, bàn tròn gỗ.
2. Máy đấm hơi BOOYAH arcade, hòm đạn đầu lâu (≈ 2; đã có ảnh tham chiếu trong Kho).
3. Nhân vật phụ thiếu bộ chuẩn (≈ 4, tốn hơn vật): Top Criminal, nữ tai mèo đồng phục, nữ kính bay cam, nữ tóc tết xanh–tím.
4. Nền (không phải việc của Meshy): canteen, văn phòng, phòng ngủ, công viên, sân bóng rổ có mural, tiệm tóc, thang cuốn — ảnh nền Kho / gen ảnh.
5. HUD hoạt hình hậu kỳ (module Dựng).

## Việc mở
- Người dùng duyệt / loại 33 ảnh `pending`, nghe thử 17 âm thanh; nghe tai các mốc "nhạc to lên".
- Quyết định có nạp mục 12–20 vào prompt Biên kịch / Đạo diễn (cờ TẮT) hay không.
- Logo / nhân vật IP đối tác (Naruto, Gintama, Jujutsu) ở E02 / E21 / E26 / E36 KHÔNG thu vào Kho (tài sản bên thứ ba, cần phép riêng).
- Chưa gán nhãn từng shot (JSON KELLY_SHOW) cho 40 clip Đợt 2; nếu cần số đo shot chính xác, chạy `reference_video.py save` ở phiên sau.
