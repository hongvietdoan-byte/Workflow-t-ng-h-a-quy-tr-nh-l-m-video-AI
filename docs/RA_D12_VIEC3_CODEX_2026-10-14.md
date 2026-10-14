# Rà tự kiểm Đ12v3 âm ref — 14/10/2026

## Phạm vi
Nguồn gốc + đoạn + tốc độ đã duyệt; cờ `ref_audio_sync` TẮT. Không làm lại mix_bus trên main.

## Đã tự rà (skill2b.5)
- Không đọc `data/`, dashboard.env, credential thật; test mới thay OBJECT `os.environ` trước import; native subprocess whitelist; pytest --tb=no.
- ON thiếu metadata báo VÀNG qua failed, không đoán từ tên motion_ref hay fallback file silent.
- OFF không đọc cột metadata và giữ extract/fit cũ, uploader/nút/key cũ; bổ sung metadata không tự bật use.
- Metadata đổi tham gia fingerprint đề xuất; người dùng đã tích tiếng cũ vẫn giữ với ref_stale, không xóa quyết định.
- Rà caller: chat_intake không đoán nguồn gốc và setter clear metadata khi gắn mới; UI là đường nhập explicit; sfx_plan vẫn fit khi đặt timeline.
- Root bắt trước review: đường path tùy ý, metadata legacy không sửa được, ghi đè trước validation, thiếu giới hạn/timeout. Đã gom sửa: nguồn upload riêng + phạm vi project, nút lưu legacy không reupload, UUID/rollback, giới hạn600s/.01..100 và timeout.

## Bằng chứng
ĐỎ2 → XANH27; nhóm chốt49/13,57s; proof ffmpeg nguồn880Hz khác đoạn đầu440Hz, speed.5 ra~2s từ đoạn1s, fit2.5s pad. Cả bộ chỉ bước gộp; chưa sản xuất.

## Còn chờ
Reviewer độc lập + QA giao diện1440/1280; chưa commit/push. Thông số UI chưa có tự nạp metadata đã lưu để sửa tiện hơn; có thể tải gốc và khai lại metadata explicit. File fixture QA tạm cần xóa trước commit.

## Rà độc lập — cần sửa gom trước gộp
- **P1 · core/pipeline.py:244:** phạm vi nguồn GỐC lấy từ chính `path` người gọi truyền vào, không lấy dự án của `scene_id`. Người có quyền sửa dự án A có thể truyền motion ref trong dự án B và metadata nguồn B; setter probe nguồn B rồi lưu metadata vào cảnh A mà không kiểm quyền B. `propose` kiểm lại thư mục A chỉ khiến bản ghi không dùng được, không bảo vệ lần đọc ở setter. Sửa: xác định project_id từ scene, lấy data root tin cậy (tham số tường minh hoặc cấu hình được neo), kiểm cả ref/source thuộc project đó trước probe. RED: hai dự án A/B, actor chỉ edit A, setter nhận hai path của B phải từ chối trước `_source_duration`, CSDL không đổi; path hợp lệ A vẫn lưu.
- **P2 · core/ref_audio.py:146–148,165:** fingerprint chỉ chứa path/giây/tốc độ, không chứa dấu vết tệp GỐC. Ghi đè nguồn cùng đường dẫn bằng âm khác nhưng cùng duration khiến lượt sau báo `already`, giữ tiếng cũ và không đánh dấu `ref_stale` cho tiếng đã tích. Sửa: thêm dấu vết nội dung nguồn vào identity (hash nội dung hoặc cơ chế version nguồn đáng tin), dùng chung cho prune/cache; kiểm lại khi nguồn bị đổi hoặc mất. RED: propose lần một → ghi đè nguồn cùng path và duration → propose lần hai phải tạo đề xuất mới, xóa đề xuất chưa tích cũ; nếu đã tích phải giữ và đánh dấu stale.
- Chưa sửa code; hai RED trên là đề xuất, chưa chạy. Đã chạy related_areas bằng environ OBJECT giả trước runpy, xác nhận step5/core_infra/step3 và test chậm bắt buộc khi gộp; đọc caller chat_intake, sfx_plan, audio_lib và UI Bước5. Không chạy API/cả bộ, không truy cập dữ liệu/env thật.

