# Bàn giao sau Đ12v6 / phần Đ13v4 — 13/10/2026

## Đã đẩy nhánh riêng
- Đ12v6: `codex/d12-viec6-phat-am`, worktree `D:/AI-Video-Pipeline/.codex-wt/d12-viec6-phat-am`, code `7f497699`, HEAD `50724044`. 90 test xanh /7,80s, 4 PNG edit/view1440/1280; cờ OFF/OPT_IN. Chưa thử giọng70/model thật, cần kiểm tích hợp Đ12v5. RA/HANDOFF cùng đợt trong docs.
- Đ13v4 phần đã làm: `codex/d13-viec4-ton-dong`, worktree cùng tên, code `3752329d`, kết quả `046e59da`. Mục1–5 trừ cost O(n²),7–8,9 độc lập đã làm; nhóm12file357 xanh/1xfail/10subtests, tự rà lifecycle2đỏ→45xanh, rà độc lập2P2→70xanh/7,24s. Hai PNG Chrome component1440/1280 đã xem, 0lỗi/tràn ngang; server8513 đã dừng. Hai cờ mới OFF/OPT_IN. Không coi trọn việc4 hoàn tất.
- Hai nhánh giữ areas.version68 theo base; không tăng version. Chưa cả bộ/gộp/live restart/API/data thật.

## Bước kế sau reset
1. Gọi get_usage_limits; % usedPercent là ĐÃ DÙNG. Lần chốt 5h72% đã dùng/28% còn, tuần62% đã dùng. Reset5h14:05:20 ngày13/10 Asia/Saigon; lịch hiện có dời14:10. Không reset credit/mua credit.
2. Đọc nguồn bắt buộc; fetch origin, đọc HỘP THƯ/Sổ việc/TOP CODEX_TASKS trên origin/main mới. Main lúc đọc cuối `2e37133f`, live #27 vẫn do máy chính. Không pull/đổi nhánh/restart live.
3. Đ13v4 còn cost O(n²): `video_need` quét job nhóm mỗi shot. Nhánh ngân sách `codex/d10-viec3b-project-budget` HEAD84507f59/code27c2e9f3 chưa main ở lần kiểm; tránh chép lại logic final_only/ước tính. Khi dependency đã gộp, tiếp đúng nhánh Đ13 hoặc phần bổ sung chỉ tối ưu collection theo dự án với invalidation đúng; kiểm không lọt dự án khác. Mục6 regex thoại trong seedance_refs vẫn chờ máy chính đang sửa; chỉ làm khi hộp thư mới xác nhận có thể nhận. Không tự sửa runner group.
4. Nếu phần còn Đ13 đang thuộc phiên khác/chưa dependency, sang Đ11v2: camera clay/fallback2D; tấm duyệt2–3góc clay từ add_props/whitebox cùng topview (tru/cot đang vẽ vuông); director_blockout sau cờOFF, giữ promptOFF byte-exact, ledger/ước tính/retry≤2; fake3bối cảnh và QA/render0USD dữ liệu tạm. Đây việc lớn, không mở khi đã70–90% theo quy tắc chỉ việc nhỏ.
5. Sau đó Đ11v4 (không nhân đôi continuity_layout), Đ12v2–4, Đ13v1–3, Đ11v5, Đ11v3 sau duyệt thiết kế; áp bảng ưu tiên main mới nếu thay đổi.

## Giữ những phần đã hoàn thành / đang chờ
Không làm lại Đ18v1d52253e6/v2HEAD6e80e98e/v3HEAD80dfcf6a; Đ15v3HEAD37bfd9f0; Đ12v5HEAD157084cf; Đ14v3HEAD18a66c64; project_budgetHEAD84507f59. Đ11v1bHEADb7a73d73 chỉ20mục đánh giá, câu hỏi chốtmockup9c chưa trả lời: không sửaHTML. Đ18v4 chưa duyệt kế hoạch: không tự build. Cloud locomotion/ambient/xdist đã main1ab50785, không làm lại. Pet GUI Windows thật thuộc máy chính, component/mock không thay nghiệm thu toast/DPI/2màn hình/sleep-resume.

## Giới hạn / an toàn
- Đ13 scan vẫn size+mtimegiây: cùng size/cùnggiây có thể bỏ sót thay đổi. Không tự migration/hash.
- Một traceback test đỏ đã hiển thị giá trị khóa môi trường; root đã báo người dùng thay CLIPAI_TOKEN/khóa Meshy. Không sao chép giá trị/log vào tài liệu, không đọc lại khóa để xác minh, không tự sửa env. Fixture HKCU hiện thay os.environ bằng dict giả, chỉ fake registry; tránh assertion khiến pytest tự in repr môi trường thật.
- Mỗi việc nhánh/worktree từ origin/main, tiếp nhánh dở đúng tên; test đỏ→xanh nhóm liên quan, không nới, rà kỹ độc lập dữ liệu/quyền/tiền, caller/related_areas. Giữ widgetkeys/version, register code/tests/flags, ghi RA/Kết quả, commit tiếng Việt trailerCodex, push nhánh. Không main/live/data thật/API/env/secrets/admin_auth/maintenanceworker. Nhóm runner sau#24 vẫn chờ người dùng/phiên máy chính chốt.
- Ngưỡng: ≥60%mộtchild,70–90%chỉviệcnhỏ,≥80%thu nhỏ,≥90%lưu/push/nghỉ. Dời đúng automation hiện có sau reset tự nhiên, không tạo trùng/monitorquota định kỳ; xóa lịch khi mọi việc được phép đã xong.
