# Seedance — cách viết motion prompt (image-to-video, ảnh duyệt = khung hình đầu)

Nguồn: tài liệu chính thức đi kèm skill Clip AI 1.3.1 (`seedance-2.0-prompt-optimizer.md`, `seedance-2.5-prompt-optimizer.md`, bản 2.5 là `sd25-pe` v0.1.0), chắt lọc cho pipeline này. Áp dụng khi `video_model` là seedance (2.0, 2.0-fast, 2.5). **Không** dùng cho Kling.

## Bối cảnh của pipeline
- Mặc định mỗi cảnh = 1 ảnh đã duyệt làm **khung hình đầu** (`first_frame`) + 1 motion prompt. Khi shot có thêm ảnh nhân vật, video (hiệu ứng kỹ năng, động tác) hoặc giọng mẫu: theo `knowledge/reference_assets_prompting.md` (mỗi tài sản một vai trò, gọi tên @Image / @Video / @Audio, khung đầu bằng câu vai trò — 30/09).
- Chọn **một nhiệm vụ duy nhất**: sinh video từ khung hình đầu. Không trộn với sửa/nối dài video.
- Độ dài (`duration_sec`) là tham số API, **không viết "tạo video N giây" vào prompt**. Không tạo mốc "0-5 giây" trừ khi thật sự cần điều khiển nhịp.

## Giới hạn theo model (dùng để lập kế hoạch, không viết vào prompt)
| Model | Độ dài clip | Prompt tối đa | Ghi chú |
|---|---|---|---|
| Seedance 2.0 | 4–15 giây | 4000 ký tự | Ngắn gọn thì tập trung hơn; prompt quá dài dễ "lạc" |
| Seedance 2.0 Fast | 4–15 giây | 4000 ký tự | Giảm mật độ sự kiện: 1 cảnh, 1 chủ thể chính, 1 hành động chính, ít đổi góc |
| Seedance 2.5 | tới 30 giây | 5000 ký tự | Clip dài → chia theo "giai đoạn" (xem dưới) |

## 10 nguyên tắc
1. **Giữ ý định**: không đổi nhân vật, số lượng, đạo cụ, bối cảnh, nhân quả, kết quả cuối của cảnh.
2. **Ngắn gọn mặc định**: mỗi thông tin chỉ nói một lần. Cảnh đơn giản = **một đoạn văn tự nhiên**. Bỏ lặp lại về phong cách, chất lượng, nhất quán.
3. **Ảnh đã cố định ngoại hình** — chỉ nêu điều ảnh không nói: chuyển động, camera, ánh sáng thay đổi, trạng thái cuối. Đừng mô tả lại mặt/tóc/trang phục (trừ khi cần chống trôi đặc điểm dễ đổi).
4. **Một sự kiện hoàn chỉnh** tốt hơn nhiều sự kiện dở dang. Cắt trước: hành động lặp, cảnh phụ, chi tiết trang trí.
5. **Sự kiện phải khớp thời lượng**: 4–5 giây = 1 hành động chính + 1 chuyển động camera. Muốn dài hơn: kéo dài quá trình (ánh mắt, hơi thở, phản ứng, dừng), **không thêm người/tình tiết/kết cục mới**, không lặp cho đủ giờ.
6. **Hành động cụ thể**: bộ phận cơ thể, hướng, tốc độ, lực, điểm tiếp xúc, trạng thái cuối. Giữ trọng lượng, quán tính, tiếp đất hợp lý. Vật cầm/đưa: chỉ có một, sau khi đưa người cũ không còn cầm.
7. **Camera có chủ thể**: theo ai, bắt đầu ở cỡ cảnh/vị trí nào, hướng và tốc độ di chuyển, kết ở bố cục nào. Không chồng nhiều chuyển động camera xung đột trong một cảnh. Không viết thuật ngữ trơ trọi (vd "dolly") mà không nói tác dụng lên chủ thể.
8. **Cảm xúc → dấu hiệu nhìn thấy**: *nguyên nhân thấy được → phản ứng tức thì → thay đổi dần (ánh mắt, chân mày, khóe miệng, hơi thở, tay, tư thế) → biểu hiện cuối*. Chọn 2–3 dấu hiệu rõ nhất, không nhồi hết.
9. **Không "gói ràng buộc" tự động**: không thêm 8K, ultra-HD, no watermark, no logo, no flicker, no deformation, no subtitles… Lỗi thật của cảnh (tay, mặt) chỉ xử lý bằng cách mô tả **tích cực** điều mong muốn.
10. **Không bịa**: không thêm nhân vật, đạo cụ chính, lời thoại, cốt truyện, kết cục chưa có trong cảnh. Không đoán chữ trên biển/màn hình (prompt không đảm bảo được chữ chính xác; dùng hậu kỳ).

