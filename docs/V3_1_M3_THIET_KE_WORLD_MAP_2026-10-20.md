# V3.1 M3.1–M3.4 — Thiết kế world map + liên tục (20/10/2026)

> **Cấp 1 — CHỈ TÀI LIỆU, 0 USD.** Việc C-M31-34 (cloud-B). Nền `origin/main` = `ffeade5e`. Theo gói G2-4 (world map CHỈ thử offline, KHÔNG chặn gen,
> KHÔNG bắt buộc 3D) + D06 `v31-d06-scene-world-map-flexible-2026-10-20` (3D → tọa độ thật; không 3D → 2D / quan hệ tương đối; thiếu → UNKNOWN; version,
> provenance, quan hệ shot, **invalidation**; duyệt trước khi chặn; offline #31/#33 trước). Căn cứ: kế hoạch V3.1 §2 "**`scene_world_map` tối thiểu:**",
> §4a dòng M3.x; `docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md` (G1–G3, G41–G50, G52); `docs/PHUONG_PHAP_SAN_KHAU_3D.md` (K1–K5, nhánh B/C, §14 stage_facts);
> thiết kế M2.1 (`docs/V3_1_M2_1_M2_2_THIET_KE_2026-10-20.md`: BYĐ v2 `kho_id`, `khung.moc_nen`, `noi_chon.trong_nha`). Sổ lỗi: `devsys/errors.json`.

## 0. Tóm tắt
Hệ thống ĐÃ có phần lớn dữ liệu hình học — nhưng rải rác và không có phiên bản: `data/projects/<pid>/stage/` (`stage.json` gốc O + trục, `grid.json`
sàn, `blocking.json` dàn cảnh, `shot_specs.json`, `setups.json`), `scenes.data.stage_camera` (máy đã giải + `props`), `plates/index.json` (render),
`core/stage_facts` (sự thật hình học). Thứ thiếu: **một bản đồ theo CẢNH có version + provenance + thời hạn hiệu lực từng thực thể**, nguồn sinh câu
vị trí (G46: "vị trí xuyên shot chỉ tả bằng chữ riêng từng shot"), và trạng thái liên tục expected / observed / resolved. Thiết kế: `scene_world_map`
là **bản tổng hợp đọc** từ các tệp sân khấu sẵn có (3D) hoặc từ sơ đồ người duyệt (2D) hoặc từ BYĐ (tương đối) — không thay K1–K5, không bắt buộc 3D.

## 1. AS-IS — mọi điểm đọc / ghi hình học hiện có (file:hàm)
| Dữ liệu | Ghi (file:hàm) | Đọc (file:hàm) |
|---|---|---|
| `stage/<stage>/stage.json` (O, trục, `factor`), `grid.json` (sàn: floor_z, top_z, loại ô) | `tools/stage_grid.py` (Blender K1), `core/stage_auto.py` dựng K1 (`base_dir` 195, kiểm `stage.json` 225) | `stage_auto.inputs_for` (265–271), `stage_auto` 697, `core/stage_grid.py` (ô ↔ tọa độ) |
| `stage/<…>/doan_<cảnh>/` (blocking, specs, kết quả giải) | `stage_auto` (702, 906), `tools/stage_grid.py v2` | `stage_auto.placed_without_handheld` (51), `stage_solver.objects_from_blocking` (76) |
| `scenes.data.stage_camera` {location, look_at, lens, move, props[kind, at, size]} | `stage_auto.apply` (620–650, máy tự động; khóa tay giữ) | `stage_facts.stage_of` (41), `plate_camera` (`STAGE_FIELD` 585), `change_audit.audit_shot` (nen), `compare._drop_auto_stage` |
| `scenes.data.plate_view` / `plate_spot` / `plate_setup` | `camera_plan.apply` (529), người (`update_scene`) | `plate_camera.camera_for` (207), `plate_choice.view_of` (157), `plate_view_check` |
| Chiều cao người | Kho `profile.height_m` (`assets.set_profile`) | `stage_auto.inputs_for` (286–289, THIẾU → báo), `plate_camera.camera_for(height_m=1.75 mặc định)`, `stage_solver.DEFAULT_H=1.7` (19), **`whitebox.EYE=1.6` cố định (13), khối người `height` mặc định 1.8 (70)** |
| Pitch / góc | `plate_camera.HIGH_TILT_DEG=30`, `OVERHEAD_TILT_DEG=60` (26), `LOOK_DOWN_PITCH_DEG=35` (57) | `plate_camera.camera_for` (254–318) |
| Mốc nền | `plate_anchor.landmark_facts` (107) | `plate_choice.view_of`, `strip_scenery` (242) |
| Trái/phải, hướng chạy | code viết sự thật: `side_truth` (cờ), `travel_truth` (cờ) | prompt ảnh / motion |
| Liên tục | `continuity.axis_warnings` (94, regex), `layout_follow` (`continuity_from`), `end_frames`, `lineage` | Bước 1 (cảnh báo), runner |
| Sơ đồ mặt bằng G46 | NGOÀI repo: `D:/AI-Video-Output/2026-10-15_du-an-31/scripts_19-10/so_do_canh{4_me_cung,6_xac_bay,8_keo_dich}.jpg` (vẽ trên `top_raw.png`) | người |
Lỗ hổng đã ghi sổ: P31-G1 (khối giữ chỗ mang sang cảnh khác — `stage_auto` 373–377), G2 (nền không có mốc tỉ lệ người), G3 (máy 'eye' mà ngước/chúi lớn,
không kiểm che), G41–G45/G47/G50 (vị trí xuyên shot, gốc chung **P31-G46**), G48 (hình dạng vật đổi giữa shot), G49 (bậc cỏ do máy cũ), G52 (logic chuỗi).

## 2. Schema `scene_world_map` (M3.1)
Lưu: `data/projects/<pid>/world/scene_<story_scene>.json` (tệp, có trong bản chụp D08) + một dòng chỉ mục revision trong `app_settings`/bảng nhỏ khi M3
được duyệt code (Cấp 2). Không đổi `scenes`.
```jsonc
{ "schema_version": 1, "scene_id": 4, "world_id": "p31_me_cung", "kind": "3d" | "2d" | "relative" | "unknown",
  "unit": "m", "axes": {"x": "E", "y": "N", "z": "up"}, "origin": {"stage": "<stage>", "spot": "...", "xyz": [0,0,0]},
  "map_revision": 3, "geometry_asset_revision": {"kho_id": 265, "sha": "…", "stage_json_sha": "…", "grid_json_sha": "…"},
  "entities": [ {"entity_id": "kelly", "kho_id": 12, "kind": "nguoi|vat|moc|che", "transform": {"xyz": [..], "yaw_deg": 90},
                 "dimensions": {"h": 1.68, "w": 0.5}, "valid_from": {"shot": 26, "beat": "bat_dau"}, "valid_to": {"shot": 29},
                 "state": {"tu_the": "dung", "cam": ["awm"]}, "source": "stage_blocking|nguoi_ve_2d|byd|code_suy", "confidence": "do|uoc|tuong_doi"} ],
  "landmarks": [{"kho_id": 88, "xyz": [..], "visible_from": "tính từ máy"}], "occluders": [{"id": "rao_tay", "box": [..], "h": 3.0}],
  "relations": [{"a": "xac", "rel": "truoc_mat|sau_lung|trai_cua|phai_cua|gan|xa", "b": "kelly", "valid_from": .., "valid_to": ..}],   // kind relative / 2d
  "approved_by": null, "approved_at": null, "provenance": {"by": "code|director|human", "from": ["stage.json", "blocking.json", "byd"], "at": "…"},
  "invalidated": null | {"why": "geometry_changed|byd_changed|blocking_changed", "at": "…", "by_revision": 4} }
```
Quy tắc (D06): 3D → `transform.xyz` đo thật từ `stage.json` + `blocking.json` (không bịa); 2D (nhánh B — 87/90 bối cảnh Kho không có mô hình) → xy theo
sơ đồ người vẽ / tách lớp ảnh, z = UNKNOWN; tương đối → chỉ `relations` rút từ BYĐ v2 (`thanh_phan`, `vat.nguoi`, `khung.moc_nen`); thiếu → `kind:
"unknown"` + yêu cầu duyệt, KHÔNG tự bịa tọa độ (kế hoạch §2). Map `approved_by = null` **không chặn gen** (G2-4) — chỉ sinh cảnh báo / câu đề xuất.

**Invalidation:** map lưu sha `stage.json`, `grid.json`, mô hình Kho, `blocking.json`, và `byd` từng shot liên quan; lệch bất kỳ → `invalidated` + `map_revision`
mới khi lập lại; câu vị trí / expected state sinh từ revision cũ bị coi "⚠ cũ" (nối `lineage`, như `stage_camera` hiện làm ảnh cũ — `lineage.IMAGE_SHOT_KEYS`).

### 2.1 Blocking mỗi shot (từ map)
`{shot_id, camera_pose (= stage_camera.location/look_at hoặc plate_camera.camera_for), lens/FOV, target, visible_landmarks (tính bằng chiếu điểm —
stage_facts), character_positions (entity → xyz + vùng khung), prop_states, state_before, state_after}` — đọc từ map + máy; KHÔNG lưu riêng (tính lại).

## 3. M3.2 — người nộm `height_m` + pitch + che (G2, G3, A10, G49)
- Người nộm: mọi nơi dựng người dùng `height_m` hồ sơ Kho đã duyệt; thiếu → báo (như `stage_auto` 286), KHÔNG mặc định im lặng. Sửa chỗ còn hằng:
  `whitebox.EYE = 1.6` + khối `height` mặc định 1.8 (`whitebox.py:13, 70`) → mắt = 0.93 × height_m; `plate_camera.camera_for(height_m=1.75)` mặc định
  → bắt buộc truyền / báo; `stage_solver.DEFAULT_H` chỉ cho vật không người.
- Mốc tỉ lệ người trong nền (G2): render nền thêm người nộm xám đúng `height_m` ở chỗ đứng (chỉ cho kiểm / tham chiếu, không gửi model khi cờ tắt).
- Pitch: thêm mức `slightly_high` (cúi 8–12°) và `eye` ≤ 5° (A10: `HIGH_TILT_DEG = 30` cố định làm nền chỉ còn sàn); `angle: eye` mà pitch đo > 5° → VÀNG
  (G3: #31 shot 28 `pitch_deg +17.3`).
- Che (G3): chiếu điểm từ máy tới mốc / người qua `occluders` + `depth.png` → mốc bị che → `visible_landmarks` không có nó (không tả "thấy tháp").
- G49: `grid.json` floor_z chênh > 0,1 m dưới chân người ở cỡ MS/MCU → VÀNG "bậc dưới chân".

## 4. M3.3 — câu vị trí sinh từ map (thay tả tay, G41–G50)
Hàm đề xuất `core/world_map.position_sentence(map, shot) -> (en_sentence, provenance)`: từ `character_positions` + `relations` + máy → "Kelly at frame
left, the floating corpse BEHIND her to the right, the tower beyond the wall at upper left" (khung trái/phải theo `side_truth`, hướng chạy theo `travel_truth`);
map `unknown` → không sinh (đường cũ, VÀNG `byd_fallback`). Thay vị trí do Director tả tay trong `image_prompt`/`blocking` chỉ khi cờ con `world_map_sentences`
bật (TẮT mặc định); đường cũ giữ để so (`text_vs_field` M2.1 báo lệch). Ca kiểm: G41 (hướng chạy shot 35 ngược mạch), G43 (xác ở nền sau lưng), G44 (phát hiện
"phía trước"), G45 (bốn địch tách ở bốn góc), G47 (shot 14 sai chỗ địch), G50 (tường keo chắn giữa 17/18).

## 5. M3.4 — continuity_state expected / observed / resolved + đồ thị phụ thuộc
| Tầng | Nguồn | Ghi |
|---|---|---|
| expected | map (entity theo `valid_from/valid_to`) + BYĐ v2 (`vat`, `hanh_dong.ket_thuc`, `noi_chon`) | tính lại, không lưu (revision map + hash BYĐ) |
| observed | QC có bằng chứng (M4.1 `qc_findings`, append-only: vị trí, vật còn cầm, đứng/gục) | bảng findings |
| resolved | người duyệt (override M4.7) | bảng overrides, liên kết finding |
Đồ thị phụ thuộc theo thực thể: cạnh `shot_i --(entity e, thuộc tính a)--> shot_j` khi `e` có trong cả hai và `a` không đổi theo BYĐ; observed lệch ở
shot_i → các shot_j phụ thuộc "⚠ cần xem" (không tự gen lại — M5.1 quyết). Không cần Continuity Engine mới: tái dùng `lineage`, `end_frames`,
`layout_follow`, `side_truth`, `travel_truth`, `stage_facts` (V3 A.1). G52 (logic chuỗi 39 clip) và G1 (đạo cụ mang sang cảnh khác: entity hết `valid_to`
khi đổi cảnh/thế giới) kiểm ở đây.

## 6. Ca offline (0 USD, chỉ đọc — dữ liệu máy chính chụp, D08)
| Ca | Dữ liệu | Kiểm |
|---|---|---|
| #31 cảnh 4 mê cung (shot 13–18) | `stage/` K1 + blocking cảnh 4, `stage_camera` shot 13–18, Kho #265 (rào 1,5 m) | map 3D; G47 (14 sai chỗ địch), G49 (bậc cỏ 13 cm), G8 (rào thấp so game) → câu vị trí + VÀNG đúng |
| #31 cảnh 6 xác bay (shot 26–29) | như trên + BYĐ | G43, G44: expected "xác trước mặt / sau lưng" khớp kịch bản; shot 29 "đi tiếp" không về phía xác |
| #31 cảnh 8 keo + địch (shot 34–38) | như trên | G41 hướng chạy, G48 hình dạng tường giữ qua shot, G50 tường chắn giữa, G42 lời dẫn đi trước hình (đồ thị: lời ↔ nhịp) |
| #33 tháp đồng hồ | nền ghép trời + máy thấp (B3–B5) | map 2D/relative (không mô hình đủ): tháp TRÁI bị cắt đỉnh, mắt xoáy trên đỉnh → câu vị trí không kéo tháp vào giữa |
Đạt: map sinh được (hoặc UNKNOWN có lý do), câu vị trí đúng các ca đã ghi lỗi, invalidation khi đổi `blocking.json`/BYĐ, 0 chặn gen, 0 lời gọi trả phí.

## 7. Nối M2.1 (BYĐ v2)
`khung.moc_nen` (y_do) so `visible_landmarks` của map (REVIEW khi lệch); `vat[].kho_id/nguoi/cach` → `prop_states`; `noi_chon.kho_id` → `world_id`;
`noi_chon.trong_nha` suy từ chỗ đứng (đã ở M2.1); `thanh_phan[].thay` (mặt/lưng) so với yaw nhân vật ↔ máy. Map đọc BYĐ qua `shot_intent.read` (M2.1).

## 8. Cờ, rollback
| Cờ | Mặc định | Tác dụng |
|---|---|---|
| `world_map` | TẮT | dựng map + expected state (chỉ ghi tệp / cảnh báo) |
| `world_map_sentences` | TẮT | câu vị trí từ map thay câu tả tay (cần `world_map`) |
| `world_map_height_dummy` | TẮT | người nộm `height_m` + pitch `slightly_high` trong render |
Không cờ nào chặn gen (G2-4); bật chặn = Cấp 3 sau người duyệt map + benchmark. Rollback: tắt cờ → đường cũ y nguyên (ref cũ, câu tả tay); tệp `world/`
để nguyên (không xóa). Test compat: cờ TẮT ⇒ gói gửi giống từng byte (golden M1.9).

## 9. Test plan
`tests/test_world_map_schema.py` (schema, kind 3d/2d/relative/unknown, không bịa tọa độ khi thiếu, invalidation theo sha), `tests/test_world_map_build.py`
(dựng từ `stage.json`/`blocking.json` mẫu — tái dùng fixture `tests/test_stage_*`), `tests/test_world_map_sentences.py` (các ca G41–G50 dạng tổng hợp,
`xfail(strict=True, reason="P31-G4x")` cho ca cần dữ liệu thật), `tests/test_whitebox.py` + `test_plate_camera*.py` mở rộng (height_m, slightly_high,
pitch eye ≤ 5°), test đồ thị phụ thuộc (đổi observed shot 26 → 27–29 cần xem). Blender / render: `-m slow`, chỉ máy chính. Hiện có phải xanh:
`test_stage_facts.py`, `test_stage_auto.py`, `test_side_truth.py`, `test_continuity*.py`, `test_camera_match_qc.py`, `test_whitebox.py`.

## 10. Việc mở
1. Nơi lưu revision map (tệp JSON vs bảng) — đề xuất tệp + chỉ mục nhỏ; bảng = migration Cấp 3.
2. Sơ đồ 2D G46 (ảnh JPG ngoài repo) → định dạng có tọa độ (người duyệt chấm điểm trên `top_raw.png`) — cần công cụ nhỏ.
3. Người duyệt map cảnh 4/6/8 #31 + tháp #33 (cổng nghiệm thu M3 kế hoạch §3).
