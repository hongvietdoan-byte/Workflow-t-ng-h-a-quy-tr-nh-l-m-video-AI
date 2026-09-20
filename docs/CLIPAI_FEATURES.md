# Tính năng Clip AI (theo tài liệu chính thức skill 1.3.1) và mức đang dùng

Nguồn: `Get this Skill to Claude/clipai-1.3.1` (SKILL.md, reference.md, 2 file tối ưu prompt Seedance). Đây là **những gì tài liệu công khai nêu**; web Clip AI có thể có thêm (chưa có tài liệu). Cập nhật 2026-09-20.

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
| 2 | Seedance 2.0 / 2.0 Fast / 2.5 image→video | 4–15 s (2.5: tới **30 s**), 480p–1080p (2.0), 4k (2.0) | **Đang dùng** | Thử 2.5 cho cảnh dài |
| 3 | Âm thanh do model tạo (`sound`, `generate_audio`) | Kling: không kèm video tham chiếu/O1; Seedance: cờ `generate_audio` | **Mới thêm (tùy chọn)** | Thử thật 1 cảnh có thoại |
| 4 | Audio tham chiếu Seedance (`reference_audio`) | ≤ 3 (2.0) / ≤ 10 (2.5), cần ảnh/video kèm | Chưa | Cách khớp môi có kiểm soát giọng — nên làm sau khi thử mục 3 |
| 5 | **Kho chủ thể Seedance (Subject Library)** | Upload ảnh/video nhân vật, qua duyệt "người thật"; **nhân vật game FF được phủ bản quyền theo thỏa thuận đã ký** → dùng `asset_uri`, ít bị risk control; AOV/DF không được phủ | **Đã làm, chưa thử thật** (game/loại nội dung chọn trong `data/games.json`; FF mặc định, có thể thêm game khác hoặc nội dung không thuộc game; mọi mục Character Bible đều gắn được): Bước 1 → "🧩 Kho chủ thể Seedance" (tải ảnh nhân vật lên kho, chờ active, hoặc nhập chủ thể đã có trên kho); Bước 4 → ô "🧩 Gắn ảnh chủ thể nhân vật vào video" | Thử thật 1 nhân vật FF; theo dõi có giảm bị chặn risk control không |
| 6 | Ảnh/video/audio tham chiếu nhiều (Seedance ≤ 9/3/3; 2.5 ≤ 30/10/10) | Vai trò `reference_image` | Chưa (chỉ 1 ảnh khung đầu) | Giữ nhất quán nhân vật qua nhiều cảnh (thêm ảnh Character Bible làm tham chiếu) |
| 7 | Khung đầu + khung cuối | 2 ảnh, vai `first_frame`/`last_frame` (Kling O1: 5 hoặc 10 s) | Chưa | Chuyển cảnh mượt giữa 2 ảnh đã duyệt |
| 8 | Multi-shot (Kling Omni) | `--multi_shot`, `multi_prompt` nhiều shot | Chưa | Cảnh nhiều góc máy trong 1 clip |
| 9 | Video tham chiếu Kling (`feature` = học chuyển động; `base` = sửa/tiếp clip) | tối đa 1 video | Chưa | Sửa clip chưa ưng thay vì gen lại từ đầu |
| 10 | Sửa video / nối dài video (Seedance 2.5) | 1 video nguồn, `duration -1`, `adaptive` | Chưa | Nối dài clip, sửa chi tiết |
| 11 | Kling elements (`element_ids`) | giữ nhân vật/đối tượng nhất quán | Chưa | Cùng mục đích với 5–6 |
| 12 | Tỉ lệ khung (21:9…9:16, adaptive) | | Có biến `CLIPAI_ASPECT_RATIO` | Video dọc cho mạng xã hội |
| 13 | **Nhạc** `music_v2` | 3–600 s, có/không lời | **Đang dùng** (Bước 5a) | — |
| 14 | **Hiệu ứng âm thanh** (SFX) | 0,5–30 s, loop | **Đang dùng** | — |
| 15 | **Giọng đọc TTS** (ElevenLabs v3, multilingual v2, turbo v2.5) | giọng chính thức/cá nhân, **lọc theo `game_code`** | **Đang dùng** (chọn giọng chính thức) | Chọn giọng theo game/nhân vật (`game_code`), ghép với mục 4 |
| 16 | Danh sách/tra cứu/xóa tác vụ, danh sách tài sản âm thanh | | Dùng để theo dõi tác vụ | — |
| 17 | Bộ tối ưu prompt Seedance 2.0 / 2.5 | quy tắc chính thức | **Đã chắt lọc** (`knowledge/seedance_prompting.md`) | — |

## Đề xuất thứ tự (cần bạn quyết)
1. **Thử thật 1 cảnh có thoại** với ô "🔊 Model tự tạo âm thanh" (Seedance hoặc Kling Omni) để xem khớp môi có đạt không — cần credit.
2. Nếu gặp **risk control** với nhân vật game: dựng **Kho chủ thể** (mục 5) — cho tôi biết game nào (FF được phủ).
3. Nếu khớp môi tự động chưa đạt: làm **audio tham chiếu** (mục 4) với giọng TTS chọn theo `game_code`.
4. Hỏi team Clip AI: có công cụ/`task_type` lip-sync riêng và endpoint giá không.
