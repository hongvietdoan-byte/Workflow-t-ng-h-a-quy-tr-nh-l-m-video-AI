# Kế hoạch AI Video Pipeline V3 — bản hợp nhất từ V2.1 (R2 + phụ lục R3) — 20/10/2026

> **Trạng thái: KẾ HOẠCH, CHƯA DUYỆT, CHƯA TRIỂN KHAI. 0 USD.** Không trùng với `docs/KE_HOACH_V3_CHINH_THUC.md` (kế hoạch v3 cũ 23/09 về phân
> shot / Director — đã xong, chỉ còn giá trị lịch sử). Bản này hợp nhất ba tài liệu, giữ chúng làm bằng chứng chi tiết:
> - **KH-gốc** `docs/KE_HOACH_TRUONG_CAU_TRUC_VA_HOI_QUY_GOI_2026-10.md` (17/10): ý shot thành trường cấu trúc + hồi quy trên gói thật.
> - **V2.1 R2** `docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md` §1–§14 (17–18/10): audit, D/E/F, phụ lục R2.
> - **V2.1 §15** (phụ lục R3, 20/10): lỗi #31 / #33 chưa có kế hoạch, nhóm N1–N7 có file:dòng.
>
> **Phụ lục A** chép rút gọn toàn bộ quyết định / thiết kế / điều kiện của V2.1 R2 §1–§14 → V3 đọc độc lập được; V2.1 chỉ còn là bằng chứng file:dòng.
>
> Mốc code: `main` = `3ecf053b`. Mọi file:dòng ở V2.1 §13 / §15 — mở lại file trước khi sửa.

## 1. Vì sao có V3

- V2.1 viết trước khi #31 phát sinh G26–G50 (19/10) và trước #33 (19–20/10). Rà lại: V2.1 chỉ che ≈ 1/4 lỗi #31 và **không che lỗi nào của #33**.
- Ba nhóm lỗi lặp ở **cả hai** dự án mà V2.1 không có: (1) vận hành Claude / tiến trình / tạm dừng, (2) ước tính giá sai, (3) vị trí vật
  và hình học 3D xuyên shot. Hai nhóm đầu đã gây trả tiền thừa thật.
- Rà CSDL thật 20/10 (V2.1 §15.5): hai tài liệu lỗi **chưa ghi hết** — thêm 13 mã (G51–G58, A11–A15), chủ yếu chấm clip nháp tối
  19/10 và lỗi chỉ hiện trong `diag_events`. V3 thêm công cụ ghi lỗi cuối dự án để không phụ thuộc trí nhớ phiên.
- Bối cảnh mới từ 19/10: bỏ Anthropic API, bước Claude chạy `claude_cli` (quyết định `no_anthropic_api_use_claude_code`) — V2.1 vẫn giả định
  chi Claude theo API.

## 2. Mục tiêu và nguyên tắc

**Mục tiêu (đo được):**
1. 0 lần trả tiền thừa do lỗi hệ thống (gửi trùng, gửi khi tạm dừng, tự gen lại vì đọc file dở, lùi model vì Kho đầy).
2. Ước tính giá trước gen lệch sổ chi ≤ 10 % (hiện: video nháp ≈ +37 %, bản cao ≈ +24 %).
3. Gói gửi model đọc **trường có cấu trúc** (BYĐ v2), không dò chữ — lỗi lọt cổng do chữ tự do −50 % (KPI V2.1 §10).
4. Vị trí người/vật xuyên các shot cùng cảnh lấy từ **một sơ đồ mặt bằng**, không tả lại bằng chữ từng shot.
5. QC bắt được clip đơ / sai khung đầu trước khi người dùng thấy; không bật QC chặn khi chưa qua benchmark (§14.4).

**Nguyên tắc (giữ từ KH-gốc §2, V2.1 §5, CHUAN_XAY_DUNG):** một builder gói (`runner._build_package`) cho gửi thật / thẻ xem / replay / golden;
mọi chặn hoặc vượt cổng ghi một chỗ có người + lý do; không im lặng khi thiếu đầu vào; "đã sửa" phải có bằng chứng chạy thật; mọi lời gọi
tốn tiền qua sổ chi + ước tính trước; cờ mới TẮT mặc định, bật khi đã kiểm chứng; mỗi lần sửa code chạy quy ước 7.

## 3. Hiện trạng tóm tắt

| Mảng | Có | Thiếu |
|---|---|---|
| BYĐ | `shot_intent.validate`, Đạo diễn khai ≤ 2 vòng | `byd_v`, `vat[]` có schema, khâu dựng gói đọc BYĐ, `byd` trong `lineage` |
| Gói gửi | một builder, `jobs.sent_package` (sha) | replay video, golden, thẻ "Gói sẽ gửi" trên Dashboard |
| Kiểm trước trả tiền | video (`video_pregen`), `pregen_check` (ảnh) | preflight ảnh trong runner; giá video trong `pregen_check` |
| Vận hành | `send_claim`, khóa vòng nền mỗi CSDL, G35 giữ khi rà lỗi | khóa poll theo job giữa tiến trình (A1), provider Claude theo dự án (A2), kiểm tạm dừng ngay trước gửi (G36), đếm Kho chủ thể (G30) |
| Hình học 3D | `stage_auto`, `stage_facts`, `plate_camera`, `model3d.stretch` (G8) | sơ đồ mặt bằng chung theo cảnh, người nộm tỉ lệ, góc hơi cao |
| QC | autoqc, qc_scene, clip_measure, final_qc, qc_golden, `qc_sequence_logic` (TẮT) | mã lỗi thống nhất, bắt clip đứng yên kéo dài, cross-shot |
| Dashboard | cổng ảnh/video, bỏ qua có lý do | BYĐ, thẻ gói, bảng override thống nhất |

