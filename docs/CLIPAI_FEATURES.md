# Tính năng Clip AI (theo tài liệu chính thức skill 1.3.1/1.4.1) và mức đang dùng

Nguồn: `Get this Skill to Claude/clipai-1.3.1` + `Get this Skill to Claude/deepix-1.4.1` (SKILL.md, reference.md, canvas.md, 2 file tối ưu prompt Seedance, và đọc trực tiếp mã nguồn `scripts/*.mjs` khi tài liệu chữ không đủ chi tiết trường API). Đây là **những gì tài liệu + mã nguồn công khai nêu**; web Clip AI/Deepix có thể có thêm tính năng chưa tài liệu hóa. Cập nhật 2026-09-22.

## ⚠ Đối chiếu slide marketing vs tài liệu API thật (2026-09-22)

Slide nội bộ "Tài nguyên tham khảo để AI làm tốt hơn" (`Get this Skill to Claude/Tài nguyên tham khảo để AI làm tốt hơn/`) giới thiệu 6 tính năng ClipAI/Deepix. Đối chiếu từng cái với **mã nguồn API thật** (không phải suy đoán từ slide) cho kết quả:

| Tính năng trong slide | Có qua API/CLI không? | Bằng chứng |
|---|---|---|
| **Deepix Storyboard** (giữ nhân vật nhất quán qua nhiều khung) | **KHÔNG có API**, nhưng **đã có phương án thay thế trong dashboard** | `deepix-1.4.1/scripts/image.mjs` liệt kê "storyboard" trong danh sách cảnh **chỉ có trên web UI**. `canvas get` trả "storyboard frames" nhưng không có lệnh CLI nào TẠO storyboard, chỉ đọc/thao tác node-graph thô. → **Đã code:** chế độ "📽 Chế độ Storyboard" (Bước 1, cạnh World Bible) — ảnh cảnh N-1 đã duyệt được gửi kèm làm ảnh tham chiếu bổ sung khi gen ảnh cảnh N (image-to-image), giữ phong cách/ánh sáng liên tục như storyboard thật mà không cần gọi tính năng Storyboard của Deepix. Xem mục #19 dưới. |
| **Chọn model theo giá/chất lượng** | **CÓ** (đây là thông tin tĩnh, không phải API) | Đã điền vào `data/pricing.json` (`listed_usd_per_video_second`, `model_choice_guide`) — xem mục #2 dưới. |
| **Prompt khó khóa cảnh phức tạp → dựng trước bằng "Bàn đạo diễn" (ảnh người dùng gửi cho thấy đây là một tính năng THẬT trên web, có màn hình 3D đặt camera/nhân vật, xuất "Lưu vào thư viện")** | **CHƯA XÁC ĐỊNH ĐƯỢC — không có trong tài liệu skill nào, nhưng tính năng có thật trên web** | Đã grep lại đúng gói `clipai-1.3.1` (không chỉ Deepix) cho "director/stage/desk/đạo diễn": **0 kết quả** — gói skill CLI 1.3.1 hoàn toàn không nhắc tới tính năng này, nhiều khả năng được thêm vào web SAU khi gói này được đóng gói (lịch sử version chỉ tới 1.3.1, không có ngày phát hành để so sánh). Đã thử dò trực tiếp bằng token thật: `/api/openapi.json`, `/api-docs` chỉ trả lỗi 404 dạng bọc JSON (không phải spec thật); đoán mù ~10 đường dẫn khả dĩ (`/api/stage`, `/api/director`, `/api/scene`...) đều trả **cùng một** thông điệp 404 — tức bộ định tuyến có handler 404 chung cho mọi đường dẫn lạ, nên **không đoán mù thêm được nữa, kết quả đoán mù không có giá trị xác nhận**. **Kết luận: cần xem Network tab thật khi thao tác "Bàn đạo diễn" trên web (đăng nhập SSO) để lấy đúng endpoint, hoặc hỏi trực tiếp team Clip AI có gói skill mới hơn 1.3.1 không.** Xem mục "Bàn đạo diễn" cuối file. |
| **Tham chiếu video-cho-chuyển-động** (tách biệt khỏi ảnh-cho-diện-mạo) | **CÓ, đã có sẵn trong API nhưng project CHƯA DÙNG (tới hôm nay)** | Kling: `video_list: [{video_url, refer_type: "feature"\|"base", keep_original_sound}]`, field `refer_type=feature` = "tham chiếu chuyển động/phong cách → tạo clip MỚI" (đúng slide); upload qua multipart field `video_files`. Seedance: `content[]` item `{type:"video_url", video_url:{...}, role:"reference_video"}`. **Đã lập trình vào `core/adapters/clipai.py::submit()` (tham số `reference_video`) và UI Bước 3** — xem mục #18 dưới. |
| **Voice Design** (tạo giọng mới từ mô tả text) | **KHÔNG có trong contract audio hiện tại** | `clipai-1.3.1/clipai/reference.md` liệt kê đúng 3 giá trị `type` cho `audio --generate`: `tts`, `sound_effect`, `music`. Không có `voice_design` hay từ khóa tương đương ở bất kỳ đâu trong 2 gói skill. |
| **Voice Clone** (nhân bản giọng từ mẫu ghi âm) | **KHÔNG có trong contract audio hiện tại** | Tương tự — không có `voice_clone`/`clone` trong danh sách `type`, endpoint, hay tham số nào. |

