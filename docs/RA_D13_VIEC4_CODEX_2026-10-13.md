# Rà Đ13 việc 4 — Codex LOCAL Windows, 13/10/2026

Nhánh `codex/d13-viec4-ton-dong`, base `e95b9779`, areas.version 68 giữ nguyên. Mức **RÀ KỸ** vì tiền/phiếu/quyền dữ liệu/vòng đời autopilot; root giao phiên rà độc lập trước commit/gộp. Chưa commit/push/cả bộ, không API trả tiền, không dữ liệu/khóa thật, không sửa runner/admin_auth hay máy chính.

## Phạm vi đã làm

1. `layout_drift_review`: mỗi lượt proposal đóng mục cũ của cùng shot khi nội dung khác hoặc lượt mới không còn lệch; giữ mục applied độc lập. Hiện tên thư mục lượt thay đường tuyệt đối máy.
2. `_safe` phiếu nhận `/24 shot` và `/lý do cần sửa`, vẫn chặn đường Unix từ hai đoạn, UNC, ổ Windows/base64/secret như cũ.
3. `short_lock_outfit`: chỉ bỏ digest khi ít nhất một outfit_images có reference_problem None; ID mất/hỏng/oversize giữ digest. Cờ OFF giữ nguyên và không đọc outfit_images. Không đổi full lock_text (ngoài đề).
4. Bỏ ba nhánh seconds=None và import resolve_model lặp: video_reference_seconds luôn trả float (thiếu đo tính dư 15s và warnings). **Chưa làm O(n²) cost.video_need**, root giữ dependency `27c2e9f3` ngoài main; không sửa cost/project_budget.
5. package_overrides ghi rõ fingerprint khóa hiện tại có thể stale bản cũ, save/undo bắt buộc base_refs list kể cả gói rỗng; kiểm sớm và thông báo tải lại gói. Chưa có caller sản xuất; không migration.
7. Pet đếm waiting_admin + waiting_merge, giữ toast/dedupe/URL allowlist. Watchdog và hello proof chỉ validate token/Owner/cờ, snapshot vẫn xác minh và đọc đầy đủ; revoke token khi stop/reauthorize/invalidate/lỗi lưu credential. Caption không Owner ở sidebar. GUI Windows thật còn chờ máy chính (CUA native unavailable).
8. scan phát hiện file đổi xóa heard/label/score/accent/duration, voice về schema default0 (NOT NULL); unchanged giữ metadata. Cờ mới `ambience_voice_guard` OFF/OPT_IN_ONLY: nhãn giọng phụ score>=sound_ai.TRUST=0.40 loại khỏi âm nền, OFF giữ chọn cũ. Không lọc kind=sfx; âm nền dài music vẫn được xét.
9. director_busy theo code là bận tạm: autopilot giữ RUNNING, diag warn, chờ tick sau, không retry/gọi trả tiền trong tick. UI đọc sổ lease failclosed+VÀNG, không lộ exception/path. Video hiện nhãn manifest NHÁP; màn giao ẩn warning nháp cũ khi final fresh. measured_size resolve theo cwd như collect_clips (giữ guard URL/UNC và cache). `delivery_unknown_guard` OFF/OPT_IN_ONLY chỉ thêm guard dự án cũ thiếu khung, ON báo cách sửa; knownHD guard giữ. check.load_dashboard_env thêm HKCU Environment đúng4key launcher, Process/file ưu tiên, chỉ mock registry trong test.

## Đỏ → xanh (nhóm liên quan, PYTHONUTF8=1, py pytest -q -p no:cacheprovider)

