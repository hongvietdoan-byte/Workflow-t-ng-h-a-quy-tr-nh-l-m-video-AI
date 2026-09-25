# Bàn giao 2026-09-25 (tối) — Tháp đồng hồ giống FF 90–100% + khớp môi (lip-sync)

> **Phiên sau đọc file này trước**, rồi `TODO.md` (📌 BÀN GIAO + mục 0), `docs/KE_HOACH_2026-09-25.md` (mục 0 = bảng tiến độ) và
> `docs/CHUAN_XAY_DUNG.md` (luật bắt buộc). Đọc xong file này là làm tiếp được, không cần đọc lại hội thoại cũ.

## 0. Người dùng vừa nói gì (nguyên ý)
> "khá ok rồi, nhưng có vẻ hình ảnh background sau lưng vẫn chưa chuẩn tháp đồng hồ đến 90-100%. Ngoài ra việc sync môi nói của nhân vật
> thì giải quyết như nào"

→ Video 0–20 s bản sửa (`data/projects/7/output/FINAL_VIDEO_sub_src.mp4`, dự án thử #7) được chấp nhận **"khá ok"**. Còn 2 việc:
**(A)** nền tháp phải giống tháp đồng hồ trong Free Fire 90–100%; **(B)** trả lời + làm thử cách khớp môi.
Người dùng **chưa** trả lời có chạy 2B (20–58 s của #6) hay không → vẫn coi là **chờ**, không tự chạy 2B.

## 1. Ngân sách đợt thử (dự án #7) — trạng thái lúc bàn giao
| Hạng mục | Đã dùng | Trần | Ghi chú |
|---|---|---|---|
| Tiền có giá (video + âm thanh) | ~$4,02 | $8 | còn ~$3,98 |
| Claude API | ~$0,26 | $1 | |
| Ảnh Deepix | **21** | 32 | +1 ảnh thử nền cố định (stage `plate_test`) phiên này; Deepix không trả giá qua API |
| Âm thanh | 15 | 25 | |
Luật giữ nguyên: gen lại ≤ 2 lần/shot, ước tính trước mọi lời gọi tốn tiền, không tự nâng trần (phải hỏi người dùng).

## 2. (A) Tháp đồng hồ 90–100%

### 2.1 Đã có trước phiên này
- Mô hình 3D: `D:\AI-Video-Pipeline\model 3D\free_fire_clocktower_3d_model_by_ffxn.glb`. Tọa độ gốc mô hình: thân tháp `Object_14`
  tâm (12,68; −31,13), thân z 25,85–44,65; quảng trường trên z ≈ 25,93, sân dưới ≈ 22,39. `render_plates` nâng mô hình +2,155 → dùng
  camera `"model_coords": true` (tự cộng phần nâng).
- Blender 5.0.1 bản **Microsoft Store** chạy nền qua `Invoke-CommandInDesktopPackage` (`core/plates3d.store_blender`, `_run_in_store`).
  Render 1 ảnh 1152×2048 EEVEE ~1,5–2 s, cả lượt ~11 s.
- Kho #263 (Tháp Đồng Hồ) có ảnh mốc 974 (detail), 975/976 (ngang mắt), 543/544 (từ trên). Pipeline gửi ảnh mốc làm **tham chiếu** cho shot
  cận/trung (`assets.location_landmark`) → ảnh sinh ra *giống kiểu* tháp nhưng model vẫn **vẽ lại** → người dùng thấy chưa đạt 90%.

### 2.2 Làm trong phiên này (có bằng chứng)
1. **Render nền đúng góc máy shot 4** (MS Kelly trước tháp): 2 camera
   - `shot4_ms`: vị trí [12,68; −12,5; 25,93+1,3], ống 32 mm; `shot4_ms_wide`: [12,68; −8,0; 25,93+1,5], ống 26 mm; nhìn vào [12,68; −31,13; 33,5].
   - Trời A (bầu trời vật lý), mặt trời cao 12°: `data/_plates3d/thap_dong_ho_shot4/20260925_135742/plate_shot4_ms_wide.png` — **thấy rõ
     toàn bộ tháp** (chóp nhọn, mái 2 tầng, tầng chuông cửa sổ đôi, cửa sổ vòm, cửa vòm chân tháp, 2 cây dừa, lan can đá). Bản chạng
     vạng quá tối, bỏ.
   - Trời C (trong suốt, để tự vẽ trời đêm), mặt trời 30°: `data/_plates3d/thap_dong_ho_shot4_night/20260925_140154/plate_shot4_ms_wide.png`
     (+ `depth_shot4_ms_wide.png`). **Chưa mở xem** — việc đầu tiên phiên sau.
2. **Thử 1 ảnh "nền cố định"** (Deepix GPT Image 2.5 Sunburst, ảnh 1 = nền render, ảnh 2 = Kelly chuẩn `data/assets/23/10.png`, prompt
   "giữ nguyên kiến trúc, chỉ đổi sang đêm, đặt Kelly trung cảnh"): `data/projects/7/plate_test/shot4_plate.png`.
   **Đánh giá: ~70%.** Đúng: đỉnh tháp (chóp, mái 2 tầng, cửa sổ đôi tầng chuông), trời đêm + trăng, đèn đường, Kelly đúng nhân vật.
   Sai: model **tự phóng to tháp**, thân tháp + cửa sổ vòm + cửa vòm chân tháp bị Kelly che/mất, lan can bị vẽ lại khác, tỉ lệ tháp béo hơn.
   → **Kết luận: đưa ảnh render làm tham chiếu (dù dặn "giữ nguyên") KHÔNG đạt 90%** — model tạo ảnh luôn vẽ lại nền.
3. Công cụ thử nghiệm đưa vào repo: `tools/experiments/tower_plate.py` (lệnh `render` / `plate` / `green`, có kiểm trần ảnh + ghi sổ chi).

### 2.3 Hướng chốt để đạt 90–100%: **ghép (composite) — tháp là pixel thật của mô hình 3D**
Nguyên tắc: AI chỉ vẽ **nhân vật**, nền lấy nguyên từ render 3D, ghép bằng code (OpenCV + numpy + ffmpeg — **đã có trên máy**;
rembg/torch/mediapipe **chưa có**).

| Bước | Việc | Tốn tiền? | Trạng thái |
|---|---|---|---|
| C1 | Nền đêm: plate trời C (trong suốt) + vẽ trời đêm phía sau (gradient xanh đậm, sao, trăng) + chỉnh màu "ngày thành đêm" cho kiến trúc (giảm phơi sáng, ám xanh lạnh, giữ đèn đường ấm nếu thêm) | Không | render xong, **chưa làm phần vẽ trời/chỉnh màu** |
| C2 | Nhân vật trên phông xanh #00FF00: `py tools/experiments/tower_plate.py green --project 7 --ref "D:/AI-Video-Pipeline/data/assets/23/10.png" --out kelly_green.png` (1 ảnh → 22/32) | 1 ảnh | **chưa chạy** (script cũ lỗi đường dẫn đã viết lại) |
| C3 | Tách phông: OpenCV HSV key + despill (khử viền xanh) + làm mềm viền 1–2 px; nếu tóc bị răng cưa → cân nhắc cài `rembg` (tải model ~170 MB — **hỏi người dùng trước khi tải**) | Không | chưa viết (`tools/experiments/composite_plate.py`) |
| C4 | Ghép: làm mờ nền nhẹ theo `depth_*.png` (độ sâu trường ảnh), "light wrap" viền, cân màu nhân vật theo nền (ám xanh trăng), bóng mềm dưới chân nếu thấy chân | Không | chưa viết |
| C5 | Cho người dùng xem ảnh ghép, so với ảnh 2.2 và ảnh cũ (250–253) | Không | — |
| C6 | Nếu đạt: ảnh ghép làm **khung đầu** cho Kling (máy tĩnh hoặc đẩy chậm → nền giữ gần nguyên trong 3–5 s) → 1 clip thử ~$0,32–0,40 | $ | chờ C5 |
| C7 | Đưa vào pipeline: shot có `location_asset` có mô hình 3D + camera khớp shot → render plate theo shot (`plates3d` + camera suy từ `shot_size/angle`) → gen nhân vật phông xanh → ghép → ảnh shot. Cờ tính năng mới (TẮT tới khi thử thật), test đơn vị cho phần ghép | Không (code) | chưa làm |

Rủi ro đã biết: ánh sáng nhân vật lệch nền (dặn prompt "ánh trăng lạnh từ trên trái"), viền tóc, video model có thể "vẽ lại" nền khi máy
di chuyển nhiều → shot dùng cách này nên máy tĩnh/đẩy chậm. Phương án dự phòng: sau khi ghép, cho Deepix "hòa ánh sáng" với mức thay đổi
thấp (nhưng dễ vẽ lại tháp → phải so lại với render).

## 3. (B) Khớp môi (lip-sync) — trả lời người dùng + việc làm

### 3.1 Các cách (đã tra)
| # | Cách | Ưu | Nhược | Trạng thái |
|---|---|---|---|---|
| L1 | **Seedance `reference_audio`** qua API ClipAI: gửi file giọng Việt của mình (ElevenLabs) kèm ảnh khung đầu → Seedance tạo video miệng theo âm | Tự động được, dùng đúng giọng clone VN | Chưa thử với tiếng Việt; Seedance 2.0 720p **$0,15/s**, 2.5 **$0,23/s** (1 shot 4 s = $0,60 / $0,92) — đắt hơn Kling $0,08/s | **Adapter chưa hỗ trợ** — cần code |
| L2 | ClipAI **Lip Sync** trên web | Chuyên cho khớp môi | **Chỉ có trên web** (không API), giao diện CN/EN → làm tay từng clip | Không tự động được |
| L3 | **Né** (mặc định hiện tại): thoại đặt ở shot không thấy miệng rõ (quay lưng, qua vai, toàn cảnh, cắt cảnh phụ); Director cấm thoại ở cận mặt người nói; `director_report` đếm `lip_sync` | Miễn phí, đã chạy | Hạn chế cách quay, cảnh cảm xúc cận mặt khó | ✅ có |
| L4 | Mô hình khớp môi chạy máy (Wav2Lip / LatentSync / MuseTalk) sau khi có clip | Không tốn API | Cần GPU + torch (**chưa cài**), chất lượng mặt 3D game chưa rõ | Chỉ nghiên cứu |

**Đề xuất:** L3 là mặc định; **L1 cho vài câu then chốt quay cận mặt** (vd. shot 4 Kelly "Em hiểu rồi…"). Thử L1 trên 1 shot trước.

### 3.2 Chi tiết API L1 (từ `D:\AI-Video-Pipeline\Get this Skill to Claude\clipai-1.3.1\clipai\scripts\video.mjs` dòng 283–420,
`shared/client.mjs` dòng 124)
- Endpoint Seedance đã có trong adapter: `PATH_SEEDANCE = /api/kling/seedance-video-submit` (`core/adapters/clipai.py`).
- `content[]` thêm mục: `{"type": "audio_url", "audio_url": {"url": ""}, "role": "reference_audio"}` — file cục bộ thì `url` rỗng và file
  gửi kèm multipart trường **`audio_files`** (giống cách `image_files`/`video_files`); URL http thì điền `url`.
- Giới hạn: Seedance 2.0 ≤ 3 audio (≤ 9 ảnh, ≤ 3 video); 2.5 ≤ 10 audio, tổng tham chiếu ≤ 50; 2.5 và 2.0 Fast chỉ 480p/720p.
- Lưu ý đã biết: Seedance **không cho** khung đầu (`first_frame`) đi cùng ảnh tham chiếu (`SEEDANCE_REFS_WITH_FIRST_FRAME = False`) →
  thử khung đầu + audio (không ảnh tham chiếu khác).

### 3.3 Việc cần làm (theo thứ tự)
1. Code: `core/adapters/clipai.py` nhận `reference_audio` (danh sách file) cho họ Seedance → thêm mục `content` + `audio_files`; kiểm giới
   hạn số audio theo model; test đơn vị (mock HTTP) theo kiểu test Seedance hiện có.
2. Runner: shot có thoại + cờ mới (vd. `lip_sync_seedance`, TẮT mặc định) → chọn model Seedance, gửi đoạn giọng của câu thoại shot đó
   (cắt từ file giọng đã tạo ở Bước giọng, đúng giây), prompt "nhân vật nói câu này, miệng khớp âm thanh".
3. Thử thật 1 shot: dự án #7 shot 4 (Kelly MS nhìn máy) — **báo giá trước** (~$0,60 bản 2.0 / 4 s), còn trong trần $3,98.
4. So sánh: miệng có khớp tiếng Việt không, nhân vật có giữ đúng không, Seedance có tự thêm âm khác không (tắt âm sinh ra, dựng dùng giọng của mình).

## 4. Việc còn lại khác (không đổi so với trước)
- **Chờ người dùng:** quyết 2B (20–58 s của #6, ~$5–6); duyệt 3 bộ nguyên tắc vai (`knowledge/roles/director.md`, `roles/dp.md`,
  `knowledge/editor/`) → bật `film_crew`; duyệt hồ sơ chuẩn KELLY/KENTA/MAXIM.
- Code: tầng A Director (Đạo diễn chỉ viết ý đồ, lượt riêng); Editor đặt chữ tránh mặt theo từng khung; GĐ-F (W2, W8, W10, M3, O6, M14,
  M16, M18, M19); GĐ-H giao diện; T1 hồ sơ mọi nhân vật; `recover_clips` chế độ tìm theo prompt; K1/K2 (khung cuối — thông tin có trong
  skill `clipai-1.3.1`).
- Dự án #6 đang dừng ở Bước 1: 31 shot, 63,7 s; cảnh cinematic 1 & 6 ở Kho #263 ban đêm. Nếu (A) đạt → áp cho các shot cinematic đó
  trước khi chạy 2B (đỡ phải gen lại).

## 5. Lưu ý kỹ thuật cho phiên sau
- Chạy script Python có chuỗi đường dẫn Windows: **không** sinh code bằng chuỗi Python thường lồng nhau (`\a`, `\1` bị hiểu thành ký tự
  điều khiển — script `gen_green` cũ đã hỏng đường dẫn vì vậy). Viết file trực tiếp bằng Write/Edit, dùng `r"..."`.
- PowerShell không nhận `\"` trong `py -c "..."` → viết file .py rồi chạy.
- Nạp token: `[Environment]::GetEnvironmentVariable('DEEPIX_TOKEN','User')` vào `$env:` trong cùng lệnh; không in token.
- `plates3d.plan(presets=[])` nghĩa là **tất cả** preset → muốn chỉ camera riêng thì truyền 1 preset nhỏ (`["eye_000"]`).
- `data/` và `manifest.sqlite` không vào git → ảnh thử nghiệm chỉ nằm trên máy này (đường dẫn ở trên).
