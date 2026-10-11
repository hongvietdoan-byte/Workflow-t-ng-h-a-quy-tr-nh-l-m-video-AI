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

- Việc 1: `codex/d8-viec1-goi-gui-kem`, code `aabcf24`, bàn giao `549ca98`; 29 test xanh sau 4 finding/7 hồi quy. Cờ OFF, chưa nối runner/Dashboard. Báo cáo RA_D8_VIEC1 trên nhánh tương ứng.
- Việc 2: `codex/d8-viec2-ky-thuat`, code `4d6956d`; 3 đỏ ban đầu → 65 xanh/1 xfail, rà OUTFIT bắt 1 P2 với 3 hồi quy đỏ → **68 passed, 1 xfail**. RÀ KỸ + root đọc sửa; báo cáo RA_D8_VIEC2 và RA_D8_END_FRAMES_MOC_KHO. Producer sân khấu v3 sinh finding VÀNG sau hai cờ OFF; OUTFIT không gửi được giữ khóa. End_frames không sửa. Chưa baseline bất biến gắn job/Dashboard/v2/v4, chưa thử thật/cả bộ/gộp main.

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

**CÒN DỞ — việc 3 phần GUI (rà 12/10; backend `tools/lao_dai/broker.py` + `logic.py` ĐÃ gộp main, đừng viết lại):** (1) cửa sổ pet tkinter trong
suốt luôn trên cùng ở góc, kéo được, không chiếm focus; (2) icon khay ẩn/mở/thoát; (3) toast Windows chỉ mã + trạng thái; (4) `tools/launch_lao_dai.ps1`
theo kiểu `tools/launch_devsys.ps1`; (5) kênh cấp token đọc: broker `issue(session)` nhận phiên Owner đã đăng nhập — lấy từ đăng nhập 8502 mới có
(`devsys/admin_auth.py`, phiên rà Codex làm 12/10; KHÔNG sửa file đó, chỉ gọi) hoặc đăng nhập Dashboard; token lưu kho credential Windows,
không ghi file thường; (6) nút "Mở trên Dashboard" mở `http://localhost:8502/?ticket=<id>`; (7) ảnh chụp kiểm tay vào `docs/images/d9/`. Kiểm
GUI trên máy Windows (máy chính). Sửa kèm lỗi pet ở ĐỢT 10 việc 4 mục 4–5 (bong bóng chỉ đếm `waiting_admin`, broker truyền `data_dir`).

## Kết quả Codex — đợt 9

- Việc 1: `codex/d9-viec1-kho-phieu`, code `7356a9f`, bàn giao `963bf0b`; 27 test xanh sau 3 finding/11 hồi quy. Snapshot v1/cờ OFF; báo cáo RA_D9_VIEC1 trên nhánh tương ứng.
- Việc 2: `codex/d9-viec2-trang-phieu`, dependency `d3cafd5` là cherry-pick code việc 1, code `636e382`; 3 đỏ ban đầu → 30 xanh; 5 finding sau rà sửa gom một vòng → **38 passed / 8,52s**. RÀ KỸ + root đọc sửa; RA_D9_VIEC2, ảnh/số đo docs/images/d9. Trang Phiếu CHỈ ĐỌC do thiếu server auth, cờ OFF giữ trang cũ; xem chi tiết 1 bấm/0 cuộn tới hàng/nút, link đúng phiếu. Quyết định ≤2 bấm chưa nghiệm thu, ghi UI/bulk/đổi trần hoãn tới auth thật. Chưa gọi từ Dashboard/cả bộ/gộp main. Tích hợp giữ hunk workaround merge của core/tickets.py và không cherry-pick dependency hai lần.
- Việc 3 — ĐANG DỞ: `codex/d9-viec3-lao-dai`, dependency `df62cc7` là cherry-pick code7356a9f việc1, backend `42ecaec`. Broker loopback GET-only/token read-only TTL kiểm session Owner mỗi snapshot, SQLite chỉ đọc; logic dáng/bong bóng/dedupe/backoff/URL allowlist; cờ OFF. Đỏ module thiếu và mismatch due_status → 39 xanh; rà độc lập 2 finding/4 đỏ → 43 xanh /1,28s. RA_D9_VIEC3_CODEX_2026-10-11.md. CHƯA GUI tkinter/khay/toast thật/kho token OS/kênh cấp phiên server/launcher/QA Windows/PNG, chưa pilot chạy được. Dừng mở bước lớn theo hạn mức, tiếp sau reset. Chỉ push nhánh riêng, chưa toàn bộ/gộp/main. Tích hợp không cherry-pick dependency việc1 hai lần.

---

# ĐỢT 10 — sửa lỗi rà Đợt 8–9 + Tổ rà soát khung đầu/cuối + cảnh không đơ (11/10 tối, người dùng duyệt)

