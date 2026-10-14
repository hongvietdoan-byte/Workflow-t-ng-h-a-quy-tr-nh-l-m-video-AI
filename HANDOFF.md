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
