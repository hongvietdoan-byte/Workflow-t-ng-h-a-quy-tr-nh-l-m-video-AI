# C-GOLDEN2 — Golden lần 3: final theo draft_job_id, COMPAT theo cờ sản xuất, model theo job, fingerprint (cloud-C, 21/10)

Nhánh `cloud/v31-golden2`, tạo từ origin/main. Chỉ sửa `tools/golden_capture.py`, `tools/golden_db_replay.py` và test, không sửa `core/`. Chi tiết định nghĩa mới ở `tests/golden/README.md`, mục "C-GOLDEN2".

## Sửa theo từng mục của đề
| Mục | Sửa | Test (fixture tổng hợp) |
|---|---|---|
| (a) final video | `--latest-per-type`: video final lần theo `draft_job_id` (bản nháp video); ảnh vẫn theo `source_job_id` | `test_a_video_final_follows_draft_job_id`, `test_a_image_still_follows_source_job_id` |
| (b) COMPAT theo cờ sản xuất | File cờ `{"baseline_flags", "experimental_flags"}`; hàm mới `validate_baseline_flags` (fail-closed: thiếu cờ catalog / không bool / experimental lạ, lặp hoặc đang BẬT). `build_from_database(…, experimental=)`. Manifest có `experimental_flags`. Fixture có `flags_mode: "baseline"`. Định dạng cờ cũ giữ nguyên định nghĩa cũ | `test_b_*` (6 test) |
| (c) model | Worker: video `_choice` → `pinned_choice(choice, job)` (model = `jobs.model`); ảnh `image_models.of_project` → `jobs.model` | `test_c_model_is_pinned_from_the_job` (hàm thuần + kiểm worker có gọi) |
| (d) pregen_fingerprint | `compare_database_job` so RIÊNG trường này. Phần còn lại giống → `COMPAT` + `pregen_fingerprint: "so_rieng"`, kèm `fingerprint_sent` / `fingerprint_built` | `test_d_*` |
| (e) tệp nền/Kho khác refs | `classify_answer`: chặn đọc `data/_plates3d/…` / `data/assets/…` → `DATA_CHANGED` + `paths` + lý do (chạy sau worker) | `test_e_*` |
| (f) `--help` cp1252 | Cả hai công cụ đặt lại stdout/stderr thành utf-8 | `test_f_help_on_cp1252_console[capture/replay]` |
| (g) worker 3.14 | `needs_native_314` (skipif có lý do) gắn cho 14 test cần worker. Trong đó `test_worker_reads_only_job_ref_and_reports_blocked_sibling` (vào main cùng CX21-GOLDEN) đỏ trên 3.13 vì audit hook đệ quy trong `pathlib.relative_to`; đỏ cả trên main ở cloud. **Máy chính cần xác nhận test này xanh trên 3.14** | `test_g_*` |

`tests/test_golden2.py`: 22 test. Đã commit khi 16 test còn đỏ, sau đó xanh cả 22. Ở cloud: `test_golden_replay.py` + `test_golden_db_replay.py` + `test_golden2.py` → 85 qua, 25 bỏ qua (cần 3.14), 0 đỏ.

**Chưa làm được ở cloud:** chạy worker thật (cần native 3.14) và dữ liệu thật #24/#27 (`D:/AI-Video-Output/golden-snapshot-2/`). Vì vậy (c), (e) và phần worker của (d) mới kiểm bằng hàm thuần + kiểm mã nguồn. Máy chính chạy lại theo lệnh dưới đây mới biết số COMPAT thật.

## Lệnh chụp lại (phiên máy chính chạy — chỉ đọc, 0 USD)
1. **Tạo file cờ baseline từ môi trường Dashboard đang chạy** (đúng cờ lúc gửi). Chạy trong repo máy chính, với `dashboard.env` đã nạp:
   ```
   py -c "import json; from core import features; exp=['stale_code_alarm','diag_merge','budget_notice_d01','poll_claim','world_map_sentences','world_map','pause_before_submit','send_estimate','refusal_skip_same_picture','horizon_needs_sky','qc_false_alarm_fix','video_qc_shadow','continuity_shadow','send_preview_panel','continuity_state','whitebox_height_dummy','final_black_freeze','qc_evidence','repair_router','release_gate']; exp=[k for k in exp if k in features.FEATURES]; b={k: bool(features.on(k)) for k in features.FEATURES}; [b.__setitem__(k, False) for k in exp]; print(json.dumps({'baseline_flags': b, 'experimental_flags': exp}, ensure_ascii=False))" > <snapshot>/compat-flags.json
   ```
   - `experimental_flags` ở trên là 20 cờ có chữ "V3.1" trong nhãn / lý do của catalog hiện tại. **Phiên chính duyệt lại danh sách này**: thêm cờ V3.1 mới gộp (vd `byd_v2_levels`, `field_guard` khi đã gộp), bỏ cờ không phải "mới".
   - Một cờ V3.1 đang BẬT ở máy chính mà có trong danh sách sẽ bị ép TẮT ở file. Nếu gói đã gửi lúc cờ đó bật thì ca sẽ khác byte. Khi đó nên bỏ cờ khỏi `experimental_flags`.
2. **Chụp lại**, mỗi shot một lần, cho #24 và #27:
   ```
   <python-native-3.14> tools/golden_capture.py --db <snapshot>/manifest.sqlite --project 24 --shot <scene> --flags-file <snapshot>/compat-flags.json --public-config-file <snapshot>/public-config.json --ref-root <snapshot-ref-root> --purpose compat --database-replay --latest-per-type --output <fixture-moi>.json
   ```
3. **Replay:**
   ```
   <python-native-3.14> tools/golden_db_replay.py --fixture <fixture-moi>.json [--fixture …] --db <snapshot>/manifest.sqlite --ref-root <snapshot-ref-root> --output <replay-moi>.json
   ```
4. **Chạy test golden trên 3.14:**
   ```
   <python-native-3.14> -m pytest -q tests/test_golden_replay.py tests/test_golden_db_replay.py tests/test_golden2.py
   ```

**Kỳ vọng:**
- 29 ca final → dựng theo bản nháp: hết lý do "cần draft lịch sử".
- Ca model (job 667/657/660/879/909/915/839/790) dựng đúng `jobs.model`.
- Job 846 → COMPAT kèm `pregen_fingerprint: so_rieng`.
- Ca đòi plate/asset khác → DATA_CHANGED có `paths`.

Ca nào vẫn INSUFFICIENT thì gửi `reason` + `diagnostic` về hộp thư để rà tiếp.

## Bộ test đầy đủ
Xem tin hộp thư `xong C-GOLDEN2`.
