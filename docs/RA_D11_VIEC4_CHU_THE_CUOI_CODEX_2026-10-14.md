# Rà Đ11v4 — chủ thể/trạng thái cuối (14/10/2026)
- Nhánh `codex/d11-viec4-chu-the-cuoi`, nền `347ab560`; chưa commit/gộp.
- Phạm vi: QC ảnh/clip local và caller Dashboard, 0 USD; cờ OFF giữ nguyên.
- QC luôn báo VÀNG chưa xác minh danh tính: detector một mặt không chứng minh đúng ID.
- Thiếu actor/ID có cảnh báo rõ; clip cuối không dùng actor đầu thay thế.
- Actor đầu/cuối có ID khác nhau: không đem cỡ/mắt của hai người khác nhau so; chân trời vẫn độc lập.
- Caller giữ số hình học khi tên/metadata phù hợp, ghi chưa xác minh ID; truyền end_actor=None rõ ràng.
- Chưa có `approved_camera_plan`/schema snapshot ID và trạng thái cuối trong main; adapter CHỜ nguồn A. Không định nghĩa schema cạnh tranh.
- ĐỎ: 4 failed/11 passed (ID chưa xác minh, thiếu trạng thái cuối, ID khác, caller chưa cảnh báo).
- XANH cuối: 74 passed/2,72 s, 7 file camera_match_qc/ui, film_grammar, continuity/layout, before_run, plate_layout_qc.
- Test UI đổi ý định theo root: giữ geometry name-only nhưng bắt buộc warning ID; không đổi test để giấu lỗi.
- Pytest thay OBJECT os.environ bằng dict giả trước import; detector/VideoCapture/DB/cost/model giả. `--tb=no`, không API/mạng/credential thật.
- Ca cuối explicit cùng ID giữ số, vẫn chưa xác minh nhận dạng; ca OFF không đọc detector/DB.
- Tự rà 2b.5: không chặn batch/autopilot, không sinh job/đổi prompt/gen, không đường dẫn dữ liệu mới, không cờ mặc định đổi.
- Caller ảnh: storyboard_cards.py:234, step2.py:419; clip: step4.py:729, cùng render sau cờ.
- related_areas: plates3d; dùng cờ chung assets/knowledge/step1/step2; không bắt buộc test chậm.
- Chưa full suite/clip thật, chưa bật cờ; QA component thật 1440/1280 do root chạy, chờ ảnh cuối sau vòng sửa; root rà độc lập trước commit/gộp.
- Keys/areas.version75 giữ; không file mã/cờ mới cần khai.

## Vòng sửa sau rà độc lập
- P2 core: actor str/list/int làm `.get` lỗi → cảnh báo trạng thái thiếu/không hợp lệ; projected horizon giữ riêng khi geometry actor lỗi. Không thêm schema snapshot/registry.
- P2 diagnostics: số khớp chỉ còn warning identity → gắn measured/expected vào mọi issue, kể cả warning ID; giữ số đo cho UI.
- QA root thấy 7 warning cards lặp: gộp mọi thông báo vào một warning có bullet lines; identity và trạng thái thiếu chung một issue/frame với code `subject_identity_unverified`. Note camera_plan name-only là caption khi core đã báo code; không lọc bằng chuỗi, không bỏ warning.
- ĐỎ thật: 5 failed/16 passed (3 malformed actor + matching diagnostics + UI group/diagnostics).
- XANH tập trung: 87 passed/8,00 s; camera_match_qc/ui, plate_camera_p24_angles, camera_plan_g0, plate_layout_qc. Môi trường dict giả trước import/call, detector/capture/DB/giá giả; --tb=no.
- Test cũ về cuối thiếu actor lọc riêng issue geometry theo code: vẫn bắt đủ 2 lỗi mắt/cỡ mặt và không lệch chân trời; identity nay cũng có diagnostics nên không đếm lẫn.
- QA PNG cuối 1440/1280 và root đọc diff vòng 2: CHỜ root, không tuyên bố nghiệm thu GUI cuối.
# Root nghiệm thu cuối
Root đọc fixdiff và xem PNG1280: warning gộp một card, giữ số đo/dự kiến kể cả matched geometry. QA actualcomponent với SQLite/đo/cost giả1440/1280,0pageerror/overflow; server riêng đã stop và fixture tạm exactfile đã xóa. Chưa clip thật/cả bộ/main/live; adapterID/endstate vẫn chờ nguồnA, không tự tạo schema.
