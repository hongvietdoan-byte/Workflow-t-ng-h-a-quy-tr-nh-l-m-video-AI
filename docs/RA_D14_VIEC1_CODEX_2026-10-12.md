# Rà tự kiểm Đ14 việc 1 — 12/10/2026

Nhánh `codex/d14-viec1-qc-quan-sat`, gốc `08c11b4`. Chưa commit; chờ RÀ KỸ caller độc lập.

- Thêm `qc_observe_enum`: mặc định TẮT, cả preset experimental phải chọn riêng.
- OFF: FakeLLM đối chiếu prompt + images + JSON output với hàm `run_qc` lấy trực tiếp từ `git show 08c11b4`, bằng nhau.
- ON: `qc_spec.compile_frame` áp ngoại lệ Lock/BYĐ hiện có; đặc điểm hồ sơ tách theo dấu câu, không so bỏ dấu/từ ngắn. Vật BYĐ đọc `thanh_phan[].vat` (ngoài cast; vai `khong_duoc_co` phải không thấy) và `vat[].vat` nếu có. Nguồn cùng job + từng source nằm trong id SHA.
- Model khai enum, vùng, bằng chứng, source; điểm/đạt do code, bỏ qua model criteria/verdict. Schema kiểm enum chính xác, id trùng/thiếu/lạ, nguồn, bằng chứng, vùng hữu hạn.
- `khong_chac`: điểm không bị trừ, pending_review, không apply_qc/autofix. Thiếu hồ sơ, đặc điểm chuẩn, tham chiếu hoặc bảng shot mâu thuẫn báo lỗi.
- Nhánh ON lấy ảnh Kho qua assets; không dùng layout làm chuẩn. Ca 678/680 giả dựng mặt/váy đen/chân đỏ/giếng; chưa chạy ảnh sản xuất, chưa chứng minh chất lượng.
- Quan sát chuyên biệt side/cap/geo chưa có số đo trong schema enum này: giữ VÀNG, không cho enum thay kết luận qc_rules. Chưa thay nhánh qc_agent/qc_team của scene_qc; cờ mới hiện nối đường run_qc ảnh đơn/batch/autoqc ngoài scene_qc.

## Đỏ → xanh / giới hạn

Một lệnh gom `tests/test_qc_observe_d14.py tests/test_qc_team.py tests/test_lock_ngoai_le.py`, tối đa ba lượt:
1. ĐỎ collection: module qc_observe chưa có.
2. XANH 53 passed / 1,18 s.
3. XANH 56 passed / 1,04 s (FakeLLM integration ON/OFF).

SAU lượt 3, nhận góp ý root: thêm đọc đúng BYĐ.thanh_phan; chuyển fixture giếng sang thanh_phan; guard must_keep rỗng; side/cap/geo giữ VÀNG. Các bổ sung này CHƯA chạy lại do trần 3 lượt; cần vòng sửa/rà xác minh trước commit. Không gọi API, không thay dữ liệu thật, không sửa TODO/PLAN/version, không push/gộp.

## Tự kiểm skill 2b.5

Test không nới assert; không đường dẫn dữ liệu tương đối; module đọc checklist qua root prompts hiện có. OFF không đổi request/output đã so byte. VÀNG không autoapprove/autofix. Không parser bỏ dấu. Không tiêu đề/nhãn thành nội dung quan sát. Không mở mạng/API trong FakeLLM. Sổ chi dùng caller tagged + ask_json hiện có. Chưa kiểm ON mọi luồng scene_qc: ghi rõ phạm vi thay vì báo đủ.

`related_areas.py` đã chạy: vùng chứa step2, step1, step3, core_infra; callers trọng tâm autoqc/autopilot/budget/diag/dashboard_ui. Báo Test CHẬM bắt buộc lúc gộp: access/editor_apply/editor_review/rough_cut/ui_v2_acceptance. RÀ KỸ cần kiểm thiếu chuẩn, ngưỡng hard_floor và vòng tự regen của apply_qc, scene_qc khi bật cờ đồng thời.

## RÀ KỸ độc lập — 12/10/2026 (chưa sửa)

