# Tổ làm phim có người chịu trách nhiệm + chỗ sửa trên Dashboard + tốc độ web (21/10/2026)

> **Trạng thái: ĐỀ XUẤT — chờ người dùng duyệt** (Cấp 1, chỉ tài liệu, 0 USD). Nguồn: người dùng 21/10 (8 ý, chép ở mục 0) sau khi xem
> bảng credit #27. Đối chiếu code `main` = `097377ad` và Dashboard thật cổng 8501 (đo bằng trình duyệt, mục 3).

## 0. Người dùng nói (21/10)
1. Sân khấu 3D chỉ là công cụ, **chưa có 3D Artist** chịu trách nhiệm.
2. Storyboard chỉ dùng Deepix làm công cụ → **cần vai Họa sĩ storyboard** quản lý.
3. Prompt video do code ghép từ chữ Đạo diễn → thiếu nhất quán, không tự nhiên, ghép sai thứ tự ưu tiên → **cần một vai viết prompt chịu trách nhiệm**
   (Đạo diễn hoặc vai riêng).
4. Gen video dùng ClipAI như công cụ, không ai chịu trách nhiệm → **Đạo diễn quản lý**.
5. Lồng tiếng, nhạc, SFX, VFX, khớp môi, dựng: ClipAI chỉ là công cụ → **Đạo diễn hoặc Dựng chịu trách nhiệm**.
6. Chia vai rõ rồi thì **lỗi do các vai tự sửa**; **Claude (phiên Claude Code) chỉ sửa code**; **người dùng là đội trưởng quyết định**.
7. Plan mới nhất đã tìm hết thiếu sót của các khâu trên Dashboard chưa; shot/khâu nào cần sửa thông tin, sửa đầu vào thì đã có chỗ thao tác chưa.
8. Web chậm: mỗi lần bấm vào shot xem/sửa, hoặc đổi giữa các bước.

**Trả lời ngắn cho 7:** CHƯA. Kế hoạch V3.1 (`docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md`) lo độ tin cậy dữ liệu / gói gửi / QC, **không có việc nào về
vai chịu trách nhiệm, về đủ ô sửa cho từng khâu, hay về tốc độ Dashboard**. M4.7 chỉ có phần XEM (BYĐ, gói gửi), M4.8 bàn 3D mới có màn XEM. Mục 2 liệt
kê chỗ còn thiếu. **Trả lời ngắn cho 8:** đo được 4–5 s mỗi lần bấm, tab Motion #31 mất 36 s (mục 3).

## 1. Tổ làm phim mới — mỗi khâu một vai chịu trách nhiệm, công cụ nằm DƯỚI vai

Nguyên tắc: **vai = người chịu trách nhiệm** (nhận đầu vào, làm, TỰ KIỂM, sửa, giao); **ClipAI / Deepix / Blender / Meshy / sync.so / ffmpeg = công cụ của
vai**, không ai "giao việc cho công cụ" mà không có vai đứng tên. Vai là Claude chạy trong pipeline (claude_cli, theo sổ chi), có tài liệu nghề + quyền
sửa đúng phần dữ liệu của mình.

