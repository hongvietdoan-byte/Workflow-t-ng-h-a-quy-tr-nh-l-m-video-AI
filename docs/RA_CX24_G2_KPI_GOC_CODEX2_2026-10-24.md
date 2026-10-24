# Báo cáo CX24-G2-KPI-GOC — Codex 2

Ngày: 24/10/2026
Nhánh: `codex/v31-kpi-goc`
Phạm vi: công cụ đo chỉ đọc và test fixture giả; không chạy trên dữ liệu #31/#33 thật, không gọi API.

## Kết quả

Đã thêm `tools/kpi_goc.py`, yêu cầu `--ban-sao` trỏ tường minh tới một bundle bản sao có manifest `kpi_goc_manifest.json`. Không có đường dẫn mặc định tới CSDL; SQLite mở bằng `mode=ro` và `query_only`; từ chối đường dẫn bên trong `AI-Video-Pipeline/data`, symlink/junction, đường dẫn thoát khỏi bundle và ghi báo cáo vào bên trong bundle.

Tool trả baseline/hiện tại và lý do chưa đo được cho năm mục tiêu. MT1 không kết luận tiền thừa chỉ từ tổng chi; cần evidence quy được lỗi hệ thống. MT2 dùng sai lệch tuyệt đối theo từng cặp ước tính trước gen/chi phí thực, báo max và trung bình. MT3 đếm `free_text_used AND unsafe_pass` trên tổng lượt kiểm cổng. MT4 tính độ phủ sơ đồ chung trên mọi cảnh nhiều shot, kể cả cảnh thiếu nhãn; thiếu map hoặc kiểm vị trí sẽ là PARTIAL. MT5 báo recall và false-positive cho clip lỗi/đạt, đồng thời tách recall clip đơ và sai khung đầu; thiếu mẫu đạt/lỗi cho một loại thì chưa được đánh dấu MEASURED.

## Hợp đồng bundle

Mỗi entry trong `baseline`, `current` và `mt3_baseline` có `project_id`, `label`, đường dẫn tương đối `db`; có thể chỉ tới `evidence` JSON trong cùng bundle. Evidence v1 gồm `project_id`, `schema_version: 1` và các object `mt1`–`mt5`, với `coverage_complete` cùng nhãn/đối chiếu cho phép đo. Mẫu MT2 cần `kind`, `estimate_usd`, `actual_usd`; MT3 cần `checks` gồm `free_text_used` và `unsafe_pass`; MT4 cần `scenes` gồm `multi_shot`, `shared_map`, `position_checks`; MT5 cần `clips` gồm loại clip, nhãn `bad` và `detected_before_user`.

Ví dụ chạy sau khi phiên chính chuẩn bị bản sao riêng, ngoài thư mục dữ liệu đang chạy:

```powershell
$env:PYTHONUTF8='1'
py tools/kpi_goc.py --ban-sao '<thu-muc-ban-sao>' --out '<thu-muc-bao-cao-ngoai-ban-sao>/kpi-goc.md'
```

`--out` là tùy chọn; nếu bỏ, kết quả Markdown/JSON được in ra stdout. Chỉ đặt `coverage_complete: true` khi đã đối chiếu đủ nguồn cho cohort; không nội suy nhãn. Evidence sidecar là dữ liệu đã được chọn/đối chiếu từ bản sao nguồn (sổ chi, lỗi, golden/replay, lineage/QC), không phải phép đo tự suy ra nguyên nhân.

**Điều kiện MT3:** baseline bắt buộc có #24, #27, #31; current là #33. Nếu phiên chính chỉ chuẩn bị DB #31/#33 thì MT3 chủ động trả `NOT_MEASURABLE` cho tới khi thêm evidence replay #24/#27 vào `mt3_baseline`. Không thay cohort gốc bằng riêng #31.

## Kiểm thử

- Đỏ trước triển khai: pytest không thu thập được test do module chưa tồn tại.
- Xanh sau sửa: `py -m pytest -q -p no:cacheprovider --tb=no tests/test_kpi_goc.py` — **9 passed**; `py -m py_compile tools/kpi_goc.py tests/test_kpi_goc.py` — đạt.
- Fixture kiểm soát DB mode=ro/no-write, chống traversal và thư mục `data` giả, trạng thái thiếu evidence, MT3 cohort, MT4 thiếu nhãn và MT5 theo loại.

## Bàn giao

Đề xuất thêm dòng kế hoạch `M5.3b đo 5 KPI gốc (cổng trước M5.4)` như đề bài; phiên chính ghi kế hoạch và chạy `plan_progress --write`. Chưa đăng ký `tools/kpi_goc.py` vào `devsys/areas.json`: tệp này hiện thuộc vùng đang sửa đồng thời của M47B/M82B, tránh xung đột Codex 2; cần phiên chính tích hợp/đăng ký sau khi vùng được giải phóng.
