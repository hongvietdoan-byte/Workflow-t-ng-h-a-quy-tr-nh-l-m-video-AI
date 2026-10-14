# Tự rà điều phối Bàn đạo diễn — 14/10/2026
## Root nghiệm thu vòng sửa và native fixture
- Root đã đọc admin runtime actualcaller, single-process guard và test rootsignaled trước release; 3 findings đã giải quyết. Mẫu native thật sau guard: version0 và16/16 clay4views,17rootsignaled/active0/Jobclosed. Báo cáo BENCH_BLENDER_PORTABLE cùng ngày; root đã xem sheet5project.
- Đây là scene giả CPU24khối/640×360/sample8; không fullpipeline/UI/VRAM/cả bộ. NtResumeProcess là API nội bộ ntdll đã thử trên máy này; limit Job dùng API Microsoft documented. CPUthreads6 không hardOSCPUcap, legacyStorecaller khác còn orphanrisk. Chưa bật cờ/main/live.

## Rà độc lập worker portable — một vòng sửa gom
- 3 findings: P1 admin explicit legacy ghi đè portable, P1 snapshot→terminate bỏ sót child mới, P2 IsProcessInJob lỗi bị coi là không thuộc Job.
- Admin ON chọn runtime service trước caption/button, submit không truyền legacy override; None/Store legacy không làm portable bị disable/reject. OFF giữ locator/sync cũ.
- Supervisor đổi contract có chủ đích: **một process Blender, nhiều threads**; Job có ACTIVE_PROCESS_LIMIT=1 + KILL_ON_JOB_CLOSE, không BREAKAWAY.
- Root tạo suspended, assign Job trước resume; giữ handle root xuyên lifetime. Timeout/success/nonzero terminate → chờ root handle signaled → query active=0 trước trả/nhả renderer lock.
- Bỏ snapshot PID/OpenProcess/IsProcessInJob; không còn API unlimited tree hoặc khoảng hở query membership. Không global scan/taskkill/registry.
- [Microsoft ACTIVE_PROCESS limit](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information): associate vượt giới hạn sẽ terminate process và thất bại; guard được đặt trước root chạy.
- Native Python childattempt thực bị từ chối hoặc terminate trước chạy; fixture child không ghi marker. Timeout root, success root signaled, nonzero, assign failure, query/terminate retry được kiểm.
- Tests tree child+grandchild trước đây thuộc contract cũ; thay bằng guard spawn-refused và known-root termination, không tuyên bố portable cho phép process tree tùy ý.
- Query/terminate/wait lỗi vẫn failclosed, giữ renderer lock và supervisor_failed reason; queueclose không cancel native, giữ worker/root tới deadline.
- ĐỎ trước sửa: 4 failed/13 deselected/2.57s (UI legacy None/Store, child refusal, root wait-before-release).
- XANH hẹp: 17 passed/8.74s; cuối 6 nhóm: **129 passed/1 skipped/13.10s**, fake environ OBJECT trước imports, explicit native whitelist, --tb=no/no cache.
- Giới hạn: importer/format/plugin cần helper process sẽ thất bại; không hạ guard hoặc tự chạy ngoài Job. Cần chứng minh Blender portable render thật với guard trước benchmark.
- Official runtime 5.0.1 x64 SHA256 921d77f6c505a35b2c2f6e67d4ad1c10b72418338ba0e0d3ea7f582a5e5fe46e đã xác minh ở phiên BUILD; version rc0 build a3db93c5b259 là proof trước vòng guard này.
- Giữ areas.version74. Chưa Blender thật sau guard, benchmark5/cả bộ/commit/push/live restart/bật cờ; root cần đọc fixdiff vòng2.

