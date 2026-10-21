# C-GOLDEN4 — sửa gốc công cụ nghiệm thu golden (cloud-E, 21/10)

Nhánh `cloud/v31-golden4` tách `origin/cloud/v31-m2-tichhop` @ 9746a6ea (công cụ C-GOLDEN2 chỉ có ở đó). Gốc: nghiệm thu lần 3
(`docs/RA_CX21_GOLDEN3_CODEX_2026-10-21.md`, nhánh `codex/v31-golden3`) KHÔNG ĐẠT vì CÔNG CỤ, 0 CODE_MISMATCH. Chỉ sửa `tools/golden_*`, fixture test.

## Đã sửa
1. **Đọc dependency — sửa gốc, không vá từng thư mục** (`tools/golden_db_replay.py`): `_worker.allowed()` trước liệt kê từng thư mục
   (lần 1 thiếu `data/_plates3d`, lần 3 thiếu `data/skills` → 60/68 ca INSUFFICIENT_INPUT). Nay worker ĐỌC mọi tệp dưới `data/` của ref-root
   (+ `knowledge/`, `prompts/`), chỉ đọc; MỌI lần đọc qua `locate()` vào manifest có sha (tệp) / `directory_sha256` (thư mục) như cũ — replay so
   manifest, đổi = DATA_CHANGED. Hỏi tồn tại / kích thước (`os.stat`, `exists`) chỉ ghi `{"stat": cỡ}` — chỉ MỞ tệp mới băm sha (không DATA_CHANGED
   giả khi tệp không liên quan đổi nội dung, không băm lại tệp lớn). **Cấm cứng** (`read_denied`, không phân biệt hoa thường): mọi `*.sqlite*` /
   `*.db*` (CSDL live — worker chỉ dùng snapshot), mọi biến thể `.env` (`dashboard.env`, `x.env.local`, `.env.bak`), `*.log` / `*.bak` / nén,
   `data/backup*`, tệp khóa (`.key/.pem/.p12/.pfx/.crt`, `id_rsa`), tên có token/secret/password/credential/cookie/api_key/owner_setup_code/
   service_account (trừ ảnh: `gold_token.png` là ảnh Kho), tên kiểu NTFS lạ (`:`, khúc kết thúc `.`/dấu cách). Lần chặn vì bí mật có kind `secret`
   (không bị gán DATA_CHANGED). Đọc thẳng qua audit hook kiểm `realpath` nằm trong nguồn/scratch (symlink ra ngoài bị chặn).
   Ghi / đổi / xóa / mạng / subprocess / sqlite ngoài scratch vẫn chặn như cũ (audit hook không đổi).
2. **replay_fixture giữ DATA_CHANGED của capture**: capture không manifest mà `classify_answer` đã phân loại DATA_CHANGED có `paths` → giữ
   DATA_CHANGED (+ `paths`), không gộp thành INSUFFICIENT_INPUT; DATA_CHANGED do race lúc chụp (không `paths`) vẫn INSUFFICIENT_INPUT.
3. **Chuỗi source_job_id** (`tools/golden_capture.py`): ca đứt ghi `chain` (id đã đi) + `broken` (job nào → nguồn nào, nguồn không tồn tại / khác
   type / dự án / shot, vòng lặp, thiếu id) — chỉ id/kiểu, không prompt/gói. 4 ca lần 3: chạy lại capture sẽ in chỗ đứt (dữ liệu thật ở máy chính).
4. `tests/golden/package_inputs.json`: thêm `sent_package_relpath: false` (ảnh + video) — codex lần 3 phát hiện thiếu (validate_compat_flags fail-closed).

## Test (Python 3.14 NATIVE trên cloud — `uv python install 3.14`, không venv)
- `tests/test_golden4.py` (mới; sau rà: 49 test): danh sách cấm (13 tên) / không cấm (7); replay giữ DATA_CHANGED; chuỗi đứt in `chain` + `broken`;
  worker 3.14 đọc `data/skills/x.json` → `files` có sha; worker đọc `dashboard.env`, `data/backup/…`, `data/x.env`, `data/manifest.sqlite` nguồn → bị chặn.
  **Code cũ: 23 đỏ / 1 xanh** (ca "vẫn cấm env…" xanh cả trước) → code mới 24 xanh (3.14); 3.13: 22 xanh + 2 skip (worker).
