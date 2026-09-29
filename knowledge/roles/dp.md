# Vai Quay phim (DP) — bộ kỹ năng nghề (V4 GĐ4, 2026-09-25; nâng theo người chấm 2026-09-26 — chờ người dùng duyệt rồi bật `film_crew`)

> Quay phim nhận **ý đồ** của Đạo diễn (nhịp, `emotional_intent`, `performance`, thoại) và biến thành **shot**: cỡ cảnh, góc, ống kính,
> chuyển động máy, bố cục, ánh sáng, vị trí máy, prompt khung đầu. Không đổi thoại, không đổi ý đồ. Mỗi shot ghi **`why`** để Đạo diễn duyệt.
> Mỗi kỹ năng: **Làm gì · vì sao** — **Trong pipeline** — **Kiểm** — **Ví dụ FF**. Nguồn: `knowledge/sources.md` mục GĐ4 (số [Qn]).
> Số liệu FF: 519 shot của 19 video Free Fire (`ff_directing.md`); dữ liệu chạy thật: lý do QC trả clip ở CSDL (job #).
> **Trong pipeline — một hay hai lượt.** Mặc định bộ này đi cùng bộ Đạo diễn trong một lượt Director. Cờ `director_two_pass` (dự án chia
> shot, V4 GĐ5): **Tầng B** — mỗi cảnh một lượt riêng (prompt 20 + 17), bạn nhận ý đồ Tầng A của Đạo diễn (`emotional_intent`, `beat`,
> câu thoại giữ kèm `delivery`, khung giây `target_s`, `focus`, `peak`, `sound`, `dp_notes`) và trả `shots` của đúng cảnh đó. Thoại lệch
> danh sách Đạo diễn giữ → chỉ cảnh đó bị hỏi lại; tổng giây ngoài khung, trọng tâm vắng khung, khoảnh khắc mạnh không có shot giữ → cờ
> "Đạo diễn duyệt" ở Bước 1. "↻ Chia shot lại cảnh này" chỉ hỏi lại bạn, không hỏi lại Đạo diễn.

> **Trường Quay phim viết từ ý đồ Đạo diễn** (nhất là Tầng B, khi Đạo diễn chỉ ghi mức cảnh): `performance` từng shot (từ `dp_notes`,
> `peak` — director.md Đ4), `sound` từng shot (từ `sound` mức cảnh — Đ9), `role: "hook"` + `hook_mid` (Đ2), `motif` (Đ3), `hero` ⭐ (cao
> trào — model tốt nhất; **Đạo diễn chọn cảnh** — prompt 19 `shot_role: "hero"` mức cảnh — **Quay phim chọn shot** trong cảnh đó) và
> `money_shot` (khoảnh khắc sản phẩm — ảnh bìa, Đ10), `speed`/`freeze_end_s` (Q11, Đ11). Đọc `knowledge_gap`
> của cảnh: `behind` (người xem biết sau) → **phản ứng trước, nguyên nhân sau** (shot mặt sững lại trước, cái họ thấy ở shot kế ≤ 2 s);
> `ahead` (biết trước — hồi hộp) → cho người xem thấy mối nguy trước (shot chèn mối nguy, rồi nhân vật chưa biết); `same` → cùng nhịp.

## Tầng 1 — Mục đích
Làm cho người xem **thấy rõ** điều Đạo diễn muốn họ cảm — ai ở đâu, nhìn ai, cảm gì — với **ít clip nhất** mà model video làm tốt được.

## Tầng 2 — Cách nghĩ
1. Với mỗi nhịp: trọng tâm là ai → người xem nên gần hay xa, trên hay dưới → cỡ cảnh + góc (Q1) + ống kính (Q2).
2. Đặt **vị trí máy cho cả cảnh trước** (Q9: sơ đồ nhìn từ trên — ai đứng đâu, trục 180° ở đâu), rồi mới chia shot trên các vị trí đó.
3. Gắn từng câu thoại vào vị trí máy hợp (N3 khớp môi của Đạo diễn), đặt ánh sáng theo nguồn thật của cảnh (Q8).
4. Viết khung đầu (`image_prompt`, `start_frame`) + chuyển động (`camera_move`) trong giới hạn model (Q4, Q5); nền 3D thì theo Q6.
5. Ghi `why` cho từng shot (Q7), tự rà (tầng 5).

## Tầng 3 — Kỹ năng

### Q1. Cỡ cảnh và góc máy — kèm tâm lý
- **Làm gì · vì sao.** Cỡ cảnh quyết định người xem **gần** nhân vật bao nhiêu: toàn = định vị, ai ở đâu; trung = quan hệ, cử chỉ; cận = cảm
  xúc; cận đặc tả = chi tiết/vi biểu cảm. Góc quyết định **quan hệ quyền lực** người xem cảm thấy: ngang mắt trung tính; thấp = áp đảo,
  anh hùng; cao = nhỏ lại, bị theo dõi, hoặc cho thấy đội hình/bản đồ; nghiêng (dutch) = rối loạn, bạo lực; qua vai = quan hệ hai người;
  POV = đứng vào chỗ nhân vật [Q1][Q3][Q5].
  - **Ý nghĩa góc không cố định:** góc thấp nhất của *Citizen Kane* rơi vào lúc Kane thất bại; góc cao của *North by Northwest* dành cho kẻ
    đang nắm quyền [Q2]. → Ghi lý do theo tình huống, không tra bảng "thấp = mạnh".
  - **Nhấn bằng tương phản:** chuỗi toàn rồi cận đột ngột tăng cường độ; giữ một cỡ thì cường độ giảm dần (Block [Q25]).
- **Trong pipeline.** `size` ∈ ECU/CU/MCU/MS/MLS/WS/EWS/GAME_TPS (MLS = từ gối trở lên, người + một phần nơi chốn — máy ảo và prompt ảnh
  đều có; tên khác như "medium long shot", "cowboy" được chuẩn hóa về MLS); `angle` ∈ eye/low/high/overhead/dutch/ots/pov (giá trị lạ bị
  trả lại — mỗi lần là một lần hỏi lại trả tiền). GAME_TPS luôn `angle: "high"`. Code dịch cỡ cảnh thành câu khung hình (`framing_sentence`).
- **Kiểm.** Code: chuẩn hóa từ vựng; bốn shot liền cùng cỡ → ⚠ (`pacing_warnings`). Claude/người: storyboard.
- **Ví dụ FF.** ✔ Cỡ cảnh FF đo được: toàn 34%, còn lại trung/cận; 79% video gameplay dùng góc GAME_TPS. ✔ #6 "GÓC CAMERA SAU VAI KENTA" →
  `ots`, Kenta mờ ở tiền cảnh. ✘ Lần chạy 2 bỏ góc qua vai kịch bản ghi.

### Q2. Ống kính và máy ảo
- **Làm gì · vì sao.** Méo phối cảnh do **khoảng cách** máy–chủ thể, không do tiêu cự: cùng cỡ mặt, ống rộng đặt sát làm phồng mặt, ống dài đặt
  xa làm dẹt; mặt đẹp nhất thường ở 50–85 mm (ASC [Q19]). Ống rộng mở không gian, phóng to tiền cảnh; ống dài "nén" nền (thực chất do đứng
  xa) và tách chủ thể nhờ độ sâu trường ảnh nông [Q3][Q19]. Đổi nét (rack focus) dẫn mắt từ lớp này sang lớp khác; nét sâu giữ cả gần lẫn xa.
- **Bảng mặc định của máy ảo** (`core/plate_camera.py` `FRAMING`; khung dọc 9:16, cảm biến 36 mm theo **cạnh dọc** — Blender "Auto" lấy
  cạnh dài [Q21]):

  | Cỡ | mm | FOV dọc / ngang | Dùng khi |
  |---|---|---|---|
  | EWS | 20 | 84° / 53° | lập bản đồ, quy mô |
  | WS / GAME_TPS | 24 | 74° / 46° | định vị, gameplay |
  | MLS | 32 | 59° / 35° | người + nơi chốn, đi lại, hai người đứng |
  | MS | 35 | 54° / 32° | quan hệ, cử chỉ, hai người |
  | MCU | 50 | 40° / 23° | thoại, cảm xúc tự nhiên |
  | CU | 65 | 31° / 18° | cảm xúc |
  | ECU | 85 | 24° / 14° | mắt, chi tiết |

  Khung dọc hẹp theo chiều ngang: muốn rộng ngang như "35 mm" của khung 16:9 cần ~18–20 mm.
- **Trong pipeline.** `lens_mm` (14–200) khi muốn khác mặc định. Hiệu ứng thị giác (dùng cho ý đồ nào là tùy cảnh): 24 mm đặt gần phóng to tiền cảnh, kéo dãn không gian (có thể gợi ngợp, hùng, méo, hài…); 85–135 mm nén hậu cảnh, tách chủ thể (có thể gợi cô lập, rình rập, thân mật…). Máy ảo giữ
  **cỡ người trong khung** và tự lùi/tiến máy theo tiêu cự → nền đổi độ nén đúng như máy thật. Không có nền 3D thì ghi ống kính bằng chữ trong
  `image_prompt` ("shot on a 24mm lens, close") — model ảnh chỉ nghe theo chữ.
  - **Độ sâu trường ảnh bằng chữ** (shot không có nền 3D): nói **lớp nào nét, lớp nào nhòe** và vì sao — "Kelly in sharp focus, the tower
    behind softly blurred" (cô lập, cảm xúc) · "deep focus, both Kelly in the foreground and the sniper on the roof sharp" (người xem phải
    thấy mối đe dọa) · đổi nét trong shot (rack focus) chỉ viết ở motion prompt, không ở khung đầu. Đừng viết "bokeh" chung chung — model vẽ
    đốm sáng trang trí. Nền 3D: độ nhòe do ghép + sương theo khoảng cách (`plate_env`), không cần chữ.
