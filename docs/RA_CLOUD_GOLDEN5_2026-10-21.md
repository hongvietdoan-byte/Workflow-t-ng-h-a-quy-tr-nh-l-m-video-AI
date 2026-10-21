# C-GOLDEN5 — Công cụ golden so A/B hai cây code trên cùng snapshot (cloud-C, 21/10)

- Nhánh: `cloud/v31-golden5`, tách từ `origin/cloud/v31-golden4` (công cụ C-GOLDEN2 + C-GOLDEN4).
- Theo sổ `v31-ep-golden-ab-acceptance-2026-10-21`.
- 0 USD: không gửi provider, không ghi dữ liệu thật.

## Đã làm — `tools/golden_db_replay.py --ab`
- Đầu vào:
  - MỘT snapshot CSDL (`--db`);
  - MỘT ref-root chỉ đọc (`--ref-root`);
  - MỘT file cờ (`--flags`: `{"baseline_flags": {...cờ sản xuất...}, "experimental_flags": [cờ mới V3.1], "public_config": {...}}` — cờ mới = false);
  - HAI cây code: `--code-a` (worktree main) và `--code-b` (worktree M2 tích hợp);
  - `--project N` (lặp được).
- Mỗi shot có job ảnh / video của dự án: lấy job MỚI NHẤT mỗi loại.
  - Envelope lấy từ gói đã gửi; job chưa gửi dùng envelope giả cố định, giống nhau cho A và B (so CODE, không so lịch sử).
- Dựng gói hai lần bằng đúng đường cũ: `_submit_args` → `_prepare_kwargs` → `_finish_kwargs` → `_build_package` + `pregen_fingerprint`. Mỗi bên một **worker cách ly như hiện có**:
  - chỉ đọc `data/`, có fingerprint;
  - cấm ghi / mạng / tiến trình;
  - Python 3.14 native.
  - Worker nhận `request["code_root"]` và import `core` của CÂY ĐÓ; `prompts/` + `knowledge/` cũng đọc từ cây đó (`data/` vẫn từ ref-root). Phần của công cụ (`_safe` của `golden_capture`) nạp theo đường dẫn từ cây chứa công cụ, nên không phụ thuộc main có công cụ hay không.
- So từng ca:
  - **SAME**;
  - **DIFF**: in trường lệch đầu tiên (đường JSON, vị trí ký tự, độ dài), **không in prompt**;
  - **ONE_FAIL**: một bên không dựng được — tính như DIFF;
  - **BOTH_FAIL**: ghi riêng.
- **ĐẠT = 0 DIFF + 0 ONE_FAIL + mỗi dự án có ≥ 1 ca SAME** (toàn BOTH_FAIL = không so được gì → CHƯA ĐẠT). Mã thoát: 0 = đạt, 1 = chưa đạt, 2 = đầu vào / môi trường sai (không chạy).
- Kiểm trước khi chạy (`_preflight`, lỗi → `ABError`, mã 2): mỗi cây code có `core/runner.py` + `sent_package.py` + `features.py`; file cờ có MỌI cờ trong `FEATURES` (đọc AST) của CẢ HAI cây; worker thật cần native Python 3.14; tệp `--output` chưa tồn tại.
- Cột tham khảo `history_a` / `history_b`: so với gói đã gửi lúc đó (`SAME_AS_SENT` / `SAME_EXCEPT_FINGERPRINT` / `DIFF_FROM_SENT` / `NO_SENT` / `NOT_BUILT`).
- Kết quả: JSON (`--output`, chế độ tạo mới, không ghi đè) + bảng theo dự án in ra màn hình.

## Test — `tests/test_golden5.py` (6 xanh trên cloud + 1 chỉ chạy máy chính)
- Đỏ trên code cũ: tạm cất phần sửa `tools/` thì 6 đỏ → xanh.
- Các ca:
  - `first_diff` chỉ nói đường + vị trí, không lộ chữ;
  - `compare_ab` đủ 4 trạng thái;
  - `run_ab` với 2 cây code tổng hợp: giống → SAME + ĐẠT; khác một dòng prompt → DIFF; một bên lỗi → ONE_FAIL; cả hai lỗi → BOTH_FAIL, không tính lệch;
  - `ab_jobs` chọn job mới nhất mỗi shot / loại + envelope;
  - `code_root` không phải cây code → từ chối;
  - `main_ab` ghi JSON + mã thoát.
- `test_real_worker_two_code_trees_same_and_one_line_changed` (`needs_native_314`): worker thật với 2 bản sao repo, giống → không lệch, đổi một dòng `sent_package` → lệch.
- Test golden cũ (`test_golden2` / `test_golden4` / `test_golden_db_replay`): xanh / skip đúng như trước.

