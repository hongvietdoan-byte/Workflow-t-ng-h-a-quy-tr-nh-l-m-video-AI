# HANDOFF — A7 bỏ cổng khóa ngân sách "Tự chạy trong trần"
- Đang làm: core/project_budget.py (needs_lock luôn False, run_over → run_warning cảnh báo, bỏ approval_pending/gate_reason, auto_caps),
  core/autopilot.py (_cap_wait → cảnh báo), dashboard (nút Duyệt & khóa → Đặt trần cảnh báo), tests.
- Bước kế: sửa test cũ, bỏ `pending` ở data/decisions.json, chạy test.
