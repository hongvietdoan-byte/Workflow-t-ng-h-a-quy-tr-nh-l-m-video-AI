# Kho kỹ thuật — Dựng phim (draft S0.11, 2026-09-29)

> **Kiểm duyệt của phiên chính (2026-09-29) — BẢN NHÁP, CHƯA vào `knowledge/`:**
> - Nhiều mục ghi nguồn là **trang chủ** (theasc.com, rogerdeakins.com) hoặc "tóm tắt qua tìm kiếm", không phải bài cụ thể đã đọc trọn →
>   theo phương pháp mục 3, độ tin của các mục đó tạm hạ xuống **vừa** cho tới khi đọc bài gốc (có tên bài, người nói, đoạn liên quan).
> - Nguồn đọc được trọn / xác minh link: DGA — Dan Attias; ProVideo Coalition — Murch; Designing Sound — Randy Thom; VFX Voice; Team Deakins
>   (trang podcast). Một số trang chặn tải tự động (Frame.io, A Sound Effect, LBBOnline, No Film School, British Cinematographer) — cần mở
>   bằng trình duyệt ở lượt đọc kỹ.
> - Đã sửa: chuyển cảnh che máy có thể sinh trong 1 lần (clip mẫu 2:20,6) — không khẳng định "model không tự làm"; số 2,4 lần là mức chuyển
>   động so với #8; ví dụ *Locked* chưa xác minh.
> - Việc kế: lượt đọc kỹ nguồn gốc (thay trích dẫn chung bằng bài cụ thể) + ví dụ có mốc giây từ S0.12, mới đưa vào `knowledge/craft/`.


> Draft chờ duyệt. Dựa nhiều vào lý thuyết Walter Murch (đã kiểm qua nhiều nguồn thứ cấp trích dẫn ông, cộng 1 nguồn ông tự đính chính).

### Thứ tự ưu tiên khi chọn điểm cắt (Murch's "Rule of Six")
- Cách làm: khi có nhiều lựa chọn điểm cắt hợp lệ, editor xếp hạng theo 6 tiêu chí: Cảm xúc → Câu chuyện → Nhịp điệu → Hướng nhìn mắt khán
  giả (eye-trace) → Liên tục 2 chiều (planarity) → Liên tục 3 chiều (continuity vật lý, ví dụ trục 180°).
- Có thể phục vụ: ý đồ A — khi cảm xúc và tính liên tục vật lý xung đột (ví dụ cắt đúng lúc diễn viên chớp mắt = đúng cảm xúc, nhưng lệch
  trục 180°), Murch ưu tiên cảm xúc trước, chấp nhận phá vỡ liên tục vật lý nếu cần · ý đồ B — dùng thang ưu tiên này để giải quyết tranh
  cãi "cắt ở đâu" giữa nhiều lựa chọn kỹ thuật đều đúng.
- Khi hợp / khi không: đây là thứ tự ưu tiên khi có mâu thuẫn, không phải luật áp cho mọi cảnh — cảnh hành động có thể cần ưu tiên nhịp điệu
  hơn cảm xúc tinh tế (vì bản chất cảnh là tốc độ).
- Ví dụ: chưa có mốc giây phim cụ thể — cần xem mẫu ở S0.12; lý thuyết trích từ sách *In the Blink of an Eye* của Murch.
- Với video AI: áp dụng ở khâu dựng (chọn/ghép các clip đã sinh), không phải lúc sinh clip; khi phải chọn giữa 2 lần sinh cùng 1 shot, ưu
  tiên bản nào đúng cảm xúc/nhịp cảnh hơn là bản nào "đẹp" hơn về mặt kỹ thuật.
- Nguồn: Walter Murch, ACE — qua tổng hợp trích dẫn tại jonnyelwyn.co.uk/film-and-video-editing/the-walter-murch-opedia/, đọc 2026-09-29,
  cao (nội dung là phát biểu/lý thuyết gốc của Murch, trang chỉ tổng hợp trích dẫn — nên tìm đọc nguyên bản sách khi có điều kiện); đối
  chiếu thêm StudioBinder (studiobinder.com/blog/walter-murch-rule-of-six/), đọc 2026-09-29, vừa (diễn giải lại, không phải nguồn gốc).

