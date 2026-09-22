# Tính năng Clip AI (theo tài liệu chính thức skill 1.3.1/1.4.1) và mức đang dùng

Nguồn: `Get this Skill to Claude/clipai-1.3.1` + `Get this Skill to Claude/deepix-1.4.1` (SKILL.md, reference.md, canvas.md, 2 file tối ưu prompt Seedance, và đọc trực tiếp mã nguồn `scripts/*.mjs` khi tài liệu chữ không đủ chi tiết trường API). Đây là **những gì tài liệu + mã nguồn công khai nêu**; web Clip AI/Deepix có thể có thêm tính năng chưa tài liệu hóa. Cập nhật 2026-09-22.

## ⚠ Đối chiếu slide marketing vs tài liệu API thật (2026-09-22)

Slide nội bộ "Tài nguyên tham khảo để AI làm tốt hơn" (`Get this Skill to Claude/Tài nguyên tham khảo để AI làm tốt hơn/`) giới thiệu 6 tính năng ClipAI/Deepix. Đối chiếu từng cái với **mã nguồn API thật** (không phải suy đoán từ slide) cho kết quả:

| Tính năng trong slide | Có qua API/CLI không? | Bằng chứng |
|---|---|---|
| **Deepix Storyboard** (giữ nhân vật nhất quán qua nhiều khung) | **KHÔNG** | `deepix-1.4.1/scripts/image.mjs` liệt kê "storyboard" trong danh sách cảnh **chỉ có trên web UI**, cùng nhóm với "style transfer / three-view character / resize / sticker / comic / ad localization / font design / character design" — script nói thẳng "use the Deepix web UI". `canvas get` có trả "storyboard frames" nhưng không có lệnh CLI nào tạo storyboard mới, chỉ đọc/thao tác node-graph thô qua Operations API (create_node/connect_nodes...) — dựng storyboard qua đường này tương đương viết lại tính năng web từ đầu, không thực tế. |
| **Chọn model theo giá/chất lượng** | **CÓ** (đây là thông tin tĩnh, không phải API) | Đã điền vào `data/pricing.json` (`listed_usd_per_video_second`, `model_choice_guide`) — xem mục #2 dưới. |
| **Prompt khó khóa cảnh phức tạp → dựng trước bằng "Bàn đạo diễn 3D" (Blockout Blender)** | **KHÔNG tìm thấy trong tài liệu/API ClipAI hay Deepix** | Grep toàn bộ `clipai-1.3.1` và `deepix-1.4.1` (SKILL.md, reference.md, canvas.md, mọi `.mjs`) không có bất kỳ chữ "3D"/"blockout"/"director desk"/"bàn đạo diễn" nào. Đây **không phải một API/sản phẩm của ClipAI** để tích hợp — nhiều khả năng slide đang nói tới kỹ thuật thủ công "dùng Blender dựng block-out 3D thô để khóa góc máy trước khi viết prompt", không phải tính năng có thể gọi tự động. Xem phần "Kết luận: có nên tích hợp Bàn đạo diễn 3D?" cuối file. |
| **Tham chiếu video-cho-chuyển-động** (tách biệt khỏi ảnh-cho-diện-mạo) | **CÓ, đã có sẵn trong API nhưng project CHƯA DÙNG (tới hôm nay)** | Kling: `video_list: [{video_url, refer_type: "feature"\|"base", keep_original_sound}]`, field `refer_type=feature` = "tham chiếu chuyển động/phong cách → tạo clip MỚI" (đúng slide); upload qua multipart field `video_files`. Seedance: `content[]` item `{type:"video_url", video_url:{...}, role:"reference_video"}`. **Đã lập trình vào `core/adapters/clipai.py::submit()` (tham số `reference_video`) và UI Bước 3** — xem mục #18 dưới. |
| **Voice Design** (tạo giọng mới từ mô tả text) | **KHÔNG có trong contract audio hiện tại** | `clipai-1.3.1/clipai/reference.md` liệt kê đúng 3 giá trị `type` cho `audio --generate`: `tts`, `sound_effect`, `music`. Không có `voice_design` hay từ khóa tương đương ở bất kỳ đâu trong 2 gói skill. |
| **Voice Clone** (nhân bản giọng từ mẫu ghi âm) | **KHÔNG có trong contract audio hiện tại** | Tương tự — không có `voice_clone`/`clone` trong danh sách `type`, endpoint, hay tham số nào. |

