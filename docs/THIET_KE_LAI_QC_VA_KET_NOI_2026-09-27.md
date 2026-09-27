# Thiết kế lại kết nối các khâu + QC cho quy trình storyboard (2026-09-27)

Bối cảnh: #8 đã đổi quy trình ảnh — **mỗi cảnh một ảnh toàn cảnh ngang → storyboard Deepix (model tự vẽ cả cảnh) → video Seedance chỉ ảnh
tham chiếu, gộp 2–4 shot**. Người dùng yêu cầu: xét lại việc nào còn dùng, tối ưu token (mỗi cảnh nạp nhiều mà hiệu quả thấp), dựng lại
kết nối giữa các khâu, đặc biệt QC. Số liệu gốc: `docs/RA_SOAT_CLAUDE_KY_NANG_2026-09-27.md`.

## 1. Việc cũ nào còn dùng trong quy trình mới
| Thứ | Còn dùng? | Ghi chú |
|---|---|---|
| Ghép phông xanh + các bộ kiểm ghép (đo xanh, mép cắt, vật che, chỗ đứng) | **Không** (cờ `location_plates` tắt) | giữ nguyên code, test vẫn chạy — cho lúc cần đúng hình học tuyệt đối |
| 54 ảnh có nhãn của #8 làm bộ đo QC | **Một phần** | nhãn là lỗi *ghép* → hết giá trị cho cách vẽ mới; giữ làm bộ đo "lỗi kỹ thuật", phải gắn nhãn thêm khung storyboard mới |
| QC nhận ảnh toàn cảnh làm tham chiếu nơi chốn | **Có — quan trọng hơn** | ảnh toàn cảnh là "chuẩn nơi chốn" của cả cảnh; QC phải so với nó |
| Ghi "lời gọi đã nạp tệp nào" | **Có** | cần để đo mọi thay đổi sau này |
| QC Claude từng ảnh (8 tiêu chí 0–1) | **Thay** | xem mục 3 |
| QC đồng bộ cả bộ (1 tấm ghép 33 ảnh, 4 cột) | **Thay bằng QC theo cảnh** | 33 ô nhỏ trên 1 tấm → Claude không thấy chi tiết |
| Motion prompt bằng Claude (Bước 3) | **Không cần cho nhóm Seedance** | P2m thử thật dựng prompt nhóm **bằng code** từ trường Director và đạt (3 shot đúng storyboard) |
| QC video bằng Claude từng clip | **Thay** | clip nhóm cắt ra nhiều shot → kiểm bằng code + 1 lượt theo nhóm |

## 2. Token đi đâu — cái gì thật sự tốn
Giá Sonnet 5: vào 2 USD/triệu, **ra 10 USD/triệu**, đọc cache = 10 % giá vào.
- **Director Tầng B**: mỗi cảnh ~27k token vào nhưng ~90 % đọc cache (rẻ); **~22k token ra mỗi cảnh ≈ 0,22 USD** → 6 cảnh ≈ 1,3 USD, gần hết
  là chữ viết ra (bảng shot JSON rất nhiều trường: performance, why, lighting, blocking, image_prompt dài…). **Chi phí nằm ở đầu ra, không
  phải ở tài liệu nạp vào.**
- **QC ảnh**: ~5,1k vào mới (ảnh cần chấm + 2–4 ảnh tham chiếu ≈ 1,4k token/ảnh + thông số) + 470 ra ≈ **0,016 USD/ảnh**; 33 ảnh + gen lại
  + QC đồng bộ ≈ 0,7–1 USD/dự án — mà **không bắt được lỗi quan trọng** (mục 3 tài liệu rà soát).
- **Motion**: ~20k token vào không cache — bỏ được với nhóm Seedance.

## 3. QC mới: "rẻ trước, Claude sau, hỏi có/không thay vì chấm điểm"
Nguyên tắc từ số liệu #8: QC Claude chấm điểm 0–1 cho 8 tiêu chí **không phân biệt** ảnh lỗi (0,67) với ảnh tốt (0,69); tiêu chí "đứng trên
nền" 0,94 cả ảnh lơ lửng. Điểm số trung bình vô nghĩa khi mô hình không được hỏi đúng câu. Làm lại thành 3 lớp:

**Lớp 0 — code, miễn phí, mọi ảnh (chặn trước khi tốn Claude):**
1. Đếm khuôn mặt (YuNet đã có) = số nhân vật của shot (trừ shot quay lưng / qua vai được khai).
2. **Cỡ cảnh đo bằng mặt**: chiều cao mặt / chiều cao khung → CU / MCU / MS / WS; lệch cỡ Director xin (vd S1·1 CU ra MCU) → vẽ lại kèm câu sửa.
3. Mắt / mặt ngoài vùng an toàn (thanh giao diện trên 15 %, dải phụ đề) — luật đã có trong `safe_zones.md`, nay áp cho ảnh.
4. Đêm: độ sáng vùng mặt dưới ngưỡng → vẽ lại kèm câu sửa ánh sáng.
5. Màu trang phục so ảnh chuẩn nhân vật (lược đồ màu trong khung mặt/thân) → cờ "có thể sai người".
Sai → gen lại **có câu sửa cụ thể** (luật 6), tối đa 2 lần; không gọi Claude.

