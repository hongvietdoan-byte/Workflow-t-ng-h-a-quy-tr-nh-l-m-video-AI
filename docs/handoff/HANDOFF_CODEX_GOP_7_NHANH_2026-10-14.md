# Đ13 việc 4 mục 4 — tối ưu chỉ mục nhóm

Code a4a9dc83, nhánh codex/d13-viec4-cost-nhom. Chỉ cost + test/areas; giữ version72.
133 test +6 subtest xanh; rà độc lập 1P2 SAVEPOINT đã sửa với 3ca đỏ→xanh, nhóm28test3,88s.
Root đọc diff vòng sửa trước commit; 99shot/20nhóm1query/20parse/99members, quote oracle byte-identical.
Đang transaction luôn đọc mới; ngoài transaction tối ưu theo project. Không thay logic budget đã gộp.
Chưa cả bộ Windows/ca production/main/live/API. Xem RA_D13_VIEC4_COST_NHOM_CODEX_2026-10-13.md.
Bước kế: bên tích hợp rà/chạy cả bộ -n8 trước gộp; không cherry-pick lại các phần Đ13v4 cũ.
# Bàn giao Đ12 việc 4
- Nhánh: `codex/d12-viec4-kho-am-thanh`; base `1cb845b2`.
- Xong báo cáo `docs/KHO_AM_THANH_CAN_BO_SUNG.md`, tool `tools/audio_mood_audit.py`, test và khai areas giữ 72.
- Công cụ chỉ stdlib/đọc JSON/CSV explicit, không tải model/API/data thật.
- Test đỏ thiếu module → 34 xanh/0,31 s (thêm URL/UNC đỏ 6 ca → xanh); tự rà ở `docs/RA_D12_VIEC4_CODEX_2026-10-13.md`.
- AST config thực có 7 mood; top40/output rút gọn không chứng minh score=0.
- Không đổi picker/SFX/TTS/mix/runtime; chưa thử Kho #24, chưa nguyên nhân thực hay nguồn tệp đã duyệt.
- Bước kế root RÀ NHẸ + push nhánh; trước gộp chạy cả bộ Windows theo related_areas.
- Không push/main/TODO/PLAN/live trong phiên con; người dùng duyệt trước tải.
# Bàn giao Đ13 việc 3

- DONE ba mục mockup, nhánh `codex/d13-viec3-mockup-pet`, base `1cb845b2`.
- Chi tiết đỏ/xanh và tự rà: `docs/RA_D13_VIEC3_CODEX_2026-10-13.md`.
- Nhóm liên quan: 7 passed /9,75s; browser 1440/1280 offline, slow.
- Không API/dữ liệu thật/backend/tickets/TODO/PLAN/main/push; areas giữ version72, test nằm sẵn dashboard_ui.
- Bước kế root: rà nhẹ diff/test/PNG; cả bộ Windows trước gộp, test slow theo related_areas.
# Đ11 việc 1b mockup — sửa gộp sau rà

Nhánh `codex/d11-viec1b-mockup`, base c5544891. Phạm vi chỉ HTML/JS/test/PNG, không backend/API/data thật/TODO/PLAN/main/push.

Đã sửa 5P2: inverse drag world; keyframe monotonic; sampler timeline chung; diff bind ID/revision + context fence; target actor_id resolve. Bổ sung #3 nền fixture/phông xanh, #4 time/weather/azimuth minh họa, #10 props ID/kích thước/provenance + stand_in chỉ viewer, #7 baseline Director fixture diff/undo. Stage approved dùng snapshot revision, actor/state/shot/setup vẫn registry nguồn duy nhất. Numeric endpoint có hiệu ứng, nhập hướng số dùng manual. Giữ #12 preset/#20 JSON để sau.

Đỏ 1failed1passed9.03s → xanh cuối 3passed50.00s (env giả thiếu/có credential giả, teardown). QA1440/1280 console0/overflow0, inverse drag16 tổ hợp + trục/numeric endpoint/diff/approved-stage/target/props/baseline. Baseline/current5/5 thao tác, không claim giảm bấm. 4PNG recapture có chủ ý; pytest chỉ tmp.

RA: `docs/RA_D11_VIEC1B_MOCKUP_CODEX_2026-10-13.md` có đối chiếu18dòng bản gọn + cách sửa/test. related_areas chỉ dashboard_ui, testCHẬM UI bắt buộc ở bước gộp; areas71 không tăng, không có file mã mới.

