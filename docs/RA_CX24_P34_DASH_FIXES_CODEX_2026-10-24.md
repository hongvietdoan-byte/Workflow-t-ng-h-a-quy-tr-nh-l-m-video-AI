# CX24-P34-DASH-FIXES — checkpoint Codex 1 (24/10/2026)

**ĐANG LÀM, chưa XONG toàn task.** Nhánh `codex/v31-p34-dash-fixes`, worktree cùng tên dưới `.codex-wt`, nền `origin/main` a700ead8. Nhận `20261024-175930-codex-9fnb.json`, báo phạm vi `20261024-180037-codex-g8re.json`. Không tự gộp/restart live.

## Đã làm trong checkpoint

### Mục6 — audit dùng đúng hồ sơ nhân vật đã liên kết

`core/change_audit.py` đọc characters đúng project và tên Unicode, ưu tiên ref_asset_id đã lưu; kiểm must_keep trên đúng profile dù tên asset khác và chưa có ảnh. ID0/brokenID/sai loại/asset thuộc project khác/duplicatecharacters báo VÀNG rõ, không fallback âm thầm. Chỉ NULL/DB legacy mới dò tên, ưu tiên project_assets rồi toàn Kho khớp duy nhất (có dấu/alias trước, fold chỉ khi duy nhất). Không đổi liên kết/profile hoặc ghi DB. Profile JSON/schema lỗi báo VÀNG. Giữ narrator không làm nhân vật Kho.

RED thực tế **13 failed,6 passed/1,16s** → GREEN **19 passed/0,56s**, gồm ba test_change_audit cũ. Reviewer độc lập rà ID/scope/alias/callers/không ghi DB: **0 P1/P2 trong diff mới**. Lưu ý tồn tại từ trước: audit_shot nhận scene_id và các caller đã rà truyền đúng pid; chưa đổi hợp đồng scene query ngoài phạm vi định danh.

### Mục11 — nhãn ảnh hiển thị model mà runner chọn

Helper thuần `dashboard/image_model_label.py`; hai layout Step2 dùng cùng nhãn. Provider hỗ trợ model= dùng image_models.of_project(proj), đúng thứ tự project→DEEPIX_MODEL→DEFAULT của ImageRunner; provider cố định dùng model của adapter; thiếu metadata nói chưa xác định. Không khởi tạo provider/call mạng, không đổi kwargs gen/widget keys/chi phí.

RED **1 error collection/0,56s** trước helper → GREEN **9 passed/0,31s**; hai project khác model, provider cố định, metadata thiếu, fallback/env giả, mock và AST wiring. Reviewer độc lập **0 P1/P2** trong helper/diff/callers.

Root đọc hai phần sửa, chạy nhóm unit serial nhẹ bằng OBJECT os.environ giả, HOME/TEMP giả, keyring giả và winreg.OpenKey bị mock trước pytest/import/call: **28 passed/0,77s** (hai test mới + test_change_audit, số ca chồng nhóm child, không cộng trùng). `--tb=no`, không plugin tự nạp/xdist/server. areas.version92, khai helper/tests ở step2 và plates3d.

## Còn phải làm trước báo XONG

| Mục | Bước tiếp |
|---|---|
|1|UI không nói “không mục lệch” khi change_events failed/code_only quota. Tạo mục đỏ ngay cả chưa gọi blocking, idempotent, giữ cổng; Rà lại có dự toán/xác nhận, Bỏ qua chỉ EP + lý do/audit + chống bỏ qua lỗi mới chưa xem. Dùng API quyền canonical sau dependency G1, không tạo vai EP thứ hai.|
|2|Trạng thái/email tài khoản Claude CLI của pipeline, cache ngắn, clean_env dùng chung, fakebinary tests, thông điệp đăng nhập lỗi; không chạy claude auth thật trong QA. Đối chiếu dependency CLI-TOKENS trước refactor env.|
|3|Nút giao vai Claude tại N4 gọi llm_runner đúng dự án/stage rồi validate/load_answer; giữ dán tay, quyền và xác nhận. API thật/phí chỉ theo dự toán và EP, QA provider giả.|
|4|Chỗ sửa height_m trên Dashboard có xác nhận, quyền sửa Kho, actor/revision/CAS. Kiểm core.kho_profile.save(conn,asset_id,changes,actor,expected_revision,reason=...) và tương thích schema1 trước dùng, không backfill/migration thật.|
|7|Chọn phía máy theo trục và ép ngưỡng vật phụ qua stage_solver; giữ m/world axes và geometry nguồn A, unit hình học fake, không mở Blender.|
|10|Giữ đăng nhập khi đổi URL. header.require_login hiện dùng session_state/token s trong query, chưa thấy cookie helper; ưu tiên dùng cơ chế có sẵn, không nạp token vào log/test thật, kiểm logout/revocation/Owner khác máy. Chưa đổi luồng auth.|
|8/9|Chỉ thiết kế trong báo cáo (nháp bên dưới), không tự triển khai.|

G1-EP-ROLE6d647212 và CLI-TOKENS296fc658 **chưa là ancestor HEAD a700ead8** lúc tạo task (merge-base exit1 riêng từng dependency); không chép lại API của nhánh khác. Đã hỏi phiên chính qua `20261024-180630-codex-j3np.json` về nhánh tích hợp và lượt AppTest nặng; kiểm thư mới trước sửa các mục phụ thuộc. Không coi chưa trả lời là duyệt, vẫn có thể chuẩn bị unit/callback nhẹ độc lập.

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
