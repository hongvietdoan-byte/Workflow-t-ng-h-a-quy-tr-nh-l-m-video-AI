# Việc giao Codex (nhánh riêng) — 10/10/2026

5 việc **thuần code + test**: không cần `data/`, khóa API, Blender hay máy chính. Làm theo thứ tự; làm được tới đâu thì
dừng ở đó, mỗi việc **một nhánh riêng** (hoặc một commit riêng nếu chung nhánh) để gộp từng phần. Phiên Claude điều phối sẽ rà theo quy ước 7
(`CLAUDE.md`), chạy cả bộ test rồi mới gộp vào `main`.

# 📋 TRẠNG THÁI + THỨ TỰ CÒN LẠI — ĐỌC TRƯỚC (phiên rà Codex cập nhật 12/10 17:05; bảng này THẮNG mọi câu thứ tự/điều kiện cũ bên dưới)

**#24 XONG 12/10; #27 Booyah ĐANG CHẠY trên máy chính.** KHÔNG đọc/ghi `data/projects/`. `core/runner.py`, `lock_exceptions.py`, `end_frames.py`,
`place_refs.py`, `scene_storyboard.py`, `plate_camera.py`, `plate_choice.py` chỉ sửa TỐI THIỂU khi gốc lỗi nằm đó, sau cờ, ghi dòng + lý do trong báo cáo RA.
Mọi câu "#24 đang chạy / chờ #24 xong / không đọc data/projects/24" bên dưới: coi như câu này. Việc ghi "chờ #24" = MỞ, trừ khi chạm đường gửi job của #27
(nhóm "runner sau #24" cuối danh sách — chờ người dùng chốt).

**ĐÃ XONG — KHÔNG LÀM LẠI** (gộp main): Đợt 1–8; Đ9 việc 1–3 (`2cd4e5c`; QA GUI Windows = phiên máy chính); Đ10 việc 1–6 (`4c55e0d`, trừ việc 3
mục 2 project_budget + mục 7 runner); Đ11 việc 1 (`2cd4e5c`); Đ12 việc 1 (`2cd4e5c`); Đ14 việc 1 (`4c55e0d`), việc 2 (phiên rà Codex `4aa8ed8`); Đ15 việc 1–2
(`09396f1`); Đ16 việc 1–2 (`09396f1`, `ae97885`), việc 3 (phiên rà Codex `8a1a6be`/`185794d` + VÀNG "người khác dùng súng đã khóa" `8e66b16`/`2f03b29`);
Đ13 việc 4 mục 6 phần `group_block` bỏ dấu (`33939c9`); **Đ17 việc 1–2** (`3715c96`, phiên rà Codex sửa sau rà: `is_pov`, phủ định ghi chú skin, popup trước chuyển cảnh, tiếng pop hỏng giữ icon); vòng nền tự QC cờ `bg_autoqc` (phiên rà Codex `3715c96`, hộp thư 17:58). **Đ17 việc 3** (gộp `17c881a` + sửa sau rà `5d34d9e`: đường tự tạo Kho chỉ cảnh báo thiếu tên tiếng Anh, chỉ 2 form Kho bắt buộc; QC enum bỏ qua ghi chú tên; style chỉ info; alias trang phục không nối dài). Ngoài đề (phiên rà Codex): `send_claim`, `layout_from_follow` (hộp thư 19:58 / 19:17). Ngoài đề (phiên rà Codex / phiên máy chính — KHÔNG viết lại, chỉ dùng lại): `tests/conftest.py` cô lập
`data/` (`954b2e8`); kiểm nhất quán hướng đi + bố cục cờ `continuity_layout` (`7757662`/`756d29d`, `core/continuity.layout_warnings`); `assets.scene_references`
tài nguyên nhắc tên giữ chỗ (`5e1d410`); `assets._without_spoken_lines` (`a38bdb3`); `prop_lock.shot_text` bỏ thoại + `plate_camera` giàn máy TPS (`fe8bfff`);
`looks.clean_prompt` mệnh đề phủ định (`0cad90c`).

