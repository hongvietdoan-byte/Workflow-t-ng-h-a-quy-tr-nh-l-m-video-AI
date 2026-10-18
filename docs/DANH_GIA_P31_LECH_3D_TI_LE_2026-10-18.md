# Đánh giá #31 — ảnh lệch bố cục 3D và sai tỉ lệ (18/10/2026)

> Người dùng chê 10 shot (14, 23, 24, 26, 27, 28, 30, 33, 34, 35): sai bố cục so với map 3D, cột thừa, sai tỉ lệ cơ thể so với bối cảnh,
> bóng ma sai ref, địch xuyên tường keo. Điều tra 0 USD, chỉ đọc (`jobs.sent_package`, `scenes.data.stage_camera`,
> `data/_plates3d/cache/<key>/meta.json`, ảnh nền ↔ ảnh gen). Người dùng chọn **sửa nhanh bằng dữ liệu/prompt trước** (kịp tiến độ),
> **lỗi gốc ghi lại ở đây để sửa code sau** (S1–S5, chưa làm).

## Lỗi gốc (có bằng chứng)

| Mã | Lỗi gốc | Bằng chứng | Shot dính | Sửa gốc (CHƯA LÀM) |
|---|---|---|---|---|
| **G1** | Khối giữ chỗ của sân khấu 3D bị mang sang cảnh khác | `stage_camera.props` = trụ Ø0,5×1,75 m nhãn "XÁC ĐEN BIẾT BAY" (dàn cảnh cảnh 6) có ở shot 28/30 (`source: "cảnh 6 (cùng sân khấu)"`) và 34/35 (`"cảnh 7 (cùng sân khấu)"`), kể cả cảnh 8 = thế giới THỰC TẠI ban ngày (không có quái). Khối render vào nền (`plate.png`) → model vẽ thành cột đá; D6 shot 34 còn gọi là *"the tall pale tower rising on the frame-right"* | 26, 28, 30, 34, 35 | **S1**: chỉ mang khối sang shot có vật đó trong BYĐ.thanh_phan / chữ shot; không bao giờ mang qua lúc đổi thế giới (song song ↔ thực tại); câu giải thích "grey block = placeholder" (`core/stage_facts.py:229`) bắt buộc đi kèm mọi nền còn khối, thiếu thì `pregen_check` báo ĐỎ |
| **G2** | Nền 3D không có mốc tỉ lệ người | Nền render trống người; cỡ người chỉ do câu % khung trong prompt (vd shot 23 *"her whole body about 60% of frame height … never resize her smaller for distance"*) — không ràng theo khoảng cách 3D. Shot 35 địch to như khổng lồ; shot 14 máy cao 3,6 m chúi −18° (meta `pitch_deg -18.2`) → hàng rào trông thấp hơn người | 14, 24, 27, 35 | **S2**: dựng người nộm đúng chiều cao (Kho `height_m`) tại chỗ đứng blocking trong Blender (ảnh bố cục riêng hoặc trong nền kèm câu giải thích); kiểm % khung trong prompt khớp hình học máy (cùng một nguồn — `feedback_geometry_single_truth`) |
| **G3** | Máy góc 'eye' mà ngước/chúi lớn, không kiểm nền bị tường che | Shot 28 `angle: eye` nhưng máy thấp hơn cảnh 0,56 m (z 10,85 vs 11,41), meta `pitch_deg +17.3` → nền gần như chỉ tường trống, model tự bịa; shot 35 `pitch +11.1` | 28, 35 | **S3**: góc 'eye' → |pitch| ≤ 5° khi giải máy (`core/stage_auto.py` / `plate_camera`); kiểm nền bằng `depth.png` (> 60 % điểm ảnh gần < 2 m = bị chắn → giữ shot) — nối `reference_plate_camera_blind` |
| **G4** | Chọn ảnh Kho bằng dò bí danh trong chữ, không đọc BYĐ | `core/assets.py:_named_extras` (1815–1855) khớp `names_of(a)` trong text + image_prompt. Bí danh #443 = *"flying black corpse, floating corpse, levitating corpse, cái xác biết bay"*. Phiên này bỏ "floating corpse" khỏi prompt shot 23 (để qua bộ lọc OpenAI) → job 993 KHÔNG gửi ảnh #443 (job 967 trước đó có) — rơi im lặng, không cảnh báo. BYĐ.thanh_phan vẫn khai "XÁC ĐEN BIẾT BAY" nhưng khâu dựng gói không đọc (đúng phát hiện V2.1 §2.4) | 23 | **S4**: đọc thêm `byd.thanh_phan[].vat` / `kho_id` (V2.1 A2e rút gọn); `pregen_check` so ref Kho của gói mới ↔ gói gửi trước, ref biến mất → VÀNG có tên |
| **G5** | Sổ gói ghi nhãn ảnh sai | `core/sent_package.py:124 _meta_index` khóa theo **basename** — Kho đặt tên `1.png/2.png/3.png` ở mọi mục → ảnh #443/2.png ghi nhãn "SKORP", #367/2.png ghi "SKORP", #425/3.png ghi "KELLY". Prompt gửi model vẫn ĐÚNG (shot 24: *"Image 5 is the object XÁC ĐEN BIẾT BAY"*) — chỉ sổ sai | (sổ) | **S5**: khóa theo đường dẫn đầy đủ (rel_path), test 2 mục Kho cùng tên file |

