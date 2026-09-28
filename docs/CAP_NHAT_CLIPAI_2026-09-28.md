# Cập nhật ClipAI (người dùng gửi 2026-09-28) → ảnh hưởng tới kế hoạch sau #8

> Nguồn đã đọc (tài liệu chính thức trên web, không cần đăng nhập): https://clipai.ingarena.net/docs/ — Seedance Model Selection, Seedance
> Generation Blocks, Game Video Production, Seed Audio 1.0 Guide, Blender Add-on. **Chưa đọc được:** tài liệu chi tiết bản cập nhật trên
> Google Docs (CN/EN) — trả 401, cần đăng nhập → phần "Chế độ bản mẫu" (Sample Mode) và Eleven Music v2.5 **chưa rõ tham số API**.
> Không tốn tiền; chưa đổi code. Mã việc mới (thêm vào `docs/KE_HOACH_SUA_SAU_DU_AN_8.md`) để góp ý.

## 1. Điều quan trọng nhất đọc được

| Điểm | Nội dung (tài liệu chính thức) | Liên quan lỗi #8 |
|---|---|---|
| **Kho chủ thể = cách chính thức qua bộ lọc "người thật"** | Mỗi ảnh / video nhân vật gửi Seedance phải **tải lên kho chủ thể rồi chọn từ kho** (từng ảnh một); nhân vật ảo tả thực hay bị nhận nhầm là người thật. **Free Fire đã ký thỏa thuận bản quyền** (AOV, DF chưa) | #8 lách bằng dải chữ + **dấu cộng đỏ trên mắt** (P2m) → mặt yếu thông tin, cận Kelly ra kiểu anime (lỗi 1.3). Code đã có `core/adapters/clipai_subjects.py` (việc D7/K5 hoãn trước đây) |
| **Seedance 2.0 / Fast KHÔNG theo mốc giây** | "2.0 does not respond to timestamps; it responds only to shot numbers"; Fast còn kém hơn về mốc giây và chuyển động phức tạp | prompt nhóm Seedance của #8 viết theo **mốc giây** ("0–1.5 s: …") → trôi mốc, hành động không kịp (lỗi 1.5, 5 clip bị QC chặn) |
| **Seedance 2.5** | tả thực hơn (da, vi biểu cảm, chuyển động), **hỗ trợ tiếng Việt** (11 ngôn ngữ; 2.0 không có tiếng Việt), tối đa **30 ảnh tham chiếu**, 4–30 s, **tham chiếu chỉ bằng âm thanh**, theo mốc giây nguyên, **tham chiếu "white-model"** (video 3D thô → render), **tham chiếu lưới storyboard**, chuyển cảnh liền giữa hai video. 480P/720P (không 1080P). Ước **720P ≈ 0,23 USD/s** (Fast 0,12; Mini 0,08; 2.0 1080P 0,37) | khớp môi tiếng Việt (1.7), chuyển động giả (1.5), liền mạch giữa shot (1.6), nền tháp từ render 3D (1.4) |
| **Cấu trúc prompt cho game** | Prompt = nhiệm vụ + chủ thể & vai trò từng tài sản (@Image1 khóa ngoại hình, @Video1 tham chiếu chuyển động) + hành động theo giai đoạn + máy quay + phải giữ + yêu cầu đầu ra; **không nhồi nhiều hành động / đổi máy vào thời lượng ngắn**; tài sản mâu thuẫn thì thay tài sản chứ không thêm câu phủ định | prompt nhóm #8 dồn 3–4 shot + hành động vào ≤ 15 s |
| **Seed Audio 1.0** | một lệnh tạo **cả track**: thoại nhiều nhân vật + nhạc + hiệu ứng + âm nền; **tiếng Việt**; khóa giọng bằng tối đa **3 file mẫu** (@Audio1–3 — vừa đủ Kelly/Kenta/Maxim); mốc thời gian **100 ms**; trả **mốc phụ đề theo câu/từ**; tối đa 2 phút; không SSML. Prompt Assistant nay tối ưu cho Seed Audio (tránh lỗi định dạng mốc giây) | độ dài / giọng / nhạc / hiệu ứng lệch nhau (1.2, 1.8); track âm thanh có thể làm **tham chiếu âm thanh cho Seedance 2.5** → khớp môi |
| **Chế độ bản mẫu (Sample Mode)** | (theo tin người dùng gửi) tạo bản mẫu trước, bản cuối 1080p dựa hoàn toàn trên bản mẫu → ít phải thử lại | đúng chỗ tốn tiền của #8 (53 clip / 33 shot). **Chưa rõ có trong API không** |
| **Eleven Music v2.5** | model nhạc mới nhất (web: Audio Generation → Text to Music) | pipeline đang gọi `music_v2`; bản nhạc mới #8 chưa được bạn nghe |
| **Blender add-on v0.3.4** | cập nhật tự động trong panel | S5: render tháp 3D; kết hợp tham chiếu "white-model" của Seedance 2.5 |

