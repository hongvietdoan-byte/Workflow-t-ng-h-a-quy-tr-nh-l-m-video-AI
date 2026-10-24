# CX24-P34-DASH-FIXES — checkpoint Codex 1 (24/10/2026)

**XONG phần code + unit + AppTest fixture theo thư PHÂN CÔNG TỔNG 223827-en7n; chờ phiên chính tích hợp.** Nhánh `codex/v31-p34-dash-fixes`, worktree cùng tên dưới `.codex-wt`, nền ban đầu `origin/main` a700ead8, đã đồng bộ CLI/D6 bằng merge2ce7ea95. Nhận `20261024-175930-codex-9fnb.json`, báo phạm vi `20261024-180037-codex-g8re.json`. Không tự gộp/restart live.

## Đã làm trong checkpoint

### Mục6 — audit dùng đúng hồ sơ nhân vật đã liên kết

`core/change_audit.py` đọc characters đúng project và tên Unicode, ưu tiên ref_asset_id đã lưu; kiểm must_keep trên đúng profile dù tên asset khác và chưa có ảnh. ID0/brokenID/sai loại/asset thuộc project khác/duplicatecharacters báo VÀNG rõ, không fallback âm thầm. Chỉ NULL/DB legacy mới dò tên, ưu tiên project_assets rồi toàn Kho khớp duy nhất (có dấu/alias trước, fold chỉ khi duy nhất). Không đổi liên kết/profile hoặc ghi DB. Profile JSON/schema lỗi báo VÀNG. Giữ narrator không làm nhân vật Kho.

RED thực tế **13 failed,6 passed/1,16s** → GREEN **19 passed/0,56s**, gồm ba test_change_audit cũ. Reviewer độc lập rà ID/scope/alias/callers/không ghi DB: **0 P1/P2 trong diff mới**. Lưu ý tồn tại từ trước: audit_shot nhận scene_id và các caller đã rà truyền đúng pid; chưa đổi hợp đồng scene query ngoài phạm vi định danh.

### Mục11 — nhãn ảnh hiển thị model mà runner chọn

Helper thuần `dashboard/image_model_label.py`; hai layout Step2 dùng cùng nhãn. Provider hỗ trợ model= dùng image_models.of_project(proj), đúng thứ tự project→DEEPIX_MODEL→DEFAULT của ImageRunner; provider cố định dùng model của adapter; thiếu metadata nói chưa xác định. Không khởi tạo provider/call mạng, không đổi kwargs gen/widget keys/chi phí.

RED **1 error collection/0,56s** trước helper → GREEN **9 passed/0,31s**; hai project khác model, provider cố định, metadata thiếu, fallback/env giả, mock và AST wiring. Reviewer độc lập **0 P1/P2** trong helper/diff/callers.

Root đọc hai phần sửa, chạy nhóm unit serial nhẹ bằng OBJECT os.environ giả, HOME/TEMP giả, keyring giả và winreg.OpenKey bị mock trước pytest/import/call: **28 passed/0,77s** (hai test mới + test_change_audit, số ca chồng nhóm child, không cộng trùng). `--tb=no`, không plugin tự nạp/xdist/server. areas.version92, khai helper/tests ở step2 và plates3d.

## Trạng thái chốt theo phân công 23:00

| Mục | Bằng chứng / giới hạn |
|---|---|
|1|EP/lý do/audit/snapshot/hash, materializer, root100unit; AppTest mới kiểm banner/EP skip/nonEP. Canonical G1 API đã dùng nhưng assignedEP phải kiểm lại sau khi main GỘP.|
|2|Ô CLI/cache/email/ownedtree cleanup và thông điệp login: unit/mock và AppTest email/runtime/refresh/settingsdenied xanh; không gọi auth status thật. OS từ chối kill cây chưa chứng minh dọn hết con.|
|3|Proposal theo project/ledger/budget, xác nhận hai bước rồi draft ghim, N4 riêng; root76unit+manual4+budget7 và AppTest consent/draft/pin/reset/noingest. Chưa Claude CLI thật.|
|4|Kho CHUNG theo thư18:54, quyền mới/CAS/v1unknown/v2guard: root34unit; AppTest số0/xác nhận/snapshot/save→rerun. Không clone dự án.|
|6/7/11|AuditID/camera_side+thay_min/nhãn model: unit/mock đã push, AppTest bàn đạo diễn cũ29 xanh. Chưa Blender/ca #34 thật.|
|10|Giữ s sau identity+cổng máy, thiếu phiên báo đăng nhập lại: root12unit/mock. Không cookie/SSO. Rà token URL là task mới CX24-URL-TOKEN-RA.|
|8/9|Chỉ thiết kế, đúng phạm vi đề bài.|

