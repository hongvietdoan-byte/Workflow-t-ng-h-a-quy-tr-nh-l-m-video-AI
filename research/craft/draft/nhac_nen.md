# Nhạc nền (Music) — mục kỹ thuật (S0.14, 2026-09-29)

> Theo `knowledge/craft/PHUONG_PHAP_PHAN_TICH.md` mục 4: mỗi mục là **tư liệu kỹ thuật** (cách làm + nhiều ý đồ có thể phục vụ + điều
> kiện + ví dụ + với video AI + nguồn) — không phải luật cố định. Nguồn ở đây đều bằng tiếng Anh, từ người làm nghề công khai (phỏng vấn,
> tài liệu chính thức công cụ). Ví dụ không có mốc giây cụ thể của một bản phim đã xem → ghi "cần nghe ở S0.12" thay vì bịa mốc giây.

### Buổi spotting (spotting session)
- Cách làm: đạo diễn + dựng phim + (khi có) music editor cùng xem bản dựng đã khoá hình, dừng liên tục ở từng chỗ để quyết: nhạc có ở
  đây không, vào ở giây nào, **ra ở giây nào**, nhạc đang làm việc gì cho cảnh. Ghi lại mốc vào/ra cho mỗi cue.
- Có thể phục vụ: đồng bộ ý đồ giữa đạo diễn và người viết nhạc trước khi tốn công viết · tránh viết nhạc "đoán" theo cảm tính riêng của
  người soạn nhạc.
- Khi hợp / khi không: hợp khi đã có bản dựng gần khoá hình (mốc giây còn đổi thì spotting phải làm lại); với video AI không có buổi
  họp thật, nhưng nguyên tắc "chốt mốc vào/ra trước khi sinh nhạc" vẫn áp dụng được cho brief.
- Ví dụ: cần nghe ở S0.12 (chưa có bản phim mẫu gắn nhãn cho mục này).
- Với video AI: brief nhạc AI nên đọc từ **timeline dựng thật** (không phải kịch bản dự kiến) — giống nguyên tắc "mốc ra quan trọng hơn
  mốc vào vì mốc ra là chỗ hay phải viết lại" (ModWheel).