Bước kế root: rà nhẹ phần sửa + 4PNG; cả bộ Windows xanh trước tích hợp/main, tăng areas version một lần ở nhánh tích hợp, ghi trạng thái/TODO và push theo quy trình. Chưa ca production; SVG proxy/fixture chưa Blender/ray/collision/render thật, map/source UNKNOWN, provider/solver/Director/Kho thật tắt, RAM mất refresh.
# Bàn giao Đ12v2
- Nhánh codex/d12-viec2-sfx-nhip; base 2c43a28f; chưa commit/push, areas.version 74.
- Hoàn tất lõi cue code 0 USD, adapter sfx_plan, cờ motion_sfx OFF + opt-in, component UI độc lập.
- Bằng chứng đỏ→xanh: 16 lỗi import; tự rà 2 ca đỏ; nhóm 4 file cuối 77 passed/11,10s.
- Rà: docs/RA_D12_VIEC2_CODEX_2026-10-14.md; diff check/py_compile xanh.
- Đỉnh optical flow chỉ đo toàn khung; máy static → dùng giây peak nhưng alignment hành động estimated+VÀNG.
- Máy unknown/moving/quiet/series lỗi → chia đều BYĐ; không nhận diện nhân vật giả.
- Catalog trusted có sẵn; thiếu âm → unmet+VÀNG, không đổi guard nhận diện.
- Chưa nối step5 vì file do Claude giữ; chưa UI sản xuất/thử thật/cả bộ Windows.
- Chưa đường Claude bổ sung trả tiền: chỉ thông báo cần luồng báo giá/duyệt hiện có khi caller nối.
- Root fresh review trước commit; không sửa TODO/PLAN, không merge/main/live/API/data thật.
- Vòng sửa sau rà độc lập đã đóng 3 P2: neo cue overlap + validate trước ghi; huge integer/tổng tràn → VÀNG; prompt motion hiện tại ưu tiên + cảnh báo BYĐ cũ.
- Bằng chứng cuối: ĐỎ 14 failed/23 passed → nhóm 4 file 96 passed/11,24s; diff check xanh. Root cần đọc diff sửa; chưa commit/push.
- QA Chrome 1440/1280 chưa chạy (Python không có Playwright); chưa cả bộ Windows/UI sản xuất/Claude trả tiền.
- Chốt root rà lần 2: prevalidate sound/file/volume trước xóa âm explicit, cho idx0 có DB/timeline scope. ĐỎ 4 → nhóm cuối 100 passed/11,06s; legacy apply giữ đường cũ.
- QA component đã xong bằng Node Playwright + Edge headless fallback (Chrome launch thoát0): 1440/1280 có PNG trong docs/images/d12, 3warning/cỡ, proposalstub1/cỡ, paid0, console/pageerror0, overflowfalse; đã dừng fixture8554. Chưa UI sản xuất/cả bộ/Claude trả tiền.
# Bàn giao Đ13 việc 2 — 14/10/2026
- Đã commit code `bad2a535`; root đọc diff vòng sửa và hồi quy, không thấy lỗi còn mở trong phạm vi. Nhánh chỉ push riêng; cả bộ Windows thuộc phiên gộp, không gộp main/live.
- DONE triển khai, chưa commit/push; nhánh codex/d13-viec2-goi-blockout từ 2c43a28f.
- Đổi core/blockout_sheet.py, tests/test_blockout_sheet.py, skill vòng làm việc (câu K/CX + ví dụ).
- Schema 2: SHA chuẩn hóa số hình học exact ratio, ngày ISO aware; schema 1 SHA raw + naive đọc được có cảnh báo duyệt lại.
- Font Pillow cũ: thử size rồi fallback không size; dependency giữ nguyên.
- Đỏ→xanh: 5 failed/88 passed → 93 passed; bổ sung test bắt thiếu huong_sang → 95 passed cuối (3.33 s).
- Lệnh nhóm: py -m pytest tests/test_blockout_sheet.py tests/test_blockout.py tests/test_blockout_facts.py tests/test_d11_clay.py tests/test_d11_clay_review.py -q -p no:cacheprovider --tb=no.
- Proof cuối 95 passed/3.29s qua pytest.main dưới patch.object(os, "environ", fake_dict) trước import pytest/test, stop teardown; các proof patch.dict cũ không đáp ứng object security, đã thay.
- Có 5 lượt pytest tổng (thêm proof patch.object theo root), lượt thêm do mở rộng allgeometry regression tìm lỗi; không đổi assert cũ.
- RA: docs/RA_D13_VIEC2_CODEX_2026-10-14.md; related_areas không yêu cầu test chậm.
- Không test code mới dạng file nên areas registry giữ sẵn tests/test_blockout_sheet.py, version 74.
- Bước kế: phiên chính RÀ KỸ dataformat/caller; sửa mọi lỗi nếu có, cả bộ Windows trước commit/gộp.
- Chưa thử Pillow cũ cài thật; đã giả lập signature cũ + PNG thật; không API/dữ liệu thật.

