# HANDOFF — S14.30 (nhánh `s14-30-delivered`, chưa push)

## Đã xong
- **Tín hiệu "đã xuất bản giao"**: bảng mới `deliveries` (core/db.py SCHEMA, `CREATE TABLE IF NOT EXISTS` — migration idempotent, không
  rebuild bảng `outputs` có CHECK kind). Cột: project_id, path, source, manifest, delivered_at, delivered_by.
  Lý do không dùng `outputs kind='delivered'`: phải rebuild bảng `outputs` (CHECK) trên CSDL thật + `delivery.status`/`lineage` duyệt
  `outputs` theo kind → rủi ro hơn; bảng riêng ít xâm lấn nhất.
- **core/delivered.py** (một nguồn): `is_delivered`, `latest`, `has_render`, `rendered_not_delivered`, `mark`, `backfill`, `HINT`.
- **Ghi đúng lúc**: `delivery.deliver` (nút “📦 Xuất bản đầy đủ” Bước 5 + bước cuối autopilot) → `_mark_delivered` ở cuối chuỗi.
  Render lỗi → exception, không ghi. Một kích thước trong danh sách xuất lỗi → KHÔNG ghi + cảnh báo "Bản giao chưa đủ… chưa tính là xong"
  + diag `not_delivered`. File bản giao không tồn tại → không ghi + báo. QC bản dựng có lỗi chặn vẫn ghi (file đã xuất; số lỗi lưu trong
  manifest `qc_blocks`) — autopilot vẫn dừng ATTENTION như cũ.
- **Lời báo giới hạn** (open + parked): dự án có bản cuối chưa giao được đánh "— có bản cuối, chưa xuất bản giao" và thêm câu
  "Dự án #… đã có bản cuối nhưng chưa xuất bản giao — bấm “📦 Xuất bản đầy đủ” ở bước Bản giao: xuất bản giao để tính là xong".
  `_describe` thêm khóa `rendered`.
- **📥**: loại mới "Bản giao" (inbox.KINDS) — "Đã có bản cuối nhưng chưa xuất bản giao … xuất bản giao để tính là xong", màn `deliver`.
- **Backfill**: `tools/backfill_delivered.py` (mặc định chạy thử; `--apply` ghi), idempotent; in + diag `delivered_backfill` số dự án đổi.

## Quyết định từng chỗ dùng định nghĩa
| Chỗ | Quyết định |
|---|---|
| `core/person_limits.is_finished` (giữ tên/chữ ký, `data_dir` giữ nhưng không dùng) | ĐỔI → `delivered.is_delivered` |
| `core/archive.finished_projects` / `parked_projects` (Kho dự án đã xong / 📦) | ĐỔI (qua is_finished) |
| `core/inbox` mục "Bản giao" | THÊM (dùng `rendered_not_delivered`) |
| `core/inbox` biến `finished` (ẩn nhắc khóa ngân sách) | GIỮ — nghĩa "đã có bản ghép", nhắc khóa ngân sách sau khi ghép là thừa |
| `core/perf.portfolio_rows` `done`/bước "✅ Hoàn tất" | GIỮ (thanh tiến độ = đã ghép); THÊM khóa `delivered` |
| `dashboard/home.status_of` "✔ Xong" + "🎬 Sản phẩm đã hoàn tất" | ĐỔI → cần `delivered`; có bản cuối chưa giao → "Chờ bạn" |
| `core/autopilot.progress` dòng "Bản giao" | GIỮ (theo chỉ định; autopilot nay luôn ghi deliveries khi chạy xong) |
| `core/effectiveness.finished_projects`, `tools/effectiveness_baseline.py` | GIỮ — số đo cần dự án có video ghép |
| `core/diag` (autopilot done mà thiếu FINAL_VIDEO) | GIỮ |
| `dashboard/steps/step1_run.py`, `step5.py`, `music_timing`, `lineage`, `rough_cut` | GIỮ — nghĩa "bản ghép cuối" |
| `tools/ui_snapshot.py` seed "done" | ĐỔI — ghi thêm deliveries để ảnh chụp vẫn "✔ Xong" |

## Backfill dự án cũ (chưa chạy trên CSDL thật)
Bằng chứng (mạnh trước): (1) thư mục `<DELIVERY_OUTPUT_ROOT|D:\AI-Video-Output>\*_du-an-<id>` có file video; (2) dòng `outputs` 'final' có
khóa `final_qc` trong manifest (chỉ `delivery.deliver` ghi, cuối chuỗi); (3) `autopilot_state='done'` + có bản cuối. Không bằng chứng mà có
bản cuối → liệt kê "KHÔNG còn tính là xong". Chạy ở `D:/AI-Video-Pipeline` SAU khi sao lưu:
```
cp data/manifest.sqlite data/backup/manifest.before_s14_30_2026-10-05.sqlite
PYTHONUTF8=1 py tools/backfill_delivered.py                # chạy thử, xem danh sách
PYTHONUTF8=1 py tools/backfill_delivered.py --apply        # ghi thật
```
Lưu ý: dashboard phải chạy bản mới (bảng `deliveries` tạo khi connect) — tool tự tạo bảng qua `connect`.

## Test
Đỏ→xanh: tests/test_delivered.py (7), test_person_limits FinishedMeansDelivered (3) + test_old_project_with_only_final_video_file_is_not_finished,
test_screens_dashboard test_rendered_but_not_delivered_is_waiting_not_done, test_perf_queue test_portfolio_rows_… (thêm assert delivered).
test_person_limits_ui: 2 chỗ "dự án xong" đổi sang `delivered.mark`. Liên quan đã chạy qua: ~440 test (không chạy cả bộ).

## Đang dở / bước kế
- Chưa chạy thật (luật 8): chưa bấm “📦 Xuất bản đầy đủ” trên dashboard thật để xác nhận dòng deliveries.
- Phiên điều phối: sao lưu CSDL → chạy thử backfill → báo người dùng danh sách "không còn tính là xong" → `--apply`.
- Mở: thư mục giao `D:\AI-Video-Output` hiện do người/phiên Claude chép tay, code chưa chép ra đó; tên thư mục khác mẫu
  (`2026-10-01_ab-hieu-ung-8`) không được nhận. QC chặn vẫn tính đã giao — hỏi người dùng nếu muốn chặt hơn.
