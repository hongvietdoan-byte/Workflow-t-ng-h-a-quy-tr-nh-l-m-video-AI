# V3.1 M0.9 — Thiết kế Kho forms / outfit / hair / face + provenance (20/10/2026)

> **Cấp 1 — CHỈ TÀI LIỆU, 0 USD, không sửa code.** Việc C-M09 (`docs/CLOUD_TASKS.md`). Đối chiếu repo `main` = `725f22e`.
> Căn cứ: `docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md` (hợp đồng dữ liệu §2 dòng 55: **ảnh Kho > profile Kho > Bible > Lock**; D05 dòng
> 105; M2.3 dòng 121 / 200; mục 4b), sổ `data/decisions.json` `v31-d05-kho-structured-forms-2026-10-20` (thay
> `v31-kho-forms-direction-2026-10-20` — 6 điều kiện), `video-form-picture-2026-10-19`; V2.1 Q3 (`docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md`
> dòng 125, 178, 294, 507); `docs/CHUAN_XAY_DUNG.md` luật 1, 4, 8. Thiết kế khóa trường dùng chung với M0.10
> (`docs/V3_1_M0_10_BAO_VE_DU_LIEU_2026-10-20.md`, nhánh `cloud/v31-m010`).
> **Ngoài phạm vi:** Kho chủ thể ClipAI (`core/subjects.py`, M1.5 — Codex đợt 19). Migration / backfill = Cấp 3, chỉ mô tả. Soạn nháp
> bằng Claude = API trả phí, xin riêng.

## 0. Tóm tắt

- Hôm nay Kho **không có** trường cấu trúc outfit / hair / face / forms. Thông tin nằm ở: chữ tự do `profile.identity` / `must_keep` /
  `may_change` / `forbidden` (`core/assets.py:PROFILE_KEYS`), ô có cấu trúc `profile.khai_bao_chu` (món + màu — `core/identity_declare.py`),
  dòng chữ "Dạng của nhân vật: TÊN" trong **mô tả** mục Kho kiểu `style` (`core/character_forms.py:_DECLARE`), vai ảnh (`asset_images.role`
  — `close_up`, `back`, `character_form`…), và trang phục **theo dự án** `characters.outfit_image_ids`. Code tách quần áo khỏi chữ khóa bằng
  regex (`character_forms.without_clothes`) — nguồn lỗi V2.1 ghi "5/22".
- Thiết kế: thêm vào **JSON `assets.profile`** (không đổi bảng) khối `schema_version: 2` gồm `face`, `hair`, `outfit`, `forms[]`, mỗi trường
  có `provenance` + trạng thái khóa (AUTO / USER_LOCKED / REVIEW_REQUIRED của M0.10), `revision` của hồ sơ, và `kho_id` (= `assets.id`) để
  truy vết. Mọi chỗ đọc đi qua **một adapter** `core/kho_profile.py` (đề xuất) trả cùng một dạng cho v1 và v2.
- 18 điểm đọc hồ sơ / dạng / trang phục trong code đã liệt kê (mục 4) — tất cả phải đổi sang adapter; cờ TẮT = byte giống.

## 1. AS-IS (file:hàm)

