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

## Bước video (18/10 tối) — lỗi gốc tìm thấy khi kiểm gói video trước khi gen (0 USD)

Kiểm bằng cách DỰNG THỬ gói video của cả 39 shot trong thư mục thử (bản sao CSDL, provider giả không gửi được, chặn ghi `data/` thật),
gọi đúng `VideoRunner._blocked / _submit_args / _prepare_kwargs` + `video_pregen.check`. Script tạm ở thư mục scratchpad phiên
(chưa thành công cụ repo — đúng khoảng trống V2.1 §6.B B1 "replay video").

| Mã | Lỗi gốc | Bằng chứng | Đã làm |
|---|---|---|---|
| **G10** | Lời người dẫn chuyện (LỜI DẪN) bị coi là lời thoại phải KHỚP MÔI | `core/lipsync.py:_method` so người nói với `characters`; shot POV không có cast → điều kiện "người nói ngoài khung" không bao giờ đúng → "post" → (cờ dialogue_take) "take" → gói nhóm S01–S03, S05–S06 ghi *"LOI DAN speak Audio1… Sync the mouth, jaw…"* + gửi reference_audio. Model có thể vẽ thêm người để khớp môi. Thêm: shot có cả người nói trong khung + lời dẫn thì `runner._take_segments` / `lipsync.shot_audio` trộn lời dẫn vào track khớp môi (agent rà quy ước 7 tìm ra) | **SỬA CODE** (bỏ người dẫn bằng `speaker_lint.is_narrator` ở `_method`, `_take_segments`, `shot_audio`; giữ vị trí thời gian lời dẫn) + 3 test; cả bộ 6098 qua |
| **G11** | Motion prompt mô tả cảnh khác khung đầu (ảnh đã duyệt) | Shot 2: motion "chưa thấy cửa, quay mới lộ" — ảnh 987 đã thấy 2 cửa; shot 4: "2 cửa phía trước" — ảnh 948 là tường kệ sách; shot 35/36: "tường keo cong" — ảnh tường thẳng. Claude viết motion bám chữ kịch bản hơn ảnh, không có kiểm code nào so motion ↔ khung đầu | Sửa tay 4 motion |
| **G12** | Tên địa danh có dấu trong câu tiếng Anh làm chặn gói | "the Cổng Trời hedge maze" (S05), "LỜI DẪN narrates" (S39) → `lint` "prompt còn chữ tiếng Việt" chặn cả clip nhóm. Motion writer không được dặn viết tên riêng không dấu | Sửa tay ("Cong Troi", "a narrator") |
| **G13** | Gói nhóm vượt 5000 ký tự | S01–S03 = 5173 ký tự: motion mỗi shot có câu giải thích "because…" (viết cho người đọc), khối khớp môi G10 cộng thêm | Bỏ câu "because" ở 1–4; sau sửa G10 gói còn 3788 |
| **G14** | Nút "⏱ Đặt thời lượng theo giọng thật" kéo dài MỌI shot có lời dẫn | `voice.fit_durations` kéo 17 shot (S10 1,3→8 s, S24 1→7 s) — đổi nhịp phim + tăng tiền video, không hỏi; chỉ 3 shot (6, 12, 31) thật sự bị chặn đỏ | Hoàn lại 14 shot, chỉ giữ 6/12/31 — **chờ người dùng quyết** có kéo theo lời dẫn không |
| G15 (nợ) | Mục cũ trong lipsync index không dọn khi method đổi về "skip" | `runner.py:2214–2250`, `lipsync.mark` chỉ ghi thêm → `synced_scene_ids` sai khi gen lại | Chưa sửa (agent rà) |
| G16 (nợ) | QC đo clip coi shot chỉ có lời dẫn là "đang nói" | `core/claude_tasks.py:323` `speaking = bool(data.get("dialogue"))` | Chưa sửa (agent rà) |
| G17 (nợ) | `quality_tier.py:177` coi `lip_sync is True` là có khớp môi trước `method_for` | shot chỉ lời dẫn mà Đạo diễn gắn lip_sync → tính shot khó | Chưa sửa (agent rà) |

**Sau dự án #31:** tổng hợp G1–G17 vào bản kế hoạch nâng cấp `docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md` (người dùng 18/10).

**Kiểm bổ sung trước gen video (người dùng hỏi "đã kiểm kỹ chưa", 18/10 tối):**

