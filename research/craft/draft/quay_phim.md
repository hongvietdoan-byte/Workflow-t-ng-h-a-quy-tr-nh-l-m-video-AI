# Kho kỹ thuật — Quay phim (draft S0.11, 2026-09-29)

> **Kiểm duyệt của phiên chính (2026-09-29) — BẢN NHÁP, CHƯA vào `knowledge/`:**
> - Nhiều mục ghi nguồn là **trang chủ** (theasc.com, rogerdeakins.com) hoặc "tóm tắt qua tìm kiếm", không phải bài cụ thể đã đọc trọn →
>   theo phương pháp mục 3, độ tin của các mục đó tạm hạ xuống **vừa** cho tới khi đọc bài gốc (có tên bài, người nói, đoạn liên quan).
> - Nguồn đọc được trọn / xác minh link: DGA — Dan Attias; ProVideo Coalition — Murch; Designing Sound — Randy Thom; VFX Voice; Team Deakins
>   (trang podcast). Một số trang chặn tải tự động (Frame.io, A Sound Effect, LBBOnline, No Film School, British Cinematographer) — cần mở
>   bằng trình duyệt ở lượt đọc kỹ.
> - Đã sửa: chuyển cảnh che máy có thể sinh trong 1 lần (clip mẫu 2:20,6) — không khẳng định "model không tự làm"; số 2,4 lần là mức chuyển
>   động so với #8; ví dụ *Locked* chưa xác minh.
> - Việc kế: lượt đọc kỹ nguồn gốc (thay trích dẫn chung bằng bài cụ thể) + ví dụ có mốc giây từ S0.12, mới đưa vào `knowledge/craft/`.


> Theo mẫu mục 4 `knowledge/craft/PHUONG_PHAP_PHAN_TICH.md`. Đây là **draft chờ duyệt**, chưa nhập vào `knowledge/roles/dp.md`.
> Góc máy, cỡ cảnh, ánh sáng không có nghĩa cố định — mỗi mục liệt kê nhiều ý đồ có thể kèm điều kiện.

### Góc máy thấp (low angle)
- Cách làm: đặt máy dưới tầm mắt chủ thể, hướng lên.
- Có thể phục vụ: ý đồ A — tăng cảm giác uy quyền/đe dọa của chủ thể (khi chủ thể là mối đe dọa hoặc đang thắng thế) · ý đồ B — cho thấy
  không gian/trần cao, kiến trúc đồ sộ bao quanh nhân vật nhỏ bé (không nói về quyền lực của người, mà về tỉ lệ không gian) · ý đồ C — góc
  nhìn chủ quan của một nhân vật đang nằm/ngồi thấp (trẻ em, người bị ngã) — ý nghĩa do ngữ cảnh, không cố định.
- Khi hợp / khi không: hợp khi câu chuyện tại thời điểm đó cần nhấn lệch cán cân quyền lực hoặc tỉ lệ không gian; không hợp nếu dùng tràn
  lan sẽ làm mọi cảnh "nặng nề" như nhau, mất tác dụng tương phản.
- Ví dụ: chưa có mốc giây — cần xem mẫu ở S0.12 (đối chiếu với phim ngắn/short drama ưu tiên học trước).
- Với video AI: mô tả trong prompt vị trí máy tương đối so với chủ thể ("camera low angle, looking up at subject") + lý do trong ghi chú nội
  bộ (không đưa lý do vào prompt); giới hạn: model dễ làm sai tỉ lệ phối cảnh khi góc quá thấp kết hợp chuyển động — nên test tĩnh trước khi
  thêm chuyển động máy.
- Nguồn: American Cinematographer (ASC) — theasc.com, đọc 2026-09-29, cao (nguyên tắc góc máy tổng hợp từ nhiều phỏng vấn DP, không phải
  1 bài cụ thể — cần bổ sung ví dụ nêu tên phim ở S0.12).

### Góc máy cao (high angle) / góc nhìn từ trên
- Cách làm: máy đặt cao hơn tầm mắt, hướng xuống chủ thể.
- Có thể phục vụ: ý đồ A — làm chủ thể nhỏ bé/yếu thế (khi tình huống là bị dồn ép, cô lập) · ý đồ B — cho khán giả cái nhìn tổng quan không
  gian (dàn cảnh đông người, địa hình) không liên quan gì đến quyền lực nhân vật · ý đồ C — góc nhìn của một thực thể quan sát từ trên (máy
  bay, nhân vật khác đứng trên cao) — luôn đọc theo mạch truyện tại chỗ đó.
- Khi hợp / khi không: hợp khi cần thiết lập không gian hoặc đúng lúc truyện cần nhân vật "bị nhìn từ trên xuống"; không hợp khi dùng để
  "cho đẹp" ở cảnh không liên quan tới tương quan giữa nhân vật và hoàn cảnh.
- Ví dụ: chưa có mốc giây — cần xem mẫu ở S0.12.
- Với video AI: prompt ghi rõ độ cao máy tương đối ("high angle establishing shot" khác với "overhead/bird's eye") vì model dễ nhầm hai loại
  này; overhead thường cần mô tả rõ mặt phẳng nằm ngang bên dưới để tránh méo phối cảnh.
- Nguồn: American Cinematographer — theasc.com, đọc 2026-09-29, cao.

### Ống kính rộng vs tele — nén không gian (lens compression)
- Cách làm: chọn tiêu cự ống kính; ống rộng (wide) làm giãn không gian và phóng đại khoảng cách trước-sau, ống dài (tele) nén không gian,
  làm các lớp cảnh gần nhau lại.
