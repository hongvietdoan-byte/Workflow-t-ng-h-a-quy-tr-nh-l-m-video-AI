# Gộp nhiều shot vào một lần gen video — phân tích phương án và kế hoạch thử (2026-09-27)

> Bối cảnh: dự án thử #8 (kịch bản #6 "ANH CHỌN AI?", 63,7 s phim) — Director chia **33 shot, trung bình 1,93 s, 30/33 shot < 3 s**. Gen
> mỗi shot một clip thì trả tiền **132 s cho 63,7 s phim** (Seedance tối thiểu 4 s/clip) — video 15,84 USD. Người dùng yêu cầu (2026-09-27):
> làm chế độ gộp, **thử nhiều phương án** để chọn cách tối ưu; so "ảnh kiểu storyboard gen một cảnh gộp dài" với "2 ảnh đầu–cuối Kling";
> tìm cách khác khả thi hơn; "công đoạn quyết định cao — phân tích rõ ràng".

## 1. Ràng buộc đã xác nhận (không phải giả định)
| # | Ràng buộc | Nguồn |
|---|---|---|
| R1 | Seedance **từ chối trộn** khung đầu/cuối với ảnh tham chiếu ("first/last frame content cannot be mixed with reference media content") → mỗi lần gen chọn *khung đầu (+ khung cuối)* **hoặc** *≤ 9 ảnh tham chiếu* (2.5: ≤ 30) | chạy thật 2026-09-24; `core/adapters/clipai.py` `SEEDANCE_REFS_WITH_FIRST_FRAME = False` |
| R2 | Seedance: nhiều shot trong **một** prompt ("Shot 1: … Shot 2: …"), **2–4 shot** mỗi lần gen, mỗi shot một thay đổi + một chuyển động máy; clip 4–15 s (2.5: tới 30 s); **không** có tối thiểu cho từng shot con | tài liệu chính thức kèm skill ClipAI (`knowledge/seedance_prompting.md` mục "Nhiều shot"); BytePlus / hướng dẫn cộng đồng: gắn nhãn "Image 1…N" cho ảnh tham chiếu |
| R3 | Kling 3.0 Omni multi-shot: ≤ 6 shot, **mỗi shot ≥ 3 s**, tổng ≤ 15 s; một ảnh `first_frame` cho cả nhóm | API ClipAI `omni-video-submit` (`multi_shot`, `multi_prompt`); Magnific / Kling docs |
| R4 | Kling multi-shot thật (GĐ6): chỉ ảnh đầu nhóm bám nhân vật — **6/12 shot sau sai nhân vật** | `docs/KE_HOACH_TONG_2026-09-24.md` (R4); dp.md Q4 |
| R5 | Kling khung đầu + khung cuối: tài liệu API ClipAI chỉ ghi `first_frame`, nhưng code dự án đã gửi `end_frame` cho Kling 3.0 Omni (cờ `end_frames`, có test `tests/test_end_frames.py`) — **chưa xác nhận bằng chạy thật**; giá Kling std có trong bảng giá → thử được (sửa 2026-09-27 sau khi đọc lại code) | `clipai-1.3.1/reference.md`; `core/adapters/clipai.py` |
| R6 | Nội suy đầu→cuối là **một đường máy liên tục** giữa hai hình: hai hình khác góc (shot–phản shot) sẽ ra biến hình/trượt, không ra vết cắt | bản chất kỹ thuật (first–last frame interpolation); cần thử để có số |
| R7 | Pipeline đã vẽ được **khung từng shot kiểu storyboard Deepix** (cờ `storyboard_api`: shot rộng nhất làm neo, cùng nơi/ánh sáng) | `core/scene_storyboard.py`, thử #7 cảnh 1 |

