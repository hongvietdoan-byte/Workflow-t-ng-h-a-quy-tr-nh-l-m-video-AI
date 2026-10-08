# Tổng hợp 3 lượt Khủng Long Đỏ (#22) — so sánh theo khâu (mục 4B)

Ngày 08/10/2026. Chỉ đọc, 0 USD: bản sao CSDL máy chính (`data/manifest.sqlite` + WAL, chép ra thư mục tạm), `data/projects/22/*`, ảnh chụp `docs/kld_runs/*.json`, tài liệu dự án, git log 06–08/10, 2 lưới khung hình trích bằng ffmpeg từ bản giao lượt 2 và lượt 3. Không sửa dữ liệu thật, không commit.

**Mốc lượt** (theo bản dựng `outputs` của CSDL, giờ UTC): lượt 1 = mọi việc trước bản dựng #29 lúc 07/10 02:37; lượt 2 = 02:38 → bản dựng #32 lúc 07:24; lượt 3 = 07:25 → bản dựng #34 lúc 13:13. Đây là cùng mốc với bản thống kê 4A.

**Ký hiệu nguồn:** **[Số]** = số liệu đo hoặc dữ liệu (job, diag, QC, tệp); **[ND]** = nhận xét của người dùng (ghi trong tài liệu/memory); **[Mắt]** = mình xem khung hình trích ra (chỉ 6 khung mỗi bản, không phải đo).

> **Lượt 3 chỉ là "chất lượng cao" MỘT PHẦN.** Chỉ 3 cảnh nhảy (shot 7–9, scene 254–256) làm lại bằng Seedance 2.5 720p. Shot 6 làm lại bằng Fast (job 549) để sửa động tác. Shot 1, 2, 4 giữ clip Fast của lượt 2; shot 3, 5 giữ clip Seedance 2.5 của lượt 2. Ảnh khung đầu chỉ vẽ lại 3 ảnh cảnh nhảy. Vì vậy, ở các khâu dưới đây, cột Lượt 3 thường ghi "giữ lượt 2".

## 0. Tóm tắt

- **Kết quả:** lượt 3 được người dùng xác nhận **đạt** (08/10). Phần cảnh nhảy tốt lên rõ: nền giữ đúng cầu thang + tháp suốt 3 clip [Mắt], chỗ nối liền. Nhưng phần cảnh 1 (shot 1–6) vẫn là chất lượng thử.
- **Tiền (giá bảng, theo 4A):** lượt 1 19,06 · lượt 2 11,99 · lượt 3 20,07 USD. **Khoảng 22,5 USD trong 48,5 USD ảnh + video không vào bản giao nào.** Riêng lượt 3 có 10,7 / 19,6 USD ảnh + video không vào phim; lỗi thao tác và cấu hình (gửi nhầm model, nút gen chung, đổi chỗ đứng sau khi gen) chiếm 6,6 USD trong số đó (mục 3).
- **Cải thiện có số đo:** QC video `identity` từ 0,72 (lượt 1) lên 0,87 / 0,86. Số ảnh phải gen để có 1 ảnh dùng: lượt 1 cần 28 job ảnh cho 9 ảnh, lượt 2 cần 12 cho 9, lượt 3 cần 9 cho 3. Ở lượt 2, nền ảnh cảnh nhảy khớp render 3D 0,42–0,47.
- **Không cải thiện:** khớp môi vẫn 0,03 / 0,44 (lượt 3 dùng lại clip lượt 2). Chỉ số mặt mịn so với khung đầu (`clip_measure`) ở clip nhảy Seedance 2.5 lượt 3 là ×0,12–0,24, không tốt hơn Fast (×0,22–0,31). Như vậy "chất lượng cao" chưa có số đo chứng minh rõ nét hơn; việc này cần người dùng nhìn.
- **Nguyên nhân gốc lặp lại nhiều nhất:** (1) dữ liệu cũ thắng dữ liệu mới: prompt "sân phẳng, nhà mái đỏ" còn sót, nền 3D không dựng lại, ảnh toàn cảnh vẽ từ ngoài tường. (2) Ảnh tham chiếu mang theo thứ không muốn: tóc người mẫu trong ảnh OUTFIT, hồ sơ đồ thường trong khóa nhận dạng. (3) Nút và alias của Dashboard gửi thứ người dùng không định gửi.
- **Thước đo tự động lệch với mắt người:** `place_match` cho qua ảnh sai chỗ (0,36–0,42) nhưng cảnh báo ảnh người dùng duyệt (0,31). QC lớp 0 đòi vẽ lại theo cỡ cảnh 10 lần, chỉ 2 bản tự vẽ lại từng được dùng.

## 1. Số liệu 4A (tóm tắt; đủ bảng ở `docs/kld_runs/THONG_KE_3_LUOT_2026-10-08.md`)

| | Lượt 1 (thử) | Lượt 2 (thử) | Lượt 3 (cao, một phần) |
|---|---|---|---|
| Tiền giá bảng (USD) | 19,06 (video Fast 13,92; 2.5 1,84; Claude 1,74; ảnh Seedream 1,56) | 11,99 (Fast 9,12; 2.5 1,84; ảnh GPT 0,62; Claude 0,41) | 20,07 (2.5@720p 11,96; 2.0 4,80; Fast 1,92; ảnh 0,52; Claude 0,46; 480p 0,41) |
| Job ảnh (tổng / được dùng trong bản giao của lượt) | 28 / 9 | 12 / 9 | 9 / 3 |
| Job video (tổng / có tiền / được dùng) | 21 / 15 / 9 | 11 / 11 / 9 | 13 / 10 / 4 |
| Thời gian đồng hồ (gồm thời gian chờ người và chờ nạp tiền ClipAI) | 06/10 15:07 → 07/10 02:37 (≈ 11,5 giờ; dừng 18:23 → 01:27 vì ClipAI hết số dư) | ≈ 4,8 giờ | ≈ 5,8 giờ (gồm Codex sửa nền `c8f7a69`, phép so `d264b23`, dựng nền Blender) |
| QC video trung bình identity / artifacts / motion_match | 0,72 / 0,79 / 0,77 | 0,87 / 0,86 / 0,79 | 0,86 / 0,83 / 0,80 |
| diag nổi bật | redraw ×7, task_failed ×9 (6 hết tiền, 3 timeout), clip_measure ×11 | clip_measure ×7, redraw ×1 | clip_measure ×7, stale_input ×1 |

**Lưu ý khi đọc 4A:**
- Cột "approved" của 4A là **trạng thái hiện tại**. Lượt 1 ghi 0 ảnh / 0 video duyệt, nhưng thực ra 9 ảnh + 9 clip đã được duyệt và dựng thành bản thử 1. Bản dựng #29 dùng clip 517, 518, 519, 520, 521, 524, 523, 513, 515. Sau đó chúng bị đánh "loại" khi lượt sau đổi đầu vào. Xem `review_log` (user:approve rồi "làm lại vì làm từ ảnh cũ").
- Cột `at` của `usage_events` có dạng `YYYY-MM-DD HH:MM:SS`, khác `jobs.created_at` (có chữ `T`). Ai lọc theo chuỗi phải chuẩn hóa, nếu không mọi dòng 07/10 sẽ rơi vào lượt 1.

## 2. So sánh 12 khâu

### 2.1 Ý tưởng, kịch bản, Biên kịch
| | Lượt 1 | Lượt 2 | Lượt 3 |
|---|---|---|---|
| Nội dung | Kịch bản Claude soạn sẵn trong `DU_AN_KHUNG_LONG_DO` mục 3 (commit `4e9a579`), dán vào Bước 1. Thoại: "Đồ khủng long xịn vậy! Hô biến!" / "Mặc đồ đôi mà không rủ tớ à? Hô biến!" | Thoại viết lại kiểu nói thường: "Ủa, đồ này ở đâu ra mà nhìn hay zậy? Để mặc thử coi!" / "Ê, mặc đồ đôi mà hổng rủ tui hả?" | Giữ lượt 2 |
| Đánh giá | **Sai**: thoại cứng [ND] | **Tốt**: người dùng không chê nữa [ND] | — |

- **Bằng chứng:** `dialogue` shot 3, 5 trong `ban_thu_1.json` và `ban_thu_2.json`. Lượt 1 có thêm `delivery` (emotion/stress); lượt 2 bỏ khối này.
- **Không dùng khâu Biên kịch.** `usage_events` không có stage `screenwriter` ở cả 3 lượt [Số]. Thoại sửa tay theo góp ý.
- **Nguyên nhân gốc:** chính kịch bản đầu vào (do phiên Claude viết) đã có câu kích hoạt "Hô biến!". Director giữ nguyên, không có lớp nào soát độ tự nhiên của thoại.
- **Tên thật FF:** kịch bản không có tên vật phẩm hay hạng FF nên không áp dụng; chưa có số đo.

### 2.2 Bible, hồ sơ nhân vật, Kho tài nguyên
| | Lượt 1 | Lượt 2 | Lượt 3 |
|---|---|---|---|
| Trang phục | Bible 4 dòng (MAXIM / KELLY + bản KL gắn OUTFIT Kho 416/417). Bộ đồ trên giường sai mẫu. Shot 7 (job 514, 516) nhảy bằng đồ thường | Bộ đồ trên giường đúng mẫu | Giữ lượt 2. Mũ Maxim đổi từ "red horned cap" sang "black cap with small red horns" |
| Tóc Kelly | — | Tóc lẫn bạc từ người mẫu trong ảnh OUTFIT → QC loại job 544, 545 | Giữ câu "dark bob, one solid colour" |
| Khẩu trang | Prompt Director ghi "mask pulled down under the chin" | "worn UP… never pulled down" | Giữ |
| Đánh giá | **Sai** ×3 | **Tốt** (đồ trên giường, khẩu trang); **Sai** (tóc lẫn) rồi đã vá | Mũ Maxim: **chưa xác nhận** |

**Bằng chứng:**
- [ND] trong `feedback_kld_preview_review_0710`, mục 2 và 4.
- Prompt ảnh shot 6 trong `ban_thu_1.json` có chữ "pulled down under the chin".
- `retry_reason` của 544/545: "Fix Kelly's hair to solid dark bob…".
- Commit `40f6111` (gửi ảnh trang phục cho shot không người), `3f1ebf9` (gửi OUTFIT ở đường chỉ-ảnh-tham-chiếu), `370dacc` (khóa nhận dạng của nhân vật có OUTFIT chỉ giữ mặt/tóc/dáng).
- Motion prompt shot 7–9 của `chat_luong_cao.json` ghi "black cap with small red horns", trong khi tư liệu gốc (`DU_AN` mục 2) ghi "mũ đỏ có sừng" và lượt 1/2 ghi "red horned cap". [Mắt] Lượt 3 thấy mũ Maxim tối màu.

