# Kế hoạch: đặt máy 3D đúng trên map Free Fire nhiều lớp (09/10)

> Người dùng chốt 09/10: hướng **LAI**. Code tự dò vị trí máy theo 4 điều kiểm và đề xuất 3 ứng viên render sẵn để chọn. Chưa ưng thì chỉnh tay ở **Bàn đạo diễn 3D** trong Dashboard, dựng trên map FF thật (giống "Bàn đạo diễn" web ClipAI nhưng có map của ta).
> Bản này thay việc (a)/(b) ở TODO 09/10 đêm (đã hoãn).
> Chi phí API: 0 USD (Blender + trình duyệt). Vẽ lại ảnh sau khi xong thì báo giá riêng.

## Vì sao phải làm (bằng chứng #24)
`core/plate_camera.camera_for` tính máy "mù", không biết hình khối map:
- chỉ dùng `angle` + `size`; `ots` thành ngang tầm mắt (−10°);
- khoảng cách thuần theo cỡ cảnh (~1 m với MS/MCU);
- `low` cố định 0,45 m;
- không bắn tia kiểm vật cản;
- đạo cụ (giếng) không có trong 3D.

Map FF có nhiều lớp (tầng quảng trường, bậc thềm, tường chắn, mái). Máy dễ rơi sang tầng khác hoặc ra sau tường. Ví dụ shot 5: render là 2 lớp tường che kín khung, trong khi người dùng nói "cùng mặt sàn ở vị trí đó không có tường cao". Model ảnh chép render rất sát, nên máy lệch thì ảnh lệch.

Nhánh nền đã có (CHƯA GỘP, chưa rà): `worktree-agent-ab5a90511a3b9ff78` `70f7259`.
- `looks_down()` → cúi 35°;
- `low` đặt máy theo chiều cao người;
- `clearance_fix()` + bắn tia trong `tools/render_plates.py` (chưa chạy thật).
Các đợt dưới dựng TIẾP trên nhánh này.

## 🔁 ĐỔI HƯỚNG 09/10 tối (người dùng): "dựng sân khấu có lưới ô rồi mới đặt máy, đo bằng số" — thay cách vá G0
Người dùng: *"vẫn đang lặp lại tình trạng có lỗi thì sửa chứ không phải tìm ra cách làm đúng"*; *"sân khấu cũng cần tọa độ kẻ các ô thành hệ lưới để xác định vị trí chính xác"*.
Chạy thật G0 #24 (≈ 0,37 USD) lộ ra cách làm sai từ gốc: Director đoán phương vị độ khi KHÔNG thấy sân khấu (giếng/nhân vật không có trong 3D → máy cúi chỉ thấy sàn, tỉ lệ giếng/yêu nữ không kiểm được), rồi Claude nhìn render để phán điều code đã biết bằng số (máy nghiêng −6° bị khai "cúi"). Đã dừng phiên vá 4 lỗi.
**Cách làm đúng (như tổ quay phim thật: dựng trường quay → đi vòng xem góc → chọn):**
- **S0 Lưới sân khấu:** gốc = chỗ đứng chính; cột chữ Tây→Đông, hàng số Nam→Bắc; ô 1 m (0,5 m chỗ diễn gần), ≈ 20×20 m. Mỗi ô bắn tia Blender từ trên xuống: cao độ sàn + vật (sàn/bậc/tường/nhà/tháp) → biết ô đi được, ô tường, ô tầng khác. Ảnh nhìn từ trên kẻ lưới + tên ô cho Director và người dùng ("dời giếng sang G8").
- **S1 Dựng sân khấu trong 3D:** đạo cụ (giếng: khối đúng cỡ) + người nộm đúng chiều cao ở ô theo nhịp → render có giếng/người thật, tỉ lệ đúng.
- **S2 Code đi vòng ứng viên:** nhiều vị trí máy (ô × độ cao × cỡ) → lưới tia đo % tháp/nhà/tường/trời/sàn, giếng + nhân vật trong khung và cỡ, vật cản gần nhất, phía trục. Đo, không đoán, 0 USD.
- **S3 Director chọn theo ô từ bảng số + tấm ghép ứng viên** theo ý đồ; luật trục / gia đình nền / cúi đúng ý / không tường che kiểm bằng SỐ. Gỡ "Claude duyệt render" của G0. Người duyệt tấm ghép cuối.
- **S4 Chạy lại #24** → tấm ghép trước khi vẽ ảnh (báo giá).
Phần G0 đã gộp (cờ TẮT) giữ: sơ đồ cảnh, setup dùng lại, luật trục/gia đình nền — chuyển sang nói bằng ô lưới.
**Bước 0 (đo trước khi xây, 0 USD):** lưới ô + bản đồ cao độ/vật thể #24; tên vật thể trong map có phân được tháp/nhà/tường/sàn không; đặt thử khối giếng + người nộm, render 1 góc.

