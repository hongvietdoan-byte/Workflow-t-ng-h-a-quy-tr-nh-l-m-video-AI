# CX20-2b — replay prepare/build từ snapshot DB chỉ đọc

## Phạm vi và kết quả code

- Giải merge có chủ ý `origin/main` `36ec43ad` tại `f17cd48b`: giữ guard/worker 2b, cập nhật đủ catalog FEATURES mới, giữ code upstream và version areas=87. Không push/main/live/TODO/plan.
- `tools/golden_db_replay.py`: SQLite backup từ URI mode=ro sang scratch, không migrate/backfill nguồn. Worker native `sys.executable` Python3.14 `-I -B`, môi trường whitelist, HOME/USERPROFILE/TEMP ngoài repo. API không đổi cwd/env toàn tiến trình gọi.
- Dựng thật bằng ImageRunner/VideoRunner `_submit_args` → `_prepare_kwargs` → `_finish_kwargs` → `_build_package`. Provider chỉ capability/signature public tương ứng Deepix/ClipAI; mọi send/upload/socket/subprocess cấm. Xóa jobs.sent_package ở DB scratch trước builder; prompt/refs/args không lấy từ baseline. Baseline chỉ tới comparator. Chỉ freeze envelope at/external_id/provider từ sổ gửi, không freeze prompt/params từ đó.
- VFS đọc nguồn theo allowlist project pid, asset_images của mục Kho/nhân vật được scene nhắc tới, data/knowledge, knowledge/prompts, pricing/settings/provider_rules public. Không chép ảnh lớn. Fingerprint cả file thực đọc, stat/exists bị thiếu và directory listing; reject traversal/symlink/junction. Audit chặn read ngoài allowlist, nguồn write/rename/remove, socket/subprocess, SQLite ngoài scratch. Code/runtime import chỉ đọc được cho phép riêng; chúng không là dependency dữ liệu. File sinh lại chỉ ghi scratch; tên cache mark dùng path nguồn chuẩn để tránh hash ngẫu nhiên từ tên temp.
- Manifest có DB SHA256/schema, HEAD, full flags, public config, job/envelope, file SHA/missing/directory SHA và provenance `snapshot_at_capture_not_at_send`. Kiểm lại nguồn sau worker để bắt drift trong lúc đọc. public_config chỉ explicit key public, không đọc dashboard.env/User env/key/header. Cấu hình model mặc định và model chọn trong DB thuộc input; cờ trial phải đủ catalog và OFF, legacy verified ON được giữ.
- Kho chủ thể: `supports_subjects` public của ClipAI; fake Library.get dùng đúng active cache SHA/id/asset://URI trong DB scratch, không GET/upload/đẻ URI. Mapping thiếu/processing/thiếu id/list lookup không đủ chứng cứ → INSUFFICIENT_INPUT. Test native gọi helper `_hosted_pictures` thật với seedance_subjects verified ON và cache active; groupflag vẫn OFF. Không chứng nhận reference-only/group đang có `verified=False` bằng cách bật cờ đó.
- Capture có `--database-replay --latest-per-type`, không cần sidecar args. Replay nhận nhiều `--fixture`, xuất project_id/scene_id/type/job_id + summary dedup job, distinct shot ảnh/video, các trạng thái và mẫu số. Không tự chuyển trạng thái kế hoạch hay mở M2.

## Bằng chứng test và tự rà

- Native DB tổng hợp do core.db.connect tạo SCHEMA/migration riêng trong temp, PNG đỏ 16×16; nguồn thật không đọc. Baseline byte đóng băng `tests/golden/db_package_expected.json`, không sinh lại trong test. Poison stored package chứng minh builder không roundtrip; ảnh lấy prompt DB, video lấy motion prompt và ảnh approved từ DB/files.
- ĐỎ đầu: **4 failed /1 passed (2,65s)** → XANH **55 passed (34,58s)**. Bổ sung guard sandbox/cache: **2 failed /60 passed (36,16s)** do test bật nhầm seedance_ref_groups verified=False; guard giữ nguyên, test chuyển sang contract helper hosted thật với chỉ legacy verified ON. Cuối **63 passed (38,38s)**. Các lượt `--tb=no -p no:cacheprovider`; mỗi import/call/spawn dưới patch.object(os, environ, fake dict), không patch.dict clear, không đọc/in/assert/repr real environment hay credential. Lượt thêm có lý do finding mới, không chạy cả bộ.
- Hồi quy: byte ảnh/video, capture/replay không sidecar, poison raw, DB/file/missing file xuất hiện drift, manifest thiếu/traversal, parent cwd/env, source write/os.open, network/subprocess/unknown read, active cached hosted mapping và missing cache, CLI report/distinct shot/INSUFFICIENT riêng.
- Tự rà 2b.5: không đổi production runner/default/autopilot; source path chuẩn khi relative/absolute; tác vụ ghi chỉ scratch, không paid send; không xuất exception/payload/log worker. Diagnostic chỉ loại exception + tên file code/số dòng. related_areas: step2, chung flags assets/autopilot/core_infra/plates3d/step1, caller chỉ capture tool/tests. Rà độc lập và cả bộ trước gộp còn dành root/phiên chính.