## Rà soát (quy tắc 7) — đã sửa
- CAO: lỗi môi trường / cây code / cờ bị gộp thành INSUFFICIENT_INPUT → toàn BOTH_FAIL → ĐẠT giả. Sửa: `_preflight` + `_native_python()` dừng cả lượt (mã 2); ĐẠT cần ≥ 1 SAME mỗi dự án.
- CAO: worker đọc `prompts/` / `knowledge/` từ ref-root → A và B dùng chung prompt. Sửa: đọc từ `code_root`.
- CAO (test): bản đổi một dòng trong test máy chính thay chuỗi không tồn tại (no-op). Sửa: đổi khóa `"label"` có thật ở `sent_package.py` + assert chỗ đổi tồn tại.
- VỪA: `_job_ref_paths` import `_safe` từ cây code đang so → dùng `_tool_capture()._safe`.
- VỪA: catalog cờ chỉ kiểm theo cây công cụ → kiểm theo `FEATURES` của từng cây.
- VỪA: `main_ab` thiếu UTF-8 stdout, kiểm tệp kết quả sau khi chạy, thiếu `baseline_flags` → KeyError. Sửa cả ba (mã 2).
- THẤP: bắt `subprocess.TimeoutExpired` từng job (→ bên đó lỗi); mỗi dòng ghi `state` của job; bảng ghi chú envelope giả.
- Ghi chú (không sửa): `head_sha` trong manifest lấy từ cây công cụ, `run_ab` không dùng.
- Test thêm: `test_preflight_stops_the_run_instead_of_folding_into_both_fail`; `test_run_ab_…` (toàn BOTH_FAIL → CHƯA ĐẠT); `test_main_ab_…` (tệp có sẵn / thiếu `baseline_flags` → mã 2). Đỏ trên code trước sửa: 3 đỏ → xanh.

## Lệnh chạy mẫu trên MÁY CHÍNH (Windows, Python 3.14 native)
```powershell
cd D:\AI-Video-Pipeline
git fetch origin
git worktree add ..\wt-main origin/main
git worktree add ..\wt-m2 origin/cloud/v31-m2-tichhop
git worktree add ..\wt-golden5 origin/cloud/v31-golden5
# snapshot CSDL chỉ đọc + file cờ (baseline sản xuất = trạng thái hiệu lực máy chính; cờ mới V3.1 = false)
py -c "import sqlite3; s=sqlite3.connect('file:data/manifest.sqlite?mode=ro', uri=True); d=sqlite3.connect(r'..\golden_ab\snap.sqlite'); s.backup(d)"
py -m core.features --json > ..\golden_ab\features_now.json     # rồi dựng flags.json: {"baseline_flags": {cờ: on?}, "experimental_flags": [...]}
cd ..\wt-golden5
py tools\golden_db_replay.py --ab --db ..\golden_ab\snap.sqlite --ref-root D:\AI-Video-Pipeline `
   --flags ..\golden_ab\flags.json --code-a ..\wt-main --code-b ..\wt-m2 --project 24 --project 27 --output ..\golden_ab\ab_24_27.json