**Kết luận cho Voice Design/Voice Clone:** giống hệt tình huống "lip-sync" đã ghi ở đầu file này — cần **hỏi team Clip AI** xem có endpoint/`task_type` riêng chưa tài liệu hóa không, trước khi coi là "không làm được". Không tự chế giả lập bằng cách khác (vd ghép ElevenLabs trực tiếp ngoài luồng ClipAI) vì phá vỡ việc theo dõi chi phí/quyền qua `pricing.json` và `cost.py` của dự án.

**Kết luận cho Deepix Storyboard:** không tự động hóa được tính năng Storyboard thật của Deepix (web-only), nhưng **đã tự động hóa được HIỆU QUẢ tương đương** bằng cách khác — xem "📽 Chế độ Storyboard" mục #19. Vẫn giữ gợi ý thủ công (mở Deepix Web dựng Storyboard, tải khung về làm ảnh tham chiếu nhân vật ở Bước 1) như một lựa chọn bổ sung cho ai muốn kiểm soát bố cục nhiều khung tay hơn — hai cách không loại trừ nhau.

## Khớp môi (lip-sync): kết luận
- **Không có endpoint/tham số "lip-sync" riêng** trong tài liệu API (tìm cả `lip`, `sync`, `口型`: không có). Có thể web có công cụ riêng (danh sách `task_type` 1–9 "loại khác" ghi "xem openapi.yaml", file này không có trong gói) → cần hỏi team Clip AI hoặc bạn mở web xem tên công cụ.
- **Cách đạt kết quả "nhân vật nói, khớp môi" bằng tính năng đã có tài liệu** (chưa thử thật):
  1. **Model tự tạo âm thanh + lời thoại:** Kling Omni `sound: on` (không dùng với video tham chiếu, không dùng với O1); Seedance `generate_audio`. Lời thoại ghi trong prompt (Seedance 2.5 quy ước: `{lời thoại}`, `<hiệu ứng>`, `(nhạc)`, chỉ rõ người nói, ngôn ngữ). Khớp môi do model tự làm.
  2. **Giọng có sẵn làm tham chiếu (Seedance):** ảnh khung đầu + audio tham chiếu (`reference_audio`, 2.0: ≤ 3 file; 2.5: ≤ 10, mỗi file ≤ 30 s) → nhân vật nói theo giọng đó. Giọng có thể tạo bằng TTS/giọng chọn theo game.
