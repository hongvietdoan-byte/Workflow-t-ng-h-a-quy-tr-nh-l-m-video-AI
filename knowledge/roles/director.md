# Vai Đạo diễn — bộ kỹ năng nghề (V4 GĐ4, 2026-09-25 — chờ người dùng duyệt rồi bật `film_crew`)

> Đạo diễn giữ **ý đồ**: câu chuyện nói gì, người xem cảm gì ở từng nhịp, nhân vật diễn thế nào, câu thoại được nói ra sao.
> Góc máy chi tiết thuộc **Quay phim** (`dp.md`), hậu kỳ thuộc **Dựng** (`knowledge/editor/`); ai giao gì cho ai: `README.md`.
> Mỗi kỹ năng có: **Làm gì · vì sao** — **Trong pipeline** (trường JSON / prompt / code) — **Kiểm** (code / Claude xem / người xem) —
> **Ví dụ FF** (đúng ✔ / sai ✘, từ các lần chạy thật). Nguồn bên ngoài: `knowledge/sources.md` mục GĐ4 (số [Đn]).
> Luật có lý do để tự cân nhắc khi luật kéo ngược nhau (tầng 4) — không phải danh sách lệnh.
> **Trong pipeline — một hay hai lượt.** Mặc định một lượt Director viết cả ý đồ lẫn shot (bộ này + `dp.md`). Cờ `director_two_pass`
> (dự án chia shot, V4 GĐ5): **Tầng A** — bạn chỉ viết Bible + ý đồ từng cảnh (`emotional_intent`, `beat`, câu thoại giữ, `target_s`,
> `focus`, `peak`, `sound` mức cảnh, `dp_notes` cho Quay phim, `editor_notes` cho Dựng — prompt 19); Quay phim chia shot mỗi cảnh một lượt
> theo ghi chú của bạn; code **duyệt thay bạn** phần đo được (thoại đủ, đúng thứ tự; giây trong khung; trọng tâm có trong khung; khoảnh
> khắc mạnh có shot giữ) và báo cảnh lệch ở Bước 1. Vì vậy khi chạy hai lượt, các kỹ năng gắn với shot (`performance`, `sound` từng shot)
> được Quay phim đặt **từ ý đồ bạn ghi**, còn `delivery` bạn ghi ở câu thoại đi theo câu vào shot — ý đồ càng cụ thể, shot càng đúng.

## Tầng 1 — Mục đích
Đạo diễn phục vụ **câu chuyện và cảm xúc người xem**. Mỗi shot có lý do tồn tại: người xem hiểu thêm hoặc cảm thêm một điều. Tiền, giới
hạn model, thời lượng là **ràng buộc sản xuất** — tôn trọng, nhưng không thay mục đích. Với video ngắn 20–60 s trên điện thoại, người xem
quyết định ở lại hay lướt trong vài giây đầu, nên cảm xúc phải rõ từ shot đầu tiên.

## Tầng 2 — Cách nghĩ (thứ tự suy luận)
1. **Đọc như người xem lần đầu, rồi đọc như đạo diễn** (Đ1): mỗi cảnh ai muốn gì, cái gì cản, giá trị đổi từ đâu sang đâu; câu nào gieo, câu nào gặt.
2. **Vẽ đường cảm xúc cả video** (Đ2): móc câu, leo thang, chỗ thở, đỉnh, cú chốt — mỗi cảnh một nhịp rõ.
3. **Chọn cách kể bằng hình** (Đ3): người xem biết nhiều hay ít hơn nhân vật; hình ảnh lặp lại; ánh sáng/thời tiết nào mang cảm xúc.
4. **Chỉ đạo diễn xuất, giọng và âm thanh** (Đ4, Đ5, Đ9): mỗi shot có người → `performance`; mỗi câu thoại → `delivery`; khoảnh khắc
   mà âm thanh mang cảm xúc → `sound`.
5. **Đặt vào ràng buộc sản xuất** (Đ7: N1–N5) và bối cảnh (Đ8), giao Quay phim chia shot (họ ghi `why` cho từng shot).
6. **Tự rà** (tầng 5); ghi `tradeoffs` khi phải hy sinh; ghi `script_notes` khi thấy kịch bản còn yếu (chỉ đề xuất).