| Thông tin | Lưu ở đâu | Ghi bởi | Đọc bởi |
|---|---|---|---|
| Hồ sơ chuẩn (identity, must_keep, may_change, forbidden, height_m, build, approved, history) | `assets.profile` JSON | `assets.set_profile` (người `dashboard/admin.py:418,430`; AI nháp `tools/draft_profiles.py:138`, `tools/profile_finalize.py:114`) | `assets.standard_for` (chỉ khi `approved`), `assets.get_profile` |
| Khai báo chữ món + màu (`khai_bao_chu[] = {mon, dong_nghia, mau_chinh, mau_dong_nghia, dau_hieu, cach_viet, hoa_tiet}`) | `assets.profile.khai_bao_chu` | `set_profile` (giữ ô cũ khi không gửi; kiểm `identity_declare.validate_khai_bao_chu`) | `identity_declare.declare_from_profile` (thiếu ô → suy từ chữ, `nguon: "suy"` + VÀNG), `core/asset_clean.py` |
| Bản rút gọn hồ sơ | `assets.profile.digest` | `core/profile_digest.refresh` | `profile_digest.for_character` ← `runner.py:2873` (cờ `profile_digest`), `prompts.py:603` |
| Dạng nhân vật (forms) | dòng `Dạng của nhân vật: KELLY` trong `assets.description` mục `kind=style` + ảnh vai `character_form` | người sửa mô tả Kho (`dashboard/admin.py:972`) | `character_forms.for_shot` / `for_rows` ← `runner.py:1123,1985,2903`, `seedance_refs.py:340,373,506,709`, `prompts.lock_text:545`, `assets._forms_here`, `scene_storyboard.py:278` |
| Dạng trong BYĐ | `scenes.data.byd.thanh_phan[].dang` chữ tự do / {nhip: …} | Director BYĐ | `shot_intent._check_dang` (chỉ kiểm dạng chữ), `identity_declare.byd_view` |
| Trang phục trong video này | `characters.outfit_image_ids` (id ảnh Kho) | `assets.set_outfit`, `add_outfit_images` (`step1_refs.py:131`, `chat_intake.py:229`) | `assets.outfit_images/outfit_label`, `costume.py:30`, `seedance_refs.py:351`, `palette.py:253`, `claude_tasks.py:565`, `prompts.lock_text` (`_has_outfit_ids` → khóa chỉ mặt/tóc/dáng) |
| Tóc / mặt | chỉ chữ trong `identity` / `must_keep`; ảnh `close_up` | — | `without_clothes` giữ mảnh nói tóc/mặt; `identity_declare.ITEMS` có `hair`, `face`, `eyes`, `mask` |
| Ảnh chuẩn | `asset_images` (role, look, variant, status) | Kho admin, `kho_review` | `assets.best_references`, `standard_set`, `view_picture` |
| Dạng vật (G38 tường keo cong) | không có; ảnh Kho sort 1 là dạng phẳng | — | `assets.best_references` theo sort → chọn sai dạng |

Provenance AS-IS: chỉ `approved` + `history[{date, why}]` cho cả hồ sơ; mô tả Kho tách khối AI có dấu (`[AI đọc ảnh]`… `assets.BLOCK_MARKS`,
`asset_vision.sync_one`); `khai_bao_chu` suy ra có `nguon: "suy"` lúc đọc (không lưu). Không biết trường nào người viết, trường nào AI.

## 2. Schema v2 (đề xuất)

Nằm trong `assets.profile` (JSON). Trường v1 giữ nguyên tên và nghĩa (đọc cũ không vỡ). Khối mới:

```jsonc
{
  "schema_version": 2,                       // thiếu = 1
  "revision": 7,                             // +1 mỗi lần ghi; ghi kèm expected_revision (CAS như package_overrides.save)
  "approved": true, "history": [...],        // v1 giữ
  "identity": "...", "must_keep": "...", "may_change": "...", "forbidden": "...", "height_m": 1.68, "build": "...",
  "khai_bao_chu": [...],                     // v1 giữ — outfit.items[] dưới đây là nơi mới, adapter đọc cả hai
  "face":   {"text_en": "oval face, light makeup", "eyes": "dark brown", "marks": [], "ref_image_ids": [812],
             "_p": {"source": "human", "by": "email", "at": "2026-10-21T..", "state": "USER_LOCKED"}},
  "hair":   {"text_en": "black bob, straight fringe", "color": "black", "length": "short", "style": "bob", "ref_image_ids": [812],
             "_p": {"source": "ai", "model": "claude-…", "from_image_ids": [812, 815], "at": "..", "state": "REVIEW_REQUIRED"}},
  "outfit": {"default": "everyday",
             "sets": [{"id": "everyday", "label": "Đồ thường", "items": [ /* cùng dạng khai_bao_chu */ ],
                       "image_ids": [813], "_p": {...}}]},
  "forms": [                                 // có THỨ TỰ (G38: dạng triển khai đầu tiên là dạng mặc định khi shot không nói)
    {"ma": "ghost", "ten_en": "ghost form", "ten_vi": "bóng mờ", "applies_to": ["KELLY"],      // style/dạng người
     "keeps": ["face", "hair", "build"], "outfit_override": true, "image_role": "character_form", "image_ids": [901],
     "words_en": "translucent glowing silhouette", "_p": {...}},
    {"ma": "curved", "ten_en": "curved deployed wall", "applies_to": [], "keeps": [], "image_ids": [1367], "_p": {...}}  // dạng vật
  ],
  "_p": {"profile": {"source": "human", "by": "...", "at": "..."}}   // provenance cấp hồ sơ cho trường v1 (chưa tách)
}
```

