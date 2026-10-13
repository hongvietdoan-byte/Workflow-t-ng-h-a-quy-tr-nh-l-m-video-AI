# Đ11 việc 1b mockup — sửa gộp sau rà

Nhánh `codex/d11-viec1b-mockup`, base c5544891. Phạm vi chỉ HTML/JS/test/PNG, không backend/API/data thật/TODO/PLAN/main/push.

Đã sửa 5P2: inverse drag world; keyframe monotonic; sampler timeline chung; diff bind ID/revision + context fence; target actor_id resolve. Bổ sung #3 nền fixture/phông xanh, #4 time/weather/azimuth minh họa, #10 props ID/kích thước/provenance + stand_in chỉ viewer, #7 baseline Director fixture diff/undo. Stage approved dùng snapshot revision, actor/state/shot/setup vẫn registry nguồn duy nhất. Numeric endpoint có hiệu ứng, nhập hướng số dùng manual. Giữ #12 preset/#20 JSON để sau.

Đỏ 1failed1passed9.03s → xanh cuối 3passed50.00s (env giả thiếu/có credential giả, teardown). QA1440/1280 console0/overflow0, inverse drag16 tổ hợp + trục/numeric endpoint/diff/approved-stage/target/props/baseline. Baseline/current5/5 thao tác, không claim giảm bấm. 4PNG recapture có chủ ý; pytest chỉ tmp.

RA: `docs/RA_D11_VIEC1B_MOCKUP_CODEX_2026-10-13.md` có đối chiếu18dòng bản gọn + cách sửa/test. related_areas chỉ dashboard_ui, testCHẬM UI bắt buộc ở bước gộp; areas71 không tăng, không có file mã mới.

Bước kế root: rà nhẹ phần sửa + 4PNG; cả bộ Windows xanh trước tích hợp/main, tăng areas version một lần ở nhánh tích hợp, ghi trạng thái/TODO và push theo quy trình. Chưa ca production; SVG proxy/fixture chưa Blender/ray/collision/render thật, map/source UNKNOWN, provider/solver/Director/Kho thật tắt, RAM mất refresh.