- Nguồn: [ModWheel — "Spotting Sessions: Where a Film Score Is Decided"](https://modwheel.net/guides/scoring-to-picture-spotting), đọc
  2026-09-29, độ tin vừa (trang giáo dục nhạc phim có biên tập, không phải phát ngôn trực tiếp một nhà soạn nhạc có tên, nhưng mô tả quy
  trình ngành khớp với các nguồn khác).

### Ghi điểm theo cảm xúc, không phải theo hành động trên màn hình
- Cách làm: nhạc theo dõi **cảm xúc bên trong** của cảnh/nhân vật hơn là minh hoạ chuyển động vật lý (đấm, chạy, nổ) từng nhịp một —
  Hans Zimmer: việc của nhạc là "mở ra cánh cửa dẫn tới trải nghiệm cảm xúc", không phải "ra lệnh cho khán giả phải cảm thấy gì".
- Có thể phục vụ: giữ nhạc không bị "sến" khi minh hoạ literal từng hành động (mickey-mousing) · cho phép nhạc mâu thuẫn có chủ ý với
  hình (ví dụ nhạc êm trên cảnh bạo lực) để tạo hiệu ứng khác lạ.
- Khi hợp / khi không: hợp với hầu hết cảnh có nhân vật; khi hợp: hành động (chase, fight) đôi khi vẫn cần nhạc bám sát nhịp vật lý — xem
  mục "Nhịp nhạc và nhịp dựng" bên dưới, hai cách không loại trừ nhau, tuỳ đoạn.
- Ví dụ: Hans Zimmer nói về cách tiếp cận chung của ông với khán giả rạp (phỏng vấn MusicTech) — cần nghe ở S0.12 để gắn vào cảnh cụ thể.
- Với video AI: viết brief theo cảm xúc của đoạn kịch bản (mood/intent) — không mô tả hành động khung hình — khớp với cách
  `core/music_timing.py` đang lấy `mood`/`emotional_intent` của cảnh làm gốc câu prompt, không lấy `action`.
- Nguồn: [MusicTech — "Hans Zimmer Interview: The Art of Film Scoring"](https://musictech.com/features/hans-zimmer-interview/), đọc
  2026-09-29, độ tin vừa (bài phỏng vấn nhưng chỉ đọc được trích dẫn qua tóm tắt tìm kiếm, chưa đọc trọn bài gốc).

### Leitmotif / chủ đề âm nhạc xuyên phim
- Cách làm: một giai điệu ngắn, dễ nhớ gắn với nhân vật/mối quan hệ/ý tưởng, xuất hiện lại dưới nhiều hoà âm khác nhau (mềm khi giới
  thiệu, căng khi xung đột, trần trụi khi hồi tưởng, đầy đủ khi giải quyết).
- Có thể phục vụ: cho khán giả "nhận ra" một cảm xúc đã gặp trước đó mà không cần thoại nhắc lại · nối các đoạn phim rời rạc thành một
  mạch cảm xúc.
- Khi hợp / khi không: hợp với phim có một tuyến cảm xúc trung tâm rõ (tình yêu, mất mát, khát vọng); không cần thiết cho phim ngắn quá
  ít cảnh để chủ đề kịp quay lại (dưới ~3 lần nghe, khán giả chưa kịp "học" giai điệu).
- Ví dụ: Oppenheimer — một thang âm sáu nốt dùng làm leitmotif xuyên phim, bắt đầu ở "Can You Hear the Music"; Harry Potter — "Hedwig's
  Theme" là chủ đề trung tâm nhắc lại suốt series. Cần nghe ở S0.12 để đối chiếu với phim mẫu của dự án.
- Với video AI: đặt tên + mô tả một "motif" cố định trong brief rồi nhắc lại mô tả đó (không phải giai điệu nốt-nốt, model nhạc AI không
  giữ chính xác một giai điệu qua nhiều lượt sinh) ở mỗi đoạn cần chủ đề quay lại; hạn chế: model AI hiện tại không đảm bảo tái tạo đúng
  y một giai điệu giữa các lần gọi — chỉ mô tả được *chất liệu* (nhạc cụ, nhịp, cảm giác) lặp lại, không phải nốt nhạc chính xác.
- Nguồn: [Wikipedia — Oppenheimer (soundtrack)](https://en.wikipedia.org/wiki/Oppenheimer_(soundtrack)); [Wikipedia — Harry Potter and
  the Philosopher's Stone (soundtrack)](https://en.wikipedia.org/wiki/Harry_Potter_and_the_Philosopher%27s_Stone_(soundtrack)), đọc
  2026-09-29, độ tin vừa (bách khoa tổng hợp, không phải phát ngôn trực tiếp nhà soạn nhạc — dùng làm ví dụ hiện tượng, không làm căn cứ
  kỹ thuật sâu).

### Nhịp nhạc và nhịp dựng (tempo & cutting rhythm)
- Cách làm: hai chiều đều tồn tại trong nghề — (a) nhà soạn nhạc viết theo nhịp cắt đã có (đọc "trống" từ cách dựng phim, ví dụ Hans
  Zimmer nhận biết một cảnh Crimson Tide "chính xác về nhịp" dù người dựng nói không cố tình cắt theo nhạc); (b) ngược lại, một số đạo
  diễn/dựng phim **dựng hình theo nhạc có sẵn trước** (Edgar Wright — Baby Driver; Godfrey Reggio dựng Koyaanisqatsi/Powaqqatsi theo nhạc
  Philip Glass).
- Có thể phục vụ: (a) giữ nhạc phục vụ câu chuyện, không ép hình theo nhạc · (b) tạo cảm giác đồng bộ hình-nhạc rất chặt, phù hợp đoạn
  cách điệu/hành động/MV.
- Khi hợp / khi không: (b) đòi hỏi nhạc đã có trước khi dựng (chi phí/kế hoạch khác hẳn pipeline hiện tại vốn dựng trước, nhạc sau) —
  không hợp với quy trình "kịch bản → quay → dựng → nhạc" hiện tại của dự án; (a) hợp với hầu hết trường hợp còn lại.
- Ví dụ: cần nghe ở S0.12 (Baby Driver, Koyaanisqatsi không nằm trong danh sách phim mẫu học theo thứ tự của dự án — ghi lại làm kiến
  thức nền, không phải ví dụ đã xem).
- Với video AI: vì pipeline dựng trước rồi mới sinh nhạc, chỉ dùng được cách (a) — đúng như `music_timing.choose_bpm` đang làm (chọn BPM
  sao cho các mốc chuyển cảnh rơi vào vạch nhịp của nhạc, không bắt hình phải đổi để khớp nhạc).
- Nguồn: [Avid — "Film Editing — The Importance of Rhythm and Pace"](https://www.avid.com/resource-center/film-editing-the-importance-of-rhythm-and-pace)
  (chứa giai thoại Hans Zimmer/Chris Levenson về Crimson Tide); nhắc tới Baby Driver, Koyaanisqatsi/Powaqqatsi qua tổng hợp tìm kiếm — đọc
  2026-09-29, độ tin vừa (trang hãng phần mềm dựng phim, tổng hợp giáo dục, không phải phỏng vấn gốc).

### Stinger / cú đánh nhạc tại bước ngoặt
- Cách làm: một tiếng nhạc ngắn, mạnh (hit) đặt đúng khung hình của cú ngoặt câu chuyện (lộ mặt, hạ gục, phản bội) — trong game, stinger
  còn dùng để báo hiệu chuyển trạng thái (ví dụ: kẻ địch bị hạ → cầu nối nhạc xuống mức thấp hơn để báo "hết nguy hiểm").
- Có thể phục vụ: nhấn mạnh một khoảnh khắc mà không cần đổi cả đoạn nhạc · báo hiệu chuyển trạng thái/chuyển cảnh cho người xem một cách
  vô thức.
- Khi hợp / khi không: hợp ở đúng khung hình của cú ngoặt (lệch vài khung hình thì mất tác dụng, giống nguyên tắc "cú đập rơi đúng khung"
  đã có ở E3); không lạm dụng — quá nhiều stinger liền nhau làm khán giả chai cảm giác.
- Ví dụ: cần nghe ở S0.12; nguồn game ghi nhận stinger dùng để báo "kẻ địch đã hạ, cầu nối nhạc xuống mức an toàn" trong scoring game nói
  chung (không gắn với tựa game cụ thể qua tìm kiếm này).
- Với video AI: khớp với beat "shock: cú đánh thấp mạnh rồi nhịp thưa, sững người" đã có trong `core/music_timing.beats()` (DEATH regex)
  — đúng hướng craft, chỉ cần đảm bảo mốc giây trong brief là mốc **thật** của bản dựng (không phải mốc kịch bản dự kiến).
- Nguồn: tổng hợp qua tìm kiếm về scoring game (stinger báo hạ gục kẻ địch), đọc 2026-09-29, độ tin vừa (không có tên tác giả cụ thể,
  chỉ là mô tả kỹ thuật ngành phổ biến — cần tìm bài gốc có tên tác giả khi có điều kiện).

### Khoảng lặng và nhạc tắt hẳn (silence / drop-outs)
- Cách làm: cắt nhạc hẳn (không chỉ hạ nhỏ) ngay trước hoặc trong một khoảnh khắc căng để sự im lặng tự nó tạo áp lực; đặc biệt phổ biến
  trong kinh dị — Colin Stetson (Hereditary) "khuếch đại sự im lặng cho tới khi bản chất âm thanh của nó lộ ra", làm mờ ranh giới giữa
  thiết kế âm thanh và âm nhạc; đạo diễn Parker Finn (Smile) cùng Cristobal Tapia de Veer chủ ý làm khoảnh khắc lặng "có sức nặng ngang
  khoảnh khắc có nhạc to".
- Có thể phục vụ: tạo cảm giác hồi hộp/đe doạ không cần tăng âm lượng · làm nổi bật một câu thoại hoặc một hành động bằng cách rút hết
  nền âm xung quanh nó · cho khán giả "thở" trước một cú twist (khớp với "khoảng lặng có chủ ý" đã ghi ở E4 pipeline).
- Khi hợp / khi không: hợp nhất ở kinh dị/hồi hộp và ngay trước bước ngoặt kịch tính; không hợp nếu lặng kéo quá dài mà không có lý do
  kịch bản — dễ đọc thành "nhạc bị lỗi" (đã ghi nhận trong `editing.md` E4: "cảnh im lặng hoàn toàn nghe như chưa làm xong" nếu không có
  ambience đi kèm).
- Ví dụ: Hereditary (Colin Stetson) — cần nghe ở S0.12; Smile (Cristobal Tapia de Veer, đạo diễn Parker Finn) — cần nghe ở S0.12.
- Với video AI: khớp trực tiếp với D6 (`core/music_timing` khoảng lặng ~-26 dB trong 0,6 s trước TWIST/CAO TRÀO) và Đ9 sound intent
  (`music == "cut"` tắt hẳn nhạc) đã có trong pipeline — craft chuyên gia xác nhận hướng đi này đúng, không chỉ là suy luận nội bộ.
- Nguồn: [Composer — Spitfire Audio, "Parker Finn on working with his dream composer to score horror debut 'Smile'"](https://composer.spitfireaudio.com/en/articles/parker-finn-on-working-with-his-dream-composer-to-score-horror-debut-smile);
  tóm tắt về Colin Stetson/Hereditary qua tìm kiếm (nguồn gốc 303 Magazine/WFMT tổng hợp) — đọc 2026-09-29, độ tin vừa (đọc qua trích dẫn
  tìm kiếm, chưa fetch trọn bài; câu của Finn/Stetson là diễn giải lại, không phải trích nguyên văn dài).

### Nhạc nguồn (diegetic/source) và nhạc nền (score) cùng tồn tại
- Cách làm: nhạc nguồn (nhân vật trong phim nghe được — radio, nhạc ở quán bar) do music supervisor chọn và xin phép; nhạc nền (score)
  do nhà soạn nhạc viết riêng cho phim, nhân vật không nghe thấy. Hai loại phối hợp: buổi spotting nhiều khi đã có nhạc nguồn đặt sẵn để
  gợi tông màu trước khi bàn nhạc nền.
- Có thể phục vụ: nhạc nguồn tạo "sự tức thì" vì khán giả đã quen bài hát (Karyn Rachtman) · nhạc nền (bản hoà tấu riêng) tạo lớp cảm xúc
  thứ hai mà lời bài hát không có được, đặc biệt khi hoà âm lại một bài hát quen thành bản khí nhạc.
- Khi hợp / khi không: nhạc nguồn hợp khi cảnh có nguồn âm vật lý hợp lý (quán bar, xe hơi có radio, buổi tiệc); nhạc nền hợp cho toàn bộ
  phần còn lại — pipeline hiện tại chỉ tạo nhạc nền (không có khái niệm "nhân vật nghe thấy nhạc"), nên nhóm nhạc nguồn hiện ngoài phạm
  vi trừ khi kịch bản có cảnh kiểu quán bar/sự kiện có nhạc.
- Ví dụ: cần nghe ở S0.12.
- Với video AI: nếu sau này kịch bản có cảnh "nhạc phát trong khung cảnh" (quán bar, đám cưới), cần tách rõ prompt cho đoạn đó khỏi
  nhạc nền chính — gắn cờ để biết đoạn nào là nguồn nhân vật nghe thấy (âm lượng/chất lượng phải khác nhạc nền để nghe "thật" hơn), việc
  này pipeline hiện chưa làm.
- Nguồn: [Composer — Spitfire Audio, "How integral is the role of a music supervisor in film & TV?"](https://composer.spitfireaudio.com/en/articles/how-integral-is-the-role-of-a-music-supervisor-in-film-tv),
  đọc 2026-09-29, độ tin cao (trích lời trực tiếp nhiều music supervisor có tên và phim cụ thể: Brienne Rose, Alexandra Patsavas, Zach
  Cowie).

### Nhạc cùng tồn tại với thoại — chừa chỗ, không chỉ hạ âm lượng
- Cách làm: giọng người (nam ~85–255 Hz, nữ ~165–255 Hz cơ bản, formant cao hơn) cần một "khoảng trống" trong dải tần; thay vì chỉ hạ to
  nhỏ toàn bộ nhạc khi có thoại, sắp xếp nhạc để phần giai điệu/nhạc cụ chính không chiếm đúng dải tần giọng nói, dùng EQ trừ (cắt bớt
  tần giữa của nhạc) + nén động (compression) + xử lý stereo để "khoét chỗ" cho thoại thay vì chỉ kéo fader nhạc xuống.
- Có thể phục vụ: giữ nhạc "nghe được" ngay cả khi đang có thoại (không phải tắt gần hết) · giữ được không khí/cảm xúc nhạc xuyên suốt
  đoạn thoại dài thay vì nhạc biến mất rồi bật lại giật cục.
- Khi hợp / khi không: hợp khi nhạc là hoà tấu không lời và không có nhạc cụ nằm đúng dải giọng nói (piano/dây thường an toàn, kèn đồng
  hoặc giọng hát nền dễ đụng); ít hợp khi đoạn nhạc có nhiều năng lượng ở đúng dải trung (giọng nói) — khi đó vẫn cần hạ âm lượng thật sự
  (duck) chứ EQ không đủ.
- Ví dụ: cần nghe ở S0.12 (đây là nguyên tắc phối/mix chung của ngành, không gắn với một bộ phim cụ thể).
- Với video AI: pipeline hiện tại xử lý bằng **hạ âm lượng động (duck)** khi có giọng (`ffmpeg_studio.DUCK`, 8–12 dB, đã đo thật —
  editing.md E4) — đây là cách đơn giản hơn "chừa chỗ tần số" chuyên nghiệp (không EQ nhạc theo giọng), hợp lý cho pipeline tự động vì
  không phải mọi bản nhạc AI sinh ra đều tách được nhạc cụ để EQ riêng; ghi nhận đây là **khoảng cách** giữa craft chuyên nghiệp và pipeline
  hiện tại, không phải sai — chỉ là mức đơn giản hơn phù hợp với ràng buộc kỹ thuật (xem file bài học).
- Nguồn: tổng hợp từ các bài về mixing dialogue/music (C&I Studios, Mastering.com "Arrangement Is Mixing") qua tìm kiếm, đọc 2026-09-29,
  độ tin vừa (bài kỹ thuật giáo dục có biên tập, không phải phỏng vấn một kỹ sư âm thanh cụ thể theo dự án).

### Chuyển tiếp nhạc giữa các cảnh/phần
- Cách làm: đoạn nhạc mới không bắt đầu đột ngột mà "chảy vào" trong khoảng ~1 ô nhịp, tâm trạng mới đến đúng lúc thay vì dừng-bắt đầu
  giật cục — nguyên tắc chung khi ghép các chunk/section của một bản nhạc dài.
- Có thể phục vụ: giữ mạch cảm xúc liên tục qua nhiều cảnh có tâm trạng khác nhau · tránh cảm giác nhạc bị "cắt dán" giữa hai đoạn.
- Khi hợp / khi không: hợp với hầu hết chuyển cảnh có tâm trạng khác nhau nhưng liền mạch câu chuyện; khi hai cảnh cách nhau về không
  gian/thời gian rất xa (ví dụ chuyển chương), có thể chủ động để nhạc dừng hẳn (xem mục khoảng lặng) thay vì chảy mượt.
- Ví dụ: cần nghe ở S0.12.
- Với video AI: khớp với dòng "Each section flows into the next over about one bar, the new mood arriving exactly at its time" đã có
  sẵn trong `core/music_timing.brief()` (`turn_line`) — người dùng từng góp ý #8 "nhạc vào không hợp lý, không có độ mềm mại" và pipeline
  đã sửa đúng hướng craft này.
- Nguồn: suy luận từ tài liệu Composition Plans của ElevenLabs (từng chunk nối tiếp có `context_adherence`) và nguyên tắc spotting chung
  — đọc 2026-09-29, độ tin vừa (ghép từ tài liệu công cụ + suy luận, không phải một phát biểu craft độc lập).

### Xây cao trào (building to climax)
- Cách làm: nhạc tăng dần theo nhiều trục cùng lúc — nhạc cụ thêm dần, âm lượng/độ dày tăng, tiết tấu dồn — kéo dài sự chờ đợi rồi giải
  toả đúng lúc hình ảnh đạt đỉnh; một cách cụ thể: giữ một nốt cao kéo dài (sustain) tạo chờ đợi, rồi "rơi" xuống đột ngột để tạo kịch
  tính giải toả.
- Có thể phục vụ: cho khán giả cảm nhận "sắp có chuyện" trước khi biết chuyện gì · làm đỉnh cảm xúc của cảnh rõ ràng hơn là chỉ dựa vào
  hình ảnh/diễn xuất.
- Khi hợp / khi không: hợp với cảnh có một đỉnh cảm xúc rõ (đối đầu, đoàn tụ, twist); không hợp nếu lạm dụng ở mọi cảnh — khán giả sẽ hết
  nhạy với "sắp có chuyện" nếu phim nào cũng xây cao trào liên tục.
- Ví dụ: cần nghe ở S0.12 (ví dụ minh hoạ "nốt cao giữ rồi rơi xuống" lấy từ case study quảng cáo Frame.io/Musicbed, không phải phim
  truyện — dùng tham khảo nguyên lý, không phải ví dụ phim).
- Với video AI: đúng hướng với cách `music_timing._style` build câu prompt theo `mood` từng đoạn tăng dần cường độ (ví dụ "hoảng loạn,
  khẩn cấp" → "a fast low ostinato and heartbeat drums, rising dread") — model nhạc AI hiện tại nhận mô tả bằng lời, không có tham số
  "tăng dần" chính xác theo giây như một nhạc sĩ thật viết tay; cần brief rõ câu chữ "rising", "building" ở đúng đoạn.
- Nguồn: [Musicbed Blog — "Case Study: Using Musicbed to Soundtrack a Frame.io Branded Doc"](https://www.musicbed.com/articles/music/using-musicbed-to-soundtrack-frame-io-branded-doc/),
  đọc 2026-09-29, độ tin thấp–vừa (case study quảng cáo/thương mại, không phải phim truyện, chỉ dùng minh hoạ nguyên lý âm nhạc chung).

### Kết / nút thắt cuối (ending / button)
- Cách làm: kết thúc rõ ràng bằng một cú đánh cuối (final hit) thay vì để nhạc tự mờ dần (fade) khi bản thân phim đã kết ở một khung hình
  dứt khoát; ngược lại, đoạn mờ dần hợp khi phim kết mở/lửng.
- Có thể phục vụ: cho khán giả cảm giác "hết" rõ ràng, khớp với một hành động/khung hình cuối dứt khoát · mờ dần phục vụ kết mở, dư âm,
  không muốn chốt cảm xúc quá rõ.
- Khi hợp / khi không: cú đánh cuối hợp với phim/đoạn có nút thắt được giải quyết; mờ dần hợp với kết lửng hoặc chuyển sang credit có
  nhạc riêng.
- Ví dụ: cần nghe ở S0.12.
- Với video AI: khớp trực tiếp với dòng "End cleanly on a final hit... No long tail" đã có trong `brief()` — cũng khớp với phát hiện
  thực tế đã ghi trong E4: "model nhạc luôn mờ 5 s cuối" (ClipAI) buộc pipeline phải xin dư 4 s rồi tự cắt đúng lúc phim kết thúc
  (`TAIL_PAD_MS`) — một giới hạn công cụ AI mà craft "kết dứt khoát" của người thật không gặp phải.
- Nguồn: suy luận nối giữa nguyên tắc chung (ending/button trong âm nhạc thương mại/phim) và quan sát thực tế đã ghi trong
  `knowledge/editor/editing.md` E4 (ví dụ FF #2A) — độ tin vừa (phần "model luôn mờ cuối" là quan sát thực tế của dự án, không phải
  nguồn ngoài).

### Nhạc tạm (temp track) và "temp love"
- Cách làm: đạo diễn dùng nhạc có sẵn (bài hát/nhạc phim khác) để dựng thử trước khi có nhạc thật; rủi ro là đoàn làm phim "yêu" bản tạm
  đến mức nhạc thật khó thay thế được cảm giác quen thuộc đó (temp love — music supervisor Madonna Wade-Reed: gắn với "những bài hát lớn,
  dễ nhận ra" mà khán giả đã nghe ở đâu đó). Cách xử lý: hỏi nhạc tạm đang **làm việc gì** cho cảnh (tiết tấu? một nhạc cụ đặc trưng? một
  câu chữ trong lời? cách người dựng cắt theo nhịp bài đó) — Mike Boris — rồi tìm yếu tố đó trong nhạc mới, thay vì cố chép lại cả bài.
- Có thể phục vụ: giúp đoàn thống nhất tông màu trước khi có nhạc thật · nguy cơ: nhạc thật luôn bị so sánh thiệt thòi với bản tạm đã
  quen tai.
- Khi hợp / khi không: nhạc tạm hợp ở giai đoạn dựng thử; không nên giữ nguyên cảm giác "phải giống hệt bản tạm" khi giao brief cho nhạc
  thật — cần tách ra yếu tố cụ thể (nhịp, nhạc cụ, cảm xúc) thay vì nói "giống bài X".
- Ví dụ: cần nghe ở S0.12 (bài viết không gắn ví dụ phim cụ thể có tên).
- Với video AI: pipeline hiện không dùng nhạc tạm có sẵn (nhạc mượn) làm mốc — sinh thẳng bằng brief mô tả cảm xúc, nên né được rủi ro
  "temp love" nhưng cũng thiếu chỗ dựa nghe thử trước; nếu sau này có bước cho người dùng nghe bản tạm rồi mới chốt, nên hỏi "cái gì
  trong bản tạm này bạn thích" rồi đưa thẳng yếu tố đó (nhạc cụ, tiết tấu) vào prompt, không đưa tên bài hát.
- Nguồn: [Soundstripe — "How to Avoid the Temp Love Trap: Music Supervisors Weigh In"](https://www.soundstripe.com/blogs/how-to-avoid-temp-love),
  đọc 2026-09-29, độ tin vừa (trích lời trực tiếp nhiều music supervisor có tên — Madonna Wade-Reed, Mike Boris, Jen Pyken, Gabe
  McDonough — nhưng bài đăng trên trang bán nhạc thư viện có động cơ thương mại nên xếp vừa, không cao).

### Brief bằng cảm xúc/ý đồ câu chuyện, không bằng nhãn thể loại
- Cách làm: khi nói chuyện với người viết nhạc (hoặc mô tả trong brief), mô tả **cảm giác muốn khán giả có** và **bối cảnh câu chuyện**
  của nhân vật tại đúng khoảnh khắc đó, không nói tên thể loại nhạc ("nhạc buồn", "nhạc rock") hay chỉ số kỹ thuật (tempo/nhạc cụ) ngay
  từ đầu — ví dụ đạo diễn Ari Aster brief cho Colin Stetson (Hereditary) chỉ bằng một câu ẩn dụ: "nó nên nghe như 'A Sunrise in Hell'".
  Một ví dụ khác: "muốn nhạc nghe như bài mẹ tôi từng nghe trong buổi hẹn hò đầu tiên" — truyền tải nhiều hơn bất kỳ chỉ số kỹ thuật nào.
- Có thể phục vụ: cho người viết nhạc (hoặc model AI) không gian diễn giải đúng ý đồ thay vì đoán mò từ nhãn thể loại mơ hồ · tránh việc
  "tempo nhanh hơn" bị hiểu nhầm khi ý thật là "cần có năng lượng hơn" chứ không phải đổi số BPM.
- Khi hợp / khi không: hợp khi mô tả một khoảnh khắc/cảm xúc cụ thể; khi cần độ chính xác kỹ thuật (đúng BPM khớp mốc cắt, đúng nhạc cụ
  để không đụng dải tần giọng nói) vẫn cần bổ sung thông số kỹ thuật cụ thể bên cạnh mô tả cảm xúc — hai lớp không thay thế nhau.
- Ví dụ: Hereditary — đạo diễn Ari Aster brief Colin Stetson bằng ẩn dụ "A Sunrise in Hell" (The Futz Butler, dẫn lại). Cần nghe ở S0.12
  để có ví dụ phim đã xem trong dự án.
- Với video AI: mô tả `mood`/`emotional_intent` bằng tiếng Việt cụ thể theo ngữ cảnh cảnh quay (đã là cách Đạo diễn đang làm, ví dụ "bí
  mật, nghẹt thở") rồi để `MOOD_STYLES` dịch sang câu tiếng Anh kỹ thuật cho model nhạc — đúng nguyên tắc "brief bằng cảm xúc, dịch sang
  kỹ thuật ở lớp sau", không bắt Đạo diễn tự nghĩ ra thuật ngữ nhạc lý.
- Nguồn: [The Futz Butler — "Communicating the Unknowable – How to Nail Your Music Brief"](https://thefutzbutler.com/news/how-to-prepare-music-brief),
  đọc 2026-09-29, độ tin vừa (trang một công ty âm nhạc quảng cáo, có dẫn giai thoại Ari Aster/Colin Stetson nhưng không phải phỏng vấn
  gốc hai người này — giai thoại được lan truyền rộng trong ngành nên xếp vừa thay vì thấp).

### Nhạc hài — "giữ mặt nghiêm" (scoring comedy straight)
- Cách làm: nhiều nhà soạn nhạc hài cố tình viết nhạc **nghiêm túc, không nháy mắt với khán giả** thay vì nhấn nhá hài hước trực tiếp
  (mickey-mousing hài) — Theodore Shapiro (gần 50 phim hài): bản năng của ông là "làm việc nghiêm túc"; nhạc nghiêm túc tạo tương phản
  khiến miếng hài "rơi" mạnh hơn là nhạc đã báo trước "sắp có trò đùa". Cách khác (Mikel Hurwitz, horror-comedy "Too Late"): dùng nhạc cụ
  đặc trưng (accordion, harpsichord) để báo hiệu "đang ở đoạn hài" khi phim trộn hài với thể loại khác, nhưng vẫn tiết chế — chỉ đẩy tới
  "80% adrenaline" thay vì full-blown.
- Có thể phục vụ: tương phản nghiêm túc làm miếng hài bất ngờ hơn · nhạc cụ đặc trưng giúp khán giả phân biệt "đang hài" hay "đang căng"
  khi phim trộn thể loại trong cùng một cảnh.
- Khi hợp / khi không: "giữ mặt nghiêm" hợp với hài tình huống/hài đen muốn miếng hài tự nhiên, không bị nhạc "mớm"; nhạc cụ đặc trưng
  báo hiệu hợp khi phim liên tục đổi tông (hài ↔ căng) và cần tín hiệu rõ cho khán giả biết đang ở "chế độ" nào.
- Ví dụ: cần nghe ở S0.12 (Theodore Shapiro và Mikel Hurwitz không nằm trong danh sách phim mẫu đã xem — ghi làm kiến thức nền).
- Với video AI: khi cảnh kịch bản có `mood` hài/trêu đùa, `MOOD_STYLES` hiện dịch thành "uneasy lightness: soft pizzicato and light
  percussion over an uneasy pad" — đã theo hướng "tiết chế, không mớm hài trực tiếp" chứ không viết nhạc "vui nhộn" lộ liễu; đây là điểm
  khớp giữa craft và pipeline hiện tại, không phải khoảng trống.
- Nguồn: [NPR — "What Makes A Comedy Funnier? Music With A Straight Face"](https://www.npr.org/2016/07/16/486060013/what-makes-a-comedy-funnier-music-with-a-straight-face)
  (Theodore Shapiro); [Berklee College of Music — "So Funny It's Scary: Mikel Hurwitz on Scoring the Horror-Comedy Too Late"](https://college.berklee.edu/film-scoring/news/mikel-hurwitz-on-scoring-the-horror-comedy-too-late),
  đọc 2026-09-29, độ tin cao (NPR phỏng vấn trực tiếp; Berklee là trường nhạc chính thức phỏng vấn cựu sinh viên/nhà soạn nhạc có tên).

### Tiết chế trong nhạc lãng mạn (restraint in romance)
- Cách làm: với nhân vật kín đáo/nhút nhát, chọn nhạc **đơn giản, tiết chế** thay vì giai điệu lãng mạn "trải rộng" (sweeping theme) —
  Volker Bertelmann (Loving): không dùng chủ đề lớn vì nhân vật là người "nhút nhát, kín đáo", kết quả là nhạc đơn giản, tiết chế nhưng
  vẫn đẹp thật sự. Ngược lại, có phê bình cho rằng một số phim lãng mạn khác (The Sessions, Marco Beltrami) lạm dụng "gợi ý cảm xúc" quá
  mức khi tiết chế hơn sẽ tốt hơn.
- Có thể phục vụ: tiết chế giữ nhạc trung thực với tính cách nhân vật, không "nói thay" cảm xúc mà để khán giả tự cảm · chủ đề trải rộng
  phù hợp khi câu chuyện/nhân vật cởi mở, kịch tính rõ ràng hơn.
- Khi hợp / khi không: chọn theo **tính cách nhân vật trong cảnh đó**, không phải mặc định "cảnh yêu = nhạc dây du dương to"; nhân vật
  kín đáo, cảnh ngại ngùng → tiết chế; nhân vật cởi mở, khoảnh khắc đoàn tụ lớn → có thể trải rộng.
- Ví dụ: cần nghe ở S0.12 (Loving, Volker Bertelmann).
- Với video AI: khớp với cách `MOOD_STYLES` đang phân biệt "ấm áp, hạnh phúc, hóa giải" (trải rộng: "the love motif on strings and piano,
  swelling and hopeful") khỏi "đau, kìm nén, buồn" (tiết chế: "sparse solo piano with cold string pads, restrained") — đúng nguyên tắc
  chọn theo tính chất cảm xúc của đoạn, không phải một công thức "nhạc yêu" duy nhất.
- Nguồn: [Composer — Spitfire Audio, "From Casablanca to Moonlight: the evolution of the romantic film score"](https://composer.spitfireaudio.com/en/articles/from-casablanca-to-moonlight-the-evolution-of-the-romantic-film-score),
  đọc 2026-09-29, độ tin vừa (đọc qua trích dẫn tìm kiếm, chưa fetch trọn bài gốc để xác nhận ngữ cảnh đầy đủ của câu nói Bertelmann).
