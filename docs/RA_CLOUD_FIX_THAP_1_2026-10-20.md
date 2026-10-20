# C-FIX-THAP-1 — 6 mục THẤP sau rà gộp 20/10 (làn cloud-C, 20/10/2026)

Nhánh `cloud/v31-fix-thap-1` (từ `origin/main` sau "Gộp 5 việc cloud-C"). Cờ giữ TẮT. Test: `tests/test_v31_fix_thap_1.py` (21 ca — 11 ĐỎ trước
sửa đúng lý do; mục 5 xanh ngay: hành vi đã đúng, nay có test hành vi thay cho so chuỗi nguồn). 0 USD.

| # | Mục (đề phiên chính) | Sửa | Test |
|---|---|---|---|
| 1 | `video_qc_shadow.check` giải mã CẢ clip (`clip_measure.frames(width=640)`) chỉ để lấy khung 0; tính lại `motion_series` mà `measure` vừa tính | `video_qc_shadow.first_frame()` đọc MỘT khung (cv2.VideoCapture.read); `clip_measure.motion_series` nhớ 4 clip gần nhất theo (đường dẫn, cỡ, mtime) — `measure` (jerks) và shadow đọc cùng clip liền nhau → giải mã + luồng quang một lần; tệp ghi lại → đo lại | không gọi `frames`; `motion_series` 2 lần → giải mã 1 lần |
| 2 | `qc_scene._BEHIND_ANY` dò cả `image_prompt` / `action` ("the sun behind", "rút súng sau lưng" bỏ nhầm kiểm cỡ) | chỉ dò trường máy / bố cục (`angle`, `shot`, `blocking`, `start_frame`); tiếng Việt chỉ khi nói về MÁY ("máy … sau lưng", "quay lưng về máy", "qua vai"); bỏ "behind her shoulders" | 3 ca không được bỏ kiểm + 4 ca trường máy vẫn bỏ; test DP1 chuyển cụm chữ sang `blocking` |
| 3 | `plate_layout_qc._OUTDOOR`: "sân khấu" bị coi là ngoài trời | `sân(?! khấu)` | "INT. sân khấu nhà hát" → trong nhà; "INT. sân sau nhà kho" → vẫn không đoán |
| 4 | `code_version.self_stale` / `banner` nói "≠ HEAD <sha>" trong khi so dấu vân tay | câu theo dấu vân tay ("tệp .py của core/ / dashboard/ đã đổi từ lúc khởi động (dấu a → b)"); bản ghi cũ chưa có dấu → câu sha như trước; `stale_instances` trả thêm `code` | câu không còn "≠ HEAD"; test M1.7 cũ đổi câu kỳ vọng |
| 5 | test hành vi `estimate_images` khi `claude_cli` + `send_estimate` BẬT → phần Claude = 0 | (đã đúng) thêm test gọi thật `cost.estimate_images`: claude_cli → `chat_prompt` = `qc` = 0, tổng < anthropic | 1 ca |
| 6 | `continuity_shadow`: `\bmất\b` khớp rộng | `_LOSE` chỉ cụm rơi / mất VẬT ("đánh rơi", "làm mất", "bị giật mất", "thả súng", "ném súng đi", "drops", "loses the gun"…); `_SHIFT` "trở về" chỉ "thực tại / hình dạng" | "mất thăng bằng / bình tĩnh / biến mất / trở về nhà" → vẫn báo súng biến mất; 4 cách thả thật → không báo |

Chạy: 21 + test các nhánh liên quan (DP1, DP2, M17, M42, M43, FIX-M16-17) = 99 qua. Cả bộ `-m "not slow" -n auto` (Linux cloud): 6447 qua, 4 đỏ = các ca đỏ sẵn trên `main` cùng máy.
Chưa: Windows (cache `motion_series` dùng `st_mtime_ns` — có trên Windows), agent quy ước 7 (luật cloud: không mở phiên con).
