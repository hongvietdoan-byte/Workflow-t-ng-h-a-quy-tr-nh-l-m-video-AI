# Kế hoạch M2.10 — gói gửi TỐI GIẢN (prompt ngắn + ref đúng vai) — 2026-10-21

Mã việc: C-M210-DESIGN (cloud-E). Phần (1) tài liệu này; phần (2) `core/lean_package.py` SHADOW (cờ `lean_package` TẮT, `verified` False).
Không đổi gói thật, không gửi gì, 0 USD. A/B thật trên #31/#33 = Cấp 3, chờ EP.

## 0. Vì sao — số liệu gói thật (docs/data/goi_gui_31_33_2026-10-21.md, CSDL chỉ đọc)

| | prompt ký tự TB (max) | ref TB (max) | vai ref nhiều nhất |
|---|---|---|---|
| #31 ảnh (101 gói, gpt-image-2.5-sunburst) | 5 380 (11 473) | 6,2 (9) | character 287 · object 112 · place_render 104 · character_form 75 |
| #33 ảnh (35) | 11 059 (13 419) | 5,8 (7) | character 102 · place_render 70 · previous_scene 30 |
| #31 video (67; seedance 53 / kling 14) | 3 029 (4 858) | 4,9 (15) | character 115 · start_frame 67 · reference_only 54 |
| #33 video (15, seedance) | 4 045 (4 679) | 8,5 (13) | reference_only 49 · character 34 · start_frame 15 · reference_video 15 |

