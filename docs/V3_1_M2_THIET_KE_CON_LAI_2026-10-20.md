# V3.1 M2 còn lại — Thiết kế M2.4, M2.6, M2.7, M2.8, M2.9 (20/10/2026)

> **Cấp 1 — CHỈ TÀI LIỆU, 0 USD, không sửa code.** Việc C-M2X (làn `cloud-C`). Nền `origin/main` = `03c85f0`.
> Căn cứ: `docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md` (mục 5 dòng M2.4–M2.9, §4a, §4b), thiết kế đã gộp main:
> `docs/V3_1_M2_1_M2_2_THIET_KE_2026-10-20.md` (BYĐ v2, `shot_intent.read`, cờ `byd_fields`), `docs/V3_1_M0_9_THIET_KE_KHO_FORMS_2026-10-20.md`,
> `docs/V3_1_M0_10_BAO_VE_DU_LIEU_2026-10-20.md` (write guard, bảng đường ghi hàng 6 = `insert_scene_after`), sổ lỗi `devsys/errors.json`
> (P31-G1, G5, G6, G13–G17, G21, G28, G37, G53, G54; P33-A11, A12, B9 — tất cả `OPEN`), nghiệm thu M2.9 = `tests/test_narration_regression.py`
> (21 xfail strict). Số dòng dưới đây đo trên `03c85f0`.
> Triển khai = Cấp 2 (gói G2-3 "M2", mở khi có golden M1.9 — `tools/golden_capture.py` của Codex Đ20 việc 2 CHƯA gộp main).
> Bật cờ production = Cấp 3. Không có migration CSDL nào trong 5 việc này.

## 0. Tóm tắt

| Việc | Lỗi | Gốc (đã đọc code) | Sửa đề xuất | Cờ (mặc định TẮT) | Nặng |
|---|---|---|---|---|---|
| M2.4 | G6, G21, G1 | `llm_io.insert_scene_after:838` chỉ chép `story_scene`/`sequence`; `stage_auto.inputs_for:373–377` mang MỌI đạo cụ cảnh trước "cùng sân khấu" | chèn shot thừa kế bối cảnh shot `after_idx` + BYĐ DRAFT (REVIEW_REQUIRED); đạo cụ chỉ mang khi có trong BYĐ / chữ shot, không qua đổi thế giới | `insert_inherit`, `stage_props_byd` | 2 |
| M2.6 | G5 | `sent_package._meta_index:124` khóa theo `basename`; meta dựng ở `runner.py:3612–3614`, `3706–3710`, `end_frames.py:478` cũng chỉ `basename` | khóa theo `rel_path` (+ `asset_id` khi có), giữ `file` để đọc | `sent_package_relpath` | 1 |
| M2.7 | (E, N4/N7) | ảnh chỉ có `ImageRunner._pregen:3416` (nền 3D lẫn) + `_blocked:3313` (bố cục, công thức) — mã/định dạng khác `video_pregen` | `core/image_pregen.check(conn, scene_id, plan)` cùng dạng `{ma, muc, ly_do}` + bộ mã chung `core/pregen_codes.py`; runner ảnh gọi y như video | `image_pregen` (shadow → enforce) | 3 |
| M2.8 | G28, G37, B9, G13, G54 | `seedance_refs._groups:98` gộp mọi shot `_groupable` — không xét shot CẦN khung đầu; trần ký tự rải rác (`seedance_refs.GROUP_PROMPT_BUDGET=3500`, `runner.py:2108–2127` từng câu tự kiểm, D6/gore riêng) | (a) luật "cần khung đầu → không gộp nhóm ref-only" dựa trên khả năng model; (b) MỘT ngân sách ký tự theo khối có ưu tiên, câu bắt buộc không bao giờ bị cắt im lặng | `router_first_frame`, `prompt_budget` | 2 |
| M2.9 | G15, G16, G17, G53, G14, A11, A12 | 4 caller không dùng `speaker_lint.is_narrator`; `voice.fit_durations:436` tự kéo; thông điệp "ném keo" viết cứng `runner.py:1528` | mọi caller hỏi MỘT hàm `lipsync.talking(data)`; fit_durations = đề xuất + duyệt; thông điệp theo lý do; BYĐ chạy qua `claude_cli` | `narration_offscreen`, `fit_durations_review` | 2 |

