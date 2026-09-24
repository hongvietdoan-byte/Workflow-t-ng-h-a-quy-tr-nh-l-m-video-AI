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
- **ClipAI có thể trả `task_id` mà KHÔNG tạo task** (đo 2026-09-24: 16 task Kling bị đánh "not found" không có trong toàn bộ danh sách 136 task của tài khoản; dồn vào lúc chạy nhiều dự án/đang bị giới hạn tốc độ). Code: dò trạng thái quét 3 trang (`CLIPAI_STATUS_PAGES`), một lần đọc danh sách dùng chung cho mọi job trong 5s (`CLIPAI_LIST_TTL`); task chưa từng thấy sau 6 lần dò = `not_created` → bỏ khỏi sổ chi, giảm số job đồng thời, gửi lại ngay không tính lượt thử (tối đa 3 lần liền, sau đó dừng shot).
- Trường `cost` trong danh sách: task Kling hỏng vì prompt > 512 ký tự vẫn ghi `cost=90`; task Seedance bị chặn bản quyền ghi `cost=0`.
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
py -m core.adapters.trial --yes      # thử thật 1 ảnh + 1 clip (TỐN CREDIT); thêm --model seedance để thử Seedance
py -m streamlit run dashboard/app.py
```

## Kết quả chạy thật đầu tiên (2026-09-19, `core.adapters.trial`)
- **Deepix** (Seedream 5.0 Pro, `2048x1152`): xong sau ~31 giây. Ảnh đúng prompt (người mặc áo choàng đỏ, núi sương, ánh bình minh viền vàng), chất lượng cao. **File trả về thực chất là JPEG** (~290 KB) dù ta lưu đuôi `.png` → adapter Clip AI nay gửi tên/định dạng đúng theo nội dung.
- **Clip AI** (`kling-v3-omni`, mode `pro`, 16:9, 5 giây, ảnh khung đầu): xong sau ~84 giây (poll 10 giây/lần). Kết quả: H.264 1920x1080, 24 fps, 5,04 giây, ~10,7 MB (~17 Mbps), **không có luồng audio** (sound off). Task id dạng `omni:<số dài>`.
- **Chất lượng clip:** nhân vật giữ nguyên hình dáng qua các khung, camera tiến vào (push-in) đúng prompt, áo choàng lay, sương trôi; ghép được với FFmpeg và nhạc.
- **Ước tính thời gian batch:** clip ~1,5 phút/cảnh, mặc định 5 cảnh chạy song song → 100 cảnh khoảng 30 phút cho video, ảnh nhanh hơn nhiều.
- **Chưa kiểm chứng:** negative prompt qua API, thông điệp risk control thật, thời hạn link `video_url`, chi phí credit mỗi lần, hành vi Seedance.

## So sánh Kling và Seedance (cùng ảnh khung đầu, cùng prompt push-in, 5 giây, 2026-09-19)
| | `kling-v3-omni` (mode `pro`) | `dreamina-seedance-2-0-260128` (720p) |
|---|---|---|
| Thời gian chờ | ~84 giây | ~167 giây |
| Độ phân giải / fps | 1920x1080 / 24 | 1280x720 / 24 |
| Dung lượng (5 giây) | ~10,7 MB (~17 Mbps) | ~3,6 MB (~5,8 Mbps) |
| Âm thanh | không | không (`generate_audio` tắt) |
| Chuyển động | push-in, áo lay, sương trôi | push-in, áo lay, sương trôi; nhân vật rõ hơn một chút |
| Task id | `omni:<số>` | `seedance:cgt-...` |
- Chất lượng thị giác gần tương đương ở mẫu này; Kling nhanh hơn và độ phân giải mặc định cao hơn. Seedance 2.0 thường hỗ trợ 1080p (đặt `CLIPAI_RESOLUTION=1080p`), cần thử để so công bằng; Seedance 2.5 kéo dài tới 30 giây.
- Mẫu chỉ có 1 cảnh phong cảnh có nhân vật nhỏ: **chưa đủ** để kết luận về chuyển động nhân vật, cận cảnh, hành động nhanh, hoặc bộ lọc kiểm duyệt. Nên chạy bộ mẫu `eval/` (hành động, cận cảnh cảm xúc, bẫy IP) trên cả hai.
- Lệnh chạy thử nay lưu `trial_video_<model>.mp4` riêng từng model (lần đầu Seedance ghi đè file Kling vì dùng chung tên).

## Chi phí (ước tính trong Dashboard)
API không có endpoint giá/số dư, nên giá do bạn khai báo trong `data/pricing.json`:
1. Ghi số dư credit trên web, chạy đúng 1 lần (1 ảnh, hoặc 1 clip Kling/Seedance), ghi lại số dư; hiệu số là giá.
2. Điền vào `per_image` (theo model ảnh), và `per_video_second` (credit mỗi giây video) hoặc `per_video_clip` (credit mỗi clip) theo khóa `model:chất-lượng`, ví dụ `kling-v3-omni:pro`, `dreamina-seedance-2-0-260128:720p`. `null` = chưa biết giá.
3. Dashboard (Bước 2 và Bước 4) hiển thị "Ước tính chi phí" trước khi chạy: số mục, số giây, chi phí tối thiểu và tối đa (nếu mọi mục phải làm lại đủ `max_retry_count` lần). Khi dùng API thật và số mục ≥ `confirm_batch_at` (mặc định 10), các nút chạy bị khóa cho tới khi bạn tick xác nhận.
4. Mỗi lần gửi API thật được ghi vào bảng `usage_events` (model, chất lượng, số giây); thanh điều khiển hiển thị tổng "đã ghi nhận" theo giá khai báo. Provider giả lập (`mock`) không tính tiền.
- Số ghi nhận là **ước tính từ giá khai báo**, không phải hóa đơn; nền tảng có thể tính khác (ví dụ tác vụ lỗi có bị trừ credit hay không chưa biết).

## Chạy thật 1 cảnh đầy đủ qua Dashboard (2026-09-22, dự án "Real API Test 2026-09-22")
Thử toàn bộ Bước 1→5 qua giao diện Dashboard thật (không phải script), dùng nhân vật KELLY (đã có 7 ảnh tham chiếu trong Kho tài nguyên), cảnh đơn giản "đứng trên bãi biển hoàng hôn, không thoại".

- **Bước 2 (Deepix, `dola-seedream-5-0-pro-260628`):** ~40 giây. Lần gen đầu vẽ thêm một khẩu súng bắn tỉa không có trong prompt — hoá ra **đúng theo ảnh tham chiếu** (bảng thiết kế KELLY có liệt kê AWM là vũ khí đặc trưng), không phải model bịa; ảnh tham chiếu đã thắng thế so với mô tả chữ tôi tự đoán sai (tôi ghi "tóc vàng" nhưng thiết kế thật là tóc bob nâu đen — ảnh tham chiếu vẫn ra đúng tóc nâu đen, xác nhận cơ chế ưu tiên ảnh tham chiếu hơn text hoạt động đúng).
- **AutoQC bằng `LLM_PROVIDER=claude_cli` chạy THẬT lần đầu tiên** (trước giờ luôn bị chặn bởi lỗi "OAuth session expired" khi dashboard chạy từ tiến trình con của một phiên Claude Code — xem TODO.md 2026-09-21). Lần này claude_cli hoạt động: chấm ảnh đầu 0.75 < ngưỡng 0.85, tự nêu lý do cụ thể (bỏ khẩu súng không có trong mô tả cảnh, đổi sang medium shot, sửa tay cầm) và tự gen lại — ảnh thứ 2 đạt yêu cầu, duyệt được ngay.
- **claude_cli đụng hạn mức chi tiêu tháng ngay sau đó** khi thử sinh motion prompt (Bước 3): `LlmError: You've hit your monthly spend limit`. Xác nhận đúng lo ngại đã ghi trong TODO.md — claude_cli dùng chung hạn mức với các phiên Claude Code khác trên cùng tài khoản, không phải ngân sách API riêng. Chuyển sang nhập tay JSON (đường V0 "dán JSON") cho phần còn lại của bài test — vẫn hoạt động bình thường.
- **Bước 4 (Clip AI, `kling-v3-omni` mặc định, mode `pro`):** ~170 giây (2 phút 50). Bật tuỳ chọn "🔊 Model tự tạo âm thanh/lời thoại" (Kling `sound=on`) — kết quả **CÓ track audio thật** (codec `aac`), xác nhận tính năng hoạt động (dù cảnh này không có thoại nên chỉ có nhạc nền/ambient do model tự sinh, chưa thử với cảnh có lời thoại thật). Video: H.264 1920x1080, 24fps, 5,04s, ~5,9 MB.
- **Bước 5a (Clip AI audio, `music_v2`):** tạo 1 bản nhạc nền instrumental ~6 giây, xong trong vài giây. Chọn bản, ghép vào bản render cuối.
- **Bước 5b (Render Final, FFmpeg):** ghép clip + nhạc thành công, `FINAL_VIDEO.mp4` (H.264+AAC, 1920x1080, 5,04s, ~1,4 MB).
- **Bug phát hiện + đã sửa:** nút "✨ Tạo SFX" thủ công (`extras_section`, Bước 5a) và nút "🤖 AI tự đề xuất hiệu ứng" (`sfx_assistant`) dùng **trùng key Streamlit** `f"sfx_go_{pid}"` → `StreamlitDuplicateElementKey` crash Bước 5 bất cứ khi nào có cấu hình audio provider thật (đúng config đang dùng). Bug này không lộ ra ở bộ test cũ vì các test Bước 5 trước giờ không set `AUDIO_PROVIDER`/`VIDEO_PROVIDER=clipai`, nên nhánh có nút thủ công chưa từng render cùng lúc với nhánh AI trong CI. Đã đổi key nút AI thành `sfx_ai_go_{pid}` (`dashboard/app.py`), cập nhật 3 test cũ tham chiếu key sai, thêm 1 test hồi quy dựng cả hai nút cùng lúc với `AUDIO_PROVIDER=mock` để bắt lại nếu tái phát. 531 test pass.
- **Chưa thử được trong lần này:** nút "🤖 AI tự đề xuất hiệu ứng" thật (cần claude_cli, đang hết hạn mức); cảnh có lời thoại thật với audio-in-video (cảnh test không có thoại).