## Sau rà độc lập và vòng sửa gom
- Đã đóng 2 P2: bitmap thiếu glyph tiếng Việt gây UnicodeEncodeError; canonical SHA lọt metadata lồng có tên trường trùng geometry.
- Hai hồi quy ĐỎ **2 failed / 29 deselected** → sửa exact geometry paths + font Unicode local/fail rõ trước PNG → **97 passed / 3,43 s** nhóm 5 file; không đổi assert cũ.
- Security: toàn lượt sửa/test dùng patch.object(os, "environ", dict giả) trước import/call, context manager khôi phục; không đọc/sao chép môi trường thật, không API/model/provider thật/subprocess. Proof patch.dict cũ không được dùng làm bằng chứng security.
- Thiếu mọi font Unicode: ValueError actionable, không bỏ dấu/âm thầm thay nhãn; Arial/DejaVu bình thường giữ nguyên, thêm Tahoma/Segoe UI local; root đã đồng ý.
- git diff --check sạch; chưa commit/push/cả bộ Windows. Root đọc diff vòng sửa và kiểm tích hợp trước gộp.

## QA bổ sung HEAD ef9178bb
- QA actual Pillow 10.0.1 còn mở: automatic policy chặn ProcessStartInfo whitelist env + pip isolated/binary-only/target TEMP trước chạy; `blocked by policy`, không lý do chi tiết. Chưa chạy pip/cài/probe/PNG/actual proof; không bypass/đổi runtime/test lại/commit/push. Root đọc RA giới hạn rồi quyết bước kế.
# Bàn giao Đ13 việc 1 phần độc lập — 14/10/2026
- Code đã commit `728be4be`; root đọc diff vòng hai và caller, không thấy lỗi thêm trong phạm vi. Push riêng; mục 2/4 tiếp tục MỞ.
- DONE mục 1/3/5; nhánh codex/d13-viec1-post-fx từ 2c43a28f; chưa commit/push.
- Mục 1: post_fx tên shot + SHA256 sourcebytes/spec/seconds/filter/encode, luôn render qua atomic_output; failure giữ bản trước.
- Mục 3: rule 6 director_p24_1110 có schema đầy đủ, cổng p24_lessons giữ nguyên; OFF prompt byte-identical.
- Mục 5: rough_cut mang manifest.post_fx và Editor append context sau post_fx_render; conditional fingerprints tránh cache report cũ.
- Test rgbashift: đọc -filters actual; thiếu thì skip chỉ glitch, lỗi khác không skip; tất cả effect thật local đã qua.
- Đỏ 5 failed/103 passed → xanh cuối 108 passed/45.11s; 3 lượt nhóm 5 file liên quan.
- Proof shell: py C:/Users/hongviet.doan/AppData/Local/Temp/d13_v1_proof.py (launcher ngoài repo).
- Launcher thay os.environ OBJECT bằng dict giả trước import pytest/modules; native Popen explicit env whitelist; context managers teardown.
- Red fakeabsent, green fakepresent; MockLlm/mocks ở tests cũ; không API/khóa/data thật; --tb=no.
- pytest group: tests/test_d13_post_fx.py tests/test_post_fx.py tests/test_p24_lessons_1110.py tests/test_editor_review.py tests/test_rough_cut.py -q -p no:cacheprovider --tb=no.
- File đổi: core/post_fx.py, core/rough_cut.py, core/editor_review.py, knowledge/roles/director_p24_1110.md, tests/test_post_fx.py, tests/test_d13_post_fx.py, devsys/areas.json.
- Areas test mới đăng ký, version 74 giữ; diff --check qua; không đổi widget keys.
- RA: docs/RA_D13_VIEC1_CODEX_2026-10-14.md; related_areas yêu cầu slow tại bước gộp.
- MỞ: mục 2 _hold_end và mục 4 delivery.status do owner xử lý; không đụng delivery/ffmpeg_studio/step5.
- Bước kế: root RÀ KỸ sạch, tích hợp owner; cả bộ Windows gồm slow trước commit/gộp.
- Rủi ro: thêm lượt băm byte nguồn; spec/nguồn thực sự mới giữ file mới; không dọn/xóa UUID cũ hay dữ liệu thật.

Vòng sửa RÀKỸ14/10: 2P2 đã sửa gom. Nối post_fx từ outputĐạoDiễn→shot_data/v3store_plan hoặc DIRECTOR_KEYS/legacymerge→DB→apply, gatedp24_lessons; renderer/contextgatedpost_fx_render. Sharedcontext cho cảEditor vàDirector secondpass; khôngcopy intent. 3callerchainassertion đỏ→3xanh/0,45s; OFFbaseline+invalidyellow/deepcopy bổ sung. Nhóm5file gốc+test_v3 chạy launcherfakeenv/registryblocked/nativewhitelist; chờ sốcuối. Giữareas74/heldfiles/noAPI/noactualdata/commitpush. Root đọcfixdiff, mục2/4chờowner.

DONE vòng sửa: 147passed/131,81s nhóm6file (5fileworker+test_v3), fakeenv/registryblocked/nativewhitelist --tb=no. Root đã đọcfixdiff khônglỗithêm; khôngthay intent_all, sharedcontext lấyres.post_fx từmanifestnguồnchuẩn cho2lượt. RA chốt2P2+redgreen. Mục1/3/5hoàn tấtcode, mục2/4ownerheld vàcảbộ/gộp/commitpush/productionchưa làm.