## Negative prompt
API Clip AI **không có trường negative prompt** cho Seedance (chỉ gửi nếu `CLIPAI_NEGATIVE=append`, khi đó nối "Avoid: …"). Vì vậy: viết điều mong muốn theo hướng tích cực ("bàn tay giữ nguyên năm ngón, tư thế tự nhiên") thay vì liệt kê điều cấm. Trường `negative_prompt` trong JSON có thể để ngắn hoặc trống.

## Cấu trúc gợi ý (khung hình đầu → sự kiện → camera → kết)
```
[Khung hình đầu định nghĩa bố cục, tư thế, ánh sáng lúc bắt đầu.] <Một sự kiện liên tục: hành động cụ thể theo thứ tự>. Camera <theo chủ thể nào, từ đâu, hướng/tốc độ, kết ở đâu>. <Trạng thái cuối nhìn thấy được>.
```
Ví dụ (5 giây, cảnh đêm rừng):
```
Từ khung hình đầu, Lyra đứng giữa sương mù rừng Elder, ánh trăng lạnh. Cô chậm rãi quay đầu về phía tiếng động bên trái, tay phải đặt lên chuôi kiếm, hơi thở tạo làn hơi mỏng. Camera đẩy vào chậm từ cỡ toàn thân đến cận nửa người, hơi rung tay cầm nhẹ. Kết cảnh: Lyra dừng lại nhìn thẳng về phía xa, sương trôi ngang phía sau.
```

## Clip dài (2.5, > 8–10 giây): dùng "giai đoạn", không mốc giây
```
Giai đoạn 1 — Bắt đầu: <trạng thái>. Sự kiện: <một thay đổi chính>. Kết: <trạng thái nhìn thấy>.
Giai đoạn 2 — Tiếp nối <trạng thái giữ>: <một thay đổi chính>. Kết: <...>.
Giai đoạn 3 — Sự kiện thu lại. Kết: <hình cuối>.
```
Số giai đoạn theo số sự kiện, không cố đủ 3. Chỉ dùng mốc giây (0-5s, 5-10s…) khi người dùng yêu cầu điều khiển nhịp; mốc phải liên tục, không chồng nhau; sự kiện quá dày thì giảm giai đoạn.

## Nhiều shot (chỉ khi kịch bản yêu cầu)
Seedance không dùng multi-shot có cấu trúc như Kling. Nếu cần: viết `Shot 1:`, `Shot 2:` trong cùng một prompt, thường 2–4 shot, mỗi shot một thay đổi trạng thái + một chuyển động camera. Cảnh đơn giản không chia shot.

## Camera & nhiếp ảnh
- Camera "hot" có thể viết thẳng: một-cú-máy, handheld, FPV, drone/aerial, hitchcock zoom, bullet time — nhưng **phải nói theo chủ thể nào và kết ở đâu**.
- Thuật ngữ hiếm/khó hiểu → giữ tên và **mở ra thành kết quả nhìn thấy**: "độ sâu trường ảnh nông" = chủ thể nét, hậu cảnh mờ dần; "follow" = camera cùng tốc độ chủ thể, nền kéo vệt ngược hướng; "rack focus" = nét chuyển từ A sang B; "vignette" = bốn góc tối dần, tâm sáng bình thường. Số tiêu cự/khẩu độ chỉ bổ sung.

## Âm thanh (pipeline mặc định tắt âm thanh video; nhạc/SFX làm ở Bước 5a)
Nếu sau này bật `generate_audio`: nhạc `(…)`, hiệu ứng `<…>`, lời thoại `{…}`, phụ đề `【…】`; nêu rõ ngôn ngữ thoại, gắn mỗi câu với người nói, người khác im lặng lắng nghe; cảnh không thoại: nói rõ miệng khép, không lời dẫn. Nếu dùng `<>` cho SFX thì đừng dùng `<>` cho tên nhân vật.