## 2. Các phương án
| Mã | Cách | Ảnh cần | Tiền video cảnh thử (12,5 s, 6 shot) | Ưu | Rủi ro (cần thử để biết) |
|---|---|---|---|---|---|
| **P0** mốc | Mỗi shot 1 clip Seedance Fast (cách hiện tại) | 6 khung đầu | 6 × 4 s = 24 s → **2,88** | kiểm soát từng shot, gen lại lẻ rẻ | tốn gấp đôi; cắt giữa clip rời dễ lệch |
| **P1** | Seedance, **khung đầu (shot 1) + khung cuối (shot cuối)**, prompt "Shot 1…Shot N" — chia 2 lần gen × 3 shot | 2 ảnh / lần gen | ~13 s → **1,56** | khóa đầu–cuối bằng ảnh thật; ít ảnh | shot giữa chỉ có chữ → lệch nhân vật/bố cục; model có cắt đúng chỗ không |
| **P2** | Seedance **chỉ ảnh tham chiếu**: khung storyboard của từng shot (Image 1 = Shot 1…) + ảnh nhân vật, không khung đầu — 2 lần gen × 3 shot | 3 khung + ≤ 3 ảnh nhân vật / lần | ~13 s → **1,56** | **mọi shot có ảnh hướng dẫn**; nhân vật có ảnh danh tính | khung đầu không trùng pixel với storyboard; model có theo đúng thứ tự Image↔Shot không |
| **P3** | Kling multi-shot, khung đầu + multi_prompt (mỗi shot ≥ 3 s) — 2 lần gen × 3 shot | 1 ảnh / lần | 6 × 3 s = 18 s → **1,44** | rẻ/giây, cắt theo cấu trúc API | R3: shot < 3 s bị kéo dài 3 s (nhịp chậm lại); R4: shot sau sai nhân vật |
| **P4** | Kling std khung đầu + khung cuối, một đường máy liền | 2 ảnh | ~13 s → **1,04** | rẻ; chuyển động máy liền mượt | R6: hai góc khác nhau → dự kiến biến hình, không ra cắt → **thử để có bằng chứng** (người dùng hỏi thẳng phương án này) |
| **P5** | **Director gộp ở gốc**: ít vết cắt hơn — một shot dài 6–10 s có đổi cỡ bằng chuyển động máy (đẩy vào, lia theo người nói) thay cho 3–4 cắt | 1 ảnh | ~13 s → 1,56 (Seedance) / 1,04 (Kling) | rẻ nhất, model làm tốt shot liền; hợp video dài | đổi ngôn ngữ dựng (ít cắt hơn FF gốc ~2 s/shot) — cần người dùng chấp nhận |
| **P6** | Lai theo loại shot: shot khớp môi / ⭐ / money shot giữ riêng (P0); phần còn lại gộp theo P1/P2/P3 thắng | — | tùy | giữ chất lượng chỗ quan trọng | phức tạp hơn một chút |

Đánh giá sơ bộ (chưa có số thật): **P2 là ứng viên mạnh nhất cho cảnh nhiều góc** (mọi shot có ảnh hướng dẫn, không vi phạm R1), **P1** là phương án dự phòng khi thứ tự Image↔Shot không được model tôn trọng. **P4 không phải câu trả lời cho cảnh gộp nhiều góc** (R6) — chỉ dùng cho shot liền một vị trí máy (thay H5). **P3** rẻ/giây nhưng có lỗi R4 đã gặp thật. **P5** là đòn bẩy lớn nhất cho video 30–60 phút và kết hợp được với P1/P2.

## 3. Kế hoạch thử (chờ người dùng duyệt — tốn tiền)
- **Cảnh thử:** cảnh 2 của #8 ("CẢNH 1 – 8–20 GIÂY": 3 nhân vật, 6 shot, 12,5 s, thoại liên tục) — khó nhất vì nhiều người + đổi góc. Nếu
  còn trần: thêm cảnh 1 (cinematic 4 shot, cận cảm xúc).
- **Chung cho mọi phương án:** cùng khung storyboard Deepix của cảnh (6 khung, ~0,31 USD, vẽ qua Bước 2 như bình thường), cùng motion ý đồ,
  Seedance **Fast 720p** / Kling **std 720p** (chế độ Thử rẻ), không âm thanh model (giọng lồng sau), 1 lần gen / phương án (không gen lại).