Không gộp code main, không restart live; bàn giao phiên chính chạy cả bộ/tích hợp G1 và nghiệm thu thực tế. Các mô tả CHƯA AppTest ở checkpoint bên dưới là lịch sử trước lượt chốt này.

## Thiết kế nháp mục8/9 (chưa triển khai)

- Đồng bộ đổi chỗ đứng: dùng registry A/approved blocking là nguồn duy nhất. Proposal giữ revision/segment/subject IDs; người duyệt thấy diff shot bị ảnh hưởng và artifact nào cũ. CAS/apply một transaction theo API A, không ghi tọa độ vào registry thứ hai. Chỉ invalidation dependency đã đổi; không tự gen/render lại hay tự gửi provider. Cần tests clone/multi-shot/stale revision/khóa tay và quyền EP trước nối UI.
- Dựng từ video tham chiếu: người dùng chọn file được phép dùng + đoạn giây/speed/crop, lưu provenance/hash và phạm vi dự án. Offline FFmpeg trích nhịp/keyframes/audio thành proposal có confidence; thiếu metadata báo VÀNG/UNKNOWN, không đoán source. Director duyệt rồi mới đưa vào storyboard/blocking nguồn A. Mọi bước phân tích model trả phí/gen lại phải dự toán và xin riêng; không tải TikTok/Apify hay gọi API trong task này.

## Giảm tải và giới hạn

Theo thư175249-xxc7/175629-mfn2: giảm tải tới22h và **chờ thư TĂNG TỐC**, không tự tăng tốc theo đồng hồ. Pytest chỉ serial targeted (trần n2), mỗi lúc chỉ một phiên test nặng; đã hỏi điều phối AppTest trước dùng. Không cả bộ, không Streamlit/Blender/headless/Computer Use. Unit checkpoint không tạo server/process nền, chỉ SQLite giả/temp. Không data thật/dashboard.env/secrets/admin_auth/special runner files/API trả phí; 0USD. Toàn task còn ĐANG LÀM, chưa thử UI thật/chưa nghiệm thu #34.

## Checkpoint tiếp — nền mục 1 (chưa nối UI)

`core.change_review.refresh_failed_findings(conn, project_id)` đồng bộ mục đỏ cho các shot của dự án trước khi ai gọi blocking. Dùng đúng `_hold_failed` hiện có: cùng cờ motion, quota giữ cổng, không nhân đôi mục, lỗi đã bỏ qua không mọc lại, lỗi mới mở lại, chính event reviewed/skipped thì tự đóng. Savepoint bao cả lượt; không commit transaction caller, lỗi giữa chừng hoàn tác riêng lượt đồng bộ. `open_findings` giữ chỉ đọc. Chưa caller production, chưa nối màn hình hay thay quyền/Bỏ qua: không tuyên bố đã gỡ lỗi Dashboard.

RED **6 failed/0,99s** trước helper → GREEN **9 passed/0,42s** sau bổ sung ca rollback giữa chừng trong/ngoài transaction và read API không ghi. Nhóm targeted mới + hồi quy `test_change_review` **22 passed,52 deselected/4,91s**, serial, OBJECT môi trường/HOME/temp giả + keyring/winreg giả trước import. Không provider thật/server/AppTest. Reviewer độc lập rà helper/lifecycle/scope/transaction và callers autopilot/before_run/inbox_clean/prompt_rewrite/runner/change_review_ui: **0 P1/P2 trong diff mới**, root đọc lại hai lượt. Khai test ở core_infra; giữ areas.version92.

Mục1 vẫn còn UI rõ lý do/lượt rà lỗi, quyền EP canonical + lý do/audit/chống bypass lỗi mới, dự toán Rà lại. G1/CLI dependency vẫn theo câu hỏi180630-j3np. Mục7 đang triển khai độc lập bằng unit hình học, không Blender; không thay registryA.

## Thiết kế mục 8/9 — ranh giới và tiêu chí nghiệm thu

Đây là đề xuất thiết kế trong phạm vi đề bài, chưa phải tính năng đã triển khai hay cho phép chạy production.

