# S0.12 — Tổng hợp quan sát nhiều phim (cập nhật sau 3/8 video, đã tải + đo bằng ffmpeg)

> 3/8 video đã xem (01 AI心動劇場, 02 TOMORROW/Omeleto, 03 WARLIKE/BIGFILMS) — **video 01 và 02 đã làm lại bằng phương pháp tải về +
> ffmpeg/ffprobe (chính xác hơn hẳn lượt đo trong trình duyệt trước)**. Theo phương pháp (`knowledge/craft/PHUONG_PHAP_PHAN_TICH.md` mục
> 1–2): quan sát thấy ở **≥ 2 video** mới viết dưới dạng "mẫu hình bước đầu" (kèm điều kiện, độ tin); quan sát 1 video vẫn ở nguyên trong
> file riêng.

## Đổi phương pháp giữa chừng (2026-09-29)
Phiên chính cho phép tải đoạn video về máy (yt-dlp, xoá ngay sau khi phân tích, không đưa vào repo) thay vì chỉ xem qua trình duyệt.
Kết quả: **số đo chính xác hơn nhiều** (điểm cắt bằng `ffmpeg scene score` thay vì canvas trình duyệt bị giới hạn 45s/lệnh; đo được LUFS/
LRA/đỉnh thật/quãng lặng bằng `ebur128`+`silencedetect` — trước đó hoàn toàn không đo được gì về âm thanh). Video 01 và 02 đã **làm lại
toàn bộ** với phương pháp mới; số liệu trong 2 file đó đã thay thế số liệu lượt trước.

## Mẫu hình bước đầu (thấy ở ≥ 2/3 video)

### 1. Nhịp cắt đổi theo mức độ "chuyển động/thông tin" của cảnh — nhưng KHÔNG đổi ở phim thoại liên tục
- Video 01 (AI drama, thoại liên tục): nhịp cắt **gần như hằng số** suốt phim đã đo (median 1.4–2.0s ở cả 2 đoạn cách nhau 74 phút).
- Video 02 (phim ngắn CGI, ít thoại): nhịp cắt **đổi rất mạnh** — đoạn thiết lập/dạo đầu chậm (median 3.7s), cụm bạo lực rút xuống <1s, đoạn cao trào súng kéo dài 18–40s/shot không cắt.
- Video 03 (hành động, không thoại rõ): nhịp cắt **đổi mạnh tương tự** — đoạn đánh nhau median 1.84s (33 shot/phút), đoạn mở đầu/kết chậm hẳn (median 4.72s, gấp 2.5×).
- **Mẫu hình bước đầu [có thể]**: khi hình ảnh/hành động là phương tiện kể chuyện chính (video 02, 03), nhịp cắt bám sát mức độ kịch tính từng đoạn; khi thoại là phương tiện chính và thoại gần như liên tục suốt phim (video 01), nhịp cắt giữ ổn định vì luôn có "1 câu ≈ 1 shot" bất kể nội dung cảm xúc của câu đó. **Điều kiện**: mới thấy ở 3 mẫu thuộc 3 thể loại khác hẳn nhau (không phải lặp lại trong-thể-loại) — cần thêm video AI drama thứ 2 (mục 4 trong danh sách 8 video) để biết đây là đặc trưng "AI drama nói chung" hay riêng video 01.
- Điểm thú vị: **khi video 01 CÓ đoạn hành động (dù không có, chỉ đối thoại) và video 03 vào đoạn đánh nhau, hai nhịp cắt hội tụ về cùng độ lớn (~1.8-2.0s, ~30-34 shot/phút)** dù thể loại khác hẳn — gợi ý có thể tồn tại một "trần nhịp cắt nhanh" chung mà nhiều thể loại hội tụ về khi cần dồn dập, bất kể nội dung là thoại hay hành động. Độ tin: đoán, cần thêm mẫu.

### 2. Âm thanh liên tục vs ngắt quãng — chia theo phương tiện kể chuyện
- Video 01 (thoại là chính): **46 và 33 quãng lặng** trong 180s và 68s — nhạc/âm thanh ngắt thường xuyên giữa các câu; ~60% quãng lặng trùng một điểm cắt shot.
- Video 02 (hình ảnh là chính, ít thoại): chỉ **11 và 3 quãng lặng** trong 180s và 130s.
- Video 03 (hành động, không thoại rõ): chỉ **1 quãng lặng duy nhất trong cả 240.9s** (đúng đoạn credit cuối).
- **Mẫu hình bước đầu [có thể → khá vững, 3/3 video cùng hướng]**: phim/video có thoại làm phương tiện kể chuyện chính có âm thanh ngắt theo nhịp câu nói; phim/video kể chuyện chủ yếu bằng hình ảnh + hành động giữ nhạc/SFX chạy gần như liên tục không ngắt. Đây là quan sát nhất quán nhất trong 3 video, đáng tin hơn mục 1 vì cả 3 đều cùng chiều.
- LRA (khoảng động âm lượng): video 01 (thoại) ~8.7-8.8 LU, video 02 (hình ảnh, nhiều cao trào) 18.1–21.3 LU (rất rộng), video 03 (hành động liên tục) 10.1 LU (vừa) — **[có thể]**: phim có nhiều đoạn tương phản cảm xúc (yên tĩnh xen cao trào) có LRA rộng hơn phim giữ một mức căng thẳng tương đối đều (hành động liên tục) hoặc phim thoại đều đều.