| Vai | Chịu trách nhiệm | Công cụ | Quyền sửa (chỉ phần của mình) | Hiện nay |
|---|---|---|---|---|
| **Đội trưởng** (người dùng) | Quyết định, duyệt chốt, chọn bản | Dashboard | mọi thứ | ✓ |
| **Biên kịch** | Kịch bản, thoại | — | `text`, thoại | có vai (prompt 23), ít dùng |
| **Đạo diễn** (trưởng tổ) | Ý đồ, cảm xúc, nhịp; **quản lý gen video** (ý 4): chọn model/đường gen, duyệt clip, quyết gen lại hay đổi cách; nhận việc các vai trả lên | ClipAI (video) qua vai Viết prompt | ý đồ cảnh/shot, `video_route`, model, quyết duyệt/loại clip (trong trần) | có vai nhưng không quản lý gen video; người + phiên Claude quyết |
| **Quay phim** | Máy, cỡ, góc, bố cục, ánh sáng | máy ảo `plate_camera` | `size/angle/move/lens_mm/start_frame/plate_view` | có vai |
| **3D Artist** (MỚI, ý 1) | Sân khấu 3D: chọn/kiểm mô hình, đặt vật mốc + người nộm đúng cỡ, render plate, kiểm plate khớp kịch bản (trời, giờ, chỗ đứng); sửa khi ảnh lệch nền | Blender, Meshy, `stage_*`, `whitebox` | `plate_spot`, sân khấu cảnh, render lại nền | chỉ có code + bàn duyệt sân khấu (prompt 29*), không vai đứng tên lỗi nền |
| **Họa sĩ storyboard** (MỚI, ý 2) | Ảnh khung đầu: NHÌN plate + ảnh Kho rồi viết prompt ảnh, gen, tự kiểm (so plate, so Kho), tự vẽ lại ≤ 3, trình Đạo diễn | Deepix (Seedream / GPT Image), `chat_prompt` (D6 ảnh) | `image_prompt`, chọn ảnh ref, vẽ lại | không có vai; `image_prompt` do Quay phim viết mù trước khi có ảnh |
| **Viết prompt video** (MỚI, ý 3 — thuộc Đạo diễn) | MỘT prompt liền mạch / shot từ ảnh đã duyệt + ý đồ + dữ kiện code; đúng thứ tự ưu tiên của tổ; code chỉ KIỂM, không nối câu | D6 `chat_prompts` + `knowledge/model_guides/` | `motion_prompt` | D6 có (cờ BẬT cho #27 tập 2) nhưng là "bước", chưa là vai; code vẫn nối lớp khi cờ tắt |
| **Âm thanh** (thuộc Dựng, ý 5) | Lồng tiếng (giọng, cách đọc, chữ thường), nhạc theo đường cảm xúc, SFX + âm nền, khớp môi | ClipAI TTS / nhạc / SFX, sync.so | giọng, `delivery`, nhạc, `sfx_plan` | rời rạc ở Bước 5; #27 phiên Claude Code chọn giọng + sửa chữ |
| **Dựng / VFX** (mở rộng, ý 5) | Cắt, nối, chuyển cảnh, chữ, popup, **VFX ghép bằng code** (vật kỹ năng, chữ tên cổng), dựng bản giao, tự rà | ffmpeg, `final_cut`, `ffmpeg_studio`, `skill_objects` | bản dựng, hiệu ứng ghép | #27 do phiên Claude Code làm bằng script ngoài (`tools/experiments/p27_*`) |
| **QC** | Không là vai riêng: mỗi vai tự kiểm phần mình bằng số đo code + nhìn; Tổ QC giữ TẮT tới khi ≥ 75 % (`qc-team-off`) | `clip_measure`, `framing_guard`, `camera_match_qc` | — | như cũ |
| **Kỹ sư** (phiên Claude Code / cloud / Codex) | **CHỈ code** (ý 6): sửa lỗi công cụ, thêm ô sửa, thêm năng lực cho vai | git | code + test | hiện còn sửa thẳng dữ liệu sản xuất (mục 1b) |

### 1a. Vòng sửa lỗi (ý 6)
1. Lỗi (Đội trưởng mô tả, QC đo được, hay vai sau phát hiện) → **phiếu lỗi** gắn đúng khâu + shot (dùng mã `devsys/errors.json` + `qc_evidence`).
2. Phiếu tới **vai chịu trách nhiệm khâu đó** → vai sửa ĐẦU VÀO của mình (≤ 2 lần đổi đầu vào, luật `CHUAN_XAY_DUNG`) → tự kiểm → giao lại.
3. Hết 2 lần mà chưa đạt → **trả lên Đạo diễn**: đổi cách (đổi model, ghép bằng code qua Dựng/VFX, đổi ý đồ) hoặc hỏi Đội trưởng nếu tốn tiền mới / đổi ý đồ.
4. Lỗi do CÔNG CỤ / code (ví dụ thiếu ô sửa, gửi sai gói, Dashboard chậm) → phiếu sang **Kỹ sư** qua hộp thư (`tools/hop_thu.py`); vai không tự vá code.
5. Mọi bước sửa hiện trên Dashboard (ai sửa, sửa gì, trước/sau, tiền) — Đội trưởng chỉ duyệt/quyết.

### 1b. Luật mới cho phiên Claude Code (ý 6)
- **Không sửa thẳng dữ liệu sản xuất** (`scenes.data`, prompt, Kho) bằng SQL / script để chữa một shot. Bằng chứng việc này đang xảy ra: 376 lần sửa tay prompt
  (14/10, lẫn người + Claude), các bản sao lưu `data/manifest.backup_20261018_truoc_sua_motion.sqlite`, `…_truoc_sua_shot_1_8_9_23`, `…_truoc_sua_15_18_33`…
- Gặp lỗi sản xuất: tạo phiếu cho vai (hoặc bấm nút của vai trên Dashboard); nếu vai không làm được vì thiếu công cụ → đó là việc code của Kỹ sư.
- Ngoại lệ chỉ khi Đội trưởng bảo rõ trong chat, và ghi lại lý do.

## 2. Dashboard: chỗ sửa đầu vào theo khâu (ý 7)

Rà các ô sửa ở `dashboard/steps/step1*.py…step5.py` + các khung UI phụ (21/10). ✅ có ô sửa · ⚠ có một phần / chỉ xem · ❌ không có.

| Khâu / vai | Đầu vào cần sửa được | Hiện có | Thiếu |
|---|---|---|---|
| Biên kịch | kịch bản, thoại, cách đọc | ✅ Bước 1: nội dung cảnh, bảng thoại (người nói, nhịp, cường độ, ngắt) | — |
| Đạo diễn | ý đồ cảm xúc, diễn xuất, `why`, thời lượng, nhân vật | ✅ Bước 1 trình sửa cảnh | ❌ ô "mô tả điều muốn đổi" cho Đạo diễn làm lại một shot theo ý (hiện chỉ "↻ Chia shot lại cảnh này") |
| Đạo diễn — BYĐ (tư thế đầu/cuối, đạo cụ `vat`, hướng) | sửa từng mục | ⚠ chỉ XEM (M4.7 phần XEM, cờ TẮT) | ❌ ô sửa BYĐ (M4.7 phần sửa / overrides = C3-4 chờ) |
| Quay phim | cỡ, góc, chuyển động, đường gen, chuyển cảnh, rung | ✅ Bước 1 (`size/angle/move/video_route/transition_in/shake_in`) | ❌ `lens_mm`, `plate_view` (hướng nền), `start_frame`, khớp môi `lip_sync` — không có ô (grep `dashboard/` = 0) |
| 3D Artist | chỗ đứng trên sân khấu (`plate_spot`), vật mốc, người nộm, trời/giờ của nền | ⚠ "↻ Render lại nền 3D shot N (0 USD)" ở Bước 2; màn XEM sân khấu (C-STAGE-VIEW, chờ gộp) | ❌ chọn chỗ đứng / đổi hướng máy 3D / dời vật mốc / duyệt-trả lại sân khấu (M4.8b chưa có kế hoạch nút — C-STAGE-PLAN đang CHỜ) |
| Họa sĩ storyboard | prompt ảnh, ảnh ref gửi kèm, nền in-game, mô tả muốn đổi | ✅ "Prompt ảnh", Background, "Lý do bỏ duyệt", D6 mô tả khi loại (cờ `chat_prompts`) | ⚠ chọn/bỏ từng ảnh tham chiếu sẽ gửi (đang XEM được ở thẻ gói gửi, không sửa) |
| Viết prompt video | motion prompt, `end_state`, video ref | ✅ Bước 1/3: motion prompt, 🏁 trạng thái cuối, video ref | ⚠ còn ô SỬA TAY prompt thô (người dùng 14/10: không nên sửa tay) — đổi thành "mô tả điều muốn đổi" ở MỌI chỗ (Bước 3 còn ô dán JSON) |
| Đạo diễn — gen video | model, nhóm cảnh, bản nháp/bản cao, gen lại | ✅ Bước 4 | ⚠ "Câu sửa (tiếng Anh)" khi gen lại — bắt người viết tiếng Anh; nên là mô tả tiếng Việt cho vai Viết prompt |
| Kho (nhân vật, trang phục, dạng, vật) | mô tả, ảnh, dạng (form), giọng | ✅ Bước 1 Character Bible | ⚠ dạng/outfit/tóc theo provenance (M2.3 chưa làm) |
| Âm thanh | giọng từng câu, chữ đọc, nhạc theo đoạn, SFX theo shot | ✅ Bước 5 giọng, nhạc 2 đoạn, SFX gợi ý | ❌ sửa chữ đọc TTS từng câu (#27 lỗi 9 IN HOA), ❌ khớp môi |
| Dựng / VFX | chuyển cảnh, popup, chữ, ảnh bìa, dựng lại | ✅ Bước 5 nhiều nút | ❌ **VFX ghép bằng code** (tường keo mọc, chữ tên cổng đúng lúc đọc); ❌ dựng kiểu #27 (đệm từng shot, nối nhạc nhiều đoạn, lời dẫn theo mốc) — logic có một phần trong `ffmpeg_studio`/`music_cues`, chưa có nút |

## 3. Tốc độ Dashboard (ý 8) — số đo thật 21/10

Đo trên Dashboard đang chạy (cổng 8501, máy chính), trình duyệt nội bộ, từ lúc bấm tới khi trang ngừng thay đổi ≥ 2 s:

| Thao tác | #22 (9 shot) | #31 (39 shot) |
|---|---|---|
| Đổi bước Storyboard → Video | 3,9 s | — |
| Đổi bước → Kịch bản | 2,6 s | — |
| Đổi bước → Storyboard | 4,4 s | mở thẳng trang: 6,2 s |
| Bấm "✎ Sửa" một thẻ shot | 4,3 s | 4,7 s |
| Mở tab "🎞 Motion & giọng" | — | **36 s** |
| Quay lại tab "🖼 Ảnh + QC" | — | 0,4 s |

Khi không bấm gì trang không chạy ngầm (0 thay đổi / 15 s). **Gốc khả dĩ (chưa đo phía máy chủ):** Streamlit chạy lại TOÀN BỘ trang mỗi lần bấm — mở một
shot cũng dựng lại mọi thẻ của mọi shot, header, thanh trạng thái; chỉ 5 chỗ dùng `st.fragment` và 19 chỗ cache trên 13 577 dòng `dashboard/`. Tab Motion
#31 có thể còn nạp nhiều video/ảnh một lúc.

Việc đề xuất (0 USD):
- **P1 đo phía máy chủ:** bọc thời gian từng khối (header, thanh bước, từng thẻ, đọc CSDL) ghi `diag`/log khi rerun > 1 s; chạy trên bản sao CSDL #31 → bảng
  khối nào tốn bao nhiêu. Không sửa mù.
- **P2 thẻ shot thành fragment:** bấm "✎ Sửa"/"Chi tiết"/duyệt một shot chỉ chạy lại thẻ đó; trình sửa mở trong `st.dialog` riêng.
- **P3 nạp lười:** tab Motion / video chỉ nạp media của shot đang mở (ảnh thu nhỏ trước, video khi bấm phát); phân trang ≥ 12 shot.
- **P4 cache đọc CSDL theo phiên bản dự án** (đổi khi có `change_events` mới) cho số đếm tiến độ, thanh trạng thái, gói gửi.
- Mục tiêu nghiệm thu: bấm mở shot ≤ 1 s, đổi bước ≤ 2 s, tab Motion #31 ≤ 3 s — đo lại cùng cách ở bảng trên.

## 4. Việc đề xuất — đợt M6 "Tổ có chủ" (thêm vào Master Build sau khi duyệt)

| Mã | Việc | Cấp | Tiền |
|---|---|---|---|
| M6.0 | Ghi sổ quyết định (vai + luật "Claude chỉ sửa code") + check: phiên Claude Code ghi `scenes.data` ngoài đường của vai → diag | 2 | 0 |
| M6.1 | Khung vai: bảng `crew_roles` (vai, khâu, trường được sửa, công cụ), phiếu lỗi theo vai (dùng `errors.json` + `qc_evidence`), vòng sửa 1a | 2 | 0 |
| M6.2 | Vai **Họa sĩ storyboard**: D6 ảnh thành vai (nhìn plate + Kho), tự kiểm so plate, tự vẽ lại ≤ 3, trình Đạo diễn | 2 | Claude/shot (claude_cli) |
| M6.3 | Vai **Viết prompt video** dưới Đạo diễn: D6 mặc định, bỏ đường code nối lớp khi vai bật; ô "mô tả điều muốn đổi" thay mọi ô sửa tay/câu tiếng Anh | 2 | như trên |
| M6.4 | Vai **3D Artist**: nhận phiếu "nền lệch", sửa chỗ đứng / máy / vật mốc, render lại; gộp với M4.8b bàn đạo diễn 3D | 2 | 0 (Blender) |
| M6.5 | Đạo diễn **quản lý gen video**: quyết duyệt/loại/gen lại trong trần theo số đo + ý đồ, trả lời phiếu các vai | 2 | trong trần dự án |
| M6.6 | Vai **Âm thanh + Dựng/VFX**: đưa `p27_final_mix` + ghép vật kỹ năng + chữ theo mốc thành khâu Bước 5 có nút; sửa chữ TTS từng câu | 2 | 0 (ffmpeg) |
| M6.7 | Ô sửa còn thiếu ở mục 2 (BYĐ, `lens_mm`/`plate_view`/`lip_sync`, ảnh ref gửi kèm) — mỗi ô qua guard M2.5 | 2 | 0 |
| M6.8 | Tốc độ Dashboard P1→P4 (mục 3) | 2 | 0 |

Thứ tự đề xuất: **M6.8 P1 + M6.0 trước** (đo + luật, không phụ thuộc M2) → M6.1 → M6.3 (lợi nhất, D6 đã có) → M6.2 → M6.6 → M6.4 (cùng M4.8) → M6.5 → M6.7.
Liên quan M2 (BYĐ v2, guard ghi M2.5): M6.7 và M6.1 cần guard M2.5 để vai không ghi đè chỗ Đội trưởng đã khóa.

## 5. Cần Đội trưởng quyết
1. Duyệt danh sách vai ở mục 1 (thêm/bớt/đổi tên)? "Viết prompt video" là vai riêng dưới Đạo diễn (đề xuất) hay chính Đạo diễn?
2. Vai được TỰ sửa + tự gen lại trong trần dự án (≤ 3 ảnh, ≤ 2 video/shot) không cần hỏi, chỉ hỏi khi vượt trần / đổi ý đồ — đồng ý?
3. Thứ tự M6 ở mục 4, và xếp M6 trước hay sau M2 (M2 đang chờ golden)?