| Khâu | Đổi chỗ đứng / máy / thời tiết (mục 8) | Dựng từ video tham chiếu (mục 9) |
|---|---|---|
| Đầu vào | Project/scene/shot IDs, revision A đang duyệt, subject IDs liên kết Kho, thay đổi có đơn vị m/độ và lý do | File người dùng có quyền sử dụng, hash, đoạn đầu/cuối, tốc độ, crop/aspect và nguồn; không tự tải URL |
| Xem trước | So sánh revision cũ/mới; danh sách shot, nền, prompt ảnh/motion và job bị ảnh hưởng; tách khóa tay khỏi phần sinh | Trích keyframe/nhịp/âm thanh offline thành bản đề xuất theo shot; mỗi quan sát ghi timecode, nguồn và mức chắc chắn |
| Thiếu đầu vào | Thiếu chỗ đứng/height_m/trục hoặc góc sau cờ OFF thì báo rõ; không chèn tọa độ/góc ngoài nguồn A | Ref cũ thiếu metadata báo VÀNG; không đoán tốc độ/timecode hay tự nhận khuôn mặt/chủ thể |
| Duyệt và ghi | EP duyệt diff theo API A; kiểm quyền/khóa/revision phía server, CAS toàn gói và giữ draft khi conflict | Đạo diễn chuẩn hóa proposal theo schema hiện hành, EP chốt cấu trúc trước apply A; không biến độ tin cậy AI thành duyệt |
| Hậu quả | Chỉ đánh dấu cũ các artifact phụ thuộc revision đổi; trường người khóa không bị tự ghi đè | Tạo kịch bản/blocking/audio-reference có provenance; không sao chép token, đường dẫn cá nhân hay dữ liệu dự án khác vào prompt |
| Chi phí | Apply không đồng nghĩa gen lại; mỗi lượt gen/render có dự toán, cổng/pregen và xác nhận hiện có | FFmpeg offline 0 USD vẫn có hàng đợi/timeout; phân tích model/TTS/ảnh/video trả phí phải có dự toán và duyệt riêng |
| Nghiệm thu | Fake multi-shot/multi-project, stale revision, mất quyền giữa preview/apply, khóa tay, rollback toàn gói và invalidation đúng phạm vi | Fake video ngắn: khớp timecode/speed/crop; metadata thiếu không tự điền, hash đổi vô hiệu proposal cũ, không tự gọi mạng; chờ người xem chất lượng thật |

Lộ trình: đọc pinned snapshot → dựng proposal/diff → EP duyệt → apply transaction qua nguồn A → đánh dấu artifact cũ → người dùng chọn dựng lại. Hỏng bước apply phải rollback cả gói; hỏng gen sau apply giữ trạng thái và chẩn đoán, không tự lùi revision đã duyệt. Không nối hệ tọa độ/registry thứ hai, không bật `anchor_by_spot` hoặc cờ góc mới trong task này. Cơ bản/Nâng cao cùng gọi backend guard; clone không sao chép approval/quyền từ dự án nguồn. Các test trên là tiêu chí phải xây dựng khi được giao triển khai, chưa có kết quả chạy thật cho mục 8/9.

## Checkpoint mục 7 — phía máy và ngưỡng vật phụ

Bổ sung `camera_side` vào yêu cầu khung: trái/phải giữ nguyên `axis_side`; trước/sau dùng tích vô hướng từ trung điểm trục có hướng A→B, không đổi world axes hay vị trí chủ thể. Thiếu trục, trục trùng điểm, vị trí không hữu hạn hoặc phía không hợp lệ thì báo lỗi. Solver có seed theo phía; C2 kiểm ứng viên K3 và số đo K4, cả khung đầu/cuối. Không bỏ qua ràng buộc khi khó tìm máy. Vật phụ có `thay_min` từ 0–100% thành ràng buộc S1; không khai thì giữ hành vi mềm trước đây.

N4 của Quay phim/Quay phim duyệt thêm lựa chọn phía và ngưỡng từng vật phụ từ JSON đã dán. Lựa chọn chỉ sửa bản copy JSON rồi đi `stage_desk.load_answer` với user/actor/khóa/xác nhận/duyệt cũ; không ghi máy/state trực tiếp, không gọi provider. Để trống ô JSON vẫn đọc file như cũ; lựa chọn mới chỉ hiện khi đã dán JSON. Giữ widget keys cũ; khóa widget mới chứa digest semantic JSON để đổi ý đồ phải chọn lại, không đưa raw payload vào key.

RED hình học **16 failed,5 passed/0,43s**; helper UI **1 collection error/0,83s** trước file mới. Sau rà độc lập gom **3 P2**: `shots=null` gây TypeError; shot/vật phụ trùng gây trùng widget; lựa chọn cũ đè JSON mới. Đã sửa bằng kiểm container/khóa trước vẽ và namespace digest canonical. Ca stale thực **1 failed,12 passed/0,46s** → GREEN nhóm child cuối **68 passed/1,68s**. Root đọc fixdiff hai lượt và mở rộng đúng hồi quy hình học thuần: hai test mới + stage_solver/stage_grid/stage_rules **98 passed/2,49s**. Rà vòng 2 và caller identity_declare/shot_intent/plates3d/step2: **0 P1/P2 còn lại trong phạm vi đã gom**.