```
- `experimental_flags` = các cờ mới của V3.1 có trong nhánh M2: `byd_v2_levels`, `field_guard`, `insert_inherit`, `stage_props_byd`, `sent_package_relpath`… — liệt kê đủ theo `core/features.py` của `wt-m2`.
- `baseline_flags` + `experimental_flags` phải phủ MỌI cờ trong catalog của CẢ `wt-main` và `wt-m2` (thiếu → mã 2), dạng boolean (fail-closed như C-GOLDEN2).

## Giới hạn
- Worker thật chưa chạy trên cloud (Python 3.13): nghiệm thu thật #24/#27 phải làm ở máy chính.
- Envelope giả cho job chưa từng gửi làm `provider = fake`, nên gói không giống gói thật sẽ gửi. Điều này chấp nhận được vì A và B cùng dùng một envelope.

## Full suite (cloud, Python 3.13)
- `-m "not slow" -n auto`: **7154 passed, 5 failed**, 43 skipped, 22 xfailed.
- 5 đỏ đều đỏ y hệt trên nền `origin/cloud/v31-golden4` (đã chạy lại riêng 5 test trên worktree nền), không liên quan diff này (chỉ `tools/golden_db_replay.py` + `tests/test_golden5.py` + `devsys/areas.json` + báo cáo): `test_devsys_plan_map::test_real_plan_and_map_agree`, `test_cost_route_e1::…recut_by_hand…`, `test_end_popup_p24::…icons…`, `test_ffmpeg_studio::…punches_in…`, `test_sent_package::…unreadable_picture…` (chạy bằng root → đọc được tệp "không đọc được").

## GOLDEN6 — negative control đỏ ở máy chính: tìm gốc + sửa (cloud-C, 21/10)

Codex báo (`docs/RA_CX21_GOLDEN5_CODEX_2026-10-21.md`, nhánh `codex/v31-golden5`): sửa một dòng `sent_package.py` ở cây B mà vẫn có `DIFF + ONE_FAIL = 0`.

**Tái hiện trên cloud bằng Python 3.14 native thật** (`uv python install 3.14`, Linux, `sys.prefix == base_prefix`, đã cài requirements). Test `test_real_worker_two_code_trees_same_and_one_line_changed` đỏ y như Codex báo.

**Gốc: lỗi ở TEST, không phải worker nạp sai cây.**
- Test đổi dòng `out = {"label": …}` trong `meta_entry` — nhãn ảnh tham chiếu. Gói của fixture không có ảnh tham chiếu nên dòng đó không bao giờ chạy, và hai bên vẫn giống nhau.
- Thử đổi dòng `"call": call,` ở cây B (mọi gói đều đi qua dòng này) → **2/2 ca DIFF ở trường `call`**. Như vậy worker nạp đúng `core` của `--code-b`.

**Đã sửa** (`tools/golden_db_replay.py`, `tests/test_golden5.py`):
1. Negative control đổi dòng `"call": call,`. Test kiểm:
   - đếm DIFF đúng bằng số ca SAME trước khi đổi;
   - mọi DIFF nằm ở trường `call`;
   - lần chạy "giống nhau" phải có ≥ 1 ca SAME, để toàn BOTH_FAIL không lọt qua như trước.
2. **Bằng chứng nạp đúng cây ở mỗi ca.**
   - Worker `--ab` trả `loaded` = đường dẫn thật của `core.runner` / `core.sent_package`.
   - Công cụ kiểm `loaded_outside` (realpath + normcase) xem các module đó có nằm trong `--code-a` / `--code-b` không. Nạp sai cây → `INSUFFICIENT_INPUT` kèm tên module.
   - Mỗi dòng kết quả A/B có `loaded_a` / `loaded_b`.
   - Đường capture / replay thường KHÔNG mang `loaded`, để fixture không chứa đường dẫn tuyệt đối của máy chụp.
3. **Không đọc `.pyc` trong cây code** (`sys.pycache_prefix` trỏ vào thư mục tạm, chỉ ở `--ab`). Đây là rủi ro THẬT:
   - test `test_stale_bytecode_in_a_code_tree_is_never_used` dựng một `.pyc` cũ cùng mtime + kích thước nguồn;
   - bỏ dòng sửa → test ĐỎ (gói ra theo `.pyc` cũ); có dòng sửa → xanh.
4. Nếu `core` đã được nạp trước từ cây khác → worker từ chối và nói rõ (phòng thủ, vì `-I` không đưa thư mục script vào `sys.path`).
5. Kiểm chữ ký `prompts/` + `knowledge/` cả trước lẫn sau worker đều dùng cây code đang so (`_home_of`). Đây là điểm Codex nêu ở dòng 62.
6. **Tách lý do BOTH_FAIL.** Trước đây mọi trường hợp chung một câu "prepare chờ hoặc cần draft lịch sử"; nay tách thành:
   - `cần draft lịch sử (bản cao nâng từ nháp)` (`_from_sample`);
   - `prepare chờ (_wait)`;
   - `prepare giữ (_hold)`.

**31 BOTH_FAIL của lượt Codex:** cả 31 đều thuộc nhóm "prepare chờ hoặc cần draft lịch sử" — builder không dựng gói mới vì job cần task nháp lịch sử hoặc đang chờ / giữ.
- Đây không phải lỗi của A hay B; A và B ra cùng lý do.
- Cột lịch sử `NOT_BUILT 29` / `NO_SENT 6` chỉ để tham khảo: `NOT_BUILT` = công cụ không dựng được; `NO_SENT` = job chưa từng gửi, nên không có gói để so lịch sử.
- Lượt chạy lại sẽ chia 31 ca theo 3 nhóm mới.

**Test:**
- Python 3.14 native Linux, 5 tệp golden: 165 xanh, 3 đỏ. Cả 3 đỏ đã có từ trước sửa và là ca chỉ đúng trên Windows: `test_unsafe_manifest_path_rejected[C:/outside]`, `test_actual_prepare_build_native[2]`, `test_capture_and_replay_without_sidecar`.
- Negative control và test `.pyc` cũ: XANH.
- Python 3.13: 73 xanh.

**Codex chạy lại trên máy chính:** cùng lệnh `--ab` của C-GOLDEN5 với công cụ HEAD mới của `cloud/v31-golden5`; xác nhận negative control native xanh, và mọi dòng có `loaded_a` / `loaded_b` trỏ đúng worktree.
