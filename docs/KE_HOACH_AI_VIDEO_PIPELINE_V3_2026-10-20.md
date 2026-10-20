# Kế hoạch AI Video Pipeline V3 — bản hợp nhất từ V2.1 (R2 + phụ lục R3) — 20/10/2026

> **Trạng thái: KẾ HOẠCH, CHƯA DUYỆT, CHƯA TRIỂN KHAI. 0 USD.** Không trùng với `docs/KE_HOACH_V3_CHINH_THUC.md` (kế hoạch v3 cũ 23/09 về phân
> shot / Director — đã xong, chỉ còn giá trị lịch sử). Bản này hợp nhất ba tài liệu, giữ chúng làm bằng chứng chi tiết:
> - **KH-gốc** `docs/KE_HOACH_TRUONG_CAU_TRUC_VA_HOI_QUY_GOI_2026-10.md` (17/10): ý shot thành trường cấu trúc + hồi quy trên gói thật.
> - **V2.1 R2** `docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md` §1–§14 (17–18/10): audit, D/E/F, phụ lục R2.
> - **V2.1 §15** (phụ lục R3, 20/10): lỗi #31 / #33 chưa có kế hoạch, nhóm N1–N7 có file:dòng.
>
> Mốc code: `main` = `3ecf053b`. Mọi file:dòng ở V2.1 §13 / §15 — mở lại file trước khi sửa.

## 1. Vì sao có V3

- V2.1 viết trước khi #31 phát sinh G26–G50 (19/10) và trước #33 (19–20/10). Rà lại: V2.1 chỉ che ≈ 1/4 lỗi #31 và **không che lỗi nào của #33**.
- Ba nhóm lỗi lặp ở **cả hai** dự án mà V2.1 không có: (1) vận hành Claude / tiến trình / tạm dừng, (2) ước tính giá sai, (3) vị trí vật
  và hình học 3D xuyên shot. Hai nhóm đầu đã gây trả tiền thừa thật.
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
| **P0.5 (mới)** | **N1 vận hành:** A1 khóa poll/succeed theo job, A3 `clean_env` bỏ key API, G36 kiểm tạm dừng trước `submit`, G39 kiểm `data_dir`, A2 provider Claude theo dự án, G30 đếm Kho chủ thể. **N2 giá:** A7 phụ phí ref + giá nâng 1080p + hệ số từ sổ chi, A8 tier nháp, A9 Claude = 0 khi `claude_cli` + giá video trong `pregen_check` | V2.1 §15.2 N1, N2 | không (độc lập BYĐ) | 0 USD (provider giả) | sau mỗi nhóm: test + quy ước 7 |
| **P1** | Golden gói: B0 dò đường mở ảnh, B1 chụp (ảnh + **video**), B2 test Compatibility / Correctness. Correctness thêm ca thật #31 (G27, G13) và #33 | V2.1 §6.B, §14.1 | baseline đã xác minh 18/10; chụp lại cờ ở máy chính | 0 | duyệt phạm vi chỉ đọc |
| **P2** | BYĐ v2 (A0–A3): `byd_v`, `vat[]` schema + parser v1/v2 (sửa luôn lỗi ngầm `qc_observe`), Q2 trigger, Q3 `forms[]` trong `assets.profile` (+G38), field readers A2a–A2f, `byd` vào `lineage`. **Kèm N5:** `insert_scene_after` chép bối cảnh + BYĐ (G6, G21); **G1** chỉ mang đạo cụ có trong BYĐ; **A4** `locks.guard` cho mọi đường Claude ghi `scenes.data` (VÀNG trước, chặn sau) | V2.1 §6.A, §14.2, §15.2 N5 | P1 | Q3 ≈ 0,05 USD (xin duyệt) | Q3, mỗi cờ con |
| **P3** | Dashboard: thẻ "Gói sẽ gửi" (so `sent_package`; sửa G5 khóa theo đường dẫn đầy đủ), BYĐ trên Dashboard, siết 3 cổng Q6 + bảng `overrides`, chỉ số C (cost/accepted shot, retry cost, override rate). **Kèm N6:** G15–G17 | V2.1 §6.C, §15.2 N6 | P2 | 0 | migration `overrides` |
| **P4** | **D + N3 gộp:** sơ đồ mặt bằng theo cảnh thành dữ liệu (`stage_facts`) làm Expected state vị trí; người nộm tỉ lệ (G2); góc `slightly_high` + `eye` ≤ 5° + kiểm `depth.png` (G3, A10, G49); bỏ khóa chân trời khi nền không có trời (G20). **E + N4/N7:** image preflight, mã lỗi, clip đứng yên > 1,5 s, `qc_sequence_logic`, cross-shot (G42), luật router không gộp nhóm khi cần khung đầu (G28, G37, B9), độ dài gói nhóm (G13), cắt cảnh trong video ref (B8), A5, A6, G14 | V2.1 §7.D/E, §14.3, §14.4, §15.2 N3/N4/N7 | P2 | render 0 USD; gen thử ảnh chứng minh N3 — xin duyệt | benchmark §14.4 trước khi cho chặn |
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
| 6 | Q3, Q6(c), migration `overrides`, Premiere | như V2.1 §14.6 |

## 6. Tồn đọng: thay nền video (người dùng 20/10, "có thể update sau")

**Yêu cầu:** người dùng gửi một video quay người thật + (mô tả nền bằng chữ **hoặc** ảnh ref nền) → hệ thống trả video cùng người, cùng
động tác, nền mới. Ví dụ thành quả người dùng gửi: `E:/Tai xuong/cgt-20261020000346-zyeku_202610192303.mp4` (9,7 s, 1080×1920, 24 fps): người
nhảy giữ nguyên mặt, áo, động tác; nền thành vườn hoa hồng hoàng hôn, ngược sáng khớp viền tóc, nền chuyển động theo máy.
Cách làm gốc nằm trong một cuộc trò chuyện ChatGPT người dùng chỉ ra — **CHƯA ĐỌC ĐƯỢC** (link cần đăng nhập). Bổ sung kỹ thuật
khi có nội dung.

**Phác thảo (chờ xác nhận bằng cuộc trò chuyện):**
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