- **Đã làm trong Dashboard:** ô **"🔊 Model tự tạo âm thanh / lời thoại"** ở Bước 4 (mục 1; mặc định tắt vì có thể đổi giá và cần lời thoại trong motion prompt). Mục 2 chưa làm (cần chọn giọng theo cảnh).

## Danh mục tính năng
| # | Tính năng | Tài liệu nói gì | Dự án hiện tại | Giá trị / việc nên làm |
|---|---|---|---|---|
| 1 | Kling Omni image→video (`kling-v3-omni`, `kling-video-o1`) | 3–15 s, mode std/pro/4k, ảnh khung đầu | **Đang dùng** (khung đầu = ảnh đã duyệt) | — |
| 2 | Seedance 2.0 / 2.0 Fast / 2.5 image→video | 4–15 s (2.5: tới **30 s**), 480p–1080p (2.0), 4k (2.0) | **Đang dùng**; giá niêm yết USD/giây đã điền ở `data/pricing.json` (`listed_usd_per_video_second`, `model_choice_guide`) | Thử 2.5 cho cảnh dài; điền giá credit thật khi đo được (`per_video_second`) |
| 3 | Âm thanh do model tạo (`sound`, `generate_audio`) | Kling: không kèm video tham chiếu/O1; Seedance: cờ `generate_audio` | **Mới thêm (tùy chọn)** | Thử thật 1 cảnh có thoại |
| 4 | Audio tham chiếu Seedance (`reference_audio`) | ≤ 3 (2.0) / ≤ 10 (2.5), cần ảnh/video kèm | Chưa | Cách khớp môi có kiểm soát giọng — nên làm sau khi thử mục 3 |
| 5 | **Kho chủ thể Seedance (Subject Library)** | Upload ảnh/video nhân vật, qua duyệt "người thật"; **nhân vật game FF được phủ bản quyền theo thỏa thuận đã ký** → dùng `asset_uri`, ít bị risk control; AOV/DF không được phủ | **Đã làm, chưa thử thật** (game/loại nội dung chọn trong `data/games.json`; FF mặc định, có thể thêm game khác hoặc nội dung không thuộc game; mọi mục Character Bible đều gắn được): Bước 1 → "🧩 Kho chủ thể Seedance" (tải ảnh nhân vật lên kho, chờ active, hoặc nhập chủ thể đã có trên kho); Bước 4 → ô "🧩 Gắn ảnh chủ thể nhân vật vào video" | Thử thật 1 nhân vật FF; theo dõi có giảm bị chặn risk control không |
| 6 | Ảnh/video/audio tham chiếu nhiều (Seedance ≤ 9/3/3; 2.5 ≤ 30/10/10) | Vai trò `reference_image` | Chưa (chỉ 1 ảnh khung đầu) | Giữ nhất quán nhân vật qua nhiều cảnh (thêm ảnh Character Bible làm tham chiếu) |
| 7 | Khung đầu + khung cuối | 2 ảnh, vai `first_frame`/`last_frame` (Kling O1: 5 hoặc 10 s) | Chưa | Chuyển cảnh mượt giữa 2 ảnh đã duyệt |
| 8 | Multi-shot (Kling Omni) | `--multi_shot`, `multi_prompt` nhiều shot | Chưa | Cảnh nhiều góc máy trong 1 clip |
| 9 | Video tham chiếu Kling (`feature` = học chuyển động; `base` = sửa/tiếp clip) | tối đa 1 video | **Đã làm** (2026-09-22) — trùng với mục 18 | — |
| 10 | Sửa video / nối dài video (Seedance 2.5) | 1 video nguồn, `duration -1`, `adaptive` | Chưa | Nối dài clip, sửa chi tiết |
| 11 | Kling elements (`element_ids`) | giữ nhân vật/đối tượng nhất quán | Chưa | Cùng mục đích với 5–6 |
| 12 | Tỉ lệ khung (21:9…9:16, adaptive) | | Có biến `CLIPAI_ASPECT_RATIO` | Video dọc cho mạng xã hội |
| 13 | **Nhạc** `music_v2` | 3–600 s, có/không lời | **Đang dùng** (Bước 5a) | — |
| 14 | **Hiệu ứng âm thanh** (SFX) | 0,5–30 s, loop | **Đang dùng** | — |
| 15 | **Giọng đọc TTS** (ElevenLabs v3, multilingual v2, turbo v2.5) | giọng chính thức/cá nhân, **lọc theo `game_code`** | **Đang dùng** (chọn giọng chính thức) | Chọn giọng theo game/nhân vật (`game_code`), ghép với mục 4 |
| 16 | Danh sách/tra cứu/xóa tác vụ, danh sách tài sản âm thanh | | Dùng để theo dõi tác vụ | — |
| 17 | Bộ tối ưu prompt Seedance 2.0 / 2.5 | quy tắc chính thức | **Đã chắt lọc** (`knowledge/seedance_prompting.md`) | — |
| 18 | **Video tham chiếu chuyển động** (Kling `video_list`/`refer_type`; Seedance `content[].role=reference_video`) — tách biệt khỏi ảnh-cho-diện-mạo, xem mục "Đối chiếu slide" ở đầu file | Kling: 1 video, `refer_type` feature\|base, không đi kèm `sound:on`. Seedance: qua `content[]`, không phân biệt feature/base | **Đã làm (2026-09-22)**: `core/adapters/clipai.py::submit(reference_video=...)`, cột `motion_prompts.ref_video_path`/`ref_video_type`, UI Bước 3 (expander "🎥 Video tham chiếu chuyển động" dưới mỗi motion prompt) | **Chưa thử thật** — cần 1 lần chạy thật để xác nhận field `refer_type`/`role` đúng như tài liệu suy ra từ `video.mjs`; ứng dụng rõ nhất: dùng clip gameplay Free Fire thật làm tham chiếu chuyển động cho skill nhân vật (xem `knowledge/ff_character_skills_visual.md`) |
| 19 | **"Chế độ Storyboard" thay thế Deepix Storyboard** (không phải API của Deepix — dùng lại image-to-image sẵn có) | — (kỹ thuật của dự án, không phải hợp đồng ClipAI/Deepix) | **Đã làm (2026-09-22)**: cột `projects.storyboard_mode`, `Pipeline.set_storyboard_mode`, `ImageRunner._submit_args` tự thêm ảnh cảnh N-1 đã duyệt làm ảnh tham chiếu bổ sung (`core/assets.py::reference_note` có nhánh `role="previous_scene"`), UI Bước 1 cạnh World Bible | **Chưa thử thật**; chỉ nối cảnh liên tiếp theo `idx`, không phát hiện "cảnh nào thật sự tiếp nối cảnh nào" — bật/tắt bằng tay theo dự án |