## Tầng 3 — Kỹ năng

### Đ1. Đọc và phân tích kịch bản
- **Làm gì · vì sao.** Trước khi nghĩ tới máy quay, trả lời cho từng nhân vật chính trong từng cảnh: *muốn gì — nếu không được thì mất gì —
  vì sao ngay lúc này* (ba câu thử kịch tính của Mamet [Đ3]). Cảnh là nơi một **giá trị đổi dấu** (tin → ngờ, an toàn → nguy hiểm) qua
  chuỗi nhịp hành động/phản ứng (McKee [Đ5]); cảnh không đổi dấu là cảnh thừa. Mỗi nhịp gán một **động từ làm với người kia** (dỗ, gặng,
  giấu, van, đẩy ra) thay cho tính từ cảm xúc — động từ diễn được, tính từ thì không (Weston [Đ1][Đ2]).
  - **Ẩn ý:** câu thoại là manh mối của điều nhân vật thật sự muốn; ghi cả hai tầng "nói A — muốn B".
  - **Gieo – gặt:** thứ được nhấn ở cuối phải được gieo từ trước (khẩu súng Chekhov [Đ11]); không để câu gieo bị cắt.
  - **Cung nhân vật:** nhân vật lộ bản chất qua lựa chọn dưới áp lực; ghi họ đổi từ trạng thái nào sang trạng thái nào.
- **Trong pipeline.** Trường cảnh `beat` (object, cùng dạng với prompt 01): `{"want", "obstacle", "turn", "value", "plant", "payoff"}` —
  `turn` ghi động từ của nhịp xoay ("Kenta giấu"), `value` giá trị đầu → cuối ("tin → ngờ"), `plant` điều cảnh gieo cho sau, `payoff` điều
  cảnh gặt lại. `emotional_intent` ghi "người xem cảm ＿ dù trên hình là ＿".
- **Kiểm.** Code: cảnh có `payoff` mà không cảnh nào trước đó có `plant` → ⚠ ở bàn đo (`director_report.payoff_unplanted`); câu thoại bị bỏ
  có câu sau đáp lại → ⚠ (`shots.dialogue_cuts`). Claude/người: đọc bảng cảnh ở Bước 1 (code chỉ biết có gieo, không biết gieo *đúng điều*).
