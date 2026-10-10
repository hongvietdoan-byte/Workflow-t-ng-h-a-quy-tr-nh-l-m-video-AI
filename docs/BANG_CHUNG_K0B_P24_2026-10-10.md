# Bằng chứng chạy khô K0b phần 1 — dự án #24 (10/10/2026)

Kế hoạch: `docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md` (A14, A18, A20, mục 3.1, dòng K0b). **0 USD** — không gọi Claude / model ảnh /
video. Bản chính `D:/AI-Video-Pipeline` CHỈ ĐỌC (CSDL `mode=ro`); #24 không đổi, chưa nối pipeline.

Tái chạy: `PYTHONUTF8=1 py tools/dryrun_k0b_p24.py` → `data_out/k0b_p24/byd_shot{1..9}.json` + `summary.json`.
Mã mới: `core/identity_declare.py` (A18/A20 bằng chữ, hàm thuần), `tests/test_identity_declare.py`, 3 ca hồi quy có BYĐ + gói.

## 1. Bảng mỗi shot

Khóa nhận diện: Kelly theo `assets.profile.must_keep` (#23); **yêu nữ #418 / #419 CHƯA có `must_keep` (profile rỗng)** → tạm suy từ mô tả
Kho tiếng Việt. Mọi món là `suy` (chưa có ô `khai_bao_chu`). Chỉ kiểm nhân vật có trong khung theo BYĐ; chữ của mỗi nhân vật = đoạn prompt
nói về nó (`identity_declare.segment` — tránh tính tóc đen của "bóng đen" shot 3 cho Kelly).

| Shot | BYĐ hợp lệ | Ô suy từ chữ (tư thế) | Khóa nhận diện (có / thiếu / sai màu) | Hình học: sự thật · câu trái | YuNet mặt (ảnh) |
|---|---|---|---|---|---|
| 1 | ✅ | Kelly `dung` ('stand') ✓ | Kelly 3/2/0 — thiếu crop top, sneakers | giếng thấy miệng, giữa · 0 | 623: 0 |
| 2 | ✅ | Kelly `dung` ('lean') ✓ | Kelly 0/5/0 — prompt không tả trang phục | chân trời **một phần ba trên** (máy cúi) · 0 | 624: 1 · 632: 1 |
| 3 | ✅ | Kelly `dung` ✓ | Kelly 0/5/0 | chân trời một phần ba trên · 0 | 625: 0 · 634: 0 |
| 4 | ✅ | Kelly `ngoi` + mông + bàn tay ('fallen back') ✓ | Kelly 3/2/0 | **miệng giếng KHÔNG thấy** (máy 0,6 m < miệng 0,9 m), khối thay thế · 0 (prompt mới) | 626: 0 · 635: 0 · 639: 1 |
| 4 cũ | — | — | Kelly 3/2/0 | **1 câu ĐỎ: 'mouth facing us'** | — |
| 5 | ✅ | không suy được | yêu nữ D1 9/0/0 | miệng không thấy · 0 | 627: 0 · 636: 0 |
| 6 | ✅ | yêu nữ `dung` ✗ (đúng: bò) | yêu nữ D1 9/0/0 | chân trời một phần ba trên · 0 | 628: 0 · 637: 0 |
| 7 | ✅ | yêu nữ `dung` ✓ | D1 2/7/0 · D2 0/6/0 (đang biến hình, tả gộp) | · 0 | 629: 0 |
| 8 | ✅ | yêu nữ `dung` ✗ (đúng: quỳ) | D2 4/2/0 — thiếu váy, chân | giếng thấy miệng, **khối thay thế** · 0 | 630/638/640: 0 |
| 9 | ✅ | yêu nữ `quy` ✓ · Kelly `quy` ✗ (đúng: ngồi) | Kelly 0/5/0 · D2 3/3/0 | chân trời một phần ba trên · 0 | 631: 0 · 633: 0 |

Số chính:
- **BYĐ 9/9 hợp lệ** (validate có CSDL, mã Kho #263 có thật). 15 ô suy từ chữ; tư thế suy sai **3/10** (S6, S8, S9-Kelly) — suy bằng từ
  khóa trên cả đoạn chữ không biết câu nào của ai → K1a phải để Đạo diễn ĐIỀN `hanh_dong`, không suy. Enum `TU_THE` không có "ngã / ngả
  thân" — ngã ngửa chỉ diễn đạt gần đúng bằng `ngoi` + chạm đất mông + bàn tay (job 635 ngồi thẳng cũng khớp enum này → cần thêm độ ngả thân).
- **Khóa nhận diện A18: 7/9 shot sẽ ĐỎ**; 11 lượt nhân vật × món: 33 có / **37 thiếu** / 0 thiếu màu / 0 sai màu. Kelly thiếu crop top +
  sneakers ở mọi shot (món trong must_keep nhưng prompt không nhắc); shot 2, 3, 9 không tả trang phục Kelly. **Chưa rõ prompt GỬI THẬT**:
  bảng `jobs` không lưu prompt đã gửi (chỉ `sent_refs`) → không chạy được trên "prompt đã gửi"; nếu bước gửi chèn khóa Kho thì số đỏ thật thấp hơn.
  Cảnh báo cho K1a: luật "mọi món must_keep phải có chữ" quá chặt với món ngoài khung (giày ở cỡ cận, lưng) → cần BYĐ cỡ cảnh / `thay` lọc món.
- **Hình học**: 9/9 có sự thật; prompt hiện tại 0 câu trái; prompt cũ shot 4 bắt đúng 1 câu ĐỎ.
- **YuNet**: 3 mặt / 18 ảnh (shot 2 Kelly nghiêng ×2, job 639). Mặt yêu nữ là mặt nạ đen trơn, Kelly quay lưng (3, 4) → YuNet KHÔNG dùng
  để đếm người ở dự án này. Render nền đã gửi (`plate.png` / `plate_lift.png`, 18 tệp): 0 mặt (đúng — render không có người).
- **MediaPipe Pose: KHÔNG đo được** — mediapipe 1.0.1 không còn `mp.solutions`, máy chỉ có `face_landmarker.task`, không có
  `pose_landmarker*.task`. Không tải (theo đề bài) → cần người dùng duyệt tải model (≈ 5–30 MB).

## 2. Lỗi người dùng đã bắt ở #24 → phép kiểm nào bắt được

| Lỗi | Bắt trước tiền (chữ / sân khấu) | Bắt sau gen (ảnh) | Kết luận |
|---|---|---|---|
| Lòng giếng thấy ở shot 4 | **code** `stage_facts`: sự thật `top_visible=false` + câu 'mouth facing us' ĐỎ (prompt cũ) | Claude khai `inside_visible` → `judge` ĐỎ (chưa chạy thật) | BẮT ĐƯỢC trước tiền (code) |
| Giếng thành khối shot 8 | code chỉ PHÒNG NGỪA (sự thật `stand_in` → câu dặn); chữ không sai nên 0 câu bắt (ca chống báo nhầm đúng) | Claude khai `flat_plain_block` → ĐỎ (chưa chạy); code chưa đo | Chỉ phòng ngừa + Claude |
| Tư thế ngã shot 4 (job 635 ngồi) | BYĐ ghi được gần đúng; enum thiếu độ ngả | Pose: **không có công cụ**; YuNet 0 mặt cả 635 và 639 | CHƯA bắt |
| Tháp 'nền mẫu' 2/3/8/9 (job 623–631) | không có sự thật nền / mốc trong `stage_facts` | so ảnh ↔ render: chưa có (plate_layout_qc báo lệch 9/9 kể cả ảnh đúng → không tin) | CHƯA bắt |
| Nghiêng máy mất 2/6/9 | code: sự thật `pitch_horizon` = **một phần ba trên đúng ở 2, 3, 6, 9** → câu dặn có | đo chân trời trên ảnh đêm sương: chưa tin cậy | Phòng ngừa có, phát hiện CHƯA |
| Trăng luôn góc trái | không có sự thật nguồn sáng / trăng | — | CHƯA bắt |
| Máu / tóc từ ảnh mẫu Kho | gói ghi được ảnh Kho đã gửi (giếng `1.png` → `2.png` từ job 623) nhưng không có kiểm nội dung ảnh mẫu | — | CHƯA bắt (cần kiểm ảnh mẫu Kho trước khi gửi) |
| Màu giếng không ăn khớp | không có màu vật trong BYĐ / Kho | `palette` chỉ so trang phục | CHƯA bắt |
| Trang phục (A18, bằng chữ) | **code** `identity_declare`: 37 món thiếu / 7 shot ĐỎ | QC họa tiết (A20) chưa có | Bắt được ở chữ; ảnh: QC rà 10/10 thấy trang phục ĐÚNG → nhiều mục đỏ chữ là báo thừa nếu bước gửi đã chèn khóa |

Tổng: 9 loại lỗi → **2 bắt được bằng code trước tiền** (lòng giếng, khóa trang phục bằng chữ), 2 chỉ phòng ngừa (khối, nghiêng máy), **5 chưa
bắt** (tư thế, nền mẫu, trăng, ảnh mẫu bẩn, màu giếng).

## 3. Ca hồi quy thêm (`tests/golden/cases/`, có BYĐ + gói refs/model + ảnh kết quả)

- `p24_shot4_mouth_old_byd` — prompt cũ shot 4, kỳ vọng `stage_facts` (câu ĐỎ) + `identity_declare` (Kelly), gói job 626.
- `p24_shot8_block_byd` — khối shot 8 (chống báo nhầm câu), gói job 630.
- `p24_shot4_pose_job635` — tư thế: BYĐ `ngoi` + mông + bàn tay; `do_tu_the` 635 sai / 639 đúng; lớp phải bắt `d26` (chưa có công cụ).

Giới hạn còn lại: tách món từ chữ là SUY (tiếng Việt: "mặt đen với hai mắt tròn đỏ" gộp vào `face`); đồng nghĩa màu / món là bảng tay; chưa
có ô `khai_bao_chu` trong hồ sơ Kho (K0b phần sau tạo trường, K1a điền).