Thứ tự đề xuất: **M2.6 → M2.9 → M2.4 → M2.8 → M2.7** (nhẹ + có test sẵn trước; M2.4 cần M2.1 `read()` + guard M2.5 shadow; M2.7 lớn nhất, dùng
lại mã của M2.8 "ky_tu").

---

## 1. M2.4 — Chèn shot thừa kế bối cảnh + BYĐ DRAFT; đạo cụ chỉ theo BYĐ (G6, G21, G1)

### 1.1 AS-IS
| Phần | file:hàm (dòng) | Hiện trạng |
|---|---|---|
| Chèn shot | `core/llm_io.py:insert_scene_after` (838–) | shot mới = `story_scene` + `sequence` của shot `after_idx`; bắt buộc `image_prompt`, `action`/`text`, `duration_s`, `plate_spot`; trường khác chỉ khi người truyền (`_INSERT_DIRECT:750`, `_INSERT_VIA_UPDATE:768`) |
| Hệ quả G6 | `place_refs.wants_render` | shot 15–17 #31 thiếu `location_asset/location/time/weather/lighting/mood` → không coi là bối cảnh 3D → gói KHÔNG có nền 3D, im lặng; chép tay `location_asset` thì nền ra day-clear (thiếu `time`/`weather`) |
| Hệ quả G21 | `video_pregen._byd:218`, `_check_motion` | shot chèn không có `byd` → VÀNG "chưa có BYĐ" |
| G1 | `core/stage_auto.py:inputs_for` (265; 366–378) | mọi đạo cụ của cảnh trước "cùng sân khấu" (`prev_state.objects`, có `h`,`d`) thành vật CỐ ĐỊNH với `source: "cảnh N (cùng sân khấu)"` — không hỏi BYĐ / chữ shot, không xét đổi thế giới (song song ↔ thực tại) → khối xám "XÁC ĐEN BIẾT BAY" render vào nền shot 28/30/34/35 |
| Câu giải thích khối | `core/stage_facts.py:_prompt_stand_in` (223) | chỉ thêm khi `ctx.render`; không có kiểm "nền còn khối mà thiếu câu" |

### 1.2 Thay đổi
1. **Thừa kế bối cảnh** (cờ `insert_inherit`): trước khi ghi, đọc `prev.data`; với mỗi khóa trong `INHERIT_KEYS = ("location_asset", "location",
   "time", "weather", "lighting", "mood", "characters"?)` mà `fields` KHÔNG có → chép từ shot `after_idx`. `characters` để NGOÀI danh sách mặc định
   (shot chèn có thể là insert vật) — câu hỏi mở Q1. Các khóa chép ghi kèm provenance `inherited_from: <scene_id>` trong diag (một dòng
   `insert_inherit`), không thành `_user_locked` (người không gõ chúng) — khác trường `fields` (vẫn khóa như nay).
2. **BYĐ DRAFT**: shot mới nhận `byd` dựng từ BYĐ của shot `after_idx` qua `shot_intent.read` (M2.1): giữ `noi_chon`, `thanh_phan` (lọc theo
   `characters` của shot mới nếu có), bỏ `hanh_dong`, `may`, `vat` (vật phải khai lại) ; `_p = {"by": "code", "draft": true, "from": after_scene_id}`.
   Trạng thái M0.10 = **REVIEW_REQUIRED** cho cả nhóm `byd` (M0.10 bảng 3.1 hàng 6 đã ghi). `video_pregen._check_motion` thấy `_p.draft` → VÀNG
   `byd_draft` "BYĐ nháp từ shot N — duyệt ở Bước 3" (không còn "chưa có BYĐ"). Shot `after_idx` không có BYĐ → không dựng, diag nói rõ.
3. **Đổi số không đụng BYĐ**: `byd.shot` của các shot sau tăng 1 cùng giao dịch (nay `insert_scene_after` đã dời "shot N" trong `_TEXT_KEYS`; thêm
   `byd.shot`). Ghi qua guard M2.5 (Actor `code:insert_renumber`), đường ghi này đã liệt kê ở M0.10.
