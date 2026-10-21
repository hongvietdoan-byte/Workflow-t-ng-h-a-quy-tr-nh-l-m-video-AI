# Rà CX21-GOLDEN — 21/10/2026

Phạm vi: sửa công cụ chụp/replay ngoại tuyến theo `docs/CODEX_TASKS.md` CX21-GOLDEN.
Nhánh `codex/v31-golden-fix`, nền `a3a4e75c`. Không đọc snapshot sản xuất, không sửa dữ liệu thật,
không gọi provider/API, không đổi cờ, không push/main/TODO. Nghiệm thu thật #24/#27 vẫn **OPEN**.

## Thay đổi

- `--latest-per-type`: job cuối thiếu prompt (kể cả raw NULL/hỏng) theo `source_job_id` tới bản nguồn
  có prompt; mỗi bước kiểm cùng project/scene/type, phát hiện vòng lặp/nguồn thiếu. Gói không an toàn
  không được dùng. `selected_job_id` giữ ID cuối, `id` là nguồn thực sự được dựng/so byte.
- Ca thiếu nguồn/gói hỏng/provider-model thiếu hoặc lỗi dựng riêng ca trả INSUFFICIENT_INPUT và tiếp tục.
  Chế độ capture thường giữ kiểm đầu vào chặt như trước.
- VFS thêm quyền FILE ảnh được job tham chiếu trong `data/_plates3d/cache/` và `data/assets/`.
  Không mở subtree; file đọc đi qua kiểm symlink/junction, hash và dependency manifest hiện có.
- Diagnostic chặn gồm loại + đường dẫn tương đối root; ngoài root thay `<outside-root>`. Không xuất
  exception message, payload, credential hay stdout/stderr worker. Ca không có manifest vẫn giữ diagnostic khi replay.
- BUILT lệch byte ngay khi capture vẫn INSUFFICIENT_INPUT; README ghi cách chọn shot và lệnh chụp lại.

## Bằng chứng và giới hạn

- Đỏ trước: 3 test source hợp lệ/thiếu/khác type đều đỏ trên code cũ.
- Lượt xanh 1: 74 qua, 1 đỏ do audit diagnostic nhánh utime dùng biến path chưa gán; đã đổi sang arg.
- Lượt xanh 2: 77 qua trong 57,36 giây (hai file golden). Sau đó bổ sung ca NULL/hỏng, vòng lặp,
  provider thiếu và lỗi dựng per-case theo finding tự rà/root. Kết quả lượt cuối ghi ở mục cuối.
- Các test mới dùng DB/ref tổng hợp; `patch.object(os, 'environ', {})` trước import/call/spawn ứng dụng;
  native subprocess có env whitelist. Test native đọc plate/asset đúng FILE thành công, chặn sibling và
  kiểm diagnostic path tương đối. Test cũ vẫn kiểm hash manifest và DATA_CHANGED khi ref đổi.
- Không sửa baseline/hạ ngưỡng hay nới test. Chỉ chạy test liên quan, không chạy cả bộ ở nhánh con.
- `related_areas.py` chỉ ra step2 và vùng dùng chung cờ assets/autopilot/core_infra/plates3d/step1;
  tự rà 2b.5: không sửa pipeline/cờ, không mạng/subprocess trong sandbox, không nâng COMPAT khi thiếu lịch sử.
  Code và test đều đã khai trong `devsys/areas.json`; không thêm file mã mới, giữ version 88.
- Fresh review độc lập và cả bộ test do phiên gộp thực hiện. Chưa chứng minh chất lượng/COMPAT dữ liệu thật.

## Phụ thuộc / va chạm tích hợp

`tools/golden_db_replay.py` cùng file với CX21-FIX `b3f34f0a` (native Python3.14/venv failclosed).
Nhánh GOLDEN chỉ đổi permission/_worker, comparator replay thiếu manifest, exception diagnostic; giữ nguyên
`build_from_database` runtime. Khi gộp giữ cả runtime FIX và worker GOLDEN. README chỉ thêm đoạn cuối,
không thay phần SHA DB/hash-mtime của FIX. Lệnh nghiệm thu lại ở cuối `tests/golden/README.md`.

Kết quả cuối: **88 passed trong 59,79 giây**, native Python 3.14, lệnh:
```
C:/Users/hongviet.doan/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pytest tests/test_golden_replay.py tests/test_golden_db_replay.py -q --tb=no -p no:cacheprovider
```
Lượt bổ sung cuối có lý do: lỗi audit utime + các ca NULL/malformed/cycle/provider/per-case mới phát hiện.
`git diff --check` sạch. Không chạy nghiệm thu thật #24/#27; không khẳng định COMPAT sản xuất.

## Rà kỹ độc lập

- Đã đọc diff `a3a4e75c..47a0a9bc` và các chỗ gọi: source chain cùng project/scene/type,
  NULL/hỏng/vòng lặp, tiếp tục từng ca; quyền FILE plate/asset và manifest; baseline chỉ cấp quyền
  trước khi bị mask NULL, không đưa prompt/args vào builder; diagnostic; comparator và CLI.
- `related_areas.py` xác nhận vùng step2, không có khu vực gọi tới module đổi; các vùng dùng chung
  cờ assets/autopilot/core_infra/plates3d/step1 không bị thay đổi. Không tìm thấy finding cần sửa.
- Đính chính thử nghiệm trong phiên rà: giả định NUL path phát ValueError không đúng với native
  Python 3.14 Windows; phép thử trực tiếp trả `missing`. Ca OSError chỉ dùng mock, chưa tái hiện
  lỗi Windows thật. Hai test thử ban đầu đỏ **không phải bằng chứng hai bug sản phẩm**.
  Đã bỏ toàn bộ test và catch thử nghiệm, giữ nguyên code tại `47a0a9bc`.
- Lượt gom thử có 89 qua/1 đỏ trong 82,99 giây: gồm 88 test hiện có qua, một ca OSError mock qua,
  một ca NUL đỏ do kỳ vọng sai đã bỏ. Không ghi lượt này là cả bộ xanh; bằng chứng sạch trước rà
  vẫn là 88 passed/59,79 giây ở trên. Không chạy lại bộ không thay đổi.
- Không đọc snapshot/dữ liệu thật, không API/provider, không thay TODO/main/cờ hay areas version 88.
  Nghiệm thu thật #24/#27 vẫn OPEN; giữ runtime guard CX21-FIX `b3f34f0a` khi tích hợp.
