# Phân tích trước khi làm tiếp (2026-09-23): nhất quán ảnh ↔ prompt · Director cho Free Fire · Lip Sync tiếng Việt · Storyboard 3D

Chỉ phân tích, **chưa sửa code**. Nguồn: code hiện tại (`main` @ `cc3198c`), User Guide ClipAI (bản 07/08/2026, thư mục `Get this Skill to Claude/Tài nguyên tham khảo…`), skill `clipai 1.3.1` / `deepix 1.4.1`, gọi thử API ClipAI **chỉ đọc** bằng token của bạn (không tạo gì, không tốn credit), đọc mã JavaScript công khai của web ClipAI, và thử phân tích 1 video Free Fire nội bộ trên máy.

## Tóm tắt

| Mục | Kết luận ngắn | Làm được bằng API? |
|---|---|---|
| 2. Ảnh ↔ prompt | Đang có 3 "neo" nhận dạng (mô tả chữ, Character Lock, ảnh tham chiếu) nhưng mỗi bước dùng một phần khác nhau; ảnh cảnh chỉ là **trạng thái đầu** của một cảnh dài; Kling không nhận ảnh nhân vật. Cần **một "hợp đồng shot" duy nhất** sinh ra cả prompt ảnh, prompt video và tiêu chí QC. | Có (trừ Kling Elements) |
| 3. Director cho Free Fire | Kiến thức đạo diễn chung đã có; thiếu **ngữ pháp dựng riêng của Free Fire** và thiếu **lớp phân shot**. Có thể học từ video FF bằng cách cắt shot tự động + Claude gắn nhãn. **Director Workspace của ClipAI không có trong API** (chỉ trên web). | Nghiên cứu: có · Director ClipAI: không |
| 4. Lip Sync | Có trên web ClipAI (`/kling/lip-sync`), **token API bị từ chối**. Chính thức chỉ đảm bảo **tiếng Trung, tiếng Anh**; 1 người; clip 2–10s; mặt rõ suốt clip. Có chế độ **tải file âm thanh lên** → có thể thử giọng Việt tự tạo, nhưng không được đảm bảo. | Không (chỉ web) |
| 5. Storyboard 3D | **Director Workspace của ClipAI chính là mô hình Blender bạn mô tả** (nền 360°, camera có FOV, tối đa 10 nhân vật có tư thế, khung 9:16, timeline keyframe xuất MP4 ≤30s) và **nhập/xuất cấu hình bằng file JSON** → Dashboard có thể tự sinh file dựng sẵn để bạn mở trên web. | File JSON: có · Render: chỉ web |

---

## Mục 2 — Phối hợp ảnh và prompt để đồng nhất cảnh + nhân vật

### Hiện trạng (đọc từ code)
- **Nhận dạng nhân vật nằm ở 3 nơi:** mô tả chữ trong Character Bible, Character Lock (bắt buộc giữ / được đổi / cấm lệch), ảnh tham chiếu trong kho tài nguyên.
- **Ảnh cảnh (Deepix):** prompt ảnh do Director viết ở Bước 1 + `Blocking` + Lock; gửi kèm theo thứ tự: ảnh layout (nếu dựng storyboard) → ảnh nhân vật/bối cảnh → ảnh đã duyệt của cảnh trước cùng nhóm; mỗi ảnh có câu ghi vai trò ("Image 1 is the LAYOUT…", "Images 2/3 show KELLY…") — `core/runner.py::ImageRunner`, `core/assets.py::reference_note`.
- **Prompt video:** Claude viết ở Bước 3, **có nhìn ảnh đã duyệt** (`llm_runner` gửi ảnh cảnh), viết theo cú pháp của model (Seedance gọi @Image).
- **Video:** mọi model bắt đầu từ ảnh đã duyệt. **Seedance** nhận thêm ảnh nhân vật (tối đa 8, bản 2.5 là 29). **Kling chỉ nhận khung đầu** (`core/adapters/clipai.py`, `image_list: first_frame`).