**Kết luận cho Voice Design/Voice Clone:** giống hệt tình huống "lip-sync" đã ghi ở đầu file này — cần **hỏi team Clip AI** xem có endpoint/`task_type` riêng chưa tài liệu hóa không, trước khi coi là "không làm được". Không tự chế giả lập bằng cách khác (vd ghép ElevenLabs trực tiếp ngoài luồng ClipAI) vì phá vỡ việc theo dõi chi phí/quyền qua `pricing.json` và `cost.py` của dự án.

**Kết luận cho Deepix Storyboard:** không tự động hóa được trong dashboard. Việc "áp dụng vào Dashboard" cho mục này là **ghi chú quy trình thủ công**: trước khi vào Bước 1 (chọn tài nguyên) của dự án có nhiều cảnh cùng 2+ nhân vật tương tác liên tục, khuyến khích người dùng mở Deepix Web → dựng Storyboard thủ công → tải các khung đã duyệt xuống → dùng làm ảnh input cho "🖼 Ảnh tham chiếu của từng nhân vật" ở Bước 1 (đã có sẵn trong `character_reference_panel`). Đây là gợi ý quy trình, không phải nút bấm mới trong code.

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

## Kết luận: có nên tích hợp "Bàn đạo diễn 3D" (Blockout Blender)?

**Không tích hợp — không có gì để tích hợp.** Đã rà toàn bộ tài liệu + mã nguồn API của cả `clipai-1.3.1` và `deepix-1.4.1` (SKILL.md, reference.md, canvas.md, mọi file `.mjs`): không có sản phẩm/endpoint nào tên "Bàn đạo diễn 3D", "3D director desk", hay "Blockout Blender" thuộc ClipAI/Deepix. Dòng chữ nhỏ "Blockout Blender" ở góc slide nhiều khả năng chỉ là **gợi ý kỹ thuật thủ công** (dùng phần mềm Blender bên ngoài để dựng block-out 3D thô — vị trí nhân vật, đường đi máy quay — trước khi viết prompt cho model video), không phải một dịch vụ có API để gọi tự động.

Vấn đề gốc mà slide nêu (prompt chữ không khóa được quan hệ không gian trong cảnh quay phức tạp — tỷ lệ, vị trí, đường đi máy quay, thời điểm hành động) **đã có giải pháp khác trong dự án**: `knowledge/motion_complex_shots.md` (gắn vào Bước 3, xem `core/knowledge.py` GROUPS["motion"]) giải quyết cùng vấn đề bằng cách **khóa không gian và chia nhịp bằng chữ** (không cần dựng 3D) — ví dụ chia "giai đoạn" thay vì mốc giây, whip pan đúng chỗ. Hai cách tiếp cận không loại trừ nhau, nhưng vì không có API để nối, việc "tích hợp" khả thi duy nhất là **thủ công**: nếu một cảnh thật sự quá phức tạp mà cách viết chữ trong `motion_complex_shots.md` vẫn không đủ, người dựng cảnh có thể tự dựng block-out thô trong Blender (hoặc bất kỳ phần mềm 3D nào), chụp vài khung hình từ góc máy dự kiến, rồi dùng ảnh đó làm **thêm 1 ảnh tham chiếu** khi viết motion prompt (Seedance đã hỗ trợ nhiều ảnh tham chiếu, mục 6) — không cần thay đổi code, chỉ là một cách dùng tính năng đã có.

## Đề xuất thứ tự (cần bạn quyết)
1. **Thử thật video tham chiếu chuyển động** (mục 18, vừa code xong) — 1 cảnh dùng clip gameplay FF thật, xác nhận API nhận đúng `refer_type`/`role`.
2. **Thử thật 1 cảnh có thoại** với ô "🔊 Model tự tạo âm thanh" (Seedance hoặc Kling Omni) để xem khớp môi có đạt không — cần credit.
3. Nếu gặp **risk control** với nhân vật game: dựng **Kho chủ thể** (mục 5) — cho tôi biết game nào (FF được phủ).
4. Nếu khớp môi tự động chưa đạt: làm **audio tham chiếu** (mục 4) với giọng TTS chọn theo `game_code`.
5. Hỏi team Clip AI: có công cụ/`task_type` lip-sync riêng, **Voice Design**, **Voice Clone** chưa tài liệu hóa không, và giá thật (credit) cho từng model video.
