# Kế hoạch tổng — rà soát toàn Dashboard: lỗi → bước cần tối ưu → giải pháp → lộ trình

## Context
Đợt thử thật GĐ6 (3 phương án V0/V1/V2, kịch bản Kenta) gen lỗi nhiều, tốn tiền, và nhiều lỗi lặp lại dù các phiên trước đã định hướng
tránh. Người dùng yêu cầu một **kế hoạch tổng chi tiết**: liệt kê toàn bộ lỗi, các bước cần tối ưu, giải pháp, **đánh giá & phân tích
từng phân đoạn**, rà soát kỹ toàn Dashboard, và **tổng kết những gì đã làm** trong phiên này.
Nguồn: code (đọc trực tiếp + 3 lượt rà soát theo phân đoạn), số liệu thật GĐ6 (`tools/audit_run.py` trên CSDL chỉ đọc,
`tools/recover_clips.py` đối chiếu ClipAI), `docs/PHAN_TICH_LOI_GD6_2026-09-24.md` (R1–R7, F1–F11),
`docs/PHAN_TICH_VONG_DASHBOARD_2026-09-24.md` (V1–V8, W1–W17), plan người dùng gửi (C1–C8, S1–S4), 2 skill mới, các tài liệu rà soát cũ
(DASHBOARD_REVIEW, UI_AUDIT, WORKFLOW_REVIEW, V2_TEST_REPORT, TODO "Tồn đọng").

---

## 1. Tổng kết những gì ĐÃ LÀM trong phiên này (nhánh `claude/upbeat-hawking-6o9njo`, PR #1)
| # | Việc | Kết quả / file | Commit |
|---|---|---|---|
| 1 | Phân tích vòng chạy Dashboard từ code | 8 lỗ hổng cấu trúc V1–V8, vòng mới "rẻ trước, đắt sau, người duyệt ở 2 điểm", việc sửa W1–W17 — `docs/PHAN_TICH_VONG_DASHBOARD_2026-09-24.md` | 4844231, b52418c |
| 2 | Công cụ báo cáo chỉ đọc tiền & lỗi theo bước | `tools/audit_run.py` (+test): tiền theo lý do gửi, gen lại cùng đầu vào, tiêu chí QC kéo trượt, người vs QC, lỗi nhà cung cấp, shot tốn nhất, câu sửa lọt vào prompt, mục 2b "clip làm từ ảnh có lỗi nhìn thấy trước" | e407284 … a8e2b1a |
| 3 | Số liệu thật GĐ6 (người dùng chạy) | Sổ ghi $42,88 (khớp); 59% tiền video là gửi lại; QC gen lại cùng đầu vào 3/3, 0 dùng được; QC ảnh V1 thấy lỗi bố cục (TB 0,52) nhưng không chặn; ~70% tiền video thật trả cho clip làm từ ảnh có lỗi nhìn thấy trước, V1 16/16 clip đó vào bản cuối | 53feaca, a8e2b1a |
| 4 | Công cụ đối chiếu/lấy lại clip ClipAI (W14) | `tools/recover_clips.py` (+test). Thật: quét hết 136 task Kling → **16 task "not_found" không hề được ClipAI tạo** → 0 clip để lấy lại, sổ chi **ghi thừa ~$15**, tiền video GĐ6 thực **~$28–29**; chặn bản quyền: ClipAI chỉ báo câu chung, `cost=0`; task hỏng vì prompt > 512 có `cost=90` | d1604bb, 6a1c404, 055d206 |
| 5 | **W12 — ClipAI không tạo task** (code) | Dò trạng thái quét 3 trang + đọc danh sách dùng chung 5s; task chưa từng thấy sau 6 lần = `not_created` → bỏ khỏi sổ chi, giảm số job đồng thời, gửi lại không tính lượt (tối đa 3 lần), không tính vào trần job; `tests/test_not_created.py` (**còn hở ở chế độ tay — xem O7**) | 6520861 |
| 6 | Quyết định người dùng → PLAN.md Mục 5 | 2 look hình: **anime** và **giống y hệt mẫu in-game Free Fire**; cổng storyboard bật mặc định; tự gen lại tối đa **2 lần** (mỗi lần đổi đầu vào); bỏ video mẫu theo dự án → **gói look đã kiểm** + **thư viện prompt mẫu tự đúc kết** (W17) | a37aea2, c5c4834 |
| 7 | `tools/build_docs.sh` chạy được trên Linux/cloud | pandoc/pypandoc + Chromium | a37aea2 |
| 8 | Đối chiếu 2 skill mới → `knowledge/` | Film Direction Kit 2.0.0 (render_style, bảng ký hiệu máy + áp dụng cho prompt ảnh, 3 nguyên lý tri giác); Seedance Director 1.0.2 (mỗi ảnh tham chiếu một vai trò) | 69edb13 |
| 9 | **W1 — cổng duyệt storyboard** (code) | `core/storyboard_gate.py`, pha `storyboard` trong autopilot, ô bật/tắt Bước 1, Bước 2 "🎞 Storyboard" có cờ ⚑ + ảnh tài nguyên + nút duyệt; ảnh đổi sau khi duyệt thì cổng bật lại; `tests/test_storyboard_gate.py` | c5c4834 |
| 10 | PR #1 | https://github.com/hongvietdoan-byte/Workflow-t-ng-h-a-quy-tr-nh-l-m-video-AI/pull/1 — 682 test pass (chưa thử API thật) | — |

---

## 2. Bức tranh tổng — vì sao gen lỗi nhiều và tốn tiền
- **Tiền:** video là khoản chính. GĐ6 sổ ghi $42,88 nhưng ~$15 là task "ma" → thực ~$28–29. Trong tiền thật: ~70% trả cho clip làm từ ảnh
  đã sai; phần tránh được ước ~45–50%.
- **Năm nguyên nhân gốc hệ thống:**
  1. **Hỏng im lặng** — thiếu đầu vào (ảnh tham chiếu, Lock, layout, tham chiếu Seedance) mà không báo, pipeline vẫn chạy và trả tiền.
  2. **Tự động hoá trả tiền cho lỗi, không tự động hoá tìm lỗi** — mọi vòng sửa ở lớp cuối (gen lại), không quay về lớp gốc; gen lại cùng đầu vào.
  3. **Không ai nhìn ảnh trước khi chi tiền video** (đã sửa bằng W1) và QC chưa hiệu chỉnh nhưng được tự duyệt.
  4. **Lớp mới không kế thừa biện pháp cũ** — multi-shot, v3 shot, nhân bản dự án đi đường riêng, bỏ qua luật đã có.
  5. **Sổ chi và trần không phản ánh tiền thật** — Claude đi ngoài sổ, video ghi lúc gửi không đối chiếu.

---

## 3. Đánh giá & phân tích từng phân đoạn
Thang: ✅ tốt · ⚠ dùng được nhưng có lỗ · ❌ đang gây lỗi/tốn tiền. Mã lỗi tra ở Mục 4.

### P0 · Thiết lập dự án & Kho tài nguyên (⚠)
- **Tốt:** kho FF 64 nhân vật + thú cưng, nhập hàng loạt, tự dò tên trong kịch bản, ảnh trang phục riêng.
- **Yếu:** đường dẫn ảnh tương đối theo thư mục làm việc (A1) → Director/QC có thể thấy 0 ảnh; so tên theo chữ đầu (A15); không có
  trường look (A5) — `style_profile` trộn nhịp dựng với look; chưa có chiều cao/vóc dáng (A7).
- **Tối ưu:** look `ANIME`/`FF_INGAME` là thuộc tính dự án; ảnh tài nguyên = chuẩn tuyệt đối với look in-game; kiểm ảnh đọc được khi mở Dashboard.

