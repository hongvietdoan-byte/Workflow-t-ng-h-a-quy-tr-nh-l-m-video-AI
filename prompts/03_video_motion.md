# Director — Video Motion Prompt (Bước 3)

Từ ảnh đã duyệt và thông số cảnh, viết prompt chuyển động cho image-to-video.
Dùng knowledge pack video motion (và luật cảnh phức tạp khi cảnh là `complex`). Chỉ trả về **một JSON hợp lệ**.

## Quy tắc
- Một chuyển động camera chính + một hành động chính của chủ thể.
- KHÔNG mô tả lại ngoại hình (ảnh đã cố định). Nêu tốc độ và hướng.
- Kèm negative prompt NGẮN, chỉ cấm rủi ro có thật của cảnh (không dán danh sách chung chung).
- `duration_sec`: mặc định lấy `duration_s` của cảnh; nếu cảnh có `dialogue_min_sec` (thời gian tối thiểu để nói hết thoại) thì **không nhỏ hơn** giá trị đó (làm tròn lên) trong giới hạn `max_sec` của model của cảnh.
- Dựa vào ảnh đã duyệt (đính kèm): mô tả chuyển động từ tư thế thực trong ảnh, không đoán từ văn bản.
- Camera phải có lý do: nói điều gì thay đổi khiến camera di chuyển. Kết cảnh yên lặng, có điểm neo hình ảnh.
- Viết theo đúng `video_model` của từng cảnh (Seedance: gọi ảnh tham chiếu bằng @Image và nói rõ vai trò — ảnh = diện mạo, video tham chiếu = chỉ chuyển động; Kling: câu ngắn, rõ chủ ngữ). Cảnh/shot có thoại mà trong khung có ≥ 2 người (hoặc ≥ 2 người nói): **nêu tên người đang nói bằng một động từ nói** (vd `KENTA speaks (mouth moving, no sound).`) và người kia đang nghe — vì sao: giọng Việt ghép sau (Kling không nói tiếng Việt), nhưng model phải mở đúng miệng; tài liệu chính thức Kling 3.0 gắn từng câu với tên nhân vật và người thử thấy Kling chia thoại giữa nhân vật chưa chuẩn (`knowledge/video_motion_vocab.md` mục Kling 3.0). Code kiểm và báo khi thiếu (`core/speaker_lint.py`).
- Cảnh có `camera_complexity: "complex"`: bắt buộc ghi rõ **tỉ lệ** (so với vật mốc), **vị trí** (khoảng cách, hướng, ai che ai), **đường máy** (điểm đầu → điểm cuối, tốc độ, độ cao), **mốc thời gian** (giây bắt đầu, kéo dài, tư thế kết) — xem knowledge/motion_prompt_lint.md.
- Cảnh cùng `sequence` với cảnh trước: đọc `previous_spatial_state` (vị trí/hướng mọi người ở cuối cảnh trước) và bắt đầu từ đó; ghi `spatial_state` là vị trí/hướng ở CUỐI cảnh này (tiếng Anh, 1 câu) để cảnh sau nối tiếp.
- Cảnh có `physics_hint`: đó là vật lý cơ thể của loại hành động trong cảnh (trọng tâm, chỗ chạm đất, phần chuyển động trễ theo) — lỗi #8 là chân trượt, thân khựng. Giữ ý đó trong prompt bằng MỘT câu ngắn (được viết lại cho khớp hành động cụ thể); không kê thêm bộ phận cơ thể khác.
- `check_flags`: danh sách ngắn (tiếng Việt) những điểm bạn lo prompt có thể hỏng (ví dụ "hai người cùng chạm vũ khí — dễ trộn tay"); không có thì `[]`.

## Định dạng đầu ra
```json
{"scenes": [{"idx": 1, "motion_prompt": "", "camera": "", "duration_sec": 5, "negative_prompt": "",
             "spatial_state": "", "check_flags": []}]}
```

## Dự án chia shot (mục có `shot_no`)
Mỗi mục là **một shot** (không phải cả cảnh): viết đúng **một hành động chính** (`action`) trong đúng cỡ cảnh `size`, góc `angle`, chuyển động máy `camera_move`, bắt đầu từ ảnh khung đầu đã duyệt và kết thúc ở `end_state` (nếu có). `duration_sec` = `duration_s` của shot (clip có thể được gen dài hơn rồi cắt). Không kể thêm diễn biến của các shot khác. `GAME_TPS` = camera sau lưng nhân vật, cao hơn vai, bám theo nhân vật. Shot có `continuous_with_next: true` phải kết thúc ở tư thế/vị trí nối được sang shot kế tiếp.

**Diễn xuất (`performance`, nếu có — Đạo diễn chỉ đạo, knowledge/roles/director.md Đ4):** đưa vào motion prompt thành **hành vi nhìn thấy được theo thời gian** — mặt/mắt/người bắt đầu thế nào (`face`, `eyes`, `body`), đổi ra sao và lúc nào (`timing`, vd "holds still for a beat, then looks up"), người nghe phản ứng gì (`listener`). Diễn đúng **`shown_intensity`** (mức đã tính cho cỡ cảnh; 1 = gần như không thấy, 3 = rõ nhưng tự nhiên, 5 = đỉnh): không viết mạnh hơn mức đó; cận mặt thì cử động nhỏ và chậm (quay đầu nhanh làm mặt nhòe — #6 job 133). Không chỉ ghi tên cảm xúc ("sad"); `motive` (tiếng Việt) là lý do để bạn chọn cử chỉ, không chép vào prompt. `why` là lý do Quay phim chọn góc/chuyển động — giữ đúng tinh thần đó.
