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

## Bổ sung từ duyệt ảnh thử #27 "Liệu bạn sẽ Booyah tập 1" (12/10)

7. **Vũ khí / đạo cụ đã gắn Kho cho dự án: gọi đúng TÊN trong mọi shot có nó.** Kelly cầm SKORP thì shot nào thấy súng cũng viết
   "SKORP" (kèm hình dáng ngắn), không viết chung "assault rifle / gun"; tường keo viết "bom keo / tường keo" kèm DẠNG. Vì: #27 shot
   1 / 19 / 21 viết chung → ảnh ra súng trường / AK; khâu chọn ảnh tham chiếu khớp theo tên nên không gửi ảnh Kho. Căn cứ: danh
   sách tài nguyên dự án gửi kèm. Code kiểm / chèn lại sau cờ `project_prop_lock`.
8. **Tường keo có 2 dạng, chọn một dạng và giữ cả cảnh.** (a) mặc định: tường keo màu TRẮNG trơn, không họa tiết / hình; (b) skin
   Gloowall OB55 theo ảnh Kho (người dùng 12/10). Shot sau của cùng cảnh giữ đúng dạng đã dùng. Vì: #27 shot 16 hổ phách, shot 19 băng
   xanh — hai thứ khác nhau cho cùng một bức tường.
9. **Chỗ núp / vật chắn chỉ dùng thứ CÓ trong model 3D của bối cảnh; cần thêm chỗ núp thì dùng tường keo.** Không tự vẽ thêm khối đá,
   thùng, xe… mà map không có. Bom keo là vật phẩm thật của trận đấu nên hợp lệ ở mọi chỗ. Vì: #27 shot 16 địch núp sau vật cản không
   có trong file 3D (người dùng 12/10). Căn cứ: sự thật sân khấu 3D (`stage_facts`), danh sách vật thể của chỗ đứng.
10. **Nhiều người bị hạ cùng lúc: tư thế nằm khác nhau theo cách ngã.** Úp mặt, nghiêng, co người, ngửa — không mặc định cả nhóm nằm
    ngửa dang tay. Vì: #27 shot 1 ba đồng đội nằm ngửa giống hệt nhau, người dùng yêu cầu có dáng úp gục.
11. **Được dùng mọi khu vực có trong model 3D quanh mốc** (vd bãi cỏ quanh Tháp Đồng Hồ), không chỉ quảng trường; chọn theo hành
    động của shot. Đây là gợi ý mở rộng chọn chỗ đứng (người dùng 12/10), không phải luật bắt buộc.
12. **Tỉ lệ súng so với người theo game, đo bằng chiều cao đầu.** Đo trên ảnh in-game Kelly cầm súng (người dùng 12/10, Kho
    #433/#434/#435/#436 có ảnh "kelly_cam_…_ty_le"): SKORP ≈ 3 đầu, M7 ≈ 3,3 đầu, RPK ≈ 3,7 đầu + chân chống, Hawk ≈ 4,6 đầu (người
    ≈ 7 đầu). Mọi súng chính đều cầm HAI tay, báng tì cánh tay/vai, nòng vượt qua hông bên kia — không bao giờ cỡ súng lục, không cầm
    một tay kể cả khi ăn mừng (tay kia giơ lên thì súng đeo / chống xuống, không thu nhỏ). Viết cỡ này vào câu tả shot có súng. Vì: #27
    ảnh thử SKORP bị vẽ như súng lục, cầm một tay. Căn cứ: ảnh tỉ lệ trong Kho (đo thô trên ảnh, sai số ~10 %).
    Súng KHÔNG cầm trên tay thì đeo chéo SAU LƯNG đúng cỡ thật (nòng chúc xuống, báng / ống ngắm nhô qua vai, tối đa 2 khẩu) —
    vd ăn mừng giơ tay: súng chính đeo sau lưng hoặc cầm hai tay hạ thấp, không biến thành súng lục. Viết "slung on her back" để
    gửi kèm ảnh Kho "ĐEO SÚNG SAU LƯNG".
