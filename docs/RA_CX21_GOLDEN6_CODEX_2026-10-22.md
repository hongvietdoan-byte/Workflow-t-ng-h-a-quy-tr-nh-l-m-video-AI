# CX21-GOLDEN6 — negative control xanh, lượt thật bị chặn bởi catalog công cụ

Ngày 22/10/2026, Asia/Saigon. **CHƯA ĐẠT nghiệm thu.** Negative control native đã xanh, nhưng cấu hình hợp lệ theo hai cây A/B bị validator của cây công cụ từ chối trước khi worker chạy. Không có bằng chứng tương thích từ 158 hàng BOTH_FAIL này.

## Nguồn và phạm vi

- A = `origin/main` **`62ede0dc657bf6d031f1fe03bdefaa322d404618`**.
- B = `origin/cloud/v31-m2-tichhop` **`9746a6ea38d874baf226765cfd378db01eca988d`**. Đã đọc thư mới nhất; chưa có nhánh tích hợp thay thế được chỉ rõ, không tự gộp thêm nhánh.
- Công cụ = `origin/cloud/v31-golden5` **`91708722`** (có sửa C-GOLDEN6).
- Snapshot **MỚI** tại `D:/AI-Video-Output/golden-snapshot-6/manifest.sqlite`: SQLite backup từ `file:///D:/AI-Video-Pipeline/data/manifest.sqlite?mode=ro`, chỉ thực hiện sau khi negative control xanh. Không dùng lại snapshot 5; ref-root live chỉ đọc.
- **0 USD**, không gửi job/API, không sửa công cụ/tests, không ghi dữ liệu thật/migration/cờ live. Nhánh chỉ chứa báo cáo; CSDL/JSON/checkpoint/JUnit giữ ngoài Git.

## Negative control — chạy trước lượt thật

Chạy đúng một test native Python 3.14: `tests/test_golden5.py::test_real_worker_two_code_trees_same_and_one_line_changed`, `-q --tb=no -p no:cacheprovider -rf`.

**1 passed trong 19,67 giây.** Test kiểm cây giống có ca SAME thật, đổi dòng `"call": call,` của builder cây B phải có DIFF tại `call`, và module của từng cây nằm đúng worktree. Không chạy broad suite hay thử lại test cũ đỏ. Script orchestration kiểm JUnit xanh trước khi backup CSDL/chạy lượt thật.

Native spawn với `ProcessStartInfo.Environment.Clear()` + whitelist; thay OBJECT `os.environ` bằng dict giả qua `patch.object` trước import pytest/core. HOME/USERPROFILE/TEMP ngoài repo; fixtures/CSDL/credentials của test đều giả. Trần owned test 300 giây, mỗi worker công cụ 120 giây, toàn lượt thật 30 phút. Không đọc/in/repr môi trường thật, header, token, credentials hoặc payload.

## Cấu hình và gốc lỗi

**Baseline tái dựng** theo sổ `v31-ep-golden-ab-acceptance-2026-10-21`: trạng thái hiệu lực sản xuất hiện có + cờ mới V3.1 TẮT; không có snapshot cấu hình lịch sử. Cờ lấy bằng `core.features.state()` của mã máy chính, chỉ chuyển FEATURE cụ thể có tên trong catalog và giá trị bool/chế độ; không đọc `dashboard.env`/secrets.

