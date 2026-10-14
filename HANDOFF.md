# HANDOFF — Đ18.4c PARTIAL inventory/dry-run

## Người dùng chốt 14/10 21:54 — thay chỉ dẫn tự tiếp tục phía dưới

- Khi hạn mức tuần gần hết hoặc không đủ cho việc kế tiếp: lưu/commit/push trạng thái và bàn giao cho Claude, KHÔNG tiếp tục công việc ở chat Codex này hoặc chờ reset tuần để tự làm lại.
- Đã XÓA lịch `ti-p-t-c-c-c-vi-c-codex-c-n-l-i-sau-reset`; lịch 15/10 01:45 bị hủy. Không tạo lịch thay thế.
- Claude nhận các nhánh đã push và bước còn mở theo bàn giao này: store look/pin nguồn chờ quyết định bộ dạng/ảnh; Đ18.4c mới PARTIAL dry-run, còn semantic/atomic apply; kiểm dependency/main trước sửa. Không coi bàn giao là quyền chạy API trả phí/migration dữ liệu thật.

## Chốt root 14/10 21:43 — ưu tiên trạng thái này

- Code dry-run `9320b224`; nhánh `codex/d18-viec4c-dry-run` được push riêng, tiếp đúng worktree này khi có quyết định domain. Không lấy dependency commits như nhiệm vụ mới/không làm lại4a4b.

- Root đã đọc toàn bộ fix lần hai; 67 xanh/1skip2,17s, diff-check sạch. Chốt phạm vi inventory offline + raw/hash/mapping + restore_payloads, luôn PARTIAL/ready=False; chưa DB apply/semantic reconcile/activate/production restore.
- Đã push 4b codef18f936f/HEAD66234479 (116test) và ref_audio code1d46d091/HEADe9eb1b54 (22test/2JPEG actualcomponent1440/1280). Ref QAowned launcher118464 đã dừng; 18636 đóng, không live8501/8502.
- Câu hỏi bộ dạng/pin ảnh/hash Kho còn chờ; không mặc định look=1ảnh. Chốt câu trả lời trước hoàn thiện look/pins backingphysicalversion và semantic/atomic4c. Phần dry-run này không bị coi là nghiệm thu toàn4c.
- Quota đã dùng5h82%/còn18%, tuần92%/còn8%, reset5h15/10 01:40:29 Asia/Saigon. Sau reset đọc main/hộp thư mới, không làm lại nhánh đãpush, không nhận file owner khi chưa release. Lịch cùng ID sẽ dời saureset; chưa mainmerge/cảbộ Windows/live/API/realdata.

- Worktree D:/AI-Video-Pipeline/.codex-wt/d18-viec4c-dry-run, codex/d18-viec4c-dry-run; fetch origin/main mới 7340e6b1.
- Dependencies chưa main: 23b9fa51 →554c7fbb, f18f936f →2803a133 cherry-pick chủ ý. Không sao chép validator/store hay đổi lại backend. TODO conflict4a giữ main; sau dependency4b trả TODO về bytesorigin/main (diffmain rỗng, HEADdiff xóa2dòng thư4b CHỈ của dependency; không xóa bất kỳ dòng main).
- Module mới core/stage_registry_import.py, tests/test_stage_registry_import.py; areas version80 giữ, chỉ registermodule/test.
- Bounded explicit inventory raw immutable bytes/SHA256 + deterministic proposal mapping/source-version/hash scope; unresolved/conflict IDs/units/scale/text blocking/round/state/lookdomain. Preserve unknownfields/binary/approval history/locks/subjects/end_actor/POV/move/beats.
- Always status PARTIAL/ready_for_apply=False. Không import store/SQLite/provider/env, không scan production/latest, không API apply/importwrite/migration/activate/UI.
- Restore API chỉ trả raw payloads, test bản sao tạm chứng minh bytes không mất. Path reject escaping/symlink/junction/ancestor/ADS; check sauopen/read, không claim raceproof tuyệt đối.
- Test lượt1 ĐỎ17failed/4errors; lượt2 20passed/1skip; lượt3 27passed/1skip; root findings sau lượt3 → bổ sung malformedkind/rootancestor/linkswap và xác nhận lượt4 33passed/1skip0.90s. Skip native symlink Windows privilege, mockguards đã test.
- related_areas plates3d khôngcaller; không test chậm bắt buộc riêng importer. Chưa fullsuiteWindows/production QA.
- Tự rà docs/RA_D18_VIEC4C_DRY_RUN_CODEX_2026-10-14.md; protocol có hợp đồng PARTIAL. Không commit/push/TODO mới.
- Bước kế root independent RÀ KỸ/confirm. Apply/atomic restore/semantic A conversion cần scope4c tiếp sau lookdomain chốt; không tự mở.


## Rà độc lập hẹp và sửa gom — mới nhất
- 3P2+1P3 đã báo root trướcfix: offline/network+Windowsalias paths, reportrestore integrity/bounds/types, scaleunknown/stableID diagnostic, remainingtotalreadbudget. Source raw không đổi; report PARTIAL/readyFalse.
- Reviewer3lượt: 22REDrestore/diagnostic/budget +12REDlexicalguard sau sửa spy Path.stat→first_link, **67GREEN/1skip2.17s**. Skip nativesymlinkprivilege cũ; mockguards xanh, khôngnới/broad/fullsuite.
- restorevalidate full metadata/project/version/hash/mapping+bounded immutable collections; hashintegritykhôngsignature/authenticity. Khôngsourcewrites/DB/apply/approve hoặc rereview4b.
- relatedareas plates3d/nochcaller; areas80 giữ, RA/protocol cập nhật. KhôngTODO mới/commit/push/main/live/API/credentials/data thật.
- Root đọcfixlần2 trướcintegration; domainlook/semanticreconcile/atomic4capply/productionrestore vẫn bước riêng, không claim4c toàn bộ xong.