4. **G1 — đạo cụ theo BYĐ** (cờ `stage_props_byd`, sửa trong `stage_auto.inputs_for`): một đạo cụ của cảnh trước chỉ được mang khi
   (a) cùng `world_id` (thế giới; chưa có M3 thì dùng `location_asset` + `time` — đổi `location_asset` = thế giới khác) VÀ
   (b) có tên trong `byd.vat[].vat` / `byd.thanh_phan[].vat` (qua `read()`), hoặc chữ shot (`prop_lock.shot_text`) nhắc tên.
   Không thỏa → không mang + ghi `notes` "bỏ đạo cụ X của cảnh N: shot không nhắc" (người đọc thấy ở Đạo diễn sân khấu). BYĐ v1 / thiếu → chỉ xét
   chữ shot (không đoán thêm).
5. **Khối còn trong nền mà thiếu câu giải thích → ĐỎ**: mã `khoi_giu_cho` (M2.7, chung ảnh + video): nền (`plate`) có khối (`stage_camera.props`
   kind `block`) mà prompt không chứa câu `_prompt_stand_in` → ĐỎ có lý do. Thêm vào `tools/pregen_check.py` qua `image_pregen` (không viết lại).

### 1.3 Test đỏ → xanh
| Test (mới trong `tests/test_insert_scene.py` / `tests/test_stage_auto.py`) | Cờ TẮT | Cờ BẬT |
|---|---|---|
| chèn sau shot có `location_asset/time/weather` → shot mới có đủ 6 khóa | giữ hành vi cũ (assert thiếu) | đủ, diag `insert_inherit` |
| `fields` có `time` khác → giữ của người, không ghi đè | — | giữ |
| shot `after_idx` có BYĐ → shot mới `byd._p.draft`, `video_pregen` VÀNG `byd_draft` (không "chưa có BYĐ") | "chưa có BYĐ" | `byd_draft` |
| `byd.shot` các shot sau +1 | — | đúng |
| G1: đạo cụ cảnh 6 không có trong BYĐ / chữ shot cảnh 7 → không vào `fixed` | còn (đỏ trước khi sửa) | không còn + note |
| G1: đổi thế giới (cảnh 8 thực tại) → không mang dù cùng sân khấu | còn | không |
| `khoi_giu_cho`: nền có khối, prompt thiếu câu → ĐỎ | — | ĐỎ |
Hiện có phải xanh: `test_insert_scene.py`, `test_update_scene_end_state.py`, `test_stage_auto.py`, `test_stage_facts.py`, `test_place_refs.py`.
Correctness #31: shot 15–17 (replay gói: có nền 3D đúng giờ/thời tiết), shot 28/30/34/35 (không còn trụ "XÁC ĐEN BIẾT BAY").

### 1.4 Golden / rollback
Cờ TẮT: `insert_scene_after` và `inputs_for` không đổi một byte → golden #24/#27 giữ (hai dự án không chèn shot). Rollback = tắt cờ; dữ liệu đã chép
vẫn là giá trị hợp lệ (người sửa được), BYĐ DRAFT xóa được bằng `update_scene`.

---

## 2. M2.6 — `sent_package` nhãn theo `rel_path` / `asset_id` (G5)

