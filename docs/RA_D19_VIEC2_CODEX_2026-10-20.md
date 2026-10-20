# Rà Đ19 việc 2 — đối soát giá ClipAI chỉ đọc (20/10/2026)

Nhánh `codex/d19-viec2-doi-soat`, gốc `c32162dc`. Chưa commit/gộp/push. Không sửa TODO, bảng giá, code sản xuất, cờ, dữ liệu dự án hay schema.

## Phạm vi và nguồn đã rà

Đọc AGENTS, CLAUDE, TODO đầu phiên, CHUAN_XAY_DUNG, skill vòng làm việc theo plan; Đ19 việc 2 trong CODEX_TASKS và §5 tài liệu gói V3.1.
Đọc nguồn thật: `core/adapters/clipai.py` (`_page`, `task_usage`, `from_env`), `core/adapters/http.py` (envelope), `core/db.py` (jobs/usage_events và migration quality_tier/draft_job_id), `core/cost.py` (seedance_token_usd/clip_price), `core/budget.py` (row_usd/spent), `core/runner.py` (video/clipai/second).

`tools/clipai_cost_reconcile.py`: `--db` và `--pricing` bắt buộc; task offline qua `--tasks-json`. Chỉ khi chọn `--live` mới dựng provider qua `from_env` và đọc `_page('seedance', page)`, giới hạn 1–100 trang, mặc định 10. Không nạp dashboard.env/registry, không gọi live trong phiên này. Có thể inject provider vào main/collect_tasks để kiểm bằng transport giả.

SQLite dùng URI do công cụ dựng `Path.as_uri() + '?mode=ro'`, bắt file tồn tại, kể cả bản sao; không mở schema qua core.db.connect. main đóng connection. Chỉ SELECT cột cần thiết, không join nhân bản số tiền. External ID chuẩn hóa seedance prefix; nhiều job trùng ID hoặc nhiều usage event cùng job => cảnh báo, tiền sổ chi chưa xác định. Task thiếu khỏi vùng phủ được cảnh báo; giới hạn trang không khẳng định provider không tạo task.

Mỗi task giữ riêng actual web `seedance_cost_usd`, estimate lúc gửi `request_params.seedance_cost_usd`, tính token bằng hàm bảng giá hiện hành, giá sổ chi bằng model/tier/quantity thực của usage event qua `clip_price`. Loại draft / upgrade (`draft_task` hoặc `draft_job_id`) / direct; tổng tách loại và project, đếm trường thiếu, không đổi thiếu thành 0. Output dựng allowlist, không copy payload/prompt/header/error raw. JSON hỏng, bad type, trạng thái chưa xong, thiếu actual/token/giây/giá đều báo.

## Bằng chứng offline (chưa thử dữ liệu/API thật)

Cả ba lượt cùng đích: `tests/test_clipai_cost_reconcile.py -q --tb=no -p no:cacheprovider`, PYTHONUTF8=1; native runtime Python 3.14 có sẵn, whitelist môi trường tiến trình mới, `patch.object(os, 'environ', dict_gia)` trước import pytest/code dự án. Không patch.dict(clear=True), không đọc/in môi trường thật. Test import lặp có/thiếu cấu hình giả; patch context tự hoàn nguyên.

- RED: **3 failed, 13 passed in 3.52s**, exit 1: JSON chuỗi hỏng chưa cảnh báo; envelope của fake transport chưa đúng hợp đồng thực.
- GREEN 1: **16 passed in 0.96s**, exit 0.
- GREEN 2 sau tự rà bổ sung: **20 passed in 2.00s**, exit 0.
- Fake transport chỉ nhận GET video-list. Test write trên connection RO nhận OperationalError. Không API thật, không đọc DB thật/khóa thật.
- Fixture dựng SQLite tạm: 3 nháp × 1.150336 = **3.451008 USD**, bước nâng **6.364575 USD**, tổng **9.815583 USD**; estimate bước nâng **2.79936** tách riêng. Token price 1080p thấp **8.571%** so tiền thật, chỉ **1** điểm 1080p. Chưa đủ ≥5 điểm để cân nhắc hiệu chỉnh, không thay bảng giá.

## Tự rà 2b.5 và khâu liên quan

