# Rà Đ12 việc 2 · nối caller Bước 5

Nhánh `codex/d12-viec2-noi-sfx`, nền `43205faf`; code **ffac01b1 đã push**, root đã rà lần hai và QA 1440/1280. Chưa gộp main/chạy cả bộ.

## Luồng và quyền

- Nút code chủ động 0 USD dùng chung `sfxplan_<pid>` + `sfx_table_<pid>` + `sfx_apply_<pid>`, không tự áp sau proposal. Không tự gọi Claude; unmet hiện đúng schema nhánh, AI bổ sung dùng nút existing có ước tính phí.
- Đối chiếu component base: `motion_sfx_propose_<pid>` giữ; **RENAMED** `motion_sfx_result_<pid>` → `sfxplan_<pid>`; **REMOVED** `motion_sfx_optin_<pid>`/checkbox và expander riêng có chủ đích: nút code là opt-in trực tiếp, chỉ một bảng duyệt.
- Cờ OFF/OPT_IN_ONLY; experimental không bật ngầm. API đọc `propose_motion` giữ `need_view`; wrapper `propose_motion_review` cần edit. Handler kiểm quyền trước provider, apply kiểm edit trước ghi; readonly code/apply disabled.
- OFF không chạy proposal/đo/SHA mới. ACL của nút AI và apply được harden **luôn**, kể cả OFF: đây là thay đổi bảo mật có chủ ý, **không khẳng định mọi đường OFF bất biến từng byte**. AppTest OFF+readonly bấm AI bị từ chối trước client/provider forbidden.

## Sửa gom sau rà độc lập

1. P2 I/O rerun: Step5 dùng `motion_current(..., strong=False)` chỉ DB/catalog/clip metadata/stat. Apply bắt buộc SHA mạnh trước stage và ngay trước manifest commit; stat không phải điều kiện chấp nhận cuối. Overwrite cùng size/mtime vẫn bị SHA phát hiện.
2. P2 phạm vi/budget: helper `core/motion_sfx_safe.py` chuẩn hóa absolute server data root; clip thuộc dự án trong videos/trash/videos/assets/takes và đuôi video cho phép; reject URL/UNC/relative/outside/symlink/junction/special trước mở. Preflight ≤128 clip, ≤512 MiB/file, ≤2 GiB/lô; đọc streaming 1 MiB có deadline 20s, kiểm size/dev/inode/mtime trước/sau. Đây là deadline kiểm giữa các chunk, không hứa ngắt syscall I/O bị treo.
3. P2 snapshot: SHA trước/sau timeline/BYĐ/đo; trong mỗi SHA kiểm metadata trước/sau. Payload gồm scenes.data/motion, full clip metadata (path/requested duration/state/usable/extra/scene_id…), trusted catalog metadata, transition/fade. Catalog đổi tên/drop/phân loại cùng ID làm stale; không băm toàn Kho trên rerun.
4. P3 selection: index int không bool, trong phạm vi, duy nhất; số hữu hạn không bool/string trước cast. UI truyền raw số vào wrapper, giữ scene/anchor_idx, tính lại offset; validator lõi chặn negative offset/outside shot/NaN/volume trước ghi.
5. An toàn dữ liệu đường mới: stage dùng `apply(..., _directory=stage)`; copy đủ âm vào file `motion_<uuid>` mới, manifest candidate; `os.replace` chỉ sau kiểm snapshot mạnh và bytes manifest chưa đổi. Không ghi đè file cũ, không xóa file cũ/manual. Copy/validation/CAS lỗi giữ manifest cũ và dọn đúng các file mới của lần chạy.
6. Âm được chọn phải còn trong trusted catalog, nguồn thuộc `sound_sources.path` đăng ký, absolute regular local/no links và budget. SHA nguồn trước stage, so SHA bản copy và nguồn sau stage; nguồn đổi thì fail closed.
7. `ensure_duration` legacy có UPDATE duration/kind + commit: stage **không gọi**, chỉ đọc duration metadata/None để không tự ghi Kho hoặc tự đổi fingerprint. Test duration=None chạy helper+apply thật và chứng minh không gọi ensure_duration; không claim đã đo. Render downstream xử lý duration thiếu theo hành vi existing.

## Bằng chứng và giới hạn

- Writer trước rà: RED4 →59 GREEN/3,31s; 6 lượt hẹp (đã ghi vượt mức quy trình).
- Rà/sửa: RED7 selection/freshness/snapshot/scope + RED atomic copyfailure; sau sửa 77 xanh/4 fail do test thiếu import Path; sửa test import →85 xanh/3,14s; thêm root yêu cầu Kho/duration/OFF →88 xanh/4,02s; chỉnh UI raw numeric → **88 passed /4,28s**. Tổng 6 lượt pytest hẹp trong vòng rà/sửa; ghi rõ vượt 2–3, không chạy rộng/cả bộ.
- Lệnh cuối: `py -m pytest -q tests/test_motion_sfx_caller.py tests/test_motion_sfx.py --tb=no -p no:cacheprovider`; `git diff --check` sạch ngoài cảnh báo CRLF.
- Các hồi quy gồm atomic copyfailure, manifest conflict, nguồn âm đổi lúc stage, manifest unsafe, source ngoài registered/trusted Kho, atomic helper+apply thật giữ manual/oldfiles, budget/path/special/deadline, catalog/clip state stale, readonly/OFF/provider forbidden.
- AppTest actual `sfx_assistant`: code→review→apply giả, readonly/OFF. Fixture và harness ngoài repo dùng clip `<fake>/7/videos/clip.mp4`, fake os.environ OBJECT trước imports/calls; provider forbidden; không credential/data thật. Harness root `D:/AI-Video-Pipeline/.codex-wt/_qa_motion_sfx_step5.py`.
- Lock `.motion_sfx.lock` chỉ phối hợp caller mới. CAS bytes+replace **không phải CAS tuyệt đối** với writer legacy không dùng lock: writer khác có thể chen giữa so manifest và replace. Crash có thể để file mới mồ côi; file AI cũ cố ý giữ để không xóa tài sản trước commit. Không sửa toàn bộ audio_lib/legacy paid AI.
- Snapshot pre/post và kiểm file fail closed với thay đổi quan sát được; không tuyên bố khóa toàn bộ DB/filesystem trước mọi writer không phối hợp/ABA.
- Rà lần hai của root đã đọc diff sửa: scoped/bounded I/O, metadata/catalog freshness, selection raw numeric, stage chỉ đọc duration, giữ manual/oldfiles và giới hạn CAS legacy. Không còn lỗi chặn trong phạm vi caller; các giới hạn trên vẫn mở.
- QA root Edge headless trên Windows, component `sfx_assistant` thật ở cổng fixture 18635: 1440/1280 đều code→bảng duyệt→apply giả 1 cue, readonly khóa nút code; 0 pageErrors và không overflow ngang. Provider forbidden, môi trường/SQLite/clip giả. Hai ảnh `docs/images/d12/sfx_step5_1440.png`, `sfx_step5_1280.png` đã xem bằng mắt; metrics `sfx_step5_metrics.json`. Hai lượt locator/scroll/ghi metrics QA sai đã sửa trước lượt cuối; không sửa production để che QA. Server fixture thuộc lượt chạy đã dừng, không restart live.
- `core/motion_sfx_safe.py` và tests/fixture khai areas, version giữ **76**. Không sửa TODO/main/live/runner/admin_auth/maintenanceworker; không API/tiền. Chưa clip/BYĐ thật/chất lượng âm, chưa cả bộ Windows; root QA screenshot 1440/1280 bổ sung sau.