Đây là bằng chứng unit hình học và mock widget nhẹ, **chưa phải nghiệm thu UI/Blender/dự án #34 thật**. Không AppTest/server/headless/CU, không paid API hay DB thật; tất cả test có OBJECT os.environ/HOME/temp giả và mock registry/keyring trước import. Không cờ mới, giữ areas.version92 và cờ stage_desk_ui như nền. Đã khai helper + hai test trong areas.

Trạng thái toàn task: **ĐANG LÀM**. Code mục6/7/11 đã có; nền mục1 đã push00992f34, còn nối UI/EP/audit/Rà lại. Mục2/3/4/10 và nghiệm thu GUI còn mở. Mục8/9 đã ghi thiết kế đủ luồng/tiêu chí, chưa triển khai. Vẫn chờ main trả lời180630-j3np về dependency G1/CLI và lịch QA nặng; không coi im lặng là duyệt hoặc tự mở lượt test nặng.

## Thư phiên chính mới hơn — 18:26:56 (182656-par2)

Câu hỏi180630-j3np ĐÃ ĐƯỢC TRẢ LỜI: G1/CLI còn trong worktree tích hợp main; **không merge/cherry-pick nhánh Codex lẻ vào P34-DASH**. Viết theo API trong6d647212/296fc658, chỉ rebase sau thư báo GỘP của phiên chính. Trước22h chỉ unit nhẹ; AppTest serial nặng sau22h và điều phối một phiên, vẫn chờ thư TĂNG TỐC trước nới tài nguyên. Thay thế các dòng 'còn chờ reply180630' ở trên.

Đang làm độc lập mục2 qua ClaudeCliClient.clean_env() public đã có cả ở nền và296fc658; không sao chép bộ lọc env/giải pháp token. Mục1 khi nối UI: giữ API đọc chỉ đọc; bookkeeping tạo đỏ qua refresh riêng; Bỏ qua dùng guard EP canonical, lý do + audit nguyên tử và snapshot phiên bản lỗi. Nút bỏ qua phải gắn snapshot vào khóa/nonce để Streamlit rerun không tự lấy lỗi mới chưa xem làm bằng chứng người đã duyệt. Không dùng close() commit giữa transaction audit; không để ngoại lệ DB/audit làm mở cổng. Đây là ghi chú thiết kế triển khai tiếp, chưa phải phần đã code.

## Checkpoint mục 1 — hiển thị lỗi trước khi có mục đỏ

Thêm `failed_review_summary` chỉ đọc: cùng cờ scene/motion/quota, đúng project theo scenes; mục lỗi đang mở vẫn hiện, chỉ mục đã đóng bởi người mới che lỗi cũ. Lý do qua diag.redact; không trả token/payload thô. UI gọi trước open_findings: hiển thị “Rà soát LỖI” cùng số lần/lý do cả khi blocking chưa từng chạy; lỗi đọc sổ không biến thành trạng thái sạch. Không gọi materializer hay thay close/blocking/quyền, nên chưa thêm đường bỏ qua tự do. Màn read_only cũng chỉ đọc, không ghi DB.

RED ba ca summary **3 failed/0,36s** → GREEN12/0,41s; bổ sung hai mock screen không import Streamlit/AppTest. Reviewer phát hiện **1 P2**: cả scenes/change_events có state nhưng query dùng field không alias. Fixture thêm scenes.state như production: **4 failed,10 passed/0,32s** → sửa rõ e.state/e.note → **14 passed/0,35s**. Rà vòng2 **0 P1/P2** trong summary/caller, root đọc fix hai lượt. Không nới schema/test; giữ API đọc không commit.

Đây là phần hiển thị, chưa hoàn tất toàn mục1: mục đỏ materializer chưa nối UI trước khi đường Bỏ qua EP/lý do/audit/chống lỗi mới được kiểm; nút Rà lại có dự toán vẫn phải nối/kiểm. Không tuyên bố người dùng đã gỡ được mọi cổng trên Dashboard. Module CLI status đang hoàn thiện riêng, chưa dùng API/model/credential thật.

## Checkpoint mục 2 — tài khoản Claude CLI của pipeline

