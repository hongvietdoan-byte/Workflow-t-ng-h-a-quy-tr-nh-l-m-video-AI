# Dựng video Free Fire — ngữ pháp chung (đo từ video thật)

Đo từ 19 video Free Fire (kênh Garena Free Fire VN + video nội bộ OB55), 519 shot, 1.316 giây — xem `docs/FF_STYLE_RESEARCH.md`. Phong cách riêng của dự án nằm ở `knowledge/ff_styles/<STYLE>.md`.

## Nguyên tắc
1. **Một cảnh kịch bản = nhiều shot.** Video Free Fire trung bình **~24 shot/phút**, shot trung vị **~2 giây** (phần lớn 1,0–3,4s). Một cảnh 15 giây quay một shot là sai nhịp.
2. **Nhịp do kịch bản quyết định**, không cố định: shot hành động và phản ứng ngắn; thoại để shot dài bằng câu nói; thiết lập, kết và money shot được dài hơn. Các con số chỉ là khoảng tham khảo.
3. **Mở bằng móc (hook)** trong 1–3 giây đầu (13/19 video): khoảnh khắc đắt nhất, hình ảnh gây tò mò, hoặc phản ứng hài của nhân vật chính. **Kết bằng shot kết** (19/19): tạo dáng, nhìn thẳng máy quay, câu chốt, logo.
4. **Xen phản ứng**: sau mỗi nhịp hành động hoặc câu thoại quan trọng là một shot phản ứng ngắn (0,6–1,8s) — cận mặt, mắt, cử chỉ.
5. **Chèn chi tiết** (13% shot): vật, vũ khí, kỹ năng, hiệu ứng cận — kể thông tin không cần thoại.
6. **Cỡ cảnh đa dạng**: toàn (34%) để định vị, trung/trung cận cho người nói, cận/cận đặc tả cho cảm xúc và chi tiết; không lặp một cỡ cảnh quá 3 shot liền nếu không có lý do.
7. **Máy phần lớn tĩnh (62%) hoặc đi theo (28%)**; đẩy vào, vòng quanh, lia nhanh dùng có chủ đích (cao trào, khoe trang phục, chuyển cảnh).
8. **Hiệu ứng kỹ năng** có mặt ở ~38% shot — là "chất Free Fire"; chèn shot hiệu ứng 0,3–0,5s làm chuyển cảnh.
9. **Chữ trên hình** (tiêu đề, chữ chương, con số then chốt) và **giao diện game** là đặc trưng của video gameplay/Kelly Show — làm bằng hậu kỳ (card, phụ đề), không bắt model video vẽ.
10. **Góc camera game** (`GAME_TPS`: sau lưng nhân vật, cao hơn vai, nhân vật ở 1/3 dưới khung) chiếm 79% video gameplay — dùng khi muốn "chất trong game".

## Từ vựng shot (dùng thống nhất trong Director, prompt ảnh, prompt video, QC)
- Cỡ cảnh: `ECU` cận đặc tả · `CU` cận · `MCU` trung cận · `MS` trung · `WS` toàn · `EWS` toàn rộng · `GAME_TPS` camera game · `GRAPHIC` đồ họa/tiêu đề
- Góc: `eye` · `low` · `high` · `overhead` · `dutch` · `ots` (qua vai) · `pov`
- Chuyển động: `static` · `push_in` · `pull_out` · `pan` · `tilt` · `track` · `orbit` · `handheld` · `crane` · `whip` · `zoom`
- Vai trò: `hook` · `setup` · `action` · `reaction` · `insert` · `dialogue` · `transition` · `ending`

## Thoại
- Câu thoại nằm trọn trong shot của người nói (trung cận/trung), hoặc lời nói đè sang shot phản ứng của người nghe.
- Cảnh đối thoại nhiều người: shot/đáp (người nói – người nghe) và thỉnh thoảng một shot hai người để định vị.
- Thoại dài để shot dài; đừng cắt ngang giữa câu.
