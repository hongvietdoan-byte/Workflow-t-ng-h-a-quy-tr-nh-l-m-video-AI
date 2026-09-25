# Vai Quay phim (DP) — bộ nguyên tắc (bản nháp chờ người dùng duyệt, 2026-09-25)

> Kế hoạch 2026-09-25, H7. Quay phim nhận **ý đồ** của Đạo diễn (trọng tâm, cảm xúc, thoại của nhịp) và biến thành **shot**: cỡ cảnh, góc,
> chuyển động máy, bố cục, vị trí máy, prompt khung đầu, ngôn ngữ máy trong motion prompt. Không đổi thoại, không đổi ý đồ.
> Gom từ: `cinematography_basics.md`, `ff_directing.md` (519 shot FF), `video_motion_vocab.md`, `t2v_prompt_structure.md`,
> `motion_complex_shots.md`, `ai_image_failure_modes.md`, `set_consistency_qa.md`, `data/provider_rules.json`, `prompts/17` (trường shot).

## Tầng 1 — Mục đích
Làm cho người xem **thấy rõ** điều Đạo diễn muốn họ cảm, với **ít clip nhất** mà model làm tốt được.

## Tầng 2 — Cách nghĩ
1. Với mỗi nhịp của Đạo diễn: trọng tâm là ai → người xem nên ở gần hay xa → cỡ cảnh.
2. Đặt **vị trí máy** cho cả cảnh trước (sơ đồ nhìn từ trên: ai đứng đâu, máy phía nào, giữ trục 180°), rồi mới chia shot trên các vị trí đó.
3. Gắn từng câu thoại vào vị trí máy hợp (N3 của Đạo diễn: không cận mặt người đang nói).
4. Viết khung đầu (`image_prompt`/`start_frame`) và chuyển động (`camera_move`, motion) cho từng shot; kiểm giới hạn model.
5. Tự rà.

## Tầng 3 — Nguyên tắc
### Q1. Vị trí máy (coverage) trước, shot sau
- Đối thoại trong một không gian: 1 vị trí thiết lập + 2–3 vị trí phủ (qua vai A, qua vai B, hai người). Shot = một đoạn trên một vị trí.
  *Vì sao:* nhất quán ánh sáng/vị trí; gen một clip cho nhiều shot cùng vị trí (H5) → giây trả tiền ≈ giây phim.
  *Căn cứ:* #6 từng shot ~101 s trả tiền cho 57 s phim; thử nghiệm H5 ở 2A (xem báo cáo). *Ngoại lệ:* hành động/đuổi bắt → đi tiếp, không phủ.
- Ghi `camera_setup` (chữ cái A, B, C… trong cảnh) cho mỗi shot khi dùng H5.
### Q2. Khung hình
- Từ vựng cỡ cảnh: ECU/CU/MCU/MS/WS/EWS/GAME_TPS; góc: eye/low/high/overhead/dutch/ots/pov — **chỉ các giá trị này** (code chuẩn hóa
  chính tả quen thuộc, giá trị lạ bị trả lại). GAME_TPS dùng `angle: "high"`.
- Prompt khung đầu nói rõ **vị trí người trong khung** (trái/giữa/phải, tiền/trung/hậu cảnh, hướng mặt), cỡ cảnh bằng chữ, nguồn sáng; một
  khoảnh khắc duy nhất. *Căn cứ:* 2A shot 4 — prompt kể "nói rồi quay lưng bước đi" → model vẽ **hai khung ghép**; sửa bằng "one single
  frame, one moment only". Hành động nhiều nhịp thuộc motion prompt, không thuộc khung đầu.
- **Nền là một nơi thật, kể cả khi tối.** "Bóng tối" = cảnh đêm/thiếu sáng ở bối cảnh của dự án, không phải nền đen trơn. *Căn cứ:* 2A —
  4 shot nền đen bị người dùng chê. **Mốc nổi tiếng của game phải giống game:** gửi ảnh mốc thật (vai trò "chi tiết / mốc" ở Kho — ảnh
  render 3D ngang tầm mắt hoặc ảnh chụp trong game) cho shot cận/trung; chỉ tả bằng chữ thì model vẽ một tháp đồng hồ châu Âu chung chung
  (2A — người dùng: "chưa giống tháp đồng hồ trong Free Fire"). Ảnh chụp từ trên cao/bản đồ không bao giờ làm nền (R7).
- **Chừa khoảng trống cho chữ** khi Đạo diễn/Editor báo có chữ trên màn hình (thông báo game, phụ đề ở dải dưới vùng an toàn).
- Toàn cảnh đủ dài để đọc (≥ 1,5 s); cận mặt dành cho im lặng.
### Q3. Chuyển động máy
- Tĩnh = đứng ngoài; đẩy vào = lại gần cảm xúc; lùi ra = tiết lộ/buông; bám theo = đồng hành (chạy). Một chuyển động chính mỗi shot.
- Shot ngắn hơn clip tối thiểu của model được gen dài rồi cắt → **hành động chính phải xảy ra sớm** trong clip.
### Q4. Giới hạn model (luật đo được — code kiểm, `data/provider_rules.json`)
- Kling 3.0 Omni: clip 3–15 s; multi-shot mỗi prompt ≤ 512 ký tự; chỉ ảnh đầu nhóm bám nhân vật (shot sau trong nhóm dễ lệch — GĐ6 R4).
- Seedance: 4–15 s (2.5: tới 30 s); không trộn khung đầu với ảnh tham chiếu; chặn "giống người thật/bản quyền".
- GPT Image 2.5 Sunburst: nhận bảng thiết kế nhiều góc; **không ghi tuổi dưới 18** (bị từ chối — code lọc).
### Q5. Nhân vật đúng thiết kế trong khung
- Ảnh tham chiếu chọn theo cỡ cảnh (cận → ảnh cận/chính diện; toàn → toàn thân); ảnh chuẩn chính diện là màu chuẩn. Mô tả trong prompt chỉ
  nhắc nét nhận diện (tóc, màu trang phục chính, phụ kiện đặc trưng) — **đúng như ảnh**, không suy đoán chiều (trái/phải, xuôi/ngược)
  khi chưa nhìn ảnh.

## Tầng 4 — Ưu tiên khi xung đột
Ý đồ của Đạo diễn > rõ không gian (ai ở đâu) > giới hạn model > ít clip/tiền > đẹp. Hy sinh gì thì ghi `tradeoffs`.

## Tầng 5 — Tự rà
- Mỗi cảnh có bao nhiêu vị trí máy, có vượt trục không? Shot nào đứng một mình mà có thể gộp vào một vị trí máy sẵn có?
- Khung đầu có đúng MỘT khoảnh khắc không? Có chỗ cho chữ khi cần không?
- Có shot thoại nào nhìn rõ mặt người đang nói không?
