# CX24-GIAM-SAT — checkpoint Codex 2 (24/10/2026)

Trạng thái: **ĐANG LÀM**, đây là checkpoint an toàn, chưa phải nghiệm thu hoàn tất.

- Nhánh/worktree: `codex/v31-giam-sat` / `.codex-wt/v31-giam-sat`.
- Đã có rubric 3 trục, bundle dùng `devsys.scorer`, tổng điểm tính bằng code, thu thập bằng chứng chỉ đọc, worker, khóa lượt, ghi lịch sử/báo cáo, và writer M9 có sao lưu/idempotency.
- Kiểm tra gần nhất: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider --tb=no tests/test_devsys_plan_writer.py` — 5 passed; `py -m py_compile devsys/plan_monitor.py devsys/plan_monitor_worker.py devsys/plan_writer.py` và `git diff --check` đều đạt.
- Chưa xong: test bundle/score/trigger/lock, tích hợp 3 trang, AppTest, đăng ký area, rà caller và báo cáo cuối.
- Nhánh WIP đang lùi 61 commit so với `origin/main`. Trên `origin/main` đang có việc khác chạm `devsys/app.py`, `devsys/areas.json`, `devsys/plan_progress.py`, `tools/plan_progress.py`; do đó chưa nối UI hay đăng ký area ở checkpoint này. Đồng bộ sẽ làm trong worktree nhánh này, không đụng live main.
- Phạm vi kiểm tra chỉ dùng code và fixture tạm; không mở dự án/dữ liệu thật, không gọi API hay thao tác Computer Use.

Bước kế: giữ checkpoint trên remote, đồng bộ nhánh với `origin/main`, tiếp tục logic/test độc lập; nối app và areas sau khi rà xung đột với các nhánh đang làm.