Đã sửa sau 18/10 (không cần kế hoạch): G7, G8, G10, G24, G27, G35 (V2.1 §15.1).

## 4. Lộ trình V3

| Phase | Phạm vi | Nguồn chi tiết | Phụ thuộc | Chi phí | Điểm dừng duyệt |
|---|---|---|---|---|---|
| **P0** | Duyệt V3 + Q1–Q6 (V2.1 §4, §14.6) | tài liệu này | — | 0 | người dùng |
| **P0.5 (mới)** | **N1 vận hành:** A1 khóa poll/succeed theo job, A3 `clean_env` bỏ key API, G36 kiểm tạm dừng trước `submit`, G39 kiểm `data_dir`, A2 provider Claude theo dự án, G30 đếm Kho chủ thể. **N2 giá:** A7 phụ phí ref + giá nâng 1080p + hệ số từ sổ chi, A8 tier nháp, A9 Claude = 0 khi `claude_cli` + giá video trong `pregen_check`. **Bổ sung từ rà CSDL (§15.5):** A13 hết lượt gói Claude Code = dừng có giờ mở lại, A14 trích ngân sách dự án = 0 thì chặn, G55 cảnh báo Dashboard chạy code cũ, G56 gộp diag lặp, G57/G58, A15; công cụ `tools/project_error_report.py` ghi lỗi cuối dự án từ `diag_events` + `jobs`. **Kèm R3 (đang xảy ra):** parser `vat` v1 `str → {vat}` cho `qc_observe` | V2.1 §15.2 N1, N2, §15.5 | không (độc lập BYĐ) | 0 USD (provider giả) | sau mỗi nhóm: test + quy ước 7 |
| **P1** | Golden gói: B0 dò đường mở ảnh, B1 chụp (ảnh + **video**), B2 test Compatibility / Correctness. Correctness thêm ca thật #31 (G27, G13) và #33 | V2.1 §6.B, §14.1 | baseline đã xác minh 18/10; chụp lại cờ ở máy chính | 0 | duyệt phạm vi chỉ đọc |
| **P2** | BYĐ v2 (A0–A3): `byd_v`, `vat[]` schema + parser v1/v2 (sửa luôn lỗi ngầm `qc_observe`), Q2 trigger, Q3 `forms[]` trong `assets.profile` (+G38), field readers A2a–A2f, `byd` vào `lineage`. **Kèm N5:** `insert_scene_after` chép bối cảnh + BYĐ (G6, G21); **G1** chỉ mang đạo cụ có trong BYĐ; **A4** `locks.guard` cho mọi đường Claude ghi `scenes.data` (VÀNG trước, chặn sau) | V2.1 §6.A, §14.2, §15.2 N5 | P1 | Q3 ≈ 0,05 USD (xin duyệt) | Q3, mỗi cờ con |
| **P3** | Dashboard: thẻ "Gói sẽ gửi" (so `sent_package`; sửa G5 khóa theo đường dẫn đầy đủ), BYĐ trên Dashboard, siết 3 cổng Q6 + bảng `overrides`, chỉ số C (cost/accepted shot, retry cost, override rate). **Kèm N6:** G15–G17 | V2.1 §6.C, §15.2 N6 | P2 | 0 | migration `overrides` |
| **P4** | **D + N3 gộp:** sơ đồ mặt bằng theo cảnh thành dữ liệu (`stage_facts`) làm Expected state vị trí; người nộm tỉ lệ (G2); góc `slightly_high` + `eye` ≤ 5° + kiểm `depth.png` (G3, A10, G49); bỏ khóa chân trời khi nền không có trời (G20). **E + N4/N7:** image preflight, mã lỗi, clip đứng yên > 1,5 s, `qc_sequence_logic`, cross-shot (G42), luật router không gộp nhóm khi cần khung đầu (G28, G37, B9), độ dài gói nhóm (G13), cắt cảnh trong video ref (B8), A5, A6, G14; **§15.5:** G51 tiêu chí đơ / tương tác / lố cho QC clip, G52 lỗi logic chuỗi, G53 lời dẫn ở `seedance_refs`, G54 ngân sách ký tự, A11 thông điệp khung cuối, A12 BYĐ qua `claude_cli` | V2.1 §7.D/E, §14.3, §14.4, §15.2 N3/N4/N7 | P2 | render 0 USD; gen thử ảnh chứng minh N3 — xin duyệt | benchmark §14.4 trước khi cho chặn |
| **P5** | F repair router theo mã lỗi | V2.1 §7.F, §14.5 | P4 | theo `spend_gate` | từng nhóm lỗi |
| **Tồn đọng** | Export Premiere (P5+ tùy chọn); **Thay nền video** (§6) | — | — | — | — |

## 5. Quyết định chờ người dùng

| # | Câu hỏi | Khuyến nghị |
|---|---|---|
| 1 | Duyệt V3, mở **P0.5** ngay (0 USD) và P1 chỉ đọc? | Có |
| 2 | A2: provider Claude theo dự án (cột `projects.llm_provider`) hay theo phiên? | Theo dự án; rỗng = `dashboard.env` |
| 3 | G30: khi Kho chủ thể đầy — chặn + đề xuất dọn (người duyệt) hay tự dọn asset dự án đã kết thúc? | Chặn + đề xuất |
| 4 | A4: trường người sửa tay tự vào `_user_locked`? | Có, bắt đầu VÀNG |
| 5 | N3: chuyển sơ đồ mặt bằng thành dữ liệu cho mọi cảnh có ≥ 2 shot cùng sân khấu? | Có, thử trước trên cảnh 4/6/8 #31 |
| 6 | Q1–Q6 của V2.1, migration `overrides`, Premiere, quyền chụp fixture chỉ đọc | xem Phụ lục A.8 |