`core/cli_auth_status.py` dùng duy nhất `ClaudeCliClient.clean_env()` public (đã đối chiếu API296fc658, không sao chép bộ lọc env/token, không sửa llm_runner). Chỉ chạy `auth status` khi người có quyền Cài đặt mở dialog qua ⚙ Hệ thống; dự án không chọn claude_cli không gọi lệnh. Hiện trạng thái/email allowlist, binary/config path của đúng môi trường pipeline, hướng dẫn đăng nhập bằng đúng runtime; email thiếu/sai không bị bịa và được ghi chưa xác định. Không đọc file credential, không trả stdout/stderr/ngoại lệ/payload thô. Đệm30giây theo runtime/config/HOME/env hash, nút Kiểm lại bỏ cache; không spawn mỗi lần rerun khi dialog đóng.

Popen có nhóm/session riêng; timeout8giây dừng cây đúng PID sở hữu (Windows taskkill /T /F, Unix killpg), thu hồi cha, đóng pipe thành công/timeout/lỗi. Không kill theo tên process. Nếu OS từ chối dừng cây, fallback chỉ xử lý cha; **chưa chứng minh cây con hết trên máy thật**. Thu hồi có timeout riêng nên tổng thời gian lỗi có thể dài hơn8giây, không phải cam kết HTTP8giây.

RED helper **1 collection error/0,61s** →20unitxanh/0,88s. Rà gom hai nhóm P2: (a) thiếu dlg_cli_auth trong DIALOG_FLAGS nên nút không mở; thêm workflow fake dùng open_dialog thực, **1 failed,20 passed/12,88s** →21xanh/0,59s; (b) run() timeout chỉ dừng shim.cmd, chuyển ownedtreePopen, **1 failed,21 passed/0,60s** →24xanh/0,67s. Vòng rà cleanup bổ sung communicate OSError không thu hồi + pipe chưa đóng: **3 failed,24 passed/0,71s** →27xanh/0,68s. Reviewer cuối **0 P1/P2 còn lại trong phạm vi đã gom**, root đọc fix hai lượt.

Root chạy chung đúng nhóm mới + hồi quy change_review bằng OBJECT môi trường/HOME/temp giả, keyring/registry giả trước import: **54 passed,52 deselected/3,35s** serial. Trong test CLI, Popen/run thật bị chặn, chỉ fakeprocess; Windows/Unix cleanup đều mock. Không AppTest/CLI/native/account thật/server/headless/Blender/CU/API trả phí. Không coi mock là bằng chứng đã đăng nhập được trên máy thật. Đăng ký helper/test ở core_infra, giữ areas.version nền92.

Phần lỗi khâu CLI cần thông báo rõ trong luồng job/giao vai vẫn phải đối chiếu khi nối mục3 và tích hợp main; hiện runner chỉ có hint auth cũ, chưa sửa ở checkpoint này. Mục2 mới có ô chẩn đoán tài khoản, chưa nghiệm thu CLI thật.

## Phụ thuộc / bước kế cập nhật lúc 18:40

- Phiên chính đã GỘP CLI-TOKENS và D6 ở **f4031e9b** (183108-z58j/183035-af16); G1 vẫn chưa GỘP lúc kiểm. Không cherry-pick nhánh lẻ; trước nối giao vai cần cập nhật nền từ main đã công bố. Nhánh task đã push nên không tự force-push để rebase; nếu đồng bộ bằng merge main vào nhánh task phải giữ đủ đăng ký areas/test và báo rõ.
- Mục10 đã hỏi **183043-codex-1f60**: hiện chỉ querys/session_state, không có cookie helper; cần xác định transport phục hồi token cho tab/URL mới, giữ auth.identity/machine_auth/revocation. Chưa có câu trả lời lúc kiểm, không tự tạo registry quyền khác.
- Mục4 khảo sát API hiện có: set_profile v1 chỉ biết PROFILE_KEYS, không giữ mọi unknownfield; set_profile v2 dùng CAS/actor đúng; không có cloneasset nguyên tử. create/set_profile/set_character_link tự commit riêng nên UI không được ghép chuỗi tạo bản riêng có thể mồ côi/mất ảnh. Cần backend clone+profile/image mapping+projectlink/ACL/CAS chung transaction từ vùng Kho đang do Codex3 giữ; chưa tự viết writer cạnh tranh.
- Tin183413-zii9 giao việc main-red cho Codex rảnh: phiên này đang P34, chưa nhận/chưa sửa runner/tools/dependency ấy để tránh chồng phiên khác.
- Toàn task vẫn **ĐANG LÀM**: còn1 EP/lý do/audit/Rà lại,3 giao vai,4 height_m(shared/private),10 cookie/token transport, hoàn thiện2 lỗi job và QA sau điều phối. Code6/7/11 không làm lại;8/9 chỉ thiết kế. Không phát eventxong sớm.