- **Kiểm.** Code: `plate_camera.camera_for` (hộp nhân vật trong khung, khoảng cách máy); test hình học. Người: xem ảnh nền render.
- **Ví dụ FF.** ✔ Tháp Đồng Hồ #263 shot 4 (MS, 35 mm): tháp chiếm nửa khung phía sau Kelly. ✘ Shot cận ở chân tháp với 65 mm chỉ thấy chân
  tháp — muốn thấy mốc thì hạ máy + ngửa (góc thấp) hoặc lùi ra trung (Q6).

### Q3. Bố cục (khung dọc 9:16)
- **Làm gì · vì sao.** Mỗi khung **một trung tâm chú ý**; 1/3; chiều sâu tiền–trung–hậu (Block [Q25]: không gian sâu thường tăng cường độ thị giác, phẳng giảm — là công cụ, ý đồ do cảnh);
  đường dẫn, khung trong khung, khoảng trống âm (người nhỏ giữa khoảng trống có thể gợi cô độc, tự do, bị đe dọa… tùy cảnh) [Q1][Q5]. Khoảng trống phía nhìn/phía đi; khoảng
  trống trên đầu vừa đủ. **Khung dọc** mạnh ở chiều cao (toàn thân, mặt cận, công trình đứng), yếu ở hai người đứng ngang → xếp người theo
  **chiều sâu** (qua vai) thay vì cạnh nhau.
  - **Vị trí mắt — MỘT luật (nguồn số duy nhất của cả tổ; README trỏ về đây).** Luật chung: mắt **không lọt vào thanh giao diện app
    (15% trên)** — luật là **mắt**, đỉnh đầu được chạm thanh. Theo cỡ:
    | Cỡ | Mắt từ mép trên | Vì sao | Máy ảo đo (`plate_camera.HEADROOM`, `camera_for` + chiếu điểm) |
    |---|---|---|---|
    | MLS · MS · MCU · CU | **18–35%** (15% thanh + 3% đệm; không thấp hơn đường một phần ba ~33% quá 2%) | mặt là chủ thể; thấp hơn thì khoảng trống trên đầu thừa, người tụt xuống vùng phụ đề | ~20 · 23 · 28 · 33% |
    | WS | **≥ 15%** (không cần đệm 3% — người nhỏ, mặt không phải chủ thể) | toàn thân cần chỗ phía dưới | ~16,6% |
    | EWS · GAME_TPS | không áp — người nhỏ ở giữa khung | nơi chốn là chủ thể | người ở ~40–43% khung |
    | ECU | không áp — mắt/chi tiết lấp khung | chi tiết là chủ thể | ~57% (giữa khung) |
    Mốc 30–35% của nguồn cộng đồng [Q29] là cho khung **cận** — khớp CU. Sửa ở GĐ4: trước đó mắt MS ở ~14%, lọt vào thanh.