Quy tắc:
- `_p.source ∈ {human, ai, image, import}`; `ai` bắt buộc `model` + `from_image_ids` (ảnh đã đọc) hoặc `from_text` (nguồn chữ); `image` =
  đo từ ảnh bằng code (ví dụ `palette.py` đã có `by auto|user, ref_sha`).
- `_p.state` theo M0.10: người ghi → USER_LOCKED; AI ghi vào trường USER_LOCKED → không ghi, lưu `proposal` + diag; AI ghi trường trống →
  REVIEW_REQUIRED (người duyệt mới tính là "chuẩn"). Hồ sơ `approved` chỉ khi mọi trường cấu trúc có mặt đều USER_LOCKED.
- `kho_id` = `assets.id`: mọi nơi dùng hồ sơ ghi `kho_id` + `revision` đã đọc vào `jobs.sent_package` / lineage (truy vết lần gen nào dùng
  bản hồ sơ nào). `forms[].ma` là khóa ổn định cho BYĐ `thanh_phan[].dang` (V2.1 A1: enum "∈ forms Kho" **chỉ khi** Kho có forms; chưa có
  → VÀNG `dang_khong_kiem_duoc`).
- Thiếu dữ liệu → **không bịa**: trường vắng = vắng; adapter trả `None` + lý do; người gọi báo (luật 1). Không có `hair` → không viết câu
  tóc mới, dùng chữ v1 như hôm nay + VÀNG một lần "hồ sơ chưa tách tóc".
- Ảnh > chữ: khi `ref_image_ids` có ảnh chuẩn đã duyệt, câu chữ chỉ bổ trợ; mâu thuẫn chữ AI ↔ ảnh → REVIEW_REQUIRED (điều kiện 2).

## 3. Adapter đọc v1 / v2 — `core/kho_profile.py` (đề xuất)

```
read(conn, asset_id) -> KhoProfile{kho_id, revision, schema_version, approved,
                                   identity, must_keep, may_change, forbidden, height_m, build,     # v1, luôn có
                                   face, hair, outfit_sets, forms,                                   # v2; v1 → suy (dưới)
                                   provenance: {field: _p}, gaps: [lý do thiếu]}
for_character(conn, project_id, name) -> KhoProfile | None     # thay assets.standard_for (cùng luật approved + link_characters)
forms_for_shot(conn, project_id, scene) -> {TÊN: Form}          # thay character_forms.for_shot / for_rows
outfit_for(conn, project_id, name, scene) -> OutfitSet           # characters.outfit_image_ids (dự án) > form.outfit_override > outfit.default
lock_text_en(profile, form=None, outfit=None) -> str            # thay without_clothes + lock_en: ghép từ trường, không tách chữ bằng regex
```

Đọc v1 (schema_version thiếu): `face` / `hair` = `None` + `gaps` "chưa tách" (KHÔNG suy bằng regex vào trường mới); `outfit.sets[0].items` =
`khai_bao_chu` nếu có, không thì `identity_declare.declare_from_text` với `nguon: "suy"` như hôm nay; `forms` = từ `character_forms.declared`
trên mô tả các mục style của dự án (hành vi `video-form-picture-2026-10-19` giữ nguyên); `lock_text_en` v1 = đúng chuỗi code hiện tại
(`runner.lock_note` + `without_clothes`) → **cờ TẮT hoặc dữ liệu v1 cho ra byte giống**.

Cờ (TẮT mặc định): `kho_forms_v2` — chỉ chọn nhánh đọc trường v2 khi hồ sơ có `schema_version: 2`. Cờ TẮT: adapter = đường cũ.

## 4. MỌI đường đọc phải qua adapter (điều kiện 6)