## 2. Đề xuất đổi kế hoạch (mã mới)

| Mã | Việc | Loại | Thay / bổ sung |
|---|---|---|---|
| **S4.7** | Dùng **Kho chủ thể** cho mọi ảnh nhân vật gửi Seedance (tự tải từng ảnh, nhớ `subject_id`), **bỏ mẹo dấu đỏ trên mắt** khi đã có chủ thể | 💻 + 💵 thử 1 nhóm (~0,5 USD) | thay P2m (đánh dấu ảnh); giải lỗi 1.3 |
| **S4.8** | Prompt Seedance 2.0 / Fast viết theo **"Shot 1 / Shot 2"** thay vì mốc giây; mốc giây chỉ dùng cho 2.5 | 💻 miễn phí | sửa ngay nguyên nhân trôi hành động trong nhóm |
| **S4.9** | Prompt theo cấu trúc game của ClipAI: vai trò từng ảnh (@Image1 khóa ngoại hình, @Image2 khung đầu…), hành động theo giai đoạn, "phải giữ", máy khóa mặc định | 💻 | gộp vào S4.4 |
| **S4.10** | A/B **Seedance 2.5** (720P) so với Fast trên 3 shot của #8: cận Kelly (1.3), shot chạy (1.5), shot thoại có **tham chiếu âm thanh tiếng Việt** (1.7) | 💵 ~3–4 USD | có thể thay A/B khớp môi (a)/(b) ở S4.2 bằng cách thứ ba: Seedance 2.5 + âm thanh |
| **S4.11** | **Chế độ bản mẫu**: xác minh có trong API không; nếu có: bản mẫu 480P cho mọi shot → người duyệt → bản cuối 1080P | 🔍 + 💻 | cần tài liệu Google Docs (bạn mở / xuất giúp) |
| **S2.6** | Thử **Seed Audio 1.0** làm track thoại cả cảnh (3 giọng mẫu Kelly/Kenta/Maxim) có mốc 100 ms + mốc phụ đề → khóa timeline S2 | 💵 vài lượt âm thanh | có thể thay TTS từng câu; nếu tốt: track này làm tham chiếu âm thanh cho Seedance 2.5 |
| **S1.15** | Tùy chọn model nhạc **Eleven Music v2.5** (khi API có) cho brief nhạc theo nhịp truyện | 💻 + 💵 1 lượt | sau khi bạn nghe nhạc v4 |
| **S5.6** | Render tháp GLB thành video "white-model" (máy chạy quanh quảng trường) làm tham chiếu chuyển động / bố cục cho Seedance 2.5 | 💻 (Blender) + 💵 thử | bổ sung S5.1 |

## 3. Cần bạn
1. Mở / xuất giúp tài liệu chi tiết bản cập nhật (Google Docs EN) — tôi cần phần **Sample Mode** (có API không, tham số, giá bản mẫu vs bản cuối) và tên model **Eleven Music v2.5**.
2. Đồng ý đưa S4.7–S4.11, S2.6, S1.15, S5.6 vào kế hoạch (các việc 💵 vẫn hỏi trước từng lần, có ước tính).
3. Kho chủ thể trước đây bị hoãn (quyết định 2026-09-22) — nay tài liệu chính thức khuyên dùng: đồng ý dùng lại cho nhân vật Free Fire?