## Phân loại bằng chứng, giới hạn còn mở

- Manifest/đầu vào thiếu → INSUFFICIENT_INPUT. DB/file/cờ/config/job/envelope khác capture → DATA_CHANGED, không CODE_MISMATCH. Byte khác ngay lúc capture nhưng không có input lịch sử → INSUFFICIENT_INPUT (không đoán dữ liệu trước gửi). Chỉ baseline đã khớp lúc capture + cùng dependency sau đó nhưng builder lệch mới CODE_MISMATCH. Byte đúng → COMPAT, không suy ra chất lượng đúng.
- Whole DB fingerprint cố ý bảo thủ: DB snapshot thay đổi bất kỳ bảng nào cũng DATA_CHANGED. Dùng cùng snapshot vật lý bất biến cho capture và replay, tránh DB Dashboard live. File ngoài allowlist/asset chưa xác định được trong shot, nguồn dùng symlink, provider/model khác whitelist, `_from_sample`, upload/list registry thiếu chứng cứ, hoặc prepare cần subprocess → INSUFFICIENT_INPUT; không tự đoán/fallback.
- Audit/VFS là guard cho code pipeline tin cậy, **không phải OS sandbox chống Python ác ý**. Socket/Popen và các audit event đã liệt kê được chặn; chưa chứng minh mọi đường native/ctypes/os.system/startfile/registry có cùng bảo vệ. Rà độc lập cần kiểm đúng threat model này; không chạy mã tùy ý hay plugin ngoài trusted pipeline trong worker.
- **Code + lệnh đã có; M1.9/CAO-M2 acceptance thật vẫn OPEN.** Chưa chạy #24/#27, chưa cả bộ Windows, chưa gộp/mở M2, chưa API/provider trả tiền. Phiên chính chụp/chạy nghiệm thu, ghi rõ các ca INSUFFICIENT_INPUT; chúng không được tính thành COMPAT. Rà độc lập code còn mở.

## Lệnh phiên chính (0 USD, chưa chạy)

Chuẩn bị DB snapshot rời bất biến và thư mục output ngoài repo. ref-root là nguồn file cho snapshot, worker chỉ đọc; DB không được trỏ live Dashboard. Flags structured `{flags: {...}, experimental_flags: [...]}` phải có mọi verified False=false; legacy theo explicit cấu hình, không lấy secret/provider env. Các biến scene IDs là `scenes.id` của **3 shot khác nhau**, đủ approved image + approved motion. Điền các ID đã chọn, không nhập sidecar args.

```powershell
$db = 'D:/AI-Video-Output/golden-snapshot/manifest.sqlite'
$root = 'D:/AI-Video-Pipeline'
$out = 'D:/AI-Video-Output/golden-snapshot'
$flags = "$out/compat-flags.json"
# $scenes24 và $scenes27: mỗi biến chứa ít nhất 3 scenes.id khác nhau do phiên chính chọn.
foreach ($sid in $scenes24) {
  py tools/golden_capture.py --db $db --project 24 --shot $sid --flags-file $flags --ref-root $root --purpose compat --database-replay --latest-per-type --output "$out/p24-s$sid.json"
}
foreach ($sid in $scenes27) {
  py tools/golden_capture.py --db $db --project 27 --shot $sid --flags-file $flags --ref-root $root --purpose compat --database-replay --latest-per-type --output "$out/p27-s$sid.json"
}
$replayArgs = @('--db', $db, '--ref-root', $root, '--output', "$out/replay-24-27.json")
foreach ($sid in $scenes24) { $replayArgs += @('--fixture', "$out/p24-s$sid.json") }
foreach ($sid in $scenes27) { $replayArgs += @('--fixture', "$out/p27-s$sid.json") }
py tools/golden_db_replay.py @replayArgs
```

Owner kiểm từng project 24 và 27: `distinct_compat_image_shots >=3`, `distinct_compat_video_shots >=3`; `compat_percent_complete_input=100` (mẫu số COMPAT+CODE_MISMATCH); DATA_CHANGED/selected_cases ≤1/3. Selected cases là job duy nhất được chọn, không phải số take đếm lặp. DATA_CHANGED kèm lý do; INSUFFICIENT_INPUT riêng và không đếm vào 3 shot xanh. `acceptance=OPEN_OWNER_ONLY_24_27` luôn giữ cho người nghiệm thu quyết, không tự mở M2.
