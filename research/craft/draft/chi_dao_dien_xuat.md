# Kho kỹ thuật — Chỉ đạo diễn xuất (draft S0.11, 2026-09-29)

> **Kiểm duyệt của phiên chính (2026-09-29) — BẢN NHÁP, CHƯA vào `knowledge/`:**
> - Nhiều mục ghi nguồn là **trang chủ** (theasc.com, rogerdeakins.com) hoặc "tóm tắt qua tìm kiếm", không phải bài cụ thể đã đọc trọn →
>   theo phương pháp mục 3, độ tin của các mục đó tạm hạ xuống **vừa** cho tới khi đọc bài gốc (có tên bài, người nói, đoạn liên quan).
> - Nguồn đọc được trọn / xác minh link: DGA — Dan Attias; ProVideo Coalition — Murch; Designing Sound — Randy Thom; VFX Voice; Team Deakins
>   (trang podcast). Một số trang chặn tải tự động (Frame.io, A Sound Effect, LBBOnline, No Film School, British Cinematographer) — cần mở
>   bằng trình duyệt ở lượt đọc kỹ.
> - Đã sửa: chuyển cảnh che máy có thể sinh trong 1 lần (clip mẫu 2:20,6) — không khẳng định "model không tự làm"; số 2,4 lần là mức chuyển
>   động so với #8; ví dụ *Locked* chưa xác minh.
> - Việc kế: lượt đọc kỹ nguồn gốc (thay trích dẫn chung bằng bài cụ thể) + ví dụ có mốc giây từ S0.12, mới đưa vào `knowledge/craft/`.


> Draft chờ duyệt. Nguyên tắc gốc (đã chốt trong `PHUONG_PHAP_PHAN_TICH.md` mục 2): diễn xuất/hành động khó đến từ **chỉ đạo** — đạo diễn
> truyền đạt tình huống, động cơ, chuỗi hành động, chi tiết cơ thể (và tập luyện/quay thử) cho diễn viên — không mặc định "có video mẫu".
> Với pipeline video AI, mục này dịch quy trình chỉ đạo đó thành cách viết prompt diễn xuất/chuyển động cho model.

### Cho tình huống, không diễn cảm xúc hộ diễn viên (situation over emotion label)
- Cách làm: đạo diễn mô tả HOÀN CẢNH cụ thể (chuyện gì vừa xảy ra, nhân vật đang phải làm gì tiếp theo) thay vì ra lệnh trực tiếp một nhãn
  cảm xúc ("hãy buồn", "hãy tức giận").
- Có thể phục vụ: ý đồ A — diễn viên tự tìm ra biểu cảm/nhịp điệu thật từ hoàn cảnh, kết quả tự nhiên hơn là "diễn" một nhãn cảm xúc theo
  lệnh · ý đồ B — cho phép mỗi lần quay (take) có sắc thái hơi khác nhau trong khi vẫn đúng tình huống, tạo dư địa chọn lựa ở dựng phim ·
  điều kiện: cần cho đủ chi tiết cụ thể (ai, chuyện gì, ngay trước/sau khoảnh khắc này) để diễn viên có "chất liệu" thật để phản ứng.
- Khi hợp / khi không: hợp với hầu hết cảnh có kịch tính tâm lý; ít cần thiết ở các động tác kỹ thuật thuần túy (một pha nhào lộn không cần
  "động cơ tâm lý" mà cần chỉ dẫn vật lý — xem mục "Chi tiết cơ thể" bên dưới).
- Ví dụ: đạo diễn TV kỳ cựu Dan Attias — nhấn mạnh việc nhắc diễn viên "động cơ ở đây là gì" vì diễn viên quay không theo thứ tự thời gian
  dễ quên mạch tâm lý nhân vật (DGA Quarterly, Summer 2018) — chưa có mốc thời lượng cụ thể của buổi phỏng vấn, cần xem toàn văn ở S0.12.
