# C-3D-GOC-B: khâu 3D, sửa gốc R1 (vị trí xuyên shot lấy từ MỘT bản đồ cảnh) — cloud-claude, 22/10/2026

Người dùng 22/10 yêu cầu:
- sửa GỐC, để đặt chỗ khác hay làm cách khác cũng không lặp lại lỗi;
- giữ mối liên kết chặt chẽ;
- "có làm luôn đi", tức phiên cloud nhận gói này. Phiên chính đã được báo qua hộp thư lúc 11:05.

Phạm vi: 0 USD, không thêm cờ. Gói chỉ báo: không chặn gen, không sửa prompt, không đổi gói gửi đi.

Nhánh `cloud/v31-3d-goc-b` được dựng trên `cloud/v31-3d-goc-a` @ 3903a62e, cộng `cloud/v31-qc-bocuc` và `cloud/v31-crew-hoso`, đã merge `main`. Các nhánh ghép vào không xung đột.

## 1. Gốc và cách sửa
Sổ lỗi `V31-GOC1` ← `P31-G46` ← G41, G43, G44, G45, G47, G50 và G1.

Gốc: vị trí người/vật xuyên các shot chỉ được tả bằng chữ riêng từng shot. Mỗi ảnh gen độc lập nên model đặt lại vị trí mỗi lần, và vá chữ shot này thì lệch shot kia.

Cách sửa: **chỉ có một nguồn vị trí là bản đồ cảnh `core/world_map`** (M3.1, D06). Cả ba nơi đều đọc cùng map đó, cùng một phép chiếu `world_map.frame_xy` và cùng ngưỡng trục `layout_facts.SAME_VIEW_YAW_DEG`:
- câu vị trí M3.3;
- `core/layout_facts.positions` (nguồn bố cục chung với QC và gói A);
- 5 bất biến trong `core/position_invariants.py`.

| Bất biến | Bắt lỗi | Mức |
|---|---|---|
| R1-MAP | cảnh ≥ 2 shot mà chưa có map còn hiệu lực, map UNKNOWN hoặc map hỏng | KHÔNG RÕ + lý do |
| R1-SIDE | chữ (image_prompt / blocking / action / motion) nói trái/phải ngược chỗ map đặt theo máy của shot (G44); câu thay sinh từ map | VÀNG |
| R1-AXIS-JUMP | cùng vật đổi bên giữa hai shot liền nhau trong khi hai máy cùng phía trục (G44 26↔27). Máy ngược trục thì đổi bên là đúng | VÀNG |
| R1-TRAVEL | theo từng câu: hướng đi (vào nền / về phía máy / ra khung trái-phải) đối chiếu vị trí trên map của thứ được nhắc "đi về phía" / "rời khỏi" (G41, G43). Người đi lấy theo tên trong câu; "nhìn / ngắm về phía" không tính là đi | VÀNG; thiếu toạ độ → KHÔNG RÕ |
| R1-PROP-SCENE | khối giữ chỗ mang từ cảnh N khác vào, mà map / BYĐ / nhân vật của cảnh này không có vật đó (G1: xác bay cảnh 6 ở cảnh 8). Vật cố định cùng sân khấu có ở cảnh này (stage_auto cố ý mang sang) thì không báo | VÀNG; không có map/BYĐ → KHÔNG RÕ |

`layout_facts.positions` lấy toạ độ mặt sàn theo shot từ map. Lưu ý **số shot của map là `scenes.idx`** (theo shot_specs `shot` của stage_auto), không phải `shot_no` trong cảnh. Map cũ, tương đối hoặc hỏng thì trả `{}` và ghi lý do vào `missing`.

`world_map` được tách thành hai phần thuần, không đổi hành vi (test dp8/dp11/stage_view vẫn xanh):
- `frame_xy`: phép chiếu dùng chung, tách ra từ `_place`;
- `side_review`: lõi của `review`, không đọc cờ; `review` vẫn chịu cờ như cũ.