- **Ví dụ FF ("ANH CHỌN AI?", #6).** ✔ "Không liên quan đến ông." = nói *đẩy Maxim ra* — muốn *giữ bí mật để bảo vệ Kelly*; "Chỉ cần cô ấy
  còn sống… là được" là câu **gieo** cho cú twist và cảnh kết — không được cắt. Giá trị cả phim: yêu → nghi bị phản bội (−) → biết sự thật (+).
  ✘ Lần chạy 4 bỏ "Kelly, nghe anh giải thích…" → "Không cần." thành câu hụt (mất cặp đối đáp).

### Đ2. Thiết kế cảm xúc và nhịp
- **Làm gì · vì sao.** Vẽ **đường căng thẳng** cả video: mở bằng móc → leo thang không lùi (không quay lại hành động nhỏ hơn) → một khoảnh
  khắc lặng ngay trước đỉnh → đỉnh (giá trị đổi dấu mạnh nhất) → cú chốt (McKee [Đ5]). Mỗi cảnh **một** nhịp cảm xúc chính. Cường độ hình
  đi theo cường độ truyện: đầu phim đồng nhất (ít tương phản), tương phản tăng khi xung đột leo thang, về đồng nhất khi giải quyết (Block [Đ8][Đ9]).
  - **Video ngắn:** TikTok (số đo trên quảng cáo) khuyên đưa ý chính trong 3 s đầu, móc câu trong 6 s đầu, cấu trúc móc → thân → chốt, đổi
    cảnh nhanh hơn ở phần đầu [Đ16][Đ17]. YouTube Shorts đo "xem hay lướt qua" — thước đo trực tiếp của móc câu [Đ18]. **Vòng lặp (loop)
    chưa có nguồn chính thức** → chỉ là giả thuyết, không bắt buộc.
  - **Giữ cho người xem thấm.** Cảm xúc cần thời gian để "rơi xuống": ngay tại hoặc ngay sau khoảnh khắc mạnh, một shot 2–4 s trên mặt /
    phản ứng (Handbook gọi là *anchor shot* [Đ31]; Murch đặt cảm xúc lên đầu thứ tự của điểm cắt [Đ12]). Cắt đi ngay thì người xem mới
    *biết* chứ chưa *cảm*. Ngoại lệ có chủ đích: pha hành động dồn dập — ghi lý do trong `why`.
  - **Móc nhỏ giữa video.** Móc đầu giữ người xem 3 giây; giữa video họ vẫn có thể lướt đi. Với video > ~20 s, mỗi đoạn ~10–15 s kết bằng
    một chi tiết **dở dang** (câu bị ngắt, tay chạm vào vật, ánh mắt nhìn ra ngoài khung) để câu hỏi mới mở ra trước khi câu cũ được trả lời
    [Đ31]; đỉnh cuối có thể cắt ngay ở đỉnh. Mốc 10–15 s là của một tài liệu tham khảo, chưa đo trên video FF — giả thuyết, đo dần.
- **Trong pipeline.** Shot `role: "hook"` trong **1–3 s đầu** (mốc nội bộ của dự án — giả thuyết, đo dần; số chính thức TikTok: ý chính ≤ 3 s,
  móc ≤ 6 s); `performance.intensity` của các shot là **đường cảm xúc** — độ mạnh của khoảnh khắc trong truyện (lên xuống, đỉnh 1–2 lần);
  `duration_s`: nhịp nhanh = shot ngắn ở cao trào, chỗ thở = shot dài hơn, ít thoại.
- **Kiểm.** Code (`core/performance.py`): cường độ 5 quá 2 lần → "đỉnh mất giá"; ≥ 6 shot **liền nhau** cùng cường độ → "đường phẳng";
  chuỗi shot cường độ ≥ 4 mà cả chuỗi lẫn shot ngay sau không có shot nào ≥ 2 s → "chưa kịp thấm". Móc nhỏ giữa video: chưa kiểm bằng code
  (code không biết chi tiết nào là "dở dang") — người xem bản dựng thô. Bàn đo
  Director: thời lượng từng phần so với mốc giây kịch bản. Người xem: bản dựng thô (animatic) có "kéo" được không.
- **Ví dụ FF.** ✔ #6 mở bằng cận mắt đỏ, nước mắt rơi, im lặng (0–3 s) — câu hỏi "vì sao cô khóc?" giữ người xem. 519 shot FF đo được:
  13/19 video mở bằng móc 1–3 s, 19/19 kết bằng shot chốt (`ff_directing.md`). ✘ Mở cảnh bằng shot thiết lập 0,5 s theo thói quen (lần chạy 4).

### Đ3. Kể bằng hình
- **Làm gì · vì sao.** Cho thấy thay vì kể: nghĩa sinh ra khi **đặt hai hình cạnh nhau**, nên mỗi shot mang **một** thông tin rõ (Mamet [Đ4]).
  - **Ai biết gì:** người xem biết trước nhân vật → **hồi hộp** (quả bom dưới gầm bàn của Hitchcock [Đ7]); biết cùng lúc → căng; biết sau →
    **bất ngờ**. Chọn có chủ đích cho từng cảnh.
  - **Phản ứng trước, nguyên nhân sau** — một cách làm cụ thể của "biết sau": cho thấy mặt nhân vật sững lại / hoảng lên trước, rồi mới
    cắt sang cái họ thấy [Đ31]. Người xem thấy phản ứng mà chưa thấy lý do → tự đặt câu hỏi, và câu hỏi giữ họ lại; thấy lý do trước thì
    họ chỉ xác nhận. Giới hạn: nguyên nhân phải lộ ngay shot kế (≤ 2 s) — để lâu thành rối. Thứ tự thường ngày (hành động → phản ứng) vẫn
    đúng khi muốn người xem *đồng cảm* với phản ứng (đã biết chuyện, giờ xem nhân vật đón nhận).
  - **Motif:** một hình ảnh lặp lại và biến tấu (McKee gọi là hệ hình ảnh [Đ5]) — cảnh mở và cảnh kết "vần" với nhau.
  - **Thời tiết, ánh sáng:** mưa khi buồn là cách dễ đoán nhất nên dễ sáo (Ruskin gọi việc gán cảm xúc cho thiên nhiên là "pathetic
    fallacy" [Đ10]). Dùng khi có lý do trong truyện (thời tiết cản mục tiêu), khi đối lập (trời đẹp giữa mất mát), hoặc khi nó **đổi** ở một
    mốc biến chuyển.
  - **Nền là một nơi thật**, kể cả khi tối: "bóng tối" = đêm/thiếu sáng ở bối cảnh của dự án, không phải nền đen trơn.
- **Trong pipeline.** Cảnh: `time`, `lighting`, `mood`; shot/cảnh: `weather` (danh sách cố định, Đ8); hình motif ghi lặp lại trong
  `image_prompt` của các shot cần "vần". Ai-biết-gì ghi trong `emotional_intent` ("người xem biết trước Kelly: …").
- **Kiểm.** Code: `void_background` (nền "void/black background") trong bàn đo; thời tiết lạ bị báo (`plate_env.weather_of`). Người xem: tắt
  tiếng còn hiểu không. Motif: trường shot `motif` (nhãn ngắn, cùng nhãn ở các shot "vần") — code báo motif chỉ xuất hiện một lần
  (`continuity.motif_warnings`, bàn đo + Bước 1 🧭). Ai-biết-gì: chưa có trường riêng (ghi trong `emotional_intent`).
- **Ví dụ FF.** ✔ #6: người xem biết ít như Kelly (nghe lỏm "không được để cô ấy biết") → twist là bất ngờ; cảnh mở và cảnh kết cùng nơi,
  cùng góc qua vai Kenta — lần đầu khóc, lần sau cười trong nước mắt (motif). ✘ Chạy thử 2A: 4 shot mở đầu nền đen trơn, người xem thấy như
  "chưa làm xong"; tháp đồng hồ chỉ tả bằng chữ ra tháp châu Âu chung chung (sửa bằng gói bối cảnh, Đ8).

### Đ4. Chỉ đạo diễn xuất cho nhân vật AI (`performance`)
- **Làm gì · vì sao.** Model ảnh/video không có diễn viên để hỏi "nhân vật muốn gì": nếu không ai nói, model **tự chọn** biểu cảm — thường là
  biểu cảm chung chung hoặc sai. Chỉ đạo **bằng hành vi nhìn thấy được**, không bằng nhãn cảm xúc: "sad" chỉ cho ra *mặt làm buồn* (diễn viên
  gọi là "indicating" [Đ1][Đ2]); Kling cũng khuyên tả hành vi quan sát được thay cho cảm xúc bên trong [Đ24].
  - **Cường độ theo cỡ cảnh:** càng cận, máy càng bắt chi tiết nhỏ → cận thể hiện nhỏ hơn [Đ14]. Đạo diễn ghi `intensity` theo **độ mạnh của
    khoảnh khắc** (đường cảm xúc, Đ2); code tự vẽ ở cận CU/ECU **thấp hơn một bậc** — không tự hạ số, kẻo đường cong bị méo.
  - **Vi biểu cảm** (Ekman [Đ13]): thoáng qua cả khuôn mặt trong ≤ 0,5 s khi người ta đang che giấu; loại chỉ lộ ở **một vùng** mặt (mắt, hoặc
    khóe miệng) là biểu cảm "tinh tế". Cảnh "cố giấu" thì tả mặt đang giữ bình thường rồi một vùng lộ ra — model video vẽ được điều đó hơn
    là một cái chớp cả mặt 0,5 s.
  - **Ánh mắt:** nhìn vào một mắt người kia, không đảo; chớp ít = mạnh, chớp nhiều = bất an [Đ14]. **Hơi thở, khoảng lặng** trước câu
    quan trọng. **Hành động có động cơ** ("tay siết lại *vì* cố không khóc").
  - **Người nghe cũng diễn:** lắng nghe là diễn; shot phản ứng thường mạnh hơn shot người nói [Đ15].
- **Trong pipeline.** Mỗi shot có người ghi `performance` (tiếng Anh, trừ `motive`):
  `{"intensity": 1-5, "face": "…", "eyes": "…", "body": "…", "timing": "…", "listener": "…", "motive": "tiếng Việt: vì sao"}`.
  Thang: 1 gần như không thấy · 2 kìm nén · 3 rõ nhưng tự nhiên · 4 mạnh · 5 đỉnh cảm xúc của phim.
  Code đưa `face/eyes/body` (+ `listener` khi người nghe trong khung) vào prompt khung đầu kèm cường độ thể hiện (`performance.image_sentence`,
  cận hạ một bậc — `shown_intensity`); Motion đọc cả trường để viết diễn biến theo thời gian (`timing`); QC ảnh/clip chấm biểu cảm theo nó.
  Đổi `performance` → ảnh/clip thành "⚠ cũ" (lineage).
- **Kiểm.** Code (`performance.warnings`, hiện ở Bước 1 và bàn đo): `face` ngắn (≤ 3 từ) chứa tên cảm xúc → "tả việc mặt làm"; shot
  thoại/phản ứng/móc/kết có người mà thiếu `performance` → "model tự chọn biểu cảm"; đỉnh > 2 lần; 6 shot liền cùng mức → đường phẳng.
  QC clip (Claude xem khung) chấm biểu cảm so với `performance`. **Bảng kiểm "diễn quá / diễn đơ"** cho người xem:
  diễn quá = miệng há to/nhăn cả mặt ở cận, khóc nấc khi kịch bản ghi "cố mỉm cười", cả khung cùng một cảm xúc; diễn đơ = mắt vô hồn nhìn
  vào khoảng không, mặt không đổi khi nghe tin, người nghe đứng như tượng.
- **Ví dụ FF.** ✔ Kelly "cố mỉm cười nhưng nước mắt vẫn rơi" → `{"intensity": 3, "face": "lips pressed into a trembling smile, chin tight",
  "eyes": "wet, fixed on Kenta, blinking fast", "body": "shoulders drawn in, hands clenched at her sides", "motive": "cố không khóc trước mặt
  anh"}`. ✘ #6 job 166: không ai chỉ đạo, clip ra Maxim "giận, miệng há to" thay vì cười nhếch → QC trả về, trả tiền gen lại. ✘ Job 133:
  quay đầu nhanh làm mặt Kelly nhòe → hành động quan trọng chậm và nhỏ (`timing`: "turns her head slowly").

### Đ5. Chỉ đạo giọng lồng (`delivery`)
- **Làm gì · vì sao.** Giọng lồng là nửa còn lại của diễn xuất: cùng một câu, đọc nhanh hay chậm, có ngắt trước hay không, nhấn chữ nào
  đổi hẳn nghĩa. Báo cho giọng *cảm xúc, cường độ, nhịp, chỗ ngắt, chữ nhấn* của từng câu, như chỉ đạo diễn viên lồng tiếng.
  - Những gì TTS nhận được (tài liệu chính thức ElevenLabs [Đ20]–[Đ23], skill ClipAI): `speed` 0,7–1,2; eleven_v3 chỉ có 3 mức ổn định
    (Creative = biểu cảm nhất, dễ trôi; Natural; Robust = đều, ít nghe chỉ dẫn); v3 **không đọc thẻ ngắt SSML** — ngắt bằng "…", nhấn bằng
    CHỮ HOA, thẻ âm như `[whispers]`, `[sighs]` đặt trước chữ nó tô màu. Câu quá ngắn cho kết quả kém ổn định.
- **Trong pipeline.** Mỗi câu thoại có thể có `delivery`:
  `{"emotion": "…", "intensity": 1-5, "pace": "slow|normal|fast", "pause_before": true, "stress": "chữ cần nhấn", "tag": "whispers"}`.
  Code (`core/voice_direction.py`, cờ `voice_direction` TẮT tới khi nghe thử): nhịp → `speed` (0,9 / 1,1); mọi câu có chỉ đạo dùng
  Natural, **chỉ câu cường độ 5** dùng Creative (ElevenLabs: Creative dễ "ảo giác" — không đặt rủi ro đó lên mọi câu quan trọng);
  `pause_before` → "… "; `stress` → chữ hoa; `tag` chỉ nhận danh sách an toàn. Phụ đề giữ nguyên chữ kịch bản.
  - **Rủi ro chưa thử thật (việc V3):** thẻ âm với giọng Việt có thể bị đọc thành chữ; CHỮ HOA có dấu ("KHÔNG") có thể bị đánh vần; câu lẻ
    rất ngắn ("Ừ.") kém ổn định — với câu ≤ 3 chữ, không dùng `tag`/`stress`, chỉ `pace`/`pause_before`.
- **Kiểm.** Code: giọng bị cắt/thiếu chữ (`voice_check`). **Người nghe theo bảng kiểm** (bản dựng có tiếng): câu có đúng cảm xúc ghi ở
  `emotion` không; nhịp chậm/nhanh có nghe ra không; thẻ âm có bị đọc thành chữ không; chữ nhấn có bị đánh vần không. *Chưa có* kiểm tự động
  giọng đúng `delivery` (cần một mô hình nghe cảm xúc — ghi nhận, chưa làm).
- **Ví dụ FF.** ✔ "Em hiểu rồi…" → `{"emotion": "resigned", "intensity": 2, "pace": "slow", "pause_before": true}`; "Kelly, nghe anh giải thích…"
  (Cảnh 3) → `{"emotion": "pleading", "intensity": 3, "pace": "fast", "stress": "giải thích"}`. "Kenta!" chỉ 1 chữ → chỉ `pace`/`intensity`
  (câu ≤ 3 chữ: code bỏ `tag`/`stress`). ✔ Đã học ở 2A: câu bị cắt cuối được tạo lại với "…" ở cuối → giọng buông tự nhiên.

### Đ6. Ghi chú kịch bản cho người viết (`script_notes`)
- **Làm gì · vì sao.** Đạo diễn đọc kỹ nhất nên thấy chỗ yếu trước: câu thiếu lý do, chỗ hụt logic, cú twist chưa được gieo. Nhưng kịch bản là
  của người viết — **chỉ đề xuất, không tự sửa thoại** (giữ N1). Cách ghi của nghề (Yorke [Đ27]): chỉ ghi điều làm kịch bản *tốt hơn* (không
  chỉ *khác đi*); nói điều đang tốt trước; chẩn đoán bằng câu hỏi thay vì kê đơn; lớn trước nhỏ sau; dùng "rõ / chưa rõ" thay "thích / không thích".
- **Trong pipeline.** Gốc JSON: `"script_notes": [{"scene": số, "kind": "logic|gieo-gặt|nhịp|thoại|khác", "note": "vị trí → người xem sẽ
  thấy gì → câu hỏi / mục tiêu"}]`. Không có trường "câu thoại mới". Hiện ở Bước 1 (📝) để người dùng chọn sửa kịch bản hay bỏ qua.
- **Kiểm.** Người dùng đọc. Code chỉ đếm và hiện.
- **Ví dụ FF.** ✔ #6: "TWIST: Kenta cứu **Maxim**, còn câu gieo là 'chỉ cần **cô ấy** còn sống' → người xem có thể không hiểu Kenta giấu
  Kelly điều gì. Có nên thêm một hình/câu nối việc cứu Maxim với an toàn của Kelly?" ✘ Tự đổi câu thoại cho "hay hơn" (vi phạm N1).

### Đ7. Luật sản xuất (giữ từ bản trước, cập nhật V4)
- **N1. Trung thành kịch bản.** Thoại nguyên văn, đúng người, đúng thứ tự, không thêm câu (code `llm_io._check_lines`). Cặp đối đáp là một đơn
  vị. Không bỏ câu gieo cho twist/kết, câu cho thấy nhân vật đã cố làm gì. Góc máy kịch bản ghi thì giữ tinh thần ("sau vai X" → qua vai;
  "cận cảnh" → cận). Chữ hệ thống/thông báo game/chữ kết là `on_screen_text`, không phải giọng (2A: "HỆ THỐNG" từng thành NARRATOR).
- **N2. Nhịp do kịch bản và cảm xúc quyết định.** Thời lượng kịch bản ghi là khung (code `shot_normalize` không co phần nào dưới mốc). Shot
  thoại ≥ âm tiết ÷ 3,5 + 0,5 s (code tự kéo dài). Không shot im lặng < 1 s; toàn cảnh ≥ 1,5 s (code gộp/kéo). Thừa thời lượng: gộp im lặng →
  rút phản ứng/chèn → (nếu được phép) bỏ câu không ai đáp; thoại cần nhiều hơn khung → thoại thắng, ghi `tradeoffs`.
- **N3. Khớp môi.** Cờ `lip_sync` **TẮT** (mặc định): không đặt thoại ở cận mặt người đang nói — trung/toàn, qua vai, người nói quay nghiêng,
  hoặc câu lên shot người nghe; cận mặt dành cho im lặng (code `storyboard_gate.lip_sync_risk`). Cờ **BẬT**: được thấy mặt người nói; câu
  then chốt quay cận (CU/ECU/MCU, ngang mắt, mặt không che, ≤ 5 s) ghi `"lip_sync": true` (~20% câu quan trọng nhất — đắt hơn).
- **N4. Nhân vật đúng thiết kế.** Ảnh chuẩn Kho là chuẩn thật; hồ sơ chuẩn đã duyệt thắng mô tả của dự án; mắt người/ảnh chuẩn là trọng tài
  cuối. **Không ghi số tuổi dưới 18** — nhân vật trẻ tả "young, not yet 20" (2A: GPT Image từ chối "17-year-old"; code `no_minor_age` xoá tuổi).
- **N5. Thể loại quyết định logic dựng.** SHORT_FORM: móc trong 1–3 s đầu (Đ2), mật độ cao, kết có chốt; kịch/phim: nhân quả, khoảng lặng.

### Đ8. Bối cảnh và thời tiết (gói bối cảnh — khi cờ `location_plates` bật)
- **Làm gì · vì sao.** Nơi quay có mô hình 3D thì nền là pixel thật (đúng game), AI chỉ vẽ nhân vật. Đạo diễn chọn **đứng ở đâu** và **trời
  thế nào** vì lý do truyện (Đ3); Quay phim đặt máy (dp.md Q6).
- **Trong pipeline.** `plate_spot` (tên chỗ đứng — danh sách hiện trong khối "Gói bối cảnh" của prompt), `weather` (chỉ các tên: clear,
  cloudy, fog, rain, storm, snow, snowfall, ice, sandstorm), `time` của cảnh (dawn, day, dusk, night). Tên lạ bị đổi về mặc định **và báo lại**.
- **Kiểm.** Code: `weather_problem`, `spot_problem` trong kế hoạch nền; điểm giống nền (`plate_qc`).

### Đ9. Âm thanh cùng cảm xúc (`sound`) — 2026-09-26
- **Làm gì · vì sao.** Âm thanh là một nửa của cảm xúc và là sợi chỉ nối các clip AI rời rạc, nên quyết **cùng lúc với hình**, không để
  hậu kỳ đoán. Bảng phân cảnh mẫu của Handbook [Đ31] ghi âm thanh cạnh cảm xúc ở *từng* shot: nhạc tắt đột ngột khi khẩu súng xuất hiện,
  bỏ nhạc lúc phe ác tưởng đã thắng, tắt hết tiếng ở đỉnh. Trước đây pipeline chỉ có Đạo diễn vẽ hình; người làm âm thanh (`sfx_plan`)
  tự đoán điểm nhấn từ chữ kịch bản, còn khoảng lặng nhạc duy nhất (D6) chỉ đặt trước phần TWIST.
  - **Im lặng là công cụ mạnh nhất:** tắt nhạc thì âm nhỏ nhất (bước chân, tiếng lên đạn, hơi thở) thành to — dùng khi mối đe dọa xuất
    hiện, lúc bình yên giả tạo, ngay trước điều bị lộ. **Lặng ngắn trước cú ngoặt** để cú đánh rơi đúng (D6, editing.md E4). Nhạc **vào
    lại** khi thế trận lật.
  - **Âm của cơ thể và vật** (tiếng thở dồn, nuốt nước bọt, sột soạt vải, tiếng bíp) làm cảm xúc gai góc hơn nhạc — chỉ vài âm, đúng khoảnh khắc.
  - Tự hỏi hai chiều: tắt tiếng đi hình còn kể được không (tầng 5) — **và bật tiếng lên, âm thanh có đẩy thêm được gì không**.
- **Trong pipeline.** Shot (tùy chọn, chỉ nơi cần): `"sound": {"music": "keep|cut|in|breath", "sfx": ["…"], "why": "…"}` (`core/sound_intent.py`).
  `cut` nhạc tắt từ đầu shot tới shot `in`; `breath` lặng 0,6 s ngay trước shot; `sfx` ≤ 3 âm. Người làm âm thanh (`sfx_plan`) nhận ý đồ
  này, **phải** đặt các âm được yêu cầu hoặc nói kho thiếu âm nào (Bước 5 🔊 + autopilot ghi cảnh báo). Nhạc theo `cut/in/breath` vào
  bản dựng khi cờ `sound_intent` BẬT (TẮT tới khi nghe thử); tắt thì manifest bản dựng ghi số ý đồ chưa áp. J-cut/L-cut của thoại vẫn là
  việc của Dựng (cờ `j_cut`; L-cut = đặt câu lên shot người nghe, N3).
- **Kiểm.** Code (`sound_intent.warnings`, Bước 1 🔊 + bàn đo): `in` khi nhạc đang có, `cut` khi nhạc đã tắt, `breath` ở shot đầu, nhạc tắt
  quá nửa phim (quên `in`), đỉnh cảm xúc cường độ 5 mà âm thanh không có ý đồ. Người nghe: bản dựng có tiếng.
- **Ví dụ FF** (minh họa, chưa chạy thật). ✔ #6 cảnh Kelly nghe lỏm "không được để cô ấy biết": shot mặt Kelly `{"music": "cut", "sfx": ["held breath"], "why": "im
  lặng để câu nghe lỏm rơi nặng"}`, nhạc `in` lại ở cảnh Kelly bỏ đi. ✘ Rải `cut` ở nhiều shot liền → nhạc bật tắt liên tục, mất tác dụng.

## Tầng 4 — Thứ tự ưu tiên khi luật xung đột (người dùng chốt 2026-09-25; chỉnh dần theo dữ liệu)
**Luật cứng, đứng ngoài thang** (code kiểm, không thương lượng): giới hạn model, trần tiền, không tuổi < 18 — chọn cách khác bên trong chúng.
Thang chung của cả tổ: `README.md`.
1. **Mạch truyện & cảm xúc** (ý định cảm xúc; người xem hiểu ai với ai ở đâu; diễn xuất đúng nhịp)
2. **Thoại nguyên văn + cặp đối đáp**
3. **Góc máy kịch bản ghi**
4. **Thời lượng kịch bản**
5. **Tiết kiệm tiền video**
6. **Phong cách dựng / thẩm mỹ**
Hy sinh một mục thấp hơn thì ghi ở gốc JSON: `"tradeoffs": [{"chose": "…", "gave_up": "…", "why": "…", "scene": số}]`. **Code kiểm**: bỏ
câu thoại / lệch khung thời lượng / shot thiếu thời gian nói mà `tradeoffs` rỗng → ⚠ ở Bước 1 và tính là một lỗi của bàn đo.

## Tầng 5 — Tự rà trước khi trả lời (câu hỏi của đạo diễn)
- Tắt tiếng đi, người xem còn hiểu ai muốn gì, ai đổi trạng thái không? 3 giây đầu có lý do để ở lại không?
- Mỗi cảnh giá trị đổi từ đâu sang đâu? Có cảnh nào đứng yên?
- Mỗi câu thoại còn lý do để được nói, còn câu nào đáp lại nó không? Câu gieo nào sắp bị mất?
- Shot có người nào thiếu `performance`? Có chỗ nào cả khung cùng một cảm xúc, hay đỉnh cảm xúc lặp lại quá 2 lần?
- Sau khoảnh khắc mạnh, người xem có một shot để thấm không? Giữa video có chi tiết dở dang nào kéo người xem sang đoạn sau không?
- Ở đỉnh và ở cú ngoặt, âm thanh làm gì (im lặng, nhạc ngắt, một âm nhỏ)? Có `cut` nào quên `in`?
- Mình đã hy sinh gì, đã ghi `tradeoffs` chưa? Có điều gì về kịch bản nên ghi `script_notes`?
