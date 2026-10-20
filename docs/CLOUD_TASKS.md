# Việc chạy trên Claude Code cloud (tài khoản credit $100) — 06/10/2026

Người dùng có một tài khoản **Cloud session credits $100** (hết hạn 05/11/2026, 14:59 GMT+7). File này chứa prompt tự đủ để dán vào phiên cloud ở **claude.ai/code** (repo `hongvietdoan-byte/Workflow-t-ng-h-a-quy-tr-nh-l-m-video-AI`). Phiên chính ở máy `D:\AI-Video-Pipeline` rà + chạy cả bộ test (Windows) rồi mới gộp vào `main`.

## Cloud làm được / không làm được
- **Được:** code + test thuần trong git, tài liệu, chạy test liên quan trên Linux, commit + push nhánh riêng.
- **Không:** `data/`, `data/manifest.sqlite`, `dashboard.env`, khóa ClipAI / Claude API, Blender, PowerShell, Dashboard thật, dữ liệu `devsys/data` của máy chính. Không chạy gì tốn tiền API.
- Test chỉ chạy trên Windows (đường dẫn `D:\`, PowerShell) có thể bỏ qua/đỏ trên Linux → ghi rõ trong báo cáo, KHÔNG sửa test cho xanh trên Linux nếu làm hỏng trên Windows.

## Ngân sách credit — dừng cứng $90, không vượt 95 $ (hết credit = không commit/push được → mất việc)
| Credit đã dùng (của $100) | Làm gì | Hỏi người dùng số credit |
|---|---|---|
| < $60 | chạy bình thường, 1 việc/phiên | trước mỗi việc + mỗi ~30 lượt gọi |
| $60–80 | chỉ việc nhỏ hoặc tiếp việc đang dở; commit + push sau MỖI bước | mỗi ~20 lượt gọi |
| $80–85 | không mở bước mới lớn; làm bước nhỏ đang dở | **mỗi ~10–15 lượt gọi** |
| $85–90 | chỉ hoàn tất bước đang dở → commit, push, cập nhật `HANDOFF.md`, báo cáo | **mỗi ~5–10 lượt gọi** |
| **≥ $90** | **dừng cứng** (người dùng chọn 06/10 để luyện kiểm soát chặt) — không chạy thêm gì; TUYỆT ĐỐI không vượt 95 $ | — |

- Phiên cloud **không tự đọc được số credit** → người dùng xem ở trang credit và báo trong chat ("đã dùng $X"); phiên cloud hỏi người dùng số credit **trước khi bắt đầu mỗi việc** và **sau mỗi ~30 lượt gọi công cụ**.
- Ước chi mỗi việc (Opus, ước theo token, có thể lệch): việc vừa ≈ $8–15, việc lớn ≈ $15–25. Chưa chắc đủ → làm phần nhỏ trước.
- **Commit + `git push` sau MỖI commit** (không gom cuối phiên), `HANDOFF.md` ở gốc nhánh luôn ghi: đã xong / đang dở / bước kế. Hết credit giữa chừng vẫn còn việc trên GitHub để làm tiếp.
- Một phiên cloud = một việc. Không mở phiên con (Agent) trong cloud — tốn gấp đôi.

## Luật chung (dán kèm mọi prompt)
```
Luật dự án (bắt buộc):
- Trả lời/ghi chú tiếng Việt. Đọc CLAUDE.md + docs/CHUAN_XAY_DUNG.md trước (không im lặng khi thiếu đầu vào; "đã sửa" kèm bằng chứng chạy thật).
- HỘP THƯ: nhận việc / báo / hỏi qua mục 📨 đầu TODO.md trên main (luật "LUẬT HỘP THƯ CHUNG" ở đó; tên làn `cloud-B`) — ngoại lệ duy nhất được push main: commit CHỈ đổi dòng hộp thư (`hộp thư: …`), pull --ff-only trước, không force.
- Làm trên nhánh mới `cloud/<mã-việc>` tách từ main. KHÔNG push lên main (trừ commit hộp thư), KHÔNG sửa phần khác của TODO.md / trạng thái kế hoạch, KHÔNG tăng devsys/areas.json "version" (file mã mới vẫn phải khai vào areas.json).
- KHÔNG gọi API tốn tiền (Claude/ClipAI/TTS…) — chỉ mock. Không có data/ máy chính: dùng fixture trong tests/.
- Test ĐỎ TRƯỚC, XANH SAU cho từng mục; chỉ chạy test liên quan: `python -m pytest -q -p no:cacheprovider tests/<file>.py` (Linux dùng python3; PYTHONUTF8=1).
- Commit nhỏ, dòng cuối: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; `git push -u origin <nhánh>` NGAY sau mỗi commit; cập nhật HANDOFF.md (đã xong / đang dở / bước kế) mỗi commit; xóa HANDOFF.md ở commit cuối khi xong hẳn.
- Credit (dừng cứng $90): hỏi người dùng "đã dùng bao nhiêu $" trước khi bắt đầu, rồi mỗi ~30 lượt gọi (< $60) / ~20 ($60–80) / ~10–15 ($80–85) / ~5–10 ($85–90); từ $85 chỉ hoàn tất bước đang dở rồi commit + push + HANDOFF; ≥ $90 dừng hẳn, không vượt 95 $. Ghi số credit vào HANDOFF.md mỗi lần hỏi. Không mở phiên con (Agent).
- Tự kiểm trước bàn giao: test bị nới để che lỗi; đường dẫn tương đối / phụ thuộc thư mục đang chạy; chặn mới làm vỡ luồng tự động/hàng loạt; bật mặc định đổi hành vi; so chữ bỏ dấu khớp nhầm từ ngắn; tiêu đề/nhãn đọc nhầm thành nội dung; lời gọi tốn tiền chạy khi chưa có đồng ý.
- Kết thúc: báo cáo ≤ 25 dòng: nhánh, commit cuối, file sửa, test đỏ→xanh (tên), test bỏ qua vì Linux, rủi ro/việc mở.
```

---

## Việc 1 — S14.45 Bảng chấm hiệu quả quy trình (AI Dev System) · ≈ $10–15
```
Việc S14.45 của dự án (đọc dòng "S14.45 ·" trong docs/KE_HOACH_SUA_SAU_DU_AN_8.md và mục 2b của .claude/skills/vong-lam-viec-theo-plan/SKILL.md).
Mục tiêu: AI Dev System (devsys/ + tools/devsys_*.py + trang web devsys) ghi và hiển thị hiệu quả token của quy trình nhiều phiên.
1. Dữ liệu trong git: file `devsys/workflow_runs.json` (hoặc .jsonl) — mỗi dòng: mã việc (S14.x), ngày, chế độ tài khoản (goi | usd | cloud), mức rà (ky | nhe), token làm / rà / sửa (nghìn), số vòng sửa, số lỗi rà bắt (tổng + nặng), ghi chú. Lệnh `python -m devsys.workflow add …` để ghi (skill sẽ gọi sau mỗi nhánh gộp) + `list`.
2. Nhập lại từ kế hoạch: đọc các dòng "Số đo: …" trong docs/KE_HOACH_SUA_SAU_DU_AN_8.md (dạng "làm ≈ 233k + sửa ≈ 257k token, rà ≈ 138k (≈ 28 %), rà bắt 5 lỗi", "làm ≈ 252 nghìn token, rà ≈ 123 nghìn", "rà 0"…) → parser chịu được các biến thể (k / nghìn, có/không "sửa"); dòng không đọc được → liệt kê, KHÔNG im lặng bỏ.
3. Trang web devsys "Hiệu quả quy trình": bảng từng nhánh + tổng theo ngày/chế độ; so với 2 mốc ghi sẵn: mốc A 04–05/10 (7 nhánh, làm ≈ 2,0 triệu, rà ≈ 1,1 triệu ≈ 35 %, ≈ 443k/nhánh, rà bắt 1–3 lỗi/nhánh); mốc B 05–06/10 (rà kỹ ≈ 653k/nhánh, rà ≈ 20 %, sửa ≈ 48 %, 5,2 lỗi/nhánh; rà nhẹ ≈ 124k/nhánh). Chỉ số: token/nhánh (rà kỹ vs nhẹ), % rà, % sửa, token rà / lỗi bắt, số vòng sửa. Làm theo cách các trang devsys hiện có dựng (tìm trang "Hiệu quả vận hành" Đợt 6b làm mẫu).
4. Test: parser trên các dòng "Số đo" thật (chép vài dòng làm fixture), add/list, trang hiển thị (theo cách test trang devsys hiện có).
```

## Việc 2 — S14.24 Agent chấm bài học (CHẾ ĐỘ BÓNG) · ≈ $15–25
```
Việc S14.24 của dự án: Đợt 5 "Agent chấm bài học" — đọc mục "## Đợt 5 — Agent chấm bài học (ý 2)" trong docs/KE_HOACH_BO_NAO_PROMPT_TU_HOC_2026-10-04.md (≈ dòng 344–440: core/lesson_judge.py ~260 dòng, facts(), build_prompt(), normalize(), judge(), judge_all(), estimate(), MockJudge, rubric 6 tiêu chí, 8 van về người, chống trôi knowledge) và dòng "S14.24 ·" trong docs/KE_HOACH_SUA_SAU_DU_AN_8.md.
Làm ĐÚNG CHẾ ĐỘ BÓNG: chấm nhưng KHÔNG đổi bài học/knowledge nào, chỉ ghi kết quả để người xem; sau cờ mới TẮT mặc định (theo mẫu core/features.py). Lời gọi Claude thật phải đi qua sổ chi + ước tính trước (tìm llm_runner / spend_cap / STAGE_SETTINGS — khâu Claude mới cần max_tokens riêng trong STAGE_SETTINGS); trên cloud chỉ chạy MockJudge.
Lưu ý S14.46 (đang làm ở máy chính): bài học về tính năng đã bỏ (phông xanh / location_plates, layout_to_model, chain_previous_auto, setcheck_autofix, seedance_sample_mode) sẽ bị cất — van "chủ đề đã bỏ" để agent chấm coi là KHÔNG dùng; không đụng code lọc của S14.46 (core/lessons.py phần lọc) — chỉ đọc qua hàm công khai.
Test đỏ→xanh: normalize (enum, thiếu trường → báo), 8 van về người, estimate, MockJudge end-to-end, cờ tắt = không chạy.
```

## Việc 3 — S14.25 Đợt 6a Góp ý → mistakes · ≈ $8–15
```
Việc S14.25 phần Đợt 6a (Đợt 6b đã làm ở S14.10 — KHÔNG làm lại): đọc mục "### 6a. Feedback chảy vào `mistakes`" trong docs/KE_HOACH_BO_NAO_PROMPT_TU_HOC_2026-10-04.md (≈ dòng 443+) và dòng "S14.25 ·" trong docs/KE_HOACH_SUA_SAU_DU_AN_8.md.
Mục tiêu: góp ý người dùng (chấm ≤ 2/5, ghi chú từ chối…) chảy vào bảng `mistakes` qua cờ mới `feedback_to_mistakes` (TẮT mặc định), có khử trùng, có nguồn (source/ref_id/stage), không ghi khi cờ tắt. Không đụng code lọc chủ đề đã bỏ của S14.46.
Test đỏ→xanh: góp ý thấp → 1 dòng mistakes đúng stage; trùng → không ghi lại; cờ tắt → không ghi; góp ý tốt → không ghi.
```

---

## Sau khi phiên cloud xong (phiên chính ở máy chính)
1. `git fetch` → đọc báo cáo + `git diff main...cloud/<mã>`.
2. Rà theo mức (skill mục 2): S14.24 RÀ KỸ (đụng lời gọi Claude tốn tiền + knowledge); S14.45, S14.25 rà nhẹ trừ khi đụng tiền/dữ liệu.
3. Cả bộ test trên Windows → gộp `main` → tăng `devsys/areas.json` version một lần → push → pull ở `D:\AI-Video-Pipeline` → khởi động lại Dashboard / devsys.
4. Ghi số đo vào dòng việc (chế độ `cloud`, credit đã dùng) + `py -m devsys.workflow add …` (khi S14.45 đã gộp).

---

## Làn thứ ba: phiên cloud TÀI KHOẢN KHÁC hỗ trợ ngoài Codex (người dùng 20/10)
Cloud = tài khoản Cloud credits riêng ở claude.ai/code (KHÔNG phải tài khoản đang chạy phiên chính — người dùng 20/10: "không phải cloud
của tài khoản này"). Phiên chính KHÔNG dùng `start_session target:"cloud"`; chỉ viết prompt tự đủ vào mục "Việc V3.1 cho cloud" bên dưới,
push lên main, rồi báo người dùng mã việc để dán vào phiên cloud của tài khoản kia (kèm khối "Luật chung" ở trên).
- Chọn việc cho cloud: Cấp 1 (tài liệu / thiết kế / test chỉ đọc) hoặc code Cấp 2 ĐÃ duyệt phạm vi, không cần `data/` / Windows / khóa API.
  Không giao cloud việc trùng file với Codex đang làm (đợt Codex mới nhất trong `docs/CODEX_TASKS.md`) hay với phiên con máy chính.
- Phiên cloud không báo về → phiên chính `git fetch` nhánh `cloud/*`, đọc `docs/RA_CLOUD_*.md`, rà quy ước 7, cả bộ test Windows, rồi gộp.
- Mọi trao đổi với cloud qua hộp thư 📨 `TODO.md` (người dùng 20/10): phiên chính đăng `phiên-chính → cloud-B: <MÃ> — CHỜ`; cloud tự đổi ĐANG LÀM / XONG / HỎI. Người dùng chỉ cần nói với cloud "đọc hộp thư, làm việc CHỜ của cloud-B".

### Việc V3.1 cho cloud (giao 20/10)
| Mã | Việc | Nhánh | Trạng thái |
|---|---|---|---|
| C-M06-07 | M0.6 bảng AS-IS/TO-BE + M0.7 ma trận test (chỉ tài liệu) | `cloud/v31-m06-m07` | XONG — gộp main 20/10 |
| C-M010 | M0.10 đặc tả AUTO/USER_LOCKED/REVIEW_REQUIRED + audit đường ghi (chỉ tài liệu) | `cloud/v31-m010` | XONG — gộp main 20/10 |
| C-M09 | M0.9 thiết kế Kho forms/outfit/hair/face + provenance (chỉ tài liệu) | `cloud/v31-m09` | XONG — gộp main 20/10 |
| C-M011 | M0.11 test plan + tiêu chí 3 vòng pilot + dự toán B/C (chỉ tài liệu) | `cloud/v31-m011` | XONG — gộp main 20/10 |
| C-M04-05 | M0.4–M0.5 sổ lỗi `devsys/errors.json` + test hợp đồng + nhập G/A/B có nguồn (code devsys, Cấp 2 G2-1 ĐÃ DUYỆT) | `cloud/v31-m04-m05` | ĐANG LÀM (cloud tài khoản khác, 20/10) |
| C-RA-D19 | Rà chỉ đọc 4 nhánh Codex đợt 19 | `cloud/v31-ra-d19` | CHỜ (hộp thư) |
| C-M14B | M1.4b provider Claude theo dự án + snapshot theo job + dừng khi hết quota (CODE Cấp 2 G2-2 đã duyệt; migration chỉ viết, KHÔNG áp CSDL thật) | `cloud/v31-m14b` | CHỜ (hộp thư) — làm SAU C-RA-D19, TRƯỚC C-M21-22 |
| C-M21-22 | Thiết kế M2.1 BYĐ v2 + M2.2 field readers/lineage (chỉ tài liệu) | `cloud/v31-m21-m22` | CHỜ (hộp thư) |
| C-M41 | Thiết kế M4.1 schema bằng chứng QC + mã lỗi (chỉ tài liệu) | `cloud/v31-m41` | CHỜ (hộp thư) |
| C-FIX-D19 | Sửa lỗi CAO/VỪA của C-RA-D19 trên 3 nhánh Codex Đ19 (việc 2 code công cụ chỉ đọc; việc 3, 4 tài liệu) | `cloud/v31-fix-d19` | CHỜ (hộp thư) |
| C-M31-34 | Thiết kế M3.1–M3.4 world map / người nộm / câu vị trí / continuity_state (chỉ tài liệu) | `cloud/v31-m31-m34` | CHỜ (hộp thư) |
| C-M51-52 | Thiết kế M5.1 repair router + M5.2 release gate (chỉ tài liệu) | `cloud/v31-m51-m52` | CHỜ (hộp thư) |
| C-M46 | Đặc tả bộ benchmark QC M4.6 theo mã lỗi (chỉ tài liệu + công cụ liệt kê ca chỉ đọc nếu cần) | `cloud/v31-m46` | CHỜ (hộp thư) |

(20/10: 2 phiên `start_session target:"cloud"` tài khoản chính HỎNG khi khởi động — clone nhánh worktree chưa push + API error; M1.4a chuyển phiên con máy chính. 3 việc C-M010, C-M09, C-M011 độc lập, dán được song song 3 phiên.)

#### C-M06-07
```
Việc V3.1 M0.6 + M0.7 — CHỈ TÀI LIỆU, không sửa code. Nhánh cloud/v31-m06-m07 từ origin/main. Theo "Luật chung" docs/CLOUD_TASKS.md.
Đọc: grep -n "M0.6\|M0.7\|WS[0-6]" docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md rồi đọc các đoạn đó (WS0–WS6, milestone M1–M5, bảng nghiệm thu ~dòng 110–125).
1. M0.6 → docs/V3_1_M0_6_AS_IS_TO_BE_2026-10-20.md: với từng WS0–WS6, bảng năng lực TO-BE ↔ code hiện tại theo file:hàm (mở code thật, không đoán),
   trạng thái IMPL / PART / MISS / UNK + bằng chứng (dòng code / test). UNK khi không xác minh được (vd cần data/ máy chính) — ghi lý do.
   Cuối file: tổng đếm theo WS + danh sách MISS ưu tiên.
2. M0.7 → docs/V3_1_M0_7_MA_TRAN_TEST_2026-10-20.md: mỗi milestone M1.x–M5.x: test bắt buộc theo docs/CHUAN_XAY_DUNG.md (đỏ trước/xanh sau, cờ TẮT =
   byte, tiền/sổ chi, 2 dự án song song…), khu vực devsys/areas.json bị đụng, test hiện có phủ gì (tên file/test), còn thiếu gì, có cần mark slow (conftest.py).
Được chạy pytest chỉ đọc để xác minh test tồn tại/xanh (ghi số). Báo cáo ≤ 25 dòng ghi cả vào docs/RA_CLOUD_M06_M07_2026-10-2x.md.
```

#### C-M010
```
Việc V3.1 M0.10 — CHỈ TÀI LIỆU, không sửa code. Nhánh cloud/v31-m010 từ origin/main. Theo "Luật chung" docs/CLOUD_TASKS.md.
Đọc: grep -n "M0.10\|M2.5\|USER_LOCKED\|REVIEW_REQUIRED\|A4" docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md + quyết định v31-* liên quan trong data/decisions.json.
→ docs/V3_1_M0_10_BAO_VE_DU_LIEU_2026-10-2x.md:
1. Đặc tả 3 trạng thái AUTO / USER_LOCKED / REVIEW_REQUIRED cho từng trường scenes.data + Kho (ai được ghi, khi nào chuyển trạng thái, xung đột AI ghi đè tay).
2. Audit MỌI đường ghi scenes.data / Kho thật theo file:hàm (grep update/save/set_scene/UPDATE scenes… trong core/ dashboard/ tools/): nguồn ghi
   (người / AI / tự động / công cụ), có kiểm khóa tay không, có ghi diag/lịch sử không. Đường không xác minh được → ghi UNK + lý do.
3. Thiết kế test cho M2.5 (shadow trước): ca AI ghi đè trường USER_LOCKED, REVIEW_REQUIRED chặn gen, tương thích dự án cũ (thiếu trạng thái = AUTO).
Không đề xuất migration chạy luôn (Cấp 3) — chỉ mô tả. Báo cáo ≤ 25 dòng ghi cả vào docs/RA_CLOUD_M010_2026-10-2x.md.
```

#### C-M09
```
Việc V3.1 M0.9 — CHỈ TÀI LIỆU, không sửa code. Nhánh cloud/v31-m09 từ origin/main. Theo "Luật chung" docs/CLOUD_TASKS.md.
Đọc: docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md dòng ~54 (hợp đồng dữ liệu: ảnh Kho > profile Kho > Bible > Lock), D05 ~104, M2.3 ~120, mục 4b;
data/decisions.json mục v31-d05-kho-structured-forms-2026-10-20 và video-form-picture-2026-10-19. Đọc code Kho/profile hiện tại (grep kho_id, forms,
profile, outfit, hair trong core/ dashboard/) — mọi khẳng định kèm file:hàm.
→ docs/V3_1_M0_9_THIET_KE_KHO_FORMS_2026-10-2x.md: schema forms/outfit/hair/face có cấu trúc + kho_id + revision + schema_version; provenance
(nguồn: người / AI + model / ảnh chuẩn; AI không ghi đè trường người dùng); adapter đọc v1/v2 và danh sách MỌI đường đọc (Director, BYĐ, ảnh, video,
QC) phải đi qua adapter; đối chiếu đủ 6 điều kiện M2.3 (bảng điều kiện → cách đáp ứng → test); kế hoạch migration/backfill (Cấp 3 — chỉ mô tả,
up/down, dự án cũ giống byte); bộ regression đề xuất. Không đụng thiết kế Kho chủ thể ClipAI (M1.5 — Codex đợt 19).
Báo cáo ≤ 25 dòng ghi cả vào docs/RA_CLOUD_M09_2026-10-2x.md.
```

#### C-M011
```
Việc V3.1 M0.11 — CHỈ TÀI LIỆU, không sửa code, KHÔNG chạy gì tốn tiền. Nhánh cloud/v31-m011 từ origin/main. Theo "Luật chung" docs/CLOUD_TASKS.md.
Đọc: grep -n "M5\.\|pilot\|vòng A\|vòng B\|vòng C" docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md + quyết định v31-pilot-three-rounds-2026-10-20
(data/decisions.json) + bảng nghiệm thu ~dòng 110–125.
→ docs/V3_1_M0_11_PILOT_3_VONG_2026-10-2x.md: (1) vòng A offline 0 USD — replay lỗi #31/#33 (payload, continuity, QC, lineage, phục hồi): ca thử, dữ
liệu cần (fixture nào có trong tests/, cái gì phải lấy ở máy chính — ghi rõ), tiêu chí đạt/rớt đo được; (2) vòng B 5–8 shot và (3) vòng C 20–40 shot:
tiêu chí chất lượng, tỉ lệ gen lại, continuity, chi phí, số lần can thiệp tay, điểm dừng; (4) dự toán B/C TÍNH TỪ code giá hiện tại (core/cost.py và
bảng giá trong repo — dẫn hàm + công thức; ghi rõ giả định số lần gen lại; KHÔNG tự bịa giá), kèm khoảng thấp–cao. Ghi rõ: con số cuối phải chạy
tools/pregen_check.py ở máy chính trước khi xin duyệt. Báo cáo ≤ 25 dòng ghi cả vào docs/RA_CLOUD_M011_2026-10-2x.md.
```

#### C-M04-05
```
Việc V3.1 M0.4 + M0.5 — sổ lỗi (Cấp 2, gói G2-1 người dùng DUYỆT 20/10: sổ data/decisions.json id v31-cap2-milestone-packages-approved-2026-10-20).
Nhánh cloud/v31-m04-m05 từ origin/main. Theo "Luật chung" docs/CLOUD_TASKS.md (không cần hỏi credit nếu người dùng đã nói). Chỉ đụng devsys/ + tests/.
Đặc tả: docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md đoạn "**Sổ lỗi (WS0):**" (~dòng 69) + bảng D09 (~dòng 107: errors.json = định nghĩa + vòng đời;
diag_events/jobs = lần phát sinh; mã bất biến; lỗi gốc ≠ lần xuất hiện; liên kết nhiều dự án; tách đã sửa code / qua test / xác minh chạy thật;
KHÔNG tự đóng khi chỉ có unit test) + mục 4a dòng "M0.4–M0.5 sổ lỗi".
1. M0.4: devsys/errors.json (schema_version, items[] đủ trường đặc tả: id bất biến dạng P31-G1 / P33-A1 + alias, title, source_document, project/shot/job
   ids, stage L1–L16, category, root_cause_hypothesis/confirmed, evidence, severity, status, first_seen, last_seen, affected_flows, owner, fix_commit,
   tests, real_run_evidence, plan_workstream, dependencies, reopen_history). devsys/errors.py: load + problems() (mã trùng; trạng thái ngoài
   OPEN/IN_PROGRESS/FIXED_UNVERIFIED/VERIFIED/REOPENED/WONT_FIX; VERIFIED thiếu fix_commit + tests + real_run_evidence → lỗi; WONT_FIX thiếu lý do;
   OPEN thiếu plan_workstream) + CLI `python -m devsys.errors check|list`. Mẫu: devsys/decisions.py + core/decisions.py + tests/test_decisions.py.
   tests/test_error_registry.py: ĐỎ trước XANH sau cho từng luật.
2. M0.5: nhập G1–G58 (nguồn chính docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md; grep "^| G" trong docs/ cho mã khác), A1–A15 + B1–B12
   (docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md). Mỗi mục có source_document + dòng. G25 khuyết → KHÔNG bịa, ghi rõ trong báo cáo coverage.
   Trạng thái theo bằng chứng trong repo: có commit sửa + test → FIXED_UNVERIFIED (KHÔNG VERIFIED khi không có bằng chứng chạy thật);
   M0.2 đã kiểm G7, G8, G10, G24, G27, G35 (xem kế hoạch dòng M0.2). Mã A1 (succeeded 2 lần) và G36 đang được sửa ở nhánh M1.2/M1.3 → IN_PROGRESS.
   Báo cáo coverage: docs/V3_1_M0_5_COVERAGE_SO_LOI_2026-10-2x.md (tổng theo nguồn, theo trạng thái, theo workstream, mã khuyết).
3. Khai file mới vào devsys/areas.json (KHÔNG tăng version). Không sửa devsys/app.py (trang hiển thị sổ để phiên chính làm sau).
Báo cáo ≤ 25 dòng ghi cả vào docs/RA_CLOUD_M04_M05_2026-10-2x.md.
```

#### C-RA-D19
```
RÀ CHỈ ĐỌC 4 nhánh Codex đợt 19: origin/codex/d19-viec1-narration, d19-viec2-doi-soat, d19-viec3-provider, d19-viec4-subjects (đề bài: docs/CODEX_TASKS.md
"# ĐỢT 19"). Không sửa các nhánh đó. Mỗi nhánh: git diff origin/main...<nhánh>, đối chiếu đề bài + docs/CHUAN_XAY_DUNG.md, chạy test của nhánh (Linux; thiếu
streamlit/Windows → "bỏ qua"); tìm: test nới che lỗi, xfail thiếu strict / mã lỗi, công cụ "chỉ đọc" có đường ghi CSDL / gọi API trả phí, thiết kế M1.4b/M1.5
lệch quyết định v31-d02 / v31-d03b / C3-3 (chỉ dry-run xóa). Mỗi lỗi: CAO/VỪA/THẤP, file:dòng, cách sửa, test chứng minh.
→ docs/RA_CLOUD_D19_2026-10-2x.md trên nhánh cloud/v31-ra-d19.
```

#### C-M21-22
```
THIẾT KẾ (chỉ tài liệu) M2.1 BYĐ v2 + M2.2 field readers/lineage. grep "M2.1\|M2.2\|BYĐ v2\|byd_v\|A2a" trong docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md
và docs/KE_HOACH_AI_VIDEO_PIPELINE_V3_2026-10-20.md (Phụ lục A). Đọc core/shot_intent.py (parser vat v1/v2 đã gộp), core/llm_io.py, lineage.
→ docs/V3_1_M2_1_M2_2_THIET_KE_2026-10-2x.md: schema byd_v + vat[] object + provenance, mức BLOCK/REVIEW/WARN, adapter v1→v2 (dự án cũ giống byte khi cờ
TẮT), MỌI caller đọc BYĐ (file:hàm), field readers A2a–A2f, cờ, test plan (golden #24/#27 compat + #31/#33 correctness), rollback; nối M0.9 + M0.10.
Nhánh cloud/v31-m21-m22.
```

#### C-M41
```
THIẾT KẾ (chỉ tài liệu) M4.1 schema bằng chứng QC + mã lỗi thống nhất: kế hoạch V3.1 đoạn "**Bằng chứng QC:**" + D07 (v31-d07-qc-shadow-guarded) + mục 4a
"M4.x QC". Đọc core/qc_*.py, core/autoqc.py, core/qc_observe.py. → docs/V3_1_M4_1_THIET_KE_BANG_CHUNG_QC_2026-10-2x.md: schema (error_type, severity,
evidence_type, confidence_calibration, artifact_id/sha, qc_run_id, qc_version, intent_exception, actionability, source_refs), bảng mã lỗi QC ↔ sổ lỗi
(devsys/errors.json của C-M04-05), đường QC hiện có → schema mới (file:hàm), chỉ luật kỹ thuật tất định được xét BLOCK sau benchmark, còn lại REVIEW; test
plan + benchmark M4.6 (≥ 20 lỗi + 20 đạt mỗi mã). Nhánh cloud/v31-m41.
```

#### C-M14B
```
Việc V3.1 M1.4b (CODE, Cấp 2 gói G2-2 ĐÃ DUYỆT — sổ v31-cap2-milestone-packages-approved-2026-10-20). Nhánh cloud/v31-m14b từ origin/main MỚI NHẤT.
Theo "Luật chung" docs/CLOUD_TASKS.md + hộp thư. KHÔNG làm Cấp 3: không áp migration lên CSDL thật (C3-1 do phiên chính làm sau backup), không bật cờ,
không gọi API thật (chỉ provider giả / mock).
Nguồn: docs/V3_1_GOI_SUA_VA_RUI_RO_2026-10-20.md mục 2.3 (bảng file) + thiết kế Codex Đ19 việc 3 (nhánh origin/codex/d19-viec3-provider, file
docs/V3_1_M1_4B_THIET_KE_*.md — dùng kèm kết quả rà C-RA-D19 của chính anh) + quyết định v31-d02-claude-provider-per-project-2026-10-20.
Nền đã có trên main (M1.4a): core/llm_runner.py clean_env bỏ key, client_from_env không fallback ngầm, provider_status(), missing_hint(), STOP_CODES,
cli_error_code usage_limit/out_of_credit. dashboard.env máy chính nay LLM_PROVIDER=claude_cli.
Làm: client_for_project(conn, pid) (projects.llm_provider rỗng = theo env như cũ); snapshot jobs.llm_provider + llm_config_ver lúc tạo job, job đang chạy
giữ provider snapshot dù đổi cấu hình; llm_calls.provider; mọi caller ở bảng 2.3 (bg_poll, change_review, prompt_rewrite, chat_prompt, autoqc, autopilot,
dashboard/common, camera_plan) lấy client theo dự án / snapshot; hết quota (usage_limit/out_of_credit) → dừng cả lượt có giờ mở lại, 0 lời gọi API;
devsys/scorer.py thêm lựa chọn claude_cli, đổi MẶC ĐỊNH khỏi 'anthropic' (tools/devsys_score.py --provider, devsys/app.py nút chọn) — rà C-RA-D19/M1.4a
phát hiện devsys mặc định anthropic. Migration: hàm up/down trong core/db.py theo mẫu migration hiện có, CHỈ chạy trong test CSDL tạm; tương thích:
worker code cũ chạy trên CSDL đã có cột mới vẫn đúng (test).
Test ĐỎ→XANH: 2 dự án (anthropic giả / claude_cli giả) cùng tiến trình; job tạo trước khi đổi cấu hình giữ provider cũ; hết quota CLI → dừng có giờ mở, 0
lời gọi API; env có key + provider claude_cli → subprocess không nhận key; LLM_PROVIDER rỗng + key → không tự ra anthropic; cột trống = hành vi env cũ;
migration up rồi down trên CSDL tạm. Gom test liên quan một lệnh pytest, ≤ 3 lần. File mới khai devsys/areas.json (không tăng version).
Báo cáo ≤ 30 dòng → docs/RA_CLOUD_M14B_2026-10-2x.md + dòng XONG trong hộp thư.
```

#### C-FIX-D19
```
Sửa lỗi C-RA-D19 (báo cáo docs/RA_CLOUD_D19_2026-10-20.md, đã trên main) — nhánh cloud/v31-fix-d19 tách từ origin/main MỚI NHẤT, rồi
`git merge origin/codex/d19-viec2-doi-soat origin/codex/d19-viec3-provider origin/codex/d19-viec4-subjects` (bỏ HANDOFF.md + dòng TODO.md ngoài mục 📨
khi gộp). Sửa:
- Việc 2 tools/clipai_cost_reconcile.py: CAO validate_pricing từ chối null trong per_video_second → chấp nhận null (giá chưa biết = UNKNOWN, báo rõ, không
  crash) và chạy được với data/pricing.json THẬT trong repo (test đọc file thật); VỪA clip NHÓM dùng chung external_id (core/runner.py ~2315/2481) → chia
  task theo thành viên nhóm (theo sent_group / clip_span), không đếm trùng; THẤP: main không nuốt lỗi (in mã + chi tiết), ghi rõ chỉ họ seedance hoặc thêm
  --family kling, kind upgrade vs bản cao gen mới (quality_tier.NEW_GEN). Test ĐỎ→XANH cho từng lỗi. Công cụ vẫn CHỈ ĐỌC, không gọi API trả phí.
- Việc 3 docs/V3_1_M1_4B_THIET_KE_2026-10-20.md: VỪA bỏ "hold toàn bộ LLM" cho dự án/job cũ (LEGACY_LLM_CONTEXT_UNKNOWN) → job cũ = theo env như trước
  (khớp M1.4b đã code trên cloud/v31-m14b); cập nhật dẫn chiếu missing_hint / STOP_CODES / clean_env đã có trên main.
- Việc 4 docs/V3_1_M1_5_THIET_KE_KHO_CHU_THE_2026-10-20.md: VỪA lệch C3-3 → mọi xóa chỉ DRY-RUN, duyệt riêng TỪNG lần; VỪA sửa G59 làm cờ cũ
  subject_auto_cleanup (verified=True) bắt đầu XÓA THẬT → thiết kế phải vô hiệu đường xóa tự động của cờ cũ (chuyển thành dry-run + báo) TRƯỚC/cùng lúc
  sửa G59, có test; THẤP: job không cần ảnh Kho không vào QUEUE_CAPACITY.
Báo cáo ≤ 25 dòng → docs/RA_CLOUD_FIX_D19_2026-10-2x.md + XONG trong hộp thư. Không sửa code ngoài tools/clipai_cost_reconcile.py + test của nó.
```

#### C-M31-34
```
THIẾT KẾ (chỉ tài liệu) M3.1–M3.4 theo G2-4 (world map CHỈ thử offline, không chặn gen, không bắt buộc 3D) + D06 (v31-d06-scene-world-map-flexible).
Nguồn: kế hoạch V3.1 đoạn "**`scene_world_map` tối thiểu:**" + mục 4a "M3.x" + docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md (G1–G3, G41–G50, G52) +
docs/PHUONG_PHAP_SAN_KHAU_3D.md; code core/plates3d*, core/stage_auto.py, core/camera_plan.py, core/continuity*.py, core/plate_camera.py.
→ docs/V3_1_M3_THIET_KE_WORLD_MAP_2026-10-2x.md: schema scene_world_map (3D tọa độ thật / 2D / quan hệ tương đối / UNKNOWN, version, provenance,
invalidation khi geometry/BYĐ đổi), blocking mỗi shot, M3.2 người nộm height_m + pitch, M3.3 câu vị trí sinh từ map (thay tả tay), M3.4 continuity_state
expected/observed/resolved + đồ thị phụ thuộc; MỌI điểm đọc/ghi hiện có (file:hàm); ca offline #31 cảnh 4/6/8 + #33 tháp; cờ + rollback; nối M2.1 (BYĐ v2,
docs/V3_1_M2_1_M2_2_THIET_KE_2026-10-20.md). Nhánh cloud/v31-m31-m34.
```

#### C-M51-52
```
THIẾT KẾ (chỉ tài liệu) M5.1 repair router theo mã lỗi (trần ảnh ≤ 3 / video ≤ 2, dừng khi lặp lỗi, gen lại phải đổi đầu vào — luật 6 CHUAN_XAY_DUNG,
router mặc định TẮT theo G2-6) + M5.2 release gate (shot duyệt, final QC, đối soát chi phí, lỗi nghiêm trọng mở). Nguồn: kế hoạch V3.1 M5.x + mục 4a,
sổ lỗi devsys/errors.json (đã trên main), thiết kế M4.1 (docs/V3_1_M4_1_THIET_KE_BANG_CHUNG_QC_2026-10-20.md); code core/autopilot.py (AUTO_REGEN_LIMIT,
_job_cap_check), core/pipeline.py retry, core/prompt_rewrite.py, core/final_cut.py. → docs/V3_1_M5_THIET_KE_REPAIR_RELEASE_2026-10-2x.md: bảng mã lỗi →
hành động sửa (đổi đầu vào gì) → trần → khi nào dừng hỏi người; tương tác poll_claim / pause_before_submit / submit_unknown (đã bật máy chính); release
gate checklist đo được; test plan + rollback. Nhánh cloud/v31-m51-m52.
```

#### C-M46
```
ĐẶC TẢ (chỉ tài liệu) bộ benchmark QC M4.6 theo D07 (≥ 20 lỗi + 20 đạt MỖI mã, chỉ là sàng lọc, không tự cấp BLOCK): danh sách mã QC (theo thiết kế M4.1),
nguồn ca thật có thể lấy (job/shot #24 #27 #31 #33 trong tài liệu docs/DANH_GIA_*, sổ lỗi) — ghi rõ ca nào cần máy chính trích (data/ không có trên cloud),
quy trình gán nhãn (người dùng xác nhận), chỉ số (báo nhầm / bỏ sót theo mã, hiệu chuẩn độ tin cậy), ngưỡng xét BLOCK chỉ cho luật kỹ thuật tất định.
→ docs/V3_1_M4_6_DAC_TA_BENCHMARK_QC_2026-10-2x.md. Nhánh cloud/v31-m46.
```
