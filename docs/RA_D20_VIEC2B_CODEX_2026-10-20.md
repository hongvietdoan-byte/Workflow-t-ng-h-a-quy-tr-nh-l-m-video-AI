# CX20-2b — guard COMPAT và cách ly replay

- Nhánh `codex/d20-viec2b-golden-replay`, nền `9301056b` chưa có golden. Cherry-pick dependency `5ad571b9`, `d28f6213`, `13a3d1d4`, `9187a289` thành `b80eef61`, `d9c11eca`, `ea0776cf`, `688fce78`; không gộp cả nhánh cũ. Giữ areas.version=87, đăng ký tool/test/fixture.
- Hai VỪA: COMPAT bắt buộc toàn bộ cờ `verified is False` trong FEATURES tồn tại và OFF, kể cả experimental_flags rỗng; legacy verified ON được giữ trong structured flags. Catalog đọc AST, không import cấu hình. Cảnh báo đúng queued/running/retryable theo Pipeline.
- THẤP: Git có shutil.which fallback; SQLite dùng closing. API replay_builder chạy native Python whitelist, env/cwd scratch riêng; chỉ worker thay object environ/cwd. Socket/provider/subprocess bị chặn trước import runner; API không thay cwd/env toàn tiến trình gọi.
- ĐỎ **2 failed /35 passed (19,08s)** → XANH **40 passed (34,59s)**; cập nhật fixture đủ catalog và thêm validation replay → XANH **40 passed (26,86s)**. Ba lượt targeted `--tb=no -p no:cacheprovider`, native Python3.14 tuyệt đối; env spawn whitelist, patch.object fake trước import/call, HOME/USERPROFILE/TEMP ngoài repo. Không mạng, API, dữ liệu thật, credential hay cả bộ test.
- Tự rà 2b.5 + related_areas: step2; chung cờ assets/autopilot/core_infra/plates3d/step1, không caller production của helper. Không đổi runner/default/autopilot/đường gửi. Root cần rà độc lập trước gộp. `git diff --check` xanh.

## CAO-M2 OPEN

Chưa dựng `_submit_args/_submit_kwargs` ảnh/video từ snapshot DB và dependency files độc lập. Runner đọc thêm project files, Kho, model selection, cache tạo ảnh; refs trong sent_package không đủ mô tả mọi input. Copy riêng refs rồi roundtrip không chứng minh lịch sử.

Phần kế tiếp đề xuất: capture manifest trước prepare trong worker; SQLite backup từ URI ro vào scratch; fingerprint DB + mọi input file (path tương đối/SHA256), catalog/cờ, provenance `captured_at_capture_not_send`. Scratch chứa toàn bộ dependency allowlist, deny read ngoài sandbox và deny network/provider; fake adapter đúng signature, gọi chính prepare và `_build_package`. File/manifest thiếu → INSUFFICIENT_INPUT; fingerprint DB/file khác → DATA_CHANGED (dữ liệu đã đổi), không CODE_MISMATCH. Stable tại capture chưa chứng minh dữ liệu lúc gửi: package lệch thiếu provenance pre-send → INSUFFICIENT_INPUT. Chỉ CODE_MISMATCH khi có input lịch sử độc lập. Cần regression DB prompt đổi, file đổi, manifest thiếu, stable và đổi code riêng; chưa có API actual nên chưa có các regression này.

## Lệnh phiên chính — chưa chạy

Flags structured phải đủ catalog mới nhất; mọi verified False = false, legacy explicit. Dùng bản sao DB/ref nhất quán; biến shot là scenes.id:

```powershell
py tools/golden_capture.py --db D:/AI-Video-Output/golden-snapshot/manifest.sqlite --project 24 --shot $sceneId24 --flags-file D:/AI-Video-Output/golden-snapshot/compat-flags.json --ref-root D:/AI-Video-Output/golden-snapshot/root --purpose compat --output D:/AI-Video-Output/golden-snapshot/p24.json
py tools/golden_capture.py --db D:/AI-Video-Output/golden-snapshot/manifest.sqlite --project 27 --shot $sceneId27 --flags-file D:/AI-Video-Output/golden-snapshot/compat-flags.json --ref-root D:/AI-Video-Output/golden-snapshot/root --purpose compat --output D:/AI-Video-Output/golden-snapshot/p27.json
```

Replay hiện hữu chỉ khi có pre-send sidecar độc lập: `actual = replay_builder(job['input_snapshot'], ref_root=...)`; `compare_compat(job['sent_package_raw'].encode('utf-8'), actual)`. Không sidecar thì báo thiếu; không nhập args suy từ package. Chưa có command actual DB replay. CX20-2b/M1.9/M2 chưa được mở khóa. Không push/main/TODO/plan/live.