**Nguyên nhân gốc:**
1. Dashboard chỉ gán trang phục theo dự án, nên phải dùng mẹo 4 dòng Bible.
2. Ảnh mặt trong Kho mang đồ thường và chữ "identity only (face, hair, outfit)" kéo đồ thường vào clip.
3. Ảnh OUTFIT có người mẫu, câu "chỉ lấy quần áo" không đủ để tách tóc.
4. Shot không người không có đường gửi ảnh trang phục (đã sửa).

**Còn mở:** hồ sơ chuẩn `lock_rules` của bản KL vẫn là đồ thường, khiến Tổ QC chặn nhầm 6/9 khung đã duyệt (`KIEM_22` mục 2.12).

### 2.3 Đạo diễn, kế hoạch shot, `director_rewrite`
| | Lượt 1 | Lượt 2 | Lượt 3 |
|---|---|---|---|
| Việc | Director 6 lượt Claude (191k input / 46k output token). Lần đầu chọn "mỗi cảnh một clip" → 2 clip 15 s + tự bịa áo liền thân. Đổi sang chia shot → 9 shot / 51 s | Không chạy lại Director. Prompt ảnh và motion sửa tay theo 6 góp ý | Không chạy Director / `director_rewrite`. 5 trường của scene 254–256 sửa tay (BAN_GIAO mục 4) |
| Lỗi | `bad_json_retry` ×2. Tự gắn đạo cụ "mũ" (mũ bảo hiểm) vì trùng chữ. "medium shot + dép" đứng cạnh "Framing: MCU". Chèn câu bối cảnh "quảng trường, cỏ, dừa, biển" vào shot trong phòng. Tự bịa động tác nhảy | — | — |
| Đánh giá | **Tốt**: cấu trúc 9 shot, cặp "cùng khung" hô biến. **Sai**: chi tiết prompt | Sửa tay, không qua vai | Sửa tay, không qua vai |

- **Bằng chứng:** diag `director/bad_json_retry` (15:09, 15:17 ngày 06/10), `auto_attach` "mũ", `dp_calls`, `director_review` "2 cảnh đạt ý đồ". `usage_events` lượt 2/3 không có stage `director` hay `motion` [Số]. `DU_AN` mục 6 (lượt 1, 2).
- **Nguyên nhân gốc:** Director dịch sát chữ ("mũ" → đạo cụ, "xanh" → blue). Khung shot và câu bối cảnh ghép từ nhiều nguồn mâu thuẫn. Sau lượt 1, mọi sửa nằm ở dữ liệu cảnh do người hoặc phiên Claude sửa, **vai Đạo diễn không học lại**. Bài học chưa quay về prompt hay knowledge của Director (việc 4C).

### 2.4 Nền 3D (plates) và chỗ đứng
| | Lượt 1 | Lượt 2 | Lượt 3 |
|---|---|---|---|
| Phòng tầng 2 | Ảnh vẽ thêm cửa mở ra ngoài trời | Đúng render. Nhân vật vào từ mép khung, không có cánh cửa | Giữ lượt 2 |
| Cảnh nhảy | `nha_lon_dong`, prompt "flat stone plaza… low red-roof house" | Cùng chỗ đứng và cùng prompt. Tháp / nhà đổi dần qua 3 clip | Đổi sang `bac_thang_giua` (chân cầu thang). Nền 3D mới `7728a07…`, ảnh toàn cảnh = render đồng trục, câu khóa nền |
| Đánh giá | **Sai** | Phòng **Tốt**; nhảy **Sai** | **Tốt** (sau 2 lần vẽ sai) |

**Bằng chứng:**
- [ND] `feedback_kld_preview_review_0710` mục 1 và phần cập nhật chiều 07/10.
- [Mắt] Lưới 6 khung bản v2 (18,8 / 29,2 / 29,8 / 40,6 / 41,3 / 52,3 s): tháp lúc ở trái, lúc ở giữa-phải, cuối chỉ còn nhà, có hàng cọ. Bản v3: cầu thang + tháp cùng chỗ ở cả 6 khung.
- Ảnh 550–552 (vẽ lại lần 1, lượt 3) dùng nền 3D cũ và còn ref `location` (ảnh toàn cảnh). Ảnh 553–555 (lần 2) bỏ `location` nhưng vẫn bị loại. Đến 556–558 mới duyệt (`jobs.sent_refs`, `review_log`).

**Nguyên nhân gốc:**
- Đường vẽ thủ công không dựng lại nền khi đổi chỗ đứng (chỉ autopilot so khóa).
- `image_prompt` / `blocking` / `spatial_state` / `action` cũ thắng render 3D.
- Ảnh toàn cảnh vẽ từ ngoài tường. Xem `feedback_scene_location_change_checklist`, lỗi phiên Claude #3.

### 2.5 Ảnh khung đầu (Deepix), QC ảnh, `place_match`
| | Lượt 1 | Lượt 2 | Lượt 3 |
|---|---|---|---|
| Model | Seedream 5 Pro | GPT Image 2.5 Sunburst (cùng 0,052 USD) | GPT Image 2.5 |
| Số job / dùng | 28 / 9 | 12 / 9 | 9 / 3 |
| QC lớp 0 (cỡ cảnh) | 7 lần tự vẽ lại (485, 486–488, 492, 500, 501). 3 bị timeout | 1 (534, bị loại) | 0 |
| `place_match` | Ảnh nhảy 482/484 lúc đầu 0,45/0,46, các lần sau 495–497 là 0,29–0,32 | 531/532: 0,42/0,47; 530/536: 0,34/0,32 | 550–552 (sai chỗ): 0,36/0,41/0,42; **556–558 (duyệt): 0,37/0,35/0,31** |
| Đánh giá | **Sai**: Kelly kém xinh [ND], khung "cùng khung" sai | **Tốt**: đẹp hơn [ND] | **Tốt** sau khi sửa nền |

**Bằng chứng:**
- `jobs.model`, diag `image/place_match`, `image/redraw`, `review_log`.
- Ở lượt 1, ảnh 485 và 492 (tự vẽ lại) **từng được người dùng duyệt và dùng trong bản thử 1** (`review_log` user:approve). Điểm này điều chỉnh câu "0 bản tự vẽ lại được duyệt" của `KIEM_22` mục 2.14, vốn đọc trạng thái hiện tại.

**Nguyên nhân gốc:**
- Model mặc định Seedream (mặt sắc, già).
- Ảnh neo kèm câu "khoảnh khắc MỚI, góc máy KHÁC" (đã sửa `370dacc`).
- QC lớp 0 đo "mặt cao bao nhiêu khung" lệch với mắt người.
- `place_match` so với **nền 3D đang gắn**. Khi nền gắn sai chỗ (lượt 3 lần 1), thước đo vẫn cho qua. Ngưỡng 0,35 không tách được ảnh đúng và sai [Số].

### 2.6 Motion prompt và Quay phim
| | Lượt 1 | Lượt 2 | Lượt 3 |
|---|---|---|---|
| Cảnh nhảy | "Camera locked off… no camera move, no zoom" | Shot 7 "slow push-in". Shot 9 "low angle… rises while pulling back" | Shot 7 "almost static… no push-in". Thêm BACKGROUND lock + START LOCK. Shot 9 vẫn "pulls straight back… rising" |
| Shot 6 Kelly | Cười, chống hông | Đứng yên, chống hông → người dùng chê | Xoay người, búng vành mũ, chữ V |
| Đánh giá | Máy đứng yên — người dùng muốn có chuyển động [ND] | **Tốt**: máy có chuyển động [ND]; **Sai**: Kelly đứng yên | **Tốt**: nền đứng vững. **Sai một phần**: khung cuối clip 256 nhiều sân trống |

**Bằng chứng:**
- Đoạn cuối motion prompt shot 7, 9 trong 3 tệp JSON.
- [Mắt] Khung 52,3 s bản v3: hai người nhỏ, nửa dưới khung là sân trống.
- QC job 549: "hand is adjusting the cap brim instead of showing a V sign" ở khung cuối, nên chữ V có thể không rõ. Chưa xem riêng.

**Nguyên nhân gốc:**
- Push-in / vòng cung cộng nền chưa khóa làm model "đi" sang nền khác.
- Câu "pull back" ở clip cuối được giữ dù đã bỏ ở clip đầu.
- Motion lượt 2/3 sửa tay, không qua stage `motion` (`usage_events` lượt 2/3 không có `motion`) [Số].

### 2.7 Gen video
| | Lượt 1 | Lượt 2 | Lượt 3 |
|---|---|---|---|
| Model | Fast 720p (thoại 2.5). Lần gửi đầu 6 job hỏng vì ClipAI hết số dư (0 USD) | Như lượt 1 | Cảnh nhảy 2.5 720p. Có 2 lần 2.0 gửi nhầm (566, 567) và 2 clip 2.0 gửi nhầm cảnh cũ (562, 563) |
| Nối cảnh | Không nối. Chỗ 28 / 39 s lệch động tác và đồ [ND] | `start_from_prev_clip` shot 8, 9 → liền tư thế và đồ [ND] | Giữ. Phải hoán đổi dòng job 560 ↔ 569 để chuỗi nối lấy đúng clip người dùng chọn |
| Clip nhảy | Shot 7 đồ thường (514, 516) | Tóc Kelly lẫn bạc → QC tự gen lại 546, 547 | 568 / 569 / 561. `clip_measure` mặt mịn ×0,24 / ×0,23 / ×0,12 |
| Đánh giá | **Sai** | **Tốt** (nối); **Sai** (nền trôi) | **Tốt** (nền + nối, người dùng chấp nhận); **Sai** (tiền gửi nhầm, mục 3) |

**Bằng chứng:**
- diag `task_failed` 504 "Account balance not enough".
- `job_events` 559: `stale_input` → `retryable` → được "gửi lại clip lỗi (lỗi nhà cung cấp)" thành job 566 bằng model `seedance` (= 2.0).
- `job_events` 560 / 569 (actor `claude`, hoán đổi).
- diag `clip_measure` 566 / 567 (2.0) có điểm nhảy vọt ở 3,21 / 3,54 s; 568 (2.5) ở 0,04 / 2,5 s.

