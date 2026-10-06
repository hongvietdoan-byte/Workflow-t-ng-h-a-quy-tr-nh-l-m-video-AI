# HANDOFF — S14.10 (Gói F1) devsys đo đúng + Đợt 6b + thang v2.1

Phiên con đang làm (nhánh worktree). Xóa file này khi xong.

## Kế hoạch commit
1. [x] S1 `collect.flags_state` dùng đúng luật `core.features.on()` (feature_settings.json + dashboard.env) + regex `*FLAG = "…"`
2. [x] S2 `check_evidence` kiểm `test:path::Lớp::tên` bằng ast; `giai_thich_chenh` phải có bằng chứng kiểm được
3. [x] S3 `import_score` đối chiếu fingerprint/input_hash của export; commit/date luôn từ hệ thống
4. [x] S11 `todo_mo` chia điểm theo số khu vực trùng + phân loại việc code/người dùng/quy ước
5. [ ] S15 `bang_chung` đòi dòng trích có dấu hiệu chạy thật
6. [ ] Đợt 6b: `collect.ops_summary`, bundle + fingerprint, trang Hiệu quả
7. [ ] Thang v2.1 MỘT lần: rubric.md + luật `hieu_qua_tut`/`gop_y_lap` + `db:` + S6/S8/S9/S10/S14/S17/S5/S4/S12

## Test
`PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider tests/test_devsys.py tests/test_devsys_v2.py tests/test_devsys_answers.py tests/test_devsys_f1.py`
(gốc 82 qua trước khi sửa)