- Với video AI: khi viết prompt diễn xuất, mô tả TÌNH HUỐNG + hành động quan sát được ("vừa nhận tin nhắn xấu, tay dừng lại giữa chừng,
  quay đầu nhìn ra cửa") thay vì chỉ ghi nhãn cảm xúc ("sad, angry") — model có xu hướng diễn cảm xúc nhãn một cách khuôn mẫu/quá đà nếu chỉ
  cho nhãn, trong khi mô tả hành động cụ thể ra kết quả tự nhiên hơn.
- Nguồn: Dan Attias — đạo diễn, phỏng vấn DGA Quarterly, dga.org/craft/dgaq/issues/1803-summer-2018/dga-interview-dan-attias, đọc
  2026-09-29, cao; No Film School (tổng hợp thực hành tương tự, "cho tình huống thay vì cảm xúc"), nofilmschool.com/2012/01/director-
  learning-talk-actors, đọc 2026-09-29, vừa.

### Xây động cơ nhân vật xuyên suốt mạch quay không theo thứ tự
- Cách làm: đạo diễn (không phải diễn viên) là người giữ toàn bộ mạch tâm lý nhân vật qua thứ tự quay thực tế (thường không theo thứ tự
  kịch bản) — trước mỗi cảnh, nhắc lại nhân vật đang ở đâu trong hành trình cảm xúc của họ tại điểm này.
- Có thể phục vụ: ý đồ A — đảm bảo tính nhất quán tâm lý nhân vật dù quay rời rạc theo lịch trường quay · ý đồ B — cho diễn viên "mỏ neo"
  để không bị lẫn giữa các cảnh có sắc thái gần giống nhau.
- Khi hợp / khi không: đặc biệt quan trọng với phim/series quay dài ngày, nhiều bối cảnh xen kẽ; với video AI ít liên quan trực tiếp vì mỗi
  clip thường sinh độc lập — nhưng NGUYÊN TẮC vẫn áp dụng: người viết prompt (đóng vai đạo diễn) phải tự giữ "sổ tay động cơ nhân vật" xuyên
  các lần gọi model để mọi clip của cùng nhân vật nhất quán tâm lý.
- Ví dụ: Dan Attias, DGA Quarterly — như trên.
- Với video AI: gợi ý pipeline — lưu một bản tóm tắt trạng thái tâm lý/mục tiêu của nhân vật tại mỗi cảnh (trong tài liệu kịch bản/Director
  Workspace) để mỗi lần viết prompt cho clip mới đều tham chiếu lại, tránh mỗi clip "diễn" một sắc thái rời rạc không ăn khớp mạch phim.
- Nguồn: Dan Attias — DGA Quarterly, đọc 2026-09-29, cao.

### Chi tiết cơ thể cụ thể thay vì chỉ đạo trừu tượng (physical action beats)
- Cách làm: đạo diễn chia hành động thành các "beat" vật lý cụ thể, quan sát được (tay làm gì, mắt nhìn đâu, trọng tâm cơ thể dồn về đâu,
  nhịp thở) thay vì chỉ đạo trừu tượng.
- Có thể phục vụ: ý đồ A — với hành động/động tác kỹ thuật (một pha vật lý, một cử chỉ đặc trưng), mô tả beat vật lý chính xác quan trọng
  hơn mô tả tâm lý · ý đồ B — với diễn xuất tâm lý tinh tế, các chi tiết cơ thể nhỏ (một cái chớp mắt trễ, một hơi thở hụt) là nơi truyền tải
  cảm xúc thật, không phải nét mặt cường điệu.
- Khi hợp / khi không: luôn hữu ích để làm rõ ràng chỉ đạo (giảm mơ hồ giữa đạo diễn và diễn viên/model); rủi ro nếu liệt kê quá nhiều chi
  tiết rời rạc mà thiếu mạch tình huống tổng thể đi kèm — chi tiết cơ thể nên phục vụ cho tình huống, không thay thế nó.
- Ví dụ: chưa có mốc giây cụ thể trong nguồn đã đọc — nguyên tắc rút ra từ phương pháp phân tích nội bộ (`PHUONG_PHAP_PHAN_TICH.md` mục 2)
  kết hợp thực hành chỉ đạo diễn xuất phổ biến; cần đối chiếu thêm phỏng vấn đạo diễn cụ thể ở S0.12.
- Với video AI: đây là phần quan trọng nhất khi viết prompt diễn xuất — kết hợp: (1) tình huống ngắn gọn, (2) 2–3 beat vật lý cụ thể theo
  trình tự thời gian trong clip, (3) nếu có động tác kỹ thuật khó, có thể bổ sung ảnh/video tham chiếu (xem `chuyen_canh.md` mục "video tham
  chiếu động tác khó") — reference chỉ bổ sung cho phần (2), không thay thế phần (1) và (3) chi tiết cơ thể bằng lời.
- Nguồn: suy luận nội bộ dựa trên `PHUONG_PHAP_PHAN_TICH.md` (người dùng chốt 2026-09-29) + đối chiếu No Film School, đọc 2026-09-29, vừa.

### Tập luyện / quay thử (rehearsal, test takes) để hiệu chỉnh trước khi quay chính
- Cách làm: chạy thử cảnh (không quay hoặc quay nháp) trước khi quay chính thức, đạo diễn quan sát và điều chỉnh lại chỉ đạo dựa trên những
  gì diễn viên thể hiện — đây là một vòng lặp hai chiều, không phải đạo diễn ra lệnh một lần rồi quay.
- Có thể phục vụ: ý đồ A — phát hiện chỉ đạo bằng lời chưa đủ rõ trước khi tốn thời gian/chi phí quay chính · ý đồ B — cho diễn viên không
  gian thử nghiệm, đạo diễn chọn lọc từ nhiều phương án diễn thay vì áp đặt một cách duy nhất.
- Khi hợp / khi không: gần như luôn có giá trị nhưng bị giới hạn bởi thời gian/ngân sách trường quay thật; trong pipeline AI, "quay thử" có
  thể ánh xạ thành sinh thử độ phân giải/chất lượng thấp trước khi sinh bản chính thức.
- Ví dụ: chưa có mốc giây — nguyên tắc chung của nghề đạo diễn, cần ví dụ phỏng vấn cụ thể ở S0.12.
- Với video AI: tương đương "gen thử ở chất lượng thấp trước, đúng ý mới gen chất lượng cao" — nguyên tắc này đã có trong quy ước dự án
  (`docs/CHUAN_XAY_DUNG.md`: gen lại phải đổi đầu vào, không lặp y hệt) — mỗi lần gen thử nên đổi ít nhất một chi tiết trong prompt (thêm
  beat vật lý, đổi mô tả tình huống) giống như đạo diễn điều chỉnh chỉ đạo sau khi xem quay thử, không gen lặp lại y hệt chờ may rủi.
- Nguồn: nguyên tắc nghề chung (không có 1 nguồn phỏng vấn cụ thể được đọc trong đợt này về rehearsal — cần bổ sung ở S0.12, ví dụ tìm phỏng
  vấn đạo diễn cụ thể nói về rehearsal trên DGA Quarterly); đối chiếu quy ước nội bộ dự án `docs/CHUAN_XAY_DUNG.md`.

### Từ chỉ đạo diễn xuất sang prompt chuyển động cho video model — công thức gợi ý
- Cách làm (gợi ý pipeline, tổng hợp từ 4 mục trên — CHƯA phải chuẩn đã duyệt, cần đối chiếu thêm mẫu thật ở S0.12): một prompt diễn xuất
  tốt nên có đủ 3 lớp, theo đúng thứ tự chỉ đạo diễn xuất thật: (1) **Tình huống + mục tiêu** của nhân vật ngay tại khoảnh khắc đó (1 câu) —
  không phải nhãn cảm xúc; (2) **Chuỗi beat vật lý** theo trình tự thời gian trong clip (tay/mắt/tư thế/nhịp thở, tối đa 2–3 beat để model
  không bị rối); (3) **Điều chỉnh/giới hạn kỹ thuật** — model làm được gì, cần tham chiếu ảnh/video hay không (chỉ khi động tác khó về mặt
  cơ thể, xem `chuyen_canh.md`).
- Có thể phục vụ: ý đồ A — prompt có tình huống rõ giúp model chọn biểu cảm hợp lý hơn là ép nhãn cảm xúc cứng · ý đồ B — beat vật lý cụ thể
  giúp model tạo chuyển động đúng trình tự thay vì một biểu cảm tĩnh lặp lại suốt clip.
- Khi hợp / khi không: hợp cho diễn xuất tâm lý (short film, short drama, cảnh thoại trong MV_NARRATIVE); với động tác kỹ thuật thuần túy
  (võ thuật, vũ đạo phức tạp) lớp (3) trở thành bắt buộc chứ không phải tùy chọn.
- Ví dụ: chưa có mẫu prompt thật nào được test và ghi lại kết quả trong đợt này — đây là **gợi ý cho pipeline theo mục 1 tầng 4 của phương
  pháp phân tích**, cần ít nhất 2 mẫu thử nghiệm thật (ghi bằng chứng chạy) trước khi đưa vào `knowledge/roles/director.md` chính thức.
- Với video AI: đây chính là mục đích của mục này — áp dụng trực tiếp khi Director/Đạo diễn (vai trò trong pipeline) soạn prompt.
- Nguồn: tổng hợp suy luận của dự án từ 4 mục nguồn trên (Dan Attias/DGA, No Film School) + `PHUONG_PHAP_PHAN_TICH.md` — ghi rõ đây là
  **[suy luận nội bộ]**, chưa có nguồn chuyên gia nói trực tiếp về việc viết prompt diễn xuất cho video AI.
