# Ghi chú API Deepix và Clip AI (tổng hợp từ skill chính thức, 2026-09-19)

Nguồn: skill `deepix 1.4.1` và `clipai 1.3.1` do team nền tảng cung cấp (thư mục "Get this Skill to Claude", **không đưa vào git**). Đây là tóm tắt bằng lời của dự án để phiên khác không cần mở lại thư mục đó. Adapter tương ứng: `core/adapters/`.

## Chung
- Xác thực: `Authorization: Bearer <token>`. Token lấy từ giao diện web (Clip AI: avatar → API Token; Deepix: sidebar Profile → Deepix Token). **Chỉ đặt trong biến môi trường** `CLIPAI_TOKEN`, `DEEPIX_TOKEN`; không commit, không in ra log, không gửi tới host tải kết quả.
- Phong bì phản hồi không thống nhất: thành công khi `code` vắng/0/200 **và** `status` vắng/`success`/`ok`. Lỗi ở `msg` hoặc `message`.
- Biến tùy chọn: `CLIPAI_API_BASE` (mặc định `https://clipai.ingarena.net`), `DEEPIX_API_BASE` (mặc định `https://deepix.ingarena.net`).
- Lỗi HTTP: 401 = token sai; 403 không có JSON của Deepix thường là whitelist mạng chặn; 413 = ảnh tham chiếu >10 MB.

## Deepix (gen ảnh)
| Việc | Endpoint |
|---|---|
| Tạo ảnh | `POST /api/image-generator/conversation-create` (multipart) |
| Trạng thái | `GET /api/image-generator/message-status?message_id=<msg_id>` |
| Lịch sử | `GET /api/image-generator/message-list` |
| Cắt nền | `POST /ai/birefnet/predict` |
- `prompts` là **chuỗi JSON** `[{"key":"positive_prompt","text":"..."}]`; `prompt_key` 2 = text-to-image, 1 = image-to-image; ảnh tham chiếu ở trường `file[]` (có ngoặc vuông), mỗi ảnh ≤ 10 MB, JPG/PNG/WebP.
- Dùng `data.msg_id` (không phải `data.id`) để poll; trạng thái ở `data.status` (completed/failed/…), URL ảnh ở `data.image_url`. Khuyến nghị poll 3–5 giây, tối đa ~60 lần.
- Model mặc định `dola-seedream-5-0-pro-260628` (Seedream 5.0 Pro, tối đa 10 ảnh tham chiếu, `n` 1/2/4). Kích thước là **chuỗi pixel** `WxH` (cạnh chia hết 16, tỉ lệ ≤ 16:1, tổng pixel 921.600–4.624.220). Dự án dùng mặc định `2048x1152` (16:9). Model Gemini/Nano dùng chuỗi tỉ lệ (`16:9`), GPT dùng pixel riêng — không dùng chéo.
- Không có endpoint hủy tác vụ ảnh. Không tự động retry khi lỗi (mỗi lần tạo tốn credit).

## Clip AI (gen video, âm thanh)
Clip AI là cổng vào Kling và Seedance; phản hồi khác API gốc.
| Việc | Endpoint |
|---|---|
| Tạo video Kling Omni | `POST /api/kling/omni-video-submit` (multipart: `ctx` JSON + `image_files`) |
| Tạo video Seedance | `POST /api/kling/seedance-video-submit` (multipart) |
| Danh sách/tra cứu | `GET /api/kling/video-list` (`pageSize` viết hoa S; `task_type` 6 = Omni, 8 = Seedance) |
| Xóa | `POST /api/kling/video-delete` body `{id:<số nguyên>}` (id số của dòng, không phải task_id) |
| Âm thanh | `POST /api/sound/generate` (tts / sound_effect / music), `GET /api/sound/audio-list`, `GET /api/sound/voice-actors` |
| Thư viện chủ thể Seedance | `.../seedance-user-asset-*` |
- **Model chuẩn:** `kling-v3-omni` (mặc định), `kling-video-o1`, `dreamina-seedance-2-0-260128`, `dreamina-seedance-2-0-fast-260128`, `dreamina-seedance-2-5-260628`. Không dùng tên `doubao-*`. **MiniMax không có trong hợp đồng API này.**
- Không có endpoint truy vấn một tác vụ: phải quét trang đầu `video-list`. `task_status` ở danh sách là **số** (0 gửi, 1 xử lý, 2 thành công, 3 lỗi, 4 chờ); ở phản hồi tạo là **chuỗi**. URL video ở trường `video_url` cấp trên cùng.
- **Seedance có thể trả `code:0` nhưng tác vụ bên trong đã `failed`** (lý do trong `task_status_msg`) → phải kiểm tra `data.tasks[0].task_status`.
- Kling: `prompt` ≤ 2500 ký tự; `duration` là **chuỗi** (3–15 giây, không có video tham chiếu); `mode` std=720p / pro=1080p / 4k; `aspect_ratio` 16:9|9:16|1:1; ảnh khung đầu qua `image_list` (`type: first_frame`, `image_url` rỗng khi tải file lên cùng lệnh); `multi_shot` là số 0/1.
- Seedance: prompt ≤ 4000 (2.0) / 5000 (2.5) ký tự; `duration` là **số nguyên** 4–15 (2.5: 4–30) hoặc -1 (tự động); `resolution` 480p/720p (1080p/4k chỉ Seedance 2.0 thường); `ratio` gồm 16:9, 9:16, adaptive…; ảnh khung đầu là phần tử `content` với `role: first_frame`.
- **Không có trường negative prompt** trong hợp đồng công khai → adapter mặc định không gửi (`CLIPAI_NEGATIVE=append` để nối "Avoid: …" vào prompt; cần thử thực tế).
- Skill chính thức yêu cầu **tối ưu prompt Seedance theo tài liệu riêng của từng phiên bản** (2.0 và 2.5) trước khi gửi; xem `TODO.md`.
- Audio: bất đồng bộ (tạo trả `asset_id`, sau đó poll `audio-list` theo `category` tới `status=success` và có `url`); TTS cần `voice_actor_id` số của Clip AI; mặc định `eleven_v3` (TTS), `eleven_text_to_sound_v2` (SFX), `music_v2` (nhạc); `text`/`prompt` ≤ 2000 ký tự. Chưa có adapter audio.
- Bản quyền/kiểm duyệt: chủ thể Seedance `active` coi như đã qua duyệt người thật; game FF có thỏa thuận bản quyền, các game khác thì chưa (vẫn có thể bị chặn bản quyền).

## Cấu hình chạy (PowerShell, chỉ trong phiên hiện tại)
```
$env:VIDEO_PROVIDER = "clipai"; $env:CLIPAI_TOKEN = "<token của bạn>"
$env:IMAGE_PROVIDER = "deepix"; $env:DEEPIX_TOKEN = "<token của bạn>"
py -m core.adapters.check            # kiểm tra kết nối (chỉ đọc, không tốn credit)
py -m streamlit run dashboard/app.py
```
