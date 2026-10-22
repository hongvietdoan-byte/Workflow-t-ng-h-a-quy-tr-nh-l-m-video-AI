# CX21-K-EVID — bằng chứng máy chính cho chính sách khóa/bật cờ

Ngày 21/10/2026, Asia/Saigon. Nhánh báo cáo `codex/v31-k-evid`, nền `46d73112`.

**Kết luận: đã thu bằng chứng độc lập, CHƯA đủ nghiệm thu chất lượng để khóa/bật các cờ.** Không đổi cờ production; phiên chính trình EP từng cờ. Test giả chứng minh cơ chế cạnh tranh/khôi phục, không chứng minh chất lượng ảnh/video hay không còn gửi trùng trong sản xuất.

## Phạm vi và cách chạy

- Đề: `docs/CODEX_TASKS.md` mục CX21-K-EVID; quyết định `v31-ep-flag-lock-policy-2026-10-21`, `v31-ep-k7-v31-flags-verify-2026-10-21`.
- SQLite backup từ `file:///D:/AI-Video-Pipeline/data/manifest.sqlite?mode=ro` tới `D:/AI-Video-Output/k-evid-20261021/manifest.sqlite`; phân tích bản sao bằng kết nối `mode=ro`, không gọi `core.db.connect` lên dữ liệu thật.
- SHA256 snapshot: `1546aa95a6088bd719f1ffbbc4bdbd785e251957da2b0928587306b7a0efd6e6`.
- Script, số liệu chi tiết và log test giữ ngoài Git trong thư mục evidence trên. Báo cáo không chứa prompt, payload gửi, ảnh, nội dung hồ sơ hay credentials.
- Phân tích offline thay **object** `os.environ` bằng dict giả trước import module; audit hook chặn mạng/subprocess và mọi mở file để ghi ngoài evidence-out. Không nạp `dashboard.env`, không gửi job/API, không migration, không ghi file/DB live.
- Chỉ đọc các media được `plate_layout.json` và `plates/index.json` hiện hành trỏ tới; không quét Kho. Dùng `plate_layout_qc.verdict` thuần, không gọi `check_strict`, `video_gate.plate_verdict` hoặc `place_refs.shot_ref`: các đường đó có thể ghi diag/record hoặc ảnh lift.
- Các phép thử media là **recompute đầu vào hiện hành**, không phải replay lịch sử đầy đủ: scene/Kho lấy từ snapshot, file media/index từ máy chính; nhiều `plate_key` đã đổi. Không đánh đồng với số ca báo nhầm đã được người xác nhận.

## 1. qc_false_alarm_fix / horizon_needs_sky

### Kho bằng chứng đã ghi

| Dự án | Dòng qc_results | Dòng trainee scene_qc có phép đo size | Bộ observation có nhãn truth độc lập |
|---|---:|---:|---|
| #31 | 176 | 5 | Chưa có trong phần đã thu |
| #33 | 0 | 0 | Chưa có trong phần đã thu |

`qc_results` chỉ lưu criterion/score/threshold/auto_decision, không chứa toàn bộ enum observation/bằng chứng vùng nhìn của `qc_observe.judge`. `llm_calls` chỉ có metadata/token/nguồn, không response. Không thể tự dựng lại quyết định model cũ từ các bảng này. Không gọi `qc_observe.run/review_scene`, vì chúng có đường trả phí và ghi trạng thái.

### A5 — cỡ cảnh qua vai/sau lưng

Dùng 5 phép đo đã ghi trong `trainee_log.detail.size` và predicate `_behind_any` với scene hiện hành. Đây là replay nhánh quyết định size, không gọi lại detector/model.

| Dự án · shot | Job | Đo / kế hoạch | Nhánh cỡ cảnh OFF | Khi ON | Truth độc lập |
|---|---:|---|---|---|---|
| #31 · S3 | 947 | WS / WS | Không flag size | Giữ kiểm | Thiếu |
| #31 · S5 | 949 | WS / WS | Không flag size | Giữ kiểm | Thiếu |
| #31 · S19 | 960 | MLS / MS | Có flag size | Bỏ phán cỡ vì bố cục sau lưng/qua vai | Thiếu |
| #31 · S20 | 961 | MLS / MLS | Không flag size | Giữ kiểm | Thiếu |
| #31 · S22 | 963 | WS / WS | Không flag size | Giữ kiểm | Thiếu |

