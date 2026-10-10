# Bộ kỹ năng kiểm — `knowledge/checks/<ID>.md`

Nguồn: `docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md` mục 4 ("Bộ kỹ năng kiểm", K0b), mục 5 (chuẩn so theo tầng), mục 10.
Bảng gốc: `devsys/error_types.json` (23 loại L1–L15, V1–V4, A1–A4). Test hợp đồng: `tests/test_knowledge_checks.py`.

## Mục đích
Mỗi loại lỗi một tệp, gom kiến thức nghề (giám sát kịch bản, quay phim, VFX ghép hình, thiết kế bối cảnh / map FF, lỗi ảnh / video AI,
Character Lock, âm thanh / phụ đề / dựng) thành: câu model KHAI được + cách CODE kết luận. Độ phủ đến từ cấu trúc (A5), không từ lỗi cũ.

## Ai đọc
- Tổ QC sau gen (⑥) và người duyệt gói trước tiền (④) ở các đợt K1a–K3 (ảnh), K4 (video), K6 (âm / chữ / dựng): lấy câu hỏi khai
  + bảng kết luận để dựng mệnh đề kiểm.
- Đạo diễn / vòng viết hợp tác (③): đọc "Code kết luận thế nào" để biết điều gì sẽ bị kiểm.
- Người rà / agent thẩm định: đối chiếu "Đo bằng code hiện có" với sổ khâu.

## Khuôn mỗi tệp (bắt buộc 4 mục có dấu *)
1. `# <ID> — <ten>` (đúng `ten` trong bảng) · dòng "Áp dụng:" · dòng "Nghề gốc:".
2. `## Câu hỏi khai được` * — model chỉ khai điều THẤY (enum / danh sách mở có giới hạn), KHÔNG khai đúng/sai (N4, A14);
   không giao VLM trái/phải, đếm, vị trí, tỉ lệ, góc máy (N5). Enum phải trùng `claude_khai[].enum` của bảng.
3. `## Code kết luận thế nào` * — mỗi câu so với nguồn nào: BYĐ (T1) / luật thế giới (T2) / lẽ thường (T3) / sự thật hình học
   (`core/stage_facts.py`) / Kho `must_keep` → ĐỎ / VÀNG / qua. Thiếu / `unsure` / ngoài enum → VÀNG (không im lặng). Chỉ T3 lệch mà
   T1/T2 im lặng → VÀNG + câu hỏi "cố ý hay lỗi" (≤ 5 / dự án, gom theo vật — A8), KHÔNG tự kết luận.
4. `## Đo bằng code hiện có` * — trích `code_do` (file:hàm + cờ). Cờ TẮT (`bat: false` hoặc cờ mặc định tắt trong `core/features.py`)
   ghi rõ KHÔNG tính; cái chưa có ghi "chưa có (đợt Kx)". Không bịa cách kiểm.
5. `## Gợi ý nhìn kỹ (lẽ thường, không phải luật)` — ngắn; chỉ để model nhìn kỹ.
6. `## Ca lỗi thật` * — ca người dùng từng bắt + tham chiếu `tests/golden/cases/` nếu có; chưa có thì ghi "chưa có".

## Hiện trạng 10/10 (theo bảng, cờ mặc định)
Mọi cờ liên quan (`qc_team`, `palette_check`, `stage_camera`, `scene_qc`, `director_camera_plan`, `rough_cut_review`) đang TẮT mặc
định. Cách kiểm chạy không cần cờ: `core/plate_camera.py:subject_box` (máy 3D, trước gen), `core/clip_measure.py` (V1–V3),
`core/voice_check.py:check_line` (A1), `core/ffmpeg_studio.py:measure_loudness` (A2). Còn lại phần lớn "chưa có (K1a–K6)".

## Thêm loại / ca (mục 10 kế hoạch)
1. Lỗi lọt → ghi ca hồi quy `tests/golden/cases/` (BYĐ, gói, ảnh, lỗi đúng, `loai_loi`, `lop_phai_bat`) — 0 USD.
2. Xếp vào một loại; KHÔNG xếp được → thêm loại mới vào `devsys/error_types.json` (id mới, `ap_dung`, `code_do`, `claude_khai`, ghi
   trung thực `xay` + đợt) VÀ tệp `knowledge/checks/<ID>.md` theo khuôn trên — test hợp đồng đỏ tới khi đủ cả hai.
3. Lớp kiểm chưa có → thêm (câu dữ kiện cho Đạo diễn / câu kiểm gói / mệnh đề QC / cách code kết luận); có mà lọt → sửa lớp đó.
4. Sửa nguồn (BYĐ / sự thật / ảnh tham chiếu / Kho), không vá prompt của riêng ca đó; cập nhật mục "Ca lỗi thật" của tệp loại.