**THỨ TỰ CÒN LẠI** (thay mọi thứ tự trong hộp thư cũ):
1. ~~ĐỢT 17 việc 1~~ → 2. ~~ĐỢT 17 việc 2~~ (đã gộp `3715c96`) → 3. ~~ĐỢT 17 việc 3~~ (gộp `17c881a`) → 3a. **ĐỢT 11 việc 1b mockup (mục 9c) — NGƯỜI DÙNG DUYỆT 13/10**: bảng 20 dòng `docs/THIET_KE_BAN_DUNG_3D_D11.md` mục 9 theo ĐÚNG khuyến nghị (Làm: #1, #2, #8; Làm bản gọn: #3–7, #9–11, #13–19), **để sau #12 preset thư viện + #20 xuất/nhập JSON** → làm mockup theo 9c, dữ liệu theo điều kiện Đ18 A → 3b. **ĐỢT 18 việc 1 → 2 → 3** (**người dùng 13/10 chọn phương án A** theo khuyến nghị `docs/KE_HOACH_SAN_KHAU_DOAN_2026-10-12.md` — B trên cùng dữ liệu khi cần đo che khuất, C gỡ trước mắt; Đ18 việc 4 = phần A; ĐIỀU KIỆN người dùng: dữ liệu A là nguồn DUY NHẤT, Trình sửa sân khấu 3D Đ11v3 + màn Camera sửa chính dữ liệu đó, không làm màn 2D riêng; B mở rộng trên cùng dữ liệu) **— đọc hộp thư TODO 13/10 15:29 trước khi nhận việc: phiên máy chính đang giữ 11 lỗi hệ thống + gộp Đ11v2/v4** (sân khấu 3D chung theo đoạn — người dùng 12/10; việc 4 chờ người dùng duyệt kế hoạch) → 4. ĐỢT 15 việc 3 (phủ cả popup giữa phim Đ17v2) → 5. ĐỢT 12 việc 5 → 6. ĐỢT 11 việc 1b →
7. ĐỢT 14 việc 3 → 8. **project_budget gộp** = Đ10 việc 3 mục 2 + Đ13 việc 4 mục 9 phần `cost._video_need` + QC tính 2 lần khi `qc_observe_enum` bật (cờ này ĐÃ
BẬT trên máy chính → số đang sai trên #27), một nhánh `codex/d10-viec3b-project-budget` → 9. ĐỢT 12 việc 6 → 10. ĐỢT 13 việc 4 mục 1–8 + phần còn lại mục 9 →
11. ĐỢT 11 việc 2 → 12. ĐỢT 11 việc 4 (bỏ phần đã có trong `continuity_layout`) → 13. ĐỢT 12 việc 2–4 → 14. ĐỢT 13 việc 1–3 → 15. ĐỢT 11 việc 5 → 16. ĐỢT 11
việc 3 (sau khi người dùng duyệt thiết kế Đ11 việc 1 + 1b) → 17. **Nhóm runner sau #24** — CHỈ khi người dùng/phiên máy chính chốt (#27 chạy trên runner):
runner cắt bản cao sai đoạn (hộp thư 04:18 c), follower 1080p + `usage_events` giây clip nhóm (Đ10 việc 3 mục 7), xfail end_frames
(`tests/test_d8_technical.py`, Đ8 việc 2), nối gửi job Đ11 việc 5.

## Luật chung (áp cho cả 5 việc)

- **(người dùng 12/10 — áp MỌI đợt từ nay)** (a) **Tối ưu giao diện và nút bấm**: ít bấm nhất cho việc hay làm, nút đặt đúng chỗ dùng, tên nút nói rõ kết quả ("Gen 3 cảnh — ≈ 4,20 USD" thay vì "Chạy"), gom/ẩn nút ít dùng, trạng thái đang chạy/khóa hiện ngay trên nút, không hai nút cùng việc; kiểm bằng ảnh chụp 1440 + 1280. (b) **Rà soát thật kĩ khi build**: mỗi việc tự rà độc lập (agent/lượt rà riêng) + ghi báo cáo `docs/RA_*`, test đỏ→xanh, ca biên, không đổi hành vi khi cờ TẮT. (c) **Ý tưởng của người dùng là GÓP Ý, chưa chắc dùng tốt** → trước khi build phải KIỂM + ĐÁNH GIÁ HIỆU QUẢ: tần suất dùng × lợi ích (đỡ bao nhiêu bấm / tiền / lỗi thật đã gặp) × công sức + rủi ro; đề xuất bản đơn giản hơn nếu đạt cùng mục đích; ý nào lợi ít / trùng chức năng có sẵn / phức tạp quá thì ghi "KHÔNG NÊN LÀM (lý do)" hoặc "để sau" trong bảng đánh giá ở báo cáo — không build cho có. Người dùng xem bảng đánh giá rồi chốt.
- Tách nhánh từ `main` MỚI NHẤT (`git fetch origin && git checkout -b codex/<tên-việc> origin/main`). Đặt tên nhánh `codex/...`.
- Đọc `docs/CHUAN_XAY_DUNG.md` trước. Ba luật hay vi phạm: **không im lặng khi thiếu đầu vào** (thiếu / không đo được → báo VÀNG có lý do,
  không trả "đạt"); **test đỏ trước, xanh sau** (viết test, chạy thấy đỏ, sửa, chạy thấy xanh); **không nới test cũ để che lỗi**.
- Chạy test: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider <các file test liên quan>` (Windows dùng `py`; Linux/macOS dùng
  `python3`). Chỉ chạy file liên quan, KHÔNG cần chạy cả bộ (bên gộp chạy: `-n 8` ≈ 7,5 phút, tuần tự ≈ 28 phút).
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

**Nguồn:** `docs/GHI_CHU_GIAO_DIEN_SO_FATEBREAKER_2026-10-10.md` (chép từ nhánh `ghi-chu-giao-dien-fatebreaker` vào main 13/10, nhánh đã xóa) — so sánh FateBreaker ↔ Dashboard, 5 đề xuất,
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

Chạy cả bộ một lần: `PYTHONUTF8=1 py -m pytest -q -n 8 -p no:cacheprovider --durations=30 -rf` (≈ 7,5 phút; tuần tự ≈ 28 phút). Đối chiếu danh sách `slow` trong
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
- Việc 3: `codex/d8-viec3-bao-gia-video`, code `85a26db`; 3 đỏ ban đầu, 2 đỏ sau rà độc lập → 95 passed / 49,42s. Fixture 9 shot/3 refs: 0 clip/0 USD → 8 clip/5,51 USD. Shared predicate kiểm source/motion/SHA ảnh hiện tại; shared input_video_s, URL/UNC không probe. Thiếu proof có thể tính dư; ref unknown cảnh báo, chưa chứng minh trần. RA_D8_VIEC3_CODEX_2026-10-11.md.


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

- Việc 3 GUI — **ĐANG DỞ NGHIỆM THU WINDOWS** · nhánh `codex/d9-viec3-lao-dai` · code `44ad3e8`; merge main `94be37e` + dependency Đ10v4 `5bffa89` (không cherry-pick lại khi gộp). Có Tk/NOACTIVATE/drag/khay/WinRT toast/launcher + cấp token Owner local credential OS TTL5phút, HMAC cùng socket, mutex SID+target, DPI clamp. ĐỎ module → 44 xanh; native CredWrite bắt/sửa Unicode; rà P1/P2 3 đỏ → 50 xanh; root thấy thiếu lý do, 2 đỏ → **52 passed /13,37s**, 3 file. RA `docs/RA_D9_VIEC3_GUI_CODEX_2026-10-12.md`. Credential/mutex/shortcut QA riêng smoke thật; CHƯA GUI/toast/ảnh/DPI/hai màn/sleep-resume: @sky failed to activate captured window sau recovery, đã hỏi desktop. Không API/data thật/main/fullsuite; không coi hoàn tất Đ9v3.


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

- Việc 1: `codex/d10-viec1-goi-gui-kem`, code `d1b325f`; 5+2 đỏ ban đầu →116 xanh; rà độc lập 1 TRUNG wearer suy ra ngoài cast, 1 đỏ → **119 passed /154,46s**. OUTFIT thay đúng wearer, giữ góc phụ; hash khóa ảnh, bắt base_refs, replan orphan VÀNG, dedup. RA_D10_VIEC1_CODEX_2026-10-12.md; root đọc fix+push nhánh, chưa thử thật/cả bộ/gộp main.
- Việc 2: `codex/d10-viec2-ky-thuat`, code `440936f`; 6 đỏ ban đầu → 70 xanh/1 xfail; rà độc lập 1 P2 baseline partial, 2 đỏ → **73 passed / 1 xfailed / 5,72s**. V3 finding đề xuất chưa áp dụng kèm thư mục lượt; baseline explicit kiểm trước Claude; Lock OUTFIT chung tiêu chí, OFF giữ chuỗi. RA_D10_VIEC2_CODEX_2026-10-12.md. Thiếu camera baseline chưa kiểm trái/phải; chưa thử thật/cả bộ/gộp main. Root đọc fix, chỉ push nhánh; areas version giữ.
- Việc 3 · nhánh `codex/d8-viec3-bao-gia-video` · code `10a8823`: báo giá follower/running, ref chưa rõ tính dư, nhóm đã gửi và giá nâng 0,5254 USD/s dọc. ĐỎ 6 ca rồi XANH; rà độc lập thêm 3 ca đỏ đã sửa; **129 test xanh / 58,90 s** (8 file), diff check xanh. Báo cáo `docs/RA_D10_VIEC3_CODEX_2026-10-12.md`. Bỏ qua project_budget chờ #24; provenance original/marked, cắt follower 1080p và nhóm lịch sử orphan còn mở. Không API/data thật/cả bộ/main.
- Việc 4 · nhánh `codex/d10-viec4-phieu` · code `9c17c84`: reopen/CAS phiếu, projection, sidebar link một lần, câu bằng chứng, pet waiting_admin, broker readonly độc lập và chi theo ngày VN. ĐỎ 4 ca → XANH 162; rà độc lập sửa 1 P2 Markdown (đỏ AppTest → **163 passed / 20,50 s**, nhóm 9 file). Báo cáo `docs/RA_D10_VIEC4_CODEX_2026-10-12.md`. GUI pet/Windows QA làm tiếp Đ9v3; lý do chỉ có trong RAM runner chưa khôi phục được. Không API/data thật/cả bộ/main.
- Việc 5 · nhánh `codex/d10-viec5-khung` · code `97d1a40`: cờ `change_review_frames` TẮT, OFF đề giống từng byte; ON START/TRANSITION/END + nhịp/BYĐ, 3 ca vàng. ĐỎ 4 lỗi/16 qua → 20 → **21 test xanh**, diff check xanh; tự rà và agent rà caller không finding. Báo cáo `docs/RA_D10_VIEC5_CODEX_2026-10-12.md`. Chưa thử Claude thật; BYĐ đầy đủ có thể tăng token khi bật. Không API/data thật/cả bộ/main.
- Việc 6 · nhánh `codex/d10-viec6-chuyen-dong-nen` · code `5197a1c`: `ambient_motion` TẮT, OFF byte exact Director/motion/DP; ON lớp nền theo BYĐ/weather/time và VÀNG không chặn gen. ĐỎ 6 ca tính năng + 2 setup → 54 → 62 xanh; rà caller sửa 1 P2 (2 đỏ → **64 test xanh / 1,15 s**, 3 file), diff check xanh. Smoke 7 màn ui_v2 OFF/ON không exception. Báo cáo `docs/RA_D10_VIEC6_CODEX_2026-10-12.md`. Chưa thử Claude/video thật; rewrite chuyên biệt chưa thêm luật, sau lưu vẫn VÀNG. Không API/data thật/cả bộ/main.


(Codex ghi: việc · nhánh · commit · bằng chứng · việc mở.)

- Đ20 việc 6 · `codex/d20-viec6-so-loi` · mã commit xem git log/HANDOFF cùng nhánh · trang Sổ lỗi chỉ đọc, lọc/coverage/problems toàn sổ; plan_map đọc chuẩn items/schema, khâu lỗi mở viền đỏ. 9 đỏ → 52 xanh (10,26s), gồm AppTest; RÀ NHẸ sửa alias số gây crash. Báo cáo `docs/RA_D20_VIEC6_CODEX_2026-10-20.md`; chưa cả bộ Windows/slow, push/gộp/live.

- Đ20 việc 1 · `codex/d20-viec1-so-loi` · commit chứa dòng này (xem `git log -1`) · đỏ 4 ERROR trước công cụ → xanh 7 test (0,74s), SQLite tạm native/schema tổng hợp; `docs/RA_D20_VIEC1_CODEX_2026-10-20.md` · chờ rà độc lập + cả bộ Windows; ledger thiếu giá USD giữ UNKNOWN; job lỗi lấy note failed cuối mỗi job; chưa thử dữ liệu thật/chưa push.

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

## Việc 1b — Đối chiếu "Bàn đạo diễn" Clip AI (ảnh ref người dùng gửi lại 12/10) → cập nhật thiết kế + mockup TỐI ƯU HƠN (tài liệu + HTML; thứ tự theo bảng 📋 đầu file)
Ảnh ref: `docs/images/d11/clipai_ref_xoay_goc_nhin.png` (xoay góc nhìn người xem bằng chuột), `docs/images/d11/clipai_ref_nhan_vat.png` (chọn nhân vật: bảng Thuộc tính / Tư thế, màu, vị trí/xoay/tỉ lệ XYZ, tỉ lệ đồng đều, "Lưu vào thư viện";
gizmo di chuyển trên khung nhìn; khung "Góc nhìn camera — Ảnh kết quả cuối" nổi góc phải) và `docs/images/d11/clipai_ref_camera_toan_canh.png` (tab Toàn cảnh:
tải ảnh nền toàn cảnh, màu nền phông xanh #2F8F5B, lưới mặt đất, hướng nguồn sáng; chọn camera: "Dùng góc nhìn hiện tại", "Về mặc định", vị trí, ĐIỂM ĐÍCH,
độ nghiêng (roll), trường nhìn FOV; thanh phím tắt V/R/S/F/T/Q/Del/Esc/Ctrl+Z + gợi ý chuột; nút "Hoạt ảnh"; danh sách Camera 1/10, Nhân vật 2/10,
Vật thể khác 1/50 + "Thêm…"). Người dùng: plan phải TỐI ƯU HƠN bản này. Đã có trong `docs/THIET_KE_BAN_DUNG_3D_D11.md` + `mockup/ban_dung_3d.html`: hai góc
nhìn, nón nhìn, kéo/nhập vị trí, kiểm ĐỎ/VÀNG, safe area, lan đề xuất, khóa chỉnh tay. CÒN THIẾU → bổ sung thiết kế (mục mới "Đối chiếu Clip AI") + mockup:
| Clip AI có | Mình làm (tối ưu hơn) |
|---|---|
| Dựng tay từ cảnh trống | Đạo diễn DỰNG SẴN mọi cảnh nối cảnh trước (giữ NGUYÊN TẮC đợt 11); người dùng chỉ chỉnh |
| Khung "Góc nhìn camera — Ảnh kết quả cuối" nổi khi đang ở góc nhìn đạo diễn | Có khung nổi (thu/phóng, bật nhãn tên, bật mũi tên hướng nhân vật, tải ảnh) + hiện CỠ CẢNH đo được, chân trời, mắt % khung, safe area; cập nhật ngay khi kéo |
| Ảnh nền: tải ảnh toàn cảnh / màu phông xanh | Nền = render 3D THẬT của bối cảnh (plates / Tháp Đồng Hồ…) theo đúng máy; phông xanh chỉ khi chưa có map; tải ảnh toàn cảnh = tùy chọn phụ |
| Hướng nguồn sáng (slider) | Lấy từ `plate_env` giờ/thời tiết của cảnh (mặt trời/đèn của map), chỉnh được; cảnh báo VÀNG khi lệch ánh sáng ảnh duyệt |
| Camera 1/10, "Thêm camera" | Nhiều máy mỗi cảnh = các GÓC PHỦ (bộ góc máy Đ11 việc 5 mục 2): máy chính + góc phụ (OTS, cận phản ứng) đề xuất sẵn, chọn máy làm shot |
| Vị trí / Điểm đích / Độ nghiêng / FOV (số thô) | Nhập theo nghề: cỡ cảnh (WS…CU) ↔ tiêu cự mm ↔ FOV tự đổi qua lại; điểm đích = "nhìn vào" nhân vật/khối (chọn tên) hoặc số; roll có cảnh báo khi > 0 không có lý do |
| "Dùng góc nhìn hiện tại" / "Về mặc định" | Có; "về mặc định" = về đề xuất của Đạo diễn/bộ giải (không phải gốc tọa độ); thêm "Giải máy" (solver sẵn có) |
| Nhân vật: tên, màu, XYZ, xoay, tỉ lệ | Nhân vật lấy từ cast dự án (tên thật, ảnh mặt nhỏ, màu cố định theo người); tỉ lệ = CHIỀU CAO THẬT theo hồ sơ nhân vật (không kéo tỉ lệ tùy ý); vị trí theo ô lưới tên + mét |
| Tab Tư thế | Tư thế theo NHỊP BYĐ (đầu/đỉnh/cuối) từ thư viện tư thế + hồ sơ kỹ năng nhân vật; xem 3 nhịp liền nhau |
| Vật thể khác 1/50 (khối trụ…) | Đạo cụ/khối từ Kho bối cảnh (giếng, cầu thang, gloo wall…) đúng kích thước; khối tạm `stand_in` không lọt vào ảnh gửi model |
| "Hoạt ảnh" | Thành dòng thời gian KEYFRAME đầy đủ (dòng dưới) — nhịp BYĐ chỉ là keyframe mặc định |
| "Lưu vào thư viện" | Lưu PRESET vào Kho dự án: máy (góc + cỡ + đường), sân khấu cảnh (vị trí + tư thế) — dùng lại cảnh sau / dự án sau; Tiểu Nhị gọi lại được |
| Tải ảnh kết quả | Ảnh kết quả = ảnh bố cục (Image1 composition) + khung clay gửi kèm gen (Gói gửi kèm Đ8) — không phải tải về rồi tải lên tay |
| Phím tắt V/R/S/F/T/Q/Del/Esc/Ctrl+Z, gợi ý chuột, thu gọn 2 panel | Giữ đủ (cùng phím cho người đã quen Clip AI) + lật cảnh trước/sau (←/→), so cảnh trước (bóng mờ), hoàn tác theo phiên bản sân khấu |
| Chuột chỉnh GÓC NHÌN NGƯỜI XEM bàn dựng (ảnh `docs/images/d11/clipai_ref_xoay_goc_nhin.png`: kéo trái xoay quanh, kéo phải dời, cuộn thu/phóng; T nhìn từ trên, Q đặt lại, F lấy nét vật đang chọn) — tách khỏi máy quay của shot | Giữ đủ (orbit/pan/zoom, T/Q/F) + nút góc nhìn nhanh: trên / trước / bên / sau lưng máy quay / "đứng chỗ máy" (xem đúng từ máy mà vẫn kéo được); xoay quanh vật đang chọn (không quanh gốc tọa độ); giới hạn không chui dưới sàn / xuyên tường map; góc nhìn người xem KHÔNG đổi máy quay (chỉ "Dùng góc nhìn hiện tại" mới chép sang máy); nhớ góc nhìn theo cảnh khi lật trước/sau; mockup cho thao tác này chạy được bằng chuột + bàn phím |
| Giới hạn Camera 1/10 mỗi cảnh (người dùng hỏi 12/10: cảnh > 10 shot thì sao) | KHÔNG giới hạn cứng. Tách 2 khái niệm: **thiết lập máy** (setup: vị trí + hướng + cỡ + đường máy) và **shot** (đoạn phim). Nhiều shot DÙNG LẠI một setup (như quay thật: master, qua vai A, qua vai B, cận phản ứng → cả đoạn đối thoại 20 shot chỉ 4–6 setup); shot nào khác biệt mới tách setup riêng ("tách từ setup này"). Sân khấu theo BỐI CẢNH (cùng một chỗ dùng chung cho mọi cảnh/shot ở đó), không theo từng shot. Danh sách bên trái: nhóm theo setup → các shot dùng nó (số shot + thumbnail), lọc theo cảnh, cuộn ảo khi dài. Khung nhìn chỉ vẽ nón nhìn của setup đang chọn + setup của shot trước/sau (mờ), không vẽ hết; xem trước camera render khi chọn (có hàng đợi), không render cả chục máy cùng lúc. Đổi một setup → báo các shot đang dùng nó (shot đã duyệt chỉ VÀNG, không tự đổi). Dữ liệu: `shot.camera_setup_id` → bảng setup của bối cảnh (thiết kế ở việc 3) |
| (người dùng hỏi 12/10) KEYFRAME cho vật / nhân vật / máy quay | Dòng thời gian theo GIÂY của shot (độ dài = `duration_sec`), mỗi hàng một đối tượng (nhân vật, đạo cụ, máy). Keyframe lưu vị trí + hướng (+ tư thế cho nhân vật; + cỡ/tiêu cự/điểm nhìn cho máy). **Đạo diễn đặt sẵn** keyframe từ nhịp BYĐ (đầu/đỉnh/cuối) và `camera_move` (đầu/cuối); người dùng thêm/xóa/kéo keyframe ở mốc giây bất kỳ (phím K thêm tại vạch phát), chép/dán keyframe, kiểu chuyển (thẳng / mượt vào-ra / giữ). Khung nhìn vẽ ĐƯỜNG ĐI của vật/máy giữa các keyframe (chấm theo giây); nút ▶ phát clay 0 USD theo thời gian. Kiểm theo keyframe: va chạm/xuyên khối, rời khung, máy quá nhanh (m/s, °/s) so cỡ cảnh, nhân vật đi quá nhanh so dáng (đi/chạy), lệch vị trí cuối ↔ đầu shot sau → ĐỎ/VÀNG. Model video KHÔNG nhận keyframe trực tiếp → keyframe được DỊCH sang: (a) mốc giây trong motion prompt ("0–1 s…, 1–3 s…"), (b) khung đầu/cuối, (c) video clay/white model theo keyframe (Blender, 0 USD) làm video tham chiếu chuyển động khi model nhận; hiện rõ phần nào sẽ được gửi. Shot đã duyệt: đổi keyframe → VÀNG "cần gen lại". Dữ liệu: keyframe nằm trong sân khấu của shot (việc 3), Đạo diễn khai dạng số, code kiểm |
| (người dùng hỏi 12/10) Clip AI chỉ có vật + phông xanh; bản mình có MAP 3D → camera ghi những gì? | Góc nhìn camera = MỌI thứ trong nón nhìn của máy: map 3D (plates) + nhân vật clay + đạo cụ, đúng che khuất (tường/cột che nhân vật thì bị che). Tách LỚP khi xuất, người dùng chọn lớp nào vào ảnh kết quả: (1) **nền map** (= ảnh nền 3D hiện có `plates`, dùng làm tham chiếu bối cảnh), (2) **clay nhân vật/đạo cụ trên phông xanh** (= tham chiếu bố cục/tư thế, như Clip AI), (3) **ghép** nền map + clay (ảnh bố cục Image1). Mặc định gửi model theo luật hiện có: nền map + ảnh bố cục; KHÔNG để khối xám `stand_in`/nhân vật clay lọt vào ảnh mà model sẽ chép thành chi tiết thật (luật cũ `stand_in`) — mockup hiện công tắc từng lớp + nhãn "lớp này sẽ được gửi / chỉ để xem". Kiểm: máy nằm TRONG tường/vật của map (ĐỎ), vật che mất > x % nhân vật chính (VÀNG), nhân vật ra ngoài khung, map chưa có ở chỗ máy nhìn (khoảng trống/rìa map → VÀNG). Hiệu năng: map nặng → khung nhìn dùng bản map nhẹ (LOD/khối), ảnh camera cuối render bằng Blender (như plates); không có map cho bối cảnh → phông xanh như Clip AI |
| (người dùng 12/10) Nhân vật BỊ CHE (vd núp sau tường) — bật/tắt hiển thị + cách DIỄN GIẢI cho model và Dashboard | **Bàn dựng:** công tắc "Hiện người bị che" (phím H): nhân vật sau vật hiện viền/bóng mờ xuyên tường CHỈ trong khung nhìn — không bao giờ vào ảnh gửi model. **Code đo, không đoán** (theo kiểu `core/stage_facts.py` `top_visible`: code tính, câu tiếng Anh do code viết): mỗi nhân vật × mỗi keyframe, tia từ máy tới các điểm cơ thể (đầu, mắt, vai, thân, chân) → `visibility` = `thay` / `mot_phan` (+ phần nào lộ: "đỉnh đầu + một mắt ở mép trái tường") / `bi_che` (+ bởi vật nào) / `ngoai_khung`. **Ý đồ của Đạo diễn** khai riêng (`an` = cố ý núp/giấu, `lo` = cố ý lộ, `ra_khoi_cho_nap` lúc nào) — code so ý đồ ↔ đo: ý đồ núp mà máy vẫn thấy → ĐỎ; ý đồ thấy mà bị che → ĐỎ; lộ một phần ngoài ý đồ → VÀNG. **Diễn giải cho model (code viết, không để Claude tự tả):** che HOÀN TOÀN cả shot → KHÔNG gửi ảnh nhận diện, không nêu tên trong danh sách nhân vật thấy được (model hay vẽ ra người được nêu tên); nếu truyện cần thì chỉ tả HỆ QUẢ thấy được (bóng đổ, vạt áo ló, vật rung) + "no person visible"; che MỘT PHẦN → gửi ảnh nhận diện + câu chính xác phần lộ và vị trí so vật che ("only the top of her head and her left eye peek over the left edge of the stone wall; the rest of her body is hidden behind it"); LỘ RA giữa shot → mốc giây theo keyframe ("0–2 s: hidden behind the wall, not visible; at 2 s she steps out to the right of the wall"), khung đầu không có người đó. **Dashboard:** mỗi nhân vật mỗi nhịp có nhãn 👁 thấy / ◐ một phần / 🚫 bị che bởi <vật> / ⬚ ngoài khung (thẻ shot, Trình sửa, Gói gửi kèm); QC/khóa nhân vật dùng nhãn này: KHÔNG đánh trượt ảnh vì "thiếu" người đang bị che, nhưng ĐÁNH trượt nếu người đang phải bị che lại hiện ra; BYĐ/lock_exceptions chỉ ĐỌC nhãn (không sửa file cấm — nối sau #24). Test ca vàng: tường trước, nhân vật sau (che hoàn toàn / ló đầu / bước ra giây 2) |
| Xuất/nhập (biểu tượng góc phải) | Xuất/nhập JSON sân khấu (schema `stage_v2`) + ảnh; không dùng API Clip AI (chưa có endpoint) |
**TRƯỚC KHI dựng mockup: đánh giá từng dòng bảng trên** (luật chung (c): đây là GÓP Ý của người dùng, chưa chắc dùng tốt) — cột thêm: tần suất, lợi ích, công sức, rủi ro, khuyến nghị LÀM / LÀM BẢN GỌN / ĐỂ SAU / KHÔNG NÊN; chỉ đưa vào mockup các dòng LÀM / LÀM BẢN GỌN, các dòng khác ghi lý do. Giao diện phải gọn: người dùng chỉ chỉnh từng cảnh, mặc định ẩn bớt bảng thông số, phím tắt + nút ít. Việc: (1) bổ sung `docs/THIET_KE_BAN_DUNG_3D_D11.md` mục "Đối chiếu Clip AI" (bảng trên + chỗ nối dữ liệu thật: plates, cast, Kho, BYĐ, Gói gửi kèm;
cái gì chỉ là mockup, cái gì cần việc 2/3); (2) nâng `mockup/ban_dung_3d.html`: khung camera nổi trong góc nhìn đạo diễn, tab Toàn cảnh (nền 3D/phông
xanh/ánh sáng theo giờ), nhiều máy/góc phủ, ô cỡ cảnh↔mm↔FOV + "nhìn vào", tư thế theo nhịp + thanh hoạt ảnh, đạo cụ từ Kho, thanh phím tắt, "Lưu
preset"; (3) cập nhật ảnh `docs/images/d11/` (1440 + 1280, cả hai góc nhìn) + test mockup (offline, không CDN; Playwright skip khi không có trình
duyệt như hiện tại). Không code backend (để việc 2/3).

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
**Đã có (cờ `continuity_layout`, `core/continuity`): trục 180°, hướng đi so với máy, vật cố định giữ bên, người biến mất — MỞ RỘNG, không viết lại. Ca vàng ghi ở `knowledge/checks/ca_vang/` (không phải `knowledge/checks/<id>.md`).**
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

- Việc 1b mockup 9c — nhánh `codex/d11-viec1b-mockup`, code `f962f0f9` + sửa sau rà `e74d8233`: registry stage/state/setup chung, proxy world-space, preview nổi, timeline/sampler, diff ID/revision, target và baseline, nền/đèn/props fixture. Đỏ 1 failed/1 passed → **3 passed / 50,00 s**; rà độc lập sửa 5 P2, 16 tổ hợp kéo, Chrome 1440/1280 console=0/overflow=0, 4 PNG cập nhật có chủ ý. Đo cùng fixture 5/5 thao tác, chưa chứng minh giảm bấm. 18 mục bản gọn theo chốt, #12/#20 để sau. RA `docs/RA_D11_VIEC1B_MOCKUP_CODEX_2026-10-13.md`; chưa backend/render/ca thật/cả bộ, không main/live/API.

- Việc 2 · `codex/d11-viec2-clay` · code `b4e97fa1`: backend/V3 CLI Nhánh C, camera clay/sidecar bền + topview/3góc/legend, fallback chiếu2D có lý do; trụ/cột tròn. Đạo diễn khai JSON sau cờ OFF, model3d thật giữ đường cũ, kiểm plan và người/vật mọi nhịp, khóa/kế thừa explicit; estimate/ledger, tối đa đầu+2sửa, cùng lỗi2lần dừng. ĐỎ module/caller, 10ca rà và4hướng sáng → **158 passed /19,53s**,10file, `--tb=no`; 3nhóm rà đã đóng. Blender thật3fixture tạm: indoor8,29s/outdoor7,41s/steps7,40s,4góc/ca,6PNG và sidecar decode được. Hai cờ OFF/OPT_IN, areas.version68 giữ. RA `docs/RA_D11_VIEC2_CODEX_2026-10-13.md`. Chưa nối Dashboard/autopilot adapter, tư thế khác đứng/sàn nhiều cao độ/7trên9/chiếu≤5%/Kho thật/Claude thật/cả bộ/gộp; không API/dữ liệu thật/live.
- Việc 4 — phần backend/QC local đã push nhánh `codex/d11-viec4-luat-quay`, code `3716cace`: thêm eyeline/30°/lead room/headroom, so ảnh và hai khung clip với máy, báo VÀNG thiếu số/ngưỡng chưa hiệu chỉnh; hai cờ OFF. Đỏ→xanh, rà độc lập sửa 3 P2 và hai lỗi root, **59 test xanh / 1,88 s**. Rà tại `docs/RA_D11_VIEC4_CODEX_2026-10-13.md`. Còn dở: nối blocking đã duyệt vào report/màn camera, subject ID/trạng thái cuối, GUI và ca thật; chưa cả bộ, không gộp main/live/API.

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

- Việc 2 · nối caller Bước 5 trên `codex/d12-viec2-noi-sfx`, code **ffac01b1 đã push**: nút code 0 USD dùng bảng chọn/duyệt/apply sẵn có; `motion_sfx` OFF/OPT_IN_ONLY. RED4, rà thêm RED selection/snapshot/I/O/copyfailure → **88 test xanh /4,28s**. SHA mạnh có scope/budget trước áp; rerun UI chỉ DB/catalog/stat; stage không ghi Kho, atomic manifest giữ mix cũ khi copy lỗi. RÀ KỸ độc lập + root đọc diff lần hai; QA actual Step5 Edge Windows1440/1280, code→apply giả1cue/readonly, 2PNG, 0pageErrors/overflow, provider forbidden. RA `docs/RA_D12_VIEC2_CALLER_CODEX_2026-10-14.md`; areas76 giữ. Còn giới hạn CAS với writer legacy, file mồ côi khi crash, clip thật/chất lượng âm/cả bộ/main/live; không API/tiền.

- Việc 4 — nhánh `codex/d12-viec4-kho-am-thanh`, code `f7a6ab10` + sửa rà `bba75ff5`: báo cáo nguồn/license tại `docs/KHO_AM_THANH_CAN_BO_SUNG.md`, tool offline `tools/audio_mood_audit.py` đọc JSON/CSV explicit, chặn URL/UNC trước mở file. Đỏ thiếu module →26 xanh; rà 6 ca URL/UNC đỏ → **34 test xanh / 0,31 s**. AST MIT config chính thức có 7 mood; báo cáo phân biệt thiếu top-k/score thấp/ontology mismatch, AST/YAMNet và mood folder/loudness, không suy mood rỗng là 0 thật. RÀ NHẸ root đọc code/docs/fix; RA `docs/RA_D12_VIEC4_CODEX_2026-10-13.md`. Chưa đo Kho/#24, chưa chọn/tải âm/model; người dùng duyệt trước tải, chưa cả bộ/main/live/API.
- Việc 2 — phần backend/component trên `codex/d12-viec2-sfx-nhip`, code `6e789358`: map BYĐ/motion thành cue qua catalog đáng tin, post_fx cùng schema, cảnh báo âm cũ/thiếu; motion prompt hiện tại ưu tiên bản dịch cũ. Timestamp peak chỉ khi máy cố định, alignment vẫn ước tính/VÀNG; fallback BYĐ. Đỏ→xanh, rà độc lập sửa3P2 +root2guard, cuối **100 test/11,06s**. Cue overlap giữ neo shot, prevalidate âm/file/volume trước xóa, legacy giữ đường cũ. QA Edge headless1440/1280:2PNG,0console/overflow/paidAPI; Chrome launch lỗi. CờOFF+optin; RA `docs/RA_D12_VIEC2_CODEX_2026-10-14.md`. CÒN: nối caller Bước5 khi Claude giải phóng, Claude bổ sung có báo giá, clip thật/cả bộ; chưa main/live.

- Việc 1 · nhánh `codex/d12-viec1-am-nen` · code `cc8dda7`: voice chỉ giọng người, accent riêng nullable; legacy dế/gió suy từ heard_label khi đọc, không UPDATE/nghe lại. Point accent/trusted vẫn loại voice; nhãn lạ giữ guard bảo thủ. ĐỎ 3/51 → 54 xanh; rà 0 blocker/1 LOW trim đã sửa (1 đỏ → **55 passed /50,49s**, 3 file); migration giữ giá trị + query_only không đổi hàng. RA `docs/RA_D12_VIEC1_CODEX_2026-10-12.md`. Chưa thử Kho thật #437/#307, chưa cả bộ/gộp main, không API/data thật.


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

## Việc 4 — Tồn đọng THẤP từ rà gộp Đ10 + Đ14 (phiên rà Codex 12/10 sáng; mỗi mục test đỏ → xanh, sau cờ nếu đổi hành vi)
1. `core/change_review.py:157-170` (Đ10v2, cờ `layout_drift_review`): mục VÀNG `layout_drift_proposal` mỗi lượt V3 ghi mục MỚI (nội dung có
   `os.path.abspath(new_dir)`) và không bao giờ đóng → tích tụ; lượt sau đóng mục đề xuất cũ cùng shot; ghi tên lượt/đường dẫn tương đối, không đường
   dẫn máy.
2. `core/tickets.py:71` `_safe`: `path.startswith('/')` chặn cả lý do/tiêu đề bắt đầu bằng "/" (vd "/24 shot") — chỉ chặn mẫu đường dẫn tuyệt đối
   thật (≥ 2 đoạn, vd `/home/x/…`, `/mnt/…`).
3. `core/prompts.py:576-579` (`short_lock_outfit`): tiêu chí mới chỉ cần `outfit_image_ids` không rỗng — ID trỏ ảnh mất/hỏng thì mất Lock ngắn mà
   không gửi ảnh OUTFIT nào; quay lại điều kiện "có ≥ 1 ảnh OUTFIT dùng được" (`reference_problem` None) hoặc giữ Lock khi không ảnh nào dùng được.
4. Dọn: `video_reference_seconds` không bao giờ trả `seconds=None` → bỏ nhánh chết `model_router.py:403`, `quality_tier.py:633/678`, import
   `resolve_model` lặp `model_router.py:405`; `cost.video_need` quét mọi job nhóm cho từng shot (bình phương số shot) → tính một lần cho cả dự án.
5. `core/package_overrides.py`: `_scene_hash` đổi tập khóa (bản chỉnh đã lưu trước sẽ hiện "stale") và `save()/undo()` bắt buộc `base_refs` — ghi rõ
   trong docstring + test thông báo dễ hiểu khi thiếu (chưa có caller sản xuất).
6. `core/seedance_refs.py:403,855` regex `Dialogue \([^)]*\): "[^"]*"` dừng ở dấu `"` đầu tiên trong câu thoại (câu `Nói "chào" đi` → lint chặn
   "còn chữ tiếng Việt") — khớp tới `"` cuối dòng (MULTILINE) hoặc đổi `"` trong câu thành `”`; thêm test cấp runner (`tests/test_dialogue_take_runner.py`):
   nhân vật tên có dấu + shot take → `_lint` trả None (sửa `group_block` bỏ dấu tên đã gộp main 12/10, phiên rà Codex).

7. (rà gộp Đ9v3 GUI pet, 12/10 08:xx) `tools/lao_dai/logic.py:55-63` + `gui.py:27-29,154`: toast + bấm mở cả `waiting_merge` nhưng bong bóng/dáng pet
   chỉ đếm `waiting_admin` → chỉ còn phiếu chờ merge thì pet idle mà chân trang ghi "Bấm mở đúng phiếu"; đếm cả hai ("· N chờ merge") hoặc ghi quyết
   định vào THIET_KE_TIEU_NHI_LAO_DAI_D7.md + test. `channel.py:240-247` watchdog 2 s chạy cả `admin_snapshot` → chỉ kiểm `auth.identity` + cờ.
   `channel.py:174-175` cấp lại quyền: gỡ token broker cũ khỏi `broker._tokens`. `devsys/lao_dai_channel.py:282-284`: chú thích "Pet: chỉ Owner…" hiện
   đầu MỌI trang 8502 cho người không phải Owner → chỉ trang Phiếu / sidebar. Vẫn còn: QA GUI Windows thật (toast, DPI, 2 màn hình, sleep/resume).
8. (rà gộp Đ12v1 âm nền) `core/sound_lib.py:153` quét lại thư mục: file đổi nội dung không xóa `heard`/`heard_label`/`accent` → nhãn cũ dính file mới;
   `ambience.choose` chỉ xét nhãn CHÍNH (âm gió có "Speech 0.4" ở nhãn 2 vẫn nhận — ghi lại, cân nhắc). KHÔNG thêm lọc `kind='sfx'` cho âm nền
   trước khi xem `sound_lib` phân loại theo cỡ file (>2,5 MB = music → âm nền dài bị xếp music).

9. (rà gộp Đ15v1–2 + Đ16v1, 12/10 12:55) `core/cost.py:605-609` `_video_need` coi nháp ĐÃ DUYỆT (quality_tier='draft') là "cần gen" → khi bật 2 bậc,
   `run_estimate` cộng thêm 1 nháp + bản cao (thừa ≈ 0,41 USD/shot; nháp đang chạy thì chỉ cộng phần nâng) — `project_budget`, `model_router._remake_runs`
   chịu theo; xử lý như nháp đang chạy + test cờ BẬT. Autopilot gặp `LlmError(director_busy)` (`core/llm_runner.py:781-782`) dừng ERROR + diag "error" →
   coi là bận tạm, chờ lượt sau. `director_lease.busy()/replies()` trong UI không bọc lỗi (sổ khóa không mở được / khóa ghi > 10 s → OperationalError thay câu
   "đang chạy"). Nhãn "NHÁP — có clip 480p" chưa hiện ở màn Video (`step4._draft_preview`); cảnh báo nháp ở step5 hiện mãi khi `xem_nhap.mp4` còn dù đã có
   bản giao. `final_cut.measured_size` ghép đường tương đối theo gốc repo còn `collect_clips` theo thư mục hiện hành (PIPELINE_DATA tương đối → mọi clip
   "không đo được" → chặn giao); dự án cũ không `aspect` + clip đầu không đo được → `require_delivery_resolution` bỏ qua im lặng. ~~`prompt_versions_ui`: cảnh báo FALLBACK cũ~~ → CHUYỂN ĐỢT 17 việc 3d (Đ13 bỏ qua). Script ngoài Dashboard nạp env: DÙNG LẠI `core/adapters/check.load_dashboard_env` + thêm đọc khóa HKCU\\Environment (như script phiên máy chính 14:35) — không viết module song song (trước ghi `core/env_boot.py`) cho script của phiên gọi pipeline ngoài Dashboard (lỗi #27).

## Kết quả Codex — đợt 13

- Việc 4 mục 4, tối ưu nhóm đã trả tiền — nhánh `codex/d13-viec4-cost-nhom`, code `a4a9dc83`, nền budget đã main: 99 shot/20 nhóm → 1 query, 20 parse, 99 thành viên; index bất biến lookup/deepcopy O(1). Báo giá draft/final_only/follower byte-identical với oracle. Đỏ 3 + Infinity → **133 test + 6 subtest xanh / 52,18 s**; RÀ KỸ độc lập bắt P2 SAVEPOINT rollback, 3 ca đỏ → sửa, **28 test xanh / 3,88 s**. Transaction đọc mới ưu tiên đúng tiền; ngoài transaction cache theo dự án. Root rà diff vòng hai. RA `docs/RA_D13_VIEC4_COST_NHOM_CODEX_2026-10-13.md`; chưa cả bộ/ca thật, không main/live/API. Những phần Đ13v4 đã push nhánh cũ giữ nguyên, không làm lại.
- Việc 3 — nhánh `codex/d13-viec3-mockup-pet`, code `ca5bd2ba` + sửa root số tương đương: Set nhớ mọi snapshot đã gen, chặn cả preview/gen khi quay đầu vào cũ; pet dáng thường ẩn phiếu. Browser JS offline 1440/1280: đỏ đúng hai lỗi →7 xanh; root thêm ca 1.20/1.2 đỏ→xanh, cuối **7 passed/5,45 s**, 0 lỗi console/JS/overflow/mạng. RA `docs/RA_D13_VIEC3_CODEX_2026-10-13.md`; ảnh tmp không ghi đè tài liệu, slow giữ theo số đo đầu ≥8 s. Chưa native GUI/backend/cả bộ/main/API.

(Codex ghi: việc · nhánh · commit · bằng chứng · việc mở.)

- **14/10 — Việc 2:** `codex/d13-viec2-goi-blockout`, code `bad2a535`. Schema 2 chuẩn hóa số đúng trường hình học; schema 1 giữ SHA raw; ngày mới có múi giờ, ngày cũ thiếu múi giờ cảnh báo duyệt lại. Font Pillow cũ có fallback, thiếu font Unicode báo rõ. Đỏ 5 lỗi → 95 xanh; rà độc lập bắt 2 P2, hồi quy 2 đỏ → **97 xanh / 3,43 s** (5 file). Root đã đọc diff vòng sửa; test môi trường dict giả bằng `patch.object`, không API/dữ liệu thật. RA: `docs/RA_D13_VIEC2_CODEX_2026-10-14.md`. Giữ areas.version 74; chưa cả bộ Windows/gộp/live; chưa cài Pillow cũ để thử thực tế.
- **14/10 — Việc 1, mục 1/3/5 độc lập:** `codex/d13-viec1-post-fx`, code `728be4be`. Tên file shot + SHA đầu vào, ghi atomic; schema Đạo diễn gated `p24_lessons` và lưu tới scene.data cả v2/v3; manifest.post_fx tới Editor + Đạo diễn rà lại gated `post_fx_render`, fingerprint tránh cache cũ. Đỏ 5 lỗi → 108 xanh; rà độc lập bắt 2 P2 caller, 3 hồi quy đỏ → **147 xanh / 131,81 s**, 6 file (ffmpeg thật local; thiếu rgbashift chỉ skip ca glitch). Root đọc diff vòng sửa; môi trường dict giả, native env whitelist, không API/data thật; areas giữ 74. RA `docs/RA_D13_VIEC1_CODEX_2026-10-14.md`. **MỞ mục 2/4** (delivery đang do Claude giữ), chưa cả bộ Windows gồm slow/gộp/live; tên mới không dọn UUID cũ.

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

## Việc 3 — ffmpeg đọc file Kho âm thanh trên ổ mạng (hộp thư 12/10 04:18 d; nhỏ, không cờ)
Khi dựng bản cuối #24, ffmpeg lỗi đọc file Kho âm thanh nằm trên ổ G: (Google Drive đồng bộ, lỗi 69) lúc cắt — phải chép tay về máy. Sửa: chỗ cắt/trộn
âm từ Kho (`core/sound_lib.py`, `core/ffmpeg_studio.py`, nơi gọi khi dựng — tìm caller) chép file nguồn ở ổ mạng/thư mục đồng bộ về thư mục tạm của dự án
(có kiểm cỡ + mtime, dùng lại bản đã chép) rồi mới đưa ffmpeg; lỗi đọc → nói rõ file nào + "chép về máy" (không im lặng). KHÔNG sửa `core/runner.py`.
Test bằng file giả (mô phỏng lỗi đọc), không cần ổ G thật.

## Kết quả Codex — đợt 14

- Việc 1 · nhánh `codex/d14-viec1-qc-quan-sat` · code `86d7a94`: cờ `qc_observe_enum` TẮT/opt-in riêng, OFF request/output byte giống `08c11b4`. ON enum/vùng/nguồn, code chấm, không chắc VÀNG; ảnh đơn/batch/autoqc/cảnh dùng chung, cảnh 1 call giữ người/shadow/lớp0. ĐỎ module → 56 xanh; rà độc lập gom 14 đỏ → 111 xanh; root kiểm cuối **113 passed / 7,81 s**, 5 file. Báo cáo `docs/RA_D14_VIEC1_CODEX_2026-10-12.md`. Chưa thử ảnh thật678/680 hoặc chi phí model; OUTFIT riêng chưa hỗ trợ (báo thiếu trước API), side/cap/geo giữ VÀNG; project_budget chờ#24. KhôngAPI/data thật/cả bộ/gộp main. → GỘP main `4c55e0d` (12/10 06:58).
- Việc 2 · phiên rà Codex · `4aa8ed8` (cờ `auto_send_self_fix`, đã BẬT trên máy chính 12/10) — Codex bỏ qua.


(Codex ghi: việc · nhánh · commit · bằng chứng · việc mở.)


---

# ĐỢT 15 — Chặn bản giao 480p, khóa chạy Đạo diễn, vùng an toàn lớp phủ (hộp thư phiên máy chính 12/10 07:00 / 09:56 / 10:22)

Luật chung GIỐNG đợt 1; nhánh `codex/d15-viec<N>-<tên>` từ `origin/main`; KHÔNG sửa `core/runner.py`, `core/lock_exceptions.py`, `core/end_frames.py`,
`core/place_refs.py`, `core/scene_storyboard.py`; KHÔNG đọc/ghi `data/projects/` (#27 Booyah đang chạy). Không API tốn tiền khi test. Ghi
"Kết quả Codex — đợt 15". **Thứ tự: việc 1 → 2 → 3** (việc 1 chặn lỗi giao hàng thật, làm TRƯỚC Đ12 việc 5).

## Việc 1 — KHÔNG BAO GIỜ giao clip 480p phóng to (người dùng chốt 12/10; KHÔNG cờ — đây là luật)
Hiện `core/delivery.py` ~714: `upscale = {i … if ffmpeg_studio.needs_upscale(c, frame)}` phóng LẶNG LẼ mọi clip nhỏ hơn khung (480p nháp → 1080×1920).
1. Trước `render_final` của **bản giao** (`render_final` khi dựng bản cuối, không phải bản xem nháp — tìm cờ/tham số phân biệt hiện có, vd bản
   DRAFT ở `dashboard/next_step.py:85` "bản dựng lúc này là bản DRAFT"): clip có cạnh ngắn < 720 px khi khung có cạnh ngắn ≥ 1080 → `ValueError`
   nêu TÊN shot + cách sửa ("nâng 1080p hoặc gen ≥ 720p"), không im lặng. 720p → 1080p vẫn được phóng như cũ (E1 đã duyệt).
2. Bản xem nháp (DRAFT) vẫn dựng được nhưng gắn nhãn rõ "NHÁP — có clip 480p" trong manifest + màn Giao (không lẫn với bản giao).
3. Autopilot / Tổ dựng (`core/autopilot.py`, editor) chặn trước khi chọn bản nháp 480p làm bản giao — nói lý do + việc cần làm (nâng bản cao).
4. Báo giá (`cost.estimate_run`, `quality_tier`) KHÔNG tính phương án "nháp 480p làm bản giao".
5. Test: ~15 file test dựng bằng clip rất nhỏ (64×64, 160×284…) → cho test một cách HỢP LỆ (vd luật chỉ áp khi clip đến từ job video thật có
   độ phân giải đo được, hoặc tham số khung test), KHÔNG nới assert. Ca vàng: #24 v3 (shot 02/03/09 còn 480p trong clip nhóm 1080p — hộp thư 11/10 23:53).

## Việc 2 — Khóa chạy Đạo diễn theo dự án + lưu câu trả lời thô (cờ không cần — sửa lỗi)
Ca #27 (12/10 09:56): bấm "🤖 Lập kế hoạch" 2 lần cách ~5 s → 2 lượt Tầng A chạy song song, mỗi lượt tự hỏi lại + Tầng B → mất ~1,5 USD thừa; UI chỉ
hiện lỗi một lượt. Sửa: khóa theo dự án cho `llm_runner.run_director` / `run_director_scene` (cùng kiểu khóa job / `runner._turn` — đọc, không sửa
runner): lượt thứ hai trả "Đạo diễn đang chạy cho dự án này (bắt đầu hh:mm) — chờ xong" và KHÔNG gọi Claude; khóa tự nhả khi lỗi/treo (hạn), sống
qua rerun Streamlit (lưu CSDL hoặc file khóa có PID + giờ). Nút trên Dashboard tắt khi đang chạy (đọc khóa). Khi câu trả lời Claude sai định dạng:
lưu câu trả lời THÔ (đã lọc bí mật, giới hạn cỡ) vào chỗ chẩn đoán (`diag` / thư mục lượt) để xem lại. Test: 2 luồng gọi cùng lúc → 1 lời gọi giả.

## Việc 3 — Vùng an toàn TikTok/Reels cho MỌI lớp phủ (hộp thư 07:00; cờ `overlay_safe_zone` TẮT)
Đã có cho phụ đề (`core/subtitles.py:36-39`, `knowledge/editor/safe_zones.md`) và QC (`core/qc_scene.py:28` TOP_BAR). Mở rộng cho chữ/popup/HUD:
`core/end_popup.py` (popup cuối), lớp chữ khác trong dựng. Vùng tham khảo 1080×1920: tránh trên ~0–150 px (tab), dưới ~25 % (chú thích/nhạc), phải
~120–150 px (cột nút); cấu hình theo nền tảng (dùng lại bảng nền tảng của subtitles). Code kiểm VÀNG khi lớp phủ lấn (không chặn), đề xuất vị trí
trong vùng; có cờ thì tự đặt trong vùng. Ca thật #24 v3: popup 1,8–20 % chiều cao lấn tab trên. Test có cờ/không cờ (không cờ: vị trí giữ y cũ).

## Kết quả Codex — đợt 15

- ✅ Việc 1 · nhánh `codex/d15-viec1-ban-giao` · code `89ce7b61`: đo clip gốc trước dựng/giao/xuất HD, kể cả manual/follower; dưới 720 hoặc không đo được báo shot + nâng 1080p/gen ≥720. Nháp có sidecar và nhãn riêng, không outputs.final/ghi đè. Guard Autopilot trước nhạc, Editor trước stash; export truy nguồn final, legacy thiếu nguồn phải dựng lại. Báo giá không coi 480 là final; nháp paid-running chỉ cộng phần cao, nguồn cao mất báo phục hồi/unknown không gửi thêm. ĐỎ 3 ca → nhóm 14 file 276 xanh/467s; rà 2 finding + follower dedup: 10 subcase đỏ → xanh; nhóm sửa 77 test +10 subtests/15,44s; caller cost/model/picker 21 xanh, UI 13 xanh/29,26s. Assert cũ giữ, fixture xuất khung nhỏ thật. RA `docs/RA_D15_VIEC1_CODEX_2026-10-12.md`. Root đọc phần sửa; giữ areas.version/key. Chưa cả bộ Windows/thử #24–27, không API/dữ liệu thật, chỉ push nhánh. → GỘP main `09396f1`.
- ✅ Việc 2 · nhánh `codex/d15-viec2-khoa-dao-dien` · code `c3853a0d`: khóa chung Director toàn bộ/chia lại cảnh trước call/autoattach; SQLite sidecar PID/token/heartbeat + pending marker atomic chống lượt trả tiền chồng, writer fence chặn chủ cũ ghi. Raw sai định dạng single/scene/A/B/merged lưu đã lọc, 16KB UTF8 ×20/dự án, không đè plan tốt; UI hero/panel/resume/replan giữ key và tắt khi busy. ĐỎ module →79→83 xanh; rà 3 finding, 6 ca đỏ→6 xanh; nhóm 5 file cuối **94 passed /22,39s**. Rà `docs/RA_D15_VIEC2_CODEX_2026-10-12.md`; root đọc phần sửa. Nếu dọn pending lỗi, tiếp tục chặn tới khi xác nhận call đã dừng và khởi động lại tiến trình sở hữu. Chưa cả bộ Windows/UI/API thật, không dữ liệu sản xuất, giữ areas.version, chỉ push nhánh. → GỘP main `09396f1`.


(Codex ghi: việc · nhánh · commit · bằng chứng · việc mở.)

---

# ĐỢT 16 — ƯU TIÊN SỐ 1 (người dùng giao 12/10 12:12, TRƯỚC mọi đợt khác) — 2 lỗi chặn dự án #27 Booyah

Luật chung GIỐNG đợt 1 (cả luật người dùng 12/10: rà kĩ, đánh giá hiệu quả). Nhánh `codex/d16-viec<N>-<tên>` từ `origin/main` MỚI NHẤT. Không API tốn tiền khi
test (Claude/ảnh = giả). KHÔNG đọc/ghi `data/projects/`. `core/runner.py` được SỬA TỐI THIỂU chỉ khi gốc lỗi nằm ở đó (ghi rõ dòng + lý do trong báo cáo; #27
đang chạy trên runner — không đổi gì khác). Xong việc nào push nhánh việc đó NGAY + ghi "Kết quả Codex — đợt 16" (phiên rà Codex gộp gấp, phiên máy chính
chờ để gen tiếp #27: shot 16 + 21 vẽ lại rồi 17 ảnh còn lại). Ca thật: hộp thư `TODO.md` dòng [12/10 12:10] + [12/10 12:12], `TODO.md` "#27 ẢNH THỬ v3".

## Việc 1 — Từ chối ảnh kèm ghi chú KHÔNG chạy Đạo diễn viết lại prompt (cờ `director_rewrite` đang BẬT trên máy chính)
#27 shot 16: 2 lần `Pipeline.reject(job, 'user', note=…)` mà `prompt_rewrite.versions` = 0; ghi chú chỉ nối cuối prompt ("Fix: …") → mất ý ghi chú
lần trước, chữ mâu thuẫn cũ ('translucent amber') vẫn còn. Đường code: `core/pipeline.py` `reject` → `_rewrite_before_retry` →
`prompt_rewrite.before_retry` → `.apply()` trước `_spawn_retry`; `prompt_rewrite.rewrite_for_retry` (`core/prompt_rewrite.py:296`) KHÔNG có nơi nào gọi
— tìm vì sao nhánh viết lại không chạy với ảnh (image_gen) / với người từ chối (by='user'): cờ đọc sai chỗ, điều kiện kind/state, Claude lỗi bị nuốt
(diag nói gì?), hay runner gửi job con với prompt cũ (đọc prompt trước `.apply()`?). Sửa tận gốc; **ghi chú tích lũy**: lần từ chối sau phải giữ ý các
lần trước (đưa đủ lịch sử ghi chú cho Đạo diễn), và Đạo diễn viết lại BỎ chữ mâu thuẫn chứ không nối thêm. Không viết lại được (Claude lỗi) → nói rõ
trên Dashboard + diag (không im lặng), giữ cách "Fix: …" cũ. **Test chạy ĐƯỜNG THẬT**: `Pipeline.reject` (user + note, image_gen và video_gen) → job con
→ `runner.submit_pending` với provider giả bắt prompt GỬI ĐI → assert prompt mới (không còn chữ cũ, có ý cả 2 ghi chú) + `prompt_rewrite` có version.

## Việc 2 — `project_prop_lock`: bỏ từ mâu thuẫn khỏi prompt gửi đi + tỉ lệ vũ khí
(a) Món khóa ở DẠNG MẶC ĐỊNH (vd tường keo Gloowall trắng đục) mà chữ shot có từ màu/chất liệu mâu thuẫn ('translucent amber glue-grenade wall') → hiện chỉ
VÀNG + câu 'overrides' và ảnh vẫn ánh vàng. Sửa: code BỎ/THAY các từ màu-chất liệu mâu thuẫn trong cụm tả món đó ở prompt GỬI ĐI (giữ bản gốc trong dữ liệu,
hiện diff "đã bỏ: translucent amber" trên Dashboard), chỉ khi món ở dạng mặc định; dạng skin khác thì theo mô tả skin. Không xóa từ ngoài cụm của món đó.
(b) Tỉ lệ vũ khí: model vẽ SKORP (SMG) nhỏ như súng lục dù có ảnh Kelly cầm SKORP → mô tả món Kho có trường kích thước/tỉ lệ so người (vd "SMG about
forearm-to-shoulder length, held two-handed with the stock") và prop_lock chèn câu tỉ lệ đó vào prompt khi món có mặt; món chưa có tỉ lệ → VÀNG "thiếu tỉ lệ".
Đánh giá hiệu quả (luật (c)): có nên lấy tỉ lệ tự động theo loại súng (SMG / súng trường / súng lục) thay vì nhập tay từng món không. Test: prompt gửi đi
của ca shot 16 không còn 'translucent amber'; câu tỉ lệ có khi món SKORP có mặt; cờ TẮT giữ y cũ.

## Việc 3 — ✅ PHIÊN RÀ CODEX ĐÃ LÀM (12/10 14:14, Codex BỎ QUA — gộp main) — KHÓA SÚNG THEO NHÂN VẬT (người dùng 12/10 13:19, ƯU TIÊN SỐ 1 cùng việc 1–2; cờ `project_prop_lock` — dùng chung cờ, đã BẬT trên máy chính)
Người dùng: "khóa sẵn nhiều súng, tránh tự ý dùng và gán sai". Hiện `project_prop_lock` chỉ chạy khi dự án gắn MỘT súng; nhiều súng → chỉ VÀNG. Làm TRÊN
nhánh việc 2 đã gộp (`core/prop_lock.py` clean_prompt / weapon_scale). Ca thật #27 (bảng người dùng ĐÃ DUYỆT, `TODO.md` khối 📌 12/10 13:21): KELLY → SKORP
#433 · LÍNH ĐỊCH ÁO CHOÀNG → M7 #434 · SỨ GIẢ BÓNG ĐÊM → HAWK #435 · XÚC TU ĐỎ → RPK #436 · YÊU NỮ TÀ LINH DẠNG 1 → M7 #434; đeo súng sau lưng = Kho style
#437 'ĐEO SÚNG SAU LƯNG'. Mô tả Kho #433–436 đã có câu "In-game scale …" (commit main `0932435`).
(a) **Bảng gán theo dự án** `nhân vật → vũ khí Kho` (lưu như `assets.set_outfit` / `outfit_images`; KHÔNG sửa `lock_exceptions.py`): Bible/Bước 1 có ô chọn súng
cho từng nhân vật (gọn — một ô chọn cạnh trang phục, luật chung (a)); Đạo diễn ĐỀ XUẤT khi chạy (khai `vu_khi` theo nhân vật), người dùng duyệt = khóa;
đổi gán → shot đã duyệt VÀNG "cần vẽ lại", không tự gen.
(b) **Prompt ảnh/video**: shot có nhân vật X cầm súng (từ chung "gun/rifle/súng" hoặc tên sai) → chèn ĐÚNG súng của X (tên + mô tả dạng mặc định) + câu tỉ lệ từ
mô tả Kho (trọn câu) + ảnh tham chiếu cầm súng đúng tỉ lệ (ảnh chính của món, vd `kelly_cam_skorp…`) trong Gói gửi kèm; shot nêu súng KHÁC súng đã khóa của
X → ĐỎ trước gen (nói tên shot + súng đúng); nhân vật chưa gán súng mà shot có súng → VÀNG nêu tên nhân vật, KHÔNG đoán; nhân vật không cầm (súng đeo sau
lưng) → dùng ref style #437 + câu "slung on back, correct size", không vẽ súng trên tay.
(c) **Nhiều người cùng khung** (#27 shot 16: 4 địch bắn nhau): mỗi người đúng súng của mình (gắn câu theo từng người, không gộp "they hold rifles"); ảnh ref
không vượt trần ảnh gửi kèm (giữ chỗ như bản sửa 12/10: ưu tiên mặt > trang phục > súng, súng trùng nhiều người chỉ 1 ảnh).
(d) `_plain` 280 ký tự đang cắt đuôi câu "In-game scale …" → giữ TRỌN câu tỉ lệ (cắt chỗ khác hoặc tách câu tỉ lệ riêng); không chèn tỉ lệ đôi (câu Kho +
câu suy theo loại) — có câu Kho thì dùng câu Kho.
Đánh giá hiệu quả (luật (c)) trước khi làm UI: ô chọn ở đâu ít bấm nhất; có cần Đạo diễn đề xuất hay chỉ bảng tay. Test: ca #27 dựng lại bằng dữ liệu giả (5
nhân vật, 4 súng): prompt gửi đi mỗi người đúng súng + trọn câu tỉ lệ; shot nêu sai súng → ĐỎ; nhân vật chưa gán → VÀNG; đeo sau lưng; cờ TẮT giữ y cũ.
`core/runner.py` sửa tối thiểu nếu cần (như việc 2) + ghi lý do. (ĐÃ LÀM — phiên rà Codex; không có nhánh Codex.)

## Kết quả Codex — đợt 16

- Việc 1 · nhánh `codex/d16-viec1-viet-lai-prompt` · code `09778931`: lịch sử user-note đúng chuỗi parent cùng shot/loại, giữ ý các lần từ chối; client config LlmError không bị nuốt; fallback hiện trên Dashboard kể cả versions=0, chẩn đoán chọn last_at/id. ĐỎ history ảnh/video và lỗi client →45 test+4subtests xanh; rà1P2 cảnh báo lặp đỏ→xanh, nhóm cuối **46 passed +4 subtests /4,74s**. Test đường thật reject→child→Image/VideoRunner.submit_pending bắt provider.submit: hai ý note, bỏ translucent amber, không Fix, 3 phiên bản; OFF giữ Fix/noClaude. Không sửa runner/pipeline, giữ areas.version/key. RA `docs/RA_D16_VIEC1_CODEX_2026-10-12.md`. **CHƯA xác nhận nguyên nhân production #27 versions=0**: hook đã nối ở base; cần phiên máy chính xem diag fallback/config và thử thật sau gộp. Cùng giây chẩn đoán và cảnh báo không gắn prompt/job còn giới hạn. Không API/data thật/cả bộ/gộp main. → GỘP main `09396f1`; nguyên nhân #27 XÁC NHẬN 14:35 = script không nạp khóa.
- ✅ Việc 2 · nhánh `codex/d16-viec2-khoa-dao-cu` · code `cc74097`: làm sạch riêng action/fix ở builder gửi ảnh, chỉ cụm món mặc định, giữ scene/Kho/skin và OFF từng byte; preview hiện 'sẽ bỏ'. Người dùng chốt **tự suy tỉ lệ theo loại súng**: metadata/số đo ưu tiên, heuristic ghi Estimated/not measured và chỉ kích cỡ, không ép pose; loại thiếu/mâu thuẫn VÀNG. ĐỎ 3 ca (a), 3 ca (b) →56 xanh; RÀ KỸ 6 finding →6 đỏ→6 xanh; nhóm cuối **62 passed /4,53s**, giữ realism_removed/key/version. Root đọc phần sửa và kiểm component Streamlit thật bằng Chrome Playwright tại1440/1280:0 pageerror/0 tràn ngang; 2 PNG `docs/images/d16/prop_lock_*.png`. RA `docs/RA_D16_VIEC2_CODEX_2026-10-12.md`. Runner sửa tối thiểu builder2134–2139 vì trước gửi nguyên cụm mâu thuẫn. Chưa model thật/toàn Dashboard/cả bộ Windows; parser cố ý hẹp, không NLP rộng. Không API/dữ liệu thật/gộp main. → GỘP main `ae97885`.
- Việc 3 · phiên rà Codex · `8a1a6be`/`185794d` gộp `ae97885`; bổ sung VÀNG "người khác dùng súng đã khóa" `8e66b16`/`2f03b29` (gộp `3ac9c4f`/`b9ae7a2`).


(Codex ghi: việc · nhánh · commit · bằng chứng · việc mở.)

---

# ĐỢT 17 — Lỗi hệ thống khi vẽ #27 Booyah (hộp thư phiên máy chính 12/10 14:35 / 14:41 / 15:07 / 15:22)

Luật chung GIỐNG đợt 1 (cả luật người dùng 12/10: giao diện gọn, rà kĩ, đánh giá hiệu quả). Nhánh `codex/d17-viec<N>-<tên>` từ `origin/main` MỚI NHẤT. Không
API tốn tiền khi test; KHÔNG đọc/ghi `data/projects/`. #27 đang vẽ ảnh: thay đổi hành vi sau cờ sẵn có (`project_prop_lock`, `director_rewrite`) hoặc cờ mới
TẮT; `core/runner.py` chỉ sửa tối thiểu khi gốc lỗi nằm đó (ghi lý do). Phiên máy chính đã sửa tay dữ liệu #27 cho từng ca — đây là sửa TẬN GỐC.
Thứ tự: việc 1 → 2 → 3. Xong việc nào push nhánh việc đó ngay + "Kết quả Codex — đợt 17".

## Việc 1 — Đạo cụ / súng khóa (ca thật #27 shot 16, job 700)
**Đã có trên main — dùng lại, không viết lại:** `prop_lock.shot_text` đã bỏ dòng thoại/lời dẫn (`fe8bfff`, dùng `assets._without_spoken_lines` `a38bdb3`); `prop_lock.match_refs` đã bỏ câu 'as its reference picture shows' khi ảnh khóa không được gửi (`640085e`) — (c) chỉ còn thêm VÀNG + đánh giá ưu tiên; `assets.scene_references` giữ chỗ tài nguyên nhắc tên (`5e1d410`).
(a) **Đạo diễn viết lại prompt tự chèn tên DẠNG skin** ('Gloowall OB55', lấy từ mô tả Kho #367) dù prompt cũ + ghi chú không có → `prop_lock.chosen_variant`
chọn skin → gửi ảnh cửa thang máy kim loại, trong khi cùng câu ghi 'plain white… no pattern' (0,052 USD mất). Sửa: sau khi Đạo diễn viết lại
(`core/prompt_rewrite.py`, cùng chỗ kiểm `_new_people`), CODE kiểm tên dạng/biến thể đạo cụ mới xuất hiện mà prompt cũ + ghi chú không có → gỡ (hoặc từ chối
bản viết lại, quay về cách cũ có báo) + test. (b) `prop_lock.issues` VÀNG khi chữ shot nêu tên dạng skin NHƯNG tả màu/chất liệu của dạng mặc định (mâu
thuẫn dạng). (c) **Ảnh khóa bị rơi vì trần ảnh**: job 700 `reference_images` có 4 ảnh súng nhưng gửi đi chỉ có 5 nhân vật + Bom keo + 2 nền + storyboard (9) —
súng rơi IM LẶNG. Báo VÀNG (Dashboard + diag) khi ảnh khóa không được gửi vì trần, và đánh giá ưu tiên ảnh khóa hơn ảnh nền rộng (plate_wide) — lưu ý
phiên máy chính vừa sửa `assets.scene_references` 15:22 (tài nguyên được nhắc tên giữ chỗ trước ảnh mặt thứ 2; test
`test_a_named_prop_keeps_its_slot_over_second_face_pictures`) — giữ hành vi đó. (d) **Shot góc nhìn thứ nhất (POV / first-person) có chữ súng**: người dùng
— FF không có góc nhìn thứ nhất khi cầm súng → code kiểm VÀNG/ĐỎ trước gen (đánh giá mức) + `prop_lock` KHÔNG chèn câu/ảnh súng cho shot POV (bài học Đạo diễn
13 đã có). Test từng ca; cờ TẮT giữ y cũ.

## Việc 2 — Popup icon GIỮA PHIM theo shot (người dùng #27)
`core/end_popup` chỉ ghép icon ở cuối phim; người dùng muốn icon 'QUÉT SẠCH ĐỘI' (Kho #432) bật lên ở CUỐI shot 20 (lúc hạ gục hết địch) ~1,5 s + tiếng pop.
Phiên máy chính đã ghi tạm `scene.data.post_popup = {asset_id, at:'end', seconds, pop_sound}` ở shot 20 — CHƯA code nào đọc. Làm: dựng (delivery / end_popup)
đọc `post_popup` từng shot (vị trí theo thời gian shot trên timeline bản dựng, dùng lại hiệu ứng pop + âm của popup cuối), VÀNG khi có `post_popup` mà không
ghép được (không im lặng). Ảnh #432 còn nền xanh đặc (627×423 RGBA) → tách nền (chroma key có sẵn trong ffmpeg_studio? kiểm) hoặc cho chọn khung cắt. Vị
trí trong vùng an toàn: dùng bảng nền tảng/vùng an toàn có sẵn của `core/subtitles` (ĐỢT 15 việc 3 làm SAU sẽ phủ thêm popup này). Ô chỉnh trên Dashboard gọn (luật (a)): bật popup cho shot + chọn ảnh Kho + giây. Cờ mới `shot_popup` TẮT.

## Việc 3 — Khớp tên Kho (gửi thiếu ảnh mẫu / khớp nhầm)
(a) Khớp tên Kho chỉ nguyên cụm + Kho Claude tạo chỉ có tên Việt → chữ shot tiếng Anh không kéo ảnh mẫu (cổng torii #426 không được gửi ở shot 2 → cổng sai;
phiên máy chính đã thêm biệt danh tiếng Anh tay cho #426/#428/#429/#438–440). Sửa: lúc tạo mục Kho (Claude hoặc người) BẮT BUỘC ≥ 1 tên tiếng Anh (đề xuất tự
động, người sửa được); VÀNG khi chữ shot tả một vật dự án đã gắn mà không khớp tên (vd 'torii' nằm trong tên/mô tả). (b) `assets.find_in_text` khớp 'no'
(tiếng Anh) với 'Nỏ' #360 do so khớp bỏ dấu khi chữ không dấu → danh sách từ tiếng Anh thường (no, not, gun, …) không bao giờ khớp tên Việt gấp dấu; test.
(c) Tài nguyên kind `style` (#427 bóng mờ, #428 trời song song) KHÔNG bao giờ được gửi làm ảnh ref (assets chỉ nhận weapon/prop/pet/location/outfit) — đúng
nếu ảnh có HUD, nhưng phải NÓI (VÀNG "kiểu ảnh chỉ dùng bằng chữ") thay vì im lặng; đánh giá có nên cho gửi style không HUD.
(d) Việc nhỏ (hộp thư 15:22) — LƯU Ý: `dashboard/design/screens/prompt_versions_ui.panel` (Codex Đ16v1 `0977893`) ĐÃ chọn sự kiện mới nhất FALLBACK/DONE; tái hiện ca 04:53 trước (lần viết lại thành công có ghi DONE cùng stage không — `runner._diag` ghi fallback riêng), chỉ sửa chỗ thiếu. Ca: thẻ shot vẫn hiện cảnh báo `director_rewrite_fallback` CŨ (04:53, hồi script chưa nạp khóa) dù các lần viết lại sau đã thành
công → chỉ hiện cảnh báo của lần gen lại MỚI NHẤT (trùng ĐỢT 13 việc 4 mục 9 — làm ở đây, Đ13 bỏ qua mục đó).

## Kết quả Codex — đợt 17

- ✅ Việc 1 · bổ sung code `2064df8b` sau phần `3b072ca3`, cùng nhánh `codex/d17-viec1-dao-cu`: người dùng chốt ưu tiên ảnh súng khóa thay đúng slot nền rộng phụ, giữ nền chính/storyboard/nhân vật/skill/previous và cap; mapping dựng sau thay ảnh. POV+súng chỉ VÀNG, không chèn câu/ảnh khóa súng, giữ đạo cụ khác và ảnh nhận diện người; guard sai chủ súng độc lập giữ mức cũ. Cùng súng/dạng dùng chung ảnh đã có, collage nhiều món để sau vì chưa thử chất lượng. ĐỎ→XANH **91 passed +30 subtests /7,80s**; rà c/d bắt 1 P2 phủ định OTS/TPS →4 subcase đỏ→xanh, root đọc diff sửa. UI không đổi thêm, giữ bằng chứng 1440/1280 phần trước. Không API/dữ liệu thật/cả bộ Windows/gộp main; RA và handoff đã cập nhật. Đã hoàn tất phạm vi code Đ17v1; thử model thật vẫn mở.

- 🟡 Việc 1 · nhánh `codex/d17-viec1-dao-cu` · code `3b072ca3`: a/b + c cảnh báo hoàn tất trong phạm vi đã chốt. Rewrite từ chối skin mới ngoài prompt/ghi chú khẳng định, phân biệt mã skin, vẫn kiểm metadata khi ảnh mất; VÀNG mâu thuẫn thuộc tính cùng cụm đạo cụ. Gói refs cuối ghi diag/hiện Dashboard khi ảnh khóa thiếu; giữ namedprop reservation, chưa đổi ưu tiên. ĐỎ a/b/c + 8 subcase rà → **86 passed +14 subtests /7,48s**; 4 finding độc lập sửa gom, root đọc diff. QA component Streamlit thật Chrome 1440/1280 với dữ liệu giả: 0 pageerror/0 tràn ngang, 2 PNG `docs/images/d17/`. Giữ keys/areas.version; runner chỉ thêm cảnh báo tại `_finish_args`, lý do trong RA. **Còn chờ người dùng chốt c ưu tiên plate_wide và d POV; chưa hoàn tất toàn việc.** Chưa API/model thật/cả bộ Windows/gộp main. Bàn giao `docs/HANDOFF_D17_VIEC1_CODEX_2026-10-12.md`; rà `docs/RA_D17_VIEC1_CODEX_2026-10-12.md`.
- ✅ Việc 2 · nhánh `codex/d17-viec2-popup-shot` · code `e129832c`: cờ `shot_popup` OFF/OPT_IN_ONLY; đọc post_popup từng shot, timeline clip thực trim/xfade và nháp, cùng hiệu ứng pop/âm/safe_box, không kéo dài shot. Tách xanh nối biên tùy chọn, giữ ảnh gốc/xanh kín; UI chọn một shot, một hàng bật/Kho/giây + nút lưu, server kiểm quyền và scene-project. Thiếu shot/ảnh/âm/đo/cấu hình báo VÀNG diag+manifest, hash theo spec/bytes/platform. ĐỎ module + caller draft; rà 4 finding và selector/videopath → **102 passed +10 subtests /22,87s**, focused output_video **6 đỏ→6 xanh /0,21s**. Root đọc vòng sửa; UI component Streamlit fakeowner Chrome1440/1280:0 pageerror/0 overflow,2 PNG `docs/images/d17/`. areas khai module/test/cờ, giữ version/keys. RA `docs/RA_D17_VIEC2_CODEX_2026-10-12.md`. Chưa thử #27/cả bộ Windows/bật sản xuất/gộp main; lookup legacy end-popup không local_root giữ assets.get cũ, guard mới bảo đảm mọi popup shot.
- ✅ Việc 3 · nhánh `codex/d17-viec3-ten-kho` · code `e55255ca`: cờ `asset_english_names` OFF/OPT_IN_ONLY, tên Anh/tên riêng qua aliases, gợi ý cục bộ có căn cứ; không migration/backfill/API dịch mới. Chặn no→Nỏ, giữ alias rõ và cụm Việt không dấu; cảnh báo danh từ cụ thể của vật đã gắn chưa khớp tên + style chỉ dùng chữ, không đổi selector. DONE chung ở save_rewrite cho caller scripts, panel giữ nguyên. Costume kiểm tên/alias trước tiền và sau download, race đổi số lưu ảnh đã có tối đa3 lần không submit lại; ff_site nói rõ từng skip. ĐỎ 5 +2 caller, rà 2 finding→3 đỏ→xanh; nhóm7file **154 passed +4 subtests /53,14s**; root đọc diff sửa. UI component Kho chung/riêng bằng Chrome1440/1280:0 pageerror/0 tràn ngang,4PNG `docs/images/d17/english_*.png`. RA `docs/RA_D17_VIEC3_CODEX_2026-10-12.md`. Giữ keys/areas.version, không API/dữ liệu thật/main. Chưa cả bộ Windows/thử #27; danh từ cảnh báo hữu hạn, ngôn ngữ do người nhập xác nhận, style không HUD chưa gửi ảnh.

(Codex ghi: việc · nhánh · commit · bằng chứng · việc mở.)

# ĐỢT 18 — Shot liền mạch dùng CHUNG một sân khấu 3D (người dùng 12/10, hộp thư phiên máy chính 19:20)

Luật chung GIỐNG đợt 1 (cả luật người dùng 12/10: giao diện gọn, rà kĩ, **ý tưởng là góp ý → đánh giá hiệu quả trước khi build**). Nhánh
`codex/d18-viec<N>-<tên>` từ `origin/main` MỚI NHẤT. Không API tốn tiền khi test; KHÔNG đọc/ghi `data/projects/`. #27 đang vẽ: mọi đổi hành vi sau cờ
TẮT; `core/runner.py`, `scene_storyboard.py`, `plate_camera.py`, `plate_choice.py`, `place_refs.py` chỉ sửa TỐI THIỂU (ghi lý do). Thứ tự: việc 1 → 2 → 3;
việc 4 CHỈ sau khi người dùng duyệt kế hoạch việc 1.

**Người dùng muốn:** Director đã phân cảnh kỹ; các shot cùng ĐOẠN liền mạch (cùng chỗ, hành động nối tiếp — KỂ CẢ khi truyện rẽ nhánh rồi quay lại cùng
chỗ) dùng chung MỘT bộ dựng 3D: bối cảnh + vị trí nhân vật chính/phụ + vật (đồng đội gục, tường keo, súng dưới đất…); mỗi shot chỉ đặt MÁY khác trên sân
khấu đó → đổi góc/tình huống không lệch bố cục.
**Ca thật #27 (12/10):** shot 11–12 hàng đồng đội gục đổi chỗ/chồng nhau so với shot 1–3 (khác `sequence`); S07 chỗ nhặt súng trùng chỗ đấu súng; S08-2 Kelly
núp sai phía tường keo (máy nhìn về tháp → cô ở phía địch).
**Đã có — dùng lại, KHÔNG viết lại:** vá tạm của phiên máy chính `4b280d6`: `scene.data.continuity_from` (idx shot trước) → `runner.layout_reference` gửi ảnh
shot đó vai `layout_from` (`assets.reference_note`, `storyboard_frames.mapping_text`), `scene_storyboard.other_spot` (plate_spot khác shot neo → không ảnh
neo), `tests/test_layout_from_p27.py`; `core/camera_plan` (G0, cờ `director_camera_plan` TẮT — sơ đồ cảnh + bộ góc máy cho cảnh trên bối cảnh có 3D);
`core/stage_director` + `stage_solver` (Sân khấu 3D v2 — dàn cảnh `blocking` + `shot_specs` MỘT cảnh); `core/blockout_sheet` (tấm duyệt 2D, chưa nối
pipeline); `core/continuity.layout_warnings` (cờ `continuity_layout` TẮT — kiểm hướng đi/bố cục). Kế hoạch gốc: `docs/KE_HOACH_DAT_MAY_3D_2026-10-09.md`,
`docs/PHUONG_PHAP_SAN_KHAU_3D.md`.

## Việc 1 — Kế hoạch + đánh giá (CHỈ tài liệu, không code) → `docs/KE_HOACH_SAN_KHAU_DOAN_2026-10-1x.md`
(a) Bản đồ hiện trạng: 4 module trên làm gì, dữ liệu nằm đâu (scene.data `sequence`/`story_scene`/`plate_spot`/`plate_view`/`blocking`/`continuity_from`,
`location_pack`, tệp plan của camera_plan), đường nào ĐANG chạy trên #27, đường nào cờ TẮT/chưa nối. (b) Định nghĩa **"đoạn liền mạch"** (segment): khóa
đề xuất (location + plate_spot + mốc thời gian truyện?) — ai đặt (Director ghi / code suy từ sequence + plate_spot / người sửa trên Dashboard), ca rẽ nhánh
quay lại cùng chỗ (#27 shot 1–3 ↔ 11–12). (c) **Dữ liệu sân khấu một đoạn**: vị trí người + vật (toạ độ trên mặt bằng bối cảnh, hướng mặt, tư thế: đứng/
gục/núp), thay đổi giữa các shot trong đoạn (ai đi đâu, vật xuất hiện/mất — tường keo dựng ở shot 15), máy từng shot. Dùng cho: render nền 3D, câu prompt
(vị trí bằng chữ), ảnh neo, QC (so ảnh với sân khấu). (d) **Đánh giá hiệu quả** (luật c) — bảng: phương án A "chỉ dữ liệu 2D mặt bằng + câu prompt +
ảnh layout_from" / B "đặt người-vật thật trong Blender (stage_solver) mỗi đoạn" / C "giữ vá tạm continuity_from + VÀNG khi lệch"; mỗi phương án: lỗi #27 nào
nó chặn được, công sức, rủi ro, chi phí API mỗi đoạn, số bấm của người dùng; ghi "KHÔNG NÊN LÀM" nếu lợi ít. (e) Lộ trình tối thiểu cho #27 còn đang vẽ (cái
gì làm được ngay không cần Blender). Người dùng duyệt bảng đánh giá → mới làm việc 4.

## Việc 2 — Ảnh neo storyboard theo NHÓM (story_scene, plate_spot) thay vì cả cảnh
Rà 12/10: shot neo đổi chỗ đứng → `other_spot` làm CẢ cảnh mất ảnh neo. Sửa: chọn ảnh neo trong từng nhóm (story_scene, plate_spot) — shot cùng chỗ đứng
nhận neo của shot đầu nhóm đó; shot không có plate_spot giữ cách cũ; VÀNG khi nhóm chưa có ảnh neo nào duyệt. Sau cờ TẮT mới (đề xuất `anchor_by_spot`);
cờ TẮT giữ y cũ (test). Kiểm hai hướng: không nhận neo khác chỗ, không mất neo cùng chỗ.

## Việc 3 — Ô `continuity_from` trên Dashboard (Bước 1/2, thẻ shot)
Hiện chỉ sửa được bằng dữ liệu. Thêm ô gọn (luật a): chọn "Giữ bố cục theo shot …" (danh sách shot TRƯỚC, cùng địa điểm lên đầu), hiện ảnh nhỏ shot đó +
trạng thái (đã duyệt / chờ duyệt / chưa có ảnh — VÀNG như runner nói), nút bỏ. Ghi qua `llm_io.update_scene` (đã nhận `continuity_from`, có lineage +
change_review) — kiểm quyền sửa như các ô khác. Ảnh chụp 1440 + 1280.

## Việc 4 — (SAU khi người dùng duyệt việc 1) build phương án được chọn, sau cờ TẮT
Đề bài chi tiết sẽ viết sau khi người dùng chốt. Không bắt đầu trước.
**[14/10 18:09, người dùng giao qua phiên cloud]:** người dùng đã chọn phương án A (13/10). Codex **VIẾT ĐỀ BÀI CHI TIẾT trước** (yêu cầu ở hộp
thư `TODO.md` dòng [14/10 18:09]) → người dùng duyệt → mới build. Đây là chỗ nghẽn của Đ11 việc 3 (Trình sửa sân khấu + màn Camera trên Dashboard) và
Đ11 việc 5. `anchor_by_spot` giữ TẮT (người dùng 14/10) — không thiết kế phụ thuộc vào nó.

## Kết quả Codex — đợt 18

- ✅ Việc 1 · nhánh `codex/d18-viec1-ke-hoach-san-khau` · tài liệu `c460d6cd`: `docs/KE_HOACH_SAN_KHAU_DOAN_2026-10-12.md` đối chiếu code/callers/flags, phân biệt stage–segment–state, snapshot/transform/provenance/dependency và quyền dự án/Owner publish; bảng A/B/C ghi đúng giới hạn dữ liệu/proxy/model, chi phí API bổ sung và công/bấm chưa đo, lộ trình không cần Blender. Khuyến nghị A trước→B cùng dữ liệu, C gỡ trước mắt; **chờ người dùng chọn trước Đ18v4**. Root RÀ NHẸ + kiểm nguồn/dòng/link, RA `docs/RA_D18_VIEC1_CODEX_2026-10-12.md`; docs-only không tạo test đỏ giả, không đổi code/cờ/areas/TODO/PLAN/API/data. Chưa xác minh runtime #27/QA chất lượng. Đ18v2/v3 độc lập có thể tiếp; v3 đề ghi chỉ shot trước nhưng main đã cho shot sau, phải đối chiếu trước build.

(Codex ghi: việc · nhánh · commit · bằng chứng · việc mở.)

- ✅ Việc 2 · nhánh `codex/d18-viec2-anh-neo-theo-spot` · code `f89cbad6`: nhóm neo theo story_scene/plate_spot, shot đầu nhóm, singleton ảnh đơn; cờ anchor_by_spot OFF/OPT_IN_ONLY. ĐỎ→XANH 50 test /7 file /5,61s; rà độc lập và root sửa 3 P2 về đếm phụ thuộc, ảnh neo thiếu và cache OFF. Không đổi UI/keys, areas giữ version65. Chưa thử model thật/cả bộ Windows/bật sản xuất; không API/dữ liệu thật/gộp main. RA và HANDOFF Đ18 việc2 kèm nhánh.
- ✅ Việc 3 · nhánh `codex/d18-viec3-giu-bo-cuc` · code `5865a18`: ô giữ bố cục dùng chung Bước1/2 cả thẻ v2, nguồn trước cùng địa điểm lên đầu, giữ nguồn tương lai hiện có; thumbnail/trạng thái/nút bỏ, ghi update_scene có quyền và lineage/change_review. Cờ continuity_from_ui OFF/OPT_IN_ONLY, giữ keys/version66. ĐỎ→XANH 27 test /6,56s; rà độc lập sửa1P2 thiếu hookv2, root đọc fix. QA Chrome component và thẻv2 thật với DB/ảnh tạm1440/1280:0JS/0exception/không tràn,2PNG docs/images/d18. Chưa sản xuất/cả bộ Windows/API/gộp main. Việc4 vẫn chờ duyệt kế hoạch việc1.

## Bổ sung Kết quả Codex — đợt 10

- ✅ Việc 3b · nhánh `codex/d10-viec3b-project-budget` · code `27c2e9f3`: remaining dùng chung quote có stamp/group/nháp/bản cao; nháp duyệt ON chỉ cộng nâng, giữ guard bản giao; QC enum không cộng agent/team hai lần. Rà 3 P2 sửa: giá chưa xác minh ×1,25, QC bản cao, thiếu toàn bộ giá báo subtotal/incomplete thay 0 đủ giá. ĐỎ→XANH 124 test +6 subtest và 32 test +6 subtest, tổng146 test riêng biệt; không nới test. QA money_card thật DB/giá giả known/missing 1440/1280:0JS/exception/overflow,4PNG. Root đọc fix/xem ảnh; keys/areas.version66 giữ. Chưa production/cả bộ Windows; không API/data thật/runner/main. RA/HANDOFF13/10 kèm nhánh.

## Bổ sung Kết quả Codex — đợt 11

- 🟡 Việc1b · nhánh codex/d11-viec1b-doi-chieu · tài liệu63fb5000: mục9 đánhgiá đủ20dòng ClipAI + stage/segment/state và điểm nối code, khuyếnnghị mockupgọn9c. Root RÀNHẸ/đốichiếu sốdòng; docs-only khôngpytest/fakered. CHỜ người dùng chốt trước HTML/test/ảnh, chưa hoàn tất toàn việc. Không API/data/backend/TODO/PLAN/areas/main.

# ĐỢT 19 — V3.1: regression lời dẫn, đối soát giá, thiết kế M1.4b + M1.5 (người dùng 20/10, hộp thư phiên `dashboard-chi-tiet-update`)

**Đọc trước:** `docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md` (kế hoạch chính; mục 4b cấp quyền), `docs/V3_1_GOI_SUA_VA_RUI_RO_2026-10-20.md` (audit,
phạm vi từng gói), `data/decisions.json` mục `v31-*` (D01–D10 đã chốt = chính sách, KHÔNG phải lệnh triển khai).
**Phạm vi người dùng duyệt 20/10 ("PHÊ DUYỆT TRIỂN KHAI CÓ KIỂM SOÁT — V3.1"):** đợt này CHỈ test, công cụ chỉ đọc và tài liệu thiết kế. Phiên Claude đang
làm M1.1 + M1.4a → **KHÔNG sửa** `core/qc_observe.py`, `core/shot_intent.py`, `core/llm_runner.py`, `tests/test_qc_observe_d14.py`, `tests/test_shot_intent.py`.
**Luật:** nhánh `codex/d19-viec<N>-<tên>` từ `origin/main` MỚI NHẤT; không gọi API trả phí; không đọc/ghi `data/projects/`; không migration, không sửa
`data/manifest.sqlite`, không xóa asset ClipAI; không đổi bảng giá; không bật cờ. Mỗi việc một nhánh + báo cáo `docs/RA_D19_VIEC<N>_CODEX_2026-10-2x.md`
(việc · nhánh · commit · test đỏ→xanh · việc mở). Phiên Claude rà quy ước 7 rồi mới gộp. Mã việc V3.1 ghi trong ngoặc.

## Việc 1 — Bộ regression lời dẫn chung (V3.1 M2.9 — CHỈ TEST, không sửa code sản xuất)
File mới `tests/test_narration_regression.py`: MỘT bảng ca, chạy qua mọi hàm đang xử lý lời dẫn / người nói: `core/lipsync.py` (`_method`, `_take_segments`,
`shot_audio`, `mark`), `core/speaker_lint.py:is_narrator`, `core/seedance_refs.py` (cảnh báo `speaker_no_identity` ~546–552), `core/claude_tasks.py:323`
(`speaking`), `core/quality_tier.py` (shot khó vì `lip_sync`). Ca bắt buộc: (a) shot chỉ lời dẫn, không cast (POV); (b) lời dẫn + nhân vật trong khung không nói;
(c) nhân vật nói thật; (d) thoại trộn lời dẫn + một câu nhân vật; (e) biến thể tên người dẫn (`LỜI DẪN`, `Lời dẫn`, `NARRATOR`, `người dẫn chuyện`); (f) method
đổi lipsync → skip phải dọn mục cũ. Mong đợi đúng như mục 4 của `docs/V3_1_GOI_SUA_VA_RUI_RO_2026-10-20.md`. Ca đang SAI trên `main` (G15, G16, G17, G53)
→ `pytest.mark.xfail(strict=True, reason="G53 …")` có mã lỗi — để khi M2.9 sửa, xfail thành đỏ buộc gỡ. Không nới test để che lỗi.

## Việc 2 — Công cụ đối soát giá ClipAI theo token (V3.1 M1.6 — chỉ đọc, KHÔNG đổi bảng giá)
`tools/clipai_cost_reconcile.py`: đọc danh sách task ClipAI (GET `video-list` qua `core/adapters/clipai.ClipAIVideoProvider._page`, miễn phí) + `jobs`
(`external_id`, `quality_tier`, `draft_job_id`) + `usage_events` từ CSDL mở `mode=ro` hoặc bản sao (`--db`). Mỗi task: job / dự án, độ phân giải, loại
(nháp / bước nâng `draft_task` / gen thẳng), `has_video_input`, giây, `total_tokens`, giá theo bảng hiện tại (`core.cost.seedance_token_usd` và giá theo giây
mà sổ chi dùng), `seedance_cost_usd` nếu task có (task gửi từ web), ước tính lúc gửi (`request_params.seedance_cost_usd`). Tổng theo dự án; tách tiền bước nâng
với tiền nháp; liệt kê điểm có tiền thật để hiệu chuẩn (ghi rõ số điểm — KHÔNG kết luận giá từ một mẫu). Ra bảng markdown + `--json`. Test offline bằng
transport giả (dữ liệu mẫu chép từ mục 5 tài liệu gói: 3 nháp 480p 179 740 token / 1,150336 USD; nâng 1080p 909 225 token / 6,364575 USD / ước tính 2,79936).

## Việc 3 — Thiết kế M1.4b provider Claude theo dự án (CHỈ tài liệu → `docs/V3_1_M1_4B_THIET_KE_2026-10-2x.md`)
Dựa audit mục 2 tài liệu gói + quyết định `v31-d02-claude-provider-per-project-2026-10-20`. Phải có: schema (`projects.llm_provider`, snapshot
`jobs.llm_provider` + phiên bản cấu hình, `llm_calls.provider`), migration up/down + tương thích dự án cũ, ma trận MỌI caller (bảng B của audit) → lấy client
từ đâu sau thay đổi, job đang chạy giữ provider snapshot, quota (`usage_limit` / `out_of_credit` có giờ mở lại, dừng cả lượt — `autoqc`, `run_qc_batch`,
`qc_video_batch`), ledger cho `claude_cli` (token, 0 USD), test plan + rollback. Không code.

## Việc 4 — Thiết kế M1.5 Subject Asset Lifecycle Manager (CHỈ tài liệu → `docs/V3_1_M1_5_THIET_KE_KHO_CHU_THE_2026-10-2x.md`)
Theo chỉ đạo người dùng 20/10 + quyết định `v31-d03b-subject-library-auto-clean-2026-10-20` + mục 3 tài liệu gói (185 ảnh, 95 khung, #31 = 84 chỗ). Phải có:
asset BỀN / TẠM; quan hệ asset ↔ job ↔ dự án (bảng / khóa); giữ chỗ + cấp phát dung lượng NGUYÊN TỬ giữa nhiều tiến trình (như `send_claim`); hàng đợi khi Kho
đầy (job chờ, KHÔNG gửi ảnh đánh dấu, KHÔNG lùi Kling vì Kho đầy); cleanup có điều kiện + **dry-run**; bảo vệ asset đang dùng / chưa rõ / thuộc job chưa
đối soát; sửa G59 (luồng nền "chưa cấu hình Kho chủ thể", diag 1860/1861); **không dùng nhận diện khuôn mặt làm điều kiện duy nhất** để đưa / loại ảnh
khỏi Kho; phân tích khôi phục + retry khi provider lỗi giữa upload → submit → cleanup (lỗi 1130 "retry after Ns", timeout, asset "processing"). Không code,
không xóa asset thật.

## Kết quả Codex — đợt 19

- Mã test việc1: `846b3f1f` (nhánh `codex/d19-viec1-narration`); targeted42pass/21xfail, chưa sửa production M2.9.

- **Việc1/M2.9 — chỉ test:** `codex/d19-viec1-narration`; test narration chung7ca×9nhóm hàm thật; ĐỎ21fail/35pass→**42passed/21xfailed strict /8,40s** (G15/G16/G17 mỗi5, G53×6). Rà độc lập sửa3điểm: exception riêng khoanh lỗi gốc/không che assert khác, winreg giả ngoàiWindows, loader guard trướcimport; root đọc sửa lần hai, teardown4/4. Giữ production/areas.version87, khôngAPI/data/projects/cảbộ/main/live. Lỗi gốc vẫn chờ M2.9; chưa chạyLinux thật. RA `docs/RA_D19_VIEC1_CODEX_2026-10-20.md`, mãcommit trong HANDOFF cùng nhánh.
- Mã code việc2: `fe9d68bb`, nhánh `codex/d19-viec2-doi-soat`, 26 test qua; công cụ đối soát không sửa giá production.

- **Việc2/M1.6 — công cụ chỉ đọc:** `codex/d19-viec2-doi-soat`, `tools/clipai_cost_reconcile.py` SQLite mode=ro, offline JSON/GET opt-in, bảng Markdown/JSON allowlist; tách draft/upgrade/direct/unknown, giá token/bảng giây/actual web/request estimate, tổng known/missing và nhóm hiệu chuẩn. ĐỎ3fail13pass→20pass; rà độc lập+root đọc sửa lần hai→**26pass/1,22s**. Fixture actual9,815583USD/1điểm1080p chưa đủ sửa giá; không API/DB thật/bảng giá/cờ/migration/main/live/cả bộ. Areas87 giữ. RA `docs/RA_D19_VIEC2_CODEX_2026-10-20.md`, commit và việc mở trong HANDOFF cùng nhánh. Artifact tảiPython bị policy chặn dọn giữ ngoài commit.

- Mã tài liệu việc3: `22aff768`, nhánh `codex/d19-viec3-provider`; thiết kế đã rà, chưa triển khai M1.4b.

- **Việc3/M1.4b — chỉ thiết kế:** `codex/d19-viec3-provider`, `docs/V3_1_M1_4B_THIET_KE_2026-10-20.md`; source76hit/44file, P/J/S và injected consumers/static, schema+job snapshot+legacy hold, CLI ledger0USD/tokenNULL, quota halt cả lượt, migration up/down bảo toàn, testplan và quyền Cấp2/3. Root RÀ NHẸ bổ sung cache theo job/operation/profile và ACL/rotation cùng tài khoản. Docs-only không pytest đỏ giả, không code/SQL/API/env/flags/areas/main/live. Cần đồng bộ M1.4a, quét lại và duyệt phạm vi trước build. RA `docs/RA_D19_VIEC3_CODEX_2026-10-20.md`; mã commit trong HANDOFF cùng nhánh.

- **Tổng hợp Đ19 (nhánh riêng, chưa main):** V1 code846b3f1f/HEAD9e157f0b ·42pass21xfail strict; V2 codefe9d68bb/HEAD8854f5c4 ·26pass/ROtool; V3 code22aff768/HEAD56097a4e ·docsprovider; V4 code49c1face ·docsKho. HANDOFF.md nhánh `codex/d19-viec4-subjects` có bảng nhánh/commit/bằng chứng/bước Claude rà-gộp. Hoàn tất phần chuẩn bị Đ19, không phải đã sửa production M2.9/M1.6/M1.4b/M1.5; cả bộ Windows còn ở tích hợp.

- **Việc4/M1.5 — chỉ thiết kế:** `codex/d19-viec4-subjects`, `docs/V3_1_M1_5_THIET_KE_KHO_CHU_THE_2026-10-20.md`; BỀN/TẠM, account scope/SHA/refs, reservation nguyên tử nhiều tiến trình/queue công bằng, frozen refs/quarantine, cleanup dry-run+outbox/fence mọi writer, retention>72h/unknown giữ, G59 config explicit và recovery1130/upload-submit-delete unknown. Không face-only/ảnh đánh dấu/Kling vì đầy, không hứa5project fit hay 60/40. Root RÀ NHẸ thêm ACL và mốc lifecycle sau reopen. Docs-only không code/test/SQL/API/delete/flags/areas/main/live, chưa sửa G59/M1.5 runtime. Cần chốt nháp cũ và duyệt scope Cấp2/3. RA `docs/RA_D19_VIEC4_CODEX_2026-10-20.md`, mã commit trong HANDOFF cùng nhánh.

(Codex ghi: việc · nhánh · commit · bằng chứng · việc mở.)

---

# ĐỢT 20 — V3.1 M1 (Cấp 2 ĐÃ DUYỆT): làm LIÊN TỤC 6 việc (người dùng 20/10: "gom giao số lượng task cho codex làm liên tục")

**Quyền:** người dùng duyệt gói Cấp 2 G2-2 (M1) ngày 20/10 — sổ `data/decisions.json` id `v31-cap2-milestone-packages-approved-2026-10-20`, Cấp 3 từng mục
`v31-cap3-items-decided-2026-10-20`; bảng `docs/V3_1_GOI_DUYET_CAP2_CAP3_2026-10-20.md` mục C. Được viết code + test offline trong phạm vi việc dưới.
KHÔNG làm Cấp 3: không migration CSDL thật, không bật cờ trên máy chính, không gọi API trả phí, KHÔNG xóa asset ClipAI, không đổi bảng giá `data/pricing.json`.
**Làm liên tục:** Việc 1 → 6 theo thứ tự, không chờ phiên Claude rà giữa chừng. Việc có điều kiện "BẮT ĐẦU KHI" chưa đủ → làm việc kế, quay lại sau
(`git fetch` kiểm lại). Mỗi việc: nhánh `codex/d20-viec<N>-<tên>` từ `origin/main` MỚI NHẤT; test ĐỎ trước XANH sau (ghi tên test); cờ mới TẮT mặc định
(mẫu `core/features.py`) khi đổi hành vi đường gửi / Dashboard; cờ TẮT = hành vi cũ; file mã mới khai `devsys/areas.json` (KHÔNG tăng version); báo cáo
`docs/RA_D20_VIEC<N>_CODEX_2026-10-2x.md` (việc · nhánh · commit · test đỏ→xanh · cờ · việc mở) + ghi một dòng ở "Kết quả Codex — đợt 20" cuối file.
**KHÔNG sửa (phiên Claude đang làm):** `core/llm_runner.py` (M1.4b), `core/qc_observe.py`, `core/shot_intent.py`; `core/runner.py` + `core/bg_poll.py` + đường
claim/poll trong `core/db.py` cho tới khi `main` có commit "Gộp V3.1 M1.2" (nhánh `claude/v31-m12-m13`). Không đọc/ghi `data/projects/`, `data/manifest.sqlite`
thật (dùng fixture / CSDL tạm). Không sửa kế hoạch; `TODO.md` CHỈ mục 📨 hộp thư. Không push `main` — trừ commit `hộp thư: …` chỉ đổi dòng hộp thư (luật "LUẬT HỘP THƯ CHUNG" đầu `TODO.md`, tên làn `codex`): nhận việc / xong việc / hỏi đều ghi ở đó, pull --ff-only trước, không force.
**Tự kiểm trước báo cáo:** test bị nới để che lỗi; đường dẫn tương đối / phụ thuộc thư mục chạy; chặn mới làm vỡ luồng tự động / hàng loạt (autopilot,
bg_poll, tải lô); bật mặc định đổi hành vi; so chữ bỏ dấu khớp nhầm từ ngắn; lời gọi tốn tiền khi chưa đồng ý.

## Việc 1 — M1.8 `tools/project_error_report.py` (chỉ đọc)
Gom `diag_events` + `jobs` + `job_events` (+ `usage_events`) của một dự án (`--project N`, CSDL `mode=ro` hoặc `--db` bản sao) thành bảng đề xuất mục sổ lỗi cuối
dự án: nhóm theo mã diag / lỗi job / chuyển trạng thái lạ (vd `InvalidTransition`), lần đầu / lần cuối, số lần, job / shot liên quan, tiền đã chi cho job hỏng,
gợi ý mã sổ lỗi (G/A/B nếu khớp nguồn `docs/DANH_GIA_*`), dạng markdown + `--json` hợp schema đặc tả sổ lỗi (kế hoạch V3.1 "**Sổ lỗi (WS0):**").
KHÔNG ghi gì vào CSDL / sổ. Test: CSDL tạm dựng từ fixture (2 lỗi trùng mã, 1 job succeeded 2 lần, 1 job hỏng có tiền) → bảng đúng; CSDL thiếu bảng → báo rõ.

## Việc 2 — M1.9a golden B0–B2: công cụ chụp + khung so sánh (D08; chụp DỮ LIỆU THẬT là việc phiên Claude ở máy chính)
`tools/golden_capture.py` (chỉ đọc, `mode=ro` / `--db`): với dự án + shot chỉ định, ghi fixture JSON gồm HEAD SHA, cờ đang bật, schema version, model / provider,
payload gửi (ảnh + video: `sent_package`, prompt, thứ tự ref, hash từng file ref), tier; theo quyết định `v31-d08-fixture-capture-readonly-2026-10-20` (đang chạy job
→ cảnh báo, đề xuất snapshot). `tests/golden/` + `tests/test_golden_replay.py`: dựng lại payload bằng code hiện tại từ fixture và so (a) COMPAT: cờ TẮT phải
giống TỪNG BYTE, (b) CORRECTNESS tách riêng (golden ≠ đúng). Test bằng fixture tổng hợp nhỏ (không lấy dữ liệu thật); thêm ca lệch 1 byte → đỏ, ca thiếu
trường → báo rõ. Mô tả trong báo cáo: lệnh phiên Claude cần chạy để chụp #24/#27 (compat) và #31/#33 (correctness).

## Việc 3 — M1.6 ước tính giá đúng gói gửi — ⚠ CHUYỂN cloud-B 20/10 (C-M16), Codex BỎ QUA (A7–A9, G31; KHÔNG đổi bảng giá)
Đọc `docs/V3_1_GOI_SUA_VA_RUI_RO_2026-10-20.md` mục 5 + báo cáo Đ19 việc 2 (`tools/clipai_cost_reconcile.py`). Sửa ước tính (`core/cost.py`, `core/spend_gate.py`
phần ước tính, `tools/pregen_check.py`): tier nháp, phụ phí ref (video input), bước nâng 1080p (`draft_task`), `claude_cli` = 0 USD API, và **`pregen_check` in giá
VIDEO** (hiện chỉ ảnh). Ước tính dùng đúng gói sẽ gửi (cùng hàm dựng gói của nút Gen), không tính tay. Test: 3 ca mẫu mục 5 (nháp 480p, nâng 1080p, có video input)
→ lệch ≤ 10 % so số thật ghi trong tài liệu (ghi rõ số điểm hiệu chuẩn); `check_no_budget_lock_gate` vẫn xanh (D01: 0 điểm chặn mới theo ngân sách).

## Việc 4 — M1.7 Dashboard báo chạy code cũ — ⚠ CHUYỂN cloud-B 20/10 (C-M17), Codex BỎ QUA (G55), gộp diag lặp (G56), regen kiểm data_dir (G39), thông điệp ngân sách (A14 theo D01)
Nguồn lỗi: grep "| G55 |", "| G56 |", "| G39 |" trong `docs/DANH_GIA_*.md`, "| A14 |" trong `docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md`. G55: Dashboard / tiến
trình nền so HEAD lúc khởi động với HEAD repo → banner "đang chạy code cũ, khởi động lại". G56: diag cùng mã + cùng nội dung trong cửa sổ thời gian → gộp đếm.
G39: tạo lại (regen) kiểm `data_dir` đúng dự án trước khi ghi. A14: câu báo ngân sách theo D01 (chỉ cảnh báo, có số). Không đụng `core/runner.py` / `core/bg_poll.py`
trước khi M1.2 gộp — cần thì ghi vào việc mở. Test cho từng mã.

## Việc 5 — M1.5 Kho chủ thể: triển khai theo thiết kế Đ19 việc 4 — CHỈ DRY-RUN xóa (C3-3)
BẮT ĐẦU KHI: `main` có commit "Gộp V3.1 M1.2" (đụng `core/runner.py` ~1657 trước `picture_refs`). Theo `docs/V3_1_M1_5_THIET_KE_KHO_CHU_THE_2026-10-2x.md`
(nhánh `codex/d19-viec4-subjects` — dùng bản đã gộp main nếu có) + `docs/V3_1_GOI_SUA_VA_RUI_RO_2026-10-20.md` mục 3.2–3.3: `core/subjects.capacity`,
`auto_clean_candidates`, preflight trước gửi video (thiếu chỗ → job CHỜ có lý do + cách xử lý; không gửi ảnh đánh dấu; KHÔNG lùi Kling vì Kho đầy; không xác
định được sức chứa → VÀNG, không im lặng), sửa G59 (luồng nền nạp cấu hình như Dashboard). Cờ mới TẮT. **Xóa asset: chỉ dry-run** — `tools/subject_cleanup.py`
mặc định in danh sách + dependency (job / dự án / nhân vật tham chiếu) + lý do; KHÔNG cài đường tự xóa trong luồng nền / preflight; nếu có hàm xóa thì chỉ chạy
bằng cờ dòng lệnh + file danh sách đã được người dùng duyệt, và test chứng minh mặc định không gọi DELETE. Test theo mục 3.3 (provider giả: 100/100, 5 khung bị
loại + 3 asset cất 4 ngày + 2 cất 1 ngày + 1 dùng chung → dry-run liệt kê đúng 8, giữ 3; Kho đầy → job chờ, 0 job Kling lùi; list lỗi mạng → VÀNG, 0 xóa).

## Việc 6 — AI Dev System: trang "Sổ lỗi" (đọc `devsys/errors.json`)
BẮT ĐẦU KHI: `main` có `devsys/errors.json` + `devsys/errors.py` (việc cloud C-M04-05, nhánh `cloud/v31-m04-m05`). Trang devsys liệt kê sổ lỗi: lọc theo trạng
thái / workstream / dự án, đếm coverage, cảnh báo đỏ mục `problems()` (VERIFIED thiếu bằng chứng…); nối trang 🗺 Sơ đồ tiến độ (`devsys/plan_map.py`) để tô khâu
theo lỗi mở. Theo mẫu trang hiện có trong `devsys/app.py`; cập nhật `tests/test_tickets_page.py` danh sách điều hướng nếu thêm trang. Test hiển thị theo cách
test trang devsys hiện có.

## CHỦ ĐỘNG LẤY VIỆC (người dùng 20/10 — áp dụng như làn cloud)
**Từ 20/10 tối dùng hộp thư sự kiện:** `py tools/hop_thu.py ke --lane codex --nhan --push` → làm → `py tools/hop_thu.py xong <mã> --lane codex --branch <nhánh> --commit <sha> --report <RA_…> --push` (mã việc đợt 20: `CX20-2`, `CX20-5`, `CX20-6`; luật `hop_thu/README.md`). Không ghi dòng hộp thư vào TODO.md nữa.
Làm xong một việc → `git pull` + đọc hộp thư 📨 `TODO.md` → làm việc CHỜ kế của `codex`. Hết việc ĐỢT hiện hành (hoặc việc còn lại đang bị chặn
"BẮT ĐẦU KHI") → nhận mục **DP** đầu tiên còn CHỜ ở `docs/CLOUD_TASKS.md` "HÀNG VIỆC DỰ PHÒNG" (đánh dấu `ĐANG LÀM <giờ> (codex)` trong hộp thư +
push `hộp thư:` TRƯỚC khi code; làn khác nhận trước thì bỏ, lấy mục kế), nhánh `codex/v31-<mã>`. Không còn việc nào → ghi hộp thư
`codex → phiên-chính: HẾT VIỆC — CHỜ` rồi dừng. Phiên chính giữ cho codex luôn ≥ 2 việc CHỜ.

## Kết quả Codex — đợt 20

- Việc 2 · `codex/d20-viec2-golden` · tranche capture/validation, 17 test synthetic xanh sau rà độc lập (2 P2 đã sửa) từ SCHEMA thật; M1.9a **OPEN**, chưa current-builder/end-to-end replay; báo cáo `docs/RA_D20_VIEC2_CODEX_2026-10-20.md` (commit xem HEAD nhánh).

(Codex ghi: việc · nhánh · commit · bằng chứng · việc mở.)

- Đ20 việc 1 · codex/d20-viec1-so-loi · commit rà xem git log (cùng báo cáo) · RÀ KỸ sửa 2 P2: đủ mọi lần failed + JSON tiền hữu hạn; 2 regression đỏ → 9 test xanh (1,18s); native cost UNKNOWN khi thiếu USD, chờ cả bộ Windows/slow trước gộp.
- Việc 2 bổ sung · `codex/d20-viec2-golden`: frozen pre-send input ảnh/video qua ImageRunner/VideoRunner._build_package thật; 3 đỏ →25 xanh/9,47s; COMPAT byte + correctness cấu trúc riêng, provider stub fake/clipai/deepix; M1.9a OPEN (chưa `_submit_args`/capture sản xuất/chất lượng/cả bộ). Chi tiết RA_D20_VIEC2; không API/dữ liệu thật, chưa push/gộp.