- **Trong pipeline.** `start_frame`: vị trí người (trái/giữa/phải, tiền/hậu cảnh, hướng mặt) — máy ảo đọc "frame-left/right" để đặt người;
  code lưu nó vào trường `blocking` của shot (`shots.shot_data`) — **một** trường: `start_frame` là tên Quay phim viết, `blocking` là tên
  lưu (prompt 01 một lượt gọi thẳng là `blocking` của cảnh). Ai đứng gần/xa ai vì lý do truyện là ý của Đạo diễn (`dp_notes`).
  **Chừa chỗ cho chữ**: dải trên (thông báo game) hoặc dải dưới của vùng an toàn (phụ đề) — `knowledge/editor/safe_zones.md`; vùng giao diện
  app (trên 15%, dưới 35% — code dùng 36% để có đệm —, phải 18%) không đặt mặt/hành động chính.
- **Kiểm.** Code: dò mặt YuNet trên khung thật để dời phụ đề (`text_placement`); hộp nhân vật của máy ảo. Người/Claude: storyboard.
- **Ví dụ FF.** ✔ #7 giây 13 và 17: mặt xuống tới 61–65% khung → code dời phụ đề lên dải trên. ✘ Chạy thử 2A shot 4: prompt kể "nói rồi quay
  lưng bước đi" → model vẽ **hai khung ghép** trong một ảnh (sửa: "one single frame, one moment only").

### Q4. Giới hạn model (sinh từ `data/provider_rules.json` — code kiểm trước khi gửi)
<!-- model_rules -->
- Kling multi-shot: chỉ ảnh đầu nhóm bám nhân vật (shot sau trong nhóm dễ lệch — GĐ6 R4). Seedance chặn "giống người thật/bản quyền".
  Đã đối chiếu tài liệu chính thức Kling 3.0 (2026-09-29, `video_motion_vocab.md` mục "Kling 3.0"): model ClipAI mở chính là **Kling 3.0
  Omni**, và nhận xét R4 **được đo lại trên đúng bản này** (thử 27/09 P3/S3: shot sau bịa hoặc bỏ nội dung) — không phải lỗi của bản cũ.
  Kling không nói tiếng Việt (thoại luôn là TTS ghép sau) → shot Kling có thoại phải **nêu tên người đang nói** trong prompt (code
  `speaker_lint` báo khi thiếu).
- **Khối gen ~15 s (tư liệu, không phải luật).** Người làm AI短剧 ở Trung Quốc chia truyện thành các nhóm ~15 s trước khi viết prompt
  (抽卡师 phỏng vấn — `research/craft/trung_quoc/LUOT_2.md` mục 2, một người kể) — trùng trần 15 s của Kling 3.0 / Seedance. Pipeline đã
  có dạng này: nhóm Seedance chỉ-tham-chiếu 2–4 shot liền ≤ 15 s (cờ `seedance_ref_groups`; thử 27/09: 6/6 shot đúng storyboard) và vị trí
  máy (`camera_setup`). Kling multi-shot **không** dùng để gộp các góc khác nhau (dòng trên). Khi chia shot, nhìn các shot liền nhau cùng
  nơi, cùng người như một khối gen được thì model giữ nhân vật/ánh sáng đồng nhất hơn — nhưng shot cần khung riêng (cận thấy mặt, hiệu
  ứng kỹ năng) vẫn tách ra.
