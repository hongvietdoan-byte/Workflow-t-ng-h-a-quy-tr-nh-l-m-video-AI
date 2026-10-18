# P1 — Xác minh baseline trước B1 (kế hoạch V2.1 R2 §14.1 / §14.7)

> Ngày 18/10/2026 15:47–16:10, phiên `ai-video-pipeline-upgrade-plan-04b569`. **Chỉ đọc, 0 USD.** CSDL mở bằng
> `file:…/data/manifest.sqlite?mode=ro` (không ghi). Đây là xác minh điều kiện, **chưa phải** capture B1 (B1 vẫn chờ duyệt).

## 1. HEAD và Q5

| Kiểm | Kết quả |
|---|---|
| `git rev-parse HEAD` (worktree, = `origin/main` sau commit nhận gói) | `186a2cc9` (cha `e4a779d3`) |
| POV `4775eab4` | `merge-base --is-ancestor 4775eab4 HEAD` → **có** |
| Nhánh wizardly `3a2a6eb9` | SHA cũ **không** là tổ tiên (rebase làm phẳng, xem `e4c010ac`, `d425fc35`) → kiểm theo **nội dung**: |
| ↳ trigger | `core/db.py:690–701` `trg_scene_noi_chon` + `trg_scene_noi_chon_new` (DROP + CREATE) |
| ↳ đồng bộ bản chép | `core/shot_intent.py:33` `sync_noi_chon` |
| ↳ quyết định | `data/decisions.json` id `time-weather-single-source-2026-10-17` |
| ↳ công cụ | `tools/pregen_check.py` có trên main |
| Test nền (11 file: replay p30, shot_intent, qc_observe_d14, byd_fill, change_audit, continuity, decisions, dashboard, POV/noi_chon liên quan) | **244 passed** (79 s) |

**Kết luận Q5: ĐÃ THỎA trên HEAD** (POV theo ancestry; wizardly theo nội dung + test).

## 2. CSDL máy chính (`D:\AI-Video-Pipeline\data\manifest.sqlite`, chỉ đọc)

| Kiểm | Kết quả |
|---|---|
| `PRAGMA user_version` | 77519931 |
| Trigger | `trg_change_scene`, `trg_change_motion`, `trg_change_asset(_image, _image_new)`, **`trg_scene_noi_chon`, `trg_scene_noi_chon_new`**, `ticket_events_no_*` |
| Bảng `overrides` | chưa có (đúng: migration P3 chưa duyệt) |
| Cột `scenes` | `id, project_id, idx, title, state, data` (thời gian/thời tiết shot ở `data.time` / `data.weather`) |

## 3. Dữ liệu #24 / #27 / #31

| Dự án | Shot | Có BYĐ | `byd_v` | `vat[]` | Shot khai `dang` | `byd.noi_chon.thoi_*` ↔ `data.time/weather` |
|---|---|---|---|---|---|---|
| #24 | 12 | 12 | v1 (thiếu) 12 | rỗng 12 | 8 | khớp 12/12 |
| #27 | 22 | 0 | — | — | 0 | — |
| #31 | 36 | 36 | v1 (thiếu) 36 | rỗng 35, **chuỗi 1** (shot idx 30, id 338: `["AWM"]`) | 24 | khớp 36/36 |

`thanh_phan[]` mọi mục đều là dict có `vat` (#24, #31) → nhánh `thanh_phan` của `qc_observe` không raise.

## 4. Cờ máy chính (`data/feature_settings.json`)

`shot_intent` BẬT · `video_pregen` BẬT · `send_claim` BẬT · **`qc_observe_enum` BẬT** · `qc_team` = `trainee` · `change_review` BẬT ·
`project_prop_lock` BẬT · `scene_qc` BẬT · `byd_fields` chưa có (đúng).

## 5. Phát hiện mới (đổi mức rủi ro R3)

**R3 không còn là rủi ro tương lai mà đang xảy ra trên máy chính:** `qc_observe_enum` BẬT + #31 shot idx 30 có `byd.vat = ["AWM"]` (chuỗi)
→ `core/qc_observe.py:62–64` raise `ValueError('BYĐ.vat thiếu vật chuẩn')`. Lỗi được bắt ở `core/qc_scene.py:661` → shot đó vào
`summary["failed"]` (có báo, không im lặng) nhưng **QC ảnh shot 30 #31 không bao giờ chạy được** tới khi sửa. Đường `llm_runner.py:927`
(QC từng job) cũng gọi `qc_observe.run` → cùng lỗi.
Cách sửa đề xuất (nhỏ, chưa làm — cần duyệt vì là code pipeline, quy ước 7): parser v1 `str → {"vat": <chuỗi>}` dùng chung (§14.2) cho
`qc_observe`, kèm test chuỗi/dict/rỗng/None/dict thiếu khóa.

## 6. Còn lại trước B1

- [x] HEAD + Q5 (mục 1) · [x] trigger + schema (mục 2) · [x] dữ liệu 3 dự án (mục 3) · [x] snapshot cờ (mục 4)
- [ ] Người dùng duyệt P1 (R2 §12 câu 1, 6) — B1 chỉ đọc CSDL, fixture ghi ra workspace test riêng
- [ ] Ghi `git_sha` + snapshot cờ **tại lúc capture** vào fixture (số ở đây chỉ là mốc 18/10)