| **G6** | Shot chèn tay (`llm_io.insert_scene_after`) không thừa kế bối cảnh | Shot 15–17 chèn 18/10 thiếu `location_asset/location/time/weather/lighting/mood` → `place_refs.wants_render` = False ("không còn ở bối cảnh có mô hình 3D") → gói KHÔNG có nền 3D, chỉ ảnh Kho #265/#450 — im lặng; sau khi chép `location_asset` thì nền render ra **day-clear** (thiếu time/weather) | 15, 16, 17 | **S6**: `insert_scene_after` chép mặc định các trường bối cảnh của shot `after_idx` (cùng cảnh kịch bản); shot ở bối cảnh có 3D mà không có nền → `pregen_check` ĐỎ |
| **G7** | Shot POV bỏ ảnh súng | `core/assets.py:1830` bỏ ref súng khi `prop_lock.is_pov` (luật #27 "FF không có POV cầm súng") → shot 15 POV bắn: model vẽ súng đen thường, mất hào quang đỏ. 16/17 có ref SKORP (#433/2.png là SKORP đen) nhưng câu prompt chỉ ghi "red-glowing" ngắn → màu đỏ yếu/mất | 15, 16, 17 | Quyết định người dùng 18/10 cho POV bắn → luật POV-bỏ-súng cần điều kiện (shot khai cầm súng); hào quang đỏ là TRẠNG THÁI của SKORP sau shot 12 → nên là biến thể Kho (ảnh SKORP đỏ) chứ không chỉ câu chữ |

**Chiều cao hàng rào mê cung (shot 14):** đo trên nền 3D mới (máy 1,0 m, 24 mm, pitch 0): hàng rào cách máy ≈ 4,2 m, đỉnh cao hơn máy
≈ 0,64 m → **mô hình 3D Kho #265 cho hàng rào ≈ 1,6 m** (ngang người). Ảnh gen khớp mô hình. Câu "hàng rào 2,5 m" phiên này thêm vào prompt
là SAI so với 3D (vi phạm một nguồn sự thật) → đã bỏ 18/10 (prompt nói "cao đúng như Image 1"). Nếu trong game hàng rào cao hơn người
thì gốc nằm ở **mô hình 3D Kho #265** (tỉ lệ / thiếu phần hàng rào) — cần người dùng xác nhận bằng ảnh in-game.

**G8 (xác nhận 18/10 bằng video in-game người dùng gửi `ScreenRecording_10-17-2026_08-33-20_1.mov`):** trong game, hàng rào BÊN
TRONG mê cung cao hơn đầu nhân vật nhiều (≈ 2,5–3 m); chỉ vài đoạn rìa ngoài là tường đá thấp + bụi ngang người. Ảnh render mô hình 3D
Kho #265 (`data/assets/265/3.png`, lối vào mê cung) và nền 3D shot 14–17 đều cho hàng rào ≈ 1,5 m (tường đá ≈ 0,6 m + bụi ≈ 0,8 m) →
**mô hình 3D thiếu / thấp phần hàng rào bên trong** (có thể LOD hoặc mesh hàng rào cao không được nhập). Mọi shot mê cung (6–21) bám nền 3D
nên đều ra hàng rào thấp. Sửa gốc: kiểm file 3D gốc (mesh/LOD hàng rào trong) + ghi `height_m` đo được vào Kho; tạm thời: câu prompt ghi rõ
"chỉ nâng chiều cao hàng rào lên ≈ 2,5–3 m, giữ nguyên bố cục lối đi" (vi phạm có chủ đích nền 3D về chiều cao, có lý do).

**G9 (báo nhầm kiểm công thức):** `shot_text_checks` khớp "whole body" trong câu tả SÚNG ("aura along its whole body") → chặn shot 17
("from the waist up" mâu thuẫn "whole body"). Cụm này cần gắn với người, không với vật.

## Lỗi dàn cảnh (sửa bằng câu, không phải code)

- **30**: người bắn AWM phải đứng ở **ô cửa sổ tầng 2–3** của căn nhà có trong nền 3D; model vẽ người đè lên mái (sai model nhà).
- **33**: nền không có tường keo (vật chưa có trong sân khấu 3D) → model vẽ tường + địch chồng lên nhau, trông như đi xuyên. Tường keo
  phải CONG hai đầu về phía người ném (quyết định 14/10), địch chạy vòng qua hai đầu tường. Gốc dài hạn: đặt tường keo làm vật của sân khấu 3D.
- **33**: nền 3D không có trời (mặt nhà phủ nửa trên) nhưng prompt có câu bầu trời song song + "trời hửng sáng" → model vẽ trời xoáy đè lên
  nhà. Gốc chung: câu bầu trời gắn cố định cho cả cảnh, không xét khung có thấy trời không (nên đọc tỉ lệ trời trong nền 3D).
- **14**: người dùng chọn **kết hợp**: giãn cảnh (máy thấp, hàng rào cao hơn đầu người như map) + thêm shot POV bắn chuẩn xác / lăn né /
  bom keo để hạ từng địch.

## Sửa nhanh đã làm 18/10 (dữ liệu, 0 USD trước khi gen)

Ghi ở `TODO.md` dòng 18/10 cùng ngày (sao lưu CSDL + danh sách trường đã đổi).