| Mã | Lỗi gốc | Bằng chứng | Xử lý |
|---|---|---|---|
| **G18** | BYĐ của shot mâu thuẫn trường khác của CHÍNH shot | Shot 2: `byd.may.chuyen_dong = dung_yen` nhưng `camera_move = pan` + kịch bản "góc nhìn lia theo hướng quay" → mọi motion đều bị Tổ rà soát báo đỏ một phía. Không có kiểm code nào so BYĐ ↔ camera_move/action khi Đạo diễn khai | Motion theo camera_move + kịch bản; đóng mục có lý do |
| **G19** | Ảnh khung đầu vẽ trạng thái CUỐI thay vì ĐẦU của shot | Shot 1, 2: ảnh đã thấy 2 cửa trong khi shot là "quay người dần lộ 2 cửa"; shot 4: ý đồ qua vai thấy 2 cửa, ảnh không thấy. Gốc: prompt ảnh tả cả hành động ("camera turning to reveal two doors") → model vẽ kết quả. Liên quan G11 | Người dùng chốt ảnh tạm ổn; motion tả đúng ảnh |
| **G20** | Cổng ảnh→video báo nhầm "lệch nền 3D" khi ảnh không có/ít trời | S22 (trong phòng) và S39 (từ trên cao): cổng so đường chân trời ở 7 % / 14 % khung — ảnh khớp bố cục nền 3D (xem ảnh so sánh) nhưng không lộ trời | Đề xuất "Bỏ qua kiểm nền" kèm lý do — chờ người dùng |
| **G21** | Shot chèn tay không có BYĐ | S15–17: `video_pregen` VÀNG "chưa có BYĐ — chưa kiểm được nhịp đầu–đỉnh–cuối" (G6 mở rộng) | Ghi lại |
| **G22** | BYĐ không cập nhật khi đổi nội dung shot | S18: BYĐ vẫn "Lính áo choàng đổi tư thế" sau khi đổi thành hạ Sứ giả | Ghi lại |
| G23 | Công cụ kiểm gói video thiếu | Phải viết script tạm (thư mục thử + provider giả có chữ ký ClipAI) mới thấy G10–G13; sổ gói ghi `reference_only` không nhãn | = V2.1 §6.B B1 replay video |
| **G24** | 7 shot cận (9, 10, 12, 19, 24, 28, 32) đi **Kling** trái quyết định `video-route-2026-10-13` ("video hết Seedance 2.5, Kling chỉ đường lùi") | `core/model_router.py` nhánh `seedance_refs` (chỉ chạy khi `FEATURE_SEEDANCE_REF_GROUPS=1` — cờ nằm trong `dashboard.env`): shot cận thấy mặt không vào nhóm tham chiếu → cờ `closeup_start_frame` (S4.1, 29/09, `verified: False`) → Kling từ khung đầu, TRƯỚC luật E1 (E1 chỉ đổi model họ Seedance). Chạy không nạp `dashboard.env` thì ra Seedance 2.5 → kiểm theo cờ máy khác cờ Dashboard (cùng loại lỗi `reference_stage_auto_flag_mismatch`). `check_simple_shot_direct_720p` của sổ quyết định không bắt được vì không chạy với cờ dashboard.env | Chờ người dùng chọn: giữ Kling cho cận mặt hay về Seedance 2.5 |

## Sau gen video nháp (19/10 rạng sáng) — 39 clip, lỗi người dùng chỉ ra + tự thấy

