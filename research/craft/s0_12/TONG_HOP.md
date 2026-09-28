# S0.12 — Tổng hợp quan sát nhiều phim (cập nhật sau 2/8 video)

> Chỉ 2/8 video đã xem (01 AI心動劇場, 02 TOMORROW/Omeleto). Theo phương pháp (`knowledge/craft/PHUONG_PHAP_PHAN_TICH.md` mục 1–2): quan sát thấy ở **cả 2 video** mới được viết dưới dạng "mẫu hình bước đầu" (kèm điều kiện); quan sát chỉ ở 1 video vẫn ở nguyên trong file riêng, không đưa vào đây.

## Đã xem được cả 2 video ở khía cạnh nào

### Nhịp cắt khác biệt rõ theo mục đích/thể loại (đúng cả 2 video, nhưng theo hướng NGƯỢC nhau)
- Video 01 (AI short drama, 爽剧): nhịp cắt rất nhanh và **đều** trong mọi đoạn đã đo (median 1.6–2.0s, 29–34 shot/phút) — kể cả đoạn mở đầu lẫn đoạn giữa phim.
- Video 02 (phim ngắn CGI tự sự): nhịp cắt **không đều** — mở đầu vừa phải (median 3.1s, 38 shot/3 phút) nhưng đoạn gần cuối gần như không cắt (median ước lượng ~35s, chỉ 3 cắt/2 phút).
- **Mẫu hình bước đầu [có thể]**: định dạng xem lướt trên điện thoại/gộp tập (video 01) giữ nhịp cắt nhanh xuyên suốt để không rời mắt người xem; phim ngắn có đạo diễn tính (video 02) thay đổi nhịp cắt theo mục đích từng đoạn (nhanh khi thiết lập, chậm hẳn khi cần khoảng lặng cảm xúc). Đây là quan sát ở 2 mẫu thuộc 2 thể loại khác hẳn nhau (không phải cùng thể loại lặp lại), nên **không đủ để kết thành luật** — chỉ ghi là câu hỏi cần theo dõi tiếp khi xem thêm 6 video còn lại (đặc biệt video khác cùng nhóm AI short drama và cùng nhóm phim ngắn để so trong-nhóm).

### Ngưỡng phát hiện điểm cắt (`cuts_from_diffs`) không dùng chung một bộ số cho mọi video
- Cả 2 video đều cần **nâng ngưỡng cao hơn mặc định** (18/4/25/3) mới ra số cắt hợp lý khi đối chiếu bằng mắt: video 01 dùng 30/5/35/4 (khớp ngưỡng nghiên cứu DRAMA_DOC trước), video 02 phải nâng tiếp lên 40/6/45/5 vì nhiễu chuyển động máy/lá cây.
- **Ghi nhận kỹ thuật (không phải nghệ thuật)**: khi làm S0.12 các video sau, nên luôn dò vài mức ngưỡng và đối chiếu bằng mắt trước khi chốt số shot, không dùng một ngưỡng cố định cho mọi video.

## Giới hạn chung cả 2 video
- **Không nghe được âm thanh cả 2 video** (Web Audio không gắn được vào iframe YouTube trong phiên trình duyệt, không tải video) — mục "Nhạc nền" của cả 2 file đều ghi "không nghe được — cần người dùng nghe". Đây là giới hạn công cụ, không phải phát hiện về phim.
- **Không lấy được ảnh mẫu cho từng shot theo hệ thống** (video 01 bị quảng cáo giữa video + lỗi làm mới khung khi tua lúc pause; video 02 thì đỡ hơn — không gặp quảng cáo, khung làm mới đúng khi seek lúc đang phát) — bảng shot-by-shot đầy đủ **chưa có cho cả 2 video**, chỉ có số đo cắt (khách quan) + một số khung quan sát rời rạc bằng mắt.
- Cả 2 video: chỉ xem 240–300s trên một video dài hơn nhiều (video 01: 3.2%, video 02: 30%) — kết luận chỉ mang tính cục bộ.

## Sửa lỗi phát hiện được trong `MAU_S0_12.md`
- Mục 2.1 (TOMORROW) ghi "live-action" nhưng khi xem trực tiếp đây là **CGI 3D animation** — cần sửa nhãn thể loại trong bảng gốc (đã ghi trong `02_tomorrow_omeleto.md`).

## Việc còn lại
- 6/8 video chưa xem: WARLIKE, 《我的婆婆是軟柿子》, RISE (Worlds 2018), 《逃不出大哥手掌心》, Fortnight, 《大师兄》.
- Cần tìm cách xác nhận đúng điểm cao trào/lật mặt cho các video dài (không có mục lục) — thử đọc bình luận ghim hoặc mô tả đầy đủ ("...more") trước khi tua ước lượng theo tỉ lệ thời lượng.
- Cần người dùng nghe nhạc nền trực tiếp cho cả 2 video đã xem (không có cách nào trong trình duyệt để agent tự nghe).
