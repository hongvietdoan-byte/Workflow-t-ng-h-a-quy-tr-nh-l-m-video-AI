# Vai Quay phim (DP) — bộ kỹ năng nghề (V4 GĐ4, 2026-09-25 — chờ người dùng duyệt rồi bật `film_crew`)

> Quay phim nhận **ý đồ** của Đạo diễn (nhịp, `emotional_intent`, `performance`, thoại) và biến thành **shot**: cỡ cảnh, góc, ống kính,
> chuyển động máy, bố cục, ánh sáng, vị trí máy, prompt khung đầu. Không đổi thoại, không đổi ý đồ. Mỗi shot ghi **`why`** để Đạo diễn duyệt.
> Mỗi kỹ năng: **Làm gì · vì sao** — **Trong pipeline** — **Kiểm** — **Ví dụ FF**. Nguồn: `knowledge/sources.md` mục GĐ4 (số [Qn]).
> Số liệu FF: 519 shot của 19 video Free Fire (`ff_directing.md`); dữ liệu chạy thật: lý do QC trả clip ở CSDL (job #).

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
- **Trong pipeline.** `size` ∈ ECU/CU/MCU/MS/WS/EWS/GAME_TPS; `angle` ∈ eye/low/high/overhead/dutch/ots/pov (giá trị lạ bị trả lại — mỗi
  lần là một lần hỏi lại trả tiền). GAME_TPS luôn `angle: "high"`. Code dịch cỡ cảnh thành câu khung hình (`framing_sentence`).
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
  | MS | 35 | 54° / 32° | quan hệ, cử chỉ, hai người |
  | MCU | 50 | 40° / 23° | thoại, cảm xúc tự nhiên |
  | CU | 65 | 31° / 18° | cảm xúc |
  | ECU | 85 | 24° / 14° | mắt, chi tiết |

  Khung dọc hẹp theo chiều ngang: muốn rộng ngang như "35 mm" của khung 16:9 cần ~18–20 mm.
- **Trong pipeline.** `lens_mm` (14–200) khi muốn khác mặc định: 24 mm đặt gần = anh hùng/ngợp; 85–135 mm = nén, cô lập, rình rập. Máy ảo giữ
  **cỡ người trong khung** và tự lùi/tiến máy theo tiêu cự → nền đổi độ nén đúng như máy thật. Không có nền 3D thì ghi ống kính bằng chữ trong
  `image_prompt` ("shot on a 24mm lens, close") — model ảnh chỉ nghe theo chữ.
- **Kiểm.** Code: `plate_camera.camera_for` (hộp nhân vật trong khung, khoảng cách máy); test hình học. Người: xem ảnh nền render.
- **Ví dụ FF.** ✔ Tháp Đồng Hồ #263 shot 4 (MS, 35 mm): tháp chiếm nửa khung phía sau Kelly. ✘ Shot cận ở chân tháp với 65 mm chỉ thấy chân
  tháp — muốn thấy mốc thì hạ máy + ngửa (góc thấp) hoặc lùi ra trung (Q6).

### Q3. Bố cục (khung dọc 9:16)
- **Làm gì · vì sao.** Mỗi khung **một trung tâm chú ý**; 1/3; chiều sâu tiền–trung–hậu (không gian sâu = cường độ cao, phẳng = thấp [Q25]);
  đường dẫn, khung trong khung, khoảng trống âm (người nhỏ giữa khoảng trống = cô độc) [Q1][Q5]. Khoảng trống phía nhìn/phía đi; khoảng
  trống trên đầu vừa đủ. **Khung dọc** mạnh ở chiều cao (toàn thân, mặt cận, công trình đứng), yếu ở hai người đứng ngang → xếp người theo
  **chiều sâu** (qua vai) thay vì cạnh nhau; mắt nhân vật ở khoảng 30–35% từ mép trên [Q29] (nguồn cộng đồng), và **không nằm trong 15% trên**
  (thanh giao diện app) — luật là **mắt**, đỉnh đầu được phép chạm thanh. Máy ảo đặt mắt ở ~20% (MLS), ~23% (MS), ~28% (MCU), ~33% (CU)
  (đo bằng `camera_for` + chiếu điểm, `plate_camera.HEADROOM`; sửa ở GĐ4: trước đó mắt MS ở ~14%, lọt vào thanh).
- **Trong pipeline.** `start_frame`: vị trí người (trái/giữa/phải, tiền/hậu cảnh, hướng mặt) — máy ảo đọc "frame-left/right" để đặt người.
  **Chừa chỗ cho chữ**: dải trên (thông báo game) hoặc dải dưới của vùng an toàn (phụ đề) — `knowledge/editor/safe_zones.md`; vùng giao diện
  app (trên 15%, dưới 35% — code dùng 36% để có đệm —, phải 18%) không đặt mặt/hành động chính.
- **Kiểm.** Code: dò mặt YuNet trên khung thật để dời phụ đề (`text_placement`); hộp nhân vật của máy ảo. Người/Claude: storyboard.
- **Ví dụ FF.** ✔ #7 giây 13 và 17: mặt xuống tới 61–65% khung → code dời phụ đề lên dải trên. ✘ Chạy thử 2A shot 4: prompt kể "nói rồi quay
  lưng bước đi" → model vẽ **hai khung ghép** trong một ảnh (sửa: "one single frame, one moment only").

### Q4. Giới hạn model (sinh từ `data/provider_rules.json` — code kiểm trước khi gửi)
<!-- model_rules -->
- Kling multi-shot: chỉ ảnh đầu nhóm bám nhân vật (shot sau trong nhóm dễ lệch — GĐ6 R4). Seedance chặn "giống người thật/bản quyền".
- GPT Image 2.5 Sunburst nhận bảng thiết kế nhiều góc; không ghi tuổi dưới 18 (bị từ chối — code lọc).

### Q5. Chuyển động máy
- **Làm gì · vì sao.** Máy chỉ chuyển động khi có **động cơ trong truyện**: đi theo hành động, hé lộ thông tin, hay đẩy cảm xúc [Q35]. Đẩy vào
  chậm = lại gần cảm xúc; lùi ra = tiết lộ/buông; cầm tay = tức thời, căng; steadicam/gimbal = trôi theo người đi-nói; cần cẩu = đổi độ cao,
  mở bối cảnh; vòng cung = khoe/nhấn; lia nhanh = chuyển cảnh; dolly zoom = choáng, chợt nhận ra (ASC [Q20], Veo [Q3]). Ghi **điểm đầu →
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
- **Kiểm.** Người/Claude đọc. *Chưa có code:* sơ đồ vị trí máy vẽ tự động từ `camera_setup` (việc code V4 trong README).
- **Ví dụ FF.** ✔ "Qua vai Kenta: người xem đứng phía anh, thấy Kelly cố cười — giữ trục như shot 1." ✘ "Góc đẹp."

### Q8. Ánh sáng
- **Làm gì · vì sao.** Đèn chính (key), đèn phụ (fill), đèn viền (back) [Q27]; **ánh sáng có nguồn**: hướng, màu, cường độ khớp một nguồn thật
  trong cảnh (mặt trời của nền 3D, đèn đường, lửa). Tỉ lệ key:fill ~1:1–2:1 = tông cao, tươi; 4:1 = có khối; ≥ 8:1 = tông thấp, bí ẩn
  (nguồn thứ cấp [Q27], các nguồn lệch nhau ở mốc tông cao). Nhiệt độ màu: ngày 5600 K, u ám 6500–7500 K, đèn sợi đốt ~2700 K, đèn natri ~1700–2100 K [Q28]; đêm trăng trên
  phim được **đẩy xanh lạnh theo quy ước** (trăng thật ấm hơn) — là lựa chọn phong cách.
- **Bảng tham chiếu ánh sáng cho Đạo diễn** (mục 4.2 B7): trường cảnh `lighting` viết theo mẫu cố định *nguồn — phía — màu K — tỉ lệ —
  tông*, vd `"moonlight from frame-right (cold, ~7000K look), sodium street lamp behind as rim (~2000K), key:fill 8:1, low-key"` — mọi shot
  của cảnh kế thừa cùng một bảng, nên hướng sáng không đổi giữa các shot.
- **Trong pipeline.** Cảnh `lighting`, `time`; shot `weather`. Nền 3D: `plate_env` đặt mặt trời/màu theo giờ + thời tiết và **cùng một độ chỉnh
  màu** cho nhân vật (`composite`); prompt phông xanh ghi hướng sáng theo máy (`location_pack.green_prompt`). Không có nền 3D: tả nguồn sáng
  bằng chữ trong `image_prompt` ("warm sodium street light from frame-left, cold moonlight rim").
- **Kiểm.** Code: `composite.match_colour`/`light_wrap`. Người: ảnh ghép có "dính" nền không.
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
- **Kiểm.** Code: `same_framing` (chỉ nối ảnh shot trước khi cùng khung), `end_frames`. *Chưa có code:* kiểm trục/hướng màn hình từ
  `start_frame` (việc code V5). Người/Claude: storyboard liền nhau.
- **Ví dụ FF.** ✔ Chạy thử 2A (H5): hai shot cùng vị trí máy gen chung một clip → giảm 33% giây trả tiền. ✘ #6 từng shot: ~101 s trả tiền cho
  57 s phim (mỗi shot một clip tối thiểu).

### Q10. Nhân vật đúng thiết kế trong khung
- Ảnh tham chiếu chọn theo cỡ cảnh (cận → ảnh cận/chính diện; toàn → toàn thân); ảnh chuẩn chính diện là màu chuẩn. Prompt chỉ nhắc nét nhận
  diện **đúng như ảnh** (tóc, màu trang phục chính, phụ kiện) — không đoán chiều trái/phải, xuôi/ngược khi chưa nhìn ảnh (2A: đọc sai hướng mũ
  của Maxim). Khi cờ `profile_digest` bật, prompt dùng bản rút gọn hồ sơ (≤ 500 ký tự ảnh / ≤ 200 video, `core/profile_digest.py`).

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
