# Liệu bạn sẽ Booyah tập 1 — phân tích tư liệu + chuẩn bị dự án (12/10/2026)

- **Dự án Dashboard:** **#27 "Liệu bạn sẽ Boooyah tập 1"**: 9:16, SHORT_FORM, game FF, chế độ human_qc, QC balanced. Kế thừa từ #24: shot_mode, look, image_model (gpt-image-2.5-sunburst), render_settings.
- **Kịch bản đã nạp:** 9 cảnh, nạp theo luồng ▶ Phân tích của Dashboard (`script_reader.from_text` → `split_scenes` → `import_scenes`, 0 USD). Bảng nạp nằm ở `docs/kich_ban/lieu_ban_se_booyah_tap1_nap.tsv`. Các cột của bảng:
  - Cảnh / Thời gian / Bối cảnh / Mô tả.
  - Voice over: ghi theo dạng `LỜI DẪN:`.
  - Text, Note edit: hệ thống giữ làm ghi chú.
  - Riêng lời dẫn cảnh 1, câu "Bạn chọn: 1. … 2. …" được viết thành "Bạn chọn, một: …, hai: …" để TTS đọc đúng.
- **Tư liệu Kho gắn vào dự án (`project_assets`):** KELLY #23, MAXIM #33, WOLFRAHH #59, KAPELLA #21, Tháp Đồng Hồ #263, Cổng Trời #265, Yêu nữ tà linh dạng 1 #418, Bom keo #367, HUD banner BOOYAH #399.
- **Sao lưu CSDL trước khi tạo:** `data/backup/manifest.before_booyah_tao_du_an_20261012.sqlite`.
- **Chi thật: 0 USD.** Không gọi Claude, vì tách cảnh từ bảng là việc làm bằng code. Không gen ảnh/video/âm thanh.