### Nhịp cắt và "chớp mắt" của khán giả
- Cách làm: chọn điểm cắt trùng hoặc ngay trước khoảnh khắc diễn viên chớp mắt / có một "đổi ý nghĩ" trên gương mặt — Murch quan sát nhịp
  cắt phim khớp thống kê với nhịp chớp mắt tự nhiên của con người.
- Có thể phục vụ: ý đồ A — cảnh thoại bình thường nhịp cắt chậm hơn (phim Mỹ trung bình khoảng 6 cắt/phút với cảnh thoại) · ý đồ B — cảnh
  hành động thuyết phục có thể lên tới khoảng 25 cắt/phút — số liệu là quan sát của Murch trên phim cụ thể ông dựng, không phải công thức
  bắt buộc cho mọi phim/mọi thời đại (phim hiện đại cắt nhanh hơn nhiều so với thời Murch viết sách).
- Khi hợp / khi không: dùng làm điểm tham chiếu cảm nhận (cảnh này có đang "thở" đúng nhịp câu chuyện không), không dùng làm chỉ tiêu đếm
  cắt/phút cứng nhắc.
- Ví dụ: chưa có mốc giây — cần xem mẫu ở S0.12.
- Với video AI: khi lên kịch bản phân đoạn (số lượng clip cần sinh cho 1 cảnh thoại vs 1 cảnh hành động), có thể dùng tỉ lệ này làm ước
  lượng thô ban đầu rồi điều chỉnh theo cảm nhận thật, không áp cứng.
- Nguồn: Walter Murch, qua tổng hợp jonnyelwyn.co.uk, đọc 2026-09-29, cao (gốc là lý thuyết Murch); ProVideo Coalition — Murch tự đính
  chính cách hiểu lý thuyết của mình, provideocoalition.com/aotc-murch-books/, đọc 2026-09-29, cao.

### Tiết chế số lượng cắt trong cảnh hành động
- Cách làm: thay vì cắt liên tục để tạo cảm giác nhanh, editor cân nhắc giữ shot dài hơn ở một số cú đánh/động tác quan trọng để khán giả
  "cảm" được lực/kỹ thuật, chỉ cắt nhanh ở những đoạn nối tiếp phụ.
- Có thể phục vụ: ý đồ A — mỗi lần cắt buộc mắt và não khán giả định hướng lại trong khung mới; cắt quá dày trong pha đánh nhau có thể làm
  khán giả KHÔNG cảm nhận được cú đánh (ngược với mục đích "tạo cảm giác dồn dập") · ý đồ B — cắt dày đặc có chủ đích khi muốn gây choáng
  ngợp/hỗn loạn (ví dụ mô tả một vụ va chạm, một khoảnh khắc mất phương hướng của nhân vật) — vẫn là lựa chọn có điều kiện, không mặc định.
- Khi hợp / khi không: cảnh võ thuật/đấu tay đôi có kỹ thuật đẹp nên giữ shot đủ dài để thấy rõ đòn thế; cảnh hỗn loạn/tai nạn có thể cắt
  dày để truyền cảm giác mất kiểm soát.
- Ví dụ: Evan Schiff dựng phim *Nobody*, *John Wick* — quan điểm "phải hỏi mỗi lần cắt có thực sự cần thiết không" (Frame.io Insider, chưa
  có mốc giây cảnh cụ thể — cần xem mẫu ở S0.12).
- Với video AI: liên quan trực tiếp đến độ dài mỗi lần sinh — nếu muốn khán giả "cảm" một động tác trong video AI, clip nguồn cho động tác
  đó cần đủ dài và mượt (không cắt sớm), phần dựng chỉ nên chêm cắt nhanh ở các đoạn nối.
