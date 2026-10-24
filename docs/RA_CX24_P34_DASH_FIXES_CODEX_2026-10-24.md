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