- Luật 1: missing/invalid/unknown không giả thành 0; counter thiếu theo từng tổng.
- Luật 2/3: công cụ riêng không thêm đường gen/cờ/sổ chi; test kiểm GET transport, RO SQL, ngoại lệ được làm sạch.
- Luật 8: bằng chứng chỉ offline, chưa nghiệm thu đối soát thật; không tuyên bố M1.6 hoàn tất.
- Không ghép task nháp vào tiền bước nâng; task duplicate bị bỏ sau cảnh báo; ambiguous job/event không đoán.
- `related_areas.py tools/clipai_cost_reconcile.py tests/test_clipai_cost_reconcile.py` chạy trong cùng môi trường giả: **exit 0**, khu vực **budget**, không caller, **không đụng khu vực test chậm**. Đăng ký tool/test trong areas, version **87** giữ cho tích hợp tăng một lần.
- C7 độc lập: đã gửi phiên chính đề nghị rà; chờ kết quả phiên chính cập nhật trước tích hợp.

## Sự cố launcher và việc mở

Lần đầu dùng Windows `py.exe` với môi trường whitelist làm Python manager không tìm được runtime đã cài: launcher báo cập nhật manager và bắt đầu tải/cài 3.15. Đã Ctrl-C, không tiếp tục dùng launcher, không khẳng định cài thành công. Sau đó dùng executable 3.14 có sẵn như trên. Launcher để lại untracked `Python/` và `python_install_20261020170318_63384.log` trong worktree. Lệnh dọn hai artifact tự sinh có resolve/check đường dẫn nằm trong worktree bị automatic approval review từ chối (`blocked by policy`); chưa xóa gì. Không đưa chúng vào thay đổi đề nghị tích hợp.

Còn mở: C7 độc lập; dọn artifact launcher khi được phép; kiểm dữ liệu thật/live chỉ khi có chỉ đạo sau; thu ≥5 điểm 1080p có actual từ web/hóa đơn; chưa bổ sung poll ghi token (ngoài phạm vi); chưa chạy cả bộ và chưa gộp.

## RÀ KỸ độc lập và sửa bổ sung

Phát hiện: số nguyên cực lớn làm `math.isfinite` tràn; batch không giữ hợp đồng 50; file/task offline chưa có trần; duplicate khác tiền giữ bản đầu; thiếu cờ vẫn đoán direct; zero actual tính điểm; cộng mẫu khác model/video vào; lỗi CLI thiếu vị trí lỗi.
Đã sửa ngay tools/tests: file tối đa 16 MiB, 5000 task, 50 dòng/trang; số đầu vào 0–1e15 (trần bảo vệ tính toán, tổng tối đa 5000 task), giá âm/bool/NaN/Infinity hoặc vượt trần bị từ chối. Giá tính ra qua bộ lọc hữu hạn; chênh lệch chia số cực nhỏ giữ null khi tràn. JSON CLI cấm NaN/Infinity.
Duplicate xung đột làm các trường tiền chưa biết; thiếu bằng chứng loại giữ `unknown`; actual=0 hoặc task chưa hoàn thành không tính điểm; hiệu chuẩn chia model/video vào/resolution, cần 5 điểm cùng nhóm. Mã lỗi CLI tĩnh phân biệt pricing_input/tasks_input/provider_read/database_or_reconcile, không xuất exception/payload.
Targeted bổ sung: **25 passed 0.95s**, **25 passed 0.78s**, rồi bổ sung hồi quy overflow (kết quả lượt cuối bên dưới). Các lượt dùng executable native absolute, process whitelist và `patch.object` thay đối tượng môi trường trước import dự án, `--tb=no`, không API/DB thật. Không có lượt RED riêng cho sửa bổ sung; bằng chứng RED gốc giữ nguyên, không khẳng định RED mới.
Không sửa production/areas version/TODO, không commit/push, không chạm hai artifact launcher bị từ chối dọn.

Lượt cuối: **26 passed in 1.22s**, exit 0. Gồm hai giá hữu hạn 1e308 không thể cộng thành Infinity, giá bảng hỏng và mẫu có actual cực nhỏ; `json.dumps(..., allow_nan=False)` xác nhận report hữu hạn. Phiên chính cần đọc lại diff trước chốt C7.
# Chốt root Đ19v2

- Root đã đọc toàn bộ tool và sửa bổ sung lần hai: 26 test xanh/1,22s, C7 độc lập đã thực hiện. Chỉnh đúng nhãn help --live: from_env chỉ trong nhánh opt-in, không chạy API thật. Estimate request giữ số nguồn, có thể là giá cả batch video_num, không cộng vào tổng actual hay suy giá một task từ đó. Đây là công cụ đối soát, chưa hoàn tất sửa giá M1.6.
- Chỉ stage các file công cụ/test/areas/tài liệu được liệt kê; giữ ngoài commit hai artifact Python đã bị policy từ chối dọn. Chưa cả bộ Windows/main/live/dữ liệu thật.