- Mục1–5: 11 failed/91 passed/1 xfailed → nhóm5file 169 passed/1 xfailed, 34.50s.
- Mục7–8: 4 failed/74 passed → 79 passed, 43.38s. Vòng xanh đầu bắt voice NOTNULL và fixture sidebar mới; sửa theo schema, không nới test.
- Mục9 + guard phụ: 6 failed → 6 passed, 0.90s; draft UI 2 failed → 2 passed, 0.76s.
- Nhóm cuối 12file: **357 passed, 1 xfailed, 10 subtests passed / 104.41s**.
- Tự rà lifecycle phát hiện rò token khi bind lỗi và credential viết dở: **2 failed → nhóm pet 45 passed / 7.17s**; bổ sung cleanup theo token/grant cụ thể.
- QA fixture TEMP `C:/Users/HONGVI~1.DOA/AppData/Local/Temp/codex_d13_component_49kjdyke/app.py`: AppTest **0 exception**; root chụp Chrome1440/1280 sau. Chạy `py -m streamlit run <app.py> --server.port 8513 --server.address 127.0.0.1 --server.headless true` từ worktree. Bốn khối step4label480p/step5freshkhôngwarning/step5missingwarning/leaseDBlỗiVÀNG+disabled. DB/assets/data/flags/knowledge TEMP, provider mock; ffmpeg clip màu cục bộ.
- Phiên rà độc lập đang gom finding; worker chưa sửa vòng tiếp/không commit, chờ reviewer sửa gộp theo root. Isolation LLM_PROVIDER trong test env mock sẽ do reviewer sửa; không coi test cuối thay cho review/cả bộ.

Test Đ8 cũ đổi có chủ ý: test_v3_trial... đòi absolute path chuyển sang `(new)` và cấm tmp_path; test_short_lock_matches_full_lock_outfit_policy vẫn kiểm fullLockOUTFIT nhưng yêu cầu shortdigest giữ khi refs=[] (ID 1/99/spaces/broken); test_proposal_dedupe_and_revert... đổi open proposal sang resolved và giữ applied open. Đây đổi hợp đồng đề Đ13, không bỏ assert; thêm các ca lượt2/IDassignedunusable/slashpath/base_refs/lifecycle/secondarySpeech/OFF/cwd/UI/legacyguard/HKCU.

## Rà caller và giới hạn

Đã chạy related_areas cho19filecode: core_infra/diag/step1/step4/devsys/step5/autopilot; callers step2/dashboard/assets/step3/knowledge/budget/lipsync. Test CHẬM bắt buộc ở bước gộp (root), chưa chạy cả bộ. Caller stage_grid transaction giữ; applied/proposal source riêng; short_lock_block dùng motion_bundle, không đổi Lock dài. Giá ref luôn float, cảnh báo/ước tính dư giữ. UI script-cta/replan giữ keys, thiếu sổ khóa không gửi; snapshot có auth và readonly DB như cũ.

Tự rà skill2b.5: relative/cwd bằng test, OFF giữ cách cũ, luồng auto dùng mã lỗi riêng; không đọc nhãn như nội dung âm (chỉ parsed heard YAMNet score); không đổi khớp tên/bỏ dấu; không mạng/API mới; UI không paid trước click. Chưa thử production/model thật/GUI Windows thật. Scan vẫn nhận thay đổi bằng size/mtime giây như trước, cùng size/cùng giây có thể chưa nhận — ngoài phạm vi migration/hash. Mục6 seedance_refs chờ máy chính; mục9 cost-budget/FALLBACK root đối chiếu, không đánh dấu trọn Đ13 việc4 xong.

## Rà độc lập trước commit — 13/10/2026

Phiên rà riêng chỉ đọc code/tests, base `e95b9779`; không sửa triển khai, không chạy lại nhóm xanh/cả bộ. Đọc luật Đ13, CLAUDE quy ước 7, CHUAN và skill 2b.5. Chỉ bổ sung mục báo cáo này theo yêu cầu root.

- **P2 còn mở — `tools/lao_dai/channel.py:174–175`:** `_authorize` cấp token mới trước `self.stop()`. Khi credential cũ không xóa được (`delete_if` ném PermissionError), stop thu hồi token cũ nhưng token mới không được revoke. Tái hiện bằng cả Broker giả và **SnapshotBroker thật**, users/sessions SQLite tạm: `tokens_remaining=1`, `active=False`. Sửa: cleanup token mới bao trọn stop/setup, trước mọi thoát do lỗi; giữ xác thực phiên mới trước khi ngắt phiên cũ. Test: reauthorize khi delete_if thất bại, assert không token mới/grant/server còn hoạt động; không ghi/in token.
- **P2 còn mở — `tests/test_adapters.py:561–562`:** file fixture có `LLM_PROVIDER=mock` nhưng monkeypatch chỉ quản lý bốn khóa token. Khi ban đầu chưa có LLM_PROVIDER, sau teardown vẫn còn biến này, làm bẩn môi trường cho test sau. Tái hiện gọi chính test trong MonkeyPatch.context với os.environ giả rỗng: `test_teardown_leaks_LLM_PROVIDER=True`. Sửa: đăng ký LLM_PROVIDER với monkeypatch trước load hoặc cô lập toàn bộ môi trường; kiểm teardown khôi phục trường hợp ban đầu thiếu/có giá trị.