- Có thể phục vụ: ý đồ A — wide để nhấn sự cô lập của nhân vật trong không gian rộng, hoặc gây méo gương mặt khi cận cảnh (khó chịu, xâm
  lấn) · ý đồ B — tele để cô lập chủ thể khỏi nền (xóa phông, cảm giác riêng tư/thân mật) hoặc dồn nén đám đông tạo cảm giác ngột ngạt trong
  cảnh hành động/đuổi bắt · điều kiện: hiệu ứng nén chỉ rõ khi có nhiều lớp chiều sâu trong khung.
- Khi hợp / khi không: DP thường chọn theo cảm giác không gian mà cảnh cần (rộng mở hay dồn nén), không theo quy tắc cứng "cận cảnh = tele".
- Ví dụ: chưa có mốc giây — cần xem mẫu ở S0.12.
- Với video AI: mô tả rõ "wide-angle lens, deep space" hoặc "telephoto compression, background compressed" trong prompt; model hiện tại
  (Seedance/Kling) diễn giải "tele" tốt hơn khi mô tả kèm hiệu ứng nhìn thấy được (nền mờ + gần) thay vì chỉ ghi số mm.
- Nguồn: Grant MacAllister — "The Cinematography Bookshelf" (định hướng đọc thêm), đọc 2026-09-29, vừa; đối chiếu thêm với Team Deakins
  Podcast (rogerdeakins.com), cao — cần nghe tập cụ thể về lens choice (Episode "Lens Choice in your project") ở S0.12.

### Máy tĩnh (locked-off) khi xung quanh chuyển động
- Cách làm: máy hoàn toàn không di chuyển trong khi diễn viên/đối tượng trong khung chuyển động.
- Có thể phục vụ: ý đồ A — tạo cảm giác quan sát khách quan, để khán giả tự nhìn thay vì bị dẫn dắt (thường dùng ở cảnh cần sự thật/khách
  quan, phim tài liệu-tính) · ý đồ B — tương phản với các cảnh có máy chuyển động nhiều trước đó, đánh dấu một khoảnh khắc "đứng lại" trong
  mạch phim (im lặng, chờ đợi, sốc) — ý nghĩa phụ thuộc vào vị trí trong mạch phim, không tự nó mang nghĩa "tĩnh = buồn".
- Khi hợp / khi không: hợp khi đạo diễn muốn khán giả tự quan sát mà không bị máy "chỉ đạo" cảm xúc; không hợp nếu toàn phim đã tĩnh — mất
  tương phản.
- Ví dụ: chưa có mốc giây — cần xem mẫu ở S0.12.
- Với video AI: dễ làm nhất trong các loại chuyển động máy (ít lỗi biến dạng), nên dùng làm baseline khi test model mới trước khi thêm
  chuyển động máy.
- Nguồn: Roger Deakins — Team Deakins Podcast, rogerdeakins.com, đọc 2026-09-29, cao.

### Độ sâu trường ảnh nông (shallow depth of field / xóa phông)
- Cách làm: khẩu độ mở lớn, chủ thể nét — nền/tiền cảnh nhòe.
- Có thể phục vụ: ý đồ A — cô lập chủ thể về mặt cảm xúc/tâm lý (thế giới xung quanh "mờ đi" với nhân vật) · ý đồ B — che giấu chi tiết nền
  không muốn khán giả để ý (kể cả lý do kỹ thuật: nền dàn dựng chưa hoàn chỉnh) · ý đồ C — dẫn mắt khán giả đến đúng vật/người cần chú ý
  trong khung nhiều lớp — không phải lúc nào cũng là ẩn dụ tâm lý.
- Khi hợp / khi không: hợp khi cảnh cần sự tập trung tuyệt đối vào một điểm; không hợp cho cảnh cần khán giả đọc cả không gian (dàn cảnh
  hành động nhiều lớp, MV vũ đạo nhóm).
- Ví dụ: chưa có mốc giây — cần xem mẫu ở S0.12.
- Với video AI: nêu rõ "shallow depth of field, background heavily blurred, subject in sharp focus" — một số model (Seedance 2.5) xử lý DOF
  tốt hơn khi có 1 chủ thể rõ ràng trong prompt; nhiều chủ thể cùng lúc dễ làm model nét sai lớp.
- Nguồn: American Cinematographer — theasc.com, đọc 2026-09-29, cao (nguyên tắc tổng hợp từ nhiều bài phỏng vấn DP).

### Ánh sáng động cơ (motivated lighting)
- Cách làm: mọi nguồn sáng trong khung có lý do hợp lý trong thế giới cảnh phim (đèn bàn, cửa sổ, đèn đường) dù ánh sáng thật được bổ sung
  từ đèn trường quay.
- Có thể phục vụ: ý đồ A — giữ tính chân thực, khán giả không nhận ra "có ánh sáng dàn dựng" · ý đồ B — dùng nguồn sáng có lý do để kể thời
  gian/không gian (nắng xế = chiều muộn) · ý đồ C — cường điệu hóa nguồn sáng có lý do (đèn neon quá mạnh) để tạo phong cách riêng (noir,
  cyberpunk) — vẫn "có lý do" nhưng được đẩy quá thực tế.
- Khi hợp / khi không: gần như luôn là điểm khởi đầu an toàn; chỉ bỏ qua khi phong cách phim chủ động phi thực (biểu hiện, sân khấu hóa).
- Ví dụ: chưa có mốc giây — cần xem mẫu ở S0.12.
- Với video AI: prompt nên mô tả NGUỒN sáng trong cảnh (ví dụ "warm light from table lamp, cool blue moonlight through window") thay vì chỉ
  tả "cinematic lighting" chung chung — mô tả nguồn cụ thể giúp model nhất quán hướng sáng qua nhiều shot của cùng bối cảnh.
- Nguồn: Roger Deakins — Team Deakins Podcast, rogerdeakins.com, đọc 2026-09-29, cao.
