# Đánh giá vai Đạo diễn (Director) — đã làm tốt việc được giao chưa, sửa tối ưu thế nào (14/10/2026)

Người dùng hỏi 14/10: "kiểm tra Director đã làm tốt những vai trò nó được giao chưa? Nếu chưa thì cách tối ưu là gì?"

**Phạm vi + giới hạn bằng chứng:** phiên cloud, KHÔNG có `data/` (CSDL thật). Đánh giá dựa trên: định nghĩa vai trong code / knowledge,
báo cáo các dự án thật trong repo (#22 Khủng Long Đỏ — `docs/TONG_HOP_3_LUOT_KHUNG_LONG_DO.md`; #24 — `docs/BAO_CAO_KET_THUC_DU_AN_24_2026-10-12.md`;
#27 tập 1 — `docs/handoff/P27_TAP1_TONG_KET_2026-10-13.md`), và 24 bài học người dùng chốt cho Đạo diễn (`knowledge/roles/director_p24_1110.md`).
Số đo theo từng job (tỉ lệ duyệt lần đầu, số lần sửa tay prompt) cần CSDL máy chính — đề xuất cách đo ở mục 4, việc D1.

## 1. Kết luận ngắn

| Vai được giao | Kết quả | Mức |
|---|---|---|
| **Ý đồ câu chuyện** (Tầng A: Bible, đường cảm xúc, nhịp, giữ thoại, thời lượng) | Cả 3 dự án: cấu trúc shot đúng mạch truyện, người dùng nhận phim; #22 "9 shot / 51 s đúng mạch", cặp shot "cùng khung" tốt | ✅ **Tốt** |
| **Viết chữ cho ảnh / video** (Tầng B: `image_prompt`, `blocking`, tả đạo cụ, nền) | Nguồn lỗi LỚN NHẤT: #22 sai 6 loại chi tiết lượt 1; #24 18 vòng vẽ lại ảnh; #27 phải thêm 18 bài học trong 1 ngày (bài 7–24); lỗi hệ thống #27 số 1 (chữ tả nền trái render 3D) và số 3 (skin "thang máy" hiểu là thang máy thật) | ❌ **Yếu** |
| **Hình học máy / dàn cảnh** (camera_plan, stage_specs, vị trí sau động tác) | #24 bài 1–3 (máy thấp mà tả thấy miệng giếng; người trườn ra vẫn đứng chỗ cũ; sửa một người làm lệch ảnh đã duyệt) | ⚠ **Chưa đạt** — code giải máy (`stage_camera`) đang tách việc này khỏi chữ, chưa verified |
| **Nhất quán giữa shot** (hướng đi, bên trái/phải, cùng vật cùng dạng / chỗ) | #27 bài 8, 15, 19, 22: tường keo 2 màu, cổng đổi chỗ, Kelly đi ngược hướng, cổng đổi cỡ | ❌ **Yếu** |
| **Gọi đúng tài nguyên Kho** (tên đạo cụ, vật, trang phục) | #22 "mũ" → mũ bảo hiểm, "xanh" → blue; #27 bài 7, 16: viết "assault rifle" chung → không gửi ảnh Kho → vẽ súng khác | ❌ **Yếu** — đã có code chèn tên (`project_prop_lock`), chưa verified |
| **JSON đúng định dạng** | #22 `bad_json_retry` ×2; #27 hỏng định dạng khóa nhân vật, mất 0,93 USD (đã sửa 12/10) | ⚠ |
| **Viết lại prompt trước gen lại** (`director_rewrite`) | Chưa có lượt chạy thật nào (#22 không chạy); C1 14/10 vừa thêm rà ngay | ❓ **Chưa có dữ liệu** |
| **Điền BYĐ** (`shot_intent`) · **Trả lời Biên tập viên** (prompt 25) · **Sơ đồ khối** | Cờ TẮT ở #24; chưa có dự án thật đo | ❓ **Chưa có dữ liệu** |
| **Học từ lỗi** | "Sau lượt 1, mọi sửa nằm ở dữ liệu cảnh do người / phiên Claude sửa — vai Đạo diễn không học lại" (#22 mục 2.3). Bài học vào tay qua file knowledge | ❌ **Chưa có vòng học tự động** |

**Tóm lại:** Đạo diễn làm TỐT phần "nghĩ" (truyện, cảm xúc, nhịp), làm KÉM phần "tả sự thật bằng chữ" (nền, đạo cụ, kích thước, hướng, hình học
máy). Phần kém không phải do thiếu luật: Đạo diễn đã đọc ≈ **165 KB luật bằng chữ** mỗi lượt (`director.md` 47 KB, `dp.md` 39 KB,
`director_p24_1110.md` 15 KB, prompt 17 27 KB, prompt 19 16 KB…) mà vẫn sai — mỗi dự án thêm một loạt bài học mới.

## 2. Gốc lỗi (theo bằng chứng)

1. **Bắt model viết bằng chữ những SỰ THẬT mà code đã biết.** Nền đã có render 3D, đạo cụ đã có tên + ảnh trong Kho, kích thước vật mốc đã
   đo, độ cao máy đã có số. Đạo diễn tả lại tự do → có chỗ mâu thuẫn → model ảnh theo chữ, bỏ ảnh. Ví dụ: #27 shot 17/21 chữ tả "tháp ở xa,
   cầu thang, nhà mái đỏ" trái plate; #24 shot 5 tả lòng giếng khi máy thấp hơn miệng giếng; #22 chèn "quảng trường, dừa, biển" vào shot
   trong phòng. **14/24 bài học** của `director_p24_1110.md` thuộc loại này (1, 7, 8, 9, 12, 13, 14, 15, 16, 17, 19, 22, 23, 24).
2. **Luật dồn thành văn xuôi ngày càng dài + lẫn chi tiết riêng từng dự án.** Bài 14 (vật bị nguyền OB55), 17 (trời OB55), 8 (2 dạng tường
   keo), 12 (tỉ lệ súng theo đầu) là SỰ THẬT của tài nguyên / sự kiện, không phải cách làm nghề — nhưng được nạp cho MỌI dự án. Luật dài
   loãng: điều quan trọng chìm giữa 165 KB, và mỗi dự án mới lại sinh lỗi mới ở chỗ khác.
3. **Không đo vai.** Không có số "bao nhiêu lần ảnh / clip bị loại vì chữ của Đạo diễn" theo dự án → không biết bài học mới có làm tốt hơn
   không. Nhiều cờ sửa lỗi Đạo diễn vẫn `verified: False` (chưa ai đo trên dự án thật): `shot_intent`, `p24_lessons`, `kld_lessons_prompts`,
   `project_prop_lock`, `plate_anchored_image`, `skill_object_guard`, `stage_camera`, `director_rewrite`, `continuity_layout`.
4. **Sửa tay đi vòng qua vai.** Khi người / phiên Claude sửa prompt trên CSDL, Đạo diễn không biết; lần sau viết lại lỗi cũ (#22 lượt 2–3).

## 3. Cách tối ưu — nguyên tắc: "Đạo diễn QUYẾT, code VIẾT sự thật, code ĐO kết quả"

Không thêm luật chữ mới. Chuyển phần Đạo diễn làm kém sang code (rẻ, chắc), giữ phần làm tốt cho Đạo diễn, và đo trước / sau.

| Bước | Làm gì | Vì sao tối ưu | Tiền | Nơi |
|---|---|---|---|---|
| **D1** | **Bảng điểm vai Đạo diễn** (code, 0 USD): mỗi dự án đếm — ảnh/clip bị loại + lý do theo khâu (review_log, `change_findings.khau`, diag `prompt_formula` / `shot_lessons` / `prop_lock`), số lần sửa tay `image_prompt` / `motion_prompt` (so bản Đạo diễn viết ↔ bản gửi), số VÀNG/ĐỎ code bắt trên chữ Đạo diễn, lượt JSON hỏng, tiền Claude của vai. Chạy trên #22 / #24 / #27 → mốc gốc; tập 2 → so | Biết "tốt chưa" bằng SỐ, không bằng cảm nhận; mọi bước sau chỉ giữ nếu số tốt lên | 0 | cloud viết code + test; máy chính chạy trên CSDL thật |
| **D2** | **Code viết câu sự thật, Đạo diễn chỉ chọn**: bật + đo trên tập 2 các cờ đã có — `plate_anchored_image` (câu nền sinh từ plate), `project_prop_lock` (tên đạo cụ Kho), `skill_object_guard` (vật kỹ năng), `shot_intent` (BYĐ enum thay chữ tự do), `stage_camera` (máy do code giải). Đạo diễn ghi ý đồ + chọn mục Kho / chỗ đứng; câu tả nền, đạo cụ, cỡ, hướng máy do code ghép từ dữ liệu | Chặn đúng gốc 1 (14/24 bài học); code đã có sẵn, chỉ thiếu đo | ≈ 0,1–0,2 USD Claude/dự án (BYĐ) | máy chính bật ở 🧪, đo bằng D1 |
| **D3** | **Gọn luật**: tách `director_p24_1110.md` thành (a) cách làm nghề chung, giữ (bài 1–6, 9–11, 13, 15, 18–21) và (b) sự thật tài nguyên / sự kiện (bài 8, 12, 14, 17, 23–24, một phần 7, 16, 22) → chuyển vào hồ sơ mục Kho (`assets.profile` / ghi chú mục), chỉ nạp khi shot dùng mục đó. Đo token vào trước / sau | Giảm loãng ngữ cảnh; dự án không dùng OB55 không phải đọc trời OB55; luật đi cùng tài nguyên nên dự án sau dùng lại đúng | 0 (rẻ hơn mỗi lượt) | cloud (tài liệu + code nạp theo mục Kho), cần người dùng duyệt nội dung chuyển |
| **D4** | **Vòng học từ sửa tay**: mỗi lần người sửa `image_prompt` / `motion_prompt` hoặc loại kèm ghi chú → lưu cặp (bản Đạo diễn ↔ bản người sửa) → đề xuất bài học ở trạng thái `proposed` (đã có `lessons` + `lesson_judge` + `feedback_to_mistakes`, cờ TẮT) → người duyệt mới vào knowledge | Chặn gốc 4; bài học có bằng chứng + có người duyệt, không tự phình | nhỏ (lesson_judge gọi Claude) | cloud nối code; máy chính bật |
| **D5** | **JSON có lược đồ**: lượt Đạo diễn trả qua tool use có `input_schema` (Claude API) thay vì "chỉ trả JSON" + sửa tay | Hết `bad_json_retry` và lỗi định dạng khóa nhân vật (0,93 USD #27) | giảm | cloud |

**Thứ tự đề xuất (cập nhật 14/10, xem mục 3b):** D1 (mốc) + D6 (đường như chat, thí điểm 3–5 shot) trước → D2 → D3 → D4 (học từ MÔ TẢ, không từ sửa tay) → D5. Không làm D2–D5 "mù" khi chưa có D1:
CHUẨN XÂY DỰNG yêu cầu "đã sửa" kèm bằng chứng chạy thật.

## 3b. Bổ sung 14/10 (người dùng): vì sao chat thì tốt mà vai Director thì kém — và người dùng KHÔNG nên sửa tay prompt

Người dùng: "đưa ảnh + nội dung cho Claude, bảo viết prompt Seedance thì hầu như đều tốt; người dùng chỉ diễn đạt ý bằng mô tả, chuyển
thành prompt là việc của công cụ và model → người dùng sửa tay prompt là không đúng." Đối chiếu code, hai đường KHÁC NHAU ở 4 chỗ:

| | Chat (tốt) | Pipeline hiện tại |
|---|---|---|
| **Ai viết prompt Seedance** | Claude | Shot Seedance dùng ảnh tham chiếu: **CODE ghép** từ các trường chữ của Đạo diễn (dịch sang tiếng Anh) — `core/seedance_refs.py::code_motion` / `shot_motion`, quyết định "no Claude motion call for Seedance groups". Không có Claude nào nhìn ảnh rồi viết |
| **Có nhìn ảnh không** | Có — đúng ảnh sẽ gửi | `image_prompt` / `blocking` / `action` do Đạo diễn viết **TRƯỚC khi có ảnh** (viết mù, cả phim một lượt). Motion Claude (shot không phải Seedance ref) có nhìn ảnh nhưng gộp tới 12 shot một lượt (`llm_runner.run_motion`, `MAX_IMAGES`) |
| **Một tác giả hay nhiều lớp** | Một đoạn văn liền mạch, một người viết | Prompt cuối = chữ Đạo diễn + nhiều lớp code nối thêm (khóa đạo cụ, câu nền plate, START LOCK, câu cấm dấu "+", vật kỹ năng, khóa trạng thái nhân vật, câu "Fix:" của QC…) — #22 đã ghi "khung shot và câu bối cảnh ghép từ nhiều nguồn mâu thuẫn" |
| **Mô tả của người dùng đi đâu** | Claude đọc mô tả, tự chuyển thành prompt | Ghi chú khi loại → câu "Fix:" nối cuối, hoặc người / phiên Claude **sửa tay prompt trên CSDL**; `director_rewrite` (Claude viết lại theo ghi chú) còn `verified: False` |

**Kết luận:** pipeline tốt ở phần "nghĩ" (ý đồ), nhưng phần "viết prompt" đã bị chia cho code và cho các lớp nối chữ — đúng chỗ chat làm
tốt nhất (một Claude NHÌN ảnh + đọc mô tả + viết một prompt liền mạch) thì pipeline không làm. Người dùng đúng: sửa tay prompt là dấu hiệu công
cụ chưa làm đúng việc; giao diện nên nhận MÔ TẢ, không nhận prompt.

**Đổi đề xuất:**
- **D4 (sửa):** KHÔNG học từ sửa tay prompt. Nút "✏ Sửa motion prompt" ở Bước 4 → thay bằng ô "Mô tả điều muốn đổi" (tiếng Việt) → Claude
  viết lại (đường D6). Bài học rút từ MÔ TẢ của người dùng + kết quả duyệt, người duyệt mới vào knowledge.
- **D6 (mới, ưu tiên cao nhất cùng D1) — "đường như chat" cho prompt video:** mỗi shot MỘT lượt Claude, đầu vào giống hệt cách người dùng làm
  trong chat: (1) ảnh khung đầu đã duyệt (+ khung cuối nếu có, + đúng các ảnh tham chiếu sẽ gửi), (2) ý đồ shot của Đạo diễn + mô tả / ghi chú
  của người dùng bằng tiếng Việt, (3) MỘT trang hướng dẫn ngắn riêng cho model đích (Seedance / Kling: giới hạn, cú pháp ref) thay cho 165 KB
  luật, (4) các sự thật code biết (nền plate, tên đạo cụ Kho, cỡ, hướng máy) đưa vào làm DỮ KIỆN để Claude viết, không nối sau. Đầu ra: một prompt
  liền mạch. Code chỉ KIỂM (luật cứng nhà cung cấp, cấm từ, độ dài) và báo — không nối câu. Giữ đường cũ sau cờ để so.
- **Cách chứng minh (CHUẨN XÂY DỰNG):** thí điểm 3–5 shot của #27 (đã có ảnh duyệt + clip cũ để so): sinh prompt bằng D6, người dùng xem prompt
  (0 USD video) → gen nháp 480p 3 shot (báo giá trước) → so với clip cũ bằng D1. Đạt thì bật cho tập 2. Chi phí Claude: 1 lượt có ảnh / shot
  (ước tính qua sổ chi trước khi chạy).

## 4. Việc giao (ghi hộp thư TODO)
- **Cloud:** D1 phần code (bảng điểm đọc CSDL, test trên CSDL tạm dựng lại ca #22/#24/#27) · D3 bản tách đề xuất (người dùng duyệt) · D5.
- **Máy chính:** chạy D1 trên CSDL thật #22/#24/#27 (0 USD) → gửi số; bật cờ D2 ở 🧪 trước tập 2 (sao lưu `data/feature_settings.json`).
- **Người dùng quyết:** đồng ý hướng "code viết sự thật" (D2) cho tập 2? Duyệt danh sách bài học chuyển sang hồ sơ Kho (D3)?
