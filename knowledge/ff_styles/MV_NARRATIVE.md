# Phong cách: MV kể chuyện (clip mẫu làm bằng ClipAI)

> **GỢI Ý THAM KHẢO, KHÔNG BẮT BUỘC** (người dùng 2026-09-28): mỗi điểm có cái hay — chọn điều hợp kịch bản, trộn với phong cách khác
> (vd `DRAMA_DOC` cho cách dựng thoại), làm khác khi kịch bản cần.

Ví dụ: clip mẫu người dùng gửi 2026-09-28 — MV 201 s, 16:9, 62 shot, bài hát tiếng Trung kể người bị lừa vào sòng bạc rồi thoát ra
(phân tích + mốc giây: `docs/PHAN_TICH_CLIP_MAU_CLIPAI_2026-09-28.md`). Không phải video Free Fire; học **cách làm video AI chỉn chu,
liền mạch, dễ hiểu**.

## Cách dựng
- **Âm thanh khóa trước, 1 câu ≈ 1 shot**; hình **minh họa đúng nghĩa câu** (giơ một ngón tay ở câu "tôi có con 9"). Cắt ở ranh câu, không
  theo phách.
- **Một nhân vật, một mục tiêu, một mô-típ lặp** (con số 9 → cửa → mưa); **kết trả lời mở đầu** (cổng sắt đêm mưa → cửa mở ra mưa sáng).
- **Một bối cảnh chính** (~70 % shot) nhìn nhiều góc + 2–3 biến thể có lý do (sân khấu = điệp khúc / nội tâm; thế giới phóng to = ẩn dụ;
  cửa ra = lối thoát).
- **Chèn cận vật** (quân bài, tay, chân) để nối hai shot người; **chuyển cảnh sinh trong clip** (máy xuyên đèn chùm xuống mặt bàn) cho
  lần đổi thế giới; còn lại cắt thẳng.
- **Chuyển động là điểm mạnh**: nhảy toàn thân, nhảy nhóm đồng bộ, breakdance, váy xoay có vật lý vải — mượt thật, không lỗi. Mỗi shot
  một hành động, bắt đầu giữa chuyển động; nhân vật động gấp ~2,4 lần #8.
- **Góc máy mang nghĩa**: thấp = bị áp đảo, cao nhìn xuống = bị vây, sau lưng = quyết định rời đi.

## Look
Một bảng màu cả phim (tím–vàng, sàn bóng phản chiếu); màu nhân vật hòa màu bối cảnh; đổi ánh sáng theo truyện (đêm mưa → sáng sau mưa).
Nhân vật đám đông không mặt (mũ trùm, đồng phục) → không trôi mặt, không khớp môi; nhân vật chính có ≥ 3 dấu hiệu nhận diện.

## Khi dùng cho AI video
- Clip mẫu là **MV** nên né được khớp môi; với drama thoại: câu then chốt cận người nói + khớp môi, câu khác có thể nghe ngoài hình
  (phản ứng / cận vật) để giảm chi phí.
- Động tác khó / nhảy nhóm: dùng **video tham chiếu chuyển động** (suy luận cách clip mẫu làm); dàn cảnh bằng hình đơn giản thay vì ảnh
  dáng chi tiết (Director Workspace ClipAI khuyên — ảnh dáng chi tiết làm Seedance bắt chước cứng).
- Số đo: shot trung vị 2,5 s (trung bình 3,25 s); nhạc −14,6 LUFS liên tục, năng lượng tăng dần. Chưa có bản ghi `research/` → không có
  bảng số tự sinh.
