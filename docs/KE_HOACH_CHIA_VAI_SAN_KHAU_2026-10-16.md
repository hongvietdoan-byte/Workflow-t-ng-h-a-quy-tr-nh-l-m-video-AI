# Kế hoạch chia vai khâu Sân khấu 3D — Đạo diễn dàn cảnh / Quay phim đặt máy + tự sửa theo số đo / Đạo diễn duyệt chốt

Ngày 16/10/2026 · trạng thái: **CHỜ người dùng duyệt** (chưa code, chưa cờ, chưa gọi API) · ca thử: shot 10 cảnh 3 #31 (0 USD, ngoại tuyến)

## 1. Vì sao

**Ca gốc: shot 10 #31** (lượt đã ghi `data/projects/31/stage/kho265/doan_3/cc_20261016_101134`, bộ kiểm cho ĐẠT):

| | Ghi chú khung của Quay phim (Tầng B) | Số đo Blender (K4) |
|---|---|---|
| Khung | cận thấp, xe nôi giữa khung, chỉ **tay** Kelly ở mép phải | ống 65 mm cách xe nôi 1,9 m → xe nôi (1 m) ≈ 93 % chiều cao khung — một mảng thành xe |
| Kelly | chỉ thấy tay | Kelly đứng GIỮA máy và xe nôi (cách máy 1,35 m) → thân Kelly 237 % khung, 2/3 ảnh clay là thân cam |
| Góc | nhìn **lên** xe nôi | máy cao 0,85 m, **chúc xuống 6,5°** (đặc tả máy ghi `do_cao: thap`, không ghi `goc: ngua`) |

Gốc không nằm ở việc thiếu luật cấm. Nó nằm ở việc **khâu sân khấu không có vai Quay phim**:
- `prompts/29_director_stage_specs.md` mở đầu bằng "Bạn là Đạo diễn kiêm Quay phim": một câu trả lời gồm cả `blocking` (dàn cảnh) lẫn `shot_specs` (cỡ, độ cao, góc, vùng khung).
- `core/stage_director.build_prompt` chỉ nạp bài học #24 (`knowledge.p24_blocks`), không nạp bộ nguyên tắc Quay phim (`knowledge/roles/dp.md`).
- Ghi chú khung do Quay phim viết ở Tầng B (`core/director_two_pass.py`, prompt 20) bị đưa vào đề bài với nhãn "chỉ để hiểu ý, KHÔNG phải luật". Sau K4, phản hồi số đo (`feedback_from`, `post_checks`) quay về Đạo diễn. Không ai so khung đo được với ý đồ của người đã viết ghi chú.
- Quyết định tổ làm phim (25/09): Đạo diễn quan sát, tư vấn, duyệt chốt; **Quay phim lo góc máy, bố cục, coverage**. Khâu sân khấu đang làm ngược quyết định này.

**Không đặt luật cấm cứng** (vd "vật phụ không được to quá khung"). Theo memory `feedback_craft_no_fixed_meaning` và `feedback_no_rules_from_comments`, che khung để chuyển cảnh, tiền cảnh, qua vai… đều là ý đồ hợp lệ. Cách đúng là **khai ý đồ trước, đo xong so với ý đồ đã khai**. Người khai được giữ lệch nếu có lý do.

## 2. Luồng mới (sau cờ `stage_crew`, mặc định TẮT)

```
K1 sàn (như cũ)
 → [A] ĐẠO DIỄN — dàn cảnh: blocking theo nhịp + ý đồ từng nhịp            (đề bài 29a)
 → cổng 0 USD: bộ kiểm blocking (phần blocking của validate_answer + script_rules về người/nhịp)
 → [B] QUAY PHIM — đặt máy: shot_specs + ý đồ từng thành phần             (đề bài 29b, nạp dp.md)
 → cổng 0 USD: bộ kiểm shot_specs (ss.validate, move_errors, k3_frame_errors)
 → K3 giải máy + K4 Blender đo + draw_beats / clay (như cũ, 0 USD)
 → code lập BẢNG ĐỐI CHIẾU "đã khai ↔ đo được" từng shot (sự thật, không phán)
 → [C] QUAY PHIM tự duyệt (≤ 2 lượt): mỗi shot `khop` / `sua_may` (đổi shot_specs) / `de_nghi_doi_cho` (gửi Đạo diễn) /
       `giu_lech` (+ lý do)
 → (có đề nghị) [A'] ĐẠO DIỄN trả lời đề nghị: dời người (sửa beats) hoặc giữ (+ lý do) → về K3/K4 cho shot liên quan
 → [D] ĐẠO DIỄN duyệt chốt: xem top_beats + clay + bảng đối chiếu + các `giu_lech` → `duyet` / `tra_lai` (≤ 1 lần với Đạo diễn API; NGƯỜI DÙNG trả lại không giới hạn — sửa 16/10)
 → ghi stage_camera (apply như cũ)
```

