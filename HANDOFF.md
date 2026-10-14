# Bàn giao điều phối Bàn đạo diễn — 14/10/2026
## Cập nhật mới nhất — người dùng đã duyệt cả hai đề xuất
- Người dùng chốt Blender portable riêng cho worker; giữ bản Store hiện có. Chưa tải/cài portable, chưa đổi cấu hình live. Tiếp theo chọn bản tương thích, xác minh checksum chính thức, test lựa chọn runtime và timeout/process ownership trước phép thử Blender thật 5 dự án.
- Người dùng chốt Đ12v3 metadata ref: file gốc, giây đầu/cuối, tỉ lệ tốc độ; ref cũ thiếu báo VÀNG, không đoán. Làm phần ref_audio độc lập trên nhánh riêng; mix_bus vẫn chờ owner giải phóng delivery/ffmpeg_studio/step5.
- Nhánh hiệu năng đã push: code 8967fcc4, QA d6797503, benchmark d745549e. ĐỎ→XANH 113 passed/1 skip; regression OFF 1 passed. Chưa cả bộ, chưa gộp main, chưa chạy Blender thật.
- Benchmark 2D 1/5/10/20/30 dự án đã ghi docs/BENCH_BAN_DAO_DIEN_2026-10-14.md: đề xuất tạm 5 dự án hoạt động, một worker nặng; không coi giới hạn hàng đợi là giới hạn phần cứng/full pipeline.
- Hạn mức 5h đã dùng 82%, còn 18%; reset 14/10/2026 10:25:37 Asia/Saigon. Lịch hiện có tiếp tục 10:30, không tạo lịch trùng.
- Các dòng bàn giao cũ dưới đây là lịch sử; quyết định mới trên thay thế trạng thái chờ duyệt runtime. .review_test_tmp/ còn untracked do thao tác xóa bị policy chặn; không commit/xóa bằng cách khác.

- DONE BUILD nhánh codex/ban-dao-dien-hieu-nang từ c18b5e6f; chưa commit/push, cờ TẮT.
- Queue RAM:1worker/RRproject/priorityburst3; pending24/perproject4; scopes64/perproject12; records160.
- Coalesce latest projectscene revision; reject older/conflict; running old không publish latest; status/export scopedproject.
- Cache16entry/256MiB; metadata64KiB/files64; fullconfig/revision/source/program bytes workerhash; cachefile integrity hitcheck.
- Native6threads+sceneFIXED; autoengine giữ; CPUprofile configurable; RAM16reserve+8estimate=24GiB admission, không RSS hardlimit.
- Store nền bị chặn trước submit/activation; chưa có owned process/tree supervisor và chưa chứng minh env package. OFF legacy giữ; không cài/đổi runtime.
- Clay async entry và Dashboardadmin3D submit/pollfragment sau clay_background_queue OFF/optin/unverified; oldkeys/ACL/syncOFF giữ.
- Worker khôngSQLite/UI/paidAPI; privatecache exportcopy trướcKho, khôngoverwrite target haycleanup data thật.
- RED initialmissingAPI collectionerror; UIred1/53 thiếufakehome; GREEN cuối58passed1skipped8.01s nhóm5files.
- Prooflauncher temp ngoài repo: C:/Users/hongviet.doan/AppData/Local/Temp/clay_queue_proof.py.
- Launcher patch.object environfake BEFOREpytest/module, fakeabsent/present; nativePopenwhitelist; teardown; --tb=no.
- 5projectRRfixture +5AppTest sessions noSyncRender + noisyproject quota + coalescing/stale/cache/isolation/limits/Storefake/OFF.
- Skip existingBPYfixture未configured; khôngchạyBlender/productiondata/actualkeys/runtime/API thật.
- Docs profile: docs/BAN_DAO_DIEN_HIEU_NANG_2026-10-14.md; RA: docs/RA_BAN_DAO_DIEN_HIEU_NANG_2026-10-14.md.
- Register2core2testflag areas74; diffcheckqua; relatedareas yêu cầu cảbộ/slow ở bướcgộp.
- Khôngdelivery/ffmpeg_studio/step5/runner/admin_auth/main/live/data/PLAN/TODO; khôngremoteAPIcapacity changes.
- MỞ: queue mấtrestart/khôngdurable; RR nội bộprocess, crossprocess chỉglobal lockcũ; memorybudget estimate.
- BàneditorA chưa main; khôngclaim4–5prod/fullpipeline/autopilot đồngthời; cầnownerC5 sharedbudget vàQA thật.
- Bước kế: rootfreshRÀKỸ data/lifecycle/native + QA, sửafinding, cảbộWindows trướccommit/gộp/bậtcờ.

## Bàn giao vòng sửa sau rà độc lập
- Gom 5 findings: Store timeout orphan (chặn ON Store), export tamper (hash trước/sau pin), partial export (atomic staging/retry), NaN/Inf resource limits (positive int), GLTF budget trước allocation (8MiB metadata/boundedread).
- ĐỎ45failed/7passed0.38s; XANH112passed/1skip9.02s env ABSENT; cuối113passed/1skip9.61s env PRESENT + AppTest rejectionStore.
- Tests Store cũ chuyển bảo toàn OFF/legacy bootstrap; regression sanitizedStore bắt buộc reject trước activation. Không nới assertion để coi Store được hỗ trợ.
- Export cleanup chỉ staging absolute đã xác minh cạnh target/cacheprivate; giữ target có sẵn và file người dùng. Hash/copy không giữ queue mutex.
- Security fake env OBJECT trước imports/pytest, native env whitelist; fakehome/temp/data/flags/model, teardown object qua. Không API/data/key thật/fullsuite/commit/push/runtime change.
- Root đọc fixdiff vòng2; areas74 không tăng. Tài liệu performance/RA đã phản ánh limitation.
- CHẶN PRODUCTION máy chính Store: chờ người dùng chọn runtime worker phù hợp hoặc xây owned supervisor; chưa claim4–5safe toànmáy vì legacyStorecaller còn orphan timeout.
