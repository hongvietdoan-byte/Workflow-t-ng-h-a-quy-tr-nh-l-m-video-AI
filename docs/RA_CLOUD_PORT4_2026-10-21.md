# C-PORT4 — test đỏ trên Linux/cloud, xanh Windows (cloud-E, 21/10, nhánh cloud/v31-port4)

Máy: Linux, root, Python 3.13, ffmpeg 6.1.1 (Ubuntu). Lệnh: `PYTHONUTF8=1 python3 -m pytest -q -p no:cacheprovider <test>`.
Trước: 4 ca chạy riêng → `4 failed, 2 passed` (perf_queue, subjects xanh khi chạy riêng).

1. **test_sent_package::test_unreadable_picture_sha_null_said_and_still_sent** — gốc: LỖI CODE thật đa nền tảng. `diag.redact` có mẫu
   `[A-Za-z0-9+/_-]{40,}` (che khóa) nuốt cả đường dẫn POSIX dài: tin chẩn đoán thành "không tính được sha256 của ***.png" (không còn
   "gone.png"). Windows có `\` nên không dính. Sửa `core/diag.py` (`_long_run`): giữ đường dẫn tuyệt đối (một `/` đầu, mỗi phần < 40,
   không sau `:`/`=`); khóa có `/`, base64 `/9j/…`, `//host/…`, `key=/…` vẫn che. Thêm `tests/test_diag.py::…long_posix_path…`.
   Sau: xanh; test_diag/sent_package/ui_log/director_lease/tickets/lessons/stage_auto `201 passed`.
   Ghi chú rà: `core/tickets._safe` dựa một phần vào redact để chặn đường dẫn POSIX nằm GIỮA chuỗi (đầu chuỗi vẫn bị chặn riêng) — nay
   không còn chặn vô tình; đường Windows giữa chuỗi vốn đã bị chặn bằng regex ổ đĩa. Chưa đổi (ngoài phạm vi).
2. **test_ffmpeg_studio::test_the_frame_punches_in_on_the_beats_of_the_music** — gốc: `ModuleNotFoundError: librosa` (không có trong
   requirements.txt, máy chính cài riêng). Sửa: `skipIf(find_spec("librosa") is None)` có lý do. Bằng chứng: venv tạm có librosa →
   `tests/test_ffmpeg_studio.py 9 passed`; không librosa → `8 passed, 1 skipped`.
3. **test_end_popup_p24::test_icons_and_vietnamese_words_pop_over_the_end** — gốc: font. `subtitles.discover()` chỉ quét thư mục font
   Windows (+ data/fonts, FONT_DIRS) → Linux 0 font → PIL dùng font bitmap mặc định → dòng vàng `2 not greater than 300`. Sửa test:
   máy không có font tiếng Việt thì trỏ FONT_DIRS tới dejavu/noto/freefont hệ thống (chọn DejaVu Sans, đủ dấu); không có → skip có lý do.
   Assert giữ nguyên. Sau: `9 passed`.
4. **test_cost_route_e1::test_recut_by_hand_moves_where_the_final_is_cut** — gốc: khác bản ffmpeg. Clip dốc sáng bắt đầu Y=0; ffmpeg
   Windows kẹp Y mã lại về ≥ 16 (cắt 0 s đọc 0.8 — số cứng trong test), ffmpeg 6.1 Linux giữ 0 (đọc 0.0). Sửa: `_ramp` bắt đầu Y=16,
   `_start_second` trừ 16 → cắt 0 s đọc 0.0 trên cả hai, vẫn phân biệt cắt tự động 1 s (delta 0.1 giữ). Sau: e1 + tap2 `60 passed`.
5. **test_perf_queue::…stopping_a_queued_project…**, **test_subjects::…only_for_seedance…** — KHÔNG tái hiện: riêng lẻ xanh; hai file
   nối tiếp `30 passed`; `-n 8` ba lần `30 passed`; cả bộ (trừ golden) `-n 8`: `6800 passed, 14 skipped, 22 xfailed` (11:49).
   Nghi do tải máy lúc chạy cả bộ (perf_queue dựa thời gian thật: poll 0,02 s, `sleep(0.3)`, chờ ≤ 60 s). Chưa sửa — không có bằng chứng gốc.

Còn đỏ: không (ngoài golden replay cần Python 3.14 — thuộc CX21-GOLDEN (e), không đụng). Chưa thử trên Windows: ca 3/4 đổi test cần
một lượt chạy máy chính để xác nhận (ca 4: Windows kẹp Y<16 không còn ảnh hưởng vì dốc bắt đầu ở 16).
