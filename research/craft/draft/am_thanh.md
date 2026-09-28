# Kho kỹ thuật — Âm thanh (draft S0.11, 2026-09-29)

> **Kiểm duyệt của phiên chính (2026-09-29) — BẢN NHÁP, CHƯA vào `knowledge/`:**
> - Nhiều mục ghi nguồn là **trang chủ** (theasc.com, rogerdeakins.com) hoặc "tóm tắt qua tìm kiếm", không phải bài cụ thể đã đọc trọn →
>   theo phương pháp mục 3, độ tin của các mục đó tạm hạ xuống **vừa** cho tới khi đọc bài gốc (có tên bài, người nói, đoạn liên quan).
> - Nguồn đọc được trọn / xác minh link: DGA — Dan Attias; ProVideo Coalition — Murch; Designing Sound — Randy Thom; VFX Voice; Team Deakins
>   (trang podcast). Một số trang chặn tải tự động (Frame.io, A Sound Effect, LBBOnline, No Film School, British Cinematographer) — cần mở
>   bằng trình duyệt ở lượt đọc kỹ.
> - Đã sửa: chuyển cảnh che máy có thể sinh trong 1 lần (clip mẫu 2:20,6) — không khẳng định "model không tự làm"; số 2,4 lần là mức chuyển
>   động so với #8; ví dụ *Locked* chưa xác minh.
> - Việc kế: lượt đọc kỹ nguồn gốc (thay trích dẫn chung bằng bài cụ thể) + ví dụ có mốc giây từ S0.12, mới đưa vào `knowledge/craft/`.


> Draft chờ duyệt. Nguồn chính: Randy Thom (Skywalker Sound) — "Designing a Movie for Sound", bài kinh điển ngành thiết kế âm thanh.

### Thiết kế âm thanh từ giai đoạn kịch bản (design for sound, not add sound later)
- Cách làm: nghĩ về vai trò của âm thanh (thoại, âm nền, hiệu ứng, nhạc, và cả sự IM LẶNG) ngay khi viết kịch bản/lên kế hoạch cảnh, không
  đợi đến hậu kỳ mới "thêm âm thanh vào".
- Có thể phục vụ: ý đồ A — để âm thanh có thể DẪN DẮT một khoảnh khắc thay vì chỉ minh họa cái đang thấy trên hình (ví dụ: một âm thanh
  ngoài khung hình báo trước nguy hiểm trước khi hình ảnh xác nhận) · ý đồ B — cho phép cảnh giảm bớt yếu tố hình ảnh (ít cắt, ít chi tiết
  dựng) vì âm thanh đã gánh phần truyền tải thông tin/cảm xúc, tiết kiệm được sự phụ thuộc vào hình.
- Khi hợp / khi không: hợp với mọi cảnh có ý định dùng âm thanh chủ động (không chỉ minh họa); khi âm thanh chỉ đóng vai trò nền tảng đơn
  giản (ambience) thì không cần thiết kế phức tạp — nhưng vẫn nên được quyết định có chủ đích, không mặc định "để sau".
- Ví dụ: chưa có mốc giây phim cụ thể trong bài viết được đọc — cần xem ví dụ minh họa ở S0.12 (Thom dùng ví dụ từ nhiều phim ông làm, ví
  dụ *The Right Stuff*, *Forrest Gump*, *The Incredibles* — cần đọc trọn bài gốc để lấy mốc chính xác).
- Với video AI: khi lên kế hoạch một cảnh, ghi rõ vai trò âm thanh (dẫn dắt / minh họa / im lặng có chủ đích) TRƯỚC khi chọn model sinh
  video + nhạc (Eleven Music, Seed Audio…), để phần âm thanh không bị làm cho có sau khi hình đã xong.
- Nguồn: Randy Thom — Giám đốc sáng tạo âm thanh, Skywalker Sound, 2 Oscar Âm thanh; "Designing a Movie for Sound", filmsound.org (đọc qua
  tóm tắt tại asoundeffect.com/designing-a-movie-for-sound/), đọc 2026-09-29, cao — nên đọc bản đầy đủ ở filmsound.org tại S0.12.

### Im lặng có chủ đích (deliberate silence)
- Cách làm: loại bỏ hoặc giảm mạnh âm thanh (kể cả nhạc nền) tại một khoảnh khắc cụ thể.
- Có thể phục vụ: ý đồ A — nhấn một khoảnh khắc sốc/căng thẳng bằng cách "rút" âm thanh đi (tương phản với âm lượng lớn trước/sau đó) · ý
  đồ B — mô phỏng trạng thái tâm lý của nhân vật (ù tai, mất kết nối với thực tại) · ý đồ C — cho khán giả không gian để tự cảm nhận mà
  không bị nhạc/hiệu ứng "chỉ đạo" cảm xúc.