## "Bàn đạo diễn" — tính năng có thật, CHƯA xác định được API (2026-09-22, cập nhật sau khi người dùng gửi ảnh chụp màn hình)

Lần rà soát đầu (bên trên, mục "Chọn model" cũ) kết luận sai vì grep nhầm cả 2 gói `clipai`+`deepix` gộp chung và bỏ sót — sau khi người dùng gửi ảnh chụp màn hình thật của "Bàn đạo diễn" (giao diện 3D: đặt camera/nhân vật, "Góc nhìn đạo diễn"/"Góc nhìn camera", nút "Lưu vào thư viện", icon xuất `</>`), đã grep lại **riêng gói `clipai-1.3.1`** cho `director|stage|desk|đạo diễn`: **0 kết quả**. Tính năng này có thật trên web nhưng gói skill CLI 1.3.1 không hề nhắc tới — khả năng cao gói skill đã cũ hơn tính năng này trên web (lịch sử version của gói dừng ở 1.3.1, không có ngày phát hành để so sánh với ngày thêm tính năng).

**Đã thử dò trực tiếp bằng token thật** (không hiển thị token ra chat): `/api/openapi.json` và `/api-docs` trên `clipai.ingarena.net` trả về lỗi 404 dạng bọc JSON (`{"code":1101,"status":"error","msg":"Http404"}`), không phải spec thật. Đoán mù ~10 đường dẫn khả dĩ (`/api/stage`, `/api/director`, `/api/scene`, `/api/blocking`, `/api/previs`, `/api/storyboard`, `/api/director-desk`, `/api/3d-stage`, `/api/canvas3d`, `/api/kling/stage`) **đều trả về đúng cùng một thông điệp 404** — chứng tỏ backend có handler bắt-mọi-đường-dẫn-lạ, nên kết quả đoán mù **không xác nhận cũng không loại trừ** được gì. Trang chủ `clipai.ingarena.net` yêu cầu đăng nhập Garena/Space SSO mà tôi không có, nên không vào được chính giao diện "Bàn đạo diễn" để xem Network tab.