| Khâu | file:hàm (dòng) | Đang đọc | Đổi sang |
|---|---|---|---|
| Director | `core/prompts.py:standard_block` (521) | `standard_for` identity/must_keep/height | `for_character` + forms/outfit làm chữ cho Director |
| Director / QC / motion | `core/prompts.py:lock_text` (545–603) | `character_forms.for_shot`, `standard_for`, `lock_rules`, `_has_outfit_ids`, `profile_digest.for_character` | `for_character`, `forms_for_shot`, `outfit_for` |
| BYĐ | `core/shot_intent.py:_check_dang` (130), `core/director_byd.py`, `identity_declare.byd_view` | `dang` chữ tự do | kiểm `dang ∈ forms[].ma` khi Kho có forms (VÀNG trước) |
| Gen ảnh | `core/runner.py` 1123 (dạng), 2873–2911 (`lock_note`: digest, standard_for, without_clothes, lock_en), 2950 | | `lock_text_en` |
| Gen ảnh — chọn ảnh ref | `assets.best_references/standard_set/view_picture/_chosen_images/scene_references` | role/look/sort | thêm: ảnh của `forms[]` theo thứ tự, `face/hair.ref_image_ids` (G38: dạng vật theo `forms` không theo `sort`) |
| Gen video | `core/seedance_refs.py` 340, 351, 373, 506, 709 (`form_and_object_pictures`, FORM_TAG) | `character_forms.for_rows`, `outfit_images` | `forms_for_shot`, `outfit_for` |
| Trang phục | `core/costume.py:30`, `core/palette.py:253`, `core/claude_tasks.py:565`, `dashboard/steps/step1_characters.py:86,104` | `outfit_images/outfit_label` | `outfit_for` |
| QC | `core/qc_observe.py:42`, `core/qc_spec.py:107`, `core/qc_agent.py:221,567`, `prompts.lock_text` | `standard_for` | `for_character` (+ form: không chấm đồ thường khi ở dạng) |
| Storyboard | `core/scene_storyboard.py:278` | `character_forms.for_rows` | `forms_for_shot` |
| Sân khấu / 3D | `core/stage_auto.py:281`, `core/location_pack.py:271`, `core/meshy.py:192,430` | `standard_for` / `get_profile` (height_m, model3d) | `read` (height_m chung) |
| Công thức prompt | `core/prompt_formula.py:922,926` | `get_profile`, `standard_for` | `read` / `for_character` |
| Khác | `core/autopilot.py:392` (có hồ sơ?), `core/prop_lock.py:473`, `core/idea_buildable.py:89`, `core/asset_clean.py`, `core/profile_digest.py:132,149`, `dashboard/admin.py:407` | | `read` |

Test kiểm "mọi đường đọc qua adapter": test tĩnh quét AST — ngoài `core/kho_profile.py` và `core/assets.py`, không file nào gọi
`assets.get_profile` / `standard_for` / `character_forms.for_shot|for_rows` / `outfit_images` trực tiếp (danh sách ngoại lệ có lý do).
Mẫu: `tests/test_decisions.py` có check code tĩnh.

## 5. Đối chiếu 6 điều kiện M2.3 (D05)