## Vòng sửa gom sau rà
- P1 đã sửa: `Pipeline.data_dir` cấu hình tin cậy tùy chọn; `dashboard.common.scoped` gán root cấu hình DATA. Setter metadata lấy project_id từ scene, kiểm motion ref/source thuộc root đó trước probe; thiếu cấu hình từ chối. Setter không metadata giữ legacy.
- P2 đã sửa: identity thêm SHA256 nội dung nguồn; đọc theo chunk1MiB, trần512MiB, nguồn mất/không đọc/overflow báo VÀNG và không tách. Không cache hash theo mtime/size nên thay bytes cùng kích thước vẫn phát hiện. Giữ luật prune đề xuất chưa tích và stale tiếng đã tích.
- RED setter trên bản chưa sửa; RED source ban đầu có lỗi regex fixture, đã sửa thành Stream #0:0. Xác nhận riêng hồi quy source với mô phỏng fingerprint legacy cố định: 2fail đúng lượt đề xuất thứ hai. XANH cuối nhóm ref_audio_sync/f5b_backlog/chat_intake: **47 qua,6 bỏ qua /6,47s**; bỏ qua test cần ffmpeg trên PATH môi trường giả (proof thật có trong lượt triển khai trước).
- Test thêm: actor A/path B từ chối trước probe và CSDL nguyên; path A lưu được; thay bytes nguồn cùng path/size cho use=False/True; giới hạn đọc ở biên10bytes. Environ OBJECT giả trước imports, home fixture tạm cho Streamlit; không API/env/dữ liệu thật/cả bộ. Chưa commit/push; root đọc diff vòng sửa trước quyết gộp.

## Sửa hẹp vòng 2 theo root
- RED3 thật: source đổi trong extractor vẫn added; fit1e300 vẫn spawn; timeout ghi đè `_sync.wav` cũ. Đã sửa pre/post SHA nguồn trước add_local (mất/overflow/đổi → VÀNG, finally dọn tmp), shot fit trần600s trước spawn, fit ghi WAV tạm cùng directory rồi os.replace chỉ sau ffmpeg thành công.
- XANH focused cuối: **13 qua** trong `tests/test_ref_audio_sync.py`; thêm biến thể source mất/overflow trong extraction đều không added, tmp sạch. Atomic fit timeout giữ bytes/cache cũ và dọn temp. Không chạy lại nhóm rộng/cả bộ/API; environ OBJECT giả trước imports, subprocess native whitelist.
- Root đã QA1440/1280: 0pageerror/overflow, PNG trong docs/images/d12/ref_audio*.png; root còn ảnh height1450 để xem hết fields. Chưa xóa fixture QA; chưa commit/push, root đọc diff vòng2.
- QA cuối root: chính component `_motion_ref_editor`, ảnh1280/1440 height1500 hiển thị đủ fields, 0pageerror/overflow; root đã xem ảnh1280. Ảnh cuối thay ảnh expander đang animation. Đây là fake pipeline trên server QA riêng, chưa sản xuất/không8501; không khẳng định consoleerror. Root đã dừng PID sở hữu, reviewer xóa đúng tệp `_qa_ref_audio_ui.py` theo ủy quyền sau xác minh absolute path (không recursive).
- Root chốt fixdiff vòng2. Finding flag cuối: preset experimental tự bật ref_audio_sync dù verifiedFalse → thêm OPT_IN_ONLY. Test settings experimental/flags{} với environ OBJECT giả: RED1→GREEN1/0,16s. Không chạy lại nhóm rộng. Tổng file mới14test đã xanh theo các lượt13+1; sẵn sàng commit/push nhánh, chưa cả bộ/gộp/sản xuất.

## Bổ sung bảo vệ đầu vào ffmpeg sau commit nhánh 4a52a772
- Root finding: file nằm đúng project nhưng nội dung playlist HLS/concat có thể gọi URL hoặc đọc file khác project. Chỉ source ON `_source_probe`/`_extract_segment` thêm input options trước `-i`: `-protocol_whitelist file,pipe -format_whitelist mov,matroska,webm,wav`; HLS/concat không nằm trong demuxer allowlist. OFF `_extract` giữ nguyên.
- Đối chiếu nguồn chính thức [FFmpeg Formats](https://ffmpeg.org/ffmpeg-formats.html): format_whitelist là input allowlist demuxer; MOV enable_drefs/use_absolute_path mặc định tắt, giữ mặc định này. [FFmpeg Protocols](https://ffmpeg.org/ffmpeg-protocols.html): protocol_whitelist là input allowlist. Tên native demuxer/option xác nhận bằng proof ffmpeg thật MP4+WAV.
- RED2 mock args thiếu allowlists → XANH **16qua/1,40s** focused toàn test_ref_audio_sync; có ffmpeg thật nguồn WAV440/880Hz, speed/fit và generated nativeMP4 probe. Playlist giả.mp4 có URL chỉ chạy mock subprocess, không mở mạng; test kiểm cả allowlists và vị trí trước `-i` cho probe/extract. Không khẳng định đây là sandbox decoder tổng quát; phạm vi chặn playlist/protocol ngoài nguồn native.
- Chưa commit/push bổ sung; root đọc diff rồi quyết. Không API/data/env thật/cả bộ; environ OBJECT giả trước imports/native subprocess env whitelist.
