# Rà Đ14 việc 3 — cache âm thanh cục bộ (13/10/2026)

- Nhánh `codex/d14-viec3-am-thanh-local`, nền `3d6004bb`. Chưa commit/push; bàn giao root để rà độc lập và sửa một vòng gom.
- Đề bài CODEX_TASKS mục ĐỢT 14 việc 3: lỗi 69 ffmpeg đọc nguồn âm thanh G: Google Drive ở #24. Chỉ sửa luồng âm thanh, không runner, không cờ mới.
- Đối chiếu caller: `ambience._bed` nhận trực tiếp đường dẫn Kho vào ffmpeg; `end_popup.apply` đưa pop Kho vào mix (shot_popup dùng chung); nhạc qua `music.use_library_track/use_pick`, SFX qua `audio_lib.add_local`, `sound_lib.copy_into`. Các đường này nay dùng snapshot audio local; builder thuần của ffmpeg và mọi input video giữ nguyên.
- Cache tại TEMP của Windows/ai-video-audio-cache, bucket SHA thư mục công việc dự án; không chép G → G khi output nằm trên Drive. SHA đường dẫn tuyệt đối chuẩn hóa + size + mtime_ns; hai nguồn cùng basename khác cache. Bản riêng `.part`, kiểm size và nguồn không đổi trước khi publish atomic. Không URL/download, không sửa nguồn Kho.
- Hạn chế bản hiện tại: 128 tệp/1 GiB mỗi bucket, chưa TTL/auto dọn; lỗi đầy nói dọn cache khi không dựng. Root/reviewer rà lại concurrency khác process và cách giới hạn dung lượng.
- Lỗi đọc/copy có file nguồn + “chép về máy”; SoundError kế thừa ValueError để Dashboard C.act bắt và hiện lỗi. Nguồn zero byte vẫn giữ hợp đồng copy cũ, ffmpeg chịu trách nhiệm báo không giải mã được, không thêm validator ngầm làm hỏng test legacy.

## Bằng chứng

1. ĐỎ trước sửa: `tests/test_audio_local_cache_d14.py` **6 failed /0,74s**, thiếu helper và ambience vẫn gửi nguồn thẳng vào ffmpeg.
2. Nhóm liên quan 6 file đầu: **4 failed,119 passed /52,36s**. Bắt race Windows `os.replace` và SoundError của nguồn thiếu làm đổi hợp đồng ValueError, guard zero byte làm vỡ fixture copy legacy. Sửa code, không nới assertion cũ.
3. Nhóm sau sửa: **125 passed /47,28s**: test_audio_local_cache_d14, test_sound_lib, test_audio_lib, test_music_pick, test_end_popup_p24, test_shot_popup. Có 8 test mới: reuse, size/mtime refresh, basename, threads, partial/error, nguồn thay đổi, cache đầy, URL trước IO và ffmpeg thật.
4. WAV giả 48 kHz/440 Hz cắt+loop+fade qua `ambience._bed` trên ffmpeg Windows thành WAV **1,50s ±0,05**; nguồn/cache/output đều TEMP, không nguồn G thật.
5. `git diff --check` xanh; `related_areas.py` đọc lại với PYTHONUTF8=1: step5, callers autopilot/dashboard/step1/2/3/4/budget/core/plates/knowledge/lipsync. Areas version giữ 66, đăng ký test mới step5; không code file mới.
6. Một lệnh pytest sai tên test_end_popup.py không chạy test; sửa tên thành test_end_popup_p24. Một lần related_areas thiếu PYTHONUTF8 báo lỗi encoding; chạy lại đúng biến.

## Tự rà skill 2b.5 / việc mở

- Không nới test, không đổi widget keys/cờ mặc định/areas.version; không API, download dịch vụ hoặc đọc dữ liệu sản xuất. Không TODO/PLAN/main/live.
- Cache dùng absolute identity, không phụ thuộc cwd; không ghép từ ngắn/bỏ dấu/nội dung prompt. Worker không sửa runner.
- Review độc lập cần gom: cache pass-through nguồn đã local; cap/cross-process; cleanup không che lỗi gốc; popup cache lỗi không làm mất icon. Root đang điều phối reviewer riêng.
- Worker phát hiện thêm: `delivery` bắt lỗi ambience rồi cắt `str(e)[:200]` trong manifest; Step5 chưa hiện amb.error. Cần reviewer/root gom diagnostic rõ file + hướng dẫn, không im lặng khi mất âm nền.
- CHƯA thử nguồn Google Drive G: thật hoặc #24; chưa cả bộ Windows, chưa gộp; không claim chất lượng production. GUI 1440/1280 N/A vì không tạo/đổi UI trong bản worker; diagnostic cần sửa sau rà.

## RÀ KỸ độc lập — gom sửa (Codex, 13/10)

- Đọc skill 2b.5, CLAUDE mục 7, CHUAN và `related_areas.py`; rà callers chọn nhạc/SFX/ambience/end-popup/shot-popup/render/Step5. Bắt và sửa **5 P2**: cache bị chép lặp; cap không khóa giữa process; cleanup che lỗi nguồn; copy tiếng pop lỗi làm mất icon; ambience lỗi không hiện cảnh báo và cắt mất hướng dẫn.
- Cache snapshot khóa filesystem theo project scope: `msvcrt` Windows, `fcntl` Unix; lock được OS giải phóng khi process kết thúc, tối đa đợi 120s. Chỉ passthrough file hash nằm đúng scope; source thay đổi vẫn identity mới. Không xóa cache đang dùng; `.part` chưa dọn được còn tính trần, lỗi dọn ghi thứ cấp và giữ lỗi nguồn.
- Popup cache lỗi giữ overlay, bỏ tiếng và `sound_note` VÀNG. Ambience lỗi giữ bản dựng, ghi diag `ambience_audio`, manifest đủ reason; Step5 hiện warning trong vùng chất lượng bản dựng cũ. Không key widget mới.
- Regression đầu **3 failed /0,43s** (cache passthrough, cleanup, popup); warning UI **1 failed /0,92s** trước sửa. Thêm actual hai process Python cạnh tranh cap=1 (1 thành công, 1 báo đầy), actual `delivery.render` fake fixture tới ranh giới mix, và actual Step5 đọc outputs SQLite tạm.
- Nhóm cuối 6 file **131 passed /45,84s**; các lượt trung gian 129/46,21s và 130/46,08s vì bổ sung caller/UI regression sau khi phát hiện. Không nới assertion. Sau đó thêm thông tin thứ cấp leftover cleanup (không đổi nhánh xử lý), test cleanup focused xanh.
- QA Chrome/Playwright actual `loudness_line`, SQLite in-memory, TEMP app cổng **8527**: **1440×1000, 1280×1000**, warning có hướng dẫn và tên file cuối đường dẫn dài; **0 exception, 0 pageerror, 0 overflow**. PNG `docs/images/d14/am_thanh_warning_1440.png`, `_1280.png`; chỉ dừng process mang đường dẫn riêng `codex-d14-audio-review-ui`, không cổng live.
- Unix lock chỉ đối chiếu code, chưa chạy Unix; nguồn G thật/production/cả bộ chưa thử. Không API/network download/dữ liệu thật/env/main/live. Areas version66 giữ.
- Root đọc diff cuối lock/cache/cleanup/pop/delivery/Step5 và regression; xem2PNG1440/1280 có hướng dẫn/tênfile, khôngtràn. Chốt5P2 đã sửa;131test vàfocusedcleanup xanh. Chưa nguồnGthật/Unix/cảbộ; không gộpmain.