**Cách xác nhận đáng tin cậy duy nhất còn lại (cần bạn):**
1. Mở "Bàn đạo diễn" trên web (đã đăng nhập), mở DevTools (F12) → tab Network, thao tác vài bước (đặt camera, lưu vào thư viện) → chụp lại các request (đặc biệt request khi bấm "Lưu vào thư viện" và icon `</>` — icon đó rất có thể là "xuất JSON/code" ngay trong UI, thử bấm nó trước) → gửi URL + payload cho tôi, tôi viết adapter dựa trên đó.
2. Hoặc hỏi thẳng team Clip AI có gói skill mới hơn 1.3.1 (có thể đã thêm "Bàn đạo diễn" vào tài liệu) không — gộp chung với câu hỏi Voice Design/Voice Clone/lip-sync đã có sẵn ở trên.

**Trong lúc chờ xác nhận, vấn đề gốc mà "Bàn đạo diễn" giải quyết** (prompt chữ không khóa được quan hệ không gian trong cảnh quay phức tạp) **đã có giải pháp khác trong dự án**: `knowledge/motion_complex_shots.md` (gắn vào Bước 3) giải quyết bằng cách **khóa không gian và chia nhịp bằng chữ**, cộng thêm mục "Khi chữ vẫn không đủ" (dùng video tham chiếu chuyển động, mục 18) — hai cách không loại trừ nhau và không cần chờ xác nhận API.

## Đề xuất thứ tự (cần bạn quyết)
1. **Mở "Bàn đạo diễn" trên web + chụp Network tab** — cách nhanh nhất để biết có tích hợp được không, xem hướng dẫn ở mục ngay trên.
2. **Thử thật video tham chiếu chuyển động** (mục 18, đã code xong) — 1 cảnh dùng clip gameplay FF thật, xác nhận API nhận đúng `refer_type`/`role`.
3. **Thử thật Chế độ Storyboard** (mục 19, đã code xong) — bật ở Bước 1, gen 2-3 cảnh liên tiếp, xem ảnh có giữ phong cách liên tục hơn không.
4. **Thử thật 1 cảnh có thoại** với ô "🔊 Model tự tạo âm thanh" (Seedance hoặc Kling Omni) để xem khớp môi có đạt không — cần credit.
5. Nếu gặp **risk control** với nhân vật game: dựng **Kho chủ thể** (mục 5) — cho tôi biết game nào (FF được phủ).
6. Nếu khớp môi tự động chưa đạt: làm **audio tham chiếu** (mục 4) với giọng TTS chọn theo `game_code`.
7. Hỏi team Clip AI: có công cụ/`task_type` lip-sync riêng, **Voice Design**, **Voice Clone**, gói skill mới hơn cho **"Bàn đạo diễn"** chưa tài liệu hóa không, và giá thật (credit) cho từng model video.