| # | Điều kiện (sổ `v31-d05…`) | Cách đáp ứng | Test |
|---|---|---|---|
| 1 | Tương thích ngược Kho hiện tại + dự án cũ | v2 nằm trong JSON cũ, trường v1 giữ; adapter đọc v1 = đường cũ; cờ `kho_forms_v2` TẮT | `test_kho_profile_compat`: replay gói ảnh/video (fixture có trên `main`: `tests/fixtures/p30_payload.json`, `director_p24_shots.json`; `byd_vat_v1_p30_p31.json` chỉ có ở nhánh `claude/v31-m11-vat` chưa gộp; hồ sơ Kho #31 thật phải chụp ở máy chính theo D08) cờ TẮT và hồ sơ v1 → prompt + thứ tự ref giống byte |
| 2 | Ảnh chuẩn Kho ưu tiên hơn metadata AI | `ref_image_ids` + `forms[].image_ids` chọn trước chữ; trường `source: ai` mâu thuẫn ảnh → REVIEW_REQUIRED; ảnh luôn đi trước chữ trong `lock_text_en` | `test_image_over_ai_text`: hair AI "blonde" + ảnh close_up đã duyệt → câu khóa không có "blonde", trường REVIEW_REQUIRED |
| 3 | Không tự ghi đè dữ liệu người nhập/sửa | ghi qua write guard M0.10 (Actor, revision CAS); `set_profile` AI chỉ ghi trường AUTO/trống | `test_ai_never_overwrites_human_field` (draft_profiles / profile_finalize trên hồ sơ có trường USER_LOCKED); `test_profile_revision_cas` |
| 4 | Thiếu → nhận diện rõ, không bịa | adapter `gaps`; v1 không suy face/hair vào trường mới; BYĐ `dang` không có trong forms → VÀNG | `test_missing_hair_is_reported_not_invented`, `test_dang_not_in_forms_warns` |
| 5 | schema version + adapter v1/v2 + migration + regression | `schema_version`, `revision`, adapter, kế hoạch mục 6, bộ mục 7 | `test_schema_v2_validate` (kiểu, enum source/state, `ma` duy nhất, image_ids có thật) |
| 6 | Director, BYĐ, ảnh, video, QC dùng chung dữ liệu | bảng mục 4 + test tĩnh | `test_all_readers_use_kho_profile` (AST) + một test end-to-end: cùng hồ sơ v2 → câu Director, prompt ảnh, gói video, khóa QC cùng `revision` |

## 6. Kế hoạch migration / backfill (Cấp 3 — CHỈ MÔ TẢ)

- **Không đổi bảng.** "Migration" = ghi thêm khối v2 vào `assets.profile` của từng mục Kho.
- **Up (từng mục, có duyệt):** (1) công cụ `tools/kho_forms_backfill.py --dry-run` (0 USD) dựng **bảng chuyển đổi**: forms từ dòng "Dạng của
  nhân vật" + ảnh `character_form`; outfit từ `khai_bao_chu` + ảnh role outfit; face/hair để trống (không suy). (2) tùy chọn: Claude soạn
  nháp face/hair từ ảnh `close_up` (V2.1 Q3 ≈ 0,05 USD, qua sổ chi + ước tính trước + **xin duyệt chi**) → `source: ai`, REVIEW_REQUIRED.
  (3) người duyệt từng dòng trên Dashboard (Kho) → ghi với `schema_version: 2`, `revision += 1`, `history` + lý do.
- **Down:** xóa khóa `schema_version/revision/face/hair/outfit/forms/_p` khỏi JSON (trường v1 không bị đụng khi up) → dữ liệu như trước;
  hoặc chỉ tắt cờ `kho_forms_v2` (adapter bỏ qua v2).
- **Dự án cũ giống byte:** dự án đã giao/cất không bị đọc lại; dự án đang làm: cờ TẮT tới khi người dùng bật theo dự án; test compat mục 5.1.
- **Snapshot trước khi ghi:** `tools/project_snapshot.py` / bản sao `manifest.sqlite` (D08: chỉ đọc khi máy chính đang chạy job → snapshot).
- Mô tả Kho dòng "Dạng của nhân vật:" **giữ** (adapter v1 + người quen sửa ở đó) cho tới khi người dùng quyết bỏ.

## 7. Bộ regression đề xuất

| File test (đề xuất) | Nội dung |
|---|---|
| `tests/test_kho_profile_compat.py` | v1 / cờ TẮT = byte (prompt ảnh `runner.lock_note`, `prompts.lock_text`, `seedance_refs` gói + thứ tự ref, khóa QC) trên fixture #24/#30 có sẵn + #31 chụp ở máy chính (D08) |
| `tests/test_kho_profile_v2.py` | đọc v2: forms có thứ tự, outfit theo dự án > form > default, lock_text_en không tách regex; G38: dạng `curved` được chọn khi shot nói "deployed" |
| `tests/test_kho_profile_provenance.py` | 6 điều kiện (mục 5) + revision CAS + AI không ghi đè + thiếu không bịa |
| `tests/test_kho_profile_readers.py` | AST: mọi đường đọc qua adapter |
| giữ xanh hiện có | `test_forms_and_render_slot.py`, `test_assets.py`, `test_assets_names_d17.py`, `test_draft_profiles.py`, `test_profile_digest.py`, `test_prop_lock*.py`, `test_lock_ngoai_le.py`, `test_lock_normalize.py`, `test_kho_review.py`, `test_kho_dedup.py`, `test_change_audit.py`, `test_decisions.py` (check `check_video_sends_form_picture`) |

Ma trận luồng (CHUAN_XAY_DUNG luật 2): bấm tay · autopilot · v2 cảnh · v3 từng shot · multi-shot · nhân bản (`compare.clone_project` — hồ sơ ở
Kho, dùng chung, không chép) · chạy lại Director — mỗi luồng một ca trong `test_kho_profile_v2.py`.

## 8. Việc mở / cần người dùng

1. Tên khóa cuối cùng (`forms[].ma` tiếng Anh không dấu?) và vị trí khai dạng: giữ dòng mô tả song song hay chuyển hẳn vào `forms`.
2. Chi phí soạn nháp face/hair bằng Claude (≈ 0,05 USD theo V2.1 Q3 — con số cũ, phải ước tính lại qua `spend_gate` trước khi xin).
3. Trang phục theo dự án (`characters.outfit_image_ids`) có thành `outfit.sets` của Kho (dùng lại cho dự án khác) hay giữ theo dự án.
4. UNK (cần máy chính): số mục Kho có dòng "Dạng của nhân vật", số hồ sơ `approved`, số `khai_bao_chu` đã điền — quyết quy mô backfill.
