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
| R5 | Kling khung đầu + khung cuối: tài liệu API ClipAI chỉ ghi `first_frame` cho Kling 3.0 Omni; đầu–cuối có ở Kling O1 (5/10 s) — **chưa có giá** trong `data/pricing.json` (trần tiền sẽ chặn) | `clipai-1.3.1/reference.md`; `docs/CLIPAI_FEATURES.md` #7 |
| R6 | Nội suy đầu→cuối là **một đường máy liên tục** giữa hai hình: hai hình khác góc (shot–phản shot) sẽ ra biến hình/trượt, không ra vết cắt | bản chất kỹ thuật (first–last frame interpolation); cần thử để có số |
| R7 | Pipeline đã vẽ được **khung từng shot kiểu storyboard Deepix** (cờ `storyboard_api`: shot rộng nhất làm neo, cùng nơi/ánh sáng) | `core/scene_storyboard.py`, thử #7 cảnh 1 |

## 2. Các phương án
| Mã | Cách | Ảnh cần | Tiền video cảnh thử (12,5 s, 6 shot) | Ưu | Rủi ro (cần thử để biết) |
|---|---|---|---|---|---|
| **P0** mốc | Mỗi shot 1 clip Seedance Fast (cách hiện tại) | 6 khung đầu | 6 × 4 s = 24 s → **2,88** | kiểm soát từng shot, gen lại lẻ rẻ | tốn gấp đôi; cắt giữa clip rời dễ lệch |
| **P1** | Seedance, **khung đầu (shot 1) + khung cuối (shot cuối)**, prompt "Shot 1…Shot N" — chia 2 lần gen × 3 shot | 2 ảnh / lần gen | ~13 s → **1,56** | khóa đầu–cuối bằng ảnh thật; ít ảnh | shot giữa chỉ có chữ → lệch nhân vật/bố cục; model có cắt đúng chỗ không |
| **P2** | Seedance **chỉ ảnh tham chiếu**: khung storyboard của từng shot (Image 1 = Shot 1…) + ảnh nhân vật, không khung đầu — 2 lần gen × 3 shot | 3 khung + ≤ 3 ảnh nhân vật / lần | ~13 s → **1,56** | **mọi shot có ảnh hướng dẫn**; nhân vật có ảnh danh tính | khung đầu không trùng pixel với storyboard; model có theo đúng thứ tự Image↔Shot không |
| **P3** | Kling multi-shot, khung đầu + multi_prompt (mỗi shot ≥ 3 s) — 2 lần gen × 3 shot | 1 ảnh / lần | 6 × 3 s = 18 s → **1,44** | rẻ/giây, cắt theo cấu trúc API | R3: shot < 3 s bị kéo dài 3 s (nhịp chậm lại); R4: shot sau sai nhân vật |
| **P4** | Kling đầu–cuối liền một đường máy | 2 ảnh | 5–10 s | chuyển động máy liền mượt | R5 chưa có giá/API chưa xác nhận; R6 không làm được cắt góc → chỉ hợp **shot liền một vị trí máy**, không hợp cảnh thoại nhiều góc |
| **P5** | **Director gộp ở gốc**: ít vết cắt hơn — một shot dài 6–10 s có đổi cỡ bằng chuyển động máy (đẩy vào, lia theo người nói) thay cho 3–4 cắt | 1 ảnh | ~13 s → 1,56 (Seedance) / 1,04 (Kling) | rẻ nhất, model làm tốt shot liền; hợp video dài | đổi ngôn ngữ dựng (ít cắt hơn FF gốc ~2 s/shot) — cần người dùng chấp nhận |
| **P6** | Lai theo loại shot: shot khớp môi / ⭐ / money shot giữ riêng (P0); phần còn lại gộp theo P1/P2/P3 thắng | — | tùy | giữ chất lượng chỗ quan trọng | phức tạp hơn một chút |

Đánh giá sơ bộ (chưa có số thật): **P2 là ứng viên mạnh nhất cho cảnh nhiều góc** (mọi shot có ảnh hướng dẫn, không vi phạm R1), **P1** là phương án dự phòng khi thứ tự Image↔Shot không được model tôn trọng. **P4 không phải câu trả lời cho cảnh gộp nhiều góc** (R6) — chỉ dùng cho shot liền một vị trí máy (thay H5). **P3** rẻ/giây nhưng có lỗi R4 đã gặp thật. **P5** là đòn bẩy lớn nhất cho video 30–60 phút và kết hợp được với P1/P2.

## 3. Kế hoạch thử (chờ người dùng duyệt — tốn tiền)
- **Cảnh thử:** cảnh 2 của #8 ("CẢNH 1 – 8–20 GIÂY": 3 nhân vật, 6 shot, 12,5 s, thoại liên tục) — khó nhất vì nhiều người + đổi góc. Nếu
  còn trần: thêm cảnh 1 (cinematic 4 shot, cận cảm xúc).
- **Chung cho mọi phương án:** cùng khung storyboard Deepix của cảnh (6 khung, ~0,31 USD, vẽ qua Bước 2 như bình thường), cùng motion ý đồ,
  Seedance **Fast 720p** / Kling **std 720p** (chế độ Thử rẻ), không âm thanh model (giọng lồng sau), 1 lần gen / phương án (không gen lại).
- **Chạy:** P0 (6 clip), P1 (2 lần gen), P2 (2 lần gen), P3 (2 lần gen) → ~7,3 USD + ảnh 0,31 + QC Claude ~0,3 ≈ **8 USD**. Bỏ P0 nếu muốn
  tiết kiệm (dùng clip #6/#7 cũ làm mốc) → ≈ **5 USD**. P4 không chạy (lý do R5/R6); P5 cần Director đổi cách chia — đo ở bước sau.
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