## 1. Tư liệu (`D:\2026\OB55\Halloween\Thanh\Liệu bạn sẽ booyah`)
- Bản chép nằm ở `D:\AI-Video-Pipeline\data\ref_clips\booyah_tap1_2026-10-12\` (thư mục này không vào git). Chép 25 file, giữ nguyên bản gốc.
- Video ref nặng 247 MB, vượt ngưỡng 200 MB nên **không chép**, chỉ ghi đường dẫn gốc.
- Ảnh lưới, dải khung video và kết quả nghe nằm ở `…\_phan_tich\`.

| # | File | Loại · cỡ | Nội dung (đã xem) | Dùng cho |
|---|---|---|---|---|
| 1 | `video ref chuyển đổi giữa thế giới song song và hiện tại của Tháp đồng hồ.mp4` | MP4 4K (3840×2158) 60 fps · 31,9 s · 247 MB · **không chép** | Diễn biến theo mốc giây:<br>• 0–2 s: Tháp Đồng Hồ ban ngày, nhân vật đồ vàng đứng ở bậc thang quảng trường.<br>• **2 s: chuyển sang thế giới song song.** Nhân vật thành **bóng mờ trong suốt** (thân tím-xanh lam phát sáng, viền đỏ). Trời tối, mây giông, **lốc xoáy đỏ có tâm lửa đỏ**. **Mảnh vỡ/hòm/xe lơ lửng** trên trời. Vệt đỏ quanh mép khung.<br>• 4–11 s: chế độ chụp ảnh.<br>• 10–17 s: máy ngửa lên lốc xoáy.<br>• 17–21 s: máy hạ xuống thị trấn tối.<br>• **22 s: màn tỏa vệt/xúc tu đỏ** chuyển về thế giới thực.<br>• 23–30 s: ban ngày, máy lia quanh tháp. Hòm thính/khinh khí cầu vẫn bay trên trời.<br>• 31 s: về HUD.<br>**Âm thanh** (`tools/audio_listen.py`): không có lời nói.<br>• 0–2 s: gần như im lặng.<br>• 2 s: nhạc u ám nổi lên (≈ −28 → −34 dB), 123 BPM, A thứ, có tiếng leng keng/ting.<br>• 12 s: nhạc to lên, có tiếng nổ + whoosh.<br>• 17–18 s: tiếng rên/thở ma quái.<br>• 20 s: âm như còi hú.<br>• 22 s: whoosh + tiếng thở dài lúc chuyển cảnh.<br>• 23 s về sau: nhạc tắt hẳn (−48 dB) ở thế giới thực.<br>• 30 s: tiếng xu UI. | Cảnh 1 (cổng phải), 2–5 (lớp phủ song song, bóng mờ, bầu trời), chuyển cảnh 2/6 |
| 2 | `Tháp đồng hồ khi ở Thế giới song song.png` | 3293×1881 · 3,9 MB | Tháp nhìn từ bậc thang lúc đêm. Lốc xoáy đỏ + mặt trời đỏ, vật lơ lửng. | Cổng phải cảnh 1; nền cảnh 3–5 |
| 3 | `tháp đồng hồ lúc bình thường.png` | 3356×1883 · 6,6 MB | Cùng góc lúc ban ngày, trời xanh, hòm thính bay. | Cổng trái cảnh 1; cảnh 6–9 |
| 4 | `thế giới song song.png` | 3352×1890 · 4,4 MB | Ảnh chụp gameplay: người chơi **bóng mờ xanh lam** chạy trong nhà, vệt đỏ dưới chân, có HUD. | Hình mẫu bóng mờ (2–5) |
| 5 | `cánh cổng portal.png` | 1770×1237 · 3,2 MB | **Cổng kiểu torii**, mái trắng xám, 2 cột phát sáng đỏ, đêm giông. | Thiết kế 2 cổng (1, 2, 6) |
| 6 | `Cổng Trời - ô tô bị nguyền bay lên cao.png` | 1846×1779 · 2,2 MB | Góc thấp ngửa lên: nhà/mái + **ô tô lơ lửng giữa cột sáng đỏ**, trời giông. | Cảnh 3 (vật bị nguyền, ngoài trời) |
| 7 | `bức tường trong căn phòng tháp đồng hồ có mặt nạ bị nguyền.png` | 1561×1343 · 1,3 MB | Phòng giấy dán tường xanh, 3 mặt nạ trắng treo tường, vòng đỏ dưới sàn. | Cảnh 3 (trong nhà) |
| 8 | `vật phẩm bị nguyền - hộp nhạc.png` | 1416×757 · 1,0 MB | Hộp nhạc nằm trong vòng tròn đỏ trên sàn, người chơi bóng mờ đứng gần. | Cảnh 3 |
| 9 | `quả bóng bị nguyền.png` | 1165×731 · 0,9 MB | Quả bóng bãi biển trong vòng đỏ, có cột sáng đỏ trên bãi cỏ. | Cảnh 3 |
| 10 | `ví dụ tay quỷ.png` / `ví dụ tay quỷ 2.png` | 1072×1059 / 1295×768 · ~0,7–1,0 MB | **Tay quỷ đỏ-đen** bám vào tủ / bám trên mái nhà. | Cảnh 3–4 (vật lạ, gợi ý); hiệu ứng xúc tu cảnh 2 |
| 11 | `nhân vật cầm súng bắn địch.png` | 949×1490 · 2,8 MB | Ảnh gameplay góc thứ ba sau vai, bắn địch, có số sát thương. | Cảnh 8–9 (góc máy) |
| 12 | `hình booyah toàn cảnh.png` / `hình khung booyah .png` | 3357×1879 / 3357×401 | Màn BOOYAH trong game (dải banner đỏ-cam), dải banner rời. | Cảnh 9 (ghép hậu kỳ) |
| 13 | `logo quét sạch đội địch.png` | 627×423 | Huy hiệu "QUÉT SẠCH ĐỘI". | Cảnh 9 (tuỳ chọn) |
| 14 | `súng máy RPK` / `súng ngắm hawk` / `súng tiểu liên skorp` / `súng trường M7` | 2048²–3840×2626 | Ảnh vũ khí trên nền trơn. | Vũ khí của Kelly/địch (7–9), chờ chốt |
| 15 | `trang phục lính địch.jpeg` | 12066×3174 · 4,3 MB | Bảng thiết kế **Cloaked Terror**: áo choàng đen mũ trùm lót đỏ, mặt nạ trắng bịt mắt. | Địch cảnh 8–9 |
| 16 | `trang phục sứ giả bóng đêm.png` | 12906×3075 · 14,7 MB | **Hollow Man**: mũ phớt, mặt nạ, áo khoác trắng dính máu. | Địch 8–9 |
| 17 | `trang phục xúc tu đỏ.png` | 10058×2513 · 9,9 MB | **Red Slicker**: áo mưa đỏ, xúc tu đỏ sau lưng. | Địch 8–9 |
| 18 | `yêu nữ tà linh dạng 1.jpg` / `dạng 2.jpg` | 9244×2100 / 8143×2100 | **Crimson Glitches** dạng 1 (dạng 1 đã có ở Kho #418) và dạng 2 (#419). | Địch 8–9 (chỉ dùng dạng 1) |
| 19 | `OB55 THE UNSEEN Global Campaign Playbook.pptx` | 22 slide · 48 MB | Các slide liên quan:<br>• Slide 9: Ghost Transformation. Người sống đeo mặt nạ vào Other World, chạy nhanh hơn, **không tàng hình**; bắn hoặc trúng đạn thì thoát ra.<br>• Slide 10: người chết thành **búp bê ma**.<br>• Slide 11: skybox Other World + **reskin Tháp Đồng Hồ** (chỉ có ở Bermuda).<br>• Slide 13: vật lạ → **vật phẩm bị nguyền**.<br>• Slide 18: skin **Gloowall 907105556** (bom keo OB55). | Logic thế giới song song, bom keo |
| 20 | `Liệu bạn sẽ booyah tập 1/kịch bản tập 1.png` | 949×635 | Ảnh bảng kịch bản (đã chép vào `lieu_ban_se_booyah_tap1.md`). | — |
| — | `Liệu bạn sẽ booyah tập 2/` | trống | — | — |

**Ref sẵn có trong repo nên dùng kèm** (`data/ref_clips/ob55_unseen/`, đã phân tích ở `DU_AN_OB55_THE_UNSEEN_2026-10-08.md`):
- `06_otherworld_combat`: bóng mờ xanh lam, trúng đạn thì lóe trắng rồi về ban ngày. Mẫu cho chuyển cảnh trắng ở cảnh 6.
- `07_ghost_doll`: búp bê ma chibi khi bị hạ. Có thể dùng cho 3 đồng đội ở cảnh 1.
- `08_inner_world_skybox` (101 s): lốc đỏ, tay khổng lồ, cầu thang tháp đồng hồ, cảnh trong nhà. Dùng cho cảnh 3–4.

## 2. Đối chiếu Kho

| Cần | Kho | Trạng thái | Ghi chú / cần làm |
|---|---|---|---|
| Tháp Đồng Hồ | #263 | **CÓ 3D** | FBX chính thức ClockTower, 24 chỗ đứng, render plate được. Dùng `duong_bac` (đồng cỏ phía bắc nhìn lên tháp) cho cảnh 1. `plaza_front` / `level_9_4` / `bac_thang_giua` (bậc thang như ref) dùng cho 6–9. Trong nhà có `trong_nha_qt_t1–t3` (nhà 3 tầng trên quảng trường) cho cảnh 3. |
| **Cổng Trời** (khu vực) | #265 | **CÓ 3D** | FBX "Peak" P20 (`model 3D\…\Peak\T_30_XH_PCMAP_P20\asset.fbx`), 17 chỗ đứng (biệt thự, sân trước, hồ bơi, mê cung, bãi xe, biển QC, nhà kính…). 6 ảnh render ban ngày đã duyệt. #84 "Khu vực - Cổng Trời mới" là cùng nơi nhưng chưa gộp. Kịch bản không ghi cảnh nào ở Cổng Trời, chỉ ảnh ref "ô tô bị nguyền" nhắc tới → đề xuất dùng cho cảnh 3. **Chưa có:** render ban đêm / lớp phủ song song cho cả 2 nơi (hiện chỉ có ánh sáng ngày). |
| **Cổng portal** (vật thể 2 cổng) | — | **THIẾU** | #391 "cong", #392 "cong dich chuyen" là **vòng dịch chuyển xanh lam** (pending), không giống torii đỏ trong ref. Có 3 cách bổ sung, đề xuất a:<br>(a) Tạo mục Kho mới "Cổng portal torii OB55" từ `cánh cổng portal.png` (0 USD, cắt ảnh). Khi gen thì vẽ cổng vào ảnh khởi đầu trên plate 3D, phía sau ghép 2 render (ngày / song song).<br>(b) Meshy dựng 3D từ ảnh (≈ 0,2–0,5 USD, cần duyệt).<br>(c) Blender dựng khối torii đơn giản (2 cột + 2 xà, 0 USD) đặt vào sân khấu 3D để máy đo đúng tỉ lệ. |
| Kelly | #23 | CÓ | Hồ sơ đầy đủ, 16 ảnh, có 3D (`data/models3d/KELLY_23`). |
| Maxim / Wolfrahh / Kapella | #33 / #59 / #21 | CÓ (Kapella **không có 3D**) | Ở cảnh 1 chỉ cần hiện "bị hạ" → xem câu hỏi 6. |
| Yêu nữ tà linh dạng 1 (Crimson Glitches) | #418 | CÓ | 2 ảnh approved (ảnh thứ 3 redundant), thuộc dự án #24. |
| Sứ giả bóng đêm (Hollow Man) | — | **THIẾU trong Kho** | Có bảng thiết kế (tư liệu #16 + `ob55_unseen/trang_phuc/hollow_man…`). Cần cắt ảnh trước/sau → tạo Kho (0 USD). |
| Xúc tu đỏ (Red Slicker) | — | **THIẾU** | Có bảng thiết kế. Cắt ảnh → Kho. Xúc tu là hiệu ứng **kích hoạt**, không luôn bật. |
| Lính địch (Cloaked Terror) | — | **THIẾU** | Có bảng thiết kế. Cắt ảnh → Kho. |
| Bom keo | #367 | **CÓ tên, 0 ảnh** | Cần ảnh tường keo dựng lên (keo thường hay skin Gloowall OB55 907105556) → **người dùng cung cấp** ảnh/clip in-game. |
| Hiệu ứng skill | `data/skills/` | Không liên quan | Chỉ có KENTA, ORION. Kịch bản không có kỹ năng nhân vật. |
| Bóng mờ (dạng song song) | — | Có ref, chưa có Kho | Ảnh tư liệu #4, #8 + video ref. Đề xuất tạo mục Kho "style: bóng mờ thế giới song song" (0 USD). |
| Lớp phủ thế giới song song (trời lốc đỏ, vật lơ lửng) | — | Có ref, chưa có Kho | Tư liệu #2, #6 + `08_inner_world_skybox`. Đề xuất mục Kho style + ảnh trời (sky) dùng cho `add_sky` của plate. |
| BOOYAH | #399 | CÓ | Có banner vàng kênh Kelly. Ảnh banner OB55 đỏ-cam (tư liệu #12) đẹp hơn → đề xuất thêm vào Kho. |
| Vũ khí | nhiều mục | Một phần | Ảnh M7 / RPK / Skorp / Hawk có trong tư liệu. Chưa chốt Kelly dùng súng gì. |

## 3. Từng cảnh — đề xuất dựng
Quy ước: **FP** = góc nhìn thứ nhất, **TP** = góc thứ ba. Ước thời lượng theo lời dẫn ≈ 3,8 từ/giây.

**Cảnh 1 — Ngã rẽ (≈ 13–14 s, gồm 3 s đếm ngược)**
- Bối cảnh: Tháp Đồng Hồ #263, chỗ đứng `duong_bac`, ban ngày.
- Góc nhìn: FP, mắt Kelly 1,6 m nhìn về phía tháp. Đồng cỏ sạch ở tiền cảnh. 2 cổng torii đặt trái/phải giữa đồng cỏ. Qua lòng cổng trái thấy tháp ban ngày; qua lòng cổng phải thấy tháp phiên bản song song (trời đỏ, lốc xoáy).
- Máy: đẩy rất chậm (push-in) hoặc tĩnh.
- Chuyển động nền: cỏ lay, mây trôi; lòng cổng phải gợn sóng như xoáy.
- Đồng đội: thông báo "đã bị hạ" ×3 (thông báo hạ gục kiểu HUD ghép hậu kỳ) và/hoặc 3 búp bê ma chibi (OB55) gần đó → câu hỏi 6.
- Chữ: tên cổng dưới chân mỗi cổng + câu "Hãy chọn một thế giới…" → **ghép hậu kỳ** (ffmpeg drawtext/overlay). AI vẽ chữ tiếng Việt hay sai; luật A14 cũng là hệ thống không tự chèn chữ, chỉ khai báo.
- Sau lời dẫn: **đồng hồ đếm ngược 3 s** (3-2-1, có tick) ghép hậu kỳ trên khung cuối giữ nguyên, nền vẫn chuyển động.
- Âm thanh: gió nhẹ + hum năng lượng của 2 cổng (cổng phải trầm, méo).
- **1 clip video dài** (~10 s) + giữ khung cuối 3 s. Ref: tư liệu #2, #3, #5.

**Cảnh 2 — Vào cổng song song (≈ 6 s)**
- FP: máy tiến thẳng vào lòng cổng phải (dolly-in) → **xúc tu đỏ tỏa vào từ mép khung** (giống ref 22 s và tư liệu #10) → màn đen.
- Cách dựng: video gen đoạn máy tiến vào cổng. Xúc tu: hoặc gen trong clip (Seedance, dùng ảnh khung đầu + khung cuối là khung kín xúc tu), hoặc lớp phủ hậu kỳ. Đề xuất **khung đầu + khung cuối** (bài học S4.6 về hiệu ứng).
- Kịch bản ghi "nhân vật tàng hình": vì FP nên không thấy người. Có thể cho thấy tay mình chuyển sang bóng mờ ở giây cuối.
- Âm thanh: whoosh hút vào + rít đỏ + nhịp tim; nhạc kinh dị bắt đầu (ref 2 s).

**Cảnh 3 — Thế giới song song (≈ 8 s, 3–4 shot ngắn)**
- 3a, trong nhà (Tháp, `trong_nha_qt_t*`): tường giấy dán xanh + 3 mặt nạ trắng, hộp nhạc trong vòng đỏ, mảnh vỡ không gian lơ lửng.
- 3b, ngoài trời: Kelly bóng mờ (TP từ sau lưng) chạy ra. Ô tô lơ lửng giữa cột sáng đỏ: đặt ở **Cổng Trời #265** (`san_truoc`, có xe đỗ) hay ngay tại Tháp → câu hỏi 4.
- 3c: máy ngửa lên **bầu trời lốc xoáy đỏ** (ref 10–17 s).
- Bóng mờ: thân trong suốt tím-xanh lam phát sáng, viền đỏ (tư liệu #4; ref 2–7 s).
- Chuyển động nền: mây giông xoáy, mảnh vỡ trôi, đèn đỏ chập chờn.
- Ref: tư liệu #6, #7, #8, #9, `08_inner_world_skybox`.

**Cảnh 4 — Chạy mãi (≈ 4 s)**
- TP đuổi theo sau lưng Kelly bóng mờ chạy dọc đường dưới tường chắn (`level_2_3`) hoặc bậc thang. Trời tối mù.
- Cách thể hiện "lặp lại": dựng 2 clip cùng góc nối nhảy (jump-cut) / tua vòng, hoặc 1 clip máy tracking rồi lặp lại đoạn ngắn có biến dạng.
- Đề xuất **1 clip + hậu kỳ lặp 2 lần**. Hợp với "cảnh vật bị lặp lại" mà không tốn thêm tiền gen.

**Cảnh 5 — Kẹt vĩnh viễn (≈ 5–6 s)**
- TP: Kelly bóng mờ khuỵu gối, gục xuống.
- Thông báo "Bạn đã bị kẹt ngoài vùng an toàn" (chữ hậu kỳ) → **lọc xám màn hình** (ffmpeg hue=s=0 tăng dần) → mờ đen.
- Âm thanh: nhạc rơi xuống một nốt trầm kéo dài, tiếng thở; tắt.

**Cảnh 6 — Quay lại ngã rẽ, chọn thực tại (≈ 8 s)**
- Mở lại khung cảnh 1, dùng lại khung cuối cảnh 1, 0 USD: tua ngược / "Còn nếu…".
- FP: máy tiến vào cổng trái → **ánh sáng trắng tỏa** (ref `06_otherworld_combat` lóe trắng) → màn trắng → Tháp Đồng Hồ ban ngày (`plaza_front`/`bac_thang_giua`).
- Ánh trắng: ghép hậu kỳ (fade trắng) là đủ, 0 USD.

**Cảnh 7 — Bom keo (≈ 5 s)**
- 7a: FP tay Kelly nhặt bom keo trên đất (quảng trường). Hoặc TP cận tay.
- 7b: ném → tường keo dựng lên chắn trước mặt.
- Cần ảnh bom keo / tường keo (thiếu, câu hỏi 8).

**Cảnh 8 — Hai team địch bắn nhau (≈ 4 s)**
- TP qua vai Kelly núp sau tường keo (như tư liệu #11). Phía xa: 2 team địch bắn nhau trên quảng trường / bậc thang.
- 4 bộ trang phục: Cloaked Terror, Crimson Glitches dạng 1, Hollow Man, Red Slicker.
- **Rủi ro cao nhất:** 4 nhân vật lạ cùng khung, nhỏ, phải đúng trang phục. Đề xuất chia 2 shot: shot rộng (địch nhỏ, chỉ cần màu/khối đúng) + shot trung từng cặp đối đầu.
- Âm thanh: tiếng súng xa vọng, đạn rít.

**Cảnh 9 — Booyah (≈ 6–7 s)**
- 9a: TP Kelly lao ra từ sau keo, hạ địch cuối (gạt gục).
- 9b: Kelly ăn mừng (emote) + **pháo hoa phía sau**. Pháo hoa gen trong video, vì cần chuyển động thật.
- Banner **BOOYAH!** ghép hậu kỳ: dùng banner OB55 (tư liệu #12) hoặc Kho #399. Có thể thêm huy hiệu "Quét sạch đội".
- Âm thanh: nhạc chiến thắng bùng lên.

**Cấu trúc 2 nhánh:**
- Đề xuất **một video nối tiếp**: 1 → nhánh song song 2–5 (kết xám/đen) → 6 mở lại ngã rẽ → nhánh thực 7–9 (Booyah).
- Lời dẫn cảnh 6 "Còn nếu bạn…" đã dẫn dắt sẵn.
- Khung cảnh 1 dùng lại ở đầu cảnh 6 (0 USD), tạo cảm giác "tua lại".
- Phương án khác: tách 2 video (1+2–5, 1+6–9) cho dạng tương tác/bình chọn → câu hỏi 2.

**Nhạc theo đường cảm xúc** (bài học 08/10: đổi nhạc ở bước ngoặt, không phải mỗi clip một đoạn):

| Đoạn | Cảnh | Nhạc |
|---|---|---|
| A | 1 | Hồi hộp, nhịp đồng hồ tích tắc |
| B | 2–5 | Kinh dị u ám, kiểu ref: 123 BPM, A thứ, drone + leng keng. Lên cao trào ở 3c, rơi tắt ở 5. |
| C | 6–8 | Căng thẳng, lén lút |
| D | 9 | Bùng nổ chiến thắng |

Hạ nhạc 8–12 dB dưới lời dẫn.

**Chuyển động nền (không để cảnh đơ):** mọi motion prompt đều có lớp chuyển động nền:
- Mây trôi, cỏ/lá lay ở thế giới thực.
- Lốc xoáy quay, mảnh vỡ trôi, khói đỏ lan ở thế giới song song.

## 4. Rủi ro + thiếu tư liệu
1. **Plate 3D chỉ có ánh sáng ngày.** Thế giới song song cần bản đêm + trời lốc đỏ. Có 2 hướng:
   - Render plate 3D với trời tối, rồi `add_sky` ảnh lốc đỏ (0 USD, Blender).
   - Vẽ lớp phủ ngay trong ảnh khởi đầu.

   Đề xuất hướng 1 để nền giữ đúng map 3D (bài học #24: nền phải khớp map).
2. **Cổng portal chưa có trong Kho/3D.** Dễ bị vẽ lệch tỉ lệ/vị trí giữa shot cảnh 1 và cảnh 6 (2 shot cùng khung phải trùng nhau). Nên dùng lại đúng khung cảnh 1.
3. **4 trang phục địch:** 3/4 chưa có Kho; cảnh 8 có nhiều nhân vật nhỏ trong khung → dễ sai trang phục, dễ phải vẽ lại.
4. **Bom keo/tường keo:** không có ảnh.
5. **Bóng mờ trong suốt:** model ảnh/video có thể vẽ thành người thường hoặc ma mờ khói. Cần ảnh mẫu rõ (tư liệu #4) + câu tả cố định.
6. **Chữ tiếng Việt + đếm ngược + banner:** phải ghép hậu kỳ. Pipeline có popup cuối clip; cần kiểm khả năng overlay chữ giữa clip (cảnh 1, 5).
7. **Playbook:** người sống ở Other World **không tàng hình**, còn kịch bản ghi "tàng hình". Vì vậy dùng hình bóng mờ như ref là khớp game hơn chữ "tàng hình".
8. Theo bài học #24 (5,029 USD cho 12 shot, vẽ lại nhiều lần): cần dự phòng ~30 % ảnh vẽ lại và ~30–50 % video làm lại.

## 5. Câu hỏi cần người dùng chốt
1. **Tỉ lệ khung:** để mặc định 9:16 như #24, hay 16:9 giống video ref gameplay? *Đề xuất 9:16* (TikTok/Reels). Dự án đang đặt 9:16.
2. **2 nhánh:** một video nối tiếp (1→2–5→6–9), hay 2 video riêng? *Đề xuất nối tiếp* (≈ 60 s).
3. **Thời lượng:** lời dẫn ≈ 54 s, cộng đếm ngược + chuyển cảnh + Booyah thì ≈ 60–63 s, vượt nhẹ mốc "< 1 phút". Chấp nhận, hay rút gọn lời dẫn (vd cảnh 1, 6)? *Đề xuất* đọc nhanh ~4,2 từ/s → ≈ 57 s.
4. **Cổng Trời dùng ở đâu?** *Đề xuất* cảnh 3b (ô tô bị nguyền bay lên ở sân trước biệt thự `san_truoc`); còn lại ở Tháp. Hay toàn bộ ở Tháp?
5. **Kiểu cổng portal:** torii đỏ như `cánh cổng portal.png` (2 cổng giống nhau, khác cảnh trong lòng cổng)? Bổ sung bằng (a) ảnh Kho 0 USD, (b) Meshy, hay (c) khối Blender? *Đề xuất (a)+(c).*
6. **3 đồng đội tử trận** hiện thế nào? Chọn giữa thông báo hạ gục, thân nằm, hay **búp bê ma chibi OB55**. *Đề xuất* thông báo chữ + 3 búp bê ma nhỏ phía xa. Kapella không có 3D, nhưng ở dạng búp bê thì không cần.
7. **Kelly mặc gì:** hồ sơ Kho #23 mặc định hay bộ sự kiện? Kelly dùng súng gì (M7 / RPK / Skorp / Hawk)? "Gạt gió" = hạ gục địch cuối bằng súng hay cận chiến?
8. **Bom keo:** keo thường hay skin Gloowall OB55 (907105556)? Cần **ảnh/clip in-game tường keo**.
9. **Góc nhìn từng cảnh:** đề xuất như sau, đồng ý không?
   - FP: 1, 2, 6, 7a.
   - TP: 3b, 4, 5, 8, 9.
   - 3a, 3c: FP.
10. **Được tạo Kho 0 USD** cho các mục: Hollow Man, Red Slicker, Cloaked Terror (cắt bảng thiết kế); cổng portal; style bóng mờ + trời song song; banner BOOYAH OB55?
11. **Giọng lời dẫn:** một trong 4 giọng FF VN (`data/voices_vi.json`)? *Đề xuất* giọng nam trầm 72 (kể chuyện kinh dị).
12. **HUD/thông báo** (bị hạ, kẹt ngoài vùng an toàn): ghép hậu kỳ từ HUD Kho #396–#407 hay chữ đơn giản?

## 6. Ước tính chi phí sơ bộ (đường E1)
Giả định chung:
- ~18 shot, tổng ≈ 62 s video gen. Một phần là khung giữ/hậu kỳ không tốn tiền: đếm ngược 3 s, màn đen/trắng, lặp cảnh 4, mở lại cảnh 6.
- Video thực gen ≈ **55 s**: shot khó ≈ 30 s (portal 1/2/6, xúc tu, bóng mờ, đấu súng 8, Booyah 9), shot dễ ≈ 25 s.
- Ảnh: ~22 ảnh khởi đầu + ~6 khung cuối/neo + 30 % vẽ lại → ~36 ảnh.

| Khoản | Phương án A — E1 chuẩn (mọi shot khó nâng 1080p) | Phương án B — tiết kiệm (chỉ 4 shot then chốt nâng 1080p) |
|---|---|---|
| Ảnh GPT Image 2.5 (~0,052/ảnh × ~36) | 1,9 | 1,9 |
| Shot khó: nháp Seedance 2.5 480p (0,103/s × 30 s + làm lại 50 %) | 4,6 | 2,5 (16 s) |
| Shot khó: nâng 1080p (0,5254/s đo thật) | 15,8 (30 s) | 8,4 (16 s) |
| Shot dễ: Seedance 2.0 720p gen thẳng (0,15/s + làm lại 30 %) | 4,9 (25 s) | 7,6 (39 s) |
| TTS lời dẫn (9 câu) + SFX | ~0,5 | ~0,5 |
| Nhạc (2–4 đoạn) | 0,3–0,5 | 0,3–0,5 |
| Claude (Đạo diễn, QC) + Tổ rà soát | 1–2 | 1–2 |
| **Tổng** | **≈ 29–30 USD** | **≈ 22–24 USD** |

So với trần "< 1 phút < 30 USD":
- **A sát trần**, chưa có dư cho sự cố như #24.
- **B có dư ~6–8 USD** cho vẽ lại/làm lại.

*Đề xuất B* theo nguyên tắc chất lượng thấp trước, đạt rồi mới nâng:
- Nâng 1080p: cảnh 1 (ngã rẽ), 2 (vào cổng xúc tu), 3c (trời lốc đỏ), 9 (Booyah).
- Còn lại: 2.0 720p phóng ffmpeg.
- Bài học #24 đã tính trong số trên (vẽ lại 30 % ảnh, làm lại 30–50 % video).
- Nếu chạy thật, bước 1 là tạo Kho 0 USD + render plate đêm 0 USD. Sau đó mới báo giá chính xác theo bảng shot của Đạo diễn (Đạo diễn chạy khoảng 0,5–1 USD Claude, cần duyệt riêng).

Chi thật phiên này: **0 USD** (trần 0,5 USD, không gọi Claude).
