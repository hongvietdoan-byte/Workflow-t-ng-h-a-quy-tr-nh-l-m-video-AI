# Công thức prompt — bản nháp F0 (09/10/2026, chờ người dùng duyệt)

Nguồn: 9 shot #22 Khủng Long Đỏ (8 image prompt + motion lượt 2–3 viết tay), bài học L1–L19 (`docs/TONG_HOP_3_LUOT_KHUNG_LONG_DO.md` mục 6), góp ý #24 (`docs/RA_SOAT_TRUOC_GEN_LAI_24_2026-10-08.md`). Áp cho mọi dự án Free Fire. Chưa có code.

## 1. Công thức không gò bó: cố định CÁI PHẢI QUYẾT, không cố định CÂU CHỮ

Một prompt gồm **khung** (các phần bắt buộc phải có quyết định) + **phần sáng tạo** (Đạo diễn viết tự do cho kịch bản này).
- **Công thức quy định "phải nói về điều gì"**, không quy định câu. Ví dụ phần "khóa nền" bắt buộc có: ảnh nào là chuẩn nền + cùng máy/cùng chỗ với shot nào; còn tả nền ra sao là của Đạo diễn.
- **Phần có điều kiện**: chỉ bật khi đúng tình huống (ảnh OUTFIT có người mẫu → khóa tóc riêng; vật lao sát người → đường đi; shot cùng setup với shot trước → "cùng máy, cùng chỗ"). Kịch bản không có tình huống đó thì phần đó không xuất hiện — không nhồi câu thừa.
- **Biến thể theo loại shot** (mỗi loại một bộ phần bắt buộc riêng): thoại · hành động · nhảy theo video mẫu · cận đồ vật/sản phẩm · toàn cảnh mở · quái/sinh vật · hiệu ứng kỹ năng · chuyển cảnh. Kịch bản mới chỉ là tổ hợp các loại shot này.
- **Code kiểm phần, không kiểm chữ**: thiếu phần bắt buộc, hai phần mâu thuẫn nhau (khung "trung cận" ↔ tư thế "thấy chân"; luật của người ↔ nhân vật là quái; câu địa điểm ↔ render), phần lặp sai dữ liệu (màu, số sừng). Người sửa tay vẫn được — hệ thống chỉ chặn khi sai khung, và ghi lại phần người thêm để đề xuất bổ sung công thức.

## 2. Bài học: duyệt hết, nhưng dùng theo 3 tầng

| Tầng | Là gì | Dùng thế nào | Ví dụ |
|---|---|---|---|
| **1. Luật cứng FF** | đúng ở mọi dự án FF, sai là hỏng | code kiểm, chặn trước khi gửi | ≥ 18 tuổi; nhân vật đúng hồ sơ; nền theo render 3D; tiết chế ghê (máu/tóc/xác chỉ gợi, trong tối, ngoài nét); phụ kiện giữ trạng thái thiết kế |
| **2. Công thức khâu** | các phần bắt buộc của prompt mỗi loại shot | ghép prompt từ khung; thiếu phần thì báo | 9 phần ảnh, 8 phần motion (mục 3) |
| **3. Kinh nghiệm theo ngữ cảnh** | đúng trong điều kiện cụ thể, có độ tin (số dự án) | chỉ đưa cho Đạo diễn/Quay phim **khi ngữ cảnh khớp**, kèm lý do + độ tin; được chọn không theo nhưng phải ghi vì sao | "clip dài trên nền có mốc → máy gần tĩnh" (1 dự án); "ref-only → thêm câu chốt tóc" |

Mỗi bài học ghi: **áp khi nào** (điều kiện) · **vì sao** · **bằng chứng** (dự án/shot) · **độ tin** · **tầng**. Bài học bị dự án sau đánh đổ → hạ tầng hoặc gỡ (không xóa, ghi lý do). Đây là chỗ #24 hỏng: luật "không mắt phát sáng" (tầng 3, đúng cho người) bị đặt như tầng 1 → áp cho yêu nữ mắt đỏ.

## 3. Từ khóa bắt buộc rút từ #22

