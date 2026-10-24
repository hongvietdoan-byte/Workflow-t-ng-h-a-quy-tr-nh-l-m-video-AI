# HANDOFF — Codex 3 — main test đỏ

Nhánh `codex/v31-main-red`, worktree `D:\AI-Video-Pipeline\.codex-wt\v31-main-red`.

## Đã làm
- Xác nhận trên `main` gốc `1fcb5f6e`: ba kiểm tra đỏ là thiếu `tests/test_kpi_goc.py` trong vùng, thiếu M9.13 trong `devsys/plan_map.json`, và `tools/m60_profile.py` bị quét nhầm là script trả phí.
- Đã thêm M9.13 → `NEN`; cho phép `tools/m60_profile.py` trong kiểm tra trần chi vì chỉ tạo fixture, chặn mạng/process ngoài và thay provider bằng mock.
- Sửa `_ref_lint` dùng cùng ảnh khung đầu đã duyệt như prompt khi đo render 3D; regression test đã đỏ trước khi sửa.
- Chưa đụng `data/`, API trả phí hay máy chủ.

## Kiểm tra
- Baseline trên `1fcb5f6e`: ba kiểm tra được giao đều đỏ đúng nguyên nhân.
- Trước khi thêm bản đồ KPI: plan map, nhóm `ScriptScan` và toàn bộ `tests/test_seedance_refs.py` xanh — 43 passed.
- Sau khi khai báo `tools/kpi_goc.py` và `tests/test_kpi_goc.py` trong vùng `devsys`: bốn mục tiêu liên quan xanh — 5 passed.
- Rà độc lập `core/runner.py` + regression mới: không có finding P1/P2; cờ tắt giữ hành vi cũ.

## Hoàn tất
- Đã khai báo mã nguồn KPI gốc và test của nó vào khu vực `devsys`.
- Nhánh đã push: `codex/v31-main-red`; không đụng `data/`, API trả phí hay máy chủ.
