# Phương pháp thiết kế âm thanh — cách Đạo diễn quyết `sound` của một shot

> Dùng cho trường `sound` (`music` keep|cut|in|breath, `sfx` ≤ 3, `music_fn`, `why`) mà Đạo diễn ghi ở shot cần âm thanh mang cảm xúc
> (`core/sound_intent.py`; người lồng âm `core/sfx_plan.py` coi ý của Đạo diễn ưu tiên hơn nguyên tắc chung). Tài liệu này dạy **cách
> quyết**, không phải bảng tra: cùng một âm có thể phục vụ ý đồ khác nhau tùy cảnh — luôn ghi `why`. Âm cụ thể chỉ chọn được trong kho đã
> gán nhãn của người dùng; kho không có thì cứ ghi ý đồ, code sẽ báo thiếu (`sound_intent.unmet`) — không tự bịa tên file.

## 1. Ba lớp của một khoảnh khắc: dẫn → đập → đuôi
- **Lớp dẫn** (trước khoảnh khắc, 0,3–1 s): âm báo trước làm người xem nín thở — tiếng thở, tiếng vải, một âm kéo dài nhỏ dần, hoặc
  chính sự rút bớt âm nền. Nhiệm vụ: dồn chú ý, không phải gây ồn.
- **Lớp đập** (đúng khung hình của khoảnh khắc): một âm rõ, ngắn, đặt trùng hành động / cú cắt — lệch vài khung hình là mất tác dụng.
  Một khoảnh khắc chỉ có **một** cú đập chính.
- **Lớp đuôi** (sau cú đập): âm vang, tiếng rơi, tiếng thở ra, hoặc khoảng lặng để người xem thấm. Đuôi cho biết hậu quả — thiếu đuôi,
  cú đập nghe như lỗi.
- Không phải shot nào cũng cần đủ ba lớp; shot bình thường để `sound` trống. Dùng khi khoảnh khắc là chỗ truyện đổi chiều hoặc cảm xúc
  đỉnh (đọc thêm thang `knowledge/craft/uu_tien_cam_xuc.md`: âm thanh phục vụ cảm xúc trước).

## 2. Ý đồ → chất âm (ngôn ngữ ý đồ, không phải tên file)
| Ý đồ của khoảnh khắc | Chất âm có thể phục vụ (chọn theo cảnh, ghi `why`) |
|---|---|
| Mối đe dọa xuất hiện | nhạc `cut` hẳn; một âm trầm, gần, nhỏ (bước chân, kim loại chạm) |
| Bình yên giả | nhạc nhẹ giữ nguyên, thêm một âm môi trường lạc tông rất nhỏ |
| Lộ mặt / tiết lộ | lặng ngắn (`breath`) rồi một cú đập rõ đúng khung lộ |
| Hạ gục / cú bắn quyết định | đập mạnh, khô, ngắn; đuôi vang hoặc lặng sau đó |
| Sững người / sốc | rút gần hết âm nền, giữ tiếng thở hoặc ù tai; nhạc vào lại muộn |
| Quyết tâm / đứng dậy | tiếng nắm chặt, tiếng vải, nhịp nhạc vào (`in`) đúng lúc đứng lên |
| Căng thẳng tăng dần | âm kéo dài lớn dần, nhịp thưa dần dày; tránh đập trước cao trào |
| Giải tỏa / thắng | nhạc trở lại đầy (`in`, `music_fn: release`); đuôi dài, thoáng |
| Hài / phá không khí | một âm lệch nhịp, ngắn, khô ngay sau câu thoại; không đè lên câu |
| Hồi tưởng / ký ức | âm nền mờ đi, vang hơn; một âm lặp lại làm dấu (`music_fn: memory`) |
| Chuyển nơi / chuyển thời gian | âm môi trường của nơi mới vào trước hình (cắt J), hoặc một âm lướt ngắn |
| Kỹ năng / sức mạnh kích hoạt | lớp dẫn tích tụ ngắn → đập đúng khung hiệu ứng → đuôi tản |
| Tốc độ / truy đuổi | âm lướt theo hướng chuyển động, nhịp dày; nhạc giữ (`keep`) |
| Cô đơn / mất mát | âm môi trường thưa, xa; nhạc rất nhỏ hoặc tắt; không đập |
| Thân mật / thì thầm | âm nền hạ thấp, giữ tiếng thở và tiếng vải gần |
| Kết / chốt truyện | cú đập cuối hoặc lặng hẳn, sau đó đuôi dài tới khung cuối |

Bảng chỉ gợi ý hướng; một khoảnh khắc "đe dọa" vẫn có thể giữ nhạc nếu ý đồ là cho người xem biết trước điều nhân vật chưa biết.

## 3. Luật khoảng lặng
- **Cao trào có sức nặng nhờ cái lặng ngay trước nó.** Muốn cú đập mạnh, làm trước nó nhỏ đi (`breath` ≈ 0,6 s hoặc `cut` từ shot trước)
  thay vì làm cú đập to hơn.
- Trong khoảng lặng một âm nhỏ nghe rất rõ: đặt **một** âm nhỏ có nghĩa (tiếng thở, tiếng nuốt, tiếng kim loại), đừng lấp bằng hiệu ứng to.
- Lặng phải có lý do kịch bản và có điểm kết (`in`): lặng kéo dài không lý do nghe như nhạc bị lỗi (code đã giới hạn một đoạn tắt nhạc —
  `sound_intent.MAX_OFF_S` — trừ khi dự án chọn nhạc thưa).
- Thoại luôn nghe rõ: khoảng lặng và cú đập không được đè lên câu thoại.

## 4. Chống lạm dụng
- Cú nhấn chỉ có tác dụng khi hiếm: nhiều cú đập / stinger liền nhau làm người xem **chai cảm giác** (nguồn tổng hợp:
  `research/craft/draft/nhac_nen.md` mục Stinger, độ tin vừa). Một video ngắn thường chỉ cần vài khoảnh khắc có `sound`, không phải mọi shot.
- `sfx` tối đa 3 âm mỗi shot, và chỉ âm của khoảnh khắc đó (cơ thể, một vật then chốt) — không kê âm nền chung.
- Không dùng âm để vá hình: hình chưa rõ chuyện gì xảy ra thì sửa hình / shot, đừng bù bằng cú đập to.
- Không gán nghĩa cố định: "tim đập = hồi hộp", "chuông = kết thúc" chỉ đúng ở một số cảnh — mỗi lần dùng ghi `why` cho cảnh này.