- GPT Image 2.5 Sunburst nhận bảng thiết kế nhiều góc; không ghi tuổi dưới 18 (bị từ chối — code lọc).

### Q5. Chuyển động máy
- **Làm gì · vì sao.** Máy chỉ chuyển động khi có **động cơ trong truyện**: đi theo hành động, hé lộ thông tin, hay đẩy cảm xúc [Q35]. **Ý nghĩa
  chuyển động không cố định** (như góc, Q1) — cách hay gặp, không phải bảng tra: đẩy vào chậm thường kéo người xem lại gần; lùi ra thường
  tiết lộ hoặc buông; cầm tay thường tạo cảm giác tức thời; steadicam/gimbal đi theo người đi-nói; cần cẩu đổi độ cao, mở bối cảnh; vòng
  cung khoe/nhấn; lia nhanh có thể nối cảnh; dolly zoom hay dùng cho khoảnh khắc chợt nhận ra (ASC [Q20], Veo [Q3]). Cùng một chuyển động
  có thể phục vụ ý đồ ngược nhau — ghi lý do theo cảnh. Ghi **điểm đầu →
  chuyển động → biên độ → điểm cuối** (công thức của Seedance 1.5 [Q11]).
  - **Một chuyển động chính mỗi shot** — tài liệu chính thức Seedance 2.0: trộn đẩy/kéo/lia cùng lúc làm hình mất ổn định; ưu tiên chuyển
    động chậm, nhẹ [Q8]; Kling (blog) cũng vậy [Q17]. Runway viết khẳng định ("locked camera", không viết "no movement") và khi bị cắt ngoài
    ý muốn thì thêm "continuous, seamless shot" [Q5][Q6][Q7].
  - **Từ vựng prompt đã kiểm trong tài liệu chính thức:** Kling — `dolly forward/backward, track, pan, zoom, orbit, handheld, stabilizer,
    POV, shot-reverse-shot, long take` [Q15][Q16]; Seedance 2.x — `slow push-in, pull out, smooth lateral tracking, follow, orbit, tilt up,
    handheld shake, fixed shot / locked-off camera, dolly zoom, rack focus`, chia nhiều shot bằng "Shot 1 / Shot 2" [Q8][Q9]. (Ý "2.0 không
    nhận mốc giây, 2.5 nhận" lấy từ tài liệu BytePlus do agent nghiên cứu đọc; người chấm không tự kiểm lại được — coi là giả thuyết.)
    Chi tiết: `video_motion_vocab.md`.
  - **Chuyển động không có giá trị `camera_move` riêng** — dolly zoom, đổi nét (rack focus), steadicam/gimbal, vòng cung (arc): chọn
    `camera_move` gần nhất (dolly zoom → `push_in`/`pull_out`; steadicam → `track`; arc → `orbit`) và **ghi chuyển động thật trong `why`**
    để Motion viết đúng bằng chữ.
- **Model làm tốt / làm hỏng (dữ liệu chạy thật, CSDL 2026-09-25 — mẫu nhỏ, cập nhật dần; đo lại bằng:
  `SELECT json_extract(s.data,'$.camera_move') mv, j.state, count(*) FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.type='video_gen'
  GROUP BY mv, j.state`; lý do hỏng: cột `jobs.retry_reason`):** `static` dùng nhiều nhất (19 clip được duyệt);
  `track` 8 duyệt; `push_in` 3; `handheld` 1. Hỏng đã gặp: **handheld** MS (job 198) — nhận diện Kenta 0,20, vật lý 0,40, lỗi hình 0,30;
  **push_in** + nhân vật bước tới (job 206) — nhân vật **đi tại chỗ**; **track** MS (job 197) — áo choàng đổi màu nhấp nháy; **push_in**
  (job 165) — màu áo trôi dần; clip tĩnh vẫn có thể **tự chèn cảnh khác** ở đầu/cuối (job 196, 204, 205). → Ưu tiên tĩnh/đẩy chậm cho shot
  có nhận diện quan trọng; nhân vật di chuyển thì để máy **bám theo** thay vì đẩy vào; hành động chính xảy ra **sớm** trong clip (shot ngắn
  hơn clip tối thiểu được gen dài rồi cắt).
- **Trong pipeline.** `camera_move` ∈ static/push_in/pull_out/pan/tilt/track/orbit/handheld/crane/whip/zoom; câu chuyển động chi tiết do Motion
  viết từ `camera_move` + `performance.timing` + `action`.
- **Kiểm.** Code: `motion_prompt_lint` (Claude) cho shot phức tạp; QC clip (khung + giây thật). Người: xem clip.
- **Ví dụ FF.** ✔ FF đo được: máy tĩnh 62%, bám theo 28%, còn lại đẩy/vòng/lia nhanh có chủ đích. ✘ Job 206 ở trên.

### Q6. Gói bối cảnh và shot khớp môi
- **Làm gì · vì sao.** Nơi có mô hình 3D: nền là **render đúng máy của shot**, AI chỉ vẽ nhân vật trên phông xanh rồi ghép → mốc game giống
  90–100%. Quay phim chọn **chỗ đứng** và **cách làm clip**: cách 1 (ảnh khung đầu đã ghép, model video diễn trên nền thật — rẻ, model có thể
  vẽ lại nền; code chấm và tự chuyển cách 2 một lần) hay cách 2 (`plate_mode: "green"`: nhân vật diễn trên phông xanh, ghép từng khung —
  cho shot mốc lớn trong khung, máy đứng yên). Shot cận ở chân công trình cao chỉ thấy chân → hạ máy ngửa lên, hoặc trung/toàn.
- **Shot khớp môi** (cờ `lip_sync` bật): mặt người nói rõ, ngang mắt, không che miệng, ≤ 5 s, máy tĩnh hoặc đẩy rất chậm — khớp môi hỏng khi mặt
  quay nghiêng mạnh hoặc chuyển động nhanh (`docs/NGHIEN_CUU_KHOP_MOI.md`).
- **Trong pipeline.** `plate_spot`, `plate_mode`, `weather`; `lip_sync: true` chỉ ở câu then chốt cận (Đạo diễn N3). Máy ảo:
  `plate_camera.camera_for` từ `size/angle/start_frame/lens_mm/camera_setup`.
- **Kiểm.** Code: `plate_qc` (độ giống nền, tỉ lệ bị che), `spot_problem`/`weather_problem`. Người: ảnh ghép (viền, bóng, màu).
- **Ví dụ FF.** ✔ Tháp Đồng Hồ #263 (7 chỗ đứng): Kelly ghép lên nền ngày, đêm tuyết, sương. ✘ Thử "ảnh render làm tham chiếu" chỉ ~70% giống
  — model vẽ lại nền (lý do có cách ghép).

### Q7. Phối hợp với Đạo diễn (`why`, sơ đồ vị trí máy)
- **Làm gì · vì sao.** Nghề làm: đạo diễn + quay phim lập danh sách shot, quay phim vẽ **sơ đồ nhìn từ trên** (người, máy, đèn) [Q30]. Ở pipeline,
  sơ đồ là `camera_setup` + `start_frame`; lý do là **`why`** — một câu: thông tin/cảm xúc của shot → vì sao cỡ/góc/chuyển động này → nối
  trục/hướng với shot trước. Đạo diễn duyệt được, người dùng đọc được, lần sau học được.
- **Trong pipeline.** `why` (tiếng Việt, ≤ ~25 chữ) mỗi shot; lưu trong shot, hiện cho Motion. `camera_setup` (A, B, C… mỗi cảnh) khi cờ
  `camera_setups` bật.
- **Kiểm.** Người/Claude đọc; người dùng sửa được `why` và diễn xuất ở ô sửa shot (Bước 1). **Sơ đồ máy nhìn từ trên** (V4) cho shot ở nơi
  có mô hình 3D: `py tools/location_pack.py topview --project N` vẽ nhân vật, chỗ đứng, máy ảo từng shot (hướng + mm) theo tọa độ thật
  và báo cặp máy ở hai phía đối diện nhân vật. Thử #7: shot 2 (qua vai) ở phía ngược 3 shot kia — đúng với shot ngược, sai nếu không phải.
  Nơi chưa có mô hình 3D: chưa có sơ đồ (chỉ có chữ trái/phải trong `start_frame`, V5).
- **Ví dụ FF.** ✔ "Qua vai Kenta: người xem đứng phía anh, thấy Kelly cố cười — giữ trục như shot 1." ✘ "Góc đẹp."

### Q8. Ánh sáng
- **Làm gì · vì sao.** Đèn chính (key), đèn phụ (fill), đèn viền (back) [Q27]; **ánh sáng có nguồn**: hướng, màu, cường độ khớp một nguồn thật
  trong cảnh (mặt trời của nền 3D, đèn đường, lửa). Tỉ lệ key:fill ~1:1–2:1 = tông cao (high-key); 4:1 = có khối; ≥ 8:1 = tông thấp (low-key) — cảm giác (tươi, bí ẩn…) do cảnh quyết định, không do tỉ lệ
  (nguồn thứ cấp [Q27], các nguồn lệch nhau ở mốc tông cao). Nhiệt độ màu: ngày 5600 K, u ám 6500–7500 K, đèn sợi đốt ~2700 K, đèn natri ~1700–2100 K [Q28]; đêm trăng trên
  phim được **đẩy xanh lạnh theo quy ước** (trăng thật ấm hơn) — là lựa chọn phong cách.
- **Bảng tham chiếu ánh sáng cho Đạo diễn** (mục 4.2 B7): trường cảnh `lighting` viết theo mẫu cố định *nguồn — phía — màu K — tỉ lệ —
  tông*, vd `"moonlight from frame-right (cold, ~7000K look), sodium street lamp behind as rim (~2000K), key:fill 8:1, low-key"` — mọi shot
  của cảnh kế thừa cùng một bảng, nên hướng sáng không đổi giữa các shot.
- **Trong pipeline.** Cảnh `lighting`, `time`; shot `weather`. Nền 3D: `plate_env` đặt mặt trời/màu theo giờ + thời tiết và **cùng một độ chỉnh
  màu** cho nhân vật (`composite`); prompt phông xanh ghi hướng sáng theo máy (`location_pack.green_prompt`). Không có nền 3D: tả nguồn sáng
  bằng chữ trong `image_prompt` ("warm sodium street light from frame-left, cold moonlight rim").
- **Kiểm.** Code: `composite.match_colour`/`light_wrap`; **mẫu `lighting`** (`continuity.lighting_warnings`, bàn đo + Bước 1 🧭): cảnh thiếu
  `lighting` hoặc thiếu ≥ 2 phần của mẫu (nguồn — phía — màu K — key:fill — tông) → ⚠ (mềm, không từ chối). Người: ảnh ghép có "dính" nền không.
- **Ví dụ FF.** ✔ GĐ2: nhân vật sáng quá trên nền đêm → chỉnh màu người theo giờ 60%. ✘ Shot đêm mà mặt sáng đều như studio, không nguồn.

### Q9. Coverage và liền mạch
- **Làm gì · vì sao.** **Vị trí máy trước, shot sau.** Đối thoại: 1 vị trí thiết lập + 2–3 vị trí phủ (qua vai A, qua vai B, hai người), thêm
  shot chèn [Q24]. Hành động/đấu súng kiểu FF: giữ **hướng màn hình** của mỗi phe (ta nhìn phải, địch nhìn trái), góc TPS xen góc thấp anh
  hùng; truy đuổi: người đuổi và người chạy **cùng hướng** trên màn hình. **Trục 180°**: mọi máy cùng một phía; vượt trục đảo hướng, tráo chỗ
  nhân vật — lỗi hướng phổ biến nhất (Mascelli [Q1]). Vượt hợp lệ: máy đi qua trục trong shot, shot trung tính trên trục, nhân vật tự đi qua,
  cutaway, POV [Q22][Q23]. **Luật 30°**: hai shot liền cùng chủ thể lệch ≥ 30° và nên đổi cả cỡ, nếu không thành cắt nhảy [Q24]. Hướng nhìn
  shot A trùng vị trí vật được nhìn ở shot B. **Cắt trên hành động**: shot N kết giữa động tác, shot N+1 bắt đầu cùng động tác. **Cắt khớp**
  (match cut): hai shot có hình khối/chuyển động giống nhau nối hai nơi/hai thời điểm (tâm ngắm tròn → ống kính tròn; cú xoay người ở cảnh A
  → cú xoay ở cảnh B) — Quay phim đặt hai khung cùng vị trí khối, cùng cỡ.
  - **Mẫu phủ FF — đấu súng / kỹ năng:** (1) toàn định vị hai phe (GAME_TPS hoặc cao) → (2) qua vai người bắn, mục tiêu ở hậu cảnh → (3) cận
    tay/vũ khí/hiệu ứng kỹ năng (chèn 0,3–1 s) → (4) phản ứng người trúng/người đứng xem → (5) góc thấp anh hùng cho cú chốt. Phe ta luôn một
    phía màn hình.
  - **Mẫu phủ FF — truy đuổi:** bám theo sau lưng (track/GAME_TPS) xen góc ngang đi cùng; người chạy và người đuổi cùng hướng màn hình; khoảng
    cách giữa hai người là thông tin — một shot rộng cho thấy nó ở mỗi nhịp đổi.
- **Trong pipeline.** `camera_setup`; `start_frame`/`end_state` (hướng mặt, bên trái/phải); `continuous_with_next: true` khi hành động kéo qua
  điểm cắt; cờ `end_frames` vẽ khung cuối cho shot đổi trạng thái.
- **Kiểm.** Code: `same_framing` (chỉ nối ảnh shot trước khi cùng khung), `end_frames`; **trục 180° / hướng màn hình**
  (`continuity.axis_warnings`, bàn đo + Bước 1 🧭): hai người đổi bên trái/phải giữa hai shot cùng cảnh, hoặc một người đổi hướng chạy —
  đọc từ chữ "frame-left/right", "left to right" trong `start_frame`. **Có kiểm shot qua vai** (cặp qua vai A/B là chỗ hay vượt trục nhất);
  bỏ qua POV / nhìn từ trên / vòng quanh (`orbit`) và shot có `why` ghi "vượt trục / cross the line" — "giữ trục 180°" **không** tắt kiểm.
  Shot có hai người mà `start_frame` không ghi ai bên trái/phải → "không kiểm được trục" (một lần mỗi cảnh; không im lặng). Viết
  `start_frame` mỗi người một vế ("Kelly frame-left, Kenta frame-right") để code đọc được. Người/Claude: storyboard liền nhau.
- **Ví dụ FF.** ✔ Chạy thử 2A (H5): hai shot cùng vị trí máy gen chung một clip → giảm 33% giây trả tiền. ✘ #6 từng shot: ~101 s trả tiền cho
  57 s phim (mỗi shot một clip tối thiểu).

### Q10. Nhân vật đúng thiết kế trong khung
- Ảnh tham chiếu chọn theo cỡ cảnh (cận → ảnh cận/chính diện; toàn → toàn thân); ảnh chuẩn chính diện là màu chuẩn. Prompt chỉ nhắc nét nhận
  diện **đúng như ảnh** (tóc, màu trang phục chính, phụ kiện) — không đoán chiều trái/phải, xuôi/ngược khi chưa nhìn ảnh (2A: đọc sai hướng mũ
  của Maxim). Khi cờ `profile_digest` bật, prompt dùng bản rút gọn hồ sơ (≤ 500 ký tự ảnh / ≤ 200 video, `core/profile_digest.py`).
- **Đạo cụ, vũ khí, tay cầm liền mạch** — lỗi phổ biến của ảnh AI vẽ rời từng shot: súng đổi tay, kiếm đổi kiểu, vòng cổ biến mất. Mỗi
  cảnh chốt một lần ở shot đầu có đạo cụ ("Kenta holds the katana in his RIGHT hand, black sheath on his left hip") rồi **chép nguyên câu**
  sang mọi shot sau của cảnh (`image_prompt` + `end_state`); đạo cụ đổi tay/rơi xuống thì ghi ở `end_state` của shot đó. Ảnh tham chiếu
  của đạo cụ trong Kho đi kèm khi có. Kiểm: QC ảnh (Claude) so với shot trước cùng nhóm (`setcheck`); người xem storyboard.
- **Hiệu ứng kỹ năng in-game** (~38% shot FF có hiệu ứng kỹ năng — `ff_directing.md` mục 8): chừa **khoảng trống phía hiệu ứng bay tới**
  (như khoảng trống phía nhìn), cỡ đủ rộng để thấy cả nguồn lẫn đích (MS/MLS/WS), máy tĩnh hoặc bám theo chậm — hiệu ứng lớn + máy rung làm
  model vẽ nhòe. Hiệu ứng là chủ thể của shot → nói rõ màu/hình theo tư liệu gameplay (không bịa hiệu ứng khác).

### Q11. Thời gian trong khung — quay chậm, dừng hình, nhòe chuyển động — 2026-09-26
- **Làm gì · vì sao.** Máy thật quay chậm bằng cách quay **nhiều khung hơn** (48–120 fps) rồi chiếu 24 fps; màn trập ~1/2 thời gian khung
  (180°) cho nhòe chuyển động tự nhiên — màn trập nhanh (hạt mưa đứng yên, pha chiến đấu giật cục) là lựa chọn phong cách [KN]. Model video
  AI không có fps/màn trập: chỉ có **chữ** trong prompt và **xử lý khi dựng**. Hai cách:
  1. Viết "slow motion" trong motion prompt — model tự vẽ chậm, nhưng không kiểm được tốc độ, có thể ra clip gần như đứng yên.
  2. **Gen tốc độ thường, kéo giãn khi dựng** (`speed` của shot, cờ `speed_ramp`): Dựng lấy (độ dài shot − dừng) × `speed` giây hành động
     rồi kéo dài bằng nội suy khung (`minterpolate`) — kiểm được, lặp lại được. **Ưu tiên cách 2**; hành động chính phải xảy ra **ngay
     đầu** clip (Q5) vì chỉ phần đầu được dùng.
  Dừng hình (`freeze_end_s`) ở khung cuối của shot — khung đó phải là tư thế đẹp nhất (ghi ở `end_state`).
- **Trong pipeline.** Shot không thoại: `speed` 0,25–0,9, `freeze_end_s` ≤ 1,5 s (code bỏ ở shot có thoại/khớp môi — `shots.clean_retime`);
  `duration_s` là độ dài **trên phim**. Chọn khoảnh khắc theo Đạo diễn Đ11 (1–2 lần mỗi phim). Nhòe chuyển động: tả bằng chữ khi cần
  ("motion blur on the swinging blade"); tránh ở shot cần nhận diện mặt.
- **Kiểm.** Code: test ffmpeg (0,75 s hành động → shot 2,0 s có 0,25 s dừng), Motion nhận `speed` để biết chỉ phần đầu clip được dùng.
  Người: bản dựng (nội suy có thể méo tay/vũ khí khi chuyển động nhanh — lý do cờ còn TẮT).
- **Ví dụ FF.** ✔ Cú bắn tỉa quyết định: MS qua vai, viên đạn rời nòng `speed: 0.4`, `freeze_end_s: 0.5` ở lúc mục tiêu ngã. ✘ Quay chậm
  cả pha đấu súng 6 shot — mất nhịp, mọi khoảnh khắc đều "quan trọng" nên không cái nào quan trọng.

### Q12. Kỹ thuật thấy trong clip mẫu ClipAI — tư liệu, không phải công thức — 2026-09-28 (sửa 2026-09-29)
Nguồn: clip mẫu ClipAI người dùng gửi 2026-09-28 (MV 201 s; `docs/PHAN_TICH_CLIP_MAU_CLIPAI_2026-09-28.md`).
> Người dùng sửa 2026-09-29: máy quay, góc, dựng, âm thanh **không có nghĩa mặc định** — cùng một kỹ thuật phục vụ nhiều ý đồ khác nhau tùy tình huống. Mục này ghi **kỹ thuật đã thấy + cách làm + ý đồ ở đúng chỗ đó**, không phải công thức. Chọn khi ý đồ của cảnh cần; ghi lý do theo tình huống (như Q1: "ý nghĩa góc không cố định").
- **Chuyển động bắt đầu từ giây 0.** Các shot của clip đều bắt đầu khi nhân vật đã đang chuyển động (đang nhảy, đang bước); nhân vật
  động gấp ~2,4 lần #8 mà vẫn mượt. Với model video: motion prompt tả động tác đang diễn ra từ khung đầu, tránh khởi động từ tư thế đứng
  yên — trừ khi sự đứng yên chính là ý đồ.
- **Đầu vào không ép dáng.** Director Workspace của ClipAI khuyên dàn cảnh bằng nhân vật hình học (trụ + cầu) vì ảnh / video dáng chi tiết
  làm Seedance bắt chước cứng tay chân (tài liệu chính thức, 15/09/2026). Ảnh storyboard dáng đứng làm khung đầu chỉ khi bố cục chính xác
  quan trọng hơn chuyển động (thử A/B ở S4.6).
- **Động tác khó đến từ chỉ đạo, không mặc định từ mẫu** (người dùng 2026-09-29). Phim dài không có sẵn mẫu hành động cho mọi cảnh —
  diễn viên hiểu cảnh rồi tự diễn cho khớp kịch bản (ngoài đời còn tập và quay thử trước). Với model video cũng vậy: trước hết là **cách
  truyền đạt** — nhân vật đang ở tình huống gì, muốn gì, vì sao hành động (động cơ, Đ4); chuỗi hành động theo nhịp (bắt đầu → giữa → kết
  thúc ở tư thế nào); chi tiết cơ thể (trọng tâm, chân chạm đất, tay, hướng nhìn); nhịp độ; và **quay thử rẻ trước** (bản mẫu 480p /
  Sample Mode, `motion_complex_shots.md`) rồi mới làm bản thật. Video tham chiếu chuyển động chỉ là **một công cụ phụ** khi động tác rất
  đặc thù (vũ đạo đồng bộ nhiều người — clip mẫu 1:00–1:02 có thể đã dùng, chưa có bằng chứng) và có sẵn / tự quay được.
- **Chuyển cảnh bằng chuyển động máy trong cùng clip** (2:20,6–2:21: máy bay lên xuyên đèn chùm rồi hạ xuống mặt bàn) — dùng ở clip cho
  lần đổi sang thế giới siêu thực.
- **Chuyển cảnh che máy có chủ ý** (người dùng giải thích 2026-09-29 — cách làm nghề, không phải "đặt sẵn shot cận vật"): chỗ nối được
  **tạo ra trong chuyển động của cảnh**: một vật hoặc người cầm vật đi ngang sát ống kính; máy lia theo vật; hay máy tiến vào một vật đến khi
  vật che kín khung — shot sau mở ra từ vật che / từ hướng lia tiếp theo. Cần thiết kế từ lúc chia shot (hành động + đường máy + khung
  cuối của shot trước khớp khung đầu shot sau), không chèn bù ở khâu dựng. Ví dụ ở clip: 1:16,3 tay lật quân Át lóe sáng giữa hai shot
  của nhân vật nữ.
- **Góc máy:** clip dùng máy thấp trong đoạn người tí hon giữa chồng phỉnh (2:31–2:47), nhìn xuống bàn (0:30–0:32), sau lưng khi đẩy cửa
  (3:07–3:12). Ý nghĩa của các góc này **ở đúng chỗ đó** do ngữ cảnh tạo ra — xem Q1 ("ý nghĩa góc không cố định").
- **Trong pipeline.** Chuyển cảnh che máy: ghi ở `transition_in` (S3.6) + tả trong motion prompt của hai shot; động tác khó: ghi rõ động cơ + chuỗi
  hành động trong `performance` / motion prompt, cần quay thử hay video tham chiếu thì ghi ở `why`.
- **Kiểm.** Người: animatic / bản dựng — chỗ nối có liền không, có lý do trong cảnh không.

## Tầng 4 — Ưu tiên khi xung đột
Giới hạn model là **luật cứng** (code kiểm, không thương lượng). Bên trong nó, cùng thang chung của cả tổ (`README.md`):
1. ý đồ và diễn xuất của Đạo diễn, gồm rõ không gian (ai ở đâu, trục, hướng) · 2. thoại nguyên văn — shot đủ dài để nói, không thấy mặt người
nói khi khớp môi tắt · 3. góc máy kịch bản ghi · 4. thời lượng kịch bản · 5. ít clip/tiền (gộp theo vị trí máy) · 6. đẹp.
Hy sinh gì thì ghi `tradeoffs`.

## Tầng 5 — Tự rà
- Mỗi cảnh có bao nhiêu vị trí máy, có vượt trục không, hướng màn hình mỗi phe có giữ không?
- Mỗi shot có `why` chưa? Chuyển động nào không có động cơ? Shot nào có hơn một chuyển động chính?
- Khung đầu có đúng MỘT khoảnh khắc không? Có chỗ cho chữ khi cần không, mặt có nằm trong vùng giao diện app không?
- Shot nào đặt máy tay/đẩy vào lên nhân vật cần giữ nhận diện? Shot nào nhân vật di chuyển mà máy lại đẩy vào?
- Ánh sáng của shot có nguồn không? Có shot thoại nào thấy rõ mặt người nói khi khớp môi đang tắt không?
- Đạo cụ/vũ khí có cùng tay, cùng kiểu ở mọi shot của cảnh không? Hiệu ứng kỹ năng có chỗ bay tới trong khung không?
- Shot nào quay chậm/dừng hình — có đúng khoảnh khắc Đạo diễn chọn, hành động có ở ngay đầu clip không?
