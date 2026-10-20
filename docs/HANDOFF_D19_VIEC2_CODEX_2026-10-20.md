# Bàn giao Đ19 việc 2 — 20/10/2026

## Chốt root (ưu tiên dòng này)

Root đã đọc sửa lần hai sau RÀ KỸ độc lập, 26 test xanh/1,22s. Chỉ push nhánh riêng; Claude chạy cả bộ và rà/gộp. Không API thật/DB thật/cờ/bảng giá. Request estimate là số nguồn có thể thuộc cả batch, không tổng hợp thành actual. Hai artifact tải Python bị policy chặn dọn được loại khỏi commit, không tiếp tục cài/xóa.

Worktree `D:/AI-Video-Pipeline/.codex-wt/d19-viec2-doi-soat`, nhánh `codex/d19-viec2-doi-soat`, base `c32162dc`.

Đề nghị tích hợp đúng 5 file: `tools/clipai_cost_reconcile.py`, `tests/test_clipai_cost_reconcile.py`, `devsys/areas.json`, `docs/RA_D19_VIEC2_CODEX_2026-10-20.md`, cùng file bàn giao này. Chưa commit/push/TODO/main. Areas version vẫn 87.

Lệnh operator offline (chỉ là hướng dẫn, chưa chạy với dữ liệu thật):

```powershell
py tools/clipai_cost_reconcile.py --db <ban-sao.sqlite> --pricing <bang-gia.json> --tasks-json <tasks.json>
py tools/clipai_cost_reconcile.py --db <ban-sao.sqlite> --pricing <bang-gia.json> --tasks-json <tasks.json> --json
```

`--live` thay `--tasks-json` là opt-in đọc GET qua provider.from_env, không nạp dashboard.env/registry; không chạy nhánh này trong phiên. Báo cáo không phải hóa đơn; tiền thiếu giữ null, tổng chỉ cộng phần đã biết và báo số thiếu. Estimate theo request không cộng vào actual.

Test RED→GREEN: 3 failed/13 passed (3.52s) → 16 passed (0.96s) → **20 passed (2.00s)**; `tests/test_clipai_cost_reconcile.py -q --tb=no -p no:cacheprovider`. Do py launcher tự mở luồng cài khi whitelist env, toàn bộ test thực dùng native Python 3.14 absolute, process env whitelist, patch.object object os.environ giả trước import. Chi tiết/sự cố/kiểm related_areas/C7 tại RA.

Tiếp: phiên chính rà C7; chỉ gộp sau kiểm toàn bộ theo quy định. Không dùng/commit artifact untracked `Python/`, `python_install_20261020170318_63384.log` (launcher sinh; đã dừng; automatic approval review từ chối dọn). Không thay bảng giá từ một điểm 1080p. Không chạy API/dữ liệu thật, migration, poll ghi token, chỉnh flags hoặc secrets trong phạm vi này.

RÀ KỸ độc lập đã sửa tools/tests: giới hạn file16MiB/task5000/trang50, chặn overflow/giá hỏng, duplicate xung đột tiền null, loại chưa biết không đoán direct, mẫu zero/chưa xong không tính điểm; hiệu chuẩn nhóm model/video vào/res. CLI báo mã giai đoạn tĩnh, JSON cấm NaN/Infinity. Test bổ sung **25 xanh 0.95s → 25 xanh 0.78s → 26 xanh 1.22s**; chưa có RED riêng cho bổ sung, không thay bằng chứng RED gốc. Phiên chính đang đọc lại diff; xem RA mục cuối trước tích hợp.

