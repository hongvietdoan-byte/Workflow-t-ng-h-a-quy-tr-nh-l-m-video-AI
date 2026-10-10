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
