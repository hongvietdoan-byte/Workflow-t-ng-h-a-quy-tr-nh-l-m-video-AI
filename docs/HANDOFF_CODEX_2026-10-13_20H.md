# Bàn giao lượt 19:15 ngày 13/10/2026

## Đã push nhánh riêng, không làm lại

- Đ11v1b mockup: codex/d11-viec1b-mockup HEAD87ed86f7, codef962f0f9 +sửa e74d8233. 3 test/50s, 16 tổ hợp kéo, 4PNG, 5P2 sửa; 18 mục bản gọn, #12/#20 để sau. Registry một nguồn, viewer/camera/sampler/diff/approved. Đo5/5 thao tác, không chứng minh giảm bấm. Chưa backend/render/ca thật.
- Đ13v4 cost nhóm: codex/d13-viec4-cost-nhom HEADbd0a2306, codea4a9dc83. 133 test+6subtests52,18s; rà tiền SAVEPOINT3đỏ→sửa,28test3,88s. 99shot/20nhóm→1query/20parse/99members ngoài transaction; trong transaction đọc mới ưu tiên đúng tiền. Không viết lại budget đã main6e987e82.
- Đ12v4: codex/d12-viec4-kho-am-thanh HEADd8d39642, codef7a6ab10 +bba75ff5. 34test0,31s, JSON/CSV offline chặnURL/UNC, tài liệu license/nhu cầu. AST có7mood; top-k thiếu không phải score0. Không đo Kho/thử thật/tảiâm/model.
- Đ13v3: codex/d13-viec3-mockup-pet, codeca5bd2ba +root chuẩn hóa số; 7test5,45s, browser1440/1280, gen trùng và pet thường. Xem RA/HANDOFF riêng.

## Bước kế

Fetch origin, đọc HỘP THƯ/Sổ việc TODO và bảng ưu tiên CODEX_TASKS mới; không theo thứ tự cũ nếu đã đổi.
Đ18 A đã duyệt với registry stage/segment/state DUY NHẤT cho editor3D/Camera; v4 chỉ sau các nhánh Đ18v1–3 được gộp (chưa main lần cuối). Mockup9c đã mở và xong bản gọn, không hỏi lại duyệt18mục.
Đ11v2/v4 đã main theo mail15:47; phần v4 còn lưu blocking đã duyệt, objects theo beat, subject.id/end_actor, GUI/ca thật. Khi nối phải dùng nguồn A, không tạo registry cạnh tranh. Tới lượt sau ưu tiên việc này nếu dependency đủ; nếu chưa tiếp Đ12v2–3 rồi Đ13v1–2/Đ11v5 theo bảng.
Đ13v4 phần cũ HEAD496e6805/code3752329d vẫn đã push, không làm lại; seedance_refs chỉ sau hộp thư giải phóng rõ. Đ12v6 HEAD50724044/code7f497699 và các nhánh Đ18v1–3/Đ15v3/Đ12v5/Đ14v3 đã push, kiểm đã gộp/cherry-pick trước sửa.
Mail19:11 Claude máy chính giữ lỗi10 khâu dựng Bước5 và chuẩn bị tập2 #27; lỗi1/8/11 đã main, cả bộ5028qua6skip, không nhận lại. Không API tốn tiền/data thật/dashboard.env/secrets/admin_auth.py/maintenanceworker/runner sau#24 chưa chốt. Không gộp main/pull/checkout/restart live D:/AI-Video-Pipeline.

## Quy trình và phòng rò khóa

Mỗi việc nhánh/worktree riêng; đỏ→xanh nhóm liên quan, rà độc lập tiền/dữ liệu/quyền và callerCLAUDE7; widget keys giữ nguyên, areas.version giữ bản nền (hiện72), register code/tests/flags. RA/Kết quảCodex/commit tiếngViệt trailerCodex/pushnhánh; cả bộ Windows -n8 thuộc bên gộp.
Đưa vào mọi prompt con/rà: os.environ dict giả trước imports/calls/spawn, mock registry/credential/provider/model trước gọi; teardown thiếu/có. Không in/assert/repr env headers token credential payloadbí mật; khôngđọckhóathật, no showlocals; pytest --tb=no, chẩn đoán fixture cách ly/lỗi đã lọc. QA chỉDB/asset/ảnh/flags/knowledge giả; nativepet chỉ computer-usekhảdụng, không shellfakeUI.
Đầu lượt get_usage_limits, phân biệtĐÃDÙNG/còn;≥60%mộtchild,70–90%chỉviệcnhỏ,≥80%thunhỏ,≥90%lưu/push/nghỉ. Khôngresetcredit/muacredit. Dời cùnglịch sau reset tự nhiên, không tạo trùng/monitorđịnhkỳ; xóa khi mọi việc được phép xong.