### 2.1 Phân vai và quyền

| Vai | Viết | Không được |
|---|---|---|
| Đạo diễn (A, A', D) | `blocking`: objects, beats (`at`, `den`, `H`, `tu_the`, `facing`, `hidden`), `axis`, `s0`; mỗi nhịp `_ly_do` + `y_do` (người xem cần thấy/cảm gì) | ghi cỡ / góc / độ cao máy |
| Quay phim (B, C) | `shot_specs`: `co`, `do_cao`, `goc`, `cao_m`, `may`, `pov`, `thanh_phan` (vai, vùng, `co_pct`, `thay`, `thay_min`), `cross_ok` + `y_do_khung` từng thành phần | dời người / đạo cụ (chỉ **đề nghị** kèm lý do + gợi ý chỗ) |

- Ghi chú khung Tầng B là **ý đồ của chính Quay phim**, nên ở bước B nó đóng vai bản phác đầu, không phải luật. Quay phim được đổi, nhưng phải ghi lý do vào `y_do_khung` (vd "đổi sang MCU vì máy cận 65 mm không chứa được xe nôi + tay").
- Mỗi thành phần có thể khai **ý đồ che / lệch có chủ ý**: `"che": "chuyen_canh" | "tien_canh" | "qua_vai" | "khac"` + `"ly_do"`. Khai rồi thì số đo lệch không bị coi là lỗi.

### 2.2 Bảng đối chiếu (code tính, 0 USD), mỗi shot

Chỉ liệt kê **sự thật số**, không phán đúng sai. Quay phim đọc và tự kết luận:

- cỡ khai (`co`, `co_pct`) ↔ `size_pct` đo được của từng thành phần (cả vai `phu`);
- `seen_pct` từng thành phần ↔ `thay_min` / vai;
- `goc` khai (hoặc chữ "nhìn lên / nhìn xuống / ngang" trong `muc_dich`, `y_do_khung`) ↔ `pitch` đo được;
- `do_cao` / `cao_m` ↔ `cam_above_floor_m`;
- vật nào **chắn đường nhìn** tới thành phần `chinh` (vật gần máy hơn và chiếm vùng của vật chính trên khung) + khoảng cách;
- máy shot liền nhau trùng (`post_checks` hiện có);
- `che` đã khai → ghi "đã khai: <ý đồ>".

Shot 10 cũ sẽ ra: "Kelly (phu) 237 % khung, chắn xe nôi; khai `goc` trống, mục đích 'nhìn lên', pitch −6,5°; xe nôi 93 % khung với CU". Quay phim tự thấy lệch so với ý đồ của mình.

### 2.3 Quay phim duyệt (C): định dạng trả lời

```json
{"shots": [
  {"shot": 10, "ket_luan": "sua_may", "ly_do": "...", "shot_spec": {...spec mới...}},
  {"shot": 11, "ket_luan": "khop"},
  {"shot": 12, "ket_luan": "giu_lech", "ly_do": "Kelly che nửa khung để chuyển sang shot 13 (che máy trong chuyển động)"},
  {"shot": 13, "ket_luan": "de_nghi_doi_cho", "nhip": "nhip_13", "vat": "kelly", "goi_y_at": [x, y], "ly_do": "..."}
]}
```

- Gửi kèm **ảnh clay** từng shot khi lệch (ngoại tuyến: phiên Claude Code đọc ảnh; API: chỉ gửi ảnh của shot có lệch, cỡ nhỏ, để giới hạn token ảnh).
- Còn lệch sau 2 lượt và không `giu_lech` → shot không có máy sân khấu, báo ĐỎ như hiện nay (máy nền thường). Không tự nới.

### 2.4 Đạo diễn duyệt chốt (D)

- Xem: `top_beats.png` + clay từng shot + bảng đối chiếu + danh sách `giu_lech` / đề nghị đã từ chối.
- `duyet` → ghi máy. `tra_lai` (Đạo diễn: một lần; người dùng: bao nhiêu lần cũng được, chưa ghi/gỡ máy CSDL tới khi `--crew-approve`) kèm ý đồ cần đổi → quay lại A' hoặc B cho đúng shot đó.
- Ở chế độ người dùng duyệt qua chat (`decision_tap2_drafts_approved_in_chat`), bước D có thể nhường cho người dùng xem ảnh ghép `--beats`. Cờ con `stage_crew_user_approve`.

## 3. Thay đổi code (dự kiến)

| Tệp | Việc |
|---|---|
| `prompts/29a_director_blocking.md` (mới) | Cách nghĩ dàn cảnh: lấy mục 2 (nhịp, động cơ), 6 (vật chắn), 9 (trục) của prompt 29; bỏ phần khung |
| `prompts/29b_dp_stage_specs.md` (mới) | Cách nghĩ đặt máy: mục 3–5, 7–8, 10 của prompt 29 + nạp `knowledge/roles/dp.md` (+ `p24_blocks`) + định dạng `y_do_khung` / `che` |
| `prompts/29c_dp_stage_review.md` (mới) | Đọc bảng đối chiếu + clay → `khop` / `sua_may` / `de_nghi_doi_cho` / `giu_lech` |
| `prompts/29d_director_stage_approve.md` (mới) | Duyệt chốt |
| `core/stage_director.py` | Tách `validate_answer` → `validate_blocking` + `validate_specs` (giữ hàm cũ gọi cả hai cho luồng cũ); `build_prompt_role(role, …)`; `compare_table(inputs, specs, v2)` (mục 2.2) |
| `core/stage_auto.py` | `run_segment_crew` (luồng mục 2, sổ chi theo từng vai: `director_stage_blocking`, `dp_stage_specs`, `dp_stage_review`, `director_stage_approve`); ngoại tuyến: `offline_prompt/answer` nhận `role` |
| `tools/stage_auto.py` | `--role dao_dien|quay_phim|quay_phim_duyet|duyet` cho `--prompt-out` / `--answer` |
| `core/features.py` | cờ `stage_crew` (TẮT; cần `stage_auto`), cờ con `stage_crew_user_approve` |
| `core/llm_runner` / `STAGE_SETTINGS` | max_tokens riêng cho 4 khâu mới (memory `reference_stage_max_tokens_vs_caps`) |
| `tests/test_stage_crew.py` (mới) | Tách/ghép đúng; bảng đối chiếu ra đúng số shot 10 cũ; `giu_lech` có lý do thì không bị giữ; đề nghị dời người → chỉ chạy lại shot liên quan; cờ TẮT → luồng cũ y nguyên |

Giữ nguyên: K1, K3, K4, `cameras_from`, `apply`, `post_checks` (thành một nguồn của bảng đối chiếu), `draw_beats`. Luồng cũ (một vai) vẫn chạy khi cờ TẮT.

## 4. Chi phí

- **Ngoại tuyến (đang dùng cho #31): 0 USD.** Phiên Claude Code lần lượt đóng 4 vai; Blender cục bộ.
- **API:** mỗi cảnh ≈ 1 (A) + 1 (B) + 1–2 (C) + 0–1 (A') + 1 (D) = 4–6 lời gọi, thay vì 1–2 hiện nay. Mỗi lời gọi có đề bài nhỏ hơn và phần chung được cache. Con số thật lấy bằng `cost.llm_estimate` trên đề bài thật của #31 (0 USD) **trước khi** bật cho dự án nào. Cờ TẮT cho tới khi người dùng duyệt số.

## 5. Ca thử — shot 10 cảnh 3 #31 (0 USD)

1. Dựng đề bài A/B thật của cảnh 3 #31 (shot 10–13) bằng `--prompt-out --role …`. Kiểm nội dung đề bài (ghi chú khung Tầng B có trong đề bài B, `dp.md` có, đề bài A không có phần khung).
2. Phiên Claude Code làm Đạo diễn (A) → Quay phim (B) → K3/K4 → Quay phim duyệt (C) → Đạo diễn duyệt (D). Lưu từng câu trả lời vào `cc_*/` như hiện nay.
3. **Đạt khi:**
   - shot 10: xe nôi đọc được là xe nôi (thứ chính, không cắt mất hình dạng); Kelly chỉ là tay/cẳng tay ở mép phải; máy **ngửa** (pitch > 0), hoặc Quay phim ghi lý do khác;
   - shot 11–13 không xấu đi so với lượt cũ (bảng đối chiếu + `--beats` so trước/sau);
   - bảng đối chiếu của **lượt cũ** bắt được cả ba lệch của shot 10 (kiểm cơ chế, không chỉ kết quả).
4. Gửi người dùng ảnh ghép trước/sau (`--beats`) để duyệt. Người dùng duyệt thì ghi `stage_camera` cảnh 3.
5. Không ổn thì sửa đề bài/vai rồi thử lại trên cùng ca, không mở rộng.

## 6. Thứ tự làm + điểm dừng

1. **Người dùng duyệt kế hoạch này** (hiện tại).
2. Code mục 3 + test, cờ TẮT → rà quy ước 7 (agent) → cả bộ test → commit/push.
3. Ca thử mục 5 (ngoại tuyến, 0 USD) → gửi ảnh → **dừng chờ người dùng duyệt**.
4. Chạy lại 7 cảnh còn lại của #31 bằng luồng mới (0 USD) → gửi ảnh ghép → duyệt.
5. Đo chi phí API (mục 4) → người dùng quyết có bật `stage_crew` ở chế độ API không.

## 7. Câu hỏi cho người dùng

1. Bước D (Đạo diễn duyệt chốt) cho #31: để vai Đạo diễn (Claude) duyệt, hay **bạn** duyệt qua ảnh ghép như hiện nay?
2. Quay phim được **đề nghị** dời người. Nếu Đạo diễn từ chối thì Quay phim phải làm với chỗ đứng đó (hoặc `giu_lech`). Đồng ý thứ tự ưu tiên này (Đạo diễn thắng) không?
3. Chế độ API (sau #31): chấp nhận 4–6 lời gọi/cảnh nếu số đo cho thấy ít phải chạy lại hơn?

## Bổ sung 16/10 — đạo cụ cầm tay theo nhịp (cờ `stage_handheld_props`, mặc định TẮT)
Gốc: #31 cảnh 3 súng SKORP hiện ra ở xe nôi rồi nằm trong tay Kelly — vũ khí Kho bị bỏ khỏi dàn cảnh nên "thấy rõ súng" không đo được.
- Cờ bật: vũ khí Kho của shot (có `height_m` + `width_m` ở Kho) vào danh sách vật cố định như đạo cụ `cam_duoc`; thiếu cỡ → ghi chú
  "không đo được" trong đề bài (không chặn cả cảnh). Đạo diễn: `hidden` ở nhịp chưa xuất hiện, `at` (+ `z`) khi nằm đâu đó,
  `cam_tay: <người>` + `tay: phai|trai|hai_tay` khi trong tay (người phải có `facing`; nằm / ngã ngửa → đặt bằng `at`).
- Điểm tay (core/stage_solver.hand_point, ƯỚC TÍNH chưa đo Pose): cao 0,55 / 0,46 / 0,45 / 0,3 × H của nhịp (đứng / quỳ / ngồi / bò),
  ra trước 0,3 m, lệch bên 0,2 m. Một nguồn cho bộ giải + Blender K4.
- Blender: mỗi chỗ một khối `PROP_<KHÓA>_V<n>` ẩn/hiện theo nhịp; luật P2 không tính đồ cầm tay là vật chắn; không vẽ vào ảnh nền
  (`stage_camera.props`), không mang sang cảnh sau.
- Hạn chế: khối là trụ đứng đường kính = bề rộng Kho (súng: bề dài) → to hơn súng thật, % thấy là ước lượng; súng không bám theo
  người đang di chuyển (`den`) trong shot — khối đứng ở chỗ đầu nhịp.
- Thử 0 USD (bản sao CSDL, SKORP tạm cao 0,25 / dài 0,55 m chỉ ở bản sao): dàn cảnh đã duyệt cảnh 3 + súng → shot 12 thấy súng 53 %,
  shot 13 20 %, shot 11 0 % (đầu shot súng còn trong xe nôi — đúng); P2 shot 12 trước khi sửa coi súng là vật chắn 20,7 % khung.