| Mã | Lỗi gốc | Bằng chứng | Shot |
|---|---|---|---|
| **G27** | Gói VIDEO chỉ gửi 1 ảnh khuôn mặt mỗi nhân vật — không gửi ảnh DẠNG (bóng mờ, Kho #427) và không gửi ảnh VẬT Kho (Bom keo skin thang máy #367, SKORP #433, XÁC ĐEN #443), trong khi gói ẢNH có đủ | `core/seedance_refs.py:314 identity_pictures`: lấy ảnh danh tính (Kelly = ảnh áo vàng 23/10.png) + bỏ ảnh trang phục khi nhân vật ở dạng, KHÔNG thêm ảnh dạng; không có nhánh ảnh vật. Gói thật job 1045 (S28–29): "Image 3 is Kelly: identity only — NOT the clothes … ghost form" + ảnh áo vàng → cận mặt ra áo vàng; job 1033 (S16–17): không có ảnh tường keo / SKORP → tường thành khối kem; S35 tường xanh trong suốt, S36 tường xám; S29 lưng thành balo | 17, 28, 29, 35, 36 |
| **G28** | Clip Seedance chế độ ảnh tham chiếu không bắt đầu đúng khung đầu đã duyệt; video prompt không mang câu bầu trời | `framing_guard` ĐỎ nhiều clip (vd job 1043 "khung 0 khác hẳn ảnh đầu, khớp 22/3232 điểm"); S16 mở đầu Kelly nằm ở xa, mất trời có bóng ma; S29 trời sương xám như nền 3D | 16, 26, 29 |
| **G26** | Câu chữ nói "nhìn về tháp" nhưng máy 3D của shot quay về phía khác → model tự vẽ tháp sai chỗ | S31: nền 3D là tường / lan can không có tháp; motion + D6 viết "the tower rising in the background" → clip có tháp đen ở chỗ không có | 31 |
| G8 (lặp) | Mô hình 3D Kho #265 hàng rào thấp ≈ 1,5 m → nhìn qua thấy nhiều lớp rào | S14 | 14 |
| **G29** | Bước kiểm gói của phiên này bỏ qua D6 (chat_prompts BẬT ở máy chính: Claude viết lại prompt video lúc gửi) và không đối chiếu ảnh cần (dạng/vật) với "Image N" trong prompt | Script chạy thử tắt D6 như replay_payload; phiên đọc danh sách ảnh của sổ gói (có dạng/vật) thay vì ánh xạ Image N (không có) — bỏ sót G27 | (quy trình) |
| **G30** | Kho chủ thể ClipAI đầy 100/100 → ảnh không tải lên, gửi ảnh đánh dấu | diag `subjects` jobs 1047, 1049–1051, 1054 (code 1110) | (nhiều) |
| G31 | Chi Claude vượt mức dự tính dự án | `money_warning`: Claude ≈ 25,5 USD / mức 14,5 (D6 ≈ 0,04–0,09 USD/job) — chỉ cảnh báo | (ngân sách) |

Sửa gốc G27 (đề xuất, chưa làm): `identity_pictures` (video) thêm ảnh dạng (`character_forms`) thay ảnh danh tính khi nhân vật ở dạng trong shot + ảnh vật Kho mà shot nhắc (cùng luật `assets._named_extras` của gói ảnh, có biến thể skin); kiểm trước gen: nhân vật có dạng mà gói video không có ảnh dạng → ĐỎ.

**Đã sửa G27 (19/10, quyết định `video-form-picture-2026-10-19`):** `core/seedance_refs.form_and_object_pictures` — ảnh dạng theo tên nhân vật của shot (`character_forms.for_rows`) + ảnh vật Kho (`assets.scene_references` vai object, có skin); hết chỗ bỏ OUTFIT → OBJECT → FORM; chỗ ảnh trừ render 3D + khung cuối (runner 3 chỗ + `quality_samples`); `runner._ref_lint` ĐỎ khi nhân vật ở dạng mà thiếu ảnh dạng. Agent rà quy ước 7 bắt 4 lỗi (khớp tên dạng theo nhãn Kho, quality_samples, khung cuối, đã sửa). Cả bộ 6104 qua. Chạy thử 8 clip cần gen lại: đủ ảnh dạng + vật, ≤ 9 ảnh. **Nợ (chưa làm):** test runner `_ref_lint` ĐỎ/không ĐỎ, test chỗ ảnh khi nhóm có 2 render và shot đơn có khung cuối; `_estimated_len` chưa tính câu FORM/OBJECT (prompt +180–573 ký tự, chưa tách nhóm) — làm sau #31 để không đổi cách gộp nhóm giữa sản xuất.

## Gen lại 8 clip sau G27 (19/10 sáng) — job 1057–1064

| Mã | Lỗi | Bằng chứng | Gốc / hướng sửa |
|---|---|---|---|
| G32 | Seedance chặn 6/8 job "real person" (ảnh `content[5..7]`) → tự lùi sang Kling (1067–1072, 31 s ≈ 2,70 USD) | `job_events` 1057/1058/1059/1060/1063/1064/1065/1066: `InputImageSensitiveContentDetected.PrivacyInformation`; diag `subjects`: "Kho chủ thể ClipAI đầy (100/100) … gửi ảnh như cũ (đánh dấu)" | G27 thêm ảnh dạng + ảnh vật Kho vào gói, nhưng Kho chủ thể đầy nên các ảnh mới không thành asset → đi dạng ảnh thô → bộ lọc người thật. Lùi Kling là đúng thiết kế (`no-kling-closeup-2026-10-18` keeps). Hướng: dọn Kho chủ thể (người dùng bấm ⚙) trước khi gen Seedance; cân nhắc kiểm trước gen báo ĐỎ khi Kho chủ thể đầy mà gói có ảnh chưa thành asset |
| G33 | Claude API hết tiền giữa đợt (01:08) | `chat_prompt_fail` 1058/1069: HTTP 400 credit balance too low; đã chi ≈ 26,31 USD / mức 14,5 | prompt video D6 lùi về bản code ghép; tự kiểm clip (QC) bị chặn — 6 clip Kling chưa có QC hệ thống. Người dùng nạp tiền Anthropic |
| G34 | Job 1061/1062 (shot 30, 31 nhóm) kẹt `queued` từ 08:00 | `change_review_hold` ×221: motion mới bỏ tháp ("No tower is in this frame") nhưng mô tả shot 30 + `plate_view` landmark vẫn giữ Clock Tower | dữ liệu mâu thuẫn (G26 tháp sai chỗ): cần chốt shot 30 có tháp hay không rồi sửa đồng bộ mô tả + plate_view, hoặc Bỏ qua ở 📥 |

Kết quả nhìn bảng `p31_so_cu_moi_6shot.jpg` (Kling): 16 có trời ✓; 17 tường keo skin thang máy ✓ + trời ✓; 28 Kelly bóng mờ ✓; 29 bóng mờ ✓, cuối clip hiện xoáy đỏ + sương (cần người dùng xem có đúng ý); 35/36 tường đúng skin nhưng dạng THẲNG hàng, không cong về phía người ném (trái `gloo-wall-curved` 14/10); 35/36 Kelly đeo súng sau lưng.

**G34 đã sửa dữ liệu (19/10 10:37, người dùng chốt bỏ tháp):** shot 30 + 31 image_prompt/blocking bỏ tháp (tháp ngoài khung), `plate_view` → `away` khóa tay; ảnh 1001/1002 vốn không có tháp → `reapprove_image` (đóng mục đỏ khâu ảnh). Sao lưu `data/manifest.backup_20261019_truoc_sua_shot30_bo_thap.sqlite`.

| G35 | Tổ rà soát tác động LỖI (Claude hết tiền) mà cổng giữ vẫn MỞ → job 1061 tự gửi ngay khi chưa được rà, trước khi kịp tạm dừng dự án | `change_events` 1400/1403 state `failed` (LlmError hết tiền); `change_review.blocking` trả None; job 1061 running 03:38:13 → Seedance chặn real_person → retry 1073 (Kling) | trái CHUAN "không im lặng khi thiếu đầu vào": rà lỗi phải GIỮ (ĐỎ có lý do + nút Bỏ qua), không coi như đạt. Sửa code: `change_review.blocking` coi sự kiện `failed` mới hơn lần duyệt là mục chặn. Bài học vận hành: tạm dừng dự án TRƯỚC khi sửa dữ liệu làm mở cổng giữ |
| G36 | Tạm dừng dự án không chặn job đang chuẩn bị dở; thử lại sau khi bị từ chối lần đầu vẫn đi Seedance | Tạm dừng 03:42:31 (`ui_actions`), job 1075 running Kling 03:42:41; 1061→1073 và 1062→… lần thử lại đầu vẫn bị Seedance chặn real_person rồi mới sang Kling (sáng: 1057→1065→1071) | `core/runner.py:404` chỉ kiểm `paused` đầu lượt quét, dòng 413 chỉ kiểm sau lần gửi đầu → phải kiểm lại `paused` NGAY TRƯỚC `provider.submit` (trong SPEND_LOCK). Đổi model khi bị từ chối (`_record_provider_failure`) không có hiệu lực ở lần gửi lại đầu → kiểm tại sao (lần bị chặn tại bước gửi, không tốn tiền nhưng phí lượt) |

Người dùng 19/10 hỏi "tưởng bỏ Kling rồi": quyết định `no-kling-closeup-2026-10-18` chỉ gỡ Kling cho shot cận mặt; Kling vẫn là đường lùi khi Seedance từ chối (mục keeps). Chờ người dùng chọn: bỏ hẳn đường lùi (ĐỎ giữ job) hay giữ.