- **Người dùng duyệt 2026-09-27:** chạy, **không tốn tiền Claude API** (trần Claude chỉ còn ~$3 cho chạy thật) → prompt gộp dựng bằng code từ trường
  Director (không gọi Claude), khung storyboard vẽ không QC Claude, chấm bằng mắt (phiên Claude Code) + ffmpeg. Không chạy P0 (mốc = clip #6/#7 cũ).
  Chạy P1, P2, P3, P4 (mỗi cách 2 lần gen × 3 shot) ≈ 5,7 USD + 6 khung ≈ 0,31 → **≈ 6 USD**. Công cụ: `tools/experiments/group_test.py`.
- **Chấm (định trước khi xem kết quả):**
  1. Nhận diện 3 nhân vật đúng ở từng shot (QC video Claude + người) — trọng số cao nhất.
  2. Số vết cắt và thứ tự đúng kịch bản (ffmpeg dò cắt cảnh `scdet`) — có cắt được về đúng từng shot để dựng không.
  3. Bố cục từng shot khớp khung storyboard (điểm giống ảnh).
  4. Liền mạch nơi chốn + ánh sáng giữa các shot.
  5. Lỗi hình (tay, mặt, biến hình), shot giữa có "tự bịa" người/vật không.
  6. **Tiền cho mỗi giây dùng được** = tiền gen ÷ số giây đạt 1–5.
- **Đầu ra:** bảng so sánh + clip cạnh nhau trên dashboard (Bước 4 🧪 Thử nghiệm) → người dùng xem, quyết phương án mặc định; code chế độ
  gộp theo phương án thắng (có cờ, có test), rồi chạy tiếp dự án thử.

## 4. Tác động video dài (30–60 phút) — nhân tuyến tính từ #8, chưa gen lại
| | 1 phút | 30 phút | 60 phút |
|---|---|---|---|
| Số shot (~31/phút) | 33 | ~930 | ~1.860 |
| Video — mỗi shot 1 clip Seedance Fast | ~15 | ~450 | ~900 USD |
| Video — gộp ≤ 15 s (P1/P2, Seedance Fast) | ~7,3 | ~220 | ~440 USD |
| Video — gộp + nhịp phim dài 3–6 s/shot (P5) | ~4–5 | ~130 | ~260 USD |
| Thời gian gen (2 clip song song) | ~1 giờ | ~23 giờ / gộp ~5 giờ | ~2 ngày / gộp ~10 giờ |
Video dài còn cần Director chia **theo chương** (một lượt Đạo diễn cho 30 phút vượt giới hạn câu trả lời).

## 5. Kết quả thử thật (2026-09-27, cảnh 2 của #8, 6 khung storyboard Seedream 720p)
| Lần gen | Kết quả | Cắt / nội dung | Nhân vật | Lỗi hình | Giây dùng được | Tiền (ClipAI `cost`) |
|---|---|---|---|---|---|---|
| P1 Seedance đầu+cuối, nhóm 1 / 2 | ❌ **từ chối lúc tạo** "may contain real person" (ảnh khung cuối) | — | — | — | 0 | 0 |
| P2 Seedance chỉ ảnh tham chiếu, nhóm 1 / 2 | ❌ **từ chối lúc tạo** (ảnh tham chiếu thứ 3) | — | — | — | 0 | 0 |
| P3 Kling multi-shot, nhóm 1 (3+4+3 s) | ✅ | cắt **đúng** 2,96 / 6,92 s; shot 1 khớp storyboard; shot 2 **sai** (lưng Kelly thay vì Maxim qua vai Kenta); shot 3 lệch (cận Maxim thay vì Kenta) | đúng người | ít | ~3/10 | 60 đv ≈ $0,60 |
| P3 nhóm 2 (3+3+3 s) | ✅ | **không cắt** — 9 s chỉ Maxim đi tới; shot 5 (Kelly), 6 (Kenta+Kelly) bị bỏ | đúng | không | ~3/9 | 53 đv ≈ $0,53 |
| P4 Kling đầu+cuối, nhóm 1 | ✅ | đầu/cuối khớp ảnh; **giữa biến hình** — Maxim thành "bóng ma xanh phát sáng" rồi thành cảnh qua vai | ❌ | nặng | ~2/7 | 42 đv ≈ $0,42 |
| P4 nhóm 2 | ✅ | đầu Maxim → máy lướt qua vai (nhòe) → cuối Kenta+Kelly khớp ảnh; bỏ shot 5 | đúng | nhẹ | ~6/6 nhưng là 1 cú máy liền | 36 đv ≈ $0,36 |
**Tổng thật:** 6 ảnh ≈ 0,31 + 4 clip Kling **1,91 USD** (sổ chi dự án ghi 2,56 — Kling std thật ~6 đv/s ≈ **$0,06/s**, bảng giá đang $0,08).
Nhóm 2 ClipAI trả **mã chờ tạm** (12 số) → công cụ đánh "không thấy task"; tìm lại theo thời điểm tạo + `multi_shot` trong `video-list`
(`find_by_prompt` không dùng được cho multi-shot vì task multi-shot có `prompt` rỗng) — ghi cho tổng kết.

**Kết luận từ bằng chứng:**
1. **Kling đầu–cuối (P4) không thay được cắt shot:** hai góc khác nhau → biến hình (nhóm 1); chỉ dùng được khi có chuyển động máy hợp lý
   nối hai khung (nhóm 2 — thành một cú máy liền, mất shot giữa).
2. **Kling multi-shot (P3) cắt đúng nhịp nhưng shot sau bịa nội dung** (chỉ có ảnh khung đầu) — xác nhận lại R4.
3. **Seedance (P1/P2) — phương án "mỗi shot có ảnh dẫn" — bị bộ lọc người thật chặn hoàn toàn** với ảnh look in-game FF. Chưa đo được chất lượng.
4. Chưa phương án gộp nào đạt yêu cầu "đúng từng shot theo storyboard" mà không trả giá chất lượng.

**Bước tiếp khả thi (chờ người dùng):**
- **S1 — Seedance qua Kho chủ thể:** tải 6 khung storyboard lên Kho chủ thể Seedance (qua kiểm duyệt người thật + bản quyền FF — tài liệu API),
  rồi chạy lại P2 bằng `asset://` (~1,5 USD). Nếu qua được thì đây là phương án có kiểm soát từng shot + gộp tiền.
- **S2 — Không gộp, nhưng cắt ít hơn (P5) + Kling std giá thật:** mỗi shot 1 clip Kling (khung đầu = storyboard → shot đúng như P3 shot 1),
  Director chia shot dài hơn (≥ 3 s, dùng chuyển động máy thay cắt) → ~70 s trả tiền / phút ≈ **4–5 USD / phút phim**.
- **S3 — Lai:** P3 Kling multi-shot chỉ cho nhóm shot **cùng người, cùng hành động liền** (vd chạy qua dãy nhà); shot đổi người/đổi góc lớn
  giữ riêng.