**Nguyên nhân gốc:**
1. Alias `seedance` = 2.0.
2. Chế độ Thử rẻ ép model riêng của cảnh về Fast (sửa `fa21c76`).
3. **Job hỏng vì `stale_input` (đầu vào cũ) bị đưa vào nút "gửi lại clip lỗi (lỗi nhà cung cấp)"** — lỗi phân loại lý do hỏng, chưa thấy ghi ở tài liệu nào.
4. Chuỗi nối và `collect_clips` lấy lần gen có số job lớn nhất, không lấy bản người dùng chọn.

> **Lưu ý dữ liệu:** sau khi hoán đổi, `qc_results` vẫn gắn theo số job, nên điểm QC của 560 / 569 trong CSDL **không còn khớp nội dung tệp**.
> Không sửa CSDL: đọc điểm QC của hai dòng này theo chiều ngược (điểm ghi ở số 560 là của tệp hiện gắn với dòng 569, và ngược lại).
> **08/10 (KLD-1/2/3 code xong, chưa thử Dashboard thật):** lỗi 3 và 4 ở trên đã có code sửa — `core/takes.py` (`chosen_video_job`), `batch.provider_failures` / `requeue_input_failures`, `Pipeline.retry` chặn `stale_input`. Từ nay **không hoán đổi dòng job** để chọn bản: dùng nút "✔ Dùng bản này cho shot".

### 2.8 Thoại, TTS, khớp môi
| | Lượt 1 | Lượt 2 | Lượt 3 |
|---|---|---|---|
| Giọng | Tự gắn giọng 72 / 70 (0 USD) | Giữ. Giọng đặt ở giây 1,0 (`1ded677`) | Dùng lại clip 539, 541 |
| Tương quan miệng – giọng | Shot 3: 0,14 · shot 5: 0,45 | 0,03 · 0,44 | 0,03 · 0,44 (không đổi) |
| Đánh giá | **Sai** | **Sai** — người dùng tạm chấp nhận [ND] | Không làm |

