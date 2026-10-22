# CX22-FLAG20 — đo trên Windows, chưa kết luận hoàn tất

- Nhánh `codex/v31-flag20`, nền `85f08963` (origin/main lúc bắt đầu). Không sửa code production, không bật cờ hay đọc dữ liệu live, 0 USD.
- 20 tên lấy bằng AST diff `9998b46b^..9998b46b`; không merge nhánh cũ. `music_story_arc` hiện đã verified True nên phép bật riêng không đổi nó.
- Không tìm thấy danh sách 362 node lịch sử trong repo; dùng cohort 158 node K8 tại `docs/flagmatrix/k8_failed_2026-10-21.txt`, cộng cohort 68 ca contract/backend.
- Raw log/kết quả/helper chỉ ở `D:/AI-Video-Output/flag20-20261022/` ngoài Git. Native Python 3.14, môi trường whitelist giả; thay OBJECT os.environ trước import pytest/project; không nạp dashboard.env/credentials. Audit chặn mọi mạng ngoài; chỉ loopback IPC cho asyncio, cấm cổng live8501/8502; production paths bị cấm.
- Mốc K8 đầu: 108 passed /37 failed /13 skipped,309.44s. 36 đỏ UI là lỗi harness chặn socketpair Windows; đã sửa harness ngoài repo và đang đo lại đúng36 UI, không sửa assertion/core. Lipsync1 đỏ ở baseline giữ riêng.
- Cohort contract68: baseline68pass29.54s; all2014fail54pass38.36s. Đây không phải cả bộ.
- Đang chạy: all20 K8 và baseline UI corrected. Tiếp: all20 UI corrected, delta failed rồi attribution từng cờ trên node ứng viên. Không suy0của sample thành0toàn bộ.
- Task chỉ đo/doc; chưa có vòng sửa production ĐỎ→XANH. Chưa XONG, chưa fullsuite từng cờ. Không push/main/TODO/live restart.
