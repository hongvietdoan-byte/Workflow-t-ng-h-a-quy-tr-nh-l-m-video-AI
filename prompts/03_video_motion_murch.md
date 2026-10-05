# Bổ sung quy tắc motion (Bộ não prompt Đợt 2 — cờ `murch_knowledge`)

- **Giữ trước, chuyển động sau** (`knowledge/i2v_motion_discipline.md` mục 2): trước khi chọn máy + hành động, nghĩ xem cái gì phải giữ
  nguyên (nhận diện, tỉ lệ, trang phục, logo/chữ, đạo cụ, bố cục). Chuyển động nào buộc model vẽ lại thứ phải giữ thì đổi chuyển động.
- **Khi các yêu cầu đá nhau**, xếp theo thang `knowledge/craft/uu_tien_cam_xuc.md`: cảm xúc của shot trước, câu chuyện, nhịp, hướng mắt,
  trục 2D, liền mạch không gian 3D sau cùng. Ghi điều đã hy sinh vào `check_flags`.
- **Ít chuyển động hơn khi có rủi ro**: một máy + một hành động chính; shot dính rủi ro thì giảm chuyển động, đừng thêm tính từ điện ảnh.
- **`check_flags` gọi đúng tên loại rủi ro**: mỗi mục bắt đầu bằng một tag `face_morph`, `body_deform`, `wardrobe_drift`,
  `background_drift`, `motion_overload`, `text_logo_corrupt` (hoặc `identity`, `physics`, `lipsync`, `audio`), rồi dấu `:` và lý do ngắn
  tiếng Việt — vd `"face_morph: cận mặt quay đầu 90° — đã giảm còn liếc mắt"`. Không có rủi ro thật thì `[]`.
