# V3.1 M0.5 — Báo cáo coverage sổ lỗi `devsys/errors.json` (20/10/2026)

Sổ: `devsys/errors.json` (schema_version 1, 86 mục). Kiểm: `python -m devsys.errors check` → Hợp lệ; `tests/test_error_registry.py` 19 qua.
Mỗi mục có `source_document` = file:dòng, test kiểm dòng đó thật sự nhắc mã.

## Theo nguồn
| Nguồn | Mã | Số mục |
|---|---|---|
| `docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md` | G1–G24, G26–G50 | 49 |
| `docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md` §15.5 (dòng 556–568) + dòng 260 | G51–G58, A11–A15, R3 (→ `V21-R3`) | 14 |
| `docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md` | A1–A10, B1–B12 | 22 |
| `docs/V3_1_GOI_SUA_VA_RUI_RO_2026-10-20.md` dòng 215 | R2 (→ `V31-R2`) | 1 |
| **Cộng** | G 57 · A 15 · B 12 · R 2 | **86** |

**Mã khuyết:** G25 — tài liệu #31 đánh số nhảy G24 → G26 (V2.1 §15.5 dòng 550 xác nhận) → không bịa, ghi `missing_codes`. G50 có thật (#31 dòng 169,
"(c) G50 …"; commit `65f4e860`). Coverage G1–G58 trừ G25 = 100 %; A1–A15 = 100 %; B1–B12 = 100 %.
Ngoài phạm vi: G59 (tự dọn Kho chủ thể 13/10 không chạy, `docs/V3_1_GOI_SUA_VA_RUI_RO_2026-10-20.md:123`) — chưa nhập (đề bài G1–G58); đề xuất thêm `P31-G59` khi phiên chính duyệt.
Mã trùng tên khác nghĩa trong lịch sử commit (A18…A29 của kế hoạch kiểm soát 10/10; G0–G9 của TODO 17/10 khác G của tài liệu #31) → mã bất biến có tiền tố dự án (`P31-`, `P33-`) để không lẫn.

## Theo trạng thái (theo bằng chứng trong repo, KHÔNG có mục VERIFIED)
| Trạng thái | Số | Mục |
|---|---|---|
| FIXED_UNVERIFIED | 13 | G7, G8, G10, G24, G27, G35 (M0.2); G36, A1, A15 (nhánh `claude/v31-m12-m13` `5e5df49d`, cờ `poll_claim` / `pause_before_submit` TẮT, chưa gộp main); A3, A13, R2 (M1.4a `222bf9c5`); R3 `vat` (M1.1 `36fcb4bd`) |
| IN_PROGRESS | 4 | G30 (M1.5), G33, G57 (M1.4b), A2 (M1.4b) |
| OPEN | 67 | còn lại |
| WONT_FIX | 2 | B6 (cổng chặn đúng — không phải lỗi), B12 (giới hạn Remote Control, ngoài pipeline) |

## Theo workstream
WS0 1 · WS1 21 · WS2 11 · WS3 20 · WS4 25 · WS5 5 · WS6 1 · không WS 2 (2 mục WONT_FIX).

## Liên kết lỗi gốc ↔ lần xuất hiện
`root_cause_id`: G41, G43, G44, G45, G47, G50 → `P31-G46` (gốc chung vị trí xuyên shot); G58 → `P31-G30` (Kho chủ thể đầy lặp ở #33).
`dependencies`: G53 → G10; V31-R2 → A2, A3, A13, G33, G57.

## Giới hạn
- `shot_ids` / `job_ids` để trống: số shot/job nằm trong cột bằng chứng (`evidence`); tách thành trường số cần đọc CSDL máy chính (diag_events/jobs) — M1.8.
- `stage`, `category`, `severity`, `plan_task` do phiên cloud gán theo nội dung nguồn (đề xuất) — phiên chính rà lại khi gộp.
- Trang hiển thị sổ (devsys/app.py) để phiên chính làm sau (theo đề bài).
