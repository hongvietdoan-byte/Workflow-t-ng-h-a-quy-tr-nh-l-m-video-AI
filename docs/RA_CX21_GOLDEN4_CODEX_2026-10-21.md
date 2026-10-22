# CX21-GOLDEN4 — nghiệm thu golden #24/#27 lần 4

Ngày chạy: 21/10/2026, Asia/Saigon. Báo cáo chỉ có số đo/chẩn đoán đã lọc; không có prompt, payload, ảnh, CSDL hay credentials.

## Nguồn, quyền và cấu hình

- Công cụ/pipeline: `cloud/v31-golden4` tại **`121138a3`** (code sau rà `bd0e398b`; commit cuối chỉ sửa số test trong tài liệu). Worktree công cụ tạm: `D:/AI-Video-Output/golden-wt4`.
- Snapshot **MỚI**, không dùng lại lần 3: SQLite backup từ `file:///D:/AI-Video-Pipeline/data/manifest.sqlite?mode=ro` tới `D:/AI-Video-Output/golden-snapshot-4/manifest.sqlite`. `ref-root` live chỉ đọc. Không ghi CSDL/dữ liệu production, không API, không gửi job: **0 USD**.
- Mọi shot có job ảnh/video thuộc #24/#27; `latest_per_type=True`, theo source/draft của công cụ, không lựa riêng ca tốt để đủ ngưỡng.
- **Baseline tái dựng**, theo quyết định `v31-ep-g1-golden-compat-production-baseline-2026-10-21`: bool `core.features.state()` từ mã máy chính + cờ FEATURE cụ thể + lựa chọn 🧪 hiện có; chỉ cờ mới V3.1 TẮT. Không có snapshot cấu hình tại thời điểm gửi, nên không gọi đây là baseline lịch sử nguyên vẹn.
- 153 tên cờ, 104 BẬT sau ép **29** cờ V3.1 TẮT. Native được spawn với `ProcessStartInfo.Environment.Clear()` + whitelist; chỉ chuyển các biến FEATURE có tên trong catalog và giá trị bool/chế độ cho bước lấy baseline, không đọc/in môi trường toàn bộ hay credentials. Không đổi cờ live.
- `public-config.json` là `{}`; không đọc `dashboard.env`. Model/provider/envelope theo job đã ghi, qua cơ chế pin model của C-GOLDEN2. Fixture ghi `baseline_note = "baseline tái dựng (...)"`.
- Đã đọc diff denylist C-GOLDEN4 trước chạy: worker cho đọc dependency dưới `data/`, có manifest; cấm tên env/CSDL live/backup/log/key/credential, ghi/mạng/subprocess vẫn bị chặn. Không tự sửa công cụ hay mở rộng quyền khi lỗi.
- Capture/replay kết thúc mã 0; test kết thúc mã 1 trong trần. Đã kiểm worktree công cụ sạch và gỡ bằng `git worktree remove`; không còn tiến trình thuộc lượt này. Snapshot/fixture giữ ngoài Git, không xóa asset.

Danh sách explicit 29 experimental:

`budget_notice_d01`, `byd_v2_levels`, `continuity_shadow`, `continuity_state`, `diag_merge`, `field_guard`, `final_black_freeze`, `fit_durations_review`, `horizon_needs_sky`, `image_pregen`, `insert_inherit`, `narration_offscreen`, `pause_before_submit`, `poll_claim`, `qc_evidence`, `qc_false_alarm_fix`, `refusal_skip_same_picture`, `release_gate`, `repair_router`, `router_first_frame`, `send_estimate`, `send_preview_panel`, `sent_package_relpath`, `stage_props_byd`, `stale_code_alarm`, `video_qc_shadow`, `whitebox_height_dummy`, `world_map`, `world_map_sentences`.

## Nghiệm thu thật

**KHÔNG ĐẠT ngưỡng COMPAT; chưa mở khóa gộp M2.**

| Dự án | Ca chọn | COMPAT | DATA_CHANGED | CODE_MISMATCH | INSUFFICIENT_INPUT | Shot ảnh COMPAT | Shot video COMPAT |
|---|---:|---:|---:|---:|---:|---:|---:|
| #24 | 24 | 0 | 0 | 0 | 24 | 0 | 0 |
| #27 | 44 | 1 | 0 | 0 | 43 | 0 | 1 |

Ngưỡng: mỗi dự án ≥3 shot ảnh + ≥3 shot video COMPAT, toàn bộ 0 CODE_MISMATCH. COMPAT đo byte tương thích với baseline tái dựng; không chứng nhận đúng nội dung/chất lượng.