## 2. Test biến thể (`tests/test_v31_3d_goc_b.py`, 131 ca cùng dp8)
- Cả cảnh (máy + vật) được xoay và tịnh tiến theo 24 seed ngẫu nhiên. R1-SIDE, R1-AXIS-JUMP và R1-TRAVEL cho cùng kết luận ở mọi chỗ đặt máy, gồm cả máy ngược trục 180°.
- Ca gốc #31 dựng lại bằng số trong `docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md`: G43 ("rời khỏi cái xác" mà xác ở nền), G41 (chạy sai phía), G44 (nhảy trục), G1 (khối cảnh 6 ở cảnh 8).
- Các ca không được đoán: thiếu máy, thiếu toạ độ, tên mơ hồ, map hỏng, cờ `stage_camera` tắt.
- `tools/position_invariants.py` đọc bản sao CSDL; CSDL thật không đổi (test kiểm mtime và size).

## 3. Rà quy ước 7 (Agent) và cách đã xử lý
- **CAO, đã sửa:** số shot lệch. Map dùng `scenes.idx`, code cũ đọc theo `shot_no`, nên mọi cảnh trừ cảnh 1 bị im lặng. Test `test_map_shot_numbers_are_project_idx_not_shot_no`. (`dashboard/stage_view_ui.py:175` dùng `shot_no or idx` — lỗi có sẵn từ trước, **phiên chính sửa khi gộp**.)
- **CAO, đã sửa:** test `test_nothing_in_the_gen_path_reads_the_map` bị đỏ. Đã thêm `layout_facts` và `position_invariants` vào danh sách module chỉ đọc. Lý do: chúng đọc để báo, không đưa vào gói gửi hay mệnh đề QC, và test vẫn cấm ghi/dựng map.
- **VỪA, đã sửa:**
  - map hỏng → ghi lý do, không làm sập `compile_frame`;
  - R1-TRAVEL báo nhầm với câu "nhìn / ngắm về phía" → nay bắt buộc có động từ di chuyển, xét theo từng câu, người đi theo tên trong câu;
  - khớp tên mơ hồ → không chọn;
  - R1-PROP-SCENE báo nhầm vật cố định cùng sân khấu → nay chỉ báo khi vật không có ở cảnh này.
- **VỪA, đã sửa:** ánh xạ KPI hồ sơ vai. `ti_le_dung_ho_so_kho` và `may_hop_le` trở lại `chua_co:` với lý do cụ thể, vì `check_framing` và `check_floor` chỉ đo được một phần. `chu_khop_khung_dau` trỏ `text_vs_view`, `byd_khong_mau_thuan` trỏ `byd_vs_fields`, `vi_tri_mot_nguon` trỏ `position_invariants.scene_report`. `py -m core.crew hoso` còn 6 mục thiếu.
- **THẤP, ghi lại:** map 2D có `origin` None nên SIDE / TRAVEL / AXIS không chạy được với map 2D (báo KHÔNG RÕ khi cần).

## 4. Chưa xong (máy chính)
1. Dựng map thật cho #31 bằng `core.world_map.refresh` (cờ world_map, 0 USD), rồi chạy `PYTHONUTF8=1 py tools/position_invariants.py --project 31`. Số phát hiện trên G41–G50 là bằng chứng chạy thật. Có bằng chứng đó mới chuyển sổ lỗi sang FIXED_UNVERIFIED / VERIFIED.
2. Nối R1 vào đường làm việc (bàn đạo diễn / pregen_check / Tổ rà soát) là bước sau. Bước này cần người dùng duyệt, vì sẽ đổi điều người dùng thấy trước khi gen.
3. R5 (một vật trong Kho có nhiều dạng): `docs/THIET_KE_R5_KHO_NHIEU_DANG_2026-10-22.md`, chờ CX21-M23 gộp và người dùng duyệt mở rộng `forms[]` cho vật.
4. Rà gói A khi gộp: nhánh A không ghi vào `layout_facts` (dùng `camera_invariants` riêng). Gói B đã nối KPI hồ sơ vai sang các hàm của A. Việc đưa số đo người của A vào `layout_facts.people` vẫn mở.

## 5. Cả bộ test Linux (sau khi sửa lỗi rà)
32 hỏng / 7367 qua. Trong đó 31 hỏng trùng danh sách nền của main. Hỏng thứ 32 là `test_two_real_processes_poll_one_job_once`, test chập chờn đã ghi nhận từ C-QC-BOCUC (hai tiến trình poll, nhạy thời gian; chạy riêng thì qua).