- Khi hợp / khi không: cần có âm thanh "bình thường" trước đó để tạo tương phản — im lặng chỉ có tác dụng khi có nền so sánh; dùng liên tục
  sẽ mất hiệu quả.
- Ví dụ: chưa có mốc giây — cần xem mẫu ở S0.12.
- Với video AI: khi ghép clip đã sinh (video thường có nhạc/âm nền mặc định của model), cần chủ động hạ/tắt track âm thanh ở khâu dựng nếu
  muốn khoảnh khắc im lặng — model sinh video hiếm khi tự "biết" im lặng có ý nghĩa kịch bản.
- Nguồn: Randy Thom — "Designing a Movie for Sound", asoundeffect.com, đọc 2026-09-29, cao (nguyên tắc chung suy ra từ luận điểm "âm thanh
  phải được thiết kế có chủ đích" của Thom — cần ví dụ cụ thể hơn ở S0.12).

### Âm thanh ngoài khung hình (off-screen sound) dẫn dắt sự chú ý
- Cách làm: đưa vào một âm thanh có nguồn không nhìn thấy trong khung hình hiện tại.
- Có thể phục vụ: ý đồ A — báo trước điều sắp xuất hiện trong khung (gây tò mò/hồi hộp) · ý đồ B — mở rộng cảm giác không gian ra ngoài
  khung hình (thế giới vẫn tiếp diễn ngoài những gì camera đang thấy) · ý đồ C — làm cầu nối âm thanh giữa hai cảnh (âm thanh của cảnh sau
  bắt đầu trước khi hình ảnh cảnh sau xuất hiện — J-cut).
- Khi hợp / khi không: hợp khi muốn gợi mở mà chưa muốn xác nhận bằng hình; không hợp nếu gây hiểu lầm không chủ đích (khán giả chờ một thứ
  không bao giờ xuất hiện, trừ khi đó là chủ đích).
- Ví dụ: chưa có mốc giây — cần xem mẫu ở S0.12.
- Với video AI: cần dựng ghép thủ công (âm thanh từ 1 nguồn/clip chèn sớm hơn hình của clip khác) — model sinh video theo từng clip độc lập
  không tự tạo được hiệu ứng J-cut xuyên clip.
- Nguồn: Producing Great Sound for Film and Video (Jay Rose, tổng hợp bách khoa) — en.wikipedia.org/wiki/Producing_Great_Sound_for_Film_and_
  Video, đọc 2026-09-29, vừa (dùng làm định nghĩa thuật ngữ nền, không phải phỏng vấn chuyên gia).

### Cân bằng lời thoại — nhạc — hiệu ứng theo ưu tiên kể chuyện tại từng khoảnh khắc
- Cách làm: mix âm thanh không giữ tỉ lệ cố định giữa thoại/nhạc/hiệu ứng — nâng/hạ từng lớp theo việc lớp nào đang "kể chuyện" nhiều nhất ở
  khoảnh khắc đó.
- Có thể phục vụ: ý đồ A — hạ nhạc khi thoại là trọng tâm (tránh nhạc lấn thoại) · ý đồ B — nâng nhạc/hiệu ứng át thoại khi bản thân sự kiện
  âm thanh đó mới là thứ cần truyền tải (ví dụ một tiếng động lớn ngắt lời nhân vật có chủ đích) · ý đồ C — hạ toàn bộ nhạc nền một khoảng để
  nhường chỗ cho một chi tiết hiệu ứng nhỏ quan trọng.
- Khi hợp / khi không: luôn cần đánh giá lại theo từng cảnh, không có tỉ lệ mix chung cho toàn phim; các chuẩn kỹ thuật (ví dụ mức LUFS phát
  hành) là giới hạn kỹ thuật, không phải hướng dẫn nghệ thuật về việc lớp nào nên nổi lên lúc nào.
- Ví dụ: chưa có mốc giây — cần xem mẫu ở S0.12; đối chiếu quyết định nội bộ đã có "hạ nhạc 8–12 dB" (ghi trong memory dự án) — đó là giải
  pháp kỹ thuật cho 1 tình huống cụ thể, không phải quy tắc chung.
- Với video AI: khi dùng nhạc sinh bằng Eleven Music/Seed Audio cùng thoại lồng tiếng, cần đủ track riêng để mix lại theo từng đoạn, không
  gộp cố định — nếu model chỉ xuất 1 track trộn sẵn thì mất khả năng cân chỉnh theo cảnh.
- Nguồn: Randy Thom — nguyên tắc chung suy ra từ "Designing a Movie for Sound" (âm thanh phải phục vụ kể chuyện, không phải phụ trợ trang
  trí), asoundeffect.com, đọc 2026-09-29, cao — cần đọc thêm phỏng vấn kỹ thuật mix cụ thể (không có trong đợt tìm kiếm này) ở S0.12.