- **Bằng chứng:** diag `clip_measure` job 521 (0,45, giọng 0,3 s), 539 (0,03), 541 (0,44). Số 0,14 lấy từ thông điệp commit `1ded677`. `lipsync/index.json` `method=generate`.
- **Nguyên nhân gốc:** Seedance 2.5 đường chỉ-ảnh-tham-chiếu + `reference_audio` không nhép theo giọng dù mốc giây đúng. Cách từng đạt 0,72–0,96 là clip nhóm `dialogue_take` (#10), chưa dùng ở #22. Khẩu trang luôn đeo che miệng nên lỗi ít lộ — đây là lợi ích phụ, không phải lời giải.

### 2.9 Nhạc, âm thanh, SFX, hậu kỳ
| | Lượt 1 | Lượt 2 | Lượt 3 |
|---|---|---|---|
| Nhạc | Chỉ nhạc gốc từ 17,04 s; cảnh 1 không nhạc | Nhạc ClipAI (3 bản, 1 lỗi 429) vào 1,8 s + nhạc gốc làm "Nhạc đoạn 2" từ 18,08 s | Giữ |
| Hậu kỳ | Chớp trắng + rung ở 7,5 / 14,04 s | Rung 8,54 / 15,08 s; nhún theo nhịp (bản #30 lỗi đọc `.m4a`, bản #31 → 85 nhịp) | Bỏ rung ở shot 4, 6 (`shakes` null); giữ nhún 85 nhịp + chớp |
| Đánh giá | **Sai**: thiếu nhạc cảnh 1 [ND] | **Tốt**; rung trước khi vào nhạc bị chê [ND] | **Tốt** |

- **Bằng chứng:** manifest `outputs` #29–#34 (`shakes`, `beat_pulse`, `beat_pulse_error` "Format not recognised"). Commit `c71b761`, `6aeee4d`, `337d0c8`.
- **Nguyên nhân gốc:** nhạc theo đoạn cảnh chưa phải mặc định nên phải đặt giây tay (TODO việc để sau, mục 13). Bộ dò nhịp không giải mã được `.m4a`.

### 2.10 Dựng (Editor)
| | Lượt 1 | Lượt 2 | Lượt 3 |
|---|---|---|---|
| Bản dựng | #29 (1 lần) | #30, #31, #32 (3 lần trong 24 phút) | #33 **sai**: 11 tệp, gồm 4 tệp phụ trong `videos/`, thiếu shot 1, 2 đang ở thùng rác. #34 đúng 9 clip |
| Cắt | `motion_trim` chỉ cắt đuôi (4,04 → 2,0–3,0 s; 12,04 → 11,5 s), mốc đầu luôn 0,0 s | Như lượt 1 | Như lượt 1. Chỗ nối 254 → 255 lệch tay; giật ở 1,5 s của 255 (diag 560 / 569) |
| Đánh giá | Đủ dùng | Đủ dùng | **Sai** rồi sửa tay; thiếu `trim_start` |

- **Bằng chứng:** `outputs.manifest.clips` #33 có `01_seedance20_job562.mp4`, `02_seedance20_job563.mp4`, `08_job560_giu.mp4`, `08_seedance25_job569.mp4`. `KIEM_22` mục 2.9. Không có stage `editor` trong `usage_events` (Editor Claude không chạy) [Số].
- **Nguyên nhân gốc:** khâu dựng gom **mọi** `.mp4` trong `videos/`, không chỉ clip đã duyệt. Editor chưa có loại sửa bỏ N giây đầu.

### 2.11 QC video, `clip_measure`, tự loại / tự gen lại
| | Lượt 1 | Lượt 2 | Lượt 3 |
|---|---|---|---|
| QC tự loại | 510, 511, 512, 514, 522 | 544, 545 | 560 (0,81 < 0,82) |
| Tự gen lại | 513, 514, 515, 516, 524. Shot 7 chạm trần 2 lần (`auto_regen_limit`) | 546, 547 | 569 (QC 0,72, tệ hơn bản gốc) |
| Tự gen lại có được dùng? | 513, 515, 524: có (bản thử 1). 514, 516: không | Có (bản thử 2) | **Không** — người dùng giữ bản QC loại |
| Đánh giá | Giúp một phần | Giúp | **Sai**: tốn 2,76 USD cho bản tệ hơn |

**Bằng chứng:**
- `review_log` ai_agent.
- `job_events` 569: "cùng lỗi lặp lại sau khi sửa… cần sửa lớp gốc".
- Câu sửa QC tả lại lỗi ("yellow tracksuit") kéo lỗi vào lần sau (`DU_AN` lượt 3).

**Nguyên nhân gốc:**
- Ngưỡng 0,82 sát với điểm của bản người dùng chấp nhận (0,81–0,82).
- Lời phê "mặt mịn hơn" là đặc tính của Seedance chỉ-ảnh-tham-chiếu (×0,12–0,39 ở mọi clip), không sửa được bằng gen lại.
- Tổ QC ảnh so với hồ sơ đồ thường, nên chặn 6/9 khung đã duyệt (`KIEM_22`).

### 2.12 Tiền, ngân sách, giao diện
| | Lượt 1 | Lượt 2 | Lượt 3 |
|---|---|---|---|
| Ước tính và tiêu | Ước tính Dashboard 13,86 USD, kế hoạch dư ≈ 24. Ước "thử rẻ ≈ 5,84" | Thêm ≈ 12 USD | 20,07 USD. Ước giá shot 7–9 sai lúc đầu (1,23 → thật ≈ 1,44 / clip Fast; 2.5 ≈ 2,76–3,18 / clip theo công thức web) |
| Giao diện | Thiếu ô (cỡ shot, chuyển cảnh, giây vào nhạc, thời lượng số lẻ…), sửa trong ngày (`446f33a`, `17754f0`, `c71b761`, `f9226f9`, `ca2260e`) | Đổi đường gen 6 shot mất ~30 thao tác | Nút "▶ Gen video" chung tự loại 4 clip đã duyệt và gửi nhầm 2. Thử rẻ ép model. Màn báo 73 % dù đã xong |
| Đánh giá | Sửa nhanh nhiều lỗi UI | — | **Sai** — đã vá ở `ff5dce0`, `07edd58`, `fa21c76` (chưa có bằng chứng chạy thật trên dự án mới) |

- **Bằng chứng:** `BAN_GIAO` mục 2, 5, 8. Giá thật 2.0@1080p 12 s = 2,93 USD; công thức repo cao hơn ≈ 33 % [ND chụp web].
- **Nguyên nhân gốc:** nút gen gửi mọi cảnh "cần gen" theo cài đặt của cả dự án. Alias model không hiện tên thật. Ước giá không đọc điều kiện hàm (hộp So độ nét chỉ nhận shot ≤ 4 s, không video ref).

## 3. Tiền không vào bản giao nào, theo lý do

**Cách tính:** chỉ tính job ảnh/video **có dòng sổ chi** mà **không nằm trong bản dựng nào** (#29, #32, #34). Nhân số lượng với giá bảng suy ra từ 4A:
- ảnh 0,052
- Fast 720p 0,12 USD/s
- 2.0 720p 0,15 USD/s
- 2.5 720p 0,23 USD/s
- 2.5 480p ≈ 0,103 USD/s

Clip 2.5 có video tham chiếu theo công thức web có thể đắt hơn (2,76–3,18 / clip 12 s), nên số dưới đây là **cận dưới**. Claude API (2,61 USD) không tính vào đây. Job 486–488 bị timeout nhưng vẫn có dòng sổ chi; **chưa đối chiếu** ClipAI có thật trừ tiền không.

| # | Lý do | Job | USD |
|---|---|---|---|
| 1 | Clip bị QC tự loại, không dùng (mặt mịn, tóc lẫn bạc, cắt cảnh trong clip ở 2,71 s) | 510, 511, 512, 522 (lượt 1); 544, 545 (lượt 2) | 7,68 |
| 2 | QC tự gen lại, không dùng | 514, 516 (shot 7 đồ thường); bản gen lại cảnh 255 (dòng 560 sau hoán đổi) | 5,64 |
| 3 | Gửi nhầm model (alias `seedance` = 2.0) | 566, 567 | 3,60 |
| 4 | Nút "Gen video" chung gửi nhầm cảnh đã duyệt | 562, 563 (564, 565 hủy trước khi gửi, 0 USD) | 1,20 |
| 5 | Đổi chỗ đứng cảnh nhảy sau khi đã gen | video 548; ảnh 550–555; ảnh toàn cảnh GPT lượt 3 | 1,80 |
| 6 | Phép so độ nét (ngoài phim) | A 720p 0,92 + B nháp 480p 0,41 (người dùng: B không cần) | 1,33 |
| 7 | QC lớp 0 cỡ cảnh: ảnh cha bị hủy để vẽ lại + bản vẽ lại không dùng | 476, 479, 480, 481, 498, 499, 529; 500, 501, 534 | 0,52 |
| 8 | Ảnh lỗi nhà cung cấp (timeout) + bản gửi lại không dùng | 486, 487, 488; 489, 490, 491 | 0,31 |
| 9 | Ảnh người dùng loại vì sai nội dung | 477, 482, 483, 484, 494, 530 | 0,31 |
| 10 | Ảnh toàn cảnh Seedream (không khung duyệt nào dùng) | establishing ×2 lượt 1 | 0,10 |
| | **Cộng** | | **≈ 22,5** |

- **Theo lượt:** lượt 1 ≈ 8,8 · lượt 2 ≈ 3,0 · lượt 3 ≈ 10,7.
- **Đối chiếu:** tổng ảnh + video theo 4A là 48,51 USD. Gồm ≈ 22,5 không vào bản giao nào + 13,5 chi cho bản thử đã giao rồi bị thay ở lượt sau + 12,5 vào phim cuối. Phần bị thay gồm lượt 1: 9 ảnh + 9 clip = 8,55; lượt 2 → 3: ảnh 531, 532, 536 + clip 542, 543, 546, 547 = 4,96. Đây là chi phí lặp có chủ đích (thử rẻ trước), **không** tính là lãng phí.
- **Phần tránh được bằng thao tác / cấu hình** (dòng 3, 4, 5, 6) = **7,9 USD**. Phần từ chất lượng model + QC (dòng 1, 2) = 13,3 USD; nguyên nhân gốc ở đầu vào (OUTFIT có tóc, thiếu ảnh OUTFIT, đặc tính mặt mịn), không ở bản thân việc gen lại.

## 4. Rút kinh nghiệm theo vai (4C)

**Cách làm.** Chỉ đọc, 0 USD. Đối chiếu mục 2–3 ở trên với prompt và knowledge **hiện có** của từng vai (`prompts/*.md`, `knowledge/roles/*`, `knowledge/editor/*`, `core/prompts.py`, `core/seedance_refs.py`). Những gì đã có thì **không** đề xuất lại. Mỗi thay đổi có mã KLD-n, xếp ở mục 5.

**Vai Claude nào thật sự chạy trên #22.** Đếm `usage_events` / `llm_calls` của dự án 22 trên bản sao CSDL 08/10:
- `director` 6 lượt (cả 6 ở lượt 1).
- `motion` 1 lượt (lượt 1).
- `qc_team` 41 lượt.
- `video` (QC clip) 37 lượt.

Các vai **không có lượt nào**: `screenwriter`, `director_rewrite`, `editor`, `translate`, `qc` (QC ảnh bằng Claude), `music`, `sfx`, `subtitles`, `asset_checklist`, `lessons`, `lesson_judge`. Bảng `lessons` có **0 dòng**. Bảng `mistakes` mới gom tới dự án 13, nên #22 chưa vào. `experience_cases` của #22 có 33 ca `failure` (ảnh 21, video 12) và **0 ca `success`**.

**Độ tin.** Mọi bài học dưới đây có độ tin **"1 dự án"**, trừ chỗ ghi khác. Lượt 1 → 2 → 3 đổi nhiều thứ cùng lúc, nên không có A/B từng yếu tố (xem `KIEM_22` mục 0).

**Phân loại thay đổi:**
- **[P]** prompt / knowledge: để sau cờ TẮT, rà nhẹ.
- **[C]** luật kiểm bằng code: cảnh báo, không đổi đầu ra trả tiền.
- **[$]** động tới tiền, dữ liệu hay quyền: rà kỹ.
- **[UI]** giao diện.
- **[L]** sửa lỗi.

### 4.1 Biên kịch (`screenwriter`) — không có dữ liệu chạy
- **Vì sao không có dữ liệu:** kịch bản do phiên Claude viết sẵn trong `DU_AN_KHUNG_LONG_DO` mục 3 rồi dán vào Bước 1, nên khâu Biên kịch không chạy (mục 2.1).
- **Học từ chỗ tốt (gián tiếp):** thoại lượt 2 ("Ủa, đồ này ở đâu ra mà nhìn hay zậy?…") được người dùng nhận. Kiểu thoại này **đã có sẵn** trong `knowledge/roles/screenwriter.md` B12 (GenZ, sạch) và B13 (thoại khớp hành động). Không cần thêm luật cho Biên kịch.
- **Học từ chỗ sai (gián tiếp):** câu "Hô biến!" lọt vào vì kịch bản **không đi qua Biên kịch**, và cũng không lớp nào sau đó soát độ tự nhiên của thoại dán tay. Director giữ nguyên văn đúng luật N1.
- **Đề xuất:**
  - **KLD-9 [P]**: Đạo diễn soát thoại kịch bản dán tay — xem 4.2.
  - **KLD-10 [UI]**: khi kịch bản dán tay (không qua Biên kịch), cho nút tùy chọn "Biên kịch đọc thoại". Nút này chạy riêng B12/B13 trên câu thoại, đề xuất sửa từng câu, người dùng tích chọn, có hiện giá trước khi bấm.
- **Bằng chứng:** mục 2.1; `usage_events` không có stage `screenwriter`.

### 4.2 Đạo diễn (`director`, Tầng A/B, cờ `film_crew` đã verified 08/10)

**(i) Làm tốt**
- Cấu trúc 9 shot / 51 s đúng mạch truyện.
- Cặp shot "cùng khung" quanh cú hô biến.
- Ghi được `tradeoffs` (cảnh 2 chọn MAXIM làm `focus`).
- `director_review` duyệt 2/2 cảnh. Người dùng nhận phim.
- Lần đầu chọn "mỗi cảnh một clip" ra 2 clip 15 s; đổi sang chia shot thì được. Đây là gợi ý (1 mẫu) rằng cảnh có biến hình hoặc nhiều nhịp nên chia shot.

**(ii) Làm sai**

Tất cả xảy ra ở lượt 1. Lượt 2 và 3 sửa tay, vai không học lại:
- **(a) Dịch sát chữ:** "mũ" thành đạo cụ mũ bảo hiểm (do `auto_attach`); "xanh" thành blue.
- **(b) Tự viết "mask pulled down under the chin" cho bộ đồ có khẩu trang.** Nhiều khả năng để lộ miệng cho khớp môi, nhưng làm sai thiết kế trang phục. Người dùng chốt: khẩu trang luôn đeo kín.
- **(c) Chèn câu bối cảnh ngoài trời vào shot trong phòng.** Đã sửa bằng code `indoor_spot` (`370dacc`).
- **(d) Khung shot mâu thuẫn:** "medium shot + dép" đứng cạnh "Framing: MCU".
- **(e) Tự bịa động tác nhảy,** trong khi đoạn nhảy lấy động tác từ video mẫu.
- **(f) Giữ thoại cứng của kịch bản dán tay mà không ghi `script_notes`.**

**(iii) Thay đổi đề xuất**
- **KLD-8 [P]** — bổ sung vào `knowledge/roles/director.md` **N4 "Nhân vật đúng thiết kế"** ba câu có lý do. Viết theo cách nghĩ, không phải lệnh trần:
  1. *"Phụ kiện thuộc thiết kế trang phục (khẩu trang, mũ, kính) giữ đúng trạng thái như ảnh OUTFIT trong mọi shot. Muốn đổi (kéo khẩu trang xuống để thấy miệng) thì đó là hy sinh thiết kế: ghi `tradeoffs` và hỏi người dùng, vì trang phục là thứ video đang quảng bá. Ở #22 người dùng chọn đeo kín và chấp nhận khớp môi khó thấy."*
  2. *"Chữ tiếng Việt nhiều nghĩa (xanh = blue/green; mũ = cap/helmet/hood) thì tra ảnh Kho hoặc hồ sơ của vật đó trước khi viết tiếng Anh. Ảnh là chuẩn thật (N4); nghĩa đầu tiên của từ điển không phải."*
  3. *"Shot nhảy hay động tác theo video mẫu: động tác là của video mẫu. `performance` chỉ tả mặt, ánh mắt, cường độ — không tự biên đạo, vì hai nguồn động tác sẽ kéo nhau (#22 lượt 1)."*
- **KLD-9 [P]** — bổ sung vào **Đ6 (`script_notes`)**: *"Kịch bản dán tay (không qua Biên kịch) — đọc to từng câu thoại. Câu nghe như khẩu hiệu hoặc lời quảng cáo (vd 'Hô biến!') ghi `kind: thoại` kèm câu hỏi gợi ý. Không tự sửa (N1). Căn cứ: screenwriter.md B12/B13; #22 lượt 1 người dùng chê thoại cứng."*
- **KLD-31 [P]** — thêm ví dụ ✘/✔ của #22 vào Đ7 hoặc Đ8: "mỗi cảnh một clip 15 s → tự bịa áo liền thân; chia shot → đúng". Ghi rõ độ tin **1 mẫu**, không thành luật.
- **(d)** đã có code kiểm khung (`shots`) nhưng vẫn lọt. Không đề xuất thêm khi chưa có mẫu thứ hai.

**(iv) Bằng chứng:** mục 2.3; diag `director/auto_attach` "mũ", `bad_json_retry` ×2; `ban_thu_1.json` shot 6 "pulled down under the chin"; `feedback_kld_preview_review_0710` mục 3–4.

### 4.3 Đạo diễn viết lại (`director_rewrite`) — không có dữ liệu chạy
- Không có lượt nào. Gen lại ở #22 đi theo hai đường: câu `Fix:` của QC (546, 547, 569) và người dùng sửa tay.
- **Bằng chứng gián tiếp:** câu sửa của QC tả lại lỗi ("yellow tracksuit") và kéo lỗi vào lần sau (mục 2.11). Đây đúng là bệnh mà `prompts/26_director_rewrite.md` sinh ra để chữa ("câu nối cuối thua phần mô tả sai").
- **Đề xuất KLD-34 [C]:** kiểm xem đường tự gen lại **video** của QC có đi qua `director_rewrite` khi cờ bật hay không. Nếu chưa, ghi vào việc học việc / đo ở dự án sau. Không sửa prompt 26 vì chưa có dữ liệu chạy.

### 4.4 Quay phim (DP, Tầng B — `dp_calls` 2 lượt ở lượt 1)

**(i) Làm tốt**
- Lượt 3: máy "almost static" + ảnh render PLACE → nền giữ đúng cầu thang và tháp suốt 3 clip 11,5 s [Mắt].
- Lượt 2: có chuyển động máy → người dùng khen "chuyên nghiệp hơn".
- `camera_setup` A–D có nhãn, dùng được cho `plate_camera`.

**(ii) Làm sai**
- Lượt 1: máy locked-off cả đoạn nhảy → người dùng muốn có chuyển động.
- Lượt 2: push-in và vòng cung trên clip 11,5 s, trong khi nền chưa khóa → tháp và nhà đổi dần.
- Lượt 3: shot 9 "pulls straight back… rising" → khung cuối nửa dưới là sân trống. Luật Q5 "ghi điểm cuối" đã có sẵn, nhưng motion lượt 3 sửa tay nên không ai kiểm.

**(iii) Thay đổi đề xuất**
- **KLD-14 [P]** — thêm vào `knowledge/roles/dp.md` Q5 mục "Model làm tốt / làm hỏng" một dòng dữ liệu #22, giữ đúng giọng "không có nghĩa mặc định":
  - *"#22 (1 dự án, Seedance 2.0 Fast / 2.5, clip 11,5 s ở nơi có render 3D): ✘ push-in hay vòng cung khi nền chỉ có ảnh mô tả → kiến trúc trôi dần. ✔ gần tĩnh + ảnh render PLACE → nền giữ đủ 11,5 s. ✘ lùi + nâng máy ở clip cuối → giây cuối nửa khung là sân trống."*
  - *"Cách nghĩ: clip càng dài và nền càng có mốc (tháp), chuyển động càng phải nhỏ và có điểm cuối được đóng khung. Người dùng vẫn muốn máy có chuyển động — chọn biên độ nhỏ có động cơ chứ không bỏ hẳn."*
- **KLD-13 [C]** — `core/motion_prompt_lint.py` (hoặc `speaker_lint` cùng chỗ): shot có `camera_move` ∈ {pull_out, crane, orbit} mà `motion_prompt` không có câu tả **khung ở giây cuối** → ⚠ ở Bước 3. Chỉ cảnh báo, 0 USD.

**(iv) Bằng chứng:** mục 2.6; khung 52,3 s bản v3; motion shot 7, 9 trong 3 tệp JSON.

### 4.5 Motion (`motion` — 1 lượt ở lượt 1; lượt 2/3 sửa tay)

**(i) Làm tốt** — các câu viết tay ở lượt 2/3 đã có hiệu quả:
- "worn UP… never pulled down" (khẩu trang);
- "dark bob, one solid colour" (tóc Kelly);
- Kelly "xoay người, búng vành mũ, chữ V" thay cho đứng chống hông;
- `start_from_prev_clip` → nối liền tư thế và trang phục.

**(ii) Làm sai**
- Kelly đứng yên sau biến hình ở lượt 2 — người dùng chê.
- Tóc lẫn bạc từ người mẫu trong ảnh OUTFIT (544/545 bị loại, ≈ 2,8 USD) dù prompt đã có câu "chỉ lấy quần áo".
- Câu "pull back" giữ ở clip cuối.

**Đã có sẵn trong code, không đề xuất lại:**
- "Shot N starts with exactly this composition" — tương đương START LOCK.
- "PLACE render… decides architecture over conflicting text" — tương đương khóa nền (`core/seedance_refs.prompt`).

**(iii) Thay đổi đề xuất**
- **KLD-12 [P]** — `prompts/03_video_motion.md`, sửa luật "KHÔNG mô tả lại ngoại hình (ảnh đã cố định)" thành:
  - *"…trừ đường **chỉ-ảnh-tham-chiếu** (Seedance ref-only), nơi không có khung đầu cố định. Ở đường đó, thêm **một câu** chốt những nét mà ảnh tham chiếu dễ làm lẫn: tóc của nhân vật khi ảnh OUTFIT có người mẫu, và trạng thái phụ kiện ('mask worn up over nose and mouth'). Lý do: #22 lượt 2, tóc người mẫu lẫn vào Kelly."*
  - Thêm câu: *"Shot có người mà không có hành động thấy được trong clip (chỉ một tư thế) thì người xem đọc là 'đứng đơ'. Cho một hành động nhỏ có động cơ, trừ khi `why` ghi cố ý tĩnh."* Căn cứ: lượt 2 shot 6 bị chê.
- **KLD-7 [$]** — sửa `core/seedance_refs.prompt`, hàm `says()` cho ảnh OUTFIT: thêm *"ignore the hair, face and body of any person modelling these clothes"* và *"wear each accessory exactly as the picture shows it, for the whole clip"*. Câu tương tự cho ghi chú ảnh tham chiếu OUTFIT ở đường vẽ ảnh (`assets.reference_note`). Thay đổi này động tới đầu ra trả tiền, nên đặt sau cờ hoặc A/B 1 shot rẻ trước.

**(iv) Bằng chứng:** mục 2.2, 2.6; `retry_reason` 544/545; `chat_luong_cao.json` motion shot 6–9.

### 4.6 Dịch (`translate`) — không có dữ liệu chạy
- Không có lượt nào; Director viết tiếng Anh trực tiếp.
- **Gián tiếp:** lỗi "xanh → blue", "mũ → helmet" (4.2) cũng sẽ gặp ở khâu dịch.
- **KLD-32 [P]:** thêm vào prompt khâu dịch câu ở KLD-8 ý 2: chữ nhiều nghĩa → giữ nguyên chữ Việt trong ngoặc và báo, không đoán. Ưu tiên P3 vì chưa có lượt chạy nào.

### 4.7 Tổ QC (`video` QC clip · `qc` QC ảnh Claude · `qc_team` · `scene_qc` lớp 0)

**(i) Làm tốt**
- QC clip bắt đúng tóc lẫn bạc (544/545) và đồ thường ở shot 7 (514/516).
- QC clip `identity` tăng 0,72 → 0,87.
- `clip_measure` chỉ ra mặt mịn ×0,12–0,39 và điểm nhảy vọt của clip 2.0 (566/567 ở 3,2–3,5 s), khớp với điều mắt thấy.
- Hai ảnh QC lớp 0 tự vẽ lại (485, 492) từng được dùng ở bản thử 1.

**(ii) Làm sai**
- **(a)** QC tự gen lại clip 255 vì 0,81 < 0,82 → bản mới 0,72, tệ hơn, mất 2,76 USD. Lỗi "mặt mịn" là **đặc tính** của đường ref-only (×0,12–0,39 ở mọi clip), không phải thứ câu sửa chữa được.
- **(b)** Câu sửa của QC nhắc lại chữ của lỗi ("yellow tracksuit"), kéo lỗi sang lần sau.
- **(c)** `qc_team` chặn 6/9 khung người dùng duyệt. Lý do: `prompts.lock_text` lấy hồ sơ chuẩn **đồ thường** của KELLY/MAXIM cho biến thể KL. Đường video đã sửa việc này ở `370dacc`, nhưng **`lock_text` chưa sửa**.
- **(d)** Lớp 0 đòi vẽ lại theo cỡ cảnh 10 lần, chỉ 2 bản được dùng; người dùng duyệt MS/MLS khi shot xin MCU.
- **(e)** `qc` (QC ảnh Claude) không chạy lượt nào. Mọi phán xét ảnh trước người là lớp 0 + `qc_team`.

**(iii) Thay đổi đề xuất**
- **KLD-5 [$]** — `Pipeline._no_auto_retry` (`core/pipeline.py`) thêm một lý do "không tự gen lại":
  - **Điều kiện:** tiêu chí rớt duy nhất là `identity` do cờ `look_drift` của `clip_measure`, trên clip đi đường Seedance ref-only.
  - **Hành động:** giữ cho người dùng quyết, kèm câu "đặc tính model, gen lại không sửa được (≈ X USD)", và ghi một ca `experience_cases` `kind=model_property`.
  - **Căn cứ:** `docs/CHUAN_XAY_DUNG.md` luật "gen lại phải đổi đầu vào". Câu `Fix: smooth face` không đổi đầu vào thật. Bộ chặn "cùng lỗi lặp lại" hiện chỉ chặn từ lần thứ hai.
- **KLD-15 [P]** — `prompts/12_video_qc.md`, mục `issues`:
  - *"Tả **trạng thái đúng** cần thấy ('KELLY wears the red dinosaur hoodie'), không nhắc lại chữ của thứ sai ('yellow tracksuit'). Chữ của lỗi đi vào prompt lần sau thì model vẽ lại đúng thứ đó."*
  - Với `look_drift` trên clip ref-only: ghi vào `issues` là *"model property — regenerating with the same route will not fix it"*.
- **KLD-4 [C]** — `core/prompts.lock_text`: nhân vật có `outfit_image_ids` → chỉ giữ mặt, tóc, dáng từ hồ sơ chuẩn, thêm *"trang phục: theo ảnh OUTFIT, không theo đồ thường của hồ sơ"*. Làm cùng cách `370dacc` đã làm cho runner. **Phải xong trước khi đo học việc** `qc_team`, nếu không số khớp của học việc sẽ là rác.
- **KLD-16 [C]** — `core/qc_scene.py` khi ở chế độ **học việc** (người dùng duyệt 08/10, đang lập kế hoạch code):
  - `shot_size` luôn là `flag`, không `redraw`;
  - ghi cặp (cỡ đo được, quyết định của người) để hiệu chỉnh `SIZE_FROM`;
  - 9 khung duyệt của #22 là mẫu hiệu chỉnh đầu tiên.
- **(e)** không đề xuất bật `qc` chỉ vì #22. Đó là quyết định cấu hình của người dùng.

**(iv) Bằng chứng:** mục 2.11, 3 (dòng 1–2 = 13,3 USD); `job_events` 569; `KIEM_22` 2.12, 2.14; `prompts.py:507` (`lock_text` không xét OUTFIT).

### 4.8 Editor / Dựng (`editor` LLM — không có dữ liệu chạy; dựng bằng code — có)

**(i) Làm tốt**
- `motion_trim` cắt đuôi đúng 7 clip.
- Chớp trắng đúng giây hô biến (7,5 / 14,04 s).
- 6 bản dựng trong 2 ngày, bản #34 đạt.

**(ii) Làm sai**
- **(a)** Bản dựng #33 gom 4 tệp phụ trong `videos/`. `final_cut.collect_clips` đánh mọi `.mp4` lạ là `usable: True`.
- **(b)** Không có cách bỏ N giây **đầu** clip. Nối 254 → 255 lệch tay, giật ở giây 1,5 của 255. `motion_trim` chưa lần nào dời đầu clip (`KIEM_22` 2.9).
- **(c)** Editor Claude không chạy, nên không ai duyệt bản thô theo ý đồ.

**(iii) Thay đổi đề xuất**
- **KLD-3 [L]** — `core/final_cut.collect_clips`: tệp `.mp4` không thuộc shot nào thì mặc định `usable: False`. Bản dựng liệt kê chúng bằng một dòng "⚠ N tệp lạ trong videos/ không đưa vào", người dùng tích mới đưa vào.
- **KLD-19 [P + C]** — `prompts/24_editor_review.md`, thêm `action` **`trim_head`** (`target_shot`, `amount` 0,2–3 s: bỏ N giây đầu shot). Code áp lên `NN_raw.mp4`, không áp cho shot thoại / khớp môi / `start_from_prev_clip` (vì clip sau mượn khung cuối của clip này). **Trùng TODO "việc để sau" mục 12** — chỉ xếp ưu tiên ở đây.

**(iv) Bằng chứng:** mục 2.10; `outputs.manifest.clips` #33; `final_cut.py:33–41`.

### 4.9 Nhạc / SFX / Phụ đề (`music`, `sfx`, `subtitles`) — LLM không có dữ liệu chạy
- Nhạc làm bằng ClipAI `music_v2` + nhạc gốc, đặt giây tay. Nhún theo nhịp chạy từ `337d0c8` (sửa đọc `.m4a`).
- **Học từ chỗ tốt:** "Nhạc đoạn 2" + nhạc vào 1,8 s + nhún 85 nhịp → người dùng nhận.
- **Học từ chỗ sai:**
  - lượt 1 cảnh 1 không có nhạc;
  - rung trước khi vào nhạc bị chê.
- **Đề xuất:**
  - **KLD-26 [C]**: `delivery` cảnh báo khi rung (`shakes`) hay nhún đặt **trước** giây nhạc nhảy bắt đầu. Đúng ý người dùng "rung/nhún chỉ khi đã vào nhạc". Chỉ là cảnh báo, người dùng vẫn cho phép được.
  - Nhạc theo đoạn cảnh mặc định = **TODO mục 13** (không thêm).
- **Bằng chứng:** mục 2.9; manifest `outputs` #29–#34.

### 4.10 Bảng kê tài nguyên (`asset_checklist`) + Kho / Bible / hồ sơ (code + dữ liệu)

**(i) Làm tốt**
- Gửi ảnh OUTFIT cho shot không người → bộ đồ trên giường đúng mẫu (`40f6111`).
- Gửi OUTFIT ở đường ref-only (`3f1ebf9`).

**(ii) Làm sai**
- Phải dùng mẹo 4 dòng Bible vì Dashboard chỉ gán trang phục theo cả dự án.
- `auto_attach` gắn tài nguyên tên một chữ "Mũ".
- Hồ sơ chuẩn của biến thể KL vẫn là đồ thường (`lock_rules`).
- Mũ Maxim lượt 3 thành "black cap with small red horns" — **chưa người dùng xác nhận**.

**(iii) Thay đổi đề xuất**
- **KLD-11 [C]** — `core/assets.auto_attach`: tài nguyên có tên **một chữ** là danh từ chung (mũ, áo, súng…) thì đưa vào `ambiguous` (người chọn), không tự gắn. Lý do: không ai xác nhận lúc tự gắn (docstring đã nói "stricter than Step 1"), và #22 là ca trùng chữ đầu tiên đã đo.
- **KLD-27 [$ dữ liệu]** — tạo hồ sơ chuẩn cho biến thể trang phục: `lock_rules` của MAXIM KL / KELLY KL ghi đúng bộ Khủng Long Đỏ.
  - Nội dung: mũ đỏ có sừng, khẩu trang đeo kín, tóc Kelly bob đen một màu.
  - Người dùng duyệt từng dòng. Sửa qua màn Kho, không sửa tay CSDL.
  - Câu hỏi chờ người dùng: **mũ Maxim đỏ hay đen** — bản lượt 3 đang đen.
- **KLD-33 [P]** — `prompts/27_asset_checklist.md`, thêm 2 dòng cần kê:
  - *"trang phục có phụ kiện đổi trạng thái được (khẩu trang, mũ trùm): ghi trạng thái mặc định"*;
  - *"ảnh OUTFIT có người mẫu: ghi rõ tóc của nhân vật để prompt chốt"*.

**(iv) Bằng chứng:** mục 2.2; diag `director/auto_attach`; `KIEM_22` 2.12.

### 4.11 Bài học (`lessons`, `lesson_judge`) — không có dữ liệu chạy
- **(i) Không có chỗ làm tốt để học.**
- **(ii) Thiếu sót:**
  - Bảng `lessons` có **0 dòng** trên CSDL thật.
  - `mistakes` dừng ở dự án 13 (193 dòng), vì `harvest()` không tự chạy sau mỗi dự án.
  - `propose()` cần ≥ 3 lỗi ở ≥ 2 dự án, nên bài học "1 dự án" của tổng kết này không có đường vào.
  - `experience_cases` #22 có 33 failure nhưng 0 success, dù 9 ảnh + 9 clip đã được duyệt. **Cần kiểm** `import_review_log`: có thể nó đọc trạng thái hiện tại thay vì lần duyệt.
- **(iii) Đề xuất:**
  - **KLD-21 [C]:** `lessons.harvest()` + `experience.refresh()` chạy (0 USD) mỗi khi dựng bản giao.
  - **KLD-21 [C]:** thêm đường "bài học tổng kết dự án": `source='project_review'`, state `proposed`, ghi độ tin "1 dự án", người duyệt ở tab Bài học. Kèm công cụ `tools/lessons_add.py` (chưa có, xem mục 6).
  - **KLD-22 [L]:** kiểm vì sao 0 ca success.
- **Bằng chứng:** truy vấn bản sao CSDL 08/10 (`lessons` 0, `mistakes` tối đa dự án 13, `experience_cases` dự án 22: image failure 21, video failure 12).

### 4.12 Vai bằng code có lỗi rõ ở #22

**Nền 3D / `place_match` / ảnh toàn cảnh**
- **Tốt:** render đồng trục + ảnh toàn cảnh = render → nền đúng.
- **Sai:**
  - đường vẽ thủ công không dựng lại nền khi đổi chỗ đứng;
  - ảnh toàn cảnh vẽ từ ngoài tường;
  - `place_match` không tách được ảnh đúng với ảnh sai: ảnh đúng 0,31–0,37, ảnh sai 0,36–0,42, ngưỡng `LOW_MATCH = 0.35` ghi "to check on real runs".
- **Đề xuất:**
  - **KLD-6 [C/$]:** so khóa `plan()` với `plates/index.json` ở **mọi** đường gen ảnh/video. Đổi `plate_spot`/`plate_view` mà nền cũ → chặn gửi kèm câu "nền 3D đã cũ — dựng lại (0 USD)". Ô Bước 1 báo 5 trường (`location`, `image_prompt`, `blocking`, `spatial_state`, `action`) còn nhắc chỗ cũ. = **TODO mục 4**, nâng P1.
  - **KLD-17 [C]:** `place_match` ở chế độ chỉ ghi (không cảnh báo đỏ) cho tới khi hiệu chỉnh. Lưu cặp có nhãn người (556–558 đúng; 550–552 sai; 531/532 sai một phần) làm mẫu; đo so với render của **chỗ đứng trong kế hoạch**, không phải nền đang gắn.
    - **Đã code 08/10:** `place_refs.CALIBRATED = False` → `place_match` luôn `info` kèm số; `place_refs.measure()` bỏ qua khi nền đang gắn khác kế hoạch (`stale_plates`); mỗi lần đo lưu `<data>/<id>/place_match.json`; `place_refs.pairs()` gắn nhãn = quyết định cuối của NGƯỜI trong `review_log` (QC không tính).
    - **Cặp có nhãn #22 (mẫu hiệu chỉnh, chỉ ghi ở đây — không sửa CSDL thật):** ảnh 556, 557, 558 = nền **đúng**; 550, 551, 552 = nền **sai**; 531, 532 = **sai một phần**. Khi đủ cặp (≥ 2 dự án) mới đặt lại `LOW_MATCH` rồi bật `CALIBRATED`.
  - **KLD-18:** ảnh toàn cảnh dựng từ render đồng trục = **TODO mục 5**.

**Gen video / `model_router` / chuỗi nối**
- **Tốt:** `start_from_prev_clip`; Kho chủ thể 0 từ chối.
- **Sai:**
  - alias `seedance` = 2.0 (3,60 USD);
  - chuỗi nối và dựng lấy job số lớn nhất, không lấy bản người dùng chọn, nên phải hoán đổi dòng 560 ↔ 569 và làm lệch `qc_results`.
- **Đề xuất:**
  - **KLD-2 [L/$]:** trường "bản dùng cho shot" (`scenes.data.chosen_video_job`, đặt khi người dùng bấm "Dùng bản này"). `start_from_prev_clip`, `final_cut.collect_clips` và `stage_map` đọc trường này trước "job lớn nhất". Cấm hoán đổi dòng job. Với #22: **ghi chú** trong tài liệu (không sửa CSDL) rằng điểm QC của 560/569 lệch tệp.
  - **KLD-23 [UI]:** thẻ cảnh và ô chọn model hiện tên thật + độ phân giải ("Seedance 2.0 · 720p" thay cho `seedance`). = phần còn lại của **TODO mục 3**.

**Dashboard UI / nút gen**
- **Tốt:** sửa nhanh nhiều ô thiếu ở lượt 1; nút gen chỉ gửi cảnh chọn (`ff5dce0`, chưa thử thật).
- **Sai:** job 559 hỏng do `stale_input` vẫn nằm trong nút "↻ Gửi lại clip lỗi (lỗi nhà cung cấp)" (`dashboard/steps/step4.py:162`, truy vấn mọi `failed` chưa escalate) → gửi lại **y nguyên đầu vào cũ** thành job 566 bằng 2.0.
- **Đề xuất KLD-1 [L/$]:**
  - (a) truy vấn của nút loại job có ghi chú `stale_input:` / `missing inputs`;
  - (b) các job đó hiện riêng một dòng "⚠ N clip hỏng vì đầu vào đã cũ — xếp hàng lại từ đầu vào mới" (đi `batch.queue_videos`, có giá);
  - (c) `Pipeline.retry` không có `fix` từ chối job có ghi chú `stale_input` (lớp chặn thứ hai, giống `InvalidTransition`).

**Khớp môi / TTS (`voice`, `lipsync`)**
- **Tốt:** giọng đúng người, đúng giây 1,0 (`1ded677`).
- **Sai:** 0,03 / 0,44 trên đường ref-only + `reference_audio`.
- **Đề xuất KLD-25 [P]:** thêm dữ liệu #22 vào director.md N3 "Rủi ro chưa thử": *"#22: Seedance 2.5 ref-only + reference_audio, giọng ở giây chẵn → 0,03 / 0,44, chưa nhép. Đường đã đạt 0,72–0,96 là `dialogue_take` (#10). Cảnh có trang phục che miệng thì chấp nhận được — người dùng tạm chấp nhận ở #22."* Dự án sau dùng `dialogue_take` cho shot thoại cận (chờ người dùng chọn).

**Tiền / thống kê**
- **KLD-30 [L]:** công cụ thống kê chuẩn hóa `usage_events.at` (`YYYY-MM-DD HH:MM:SS`) và `jobs.created_at` (có `T`) trước khi so chuỗi.
- Ước giá Seedance 2.5 + video ref theo giá web = **TODO mục 6**.

## 5. Danh sách thay đổi chờ người dùng duyệt

Không thay đổi nào được tự bật. Cột **Loại**:
- **prompt** = prompt / knowledge, sau cờ TẮT, rà nhẹ;
- **code-luật** = cảnh báo hoặc chặn bằng code;
- **mặc định** = đổi giá trị mặc định;
- **UI** = giao diện;
- **sửa lỗi** = lỗi sai hành vi.

**Rủi ro tiền:** "giảm" = chặn chi tiêu thừa; "tăng" = có thể làm tốn thêm; "—" = không đụng tiền.

**Công:** S ≤ ½ ngày · M ≈ 1 ngày · L > 1 ngày (gồm test đỏ → xanh).

| Mã | Vai | Thay đổi | Loại | Rủi ro tiền | Công | Ưu tiên |
|---|---|---|---|---|---|---|
| KLD-1 | Dashboard / Gen video | Nút "↻ Gửi lại clip lỗi (lỗi nhà cung cấp)" bỏ job `stale_input` / `missing inputs`; hiện riêng "đầu vào đã cũ → xếp hàng lại từ đầu vào mới"; `Pipeline.retry` không `fix` từ chối job `stale_input` (job 559 → 566) | sửa lỗi | giảm (≈ 1,8 USD/lần ở #22) | S | **P1** |
| KLD-2 | Gen video / Dựng | Trường "bản dùng cho shot" (`chosen_video_job`); chuỗi nối + `collect_clips` + `stage_map` đọc nó; cấm hoán đổi dòng job (sau hoán đổi 560↔569, `qc_results` lệch tệp); ghi chú lệch QC của #22 trong tài liệu, không sửa CSDL | sửa lỗi + dữ liệu | giảm (tránh gen lại vì nối sai clip) | M | **P1** |
| KLD-3 | Editor / Dựng | `final_cut.collect_clips`: `.mp4` lạ trong `videos/` mặc định không dùng, liệt kê ⚠ để người tích | sửa lỗi | — | S | **P1** |
| KLD-4 | Tổ QC (`qc_team`) | `prompts.lock_text`: nhân vật có OUTFIT chỉ khóa mặt/tóc/dáng, trang phục theo ảnh OUTFIT (6/9 khung bị chặn nhầm) — điều kiện trước khi đo học việc | code-luật | — (Claude QC vẫn chạy như cũ) | S | **P1** |
| KLD-5 | Tổ QC (`video`) | `_no_auto_retry`: không tự gen lại khi lỗi duy nhất là `look_drift` trên đường ref-only (đặc tính model); giữ cho người + ghi ca kinh nghiệm | code-luật | giảm (2,76 USD ở clip 255) | S–M | **P1** |
| KLD-6 | Nền 3D | So khóa `plan()` ↔ `plates/index.json` ở mọi đường gen; báo 5 trường còn nhắc chỗ cũ khi đổi chỗ đứng (= TODO mục 4) | code-luật | giảm (1,80 USD ở #22) | M | **P1** |
| KLD-7 | Motion / Gen video | `seedance_refs.says()` (OUTFIT) + ghi chú ảnh OUTFIT đường ảnh: "bỏ tóc/mặt/dáng người mẫu; phụ kiện đeo đúng như ảnh suốt clip" | prompt (trong code) | tăng nhẹ nếu đổi đầu ra — thử 1 shot rẻ trước | S | **P1** |
| KLD-8 | Đạo diễn | director.md N4: 3 câu (phụ kiện trang phục giữ trạng thái — đổi là `tradeoffs`; chữ nhiều nghĩa tra ảnh Kho; động tác theo video mẫu không tự biên đạo) | prompt | — | S | P2 |
| KLD-9 | Đạo diễn | director.md Đ6: kịch bản dán tay → đọc to thoại, câu khẩu hiệu ghi `script_notes` kind thoại | prompt | — | S | P2 |
| KLD-10 | Biên kịch / UI | Nút tùy chọn "Biên kịch đọc thoại" cho kịch bản dán tay (B12/B13, có giá trước) | UI + prompt | tăng nhỏ (1 lượt Claude, người bấm) | M | P3 |
| KLD-11 | Kho / `auto_attach` | Tên tài nguyên một chữ là danh từ chung → `ambiguous`, không tự gắn ("Mũ") | code-luật | — | S | P2 |
| KLD-12 | Motion | prompts/03: ngoại lệ đường ref-only (1 câu chốt tóc / phụ kiện); shot có người cần một hành động thấy được trừ khi `why` ghi cố ý tĩnh | prompt | — | S | P2 |
| KLD-13 | Quay phim / Motion | Lint: `pull_out` / `crane` / `orbit` thiếu câu tả khung ở giây cuối → ⚠ Bước 3 | code-luật | — | S | P3 |
| KLD-14 | Quay phim | dp.md Q5: dòng dữ liệu #22 (push-in / vòng cung nền trôi; gần tĩnh + PLACE giữ 11,5 s; lùi + nâng máy để sân trống) — độ tin 1 dự án | prompt | — | S | P2 |
| KLD-15 | Tổ QC (`video`) | prompts/12: `issues` tả trạng thái đúng, không nhắc chữ của lỗi; `look_drift` ref-only ghi "model property" | prompt | giảm (bớt lỗi kéo sang lần sau) | S | P2 |
| KLD-16 | Tổ QC (`scene_qc`) | Ở học việc: `shot_size` chỉ `flag`, ghi cặp (đo, người) để hiệu chỉnh `SIZE_FROM`; 9 khung duyệt #22 làm mẫu đầu | code-luật | giảm (≈ 0,5 USD / dự án) | S (gộp kế hoạch học việc) | P2 |
| KLD-17 | Nền 3D (`place_match`) | Chỉ ghi, không cảnh báo đỏ tới khi hiệu chỉnh; lưu cặp có nhãn 550–558, 531/532; đo so với render chỗ đứng trong kế hoạch | code-luật | — | M | P2 |
| KLD-18 | Nền 3D (`scene_establishing`) | Ảnh toàn cảnh = render đồng trục khi chỗ đứng có 3D (= TODO mục 5) | code-luật / mặc định | giảm (bỏ ảnh AI toàn cảnh) | M | P2 |
| KLD-19 | Editor | prompts/24 + code: action `trim_head` (bỏ N giây đầu; không áp shot thoại / nối) (= TODO mục 12) | prompt + code | — (0 USD dựng lại) | M | P2 |
| KLD-21 | Bài học | Tự `harvest()` + `experience.refresh()` khi dựng bản giao; đường "bài học tổng kết dự án" (`source=project_review`, state proposed, độ tin) + `tools/lessons_add.py` | code-luật | — | M | P2 |
| KLD-22 | Bài học | Kiểm `experience.import_review_log`: #22 có 0 ca success dù 9 ảnh + 9 clip từng duyệt | sửa lỗi | — | S | P3 |
| KLD-23 | Dashboard / Gen video | Thẻ cảnh + ô chọn model hiện tên thật + độ phân giải (phần còn lại TODO mục 3) | UI | giảm (3,60 USD gửi nhầm 2.0 ở #22) | S | P2 |
| KLD-25 | Đạo diễn / Khớp môi | director.md N3: dữ liệu #22 (ref-only + reference_audio 0,03 / 0,44; `dialogue_take` từng 0,72–0,96; trang phục che miệng thì chấp nhận) | prompt | — | S | P2 |
| KLD-26 | Dựng / Hậu kỳ | Cảnh báo rung / nhún đặt trước giây nhạc nhảy vào | code-luật | — | S | P3 |
| KLD-27 | Kho / hồ sơ | Hồ sơ chuẩn biến thể KL (khẩu trang đeo kín, tóc bob đen một màu) qua màn Kho. **XONG 08/10: mô tả chuẩn ghi vào Kho #416 (nam) / #417 (nữ), người dùng duyệt; #22 không sửa.** **Người dùng xác nhận 08/10: mũ Maxim KL là MŨ ĐEN SỪNG ĐỎ** (lượt 3 đúng); mô tả cũ "mũ đỏ có sừng" sai vì chỉ nhìn ảnh chính diện → hồ sơ/prompt phải sửa theo | mặc định / dữ liệu | — | S (+ người duyệt) | P2 |
| KLD-30 | Tiền / thống kê | Chuẩn hóa định dạng giờ `usage_events.at` ↔ `jobs.created_at` trong công cụ thống kê | sửa lỗi | — | S | P3 |
| KLD-31 | Đạo diễn | Ví dụ #22 (mỗi cảnh một clip 15 s → bịa áo; chia shot → đúng), độ tin 1 mẫu | prompt | — | S | P3 |
| KLD-32 | Dịch | Prompt dịch: chữ nhiều nghĩa giữ nguyên + báo, không đoán | prompt | — | S | P3 |
| KLD-33 | Bảng kê tài nguyên | prompts/27: kê trạng thái mặc định phụ kiện trang phục; ảnh OUTFIT có người mẫu → ghi tóc nhân vật | prompt | — | S | P3 |
| KLD-34 | Đạo diễn viết lại | Kiểm đường tự gen lại video của QC có qua `director_rewrite` khi cờ bật; chưa thì đo ở dự án sau | code-luật (kiểm) | — | S | P3 |

**Đếm:** P1 = 7 · P2 = 14 · P3 = 9 · tổng 30. Mã 20, 24, 28, 29 bỏ trống vì là việc đã có ở TODO (mục 6, 9) hoặc trái chính sách tiền 04/10 ("chỉ cảnh báo").

**Thứ tự làm gợi ý:**
1. KLD-1, KLD-3 (sửa lỗi nhỏ, chặn tiền ngay).
2. KLD-4 (để học việc `qc_team` đo được).
3. KLD-2, KLD-5, KLD-6.
4. KLD-7 (cần thử 1 shot rẻ).
5. Các mục P2 prompt (KLD-8, 9, 12, 14, 15, 25), gom một đợt sau cờ TẮT.

## 6. Bài học đưa vào đường chuẩn

**Cách nạp (không chạy trong phiên này).**
- **Bảng `lessons`:** hiện **không có công cụ CLI** nạp bài học tay. `devsys/` chỉ đọc `lessons`; `tools/` chỉ có `lessons_retire.py`. Hàm gần nhất là `core.lessons.add_research(conn, group, title, body, url)`, nhưng nó gắn `source='research'`, nên bài học sẽ rơi vào mục "nguồn web" của tài liệu — sai nhãn. Vì vậy đề xuất **KLD-21** thêm `tools/lessons_add.py`. Lệnh sẽ dùng (chạy thử trước, rồi `--yes` sau khi sao lưu CSDL; nhóm ∈ `director` / `motion` / `qc` theo `core.knowledge.GROUPS`):
  ```
  py tools/lessons_add.py --db data/manifest.sqlite --from docs/TONG_HOP_3_LUOT_KHUNG_LONG_DO.md --section 6 --source project_review:22 --dry-run
  ```
  Bài học vào ở trạng thái `proposed`; người dùng duyệt ở tab Bài học (khi đó `sync_knowledge` mới ghi vào tài liệu mà Director / Motion / QC đọc).
- **Đường có sẵn ngay** (ca kinh nghiệm, không cần công cụ mới) — chạy từ `D:\AI-Video-Pipeline`, sau khi sao lưu, mỗi bài một lệnh:
  ```
  py -c "import sqlite3; from core import experience as e; c=sqlite3.connect('data/manifest.sqlite'); c.row_factory=sqlite3.Row; print(e.record(c, key='kld22:L1', stage='video', outcome='failure', note='<phát hiện>', source='tong_hop_kld_2026-10-08', project_id=22, kind='lesson', confirmed_by='user'))"
  ```
- **`.claude-memory/projects/ai-video-pipeline.md`:** đã thêm mục "Bài học tổng hợp 3 lượt KLD — 08/10" (chỉ phần chưa có ở memory).

| # | Nhóm | Tiêu đề | Bối cảnh | Phát hiện | Nguồn |
|---|---|---|---|---|---|
| L1 | qc | Mặt mịn của Seedance ref-only không sửa được bằng gen lại | Clip 255 (#22 lượt 3), QC 0,81 < 0,82 | Tự gen lại ra 0,72, tệ hơn, mất 2,76 USD; `clip_measure` đo mặt mịn ×0,12–0,39 ở mọi clip ref-only → đặc tính model, không phải lỗi của lần gen | job 560/569, diag `clip_measure` (mục 2.11) |
| L2 | qc | Câu sửa của QC không được nhắc chữ của lỗi | QC ghi "yellow tracksuit" vào câu sửa | Chữ của lỗi đi vào prompt lần sau và kéo lỗi lại; tả trạng thái đúng thay vì thứ sai | `DU_AN` lượt 3, mục 2.11 |
| L3 | qc | Khóa nhận dạng của biến thể trang phục phải bỏ quần áo đồ thường | `qc_team` chặn 6/9 khung người duyệt | `lock_text` dùng hồ sơ đồ thường cho KELLY KL / MAXIM KL → chấm sai "không phải croptop trắng"; khớp 73 % ≈ "luôn chặn" 76 % | `KIEM_22` 2.12 |
| L4 | qc | Đo cỡ cảnh bằng chiều cao mặt lệch với mắt người | Lớp 0 đòi vẽ lại 10 lần | Chỉ 2/10 bản vẽ lại được dùng; người dùng duyệt MS/MLS khi shot xin MCU → cờ đo nên là ghi chú cho tới khi hiệu chỉnh | `KIEM_22` 2.14, mục 2.5 |
| L5 | director | Phụ kiện trang phục là thiết kế, không phải công cụ khớp môi | Director viết "mask pulled down" để lộ miệng | Người dùng chốt khẩu trang luôn đeo; đổi trạng thái phụ kiện là hy sinh thiết kế (ghi `tradeoffs`, hỏi người dùng) | `ban_thu_1.json` shot 6, `feedback_kld_preview_review_0710` |
| L6 | director | Chữ Việt nhiều nghĩa phải tra ảnh Kho | "mũ" thành mũ bảo hiểm (`auto_attach`), "xanh" thành blue | Nghĩa đầu của từ điển sai; ảnh Kho / hồ sơ là chuẩn | diag `director/auto_attach`, mục 2.3 |
| L7 | director | Động tác nhảy theo video mẫu, không tự biên đạo | Director bịa động tác ở lượt 1 | Hai nguồn động tác kéo nhau; ảnh chỉ để mặt + đồ + nơi | mục 2.3, `feedback_continuity_storyboard` |
| L8 | motion | Đường ref-only cần một câu chốt tóc và phụ kiện | Tóc người mẫu OUTFIT lẫn vào Kelly (544/545 bị loại) | Luật "không tả lại ngoại hình" chỉ đúng khi có khung đầu cố định; ref-only thì không có | `retry_reason` 544/545 |
| L9 | motion | Clip dài trên nền có mốc: chuyển động nhỏ, đóng khung điểm cuối | Clip nhảy 11,5 s | Push-in / vòng cung → nền trôi; gần tĩnh + PLACE → giữ 11,5 s; lùi + nâng máy → sân trống ở giây cuối. Người dùng vẫn muốn máy có chuyển động | mục 2.6, [Mắt] bản v2/v3 |
| L10 | motion | Nhân vật đứng tư thế suốt clip bị đọc là "đơ" | Kelly chống hông sau biến hình (lượt 2) | Cần một hành động nhỏ có động cơ, trừ khi cố ý tĩnh | mục 2.6, `feedback_kld_preview_review_0710` |
| L11 | director | Thoại dán tay cần được đọc to | "Hô biến!" lọt qua vì không đi Biên kịch | Director giữ nguyên văn (N1) nhưng phải ghi `script_notes` kind thoại | mục 2.1 |
| L12 | (code) | Job hỏng vì đầu vào cũ không phải lỗi nhà cung cấp | Job 559 `stale_input` được gửi lại y nguyên thành 566 (2.0) | Nút gửi lại phải tách lý do hỏng | `job_events` 559, `step4.py:162` |
| L13 | (code) | Không hoán đổi dòng job để chọn bản | Hoán đổi 560 ↔ 569 để chuỗi nối lấy đúng clip | `qc_results` theo số job → điểm QC lệch tệp; cần trường "bản dùng cho shot" | `job_events` 560/569 |
| L14 | (code) | Thư mục `videos/` không phải danh sách dựng | Bản dựng #33 có 4 tệp phụ | `collect_clips` gom mọi `.mp4` lạ là dùng được | manifest #33 |
| L15 | (code) | `place_match` ngưỡng 0,35 không tách đúng / sai | Ảnh sai chỗ 0,36–0,42 qua; ảnh duyệt 0,31 bị cảnh báo | So với nền đang gắn nên nền gắn sai vẫn qua; cần mẫu có nhãn + so với kế hoạch | mục 2.5 |
| L16 | (quy trình) | Đường bài học chưa chạy | `lessons` 0 dòng; `mistakes` dừng ở dự án 13 | `harvest` / `propose` không tự chạy; ngưỡng ≥ 2 dự án chặn bài học tổng kết 1 dự án | truy vấn CSDL 08/10 |
| L17 | (tổng) | Tiền không vào bản giao | 3 lượt #22 | ≈ 22,5 / 48,5 USD ảnh + video không vào bản giao nào; 7,9 USD tránh được bằng thao tác / cấu hình; 13,3 USD từ QC + đặc tính model | mục 3 |
| L18 | (tổng) | "Chất lượng cao" chưa có số đo rõ nét hơn | Lượt 3: 3 clip 2.5 720p | `clip_measure` mặt mịn 2.5 (×0,12–0,24) không tốt hơn Fast (×0,22–0,31); chỉ mắt người phân biệt được | mục 0 |
| L19 | director | Ảnh toàn cảnh phải cùng hướng nhìn với nền mong muốn của shot | Cảnh nhảy lượt 3 (254–256, chân cầu thang `bac_thang_giua`); lượt 1–2 ảnh toàn cảnh vẽ từ ngoài tường | Ảnh toàn cảnh khác hướng camera khung đầu kéo cả ảnh shot sai nền (prompt cũ + toàn cảnh ngoài tường thắng render 3D); lượt 3 dùng render 3D đồng trục cùng hướng máy → nền cầu thang + tháp giữ đúng suốt 3 clip. Khi chọn chỗ đứng / hướng máy, toàn cảnh phải nhìn cùng hướng với nền shot cần; chỗ có 3D thì lấy render đồng trục (KLD-18) | mục 2.4, `.claude-memory` bài học 07/10, người dùng 08/10 |