### 2.1 AS-IS
`core/sent_package.py:_meta_index` (124) dựng `{basename: meta}` bằng `setdefault` → hai ảnh Kho cùng tên (`2.png` của mục #443 và #367) chung một
khóa: ảnh thứ hai lấy nhãn của ảnh thứ nhất. `_one_ref` (132) tra `meta.get(os.path.basename(path))`. Ba chỗ dựng meta chỉ ghi basename:
`runner.py:3612–3614` (ảnh), `runner.py:3706–3710` (storyboard), `end_frames.py:478` (khung cuối). Prompt gửi model ĐÚNG — chỉ SỔ sai
(ảnh hưởng trang "Gói sẽ gửi", `video_pregen._check_refs`/`_ref_sha` đọc `refs[].label`, đối soát golden).

### 2.2 Thay đổi (cờ `sent_package_relpath`)
- Meta thêm `"path": rel_path(r["path"])` (+ `"asset_id"` khi ref có — `assets.scene_references` đã biết id ảnh) ở cả 3 chỗ dựng.
- `_meta_index` → hai chỉ mục: `by_path` (rel_path) ưu tiên, `by_file` (basename) chỉ dùng khi basename **duy nhất** trong meta; basename trùng mà
  không khớp path → nhãn `None` + cảnh báo `"gói gửi: 2 ảnh cùng tên <file> — không gán nhãn theo tên"` (không đoán).
- Gói thêm `ref.asset_id` khi có; tăng `V` gói chỉ khi cờ bật (để golden phân biệt).

### 2.3 Test đỏ → xanh (`tests/test_sent_package.py`)
- 2 mục Kho cùng `2.png` khác thư mục → nhãn mỗi ảnh đúng mục (đỏ trên `03c85f0`).
- meta cũ chỉ có `file` (job đang chạy lúc nâng code) → basename duy nhất vẫn gán; trùng → `None` + cảnh báo.
- cờ TẮT → JSON gói giống byte (so fixture hiện có).

### 2.4 Golden / rollback
Cờ TẮT = byte cũ. Gói đã ghi bằng v mới vẫn đọc được (khóa thêm, không bỏ khóa). Rollback: tắt cờ.

---

## 3. M2.7 — Image preflight trong `ImageRunner._pregen`, chung mã lỗi với video

### 3.1 AS-IS
| Kiểm | file:hàm | Định dạng |
|---|---|---|
| nền 3D lẫn camera khác | `runner.py:ImageRunner._pregen` (3416) → `place_refs.package_problem` | chuỗi; diag `plate_package_mixed`; `WAIT_REASONS`/`PREGEN_HELD` |
| bố cục Kho thiếu, prompt sai công thức | `ImageRunner._blocked` (3313) → `assets.missing_layout`, `prompt_formula.red_issues` | chuỗi |
| chờ nền / establishing / neo / shot trước | `ImageRunner._wait` (3340) | `_hold(job, chuỗi)` |
| gói video | `core/video_pregen.check` (531) | `[{ma, muc: do/vang, ly_do}]`, mã `khung_dau, khung_cuoi, thoi_luong, tham_chieu, chuyen_dong, van_tay, byd` |
| công cụ người | `tools/pregen_check.py:check` | gọi `batch.image_gates`, `change_review.blocking`, `place_refs.*`, `cost.estimate_images` |
Ảnh không có: trần ảnh tham chiếu của model, ảnh ref đọc được, vân tay gói (gửi lại y gói đã có ảnh), BYĐ, ngân sách ký tự, khối giữ chỗ (G1).

### 3.2 Thay đổi
- `core/pregen_codes.py` (mới, chỉ hằng + mô tả): `DO, VANG`; mã chung `tham_chieu`, `van_tay`, `byd`, `byd_draft`, `ky_tu` (M2.8),
  `khoi_giu_cho` (M2.4); mã ảnh `nen_3d` (= `plate_package_mixed`), `cong_thuc`, `bo_cuc_kho`; mã video giữ nguyên. Mỗi mã ánh xạ
  `devsys/errors.json` (`P31-G1` → `khoi_giu_cho`, `P31-G13/G54` → `ky_tu`…) để sổ lỗi đếm lần xảy ra (D09: diag = lần phát sinh).
  `video_pregen` import hằng từ đây (giá trị chuỗi không đổi → test cũ xanh).
- `core/image_pregen.py` (mới): `plan_of(job, args, kwargs, package, data_dir)` + `check(conn, scene_id, plan)` gồm:
  `_check_plate` (bọc `place_refs.package_problem`), `_check_formula` + `_check_layout` (bọc 2 hàm `_blocked` đang gọi — CHUYỂN, không chép),
  `_check_refs` (tệp đọc được, số ảnh ≤ `image_models` trần, `sendable_references` đã bỏ ảnh nào → VÀNG), `_check_fingerprint` (dùng
  `video_pregen.fingerprint` — tách ra `pregen_codes`/module chung), `_check_byd` (VÀNG như video), `_check_stand_in` (M2.4), `_check_chars` (M2.8).
- `ImageRunner._pregen` = khung y `VideoRunner._pregen` (1027): dựng gói bằng `_build_package` (một builder — đã là luật V3.1 §2), ĐỎ → giữ chờ +
  `_pregen_note(job, "image_pregen_hold", …)`; VÀNG → gửi + ghi. Lớp kiểm hỏng → ĐỎ có lý do (luật 1). Thêm `"image_pregen_hold"` vào `HOLD_CODES` (75).
- **Shadow trước** (D07 tinh thần + CHUAN "không làm vỡ luồng hàng loạt"): cờ `image_pregen` có 2 mức — `shadow` (chạy, ghi diag
  `image_pregen_shadow`, KHÔNG giữ job; `_blocked` + kiểm nền cũ vẫn chặn như nay) → `on` (giữ job theo ĐỎ). `tools/pregen_check.py` gọi
  `image_pregen.check` cho mọi shot (ra cùng bảng mã) — người xem trước khi xin gen.
- Thứ tự gọi trong vòng gửi (`runner.py:494–516`) không đổi: `_pregen_cooling` → `_pregen` → `SPEND_LOCK`. Không thêm điểm chặn theo ngân sách (D01).

### 3.3 Test đỏ → xanh (`tests/test_image_pregen.py` mới)
- mỗi mã: một ca ĐỎ / VÀNG / đạt, provider giả, 0 mạng (khuôn `tests/test_video_pregen.py`).
- `nen_3d`: đúng thông điệp `plate_package_mixed` cũ (so chuỗi) — không đổi lời người dùng đang quen.
- shadow: ĐỎ nhưng job vẫn gửi + 1 dòng diag; `on`: job ở `queued`, `WAIT_REASONS` có lý do; cờ TẮT = gọi y `_pregen` cũ (assert theo mock).
- lớp kiểm ném ngoại lệ → ĐỎ `loi_kiem` (on) / diag (shadow), không gửi im lặng.
- `video_pregen` đổi import hằng → `test_video_pregen.py`, `test_pregen_root_1710.py`, `test_pregen_root_fix_1710.py` xanh không sửa test.
- `tools/pregen_check` mã thoát 1 khi `image_pregen` ĐỎ (đã có cơ chế: thêm khóa `image_pregen` vào kết quả).

### 3.4 Golden / rollback
Kiểm không đổi gói gửi → golden byte giữ ở mọi mức cờ. Rollback: cờ về TẮT (đường `_pregen` cũ còn nguyên, chỉ bọc lại).

---

## 4. M2.8 — Router theo khả năng model + ngân sách ký tự (G28, G37, B9, G13, G54)

### 4.1 AS-IS
| Phần | file:hàm (dòng) | Hiện trạng |
|---|---|---|
| Gộp nhóm Seedance ref-only | `seedance_refs._groups` (98), `_groupable` (84) | shot `eligible` + `route is None` + không khớp môi → gộp ≤ `GROUP_MAX_SHOTS=4`, ≤ 15 s, ước ≤ `GROUP_PROMPT_BUDGET=3500` ký tự |
| Nhóm dùng khi gửi | `shots.group_of` (835), `VideoRunner._sends_group` (1834) | nhóm ref-only: model nhận ảnh storyboard làm THAM CHIẾU, không phải khung đầu |
| Lỗi | G28 (job 1043: khung 0 khác ảnh đầu, 22/3232 điểm), G37 (shot 28 nhóm 28+29: mất dạng bóng mờ — ảnh dạng có thể bị cắt khi hết chỗ, thứ tự bỏ OUTFIT→OBJECT→FORM), B9 (#33 S6: ref-only theo khoảng cách máy của video ref) | ref-only KHÔNG giữ khung đầu đã duyệt — router không biết shot nào CẦN khung đầu |
| Trần ký tự | `seedance_refs.PROMPT_MAX=4000` (1087); `runner.py:2108–2127` từng câu (`side_truth`, `travel_truth`) tự so `PROMPT_LIMITS` rồi bỏ + diag; D6 3256 > 3192 bị từ chối; `gore_restraint` "không thêm được" (G54); motion có câu "because…" cho người đọc (G13: S01–S03 5173 ký tự) | không có thứ tự ưu tiên: câu đến sau bị bỏ dù quan trọng hơn câu đến trước |

### 4.2 Thay đổi
**(a) Luật khung đầu** (cờ `router_first_frame`):
- `data/provider_rules.json` → `video_models.<m>.first_frame_in_ref_mode: false` (Seedance 2.x ref-only), `true` cho chế độ ảnh đầu / Kling i2v
  — số liệu ở file luật (như `video_rules`), không viết cứng trong code.
- `core/model_router.needs_first_frame(conn, scene_id, data) -> Optional[str]` (lý do) khi một trong:
  1. `start_from_prev_clip` / `continuity_from` (khung đầu là khung cuối shot trước);
  2. BYĐ v2 `khung.moc_nen.y_do == "trong_khung"` hoặc `framing_guard` có khung đầu bắt buộc (đọc qua `shot_intent.read`, M2.1);
  3. nhân vật ở dạng đặc biệt cả clip (`character_forms.for_rows(...)[who]["all"]`) — G37;
  4. dự án có video ref chuyển động + `size` khóa (B9) — `byd.may.co` ≠ cỡ của video ref.
- `seedance_refs._groupable` thêm điều kiện `not needs_first_frame(...)` khi cờ bật → shot đó gửi một mình (chế độ có khung đầu nếu model hỗ trợ);
  model đang chọn không có chế độ khung đầu → VÀNG `khung_dau` ở `video_pregen` kèm lý do + gợi ý model (không tự đổi model, không tự tốn tiền).
- Giá: tách nhóm thay đổi số clip → `model_router.plan` / `cost` phải dùng CÙNG `groups()` (đã dùng) — ước tính tự đúng; test giá so trước/sau.

**(b) Ngân sách ký tự** (cờ `prompt_budget`):
- `core/prompt_budget.py` (mới): `fit(blocks, cap) -> (text, dropped)`; `blocks = [(key, text, priority)]`, priority ∈
  `BAT_BUOC` (danh tính ảnh "Image N is…", nền/khối giữ chỗ G1, look lock, khóa cỡ khung) > `QUAN_TRONG` (side_truth, travel_truth, gore_restraint,
  D6) > `PHU` (câu "because…", diễn giải). Cắt từ `PHU` lên; `BAT_BUOC` vượt trần → không cắt, trả ĐỎ `ky_tu` cho M2.7/`video_pregen` liệt kê khối.
- Cap = `clipai.PROMPT_LIMITS[model]` (một nguồn). `runner.py:2108–2127`, `seedance_refs._estimated_len`, D6, gore chuyển sang ghép khối; mỗi khối bị
  bỏ → MỘT diag `prompt_budget` (giữ lời "KHÔNG thêm câu … > trần" cũ để người dùng quen).
- G13: Đạo diễn vẫn viết "because…" (cho người đọc Bước 3) nhưng câu đó gắn `PHU` → bị bỏ trước khi chạm trần (không sửa prompt Đạo diễn ở việc này).

### 4.3 Test đỏ → xanh
- `tests/test_seedance_refs.py`: nhóm 3 shot, shot giữa `start_from_prev_clip` → cờ TẮT 1 nhóm (đỏ theo lỗi) / BẬT tách đúng; dạng cả clip (G37) tách;
  `groups()` không đổi khi không shot nào cần khung đầu (byte).
- `tests/test_prompt_budget.py` (mới): thứ tự cắt; `BAT_BUOC` vượt → ĐỎ `ky_tu`, không cắt; ca thật #31 S01–S03 (5173 → ≤ 4000 bỏ "because"), D6 3256/3192.
- `tests/test_video_pregen.py`: VÀNG `khung_dau` khi model không có chế độ khung đầu.
- Correctness #31 (G28 shot 16/26/29, G37 shot 28+29) + #33 S6 (B9): replay gói — shot cần khung đầu gửi đơn, ảnh dạng còn trong gói. Chất lượng clip
  thật chỉ chứng minh bằng gen (Cấp 3, xin riêng) — test giả không phải chất lượng thật.

### 4.4 Golden / rollback
Hai cờ TẮT = nhóm + prompt giống byte. Bật `router_first_frame` đổi SỐ clip (giá) → báo giá qua `pregen_check` trước khi xin bật. Rollback: tắt cờ.

---

## 5. M2.9 — Lời dẫn ngoài khớp môi ở MỌI caller (G15–G17, G53) + G14, A11, A12

### 5.1 AS-IS (nghiệm thu = `tests/test_narration_regression.py`, 7 ca × 9 test; 21 xfail strict)
| Lỗi | file:hàm (dòng) | Đọc gì | Đúng phải là |
|---|---|---|---|
| — (đã đúng) | `lipsync._method` (73) | bỏ người dẫn qua `speaker_lint.is_narrator` | nguồn chuẩn |
| G53 (6 xfail: 5 ca lời dẫn + `mixed`) | `seedance_refs._say_speakers_without_picture` (531) | `dialogue.is_non_speaker` (nhãn chữ trên màn), KHÔNG bỏ người dẫn | chỉ người nói TRONG khung |
| G16 (5 xfail) | `claude_tasks._measure_clip` (323) | `speaking = bool(data.get("dialogue"))` | có người nói trong khung |
| G17 (5 xfail) | `quality_tier.hard_signs` (176) | `data.get("lip_sync") is True` trước `method_for` | `lipsync.voiced(method_for(data))` |
| G15 (5 xfail) | `lipsync.mark` (116) chỉ gộp thêm → `synced_scene_ids` (122) giữ `state: done` khi method về `skip` | khi method = `skip`: xóa `state/offsets` cũ |
| G14 | `voice.fit_durations` (436) | kéo dài MỌI shot có giọng (kể cả chỉ lời dẫn), ghi thẳng `motion_prompts.duration_sec` | đề xuất → người duyệt |
| A11 | `runner.py:_skill_object_appears` (1520, thông điệp 1528) | "(ném keo)" viết cứng cho mọi lý do `end_frames.skip_reason` (193) | thông điệp theo lý do + vật thật |
| A12 | `director_byd.settle` (116) gọi từ `llm_runner.py:866, 910` | #33 không có BYĐ (22 lần VÀNG) | BYĐ chạy được qua `claude_cli` |

### 5.2 Thay đổi
- **Một hàm**: `lipsync.talking(data) -> bool` = có người nói TRONG khung (`speaker_lint.in_frame` cho từng người nói của `dialogue.scene_lines`, bỏ
  `is_narrator` và `is_non_speaker`). Bốn caller G53/G16/G17/G15 gọi hàm này (cờ `narration_offscreen`); AST test: không caller nào còn đọc
  `bool(data.get("dialogue"))` / `lip_sync is True` để suy "đang nói" (danh sách cho phép rõ ràng).
- G15: `lipsync.mark(..., method="skip")` xóa `state`, `offsets`, `job_id` của mục đó (không xóa tệp âm thanh).
- **G14** (cờ `fit_durations_review`): `voice.plan_fit(...)` trả danh sách `{scene_id, idx, from, to, short, ly_do: "thoai_trong_khung" |
  "chi_loi_dan" | "giong_ngoai_khung", tien_them_usd}` (giá qua `cost`/`model_router.price_per_sec`, không tính tay); nút "⏱" mở bảng duyệt
  (mặc định CHỈ tick shot bị chặn đỏ / thoại trong khung; shot chỉ lời dẫn bỏ tick — Q3). `apply_fit(conn, chosen)` ghi qua guard M2.5.
  `fit_durations` cũ giữ cho cờ TẮT.
- **A11**: `end_frames.skip_reason` trả `(code, vat)`; bảng thông điệp `SKIP_TEXT = {"skill_object": "shot có vật kỹ năng {vat} xuất hiện", …}`;
  runner ghép theo mã. Không cờ (chỉ đổi chữ diag) — nhưng giữ code diag `end_frame_skill_object` (trang Chẩn đoán lọc theo code).
- **A12**: kiểm `director_byd.settle` chạy với `ClaudeCliClient` (M1.4b provider theo dự án): `client.complete` trả chữ có JSON trong rào ``` →
  `settle` đã parse? (xác minh khi code; thêm `_extract_json` dùng chung với Đạo diễn nếu thiếu). Phụ thuộc gộp M1.4b (`cloud/v31-m14b`).

### 5.3 Test đỏ → xanh
- `tests/test_narration_regression.py`: bật `narration_offscreen` trong fixture `api` (thêm vào `flags.json` tạm) → 21 xfail thành xanh; `strict=True`
  buộc gỡ marker cùng commit (nếu không gỡ, xfail strict ĐỎ — đúng ý đồ). Thêm tham số cờ TẮT: hành vi cũ (giữ khẳng định lỗi) để chứng minh
  cờ TẮT = byte cũ.
- `tests/test_voice_*.py` (mới `test_fit_durations_review.py`): `plan_fit` không ghi CSDL; shot chỉ lời dẫn có `ly_do="chi_loi_dan"`; `apply_fit`
  chỉ đổi shot được chọn.
- `tests/test_end_frames.py`: thông điệp không chứa "ném keo" khi vật là tháp; code diag giữ.
- `tests/test_director_byd.py`: client giả kiểu CLI (chữ + rào JSON) → BYĐ ghi được.

### 5.4 Golden / rollback
G17 đổi dấu hiệu "shot khó" → có thể đổi gợi ý mức chất lượng (`quality_tier`) → gói final khác: vì vậy để sau cờ. Cờ TẮT = byte cũ. Rollback: tắt cờ.

---

## 6. Cờ (đăng ký `core/features.py`, mặc định TẮT, `verified: False`)
| Cờ | Việc | Ghi chú |
|---|---|---|
| `insert_inherit` | M2.4 | thừa kế bối cảnh + BYĐ DRAFT |
| `stage_props_byd` | M2.4 (G1) | đạo cụ theo BYĐ/chữ + thế giới |
| `sent_package_relpath` | M2.6 | sổ gói khóa theo đường dẫn |
| `image_pregen` | M2.7 | `off` / `shadow` / `on` |
| `router_first_frame` | M2.8 | đổi số clip → báo giá trước khi bật |
| `prompt_budget` | M2.8 | |
| `narration_offscreen` | M2.9 | G15–G17, G53 |
| `fit_durations_review` | M2.9 (G14) | |
Bật cho dự án kế = Cấp 3, ghi `data/decisions.json` + check (quy ước 8). Không cờ nào chặn theo ngân sách (`check_no_budget_lock_gate` xanh — D01).

## 7. Ma trận luồng bắt buộc (CHUAN luật 2) — mỗi việc phải có test hoặc lý do
| Luồng | M2.4 | M2.6 | M2.7 | M2.8 | M2.9 |
|---|---|---|---|---|---|
| bấm tay Bước 2/3/4 | chèn shot ở Dashboard | xem "Gói sẽ gửi" | Gen ảnh | Gen video | nút ⏱ |
| autopilot / lô | — (chèn chỉ tay) | ✓ | ✓ không làm kẹt lô (job khác vẫn gửi) | ✓ | QC tự động |
| v2 cảnh / v3 shot / multi-shot Kling | v3 | ✓ | ✓ | Kling i2v luôn có khung đầu (luật không áp) | ✓ |
| nhân bản dự án | BYĐ DRAFT giữ `_p` | — | — | — | index lipsync không chép |
| chạy lại Đạo diễn | BYĐ DRAFT REVIEW_REQUIRED không bị ghi đè im lặng (M2.5) | — | — | — | — |

## 8. Phụ thuộc và cổng
| Việc | Cần trước | Cổng nghiệm thu |
|---|---|---|
| M2.6 | — | test G5 xanh; byte TẮT |
| M2.9 | M1.4b gộp (chỉ phần A12) | 21 xfail → xanh khi BẬT; byte TẮT |
| M2.4 | M2.1 `read()`; M2.5 guard shadow | #31 shot 15–17 + 28/30/34/35 replay đúng |
| M2.8 | M2.1 (`khung.moc_nen`), M0.9 adapter dạng (G37) | #31 G28/G37 + #33 B9 replay: shot cần khung đầu gửi đơn |
| M2.7 | M2.8 (`ky_tu`), M2.4 (`khoi_giu_cho`) | mọi mã có ca; `pregen_check` cùng mã; shadow ≥ 1 dự án trước khi `on` |
Chung: golden M1.9 (compat #24/#27 byte với mọi cờ TẮT) phải gộp trước khi gộp bất kỳ việc nào ở trên.

## 9. Câu hỏi mở (cho phiên chính / người dùng — không chặn thiết kế)
- **Q1** M2.4: shot chèn có thừa kế `characters` không? (đề xuất KHÔNG — insert vật / cảnh trống phổ biến).
- **Q2** M2.8: B9 (cỡ khung theo video ref) — tách khỏi nhóm hay chỉ cảnh báo? Câu khóa cỡ khung chỉ giúp S4 #33 → đề xuất tách.
- **Q3** M2.9/G14: shot chỉ lời dẫn có được kéo theo giọng không? (sổ lỗi: "chờ người dùng quyết") — đề xuất mặc định không tick.
- **Q4** M2.9: G15–G17/G53 là lỗi thuần (chỉ bỏ báo sai) — người dùng có muốn bật `narration_offscreen` mặc định ngay khi gộp (ngoại lệ "bật mặc
  định đổi hành vi")? Đề xuất: bật sau 1 dự án shadow vì G17 đổi gợi ý mức chất lượng.

## 10. Chi phí
Toàn bộ code + test = 0 USD (provider giả). Chứng minh chất lượng clip (G28/G37/B9) và `router_first_frame` cần gen thật = Cấp 3, báo giá qua
`tools/pregen_check.py` / `spend_gate` trước khi xin duyệt.
