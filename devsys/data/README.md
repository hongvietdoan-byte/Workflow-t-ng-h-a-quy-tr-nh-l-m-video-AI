# devsys/data — dữ liệu sinh ra của AI Development System (không commit)

| Đường dẫn | Nội dung | Ai ghi |
|---|---|---|
| `runs/<giờ>.json` | Một lần chạy toàn bộ test (tổng + từng file test + tên test lỗi) | nút ▶ Chạy test, `py tools/devsys_collect.py --tests` |
| `scores/<giờ>_<khu_vực>.json` | Một lần chấm một khu vực (định dạng `devsys-score/1`, xem `devsys/rubric.md`) | `tools/devsys_score.py`, người chấm ngoài (`--import`) |
| `events.jsonl` | Sự kiện: commit (hook), chạy test, chấm điểm | `tools/devsys_hook.py`, các lệnh trên |
| `snapshot.json` | Ảnh chụp số đo miễn phí mới nhất | `tools/devsys_collect.py`, hook |
| `exports/<khu_vực>.md` | Dữ liệu đầu vào cho người chấm ngoài | `tools/devsys_score.py --export` |
| `*.log`, `score_job.json` | Nhật ký các việc chạy nền từ web | web |

Xóa thư mục này không làm hỏng gì: web tính lại mọi số đo từ repo, chỉ mất lịch sử điểm / lần chạy test.
