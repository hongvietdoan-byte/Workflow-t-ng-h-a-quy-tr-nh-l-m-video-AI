# Kỷ luật chuyển động I2V (ảnh → video) — 3 mục

> Nguồn: tài liệu khung I2V motion prompt người dùng đưa 04/10 (bảng Risk Assessment + mục preservation), đối chiếu trong
> `docs/KE_HOACH_BO_NAO_PROMPT_TU_HOC_2026-10-04.md` Đợt 2c. Chỉ lấy 3 mục chưa có ở các tài liệu motion khác (từ vựng máy, cấu trúc
> prompt, cách viết Seedance/Kling đã có — không lặp). Mọi mức "nhiều/ít/mạnh" dưới đây là **heuristic** rút từ kinh nghiệm người làm,
> **không phải thông số nhà cung cấp**; cảnh có lý do rõ thì được làm khác, ghi lý do vào `check_flags`.

## 1. Sáu rủi ro + cách chữa (cũng là từ điển tag lỗi)
Trước khi viết, nhìn ảnh khung đầu + hành động và hỏi shot này dính rủi ro nào. Tên tag dùng chung với bài học lỗi (`core/lessons.py`
`RISK_TAGS`) — ghi `check_flags` bắt đầu bằng đúng tên tag để lỗi thật sau này gom đúng nhóm.

| tag | dấu hiệu rủi ro | cách chữa (theo thứ tự thử) |
|---|---|---|
| `face_morph` | quay đầu nhiều, cận mặt, mặt nhỏ trong khung, mặt bị che | giảm góc quay đầu, giảm chuyển động máy, bớt hành động đồng thời |
| `body_deform` | tư thế cực đoan, động tác nhanh, nhiều khớp cùng đổi | giảm biên độ, chia hành động thành nhịp / thành 2 shot |
| `wardrobe_drift` | trang phục phức tạp, vải rộng, máy di chuyển nhiều | khóa thiết kế trang phục, chỉ cho phần vải cần phản ứng (gió, quán tính) chuyển động |
| `background_drift` | orbit / parallax mạnh, kiến trúc nhiều chi tiết | giảm cường độ máy, giữ một điểm neo nền nhìn thấy suốt clip |
| `motion_overload` | quá nhiều thứ cùng chuyển động (người + máy + vật + hiệu ứng) | giảm "ngân sách chuyển động": một máy + một hành động chính |
| `text_logo_corrupt` | chữ nhỏ, logo, UI / HUD trong khung | đừng yêu cầu model animate chữ / logo; để chúng đứng yên hoặc ra khỏi khung |

Bốn tag phản hồi khác (để lỗi người xem báo có chỗ rơi, không phải rủi ro để viết prompt): `identity` (sai người / đổi người giữa clip),
`physics` (xuyên vật, trôi nổi, trượt chân), `lipsync` (môi lệch câu), `audio` (âm thanh / nhạc / giọng sai).

## 2. Giữ trước, chuyển động sau (preservation-first)
Luật "KHÔNG mô tả lại ngoại hình" của prompt motion là lệnh **cấm nói**; mục này là việc **phải nghĩ** trước khi chọn chuyển động.
1. Liệt kê (trong đầu, không chép vào prompt) cái phải giữ nguyên suốt clip: **nhận diện** (mặt, tóc), **tỉ lệ** người/vật, **trang phục**,
   **logo / chữ**, **đạo cụ** trên tay, **bố cục** (ai ở đâu trong khung, điểm neo nền).
2. Với mỗi thứ phải giữ, hỏi: chuyển động định viết có ép model vẽ lại nó không (quay đầu → vẽ lại mặt; orbit → vẽ lại nền; vung áo →
   vẽ lại trang phục)? Có thì đổi chuyển động, đừng hy vọng model giữ được.
3. Chỉ sau đó mới chọn máy + hành động. Thứ gì được phép đổi thì nói rõ (vd chỉ tà áo bay), còn lại im lặng = giữ nguyên ảnh.
4. Đánh đổi giữa các yêu cầu: xếp theo `knowledge/craft/uu_tien_cam_xuc.md` — cảm xúc của shot trước, liền mạch không gian 3D sau cùng.

## 3. Hỏng thì GIẢM chuyển động trước, đừng thêm tính từ điện ảnh
Luật dự án: gen lại phải **đổi đầu vào** (tự động video ≤ 2 lần — `docs/CHUAN_XAY_DUNG.md` luật 6). Mục này nói **đổi theo hướng nào**.
Thêm "cinematic, epic, dramatic, ultra detailed" không phải là đổi đầu vào có chủ đích — chúng thường tăng chuyển động và tăng rủi ro.
Thứ tự thử (dừng ở bước đầu tiên chữa được lỗi đã thấy):
- **P0** — Gọi đúng tên lỗi theo tag ở mục 1 (lỗi thấy được, không đoán). Không gọi được tên → chưa gen lại, ghi lại để người xem.
- **P1** — Giảm chuyển động máy: bỏ orbit / parallax / đường máy dài → đẩy nhẹ hoặc máy tĩnh.
- **P2** — Giảm hành động: một hành động chính, biên độ nhỏ hơn, chậm hơn; hành động dài → chia nhịp hoặc chia shot.
- **P3** — Siết danh sách giữ nguyên: nói rõ điểm neo nền, thứ không được đổi; bỏ chữ / logo khỏi phần chuyển động.
- **P4** — Đổi ảnh đầu vào: khung đầu khác (mặt to hơn, ít bị che, ít chữ trong khung) hoặc tách shot.
- **P5** — Đổi model (theo luật chọn model của dự án) — sau cùng, vì đổi model đổi luôn cách đọc prompt và giá.