## 6. Tồn đọng: thay nền video (người dùng 20/10, "có thể update sau")

**Yêu cầu:** người dùng gửi một video quay người thật + (mô tả nền bằng chữ **hoặc** ảnh ref nền) → hệ thống trả video cùng người, cùng
động tác, nền mới. Ví dụ thành quả người dùng gửi: `E:/Tai xuong/cgt-20261020000346-zyeku_202610192303.mp4` (9,7 s, 1080×1920, 24 fps): người
nhảy giữ nguyên mặt, áo, động tác; nền thành vườn hoa hồng hoàng hôn, ngược sáng khớp viền tóc, nền chuyển động theo máy.
Cách làm gốc: cuộc trò chuyện ChatGPT người dùng xuất PDF `E:/Tai xuong/Kling_Seedance_2_5_Conversation.pdf` (đã đọc 20/10):
- **Model / chế độ:** Seedance 2.5 trên Kling AI, chế độ *Video Edit / Video-to-Video*, video gốc làm reference; giữ thời lượng (≈ 9,8 s),
  9:16, ≥ 1080×1920; creativity THẤP, reference adherence + motion preservation CAO; giữ camera motion gốc.
- **Prompt 6 khối (bản rút gọn ≤ 5 000 ký tự là bản dùng):** TASK → giữ nguyên người (mặt, tóc, da, áo, mọi cử chỉ; "do not regenerate") →
  BACKGROUND (xóa nền cũ, tả nền mới thật, "not CGI") → CAMERA MOTION SYNC (phân tích và tái tạo rung tay; nền neo trong thế giới 3D;
  "do NOT stabilize, freeze, or independently animate the background; do NOT attach background movement to the person's body") →
  3D PARALLAX (vật gần dịch nhiều hơn vật xa) → SUBJECT MASKING (tóc, ngón tay, mờ chuyển động, tay sát máy) → NATURAL COMPOSITING (ánh
  sáng ấm, viền sáng, bóng) → TEMPORAL CONSISTENCY → FINAL RESULT. Kèm negative prompt (static/frozen/locked background, camera motion
  mismatch, flat 2D backdrop, edge halos, missing fingers, face/clothing changes…).
- **Thứ tự ưu tiên trong prompt:** giữ người → đồng bộ chuyển động máy → thay nền sạch → ánh sáng.
- **Giới hạn đã ghi trong cuộc trò chuyện:** prompt không bảo đảm tách nền 100 %; nếu model vẫn ra nền đứng yên / trượt → cần camera
  tracking từ video gốc + matting/compositing (đường dự phòng).

**Mẫu đã chạy thật trên ClipAI (người dùng 19/10 23:00, đọc lại danh sách task ClipAI 20/10, chỉ đọc):**

| | Bản mẫu 480p `cgt-20261020000042-prl47` | Bản 1080p `cgt-20261020000346-zyeku` |
|---|---|---|
| Model | `dreamina-seedance-2-5-260628` | cùng |
| Nội dung gửi | `text` = **"Chỉnh sửa@Video1 "** + prompt rút gọn (bản "nên dùng" của PDF) **nối liền negative prompt vào cuối** (không có trường negative riêng); `reference_video` = `asset://asset-20261019235356-z5stm` (video nguồn đã tải lên kho asset ClipAI) | `content = [{type: "draft_task", draft_task: {id: "<task 480p>"}}]` — nâng từ bản mẫu, không gửi lại prompt |
| Tham số | `draft: true`, `duration: -1` (theo video nguồn), `ratio: "adaptive"`, `resolution: "480p"`, `generate_audio: true`, `video_num: 2` | `resolution: "1080p"`, `video_num: 1` |
| Kết quả | 2 bản mẫu; hết hạn nâng sau ≈ 7 ngày (`draft_expired_at`) | 9 s, 9:16, 24 fps, `has_video_input: true`, 909 225 token |
| Giá | ước tính lúc gửi 2,52 USD (2 bản) | ước tính lúc gửi 2,80 USD; **dòng task ghi `seedance_cost_usd` 6,36 USD** — cần đối chiếu sổ ClipAI xem số nào là tiền thật |

Đối chiếu với code hiện có (`core/adapters/clipai.py`):
- `submit_video_edit` (S4.12, cờ `seedance_video_edit`) đã gửi được Seedance 2.5 sửa clip, nhưng **khác mẫu**: thêm
  `omni_reference_task_type: "edit"`, `generate_audio: False`, không có `draft`, tải video dạng tệp thay vì asset, và chặn 1080p.
- `submit_final_from_sample` đã có (nâng `draft_task` → 1080p) — dùng lại được cho bước nâng.
- → Việc code: thêm tùy chọn `draft=True` + tiền tố "Chỉnh sửa@Video1" vào `submit_video_edit` (hoặc hàm mới `submit_background_replace`),
  so trước bằng một lần gửi thử 480p xem có cần `omni_reference_task_type` không; giá ước tính theo token video vào (`cost.seedance_token_usd`)
  và cập nhật bảng giá nâng 1080p (trùng A7).