- `tests/test_golden_db_replay.py::test_worker_reads_only_job_ref_and_reports_blocked_sibling` → đổi thành `…_reads_job_ref_and_sibling_into_manifest`
  theo đề mới (tệp anh em dưới data/ ĐỌC ĐƯỢC + vào manifest) — đổi luật theo đề, không nới để che lỗi.
- Golden (3.14, `test_golden4` + `test_golden_db_replay` + `test_golden_replay` + `test_golden2`): **155 qua, 3 đỏ** — cả 3 đỏ sẵn trên nhánh tích
  hợp cùng máy (trước sửa 11 đỏ: 8 `test_golden_replay` hết đỏ nhờ thêm cờ fixture). 3 đỏ còn lại do MÔI TRƯỜNG Linux, không do công cụ:
  `test_actual_prepare_build_native[2]` + `test_capture_and_replay_without_sidecar` (sha ảnh PNG Pillow tạo trong fixture khác bản Pillow máy chính →
  so `db_package_expected.json` lệch), `test_unsafe_manifest_path_rejected[C:/outside]` (đường dẫn ổ đĩa Windows là tương đối trên Linux).

## Chạy lại nghiệm thu lần 4 (codex, máy chính, Python 3.14 native)
Như lần 3 (`docs/RA_CX21_GOLDEN3_CODEX_2026-10-21.md` mục "Nguồn và giới hạn"), đổi mã công cụ sang `cloud/v31-golden4`:
```
git worktree add D:/AI-Video-Output/golden-wt4 origin/cloud/v31-golden4
# snapshot CSDL mới (SQLite backup, mode=ro) như lần 3; ref-root chỉ đọc D:/AI-Video-Pipeline
py -3.14 tools/golden_capture.py --db <snapshot> --project 24 --shot <id> --flags-file <baseline> --ref-root D:/AI-Video-Pipeline --output <fixture> --purpose compat --database-replay --latest-per-type   (mọi shot #24/#27 như lần 3)
py -3.14 tools/golden_db_replay.py --fixture <fixture> --db <snapshot> --ref-root D:/AI-Video-Pipeline --output <report>
```
Đọc thêm trong kết quả: ca chuỗi đứt (`chain`, `broken`), ca DATA_CHANGED giữ `paths`. Ngưỡng không đổi: mỗi dự án ≥ 3 shot ảnh + ≥ 3 shot video COMPAT, 0 CODE_MISMATCH.

## Rà khâu liên quan (quy ước 7, agent) — đã sửa
Không CAO. VỪA-1 danh sách cấm sót biến thể (`.env.bak`, `.log`, `.sqlite3`, `Backup/`, `::$DATA`…) → so casefold + khúc tên + tên NTFS lạ (test 16
tên mới). VỪA-2 ảnh Kho có chữ "token" bị cấm rồi gán DATA_CHANGED → ảnh bỏ qua từ khóa + kind `secret`. VỪA-3 `exists`/`stat` băm cả tệp → DATA_CHANGED
giả + chậm → ghi `{"stat": cỡ}`. THẤP: bỏ `allowed("data")` (listdir gốc data/ trả scratch); symlink qua audit hook → kiểm realpath (test symlink);
replay giữ DATA_CHANGED chỉ khi có `paths`. Để lại (THẤP, ghi nhận): `asset_images` không phải ảnh vẫn làm cả job INSUFFICIENT; `asset_paths` /
`_job_ref_paths` nay thừa; tệp mới chỉ đọc lúc replay → INSUFFICIENT (manifest) thay vì CODE_MISMATCH; `cv2.imread` (mã C) không phát audit —
đọc ảnh tuyệt đối không qua sandbox (có từ trước).

## Rủi ro / việc mở
- Đọc rộng hơn → manifest lớn hơn; tệp dưới data/ đổi giữa capture và replay (kể cả không liên quan nếu builder liệt kê thư mục) → DATA_CHANGED
  thật (đúng ý "dữ liệu đổi"), cần capture + replay trên CÙNG snapshot/ngày.
- Danh sách cấm theo tên: credential đặt tên lạ dưới data/ sẽ đọc được (chỉ vào manifest dạng sha, không xuất nội dung) — rà ở mục dưới.
- Rollback: revert 2 tệp `tools/golden_*` (fixture cờ giữ).