- Nguồn: Evan Schiff (editor, *John Wick*, *Nobody*), phỏng vấn "Art of the Cut" — Frame.io Insider, blog.frame.io/2021/05/19/art-of-the-cut-
  evan-schiff-nobody/, đọc 2026-09-29, cao.

### Đọc nhịp điệu qua độ dài shot (không chỉ nhịp nhạc)
- Cách làm: editor phân tích vì sao một đạo diễn/editor cụ thể giữ một shot bao lâu — dựa trên nội dung thông tin trong khung, không chỉ
  dựa trên nhạc nền.
- Có thể phục vụ: ý đồ A — shot dài hơn khi khung có nhiều thông tin cần khán giả đọc (bố cục phức tạp, nhiều nhân vật) · ý đồ B — shot rất
  ngắn khi thông tin đơn giản, lặp lại có chủ đích để tạo nhịp gấp (phong cách hành động của một số đạo diễn cụ thể) · điều kiện: "công thức"
  4 giây hay 1,5 giây không tồn tại — mỗi đạo diễn/thể loại có nhịp riêng cần học qua quan sát mẫu thật, không suy từ lý thuyết chung.
- Khi hợp / khi không: dùng cách phân tích này để HỌC phong cách một mẫu cụ thể, không dùng để áp đặt một con số chung cho mọi dự án.
- Ví dụ: Tony Zhou (editor, kênh "Every Frame a Painting") phân tích phong cách dựng của nhiều đạo diễn (Scorsese, Jackie Chan, Michael
  Bay) — chưa có mốc giây tập cụ thể — cần xem mẫu ở S0.12.
- Với video AI: khi phân tích 1 phim mẫu để rút kỹ thuật cho pipeline, nên đo độ dài shot thật (khung/giây) thay vì đoán, đúng theo mục 2 của
  phương pháp phân tích.
- Nguồn: Tony Zhou & Taylor Ramos — "Every Frame a Painting", tổng hợp tại en.wikipedia.org/wiki/Every_Frame_a_Painting (kênh gốc đã ngừng
  sản xuất, nội dung vẫn còn trên YouTube), đọc 2026-09-29, vừa–cao (Zhou là editor có kinh nghiệm thật, nhưng trình bày dạng luận cá nhân).

### Cắt theo câu hát vs cắt theo phách trong MV
- Cách làm: hai cách tổ chức điểm cắt trong MV — theo cấu trúc lời bài hát (câu, đoạn) hoặc theo phách nhạc (beat).
- Có thể phục vụ: ý đồ A — cắt theo phách tạo cảm giác đồng bộ hình-nhạc rõ ràng, là kỳ vọng mặc định của khách hàng/khán giả MV · ý đồ B —
  cắt theo câu hát cho phép hình ảnh "kể" theo mạch cảm xúc lời bài hát, tránh cảm giác máy móc/đoán trước được nếu lạm dụng cắt theo phách
  · thực hành phổ biến: trộn cả hai — theo câu hát ở đoạn verse, nhấn phách ở điệp khúc/cao trào.
- Khi hợp / khi không: MV có vũ đạo mạnh thường cần phách rõ; MV kể chuyện/tâm trạng thường ưu tiên câu hát; không có quy tắc "1 câu = 1
  shot" bắt buộc — đây là quy ước có thể phá vỡ có chủ đích (đã chốt ở S0.9, xem `knowledge/craft` mục nguồn nội bộ).
- Ví dụ: chưa có mốc giây — cần xem mẫu ở S0.12; đối chiếu `research/ff_styles/MV_NARRATIVE.md` đã có phân tích nội bộ.
- Với video AI: lên kế hoạch độ dài từng clip theo bảng phân nhịp (map câu hát + phách) trước khi gọi model sinh, để không phải cắt xén clip
  sau khi sinh (tốn tiền sinh lại).
- Nguồn: LBBOnline, lbbonline.com/news/more-than-just-cutting-to-the-beat-the-nuance-of-editing-music-videos, đọc 2026-09-29, vừa.