### 3.1 Ảnh khung đầu — 9 phần
| # | Phần | Bắt buộc | Từ khóa / mẫu #22 |
|---|---|---|---|
| 1 | Phong cách | luôn | `Free Fire in-game 3D render, stylized proportions, moderate texture detail, clear gameplay lighting` |
| 2 | Khung hình | luôn | cỡ cảnh **kèm giới hạn cơ thể**: `medium close-up from mid-chest up, no legs` · `wide shot … full bodies with feet visible`; góc máy; `vertical frame` |
| 3 | Khóa nền | khi có render 3D | `inside <chỗ đứng> exactly as the 3D render` + kể 2–4 mốc **đúng vị trí trong khung** (`clock tower … left of centre`, `house peeks above the right-hand side wall`) + `the PLACE render picture decides the whole background` |
| 4 | Nối tiếp | khi cùng setup shot trước | `same camera and same spot as the previous shot` |
| 5 | Nhân vật | mỗi người | TÊN + vị trí (`frame-left`) + hướng mặt/nhìn; trang phục **kể từng món có màu** theo ảnh OUTFIT (`red hoodie with the GREEN fire-breathing dinosaur print, black sleeves`); **trạng thái phụ kiện** (`mask worn UP over mouth and nose (never pulled down)`); khóa tóc riêng khi ảnh OUTFIT có người mẫu |
| 6 | Khoảnh khắc | luôn | **một** trạng thái khớp khung: `mid-step, looking toward the bed off-screen right` · `crouching mid-dance` |
| 7 | Luật FF | luôn | tiết chế ghê; tuổi; (code thêm) |
| 8 | Ánh sáng | luôn | nguồn + hướng: `soft window light from the side` · `bright warm midday sunlight from upper-front` |
| 9 | Chốt chất lượng | luôn | `everything in focus, not a movie still, not blurred background` |