- Baseline phủ hai cây: **155 cờ, 104 BẬT, 30 experimental TẮT**; `public_config = {}`. Model/provider/envelope theo job/cơ chế pin của công cụ.
- So với danh sách 29 cờ của GOLDEN5, cây A/main mới có **`gen_auth_shadow`** (V3.1); baseline của cờ này là **false** và được khai explicit trong experimental. Không tự loại cờ khỏi cấu hình để qua validator.
- `_preflight()` kiểm catalog của A/B nên qua. Nhưng `build_from_database()` gọi `validate_baseline_flags()` dựa trên **catalog FEATURES của cây công cụ** (153 cờ), không có `gen_auth_shadow`.
- Mọi lần dựng bị `ValueError`: `experimental_flags cần list tên cờ duy nhất có trong catalog`. `run_ab()` bắt lỗi đầu vào này từng bên, gộp thành INSUFFICIENT_INPUT → BOTH_FAIL thay vì dừng toàn lượt bằng mã 2.
- Đây là **invalid precondition / lỗi validator catalog union của công cụ**, không phải hai pipeline cùng không dựng được do dữ liệu, và không phải bằng chứng code A/B giống nhau. Cần chủ công cụ sửa cổng kiểm cấu hình/catalog union rồi giao nghiệm thu lại; không tự sửa hoặc chọn cấu hình khác trong việc này.

30 experimental explicit (đều false):

`budget_notice_d01`, `byd_v2_levels`, `continuity_shadow`, `continuity_state`, `diag_merge`, `field_guard`, `final_black_freeze`, `fit_durations_review`, **`gen_auth_shadow`**, `horizon_needs_sky`, `image_pregen`, `insert_inherit`, `narration_offscreen`, `pause_before_submit`, `poll_claim`, `qc_evidence`, `qc_false_alarm_fix`, `refusal_skip_same_picture`, `release_gate`, `repair_router`, `router_first_frame`, `send_estimate`, `send_preview_panel`, `sent_package_relpath`, `stage_props_byd`, `stale_code_alarm`, `video_qc_shadow`, `whitebox_height_dummy`, `world_map`, `world_map_sentences`.

## Kết quả lượt thật — không có worker dựng gói

Đã gọi `main_ab --ab` **một lần**, chọn mọi shot có job ảnh/video mới nhất của #24/#27/#31/#33. Lượt kết thúc **5,744 giây, mã 1**, không timeout. Có 316 lần gọi builder bị validator chặn, **0 worker A/B được spawn**, không có raw package để so.

| Dự án | Hàng được chọn | SAME | DIFF | ONE_FAIL | BOTH_FAIL trước worker |
|---|---:|---:|---:|---:|---:|
| #24 | 24 | 0 | 0 | 0 | 24 |
| #27 | 44 | 0 | 0 | 0 | 44 |
| #31 | 78 | 0 | 0 | 0 | 78 |
| #33 | 12 | 0 | 0 | 0 | 12 |
| Tổng | 158 | 0 | 0 | 0 | 158 |

**Loaded evidence: 0/316 bên** có module path; mọi `loaded_a`/`loaded_b` là null do lỗi xảy ra trước worker. Vì vậy chưa xác nhận core của A/B cho bất kỳ ca thật nào. Không suy rằng 0 DIFF/0 ONE_FAIL là đạt: tất cả bốn dự án có 0 SAME, không đáp ứng ngưỡng; công cụ cũng trả `pass = false`.

## Bàn giao

Root đã yêu cầu chốt báo cáo CHƯA ĐẠT, **không loại `gen_auth_shadow`, không rerun**, không sửa validator/tests. Đã giữ nguyên kết quả công cụ và phân biệt lỗi precondition với BOTH_FAIL nghiệp vụ.

JSON kết quả `ab_all.json`, cấu hình `flags.json`, checkpoint và JUnit nằm ngoài Git ở `D:/AI-Video-Output/golden-snapshot-6/`. Không commit prompt/payload/CSDL/ảnh/log raw. Phiên chính tiếp nhận để gửi chủ công cụ và quyết định lượt nghiệm thu kế.

SHA256 snapshot CSDL: `f2c92e322cadd3f23e34429b63b5bce99dd94e98ccf2a83bf710a6306659cd2a`. Đã kiểm ba worktree tạm sạch và gỡ bằng `git worktree remove`; test/lượt thật đã kết thúc, không còn owned process. Giữ snapshot ngoài Git, không xóa asset/dữ liệu thật.