### Chỗ gây lệch
1. **Một ảnh cho cả một cảnh dài.** Ảnh là trạng thái đầu; cảnh 2 của Kenta có 5 nhịp hành động trong 15s → model tự bịa phần giữa/cuối, nhân vật và vị trí dễ trôi.
2. **Prompt ảnh và prompt video được viết ở hai lúc, bởi hai lần gọi Claude, từ hai nguồn** (JSON Director vs. ảnh đã gen) → hành động/vị trí mô tả có thể không khớp.
3. **Không có khung cuối.** ClipAI hỗ trợ khung đầu + khung cuối (User Guide mục 4.1 "Frames"), code mới có thử nghiệm `last_frame` đang tắt.
4. **Mỗi lớp dùng một phần nhận dạng khác nhau:** Deepix nhận ảnh + Lock, Seedance nhận ảnh, Kling không nhận gì ngoài khung đầu, QC video so với ảnh + Lock.
5. **Kling Elements** (nhân vật nhiều góc + gắn giọng, cách Kling giữ nhân vật) có trên web (`/kling/element-create`, lệnh gen video web gửi kèm `element_id`) nhưng **token API bị từ chối** (thử `element-list`: `code 1102 LoginErr`).
6. Chưa có QC so **các clip với nhau** (chỉ có cho ảnh), chưa cân màu khi dựng.

### Đề xuất: "hợp đồng shot" (shot contract)
Một bản ghi duy nhất cho mỗi shot, Director sinh ra, mọi bước đọc chung:

| Trường | Dùng cho |
|---|---|
| cỡ cảnh, góc máy, chuyển động máy, thời lượng 2–6s | prompt ảnh, prompt video, chọn model |
| **khung đầu** (ai ở đâu, tư thế, hướng nhìn) | prompt ảnh khung đầu, layout/storyboard |
| **khung cuối** (khi shot có đổi trạng thái) | ảnh khung cuối → video khung đầu + cuối |
| hành động trong shot (1 động từ chính) | prompt video |
| danh sách tài nguyên + vai trò (@Hình1 = diện mạo Kenta, @Hình2 = bối cảnh…) | cùng một bảng nhãn cho Deepix và Seedance |
| điều QC phải kiểm (từ Lock + khung đầu/cuối) | QC ảnh, QC video |

Kèm theo: các shot cùng nhóm cảnh dùng chung một model; QC đồng bộ cả bộ clip; cân màu khi dựng; **hỏi team ClipAI mở API cho Kling Elements** (hoặc dùng Seedance cho shot có nhân vật chính khi chưa có).

---

## Mục 3 — Director học cách dựng video Free Fire