## Mục 1 — cổng bỏ qua có EP/lý do/audit/snapshot

Đã nối materializer vào UI chỉ khi có quyền sửa; chỉ đọc vẫn chỉ đọc. Lần lỗi có mục đỏ trước khi ai gọi blocking, hiện nút Rà lại với paid_confirm/dự toán cũ. Lỗi read/refresh không được hiện sạch. Phiên AI không có nút Bỏ qua. Nút Bỏ qua lỗi thay bằng EP + lý do, snapshotnonce trong widget key để rerun/click cũ không tự chấp nhận lỗi mới; khóa ordinary controls không đổi.

Backend `dismiss_failed_review` dùng `_need_ep` canonical của stage_desk, đọc lại users.active/role từ server, yêu cầu actorhuman trùng identity, đúngproject/scene/source/open và snapshot đầy đủ. Updatefinding + audit trong một savepoint; audit hỏng rollback toàn bộ, transaction caller không bị commit. Cờ change_reviewOFF không ghi bypass. `close(... dismissed)` cho review_fail bị từ chối, không còn đường rawclose bỏ qua kiểm EP. Bốn ca lifecycle cũ đổi sang fixture EP/lý do/audit; không bỏ/nới khẳng định giữ/mở cổng.

RED **15 failed/0,56s** trước API → GREEN15/0,31s. Rà gom2P2: coverage cũ chỉ so timestamp đến giây có thể che cùng event lỗi lại SAU khi EP bỏ qua; UI đọc snapshot ngoài try có thể crash khi finding bị đóng đồng thời. Sửa marker `event_versions` id→hash(kind,state,fulltimestamp,note) trong audit, không lưu rawnote; blocking mở lại đúng finding có bằng chứng phiên lỗi đổi, summary readonly cũng hiện phiên mới. UI race có caption tải lại + không vẽ nút stale. Ca lỗi cùnggiây sau skip RED1/0,25s → xanh; mock UI nonce/race bổ sung. Kết quả root toàn `test_change_review` +2file P34: **100 passed/10,65s** serial, fakeenv/DB/model. Reviewer vòng2: **0 P1/P2 trong phạm vi đã gom**, root đọc fix hai lượt. Audithistory lookup còn quét action mới theo scene có dismissed; chưa benchmark production.

Giới hạn: chưa AppTest/GUI/#34 thật. G1 chưa main nên EP đượcgán riêng mới kiểm qua contract API/mock, Owner/quyềncanonical nền giữ nguyên; chờ gộp G1 trước chốt tích hợp. Không migration, không trảphí/data thật/API; role/audit dùng nguồn cósẵn. Đã merge main đãGỘP CLI/D6 vào nhánhtask bằng **2ce7ea95**, xử lý3block areas bằng unionkhai báo/cờ, version92, không rewrite/forcepush và không gộpcode vào main.


## Mục 3 và lỗi đăng nhập mục 2 — đề xuất N4 qua CLI

`core/stage_cli_proposal.py` dùng client Claude CLI của đúng dự án và ledger tệp; provider khác/client sai/ledger thiếu đều từ chối, không chuyển API. Chỉ dùng K1 đã có, không tự dựng Blender. Ước tính token bằng API canonical, nói rõ chỉ phần đầu vào thấy được, không bịa baseline/model. Bốn vai sân khấu đăng ký policy canonical `other`; giữ cờ cli_call_budget hiện có, không bật cờ. Người dùng xác nhận hạn mức trước khi chạy; JSON hợp lệ chỉ thành bản nháp, không tự ingest, ghi camera hay duyệt EP. N4 vẫn cần xác nhận và validator hiện hành; nhập tay vẫn còn. Pin theo input/phase/state/prompt/metadata ảnh, không cam kết nguyên khối output CLI: người dùng được chỉnh draft rồi validator kiểm. Đầu vào đổi trước generate hoặc trước worker N4 thì giữ draft và từ chối; không tự gọi lại.

Rà quyền phát hiện authON thiếu identity và cached-owner/thu hồi quyền giữa precheck→khóa. RED **6 failed,24 passed/0,71s** → sửa lấy users.active/role mới, kiểm quyền trước provider/ledger và lại dưới khóa S; pinned N4 kiểm connection worker trước ingest. Builder **46 passed/1,06s**. Reviewer đọc fix hai lượt, **0 P1/P2 trong phạm vi đã gom**. Root đọc lại và chạy serial proposal+camera controls+CLI status **76 passed/1,39s** bằng OBJECT env/HOME/DB/provider/process giả. Không gọi CLI/native/Blender/API, không ghi dữ liệu thật; chưa AppTest/ca #34 thật.

