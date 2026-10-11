# Việc giao Codex (nhánh riêng) — 10/10/2026

5 việc **thuần code + test**: không cần `data/`, khóa API, Blender hay máy chính. Làm theo thứ tự; làm được tới đâu thì
dừng ở đó, mỗi việc **một nhánh riêng** (hoặc một commit riêng nếu chung nhánh) để gộp từng phần. Phiên Claude điều phối sẽ rà theo quy ước 7
(`CLAUDE.md`), chạy cả bộ test rồi mới gộp vào `main`.

## Luật chung (áp cho cả 5 việc)

- Tách nhánh từ `main` MỚI NHẤT (`git fetch origin && git checkout -b codex/<tên-việc> origin/main`). Đặt tên nhánh `codex/...`.
- Đọc `docs/CHUAN_XAY_DUNG.md` trước. Ba luật hay vi phạm: **không im lặng khi thiếu đầu vào** (thiếu / không đo được → báo VÀNG có lý do,
  không trả "đạt"); **test đỏ trước, xanh sau** (viết test, chạy thấy đỏ, sửa, chạy thấy xanh); **không nới test cũ để che lỗi**.
- Chạy test: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider <các file test liên quan>` (Windows dùng `py`; Linux/macOS dùng
  `python3`). Chỉ chạy file liên quan, KHÔNG cần chạy cả bộ (≈ 28 phút; bên gộp chạy).
- File `.py` mới phải khai vào `devsys/areas.json` (đúng khu vực, sửa tối thiểu một dòng, giữ định dạng). **KHÔNG tăng `version`.**
  Không dùng PowerShell `Set-Content` để sửa JSON (làm hỏng dấu tiếng Việt).
- KHÔNG sửa `TODO.md`, `PLAN.md`, `PLAN.docx/pdf`. KHÔNG gọi dịch vụ tốn tiền (ClipAI, Claude API, Kling…). KHÔNG đọc/ghi `data/`.
- Comment/docstring theo phong cách file xung quanh (tiếng Việt có dấu được). Commit nhỏ; message kết thúc bằng dòng ghi công cụ của bạn.
- Xong mỗi việc: ghi ngắn vào cuối file này mục "Kết quả Codex": tên nhánh, mã commit, test đỏ→xanh (tên), việc còn mở.

---

## Việc 1 — `plate_layout_qc.compare` không được báo "khớp" khi không đo được (nhỏ)

**Vấn đề:** `core/plate_layout_qc.py:81` `compare(...)` trả `{"mismatch": False, ...}` khi không đọc được render nền (dòng ~91) hoặc ảnh
vẽ (dòng ~95). Người gọi (dòng ~182 và nơi khác — Grep `plate_layout_qc.compare` / `["mismatch"]` trong `core/`, `dashboard/`, `tools/`)
hiểu `mismatch: False` là "bố cục khớp" → lỗi im lặng (trái `CHUAN_XAY_DUNG` mục 1). Thẩm định 4 (`docs/THAM_DINH_KE_HOACH_KIEM_SOAT_2026-10-10.md`)
và chạy khô #24 ghi công cụ này "mù" khi không đo được.

**Làm:** thêm trường rõ nghĩa (vd `"measured": False` + `"muc": "vang"`, giữ `reasons`) cho mọi nhánh không đo được (đọc ảnh lỗi, không
tìm được chân trời nếu có nhánh đó); `mismatch` vẫn False để không chặn nhầm, nhưng MỌI người gọi phải hiện/ghi VÀNG "không đo được bố cục"
thay vì coi là đạt. Sửa từng người gọi cho đúng.

**Test** (`tests/test_plate_layout_qc.py` nếu có, không thì tạo): ảnh không tồn tại → `measured False`, có lý do; người gọi chính hiển thị
/ ghi VÀNG (mock). Ảnh đọc được → hành vi cũ giữ nguyên (test cũ phải xanh nguyên văn).

---

## Việc 2 — Bộ giải máy hiểu tư thế nằm `nga_ngua` / `nam` (vừa)

**Bối cảnh:** `core/shot_intent.py` `TU_THE` có `nga_ngua` (ngã ngửa chống tay) và `nam` (nằm) nhưng **chỉ dùng chạy khô**; prompt Đạo
diễn `prompts/29_director_stage_specs.md` dòng ~11–13 CHƯA cho dùng, vì bộ giải coi người nộm là trụ đứng cao H: cỡ khung
(`core/stage_solver.py:286` `sg.layer_heights(layer, H)`) và điểm ngắm tính theo chiều cao, trong khi người nằm dài ≈ H theo phương ngang →
shot toàn thân sẽ cắt người. (Phiên rà 10/10 đã chỉ ra.)

**Làm:**
- `core/stage_solver.py:48` `objects_from_blocking`: dòng ~61 đã chép `tu_the`. Với `tu_the ∈ {nga_ngua, nam}` thêm hình học thân: chiều cao
  thấp (ngã ngửa ≈ 0,45·H, nằm ≈ 0,2·H — số tạm, ghi rõ "chưa đo"; Pose 10/10 KHÔNG tách được ngồi/ngã ngửa nên đừng dựa vào đo ảnh) và
  **bề dài ngang ≈ H theo hướng `facing`** (đầu → chân), để các điểm cần lọt khung gồm cả hai đầu thân.
- `core/stage_grid.py` (`frame_eval` dòng ~635, `FRAMING` dòng 323, chỗ dùng chiều cao người ~567/631) + `_targets` / cỡ khung trong
  solver: dùng các điểm đầu–chân thật thay cho trụ đứng khi người nằm. Người đứng/ngồi/quỳ/bò: kết quả GIỮ NGUYÊN.
- Chỉ sau khi xanh: thêm `nga_ngua|nam` vào danh sách tư thế ở `prompts/29_director_stage_specs.md` dòng ~13 (một dòng, không đổi câu
  khác) và sửa `tests/test_shot_intent.py::test_tu_the_matches_prompt_29` cho khớp (prompt = TU_THE). Bỏ ghi chú "chỉ chạy khô" cạnh
  `TU_THE` và trong `knowledge/checks/L4.md`.

**Test:** `test_lying_pose_frames_full_body_length` (người `nam` ở cỡ WS: cả đầu lẫn chân trong khung); `test_nga_ngua_lower_eye_height`;
test cũ `tests/test_stage_solver.py`, `tests/test_stage_rules.py`, `tests/test_stage_facts.py`, `tests/test_shot_intent.py` xanh nguyên văn
(số đo #24 trong test không được đổi cho người đứng).

---

## Việc 3 — Bổ sung giá trị còn thiếu trong bảng loại lỗi (nhỏ)

**Vấn đề** (thẩm định / nhánh A 10/10): `devsys/error_types.json` lệch với code:
- **L9** (dòng ~40): enum khai chân trời thiếu `horizon_not_visible`, trong khi `core/stage_facts.py:337` có (và dòng ~288 xử lý nó).
- **L8** (dòng ~36): enum cỡ cảnh thiếu `GAME_TPS`, trong khi `core/stage_grid.py:323` `FRAMING` và `core/shot_intent.py:19` `CO` có.
- **L12** (dòng ~52): thời gian chỉ có ngày/đêm; thêm bình minh / hoàng hôn (`binh_minh`, `hoang_hon` hoặc theo cách đặt tên enum đang
  dùng ở file) — kiểm `core/shot_intent.py` (nhóm "Nơi chốn": thời gian) có enum tương ứng không; nếu chưa có thì thêm cả ở đó + validate.

**Làm:** sửa JSON tối thiểu (giữ định dạng dòng), cập nhật `knowledge/checks/L8.md`, `L9.md`, `L12.md` cho khớp enum. Thêm test hợp đồng
(trong `tests/test_devsys_stages.py` hoặc `tests/test_knowledge_checks.py`): enum khai L9 ⊇ tập observe chân trời của `stage_facts`; enum
cỡ L8 ⊇ `stage_grid.FRAMING`. Đỏ trước (với JSON cũ), xanh sau.

---

## Việc 4 — Nhánh C (V8) phần SCHEMA: sơ đồ bối cảnh khối + kiểm bằng số (vừa–lớn, thuần Python)

**Đặc tả:** `docs/PHUONG_PHAP_SAN_KHAU_3D.md` mục **12b** (đọc cả mục) + mục 2 (hệ tọa độ, lưới) + dòng V8 ở mục 10. Chỉ làm phần Python
thuần — KHÔNG dựng Blender, KHÔNG gọi Claude, KHÔNG nối vào luồng (chưa cờ).

**Làm:** module mới `core/blockout.py`:
- `validate(plan) -> list[issue]` cho sơ đồ Đạo diễn khai: `san` (kích thước vùng diễn), `khoi[]` `{id, loai ∈ {tuong, bac, cot, hop, tru,
  cua, lan_can, mai, cay_khoi, xe_khoi}, tam [x, y] (m, theo lưới mục 2), kich_thuoc [dai, rong, cao] mỗi số là KHOẢNG [min, max] + nguon
  ∈ {kho, vat_quen, anh}, huong (độ), mo_ta_ngan, vat_kho (tùy chọn)}`, `loi_mo[]`, `huong_sang`. Enum sai / thiếu trường / số âm / khoảng
  ngược → issue ĐỎ có `path` + lý do (không im lặng; theo kiểu `_issue` của `core/shot_intent.py`).
- `check_geometry(plan, cho_dung=[...], vat_kich_ban=[...]) -> list[issue]` (12b.1 a, b, d): khối chồng lấn vô lý (giao hộp chân đế >
  ngưỡng, trừ loại được phép chồng như `mai` trên `tuong` — ghi rõ bảng cho phép); chân khối không chạm sàn; **lối đi ≥ 0,8 m** giữa các
  khối quanh chỗ đứng kịch bản; chỗ đứng kịch bản nằm trên sàn trống; **mọi vật kịch bản nhắc tới có khối** (so `vat_kich_ban` với `vat_kho` /
  `mo_ta_ngan`, so khớp chính xác không bỏ dấu — bài học 'van' khớp 'vàng'); kích thước lệch Kho/vật quen > ±20 % → VÀNG.
- `to_props(plan)` → danh sách khối ở dạng mà `tools/render_plates.py:572` `add_props(specs)` nhận (đọc hàm đó để khớp khóa) — chỉ chuyển
  dữ liệu, không gọi Blender. Lấy giữa khoảng.
- (Phần 12b.1 c — chiếu ngược vào ảnh — và 12b.2 lưu Kho: KHÔNG làm, ghi "việc mở".)

**Test** `tests/test_blockout.py`: sơ đồ hợp lệ → 0 issue; mỗi loại lỗi một ca (enum sai, thiếu trường, chồng lấn, lơ lửng, lối đi 0,6 m,
chỗ đứng trong khối, vật kịch bản thiếu khối, kích thước lệch 30 %); `to_props` ra đúng khóa `add_props`. Thêm 2 ca hồi quy vào
`tests/golden/cases/` theo `tests/golden/README.md` (thiếu khối cho vật kịch bản nhắc; khối chồng lấn) với `chua_co_lop`/lớp chạy đúng luật
README.

---

## Việc 5 — Dọn cảnh báo Pillow `getdata` (rất nhỏ)

`Image.getdata` sẽ bị bỏ ở Pillow 14 (cảnh báo hiện trong mọi lần chạy cả bộ). Thay bằng cách tương đương không cảnh báo (vd
`get_flattened_data()` nếu Pillow cài sẵn có, hoặc `numpy.asarray(img)` / `img.tobytes()`; kiểm phiên bản Pillow trong môi trường) ở:
`tests/test_end_popup_p24.py:118`, `tests/test_dialogue_take.py:50`; Grep thêm `getdata(` trong `core/`, `tools/`, `tests/`. Kết quả số phải
giữ nguyên (test xanh như cũ, không còn `DeprecationWarning` getdata: chạy với `-W error::DeprecationWarning` cho riêng các file đó).

---

## Kết quả Codex

(Codex ghi ở đây: việc · nhánh · commit · test đỏ→xanh · việc mở.)

- Việc 1 · `codex/tasks-20261010` · `30e72bb` · đỏ 5 ca thiếu measured/diag báo đạt → xanh **83 test**, gồm `test_plate_layout_qc`, `test_camera_plan_g0`, `test_stage_facts`. Người gọi duy nhất `check_job` → runner diag đã báo warn; không đổi key UI. Còn mở: ngưỡng QC chưa hiệu chỉnh trên ảnh thật; không thử dữ liệu thật/API.

- Việc 2 · `codex/tasks-20261010` · `f6fb193` · 7 ca đỏ (`test_lying_pose_frames_full_body_length`, `test_nga_ngua_lower_eye_height`) → **123 test xanh**, giữ nguyên test cũ solver/rules/facts/grid/director/plate-camera. Cảnh toàn thân dùng tâm đoạn đầu–chân, đo bao ngang/cao; POV và cỡ chặt dùng mắt thấp. Prompt = TU_THE sau khi hình học xanh. Rà: chỉ nhánh lying đổi hình học; tư thế khác giữ số cũ. Còn mở: cao 0,45H/0,2H là tạm chưa đo; chưa thử render Blender/ảnh thật.

- Việc 3 · `codex/tasks-20261010` · `e5aeb33` · 3 hợp đồng enum đỏ (L9 observe, L8 FRAMING, L12 thời gian BYĐ) → **55 test xanh** knowledge/devsys-stages/shot-intent. THOI_GIAN đã có dawn/day/dusk/night + validate, không thêm enum trùng; khai L12 dùng binh_minh/hoang_hon. Điều chỉnh assertion tài liệu L4 chỉ-chạy-khô đã lỗi thời sau việc 2, giữ kiểm đủ TU_THE + nhãn chưa đo. Còn mở: các lớp khai vẫn chưa nối/chưa hiệu chỉnh như trạng thái cũ.

- Việc 4 · `codex/tasks-20261010` · `72d1fd5` · đỏ thiếu module + 4 hợp đồng add_props bị bỏ qua → **90 test xanh** blockout/devsys-stages/decisions/plates/plate-camera. `blockout`: schema issue ĐỎ có path; hộp chân đế xoay, giao >2% + cao >5 cm, sàn/chỗ đứng/lối ≥0,8 m, tên/mã chính xác có dấu, cỡ lệch >20% hoặc thiếu số chuẩn VÀNG. Mái chỉ chạm đỉnh tường/cột/trụ. Theo chốt người dùng mở rộng tối thiểu add_props box/cylinder (test AST mock bpy), giữ giếng cũ. Hai ca golden có lớp test chạy + d97 bat:false, không nối vào khâu. Không tăng areas.version. Còn mở: chiếu ảnh 12b.1c, duyệt/lưu Kho 12b.2, sàn nhiều cao độ/chỗ đứng trên bậc, nhãn nhìn thấy trên tấm duyệt, render Blender thật + nghiệm thu ≥3 bối cảnh; các ngưỡng khối là tạm, kiểm giữa khoảng.

- Việc 5 · `codex/tasks-20261010` · `0c4fafe` · Pillow 12.3.0: bật -W error::DeprecationWarning làm đỏ **4 ca** popup/mark/hash (hash cũ nuốt cảnh báo thành thiếu số). Thay bằng byte L/RGB cùng thứ tự, giữ nguyên mọi assertion/ngưỡng cũ → **17 test xanh** trên 3 file với cảnh báo thành lỗi. rg core/tools/tests không còn getdata(. Không dùng get_flattened_data để giữ tương thích Pillow cũ. Còn mở: cả bộ do Claude chạy trước gộp, không chạy API/dữ liệu thật.

- Bàn giao cuối 10/10: **260 test liên quan gộp qua (18,77 giây)** + **17 test Pillow qua với -W error::DeprecationWarning**. Đã tự rà diff theo skill 2b.5: không đổi key widget, không nới ngưỡng/assertion cũ, chỉ cập nhật hợp đồng pose theo yêu cầu; không chạm TODO/PLAN/data/API, không tăng areas.version, không bật cờ/luồng mới. Nhánh đã push, chưa gộp main; Claude rà và chạy cả bộ trước gộp. Tìm GitHub theo yêu cầu: MCP thực thi https://github.com/ahujasid/mcp-for-blender, mã nguồn Blender chính thức https://github.com/blender/blender; skill tham khảo https://github.com/arjun988/blender-skills (modeler/environment) và https://github.com/kajisho5/blender-skill (headless). Chỉ đọc tài liệu, chưa cài/chạy hay xác minh chất lượng dựng.

- Rà độc lập + vòng sửa 10/10 (nhánh `claude/codex-fix-1010`, Claude): (1) người `nam`/`nga_ngua` thiếu `facing` → ValueError trong
  `stage_solver.objects_from_blocking` (Đạo diễn nhận SchemaError, gọi lại) thay vì nổ lúc `solve_scene`; (2) **HOÃN** mở `nam`/`nga_ngua`
  trong `prompts/29_director_stage_specs.md` (trả về như main; giữ code solver) — test hợp đồng `test_tu_the_matches_prompt_29` chặn tới khi
  xong; (3) `plate_layout_qc`: render sáng không chân trời nhưng có F1 → `measured True`, `partial True` ("đo được một phần").
  **Việc mở:** (a) `tools/stage_grid.py` dựng người nộm NẰM (xoay theo `facing`, cao `body_height`, dài `body_length`; chữ ký nhịp dòng ~1247
  thêm `tu_the`) → rồi mới mở `nam|nga_ngua` ở prompt 29 + gỡ assertNotIn trong test; (b) `blockout.to_props` trả `at` theo tọa độ SÂN KHẤU,
  chưa đổi sang tọa độ scene như giếng (`sg.model_from_rel`, apply_v4.py:104); (c) `core/stage_facts.STAND_IN_KINDS` chưa có `"block"`.

---

# ĐỢT 2 — việc giao Codex (10/10 tối, người dùng duyệt cả 4 việc)

Luật chung GIỐNG đợt 1 (mục "Luật chung" đầu file) + thêm:
- Tách nhánh từ `main` MỚI NHẤT; **mỗi việc một nhánh** `codex/d2-viec<N>-<tên>` (việc 1 + 2 gộp một nhánh được — cùng vùng).
- **KHÔNG đụng** `core/identity_declare.py`, `tools/dryrun_k0b_p24.py`, `tools/nhan_bao_nham_a18.py`, `docs/NHAN_BAO_NHAM_A18*` (Claude
  đang sửa A18 trên nhánh `a18-sua-bao-nham`). Không sửa `dashboard/` (việc 4 chỉ làm mockup + nghiên cứu).
- Việc có Blender: KHÔNG chạy Blender thật — test bằng mock `bpy` / kiểm AST như test `add_props` đợt 1 (`tests/test_plates_f2.py` hoặc
  nơi bạn đã viết ở việc 4 đợt 1). Bên gộp sẽ render thật để nghiệm thu.
- Ghi kết quả vào mục "Kết quả Codex — đợt 2" cuối file.

## Việc 1 — Người nộm NẰM trong sân khấu Blender + mở lại tư thế nằm cho Đạo diễn (vừa)

**Vấn đề** (rà 10/10, việc mở (a) đợt 1): solver đã tính thân nằm (`core/stage_solver.py` `objects_from_blocking`: `body_length`,
`body_height`, bắt buộc `facing`) nhưng `tools/stage_grid.py` dựng người nộm là TRỤ ĐỨNG cao `o["H"]` (dòng ~1251 `"height": o["H"]`;
hàm dựng trụ quanh dòng ~284–300) và không biết `tu_the`; chữ ký nhịp dòng ~1247 thiếu `tu_the` nên 2 tư thế cùng chỗ cùng H bị gộp.
Vì vậy prompt 29 đang HOÃN `nam`/`nga_ngua` (test chặn: `tests/test_shot_intent.py` ~dòng 41–52, `knowledge/checks/L4.md`,
chú thích `core/shot_intent.py` dòng ~26–27).

**Làm:**
1. `tools/stage_grid.py`: người có `tu_the ∈ {nam, nga_ngua}` → người nộm NẰM: dài `body_length`, cao `body_height` (nga_ngua thân
   nghiêng chống tay — đơn giản: hộp/trụ nghiêng theo `body_height/body_length`), xoay theo `facing` (hướng đầu → chân, cùng quy ước
   solver — đọc `core/stage_grid.lying_point`), tâm = điểm solver dùng (`anchor_point`/`lying_point`) để số bắn tia / render khớp solver.
   Người đứng/ngồi/quỳ/bò GIỮ NGUYÊN số cũ (test hồi quy so số cũ).
2. Thêm `tu_the` vào chữ ký nhịp (dòng ~1247).
3. Mở lại prompt `prompts/29_director_stage_specs.md` dòng `tu_the` cho `nga_ngua`, `nam` (đúng như bản Codex đợt 1 commit `f6fb193`
   trước khi bị hoãn); gỡ test chặn tạm + chú thích hoãn ở `core/shot_intent.py`, `L4.md`; thay bằng test hợp đồng: prompt 29 liệt kê đủ
   `shot_intent.TU_THE` VÀ `tools/stage_grid.py` có nhánh dựng nằm.
**Test (đỏ → xanh):** mock bpy: người `nam` facing 90° → khối nằm ngang dài ≈ body_length, cao ≈ body_height, trục dài theo facing;
`nga_ngua` nghiêng; người đứng không đổi; chữ ký nhịp khác nhau khi chỉ khác `tu_the`; hợp đồng prompt 29 ↔ TU_THE.
**Lưu ý:** đổi prompt 29 = đổi hành vi Đạo diễn thật (lời gọi Claude tốn tiền) → ghi rõ trong "Kết quả" để bên gộp rà kỹ.

## Việc 2 — Khối nhánh C dùng được như khối thay thế (nhỏ)

**Vấn đề** (việc mở (b)(c) đợt 1): `core/blockout.py:214` `to_props` trả `at` theo tọa độ SÂN KHẤU, còn giếng đi qua
`core/stage_grid.py:101` `model_from_rel` (xem `tools/experiments/stage_v2_p24/apply_v4.py` ~dòng 104) để ra tọa độ scene;
`core/stage_facts.py:29` `STAND_IN_KINDS = {"well"}` chưa có `"block"` (dòng ~188 bỏ qua mọi kind khác) → không có câu sự thật "khối
thay thế = vật thật" cho khối nhánh C (12b.3 yêu cầu áp `stand_in` cho MỌI khối).
**Làm:** `to_props(plan, stage=None)`: có `stage` → đổi `at` qua `model_from_rel` (giữ hành vi cũ khi `stage=None`, có test); thêm
`"block"` vào `STAND_IN_KINDS` + câu sự thật dùng `mo_ta_ngan`/`vat_kho` của khối (đọc cách giếng sinh câu ở `stage_facts`).
**Test:** to_props có/không stage; stage_facts sinh câu stand_in cho block; giếng không đổi (test cũ xanh).

## Việc 3 — Nhánh C bước 12b.2: tấm duyệt sơ đồ khối + lưu bản `blockout` (vừa–lớn)

**Đặc tả:** `docs/PHUONG_PHAP_SAN_KHAU_3D.md` mục **12b.2** (đọc cả 12b). Thuần Python, chưa nối Dashboard, chưa bật cờ (thêm id quyết
định `bat:false` trong `devsys/decisions.json` như d97).
**Làm:** module mới (vd `core/blockout_sheet.py`):
1. `render_top_view(plan, cho_dung=[...], out_png)`: ảnh nhìn từ trên bằng PIL (hoặc matplotlib nếu đã có trong môi trường — kiểm
   `requirements`/import, KHÔNG cài thêm gói): lưới mục 2 có tên ô, khối có nhãn `id · loai · kích thước giữa khoảng`, chỗ đứng kịch bản,
   hướng sáng, issue của `check_geometry` tô màu (ĐỎ/VÀNG). Đường dẫn ra là tham số (không ghi `data/`).
2. `to_location_pack(plan, nguoi_duyet, phien_ban)` → dict dạng `location_pack` kiểu `blockout` (có `phien_ban`, `nguoi_duyet`,
   `ngay`, `issues` lúc duyệt, sha của plan) + `from_location_pack` đọc lại; plan có issue ĐỎ → từ chối đóng gói (raise, không im lặng).
   Đọc `core/` xem `location_pack` hiện có dạng gì (Grep `location_pack`) để không đụng khóa cũ; nếu chưa có thì định nghĩa schema mới
   trong module + ghi vào "Kết quả".
3. (2–3 góc clay có nhãn: KHÔNG làm — cần Blender; ghi việc mở.)
**Test:** ảnh ra đúng kích thước, có đủ nhãn khối (kiểm bằng dữ liệu vẽ trả về, không OCR); khối ĐỎ được tô; đóng gói / đọc lại khứ hồi;
plan có ĐỎ bị từ chối; sha đổi khi plan đổi. Khai file mới vào `devsys/areas.json`.

## Việc 4 — Mockup màn Video 3 cột + NGHIÊN CỨU tối ưu giao diện (vừa; KHÔNG sửa `dashboard/`)

**Nguồn:** `docs/GHI_CHU_GIAO_DIEN_SO_FATEBREAKER_2026-10-10.md` trên nhánh `ghi-chu-giao-dien-fatebreaker` (`git show
origin/ghi-chu-giao-dien-fatebreaker:docs/GHI_CHU_GIAO_DIEN_SO_FATEBREAKER_2026-10-10.md`) — so sánh FateBreaker ↔ Dashboard, 5 đề xuất,
3 điều KHÔNG chép (prompt thô làm trung tâm — trái A13; bỏ stepper; giấu tiền). Mockup hiện có: `mockup/dashboard_v2_4man.html`
(phong cách UI v2 — giữ token màu/cỡ chữ 12,5 px của nó).
**Làm:**
1. `mockup/video_3cot.html` (HTML tĩnh, dữ liệu giả, không gọi mạng): trái = tham chiếu của shot (nhân vật/bối cảnh/đạo cụ, ảnh nhỏ)
   + checklist 3–4 dòng có chấm trạng thái; giữa = khung đầu + **gói gửi dạng ảnh nhỏ + vai** (`@image1 = Kelly · nhận diện`…, tương ứng
   `jobs.sent_package` K1a) + một dòng tiếng Việt + nút (KHÔNG hiện prompt thô mặc định, có "Xem prompt" thu gọn); phải = trình xem clip +
   **dải phiên bản V1…Vn** có trạng thái + "đang dùng"; dưới = dải phim các shot; tiền ước tính trên mọi nút tốn tiền; giữ stepper 1–4 trên đầu.
   Thêm `mockup/kho_nguon_dich.html`: thẻ Kho ghép đôi ảnh mẫu ↔ mô tả / `khai_bao_chu`, nhãn lệch (R1).
2. **Nghiên cứu tối ưu giao diện hơn nữa** → `docs/NGHIEN_CUU_TOI_UU_GIAO_DIEN_2026-10-11.md`: (a) đo trên mockup và trên Dashboard thật
   (đọc code `dashboard/` + `tests/test_ui_v2_acceptance.py`, không chạy Dashboard): số lần bấm từ "dự án mới" → "video đầu", số lần cuộn
   để duyệt 9 shot, mật độ (shot / màn 1440×900); (b) tham khảo các công cụ dựng/AI video công khai (vd Runway, Kling web, CapCut, DaVinci
   Resolve, Premiere, Frame.io, ComfyUI…) — chỉ nêu MẪU tương tác (dải phiên bản, so cạnh nhau, phím tắt, duyệt hàng loạt, xem trước khi
   rê chuột), dẫn nguồn URL, không chép nội dung; (c) giới hạn của Streamlit cho bố cục 3 cột / dải phim (st.columns, fragment, component
   tùy biến) + cách làm khả thi; (d) đề xuất xếp hạng theo giá trị / công sức, mỗi đề xuất ghi file Dashboard dự kiến đụng + rủi ro test UI.
**Không:** sửa `dashboard/`, thêm gói phụ thuộc, gọi API.

## Kết quả Codex — đợt 2

| Việc | Nhánh | Commit | Bằng chứng / việc mở |
|---|---|---|---|
| 1 | `codex/d2-viec1-2-san-khau` | `08d3e47` | 8 test mới đỏ → xanh; nhóm 172 test xanh (Windows). Rà diff + rà lại prompt: giữ số dựng đứng; thân nằm theo facing, bao hình và đầu theo solver. **Prompt 29 đổi hành vi Director thật**, cần bên gộp rà kỹ và render Blender thật (phiên này chỉ bpy giả, chưa API). |
| 2 | `codex/d2-viec1-2-san-khau` | `38c4d49` | 3 test đỏ → xanh; cùng nhóm 172 test. Rà: stage=None giữ số cũ; stage dùng model_from_rel; tên/mã Kho giữ nguyên có dấu; khối không bị ép vật liệu đá; giếng qua hồi quy. Chưa nối pipeline mới. |
| 3 | `codex/d2-viec3-tam-duyet` | `163f378` | Test đỏ import module thiếu → 71 test liên quan xanh trên Windows; kiểm PNG bằng mắt. Rà diff: module thuần PIL đã có requirements; schema mới `kind=blockout`, `schema_version=1`, không đụng `assets.profile.model3d`; SHA canonical, copy dữ liệu, từ chối geometry ĐỎ, giữ VÀNG. d101 tắt, chưa nối pipeline. |
| 4 | `codex/d2-viec4-mockup-video` | `fb51e24` | 4 test mockup đỏ → xanh; nhóm cùng UI acceptance **8 test xanh**, phép đo AppTest 12 click + 2 nhập (mock, job running). Rà: giữ stepper/giá/A13, ảnh và vai gói gửi, 9 shot, phiên bản có trạng thái/đang dùng, Kho nguồn cạnh khai_bao_chu và R1; toàn bộ SVG/JS offline. Không đổi Dashboard/key widget; areas.version giữ. |

Không đổi TODO/PLAN/data, không chạy Blender/API, không tăng areas.version. Cả bộ do bên gộp chạy theo luật ĐỢT 2.

Việc mở: 2–3 góc clay/ảnh tham chiếu cần bên gộp làm bằng Blender; chưa ghi Kho thật. Tấm kiểm chỗ đứng theo tham số; gói hiện duyệt geometry của plan, chưa lưu chỗ đứng/kịch bản ngoài plan. Sơ đồ nhiều issue có nhãn báo phần còn lại và trả đủ issues. Không gọi API/Blender, không đổi TODO/PLAN/data, không tăng areas.version; cả bộ do bên gộp chạy.

Báo cáo `docs/NGHIEN_CUU_TOI_UU_GIAO_DIEN_2026-10-11.md` dẫn nguồn chính thức, phân biệt đo AppTest với ngân sách CSS; **chưa đo cuộn pixel bằng browser**, chưa chạy Dashboard/media/API thật. Code hiện đã 3 thẻ mỗi hàng và chip phiên bản, không lấy mô tả UI cũ làm baseline. Mockup chỉ mô phỏng, cần người duyệt trước triển khai. Cả bộ test do bên gộp chạy theo đề bài.


---

# ĐỢT 3 — AI Dev System nắm TOÀN BỘ kế hoạch + việc đang chạy (10/10 tối, người dùng duyệt)

**Vấn đề:** AI Dev System (web cổng 8502, `devsys/`) chỉ nắm kế hoạch S (`devsys/plan_progress.py` `PLAN_FILE` =
`docs/KE_HOACH_SUA_SAU_DU_AN_8.md`), `TODO.md` và sổ khâu K0a. KHÔNG thấy: tiến độ kế hoạch kiểm soát K0a–K8
(`docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md` mục 8, bảng dòng ~342–352 cột đợt có ✅/🟡; chốt A1–A26 mục A), điểm thẩm định cổng
A21 (`docs/THAM_DINH_KE_HOACH_KIEM_SOAT_2026-10-10.md` các mục "# Lần N"), việc giao Codex (file này), nhánh/worktree chưa gộp, kế hoạch
sân khấu 3D (`docs/PHUONG_PHAP_SAN_KHAU_3D.md`), ghi chú UI (nhánh `ghi-chu-giao-dien-fatebreaker`). `devsys/workflow.py:79` chỉ nhận mã
dạng `S14.45` → lượt K0b / Codex không ghi được số đo.

Luật chung GIỐNG đợt 1 + thêm: nhánh `codex/d3-viec<N>-<tên>`; KHÔNG sửa `TODO.md`; mọi số do CODE tính từ file/git (không ai tự khai);
đọc file không được → hiện "không đọc được: <lý do>" (không im lặng, không 0 %); KHÔNG đụng vùng A18 (xem đợt 2). Test trang web: theo
cách `tests/test_devsys.py` / `tests/test_devsys_v2.py` đang làm (2 file này có nhãn `slow` — chạy `-m slow` cho riêng chúng một lần
trước bàn giao). Đổi `devsys/` → bên gộp khởi động lại cổng 8502.

## Việc 1 — Sổ kế hoạch + tiến độ kế hoạch kiểm soát (vừa)
1. `devsys/plans.json` (mới): danh sách MỌI kế hoạch đang sống — `{id, ten, file, kieu ∈ {viec_s, dot_bang, codex, ghi_chu, phuong_phap},
   trang_thai ∈ {dang_chay, cho, xong, chua_lam}, ghi_chu}`; điền sẵn: kế hoạch S, kế hoạch kiểm soát, thẩm định, CODEX_TASKS (đợt 1–3),
   sân khấu 3D, ghi chú UI (file trên nhánh → `nhanh` + `file`). Test hợp đồng: mọi `file` tồn tại (hoặc nhánh có trong `git branch -r`).
2. `devsys/plan_progress.py` (hoặc module mới `devsys/plans.py`): đọc bảng đợt mục 8 kế hoạch kiểm soát → mỗi đợt K0a…K8: trạng thái
   (✅ / 🟡 / chưa), mã commit trích được, thứ tự theo `devsys/stages.py:24` `DOT`; % = ✅ / tổng (🟡 = ½). Đọc mục A → số chốt (A1…An)
   + chốt mới nhất. Không phá API cũ của `plan_progress` (trang 📋 và `tools/plan_progress.py --write` giữ nguyên kết quả — test hồi quy).
3. Trang 📋 "Kế hoạch đang chạy" (`devsys/app.py:870` `page_plan`): thêm khối "Mọi kế hoạch" (bảng từ plans.json + % tính được) và khối
   "Kế hoạch kiểm soát K0a–K8" (thanh đợt, đợt hiện tại = `devsys/stages.json` `dot_hien_tai`, cảnh báo nếu lệch với bảng mục 8).

## Việc 2 — Trang "Đang chạy": nhánh, worktree, việc giao (vừa)
Trang mới (thêm vào `PAGES` `devsys/app.py:1123`): đọc `git branch -r --no-merged origin/main`, `git worktree list --porcelain`,
`git log -1` mỗi nhánh → bảng: nhánh, của ai (tiền tố `codex/` = Codex, `worktree-agent-*` / `claude/*` = Claude, khác = người), commit
cuối + ngày, số commit chưa gộp, file đổi (`--stat` gọn), đã rà chưa (tìm "rà" / "Rà" trong message commit hoặc mục "Kết quả Codex" của file
này nhắc tên nhánh). Thêm bảng "Việc giao Codex": parse các mục `## Việc N` theo từng `# ĐỢT` + mục "Kết quả Codex — đợt N" → mỗi việc:
đã có kết quả chưa, nhánh, commit. Git chạy lỗi / không có git → báo rõ. Test: repo git tạm (tmp_path) có 2 nhánh chưa gộp + 1 worktree;
file CODEX_TASKS mẫu.

## Việc 3 — Thẻ cổng điểm A21 (nhỏ)
Parse `docs/THAM_DINH_KE_HOACH_KIEM_SOAT_2026-10-10.md`: mỗi tiêu đề `# Lần N …` lấy điểm kế hoạch + build (mẫu chữ: "kế hoạch **x / 10**",
"build **y / 10**"; lần 1–3 có cách ghi khác — đọc file, viết bộ parse chịu được từng dạng, ca nào không đọc được → ghi "không đọc được").
Hiện ở trang Tổng quan: đường điểm theo lần so với vạch 8,5 + "ĐẠT/CHƯA ĐẠT" + lỗ hổng còn lại (số mục dưới "Lỗ hổng còn lại" của lần
mới nhất). Test: file mẫu đủ 5 dạng tiêu đề.

## Việc 4 — `devsys.workflow` nhận mã ngoài S (nhỏ)
`devsys/workflow.py:79`: nhận thêm mã đợt kế hoạch kiểm soát (`K0b`, `K1a`…, có thể kèm hậu tố `-<chữ>` vd `K0b-TD5`) và mã Codex
(`CX-d2-1` …); giữ kiểm chặt (không nhận chuỗi tùy ý), cập nhật docstring + trang "Hiệu quả quy trình" lọc/nhóm theo loại mã. Test: mã cũ
S14.45 vẫn nhận; mã mới nhận; mã rác bị từ chối với lý do.

## Kết quả Codex — đợt 3

| Việc | Nhánh | Commit | Bằng chứng / việc mở |
|---|---|---|---|
| 1 | `codex/d3-viec1-so-ke-hoach` | `de1dc4a` | Đỏ thiếu module + ca kết quả gạch đầu dòng/registry null → xanh 6 test mới; hồi quy nhóm 68 test thường (trước ca thứ 6), 2 test slow của test_devsys/test_devsys_v2 xanh. Rà: API plan_progress cũ không đổi; % K theo DOT và dấu đầu tiên (không lấy trạng thái lịch sử), thiếu nguồn/đợt không 0%; chốt A đọc đúng mục A; git nhánh chỉ đọc, không API. |
| 2 | `codex/d3-viec2-dang-chay` | `ed0c445` | Đỏ thiếu module → 3 test repo Git tạm/parse kết quả xanh; nhóm 66 test thường + 2 test slow devsys xanh. Rà: chỉ git đọc, timeout, lỗi Git/đọc báo rõ; nhánh/worktree không bị đổi; tách kết quả checkout và nhánh chưa gộp. Nguồn rà là message hoặc kết quả nhắc nhánh, KHÔNG coi là rà độc lập. |
| 3 | `codex/d3-viec3-cong-a21` | `c6b867c` | Đỏ thiếu module + ca danh sách inline/hỏng → 7 test mới xanh; nhóm 69 test thường (trước ca thứ 7) + 2 test slow devsys xanh. Rà: điểm thiếu/ngoài 0–10 không thành 0; lần 1 lấy tổng, lần 2 lấy tiêu đề, lần 3 build K0a; không lấy điểm ước tương lai; danh sách lỗ hổng hỏng không báo 0. |
| 4 | `codex/d3-viec4-ma-quy-trinh` | `4122f17` | 13 ca đỏ trước sửa; giữ tương thích F1.1 sau hồi quy; 106 passed, 2 deselected (không slow); riêng giao diện slow 2 passed, 63 deselected; kiểm lại workflow sau rà: 43 passed · Claude chạy cả bộ và gộp; khởi động lại 8502 sau tích hợp. |

Sổ 8 kế hoạch, nguồn ghi chú UI đọc bằng git show nhánh. % Codex theo kết quả trong checkout: nhánh chưa gộp chưa xuất hiện trong main là 0 hợp lệ, trang Đang chạy sẽ theo dõi nhánh riêng. TODO/PLAN/data không đổi; areas.version giữ, bên gộp chạy cả bộ và khởi động lại 8502. Nhánh độc lập từ main 7764122.

Số đọc thực tại lúc kiểm: 7 nhánh chưa gộp, 126 worktree, 13 việc giao, 5 kết quả nhánh chưa gộp; số thay đổi theo Git, không ghi cứng UI. Các refs chỉ cập nhật sau fetch của người dùng, trang không tự fetch. Không sửa TODO/PLAN/data, không API, areas.version giữ; bên gộp chạy cả bộ/restart 8502. Nhánh độc lập từ main 7764122.

Nguồn main cập nhật `e457c09` đã có lần 6: KH 8,4 / build 8,5 → CHƯA ĐẠT, 6 lỗ hổng theo bản thẩm định. Đã hỗ trợ dạng `(1)…(6)` và không đếm phần “Đã sửa ngay”; sửa xong vẫn cần thẩm định lần 7, không tự nâng điểm/trừ số. Không sửa TODO/PLAN/data/API; areas.version giữ; bên gộp chạy cả bộ/restart 8502.

Rà diff: giữ key widget cũ, thêm `flow_task_kinds`; không sửa Dashboard, dữ liệu thật hay version areas; kiểm mã bằng fullmatch, lỗi đọc file hiện lý do. Mã K lấy từ stages.DOT; mã kế hoạch cũ có số vẫn đọc được, mã tùy ý bị từ chối. Không gọi API.

---

# ĐỢT 4 — rà K3 + test chập chờn + đo thời gian test (10/10 khuya, người dùng duyệt cả 3 việc)

Luật chung GIỐNG đợt 1 (mục "Luật chung" đầu file) + thêm:
- Nhánh `codex/d4-viec<N>-<tên>`. Việc 1 tách từ `origin/k3-ra-sua` (KHÔNG từ `main`); việc 2–3 tách từ `origin/main` mới nhất.
- KHÔNG đụng nhánh Codex đợt 2–3 đang chờ gộp; KHÔNG sửa `dashboard/`; KHÔNG chạy Blender/API; KHÔNG đọc/ghi `data/`.
- Phiên Claude lúc 00:24 11/10 sẽ KHÔNG mở phiên rà K3 nữa — chờ kết quả việc 1 của Codex rồi rà diff + gộp.
- Ghi kết quả vào mục "Kết quả Codex — đợt 4" cuối file.

## Việc 1 — Rà kỹ lớp kiểm video TRƯỚC gen K3 (vừa; RÀ + sửa lỗi tìm thấy)

**Bối cảnh:** `core/video_pregen.py` `check(conn, scene_id, plan)` 6 mục, nối vào `core/runner.py` (~:371 trước SPEND_LOCK +
`VideoRunner._pregen` ~:728), cờ `video_pregen` mặc định TẮT (ĐỎ → job giữ `queued` + WAIT_REASONS + chẩn đoán `video_pregen_hold`;
VÀNG → gửi + chẩn đoán). `_build_package` được tách ra từ `_write_sent_package` (`core/sent_package.py`). Nhánh gốc
`k3-video-truoc-gen` (`d2b80d5`); phiên rà trước đã sửa điểm (2) — job ĐỎ không dựng lại request mỗi nhịp (`080360a` trên
`k3-ra-sua`). 49 test `tests/test_video_pregen.py` + `tests/test_sent_package.py` đang xanh.

Đọc `git diff origin/main...origin/k3-ra-sua` + chỗ gọi tới, rà 4 điểm còn lại:
1. **Cờ TẮT → đường gửi y hệt `main`** sau khi tách `_build_package` (gói `sent_package` từng byte giống, thứ tự ghi sổ chi / external_id
   không đổi). Chứng minh bằng test so gói trước–sau trên cùng job giả.
2. **Multi-shot (nhóm nhiều shot một lần gen) mà shot đầu ĐỎ** → follower kẹt mãi, bị gửi lẻ, hay được giữ cùng nhóm có lý do hiện ra?
3. **Lỗi đọc tệp** (khung đầu/cuối, video ref mất / hỏng) chỉ chặn ĐÚNG shot đó, không làm nổ cả vòng runner hay chặn job khác.
4. **`_submit_kwargs`** (upload ảnh Kho chủ thể lên ClipAI): lớp kiểm có chạy TRƯỚC mọi upload/lời gọi tốn tiền không; ĐỎ thì không
   upload gì.

Mỗi lỗi: test đỏ → sửa → xanh, commit riêng. Không lỗi: ghi "đã rà, không lỗi" + test chứng minh (nếu thêm). Báo cáo trong mục kết quả:
lỗi (mức cao/trung/thấp, `file:dòng`), commit, test.

## Việc 2 — Test chập chờn `test_director_byd` (nhỏ)

`tests/test_director_byd.py::FlagOffTests::test_off_run_makes_no_extra_call...` hỏng 1 lần khi chạy CÙNG `tests/test_byd_fill.py` +
`tests/test_devsys.py`, chạy lại đều qua → nghi rò cờ (`shot_intent`, `core/flags`) / biến môi trường / cache module giữa test. Tìm
nguồn rò (thử đổi thứ tự: `-p no:randomly` nếu có, hoặc chạy ghép từng cặp), sửa ở chỗ dọn (fixture/tearDown/patch đúng phạm vi) —
KHÔNG nới assert. Bằng chứng: chạy bộ ba file ghép ≥ 5 lần liền đều xanh (ghi lệnh + kết quả).

## Việc 3 — Đo lại thời gian test (rất nhỏ, chạy lâu)

Chạy cả bộ một lần: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider --durations=30 -rf` (≈ 28 phút). Đối chiếu danh sách `slow` trong
`conftest.py` (test ≥ ~8 s): thêm id mới chậm, bỏ id không còn chậm/không tồn tại; giữ `tests/test_slow_marker.py` xanh. Ghi bảng 30 test
chậm nhất (id · giây) + tổng thời gian + số test hỏng (nếu có, liệt kê tên — KHÔNG sửa test ngoài phạm vi, chỉ báo).

## Kết quả Codex — đợt 4

| Việc | Nhánh | Commit | Bằng chứng / việc mở |
|---|---|---|---|
| 1 | `codex/d4-viec1-ra-k3` | `025b346` (các lỗi riêng: `d571899`, `008621b`, `1754c84`, `7921f56`, `9eb14a8`, `dc7a436`, `9841fe2`, `9c79536`; fixture `e2d0c02`) | Rà đủ 4 điểm; 15 test mới, từng lỗi đỏ→xanh. Nhóm liên quan 162 passed / 2 skipped; kiểm cuối K3 + sent_package 64 passed. So gói cờ tắt từng byte và thứ tự ghi sổ với snapshot main c78bcfe. Rà độc lập trước commit + rà lượt hai; báo cáo `docs/RA_D4_VIEC1_CODEX_2026-10-10.md`. Chưa thử provider thật, chưa chạy cả bộ, K3 mặc định tắt. |
| 2 | `d4-viec2-byd-flaky` (Claude làm thay — Codex hết gói) | `06b4a38` | Nguồn: `core/prompt_formula.py:706` `_now()` theo giây ghi vào `formula_check.at`; test so hai lần chạy vắt ranh giới giây. Đóng băng `_now` trong test; ghép 3 file 5 lần đều 62 passed. |
| 3 | (Claude, cùng lần chạy cả bộ khi gộp) | — | Cả bộ 4004 passed / 4 skipped, 1110 s; 17 test ≥ 8 s đều đã trong `SLOW_TESTS` → không đổi `conftest.py`. Chậm nhất: test_v3 kling_multishot 47,5 s; devsys every_page 31,2 s. |

---

# ĐỢT 5 — NGHIÊN CỨU: đồng nghiệp tự xử lý lỗi trên Dashboard (11/10, người dùng duyệt)

**Vấn đề:** Dashboard sắp có đồng nghiệp dùng. Ngày 11/10, dự án #24 gặp nhiều lỗi phải sửa mà KHÔNG làm được trên Dashboard — người dùng phải chat với phiên Claude, phiên Claude giao phiên con sửa tay bằng công cụ dòng lệnh. Đồng nghiệp không chat được với phiên Claude → cần Dashboard tự phục vụ. Việc này là NGHIÊN CỨU + THIẾT KẾ (tài liệu + mockup), KHÔNG sửa `dashboard/`, `core/`.

**Các ca lỗi thật 11/10 (dữ liệu thiết kế):**
1. Ảnh vẽ thấy miệng giếng dù máy thấp (0,5 m) ngửa lên — sai hình học (`core/stage_facts.py` `_derive_top…`).
2. Vị trí nhân vật sai sau động tác di chuyển (yêu nữ trườn ra khỏi giếng phải cách thành 1–1,5 m; blocking viết tay để 0,25 m) → phải sửa sân khấu 3D (`data/projects/<id>/stage_v2_*/blocking.json`, `tools/stage_grid.py v2`), giải lại máy, render nền (`tools/location_pack.py render`), viết lại blocking/prompt/BYĐ cho nhiều shot; giữ nhân vật khác khớp ảnh ĐÃ DUYỆT (`core/shot_lessons.py` movement_gaps, layout_drift).
3. Thêm shot mới (shot 10) — `Pipeline.add_scene_next` + điền đủ trường như shot khác.
4. Khung đầu + khung cuối cho video Kling (`core/end_frames.py`).
5. Gói gửi lẫn HAI nền 3D khác góc máy (cache cũ) → model ghép nhà dính tường; chỉ tìm ra bằng cách mở `jobs.sent_package`.
6. Vật thừa (thùng dầu đỏ) có THẬT trong map 3D Kho → xóa bằng Blender (tài nguyên DÙNG CHUNG mọi dự án).
7. Ngoại lệ khóa nhân vật theo shot (`byd.ngoai_le`, `core/lock_exceptions.py`) — ảnh sạch không glitch ở shot 9–10.
8. Tổ rà soát (`core/change_review.py`) báo mục đỏ cũ/đúng-nhưng-đã-xử-lý → người phải quyết bỏ qua.
9. Duyệt ảnh từ điện thoại (người dùng không mở được Dashboard) → phiên Claude ghép ảnh so sánh gửi qua chat.

**Hướng đã đề xuất với người dùng (4 lớp) — nghiên cứu sâu, phản biện, chi tiết hóa:**
1. Chẩn đoán tự động khi loại ảnh + ô "Gói đã gửi" (nền, ảnh mẫu, ref của từng job; cảnh báo nền khác góc, vật có trong map, mâu thuẫn hình học, cảnh báo `shot_lessons`).
2. Trợ lý sửa shot trong Dashboard: người dùng gõ/khoanh lỗi → Claude API trên máy chủ gọi CÔNG CỤ = các hàm core có sẵn (sửa blocking sân khấu, giải máy, render nền, viết lại prompt/BYĐ, thêm shot, gắn khung đầu–cuối) → xem trước 3D (0 USD) + báo giá (`core/cost.py`) → người bấm duyệt mới gen. Quyền theo dự án (`core/access.py`), trần tiền theo người, mọi lời gọi qua sổ chi; sửa tài nguyên chung (Kho, map 3D, Character Bible) cần admin duyệt.
3. Phiếu chuyển lên: lỗi code / tài nguyên chung → phiếu kèm ảnh + gói gửi + chẩn đoán → admin + AI Dev System (`devsys/`) + phiên bảo trì; đồng nghiệp thấy trạng thái phiếu.
4. Vòng bài học dùng chung: mỗi lần sửa ghi (lỗi, sửa, lý do) → lặp ≥ 2 lần thì đề xuất luật/kiểm → admin duyệt → áp mọi người (xem `core/lessons.py`, `knowledge/checks/`, `experience_cases`).

**YÊU CẦU NÂNG (người dùng 11/10, thay thế phạm vi "9 ca" ở trên — 9 ca chỉ là ví dụ thật, KHÔNG phải giới hạn):**
Trợ lý tên **Tiểu Nhị**. Mục tiêu: **BẤT KỂ lỗi nào xảy ra trong lúc đồng nghiệp làm trên Dashboard đều giải quyết được qua Tiểu Nhị** — trực tiếp hoặc bằng cách Tiểu Nhị tự chuyển tới đúng nơi xử lý rồi báo lại kết quả; người dùng không phải tìm Claude Code / admin.
**THỨ TỰ ƯU TIÊN (người dùng 11/10): SỬA + NÂNG TÍNH NĂNG DASHBOARD TRƯỚC, Tiểu Nhị SAU — để không phụ thuộc vào trợ lý.** Với mỗi loại lỗi ở A, câu hỏi đầu tiên là "Dashboard cần nút/màn/kiểm nào để người dùng TỰ sửa bằng thao tác thường (không chat)?" — vd ô "Gói đã gửi" + chẩn đoán tự động, sửa vị trí nhân vật/máy trên sân khấu 3D bằng giao diện (kéo/nhập số, xem trước 3D 0 USD), thêm/chèn shot, gắn khung đầu–cuối, đóng mục Tổ rà soát có lý do, duyệt ảnh trên điện thoại. Tiểu Nhị chỉ là lớp phủ cho phần còn lại (lỗi hiếm, lỗi code, cần suy luận nhiều bước) và GỌI LẠI đúng các chức năng Dashboard đó (không có đường sửa riêng). Lộ trình (e) phải xếp: đợt 1–n = tính năng Dashboard theo tần suất × công sức; Tiểu Nhị bắt đầu khi các tính năng lõi đã có. Bảng A thêm cột "Tính năng Dashboard cần có".

A. **Phân loại TOÀN BỘ lỗi có thể gặp** (đọc code, `diag_events`, `devsys/error_types.json`, `mistakes`, `content_moderation_failures`, WAIT_REASONS, `knowledge/checks/*`): theo từng khâu — ý tưởng/kịch bản, Biên kịch, Kho (nhân vật, trang phục, map 3D, âm thanh), BYĐ/Đạo diễn, sân khấu 3D/plate, ảnh, khung cuối, video (Kling/Seedance: bộ lọc người thật, ref, thời lượng, khớp môi), âm thanh/TTS/nhạc, dựng/phụ đề/popup, xuất bản; và loại ngang — tiền/trần/sổ chi, job kẹt/hàng đợi/nhà cung cấp lỗi/hết credit, quyền/tài khoản, lỗi giao diện/Dashboard sập, dữ liệu hỏng/mất ảnh, lỗi code. Mỗi loại: dấu hiệu, chẩn đoán bằng gì, ai sửa được, Tiểu Nhị xử lý tới đâu.
B. **Bậc năng lực + an toàn của Tiểu Nhị:** (1) giải thích/chẩn đoán; (2) sửa dữ liệu trong dự án của người đó (người bấm duyệt, báo giá trước mọi lời gọi tốn tiền); (3) sửa tài nguyên dùng chung — chuẩn bị thay đổi + xem trước, admin duyệt; (4) LỖI CODE: Tiểu Nhị lập phiếu đủ bằng chứng → khởi động phiên bảo trì Claude tự động (vd Claude Code chạy nền/Agent SDK trong worktree: tái hiện bằng test đỏ → sửa → rà → cả bộ test) → admin duyệt gộp → Tiểu Nhị báo người dùng "đã sửa, làm lại được"; nghiên cứu cách làm khả thi + rủi ro + chi phí. Mỗi bậc: quyền, trần tiền, giới hạn vòng, ghi vết, hoàn tác.
C. **Đặt Tiểu Nhị ở đâu:** so sánh các phương án (nút nổi toàn cục; khung bên trong từng bước/từng shot có sẵn ngữ cảnh; tự bật khi job lỗi/ảnh bị loại/Tổ rà soát báo đỏ; hộp phiếu; trang riêng; kênh ngoài Dashboard như điện thoại/Zalo/Slack/email cho người không ngồi máy) theo: ngữ cảnh tự có, số cú bấm, chi phí token, an toàn quyền, dùng được trên điện thoại. Đề xuất phương án chính + phụ, có mockup.
D. **Đo được:** đề xuất bộ "ca lỗi chuẩn" (≥ 30 ca phủ các loại ở A, gồm 9 ca thật 11/10) để chấm Tiểu Nhị tự giải quyết bao nhiêu %, sai bao nhiêu, tốn bao nhiêu; ngưỡng để mở cho đồng nghiệp.
E. **Mô hình:** chọn model Claude cho từng bậc (hỏi đáp rẻ vs sửa phức tạp), cách nạp ngữ cảnh dự án tiết kiệm token (cache), giới hạn chi tiêu/ngày.

**Luật:** chung đợt 1 + KHÔNG sửa `dashboard/`, `core/`, `data/`, TODO.md; chỉ thêm tài liệu + mockup. Nhánh `codex/d5-nghien-cuu-tu-phuc-vu`. Đọc code để biết cái gì ĐÃ CÓ (ghi file:dòng), đừng đề xuất làm lại thứ đã có. Phản biện thẳng: chỗ nào rủi ro (tiền, quyền, gửi trùng job, sửa tài nguyên chung, Claude tự quyết sai), chỗ nào nên đơn giản hơn.

**Sản phẩm:**
- `docs/NGHIEN_CUU_TU_PHUC_VU_DASHBOARD.md` (tên trợ lý: Tiểu Nhị; phủ đủ A–E ở trên): (a) bảng phân loại lỗi đầy đủ + 9 ca thật × Dashboard hôm nay làm được gì / thiếu gì (file:dòng); (b) kiến trúc 4 lớp (luồng, dữ liệu mới/bảng CSDL nếu cần, công cụ cho trợ lý = danh sách hàm core + đầu vào/ra + tốn tiền hay không + quyền); (c) mô hình quyền + tiền (vai: đồng nghiệp / admin; trần; duyệt tài nguyên chung); (d) an toàn: trợ lý không được tự chi tiền, không sửa code, giới hạn số vòng, ghi vết; cách chống gửi trùng (đã có khóa `core/bg_poll`); (e) lộ trình theo đợt có ước lượng công (S/M/L) + thứ tự giá trị; (f) câu hỏi cần người dùng chốt (liệt kê, kèm đề xuất).
- `mockup/tieu_nhi.html` (tĩnh, theo phong cách `mockup/dashboard.html`): vị trí Tiểu Nhị theo phương án đề xuất ở C + màn ảnh có ô "Gói đã gửi" + chẩn đoán; khung chat "Sửa shot" với xem trước 3D + báo giá + nút duyệt; danh sách phiếu chuyển lên.
- Ghi kết quả vào mục "Kết quả Codex — đợt 5".

## Kết quả Codex — đợt 5

✅ Nghiên cứu + thiết kế hoàn tất 11/10/2026, nhánh `codex/d5-nghien-cuu-tu-phuc-vu` (chỉ push nhánh, chưa gộp main).

- Commit nội dung `39c290a`; sửa sau rà `4a6167f`.
- `docs/NGHIEN_CUU_TU_PHUC_VU_DASHBOARD.md`: kiến trúc 4 lớp, quyền/tiền/idempotency, placement/mobile, 42 ca chuẩn, model/cache/giá nguồn chính thức, roadmap Dashboard trước Tiểu Nhị sau, 7 chốt cần quyết định.
- `docs/D5_KIEM_KE_HIEN_TRANG.md`: 42 loại lỗi, 9 ca thật đối chiếu code/UI, catalog tool I/O/chi phí/quyền; không đọc dữ liệu thật.
- `mockup/tieu_nhi.html`: giao diện offline có gói gửi/chẩn đoán, công cụ sửa thông thường, chat ngữ cảnh, xem trước/duyệt dữ liệu/gen riêng, phiếu chuyển lên; chỉ mô phỏng.
- Rà độc lập + lượt hai, báo cáo `docs/RA_D5_CODEX_2026-10-11.md`. Kiểm HTML/JS/citation bounds xanh; Node VM 6 kiểm logic: bản đầu 4 đỏ → bản sửa 6 xanh. Không chạy pytest cả bộ vì chỉ tài liệu/mockup, không gộp.
- Việc mở: chưa visual QA do trình duyệt chặn file URL; chưa thử gen/cách ly/auth/mạng điện thoại; cần chốt 7 quyết định trong tài liệu trước triển khai. Không đổi dashboard/core/data/TODO/PLAN, không API/Blender, không restart dịch vụ.

---

# ĐỢT 6 — hậu kỳ post_fx, công cụ nhịp ref, sửa shot_lessons (11/10 trưa, người dùng duyệt cả 3)

Luật chung GIỐNG đợt 1 + thêm: mỗi việc một nhánh `codex/d6-viec<N>-<tên>` từ `origin/main` mới nhất; KHÔNG đọc/ghi `data/`, không gọi API, không chạy Blender; KHÔNG sửa `dashboard/`; KHÔNG đụng đường gửi job (`core/runner.py` submit/hydrate) và khóa nhân vật (`core/lock_exceptions.py`) — #24 đang chạy trên các phần đó. Hành vi mới sau cờ TẮT (`core/features.py`). Ghi kết quả vào "Kết quả Codex — đợt 6".

## Việc 1 — Hậu kỳ nhiễu sóng/glitch bằng ffmpeg đọc `post_fx` (vừa)
Shot có `scenes.data.post_fx` (vd #24 shot 10: cuối shot màn hình nhòe, nhấp nháy, nhiễu sóng như mất kết nối → chuyển quảng cáo; xem cách phiên 11/10 ghi trường này: grep `post_fx` trong repo) — hiện CHƯA bước dựng nào đọc. Thêm: lược đồ `post_fx` tối thiểu (loại hiệu ứng: `nhieu_song`/`glitch`/`nhap_nhay`…, vị trí `cuoi`/`dau`/`ca_shot`, thời lượng s, cường độ) + hàm áp bằng ffmpeg vào clip của shot ở bước dựng (đọc cách `core/` dựng clip/rough cut làm, tái dùng ffmpeg helper sẵn có). Thiếu/ sai trường → VÀNG có lý do, không im lặng. Cờ `post_fx_render` TẮT. Test: clip ffmpeg thật cỡ nhỏ (như `tests/test_keep_audio.py` RealFfmpegTests) — độ dài không đổi, đoạn cuối khác khung gốc, cờ tắt thì byte giống; nhãn `slow` nếu ≥ ~8 s.

## Việc 2 — Công cụ tạo tệp nhịp cho video ref (nhỏ)
Kiểm "độ phủ nhịp ref" (`core/shot_lessons.ref_coverage`, quy ước `<video>.beats.json`) cần tệp nhịp mà chưa có công cụ tạo. Thêm `tools/ref_beats.py <video>`: xuất dải khung hình có mốc giờ (ffmpeg, ~1 khung/0,5 s, JPG cạnh video) + mẫu `<video>.beats.json` đúng lược đồ `shot_lessons` (nhip: [{ten, tu_s, den_s, mo_ta}], chi_tiet, tu_khoa, bien_do) để người duyệt điền; không ghi đè tệp có sẵn (cần `--force`); `--check` kiểm tệp đã điền hợp lệ. Test dùng video tạo bằng ffmpeg trong thư mục tạm.

## Việc 3 — `shot_lessons drift/nhip` lấy thứ tự shot đúng (nhỏ)
Hiện khi `shot_specs` chỉ có một phần các shot thì thứ tự nhịp có thể sai → báo nhiễu. Sửa: thứ tự shot lấy từ CSDL khi có (`scenes.idx` theo project; thêm tham số `--db`/`--project`), không có thì từ `shot_specs` + cảnh báo VÀNG "thứ tự suy từ shot_specs". Test bằng CSDL tạm (như các test khác tạo DB tạm) với shot_specs thiếu một phần.

## Kết quả Codex — đợt 6

| Việc | Nhánh | Commit code | Bằng chứng / việc mở |
|---|---|---|---|
| 1 | `codex/d6-viec1-post-fx` | `f9603c7` | Module chưa có → test đỏ; hồi quy huge integer 2 đỏ → xanh. Nhóm post_fx + keep_audio + final_cut **43 passed / 10,18 s**, ffmpeg thật 3 hiệu ứng có đối chứng, duration/audio/gốc/cờ tắt giữ đúng. Rà độc lập + lượt hai, `docs/RA_D6_VIEC1_CODEX_2026-10-11.md`. Cờ TẮT, chưa thử phim sản xuất, chưa cả bộ/gộp main. |
| 2 | `codex/d6-viec2-ref-beats` | `4a0c638` | Đỏ module chưa có; hồi quy rà 9 đỏ → xanh. Nhóm ref_beats_tool + p24_lessons **62 passed / 1,31s**, ffmpeg portrait thật/TMP, schema, OFF, CWD, force/rollback/timeout/giới hạn khung. Rà độc lập + lượt hai, `docs/RA_D6_VIEC2_CODEX_2026-10-11.md`. Cờ TẮT; ref ≤300s, chưa thử sản xuất/cả bộ/gộp main. |
| 3 | `codex/d6-viec3-thu-tu-shot` | `d92e848` | 9 failed → **78 passed (0,78 s)**. CLI bài học shot lấy thứ tự shot từ CSDL chỉ đọc, cảnh báo thiếu ánh xạ nhịp. Rà độc lập, `docs/RA_D6_VIEC3_CODEX_2026-10-11.md`. Cờ TẮT; chưa kiểm dự án thật. |

Rà độc lập cả ba việc đã hoàn tất (báo cáo riêng `docs/RA_D6_VIEC<N>_CODEX_2026-10-11.md`). Tích hợp: giữ đủ ba cờ (`post_fx_render`, `ref_beats_tool`, `shot_lessons_db_order`, đều TẮT) và đăng ký areas.json, tăng version một lần.

---

# ĐỢT 7 — thiết kế Tiểu Nhị + Lão Đại theo chốt người dùng 11/10 (tài liệu + mockup; người dùng duyệt)

Nguồn: rà nhánh Đợt 5 (đã gộp `ecdc91b`) + hộp thư `TODO.md` 📨 dòng 14:24–14:35 (người dùng chốt). **Chỉ sửa tài liệu + mockup**
(`docs/NGHIEN_CUU_TU_PHUC_VU_DASHBOARD.md`, `docs/D5_KIEM_KE_HIEN_TRANG.md`, `mockup/tieu_nhi.html`, file mới trong `docs/`/`mockup/`); KHÔNG
sửa `core/`, `dashboard/`, `devsys/`, `data/`, `TODO.md`; không API, không Blender. Mỗi việc một nhánh `codex/d7-viec<N>-<tên>` từ `origin/main`.
Dẫn `file:dòng` thật (mở trên `origin/main`); không đề xuất làm lại thứ đã có. Ghi kết quả vào "Kết quả Codex — đợt 7".

**Chốt người dùng (ghi vào mục "Các chốt" của tài liệu, thay bản đề xuất cũ — đừng hỏi lại):**
1. Chưa cần HTTPS / điện thoại (bỏ khỏi đợt gần; ghi là việc sau).
2–3. Trần Tiểu Nhị **theo dự án** (không opt-in từng người); hết trần → Tiểu Nhị gửi yêu cầu admin nâng. Khi dùng thật: mặc định 2 USD/dự án
   (người dùng nghiêng 2–3), tách khỏi tiền gen, cảnh báo ở 80 %. **Hiện tại** giữ đề xuất 0,15 USD/phiên chat.
4. Chỉ Owner publish Kho/map/Bible; muốn sửa chính thức Kho → gửi yêu cầu/report admin.
5. Bảo trì tự động = ĐỀ XUẤT chờ người dùng xác nhận: hiện tại phiếu lỗi code → admin giao phiên Claude; **Đợt 8+**: thợ bảo trì Claude Code
   cách ly (test đỏ → sửa → rà → cả bộ Windows → nhánh + báo cáo → admin duyệt gộp); phiếu thường chạy lô ~22:00, phiếu chặn sản xuất chạy ngay
   khi admin cho phép; chỉ mở khi đủ cách ly + bộ 42 ca đạt.
6. Hạn xử lý phiếu **3 ngày**.
7. ID shot nội bộ bất biến + thứ tự riêng (không đổi ID job/ảnh cũ).

**Hai cấp trợ lý (người dùng đặt tên):**
- **Tiểu Nhị** — đồng nghiệp (và người dùng khi làm dự án): khung phải Dashboard, phạm vi dự án/shot, gỡ lỗi bằng DỮ LIỆU qua đúng chức năng
  Dashboard (đề xuất → người bấm duyệt), vượt quyền → tự lập phiếu.
- **Lão Đại** — cấp trên, CHỈ admin, **pet desktop nổi luôn trên cùng ở máy chính** (như pet Codex): nhận phiếu Tiểu Nhị chuyển lên (lỗi code /
  nâng trần / sửa Kho), nhắc phiếu sắp quá hạn 3 ngày, theo dõi chi tổng + job kẹt + dự án gen xong, khởi động thợ bảo trì khi admin cho phép.
  Duyệt vẫn ở Dashboard đã đăng nhập (pet chỉ mở đúng trang, KHÔNG duyệt trên pet).
- **Luồng phiếu:** đồng nghiệp CHỈ thấy **lỗi là gì + nút sửa ngay** (vd "bỏ ảnh nền rộng thừa rồi vẽ lại") — không thấy phiếu/code. Sửa tận gốc
  chạy NGẦM: Tiểu Nhị tự lập phiếu (bằng chứng + "đã gỡ tạm bằng…") → Lão Đại báo admin → admin duyệt → thợ bảo trì sửa → admin duyệt gộp →
  (nếu cần) Tiểu Nhị báo người dùng. Chỉ báo người dùng khi lỗi CHẶN HẲN: "đã báo admin, dự án tạm dừng ở shot này".
- **Phiếu** (admin đọc): tiêu đề chữ thường, ảnh hưởng (dự án/shot bị chặn, tiền), nguyên nhân (đoán / đã xác nhận + bằng chứng), cần gì + ai
  làm + hạn 3 ngày, trạng thái, phần kỹ thuật (file/test/nhánh) + nút duyệt; lỗi code sửa xong ghi "đã sửa gì, test nào".
- **"Gói gửi kèm" chỉnh được theo shot** — xếp **Đợt 1 Dashboard** cùng "Gói đã gửi": xem gói lần trước; bỏ / thêm (từ Kho hoặc nền 3D của
  đúng shot) / ghim ảnh cho lần vẽ tới; kiểm ngay gói (2 nền khác góc, nhân vật trong khung thiếu ảnh mẫu…) + báo giá + vẽ lại. Tiểu Nhị dùng
  ĐÚNG chức năng này. Ca thật 11/10: job 649 (ảnh nền rộng thừa), 645–651 (thiếu ảnh mẫu Kho 419) — hôm nay phải sửa code mới gỡ được
  (`0082b8b`, `0da6966`).

## Việc 1 — Cập nhật tài liệu nghiên cứu theo chốt (vừa)
1. Ghi các chốt + hai cấp + luồng phiếu ở trên vào `docs/NGHIEN_CUU_TU_PHUC_VU_DASHBOARD.md` (sửa mục "Các chốt", kiến trúc 4 lớp, mô hình quyền
   + tiền, lộ trình). Chỗ nào bản cũ mâu thuẫn chốt → sửa theo chốt, ghi "(chốt 11/10)".
2. **Phiếu đi vào AI Dev System có sẵn hay hệ mới:** đọc `devsys/answers.py` (`answer()`, `load()`), `devsys/app.py` (web 8502),
   `devsys/error_types.json`; so 2 cách (trùng dữ liệu, quyền, ai đọc/đóng, Lão Đại đọc gì), chọn một + lý do. Xét lại 5 bảng mới đề xuất
   (proposals, operations, audit, tickets, budget_reservations) so `diag_events`, `change_findings`, `usage_ledger`, `devsys/answers`: bỏ / gộp /
   bắt buộc. Lược đồ phiếu đủ các trường ở trên + hạn 3 ngày + trạng thái.
3. **Lớp 4 dùng `experience_cases`** (`core/experience.py:26`, tài liệu bỏ sót).
4. **Thiết kế "Gói gửi kèm" theo shot:** dữ liệu lưu ở đâu (đề xuất `scenes.data` khóa riêng hay bảng mới; KHÔNG sửa gói đã gửi — `jobs.sent_package`
   bất biến), ai đọc khi dựng gói (chỉ mô tả chỗ nối — `core/runner.py` / `core/scene_storyboard.py` / `core/place_refs.py`, KHÔNG sửa), các phép
   kiểm ngay (dùng lại `core/place_refs.py` `package_problem` từ `0082b8b`, kiểm ảnh mẫu người trong khung từ `0da6966`), báo giá, hoàn tác,
   ghi vết. Đây là đầu vào cho ĐỢT 8 việc 1.
5. **Thiết kế Lão Đại** (pet): Windows app nhỏ cửa sổ trong suốt luôn trên cùng; đọc gì (phiếu, sổ chi, job kẹt, dự án gen xong) qua đường CHỈ ĐỌC
   nào (HTTP 8501/8502 có đăng nhập hay đọc CSDL chỉ đọc); toast Windows + bong bóng "📨 N phiếu chờ duyệt"; bấm mở đúng trang Dashboard;
   khởi động thợ bảo trì chỉ sau admin cho phép. So 2–3 cách làm (vd Python + pywebview/tkinter, Tauri/Electron) theo công sức + rủi ro. Đầu vào
   cho ĐỢT 9.
6. **Bộ 42 ca chuẩn:** định dạng fixture (ca thật C01–C09 lấy dữ liệu từ đâu mà không cần `data/` thật), nơi lưu, cách chấm %, **ước tính chi phí
   1 lượt** (số lời gọi × model × token; giá cache hit Sonnet 5.5 = **0,20** USD/MTok, đã sửa); cân nhắc khung `core/evalset.py`; thêm **bản tối thiểu
   cho pilot đầu**.
7. **Lộ trình (e): chấm TỪNG tính năng Dashboard** theo tần suất × công sức (tính năng · ca lỗi · tần suất giả thuyết + nguồn · S/M/L · điểm · thứ
   tự) — "Gói gửi kèm" + "Gói đã gửi" ở Đợt 1 theo chốt.
8. **Câu hỏi chốt còn mở (mỗi câu kèm đề xuất):** (a) ngưỡng bài học `MIN_EVENTS = 3` / `MIN_PROJECTS = 2` (`core/lessons.py:20-21`) so "lặp ≥ 2";
   (b) Tiểu Nhị / Lão Đại dùng Claude API (sổ chi) hay hạn mức gói/CLI; (c) kết luận mục 2.
9. **Thêm ca:** khung cuối bị coi là cũ khi khung đầu đổi (`core/end_frames.py:56-62` `usable_path`, `start_job_id` lệch) — người dùng thấy gì,
   nút sửa ngay là gì.
10. Sửa 4 tham chiếu lệch: `dashboard/steps/step1.py:294` → 292; `core/lessons.py:214` (là đoạn 217–223 đếm lỗi chưa phân loại);
    `step1_prep.py:295` là đặt nhân vật lên ảnh bối cảnh, không phải "Storyboard 2D"; `knowledge/checks/L13.md:20` → 24–31.

## Việc 2 — Mockup theo chốt (nhỏ–vừa)
`mockup/tieu_nhi.html` + file mới `mockup/lao_dai_pet.html` (offline, không gọi mạng):
1. **Gói gửi kèm theo shot** trong khung shot: gói lần trước (ảnh nhỏ + vai), bỏ / thêm từ Kho hoặc nền 3D đúng shot / ghim; kiểm ngay hiện ĐỎ
   "2 nền khác góc" / "người trong khung thiếu ảnh mẫu" kèm nút sửa ngay; báo giá vẽ lại; dựng theo ca job 649 / 645–651 (#24).
2. **Luồng đồng nghiệp:** chỉ "lỗi là gì + nút sửa ngay"; KHÔNG hiện phiếu/code. Ca lỗi chặn hẳn → dòng "đã báo admin, dự án tạm dừng ở shot này".
3. **Lão Đại pet** (`lao_dai_pet.html`, mô phỏng cửa sổ nhỏ góc màn hình): dáng thường / dáng có phiếu + bong bóng "📨 N phiếu chờ duyệt",
   danh sách phiếu (trường ở trên, hạn 3 ngày, sắp quá hạn tô vàng), chi hôm nay / job kẹt / dự án gen xong; nút "Mở trên Dashboard" (không có
   nút duyệt trên pet).
4. Bỏ phần duyệt trên điện thoại (chốt 1). Sửa: nhãn dự án khớp #24 / job 649 (đang ghi "Khủng Long Đỏ"); thập phân dấu phẩy ("1,2 m",
   "0,16 USD"); ô khoảng cách cho nhập cả giá trị SAI hiện tại (0,25 m) để thấy cảnh báo; **đổi một ô sau khi đã Gen thì giữ dấu "đã gen bản trước"
   + cảnh báo gen lần 2 sẽ tốn thêm tiền**.
5. Kiểm bằng Playwright Chromium ở 1280 (và 390 cho khung Tiểu Nhị): 0 lỗi console, không cuộn ngang, nút mới chạy; giữ hành vi đã sửa ở `4a6167f`.
   Có thể thêm test grep/JS nhẹ như `tests/test_mockup_video_3cot.py` (khai vào `devsys/areas.json` khu `dashboard_ui` — được sửa đúng dòng `tests`
   này, KHÔNG tăng version).

## Kết quả Codex — đợt 7

| Việc | Nhánh | Commit nội dung / bàn giao | Bằng chứng / việc mở |
|---|---|---|---|
| 1 — thiết kế | `codex/d7-viec1-thiet-ke` | `8a94fac` / `a5c3eb9` | Đủ 10 mục; 42 mã ca, 123 tham chiếu trong giới hạn, 12 link tồn tại; diff check xanh. Ba câu còn mở, C09 hoãn, ACL/broker/pet chưa thử. Báo cáo RA_D7_VIEC1 trên nhánh tương ứng. |
| 2 — mockup | `codex/d7-viec2-mockup` | `b5ff46a` | 2 test đỏ → 6 xanh; Chromium Tiểu Nhị 1280/390 và pet 1280: 0 lỗi console, 0 mạng, không cuộn ngang; kiểm tương tác và PNG. Root rà nhẹ sửa 2 nhãn. Báo cáo RA_D7_VIEC2; chỉ mô phỏng offline, chưa pet/Dashboard thật. |

Hai nhánh từ main mới nhất tại lúc tạo (việc 1 base `229f812`, việc 2 base `5593cde`), gộp main 11/10 (phiên rà Codex, kèm sửa sau rà: hợp đồng Đợt 8 trong THIET_KE mục 3, giá cache hit Sonnet 5.5 = 0,20, mockup không ghi đè lặng lẽ, ngày phiếu, ảnh PNG chuyển `docs/images/d7/`). Phiên rà tích hợp giữ đủ kết quả và đúng dòng đăng ký test dashboard_ui, kiểm theo quy trình trước gộp. Không sửa core/dashboard/data/TODO/PLAN, không API/Blender; chưa chạy cả bộ Windows.

---

# ĐỢT 8 — code sau cờ TẮT (việc 1–2) + sửa báo giá video (việc 3), không đụng đường #24 (giao SAU khi Đợt 7 việc 1 gộp; người dùng phân công 11/10 14:35)

Luật chung GIỐNG đợt 1 + thêm: mỗi việc một nhánh `codex/d8-viec<N>-<tên>` từ `origin/main`; **KHÔNG sửa `core/runner.py`, `core/lock_exceptions.py`,
`core/end_frames.py`, `core/place_refs.py` chọn nền, `core/scene_storyboard.py`** (#24 đang chạy trên đó — phần nối vào luồng ghi thành việc mở,
phiên rà Codex nối sau khi #24 xong); không đọc/ghi `data/` thật, không API, không Blender. Hành vi mới sau cờ TẮT (`core/features.py`), cờ
tắt thì byte giống. Test đỏ → xanh. Ghi kết quả vào "Kết quả Codex — đợt 8".

## Việc 1 — Lõi "Gói gửi kèm" theo shot (vừa)
Theo thiết kế Đợt 7 việc 1 mục 4. Module mới thuần (vd `core/package_overrides.py`): lưu chỉnh của shot (bỏ / thêm / ghim ảnh, ai, lúc nào, lý do),
áp chỉnh lên danh sách ảnh tham chiếu ĐÃ dựng (hàm thuần: vào danh sách ref + chỉnh → ra danh sách mới + cảnh báo), kiểm ngay (dùng lại
`place_refs.package_problem` và kiểm ảnh mẫu người trong khung — gọi, không sửa), hoàn tác, không bao giờ sửa `jobs.sent_package`. Cờ
`package_overrides` TẮT. Test bằng CSDL trong bộ nhớ + ảnh giả, có ca job 649 (2 nền khác góc) và 645–651 (thiếu ảnh mẫu Kho 419) dựng lại từ mô tả.
Việc mở: nối vào chỗ dựng gói ảnh/storyboard + màn Dashboard (sau #24).

## Việc 2 — Việc mở kỹ thuật (nhỏ; mỗi mục: điều tra → test đỏ → sửa sau cờ, hoặc chỉ báo cáo nếu chạm file cấm)
1. **`layout_drift` nối Tổ rà soát:** `core/shot_lessons.py:217` `layout_drift` hiện chỉ chạy qua CLI; đề xuất + làm (sau cờ) để đổi blocking của
   shot ĐÃ DUYỆT sinh mục trong `core/change_review.py` (cờ `change_review`) thay vì im lặng. Đọc `knowledge/checks/L13.md:24-31`.
2. **`short_lock_block`** (`core/prompts.py:562`): theo `docs/KIEM_22_TINH_NANG_KLD_2026-10-08.md:104` không áp cho nhân vật có ảnh OUTFIT (MAXIM KL,
   KELLY KL); xác nhận bằng test, sửa sau cờ mới (KHÔNG đổi prompt khi cờ tắt — #24 đang gen).
3. **Khung cuối dùng ảnh mốc Kho thay nền 3D** (`core/end_frames.py` — file CẤM sửa đợt này): chỉ điều tra + viết báo cáo
   `docs/RA_D8_END_FRAMES_MOC_KHO.md` (hiện chọn ảnh gì, vì sao, đề xuất sửa + test đỏ đặt sẵn đánh `xfail` có lý do) để làm sau #24.

## Việc 3 — Ước tính tiền video đếm thiếu (vừa; hộp thư phiên máy chính 11/10 15:04, ca thật #24 báo giá 3,11 USD thay vì ~27)
Không gấp với #24 (phiên máy chính tự tính tay) nhưng sửa tận gốc. ĐƯỢC sửa `core/cost.py`, `core/model_router.py`, `core/quality_tier.py`
(không thuộc đường gửi job); KHÔNG sửa runner/end_frames/place_refs/scene_storyboard. Sửa thẳng (đây là sửa lỗi báo giá, không cần cờ) — nhưng
ghi rõ trong "Kết quả" con số trước/sau trên dữ liệu giả dựng giống #24.
1. **"Đã làm" quá rộng:** `core/cost.py:589-591` `estimate_run` coi mọi job `video_gen` ở trạng thái succeeded/approved/running/queued/pending_review
   là clip đã có, KHÔNG kiểm clip đó làm từ ảnh đã duyệt HIỆN TẠI + motion prompt HIỆN TẠI → shot đã đổi ảnh/motion vẫn bị coi là xong (#24 chỉ đếm 1
   clip). Cùng kiểu: `core/model_router.py:339-340` `_remake_runs` (`has`). Một nguồn duy nhất cho "shot này còn phải gen video không" (đọc cách
   job ghi ảnh khởi đầu / motion — `jobs.sent_package`, `image_job_id`, sha… — để so; thiếu dữ liệu so → coi là CẦN gen + ghi lý do, không im lặng).
2. **Không cộng giây video ref** (`input_video_s`): `core/model_router.py:393-396`, `core/cost.py:275`, `core/quality_tier.py:555/558, 593-594` → thiếu
   ≈ 1,6 USD ở #24 (shot 5, 6, 8). Đọc bảng giá / công thức token ClipAI đang có (`seedance_estimate`) xem giây video ref tính thế nào; một hàm dùng
   chung cho cả 3 nơi.
3. **Cân nhắc:** `core/quality_tier.py:~88` `path()` xếp difficulty `unknown` vào đường nháp như shot khó — chỉ báo cáo (đúng/sai + đề xuất), không
   đổi nếu chưa chắc.
Test đỏ → xanh: dự án giả 9 shot (1 clip cũ khớp ảnh/motion hiện tại, vài clip cũ lệch, 3 shot có video ref) → số clip phải gen + tiền đúng; các test
báo giá cũ (`tests/` grep `estimate_run`, `model_router.plan`, `quality_tier`) vẫn xanh hoặc sửa có lý do.

## Kết quả Codex — đợt 8

- Việc 1: `codex/d8-viec1-goi-gui-kem`, code `aabcf24`, bàn giao `549ca98`; 6 đỏ + 1 lỗi hồi quy → 29 xanh. Rà 4 finding, sửa CAS/hash/base/ảnh/undo. Cờ OFF, chưa nối Dashboard/runner sau #24; RA_D8_VIEC1 trên nhánh.
- Việc 2: `codex/d8-viec2-ky-thuat`, code `4d6956d`, bàn giao `d762b6e`; 3 đỏ ban đầu, 3 đỏ sau rà → 68 xanh / 1 xfail có lý do. layout_drift nối stage_grid sau cờ; OUTFIT skip digest sau cờ. Endframes chỉ báo cáo/test xfail. Còn baseline immutable và kiểm decode ảnh; RA_D8_VIEC2 trên nhánh.
- Việc 3: `codex/d8-viec3-bao-gia-video`, code `85a26db`; 3 đỏ ban đầu, 2 đỏ sau rà độc lập → 95 passed / 49,42s. Fixture 9 shot/3 refs: 0 clip/0 USD → 8 clip/5,51 USD. Shared predicate kiểm source/motion/SHA ảnh hiện tại; shared input_video_s, URL/UNC không probe. Thiếu proof có thể tính dư; ref unknown cảnh báo, chưa chứng minh trần. RA_D8_VIEC3_CODEX_2026-10-11.md.

Chỉ push nhánh riêng; không gộp main/cả bộ/test thật #24/API/data. Phiên tích hợp giữ các hunk areas và chạy cả bộ Windows trước gộp.

---

# ĐỢT 9 — kho phiếu + Tiểu Nhị tự lập phiếu + pet Lão Đại (người dùng duyệt 11/10; chạy SONG SONG Đợt 8 được)

Đầu vào: `docs/THIET_KE_TIEU_NHI_LAO_DAI_D7.md` mục 1, 2 (phiếu, lược đồ, vòng đời, nhắc hạn), 4 (pet) — đọc kỹ, làm đúng. **Chốt người dùng
11/10: bảng phiếu nằm CÙNG CSDL pipeline `data/manifest.sqlite`** (phương án A). Luật chung GIỐNG đợt 1 + thêm: mỗi việc một nhánh
`codex/d9-viec<N>-<tên>` từ `origin/main`; KHÔNG sửa `core/runner.py`, `core/lock_exceptions.py`, `core/end_frames.py`, `core/place_refs.py`,
`core/scene_storyboard.py` (#24); KHÔNG đọc/ghi `data/` thật (test dùng CSDL tạm), không API tốn tiền. Mọi tính năng mới sau cờ TẮT. Ghi kết quả vào
"Kết quả Codex — đợt 9". Việc 2 cần việc 1 (dùng chung lớp lưu phiếu) — làm việc 1 trước hoặc cùng nhánh nối tiếp; việc 3 chỉ cần hợp đồng snapshot
của việc 1 (dùng fixture).

## Việc 1 — Kho phiếu trong CSDL pipeline (vừa)
1. Lược đồ `support_tickets` + `ticket_events` theo THIET_KE mục 2 (id, title chữ thường, kind, error_type + taxonomy_revision, severity,
   project/scene/job nullable, fingerprint UNIQUE, source_actor, created_at UTC, `due_at = created_at + 72 h`, owner, state, impact, cause đoán/xác nhận
   + evidence_refs, cần gì / ai làm, phần kỹ thuật admin). Thêm vào `core/db.py` SCHEMA theo cách các bảng khác được thêm (CREATE IF NOT EXISTS +
   `ensure_columns` nếu có) — chạy trên CSDL cũ không lỗi. `ticket_events` append-only.
2. Module `core/tickets.py`: `open_or_merge(conn, ...)` (gộp theo fingerprint, thêm bằng chứng thay vì phiếu trùng), `transition(conn, id, to, actor,
   reason, expected_state)` (đúng máy trạng thái THIET_KE: nhánh code và nhánh budget/shared_asset; chuyển sai → lỗi rõ; CAS), `extend_due(...)` (giữ
   due gốc, ghi người/lý do), `due_status(ticket, now)` (vàng còn ≤ 24 h, đỏ quá 72 h; quá hạn KHÔNG tự đóng), `admin_snapshot(conn)` (projection chỉ
   đọc cho Lão Đại: số phiếu theo trạng thái, sắp/quá hạn, chi hôm nay tách pending/unknown, job kẹt, dự án gen xong — dùng lại hàm sẵn có:
   `budget.spent`, WAIT_REASONS, `diag`), `user_projection(ticket)` (đồng nghiệp chỉ thấy "lỗi là gì + đã báo admin, dự án tạm dừng ở shot này" khi
   CHẶN HẲN; không lộ phiếu/code/dự án khác). Ghi vết qua `audit_log` (`core/db.py:153–159`), không bảng audit mới.
3. Cờ `support_tickets` TẮT. Test: tạo/gộp/chuyển trạng thái đủ hai nhánh, CAS, gia hạn, nhắc hạn theo giờ giả, CSDL cũ không có bảng, projection
   đồng nghiệp không lộ dữ liệu.

## Việc 2 — Tiểu Nhị tự lập phiếu + trang phiếu admin (vừa)
1. Hàm `tickets.from_fix(conn, project_id, scene_id, job_id, problem, temporary_fix, evidence)` để khi lỗi được GỠ TẠM bằng dữ liệu (vd "Gói gửi kèm"
   bỏ nền rộng thừa, Đợt 8) thì tự lập/gộp phiếu kind=code với "đã gỡ tạm bằng…" — chỉ là API + test; chỗ gọi từ Dashboard để sau khi Đợt 8 nối.
2. Trang **"Phiếu" trên AI Dev System 8502** (phân hệ admin, `devsys/app.py` trang mới): danh sách theo hạn (sắp quá hạn tô vàng, quá hạn đỏ), chi tiết
   phiếu (ảnh hưởng, nguyên nhân + bằng chứng, cần gì, ai làm, hạn, trạng thái, phần kỹ thuật file/test/nhánh), nút chuyển trạng thái hợp lệ có lý do.
   8502 hiện chưa có ACL an toàn (THIET_KE mục 2): thao tác GHI chỉ bật khi có đăng nhập admin phía server — nếu chưa có cơ chế, trang CHỈ ĐỌC + ghi rõ
   lý do, không tự làm ACL tạm. Đọc CSDL qua đường dẫn cấu hình sẵn có (xem `core/db.py` / env), KHÔNG cứng `D:\`.
3. **Tối ưu XEM – CHỌN – DUYỆT phiếu cho admin (người dùng 11/10 yêu cầu):**
   - **Xem:** một hàng đợi duy nhất xếp theo mức cần xử lý (chặn sản xuất → quá hạn → sắp quá hạn → còn lại); mỗi dòng đủ để quyết mà không mở:
     tiêu đề, dự án/shot bị chặn, tiền liên quan, hạn còn lại, việc admin cần làm (1 động từ: duyệt gộp / duyệt nâng trần / duyệt sửa Kho / giao
     bảo trì). Chi tiết mở NGAY dưới dòng (không sang trang): bằng chứng (ảnh nhỏ / job / test đỏ→xanh / diff tóm tắt / nhánh), "đã gỡ tạm bằng…".
   - **Chọn:** lọc nhanh theo loại (code / nâng trần / Kho), theo dự án; phiếu cùng fingerprint gộp sẵn thành một (đếm số lần gặp, các dự án bị ảnh hưởng).
   - **Duyệt:** nút quyết định ngay trên dòng (Duyệt / Từ chối / Cần thêm thông tin / Gia hạn) — lý do có mẫu chọn sẵn + ô ghi thêm; duyệt xong tự
     chuyển phiếu kế; **duyệt hàng loạt** chỉ cho phiếu cùng loại không tốn tiền (vd đóng các phiếu trùng đã sửa) và phải xem danh sách trước khi bấm;
     phiếu nâng trần hiện số tiền trước/sau + trần dự án, bấm duyệt mới đổi trần. Không có thao tác nào tự chi tiền.
   - **Từ pet:** link pet mở THẲNG đúng phiếu (anchor/query `?ticket=<id>`), không mở trang chung.
   - **Đo:** ghi số lần bấm + số lần cuộn để quyết 1 phiếu thường (mục tiêu ≤ 2 bấm, 0 cuộn trang ở 1440×900) bằng AppTest/Playwright như
     `tools/ui_v2_acceptance.py`; so trước/sau, ghi vào "Kết quả".
4. Test AppTest trang phiếu với CSDL tạm (thứ tự hàng đợi, gộp fingerprint, duyệt → phiếu kế, duyệt hàng loạt chặn loại tốn tiền, link `?ticket=`);
   slow nếu ≥ 8 s.

## Việc 3 — Pet Lão Đại pilot (vừa; chạy/kiểm trên máy chính Windows)
Theo THIET_KE mục 4, cách **Python + tkinter** (pilot): `tools/lao_dai/` — cửa sổ nhỏ trong suốt luôn trên cùng ở góc, kéo được, icon khay ẩn/mở/
thoát, không chiếm focus; dáng thường / dáng có phiếu + bong bóng "📨 N phiếu chờ duyệt"; toast Windows chỉ mã + trạng thái (không ảnh / tên nhạy
cảm); bấm mở đúng trang phiếu 8502 hoặc trang duyệt Dashboard 8501 trong trình duyệt (KHÔNG có nút duyệt trên pet). Đọc qua **broker loopback chỉ
đọc** (`127.0.0.1`, token read-only có hạn, không mở ra LAN) trả `tickets.admin_snapshot`; pet KHÔNG đọc SQLite trực tiếp. Lỗi broker / mất kết nối →
dáng "mất kết nối" có lý do, không im lặng. Khởi động thợ bảo trì: CHƯA làm (chốt 5 chờ người dùng xác nhận). Test: broker (từ chối không token,
token hết hạn, chỉ GET), logic chọn dáng/bong bóng từ snapshot giả; phần GUI kiểm tay trên máy chính, ghi ảnh chụp vào `docs/images/d9/`. Kèm
`tools/launch_lao_dai.ps1` theo kiểu `tools/launch_devsys.ps1`.

## Kết quả Codex — đợt 9

(Codex ghi: việc · nhánh · commit · bằng chứng · việc mở.)