### Nguồn tham khảo chính thức
- Kênh [Garena Free Fire Official](https://www.youtube.com/@FreeFire_Official) (~10 triệu người theo dõi), [Garena Free Fire Global](https://www.youtube.com/@GarenaFreeFireGlobal/shorts), [Garena Free Fire VN](https://www.youtube.com/c/GarenaFreeFireVN/featured), [Garena Free Fire EU](https://www.youtube.com/channel/UC5GnithsB1ZyfG5KhVzpSBQ).
- Phim CGI "Official Film" (ví dụ [New Look, New Chapter](https://m.youtube.com/watch?v=gQ-D7ZPWp64), [Battle In Style](https://www.youtube.com/watch?v=NNAHeKhucSE)), loạt **Kelly Show** (tiểu phẩm hài với nhân vật game — gần nhất với kịch bản "Kenta cướp kill"), loạt **Project Crimson** (Origins / Technology / Trail of Destruction), anime Free Fire của KADOKAWA với Kelly là nhân vật chính ([Crunchyroll](https://www.crunchyroll.com/news/latest/2025/7/5/garena-free-fire-anime-teaser-visual-trailer), [Anime News Network](https://www.animenewsnetwork.com/news/2025-07-04/garena-free-fire-anime-unveils-trailer-visual-staff/.226311)).

**Hạn chế đã gặp:** máy này bị chặn trang youtube.com (cả trình duyệt tích hợp và tải trực tiếp đều trả 404; chỉ đọc được RSS danh sách video). Muốn phân tích phim, cần file video (bạn tải về, hoặc cho phép dùng công cụ tải trên máy khác).

### Thử nghiệm: phân tích 1 video Free Fire nội bộ (`D:/2026/OB55/Tình huống sử dụng Kenta đổi góc…mp4`)
Cắt shot tự động bằng ffmpeg (ngưỡng đổi cảnh 0,3) + xem 1 khung/shot:

| Thông số | Kết quả |
|---|---|
| Độ dài / khung | 38,8s · 1080×1920 (dọc) · 60 fps |
| Số shot | ~12 (điểm cắt 1,1 · 2,0 · 6,7 · 7,0 · 17,9 · 21,7 · 27,1 · 27,4 · 30,5 · 32,3 · 35,9 · 37,5s) |
| Nhịp | phần lớn 1–5s; 1 đoạn gameplay liền 10,9s |
| Cấu trúc | **Mở** (0–2s): Kenta toàn thân kiểu sảnh chờ + tiêu đề lớn → **Thân**: gameplay **góc thứ ba sau lưng** (camera game), mỗi đoạn có chữ chương vàng ("TẤN CÔNG BẤT NGỜ", "RÚT LUI AN TOÀN") + giao diện game (Monster Kill, bảng hạ gục) → **Kết** (34–39s): Kenta trình diễn kiếm, trung/cận, câu hỏi kêu gọi + ngày cập nhật |

So với bản dựng thử của chúng ta (56s, **3 shot** 15/15/26s, không chữ chương, không góc game): nhịp chậm gấp ~4 lần và thiếu "chất" Free Fire (góc thứ ba sau lưng, giao diện game, chữ chương).

### Đề xuất
1. **Thư viện ngữ pháp dựng Free Fire** (`knowledge/ff_directing.md`): từ 10–20 video tham khảo (CGI Official Film, Kelly Show, video kỹ năng), dùng công cụ sẵn có (`core/video_analysis.extract_frames` + cắt shot ffmpeg) → Claude gắn nhãn mỗi shot (cỡ cảnh, góc, chuyển động, vai trò: hook / hành động / phản ứng / chèn chi tiết / kết) → thống kê nhịp theo từng thể loại → 3 khuôn mẫu: **video kỹ năng**, **tiểu phẩm hài**, **phim điện ảnh CGI**.
2. **Lớp phân shot cho Director** (đã nêu trước): mỗi cảnh → nhiều shot theo khuôn mẫu thể loại; kiểm tra nhịp và độ đa dạng cỡ cảnh.
3. **Góc "camera game"** thành một lựa chọn cỡ cảnh riêng (góc thứ ba sau lưng, hơi cao) cho shot gameplay.
4. Tính năng "tra cứu Director của ClipAI" bằng API: **không làm được** — Director Workspace chạy trong trình duyệt, không có endpoint cho token API (xem mục 5 cho cách phối hợp qua file JSON).

---

## Mục 4 — Lip Sync của ClipAI và tiếng Việt

### Tìm được
- **User Guide mục 13:** Lip Sync có trên thẻ video hoặc tải video lên. Nhập **chữ** (chọn giọng, tốc độ, cảm xúc) hoặc **tải file âm thanh**. Giới hạn: video 2–10s, .mp4/.mov, ≤100MB, chỉ 720p/1080p; âm thanh 2–10s, .mp3/.wav/.m4a/.aac, ≤5MB; **mặt phải liên tục rõ trong khung**; **chỉ đảm bảo tiếng Trung và tiếng Anh**; **chỉ 1 người nói**.
- **Mã web:** endpoint `/kling/lip-sync`, hai chế độ: nhập chữ (giọng Kling, trường `voice_language` mặc định `"zh"`) và `audio2video` (tải âm thanh lên qua `/kling/upload`).
- **API bằng token:** các endpoint không có trong tài liệu đều trả `LoginErr` → **không gọi được từ Dashboard**.

### Tiếng Việt khả thi đến đâu
- Chế độ **tải âm thanh** cho phép dùng giọng Việt do chúng ta tạo (ElevenLabs) → khẩu hình có thể khớp tạm, nhưng ClipAI **không cam kết** chất lượng với tiếng Việt → phải thử.
- Điều kiện khớp với phân shot: chỉ dùng được cho shot **1 người nói, cận/trung cận, mặt luôn trong khung, ≤10s** — cảnh đối thoại 2–3 người như hiện nay không dùng được.
- **Giọng Việt hiện có (gọi API thật, chỉ đọc):** 118 giọng chính thức (ElevenLabs); chỉ **5 giọng khác nhau** ghi hỗ trợ `vi` (4 nam: Xinghe Jiang, Austin, Ethan Zhang, Mark; **1 nữ**: Arabella), **không giọng nào là giọng gốc Việt**. Web có **Voice Design** (`/sound/voice-actors/design`, mô tả ≥20 ký tự + câu mẫu ≥100 ký tự, `eleven_v3`) và **Voice Clone** — cũng chỉ trên web; "giọng tùy chỉnh / thư viện giọng theo game" đang được phát triển.

### Đề xuất
1. Thử tay trên web (cần bạn đồng ý, tốn credit): 2 clip 1 người nói ~5s — (a) Lip Sync bằng chữ tiếng Việt, (b) Lip Sync tải giọng Việt ElevenLabs lên → nghe/xem và ghi kết quả vào `docs/api_notes.md`.
2. Tạo 3 giọng Việt (Kelly, Maxim, Kenta) bằng Voice Design trên web → chúng xuất hiện trong danh sách giọng để Dashboard chọn.
3. Dashboard: chỉ đề xuất giọng có `vi`; đánh dấu shot nào đủ điều kiện Lip Sync.
4. Nhờ team ClipAI: mở API (token) cho Lip Sync, Kling Elements, Voice Design; hỏi lộ trình hỗ trợ tiếng Việt.

---

## Mục 5 — Storyboard 3D kiểu Blender (khung camera trong không gian 3D)

### Hiện trạng
Previz hiện là **dựng 2D**: đặt hình người (ma-nơ-canh màu) lên **một ảnh nền phẳng** theo phối cảnh Claude đọc được; mỗi cảnh một layout; cần ảnh bối cảnh trong kho; chưa chạy thật.

### Director Workspace của ClipAI (User Guide mục 10) — đúng mô hình bạn mô tả
- Nền **360°** (tải lên hoặc "To panorama" tự tạo từ ảnh thường), xoay/phóng nền, lưới mặt đất.
- **Camera**: vị trí, điểm nhìn, roll, **FOV**; nhiều camera; "Camera View" = khung đầu ra; tỉ lệ 21:9 → **9:16**.
- **Nhân vật** (≤10): vị trí/xoay/tỉ lệ + **tư thế** (đứng, đi, chạy, ngồi, ngồi xổm… và chỉnh từng khớp).
- **Timeline keyframe** (1–30s, 24 fps) cho camera và nhân vật → xuất **MP4 tham chiếu** (không kèm tiếng) cho Seedance/Kling; xuất ảnh tham chiếu (giữ/bỏ nhãn tên).
- **Nhập/xuất cấu hình bằng file JSON** (`clipai-director-<thời gian>.json`, `version: 1`: nhân vật `position/rotation/scale/posePresetId/poseControls`, camera `position/target/roll/fov`, nền `panoramaRotation/Scale/OffsetY`, `viewportAspect`, hoạt ảnh `durationSeconds ≤30, fps 24, keyframes`).

### Phương án
| Phương án | Cách làm | Ưu | Nhược |
|---|---|---|---|
| **A. Sinh file JSON cho Director ClipAI** (đề xuất trước) | Dashboard chuyển "hợp đồng shot" → file JSON (camera, vị trí, tư thế, keyframe) → bạn mở trên web, chọn nền 360°, chỉnh → xuất ảnh/MP4 tham chiếu → tải lại Dashboard dùng làm khung đầu / video tham chiếu chuyển động | Dùng công cụ 3D có sẵn, không phải xây; ra đúng định dạng model hiểu | 1 bước làm tay trên web mỗi shot; schema chưa có tài liệu → **cần bạn xuất 1 file mẫu** để khớp |
| B. Blender chạy nền (bpy) | Script dựng cảnh 3D, đặt camera theo shot, render ảnh/clip previz | Tự động hoàn toàn | Cần mô hình 3D map/nhân vật Free Fire (Meshy/nội bộ), nặng, lâu |
| C. 3D trong trình duyệt (three.js) ngay trong Dashboard | Tự xây trình dựng như Director ClipAI | Không phụ thuộc web ngoài | Tốn công nhất, trùng tính năng ClipAI đã có |

**Đề xuất:** A trước (sau khi có lớp phân shot), B để nghiên cứu dần (`docs/RESEARCH_3D_PREVIZ.md` đã có hướng này).

---

## Thứ tự đề xuất

1. **Lớp phân shot + hợp đồng shot** (mục 2 + 3): nền cho mọi thứ còn lại. Không tốn credit.
2. **Thư viện ngữ pháp dựng Free Fire** (mục 3): cần bạn cung cấp 10–20 file video tham khảo (YouTube bị chặn trên máy này) — có thể bắt đầu với thư mục `D:/2026/OB55` và `D:/2025`.
3. **Sinh file JSON Director cho ClipAI** (mục 5): cần 1 file JSON bạn xuất từ Director Workspace làm mẫu.
4. **Thử Lip Sync + Voice Design tiếng Việt trên web** (mục 4): cần bạn đồng ý (tốn credit) và nghe kết quả.
5. **Hỏi team ClipAI** mở API cho Kling Elements, Lip Sync, Voice Design, Director.

## Việc cần bạn
- Chọn/duyệt thứ tự trên.
- Gửi 1 file cấu hình xuất từ Director Workspace (bất kỳ cảnh nào).
- Chỉ thư mục video Free Fire tham khảo được dùng (và có được gửi khung hình cho Claude phân tích không).
- Đồng ý thử Lip Sync / Voice Design trên web (tốn credit).