## Bổ sung từ tài liệu chính thức Seedance 2.5 (火山引擎 提示词指南, đọc 2026-09-29 — `research/craft/trung_quoc/PROMPT.md`)
- **Mốc thời gian theo model:** Seedance 2.0 / Fast chỉ theo **số shot** (`Shot 1:`), không theo mốc giây — #8 ghi "0–1.5 s" cho 2.0 và
  hành động bị trôi (lỗi 1.5). Seedance 2.5 theo mốc giây **nguyên**, liên tục, không nhảy cóc ("0–3 s… 3–7 s…"); không dùng mốc giây để
  ép số lần lặp động tác. Code clip nhóm: `seedance_refs.prompt(..., model=)` tự chọn.
- **Khung 4 phần khi có nhiều tư liệu:** (1) vai trò từng ảnh / video / âm thanh, đánh số **theo thứ tự nhân vật xuất hiện lần đầu** (lệch
  thứ tự dễ gán nhầm nhân vật); (2) một câu tóm tắt: ai, ở đâu, chuyện gì, phong cách; (3) diễn biến chia đoạn (số shot hoặc mốc giây như
  trên); (4) điều giữ suốt clip (máy, không khí, âm nền). Tác vụ 1 chủ thể, 1 hành động: chỉ cần phần 2–3.
- **Hành động khái quát, chi tiết 1–2 điểm nhấn;** không liệt kê từng động tác nhỏ trong shot ngắn (code gợi ý ⚠ khi 1 shot có ≥ 3 hành
  động lớn — `seedance_refs.busy_shots`).
- **Biểu cảm bằng câu mô tả**, không thành ngữ / nhãn trừu tượng. Từ cảm xúc quá mạnh ("cuồng nhiệt", "cực sốc", "furious", "ecstatic")
  dễ làm **mắt phát sáng bất thường** → dùng từ thường hơn; cảnh cảm xúc mạnh thêm "natural human eyes, no glowing eyes" (code tự làm ở clip
  nhóm khi cường độ ≥ 4).
- **Phủ định chỉ hỗ trợ cho phụ đề và âm thanh** — khác nguyên tắc 9 ở trên, nhưng chỉ khi cần: video **có sinh âm thanh** hoặc prompt có
  **câu thoại** (dễ tự sinh phụ đề). Khi đó: tách thoại theo khuôn `NHÂN VẬT (cảm xúc): "câu"`; cấm nhạc thì liệt kê hết từ đồng nghĩa
  (music, background music, BGM, score, melody, instruments…) và nhắc ở **đầu và cuối** prompt. Pipeline mặc định tắt âm thanh video → không
  thêm.
- **Việc phức tạp tách thành nhiều lần sinh đơn giản** rồi ghép ở dựng, không gộp nhiều loại tham chiếu + sửa + hiệu ứng vào một lần.
- **Ảnh tham chiếu không nét hơn đầu ra** (≈ 720p → cạnh dài ≤ 1280 px) để bớt vân nhiễu ở cỏ / lá / chi tiết dày (code: `REF_MAX_SIDE`).
- **Phân cảnh lưới (2.5):** chỉ tham khảo đại ý — nét đơn giản, < 15 ô, ít chữ; cần khớp chặt thì dùng "ảnh X đến Y là khung hình chính"
  ở câu đầu prompt.

## Checklist trước khi trả prompt
- [ ] Đúng một nhiệm vụ (từ khung hình đầu); không lẫn nối dài/sửa video
- [ ] Số nhân vật, đạo cụ, thứ tự sự kiện, kết quả không đổi so với cảnh gốc
- [ ] Một sự kiện chính, vừa với thời lượng; bản Fast còn đơn giản hơn
- [ ] Camera nói rõ chủ thể, điểm đầu, hướng, điểm cuối; không xung đột
- [ ] Không mô tả lại ngoại hình đã có trong ảnh; không gói ràng buộc chất lượng
- [ ] Không có tham số API (độ dài, tỉ lệ, độ phân giải) trong prompt
- [ ] Dưới giới hạn ký tự của model; không lặp ý
- [ ] Mốc thời gian đúng model (2.0 / Fast: số shot · 2.5: giây nguyên liên tục); hành động khái quát, 1–2 điểm nhấn