### 3.2 Motion — 8 phần
| # | Phần | Bắt buộc | Từ khóa / mẫu #22 |
|---|---|---|---|
| 1 | Điểm bắt đầu | luôn | `The clip starts exactly on the pose and framing of the first image` |
| 2 | Hành động | luôn | chuỗi động từ có thứ tự + điểm dừng: `spins once on the spot, flicks the brim …, then lands a playful pose … and holds it` |
| 3 | Vật lý | khi có người di chuyển | `weight shifting heel-to-toe with no foot sliding` · `feet never slide` |
| 4 | Máy quay | luôn | kiểu + mức + khung giữ: `Static camera` · `almost static, only a very slow tiny drift, holding the same wide full-body framing` · `pulls straight back along the camera axis` |
| 5 | Thứ đứng yên | khi cần | `nothing else moves` · nền cố định + mốc giữ chỗ |
| 6 | Khóa nhận dạng | đường ref-only | trang phục từng món + phụ kiện + tóc (vì không có khung đầu cố định) |
| 7 | Nguồn động tác | khi có video mẫu | `exactly the moves of the reference video, beat by beat` + `the dancer only gives the motion — never take her face, clothes or room` |
| 8 | Thoại | shot thoại | `says his line …; his mouth moves only while he speaks` |
| + | Đường đi vật gần người (mới, #24) | khi có | điểm đầu → điểm cuối, khoảng cách, `never touches or passes through her` |
| + | Loại nhân vật (mới, #24) | luôn | luật người / quái / thú tách riêng |

## 4. Dò lại 9 prompt #22 — lỗi và chỗ viết tốt hơn

**Lỗi trong chính prompt "đẹp":**
1. **Dữ liệu trang phục mâu thuẫn**: mũ Maxim "two small **white** horns" (shot 2, 4) ↔ "small **red** horns" (shot 7–9); in hình áo Kelly "GREEN dinosaur" (image) ↔ "**blue** dinosaur print" (blocking code ghép thêm, shot 6). → Trang phục phải lấy **một nguồn** (hồ sơ Kho), không gõ tay mỗi shot.
2. **Nhắc tên thứ cấm** "Do NOT add palm trees, grass fields, cars, red-roof houses" — bài học L2 của chính #22: nhắc chữ của lỗi kéo lỗi lại. → tả cái đúng ("chỉ có cầu thang, tường, tháp, nhà 3 tầng như render").
3. **Shot 3, 5 không khóa nền** (không "exactly as the 3D render") — chỉ đẹp nhờ cận mặt. Cỡ cảnh rộng hơn sẽ trôi nền.
4. **Câu dính liền mất dấu chấm**: "not blurred background KELLY KL keeps…" — câu khóa tóc ghép vào cuối không ngắt câu.
5. **Lặp dài**: motion 7–9 lặp ~1.200 ký tự giống nhau (nền + trang phục) → gần trần 4.000 ký tự Seedance, đẩy phần hành động (cái thay đổi giữa 3 shot) xuống cuối. → nền/trang phục viết gọn một lần, hành động lên đầu.
6. **Ánh sáng không đồng nhất** giữa shot 7 ("warm … upper-front") và 8–9 ("bright midday") cùng một cảnh liền.
7. Shot 1, 3, 5 thiếu **trạng thái cuối** của motion (shot 2, 4, 6, 9 có).

**Thứ tự đề xuất trong một prompt**: phong cách → khung → nhân vật + hành động (phần thay đổi) → nền (gọn) → ánh sáng → khóa/luật → chốt chất lượng.

## 4b. Lớp dò prompt sau mỗi lần Đạo diễn viết / viết lại (người dùng 09/10)
Sau MỖI lượt Đạo diễn (viết, viết lại, sửa theo QC): (1) code kiểm khung công thức (thiếu phần, mâu thuẫn, dữ liệu trang phục khác hồ sơ, từ ghê, luật sai loại nhân vật); (2) **so với bản trước**: prompt chỉ dài thêm mà không bỏ / thay câu cũ → cảnh báo "trồng thêm" (như #24), câu mới mâu thuẫn câu cũ → đỏ; (3) một lượt Claude "biên tập prompt" viết lại gọn theo đúng khung khi (1)/(2) có lỗi (≈ 0,05–0,2 USD/dự án, có giá trước). Kết quả hiện ở báo cáo Đạo diễn + thẻ shot; không qua thì không gửi gen.

## 5. F3 — chi phí cho 30–60 video/tháng, 1080p

Đơn giá ClipAI trong `data/pricing.json` (USD/giây ra, 9:16): Seedance 2.5 — 480p nháp 0,103 · 720p 0,231 · **1080p 0,52**; Seedance 2.0 — 1080p 0,34; Kling 3.0 Omni bản pro (1080p) **0,122**. Giả định: số giây gen = 1,75 × độ dài phim (đầu/cuối cắt bỏ, clip ≥ 4 s, gen lại ~25 %); nâng nháp = 1,4 × (chỉ cảnh đã duyệt); ảnh + Claude + âm thanh ≈ 7 USD/phim 1 phút, ≈ 10 USD/phim 2 phút. **Giá nâng nháp 2.5 → 1080p chưa đo thật** (tính như gen 1080p).

| Cách làm | Phim 1 phút (mục tiêu < 30 USD) | Phim 2 phút (mục tiêu < 60 USD) |
|---|---|---|
| A. Mọi shot nháp 2.5 480p → nâng 1080p | ≈ 61 ✘ | ≈ 120 ✘ |
| B. Mọi shot Seedance 2.0 1080p gen thẳng | ≈ 43 ✘ | ≈ 81 ✘ |
| C. Mọi shot Kling 3.0 Omni pro 1080p | ≈ 20 ✔ | ≈ 36 ✔ |
| **D. Trộn: shot khó/then chốt (≤ 20–30 % thời lượng) nháp 2.5 → 1080p, còn lại Kling pro 1080p** | **≈ 27–31** | **≈ 50–58** |

→ **Không mặc định nháp 2.5 cho mọi shot** (gấp đôi ngân sách). Đề xuất: đường **D** + trần tiền mỗi phim (cảnh báo khi ước tính vượt). Ảnh khung đầu (0,05 USD) là "nháp" rẻ nhất cho bố cục; nháp video chỉ dành cho shot có động tác khó.

### 5b. Phương án người dùng đề xuất 09/10 (E): theo nhãn dễ/khó của Đạo diễn (đã có: `scenes.data.difficulty`, `quality_tier.path`)
- Shot **dễ** → gen thẳng 1080p bằng Seedance rẻ; shot **khó / quan trọng** → nháp Seedance 2.5 480p → đạt → nâng 1080p giữ nội dung.
- Ràng buộc thật của ClipAI (`data/provider_rules.json`, `video_models.json`): **Seedance 2.0 Mini chỉ có trên web, tối đa 720p**; **Seedance 2.0 Fast qua API chỉ 480p/720p**. Qua API, 1080p chỉ có **Seedance 2.0 (0,34 USD/s)** và Seedance 2.5 (0,52).
- Tính (shot dễ 75–80 % thời lượng, prompt tốt → gen lại ít, hệ số 1,4): **1 phút ≈ 39–40 USD, 2 phút ≈ 76–79 USD** — vượt mục tiêu ~30 %. Sàn tuyệt đối: 60 s × 0,34 = 20,4 USD dù không gen lại giây nào.
- Cách đưa E về mục tiêu (cần người dùng chọn):
  - **E1**: shot dễ gen Seedance 2.0 **720p** (0,15/s) rồi phóng 1080p bằng ffmpeg (không AI, tức thì) → 1 phút ≈ 28, 2 phút ≈ 56 ✔; shot dễ mềm hơn 1080p thật.
  - **E2**: giữ 2.0 1080p cho shot dễ, nâng mục tiêu ≈ 40 / 80 USD.
  - **E3**: giảm giây gen thừa (cắt đầu/cuối, clip tối thiểu 4 s, gom nhóm) từ hệ số 1,4 → 1,2: E ≈ 35 / 68.
  - **E4**: thử Kling pro cho shot dễ bằng A/B 2–3 shot; chỉ dùng nếu đạt.

**Phải đo trước khi chốt (≈ 3–5 USD, cần duyệt):** (1) Kling 3.0 Omni pro 1080p có giữ đúng phong cách FF + nhân vật như Seedance không — 2–3 shot #22/#24 có sẵn ảnh khung đầu; (2) giá thật của một lần nâng nháp 2.5 → 1080p.