Đợt 8 việc 1–2 và Đợt 9 việc 1–3 ĐÃ GỘP main (cờ TẮT). Đợt 8 việc 3 (báo giá) CHƯA gộp — sửa trên chính nhánh `codex/d8-viec3-bao-gia-video`.
Luật chung GIỐNG đợt 1 + thêm: mỗi việc một nhánh `codex/d10-viec<N>-<tên>` từ `origin/main` (riêng việc 3 tiếp trên nhánh d8-viec3); KHÔNG sửa
`core/runner.py`, `core/lock_exceptions.py`, `core/end_frames.py`, `core/place_refs.py`, `core/scene_storyboard.py` (#24); không API tốn tiền, không
`data/` thật. Mỗi lỗi: test ĐỎ → sửa → xanh (ghi tên test). Ghi kết quả vào "Kết quả Codex — đợt 10".

## Việc 1 — Gói gửi kèm (`core/package_overrides.py`, cờ `package_overrides`) — 3 lỗi TRUNG
1. Ghim ảnh OUTFIT bị THÊM thay vì THAY (nhãn ref OUTFIT từ `assets.scene_references` là tên nhân vật "KELLY", `_resolve` gán tên tài nguyên
   "Kelly đồ bơi") → gói có 2 bộ đồ. Khớp chỗ thay theo nhân vật mặc (thêm `wearer`/`character` vào edit) hoặc theo role khi chỉ một chỗ outfit.
2. `_scene_hash` băm toàn bộ `scenes.data` → sửa `motion_en`/takes/camera_plan cũng làm chỉnh gói thành `override_stale`. Chỉ băm khóa ảnh hưởng gói
   (`lineage.IMAGE_KEYS` + characters/location/size/outfit/plate…).
3. `save(base_refs=None)` tự dựng gói khác gói thật lúc chạy → luôn stale. Bắt buộc truyền `base_refs`, thiếu → lỗi rõ.
THẤP kèm: chỉnh của shot mất số hiệu sau replan phải báo VÀNG; ghim không xóa ảnh góc phụ cùng nhân vật; không lặp cảnh báo `ref_unreadable`.

## Việc 2 — Việc mở kỹ thuật Đợt 8 (`layout_drift_review`, `short_lock_outfit`) — 3 lỗi TRUNG
1. `tools/stage_grid.py:~1575` ghi finding vào CSDL từ lượt thử v3 CHƯA áp dụng → chỉ gọi ở đường áp blocking chính thức, hoặc ghi là "đề xuất" kèm
   thư mục lượt.
2. Thiếu bản gốc để so (`--hand` = output v2 không có `blocking.json`/`shot_specs.json`; thiếu `--hand` lộ `TypeError`) → tham số bản gốc rõ ràng
   (`--approved-blocking`/`--approved-specs`) hoặc bản gốc gắn job ảnh đã duyệt; thiếu → lỗi rõ.
3. Hai tiêu chí "có OUTFIT" khác nhau (`short_lock_outfit` vs `prompts.lock_text:~543` / `runner.lock_note`) → prompt video tự mâu thuẫn. Dùng CHUNG
   tiêu chí của `lock_text` (không sửa runner; nếu cần một hàm chung thì đặt ở `core/prompts.py` và chỉ `prompts.py` gọi). THẤP: khai cờ
   `short_lock_outfit` vào khu bước 3 trong `devsys/areas.json`; test xfail end_frames dọn thư mục tạm.

## Việc 3 — Báo giá video (tiếp nhánh `codex/d8-viec3-bao-gia-video`) — 2 CAO + 3 TRUNG
1. **CAO:** shot đi theo trong nhóm Seedance ref luôn bị coi "cần gen" (gói chép từ shot dẫn, `image_path` là ảnh shot dẫn, ảnh khác là
   `refs_marked/*` hoặc `asset://`) → báo giá thừa (tái hiện runner thật nhóm 4 shot: thừa 0,90 USD). Chứng minh qua `sent_group` của shot dẫn + sha
   ảnh đánh dấu, hoặc `source_job_id` + `input_hash`. Test đi bằng runner thật (MockVideoProvider), không tự chèn gói tay.
2. **CAO — CHỜ #24 xong (người dùng chốt 11/10):** `core/project_budget.py:184-188` `remaining()` dùng chung `cost.video_need` và mức ước tính cao
   khi giá None (không `or 0`). Làm trong commit RIÊNG cuối nhánh, ghi rõ; phiên rà Codex chỉ gộp commit này khi phiên máy chính báo #24 không còn gen.
3. **TRUNG:** chưa biết thời lượng ref → không `continue` / không None (`quality_tier.py:552-554, 597-600`, `model_router.py:398-399`,
   `cost.py:272-274`): chỉ None khi ref thật sự bị tính tiền; còn lại dùng giá cao (trần giây ref / money_policy).
4. **TRUNG:** job `running` (đã trả tiền) bị tính lại → running = đang làm, không tính tiền lại; queued/retryable vẫn cần gen.
5. **TRUNG:** `tests/test_readiness_f5a.py::KhoObjectSizeTests::test_ten_shot_project_is_not_n_plus_1` đỏ (205 truy vấn) → cache theo
   `memo.per_rerun` hoặc chỉ đọc ref khi đường Seedance.
THẤP: `start_from_prev_clip` ghi rõ lý do; cảnh báo chỉ khi clip cũ bị loại (không cho mọi shot chưa có clip); test 9 shot phân biệt "lệch motion" vs
"thiếu bằng chứng"; thêm cộng giây ref ở `dashboard/model_line.py:83/89` và `quality_tier.py:484/488` nếu cùng nguồn.

6. **Bản cao / nâng final (hộp thư 11/10 23:40, #24 final_estimate 18,29–21,38 USD vs đúng ≈ 19,76 theo clip):** `core/quality_tier.py:452`
   `_clip_groups` rỗng khi `seedance_refs.enabled(pid)` = False dù job có `sent_group`/`group_leader` → tính riêng từng shot tối thiểu 4 s (`:484`);
   giây lấy `motion_prompts.duration_sec` (`:425–426, 506`) thay vì độ dài clip nháp thật (theo `external_id`/file); nháp chưa duyệt
   (`upgrade_block`) rơi nhánh "gen MỚI" giá 720p (`:485–488`); follower `quality_tier='direct'` bị bỏ (`:423`) trong khi `batch_final_price` vẫn
   cộng. Nâng thật = 1 lệnh `submit_final_from_sample` theo task nháp (`core/adapters/clipai.py:610-620`), KHÔNG gửi lại ref → giá nâng theo đúng
   cách đó. Test dựng nhóm theo `sent_group` khi cờ ref tắt, giây theo clip thật, follower.

7. **Đơn giá nâng 1080p ĐO THẬT (hộp thư 11/10 23:53):** Seedance 2.5 nháp 480p → 1080p 9:16 qua `submit_final_from_sample` = **0,5254 USD/s**
   (7 clip #24 job 670–676, 38 s, 19,964 USD theo `task_usage`; ≈ 0,0107 USD/1k token; clip có video vào cùng giá) → đưa vào bảng giá
   (`data/pricing.json` mẫu trong repo / hằng trong `core/quality_tier.py`) thay nhãn `UPGRADE_UNMEASURED` (`quality_tier.py:41`), ghi nguồn đo.
   `usage_events` ghi SAI giây clip nhóm bản cao (671: 4 thay 8, 672: 4 thay 5, 675: 4 thay 6): tìm chỗ ghi (`core/runner.py:457/461`
   `_record_usage` → `core/cost.record_usage`) — nếu sửa được ở `core/cost.py` (tính giây từ nhóm/clip thật) thì sửa + test; nếu phải sửa
   `runner.py` thì CHỈ viết báo cáo + test đỏ `xfail` (file #24). Runner không cắt follower từ clip nhóm 1080p (02/03/09.mp4 còn 480p) — file #24:
   chỉ báo cáo cách sửa, làm sau #24.

## Việc 4 — Kho phiếu / trang Phiếu / pet (Đợt 9) — lỗi TRUNG
1. `core/tickets.py:~165-174` gộp vào phiếu `closed`/`resolved` im lặng → tự chuyển `reopened` có event.
2. `user_projection` (`:~252-257`) không xét trạng thái → phiếu đóng vẫn báo "tạm dừng"; phiếu không chặn vẫn trả tiêu đề → trả None khi đóng hoặc
   không chặn.
3. `devsys/app.py` (sidebar): còn `?ticket=` thì bấm trang khác vẫn hiện Phiếu → chỉ chuyển trang ở lần mở đầu (session_state) hoặc xóa query param.
4. `tools/lao_dai/logic.py:~60` bong bóng đếm mọi trạng thái khác `closed` → chỉ `waiting_admin` (+ đỏ/vàng); toast chỉ việc cần admin hành động.
5. `tools/lao_dai/broker.py:~59` gọi `admin_snapshot(c)` thiếu `data_dir` → `gen_done` luôn rỗng; WAIT_REASONS không có trong tiến trình broker.
6. **Ảnh chụp trang Phiếu 11/10 (`docs/images/d9/trang_phieu_mo_phieu_1440.png`):** (a) chi tiết phiếu hiện JSON thô (`impact`, `cause`) → viết thành câu tiếng Việt (ảnh hưởng: chặn shot 10, ≈ 0,12 USD; nguyên nhân: đoán — …; bằng chứng: job 651…); (b) hạn hiện ISO UTC `2026-10-11T08:23:13+00:00` → giờ VN `11/10 15:23` + "còn/quá N h"; (c) hàng ghi "tiền chưa rõ" dù `impact.money_usd = 0.12` → đọc đúng khóa tiền (một nguồn với `core/tickets.py`); (d) sidebar vẫn chọn trang cũ khi mở bằng `?ticket=` (cùng lỗi mục 3).
THẤP: `due_status` bỏ qua phiếu đã xong; `blocked`/`waiting_info` quay về trạng thái trước (không về `triaged`); `_safe` chặn mọi đường dẫn tuyệt đối
(cả `/tmp`); `spend_today` theo giờ VN; `ThreadingHTTPServer` + timeout. Đợt 9 việc 3 phần GUI/khay/toast/launcher/ảnh: làm tiếp theo đề Đợt 9.

## Việc 5 — Tổ rà soát báo nhầm khung đầu ↔ cuối (hộp thư 11/10, ca thật #24)
Ca thật #24 11/10: mục 84, 90/92/93, 102/105, 111 ("khung đầu không khớp trạng thái cuối"), 109 ("4 s chỉ một pha" dù motion chia 4 nhịp) — mỗi lần
tốn tiền rà + người dùng phải bỏ qua. Gốc: `prompts/30_change_review.md` mục 1 bắt `blocking`/`image_prompt` (KHUNG ĐẦU) khớp `end_state`
(trạng thái CUỐI). Sửa:
1. Prompt: thêm nguyên tắc rõ — `image_prompt`, `blocking`, ảnh đã duyệt = **khung đầu** (`byd.hanh_dong[].bat_dau`); `action`/`motion_en` = **quá
   trình** đầu → đỉnh → cuối; `end_state`, `byd...ket_thuc` = **khung cuối**. Chỉ so cùng loại khung; khung đầu khác trạng thái cuối là BÌNH
   THƯỜNG. Đếm pha theo nhịp trong `motion_en`/BYĐ, không theo câu.
2. Code (`core/change_review.py` khi dựng đề): gắn nhãn khung cho từng trường trong "Các shot liên quan" (vd `image_prompt (khung đầu)`,
   `end_state (khung cuối)`), để Claude không lẫn. Đây là đổi hành vi Tổ rà soát đang chạy với #24 → cờ mới `change_review_frames` (TẮT); cờ tắt
   đề giống từng byte.
3. Ca vàng `knowledge/checks/` (L13 hoặc file mới) + test: dựng lại tối thiểu 3 mục trên từ mô tả (khung đầu đứng, cuối ngã → không được báo lệch;
   motion 4 nhịp / 4 s → không báo "một pha"), kiểm đề có nhãn khung và nguyên tắc; không gọi Claude thật.

## Việc 6 — Cảnh không được đơ: lớp chuyển động nền (góp ý người dùng 11/10 khi xem nháp v3 #24)
Cảnh quan xung quanh, mây trôi, sương khói lan, lá/cỏ lay, đèn/lửa chập chờn… phải có chuyển động nền nhẹ, kể cả shot máy tĩnh (vd #24 shot 9).
Theo công thức chung:
1. **Luật cho prompt viết motion** (Đạo diễn / `core/prompt_formula.py` / prompt motion — tìm đúng chỗ viết `motion_en`): mỗi motion có một lớp
   "chuyển động nền" chọn theo bối cảnh + thời tiết + giờ trong BYĐ / `location` / `weather` (không trái thời tiết: trời lặng thì không gió lớn, trong
   nhà không mây…), có lý do. Sau cờ mới `ambient_motion` (TẮT) — cờ tắt prompt giống từng byte.
2. **Kiểm bằng code VÀNG** khi motion prompt không có lớp chuyển động nền (nhận theo danh sách từ khóa/khóa có cấu trúc — không bắt Claude kết
   luận), kể cả shot máy tĩnh; VÀNG có lý do + gợi ý theo bối cảnh. Không chặn gen.
3. `knowledge/checks/` ca thật #24 shot 9 (máy tĩnh, cảnh đơ) + đăng ký `devsys/areas.json` + test (có cờ / không cờ, trời lặng không sinh gió).

## Kết quả Codex — đợt 10

(Codex ghi: việc · nhánh · commit · bằng chứng · việc mở.)

---

# ĐỢT 11 — Bàn dựng đạo diễn 3D: tấm duyệt đủ góc, Đạo diễn khai sơ đồ khối, Trình sửa sân khấu (người dùng duyệt 11/10 tối)

**NGUYÊN TẮC (người dùng chốt 11/10 tối): sân khấu do ĐẠO DIỄN (AI) DỰNG SẴN tự động cho mọi cảnh, nối theo các cảnh trước; người dùng KHÔNG dựng
từ đầu — chỉ xem và CHỈNH từng cảnh khi cần.** Hệ quả cho cả đợt:
- Mặc định: Đạo diễn khai sơ đồ khối + chỗ đứng/tư thế theo nhịp (đầu/đỉnh/cuối) cho TỪNG cảnh, kế thừa vị trí cuối của cảnh trước (liên tục) →
  code kiểm số + bộ giải tự đặt máy → tấm duyệt từng cảnh sẵn để xem. Người dùng không phải thao tác gì nếu không thấy sai.
- Trình sửa là công cụ CHỈNH MỘT CẢNH: mở đúng cảnh, sửa vị trí/tư thế/máy của cảnh đó; code tính lại và ĐỀ XUẤT lan sang các cảnh sau bị ảnh hưởng
  (vị trí cuối cảnh này = đầu cảnh sau) — người dùng chấp nhận / bỏ từng cảnh; cảnh ĐÃ DUYỆT không tự đổi (chỉ báo `layout_drift`).
- Chỉnh tay của người dùng được giữ khi Đạo diễn dựng lại (như khóa `_user_locked`), Đạo diễn nhận chỉnh đó làm ràng buộc cho các cảnh sau.
- Ưu tiên tối ưu: xem nhanh từng cảnh (lật cảnh trước/sau, so với cảnh trước) và sửa ít bấm; KHÔNG làm công cụ dựng sân khấu tự do từ đầu.

Đầu vào: `docs/PHUONG_PHAP_SAN_KHAU_3D.md` mục 2 (lưới), 12b (Nhánh C), 13 (hai chiều Director ↔ code), 14 (stage_facts); thiết kế "Trình sửa
sân khấu" ở `docs/NGHIEN_CUU_TU_PHUC_VU_DASHBOARD.md` (đoạn "Trình sửa sân khấu") + `docs/THIET_KE_TIEU_NHI_LAO_DAI_D7.md` mục 6 (thứ tự tính
năng). Đã có trên main: `core/blockout.py` (kiểm số), `core/blockout_sheet.py` (tấm nhìn từ trên + gói `blockout` có người duyệt/SHA; ảnh ví
dụ `docs/images/d9/tam_duyet_san_khau_vi_du.png`), `core/stage_grid.py`/`core/stage_solver.py`/`core/stage_facts.py`, `tools/stage_grid.py`
(v2/v3), `tools/render_plates.py` `add_props`, `core/whitebox.py`, `core/plates3d.py` `find_blender`.
Luật chung GIỐNG đợt 1 + thêm: mỗi việc một nhánh `codex/d11-viec<N>-<tên>` từ `origin/main`; KHÔNG sửa `core/runner.py`, `core/lock_exceptions.py`,
`core/end_frames.py`, `core/place_refs.py`, `core/scene_storyboard.py` và KHÔNG đọc/ghi `data/projects/24/` (#24 đang chạy trên sân khấu đó);
không API tốn tiền (Director thật chỉ chạy khi người dùng duyệt báo giá). Hành vi mới sau cờ TẮT. Ghi kết quả vào "Kết quả Codex — đợt 11".

**MÀN CAMERA (người dùng yêu cầu 11/10 tối, mẫu "Bàn đạo diễn" của Clip AI — `docs/CLIPAI_FEATURES.md` mục "Bàn đạo diễn": giao diện 3D đặt
camera/nhân vật, "Góc nhìn đạo diễn" / "Góc nhìn camera"):** mỗi cảnh phải có màn cho thấy máy quay ĐANG QUAY THẾ NÀO và chỉnh được máy đó:
- **Hai góc nhìn chuyển qua lại:** "Góc nhìn đạo diễn" (toàn sân khấu nhìn từ trên/xiên, thấy vị trí máy + hình nón tầm nhìn + nhân vật + khối)
  và "Góc nhìn camera" (đúng khung hình máy thấy: ảnh clay/nền 3D render từ máy, khung tỉ lệ dự án 9:16/16:9, vạch vùng an toàn, nhãn cỡ cảnh,
  đường chân trời, vị trí mắt nhân vật theo % khung — dùng `core/plate_camera.py` `camera_for`/`project`/`horizon_y`/`vfov`).
- **Chỉnh máy:** vị trí (kéo trên góc nhìn đạo diễn hoặc nhập mét/tên ô), cao, hướng (yaw), ngửa/cúi (pitch), tiêu cự / cỡ cảnh (WS/MS/MCU/CU…),
  góc (ngang mắt / thấp / cao / qua vai / POV); chuyển động máy đầu → cuối (`camera_move`: đẩy, kéo, lia, theo…) có điểm đầu/điểm cuối và xem
  lại cả đường đi. Mỗi lần chỉnh: kiểm số ngay bằng luật sẵn có (`plate_camera` clearance/khoảng cách tối thiểu/máy thấp không ngửa quá,
  `stage_facts` nhìn thấy gì, chân trời, che khuất) → ĐỎ/VÀNG có nút sửa; xem trước góc nhìn camera clay 0 USD.
- **Mặc định Đạo diễn/bộ giải đặt máy sẵn** (theo NGUYÊN TẮC trên); người dùng chỉ chỉnh khi thấy sai; chỉnh tay khóa lại, lan đề xuất như vị trí
  nhân vật. Đổi máy của cảnh đã có ảnh duyệt → VÀNG "ảnh cần vẽ lại", không tự gen.
- Tùy chọn sau (ghi vào thiết kế, chưa làm): quay "video white model" theo đường máy làm video tham chiếu chuyển động (như Previs Stage của
  Seedance), dùng Blender của dự án — báo giá 0 USD, chỉ tốn máy.

## Việc 1 — Thiết kế + mockup Trình sửa sân khấu (tài liệu + HTML; làm ngay)
1. `docs/THIET_KE_BAN_DUNG_3D_D11.md` (theo NGUYÊN TẮC trên — Đạo diễn dựng sẵn, người dùng chỉ chỉnh từng cảnh): luồng người dùng trên Dashboard (bước 1, cạnh "Đạo diễn"): lật xem từng cảnh đã dựng sẵn (nhìn từ trên + góc máy, so cảnh trước); khi cần chỉnh
   → kéo/nhập vị trí nhân vật (mét, theo tên ô lưới), hướng mặt, tư thế theo nhịp (đầu/đỉnh/cuối của BYĐ) → kéo/nhập máy (vị trí, cao, hướng,
   tiêu cự) hoặc "giải máy" bằng bộ giải → kiểm số ngay (stage_facts, chồng lấn, nhìn thấy, `layout_drift` với shot ĐÃ DUYỆT) → xem trước 3D
   0 USD (render clay cục bộ, một worker, có hàng đợi) → lưu thành phiên bản mới của sân khấu (bản sao dự án, có hoàn tác, ai/lúc/lý do) →
   shot bị ảnh hưởng hiện VÀNG "ảnh cần vẽ lại" (không tự gen). Ghi rõ: dữ liệu lưu ở đâu (so `stage_v2_*/blocking.json`, `shot_specs.json` hiện
   dùng bằng CLI), chỗ nối với `tools/stage_grid.py` (gọi lại hàm có sẵn, không viết bộ giải mới), quyền (đồng nghiệp sửa bản sao dự án; Kho
   chung chỉ Owner), cách Tiểu Nhị gọi lại đúng chức năng này. Chấm tần suất × công sức (lỗi #24 11/10: vị trí sau động tác di chuyển 0,25 m
   → 1,25 m, bố cục shot đã duyệt bị đổi).
2. Mockup `mockup/ban_dung_3d.html` (offline) — có MÀN CAMERA đủ như trên (nút chuyển "Góc nhìn đạo diễn" ↔ "Góc nhìn camera", chỉnh vị trí/cao/hướng/ngửa/tiêu cự/cỡ cảnh/chuyển động máy, kiểm số + xem trước khung), mở sẵn danh sách cảnh Đạo diễn đã dựng (lật trước/sau, so cảnh trước); chế độ chỉnh MỘT cảnh gồm bản đồ lưới (dùng đúng tên ô K11 = gốc O như `stage_grid.cell_name`), nhân vật + máy kéo được,
   ô nhập số, thanh nhịp đầu/đỉnh/cuối, bảng kiểm ĐỎ/VÀNG có nút sửa ngay, khung "xem trước clay", danh sách cảnh sau bị ảnh hưởng với nút chấp nhận / bỏ từng cảnh (cảnh đã duyệt chỉ báo, không tự đổi). Dựng theo ca #24
   (giếng, yêu nữ bò ra cách thành 1,25 m, Kelly lùi). Kiểm Playwright 1440 và 1280: 0 lỗi console, không cuộn ngang; test grep/JS nhẹ
   (khai `devsys/areas.json` khu `dashboard_ui`, không tăng version).

## Việc 2 — Tấm duyệt đủ góc clay + Đạo diễn khai sơ đồ khối (code sau cờ; render kiểm trên máy chính có Blender)
0. **Render "góc nhìn camera" clay từng cảnh** (0 USD, Blender cục bộ, dùng camera của `core/plate_camera.camera_for` như render nền hiện có) cho màn camera; không Blender → khung vẽ 2D chiếu từ `project` + lý do.
1. **Góc clay:** từ plan khối đã kiểm (`core/blockout.py` `to_props`), dựng Blender bằng `tools/render_plates.py` `add_props` + `core/whitebox.py`
   (KHÔNG bộ dựng mới), render 2–3 góc clay có nhãn khối; ghép cùng tấm nhìn từ trên (`blockout_sheet.render_top_view`) + ảnh tham chiếu
   bối cảnh (nếu có) thành MỘT tấm duyệt (mục 12b.2). Blender không có / lỗi → tấm chỉ có nhìn từ trên + dòng "chưa render góc clay: <lý do>",
   không im lặng. Khối `tru`/`cot` vẽ tròn trên tấm nhìn từ trên (đang vẽ vuông). Cờ `blockout_clay_sheet` TẮT. Test: bpy giả / kiểm lệnh
   dựng (như `tests/test_plates_f2.py`); render thật ghi ảnh vào `docs/images/d11/` khi chạy trên máy chính.
2. **Đạo diễn khai sơ đồ khối (đường MẶC ĐỊNH dựng sẵn cho mọi cảnh, kế thừa vị trí cuối cảnh trước, tôn trọng chỉnh tay đã khóa):** thêm phần khai `blockout` (JSON enum theo 12b.1, không văn tự do) vào prompt Đạo diễn liên quan
   (`prompts/29_director_stage_specs.md` hoặc prompt mới), CHỈ khi cờ `director_blockout` BẬT — cờ tắt prompt giống từng byte. Code nhận → kiểm số
   (`core/blockout.py`) → lỗi gửi lại Đạo diễn ≤ 2 lượt (mục 13) → còn lỗi VÀNG có lý do. Ước tính chi phí trước mỗi lời gọi, qua sổ chi.
   Test bằng Claude giả (không gọi thật).
3. Thử nghiệm thu 12b.4 ở mức dữ liệu giả: 3 bối cảnh (trong nhà, ngoài trời, có bậc) dựng + kiểm < 2 phút, ca hồi quy thiếu khối / chồng lấn bị
   bắt. Ghi rõ phần nào cần chạy thật trên máy chính (Blender, ảnh Kho thật) — phiên rà Codex chuyển qua hộp thư.

## Việc 3 — Trình sửa sân khấu thật trên Dashboard (SAU khi #24 xong — chỉ bắt đầu khi hộp thư có dòng phiên máy chính báo #24 xong)
Theo thiết kế việc 1 đã duyệt (gồm MÀN CAMERA: hai góc nhìn, chỉnh máy, kiểm số, xem trước khung camera clay): màn trên Dashboard sau cờ `stage_editor` TẮT; đọc/ghi bản sao sân khấu của dự án qua hàm có sẵn của
`tools/stage_grid.py` / `core/stage_*` (tách hàm thuần nếu cần, không đổi hành vi CLI); xem trước clay 0 USD một worker; lưu phiên bản + hoàn tác;
`layout_drift` báo shot đã duyệt bị đổi; không tự gen ảnh. Test AppTest + Playwright (≤ 2 bấm để dời một nhân vật 1 m và xem lại kiểm số).
Đề bài chi tiết có thể chỉnh sau khi người dùng duyệt thiết kế việc 1.

**Việc nhỏ đưa vào thiết kế việc 1 và làm ở việc 3 (người dùng 11/10):** phím tắt, hoàn tác nhiều bước, chép máy sang shot kế, khóa trục khi kéo;
khung an toàn 9:16 (vùng giao diện TikTok/Reels che); dùng lại ảnh clay theo mã băm máy + khối (chỉ render lại khi đổi); Tiểu Nhị đề xuất chỉnh máy
("nâng máy 0,3 m để không thấy miệng giếng") qua đúng chức năng này, người bấm duyệt.

## Việc 4 — Kiểm luật quay phim + vòng kiểm sau gen (code, 0 USD; cờ `film_grammar_check`, `camera_match_qc` TẮT; người dùng duyệt 11/10)
1. **Luật quay phim giữa các shot liền** (code, không Claude): trục 180° (hai nhân vật / hướng chuyển động không đổi bên vô cớ), hướng nhìn khớp
   (eyeline), đổi góc ≥ 30° giữa hai shot cùng chủ thể (tránh jump cut), khoảng trống phía trước mặt / hướng đi (lead room), khoảng trống trên đầu
   theo cỡ cảnh. Tính bằng `plate_camera.project` + vị trí/hướng mặt trong BYĐ + sân khấu. Vi phạm → VÀNG có lý do + gợi ý (dời máy X m / đổi góc),
   hiện trên màn camera và trong "Trước khi chạy". Ngoại lệ có chủ ý (`byd.ngoai_le` kiểu cắt nhảy cố ý) không báo.
2. **Vòng kiểm sau gen:** ảnh / khung đầu-cuối của clip làm ra so với máy đã đặt: cỡ cảnh, chân trời, vị trí + độ cao mắt nhân vật trong khung (đo
   bằng công cụ sẵn có — `core/plate_layout_qc.py`, `core/clip_measure.py`; không đoán bằng Claude). Lệch quá ngưỡng → VÀNG + gợi ý gen lại (có báo
   giá), không tự gen. Ngưỡng ghi "chưa hiệu chỉnh" tới khi đo trên ca thật (#24: ảnh thấy miệng giếng dù máy thấp).
3. Ca vàng `knowledge/checks/` + test đỏ → xanh (vượt trục, cùng góc liền nhau, lệch chân trời).

## Việc 5 — Animatic clay + bộ góc máy dùng lại + xuất vào gói gửi (cờ `clay_animatic`, `camera_setups_reuse`, `clay_refs_in_package` TẮT)
1. **Animatic clay toàn cảnh (0 USD):** ghép mọi shot thành một video xám theo nhịp BYĐ và thời lượng shot, nhân vật khối di chuyển theo nhịp,
   máy chạy theo `camera_move`; render Blender cục bộ một worker + ghép ffmpeg (`core/delivery`/`core/ffmpeg_studio`). Xem trên màn bàn dựng; không
   Blender → animatic 2D từ góc nhìn đạo diễn + lý do.
2. **Bộ góc máy dùng lại cho cả cảnh:** mỗi cảnh 3–4 góc chuẩn (toàn / trung / qua vai / phản góc) do Đạo diễn + bộ giải đặt (hướng G0 đã chốt 09/10,
   xem `TODO.md` "làm G0 TRƯỚC"); shot chọn lại góc chuẩn thay vì máy riêng; so A/B hai phương án máy cạnh nhau, chọn một bấm.
3. **Xuất vào gói gửi:** khung đầu/cuối clay theo máy làm "ảnh bố cục", video white model theo đường máy làm video tham chiếu chuyển động — qua
   "Gói gửi kèm" (`core/package_overrides.py`, Đợt 8) với vai rõ ràng; KHÔNG gửi ảnh clay như ảnh nền để chép (bài học #24 shot 8, mục 12b.3) — chỉ
   vai bố cục/chuyển động, model nào không nhận vai đó thì không gửi + lý do. Phần nối vào đường gửi job làm SAU #24 (cùng việc 3).
4. Test: bpy giả / ffmpeg nhỏ (slow nếu ≥ 8 s); dữ liệu giả 3 shot.

## Kết quả Codex — đợt 11

- ✅ Việc 1 — nhánh `codex/d11-viec1-ban-dung`, mã `867e9ac`. Thiết kế bàn dựng 3D và mockup offline hai góc nhìn; Playwright Chrome thật kiểm kéo actor/camera, đổi lens, beat, undo, khóa cảnh đã duyệt và nhận/từ chối đề xuất. Test đỏ → xanh: 1 passed (4,01 s); hai kích thước 1440/1280 không lỗi console, không tràn ngang. Bốn ảnh ở `docs/images/d11/`; rà tại `docs/RA_D11_VIEC1_CODEX_2026-10-12.md`. Preview SVG minh họa; Blender/solver/ACL/cache thật thuộc phần triển khai tiếp. Chưa chạy cả bộ; không gộp main.


(Codex ghi: việc · nhánh · commit · bằng chứng · việc mở.)

---

# ĐỢT 12 — Âm thanh theo từng chuyển động (hộp thư phiên máy chính 11/10 23:28, làm tay #24 nháp v3; người dùng phân công phiên rà Codex)

Nguồn: `D:\AI-Video-Output\2026-10-11_du-an-24\bang_am_thanh.md` + `nhap_v3_am_thanh.mp4` trên máy chính (cloud không đọc được — dựng ca thử từ mô
tả dưới). Luật chung GIỐNG đợt 1; nhánh `codex/d12-viec<N>-<tên>`; KHÔNG sửa file #24 (runner/lock_exceptions/end_frames/place_refs/
scene_storyboard); không API tốn tiền khi test; đổi hành vi sau cờ TẮT (trừ việc 1 là sửa lỗi). Ghi kết quả vào "Kết quả Codex — đợt 12".

## Việc 1 — LỖI âm nền không bao giờ được chọn (nhỏ; sửa thẳng, không cờ)
`core/ambience.py:51` lọc `voice=0`, nhưng `core/sound_ai.py:137` `summary` đặt `voice=True` cho MỌI âm không thuộc `ACCENT` (dế, gió…) → #24 cả 10 shot
`ambience.choose` trả None dù Kho có #437 dế, #307 gió. Tách nghĩa: `voice` = giọng người; thêm trường riêng (vd `accent`) cho "không phải điểm
nhấn" (migration cột `sounds` theo cách `core/db.py` thêm cột; dữ liệu cũ tính lại từ `heard_label` khi đọc, không cần nghe lại). Kiểm mọi chỗ đọc
`voice` (grep) — điểm nhấn (`sfx_plan`/`sound_lib`) vẫn không lấy giọng người. Test đỏ → xanh với Kho giả có dế/gió/giọng nói.

## Việc 2 — SFX theo nhịp chuyển động (vừa; cờ `motion_sfx` TẮT)
Hiện `scenes.data.sound` của Đạo diễn chỉ 1–2 sfx/shot, không mốc giây, không theo nhịp BYĐ (#24 shot 2/6 trống; shot 7 còn ghi "glitch" dù đã đổi
sương đỏ); `sfx_plan` gọi Claude chỉ "ít điểm nhấn". Làm:
1. Sinh danh sách sfx THEO NHỊP từ BYĐ `hanh_dong[].bat_dau/dinh/ket_thuc` + động từ chuyển động (bước chân, vút, ngã, bám/trườn, bò, biến hình,
   nấc, nhích/chạm…) — bảng ánh xạ động tác → loại âm (code, không Claude), Claude chỉ bổ sung khi bảng không phủ (báo giá trước).
2. Mốc giây ĐO từ clip (hiệu khung hình / `core/clip_measure.py` `motion_series`) thay vì đoán; không đo được → mốc theo nhịp BYĐ chia đều + VÀNG.
3. Phát hiện sfx lỗi thời: trường `sound` nhắc thứ không còn trong motion/BYĐ/`post_fx` hiện tại (vd "glitch" sau khi đổi sương đỏ) → VÀNG.
4. Khung "âm hậu kỳ" cho `post_fx` (nhiễu sóng → tiếng rè/nhiễu) dùng chung lược đồ `core/post_fx.py`.

## Việc 3 — Âm của video ref hành động + mix (vừa; cờ `ref_audio_sync` / `mix_bus` TẮT)
1. Ghép âm ref của video ref hành động khớp động tác: ref → đoạn giây nguồn → shot, co giãn `atempo` theo tỉ lệ làm chậm ref; `motion_ref/*.mp4`
   đã cắt mất tiếng → lấy âm từ file ref gốc (đường dẫn ghi trong ref), thiếu → VÀNG, không im lặng. Dùng lại `core/ref_audio.py` nếu phù hợp.
2. Mix: nén nhạc theo bus hiệu ứng (sidechain ffmpeg) + kiểm số "nhạc dưới hiệu ứng 8–12 dB" + loudnorm −14 LUFS cho điện thoại (đọc
   `core/delivery.py`/`core/ffmpeg_studio.py` loudness hiện có, không làm song song). Test ffmpeg thật cỡ nhỏ (slow nếu ≥ 8 s).

## Việc 4 — Kho âm thanh còn thiếu (nhỏ; chỉ báo cáo + công cụ)
Liệt kê theo ca #24: vải sột soạt / lết gối trên đá, tiếng chạm vai, chuông tháp lớn, sương/khói bùng (biến hình), nhạc kinh dị–bi thương có nhãn
mood dùng được (AST mood ≈ 0 với mọi bản Kho). Viết `docs/KHO_AM_THANH_CAN_BO_SUNG.md` (nguồn miễn phí/có giấy phép đề xuất, người dùng duyệt
trước khi tải) + đo vì sao mood ≈ 0 (nhãn AST không có mood → đề xuất cách gán mood: tay / mô hình khác) — không tải gì về Kho.

## Việc 5 — Thoại ĐỒNG THANH (hộp thư 12/10 00:55, #24 shot 12; cờ `unison_dialogue` TẮT)
#24 shot 12: hai nhân vật cùng nói "…chỉ có 2 hành động sắp ra mắt!" — phiên máy chính phải chỉnh tay `audio_assets` (dòng 1 trỏ file mix, dòng 2
`file=''` + `solo_file`). Làm: trường `unison` cho dòng thoại (≥ 2 người nói cùng lúc), TTS từng người → mix canh cùng điểm đầu (lệch từng chữ ≤ 0,06 s,
đo bằng năng lượng/onset), bản dựng (`core/delivery.py`) + khớp môi đọc `unison` đúng (không nối tiếp hai câu). Thiếu một giọng → VÀNG, không im lặng.
Test dữ liệu giả 2 giọng.

## Việc 6 — TTS đọc lệch từ (hộp thư 12/10 00:55: giọng 70 đọc "Trồi Lên" thành "Gồi/Chôi lên"; cờ `tts_pronunciation` TẮT)
Từ điển phát âm theo giọng/dự án (từ → cách viết cho TTS hoặc SSML/phoneme nếu provider hỗ trợ — đọc adapter TTS hiện có trước), áp trước khi gửi; kiểm
sau TTS bằng nhận dạng giọng nói sẵn có (whisper nếu đã có trong dự án; không thêm dịch vụ tốn tiền) so chữ gốc → lệch thì VÀNG + gợi ý thêm từ điển,
không tự gen lại quá 1 lần (luật gen lại phải đổi đầu vào). Ca thật: "Trồi Lên" (`tts_31339` → "Gồi lên", `tts_31340` → "Chôi lên").

## Kết quả Codex — đợt 12

(Codex ghi: việc · nhánh · commit · bằng chứng · việc mở.)

---

# ĐỢT 13 — dọn tồn đọng THẤP (sổ việc 📒 nhóm G, 12/10; người dùng duyệt)

Đăng nhập admin 8502 (sổ việc nhóm F) do **phiên rà Codex** làm (Codex không tự đăng nhập được để kiểm): `devsys/admin_auth.py` — Codex KHÔNG
sửa file này; nếu cần thao tác ghi trên 8502 thì gọi `admin_auth.current()` / `is_owner()` như `devsys/tickets_page.py`.
Luật chung GIỐNG đợt 1; nhánh `codex/d13-viec<N>-<tên>`; KHÔNG sửa file #24; không API; mỗi lỗi test đỏ → xanh. Ghi "Kết quả Codex — đợt 13".

## Việc 1 — Hậu kỳ `post_fx` (Đợt 6) — 5 mục nhỏ
1. `core/post_fx.py:69` tên `post_fx_<sid>_<uuid>.mp4` làm `_post_fx/` phình — tên cố định theo shot + băm spec, hoặc dọn bản cũ trước khi ghi.
2. `core/delivery.py:640-642` post_fx áp SAU `_hold_end` → `vi_tri: cuoi` rơi vào khung giữ; áp TRƯỚC `_hold_end` (hoặc ghi rõ quyết định) + test.
3. Chưa prompt / màn nào ghi `post_fx` đúng lược đồ: thêm lược đồ vào `knowledge/roles/director_p24_1110.md:24` (sau cờ `p24_lessons` — cờ tắt
   prompt giống từng byte).
4. `delivery.status()` không coi bản dựng là cũ khi `post_fx` hoặc cờ đổi → thêm vào khóa so.
5. Editor (prompt 24 / rough_cut) không biết glitch là chủ ý → truyền `manifest.post_fx` vào ngữ cảnh Editor (sau cờ `post_fx_render`); test ffmpeg
   thật skip khi thiếu filter `rgbashift` (thay vì đỏ).

## Việc 2 — Tấm duyệt khối (Đợt 2 việc 3) + mã quy trình (Đợt 3)
1. `core/blockout_sheet.py` `_font`: `ImageFont.load_default(size=)` cần Pillow ≥ 10.1 — dò phiên bản / fallback, hoặc nâng `requirements.txt`.
2. SHA plan khác giữa `3` và `3.0` dù hình học giống → chuẩn hóa số trước khi băm (giữ đọc được gói cũ: SHA cũ vẫn khớp với dữ liệu cũ — có test).
3. `ngay` không múi giờ vẫn nhận → yêu cầu ISO có múi giờ / UTC, gói cũ đọc được kèm VÀNG.
4. Skill `.claude/skills/vong-lam-viec-theo-plan/SKILL.md` (mục ghi số đo) chưa nói mã K (`K0b-TD5`) và CX (`CX-d2-1`) — thêm một câu + ví dụ.

## Việc 3 — Mockup Tiểu Nhị / pet (Đợt 7)
1. `tests/test_mockup_tieu_nhi_d7.py` chỉ grep chuỗi → thêm kiểm JS bằng Playwright (ĐỎ → XANH khi sửa ngay, chặn gen trùng, `min="0"` gắn đúng
   `#distance`, pet không có nút "Duyệt", câu "đã báo admin, dự án tạm dừng ở shot này") — đánh `slow` nếu ≥ 8 s.
2. `mockup/tieu_nhi.html` `lastGenerated` chỉ nhớ lần gen cuối (gen 1,2 → 1,3 → quay về 1,2 gen lại được) → nhớ tập đầu vào đã gen.
3. `mockup/lao_dai_pet.html` dáng thường vẫn hiện danh sách 3 phiếu chờ → dáng thường ẩn danh sách / hiện "không có phiếu chờ".

## Kết quả Codex — đợt 13

(Codex ghi: việc · nhánh · commit · bằng chứng · việc mở.)

---

# ĐỢT 14 — QC ảnh chấm sai + job tự sửa kẹt hàng đợi (hộp thư 12/10 00:55, #24 shot 11–12)

Luật chung GIỐNG đợt 1; nhánh `codex/d14-viec<N>-<tên>`; KHÔNG sửa file #24 (runner/lock_exceptions/end_frames/place_refs/scene_storyboard);
không API tốn tiền khi test; đổi hành vi sau cờ TẮT (#24 đang chạy bằng QC + vòng nền hiện tại). Ghi "Kết quả Codex — đợt 14".

## Việc 1 — QC ảnh "nhìn đúng nhưng kết luận sai" (cờ `qc_observe_enum` TẮT)
Ca thật: ảnh 678 bị chấm "váy phải đen" dù váy đen, mặt đúng; 680 "thiếu giếng, chân không đỏ" dù có → ảnh đạt bị loại/giữ, tốn gen lại. Hướng (theo luật
dự án "model khai, code kết luận"): model QC chỉ KHAI quan sát dạng enum theo từng mục kiểm (`thay` / `khong_thay` / `khong_chac` + vùng) cho từng đặc
điểm trong khóa nhân vật / BYĐ (`core/qc_spec.py` `compile_frame` đã có danh sách đặc điểm), CODE so với yêu cầu và quyết điểm/ĐẠT. `khong_chac` → VÀNG,
không trừ điểm như sai. Đọc `core/qc_agent.py`, `core/qc_rules.py`, `core/qc_policy.py`, `knowledge/checks/` trước, dùng lại khung khai báo sẵn có
(vd `qc_measure`, `lock_exceptions` — chỉ ĐỌC). Ca vàng: dựng lại 678/680 từ mô tả (câu trả lời model giả) → bản cũ trừ điểm sai, bản mới qua. Test không
gọi Claude thật.

## Việc 2 — ✅ PHIÊN RÀ CODEX ĐÃ LÀM (12/10 01:14, Codex BỎ QUA việc này) — Job tự sửa (origin `auto`) kẹt `queued` khi không có chạy tự động (cờ `auto_send_self_fix` TẮT)
`core/bg_poll.py:73` bỏ qua mọi job `origin='auto'` (dành cho autopilot tự gửi). Nhưng job do QC tự sửa / gen lại (`core/regen.py`, `core/pipeline.py`…
— tìm chỗ đặt `origin='auto'`) cũng mang `auto` khi KHÔNG có autopilot → không ai gửi, kẹt queued (#24 job 679/680 phải `submit_pending` tay). Sửa: phân
biệt job của autopilot với job tự sửa ngoài autopilot (origin riêng, vd `self_fix`, hoặc bg_poll gửi `auto` khi dự án không có autopilot đang chạy/xếp
hàng) — vẫn qua đúng `runner.submit_pending` (cổng tiền, trần, throttle); gửi tự động phải tôn trọng ủy quyền/trần dự án (không chi khi người dùng chưa
cho tự duyệt). Chỉ sửa `core/bg_poll.py` + chỗ đặt origin; KHÔNG sửa `core/runner.py`. Test: dự án không autopilot có job tự sửa → được gửi (cờ bật) /
giữ nguyên (cờ tắt); dự án có autopilot → bg_poll không gửi trùng.

## Kết quả Codex — đợt 14

(Codex ghi: việc · nhánh · commit · bằng chứng · việc mở.)
