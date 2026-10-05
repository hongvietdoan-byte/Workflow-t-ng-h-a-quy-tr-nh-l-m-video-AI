# devsys/data — dữ liệu sinh ra của AI Development System (không commit)

| Đường dẫn | Nội dung | Ai ghi |
|---|---|---|
| `runs/<giờ>.json` | Một lần chạy toàn bộ test (tổng + từng file test + tên test lỗi) | nút ▶ Chạy test, `py tools/devsys_collect.py --tests` |
| `scores/<giờ>_<khu_vực>.json` | Một lần chấm một khu vực (định dạng `devsys-score/1`, xem `devsys/rubric.md`) | `tools/devsys_score.py`, người chấm ngoài (`--import`) |
| `events.jsonl` | Sự kiện: commit (hook), chạy test, chấm điểm | `tools/devsys_hook.py`, các lệnh trên |
| `snapshot.json` | Ảnh chụp số đo miễn phí mới nhất | `tools/devsys_collect.py`, hook |
| `exports/<khu_vực>.md` | Dữ liệu đầu vào cho người chấm ngoài | `tools/devsys_score.py --export <khu_vực>` hoặc `--export all` |
| `ui_metrics.json` | Số đo giao diện thật (số click, rerun, khóa widget, tương phản, chữ nhỏ) cho thang bản 2 | `tools/devsys_ui_metrics.py` |
| `report.md` | Báo cáo hành động theo khu vực (vì sao trừ, sửa gì, ai làm, ưu tiên) | `tools/devsys_score.py --report` |
| `*.log`, `score_job.json` | Nhật ký các việc chạy nền từ web | web |
| `user_answers.json` | Câu trả lời của người dùng cho việc ⏸ trong kế hoạch (định dạng `devsys-answers/1`: mỗi việc một bản ghi — chọn nhanh, chữ, nguồn `devsys`/`chat`, người, giờ, `answered` → `applied` + ghi chú, lịch sử sửa) | ô trả lời trang 📋, `py -m devsys.answers add/applied` (phiên Claude ở worktree cũng ghi về file của bản chính `D:\AI-Video-Pipeline`) |

Xóa thư mục này không làm hỏng gì: web tính lại mọi số đo từ repo, chỉ mất lịch sử điểm / lần chạy test — **trừ `user_answers.json`**:
câu trả lời chưa áp dụng (`py -m devsys.answers list --pending`) sẽ mất, xem trước khi xóa.