**Thiết kế trong pipeline:**
- **Bộ dựng prompt bằng code** theo đúng 6 khối trên: khối người sinh từ mô tả đo được (tóc, áo, đạo cụ — đọc khung đầu bằng Claude
  `claude_cli`, 0 USD API), khối nền từ chữ người dùng hoặc mô tả ảnh ref nền; tự kiểm ≤ 5 000 ký tự (cùng ngân sách ký tự G13/G54).
  Khối CAMERA MOTION SYNC chỉ thêm khi đo thấy máy rung/di chuyển.
- Đầu vào: video nguồn (bắt buộc), mô tả nền và/hoặc ảnh ref nền; tùy chọn: giữ âm thanh gốc.
- Đường dự kiến: video-to-video có video tham chiếu (hướng `KE_HOACH_V2V_CAT_DOAN_2026-10-16.md` + luật video ref ClipAI ≥ 3 s), khung đầu = khung
  nguồn đã thay nền (gen ảnh với ảnh ref nền); hoặc tách người (mask) + nền gen + ghép, chỉnh ánh sáng.
- **Chuyển động nền khớp máy gốc (người dùng 20/10):** prompt cuộc trò chuyện có ba cơ chế — *Camera Motion Tracking* (đo chuyển
  động/rung của máy trong video nguồn), *Background Motion Synchronization* (nền mới dịch/rung đúng theo chuyển động đó),
  *Parallax* (lớp gần — hoa sát người — trôi nhanh hơn lớp xa — vòm hoa, trời). Hướng làm trong pipeline: đo chuyển động máy trên
  vùng NỀN của video nguồn (optical flow / homography mỗi khung sau khi che người; tái dùng `clip_measure`) → (a) đưa đường chuyển động
  vào prompt / video ref cho model, hoặc (b) nếu ghép bằng mask: nền nhiều lớp theo độ sâu, mỗi lớp dịch theo đường máy nhân hệ số
  parallax. Kiểm: so đường chuyển động nền đầu ra với đường máy nguồn (lệch ≤ ngưỡng), không có nền "đứng im" khi máy rung.
- Kiểm: mặt / trang phục giữ nguyên (so khung), động tác khớp nguồn (`clip_measure`), không lộ viền mask; bộ lọc "người thật" của Seedance
  (G32) là rủi ro — người dùng phải có quyền với người trong video.
- Chi phí: ước tính trước + sổ chi như mọi lời gọi tốn tiền; nháp 480p trước (luật rẻ trước, không phóng 480p).
- **Đã xác nhận 20/10:** ClipAI gửi được Seedance 2.5 sửa video + nâng 1080p qua API (mẫu thật ở bảng trên) → không cần adapter Kling.
- Vị trí: mục mới trong Kho / bước 4, ngoài luồng dự án phim. Phase: sau P0.5 (cần giá đúng), độc lập P1–P5.

## 7. Rủi ro chính (bổ sung V2.1 §9)

| # | Rủi ro | Giảm thiểu |
|---|---|---|
| R11 | A1 đụng đường ghi job lõi | UPDATE có điều kiện + test 2 tiến trình + chạy cả bộ |
| R12 | A2 đổi chọn provider chạm mọi khâu Claude | cờ riêng, mặc định giữ env; quy ước 7 |
| R13 | A4 chặn nhầm sửa hợp lệ của Đạo diễn | VÀNG trước, đo, rồi mới chặn |
| R14 | Sơ đồ mặt bằng sai làm sai hàng loạt ảnh | người duyệt sơ đồ trước gen (như 19/10), golden P1 bắt thay đổi gói |
| R15 | Hệ số giá tự học từ sổ chi bị lệch vì ít mẫu | hiện cả giá bảng và giá hiệu chỉnh, trần cứng dư |

## 8. Nghiệm thu tổng

Giữ V2.1 §10, thêm: P0.5 — tái hiện bằng provider giả A1 / G36 / G30 cho 0 job thừa; ước tính #33 chạy lại lệch sổ chi ≤ 10 %. P4 — cảnh
4/6/8 #31 sinh câu vị trí từ sơ đồ, người dùng chấm ảnh không còn lỗi G41–G48; clip đứng yên > 1,5 s bị gắn REVIEW trên 12 clip nháp #31.

---

## Phụ lục A — Nội dung kế thừa từ V2.1 R2 (§1–§14), để V3 đọc độc lập

> Chép lại ở dạng rút gọn các quyết định, thiết kế và điều kiện của V2.1 R2. Bằng chứng file:dòng đầy đủ vẫn ở V2.1 §13 (mốc `b39e005b`,
> xác minh lại 18/10 trên `186a2cc9` — biên bản `docs/audit/P1_BASELINE_VERIFICATION.md`). Nếu A và V2.1 lệch nhau, V3 thắng.

### A.1 Sáu giả định của KH-gốc đã sửa (V2.1 §1, §11)

