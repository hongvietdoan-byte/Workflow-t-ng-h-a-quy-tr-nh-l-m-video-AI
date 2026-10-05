# HANDOFF — S14.18 Giới hạn theo người (phiên con, nhánh worktree-agent-a689d1a6c6f7bf6e9)

## Đã xong
- Lõi `core/person_limits.py`: mức cơ bản open 2 / daily 2 / parked 1, Owner nâng riêng (app_settings `person_limits:<email>`),
  `LimitReached` (AccessDenied) có số liệu + danh sách dự án; yêu cầu vượt mức `limit_requests` (Owner duyệt/từ chối), nhật ký audit.
- Bảng mới (CREATE IF NOT EXISTS trong `core/db.py` SCHEMA): `project_creations`, `limit_requests`.
- Kiểm ở lõi: `Pipeline.create_project`, `compare.clone_project`, `archive.archive/restore/swap`; `archive.finished_projects/parked_projects`.
- 📥 của Owner: mục "Yêu cầu" (`core/inbox.py`).
- Bỏ AUTOPILOT_DAILY_JOBS (`core/autopilot.py`, `core/perf.py`, `core/capacity.py`, `core/diag.py`, `dashboard/admin.py`, `dashboard/header.py`,
  `tools/load_test.py`); test cũ đổi thành "biến cũ không còn chặn" (test_money_policy, test_perf_queue).
- Test `tests/test_person_limits.py` (15) xanh.

## Đang dở / bước kế
- Giao diện: ➕ Dự án mới + 🧬 nhân bản bắt LimitReached → bảng GIỮ/BỎ (open), form xin Owner (daily); 📦 cất → lựa chọn (parked);
  ⚙ danh sách cất tách "📦 Dự án dở đã cất" / "🏁 Kho dự án đã xong"; 👥 Nhóm: khối duyệt yêu cầu + nâng mức từng người.
- Test AppTest cho các khối trên; khai `core/person_limits.py` vào `devsys/areas.json` (không tăng version).
