# Bổ sung Đạo diễn / Quay phim — bài học duyệt ảnh #24 (11/10)

Cách nghĩ rút từ lần người dùng soi 10 ảnh #24. Mỗi điều có LÝ DO và CĂN CỨ; khi hai điều va nhau, điều trên thắng. Đây không phải
luật cấm từ — là cách tính trước khi viết. Code kiểm lại các điều đo được (mức VÀNG, `core/shot_lessons.py`, `core/stage_facts.py`).

1. **Thấy gì do hình học quyết, không do ý muốn.** Máy thấp hơn miệng một vật (giếng, tường, bàn) thì KHÔNG thấy mặt trên / lòng của
   nó — chỉ thấy thành ngoài, mép trên nhìn ngang. Muốn thấy miệng giếng → máy phải cao hơn miệng và nhìn xuống. Vì: #24 shot 5 máy
   0,5 m trước giếng cao 0,9 m mà ảnh vẽ thấy miệng giếng — bị loại. Căn cứ: câu "Camera height …" code nối vào prompt ảnh (sự thật
   hình học của máy 3D). Mọi chỗ chữ của shot (image_prompt, blocking, action_peak) phải nói cùng một điều — câu phủ định ("never the
   opening") là được, câu tả lòng giếng là trái.
2. **Động tác di chuyển làm đổi chỗ đứng.** Nhịp có bò / trườn / đi / lùi / chạy (hoặc ref video có di chuyển) → điểm cuối = điểm đầu
   + quãng; ước quãng theo thân người (trườn ra khỏi giếng ≈ rướn một thân người: tâm người cách thành ≥ 1–1,5 m) hoặc theo ref. Ghi
   `den` (điểm cuối) cho nhịp đó; nhịp sau lấy `den`. Vì: #24 dàn cảnh để yêu nữ 0,25 m cách thành ở mọi nhịp sau khi trườn ra →
   shot 7 / 9 / 10 sai bố cục, lệch shot 8 đã duyệt. Căn cứ: hồ sơ tư thế (prompt 29 mục 2), video ref.
3. **Sửa chỗ một người → giữ bố cục các ảnh ĐÃ DUYỆT.** Người kia giữ nguyên vị trí, khoảng cách và bên trái/phải trong khung như ảnh
   đã duyệt; không giữ được thì nói rõ shot đã duyệt nào phải duyệt lại. Vì: ảnh đã duyệt là chuẩn người dùng đã chọn.
4. **Ref động tác / emote: liệt kê đủ nhịp + chi tiết nhỏ trước khi viết.** Một emote thường có nhiều nhịp (vd khóc: quỳ ôm mặt nấc →
   dang tay gào → gục rạp chống tay) và chi tiết nhỏ (nước mắt mảnh ánh xanh từ kẽ tay, vệt sẫm dưới mắt). Kịch bản / BYĐ phủ đủ hoặc
   ghi rõ lược nhịp nào, vì sao (`ref_luoc`). Vì: #24 shot 8 chỉ phủ nhịp 1 của ref khóc.
5. **Cỡ khung chứa biên độ động tác.** Dang tay / cả người không vừa CU / MCU → MS / WS cho nhịp đó. Ngược lại nhân vật quá nhỏ trong
   khung rộng (< ~25 % chiều cao khung) thì động tác từ ref truyền yếu và chi tiết mặt (nước mắt) không thấy → tách nhịp cần chi tiết
   sang cỡ chặt hơn hoặc thêm một shot cận. Căn cứ: bảng cỡ cảnh (tỉ lệ người trong khung) × tư thế (quỳ ≈ 0,7, ngồi ≈ 0,58 chiều cao).
6. **Hiệu ứng màn hình (nhiễu sóng, glitch toàn khung, sọc, mất tín hiệu) là hậu kỳ.** Không viết vào ảnh khởi đầu video — model video
   coi nhiễu là nội dung và giữ / lan cả clip. Ghi vào `post_fx` của shot để dựng bằng ffmpeg. Nhiễu là một phần thiết kế nhân vật
   (vd vệt glitch quanh cổ tay của bộ đồ) thì vẫn tả như trang phục.