### P0b · Dùng Kho tài nguyên hợp lý hơn (yêu cầu bổ sung của người dùng) (⚠ → trọng tâm cho look in-game)
**Hiện trạng (core/assets.py, core/db.py, core/asset_vision.py, core/subjects.py):**
- Kho chỉ giữ **ảnh + tên + bí danh + mô tả** (tối đa 6 ảnh/tài nguyên). Mọi thông tin chuẩn của nhân vật — Character Lock, ảnh mốc đã duyệt,
  giọng, trang phục đã chọn, chủ thể Seedance (`subject_asset_id`) — nằm trong bảng `characters` **theo từng dự án** → mỗi dự án làm lại
  (tốn Claude, mỗi dự án một kiểu, nhân bản chép bản cũ — A2/A3; R1 lặp ở dự án #1 lẫn GĐ6).
- Ảnh trong kho **không có nhãn** (toàn thân / nửa người / cận mặt / sau lưng / tư thế kỹ năng / bảng thiết kế / skin). `best_references` chọn chỉ
  theo **hình dạng file** (ảnh dọc trước, lớn nhất; ảnh ngang ≥ 1200 px coi là bảng thiết kế) → shot cận nhận ảnh toàn thân (mặt nhỏ, khó giữ
  mặt), shot quay lưng nhận ảnh chính diện; kho đã nhập cả "toàn thân" lẫn "nửa người" nhưng không phân biệt khi dùng.
- Bối cảnh: chọn ảnh **"rộng nhất"**, không dùng góc máy đã phân tích sẵn trong `set_analyses` → ảnh bản đồ chụp từ trên cao làm nền cho shot
  ngang tầm mắt (R7).
- Mỗi ảnh gửi đi không nói rõ **điều khiển gì / không điều khiển gì** (Seedance Director 1.0.2).
- Chưa có **ảnh chuẩn theo look**: look anime phải "chuyển phong cách" từ ảnh in-game ở mọi shot → mỗi shot/dự án một kiểu anime khác nhau.
- Chưa nhập: 331 ảnh bản đồ in-game (trước bị loại vì > 10 MB — **nay `assets._shrink` đã tự thu nhỏ**, nhập được), artwork, icon kỹ năng.
- So tên theo chữ đầu (A15), đường dẫn tương đối (A1); kiểm "nhân vật có ảnh không" chỉ ở lúc gen.

**Giải pháp (T1–T10):**
- **T1 Hồ sơ nhân vật chuẩn ở cấp KHO (một nguồn chuẩn):** mỗi nhân vật trong kho có hồ sơ duyệt một lần — Lock (must_keep / forbidden), chiều
  cao + vóc dáng (F10), màu/đặc điểm nhận diện, mô tả ngắn, giọng mặc định, `asset_uri` Kho chủ thể Seedance, ảnh mốc theo từng look. Claude đọc ảnh
  soạn nháp (tái dùng luồng nền `asset_vision`), người duyệt. **Dự án kế thừa**, chỉ thêm biến thể (trang phục/skin, bị thương, hóa trang); Director
  không được viết lại phần chuẩn → sửa A2, A3, A11, A12, F1, F10, O6 tận gốc, và bớt 1 lượt Claude/nhân vật/dự án.
- **T2 Nhãn ảnh trong kho:** loại khung (toàn thân / nửa người / cận / sau lưng / nghiêng / tư thế kỹ năng / bảng thiết kế), skin/phiên bản, look
  (in-game / anime). Claude gắn tự động một lần + người sửa; bảng thiết kế vẫn chỉ dùng qua chữ (đã có).
- **T3 Chọn ảnh tham chiếu theo shot:** cỡ cảnh (CU/MCU → nửa người/cận; WS → toàn thân), hướng (quay lưng → ảnh sau lưng), số người trong shot
  (ít người → thêm góc; đông người → mỗi người 1 ảnh rõ nhất), look của dự án.
- **T4 Ảnh map in-game KHÔNG làm khung nền nữa (người dùng xác nhận 2026-09-24: ghép thẳng ảnh chụp từ trên cao làm nền → sai bố cục, sai tỉ lệ
  người/cảnh):** xem mục "Bối cảnh & ảnh map" ngay dưới.
- **T5 Vai trò rõ cho từng ảnh gửi** trong `assets.reference_note`: nhân vật = mặt/tóc/trang phục/tỉ lệ, không điều khiển bố cục; bối cảnh = kiến
  trúc/bố trí, không điều khiển người/cỡ cảnh; layout = vị trí tương đối, không điều khiển cỡ người; nêu ảnh nào thắng khi chồng vai trò.
- **T6 Ảnh chuẩn theo look (anime):** mỗi nhân vật tạo **một lần** bộ ảnh chuẩn anime (toàn thân + nửa người, từ ảnh in-game, giữ nguyên nhận diện),
  người duyệt, lưu vào kho nhãn `look=anime` → mọi dự án anime dùng bộ này làm tham chiếu → anime nhất quán giữa các dự án. Look in-game dùng ảnh gốc.
  (Tốn vài ảnh Deepix/nhân vật — xin phép, làm dần theo nhân vật được dùng.)
- **T7 Kho chủ thể Seedance theo tài nguyên:** tải lên một lần, `asset_uri` lưu ở kho, dùng lại mọi dự án (sau khi thử K5 cho 1 nhân vật FF).
- **T8 Kho là nền của gói look + thư viện prompt mẫu (W17):** mẫu prompt/ảnh đạt gắn với nhân vật/bối cảnh trong kho, dùng lại theo look × model.
- **T9 Sửa nền:** đường dẫn tuyệt đối theo gốc repo (A1), so tên theo tên đầy đủ/bí danh + cảnh báo khi 2 người cùng khớp (A15), kiểm trước khi chạy:
  nhân vật trong kịch bản có hồ sơ chuẩn + ảnh đúng look chưa.
- **T10 Bảng "sức khỏe kho":** nhân vật thiếu hồ sơ chuẩn / thiếu ảnh nửa người / sau lưng / ảnh chuẩn anime; bối cảnh thiếu ảnh ngang tầm mắt →
  biết cần bổ sung gì trước khi làm dự án.

#### Bối cảnh & ảnh map — đổi cách dùng (B1–B6)
**Vì sao sai:** layout hiện tại (`core/layout.py` + `core/previz.py`) lấy ảnh map làm nền, **dán hình cắt nhân vật** theo phối cảnh của ảnh đó rồi gửi
làm **ảnh tham chiếu số 1** cho Deepix; ảnh bối cảnh còn được gửi kèm với câu "keep the look of this environment". Model image-to-image **chép
điểm ảnh**, nên chép luôn góc máy từ trên cao, vị trí mái nhà, và cỡ người tí hon — bất kể shot là MCU ngang tầm mắt (R7: V2 S22 "CU" ra Kenta
tí hon trên bãi cỏ; `set_match`/`composition` TB 0,52 ở V1). Tính toán phối cảnh trong code đúng cho **ảnh nền**, nhưng shot cần góc máy khác thì
ảnh nền đó không dùng được.
**Nguyên tắc mới: ảnh map là NGUỒN THÔNG TIN, không phải KHUNG NỀN.**
- **B1 Hồ sơ bối cảnh (chữ) thay cho điểm ảnh:** đọc mỗi ảnh map **một lần** (mở rộng `set_analyses` đã có: camera, mốc + chiều cao thật, ánh
  sáng) thành hồ sơ bối cảnh ở cấp kho: kiến trúc, vật liệu, màu, mặt đất, **mốc nhận diện + chiều cao thật** (tường 1,2 m, cửa 2 m, container
  2,6 m), ánh sáng/giờ. Prompt ảnh dùng **chữ** này + thang chiều cao nhân vật (F10) ("bức tường cao ~1,2 m, ngang ngực Kelly") → tỉ lệ đúng mà không
  kéo theo góc máy của ảnh.
- **B2 Ảnh map không bao giờ làm khung nền/ảnh bố cục:** bỏ việc gửi layout ghép hình cắt cho model (layout/storyboard 2D chỉ còn để **người** xem
  kế hoạch); bỏ gửi ảnh map chụp từ trên cao (`camera` = high/top) làm tham chiếu cho shot ngang tầm mắt. Bố cục lấy từ **thông số shot** (cỡ cảnh,
  góc, blocking bằng chữ: "Kelly tiền cảnh trái, Kenta trung cảnh phải") — F9.
- **B3 Chỉ "ảnh nền ngang tầm mắt, không người" mới được làm tham chiếu điểm ảnh**, và chỉ cho shot rộng (WS/EWS/establishing) **cùng góc**; vai trò ghi
  rõ: "kiến trúc & vật liệu của bối cảnh — không điều khiển cỡ người, không điều khiển vị trí nhân vật". Phân loại tự động theo `set_analyses.camera`.
- **B4 Ảnh chi tiết (cắt từ ảnh map):** mốc/vật liệu đặc trưng (ngôi nhà mái đỏ, bức tường, cổng) cắt thành ảnh nhỏ, vai trò "thiết kế của vật X",
  dùng khi shot có vật đó — giữ nhận diện bối cảnh mà không kéo theo bố cục.
- **B5 Nguồn ảnh nền ngang tầm mắt:** (a) lọc trong 331 ảnh map in-game những ảnh `camera=eye/low`; (b) người dùng chụp thêm in-game ở góc TPS/ngang
  tầm mắt cho các bối cảnh hay dùng; (c) (tùy chọn, tốn ảnh, xin phép) gen "plate" trống ngang tầm mắt cho bối cảnh rồi **duyệt** mới vào kho —
  không dùng khi chưa duyệt.
- **B6 QC `set_match` so với hồ sơ bối cảnh + ảnh nền đã duyệt**, không so với layout (sửa L2).

#### Dùng bản đồ 3D có tốt hơn không? (câu hỏi của người dùng — đã có nghiên cứu nền ở `docs/RESEARCH_3D_PREVIZ.md`, "Hướng 3")
**Tốt hơn ở đúng chỗ ảnh map hỏng:** trong 3D, camera đặt được **ở bất kỳ góc/độ cao nào** (ngang tầm mắt, ngược góc, từ trên), tỉ lệ là **mét thật**
(nhân vật 1,75 m cạnh tường 1,2 m tự đúng), vị trí nhân vật giữ nguyên giữa các shot, và render được video blockout cho Seedance 2.5 (`reference_video`).
Cách dùng hợp lý nhất cho pipeline này:
1. **Nguồn nền ngang tầm mắt cho mọi góc (thay B5):** render bối cảnh **trống người** từ đúng camera của shot → làm ảnh nền tham chiếu (vai trò: kiến
   trúc/vật liệu), nhân vật vẫn vẽ bằng ảnh tài nguyên + chữ. Không còn phải tìm ảnh map cùng góc.
2. **Ảnh độ sâu/khối xám + vị trí nhân vật** làm chỉ dẫn bố cục — **chỉ khi thử thật cho thấy Deepix bám theo** (API Deepix không có tham số khóa bố cục
   kiểu ControlNet/mask/strength — rủi ro lớn nhất, giống vấn đề layout ghép hiện nay).
3. **Video blockout** (chuyển động camera + khối người) làm `reference_video` cho Seedance 2.5 ở cảnh hành động phức tạp.
**Tốc độ (ƯỚC TÍNH, chưa đo — máy cloud không tải được map/Blender, phải thử trên máy người dùng):**
| Việc | Thời gian ước tính | Ghi chú |
|---|---|---|
| Dựng 1 map lần đầu (nhập GLB, kiểm đơn vị bằng vật mốc, đặt tên khu vực) | 1–3 giờ công người, **một lần/map** | tự động được phần lớn bằng script Blender |
| Mở map trong Blender chạy nền | ~5–30 s/lần chạy | map ~23k–362k tam giác |
| Đặt nhân vật + camera theo blocking | < 1 s/shot | code, không AI |
| Render ảnh nền/độ sâu 1280×720 | ~0,2–3 s/shot (Workbench/Eevee, có GPU) | 26 shot ≈ 1–2 phút; Cycles chậm hơn nhiều, không cần |
| Render video blockout 4–8 s | ~0,5–5 phút/clip (khối xám, độ phân giải thấp) | chỉ cho cảnh phức tạp |
So với thời gian sẵn có của pipeline (Deepix ~40 s/ảnh, video vài phút/clip, Claude hàng chục giây/lượt), phần 3D **thêm rất ít thời gian chạy** — **với
điều kiện map đã được làm nhẹ**. Các số trên là cho map vài trăm nghìn tam giác.
**Map FF 3D thường rất nặng (người dùng lưu ý)** — hàng triệu tam giác, texture vài GB: mở cả map có thể mất vài phút và cần 16–32 GB RAM/VRAM lớn, không
hợp để mở mỗi lần gen. Cách xử lý (đều làm **một lần/map**, sau đó pipeline không đụng tới file nặng nữa):
1. **Cắt theo khu vực:** script Blender chạy nền cắt map thành từng khu (theo collection/bounding box) → mỗi khu một file GLB nhỏ; pipeline chỉ mở khu cần dùng.
2. **Giảm lưới + nén texture:** decimate còn ~10–20% tam giác, texture 1K–2K — ảnh nền chỉ là tham chiếu kiến trúc/vật liệu, không cần độ chi tiết gốc.
3. **Kho "nền đã render" (quan trọng nhất):** render sẵn các góc máy chuẩn cho mỗi khu (ngang tầm mắt 4 hướng, góc cao, góc thấp, vài cỡ cảnh) → lưu vào
   kho tài nguyên như ảnh "nền ngang tầm mắt / nền góc cao" của bối cảnh đó (G1). Dự án sau **chỉ dùng ảnh**, không mở 3D; chỉ khi cần một góc chưa có
   mới mở file khu (vài giây–vài chục giây).
4. **Tiến trình Blender giữ sẵn** (chạy nền, map khu đã mở) khi cần render nhiều shot liền, tránh mở lại file mỗi shot.
Ước tính xử lý một lần/map nặng: cắt + giảm lưới + render bộ nền chuẩn ~30–90 phút máy chạy (không cần người ngồi xem) — **phải đo thật trên file của
người dùng** (cần biết dung lượng file, số tam giác, cấu hình máy).
**Phương án nhẹ hơn không cần 3D:** chụp ảnh in-game ngang tầm mắt (camera TPS) cho các bối cảnh hay dùng (B5b) — vài phút/bối cảnh, không cần xử lý map;
hoặc "Bàn đạo diễn" ClipAI dựng khối từ ảnh (Hướng 2, chưa có API). Chi phí thật của hướng 3D là **công chuẩn bị map một lần** và **nguồn map**.
**Rủi ro/điều kiện:** (a) map fan trên mạng dùng thử nội bộ được, video phát hành cần asset chính thức từ team game; (b) Deepix có bám ảnh 3D không — chưa
biết; (c) model 3D nhân vật FF + rig (hoặc ma-nơ-canh xám); (d) chạy trên máy người dùng (Blender headless).
**Thử nghiệm đầu tiên bằng file có sẵn: tháp đồng hồ — Đảo Quân Sự (người dùng có file)**
- **Bầu trời (file 3D không có trời) — 3 cách, chọn theo look:**
  | Cách | Làm gì | Ưu | Nhược | Hợp với |
  |---|---|---|---|---|
  | A. **Sky Texture của Blender** (trời vật lý, không cần tải) | đặt độ cao + hướng mặt trời theo giờ của cảnh | nhẹ, tái tạo được, ánh sáng + bóng đổ khớp mặt trời, không lo bản quyền | không mây (thêm mây bằng lớp riêng) | mặc định, cảnh ban ngày |
  | B. **HDRI** (ảnh 360° chiếu sáng + làm nền trời) | World shader dùng file .hdr/.exr, xoay cho khớp hướng nắng | có mây, ánh sáng tự nhiên, nhiều giờ/thời tiết | phải chọn nguồn miễn phí bản quyền (Poly Haven CC0), 2K–4K là đủ (8K nặng), trời không giống trời in-game FF | cảnh cần mây/hoàng hôn/u ám |
  | C. **Render nền trời trong suốt** (alpha) rồi ghép trời | ánh sáng vẫn từ A hoặc B; phần trời để trống rồi ghép **ảnh trời chụp in-game FF** (từ kho) bằng code, hoặc để Deepix tự vẽ theo World Bible | trời đúng kiểu FF (look in-game), một trời dùng chung cả cảnh → nhất quán | thêm 1 bước ghép (nhanh, không AI) | **look in-game**: ghép trời in-game; **look anime**: để Deepix vẽ trời |
  Đề xuất: **A (hoặc B) cho ánh sáng + C cho nền trời**; mỗi cảnh cố định một "giờ + hướng nắng + trời" lưu trong hồ sơ bối cảnh/World Bible để mọi shot khớp.
- **Rìa model (ngoài tháp là khoảng trống):** thêm mặt đất lớn cùng vật liệu, sương/mist nhẹ che chân trời, và giới hạn góc máy không nhìn ra ngoài vùng có model.
- **Tỉ lệ:** kiểm đơn vị bằng chiều cao thật (cửa ~2 m hoặc chiều cao tháp nếu biết) trước khi đặt người 1,75 m.
- **Kịch bản thử (3 shot):** (1) toàn cảnh ngang tầm mắt nhìn về tháp, (2) góc thấp nhân vật dưới chân tháp, (3) góc cao — mỗi shot render: nền trống người
  (RGB + alpha trời) + ảnh độ sâu → thử 3 cách trời A/B/C × 2 look → Deepix ~5–6 ảnh (xin phép) → so với cách B1–B3 (không 3D).
- **Công cụ sẽ viết (chạy trên máy người dùng):** `tools/render_plates.py` — script Blender chạy nền: nhập file, chuẩn hóa tỉ lệ, đặt trời theo A/B/C, các
  camera chuẩn, render nền + độ sâu + alpha, lưu vào kho tài nguyên dưới dạng ảnh **chờ duyệt** của bối cảnh "Tháp đồng hồ — Đảo Quân Sự" (G2). Có thể
  thử trước phần script trên máy cloud với cảnh giả (gói `bpy`) để không mất công của người dùng.
- **Người dùng cần gửi/cho biết:** định dạng file (GLB/FBX/OBJ/.blend), dung lượng, có texture không, chiều cao thật của tháp (nếu biết), vài ảnh chụp
  trời in-game Đảo Quân Sự (cho cách C), cấu hình máy; file để trong `data/3d/` (không lên GitHub).

**Build sẵn tính năng 3D để phiên chạy trên máy người dùng test được ngay (người dùng yêu cầu 2026-09-24)**
Thông tin máy: file 3D ở `D:\AI-Video-Pipeline\model 3D` (có tháp đồng hồ Đảo Quân Sự), **Blender 5.0.1** đã cài. Phiên cloud này không chạy được file/Blender
đó, nên làm sẵn code + hướng dẫn + test giả lập; phiên trên máy chỉ việc chạy và chỉnh.
- **`tools/render_plates.py`** — script chạy **trong Blender** (`blender -b -P tools/render_plates.py -- --config plan.json`): nhập GLB/glTF/FBX/OBJ/.blend; kiểm tỉ lệ
  (kích thước khung bao + chiều cao thật nếu có); thêm mặt đất + sương che rìa model; **trời** A (Sky Texture — dò tên node/kiểu trời của Blender 5.x, lỗi thì
  rơi về nền trời gradient), B (HDRI từ đường dẫn), C (nền trong suốt); đặt camera theo **preset** (ngang tầm mắt 4 hướng quanh điểm mốc, góc thấp, góc cao) hoặc
  theo JSON (vị trí, hướng nhìn, tiêu cự, độ cao); render RGB + alpha + độ sâu bằng EEVEE/Workbench (dò tên engine theo phiên bản); ghi `manifest.json` (camera,
  góc, độ cao, tiêu cự, giờ/nắng, thời gian render từng ảnh).
- **`core/plates3d.py`** — phía Dashboard: tìm Blender (`BLENDER_PATH`, mặc định `C:\Program Files\Blender Foundation\Blender 5.0\blender.exe`), liệt kê file trong
  `MODEL3D_DIR` (mặc định `D:\AI-Video-Pipeline\model 3D`), dựng file cấu hình, chạy Blender nền (subprocess, có timeout, log), ghép trời in-game cho cách C
  (Pillow, không AI), **nhập ảnh vào Kho tài nguyên** thành ảnh "nền ngang tầm mắt/góc cao" của bối cảnh ở trạng thái **chờ duyệt** (G2) kèm thông số camera
  → `set_analyses` điền sẵn từ manifest (không cần Claude đọc ảnh).
- **Dashboard (⚙ Kho tài nguyên → "🏗 Bối cảnh 3D")**: chọn file 3D, chọn trời (A/B/C) + giờ/hướng nắng, chọn preset camera, "Render nền" (không tốn credit), xem
  trước, duyệt vào kho. Dùng tiếp như ảnh nền đã duyệt (B3).
- **`docs/HUONG_DAN_3D.md`** — hướng dẫn cho phiên trên máy: cấu hình env, lệnh chạy thử trực tiếp bằng Blender, quy trình test tháp đồng hồ (3 shot × trời
  A/B/C × 2 look, những gì cần ghi lại: thời gian mở file/render, dung lượng, số tam giác, ảnh chụp kết quả), bước Deepix cần xin phép, cách ghi kết quả vào
  `docs/RESEARCH_3D_PREVIZ.md`.
- **Kiểm trên cloud:** test `core/plates3d.py` với Blender giả (không cần Blender thật); nếu cài được gói `bpy` trên cloud thì chạy thử `render_plates.py` với
  cảnh khối hộp tự dựng. **Khác phiên bản** (bpy trên cloud ≠ Blender 5.0.1) → script chỉ dùng API ổn định + dò tên node/engine; phiên trên máy là nơi xác nhận cuối.
- Giới hạn: không đoán được dung lượng/tam giác file tháp; script in các số này ở lần chạy đầu để quyết định có cần cắt/giảm lưới (đã có sẵn tùy chọn decimate).

**Đề xuất:** không thay B1–B6 (rẻ, làm ngay); chạy **thí nghiệm nhỏ đã thiết kế sẵn** trong GĐ-I (1 khu map, 2 nhân vật, 3 shot: toàn cảnh góc cao / trung cảnh
ngang mắt / ngược góc; ~5 ảnh Deepix): so (i) nền render 3D trống người + chữ, (ii) ảnh độ sâu/khối xám, với (iii) cách B1–B3. Đạt → 3D thành nguồn nền
chuẩn cho các bối cảnh hay dùng (lưu plate vào kho như biến thể "nền ngang tầm mắt"); không đạt → giữ B1–B6. Người dùng cần: tải 1 map GLB/FBX có
texture (gợi ý trong RESEARCH_3D_PREVIZ.md), cài Blender, cho biết có model 3D nhân vật FF không, **và cho biết dung lượng / số tam giác của file map +
cấu hình máy (RAM, GPU)** để chọn mức cắt/giảm lưới. Thí nghiệm dùng **một khu nhỏ đã cắt**, không mở cả map.

### Kho tài nguyên gọn gàng — cấu trúc mới (G1–G6)
**Hiện trạng lẫn lộn:** một tài nguyên chứa trộn ảnh toàn thân, nửa người, bảng thiết kế, skin cũ/mới đã gộp ("Kelly new → KELLY"); ảnh bối cảnh
nhiều góc chung một mục; ảnh tải riêng cho dự án nằm cùng bảng với kho chung (`assets.project_id`); tối đa 6 ảnh/mục; không có trạng thái "đã
duyệt"; mới nhập là dùng ngay.
- **G1 Phân cấp cố định:** game → loại (nhân vật · thú cưng · vũ khí · xe · đạo cụ · bối cảnh · phong cách) → **tài nguyên = đúng 1 thực thể** →
  **biến thể** (skin/trang phục/look: mặc định, skin X, anime) → ảnh có **vai trò** (nhân vật: toàn thân / nửa người / cận mặt / sau lưng / nghiêng /
  tư thế kỹ năng / bảng thiết kế; bối cảnh: nền ngang tầm mắt / nền góc cao / toàn cảnh từ trên (chỉ thông tin) / chi tiết).
- **G2 Hộp chờ phân loại:** ảnh mới nhập (đồng bộ thư mục, tải lên) vào trạng thái **chờ** → Claude đề xuất vai trò/biến thể/góc máy chạy nền (tái dùng
  `asset_vision`, `set_analyses`) → người duyệt → **chỉ ảnh đã duyệt được pipeline dùng**.
- **G3 Tách kho chung và tài nguyên riêng của dự án:** tải lên cho dự án ở trong phạm vi dự án; muốn dùng chung phải "đưa vào kho" có duyệt.
- **G4 Skin/trang phục là biến thể của cùng nhân vật** (không tách thành nhân vật khác, không gộp lẫn vào ảnh gốc); ảnh chuẩn anime (T6) là biến thể
  `look=anime`.
- **G5 Quy tắc nhập:** chống trùng theo sha (đã có), tên chuẩn + bí danh (từ ff.garena.com đã có), bảng thiết kế nhận diện tự động, bỏ giới hạn 6
  ảnh/mục nhưng giới hạn theo vai trò.
- **G6 Bảng sức khỏe kho** (= T10): thiếu vai trò ảnh nào, còn bao nhiêu ảnh chờ duyệt, bối cảnh nào chưa có nền ngang tầm mắt.

### Chính sách lấy tài nguyên của Dashboard (R-pick)
Thay các chỗ lấy rải rác (`best_reference` cho Director, `scene_references` cho ảnh/video, `reference_paths`, `outfit_images`, layout, ảnh shot trước)
bằng **một hàm chọn theo mục đích** (ví dụ `assets.pick_references(purpose, project, shot)`) với bảng luật rõ ràng, cùng một bộ ảnh cho mọi bước:
| Mục đích | Nhân vật | Bối cảnh | Khác |
|---|---|---|---|
| Director / Bible | hồ sơ chuẩn (chữ) + 1 ảnh cận mặt/nửa người rõ nhất | hồ sơ bối cảnh (chữ), không ảnh map | — |
| Ảnh khung đầu (Deepix) | ≤ 2 ảnh/người theo cỡ cảnh & hướng (T3), đúng biến thể + look | chỉ nền ngang tầm mắt đã duyệt, chỉ shot rộng cùng góc (B3); còn lại chữ (B1) + ảnh chi tiết (B4) | ảnh shot trước chỉ khi cùng cỡ/góc (F8); **không** layout ghép |
| Ảnh khung cuối (K1) | như trên + ảnh khung đầu | như trên | — |
| QC ảnh / QC đồng bộ | đúng bộ ảnh đã dùng để gen + hồ sơ chuẩn | hồ sơ bối cảnh + nền đã dùng | — |
| Video (Seedance chế độ tham chiếu K4) | 1 ảnh rõ nhất/người, vai trò danh tính | 1 nền ngang tầm mắt nếu có | — |
Mỗi lần chọn: **ghi vào job** (K7), **hiện trong storyboard** ("tham chiếu đã dùng"), thiếu thì **báo** (không bỏ âm thầm); không bao giờ vượt giới
hạn ảnh của model mà cắt lặng lẽ.

### P1 · Kịch bản → Director → Character Bible (❌)
- **Tốt:** tách cảnh/shot, JSON có kiểm, khóa trường sửa tay (chế độ cảnh), cổng duyệt Bible.
- **Yếu (gây lỗi GĐ6 nhiều nhất — R1):** Director không thấy ảnh mà không báo (A1); Lock chỉ điền khi rỗng, không sinh lại khi ảnh/Bible
  đổi (A2); nhân bản chép Lock cũ (A3); câu trả lời Director đã trả tiền bị vứt vì kiểm "thiếu shot" chạy sau (A8) và lưu nửa chừng (A9);
  chạy lại Director xóa sửa tay ở chế độ shot và mô tả nhân vật (A10, A11); Director không được xem Bible hiện tại → nhân vật trùng (A12);
  ảnh Director thấy ≠ ảnh Lock/gen dùng (A13); shot rỗng kế thừa cả dàn nhân vật (A16); parser nhận nhầm tiêu đề, mất dòng .docx (A20).
- **Tối ưu:** Director bắt buộc thấy ảnh; F1 kiểm Bible↔ảnh; Lock sinh lại theo nguồn; bảo vệ sửa tay mọi chế độ; lưu giao dịch (rollback).

### P1b · Previz / layout / storyboard 2D (❌)
- **Yếu:** layout không theo cỡ cảnh, ảnh nền chụp từ trên cao, hình cắt tí hon → làm ảnh tham chiếu số 1 cho Deepix và điều khiển luôn
  cỡ cảnh/tỉ lệ (R7, L1); QC `set_match` so với chính layout sai (L2); storyboard ghi đè sửa tay đang có (L3); nhân bản chép layout mà
  không có file (L4); chỉ 10 ảnh nền.
- **Tối ưu (đã đổi theo ý người dùng):** layout/storyboard 2D chỉ để người xem kế hoạch, **không gửi cho model**; bối cảnh vào prompt bằng hồ sơ chữ
  + mốc có chiều cao thật; chỉ nền ngang tầm mắt đã duyệt làm tham chiếu cho shot rộng cùng góc (B1–B6).

### P2 · Ảnh khung đầu + QC ảnh + QC đồng bộ + storyboard (⚠ → cải thiện nhờ W1)
- **Tốt:** image-to-image với ảnh tài nguyên, QC Claude 8 tiêu chí, mức sàn nhân vật/tay/chân, pilot, **cổng storyboard (mới)**.
- **Yếu:** prompt ảnh dùng ký hiệu "MCU" (I1, F9) → shot cận ra toàn thân; nối ảnh shot trước bất kể cỡ/góc (I2, F8); câu sửa gen lại
  kèm điểm số + tiếng Việt vào prompt Deepix, chỉ giữ lần sửa gần nhất (I3, V3); QC đồng bộ chọn chuẩn theo số đông, sửa sai
  (Kenta→Maxim), tự gen lại (I4, R3); `composition/set_match/scale` không có sàn (I5); 15 ảnh V1 dưới sàn nhân vật vẫn được duyệt (I6);
  điểm trung bình, ngưỡng chưa hiệu chỉnh (I7); dấu "⚠ cũ" bỏ sót World Bible/trường look (I8).
- **Tối ưu:** câu khung cắt rõ; tách "ghi chú cho người" khỏi "câu sửa cho model"; QC đồng bộ so ảnh tài nguyên, chỉ báo; sàn cho bố cục/tỉ lệ; đo đồng thuận người–QC.

### P3 · Motion prompt (⚠)
- **Tốt:** kiến thức 7 đoạn, lint, lineage, cổng thoại.
- **Yếu:** gửi tối đa 12 ảnh full-res, ảnh thứ 13+ bị cắt âm thầm, ảnh nhóm multi-shot lặp (M20); Claude được báo sai model/giới hạn
  (M9: 30s thay vì Kling 512 ký tự/15s); `fit_durations` chỉ sửa `motion_prompts.duration_sec` → multi-shot bỏ qua, lưu sửa ghi đè,
  clip bị đánh cũ → trả tiền lại (M4); lưu sửa làm job video đang chờ fail (M5); nút "Duyệt" bỏ nội dung đang gõ (M6); cổng thoại chỉ
  cảnh báo mỗi nhịp khi tắt tiếng (W16).
- **Tối ưu:** thông số model đúng cho Claude; một nguồn thời lượng; nút duyệt lưu nội dung đang gõ.

### P4 · Video + QC video (❌)
- **Tốt:** chọn model theo cảnh, multi-shot Kling, khung đầu+cuối Seedance, giữ clip QC đã loại, W12.
- **Yếu:** gen lại cùng đầu vào (V2, M-regen); nhóm multi-shot thiếu nhân vật (R4, F4); shot sau trong nhóm không gen lại được —
  luôn "missing inputs" (M1); autopilot tự duyệt clip QC còn lỗi (M2); dashboard + autopilot cùng poll 1 job (M3); override model
  trước luật multi-shot → nhóm lẫn model (M9); chia nhóm tính lại lúc tải (M10); Seedance bỏ mọi ảnh tham chiếu khi có khung đầu nhưng
  UI vẫn cho gắn (M7); chặn bản quyền → chuyển Kling nhưng kẹt không ai thử lại (M14); QC video 6 khung, bỏ 2 đầu, không mốc thời gian,
  follower so với ảnh leader, không kiểm tiếng (M12); clip QC lỗi mãi → hỏi Claude mỗi tick (M13); làm tròn 4,5→4 (M11); dấu vân tay
  thiếu model/audio (M16); hủy task ngoài 3 trang không hủy thật (M17); ước tính giá thiếu nhiều khoản (M8).
- **Tối ưu:** F5 chẩn đoán trước khi gen lại; gen lại tối đa 2 lần và phải đổi đầu vào; W11 look in-game → Kling; W10 luật từng model trước khi gửi.

#### P4c · Ảnh đầu vào: 1 khung cảnh "sạch" + prompt, hay ảnh dạng storyboard (có ô, chữ mô tả cảnh/nhân vật ngay trong ảnh)? (câu hỏi người dùng)
**Cách model video dùng ảnh đầu vào:**
- Ở vai trò **khung đầu** (`first_frame`, cách pipeline đang dùng), model coi ảnh là **khung hình số 1 của clip** và làm nó chuyển động. Ảnh storyboard (nhiều
  ô, viền, mũi tên, chữ) sẽ bị giữ nguyên thành hình đầu clip — video mở ra bằng một tấm lưới có chữ, rồi model cố "động hóa" tấm lưới → **sai ngay từ khung đầu**.
- Ở vai trò **ảnh tham chiếu** (Seedance `reference_image`, Kling elements), model **chép điểm ảnh** chứ không "đọc" ghi chú: chữ trong ảnh hay bị vẽ lại thành
  chữ méo trong video; nhiều ô/nhiều người trên một tấm làm lẫn mặt/trang phục giữa các nhân vật — chính lý do code đã loại bảng thiết kế nhân vật khỏi tham
  chiếu (`assets.is_composite_sheet`) và Seedance Director 1.0.2 ghi "tránh ảnh ghép, contact sheet" cho ảnh danh tính. Ghi chú bằng chữ trong ảnh không thay được
  prompt: model đọc chữ trong ảnh kém hơn nhiều so với đọc prompt.
- Web ClipAI/Deepix có quảng bá "storyboard → video", nhưng **hợp đồng API đang dùng không có** tính năng này (Deepix Storyboard là web-only); nếu ClipAI mở API
  thì mới đánh giá.
**Kết luận — cách cho đầu ra tốt hơn:**
1. **Khung đầu = một khung cảnh sạch** (không chữ, không viền, không ô), đúng cỡ cảnh/góc của shot — như hiện tại, cộng khung cuối cho shot có `end_state` (K1).
2. **Thông tin cảnh/nhân vật đi bằng prompt có cấu trúc** (Seedance Director: REFERENCE ASSETS · CHARACTERS · BLOCKING · TIMELINE…), mỗi nhân vật gắn nhãn,
   **danh tính đi bằng ảnh tham chiếu sạch từng người** (1 người/ảnh, vai trò rõ) — không đốt chữ vào ảnh.
3. **Ảnh storyboard nhiều ô dùng cho người và cho Claude**: người duyệt ở cổng storyboard, Claude kiểm liên tục/đồng bộ (tấm ghép đã có ở QC đồng bộ) — không gửi cho model video.
4. Muốn "một ảnh chứa nhiều thông tin" cho model: dùng **khung đầu + khung cuối** (2 ảnh sạch) thay vì 1 ảnh nhiều ô.
**Thử để có số liệu (GĐ-I, ~$2–4):** cùng 1 shot/nhóm: (a) khung đầu sạch + prompt (hiện tại), (b) khung đầu + khung cuối, (c) Seedance chế độ tham chiếu (ảnh sạch
từng người), (d) ảnh storyboard nhiều ô làm tham chiếu (không làm khung đầu) — so nhân vật, `motion_match`, chữ lạ trong video.

### P8b · Tối giản giao diện (yêu cầu người dùng: đã dùng Claude API thì dashboard nên gọn, ít nút, ít trường, ít thanh)
**Hiện trạng đo được:** ~200 nút, ~60 khung mở rộng, ~90 ô chọn/checkbox (Bước 1: 51 nút, 15 khung, 27 ô chọn; Bước 2: 31 nút; Bước 5: 27 nút, 21 ô chọn;
đầu trang: 22 nút + 46 dialog/popover; Cài đặt: 37 nút, 22 khung). Mỗi bước vừa có luồng tay vừa có luồng tự động, cảnh báo rải khắp nơi, nhiều nút trùng
(2 nút "Kiểm tra + tải về", nhiều nút gen lại).
**Nguyên tắc:** với Claude API + chế độ tự động + 2 cổng duyệt, người dùng chỉ cần làm **4 việc**: đưa kịch bản & chọn look → duyệt nhân vật → duyệt storyboard
→ nhận video (sửa nhẹ nếu cần). Mọi thứ khác là **nâng cao**.
**Thiết kế đề xuất:**
- **Màn chính 1 cột, 4 thẻ theo tiến trình:** ① Kịch bản (tải file, chọn look Anime / In-game FF, định dạng khung, ước tính tiền + thời gian, nút "Chạy") ·
  ② Nhân vật (chỉ hiện khi dừng ở cổng Bible: mỗi nhân vật 1 hàng — ảnh kho | mô tả | cờ lệch, nút Duyệt tất cả) · ③ Storyboard (khi dừng ở cổng: lưới ảnh +
  cờ ⚑, mỗi ảnh 1 menu "gen lại / sửa mô tả", nút Duyệt) · ④ Kết quả (video, tải về, 3 tùy chọn xuất). Một thanh tiến độ duy nhất + trạng thái 1 dòng.
- **Chế độ chuyên gia** (công tắc ở Cài đặt, mặc định tắt): 5 bước tay như hiện nay cho người cần can thiệp sâu.
- **Gom cảnh báo** thành một "hộp thông báo" (từ `diag`) thay cho cảnh báo rải trong từng bước; chỉ hiện việc **cần người làm**.
- **Mặc định thông minh thay cho ô chọn:** QC, model theo cảnh, nhạc/SFX, phụ đề… tự quyết theo gói look; chỉnh ở chế độ chuyên gia.
- **Đầu trang:** dự án · tiền đã dùng/trần · ⚙ (Kho tài nguyên, Bảng giá, Người dùng) — bỏ bớt dialog lồng nhau; tab hiệu suất chuyển vào ⚙.
- **Mỗi nút tốn tiền hiện giá ngay trên nút** (M8), không cần khung ước tính riêng.
- Dọn trùng/chết: 2 nút "Kiểm tra + tải về", `resize_panel` chết, preset 1558×720, chữ "Cần ANTHROPIC_API_KEY", nút Claude CLI khi đã dùng API (E2).
- Kiểm màn hẹp + test giao diện (AppTest) cho luồng 4 thẻ.

### P5a · Giọng tiếng Việt — người dùng: "chưa có file âm thanh tiếng Việt nào trọn vẹn, voice của các nhân vật trong clip test đều lỗi" (❌)
**Đường đi hiện tại:** lời thoại lấy từ kịch bản → `core/voice.py` gửi TTS ElevenLabs qua ClipAI (`clipai_audio.generate_tts`) với giọng trong `voice_profile`
của nhân vật (theo dự án) → đo độ dài thật → kéo dài clip (`fit_durations`) → đặt lên timeline (`place_on_timeline`) → phụ đề lấy thời gian từ đây. Chữ gửi
đi qua `speakable()` thay từ tiếng Anh bằng cách đọc phiên âm (`data/pronunciation_vi.json`). Model video tự nói (Kling `sound`, Seedance `generate_audio`)
là tùy chọn, mặc định tắt.
**Nguyên nhân khả dĩ (từ code — cần xác minh bằng nghe thử):**
- AU1 **Model TTS mặc định có thể không hỗ trợ tiếng Việt:** `voice.DEFAULT_MODEL = "eleven_multilingual_v2"` dùng cho mọi câu thoại và câu nghe thử
  (`voice.py:16,124,151`). Theo hiểu biết của tôi, danh sách ngôn ngữ của Multilingual v2 **không có tiếng Việt**; tiếng Việt có ở `eleven_v3` và dòng
  Turbo/Flash v2.5. Code còn ghi "gửi `language_code` cho tiếng Việt thì ElevenLabs trả HTTP 400" (`audio_lib.py:81`) — khớp với việc model không nhận
  "vi". → model tự đoán ngôn ngữ, câu ngắn lẫn tên/từ tiếng Anh dễ bị đọc giọng nước ngoài, sai thanh điệu. **Phải xác minh** với tài liệu ElevenLabs/ClipAI
  và nghe A/B (mục D trong TODO "so eleven_v3 vs multilingual_v2" vẫn chưa làm).
- AU2 **Giọng không phải người Việt:** kho chỉ có ~5 giọng ghi `vi` (1 giọng nữ); `casting_pool` hết giọng Việt thì **lấy mọi giọng** (`voice.py:91-94`)
  → nhân vật nữ thứ hai (Kelly…) có thể nhận giọng nước ngoài đọc tiếng Việt.
- AU3 **Phiên âm tự chế làm hỏng câu:** "rank"→"răng", "skill"→"xờ-kiu", "Kelly"→"Ke-li", gạch nối giữa âm tiết → ngữ điệu gãy, có từ sai nghĩa; model đời
  mới đọc tên tiếng Anh tốt hơn khi để nguyên.
- AU4 **Câu bị cắt/không trọn:** khớp độ dài chỉ sửa `motion_prompts.duration_sec`, multi-shot bỏ qua và lưu sửa ghi đè (M4); tắt tiếng video thì cổng
  thoại chỉ cảnh báo, không kéo dài clip (D9: "S23 cần ~3,1s, clip 3s" lặp 1.092 lần); thoại của clip bị bỏ tick vẫn phát, phụ đề lệch (D1, D2).
- AU5 **Trộn tiếng:** nếu bật tiếng model video (Kling/Seedance nói tiếng Việt kém) mà vẫn giữ tiếng clip khi render → 2 giọng chồng nhau; một clip không
  có tiếng làm mất tiếng mọi clip (D4).
- AU6 **Không có kiểm tra âm thanh nào:** QC video không nghe tiếng (M12); không ai kiểm TTS đọc đủ chữ, đúng chữ, không bị cắt.
- AU7 **Không khớp môi:** lip-sync chỉ có trên web ClipAI (không API) → miệng nhân vật trong clip không khớp lời → cảm giác "lỗi" dù giọng đúng.
- AU8 Hồ sơ giọng theo dự án (không theo kho) → mỗi dự án chọn lại, nhân vật đổi giọng giữa các video.

**Giải pháp:**
- **AU-a Chọn đúng model + khóa tiếng Việt:** xác minh danh sách ngôn ngữ; chuyển mặc định sang model có tiếng Việt (dự kiến `eleven_v3`, dự phòng
  Turbo/Flash v2.5), gửi `language_code="vi"` khi model hỗ trợ; bỏ lựa chọn model không hỗ trợ tiếng Việt khỏi Bước 1.
- **AU-b Giọng:** chỉ giọng Việt cho thoại tiếng Việt, báo rõ khi thiếu (không lặng lẽ lấy giọng ngoại); tìm thêm giọng Việt (thư viện giọng ClipAI /
  giọng cá nhân nếu ClipAI cho); **giọng chuẩn mỗi nhân vật lưu ở kho** (T1) để mọi video cùng giọng.
- **AU-c Phát âm:** rà lại từ điển (bỏ phiên âm sai/gạch nối), mặc định để model đọc tên riêng tiếng Anh; chỉ phiên âm từ đã nghe thử là sai.
- **AU-d Trọn câu:** một nguồn thời lượng (M4), clip luôn kéo dài theo giọng thật kể cả khi tắt tiếng video và ở multi-shot (W16), thoại quá dài → tách shot,
  không bao giờ cắt câu; D1/D2 một timeline chung.
- **AU-e Mix sạch:** thoại tiếng Việt chỉ lấy từ TTS; tắt/loại tiếng nói của model video khi có TTS (giữ tiếng môi trường nếu cần); D4 báo và giữ tiếng.
- **AU-f Kiểm âm thanh tự động:** chuyển giọng → chữ (ASR) để so với câu gốc (đủ chữ, đúng chữ, không cắt), đo độ dài, phát hiện im lặng/cắt cụt; câu
  lỗi tự tạo lại (TTS rẻ). ASR chạy máy người dùng (miễn phí) hoặc dịch vụ có sẵn — chọn khi làm.
- **AU-g Khớp môi (không có API):** shot có thoại tránh cận miệng khi không cần (góc xa, quay nghiêng/sau lưng, chèn phản ứng) — Director được báo luật
  này; thử **audio tham chiếu Seedance** (`reference_audio`: nhân vật nói theo giọng TTS có sẵn) cho shot cận nói.
- **AU-h Bộ thử giọng chuẩn:** 10 câu mẫu (tên nhân vật, từ game, câu cảm xúc) × 2–3 model × giọng Việt → người nghe chấm → chốt cấu hình, lưu vào gói look/giọng.

### P5 · Giọng, nhạc, SFX, phụ đề, xuất bản (⚠)
- **Tốt:** TTS tiếng Việt, kho nhạc, card cuối, xuất theo kích thước, chuỗi bản giao có dấu "cũ".
- **Yếu:** thoại của clip bị bỏ tick vẫn phát (D1); phụ đề lệch với bản render (D2); upload clip tay ghi đè clip đã trả tiền + path
  traversal (D3); 1 clip không tiếng → mất tiếng mọi clip, autopilot không báo (D4); "không dùng nhạc" không được nhớ → autopilot tự gen
  nhạc trả tiền (D5); render lỗi để lại file hỏng mà vẫn "mới" (D6); đổi phụ đề/card/xuất bản không đánh dấu cũ (D7); dịch phụ đề lại bằng
  Claude mỗi lần, bỏ bản sửa tay (D8); SFX chọn theo tên file, không chạy ở autopilot; 2 nút "Kiểm tra + tải về".
- **Tối ưu:** một nguồn timeline (clip đã chọn + giây đã sửa) cho giọng/phụ đề/render; ghi nhớ lựa chọn nhạc; render ghi file tạm rồi đổi tên.

### P6 · Autopilot / điều phối (⚠)
- **Tốt:** tick idempotent, hàng đợi dự án, dừng khi Claude hết hạn mức, cổng Bible/pilot/**storyboard**, W12.
- **Yếu:** tự duyệt mọi `pending_review` ảnh/clip kể cả dưới sàn (O1/W15); QC đồng bộ tự gen lại (O2); clip cũ tự gen lại ngoài max_retry
  (O3/V5); trần theo số job chung, không theo tiền/shot (O4/V6); thử lại mọi lỗi không tạm thời (O5/W9); cổng Bible không đòi ảnh mốc/Lock
  (O6); **W12 hở: provider tạo mới mỗi lần poll ở chế độ tay → đếm "không thấy" bị reset; sau khởi động lại task thật ngoài 3 trang có thể
  bị coi là "không tạo" → gửi lại, trả 2 lần** (O7); đổi chế độ shot khi đã có dữ liệu (O8).
- **Tối ưu:** vòng mới 2 điểm người duyệt; trần tiền theo dự án + theo shot; "cùng lỗi 2 lần → dừng shot".

### P7 · Chi phí & sổ chi (❌)
- **Claude:** autoqc/asset_vision/research đi ngoài sổ → cũng không bị trần chặn (C1); không cache (C2); ảnh full-res (C3); không effort
  (C4); không kiểm `stop_reason`, gửi lại toàn bộ (C5); motion gửi dư (C6); usage thiếu project/stage (C7); model không có giá → $0 (C9);
  kiểm trần lỗi thì cho qua, lỗi ghi sổ bị nuốt (C10). **Video:** ghi tiền lúc gửi, không đối chiếu `cost` thật ClipAI (C11); giá ảnh/audio
  null → không vào trần (C12); ước tính thiếu (M8).
- **Tối ưu:** C1–C8 của plan người dùng + đối chiếu `cost` ClipAI + ước tính trước mỗi nút tốn tiền.

### P8 · Khung Dashboard: bảo mật, dữ liệu, hiệu năng, UI (⚠/❌ bảo mật)
- **Bảo mật (High):** "chỉ máy chủ" dựa header Host giả được; `?login=<email>` đăng nhập không mật khẩu; email owner hard-code; bật LAN là
  ai cũng thành Owner (S1).
- **Dữ liệu:** xóa dự án xóa cả thùng rác, sót outputs/diag, xóa project_id ở sổ chi, id tái dùng (S2); xóa nháp nhạc/audio không hỏi (S3);
  2 cửa sổ cùng dự án ghi đè nhau (WORKFLOW_REVIEW B.4).
- **Hiệu năng:** `connect()` chạy lại schema+migration mỗi rerun/poll, không đóng kết nối; mỗi poll tạo Claude client + provider mới (P1);
  Bước 5 tính trạng thái 3 lần, đọc cả file video vào RAM mỗi rerun (P2).
- **Báo cáo:** tab hiệu suất đếm sai với approved/multi-shot (P3); bản chắt lọc kiến thức bị cắt vẫn thay tài liệu gốc (Q2).
- **UI (UI_AUDIT còn mở):** Bước 3 hàng cao, "Duyệt tất cả" xa danh sách; Bước 4 hộp trên cùng chật; chữ lỗi thời "Cần ANTHROPIC_API_KEY";
  preset 1558×720 lạ, `resize_panel` chết; lỗi bị rerun nuốt; chưa kiểm màn hẹp.

### P4b · Đánh giá cách dùng ClipAI — đã dùng đúng tính năng chưa? (câu hỏi bổ sung của người dùng)
**Hiện trạng code (clipai.py:150-270, runner.py:238-260, shots.py:300, model_router.py:70-93):**
| Tính năng ClipAI (theo tài liệu API) | Đang dùng thế nào | Đánh giá |
|---|---|---|
| **Khung đầu** (Kling `image_list type=first_frame`, Seedance `role=first_frame`) | Mọi clip đều gửi đúng 1 ảnh khung đầu đã duyệt | ✅ đúng, là "mỏ neo" chính |
| **Khung cuối** (Seedance `role=last_frame`; Kling O1 5/10s; danh sách task Kling có trường `has_tail`) | Chỉ Seedance, chỉ chế độ từng shot, chỉ shot `continuous_with_next`, và khung cuối = **ảnh đầu của shot kế tiếp** (để nối cắt). Kling không bao giờ gửi khung cuối; V0 (clip 15s) và multi-shot không có | ❌ **Chưa hợp lý.** Director đã viết `end_state` (tư thế/vị trí cuối shot, prompts/17:22) nhưng chỉ thành chữ trong motion prompt — **không có ảnh khung cuối**. Tiêu chí QC video thấp nhất ở mọi phương án là `motion_match` (TB 0,49 ở V0/V2), và lý do loại thường là **kết thúc sai** ("Final image is wrong: at 12–15 s Maxim must stay pressed flat…", V0 S03 tốn $6,60 không dùng được). Chỉ dùng khung đầu = model tự bịa đoạn kết → lệch hành động → gen lại. |
| **Ảnh tham chiếu nhiều** (Seedance `reference_image`, 2.0 ≤ 9, 2.5 ≤ 30) | Tắt (`SEEDANCE_REFS_WITH_FIRST_FRAME=False`, vì API từ chối trộn khung đầu/cuối với ảnh tham chiếu) | ⚠ Đúng về kỹ thuật, nhưng **bộ chọn model vẫn dựa trên tiền đề cũ**: `model_router.py:78,87` đưa cảnh ≥ 3 nhân vật sang Seedance "vì Seedance nhận ảnh tham chiếu riêng từng người" — điều này **không còn đúng** → cảnh đông người sang Seedance mà không có tham chiếu từng người, lại dễ bị chặn "người thật"/bản quyền. UI "🧩 Gắn ảnh chủ thể" vô tác dụng (M7). |
| **Chế độ tham chiếu thay cho khung đầu** (Seedance: không gửi khung đầu, chỉ gửi ảnh tham chiếu từng nhân vật + bối cảnh) | Không có | ⚠ Là lựa chọn đáng thử cho shot đông người/nhân vật hay lệch khi ảnh khung đầu khó vẽ đúng; hiện pipeline luôn ép "khung đầu". |
| **Kho chủ thể Seedance** (`asset_uri`; nhân vật FF có thỏa thuận bản quyền → ít bị chặn) | Code có, **chưa thử thật**, bị hạ ưu tiên | ⚠ GĐ6 bị chặn 2 lần "người thật" + 1 lần bản quyền với Seedance; với look in-game (render 3D giống người) đây có thể là cách chính thức để Seedance nhận nhân vật FF. Cần thử 1 nhân vật. |
| **Kling elements** (`element_ids` giữ nhân vật/đối tượng) | Không dùng | ⚠ Đúng chỗ cần nhất: multi-shot Kling chỉ nhận **1 ảnh đầu cho cả nhóm 15s** → shot sau thiếu nhân vật bịa ra (R4, 6/12 shot sau sai nhân vật). Cần kiểm tài liệu API xem có dùng cùng multi-shot/khung đầu được không. |
| **Multi-shot Kling** (`multi_prompt`, ≤ 512 ký tự/shot) | Đang dùng cho V2 | ⚠ Rẻ (1 lệnh/nhóm) nhưng chỉ 1 mỏ neo hình → chỉ hợp khi mọi shot trong nhóm có cùng nhân vật với ảnh đầu (F4). |
| **Video tham chiếu chuyển động** (`video_list` / `reference_video`) | Code có, chưa thử thật; Seedance có thể từ chối khi đi cùng khung đầu | ⚠ Cần thử; ghi luật vào bảng luật model (W10). |
| **Âm thanh do model tạo / audio tham chiếu** | Tùy chọn / chưa | — ngoài phạm vi chi phí chính |
| **Ghi lại "đã gửi gì"** | `jobs` không lưu có khung cuối/tham chiếu/chế độ nào | ❌ Không kiểm được sau này (không biết GĐ6 V1 có dùng khung cuối không) → cần lưu. |

**Kết luận:** dùng khung đầu là đúng, nhưng **chỉ dùng khung đầu cho shot có trạng thái cuối quan trọng là chưa hợp lý** — đó là một phần
nguyên nhân `motion_match` thấp và gen lại. Ảnh khung cuối gen bằng Deepix rẻ hơn nhiều so với một lần gen lại video. Đồng thời bộ chọn
model đang dựa trên một khả năng đã tắt.

**Giải pháp (K1–K7, đưa vào GĐ-E/F):**
- **K1 Khung cuối là "hạng nhất":** shot có `end_state` rõ (đổi vị trí/tư thế/kết quả hành động, va chạm, ngã, biến đổi) → gen **ảnh khung cuối**
  bằng Deepix (dùng ảnh khung đầu + ảnh tài nguyên làm tham chiếu, prompt = trạng thái cuối, cùng khung/cỡ cảnh) → storyboard hiện **cặp
  đầu–cuối**, QC ảnh chấm cả hai (đúng nhân vật, cùng bối cảnh/ánh sáng) → gửi clip first+last frame. Shot không đổi trạng thái giữ 1 khung đầu.
- **K2 Chọn model theo nhu cầu khung cuối:** shot cần khung cuối → model hỗ trợ khung cuối (Seedance; Kling nếu tài liệu xác nhận `end_frame`/tail
  cho `kling-v3-omni`/O1 — kiểm `clipai-1.3.1/clipai/reference.md`); ghi vào bảng luật W10.
- **K3 Sửa bộ chọn model:** bỏ lý do "Seedance nhận ảnh tham chiếu từng người" khi đang ở chế độ khung đầu; cảnh ≥ 3 người chọn theo khả năng
  thật (khung đầu tốt + khung cuối, hoặc chế độ tham chiếu, hoặc Kling), kết hợp W11 (look in-game → ưu tiên Kling, tránh chặn Seedance).
- **K4 Chế độ tham chiếu Seedance** (không khung đầu, tham chiếu từng nhân vật + bối cảnh với vai trò rõ theo Seedance Director 1.0.2) — thử thật 1 shot đông người, so với khung đầu.
- **K5 Thử Kho chủ thể Seedance** cho 1 nhân vật FF (look in-game): có giảm chặn "người thật"/bản quyền không; và kiểm **Kling elements** cho multi-shot.
- **K6 Clip dài nhiều nhịp (V0):** khung đầu + cuối không cứu được các nhịp giữa → chia shot (F6) thay vì gen lại.
- **K7 Ghi "đã gửi gì"** vào job (có khung cuối, số ảnh tham chiếu, chế độ, model, độ dài gửi) + mục mới trong `tools/audit_run.py` (tỉ lệ đạt
  `motion_match` có/không khung cuối).
- **Cần người dùng:** gửi `Get this Skill to Claude/clipai-1.3.1/clipai/reference.md` (và `scripts/video.mjs`) để xác nhận chính xác các trường
  khung cuối Kling, `element_ids`, giới hạn trộn tham chiếu — không đoán từ slide.

---

## 4. Danh mục lỗi đầy đủ (mã · vị trí · tác động · mức)
**P0/P1 — Tài nguyên, Director, Bible (A)**
- A1 `assets.py:40,229`, `llm_runner.py:295` — đường dẫn tương đối, ảnh thiếu bị bỏ âm thầm → Director thấy 0 ảnh (R1) · chất lượng · **High**
- A2 `llm_io.py:189-191`, `step1.py:433,446` — Lock chỉ điền khi rỗng, không sinh lại khi ảnh/Bible đổi · **High**
- A3 `compare.py:39-41` — nhân bản chép Lock/locked/anchor cũ · High
- A4 look anime tự chọn ≠ ảnh in-game (R2) · High
- A5 `step1.py:700-712`, `reference_analysis.STYLES` — không có trường look, `style_profile` 6 lựa chọn · Med
- A6 `previz.py:109` layout chỉ nhận chữ `shot`, không cỡ cảnh (R7) · High
- A7 không có chiều cao/vóc dáng (R7.4) · High
- A8 `llm_io.py:72,196-198,209` — kiểm "thiếu shot"/số cảnh sau khi đã trả tiền, không hỏi lại, không lưu câu trả lời · **High cost**
- A9 `llm_io.py:183-191` + `common.py:163` — lưu nửa chừng, không rollback · **High data**
- A10 `shots.py:187-188`, `prompts.py:118`, `step1.py:723` — chạy lại Director ở chế độ shot xóa sửa tay/layout, UI nói "được giữ" · **High**
- A11 `llm_io.py:184-188` — mô tả/trang phục nhân vật sửa tay bị ghi đè; wardrobe thiếu → NULL · **High**
- A12 `prompts.py:102-121` — Director không thấy Bible hiện tại → nhân vật trùng tên khác hoa/thường · Med-High
- A13 `llm_runner.py:297` vs `claude_tasks.py:332` — ảnh Director thấy ≠ ảnh Lock/gen dùng · Med
- A14 `step1.py:809` — "Viết Lock từ ảnh" chạy khi không có ảnh · Med
- A15 `assets.py:316,482` — so tên theo chữ đầu, người thứ hai mất ảnh tham chiếu · Med
- A16 `shots.py:149` — shot `characters: []` kế thừa cả dàn nhân vật · Med
- A17 `shots.py:320-322,368` — shot 1,5s bị tính/cắt thành 3s · Med
- A18 `step1.py:705-709` — đổi chế độ shot khi đã có dữ liệu chỉ cảnh báo · Med
- A19 `step1.py:308` — "Làm lại" giữ nhân vật đã khóa, Bible cũ sống qua kịch bản mới · Med
- A20 `script_parser.py:12`, `script_reader.py:210-217` — "Nội dung:" bị coi là tiêu đề; .docx mất dòng ngắt/khối nội dung · Med
- A21 UX: xóa World Bible không hỏi; gen bộ trang phục 2 ảnh không giá; nút Director không ước tính; `parse_warn` không theo dự án; trần job tính trước khi chia shot · Low

**P0b — Kho tài nguyên (T)**
- T-a thông tin chuẩn nhân vật (Lock, ảnh mốc, giọng, chủ thể Seedance) lưu theo dự án, không theo kho → làm lại mỗi dự án, lệch giữa dự án · **High**
- T-b `assets.py:348-380` ảnh không có nhãn góc/cỡ; chọn tham chiếu theo hình dạng file, không theo cỡ cảnh/hướng của shot · **High**
- T-c `assets.py:456,501` bối cảnh chọn ảnh "rộng nhất", bỏ qua góc máy trong `set_analyses` (R7) · High
- T-d `assets.py:518` ảnh gửi không có vai trò giới hạn · High
- T-e chưa có ảnh chuẩn theo look (anime) → mỗi shot/dự án anime một kiểu · Med-High
- T-f chưa nhập ảnh bản đồ in-game/artwork (nay nhập được nhờ `_shrink`) · Med
- T-g `characters.subject_asset_id` theo dự án → tải chủ thể Seedance lại mỗi dự án · Low-Med
- T-h ảnh map in-game (kể cả chụp từ trên cao) ghép thẳng làm nền/layout + gửi làm tham chiếu điểm ảnh → sai bố cục, sai tỉ lệ người/cảnh (người dùng xác nhận) · **High**
- T-i kho lẫn lộn: nhiều góc/skin/bảng thiết kế trong một mục, tài nguyên riêng dự án chung bảng với kho, không có trạng thái duyệt, mới nhập dùng ngay · Med-High
- T-j lấy tài nguyên rải rác nhiều hàm, mỗi bước một bộ ảnh khác nhau (Director ≠ Lock ≠ gen ≠ QC), không ghi lại đã dùng ảnh nào · High

**P1b — Layout (L)**
- L1 layout nền chụp từ trên cao + hình cắt tí hon làm ảnh tham chiếu #1 không giới hạn vai trò (R7.1) · High
- L2 QC `set_match` so với layout sai (vòng tròn) · Med
- L3 `previz.py:95,150-153` — storyboard ghi đè sửa tay trong lúc Claude chạy · Med
- L4 `compare.py:47` — nhân bản chép `layout` không có file · Low-Med
- L5 `previz.py:108,112` — chỉ hiện 10 ảnh nền · Low

**P2 — Ảnh & QC ảnh (I)**
- I1 `runner.py:490` — prompt ảnh dùng ký hiệu "MCU", câu khung cắt có sẵn ở `shots.py:152` không được gửi (F9) · High
- I2 `runner.py:425-445` — nối ảnh shot trước bất kể cỡ/góc (F8) · High
- I3 `runner.py:496` + `pipeline.py` — câu sửa kèm điểm số/tiếng Việt vào prompt Deepix, chỉ giữ lần gần nhất (V3) · High
- I4 `claude_tasks.set_consistency`, `autopilot.py:767` — QC đồng bộ chuẩn số đông, sửa sai, tự gen lại (R3/V4) · High
- I5 `data/qc_checklist.json` — bố cục/khớp bối cảnh/tỉ lệ không có sàn (F11) · High
- I6 15/38 ảnh V1 dưới sàn nhân vật vẫn được duyệt (nghi `autopilot.py:312` duyệt mọi pending_review) · High
- I7 `pipeline.py:313` — điểm trung bình, ngưỡng 0,82 chưa hiệu chỉnh (V7) · Med
- I8 `lineage.py:14` IMAGE_KEYS thiếu World Bible/look/trường v2 → không đánh dấu cũ · Med

**P3/P4 — Motion & video (M)**
- M1 `runner.py:333` — gen lại shot sau trong nhóm multi-shot luôn "missing inputs" · **High**
- M2 `autopilot.py:459` — tự duyệt clip QC còn lỗi · **High**
- M3 `runner.py:155-177` — dashboard + autopilot cùng poll 1 job → tải 2 lần, follower trùng · Med
- M4 `voice.py:188`, `llm_io.py:390` — khớp giọng chỉ sửa motion_prompts, bị ghi đè, clip bị đánh cũ → trả tiền lại · **High**
- M5 `llm_io.py:396` — lưu sửa prompt làm job video đang chờ fail, ăn lượt · Med
- M6 `step3.py:66-77` — "Duyệt" bỏ nội dung đang gõ · Med
- M7 `clipai.py:33,199` — Seedance bỏ ảnh tham chiếu/chủ thể khi có khung đầu, UI vẫn cho gắn; video tham chiếu có thể bị từ chối · Med
- M8 `cost.py:126-160` — ước tính thiếu gen lại cũ, std, audio, cả nhóm; không hiện ở nút gen lại · Med
- M9 `model_router.py:135-147`, `prompts.py:238`, `claude_tasks.py:106` — override trước luật multi-shot; Claude được báo sai model/giới hạn · Med
- M10 `runner.py:418`, `shots.py:375` — chia nhóm tính lại lúc tải; cắt lỗi thì chép nguyên clip nhóm · Med
- M11 `clipai.py:87` — round() 4,5→4 · Low-Med
- M12 `claude_tasks.py:150-159` — QC video 6 khung, bỏ 2 đầu, full-res, không mốc thời gian, follower so ảnh leader, prompt hiện tại thay bản đã gửi, không kiểm tiếng · Med
- M13 `claude_tasks.py:183`, `autopilot.py:454` — clip QC lỗi mãi hỏi Claude mỗi tick · Med cost
- M14 `runner.py:393-407`, `step4.py:48,213` — chặn bản quyền chuyển Kling nhưng kẹt · Med
- M15 `step4.py:50` — "Gen lại clip lỗi" thử lại cả lỗi do đầu vào · Low-Med
- M16 `lineage.py:42` — dấu vân tay video thiếu model/audio/tham chiếu · Low
- M17 `clipai.py:338` — hủy task ngoài 3 trang không hủy thật · Low
- M18 `step4.py:183` — "So sánh tổng" bỏ qua multi-shot/override · Low
- M19 `clipai.py:224` — leader multi-shot bị kiểm 2.500 ký tự dù không gửi; negative bị bỏ · Low
- M20 `llm_runner.py:102,372` — cắt âm thầm ảnh thứ 13+, ảnh nhóm lặp · Med
- R4 nhóm multi-shot thiếu nhân vật trong ảnh đầu (F4) · High · R5 clip dài nhiều nhịp (F6) · Med · R6/V2 gen lại cùng đầu vào (W3) · High
- V8 lỗi tham số kiểm được trước (khung đầu/cuối Seedance ×15, real_person ×2, prompt >512 ×3) (W10, W11, W13) · Med
- K-a chỉ dùng khung đầu cho shot có `end_state` rõ → model tự bịa đoạn kết, `motion_match` thấp, gen lại (K1, K2) · **High**
- K-b `model_router.py:78,87` chọn Seedance cho ≥ 3 người dựa trên ảnh tham chiếu từng người — khả năng này đã tắt (K3) · **High**
- K-c chưa thử chế độ tham chiếu Seedance, Kho chủ thể (FF có bản quyền), Kling elements cho multi-shot (K4, K5) · Med
- K-d job không lưu đã gửi khung cuối/tham chiếu/chế độ nào → không kiểm được (K7) · Med

**P5 — Âm thanh & xuất bản (D)**
- AU1 `voice.py:16` model TTS mặc định `eleven_multilingual_v2` — nghi không hỗ trợ tiếng Việt; không gửi `language_code` · **High** (xác minh)
- AU2 `voice.py:91-94` hết giọng Việt thì lấy giọng ngoại · High · AU3 `data/pronunciation_vi.json` phiên âm sai/gạch nối · Med
- AU4 câu bị cắt (= M4, D9, D1, D2) · High · AU5 trộn tiếng model video với TTS (= D4) · Med · AU6 không kiểm âm thanh · High
- AU7 không khớp môi (không có API) · Med · AU8 giọng theo dự án, không theo kho · Med
- D1 `voice.py:200-214` thoại clip bỏ tick vẫn phát · High · D2 `subtitles.py:196-203` phụ đề lệch · High
- D3 `step5.py:419` upload ghi đè clip đã trả tiền, path traversal · **High**
- D4 `ffmpeg_studio.py:228` mất tiếng mọi clip, autopilot không báo · High
- D5 `step5.py:46`, `autopilot.py:489` "không nhạc" không được nhớ → gen nhạc trả tiền · Med
- D6 `ffmpeg_studio.py:229` render lỗi để file hỏng mà vẫn "mới"; file tạm dùng chung · Med
- D7 `lineage.py:218-235` đổi phụ đề/card/xuất bản không đánh dấu cũ · Med
- D8 `delivery.py:167` dịch phụ đề lại mỗi lần, bỏ bản sửa tay · Med cost
- D9 cổng thoại khi tắt tiếng chỉ cảnh báo mỗi nhịp, không kéo dài (W16) · Med
- D10 SFX chọn theo tên file, không chạy ở autopilot; 2 nút "Kiểm tra + tải về" · Low

**P6 — Autopilot (O)**
- O1 tự duyệt mọi pending_review ảnh/clip (= I6/M2, W15) · High · O2 QC đồng bộ tự gen lại (I4) · High
- O3 `autopilot.py:444` clip cũ tự gen lại ngoài max_retry (V5) · Med · O4 trần theo số job chung (V6) · Med
- O5 `autopilot.py:305,430` thử lại mọi lỗi (W9) · Med · O6 cổng Bible không đòi ảnh mốc/Lock · Med
- O7 **W12 hở** — `widgets.py:39,46` tạo provider mới mỗi poll; bộ đếm trong RAM; nguy cơ trả 2 lần sau khởi động lại · **High**
- O8 đổi chế độ shot giữa chừng (= A18) · Med

**P7 — Chi phí (C)**
- C1 `autoqc.py:44,54,123`, `asset_vision.py:62,115`, `research.py:79` ngoài sổ + ngoài trần · **High**
- C2 không prompt caching · C3 ảnh full-res (chỉ thu >5MB) · C4 không effort · C5 không kiểm stop_reason · C6 motion gửi dư · C7 usage thiếu project/stage — High/Med
- C9 `budget.py:79` model không giá → $0 · Low · C10 `llm_runner.py:161,178` kiểm trần lỗi cho qua, ghi sổ lỗi bị nuốt · Med
- C11 video ghi tiền lúc gửi, không đối chiếu `cost` ClipAI · Med · C12 giá ảnh/audio null → không vào trần · Med

**P8 — Khung Dashboard (S/P/Q/U)**
- S1 `common.py:281-285`, `header.py:54`, `auth.py:25` — vượt "chỉ máy chủ", đăng nhập bằng `?login=`, owner hard-code · **High bảo mật**
- S2 `pipeline.py:89`, `db.py:5` — xóa dự án mất thùng rác/lịch sử chi, id tái dùng · Med · S3 `step5.py:106,183` xóa không hỏi · Med
- S4 2 cửa sổ cùng dự án ghi đè (WORKFLOW_REVIEW B.4) · Med
- P1 `db.py:334-364`, `app.py:80`, `widgets.py:13,26,34` — schema chạy lại mỗi rerun/poll, không đóng kết nối, client mới mỗi poll · Med
- P2 `step5.py:360,520,541`, `admin.py:620` — tính lặp, đọc cả video vào RAM · Med · P3 `perf.py:89-94` tab hiệu suất đếm sai · Med
- Q1 `llm_runner.py:102` cắt 12 ảnh → QC video mất ảnh tham chiếu · Med · Q2 `knowledge.py:311` bản chắt lọc bị cắt vẫn thay tài liệu · Med
- U1 `step5.py:478`, `admin.py:662` lỗi bị nuốt · Low · U2 UI_AUDIT còn mở (Bước 3/4/5, màn hẹp, chữ lỗi thời, preset lạ, `resize_panel` chết) · Low

---

## 5. Lộ trình giải pháp (thứ tự: an toàn → tiền → chất lượng → vòng chạy → hoàn thiện)
Mỗi giai đoạn: code + test hồi quy (fixture dựng từ lỗi GĐ6 khi có) + 1 commit + push; cập nhật TODO; sửa PLAN.md thì build docx/pdf.

**GĐ-A · Khẩn: bảo mật, mất dữ liệu, tiền ma (không credit)**
- S1: bỏ `?login=` (hoặc chỉ khi `DASHBOARD_DEV=1`), xác định "máy chủ" bằng địa chỉ kết nối thật (không header Host), email owner lấy từ env.
- O7 (sửa W12): lưu "đã thấy task"/số lần không thấy vào CSDL (cột mới trên `jobs`), provider dùng chung (cache theo tiến trình ở
  `dashboard/widgets.py`); `not_created` chỉ khi chưa từng thấy **và** đã quét tới task cũ hơn thời điểm gửi.
- D3: upload clip tay → tên riêng + `os.path.basename`, clip cũ vào thùng rác. S2/S3: xóa dự án giữ lịch sử chi, AUTOINCREMENT, hỏi trước khi xóa.
- A8/A9: kiểm "thiếu shot/số cảnh" trong validator (để `ask_json` hỏi lại), lưu câu trả lời thô, lưu Director trong 1 giao dịch.
- A10/A11: bảo vệ trường sửa tay ở chế độ shot và mô tả nhân vật (khóa theo trường như `_user_locked`).
- M2/I6/O1 (W15): autopilot không duyệt ảnh/clip có tiêu chí dưới sàn hoặc đã hết lượt tự sửa — để cho cổng storyboard/người.

**GĐ-B · Chuẩn xây dựng (tài liệu)** — `docs/CHUAN_XAY_DUNG.md` 8 luật (không im lặng khi thiếu đầu vào; ma trận luồng; giả định → guard
trong code; một nguồn chuẩn nhân vật; thang kiểm thật trước khi gen hàng loạt; chẩn đoán trước khi gen lại; QC chỉ so chuẩn thật; "đã sửa"
kèm bằng chứng chạy thật) + luật chi phí; dẫn chiếu từ CLAUDE.md và TODO.

**GĐ-C · Chi phí & sổ chi (không credit, trừ 1 lần đo nhỏ xin phép)** — C1 sổ + trần cho mọi lời gọi Claude (một client có ledger, nhãn
`stage` + `project_id`); C2 prompt caching (tĩnh → chung dự án → riêng shot, `cache_control`); C3 thu ảnh ≤1024/768 px; C4 effort theo việc;
C5 kiểm `stop_reason`; C6/M20 gọn motion, báo khi vượt 12 ảnh, mỗi nhóm 1 ảnh; C9/C10 model không giá → chặn, lỗi trần → chặn; C11 đối chiếu
`cost` ClipAI (quy đổi khi có tỉ giá credit); C12 giá ảnh/audio; M8 ước tính trước mọi nút tốn tiền; C8 đo thật (~$0,1–0,3).

**GĐ-D · Lưới an toàn chống hỏng im lặng (không credit)** — A1 `assets.resolve()` theo gốc repo + kiểm khi khởi động; Director bắt buộc thấy
ảnh (lỗi rõ khi 0/N); M7 UI không cho gắn thứ Seedance bỏ; Q1/Q2 báo khi cắt ảnh/tài liệu; U1 không nuốt lỗi; cờ "đã kiểm thật" cho tính
năng rủi ro (previz, multi-shot, set-check autofix, chain_previous).

**GĐ-E0 · Kho tài nguyên chuẩn + cách dùng bối cảnh (không credit, trừ T6/B5c)** — làm trước GĐ-E vì F1/F7/F10 dựa vào nó:
1. Cấu trúc kho G1–G5: bảng biến thể + cột `view/role/look/status` trên `asset_images` (migration giữ dữ liệu cũ, ảnh cũ vào hộp chờ phân loại, Claude
   đề xuất nhãn nền bằng `asset_vision`/`set_analyses`, người duyệt), tách tài nguyên riêng dự án; G6 bảng sức khỏe kho.
2. T1 hồ sơ nhân vật chuẩn cấp kho (dự án kế thừa, chỉ lưu biến thể); T7 chủ thể Seedance theo tài nguyên.
3. Bối cảnh B1–B6: hồ sơ bối cảnh bằng chữ (mở rộng `set_analyses`), **bỏ gửi layout ghép và ảnh map góc cao cho model** (`runner.ImageRunner._submit_args`,
   `assets.scene_references`), chỉ nền ngang tầm mắt đã duyệt cho shot rộng cùng góc, ảnh chi tiết cắt từ map, QC `set_match` so hồ sơ bối cảnh; layout/
   storyboard 2D chỉ còn cho người xem.
4. R-pick: một hàm chọn tài nguyên theo mục đích thay cho các chỗ lấy rải rác; T3 chọn ảnh nhân vật theo cỡ cảnh/hướng; T5 vai trò giới hạn trong
   `reference_note`; ghi và hiện "tham chiếu đã dùng"; T9 sửa nền (A1, A15).
T6 (ảnh chuẩn anime) và B5c (plate ngang tầm mắt) tốn ảnh — chạy ở GĐ-I, xin phép.
5. **Tính năng 3D build sẵn** (không credit): `tools/render_plates.py` (Blender 5.0.1), `core/plates3d.py`, mục "🏗 Bối cảnh 3D" trong Kho tài nguyên,
   `docs/HUONG_DAN_3D.md`, test với Blender giả — để phiên trên máy người dùng test file tháp đồng hồ ngay.

**GĐ-E · Sửa gốc chất lượng (không credit) — theo 2 look**
- Look: trường `look` = `ANIME` | `FF_INGAME` (tách `style_profile`), bỏ lựa chọn khác ở Bước 1; look in-game: ảnh tài nguyên chuẩn tuyệt đối,
  render_style lấy từ ảnh; look anime: render_style bắt buộc, giữ nhận diện theo ảnh.
- F1 kiểm Bible+Lock↔ảnh (cache theo sha ảnh), Lock sinh lại khi nguồn đổi (A2, A3), Director thấy Bible hiện tại (A12), cùng ảnh cho Director/Lock/gen (A13), A14.
- F10 chiều cao/vóc dáng + mốc bối cảnh (A7).
- F7 (đã thay bằng B1–B6 ở GĐ-E0): layout không còn là ảnh tham chiếu cho model; L3–L5 sửa cho phần storyboard 2D dành cho người xem.
- F9 câu khung cắt vào prompt ảnh (I1); F8 nối ảnh chỉ khi cùng cỡ/góc (I2).
- F3 QC đồng bộ có chuẩn = ảnh tài nguyên, chỉ báo (I4); F11 sàn bố cục/khớp bối cảnh/tỉ lệ (I5); I8 lineage theo look/World Bible.
- F4 chia nhóm multi-shot theo nhân vật + thẻ ngoại hình ≤512 (R4); M9 luật multi-shot trước override, Claude được báo đúng Kling/512/15s;
  M1 gen lại follower lấy ảnh leader; M10 lưu độ dài đã gửi.
- F5 `core/diagnose.py` chẩn đoán lớp sai; gen lại **tối đa 2 lần, mỗi lần đổi đầu vào** (W3: `issues` vào motion prompt; W4: tách
  `retry_reason` và câu sửa sạch cộng dồn — I3); F6 clip dài nhiều nhịp chỉ báo.
- A15–A20 (so tên, shot rỗng, 3s tối thiểu, đổi chế độ, làm lại, parser).
- **Cách dùng ClipAI (P4b):** K1 ảnh khung cuối cho shot có `end_state` (Deepix, storyboard hiện cặp đầu–cuối, QC chấm cả hai); K2 chọn model
  theo nhu cầu khung cuối; K3 sửa `model_router` bỏ tiền đề "Seedance nhận tham chiếu từng người"; K6 clip dài chia shot; K7 lưu "đã gửi gì" +
  mục so sánh có/không khung cuối trong `audit_run.py`. (Trước khi code K2/K5: đọc `clipai-1.3.1/clipai/reference.md` do người dùng gửi.)

**GĐ-F · Vòng chạy & autopilot (không credit)** — W2 pilot mặc định chọn theo nhân vật/bối cảnh/cỡ cảnh; W5 QC đồng bộ sau pilot, trước
storyboard; W6/O3 clip cũ không tự gen lại; W7/O4 trần theo shot (2+2) và theo tiền dự án; W9/O5 chỉ thử lại lỗi tạm thời; W10 bảng luật
từng model (`data/provider_rules.json`) kiểm trước khi gửi; W11 look in-game → Kling; W13 báo khi cắt prompt; W16/D9 cổng thoại; O6 cổng
Bible đòi ảnh mốc/Lock; M3 khóa poll một nơi; M4/M5/M6 một nguồn thời lượng, không fail job đang chờ, duyệt lưu nội dung đang gõ;
M11–M19; W8 đo đồng thuận người–QC → cổng storyboard tự nới dần (≥90% trên ≥50 ảnh cùng gói look).

**GĐ-G · Âm thanh & xuất bản (không credit, trừ bộ thử giọng)** — **ưu tiên giọng Việt trước:** AU-a model có tiếng Việt + `language_code`, AU-b chỉ giọng
Việt + giọng chuẩn theo kho, AU-c rà từ điển, AU-d trọn câu, AU-e mix sạch, AU-f kiểm bằng ASR, AU-g luật shot thoại + thử audio tham chiếu Seedance;
rồi D1/D2 một timeline chung (clip đã chọn + giây đã sửa) cho giọng/phụ đề/render; D4 báo và
giữ tiếng; D5 nhớ "không nhạc"; D6 render ra file tạm rồi đổi tên, khóa render; D7 dấu cũ cho lớp; D8 cache bản dịch + dùng bản sửa tay; D10.

**GĐ-H · Giao diện tối giản, hiệu năng, dọn tồn đọng (không credit)** — **P8b:** màn chính 4 thẻ (Kịch bản → Nhân vật → Storyboard → Kết quả) dựa trên
autopilot + 2 cổng, chế độ chuyên gia giữ 5 bước tay, hộp thông báo gom cảnh báo, mặc định theo gói look, giá hiện trên nút tốn tiền, dọn nút trùng/chết;
P1 kết nối/migration một lần, client/provider dùng chung; P2 cache trạng thái, tải
file theo yêu cầu; P3 tab hiệu suất đúng; S4 cảnh báo 2 cửa sổ; U2 (UI_AUDIT); dọn TODO/PLAN lỗi thời (danh sách GĐ5 plan người dùng);
W17 thư viện prompt mẫu (mở rộng `core/lessons.py` học từ thành công, gắn vào gói look).

**GĐ-I · Kiểm thật theo bậc (tốn credit — xin phép từng bậc)**
0. **Giọng Việt (rẻ nhất, làm trước):** bộ thử AU-h — 10 câu × 2–3 model TTS × giọng Việt (vài chục lượt TTS) → người nghe chấm → chốt model/giọng;
   kiểm ASR; đọc sổ audio GĐ6 (`usage_events` kind=audio: model nào đã dùng) để xác nhận AU1.
1. Chữ (~$0,3 Claude): Director thấy ảnh, F1 kiểm Bible, layout/nhóm cho 1 cảnh → người xem.
2. Ảnh (~6 ảnh Deepix) cho cả 2 look → cổng storyboard → người duyệt; kèm T6 ảnh chuẩn anime cho các nhân vật của cảnh thử (vài ảnh/nhân vật).
3. Video 1 cảnh (~$3–5) → so bản cũ, đối chiếu `cost` ClipAI với sổ, kiểm W12 thật; **A/B khung cuối**: cùng shot có `end_state`,
   gửi 1 khung đầu vs khung đầu + cuối, so `motion_match`/người chấm; **A/B ảnh đầu vào (P4c):** khung sạch vs storyboard nhiều ô làm tham chiếu;
   thử K4 (chế độ tham chiếu, 1 shot đông người) và K5 (Kho chủ thể 1 nhân vật FF).
3b. (Tùy chọn) **Thí nghiệm bản đồ 3D với file tháp đồng hồ Đảo Quân Sự** (~5–6 ảnh Deepix, chạy trên máy người dùng bằng `tools/render_plates.py`):
   3 shot × trời A/B/C × 2 look; so với cách B1–B3; đo thời gian mở file/render thật, ghi `docs/RESEARCH_3D_PREVIZ.md`.
4. Đạt → dựng **gói look** (look × model) đầu tiên; xin ngân sách hoàn tất → `docs/V3_AB_REPORT.md`, chốt `shot_mode`, merge về `main`.
5. Hiệu chỉnh ngưỡng QC từ dữ liệu cổng storyboard (W8) → mới cân nhắc tự nới cổng.

---

## 6. Quyết định
**Đã chốt (2026-09-24):** 2 look (anime, giống y hệt in-game FF); cổng storyboard bật mặc định; gen lại tối đa 2 lần, mỗi lần đổi đầu vào;
bỏ video mẫu → gói look đã kiểm + thư viện prompt mẫu tự đúc kết; Claude qua API (trần $5); chỉ dùng tính năng có API.
**Còn mở:** gửi `clipai-1.3.1/clipai/reference.md` + `scripts/video.mjs` để xác nhận khung cuối Kling / `element_ids` / luật trộn tham chiếu (K2, K5);
đối chiếu số dư ClipAI (task hỏng vì prompt > 512 có `cost=90`; tổng trừ 23–24/9 ≈ $28–29?); tỉ giá credit ClipAI ↔ USD (cho C11);
quyết định LAN/firewall (liên quan S1).

## 7. Việc đầu tiên sau khi duyệt
Lưu kế hoạch này vào repo: `docs/KE_HOACH_TONG_2026-09-24.md` (dẫn chiếu từ PLAN.md Mục 7 + TODO.md, build lại docx/pdf), commit + push
vào PR #1; sau đó làm lần lượt GĐ-A → GĐ-H (không tốn credit), GĐ-I xin phép từng bậc. Mỗi GĐ một commit trên `claude/upbeat-hawking-6o9njo`.

## 8. Kiểm chứng
- `python -m unittest discover -s tests -t .` pass sau mỗi GĐ (hiện 682).
- Test hồi quy mỗi mã lỗi đã sửa (ví dụ: A1 chạy từ thư mục khác vẫn đọc ảnh; A8 thiếu shot → hỏi lại Claude; O7 provider tạo mới vẫn nhận
  ra task "ma"; M1 gen lại follower; D3 upload không ghi đè; S1 `?login=` không đăng nhập được, header Host giả không vượt).
- Chạy giả lập (`MOCK_REAL_MEDIA=1`) 3 phương án tới bản giao, qua cổng storyboard.
- Bối cảnh: test không có ảnh layout ghép / ảnh map góc cao nào lọt vào prompt ảnh của shot ngang tầm mắt; shot rộng cùng góc nhận đúng nền đã
  duyệt; prompt có câu chiều cao mốc + nhân vật. Kho: ảnh ở hộp chờ không bao giờ được dùng; migration giữ nguyên ảnh cũ.
- Kho: test chọn tham chiếu theo shot (CU → ảnh nửa người, quay lưng → ảnh sau lưng, shot ngang tầm mắt không nhận ảnh bản đồ từ trên cao);
  dự án mới kế thừa hồ sơ chuẩn, Director không ghi đè; nhân bản không chép Lock cũ.
- `tools/audit_run.py` sau GĐ-I: tỉ lệ gửi lại, % tiền làm từ ảnh có lỗi, đồng thuận người–QC so với GĐ6.