Đọc mẫu job 1110 (ảnh #31): **cùng một ý nói 3–4 lần** — "Image 1 là nền 3D, giữ kiến trúc" xuất hiện ở câu mở, ở dòng vai Image 1, ở "The place is
decided by the 3D render…", ở "Background: exactly the 3D render…", ở "Draw the background only as Image 1 shows it…"; dạng bóng mờ của Kelly nói
ở dòng vai Image 2, dòng vai Image 3, câu "Exception: KELLY is in a special form…", "Identity lock — … in THIS shot Kelly is in the ghost form…".
Job 1036 (video): có khung đầu nhưng vẫn gửi Kelly + dạng + Xúc tu ×2 + SKORP; dòng vai nói về Image 5/6 (render nơi chốn) mà danh sách ref có 6
ảnh — **gọi tên tài sản lệch số thứ tự** là rủi ro thật của prompt dài.

Mẫu Weave Canvas (Deepix): khung storyboard ~60 từ gọi "Figure 1 / Figure 2"; video MỘT câu ("Use frame 1 as start, frame 2 as end… They happily
hug each other."). Tài liệu chính thức (knowledge/reference_assets_prompting.md, docs/NGHIEN_CUU_PROMPT_THAM_CHIEU_2026-09-30.md): mỗi tài sản
**một** việc + một dòng vai (lấy gì / KHÔNG lấy gì); có video mang động tác thì KHÔNG tả lại; không nhồi danh sách cấm; tài sản mâu thuẫn → **thay
tài sản**, không thêm câu phủ định.

## 1. Nguyên tắc gói tối giản

1. **Ảnh mang "cái gì", chữ mang "làm gì".** Mặt, tóc, trang phục, dạng, vật, nơi chốn, bố cục → ảnh. Chữ chỉ còn: hành động, cảm xúc, cỡ cảnh /
   máy, thoại, và vài điều ảnh KHÔNG nói được (tỉ lệ đo, ai KHÔNG có trong khung, quay lưng, mức gợi).
2. **Mỗi ref một dòng vai** (≤ 25 từ): "Image N is X: lấy …; không lấy …". Thứ tự dòng = thứ tự ref gửi (đánh số do code, không do Đạo diễn).
3. **Thân lệnh 2–4 câu**: (a) cỡ cảnh + máy (từ BYĐ `may`), (b) hành động đầu → cuối (từ chữ shot / BYĐ `hanh_dong`), (c) thoại / cảm xúc nếu có,
   (d) một câu giữ an toàn nếu cần (≥ 2 người: "không đổi mặt / đồ giữa người").
4. **Câu GIỮ chép nguyên** từ gói thật (mục 4) — không viết lại, để A/B chỉ khác phần đã chủ ý bỏ.
5. **Ref tối thiểu**: một ảnh / người (góc thứ 2 bỏ), trùng sha bỏ, người / vật không có trong BYĐ bỏ, có khung đầu thì nơi chốn bỏ.

## 2. Bảng theo loại shot — bộ ref tối thiểu + câu vai + thân lệnh

Tên gọi tài sản theo model: ảnh Deepix (gpt-image) `Image N`; Seedance `@Image N` / `@Video N`; Kling `<<<image_N>>>` / `<<<video_1>>>`.

| Loại shot (mã code) | Bộ ref TỐI THIỂU theo thứ tự | Câu vai mẫu | Thân lệnh (2–4 câu) |
|---|---|---|---|
| Ảnh khung đầu 1 người (`anh_1_nguoi`) | 1 nền 3D đúng máy · 1 ảnh người | "Image 1 is the exact background (3D render, this camera): keep its layout, draw the people into it." · "Image 2 is KELLY: face, hair, outfit, build — not pose, camera or background." | "Wide shot, eye-level camera, static." + hành động 1 câu + (tỉ lệ đo M3.3 GIỮ) |
| Ảnh nhiều người (`anh_nhieu_nguoi`) | nền · mỗi người 1 ảnh (≤ 3 người; ≥ 3 → luật 12: khung có đủ người, white-model) | mỗi người một dòng riêng, cấm gộp | + "The people are different individuals: never swap faces, hair or outfits between them." + "X is NOT in this frame" (BYĐ `khong_duoc_co`) |
| Ảnh có vật (`anh_co_vat`) | nền · người · 1 ảnh vật (chỉ vật có trong BYĐ `vat`) | "Image N is the object SKORP (KELLY cam): exact shape and colours." | + câu tỉ lệ vũ khí "Weapon scale:" GIỮ (ảnh vật không cho cỡ so với người) |
| Ảnh đổi skin / trang phục / dạng (`anh_doi_dang`) | nền · ảnh người (mặt) · ảnh dạng / trang phục | "Image 2 is KELLY: face, hair and build only — NOT the clothes." · "Image 3 is KELLY's ghost form: body surface, colours, glow." | không tả lại dạng bằng chữ (ảnh 3 mang) |
| Ảnh đổi nền giữa cảnh (thẻ `doi_nen`) | thay ĐÚNG 1 ref nền + 1 dòng vai | "Image 1 is the exact background…" (ref mới) | không đổi câu khác — xem mục 5 |
| Video có khung đầu (`video_khung_dau`) | khung đầu · 1 ảnh / người (định danh khi quay / đi) · vật đang cầm / ném | "@Image 1 is the first frame (作为首帧): start exactly on it." · "@Image 2 is Kelly: identity only (face, hair, build)." | hành động đầu → cuối 1–2 câu + máy 1 câu (+ thoại). Bỏ nơi chốn, bỏ dạng (khung đầu đã ở dạng) |
| Video khung đầu + cuối (`video_dau_cuoi`) | khung đầu · khung cuối · (người chỉ khi quay mặt mới lộ) | "@Image 1 is the first frame, @Image 2 the last frame: end exactly on it." | mẫu Weave: 1 câu nối hai khung |
| Video ref hành động (`video_ref_hanh_dong`) | khung đầu · người · video | "@Video 1 gives only the movement and timing — not its people, place, camera or HUD text." | KHÔNG tả lại động tác; chỉ thứ tự giai đoạn + trạng thái cuối |
| Video không khung đầu (`video_khong_khung_dau`) | nền · người · vật như ảnh | như ảnh | như video có khung đầu |

Giới hạn số ref (code kiểm, `core/lean_package.CAPS`): ảnh gpt-image ≤ 6 (cứng 16), Seedance ≤ 8 (cứng 30, tài liệu khuyên 1–8 chủ thể), Kling ≤ 7,
có video ≤ 4 (cứng theo tài liệu B), có khung đầu → element ≤ 3. Vượt trần tối giản → bỏ theo thứ tự ưu tiên ngược (bầu trời → cảnh trước → vật →
dạng), ghi lý do `vuot_tran_model`.

## 3. Luật chọn ref (code `select`, mỗi ref bỏ có MÃ lý do)

| Mã | Khi nào bỏ | Vì sao |
|---|---|---|
| `trung_sha` | ảnh trùng sha với ref đã giữ | gửi 2 lần cùng ảnh (#31 video có khung đầu vẫn gửi lại character / location — đề C-M210 trong docs/CLOUD_TASKS.md ghi "9 ref trùng sha", phiên chính đếm trên CSDL thật; chưa kiểm lại ở nhánh này) |
| `goc_thu_2` | ảnh thứ 2+ cùng một người / vật | 1 ảnh đủ định danh; nhiều góc = thử A/B riêng |
| `khong_trong_khung` | người không có trong BYĐ `thanh_phan` hoặc vai `khong_duoc_co` | model vẽ người có ảnh (#31 thêm người lạ) |
| `vat_khong_trong_byd` | vật không có trong BYĐ `vat` (v2 hoặc chuỗi v1) | ảnh không gọi tên bị dùng lỏng |
| `nen_rong_trung` | place_render thứ 2 (góc rộng cùng trục) | nền đã có ảnh 1; tỉ lệ đã có câu đo M3.3 |
| `trung_nen` | location / atmosphere_place khi đã có nền 3D | cùng một việc |
| `trong_nha` | atmosphere_sky khi BYĐ `noi_chon.trong_nha` = true | không thấy trời |
| `khung_dau_mang_noi_chon` | video có khung đầu: location / landmark / place_render | khung đầu giữ nơi chốn + máy tốt hơn chữ (luật 11) |
| `khung_dau_da_o_dang` | video có khung đầu: character_form khi dạng KHÔNG đổi theo nhịp | khung đầu đã vẽ dạng — **rủi ro G37**, A/B mới chốt |
| `khung_dau_mang_vat` | video có khung đầu: vật BYĐ `cach` = dat / deo | vật đứng yên đã trong khung |
| `chi_thay_lung` | video có khung đầu: người chỉ thấy lưng cả shot (BYĐ `thay` = lung) | không có mặt để giữ |
| `vuot_tran_model` | vượt trần tối giản / cứng của model | xem mục 2 |

Ref vai lạ (`reference_only`, `cast`, không nhãn) → GIỮ + cảnh báo `vai_khong_ro` (không đoán). BYĐ thiếu → giữ mọi người / vật (bỏ trùng),
cảnh báo `thieu_byd` — không im lặng (CHUẨN 1).

## 4. Câu trong builder hiện tại: GIỮ / BỎ / ĐỔI

| Câu (nơi sinh) | Quyết | Lý do |
|---|---|---|
| Mở đầu "Image 1 is this shot's 3D render: keep exactly…" + "The place is decided by the 3D render…" + "Background: exactly the 3D render…" + "Draw the background only as Image 1 shows it" (assets / plate_anchor) | **ĐỔI** → 1 dòng vai nền | nói 4 lần một ý |
| "Background — measured on the 3D map … the first structure … horizon" (plate_anchor) | **BỎ** | ảnh nền mang |
| `plate_view_sentence` video "only a reference for the shape and material…" (seedance_refs) | **BỎ** (ref nơi chốn bị bỏ khi có khung đầu) | khung đầu quyết bố cục |
| "Camera and scale, measured on the 3D map…" (place_refs, câu vị trí / cỡ M3.3) | **GIỮ** | cỡ người trong khung ảnh không nói được (lỗi tỉ lệ đã đo) |
| "Real sizes: …" (assets) | **BỎ** | trùng câu đo trên |
| "Weapon scale: …" (prop_lock) | **GIỮ** | ảnh vật không cho cỡ so với người |
| "Fix: …" (sửa của người / QC) | **GIỮ** | dữ liệu người — không bỏ |
| Câu "glows / glow…" của prop lock riêng dự án | **GIỮ** khi vật được giữ | ảnh vật có thể là bản không glow |
| Dòng vai từng người "the person called X … must be exactly this person (same face…)" | **ĐỔI** → "Image N is X: face, hair, outfit, build — not pose, camera or background" | ngắn hơn ~4 lần |
| "Each person keeps ONLY the look of…" + "Before drawing, pick ONE unmistakable visual anchor" + "exaggerate their point of difference" (assets) | **ĐỔI** → 1 câu "never swap…" khi ≥ 2 người; anchor / exaggerate **BỎ** (A/B) | trùng dòng vai |
| "Identity lock — …" + "The costume of X follows the profile above…" (runner / character_forms) | **BỎ** khi có ảnh người; ghi chú tóc/áo chỉ GIỮ khi ảnh trang phục lẫn tóc (mục 7) | ảnh thắng chữ; chữ trái ảnh làm kéo nhau |
| "ignore any clothing or hair words in the scene text that contradict…" | **BỎ** | thân lệnh mới không còn chữ tả áo/tóc |
| "Render style: …" / "Style lock: …" (looks) | **GIỮ câu đầu** | ảnh cùng phong cách nhưng model video hay trôi sang anime |
| "Background in focus; not a cinematic movie still…" | **GIỮ** | lỗi DOF đã gặp |
| "X is NOT in this frame (they appear in other frames…)" (scene_storyboard) | **GIỮ** (sinh lại từ BYĐ `khong_duoc_co`) | ảnh không nói được ai vắng |
| "X stays with the back to the camera…" (`back_view`, seedance_refs) | **GIỮ** (từ BYĐ `thay` = lung) | #27 Seedance quay người |
| "… only hinted — deep shadow…" (looks, câu 'chỉ gợi') | **GIỮ** | an toàn nội dung |
| "Any white banner or red mark on a reference picture is an annotation…" | **GIỮ** khi ref còn nhãn | ảnh có nhãn |
| "Reference images are attached, grouped per named subject." · "Setting: …" · "Same place, same light, same characters and outfits throughout." | **BỎ** | không mang thông tin |
| "Image N is the storyboard frame of Shot N: … starts with exactly this composition" | **ĐỔI** → dòng vai khung đầu | |

Code: bảng này là `core/lean_package.SENTENCE_FAMILIES` (mã, mẫu nhận, quyết, lý do); báo cáo shadow liệt kê họ câu có trong gói thật + quyết.

## 5. Đổi skin / nền giữa cảnh = thay 1 ref + 1 dòng

- Đổi trang phục / skin từ shot K: BYĐ `thanh_phan[].dang` (hoặc ref `character_form` mới) → gói tối giản **thêm / thay đúng ảnh dạng** + dòng
  "Image N is X's <dạng>: body surface, colours" và dòng người đổi thành "face, hair and build only — NOT the clothes". Không thêm câu nào khác.
- Đổi nền: BYĐ `noi_chon.kho_id` khác shot trước → thay ref nền (place_render của máy mới) + dòng vai nền giữ nguyên chữ. Shadow gắn thẻ `doi_nen`
  khi biết BYĐ shot trước.
- Nối M8.1b ("đổi đầu vào kiểu Weave"): người gắn 1 ảnh + 1 câu → code đổi đúng 1 ref + 1 dòng; đánh dấu cũ ảnh/clip phụ thuộc (S-D).

## 6. Tiếng Việt

- Thoại: gửi THẲNG tiếng Việt trong ngoặc kép (`X says in Vietnamese: "…"`) — Seedance 2.5 nhận nhiều ngôn ngữ; dịch làm sai khẩu hình / nghĩa.
- Chữ tả hành động: tiếng Anh ngắn (builder hiện đã tiếng Anh). Đề xuất thử A/B: (A) hành động tiếng Anh, (B) hành động tiếng Việt gửi thẳng —
  cùng ref, đo đạt lần đầu. Tên riêng: bỏ dấu (như `ascii_name`) trong dòng vai để khớp chữ hành động.

## 7. Rủi ro + chốt an toàn

| Rủi ro | Chốt |
|---|---|
| ≥ 3 người: bỏ ảnh góc 2 làm trôi mặt người phụ | luật 12: khung đầu có đủ người (white-model); 3 người giữ 1 ảnh / người + câu "never swap"; báo `nhieu_nguoi_3` trong báo cáo |
| Ảnh trang phục lẫn tóc (form ref có tóc khác) | dòng dạng nói "not the hair" + GIỮ ghi chú tóc 1 cụm khi `dang` có; A/B riêng |
| Model bỏ qua ref không gọi tên | mỗi ref giữ đều có đúng 1 dòng vai đánh số (test: số dòng vai = số ref) |
| Bỏ dạng khi có khung đầu → mất dạng (G37) | dạng đổi theo nhịp (`dang` là bảng) luôn giữ; A/B trước khi bật |
| Bỏ câu đo nền → tỉ lệ người sai | câu "Camera and scale" GIỮ |
| BYĐ thiếu / sai | không bỏ người / vật theo BYĐ thiếu; cảnh báo `thieu_byd` |
| Cờ bật nhầm | shadow chỉ GHI tệp + 1 dòng ⚙; không đổi gói gửi (test byte); `verified` False |

## 8. Chỉ số đo (báo cáo shadow + A/B)

1. Độ dài prompt (ký tự, từ) thật → tối giản, tỉ lệ; mục tiêu ảnh ≤ 1 200 ký tự, video ≤ 800.
2. Số ref thật → tối giản; ref bỏ theo mã lý do.
3. Phủ BYĐ: trường BYĐ có giá trị mà gói tối giản không còn nói (`khong_con_noi` + lý do "ảnh mang" / "chưa dùng").
4. Tỉ lệ đạt lần đầu (A/B thật, Cấp 3): ảnh duyệt không sửa / video không gen lại; lỗi theo loại (mặt, dạng, tỉ lệ, người lạ).

## 9. Phần code SHADOW (đã làm trong nhánh này)

- `core/lean_package.py`: `classify` (loại shot + thẻ), `select` (ref giữ / bỏ + mã), `role_lines`, `body`, `families` (họ câu + quyết),
  `build` (gói tối giản + báo cáo so sánh trong cùng một bảng: prompt, refs, độ dài, ref giữ / bỏ, họ câu, phủ BYĐ — KHÔNG có đường gửi),
  `shadow(pkg_text, scene_data, …)` thuần (không ném lỗi), `note` (một dòng ⚙), `write(…)` ra tệp, `shadow_job` (runner).
  Dạng `thuong` (và bình thường / mặc định) là mặc định — không tính là đổi dạng; `thanh_phan` có vật / mốc không tính là người.
- Chạy ở đâu: (a) **runner** `_Runner._say_package` — SAU khi gói thật đã ghi + commit + ghi sổ chi; cờ TẮT = chỉ `features.on` rồi về (test:
  `shadow` không được gọi); cờ BẬT = đọc `jobs.sent_package` (đúng gói đã gửi), ghi `<data_dir>/lean_package/<project>/job_<id>.json` + 1 dòng ⚙
  mã `lean_package`; lỗi bị nuốt thành 1 dòng ⚙, không bao giờ chặn. (b) **công cụ** `tools/lean_package_shadow.py --db … --project N` chạy
  trên gói ĐÃ gửi (CSDL mở `mode=ro`, 0 USD) — đây là đường phiên chính dùng cho #31/#33.
- Acceptance: golden byte giữ (gói thật không đổi khi cờ BẬT hay TẮT); test theo 8 loại shot; số dòng vai = số ref giữ; mỗi ref bỏ có mã.
- Rollback: tắt cờ (mặc định đã tắt) hoặc revert commit. Khi BẬT, ghi ra: tệp trong `lean_package/` + MỘT dòng `diag_events` (mã `lean_package`)
  mỗi lần gửi — không cột / bảng nào khác của CSDL.
- Preset "experimental" (🧪 Thử nghiệm — bật hết cờ chưa thử thật, `core/features.state`) CŨNG bật `lean_package` (không nằm trong
  `OPT_IN_ONLY` vì không tiêu tiền — danh sách đó là "tự tiêu tiền"). Hệ quả: máy chạy preset đó ghi thêm tệp + 1 dòng ⚙ mỗi lần gửi, 0 USD,
  gói gửi không đổi (test vòng gửi thật). Muốn TẮT hẳn trên máy đó: `FEATURE_LEAN_PACKAGE=0` hoặc chọn TẮT ở 🧪.
- Rủi ro mở: chất lượng gói tối giản CHƯA chứng minh (chỉ gen thật mới chứng minh — Cấp 3); thân lệnh lấy câu đầu chữ shot có thể thiếu ý;
  `reference_only` không rõ vai; Kling element chưa có.

## 10. A/B đề xuất (Cấp 3 — chờ EP, chưa chi)

Chạy công cụ trên #31/#33 → chọn 6 ảnh (2 × 1 người, 2 × nhiều người, 2 × đổi dạng) + 4 video (2 khung đầu, 1 ref hành động, 1 đầu+cuối);
mỗi shot gen gói thật vs tối giản 1 lần. Ước tính phải qua `tools/pregen_check.py` (không tính tay). Đo mục 8.
