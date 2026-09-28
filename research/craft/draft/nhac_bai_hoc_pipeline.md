# Bài học cho pipeline — Nhạc nền (S0.14, 2026-09-29)

> Tối đa 10 bài học cụ thể, mỗi bài ghi **độ tin** (cao/vừa/thấp theo nguồn ở `nhac_nen.md`/`nhac_theo_the_loai.md`) + **đã làm / còn
> thiếu** trong code hiện tại (`core/music_timing.py`, `core/sound_intent.py`, `knowledge/editor/editing.md` E4). Không lặp lại nội dung
> đã có ở E4 — chỉ nêu cái mới hoặc cái cần sửa.

## 1. Brief nhạc phải đọc từ timeline dựng thật, không phải kịch bản dự kiến
- Độ tin: cao (ModWheel — mốc ra của cue là chỗ hay phải viết lại nhất; kinh nghiệm thực tế #8 của dự án khớp thẳng: "score composed on
  planned 64 s while cut was 84,5 s").
- Đã làm: `render_timeline()` + tham số `seconds` trong `brief()`/`sections()` đã ưu tiên đọc từ bản render thật khi có, đúng hướng craft.
- Còn thiếu: không có — ghi nhận đây là điểm pipeline đã đúng craft từ trước khi có đợt nghiên cứu này (S0.14 chỉ xác nhận lại bằng nguồn
  ngoài).

## 2. Brief theo cảm xúc/ý đồ câu chuyện của Đạo diễn, dịch sang câu tiếng Anh kỹ thuật ở lớp riêng
- Độ tin: vừa (The Futz Butler — Ari Aster/Colin Stetson; nguyên tắc "brief bằng cảm xúc, không bằng nhãn thể loại").
- Đã làm: Đạo diễn viết `mood`/`emotional_intent` tiếng Việt tự do theo ngữ cảnh; `MOOD_STYLES` (regex trên tiếng Việt) dịch sang mô tả
  nhạc tiếng Anh cho model — đã tách đúng hai lớp "người nói cảm xúc" / "câu lệnh kỹ thuật cho máy".
- Còn thiếu: `MOOD_STYLES` là danh sách quy tắc cứng (regex → 1 câu style cố định) — không phải "diễn giải" thật sự như một biên tập âm
  nhạc con người sẽ làm với một mood mới lạ chưa có trong danh sách (rơi vào nhánh mặc định "understated cinematic underscore"). Không
  cần sửa ngay (đủ dùng), nhưng là giới hạn nên biết khi mood tiếng Việt ngày càng đa dạng.

## 3. Chuyển tiếp nhạc giữa các đoạn nên "chảy" trong khoảng một ô nhịp, không dừng-bắt-đầu giật cục
- Độ tin: vừa (suy luận từ tài liệu Composition Plans của ElevenLabs + nguyên tắc spotting chung, không có một câu trích nguyên văn về
  "1 ô nhịp" từ một nhà soạn nhạc cụ thể).
- Đã làm: `brief()` đã có `turn_line` ("Each section flows into the next over about one bar...") — đúng bài học người dùng góp ý ở #8
  ("nhạc vào không hợp lý, không có độ mềm mại").
- Còn thiếu: không có việc mới — xác nhận lại hướng đã sửa là đúng.

## 4. Nhạc cùng tồn tại với thoại: pipeline dùng duck (hạ âm lượng động), không EQ "chừa chỗ tần số" như mix chuyên nghiệp
- Độ tin: vừa (tổng hợp giáo dục về mix dialogue/music, không phải phỏng vấn kỹ sư âm thanh cụ thể).
- Đã làm: `ffmpeg_studio.DUCK` hạ 8–12 dB khi có giọng, đã đo thật, có test giữ mức (`tests/test_crew_skills_0926.py`) — đủ dùng cho
  pipeline tự động vì nhạc AI sinh ra không tách được nhạc cụ riêng để EQ chọn lọc.
- Còn thiếu: đây là **khoảng cách có chủ đích, không phải lỗi** — ghi rõ trong `editing.md` E4 (nếu chưa) một câu giải thích "duck thay
  EQ vì nhạc AI không tách track nhạc cụ" để người đọc sau không tưởng nhầm là thiếu sót cần sửa.

## 5. Kết thúc dứt khoát bằng cú đánh cuối — model nhạc AI có xu hướng mờ dần, phải xin dư giây rồi tự cắt
- Độ tin: cao cho phần "kết dứt khoát nên có cú đánh cuối, không nên mờ dần khi phim kết ở khung hình dứt khoát" (nguyên tắc craft
  chung); quan sát "ClipAI luôn mờ 5 s cuối" là dữ liệu nội bộ dự án (không phải nguồn ngoài, nhưng đã xác nhận thực tế ở #2A).
- Đã làm: `TAIL_PAD_MS` (xin dư 4 s, cắt đúng lúc phim kết) + câu "End cleanly on a final hit... No long tail" trong prompt — đúng
  hướng.
- Còn thiếu: không có việc mới.

## 6. Nhạc hài/tông nhẹ nên tiết chế, không viết nhạc "vui nhộn" lộ liễu mớm trước miếng hài
- Độ tin: cao (NPR — Theodore Shapiro; Berklee — Mikel Hurwitz).
- Đã làm: `MOOD_STYLES` cho "đùa, trêu, playful, banter" → "uneasy lightness: soft pizzicato and light percussion over an uneasy pad" —
  đã tiết chế đúng hướng (không phải "vui nhộn" trực tiếp).
- Còn thiếu: không có việc mới — xác nhận hướng đã chọn đúng craft.

## 7. Nhạc lãng mạn nên chọn tiết chế hay trải rộng theo **tính cách nhân vật trong cảnh**, không mặc định "cảnh yêu = nhạc to"
- Độ tin: vừa (Spitfire Audio — Volker Bertelmann/Loving, đọc qua trích dẫn tìm kiếm).
- Đã làm: `MOOD_STYLES` đã phân hai nhánh — "ấm áp, hạnh phúc, hóa giải" (trải rộng) khác "đau, kìm nén, buồn" (tiết chế) — đúng nguyên
  tắc chọn theo cảm xúc chứ không theo thể loại.
- Còn thiếu: hai nhánh này hiện phân theo *loại cảm xúc* (vui/buồn), chưa phân theo *tính cách nhân vật* (nhân vật kín đáo vs cởi mở) khi
  cùng một loại cảm xúc — ví dụ hai cảnh cùng "ấm áp, hạnh phúc" nhưng một nhân vật rụt rè, một nhân vật bộc trực vẫn ra cùng một style.
  Chưa cần sửa ngay (Đạo diễn có thể viết mood cụ thể hơn để lách qua, ví dụ "ấm áp, rụt rè" nếu regex bắt được), nhưng là khoảng trống
  đáng ghi lại cho lần rà `MOOD_STYLES` sau.

## 8. Stinger đúng khung hình cho các bước ngoặt — cần mốc giây thật, không phải mốc kịch bản
- Độ tin: vừa (tổng hợp về stinger trong game scoring, không có tên tác giả cụ thể — cần nguồn tốt hơn).
- Đã làm: `beats()` đã phát hiện các mốc DEATH/FLASHBACK/emotional peak từ dữ liệu shot thật (không phải kịch bản dự kiến) và gắn câu
  "shock: a sharp low hit, then a stunned, sparse pulse" — đúng hướng.
- Còn thiếu: nguồn cho kỹ thuật stinger còn yếu (không có tên tác giả) — nên tìm thêm phỏng vấn composer game có tên cụ thể (Riot/
  Blizzard) ở đợt sau để nâng độ tin trước khi coi đây là căn cứ vững.

## 9. Vertical short drama (ReelShort-style): chưa có nguồn craft trực tiếp bằng tiếng Anh — khoảng trống thật sự
- Độ tin: thấp (chỉ có tài liệu hướng dẫn sản xuất định dạng, không phải phỏng vấn composer/music editor đã làm thể loại này).
- Đã làm: pipeline hiện đang phục vụ đúng định dạng này (FF vertical short drama) nhưng cách viết `MOOD_STYLES`/`beats()` dựa trên
  nguyên tắc phim nói chung (Murch, spotting…), chưa có xác nhận riêng cho đặc thù "cue dày, đổi liên tục" của vertical drama.
- Còn thiếu: cần một đợt tìm nguồn khác (có thể nguồn tiếng Trung do agent song song phụ trách, vì gốc định dạng duanju là Trung Quốc)
  hoặc tìm phỏng vấn composer ReelShort cụ thể bằng tiếng Anh — hiện tại **không nên** dùng mục "short drama dọc" trong
  `nhac_theo_the_loai.md` làm căn cứ mạnh, chỉ dùng tham khảo vì đã ghi rõ độ tin thấp–vừa.

## 10. Nhạc nguồn (diegetic) tách biệt khỏi nhạc nền — pipeline hiện chưa có khái niệm này
- Độ tin: cao (Spitfire Audio — Brienne Rose, Alexandra Patsavas, Zach Cowie, phát biểu trực tiếp có tên).
- Đã làm: không có — pipeline hiện chỉ sinh một loại nhạc nền (score), không phân biệt "nhân vật nghe thấy nhạc trong cảnh" (quán bar,
  đám cưới, radio trong xe).
- Còn thiếu: nếu kịch bản tương lai có cảnh kiểu này, cần đánh dấu riêng (ví dụ trường `sound.source_music` ở shot) để tách khỏi nhạc nền
  chính — hiện tại kịch bản FF/tháp chưa gặp trường hợp này nên **không cần làm ngay**, chỉ ghi nhận làm gợi ý khi có kịch bản cần.