- Nhánh codex/ban-dao-dien-hieu-nang từ c18b5e6f; chưa commit/push; DONE BUILD, chưa nghiệm thu production.
- Read AGENTS/CLAUDE/CHUAN/skill 2b.5 + thiết kế Bàn dựng D11 và global turn/Store adapter hiện có.
- RenderQueue một worker, RR project trong interactive/batch, burst 3 để batch không starve.
- Admission 24 pending/4 mỗi project; 64 scopes/12 mỗi project; 160 records; thay pending latest và reject revision cũ.
- Running revision cũ vẫn hoàn tất nhưng không publish vào latest; scoped status/export deny project khác, snapshot chỉ aggregate.
- Submit JSON nhỏ không DB/filehash/render/sleep; worker sourcehash/artefacthash không giữ mutex; export pin và copy ngoài mutex.
- Cache full payload + project/scene/revision/budget/source bytes/program source; bounded 16 entry/256 MiB, metadata64 KiB/files64.
- GLB/GLTF fingerprint dependency local; unknown external formats không reuse; projection fallback không poison cache clay.
- Nguồn kê khai đổi trong render → fail, file cache sửa → rebuild; cache chỉ xóa owned temp children, export không overwrite target.
- Native CPU --threads6 + cfgsceneFIXED6; auto engine giữ; CPU mode configurable, RAM admission24GiB là estimate không hard RSS cap.
- Store nền bị chặn trước admission và native activation: adapter chưa bảo đảm owned process/tree dừng khi timeout hoặc env package; OFF legacy giữ nguyên.
- Cờ queue OFF/opt-in/unverified; blockout_sheet cờ được snapshot; không paid call, không đổi capacity/remoteAPI concurrency.
- Entry thực: admin3D submit/pollfragment và clay submit_preview; Pipeline/SQL/UI chỉ ở caller, không vào worker.
- OFF admin sync branch/widget keys/ACL cũ giữ; async import metadata giữ game/place/look lúc submit.
- ĐỎ: module API chưa có, 1 collection error; UI fixture đỏ 1/53 do thiếu fake home, sửa fixture env-object đúng security.
- XANH cuối: 58 passed/1 skipped8.01s; nhóm clay_scheduler/clay_queue_ui/d11_clay/d11_clay_review/plates3d.
- 5project RR + interactive/batch fairness, 5AppTest sessions no sync render, noisyproject admission, coalesce, stale running đều qua.
- Bounds/cachebytes/source deps/isolation/CPUcmd/RAMwait/OFF có kiểm liên quan; atomic export và Store guard được thêm ở vòng sửa độc lập bên dưới.
- Security wrapper patch.object(os,environ,fake_dict) trước imports; fake absent/present; native Popen explicit whitelist; teardown; --tb=no.
- AppTest fake USERPROFILE/HOME/flags/data/models, SQLite in-memory/mocks cũ; không data/key/headers/token thật hay actualruntime.
- areas register 2core + 2test + flag, version74; diff --check qua; relatedareas bắt buộc slow/cả bộ bước gộp.
- Tự rà2b.5: không nới test, cwd/data paths giả, không auto/bulk/OFF đổi, không bỏ dấu/mạng/tiền/gen mới.
- GIỚI HẠN: queue RAM mất restart; RR không xuyên process; thread/profile/RAM không chứng minh throughput/VRAM/RSS hard cap.
- Bàn editor A chưa main, fullpipeline4–5 chưa đo; Blender thật không chạy phiên này, Store cũ baseline không phải bench scheduler.
- MỞ: root RÀ KỸ vòng đời/cache/native adapter, QA rồi cả bộWindows gồm slow; ownerC5 sharedbudget trước bật cờ.

## Rà độc lập và một vòng sửa gom 5 findings
- P1 Store timeout chỉ ngừng đợi rc.txt, không dừng Blender: chưa có owned PID/IPC/process handle nên chặn queue ON Store rõ ràng ở plates/clay submit và `_render(sanitized_child=True)`; không scan/kill process. OFF legacy giữ, chưa hỗ trợ worker máy chính Store.
- P2 export không kiểm artifact bị sửa: pin cache rồi kiểm hash trước/sau copy ngoài mutex; lệch invalidate, không publish target.
- P2 copy lỗi để target dở: staging riêng cạnh target, rename sau kiểm, cleanup staging đã xác minh absolute parent/prefix; retry thành công, giữ target có sẵn.
- P2 NaN/Inf/bool/float vô hiệu ngân sách: count/byte/timeout bắt buộc int dương trước tạo temp/worker; RAM vẫn finite number như trước.
- P2 GLTF nạp JSON trước budget: stat trước đọc, metadata tối đa min(source budget,8MiB), bounded read chống file tăng sau stat; GLB prebudget/chunk cap.
- ĐỎ trước sửa: 45 failed/7 passed, 14 deselected, 0.38s; 5 nhóm regression cô lập, không nới test. Test Store sanitized cũ thay bằng bảo toàn bootstrap legacy + regression mới bắt buộc reject sanitized Store.
- XANH lần 1: 112 passed/1 skipped9.02s, 5file related (scheduler/UI/d11_clay/d11_clay_review/plates3d), env fixture ABSENT trước mọi import.
- XANH lần cuối: 113 passed/1 skipped9.61s, cùng nhóm5file, env fixture PRESENT + UI Store rejected/no uncaught exception; teardown object môi trường qua.
- Native subprocess env whitelist, `patch.object(os,'environ',fake)` trước pytest/modules, temp/home/flags/models/SQLite giả; teardown trả object môi trường; không đọc/in/assert giá trị môi trường thật.
- Không fullsuite/commit/push/production/API/runtime install. areas version74 giữ, không thêm module khác; root đọc diff vòng 2.
- Giới hạn: global one-Blender chỉ đường queue/native mới; các Store legacy caller chưa đổi còn rủi ro orphan timeout. Chưa chứng minh 4–5 pipeline production hoặc môi trường packaged Blender; task tối ưu máy chính vẫn có chặn runtime.
- Root rà vòng2 phát hiện default `_run_in_store(run=subprocess.run)` bind lúc import làm OFF legacy bỏ qua mock/call-time runner. Sửa default None + tra cứu `subprocess.run` lúc gọi; regression activation giả tạo rc/log trong fixture owned, native bound runner được thay bẫy trước gọi. ĐỎ1failed/68deselected0.18s → XANH1passed/68deselected; chỉ test hẹp, không chạy lại nhóm113.
- Cleanup `.review_test_tmp/` bị automatic approval policy từ chối; giữ untracked, root loại khỏi commit, không bypass bằng lệnh khác.