1. Thẻ gói (B4) so với **`jobs.sent_package`** (gói đầy đủ, có sha), không phải `jobs.sent_refs`.
2. Video (L12) **đã có** kiểm trước trả tiền (`video_pregen`, cờ chưa `verified`); chỉ **ảnh (L8) chưa có** (`runner._Runner._pregen` trả False).
3. Kho **chưa có** trường `forms` có cấu trúc → enum `dang` chỉ áp sau Q3.
4. `vat[]` chưa có schema; `qc_observe` đòi `vat` là dict `{vat}` → raise với chuỗi v1 (**đang xảy ra**: #31 shot 30 `vat=["AWM"]`, `qc_observe_enum` BẬT).
5. `lineage` không đưa `byd` vào vân tay → sửa BYĐ không làm ảnh "⚠ cũ" (R4).
6. Q2 (giờ/thời tiết) đã chốt theo cách **đồng bộ bản chép bằng trigger CSDL** (`time-weather-single-source-2026-10-17`), không "bỏ" trường.

Thêm: không cần Continuity Engine mới — tái dùng `lineage`, `end_frames`, `layout_follow`, `side_truth`, `travel_truth`, `stage_facts`
(`core/continuity.py` hiện chỉ là cảnh báo regex).

### A.2 Kiến trúc đích (V2.1 §5)

```
BYĐ v2 (scenes.data.byd, byd_v)   ──validate──►  BLOCK/REVIEW/WARN ──► overrides (bảng mới)
   │  (v1 / thiếu → đường cũ + provenance + VÀNG)
   ▼
Field readers (A2a–A2f) — dùng lại character_forms, prop_lock(weapon_table), assets, plate_choice, plate_anchor, scene_establish
   ▼
runner._submit_args (ảnh/video) ──► _build_package (MỘT builder) ──► [chạy khô] thẻ "Gói sẽ gửi" / replay / golden
   │                                                        └──► [thật] jobs.sent_package ── so với thẻ
   ▼
_pregen: video_pregen (có) + image_preflight (mới, cùng mã lỗi) ──► gửi (send_claim, spend_gate, kiểm paused — G36)
   ▼
QC ảnh / video → mã lỗi + bằng chứng ──► Observed state (UNKNOWN nếu thiếu)
   ▼
Continuity state (Expected = BYĐ + sơ đồ mặt bằng N3 / Observed = QC / Resolved = người duyệt) ──► lineage: stale theo đồ thị
   ▼
Repair router (F) → tầng BYĐ / asset / ảnh / video / âm / dựng → job mới có parent_job_id + vân tay đầu vào (giữ bản cũ)
   ▼
final_cut / delivery → final_qc (+ khung đen / đứng hình) → export (+ Premiere: tùy chọn)
```

### A.3 P1 — Golden gói (V2.1 §6.B, §14.1, §8)

- **Đóng băng baseline trước B1:** trên đúng máy chụp chạy `git rev-parse HEAD`, `git status --short`, kiểm nội dung thay đổi trigger +
  POV (theo diff/test, không chỉ theo SHA cũ), chạy lại test nền; đóng băng HEAD, schema CSDL, snapshot cờ, provider/model, input dự án,
  hash ảnh/ref. Thiếu `data/` thật → ghi UNKNOWN, **không chụp golden giả**. B1 chỉ đọc CSDL production, fixture ghi ra thư mục test.
- **B0:** dò mọi `open` / `Image.open` / `cv2` và `sent_package.sha256_of` trên đường dựng gói (`assets`, `location_pack`, `place_refs`,
  `skill_objects`, `layout`, `plate_env`…) → danh sách `needs_pixels`.
- **B1:** `tools/payload_golden.py --capture` tái dùng `tools/replay_payload.build_sandbox/replay`; thêm **replay video**
  (`VideoRunner._submit_args` + `_submit_kwargs`); gói rút gọn theo schema `sent_package` v1 (prompt, refs {param, role, label, file, sha}).
- **B2:** hai bộ test tách riêng — `test_payload_compat.py` (cờ máy chính, `byd_fields` TẮT → giống fixture từng byte; khác = ĐỎ) và
  `test_payload_correctness.py` (mỗi lỗi đã biết một khẳng định; thêm ca #31/#33 ở V3).
- **Cập nhật fixture:** `--update --why`, `CHANGES.md` có **tên người duyệt**; test đỏ nếu sha fixture không có dòng CHANGES; diff theo
  shot/trường in vào commit message; không tự chấp nhận.
- **Ma trận cờ:** (a) cờ máy chính; (b) + `byd_fields` BẬT; (c) mỗi cờ con A2a…A2f bật riêng.
- Test cần `data/` → `pytest.skip("needs_data: …")` có lý do; một test đếm số skip.
- **Nghiệm thu:** Lớp 1 xanh không cần `data/`; Lớp 2 xanh ở máy chính; cố ý đổi `_MARK_SEG` → đỏ đúng shot; fixture đầu tiên = diff rỗng
  so với replay. **Rollback:** xóa file mới (không đụng production).

### A.4 P2 — BYĐ v2 (V2.1 §6.A, §14.2)

| Mục | Nội dung |
|---|---|
| A0 đối chiếu | thống kê hình dạng `byd.vat` thật #24/#27/#31 + đường đọc của `qc_observe`, `shot_intent`, `prop_lock`; đếm shot sẽ raise |
| A1 schema | `byd_v: 2` (thiếu = v1). `vat[]` = `{vat (tên, giữ khóa để tương thích qc_observe), kho_id, nguoi, cach: cam\|deo\|dat\|nem, bien_the?}`; chuỗi v1 → `{vat: "<chuỗi>"}` + VÀNG `vat_v1`. `dang` giữ 3 dạng hiện có, enum chỉ sau Q3 |
| Đọc theo version | một hàm `shot_intent.read(data, field) -> (value, provenance, warn)`; provenance ∈ `byd_v2` / `byd_v1` / `suy_tu_spot` / `doc_chu`; fallback luôn ghi diag `byd_fallback` |
| Regex → VÀNG | luật so chữ chuyển thành `text_vs_field` (VÀNG), **không** đổi ảnh / khóa / câu; đo báo nhầm ở C |
| A2b đạo cụ | `prop_lock.weapon_table` là mặc định, `vat[]` của shot ghi đè; không xây bảng mới |
| A2c/A2d | đụng `plate_choice.py` cùng sửa POV (`4775eab4` — đã lên main) |
| Q3 | `outfit / hair / face` + `forms[]: {ma, ten_en, image_role: character_form, outfit_override?}` trong `assets.profile`; `character_forms.for_shot` đọc `byd.dang` → `forms[ma]`; `without_clothes` chỉ còn lưới an toàn có VÀNG |
| Backfill #31 | `tools/byd_backfill.py` in cột provenance từng ô; ô không chắc để trống; ghi chỉ sau duyệt, qua `llm_io.update_scene` (để trigger + `change_events` thấy) |
| Mức chặn | BLOCK: schema sai, `kho_id` không có, `vat.nguoi` không thuộc `thanh_phan`. REVIEW: lệch ý đồ ↔ số đo (`moc_nen` vs `landmark_facts`), `dang` ngoài `forms`. WARN: `text_vs_field`, fallback v1 |
| `lineage` | thêm khóa `byd` (`thanh_phan, vat, noi_chon, khung`) vào vân tay ảnh **chỉ khi `byd_fields` bật** (giữ hash cũ khi tắt) |
| Test `vat` | chuỗi v1, dict v2, rỗng, `None`, dict thiếu khóa, `nguoi` ngoài `thanh_phan`, `kho_id` không có, `cach` sai, `qc_observe_enum` bật/tắt. **Cổng nghiệm thu:** 0 exception vì kiểu `vat`; dữ liệu thiếu → WARN/REVIEW/BLOCK đúng hợp đồng |
| File dự kiến | `core/shot_intent.py`, `prompts/31_director_byd.md`, `core/director_byd.py`, `character_forms`, `prop_lock`, `assets`, `scene_storyboard`, `plate_choice`, `plate_anchor`, `scene_establish`, `runner`, `shot_text_checks`, `shot_normalize`, `core/text_vs_field.py` (mới), `core/features.py` (`byd_fields` + cờ con), `core/lineage.py`, `tools/byd_backfill.py`, `data/decisions.json` + `tests/test_decisions.py` |
| Nghiệm thu / rollback | compat (cờ TẮT = byte) + correctness hết xfail + `tests/test_byd_v2.py`; KPI #31 shot trái trường = 0 (đo bằng replay). Rollback: tắt `byd_fields` / cờ con |
| Chi phí / duyệt | code 0 USD; Q3 soạn nháp ≈ 0,05 USD; Đạo diễn v2 < 0,30 USD/dự án — xin duyệt trước. Điểm dừng: duyệt bảng backfill #31, bảng chuyển đổi Q3, bật `byd_fields` cho dự án kế |

### A.5 P3 — Dashboard, cổng, chỉ số (V2.1 §2.3, §6.C, Q6)

- **Ba chỗ lỏng hiện tại:** (1) "Tôi đã xem, vẫn gen ảnh" (`dashboard/steps/step2.py:224/228` → `batch.queue_images(confirmed=True)`)
  chỉ ghi một dòng diag, không người / lý do / snapshot; (2) bỏ qua cổng video (`core/video_gate.py:skip`, lý do ≥ 3 ký tự) không mã lỗi,
  không snapshot; (3) "✔ Duyệt & khóa → Storyboard" (`step1._lock_and_go`) **không kiểm `anchor_approved`**.
- **Siết (Q6):** (a) ô "vẫn gen" chỉ bật sau khi mở thẻ gói; (b) lý do ≥ 15 ký tự — sửa **cả** `video_gate.py` và UI `video_gate_ui.py`;
  (c) "Duyệt & khóa" chặn khi thiếu ảnh mốc của nhân vật chính theo BYĐ (nhân vật phụ: REVIEW / override có lý do).
- **Bảng `overrides`:** `(id, at, actor, source nguoi/claude, scope image_gate/video_gate/lock/byd, scene_id, job_id, code, reason,
  payload_sha, payload_snapshot)`; `video_gate_skips` giữ và ghi song song; migration có up/down, kiểm trigger; không tự bật cổng chặn khi chưa nghiệm thu.
- **Thẻ "Gói sẽ gửi"** dựng bằng `_build_package` chạy khô; đã gửi thì so `jobs.sent_package`. **BYĐ trên Dashboard** đọc `scenes.data.byd`; thay đổi từ CLI/CSDL hiện ngược nhờ `change_events` + trigger.
- **Chỉ số C:** phân loại lỗi (`jobs.reject_reason` + gốc `chu_tu_do | hinh_hoc | khac`); báo nhầm mỗi luật (VÀNG mà người trả
  `khong_phai_loi`); cost / accepted shot (Σ `usage_events` join `jobs` ÷ shot có video approved); retry cost (job có `parent_job_id` /
  `retry_count > 0`); QC pass rate; override rate (`overrides` ÷ số lần gặp cổng).
- File: `dashboard/payload_card_ui.py`, `dashboard/byd_ui.py`, `step2.py`, `step4.py`, `step1_v2.py`, `video_gate_ui.py`,
  `core/video_gate.py`, `core/batch.py`, `core/db.py`, `devsys/stages.json` (L8 `kiem_truoc`).
- **Nghiệm thu:** thẻ khớp replay 100 % (thẻ shot 3 #31 = `replay --shot 3`); 100 % lần vượt cổng có người / lý do / mã / snapshot.
  Rollback: revert UI, bảng mới để nguyên.

### A.6 P4 — Continuity + QC tự động (V2.1 §7.D, §7.E, §14.3, §14.4)

**D — trạng thái liên tục (mở rộng tối thiểu):**
- Expected: BYĐ v2 (`thanh_phan.dang`, `vat.nguoi/cach`, `hanh_dong.bat_dau/ket_thuc`, `noi_chon`) + `stage_facts` / `side_truth` /
  `travel_truth` + **sơ đồ mặt bằng N3**; mỗi shot `state_before → action → state_after` cho {nhân vật, dạng, trang phục, đạo cụ, nơi, máy}.
- Observed: QC (`qc_observe` enum, `clip_measure`, `plate_layout_qc`); thiếu quan sát → UNKNOWN, không đoán. Resolved: người duyệt / overrides.
- Đồ thị phụ thuộc theo **logic truyện** (cùng thực thể, cùng cảnh), không theo thứ tự timeline; gen song song mặc định, chỉ shot có cạnh mới chờ;
  không ép khung cuối làm ref. Đổi `state_after` của A → B stale qua đồ thị (`lineage` + khóa `byd` + `end_frames.stamp_end_state`).
- **Hợp đồng lưu (§14.3):** `scenes.data.continuity_state = {schema_version, byd_revision, expected{source, value},
  observations[] (append-only: qc_run_id, artifact_id, model_version, value, unknown_fields), resolution{status, selected_observation_id, actor, reason}}`.
  QC **không** ghi đè expected; resolution chỉ ghi qua luồng duyệt có người / giờ / bằng chứng; BYĐ hoặc artifact đổi → resolution cũ
  thành STALE theo vân tay. Ghi nhiều / đồng thời → cân nhắc bảng phụ. **Nghiệm thu:** expected không bị QC sửa; observation cũ không duyệt
  nhầm artifact mới; cạnh cross-shot có bằng chứng logic truyện.

**E — QC 5 lớp:**

| Lớp | Có sẵn | Thiếu |
|---|---|---|
| Preflight | `shot_intent.validate`, `video_pregen`, `change_review.blocking`, `batch.image_gates`, `pregen_check` | `image_preflight` trong `ImageRunner._pregen`, chung mã lỗi với video |
| Ảnh | `autoqc`, `qc_scene`, `qc_team` (TẮT), `qc_observe`, `plate_layout_qc`, `camera_match_qc`, `qc_measure` | gom về mã lỗi; bằng chứng crop/bbox/số đo |
| Video | `clip_measure.measure`, `video_qc_context`, `video_analysis`, ffprobe | vật còn giữ, hành động xong so `hanh_dong.ket_thuc`, đứng yên kéo dài (G51) |
| Cross-shot | `continuity.*_warnings` (regex), `qc_sequence_logic` (TẮT) | so `state_after` A ↔ `state_before` B |
| Bản cuối | `final_qc.run` (độ dài, nhạc, peak, SRT, im lặng, phụ đề che mặt) | khung đen / đứng hình (ffmpeg `blackdetect` / `freezedetect`) |

**Benchmark trước khi cho QC chặn (§14.4):** bộ nhãn PASS / FAIL / UNKNOWN / nghiêm trọng / ca biên, tách `dev_set` / `independent_set`
(`qc_golden`), không rò biến thể cùng shot qua hai tập; báo cáo theo từng mã lỗi (confusion matrix, recall, báo nhầm, tỉ lệ UNKNOWN, chi phí,
độ trễ, đồng thuận người). Ngưỡng thử nghiệm (chưa hiệu chuẩn): ≥ 20 ca lỗi nghiêm trọng + ≥ 20 ca đạt mỗi nhóm luật; recall ≥ 95 %, báo
nhầm ≤ 5 %. Lộ trình: **Shadow** (chỉ ghi) → **Guarded** (chỉ luật kỹ thuật tất định được BLOCK, ngữ nghĩa → REVIEW) → mới tới tự sửa.
Không bật lại `qc_team` chỉ vì một tỉ lệ tổng; lưu bằng chứng có frame, `artifact_id`, `qc_run_id`, `qc_version`, vân tay đầu vào; độ tin cậy
model chỉ là tín hiệu chưa hiệu chuẩn. Không dùng "điểm tổng" thay điều kiện bắt buộc.
File: `core/continuity_state.py` (mới, mỏng), `ImageRunner._pregen`, `core/final_qc.py`, `core/qc_golden.py`. Chi phí QC model trên
benchmark: ước tính trước, xin duyệt. Điểm dừng: duyệt bộ nhãn benchmark.

### A.7 P5 — Sửa có chọn lọc (V2.1 §7.F, §14.5)

| Mã lỗi | Tầng sửa | Nguồn phát hiện |
|---|---|---|
| SCHEMA_INVALID | BYĐ (Đạo diễn sửa ≤ 2 vòng) | `shot_intent.validate` |
| ASSET_ID_MISMATCH | Kho (không gen) | validate `kho_id`, A2e |
| CHARACTER_IDENTITY_DRIFT | ảnh (ref/khóa) → gen lại ảnh | qc_scene / qc_team |
| PROP_MISSING | ref đạo cụ → ảnh | `qc_observe set_match`, A2b |
| ACTION_NOT_COMPLETED | video (khung cuối / motion) | video QC vs `hanh_dong.ket_thuc` |
| CONTINUITY_CONFLICT | state → shot phụ thuộc | D |
| AUDIO_SYNC_ERROR | âm thanh / khớp môi | `clip_measure`, `final_qc` |
| ENCODE_ERROR | dựng (0 USD) | ffprobe / `final_qc` |

Lưu vết bằng `jobs` (`parent_job_id`, `retry_count`, `retry_reason`, `input_hash`, `sent_package`) — không thêm bảng artifact; chống
retry trùng bằng `send_claim` + so `input_hash` ("gen lại phải đổi đầu vào"); trần `qc_policy.max_retry` + `projects.max_retry_count` +
`spend_gate`; sửa làm đổi ý đồ → dừng chờ người; rebuild theo `lineage.stale_scene_ids`, bản cũ vào `trash`. Chỉ cho tự sửa từng nhóm lỗi đã
chứng minh. File: `core/repair_router.py` (mới), `core/regen.py`, `core/qc_policy.py`. Cờ TẮT mặc định.

### A.8 Quyết định Q1–Q6 (V2.1 §4, §14.6)

| Q | Nội dung | Khuyến nghị | Trạng thái |
|---|---|---|---|
| Q1 | Làm golden (B) trước BYĐ (A)? | B trước A; B1 chỉ sau khi xác minh HEAD + cờ máy chính | đề xuất |
| Q2 | Giờ/thời tiết lấy ở shot? | trường shot là nguồn chuẩn, trigger đồng bộ bản chép `byd.noi_chon` | đề xuất; kiểm trigger |
| Q3 | Tách outfit/hair/face? | trong `assets.profile` + `forms[]`; soạn nháp bằng Claude sau duyệt chi phí | chờ duyệt |
| Q4 | #24/#27 làm baseline? | #27 (không BYĐ), #24 (BYĐ v1) chỉ hồi quy đường cũ; backfill #24 sau khi #31 + v2 qua test | đề xuất |
| Q5 | Đồng bộ thay đổi phiên khác (trigger + POV)? | đã gộp; xác minh 18/10 trên `186a2cc9` | **đã xác minh** |
| Q6 | Siết 3 cổng | (a)(b)(c) như A.5, kèm bảng `overrides` | (c) chờ xác nhận quy tắc "nhân vật chính" |

Câu hỏi còn mở từ V2.1 §12 (gộp vào V3 §5): duyệt kiến trúc + cho phép P1; Q3 + chi ≈ 0,05 USD; Q6(c) áp cho mọi nhân vật hay chỉ nhân vật
chính; migration `overrides` hay chỉ mở rộng `video_gate_skips`; Premiere trong phạm vi hay không; cho phép chụp fixture chỉ đọc ở máy chính.

### A.9 Rủi ro R1–R10 (V2.1 §9) — R11–R15 ở §7

| # | Rủi ro | Giảm thiểu |
|---|---|---|
| R1 | Fixture chụp trên HEAD/cờ khác production | xác minh HEAD, snapshot cờ + trigger trước B1 |
| R2 | Cờ máy chính ≠ cờ test (bài học 16/10) | capture đọc cờ thật, ghi vào fixture |
| R3 | `qc_observe` raise khi `vat` là chuỗi — **đang xảy ra** | sửa parser v1 `str → {vat}` sớm (nhỏ, tách khỏi P2, cần duyệt + quy ước 7) |
| R4 | Sửa BYĐ không làm ảnh "cũ" | `byd` vào `lineage` có điều kiện |
| R5 | Đụng file với phiên khác / sửa trên mốc cũ | kiểm HEAD; mỗi bước một commit; quy ước 7 |
| R6 | Golden bị coi là "đúng" | tách compat ↔ correctness |
| R7 | Siết cổng làm kẹt sản xuất | override có audit; (c) có tick lý do |
| R8 | Trigger đổi format JSON `scenes.data` → diff golden giả | chuẩn hóa JSON khi so (sort_keys) |
| R9 | Benchmark QC nhỏ, nhãn lệch | `independent_set`; ghi độ tin cậy chưa hiệu chuẩn |
| R10 | Chi phí ẩn (Đạo diễn v2, Q3, benchmark) | ước tính trước + sổ chi + xin duyệt từng bước |

### A.10 Nghiệm thu, rollback và ranh giới duyệt (V2.1 §10, §14.5, §14.7)

| Mục | Nghiệm thu | Rollback |
|---|---|---|
| Compatibility | cờ máy chính, `byd_fields` TẮT → #24/#27/#31 giống fixture từng byte (prompt + refs + sha + model) | revert commit |
| Correctness | mọi lỗi đã biết hết xfail khi `byd_fields` BẬT | tắt cờ con |
| BYĐ v2 | v1/thiếu → đường cũ + diag `byd_fallback` (> 0 khi chạy #24) | tắt `byd_fields` |
| Thẻ gói | khớp `replay_payload` và `jobs.sent_package` | ẩn thẻ |
| Override | 100 % lần vượt cổng có người / giờ / lý do / mã / snapshot | bảng để nguyên, UI cũ |
| KPI | lỗi lọt cổng do chữ tự do −50 %; #31 shot trái trường = 0 | — |
| Chung | không lời gọi tốn tiền ngoài sổ chi; "đã sửa" có bằng chứng chạy thật | — |

**Ranh giới duyệt:** duyệt tài liệu ≠ duyệt code hay chi phí. Duyệt V3 chỉ mở P0.5 + P1 (B0–B2); P2–P5 là thiết kế, duyệt riêng từng phase.
P1 không gọi API có phí, không migration, không sửa dữ liệu production. P2: Q3 duyệt cấu trúc + bảng chuyển đổi trước khi ghi. P3:
migration có up/down. P4: thiết kế + benchmark trước, không bật QC ngữ nghĩa chặn production. P5: chỉ tự sửa nhóm lỗi đã chứng minh, không tự
sửa BYĐ làm đổi ý đồ.

**Checklist trước khi giao phiên code:** [x] xác minh HEAD + Q5 (18/10); [x] xác minh cờ máy chính, dữ liệu, trigger, schema (18/10; chụp lại
lúc capture); [ ] chốt phạm vi P1 + quyền chỉ đọc; [ ] chốt parser/test `vat[]` trước khi bật consumer mới; [ ] duyệt Q3, Q6(c), migration
và chi phí theo phase; [ ] không làm P2–P5 khi mới duyệt P1.