`cli_error_code` nhận cả Not logged in và Please run /login thành auth; 3 ca RED trước sửa → module CLI status30 xanh. Luồng giao vai hiện câu đăng nhập/hạn mức/timeout/JSON/ledger rõ, không đưa raw output vào UI. Helper/test đã khai plates3d; giữ areas.version92 và widget N4 cũ.

## Đính chính phạm vi theo thư mới 18:54

- Mục10: thư185416-4j0w yêu cầu giữ s trên mọi link/nút nội bộ; URL mới thiếu s báo rõ phiên không mang theo, đăng nhập lại. KHÔNG cookie/transport/reverse proxy mới; chỉ ghi đề xuất cho EP.
- Mục4: thư185447-cupd chốt chỉ sửa height_m Kho CHUNG qua writer hiện có, giữ mọi trường v1 lạ và quyền cũ. KHÔNG clone dự án/API transaction mới; bản riêng sẽ tách nếu EP cần. Chuẩn bị làm tiếp theo phạm vi này, không còn chờ hai quyết định cũ.
- Toàn task vẫn ĐANG LÀM; mục4/10 và QA tích hợp còn mở. Không phát xong sớm.


## Mục10 — giữ token trên đường điều hướng hiện có, không transport mới

Theo185416-4j0w: giữ auth.identity/revocation/machine_auth và nguồn ưu tiên session hiện hành. require_login chỉ khôi phục query s từ token phiên SAU khi identity và cổng máy đã qua. Các callback go_screen/remember_pid cập nhật từng query key nên vẫn giữ s và tham số khác. Toàn dashboard chưa có href/link_button/page_link/switch_page/linkbuilder ngoài; không bổ sung phát token sang URL bên ngoài. URL/tab mới không mang s và không còn session hiển thị đúng: **Phiên đăng nhập không mang theo, đăng nhập lại.** Không echo URL/token. Không tuyên bố SSO cho tab trắng; trường hợp đó vẫn cần đăng nhập theo quyết định phiên chính.

RED3 failed/8 passed/0,55s → child12xanh/0,62s; root đọc source/caller/fix hai lượt, **0 P1/P2 trong phạm vi**, chạy riêng12xanh/0,61s với AST hàm thật + auth/UI giả, mạng/process bị chặn. Test validlink, session ưu tiên, thiếu phiên, revoke, Ownerremote, machinerefusal, authOFF, logout và callback giữ s. Không GUI/AppTest/browser/account thật; chưa nghiệm thu ca #34. Cookie HttpOnly/transport tự phục hồi URL không token chỉ là đề xuất cần EP duyệt riêng; không code trong task này. Khai test dashboard_ui, version92 giữ nguyên.

Hồi quy thêm mục3: LoadAnswerTests nhập tay cũ **4 passed/2,62s**, CLI budget cờON/OFF/argv/model/image policy **7 passed,26 deselected/1,25s**; toàn bộ dùng fakeenv/process, không cộng thành số test duy nhất với các nhóm đã chạy.


## Mục4 — bổ sung chiều cao Kho chung và bảo toàn hồ sơ

Theo185447-cupd, panel trong bàn đạo diễn dùng đúng shot idx của scene_status và resolver linkedID canonical từ audit. Nhân vật/thú thiếu height có ô số mặc định0 (chưa khai, không đoán) + xác nhận rõ Kho CHUNG ảnh hưởng mọi dự án. Widget mang assetID/hashsnapshot; lưu dùng snapshot lúc vẽ, lỗi/thiếu quyền/malformed/xung đột báo rõ và không ghi. Hồ sơ riêng dự án chỉ báo giới hạn, không clone/link/move asset. Không thay chính sách/cổng thiếu chiều cao hiện hành.

`library_height.save_height` yêu cầu xác nhận, số hữu hạn0,2–30m, đọc users.active/role/perms mới và auth.can assets dưới BEGIN IMMEDIATE; localOFF theo đủ alias canonical. Từ chối pending transaction của caller trước mở transaction riêng. Writer v1 deepcopy giữ mọi unknown/nestedfield, giữ textkeys/approved/history khi chỉ sửa height; optional rawsnapshotCAS trong writer hiện có, stale rollback/release savepoint không mắc write lock hoặc rollback caller. V2 giữ writer actor/revision/audit cũ, không nâng schema v1/migration. Không API transaction/clone mới.

