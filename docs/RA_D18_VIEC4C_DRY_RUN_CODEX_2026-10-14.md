# Tự rà Đ18.4c PARTIAL dry-run — 14/10/2026

- Root đã đọc diff sửa lần hai sau RÀ KỸ độc lập: chốt 67 xanh/1skip2,17s, guards/report/mapping/raw preservation trong phạm vi PARTIAL. Chưa semantic/atomic4c/production restore; fullsuite Windows thuộc bên tích hợp.

Chỉ inventory/read trên fixture tạm #24/#27, không production QA. Domain Kho
look/ảnh/pins/hash chưa chốt; không nhập A, tạo state/asset/look hoặc activate.

- Test ĐỎ17failed/4errors →20passed/1skip →27passed/1skip. Root quickread
  findings sau lượt3: unhashable kind ngoài sanitizedcontract, root ancestors
  và recheck resolvedpath sauopen/read. Sửa +6 test →33passed/1skip (0.90s),
  lượt4 minh bạch do finding mới, không nới test. Native symlink skip do quyền
  Windows; mock ancestor/link swap failclosed có coverage. Pytest --tb=no.
- Tự kiểm 2b.5: no paid/provider/network/credential/environment reads; tests
  patch.object thay os.environ bằng dict giả trước import/call. Không subprocess.
- Không path tương đối phụ thuộc cwd: caller root tuyệt đối + relativecanonical,
  rejectdrive/absolute/.. /backslash/ADS và symlink/junction source/rootancestor.
  Resolve/check/fstat guards trướcaccept; không hứa chống mọi racefilesystem;
  fixture/bản sao khôngwriter là điều kiện caller.
- Raw bytes/frozen dataclasses/tuple immutable; unknownfields/binary/
  approvals/state/locks/spec không mutate. Test copyrestore byte-for-byte,
  hashscope project/version/bytes, replay inputorder, changedsource proposal mới.
- Diagnostic missingIDs/units/scale/approvedround/textblocking/state/lookdomain
  đều unresolved/conflict, không bịa. CandidateID là proposal source ID, chưa
  stable aggregate A/ID Kho. Report luôn PARTIAL/ready=False, không có store API.
- Không thay DEFAULT features/caller/autopilot/UI; không DB migration/init.
  Không nới budget caller: 64file/8MBfile/32MBtotal/48depth/200knodes tổng;
  malformedJSON/duplicatekey/NaN/sourcechange failclosed, không partialresult.
- related_areas plates3d, không caller mới; giữ areas v80. Không API/data thật,
  fullsuiteWindows, rollbackmigration/live QA hoặc chất lượng hình/video.
- TODO không sửa main: dependency cherry đã giữmain bytes; HEADdiff gỡ thư4b
  chỉ trên dependency để không kéo thư chưamain sang dryrun. Chưa commit/push.
- Còn: independentreview root, domainlook user, semantic reconcile/transaction
  raw+mappings+revision+links và productionbackuprestore thuộc phần4c sau.


## RÀ KỸ độc lập hẹp + sửa gom (14/10, chưa commit)

Reviewer không xây importer; chỉ đọc module290lines/tests/HANDOFF/protocol/
diffareas, không rà lại dependency4b554c7fbb/2803a133, không mở apply4c.
Đã báo trọn finding cho root trước sửa; root bổ sung device/ADS/caseguard.

1. P2 root/network và Windows alias — core/stage_registry_import.py:88/229:
   reject UNC/device/networkroot trước stat; validate explicit specs thuần
   trước mọi root lookup; reject ADS/reserveddevice/trailingdotspace và casefold
   duplicate paths trước I/O. Regressions networkroot2 + alias9 + casealias1
   dùng spy first filesystemguard _link, không mở nguồn invalid.
2. P2 restore thiếu report integrity/bounds/sanitize — module:291: preflight
   frozen tuple/type/count/file/total bytes trước SHA/decode; verify project/
   version/PARTIAL/readyFalse, canonical sorted source metadata, source rawSHA,
   mappings exact scope và inventory_hash; malformedsource được lỗi hợp đồng
   thay AttributeError. Test report5/source4/mapping/malformed2/countbudget.
   Hash chỉ **integrity**, không signature/authenticity; người dựng lại toàn
   report+hash không được quyền approve/apply/productionrestore.
3. P2 diagnostic bỏ qua scaleunknown/ID malformed — module:114/120/196:
   unknown valueNone/false/0/negative/{} hoặc chưameasuredsource rõ vẫn
   missing_scale; stablelegacyID bool/list/dict bị missing_stable_id. Raw không
   đổi, không semanticconvert. Tests scale5 + ID3. Positive numeric legacy
   scale chỉ là khai báo, không claim đo/verified; actor ID range SQLite nhưng
   chưa kiểm identity thật vì không đọc Kho/DB.
4. P3 total I/O budget — module:268: giới hạn mỗi read theo min(filecap,
   totalremaining), statreject file vượt budget còn lại trước mở. Regression
   secondfile vượt tổng không bị open; không tăng trần caller.

Bằng chứng reviewer3lượt: **22 failed/45 passed/1skip (RED)** →
**12 failed (RED lexical guards,0.27s)** → **67passed/1skip (GREEN,2.17s)**.
Lượt đầu pathspy Path.stat không bắt Path.is_dir implementation nên các ca
path chưa chứng minh guard; đổi spy sang _link đầu tiên ở lượt2 để RED đúng
trước mọi lookup, không nới assert. Đồng thời dùng raw literal UNC tránh
SyntaxWarning. Các 22 ca restore/diagnostic/budget ĐỎ thực ở lượt1.
Lệnh cuối py -m pytest -q tests/test_stage_registry_import.py --tb=no
-p no:cacheprovider, PYTHONUTF8=1; không broad/fullsuite/repeatedGREEN.
Skip native Windows symlink privilege là test cũ; mockedguard đều xanh.

related_areas CLAUDE7: plates3d, chưacaller; không thay featuredictionary/default/
UI/autopilot, không importstore/validator/provider/credential/SQLite. Module
stdlibpure không envread/subprocess/network API. Tests patch.object OBJECT
os.environ dictfake trước imports/calls; không env/header/token/credential
repr/assert/showlocals hoặc data thật. Không nativechildspawns cần whitelist.
Areas module/test đã khai, version80 giữ; diffcheck sạch ngoàiCRLF warning.

Report vẫn PARTIAL/readyFalse; restore chỉ trả tuplebytes, không sourcewrite,
noDB/noapply/noapprove/nolatest. Bounds không thay snapshotfilesystem lock;
điều kiện nguồn là fixture/copynonwriter, không claim chống mọi ABA/race. Root
local tin cậy không alias/UNC; không claim phát hiện mọi mapped networkdrive.
Node scan sau jsondecode có rawfile hardcap, không claim streamingJSON parser.
Không TODO mới/commit/push/main/live/API/data thật; root đọc fix lần2 trước
integration. Semanticreconcile/domainlook/atomicapply/restoreproduction còn
scope4c tương lai, không đánh dấu4c toàn bộ hoàn tất.