## 🥇 G0 — LÀM TRƯỚC (người dùng 09/10): Director lập sơ đồ cảnh + bộ góc máy, bản đơn giản bằng công cụ hiện có
Người dùng: "Director phải là người làm tốt khâu này". G1–G4 bên dưới là bản NÂNG CẤP (bản đồ tầng, bộ kiểm tự động, Bàn đạo diễn). G0 làm Director đặt máy đúng cho cảnh đơn giản (#24: 9 shot cùng quảng trường, ít vật, ít di chuyển, liên kết nhau) bằng những gì đã có. Dự án thử: **#24**.

**Hiện trạng sai:** Director/Quay phim ghi `plate_view` (landmark/away/left/right) TỪNG SHOT RIÊNG, không có sơ đồ chung, nên 9 shot ra nhiều hướng không ăn khớp. Ví dụ shot 5 và 7 nhìn sang Tây, thấy mặt quảng trường khán giả chưa thấy. Không có ai xem render nền trước khi vẽ ảnh. QC ảnh bằng Claude đang TẮT (nghiệm thu #8: bắt 6/12, báo nhầm 12/21); Tổ QC chỉ học việc.

> **Trạng thái 09/10 (phiên tiếp):** mục 1–5 ✅ code, đã gộp main — nền máy `70f7259` + sửa 6 lỗi rà `f9ed9f3`; G0 `51679d0` + sửa 7 lỗi rà kỹ `7a3b165` (gộp nhầm máy khi khác angle/nhìn xuống/lens; ghi đè trường khóa tay; render lỗi vẫn gọi Claude; CLI sai khung 16:9; ước tính thiếu trần ×4; đổi máy shot đã có ảnh; diag lặp). Cả bộ test 3551 xanh (+ 1 sửa: khai 2 khâu Claude vào `devsys/decisions.json`). Cờ `director_camera_plan` TẮT. **Mục 6 ⬜ chờ người dùng duyệt tiền.** Lệnh: `FEATURE_DIRECTOR_CAMERA_PLAN=1 py tools/location_pack.py camera-plan --project 24 --review [--yes]` (không `--yes` chỉ in ước tính).

**Việc G0:**
1. **Sơ đồ cảnh** (Director, một lần cho mỗi cảnh liên tục/story scene). Đầu vào:
   - kịch bản + beat;
   - thông tin bối cảnh: spot, hướng các mốc (tháp/nhà mái đỏ/tường thấp) tính từ `model3d.anchor` + spots;
   - ảnh `topview` nếu có.

   Ra:
   - vị trí đạo cụ (giếng: hướng + khoảng cách so với spot);
   - điểm đứng của nhân vật theo từng nhịp;
   - đường trục 180°.
2. **Bộ góc máy 3–4 setup dùng lại cho cả cảnh**, như quay phim thật (A toàn cảnh về tháp, B ngược về dãy nhà, C qua vai cúi nhìn giếng…). Mỗi setup có ý đồ + lý do + phương vị (độ) + độ cao/cúi định tính. Mỗi shot gán setup + `size` + `angle`. Luật Director viết theo dạng "cách nghĩ có lý do" ([[feedback_director_as_thinking_brain]]):
   - cảnh liên tục giữ nền cùng gia đình với shot mở;
   - không vượt trục;
   - nhìn xuống thì máy cúi;
   - không đặt góc thấp sát tường chắn.
3. **Code tính số** từ setup: tọa độ/độ cao/cúi/ống kính qua `plate_camera.camera_for` + gộp nền `ab5a905` (`looks_down`, low theo chiều cao người — rà trước). `plate_view` = phương vị độ (đã hỗ trợ). Các shot cùng setup dùng cùng camera, nên cùng cache, render một lần.
4. **Director duyệt render nền** (Claude nhìn ảnh, vài cent): mỗi setup một render + ý đồ → khớp / không khớp + lý do (thấy tường lạ, thấy đồng hồ khi đang cúi, nền khác shot mở…). Không khớp thì đổi phương vị/cỡ, tối đa 2 vòng, rồi báo người dùng. Model khai quan sát dạng enum, code áp luật ([[reference_qc_model_sees_but_misreasons]]).
5. **QC bố cục bằng code sau khi vẽ ảnh:** so ảnh với render nền đã gửi (cấu trúc cạnh/độ sâu ước lượng, vị trí đường chân trời, vùng tường) → cờ "nền lệch render". Chỉ đánh dấu cho người, chưa tự vẽ lại.
6. **Chạy thật trên #24:**
   - sơ đồ + setup + duyệt render (≈ vài cent Claude, báo trước);
   - gửi người dùng tấm ghép render các setup;
   - sửa prompt shot 4–7 (shot 5 Kelly ngã ngửa ra sau xa giếng, mặt hướng giếng; shot 6 giếng nguyên vẹn; shot 7 giếng cao ngang hông yêu nữ);
   - vẽ lại shot 1–7 (≈ 0,36 USD, báo trước).
- Cờ mới `director_camera_plan`, TẮT mặc định; tắt thì luồng cũ y nguyên. RÀ KỸ (tiền Claude + cache plate).
- Bài học ghi vào prompt Director + `.claude-memory` ([[feedback_lessons_into_director]]).

## ⭐ BẢN GỘP (người dùng 09/10): (a) + (b) + kế hoạch này làm chung, 4 giai đoạn — BẢN NÂNG CẤP, sau G0
(b) "gặp tường tự xoay/lùi máy" chính là tự dò + 4 điều kiểm. (a) "khối giếng trong 3D" vừa là mốc bố cục vừa là vật chắn tia. Nhánh `ab5a905` là nền chung. Các mục "Đợt 0–4" bên dưới là CHI TIẾT kỹ thuật; thứ tự làm theo giai đoạn ở đây.

| GĐ | Việc | Ra gì |
|---|---|---|
| **G1 — Dữ liệu map (1 lần Blender mỗi map)** | Rà + gộp nền `ab5a905`. MỘT công cụ chạy cho **2 map FF**: **Tháp Đồng Hồ** (263) và **Cổng Trời** (265, núi nhiều tầng dốc). Bếp đời thường (415, `bep.glb`, không phải map FF) để ngoài, làm sau khi cần cảnh trong nhà. Ra bản đồ tầng (lưới 1 m cả map, 0,25 m quanh mỗi chỗ đứng), khối chắn, bản mô phỏng GLB, so độ sâu mô phỏng ↔ thật. Cache theo sha. Kèm Đợt 0: đo #24 shot 3/4/5/7 bằng tia trên dữ liệu này | `data/_plates3d/proxy/<sha>/` + báo cáo khớp + số đo shot 5 cho người dùng |
| **G2 — Bộ kiểm + tự dò + đạo cụ** | `core/camera_checks.py` (4 điều kiểm); sinh ứng viên + chấm điểm + render 3 ứng viên = việc (b); đạo cụ Kho có kích thước đặt khối vào cảnh Blender theo blocking = việc (a). Cờ `camera_probe` TẮT mặc định | mỗi shot: 3 render ứng viên + lý do |
| **G3 — Chọn ở Dashboard** | Thẻ ảnh shot "📐 Chọn chỗ đặt máy": 3 thumbnail, chọn → `plate_camera` (khóa tay) → render plate thật | người dùng chọn máy, 0 USD |
| **G4 — Bàn đạo diễn 3D** | three.js trên bản mô phỏng khối của G1, kiểm sống, lưu JSON camera → render map thật; thư viện chỗ đặt | chỉnh tay khi 3 ứng viên chưa ưng |

Sau G3 (chưa cần G4): render lại #24 shot 1–7 → người dùng xem → sửa prompt shot 4–7 → vẽ lại (≈ 0,36 USD, báo trước). Mỗi GĐ: RÀ KỸ (đổi cache plate mọi dự án).

## 4 điều kiểm (dùng chung cho tự dò và Bàn đạo diễn)
1. **Cùng tầng sàn.** Tia thẳng xuống dưới máy và dưới chân nhân vật: hai mặt sàn lệch ≤ 0,3 m, trừ khi shot ghi rõ quay từ tầng khác (`camera_setup` "từ trên bậc…").
2. **Nhìn thấy nhau.** 3 tia từ ống kính tới chân / ngực / đầu nhân vật. Tia nào chạm vật chắn trước nhân vật thì loại (máy sau tường / sau mép tầng).
3. **Khoảng trống.** Máy không nằm trong khối, cách tường/mái ≥ 0,4 m. Sau lưng máy không có vật chắn sát làm tối khung (tùy chọn).
4. **Nền cùng gia đình.** Đo trên render thấp (≈ 256 px): tường gần (< 4 m, độ sâu) chiếm ≤ 35 % khung. Với cảnh liên tục, nền có ít nhất 1 mốc khán giả đã thấy ở cảnh mở (tháp, nhà mái đỏ…) hoặc đúng `plate_view`.

## Đợt 0 — ĐO trước khi xây (nhỏ, làm đầu tiên)
- Viết công cụ bắn tia một lần trong Blender cho #24 shot 5, 7 (và 3, 4). Ghi ra:
  - cao độ sàn dưới máy / dưới nhân vật;
  - 3 tia ống kính → nhân vật chạm gì, ở bao xa;
  - tường gần nhất theo hướng nhìn: khoảng cách + chiều cao.
- Render đối chứng cùng hướng ở độ cao mắt 1,6 m.
- Báo người dùng số đo: xác nhận/bác giả thuyết "máy ở sau vật chắn / khác tầng".
- Kết quả ghi vào `.claude-memory` + mục này.

## Đợt 1 — Bản đồ tầng + bộ kiểm (lõi, Python thuần + Blender)
- **Bản đồ tầng sàn theo chỗ đứng.** Cache theo sha model + vùng:
  - lưới 0,5 m bán kính ~25 m quanh mỗi `spot`, mỗi ô bắn tia xuống → cao độ sàn;
  - gom ô liền nhau lệch ≤ 0,3 m thành "tầng" (flood fill);
  - lưu `data/_plates3d/levels/<sha>/<spot>.json`;
  - chạy một lần mỗi map (Blender nền).
- **Khối chắn:** cùng lúc trích tường/nhà/mái/cây thành hộp hoặc trụ có chiều cao. Đây là đầu vào cho bộ kiểm phía Python và cho bản mô phỏng của Đợt 3; một nguồn dữ liệu cho cả hai.
- **`core/camera_checks.py`** (thuần): nhận bản đồ tầng + kết quả tia → 4 điều kiểm → `{ok, lỗi[], why}`.
- **Phần Blender** (`tools/render_plates.py` hoặc tool riêng): dịch vụ bắn tia theo lô (nhiều máy một lần chạy) để không mở Blender nhiều lần.
- Test thuần: lưới giả có bậc thềm + tường. Máy khác tầng → loại; tia chạm tường → loại; tường chiếm 60 % → loại.

## Đợt 2 — Tự dò + 3 ứng viên
- **Sinh ứng viên quanh nhân vật:**
  - khoảng cách theo `size` (bảng đang có);
  - độ cao theo `angle` (low ≈ 0,5× người; eye 1,5–1,6 m; high/ots nhìn xuống cao hơn đầu + cúi);
  - hướng quét 360° bước 15°, ưu tiên quanh hướng `plate_view` và cùng phía trục 180°.
- Lọc bằng 4 điều kiểm, chấm điểm (gần hướng ý đồ, nền cùng gia đình, ít tường). Render 3 ứng viên tốt nhất ở độ phân giải thấp, Eevee, 0 USD.
- **Dashboard** (thẻ ảnh shot, Bước 2): "📐 Chọn chỗ đặt máy" hiện 3 thumbnail + lý do + cảnh báo. Chọn → lưu `plate_camera` vào shot (khóa tay `_user_locked`) → render plate thật từ đúng máy đó.
- Không ứng viên nào đạt → báo rõ (không im lặng) + gợi ý mở Bàn đạo diễn.
- Dự án cũ không có `plate_camera` → giữ `camera_for` (mặc định cũ), sau cờ mới `camera_probe` (TẮT mặc định).

## Đợt 3 — Bàn đạo diễn 3D trong Dashboard
- **KHÔNG nạp cả map vào trình duyệt** (người dùng 09/10: nặng). Map gốc là FBX 194 MB + texture; đặt máy chỉ cần sàn và vật chắn.
- **Bản mô phỏng hình khối, SINH TỰ ĐỘNG từ map thật** bằng Blender, một lần mỗi vùng ~60 m quanh spot, cache theo sha. GLB ≈ 1–5 MB, không texture, màu theo loại. Gồm 3 lớp:
  - **sàn nhiều tầng**: lưới cao độ 0,25–0,5 m từ Đợt 1, mỗi tầng một màu, bậc thang thành dốc;
  - **khối chắn**: tường/nhà/mái thành hộp hoặc khối lồi đúng vị trí + chiều cao; cây/cột thành trụ;
  - **mốc**: tháp, nhà mái đỏ có nhãn, đạo cụ Kho có kích thước.
  - Một mặt phẳng chung là KHÔNG đủ: map nhiều tầng (lỗi shot 5).
- **Chặn lệch mô phỏng ↔ map thật:** khi sinh, so ảnh độ sâu của mô phỏng với render thật ở vài máy mẫu; lệch quá ngưỡng (vd > 0,3 m ở mép tường/sàn) thì báo, không dùng.
- **Render nền vẫn dùng map thật** ở Blender: cùng hệ tọa độ, chỉ nhận JSON camera từ Bàn đạo diễn.
- **Streamlit custom component (three.js):**
  - bản mô phỏng khối, người nộm (nhân vật, chiều cao theo hồ sơ), khối đạo cụ tỉ lệ thật (giếng bát giác Ø ~1,6 m, cao ~0,8 m);
  - camera có gizmo, độ nghiêng, FOV/ống kính; khung xem trước "Góc nhìn camera";
  - như ảnh mẫu người dùng gửi (Bàn đạo diễn web ClipAI).
- **Kiểm sống:** kéo máy là chạy 4 điều kiểm, phía trình duyệt bắn tia trên bản mô phỏng khối (nhanh vì ít đa giác), hiện ⚠ "máy ở sau tường" / "khác tầng".
- Lưu → JSON camera giống định dạng `camera_for` → render plate Blender đúng máy đó. Lưu vào thư viện chỗ đặt (theo map + spot) để dự án khác dùng lại.
- Mở từ "📐 Chọn chỗ đặt máy" với ứng viên đang chọn làm điểm xuất phát.
- **Một bối cảnh = một bàn, mỗi shot = một camera** (người dùng 09/10):
  - các shot cùng bối cảnh chung một bàn; danh sách trái "CAMERA (n)" đánh số theo shot.
  - Nút **"Sửa góc máy"** ở thẻ shot N mở bàn với **Camera N chọn sẵn**, khung xem trước = khung shot N. Bấm camera khác trong danh sách = chuyển shot.
  - Camera các shot khác hiện mờ (hình chóp) + **đường trục 180°** của cảnh; kéo vượt trục → ⚠ ngay.
  - Người nộm đứng theo blocking **của shot đang chọn**. Kéo người nộm chỉ đổi shot đó, trừ khi chọn "áp cho mọi shot".
  - Shot ở bối cảnh khác mở bàn khác (map khác).
  - Lưu camera N → chỉ render lại plate shot N (0 USD) + đánh dấu ảnh shot N "cũ"; shot khác không đổi.

## Đợt 4 — Đạo cụ trong 3D (việc (a) cũ)
- Đạo cụ quan trọng (Kho `object` có kích thước, vd giếng) được đặt khối thay thế vào cảnh Blender. Vị trí theo blocking hoặc chỗ người dùng kéo trên Bàn đạo diễn; tỉ lệ thật.
- Plate có giếng đúng chỗ, đúng tỉ lệ, nên model không tự đặt giếng.
- Mask/độ sâu của đạo cụ ghi riêng (dùng cho kiểm tỉ lệ sau).

## Thứ tự + rà
1. Đợt 0 (đo, phiên chính hoặc 1 phiên nhỏ) → báo người dùng.
2. Rà nhánh nền `ab5a905` → Đợt 1 → Đợt 2. RÀ KỸ vì đổi cache plate của mọi dự án.
3. Đợt 3. Lớn, có giao diện; làm sau khi Đợt 2 chạy thật trên #24.
4. Đợt 4.
5. Sau cùng: render lại shot 3–7 #24 → người dùng xem → sửa prompt shot 4–7 → vẽ lại (≈ 0,36 USD, báo trước).

## Câu hỏi còn mở (hỏi khi tới đợt đó)
- Bàn đạo diễn: chỉ người có quyền sửa dự án dùng, hay mọi người?
- Thư viện chỗ đặt máy: dùng chung mọi dự án cùng map hay theo dự án?