Kiểm bổ sung SnapshotBroker thật trên DB tạm chỉ có users/sessions: validate hợp lệ không đổi byte DB; Owner disabled và flag OFF bị từ chối; Owner disabled thu hồi token; patch admin_snapshot ném lỗi không bị gọi. Đã đọc sửa bind failure/partial credential write của worker, hai nhánh đó đã cleanup. Các hợp đồng proposal/outfit/phiếu/âm thanh/lease UI/director_busy/nháp/cwd/OFF đọc không thấy lỗi mới. Test cũ đổi assertion khớp hợp đồng mới, không bỏ kiểm.

**Kết luận thời điểm rà: còn hai P2 cần xử lý trước commit.** Không kiểm API/dữ liệu/khóa thật/GUI Windows; cả bộ và slow bắt buộc để bước tích hợp. Giữ các việc ngoài phạm vi đã nêu phía trên.

## Vòng sửa gộp hai P2 — hoàn tất 13/10/2026

- Lifecycle: bảo vệ `self.stop()` sau issue bằng cleanup token mới khi stop lỗi; giữ xác thực Owner trước khi ngắt grant cũ. Regression dùng SnapshotBroker thật, SQLite users/sessions tạm, credential giả: delete_if lỗi không còn token/grant/server; DB không đổi byte. Bốn ca watchdog thật (Owner disabled, session revoked, flag OFF, token expired) đều thu hồi grant/token/credential, không gọi admin_snapshot, không ghi DB.
- Fixture env: thay os.environ bằng dict giả trong test HKCU, monkeypatch khôi phục nguyên đối tượng môi trường khi teardown. Regression kiểm cả LLM_PROVIDER ban đầu thiếu và có giá trị giả; không nới assertion. Không dùng delenv absent để giả định sẽ có undo.
- ĐỎ: nhóm `tests/test_lao_dai_gui.py tests/test_adapters.py` **2 failed / 68 passed**. Lượt giữa **1 failed / 69 passed** xác nhận delenv absent không khôi phục; thay bằng môi trường giả. XANH cuối: **70 passed / 7.24 s**, `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider tests/test_lao_dai_gui.py tests/test_adapters.py`. Không chạy lại nhóm 357/cả bộ.
- Root cung cấp QA component Chrome thật 1440/1280: 0 lỗi/overflow, đúng hai warning nháp, final fresh không warning, lỗi lease khóa nút; ảnh `docs/images/d13/component_1440.png` và `component_1280.png`. Phiên sửa không chạy lại QA/native pet.

**Kết luận sau sửa: hai P2 trên đã đóng; root đọc diff vòng sửa trước commit.** Cả bộ và slow vẫn chờ tích hợp; cost O(n²) chờ dependency, mục6 seedance chờ máy chính; không đánh dấu toàn Đ13 việc4 hoàn tất. Không commit/push, API, dữ liệu thật hay admin_auth.

## Chốt của root
Đã đọc diff sửa hai P2 và bằng chứng xanh70test; không còn finding mở trong phạm vi này. QA Chrome component1440/1280 đã xem đủ hai PNG: đúng warning nháp/ẩn khi final fresh, lease lỗi khóa nút, 0 lỗi/tràn ngang. Server fixture8513 đã dừng. Giữ2cờ OFF/OPT_IN, widget keys và areas.version68. Chưa cả bộ/native pet/Blender/production; còn mục6 và cost O(n²), không đánh dấu trọn việc xong.