| Dự án | BUILT tại capture | DATA_CHANGED tại capture | INSUFFICIENT_INPUT tại capture |
|---|---:|---:|---:|
| #24 | 20 | 0 | 4 |
| #27 | 44 | 0 | 0 |

Phân nhóm replay (chỉ mã và lý do công cụ, không payload):

- 4 ca `INSUFFICIENT_INPUT`: chuỗi source_job_id thiếu/hỏng hoặc không an toàn.
- 63 ca `INSUFFICIENT_INPUT`: không đủ bằng chứng đầu vào lúc gửi.
- 1 ca `COMPAT`: đúng theo comparator.

Trong các ca COMPAT, 1 ca có `pregen_fingerprint = so_rieng` theo comparator C-GOLDEN2 (fingerprint được đối chiếu riêng vì gắn ngoài `_build_package`); không xuất giá trị fingerprint. Không tự gắn `matched_at_capture=True`, đổi baseline hay hash để nâng ca.

Ca COMPAT để truy vết (chỉ định danh, không payload):

- #27, scene_id 272, job 846, `video_gen` — fingerprint so riêng.

Chuỗi lịch sử bị đứt (chỉ job id/kiểu từ diagnostic C-GOLDEN4):

- #24, scene_id 257, `image_gen`, job 623: chain `[623]`; job 623: không có draft_job_id / source_job_id kiểu số (gói không có prompt).
- #24, scene_id 258, `image_gen`, job 632: chain `[632]`; job 632: không có draft_job_id / source_job_id kiểu số (gói không có prompt).
- #24, scene_id 259, `image_gen`, job 634: chain `[634]`; job 634: không có draft_job_id / source_job_id kiểu số (gói không có prompt).
- #24, scene_id 260, `image_gen`, job 639: chain `[639]`; job 639: không có draft_job_id / source_job_id kiểu số (gói không có prompt).

So với lần 3: kiểm nhóm `data/skills` không còn là điều kiện bị chặn hàng loạt; ca BUILT vẫn phải khớp gói lịch sử mới được COMPAT. `INSUFFICIENT_INPUT: không đủ bằng chứng đầu vào lúc gửi` không chứng minh code đã hồi quy; không có snapshot cấu hình/scene/asset tại thời điểm gửi để xác định gốc từ công cụ này. Không tự sửa công cụ/pipeline trong nhiệm vụ chỉ chạy nghiệm thu.

CSDL/fixture/manifest/kết quả/JUnit giữ ngoài Git: `D:/AI-Video-Output/golden-snapshot-4/`. SHA256 snapshot CSDL: `1546aa95a6088bd719f1ffbbc4bdbd785e251957da2b0928587306b7a0efd6e6`.

## Test native Windows 3.14 — chỉ phần C-GOLDEN4

Một lượt `tests/test_golden4.py`, `-q --tb=no -p no:cacheprovider -rf`, JUnit ngoài Git. Thay OBJECT `os.environ` bằng dict giả qua `patch.object` trước import pytest/mã dự án; native/worker dùng whitelist, fixtures/CSDL/credentials đều giả. Trần owned-process 300 giây, tự dừng cả cây khi quá hạn; không chạy lại bộ ba 15 phút của lần 3.

**45 passed, 2 failed trong 22,41 giây; không timeout, không xanh.**

| Test đỏ | Bằng chứng lọc | Ý nghĩa |
|---|---|---|
| `test_exists_check_is_not_hashed_but_open_is` | `KeyError: 'data/skills/a/skill.json'` | Việc hỏi tồn tại không có trong dependency manifest như test đòi. Introspection native xác nhận `os.path.exists` là `nt._path_exists`, nên chỉ bọc `os.stat` chưa chặn được nhánh Windows 3.14 này. Chưa sửa công cụ. |
| `test_symlink_in_data_pointing_outside_is_denied` | `WinError 1314` khi dựng symlink giả | Máy chưa có quyền tạo symlink cho test; lỗi xảy ra trước probe/khẳng định cổng chặn. Chưa xác nhận guard symlink qua test Windows, không xin/thay quyền hệ thống trong việc này. |

Nhóm đọc `data/skills` vào manifest và cấm env/backup/CSDL live đã qua trong bộ trên. Không suy rộng 45 test giả thành chứng nhận sandbox OS: báo cáo cloud đã ghi giới hạn đọc native C (vd `cv2.imread`) không phát audit. Không sửa/nới test để che 2 lỗi.

Nhánh chỉ ghi báo cáo nghiệm thu, không đổi code nên không có vòng viết test mới đỏ → sửa xanh. Chưa chạy cả bộ; quyết định gộp thuộc phiên chính.