- Xác minh bản cuối: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider tests/test_qc_observe_d14.py tests/test_qc_team.py tests/test_lock_ngoai_le.py` → **56 passed / 1,14 s**. Không API, không dữ liệu thật.
- **P1 caller bypass** — `core/qc_scene.py:567,585,597,609`, `core/autoqc.py:81`, `core/autopilot.py:459`: scene_qc ưu tiên team/agent/legacy, không đi run_qc nên ON không sửa QC ảnh trên các đường cảnh. Sửa: tách hàm observe_frame thuần trả kết quả; dùng tại layer1 qc_scene ưu tiên ON (cả team/agent đồng thời), giữ layer0/code đo, hold/trusted/shadow, sổ chi/ước tính. Không gọi run_qc trực tiếp từ scene route vì apply_qc có thể tự duyệt/regen trái scene gate. Test ma trận ON scene/team/agent/legacy + OFF không đổi.
- **P1 mất nội dung tiêu chí** — `core/qc_observe.py:67–69`: hễ có một assertion thì bỏ toàn bộ checklist cùng tiêu chí. Tái hiện: consistency chỉ còn đếm người (mất chữ/logo); CU composition chỉ cỡ cảnh (mất góc/bố cục); set_match có giếng thì mất kiến trúc/vật liệu. Sửa: giữ câu hỏi checklist còn lại cạnh câu hỏi theo spec hoặc phân rã đầy đủ. Test ảnh có giếng nhưng sai kiến trúc; đúng số người nhưng logo sai; CU đúng size nhưng sai góc.
- **P1 mất ngoại lệ không thấy chân** — `core/llm_runner.py:876–883`, `core/qc_observe.py:67,143`: ON bỏ _no_feet_in_frame. Ca hẹp CU grounding=khong_thay cho **0.0**, qua hard_floor có thể gen lại ảnh đúng. Sửa: áp cùng NO_FEET_SIZES trước hỏi/kết luận, grounding=1 và bỏ lỗi chân theo policy hiện có. Test CU/MCU/MS không trừ/chạy autofix do chân; LS vẫn kiểm.
- **P2 kết quả VÀNG tới muộn** — `core/qc_observe.py:139`: transition trực tiếp thiếu already_processed như apply_qc:489; người duyệt trong lúc API chạy sẽ gây lỗi/đổi trạng thái không đúng. Sửa: helper giữ ảnh có expected-state + cập nhật có điều kiện để race an toàn; SUCCEEDED mới giữ, ảnh đã xử lý trả already_processed. Test FakeLLM callback approve trước lúc trả khong_chac, giữ approved, không transition/regen.
- **P1 thiếu ngữ cảnh hình học bị im lặng** — `core/qc_observe.py:14–17`: bỏ spec.geometry_missing từ qc_spec:226. Tái hiện compile_checks nhận geometry_missing vẫn sinh checks bình thường, có thể toàn xanh. Sửa: báo qc_missing_input hoặc VÀNG có lý do, không tự duyệt/regen. Test stage_camera khai nhưng thiếu kích thước/ngữ cảnh.
- **P1 ảnh chuẩn không phủ từng người** — `core/qc_observe.py:119–124`: reference_gaps kiểm ảnh tồn tại trong Kho; scene_references bị giới hạn gói; guard chỉ cần bất kỳ character. Người cuối cast mất slot vẫn model so mặt theo chữ. Sửa: dùng scene_storyboard.cast_missing trên refs thực gửi và kiểm file thực có; thiếu người/ảnh chuẩn báo rõ trước API. Test cast vượt cap, một file biến mất, tất cả nhân vật phải có ảnh.
- **P2 schema cần thống nhất** — `core/qc_observe.py:84–86`: schema additionalProperties=False nhưng judge bỏ qua mọi topkey. verdict/criteria bị bỏ qua là chủ ý và đã test; key lạ bất kỳ cũng được nhận (tái hiện secret_extra). Sửa: hoặc strict chỉ observations, hoặc whitelist verdict/criteria để bỏ qua và khai rõ schema; test unexpected key + model score/verdict không quyết kết quả.
- Không thay qc_rules/qc_measure hiện có; specialized side/cap/geo giữ VÀNG trong đường mới là an toàn nhưng chưa thay được phép đo code. BYĐ hiện đọc đúng thanh_phan.vat; empty must_keep đã chặn. OFF có kiểm prompt/images/output bằng baseline 08c11b4 trong nhóm 56 test xanh.
- Chưa đủ điều kiện báo việc 1 hoàn thành: còn caller bypass/thiếu policy nêu trên; case 678/680 mới fixture tổng hợp, không có bằng chứng trên ảnh sản xuất. Gom sửa **một vòng**, không nới test.

## Vòng sửa gom sau RÀ KỸ — kết quả bàn giao

- ĐỎ trước sửa: **14 failed / 89 passed / 12,13 s** trên 5 file qc_observe_d14/qc_team/lock_ngoai_le/qc_scene/autoqc. Lượt 2: 5 failed / 103 passed (fixture mock cần nhận keyword limit; bỏ recursion mock; đặt quyền mock). Lượt 3: **111 passed / 7,88 s**; giữ assertions hành vi cũ, OFF baseline vẫn xanh.
- Caller bypass: `observe_frames` dùng **một lời gọi cho cả cảnh**, `observe_frame` dùng cùng adapter thuần. `qc_scene.run_ready_scenes` ưu tiên enum trước team/agent/legacy chỉ sau gate claude_on hiện có. 4 cấu hình caller (legacy/team/agent/team+agent) đều có test; gate tắt không mở thêm lời gọi. Autoqc/autopilot vẫn tới qc_scene theo route hiện có.
- Giữ lớp 0: không đổi runner/qc_measure/qc_rules; flags cũ được ghi cùng note và mọi ảnh cảnh normal giữ người vì enum chưa nghiệm thu. Test SQLite 2 khung/1 call giữ cả hai pending_review + scene_qc_hold; shadow chỉ trainee_log, không đổi job/qc_results. JSON reviews giữ bằng chứng normal; shadow không lưu verdict người xem.
- Checklist luôn được hỏi cạnh các assertion, không mất logo/góc/kiến trúc khi đã có count/size/giếng. Profile Kho đã duyệt ưu tiên; generic character không yêu cầu Bible ghi đè. Sau pytest lượt 3, thêm thông số shot hiện hành vào detail checklist (angle/mood/location/BYĐ); kiểm assertion hẹp **3 ngữ cảnh + no-feet xanh**. Root cần đưa phần bổ sung này qua test tích hợp/cả bộ trước gộp.
- No-feet: reuse NO_FEET_SIZES, không hỏi grounding ở ECU/CU/MCU/MS; code giữ điểm 1 theo policy cũ. 4 case + LS vẫn trừ khi sai: xanh.
- Trạng thái VÀNG: helper hold khóa BEGIN IMMEDIATE rồi kiểm expected-state trước transition; ảnh đã được người duyệt trả already_processed. Có FakeLLM approve ngay trong complete + SQLite thật: approved giữ nguyên, không sinh job mới.
- Thiếu geometry_missing báo qc_missing_input; thiếu cast trong gói thực gửi kiểm scene_storyboard.cast_missing; file ảnh và thumbnail thực gửi đều phải tồn tại trước API. Test thiếu geometry/cast-cap/file-mất: xanh. Hồ sơ rỗng, BYĐ vật cấm, side giữ VÀNG cũng có test.
- Schema whitelist observations + legacy criteria/verdict bị bỏ qua; các topkey khác bị từ chối. Không lấy điểm/đạt của model.
- Tiền: giữ một look/cảnh (không tăng số lượt), cảnh gửi qua tagged qc/trainee + warning ước tính trước. cost.py đồng bộ estimate cảnh ON kể cả team/agent đồng thời, tránh cộng route bị thay. Test count estimate xanh; **không sửa project_budget.py đang chờ #24**, quote đó cần root xác minh riêng trước thử thật.
- Giới hạn: ảnh cảnh nhiều tham chiếu có thể chạm MAX_IMAGES hiện có (client báo lỗi rõ, không bỏ ảnh); chưa đo chất lượng/token/chi phí mới. Case 678/680 vẫn fixture tổng hợp; chưa chứng minh ảnh sản xuất. Outfit override chuyên biệt theo costume ngoài BYĐ chưa thay qc_spec, còn cần chốt scope #24 nếu dùng.
- Không gọi API/tốn tiền, không data thật/secret/lock_exceptions/scene_storyboard/runner/admin_auth/TODO/PLAN, không commit/push. Giữ devsys/areas.json version 56; module/test đã đăng ký ở step2. `git diff --check` xanh.

### Chốt theo root sau đọc diff

- Sửa quote cảnh enum theo **số khung tương đương** × (1 + REDRAW_SHARE), dù actual vẫn một call/cảnh; bỏ cộng tiền agent/team bị thay. Không sửa project_budget.py theo chỉ đạo root/chờ #24.
- Thêm test thông số angle/location/mood trong checklist; hồ sơ có OUTFIT riêng được chặn rõ `qc_missing_input` trước API, không chấm theo đồ mặc định Kho, không autoapprove/regen. Hỗ trợ chấm OUTFIT đầy đủ để việc sau; guard có test SQLite + 0 call/0 qc_results.
- Sau các thay đổi cuối, root cho phép chạy hẹp lại vì đầu vào mới: `py -m pytest -q -p no:cacheprovider tests/test_qc_observe_d14.py` → **39 passed / 0,52 s**. Kết quả nhóm 5 file trước đó **111 passed / 7,88 s**; fullsuite chưa chạy. `git diff --check` xanh.

Root đọc diff sửa và kiểm lại nhóm sau các chỉnh cuối context/quote/OUTFIT: 113 passed / 7,81 s trên 5 file; OFF baseline và scene gate xanh. Không gọi API hoặc chạy cả bộ.
