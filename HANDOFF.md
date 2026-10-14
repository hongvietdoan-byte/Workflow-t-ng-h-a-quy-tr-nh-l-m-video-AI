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
