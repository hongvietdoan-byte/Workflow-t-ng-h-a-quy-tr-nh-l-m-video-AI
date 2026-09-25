# Nghiên cứu khớp môi cho toàn bộ video (kế hoạch V4 GĐ3, 2026-09-25)

**Mục tiêu:** mọi shot có người đang nói và thấy mặt đều khớp miệng với **giọng Việt của mình** (giọng clone ElevenLabs), không chỉ
shot cận. Khi làm được thì luật "né cận mặt người nói" (N3) chỉ còn là một lựa chọn.

## 1. Các cách (tra 2026-09-25)
| Cách | Làm gì | Giá | Tiếng Việt | Ưu | Nhược |
|---|---|---|---|---|---|
| **A. Seedance `reference_audio`** (ClipAI, tài khoản đang có) | Tạo clip kèm file giọng; model vẽ miệng theo âm | Seedance 2.0 720p **$0,15/s** (2.5: $0,23/s) | Tài liệu công khai nêu ~8 ngôn ngữ (Anh, Trung, Nhật, Hàn…), **không thấy tiếng Việt** | Một bước, không cần tài khoản mới; web Weave Canvas cũng gửi đúng kiểu này (cổng `reference_audio` / `voiceover`) | Nguồn thứ ba cho biết model có thể **đổi nhịp** so với âm gốc → miệng lệch giọng thật; chỉ Seedance (không Kling) |
| **B. Khớp môi sau khi có clip** — sync.so `lipsync-2-pro` | Sửa miệng của clip đã có theo file giọng | ~**$0,084/s** (nền tảng trung gian); gói API của sync.so từ **$5/tháng** | Chạy theo âm thanh (âm vị) → **không phụ thuộc ngôn ngữ** | Chạy được với video 3D / AI; giữ nguyên phần còn lại của khung (hợp với gói bối cảnh); dùng cho clip của mọi model | Cần tài khoản + khóa riêng; có hàng đợi / giới hạn đồng thời (429 `concurrencyLimit`) |
| **B'. Kling LipSync (audio → video)** | Như B, của Kling | API chính thức: 0,5 đơn vị / 5 s (~$0,14/đơn vị) → ~$0,07 / 5 s; nền tảng trung gian ~$0,08–0,15 / lần | Theo âm thanh | Rẻ | Cần tài khoản Kling Developer (khóa riêng, ClipAI không có endpoint này) |
| C. Lip Sync trên web ClipAI | Làm tay từng clip | theo web | ? | — | Không tự động được |
| D. Mô hình chạy máy (LatentSync, MuseTalk, Wav2Lip) | Như B, trên máy mình | điện + GPU | Theo âm thanh | Không tốn API | Cần GPU + torch (chưa cài — **hỏi trước khi tải**), chất lượng mặt 3D game chưa rõ |

## 2. Đã làm (code, cờ `lip_sync` TẮT tới khi thử thật)
- **Chọn cách cho từng shot** (`core/lipsync.method_for`):
  - `generate` (A): shot cận (CU/ECU/MCU) mà Đạo diễn đánh dấu `lip_sync: true` (câu then chốt).
  - `post` (B): các shot thoại khác thấy mặt người nói.
  - `skip`: không ai nói, người nói ngoài khung / quay lưng, hoặc toàn cảnh xa.
- **Giọng của từng shot** (`lipsync.shot_audio`): lấy các câu đã tạo giọng của shot, đặt đúng giây như timeline cuối (`voice.LEAD` / `GAP`), đệm
  im lặng cho đủ độ dài clip (ffmpeg).
- **A:** adapter ClipAI nhận `reference_audio` (content `audio_url` vai trò `reference_audio`, file ở multipart `audio_files`); luật số audio
  theo model (2.0 ≤ 3, 2.5 ≤ 10 — `data/provider_rules.json`). Bộ chọn model đưa shot `generate` sang Seedance 720p; runner gửi giọng của shot.
- **B:** `core/adapters/syncso.py` (`POST /v2/generate`, `x-api-key`, trạng thái `PENDING…COMPLETED`, `outputUrl`) + pha autopilot `lipsync` sau
  video: gửi mỗi clip `post` một lần, tải về thay clip (giữ bản gốc `<idx>_prelipsync.mp4`), ghi sổ chi (kind video, $0,084/s trong
  `data/pricing.json` — **chưa đo**), qua trần tiền. Không có `SYNC_API_KEY` → báo một lần, shot giữ miệng cũ (không im lặng).
  **Chưa biết** tên trường file khi tải trực tiếp (tài liệu không ghi) → `SYNC_FILE_FIELDS` mặc định `video,audio`, kiểm ở lần gọi đầu.
- **Dựng:** shot đã khớp môi (`lipsync/index.json` state `done`) được đặt giọng đúng giây của đoạn giọng đã gửi, không bị đẩy lùi.
- **Đạo diễn:** khi cờ bật, khối thời lượng báo "Khớp môi đang BẬT" (được đặt thoại ở cận, đánh dấu `lip_sync: true` ~20% câu quan trọng);
  cờ storyboard "cận mặt người nói" không còn báo cho shot sẽ được khớp môi.
- **Sửa lỗi phát hiện khi làm:** `shots.shot_data` chỉ giữ các trường có sẵn → `lip_sync`, `weather`, `plate_spot`, `plate_mode` do Đạo diễn ghi
  bị bỏ; nay được giữ.

## 3. Cần thử thật (GĐ8) và cần người dùng
1. **A:** 1 shot cận #7 (Kelly "Em hiểu rồi…"), Seedance 2.0, 4 s ≈ **$0,60**: miệng có khớp tiếng Việt không, có đổi nhịp không, nhân vật có
   giữ không.
2. **B:** cần **tài khoản sync.so có API** (gói từ $5/tháng) + `SYNC_API_KEY` trong `dashboard.env` — người dùng quyết. Thử 1 clip trung ≈
   **$0,34** (4 s).
3. Tự chấm độ khớp (SyncNet) cần torch — hỏi trước khi tải; tạm thời người xem.

## Nguồn
- [sync.so — Lipsync models](https://sync.so/docs/models/lipsync) · [sync.so API reference](https://sync.so/docs/api-reference) · [Create generation](https://sync.so/docs/api-reference/api/generate-api/create) · [Get generation](https://sync.so/docs/api-reference/api/generate-api/get) · [sync.so pricing](https://sync.so/pricing) · [WaveSpeed — lipsync-2-pro](https://wavespeed.ai/models/sync/lipsync-2-pro)
- [Kling API pricing](https://kling.ai/dev/pricing) · [Atlas Cloud — Kling Lipsync A2V](https://www.atlascloud.ai/models/kwaivgi/kling-lipsync/audio-to-video)
- [Seedance 2.0 paper (arXiv 2604.14148)](https://arxiv.org/pdf/2604.14148) · [Seedance 2.0 audio reference guide (SeeGen)](https://seegen.ai/seedance-2-0-audio-guide) · [Seedance 2.0 lip sync (seedance.tv)](https://www.seedance.tv/blog/seedance-2-0-lip-sync)
- Mã trang Weave Canvas `deepix.ingarena.net/weave/app.js` (node Video: cổng `reference_audio` tối đa 10, vai trò `voiceover`)