**Một flag size có thể bị bỏ, chưa được gọi là một false positive đã sửa.** Không có truth độc lập để tính false positives trước/sau hoặc missed true cases. Đúng ca P33-A5 (#33 S2) không có phép đo lịch sử trong DB. Thử hàm thuần `check_frame` trên hai ảnh hiện còn của S2 (job 1177, 1181): OFF/ON đều không có mã lỗi và không có phép đo mặt; không dùng kết quả này làm bằng chứng cỡ cảnh đúng.

### A6 — thiếu thông tin video tham chiếu trong đề rà

Dựng riêng ngữ cảnh `change_review.build_prompt` từ snapshot cho 6 shot #33 bằng sự kiện thử chỉ tồn tại trong bộ nhớ, cờ khác giữ TẮT. Không gửi đề cho model, không ghi change_event/finding.

| Shot #33 | ref_video_path có dữ liệu | OFF có trường video tham chiếu | ON có trường đó |
|---|---|---|---|
| S1–S6 (6/6) | Có | Không | Có |

Đây là bằng chứng **thông tin được đưa vào đề**, không phải replay kết luận agent của P33-A6. Tên file/nội dung đề không đưa vào Git. Chưa có response lịch sử và nhãn đúng/sai độc lập, nên số báo nhầm/missed true cases là **chưa đo được**, không phải 0.

### G20 — chân trời khi không có trời

Có 95 record plate_layout của #31, 35 của #33; index hiện hành tương ứng 39 và 6 shot. Nhiều record mất media hoặc trỏ plate cũ. Chỉ bảng dưới là các ca mục tiêu còn đủ file để recompute; bật dependency `place_render_refs` trong bộ nhớ để kiểm nhánh indoor, không bật cờ live.

| Dự án · shot | Job | OFF | ON | Nhận no-sky | Plate key record = hiện hành |
|---|---:|---|---|---|---|
| #31 · S22 | 963 | ĐỎ | ĐỎ | Không; không đủ dấu hiệu theo nguồn hiện có | Có |
| #31 · S39 | 980 | ĐỎ | VÀNG | Có: overhead | Không |
| #33 · S2 | 1177 | VÀNG | VÀNG | Không | Không |
| #33 · S2 | 1181 | VÀNG | VÀNG | Không | Có |

S39 minh họa nhánh bỏ chân trời, nhưng **không chứng minh đã sửa ca lịch sử** vì plate key khác. S22 vẫn ĐỎ khi bật; cần chủ khâu kiểm lại dấu hiệu trong nhà/spot/nguồn hình học của đúng ca. Hàm giữ kiểm khi không rõ, không tự coi là trong nhà theo nhãn tài liệu. Chưa có cặp ca lỗi thật được người xác nhận để chứng minh không bỏ sót lỗi đúng.

`video_gate.plate_verdict` ưu tiên diag `plate_layout` đã ghi; nếu có record cũ, chỉ đổi cờ không tự tính lại record đó. Vì vậy nghiệm thu production cần quy trình tái kiểm được duyệt trên bản sao, không coi toggle cờ là đã sửa các cổng cũ.

## 2. send_claim — số liệu và hành vi khi khóa

Đếm toàn bộ hàng `jobs` trong từng dự án; `external_present` chỉ là hàng có external_id. Một external_id dùng ở nhiều hàng có thể là draft/final/group follower, **không mặc nhiên là gửi trùng**. `repeated running` là cùng job có hơn một event `to_state=running`; cũng không tự chứng minh đã có hai task trả phí.

| Dự án | Jobs | Có external_id | Job có >1 running event | Nhóm external_id dùng chung | Claim hiện tại |
|---|---:|---:|---:|---:|---:|
| #27 | 227 | 207 | 0 | 32 | 0 |
| #28 | 10 | 10 | 0 | 2 | 0 |
| #29 | 10 | 10 | 0 | 2 | 0 |
| #30 | 9 | 9 | 0 | 0 | 0 |
| #31 | 187 | 168 | 5 | 16 | 0 |
| #32 | 0 | 0 | 0 | 0 | 0 |
| #33 | 65 | 56 | 0 | 0 | 0 |

#27 có 1 dòng diag `send_claimed`, tổng count=1. Các dự án khác không có mã này trong snapshot. `job_send_claims` là giữ chỗ tạm, không phải lịch sử mọi lần claim; không có hàng hiện tại không có nghĩa chưa từng claim. DB không đủ sổ submit/request id từng lần để kết luận tổng số gửi trùng thực tế hoặc số tiền mất; ca lịch sử job776 được nêu trong test không thay cho đối soát provider.

Side effects khi khóa ON (`core/send_claim.py`, `core/runner.py:submit_pending/_submit_pending`):

- Giữ chỗ bằng SQLite `INSERT OR IGNORE`, commit trước bước gửi; tạo bảng trên DB cũ nếu thiếu. Có thêm ghi/commit/đọc lại mỗi job, liên quan lock/transaction và độ trễ SQLite.
- Tiến trình khác giữ claim → bỏ lượt gửi với diag; lỗi DB → fail-closed, chưa gửi lượt đó. Claim hết hạn sau 900 giây; crash có thể làm job chờ TTL. `finally` giải phóng claim khi lượt kết thúc.
- OFF vẫn tôn trọng claim đang tồn tại của tiến trình ON và đọc lại trạng thái; không phải OFF thì gửi bất chấp.
- Entry point chung phục vụ bấm tay/vòng nền/script dùng Runner; không khẳng định đường gửi ngoài Runner đã được bao phủ.
- Reconcile submit không rõ kết quả thuộc **poll_claim**, không phải send_claim tự giải quyết mọi crash-after-submit. Không gộp bằng chứng hai cờ thành một bảo đảm exactly-once với provider.

## 3. back_view_guard — gói thật và dependency

Đếm mọi hàng jobs có `sent_package` JSON không rỗng, không deduplicate draft/final/phiên bản; số dưới là **gói của hàng job**, không phải số shot độc lập hay số lượt trả phí. Tìm câu guard chính xác `stays with the back to the camera for the whole shot` trong các string value của JSON; không đưa payload vào báo cáo.

| Dự án | Gói JSON | Có câu guard chính xác | Có nhắc back/from behind rộng (chỉ ngữ cảnh) |
|---|---:|---:|---:|
| #27 | 207 | 35 | 136 |
| #28 | 10 | 3 | 8 |
| #29 | 10 | 2 | 8 |
| #30 | 9 | 0 | 3 |
| #31 | 168 | 0 | 38 |
| #32 | 0 | 0 | 0 |
| #33 | 56 | 0 | 1 |

Không gói JSON lỗi trong tập đếm. Một câu back rộng không chứng minh guard đã áp; có câu guard cũng không chứng minh clip giữ lưng suốt shot.

Dependency/side effects (`core/seedance_refs.py:enabled/back_view/shot_motion`): đường reference-only cần dự án `shot_mode=per_shot` và `seedance_ref_groups`. Guard chỉ nhận mệnh đề quay lưng gắn nhân vật; shot nhiều người không đoán người quay lưng. Ý đồ quay mặt về camera/ngoảnh lại được giữ. Nếu cả cast quay lưng, bỏ tả face/eyes; giữ body/timing và thêm câu không quay mặt. Nếu chỉ một người quay lưng, vẫn giữ tả mặt cho người đối diện máy. Khóa ON đổi prompt **mới được dựng** và do đó có thể đổi kết quả gen; không sửa gói/job cũ, không tự gửi lại. Các luồng không dùng builder này không được coi là đã được bảo vệ.

## 4. Test Windows và giới hạn nghiệm thu

Một lệnh tuần tự, native Python 3.14, không xdist: `pytest -q --tb=no -rf -p no:cacheprovider` với `tests/test_send_claim.py`, `tests/test_v31_m12_poll_claim.py`, `tests/test_v31_t12_m12_m13_gaps.py::test_two_real_processes_poll_one_job_once`, `tests/test_code_motion_p27.py`; lọc `-k "claim or unknown or crash or back"`.

**32 passed, 22 deselected, 17.46 giây, exit 0.** Provider giả, SQLite/file tạm; không chạy cả bộ. Native process được khởi động với whitelist env rõ ràng, fake HOME/TEMP; wrapper thay object environ trước import pytest/target. Không `--showlocals`, không in môi trường/headers/credentials; không đổi env User.

Bằng chứng cơ chế: race gửi OFF tạo 2 lần submit giả, ON còn 1; 2 thread/2 connection chỉ gửi một lần; stale sender/DB error/release/TTL được kiểm. Hai **process thật** kiểm đường poll chỉ tải/chuyển succeeded một lần; crash giữa download và submit-unknown/reconcile được kiểm riêng dưới poll_claim. Back guard kiểm loại bỏ face/eyes, giữ body/timing và các ngoại lệ quay mặt có chủ đích, phủ định, nhiều người.

Không sửa mã triển khai nên không có vòng viết test ĐỎ→sửa→XANH ở nhánh báo cáo. Test hiện có chứa cặp OFF tái hiện lỗi/ON ngăn lỗi và đã chạy xanh; không nới test. Không gộp main/restart Dashboard.

### Còn mở trước quyết định Cấp 3

1. A5/A6/G20: cần bộ artifact+observation+truth đã xác nhận và provenance lịch sử; hiện chưa tính được false-positive/false-negative đáng tin. S22 chưa cho thấy cải thiện, S39 không cùng plate key.
2. Cổng video đọc diag cũ cần kiểm quy trình tái kiểm trên bản sao; không tự xóa record/ghi đè dữ liệu thật.
3. send_claim: đối soát lịch sử provider khi được cho phép để phân biệt group/final với duplicate-submit; các số proxy không đủ kết luận không còn trả phí hai lần.
4. back_view_guard: cần người xem clip thật trước/sau, gồm ý đồ quay mặt hợp lệ; câu prompt không là chất lượng video.
5. Acceptance/rollback do EP chốt từng cờ. Chưa đổi production nên không có thay đổi cần rollback ở lượt này; nếu được bật sau này phải giữ snapshot cờ và đường tắt được duyệt. Không tự gen lại để nghiệm thu.