### 3. Đỉnh âm vượt/chạm 0 dBFS ở đoạn cao trào — 3/3 video có dấu hiệu này
> **Kiểm duyệt phiên chính (2026-09-29): KHÔNG dùng được làm mẫu hình.** Đỉnh đo trên file tải về đã nén lại (Opus/WebM) — giải mã
> nén có tổn hao thường vượt đỉnh gốc 1–3 dB, nên "> 0 dBFS" có thể do file tải chứ không do phim. Chỉ LUFS / LRA / quãng lặng là đáng tin.
- Video 01: đỉnh 0.0 dBFS (đoạn mở đầu).
- Video 02: đỉnh **3.4 dBFS** (đoạn cao trào súng — bất thường, vượt hẳn 0dBFS).
- Video 03: đỉnh **1.8 dBFS** (toàn phim, nhiều đoạn hành động).
- **Mẫu hình bước đầu [có thể]**: nhiều kênh/phim (kể cả phim trường lớn như Omeleto/Media Design School) không giới hạn true-peak limiter đủ chặt ở đoạn âm lượng cao nhất — hiện tượng **không phải lỗi riêng của kênh AI** như ban đầu nghĩ (đã thấy ở cả 3 nguồn khác hẳn nhau: AI drama, CGI festival, hành động chuyên nghiệp) — có thể là hiện tượng phổ biến trong ngành khi master cho streaming/YouTube (codec nén lại có thể tạo inter-sample peak vượt 0dBFS dù bản gốc không vượt). Cũng giống clip mẫu ClipAI đã phân tích trước (+0.7 dBFS). **4/4 mẫu âm thanh đã đo trong dự án này đều có đỉnh ≥ 0dBFS** — đáng chú ý nhưng cần hiểu là có thể do khâu nén lại của YouTube/yt-dlp chứ chưa chắc là file gốc, ghi rõ độ tin **vừa**.

## Quan sát chỉ 1 video (chưa đủ điều kiện thành mẫu hình)
- Video 02: cấu trúc có ít nhất 2 biến cố lớn cách nhau ~10 phút (đánh nhau ở phút ~2, đe doạ súng ở phút ~13) — bài học phương pháp quan trọng: **không nên chọn đoạn "cao trào" theo tỉ lệ % thời lượng** khi không có mục lục, vì có thể bỏ lỡ hoặc trùng lặp biến cố.
- Video 01: shot đầu một cảnh mới có xu hướng dài hơn nhịp chung (9.7s so với median ~2s) — mới 1 lần quan sát.

## Giới hạn chung cả 3 video
- **Không nghe được âm thanh bằng tai** ở cả 3 video (môi trường agent không có audio playback) — bù bằng số đo `ebur128`/`silencedetect`/RMS, đáng tin hơn hẳn so với "không có gì" ở lượt đầu, nhưng vẫn không thay được việc nghe thật (không biết nhạc là thể loại gì, có trùng nhịp hành động không, lời bài hát nếu có).
- **`camera_move` per-shot không đo được đáng tin** ở cả 3 video — chỉ số khác biệt khung xám (giống `scratchpad/ref/motion.py`) lẫn giữa chuyển động máy, diễn xuất, và (với video 01) cả phụ đề đổi từng khung — không tách được. Nhãn `camera_move` trong các file đều ghi rõ đây là giới hạn, không suy diễn quá mức.
- Video 01: 3.3% video đã đo (248s/7413.7s). Video 02: 31% (310s/1005s). Video 03: 100% (240.9s/240.9s, phim ngắn nên đo hết).

## Đã xoá dữ liệu tải về
Cả 5 lượt tải (video 01 đoạn 1+2, video 02 đoạn 1+2, video 03 toàn phim) đã bị xoá khỏi `scratchpad/s012` ngay sau khi viết xong file
phân tích tương ứng — chỉ giữ lại các file JSON số đo (không phải hình/âm) để agent sau có thể đối chiếu số liệu mà không cần tải lại.

## Việc còn lại
- 5/8 video chưa xem: 《我的婆婆是軟柿子》, RISE (Worlds 2018), 《逃不出大哥手掌心》, Fortnight, 《大师兄》.
- Đã bổ sung mục "1b. DramaBox" vào `MAU_S0_12.md` (3 mẫu đã xác minh, chưa phân tích) theo yêu cầu — xem file đó.
- Cần người dùng nghe nhạc nền trực tiếp cho cả 3 video đã xem để xác nhận các suy đoán từ số đo (nhạc ngắt/liên tục, đỉnh vỡ có nghe thấy không, LRA rộng có đúng là cao trào-yên tĩnh xen kẽ).
- Nhãn TOMORROW trong `MAU_S0_12.md` đã được phiên chính sửa thành CGI 3D.