**Lớp 1 — Claude, MỘT lượt cho MỖI CẢNH (thay QC từng ảnh + QC đồng bộ):**
- Gửi: tấm ghép các khung của cảnh (đủ lớn: ≤ 6 khung/tấm, mỗi khung ~512 px), **ảnh toàn cảnh** của cảnh, 1 ảnh chuẩn / nhân vật, bảng
  shot rút gọn (mã, cỡ, hành động 1 dòng, ai ở trái/phải).
- Hỏi **câu có/không cho từng khung**, kèm chỗ nhìn: đúng người (so ảnh chuẩn)? đúng nơi (so ảnh toàn cảnh)? hành động khớp dòng mô tả?
  trái/phải đúng và liên tục với khung trước? có lỗi AI rõ (tay, mặt, người thừa)? → trả JSON `{khung: [lỗi cụ thể + câu sửa tiếng Anh]}`.
- Thấy được **liên tục giữa các khung** (cái QC từng ảnh không bao giờ thấy). ~6 lượt/dự án thay ~40 lượt.

**Lớp 2 — cắt sát chỗ nghi ngờ (chỉ khi lớp 1 hoặc kiểm Bible gắn cờ chi tiết nhỏ):** gửi vùng cắt độ phân giải cao (mặt, mũ, tay, huy
hiệu) + vùng tương ứng trên ảnh chuẩn. Tránh lỗi kiểu "mũ đội ngược đọc thành xuôi" do ảnh bị thu nhỏ.

**Người duyệt ở cổng storyboard** thấy trước các khung có cờ (lớp 0/1) kèm lý do — không còn 19 ảnh "dưới sàn" không rõ vì sao.

**Đo hiệu quả bắt buộc**: gắn nhãn bằng mắt bộ khung storyboard mới của #8 (người + tôi) → chạy lớp 0/1 trên bộ nhãn, báo tỉ lệ bắt đúng /
báo nhầm trước khi tin; chỉ sau đó mới cân nhắc Haiku 4.5 cho lớp 1.

## 4. Kết nối các khâu (luồng dữ liệu mới)
```
Director (bảng shot + ý đồ)
  └─ code kiểm bảng shot (đã có một phần) ─────────────────────────────┐
Ảnh toàn cảnh mỗi cảnh (chuẩn nơi chốn + ánh sáng)                     │
  └─ storyboard Deepix theo cảnh (ảnh chuẩn nhân vật + ảnh toàn cảnh)   │
       └─ QC lớp 0 (code) → gen lại có câu sửa                          │
       └─ QC lớp 1 (1 lượt / cảnh, so ảnh toàn cảnh + ảnh chuẩn) ──────┤ cờ + lý do
       └─ [lớp 2 khi cần]                                               │
  └─ CỔNG STORYBOARD (người duyệt; khung có cờ đứng đầu) ◄──────────────┘
Video Seedance nhóm (prompt nhóm dựng bằng code từ trường Director — không Claude)
  └─ code kiểm clip: số điểm cắt = số shot (scdet), độ dài, có mặt người, nhiễu/chớp
  └─ QC video lớp 1: 1 lượt / nhóm (khung giữa mỗi shot đặt cạnh khung storyboard của shot đó)
Dựng (code: phụ đề, màu, âm thanh, vùng an toàn)
```
Mỗi khâu QC so với **chuẩn của khâu trước** (khung storyboard so ảnh toàn cảnh + ảnh chuẩn; clip so khung storyboard) — hiện QC ảnh không có
chuẩn nơi chốn, QC video không so với storyboard.

## 5. Director tốn ở đầu ra — tối ưu cho dự án sau (đợt sửa kỹ năng gộp)
- Bớt trường Claude phải viết: trường suy được bằng code (framing, lens, mẫu lighting theo giờ, nhạc cut/in) để code điền; `why`/`performance`
  rút ngắn có giới hạn ký tự.
- Sách vai giữ, thêm **bảng kiểm cuối ≤ 20 dòng** (đúng các trường hay bị bỏ) + code kiểm + chỉ hỏi lại cảnh sai.
- Không đổi cho #8 (không chạy lại Director).

## 6. Thứ tự làm (đề xuất)
1. QC lớp 0 (code) cho ảnh storyboard + test — miễn phí.
2. QC lớp 1 theo cảnh (prompt mới + tấm ghép theo cảnh + ảnh toàn cảnh) thay QC từng ảnh + QC đồng bộ trong chạy tự động (cờ mới) + test với
   Claude giả — miễn phí.
3. Ghi "lời gọi đã nạp những tệp nào" vào sổ chi.
4. Prompt nhóm Seedance dựng bằng code (bỏ Claude motion cho nhóm) — nhánh đã có trong `seedance_refs`; nối vào để Bước 3 không bắt buộc Claude.
5. Chạy ảnh #8 (38 ảnh) → gắn nhãn khung mới → đo lớp 0/1 trên nhãn → cổng storyboard.
6. Code kiểm clip + QC video theo nhóm (trước khi gen video).
