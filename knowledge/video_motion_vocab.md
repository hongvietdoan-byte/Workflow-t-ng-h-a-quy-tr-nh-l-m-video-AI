# Knowledge pack — Video motion prompt (image-to-video, v0.1, bản khởi đầu)

> Cần chuyên gia miền duyệt trước khi khóa version (PLAN.md Mục 3.6). **Đã đối chiếu hướng dẫn chính thức Kling 3.0 ngày 2026-09-29**
> (S0.14 T1 — "Kling VIDEO 3.0 Model Guide", `research/craft/trung_quoc/NGUON_TQ.md` [19]); kết quả ở mục "Kling 3.0" cuối file.

## Nguyên tắc
1. **Một clip 5 giây = một chuyển động camera chính + một hành động chính của chủ thể.** Đừng nhồi nhiều hành động.
2. Ảnh đã cố định ngoại hình → prompt chỉ mô tả **chuyển động**, không mô tả lại ngoại hình.
3. Viết cụ thể, có tốc độ và hướng: "slow push-in", "camera orbits 15° clockwise".
4. Luôn kèm negative prompt cho lỗi thường gặp (biến dạng tay/mặt, nháy hình, chữ/logo lạ).
5. Giữ nhất quán: nhân vật không đổi trang phục, không xuất hiện thêm người.

## Từ vựng camera
| Chuyển động | Mô tả |
|---|---|
| push-in / pull-out (dolly) | Tiến sát / lùi xa chủ thể |
| pan left/right | Xoay ngang tại chỗ |
| tilt up/down | Xoay dọc tại chỗ |
| orbit / arc | Di chuyển vòng quanh chủ thể |
| tracking / follow | Đi theo chủ thể |
| crane up/down | Nâng/hạ máy |
| handheld | Rung nhẹ, cảm giác đời thực |
| static | Máy cố định, chỉ chủ thể chuyển động |

## Tốc độ & nhịp
slow / medium / fast; ease-in / ease-out; "subtle" cho chuyển động nhỏ.

## Khung prompt gợi ý
`[camera move + tốc độ], [hành động chính của chủ thể], [chuyển động môi trường: gió, sương, lửa], [nhịp/cảm xúc]`

Ví dụ: "Slow push-in, Lyra turns her head toward the sound, mist drifts left to right, tense and quiet."

## Negative prompt mặc định
`deformed hands, extra fingers, distorted face, flickering, text, watermark, sudden cuts, extra people, outfit change`

## Theo thể loại (tham khảo, không mặc định — chọn theo ý đồ cảnh; mở rộng dần)
- **Hành động:** camera tracking nhanh, handheld, cắt nhịp gấp; hành động lớn của chủ thể.
- **Kinh dị/u ám:** static hoặc slow push-in, ánh sáng nhấp nháy, sương, chủ thể ít cử động.
- **Drama/đối thoại:** medium/close-up, rack focus nhẹ, chuyển động rất nhỏ.
- **Hùng vĩ/trailer game:** low angle, crane up, orbit chậm, cờ/áo choàng bay.

## Kling 3.0 — đối chiếu tài liệu chính thức (2026-09-29, S0.14 T1; nguồn [19] trong `research/craft/trung_quoc/NGUON_TQ.md`)
Model Kling mà pipeline gửi qua ClipAI là **Kling 3.0 Omni** (`kling` → `kling-v3-omni`, `core/adapters/clipai.py`), nên các điểm dưới
áp dụng thẳng. Đây là tư liệu có điều kiện — ghi nguồn và mức tin, không phải công thức.
- **Thời lượng 3–15 s** một lần gen (khớp `data/provider_rules.json`).
- **Hai kiểu nhiều shot:** Multi-Shot *tự động* (model tự chia shot, cỡ, góc) và *tự viết* (người viết "Shot 1, … Shot 2, …" + thời lượng
  từng shot). API ClipAI mà pipeline dùng là kiểu tự viết (`multi_shot` + `multi_prompt`). Một người thử (量子位 [22], độ tin vừa) thấy
  kiểu tự viết "kết quả không ổn định"; dự án tự đo 27/09 (P3/S3, `docs/PHAN_TICH_GOP_SHOT_2026-09-27.md`): shot sau trong nhóm **bịa
  hoặc bỏ nội dung** vì chỉ có ảnh khung đầu → pipeline không gộp nhiều góc bằng Kling multi-shot.
- **Cách viết một shot:** góc/cỡ + chuyển động máy (+ thời lượng), câu ngắn, có chủ ngữ; "viết như lời chỉ đạo của đạo diễn, không chồng
  từ khóa" (bài tổng hợp [21]). Công thức cộng đồng [20]: chủ thể + chuyển động + cảnh + (ngôn ngữ máy + ánh sáng + không khí) (+ âm thanh
  ở 3.0) — phần trong ngoặc tùy chọn; clip ngắn thì tả rõ nhưng đừng phức tạp.
- **Ai nói câu nào:** tài liệu gắn **từng câu thoại với tên nhân vật** ngay trong prompt; điểm yếu người thử thấy là **chia thoại giữa các
  nhân vật chưa chuẩn** [22]. Pipeline lồng giọng TTS sau, nên câu thoại không cần có trong prompt — nhưng prompt vẫn phải **nêu tên người
  đang nói** (và người kia đang nghe) để model mở đúng miệng. Code kiểm: `core/speaker_lint.py` (T2).
- **Thoại gốc chỉ 5 ngôn ngữ** (Trung, Anh, Nhật, Hàn, Tây Ban Nha) — **không có tiếng Việt** → với Kling, thoại luôn là TTS ghép sau;
  "Element Binding" giọng không dùng được cho giọng Việt. Ghi trong bảng luật (`speech_languages`, dòng Q4 của `dp.md`).
- **Element Binding** (chủ thể từ 1 video hoặc 2–4 ảnh, kèm giọng tùy chọn) và **khung đầu–cuối**: có trong 3.0; ClipAI mở phần nào cho
  API chưa kiểm hết (khung cuối: cờ `end_frames`, chưa chạy thật).
