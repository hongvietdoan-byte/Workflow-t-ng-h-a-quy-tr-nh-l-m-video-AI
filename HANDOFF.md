# Bàn giao Đ20 việc 2

Tranche capture/validation synthetic xong, **M1.9a OPEN**. Nhánh `codex/d20-viec2-golden`, gốc `c0ab784a`; chi tiết và lệnh #24/#27 COMPAT, #31/#33 CORRECTNESS ở `docs/RA_D20_VIEC2_CODEX_2026-10-20.md`.

17 test xanh sau rà độc lập (2 P2 đã sửa, đỏ 4 failed/13 passed → xanh 17 passed); fixture DB lấy SCHEMA thật bằng AST, không import app; không live data/API. Chưa có current-builder replay hoặc bằng chứng chất lượng thật. Bước kế: cung cấp input trước lắp gói từ snapshot, dùng `core.sent_package.build` với timestamp/external id cố định ở test rồi nối current production builder sau M1.2; byte comparator hiện chưa chứng minh đường đó.

Giữ nguyên areas version. Không push, không sửa TODO/kế hoạch/main. Phiên chính rà độc lập rồi quyết định công bố tranche; không đánh dấu việc 2 hoàn tất toàn bộ.

## Điểm nghỉ hạn mức — 20/10/2026

- Đã push việc 1 `codex/d20-viec1-so-loi` code978cc202 + sửa304c7ff4: 9 test xanh; 2 P2 độc lập đã sửa. CSDL native thiếu USD vẫn UNKNOWN; chưa cả bộ/chạy thật.
- Đã push tranche việc 2 `codex/d20-viec2-golden` code5ad571b9: 17 test xanh; 2 P2 JSON không hữu hạn/URL credential đã sửa. ROOT đã đọc phần sửa. Capture chỉ đọc, chưa current-builder replay/CORRECTNESS, KHÔNG coi M1.9a xong.
- Kế: hoàn tất việc 2 replay ảnh + video từ input snapshot qua builder hiện tại, COMPAT byte-for-byte cờ OFF và CORRECTNESS riêng; rồi việc 3 giá theo package; việc 4 vận hành; việc 5 kho chỉ dry-run; việc 6 khi errors.py/errors.json đã main. Đọc lại đề ĐỢT20 và hộp thư main mới nhất trước mỗi việc.
- Main đã mở runner/bg_poll sau M1.2+M1.3 commit60b9da80; không còn lý do chờ dependency này cho việc5. Không chạm llm_runner/qc_observe/shot_intent (owner khác).
- Cloud-B sổ lỗi198e9de1 chưa thấy main tại lần kiểm a2218f52; việc6 chờ gộp, không chép implementation nhánh cloud.
- Hộp thư C-RA-D19 báo rà419d4da8: D19v2 lỗi CAO pricing null bị từ chối; 4 VỪA clip nhóm ambiguous, M1.4b hold job cũ, M1.5 phạm vi C3-3 và G59 có thể kích hoạt cleanup thật. Phải đọc báo cáo `docs/RA_CLOUD_D19_2026-10-20.md` ở nhánh cloud/v31-ra-d19 trước tái dùng; không nhận trùng owner, gửi nhận qua hộp thư. Chưa sửa các finding này trong lượt này.
- Chỉ commit mục 📨 TODO được push main theo ngoại lệ mới; mọi code vẫn nhánh riêng. Hộp thư worktree `D:/AI-Video-Pipeline/.codex-wt/d20-hop-thu`, nhánhcodex/d20-hop-thu; tránh checkout main live đang chạy. Fetch/pull mailbox trước ghi, không force, kiểm union không lặp.
- Quota mốc nghỉ: 5h ĐÃ DÙNG90%, còn10%; tuần ĐÃ DÙNG14%. Reset5h dự kiến20/10 21:44:29 Asia/Saigon. Không mở child khi ≥90%, không mua/resetcredit/đổi tài khoản, không tự tạo automation.
- Mọi test env: patch.object thay OBJECT os.environ dictgiả trướcimport/call/spawn (khôngpatch.dictclear), mockcredential/provider/model; nativeexplicitwhitelist và Python3.14đãcài; pytest --tb=no khôngshowlocals/dumpenv/đọc khóa thật. Test targeted đã chạy; Windows cả bộ/slow tại tích hợp, chưa gộp main/live/restart.
## Replay bổ sung
- 25 test xanh /9,47s: current ImageRunner/VideoRunner._build_package từ frozen args/kwargs và ref bytes tổng hợp; baseline viết độc lập; provider stub fake/clipai/deepix; COMPAT + correctness cấu trúc tách riêng.
- M1.9a vẫn OPEN: chưa prompt assembly `_submit_args`/snapshot DB sản xuất/quality thật. Root đọc diff, rà độc lập rồi quyết định bước tiếp; không gộp/push/TODO ở nhánh này.
- Chi tiết giới hạn/sidecar/env launcher trong RA_D20_VIEC2. Phiên kế không sinh lại baseline từ code hiện tại để làm xanh.
- Finding tự rà cuối: fingerprint video JSON key string; đã đổi snapshot field đơn và ca video có frozen-fingerprint; xác nhận 25 xanh/9,60s. Rà độc lập `d20_golden_final_review` đang đọc.

## CX20-2b — bàn giao từng phần
Hai VỪA + THẤP đã có 40 test xanh. CAO-M2 actual DB replay vẫn OPEN, không mở khóa M2. Xem docs/RA_D20_VIEC2B_CODEX_2026-10-20.md; dependency đã cherry-pick có chủ ý, không push/main/live. Phần kế cần dependency manifest trước prepare + sandbox deny-read, phân biệt DATA_CHANGED/INSUFFICIENT_INPUT với CODE_MISMATCH; không suy args lịch sử từ package.
