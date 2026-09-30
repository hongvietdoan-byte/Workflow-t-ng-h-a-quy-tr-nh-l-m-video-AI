# Ảnh + video + âm thanh tham chiếu: gửi thế nào cho model hiểu đúng (Director · DP · người viết prompt video)

Căn cứ: tài liệu chính thức Kling Omni (API mới + bản cũ ClipAI dùng), hướng dẫn Kling 3.0 Omni / O1, BytePlus Seedance 2.5, skill ClipAI
1.3.1 + bộ tối ưu prompt Seedance 2.5 chính thức (`sd25-pe`), và lần thử #11 (30/09). Chi tiết + nguồn: `docs/NGHIEN_CUU_PROMPT_THAM_CHIEU_2026-09-30.md`.
Kết quả thử thật ghi ở mục cuối — **mục đó thắng phần suy ra từ tài liệu** khi hai bên khác nhau.

## Cách nghĩ (theo thứ tự ưu tiên)

1. **Mỗi tài sản gửi đi phải có đúng một việc, và prompt phải gọi tên nó.** Vì sao: model coi ảnh / video / chữ đều là "prompt"; tài sản
   không được gọi tên thì bị dùng lỏng hoặc bị bỏ (thử #11: video kỹ năng gửi kèm nhưng prompt Kling không gọi `<<<video_1>>>` → lốc mờ, ngắn).
   Cách gọi: Kling (qua ClipAI) `<<<image_1>>>`, `<<<element_1>>>`, `<<<video_1>>>`; Seedance `@Image 1`, `@Video 1`, `@Audio 1` (hoặc
   `@图片1`… — giữ một kiểu trong một prompt). Số thứ tự = thứ tự tài sản gửi đi.
2. **Nói rõ lấy gì VÀ không lấy gì từ mỗi tài sản.** Vì sao: ảnh nhân vật kéo theo nền, video kéo theo người, cảnh, máy quay, chữ giao
   diện. Mẫu: "@Video 1 chỉ dùng cho hình dạng, màu, độ trong, thứ tự và nhịp của hiệu ứng kỹ năng; không lấy người, trang phục, cảnh, máy
   quay, chữ giao diện". (Seedance 2.5 chính thức: "不采用视频中的人物身份、服装和场景".)
3. **Chọn model theo việc cần tham chiếu, không theo thói quen.**
   - Video để chép **hiệu ứng / lực va chạm / phong cách chuyển động** → **Seedance 2.5** (tài liệu có ví dụ "referring to the impact of
     @Video3"; ≤ 10 video, tổng ≤ 30 s).
   - Video để chép **động tác cơ thể** → Kling mẫu chính thức "Animate the character in <<<image_1>>> with the same motion as the
     character in <<<video_1>>>".
   - Video để chép **đường máy quay** → Kling "Take <<<image_1>>> as the start frame. Generate a new video following the camera movement of
     <<<video_1>>>".
   - Kling `feature` **không** được tài liệu hứa chép hiệu ứng — đừng giao việc đó cho Kling.
4. **Đã có video mang hành động thì không tả lại từng chi tiết.** Vì sao: tài liệu Seedance: "重复改写可能与素材本身冲突" — chữ tả lại có thể
   kéo ngược video. Chỉ ghi **thứ tự giai đoạn** (để khớp video) + trạng thái đầu / cuối. Khi KHÔNG có video thì mới tả kỹ bằng chữ (hồ sơ kỹ năng).
5. **Không nhồi danh sách "cấm".** Vì sao: tài liệu Seedance: không thêm câu cấm không liên quan; tài sản mâu thuẫn thì **thay tài sản**. Giữ
   tối đa vài điều cấm thật sự hay xảy ra (vd "katana stays in its scabbard"), đặt ở câu khẳng định khi được.
6. **Nhiều nhân vật: mỗi người một dòng ánh xạ, không gộp.** "Kelly tương ứng @Image 2, chỉ lấy mặt, tóc, trang phục" / "Kenta tương ứng
   @Image 3 …" + "ba người không đổi mặt, trang phục, vị trí, lời thoại cho nhau". Cấm câu gộp "Kelly và Kenta tham chiếu @Image 2, @Image 3".
   Một ảnh chỉ định danh một người (ảnh có 2 người không dùng làm ảnh định danh).
7. **Vị trí người neo vào vật cố định** (sau tường keo, ở cửa nhà gỗ, cạnh thùng) — không chỉ viết trái / phải khung. Vì sao: Seedance
   chính thức "不要只写屏幕左侧或右侧"; vật cố định giữ được khi máy đổi góc.
8. **Thoại nhiều người:** mỗi lượt ghi người nói + lời, người khác "ngậm miệng lắng nghe"; giọng mẫu `@Audio N` gắn từng người.
9. **Khung đầu:** Kling dùng ảnh `first_frame`. Seedance: nếu còn gửi ảnh nhân vật / video thì dùng chế độ tham chiếu và viết câu vai trò
   nguyên văn "@Image 1 làm khung đầu (作为首帧)" — không làm yếu thành "tham khảo bố cục". Khung cuối vẽ riêng hay trôi nền (thử #11) → chỉ dùng
   khi chắc cùng khung hình.
10. **Khi vượt giới hạn: chia shot, không nhồi.** Shot hiệu ứng (người dùng kỹ năng + video kỹ năng) tách khỏi shot phản ứng nhiều người.
11. **Video tham chiếu kéo theo cả phong cách, góc máy và nơi chốn của nó** dù đã ghi "không lấy" (thử T3 30/09: nơi chốn pha giữa ảnh Kho
    và ngôi làng trong video; máy đứng sau lưng như video thay vì "ngang từ bên"). Vì vậy: nơi chốn quan trọng → luôn có **khung đầu** (ảnh
    đã duyệt đúng nơi, đúng góc) — khung đầu giữ nơi chốn và máy tốt hơn chữ (T1 giữ đúng cảnh nhờ khung đầu). Phong cách in-game của video game
    lại là điều ta muốn.
12. **Nhiều người trong khung dọc 9:16: mỗi người phải có cỡ và chỗ rõ trong khung**, không chỉ chỗ trong cảnh. Vì sao: T3 để Maxim "ở cửa nhà"
    trong toàn cảnh → Maxim chỉ còn đầu tí hon sau tường, còn mọc thêm người lạ. Với ≥ 3 người: (a) vẽ **khung đầu có đủ 3 người** trước (model
    ảnh xếp chỗ tốt hơn model video) rồi mới làm clip, hoặc (b) chia shot (hiệu ứng / phản ứng). Không để người thứ ba ở hậu cảnh xa.

## Giới hạn cứng (tài liệu — code kiểm trước khi gửi)

| | Kling 3.0 Omni (qua ClipAI) | Seedance 2.5 |
|---|---|---|
| Ảnh tham chiếu | ảnh + element nhiều ảnh ≤ 7; **có video ≤ 4**; có khung đầu → element ≤ 3 | ≤ 30 ảnh (khuyên 1–8 chủ thể) |
| Video | 1 đoạn, **3–15,5 s**, cạnh **700–4553 px**, 24–60 fps, SAR 1:1 (ClipAI), có video thì không âm thanh gốc | ≤ 10 đoạn, mỗi đoạn 2–30 s, tổng ≤ 30 s, 407 696–8 295 044 điểm ảnh, 24–60 fps |
| Nhiều nhân vật | **element** (tối đa 4 ảnh / người, tạo trên web ClipAI) | mỗi người một dòng ánh xạ; ảnh qua Kho chủ thể nếu bộ lọc người thật chặn |
| Giá | có video × 1,5 | có nguồn giá chưa chính xác (× 1,25 dự phòng) |
| Bẫy | không gọi tên tài sản = dùng lỏng | chữ "add / remove / replace / change / continue / extend" có thể biến thành **sửa / kéo dài video** |

## Cảnh 3 nhân vật — quyết định nhanh

- Có hiệu ứng kỹ năng cần chép từ video → Seedance 2.5: khung đầu + 3 ảnh người + 1 video kỹ năng (+ ≤ 3 giọng mẫu) — trong giới hạn.
- Không hiệu ứng, cần giữ mặt 3 người → Kling + 3 element (khi đã có element) hoặc Seedance 2.5 như trên.
- Kling + khung đầu + 3 người + video kỹ năng = **vượt giới hạn** (≤ 4) → chia shot.

## Kết quả thử thật (cập nhật sau mỗi lần thử)

- **2026-09-30 T1 — Seedance 2.5, 5 s, chế độ tham chiếu: khung đầu (câu "@Image 1 is the first frame") + ảnh Kenta + video kỹ năng 3,2 s
  (@Video 1 chỉ cho hiệu ứng), prompt không tả lại chi tiết:** qua bộ lọc người thật (ảnh Kenta in-game không đánh dấu); cảnh + katana + lưỡi
  hologram giữ đúng; **hiệu ứng gần game nhất tới giờ** — vòng gió rõ trên đất, màng lốc mờ rất lớn, vệt gió xoáy bay tới tường keo. Thứ tự hơi
  khác (vòng đất trước màng lốc); lưỡi biến mất sớm. → **Cách chuẩn cho shot kỹ năng.**
- **T2 — Kling std 3 s, khung đầu + ảnh Kenta (không type) + video, prompt gọi tên `<<<image_1>>>`, `<<<image_2>>>`, `<<<video_1>>>` theo mẫu
  "Animate … with the same motion … as in <<<video_1>>>":** hiệu ứng **rõ hơn hẳn** lần không gọi tên (vòng cung xanh ngọc sáng quét quanh
  người, gió bay tới tường) nhưng to / đậm hơn game, gió đi sát đất. Gọi tên tài sản có tác dụng thật; Kling vẫn kém Seedance ở việc chép hiệu ứng.
- **T3 — Seedance 2.5, 5 s, 3 người (ảnh nơi chốn + Kelly + Kenta + Maxim, mỗi người một dòng) + video hiệu ứng, không khung đầu:** Kenta +
  hiệu ứng + tường keo đúng, Kelly đúng đồ và chỗ (núp sau tường); **Maxim hỏng** (đầu tí hon sau tường, thêm người lạ); nơi chốn và máy bị
  video kéo (luật 11, 12).

- 2026-09-30 thử #11 vòng 1–3 (Kling std 3 s): khung đầu + khung cuối → hiệu ứng tả bằng chữ sai (luồng phụt lên, lốc đặc), nền trôi khi khung
  cuối vẽ lại; + video kỹ năng (feature, prompt KHÔNG gọi `<<<video_1>>>`) → cảnh giữ, katana / lưỡi đúng, hướng gió đúng, **lốc mờ, ngắn**;
  shot 2 thừa tấm xanh trên đất. ClipAI từ chối video < 3 s, < 700 px, SAR ≠ 1:1.
