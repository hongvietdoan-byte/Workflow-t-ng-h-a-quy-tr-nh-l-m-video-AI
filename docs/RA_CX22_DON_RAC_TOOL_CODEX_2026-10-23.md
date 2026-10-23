# Báo cáo CX22-DON-RAC-TOOL — Codex — 2026-10-23

## Kết quả

Đã bổ sung `tools/don_rac.py` cho báo cáo dung lượng, xoay vòng bản sao lưu có nhật ký khôi phục, rà/dọn worktree theo điều kiện an toàn và lệnh tóm tắt nhanh. `tools/hop_thu.py gop` có thể tự gỡ worktree sạch khi commit của nhánh XONG đã nằm trong `origin/main`; lỗi dọn chỉ cảnh báo, không làm hỏng sự kiện GỘP. Nhánh remote không bị xóa. Tệp mã và test đã đăng ký trong `devsys/areas.json`; giữ `version` ở 92.

## Kiểm thử

- Đỏ ban đầu: test import `don_rac` thất bại vì module chưa tồn tại; sau khi triển khai, bộ kiểm thử mục tiêu xanh.
- `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider --tb=no tests/test_don_rac.py tests/test_hop_thu.py` — **34 passed** (56.62 giây, lần chạy cuối).
- `py -m compileall -q tools/don_rac.py tools/hop_thu.py` — đạt.
- `git diff --check` — đạt.
- `py tools/related_areas.py` — chỉ ra khu vực devsys; không có caller ngoài module hộp thư. Các test chậm `tests/test_devsys.py`, `tests/test_devsys_v2.py`, `tests/test_hop_thu.py` được nêu cho bước gộp/cả bộ; chưa chạy cả bộ vì task đang trên nhánh riêng và chưa gộp.

## Nghiệm thu trên Windows (chỉ máy chính, không thay đổi nhánh/live code)

`py tools/don_rac.py --goc D:\\AI-Video-Pipeline bao-cao` hoàn tất. Tại 2026-10-23 11:44 +07:00: 108 worktree và 137 nhánh local; các thư mục lớn nhất gồm `.codex-wt` 4,721,090,997 byte, `.claude` 3,272,484,711 byte, `model 3D` 811,951,754 byte. Trong `D:\\AI-Video-Output`, thư mục `2026-10-15_du-an-31` là 3,468,849,459 byte; `2026-09-29_bo-boi-canh-thap-chinh-thuc` là 3,184,982,361 byte. Báo cáo đầy đủ được ghi vào `D:\\AI-Video-Output\\_luu_tru\\don_rac_bao_cao.jsonl`.

`py tools/don_rac.py --goc D:\\AI-Video-Pipeline worktree` chạy ở chế độ mặc định **dry-run**: đủ điều kiện 33, đã gỡ 0, bỏ qua 75. Không worktree/nhánh nào bị xóa. Bản chạy ban đầu gặp lỗi mã hóa console Windows (`charmap`); đã cấu hình stdout/stderr UTF-8 và chạy lại thành công.

## Rà an toàn

- Không gọi API trả phí; không đọc hoặc ghi `data/`, `data/manifest.sqlite`, `dashboard.env`, `data/projects`, `data/models3d`, `data/_plates3d` hay `.codex-runtime`.
- Lệnh dọn worktree/backup mặc định dry-run; chỉ `--lam-that` mới di chuyển/xóa mục được phép. Dọn tự động sau GỘP kiểm tra fetch, tổ tiên `origin/main`, đúng HEAD, sạch, không khóa, và đường dẫn trong vùng worktree cho phép.
- Giữ nguyên worktree dirty, mới, detached, locked/prunable, chưa có trên remote, hoặc ngoài vùng cho phép.
- Rà thủ công lần hai của phiên chính vẫn cần thiết vì task có thao tác xóa/di chuyển. Chưa báo XONG cho tới khi Claude hoàn tất RÀ KỸ.

## Tệp

- `tools/don_rac.py`
- `tools/hop_thu.py`
- `tests/test_don_rac.py`
- `devsys/areas.json`