RED đầu writer2failed; helper mới16failed/2passed. Rà gom P2: staleCAS để implicittransaction mở (RED1failed/1passed), helper commit transaction caller (RED1failed), authOFF thiếu alias → sửa savepoint/refusepending/canonicalalias. Thêm actual scenes/refID fixture và mock panel xác nhận→save→rerun, v2 revision/provenance, malformed/scope/knownheight readonly. Builder cuối **34 passed,51 deselected/0,41s**; root chạy31test mới +3hồi quy writer v1/v2/audit rollback **34 passed/0,28s**. Reviewer độc lập đọc fix/core/UI/callers hai lượt **0 P1/P2 trong phạm vi**; root đọc hai lượt. Đăng ký helper/test assets, version92 giữ nguyên. Chưa AppTest/GUI/#34/data thật, không thay kết luận thành nghiệm thu production.


## Chốt AppTest serial sau 22:00 — theo 223827-en7n

Main cho hết giảm tải qua220214-snqu/222504-g99z, tối đa2phiên test nặng. Codex1 giữ một slot bên cạnh lượt tích hợp của main, không tạo slot thứ ba. Root chạy `tests/test_v31_m48_desk_ui.py`: **29 passed/35,06s**. Thêm `tests/test_p34_ui_apptest.py` dùng Streamlit AppTest thật, backend/identity/status/ledger/model giả, không AST: **6 passed/14,22s**, lượt fixture ổn định cuối **6 passed/13,77s**. Không cần chạy lặp lại sau đó.

Sáu ca: height số0+xác nhận KhoCHUNG+snapshot/save/rerun; proposal consent và paid_confirm thật hai bước tạo draft/pin/resetN4, không tự ingest; CLI email/runtime/refreshforce; settingsdenied không resolve/status; review failed banner + EP reason/snapshot; nonEP không skip. Fixture thay OBJECTenv trước imports, fake HOME/TEMP/config, block registry/keyring/native subprocess/model. Socket ứng dụng bị chặn; riêng Windows asyncio self-pipe chỉ cho loopback trong threadlocal lúc socketpair tạo cặp, không mở Streamlit server/browser hay kết nối ngoài. Các lượt lỗi đầu là fixture chặn sai API ask/ask_json và self-pipe, **không phải RED lỗi production**; sau sửa fixture không phát hiện finding production mới. Các RED→GREEN sửa chức năng nằm trong unit từng mục đã ghi riêng.

Root đọc test/source/callers hai lượt, không P1/P2 mới trong phạm vi. Khai AppTest ở step2/dashboard_ui, version92 giữ nguyên. Không ảnh chụp Computer Use, không native CLI/Blender/account/#34 thật, không API tốn tiền/DB thật/migration. G1 chưa main lần kiểm cuối; không cherry-pick nhánh riêng, không rebase/forcepush nhánh đã công bố. Phiên chính tích hợp với G1 sau tin GỘP và kiểm assignedEP; branch P34 code kết thúc tại code3e3917a7 + commit chốt test/báo cáo này. Xóa HANDOFF WIP theo yêu cầu và báo XONG kèm SHA chốt qua helper; tiếp URL-TOKEN-RA rồi N9 theo phân công mới.

## Đồng bộ sau thư GỘP 231006-kphf

Đã nhập `origin/main` ở `5d72cf7d`, gồm G1/M47B/M62/M82B theo lô `49fcccf3`; M64 chưa gộp. Dùng merge giữ lịch sử nhánh đã push, không force/rewrite hoặc nhập nhánh Codex lẻ. Ba xung đột `areas.json` chỉ là danh mục: lấy hợp code/tests/flags hai bên, giữ version92; không mất đăng ký main. `_need_ep`/rank EP dự án từ G1 được giữ nguyên.

Root chạy **163 unit passed/1,89s**, AppTest riêng **6 passed/3,41s**, G1 cấp/thu hồi EP và scope dự án trên DB tạm **4 passed/31 deselected/3,21s**. Lượt đầu gom unit và AppTest gặp 2 lỗi rồi Windows native access violation, không kết luận lỗi production; fixture AppTest đã đổi từ khôi phục toàn bộ sys.modules sang chỉ entry keyring, sau đó chạy riêng xanh. Không nới assertion hoặc mock cổng quyền sản xuất để che lỗi. Reviewer độc lập rà tích hợp tiền/quyền/caller/đăng ký: **0 P1/P2**, root đối chiếu hai lượt. Chưa chạy cả bộ của nhánh tích hợp, GUI/Blender/CLI hay dữ liệu thật; main vẫn thực hiện bước nghiệm thu/gộp cuối.
