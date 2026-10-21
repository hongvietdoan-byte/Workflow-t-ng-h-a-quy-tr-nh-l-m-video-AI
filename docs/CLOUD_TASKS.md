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
- Một phiên cloud = một việc. Không mở phiên con (Agent) trong cloud — tốn gấp đôi. **NGOẠI LỆ 21/10 (người dùng): cloud-C và cloud-E ĐƯỢC mở nhánh phụ song song — xem mục "NHÁNH PHỤ SONG SONG (cloud-C, cloud-E)".**

## Luật chung (dán kèm mọi prompt)
```
Luật dự án (bắt buộc):
- Trả lời/ghi chú tiếng Việt. Đọc CLAUDE.md + docs/CHUAN_XAY_DUNG.md trước (không im lặng khi thiếu đầu vào; "đã sửa" kèm bằng chứng chạy thật).
- HỘP THƯ SỰ KIỆN (từ 20/10 tối): nhận / xong / hỏi bằng `python3 tools/hop_thu.py` (`ke --lane <làn> --nhan --push`, `xong … --push`; luật `hop_thu/README.md`) — không ghi dòng vào TODO.md nữa. (Cũ:) nhận việc / báo / hỏi qua mục 📨 đầu TODO.md trên main (luật "LUẬT HỘP THƯ CHUNG" ở đó; tên làn `cloud-B`) — ngoại lệ duy nhất được push main: commit CHỈ đổi dòng hộp thư (`hộp thư: …`), pull --ff-only trước, không force.
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
| C-M16 | M1.6 ước tính giá đúng gói gửi (CODE, chuyển từ Codex Đ20 việc 3) | `cloud/v31-m16` | CHỜ (hộp thư) |
| C-M17 | M1.7 G55/G56/G39/A14 (CODE, chuyển từ Codex Đ20 việc 4) | `cloud/v31-m17` | CHỜ (hộp thư) |
| C-M2X | Thiết kế M2.4, M2.6, M2.7, M2.8, M2.9 (chỉ tài liệu) | `cloud/v31-m2x` | CHỜ (hộp thư) |
| C-RA-M14B | (cloud-C) RÀ KỸ độc lập nhánh `cloud/v31-m14b` rồi sửa một vòng | `cloud/v31-m14b-fix` | CHỜ (hộp thư) |
| C-T12 | (cloud-C) Bổ sung test còn thiếu của M1.2/M1.3 | `cloud/v31-t12` | CHỜ (hộp thư) |
| C-G36B | (cloud-D, chuyển từ cloud-C 20/10) G36 còn mở: lần thử lại đầu vẫn đi Seedance — điều tra + sửa gốc | `cloud/v31-g36b` | CHỜ (hộp thư) |
| C-ERR-UPD | (cloud-D, chuyển từ cloud-C 20/10) Cập nhật sổ lỗi theo các commit đã gộp 20/10 | `cloud/v31-err-upd` | CHỜ (hộp thư) |
| C-M42 | (cloud-C) M4.2 video QC đứng yên / khớp khung 0 / vật còn giữ / chuyển cảnh ref (shadow) | `cloud/v31-m42` | CHỜ (hộp thư) |
| C-M43 | (cloud-C) M4.3 cross-shot logic qua qc_sequence_logic (shadow) | `cloud/v31-m43` | CHỜ (hộp thư) |
| C-M26 | (cloud-C) M2.6 sent_package nhãn theo rel_path/asset_id — BẮT ĐẦU KHI golden M1.9 gộp main | `cloud/v31-m26` | CHỜ ĐIỀU KIỆN |
| C-M29 | (cloud-C) M2.9 lời dẫn ngoài khớp môi mọi caller — BẮT ĐẦU KHI golden M1.9 gộp main | `cloud/v31-m29` | CHỜ ĐIỀU KIỆN |
| C-M24 | (cloud-C) M2.4 insert_scene_after kế thừa bối cảnh + BYĐ DRAFT — BẮT ĐẦU KHI golden M1.9 gộp main | `cloud/v31-m24` | CHỜ ĐIỀU KIỆN |

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

#### C-M16
```
Việc V3.1 M1.6 (CODE, Cấp 2 G2-2 đã duyệt) — đề bài ĐÚNG như docs/CODEX_TASKS.md "# ĐỢT 20" → "## Việc 3 — M1.6" + luật chung đầu ĐỢT 20 (cờ TẮT khi đổi
hành vi, KHÔNG đổi data/pricing.json, D01: 0 điểm chặn mới theo ngân sách, check_no_budget_lock_gate xanh). Chuyển từ Codex sang cloud-B 20/10.
Công cụ tools/clipai_cost_reconcile.py ĐÃ trên main (dùng số hiệu chuẩn của nó; ghi rõ số điểm). Nhánh cloud/v31-m16 từ origin/main MỚI NHẤT.
KHÔNG sửa core/llm_runner.py (M1.4b chờ gộp). Báo cáo → docs/RA_CLOUD_M16_2026-10-2x.md + XONG trong hộp thư.
```

#### C-M17
```
Việc V3.1 M1.7 (CODE, Cấp 2 G2-2 đã duyệt) — đề bài ĐÚNG như docs/CODEX_TASKS.md "# ĐỢT 20" → "## Việc 4 — M1.7" (G55 báo chạy code cũ, G56 gộp diag lặp,
G39 regen kiểm data_dir, A14 câu báo ngân sách theo D01) + luật chung ĐỢT 20. core/runner.py, core/bg_poll.py nay ĐƯỢC sửa (M1.2/M1.3 đã gộp) nhưng giữ
nguyên hành vi poll_claim / pause_before_submit (đang BẬT máy chính) — test cũ của chúng phải xanh. Lưu ý thực tế 20/10: tools/stop_dashboard.ps1 chỉ tắt
8501, 2 Dashboard cũ 8503/8504 chạy code cũ cả ngày → G55 nên báo cả khi CỔNG KHÁC đang chạy code cũ (banner/diag), và stop_dashboard có tùy chọn tắt mọi
cổng dashboard.serve. Nhánh cloud/v31-m17. Báo cáo → docs/RA_CLOUD_M17_2026-10-2x.md + XONG trong hộp thư.
```

#### C-M2X
```
THIẾT KẾ (chỉ tài liệu) chuẩn bị code M2 (G2-3 mở khi có golden M1.9): M2.4 insert_scene_after kế thừa bối cảnh + BYĐ DRAFT; M2.6 sent_package nhãn theo
rel_path/asset_id (G5); M2.7 image preflight trong ImageRunner._pregen chung mã lỗi với video; M2.8 router theo khả năng model (không gộp nhóm khi cần khung
đầu/cuối…); M2.9 lời dẫn ngoài khớp môi mọi caller (G15–G17, G53) — dùng tests/test_narration_regression.py (21 xfail strict đã trên main) làm nghiệm thu.
Nguồn: kế hoạch V3.1 mục 5 dòng M2.x + mục 4a; thiết kế M2.1/M2.2, M0.9, M0.10 đã trên main; mã lỗi trong devsys/errors.json. Mỗi việc: file:hàm hiện có,
thay đổi, cờ, test đỏ→xanh, golden compat (#24/#27 cờ TẮT = byte), rollback. → docs/V3_1_M2_THIET_KE_CON_LAI_2026-10-2x.md. Nhánh cloud/v31-m2x.
```

#### C-RA-M14B (cloud-C)
```
RÀ KỸ độc lập (quy ước 7 CLAUDE.md) nhánh origin/cloud/v31-m14b (M1.4b provider Claude theo dự án, do cloud-B viết — anh là làn KHÁC nên rà độc lập).
Đụng TIỀN + provider + migration → rà kỹ. Bước 1 CHỈ ĐỌC: git diff origin/main...origin/cloud/v31-m14b; đối chiếu đề bài "#### C-M14B" (file này), thiết kế
docs/V3_1_M1_4B_THIET_KE_2026-10-20.md (đã sửa C-FIX-D19: job/dự án cũ theo env, không hold), quyết định v31-d02 + v31-cap3-items-decided (C3-1: migration
chỉ áp sau backup — code KHÔNG được tự áp lên CSDL thật lúc khởi động trừ khi theo đúng cơ chế migration hiện có của core/db.py và tương thích worker cũ).
Chạy `python tools/related_areas.py <file đổi>` để lấy khu vực liên quan; rà: caller nào còn client_from_env thay vì client_for_project; job đang chạy có giữ
snapshot không; đường nền (bg_poll, autoqc, autopilot, change_review) khi hết quota dừng cả lượt có giờ mở; có đường nào tự sang anthropic khi dự án cũ NULL
mà env claude_cli; devsys mặc định không còn anthropic; migration up/down + worker cũ; test bị nới. Ghi docs/RA_CLOUD_M14B_REVIEW_2026-10-2x.md (mỗi lỗi:
CAO/VỪA/THẤP, file:dòng, cách sửa, test).
Bước 2 SỬA một vòng: nhánh cloud/v31-m14b-fix tách từ origin/cloud/v31-m14b, sửa HẾT lỗi CAO/VỪA (+ THẤP nếu rẻ), test ĐỎ→XANH từng lỗi, gom test 1 lệnh.
Không áp migration lên CSDL thật, không gọi API thật. XONG ghi hộp thư.
```

#### C-T12 (cloud-C)
```
Bổ sung TEST còn thiếu (chỉ test, không đổi hành vi; nếu test lộ lỗi thật → sửa tối thiểu + ghi rõ) cho M1.2/M1.3 đã gộp main (cờ poll_claim +
pause_before_submit đang BẬT máy chính): (1) đường VIDEO qua core/safe_download.py: core/runner.py _finish_group / _finish_upgrade — tệp tạm + os.replace, người đọc
không thấy tệp dở, clip nhóm; (2) core/bg_poll.poll_all ở mức 2 TIẾN TRÌNH thật (multiprocessing, CSDL SQLite tạm) cùng poll một job → đúng 1 succeeded;
(3) core/end_frames.py: bước tạo khung cuối có thể tốn tiền lúc dự án đang Tạm dừng → phải 0 lần gửi khi pause_before_submit bật (nếu đang gửi được → đó
là lỗi, sửa sau cờ pause_before_submit). Nguồn: báo cáo phiên con M1.2/M1.3 (mục rủi ro trong hộp thư 18:12 + tests/test_v31_m12_poll_claim.py,
tests/test_v31_m13_pause_before_submit.py). Test chạy được trên Linux (không cần Windows). Nhánh cloud/v31-t12.
```

#### C-G36B (cloud-D)
```
G36 còn mở (docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md dòng "| G36 |"): sau khi Seedance từ chối (real_person), LẦN THỬ LẠI ĐẦU vẫn đi Seedance rồi mới
sang Kling (1061→1073, 1057→1065→1071) — đổi model trong core/runner.py _record_provider_failure không có tác dụng ở lần gửi lại đầu. Điều tra gốc (đọc
code + dựng lại bằng provider giả: job bị từ chối real_person → job thử lại phải mang model đã đổi ngay lần đầu), sửa GỐC (không vá), test ĐỎ→XANH. Giữ
nguyên poll_claim / pause_before_submit; chặn trả tiền trùng; không gọi API thật. Nếu sửa đổi hành vi đường gửi → sau cờ mới TẮT (core/features.py).
Nhánh cloud/v31-g36b. Báo cáo + XONG hộp thư.
```

#### C-ERR-UPD (cloud-D)
```
Cập nhật devsys/errors.json (sổ lỗi, đã trên main) theo các việc gộp main 20/10: M1.1 (R3 vat — commit gộp 36fcb4bd), M1.4a (R2 provider — 222bf9c5),
M1.2 A1 + A15 và M1.3 G36 (60b9da80; cờ BẬT máy chính 20/10 — sổ v31-c3-2-flags-on-main), C3-0 (dashboard.env claude_cli), lỗi Dashboard cũ chạy
cổng 8503/8504 (G55 thực tế). Trạng thái tối đa FIXED_UNVERIFIED (chưa có bằng chứng chạy thật), điền fix_commit + tests (tên test thật) + plan_workstream;
KHÔNG VERIFIED. Chạy `python -m devsys.errors check` phải "Hợp lệ"; tests/test_error_registry.py xanh. Lấy commit/test bằng git log / grep, không đoán.
Nhánh cloud/v31-err-upd. XONG hộp thư.
```

---

## HÀNG VIỆC DỰ PHÒNG (người dùng 20/10: làn hết việc tự lấy thêm; phiên chính chủ động bổ sung) — từ 20/10 tối: các mục DP là việc `--to pool` trong hộp thư sự kiện; nhận bằng `hop_thu.py ke --lane <làn> --nhan --push`
Làn cloud (B, C, …) **và Codex** hết việc được giao riêng → nhận mục **DP** đầu tiên còn `CHỜ` trong hộp thư (dòng "VIỆC DỰ PHÒNG"): sửa đuôi mục đó thành
`ĐANG LÀM <giờ> (<làn>)` + push commit `hộp thư:` NGAY (trước khi code) — thấy làn khác đã nhận trước (union merge có thể để 2 dòng nhận) thì làn
nhận SAU bỏ, lấy mục kế. Mọi mục: Cấp 2 đã duyệt (G2-4 / G2-5: QC chỉ Shadow/REVIEW, không tự BLOCK, map chỉ offline), cờ mới TẮT, test ĐỎ→XANH,
không API trả phí, nhánh `cloud/v31-<mã>`; báo cáo `docs/RA_CLOUD_<MÃ>_2026-10-2x.md` + XONG hộp thư.

#### DP1 — M4.5 sửa báo nhầm A5 + A6
```
Nguồn docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md dòng "| A5 |" (QC lớp 0 đo nhầm cỡ cảnh khi bố cục qua vai) và "| A6 |" (Tổ rà soát báo nhầm "không có
video tham chiếu" khi thiếu ref_video_path). Sửa gốc trong core/qc_*.py / core/change_review.py (đọc code đối chiếu dòng), test regression từ ca thật mô tả
trong tài liệu (fixture tổng hợp). Giữ QC shadow/REVIEW. Mã sổ lỗi P33-A5/P33-A6 (devsys/errors.json) — KHÔNG đổi trạng thái sổ (C-ERR-UPD làm).
```

#### DP2 — M3.5 bỏ kiểm chân trời khi nền không có trời (G20)
```
Nguồn: grep "| G20 |" docs/DANH_GIA_*.md. Kiểm chân trời (horizon) chỉ chạy khi nền có trời (khai trong bối cảnh / plate / BYĐ); nền trong nhà / không trời →
bỏ qua có ghi lý do (không im lặng). Đọc code core/qc_*.py, core/plate*.py tìm kiểm horizon. Sau cờ mới TẮT. Test ca có trời / không trời / không rõ (→ giữ kiểm).
```

#### DP3 — M4.4 Final QC blackdetect / freezedetect
```
Bản dựng cuối (core/final_cut.py): chạy ffmpeg blackdetect + freezedetect, ra danh sách đoạn đen / đứng hình (giây, shot) vào báo cáo final QC, mức REVIEW
(không chặn xuất — G2-5). Cờ mới TẮT. Ngưỡng tham số hóa; đứng hình > 1,5 s (khớp M4.2) báo REVIEW. Test bằng video tổng hợp nhỏ do ffmpeg tạo trong test
(lavfi color/testsrc) — có đoạn đen / đứng hình / không có. Lưu ý quyết định 11/10 "video không được đơ" (feedback ambient motion).
```

#### DP4 — M4.1 schema bằng chứng QC (code, shadow)
```
Theo thiết kế docs/V3_1_M4_1_THIET_KE_BANG_CHUNG_QC_2026-10-20.md (đã trên main): module schema + hàm chuẩn hóa kết quả QC hiện có sang bản ghi bằng chứng
(error_type, severity, evidence_type, confidence_calibration, artifact_id/sha, qc_run_id, qc_version, intent_exception, actionability, source_refs) + ghi
shadow (không đổi quyết định QC hiện tại). Cờ mới TẮT; cờ TẮT = byte giống. Migration bảng mới nếu cần: CHỈ code + test CSDL tạm (áp CSDL thật = Cấp 3).
```

## Việc cloud-C (làn chính chạy liên tục — người dùng 20/10: cloud-C còn nhiều token tuần)
Luật chung: như "Luật chung" + hộp thư; QC chỉ shadow/REVIEW (G2-5); cờ mới TẮT, cờ TẮT = byte giống; test ĐỎ→XANH; không API trả phí. Việc M2 chỉ bắt đầu khi
`main` có commit gộp golden M1.9 (Codex Đ20 việc 2 — tìm `git log origin/main --grep "golden"` + file tests/test_golden_replay.py) — G2-3; trước đó làm việc
không điều kiện hoặc mục DP. Mỗi việc M2 phải thêm/chạy golden compat (#24/#27 cờ TẮT = byte) bằng khung của M1.9.

#### C-M42
```
M4.2 (kế hoạch V3.1 dòng M4.2; mã G51, B8 trong devsys/errors.json + nguồn docs/DANH_GIA_*): video QC — đứng yên > 1,5 s = REVIEW, khớp khung 0 với ảnh đầu,
vật còn giữ trong tay (G51), chuyển cảnh trong video ref (B8). Ghi bản ghi theo schema M4.1 nếu DP4 đã gộp, nếu chưa thì cấu trúc tạm tương thích. Shadow:
chỉ ghi kết quả, không đổi quyết định QC / không chặn. Đo bằng ffmpeg / OpenCV trên video tổng hợp tạo trong test (lưu ý reference_opencv_opencl_hang:
tắt OpenCL — cv2.ocl.setUseOpenCL(False)). Nhánh cloud/v31-m42.
```

#### C-M43
```
M4.3 (G52, G42): cross-shot logic qua core qc_sequence_logic ở chế độ shadow — đọc code hiện có (cờ qc_sequence_logic, commit b269e88f), nối với
continuity_state thiết kế M3.4 (docs/V3_1_M3_THIET_KE_WORLD_MAP_*.md) ở mức đọc; ca: vật / trang phục / hướng di chuyển đổi giữa 2 shot liền. Shadow, không chặn.
Nhánh cloud/v31-m43.
```

#### C-M26 / C-M29 / C-M24 (BẮT ĐẦU KHI golden M1.9 gộp main)
```
Theo docs/V3_1_M2_THIET_KE_CON_LAI_2026-10-20.md (mục M2.6, M2.9, M2.4) + thiết kế M2.1/M2.2, M0.9, M0.10 đã trên main. Thứ tự M2.6 → M2.9 → M2.4.
M2.9 nghiệm thu = tests/test_narration_regression.py: ca G15/G16/G17/G53 hết xfail (gỡ dấu xfail đúng ca đã sửa; strict=True làm ca chưa sửa vẫn bắt).
M2.4 dùng write guard ở chế độ shadow nếu M2.5 chưa có (không chặn). Mỗi việc: golden compat #24/#27 cờ TẮT = byte; cờ mới TẮT; nhánh cloud/v31-m26 / m29 / m24.
```

#### C-FIX-M16-17 (cloud-C — ưu tiên NGAY sau việc đang làm; M1)
```
Sửa lỗi rà kỹ của phiên chính trên 2 nhánh (phiên chính gộp cả hai vào main khi cờ TẮT — tách nhánh sửa từ origin/main MỚI NHẤT; nếu main chưa có thì
merge origin/cloud/v31-m16 + origin/cloud/v31-m17 trước). Mỗi lỗi test ĐỎ→XANH; chạy tests/test_v31_m16_send_estimate.py, tests/test_v31_m17_ops_notices.py,
test check_no_budget_lock_gate.
M16 (cờ send_estimate): CAO core/cost.py:389 send_clip_usd tính tier qua batch._draft_tier không có parent_job_id → job gen lại / thử lại kế thừa bậc cha
(core/quality_tier.py:343–356, core/pipeline.py:395) bị báo giá nháp 480p (~1,15 USD) thay vì bước nâng 1080p (~6,36 USD): thêm parent_job_id cho clip_estimate
và send_clip_usd (tier = quality_tier.tier_for_new_job(conn, sid, parent); final → upgrade_price(ratio, sec, upgrade_input_seconds(...))), các caller step4
(:312 "↻ Gen lại clip này", :219/:233 thử lại) truyền job id. Test: job final + cờ BẬT → clip_estimate(..., parent_job_id=final) ≥ upgrade_price.
VỪA tools/pregen_check.py (~139–154): nạp LLM_PROVIDER từ dashboard.env (không phải secret) hoặc --llm-provider; in "Claude tính theo LLM_PROVIDER=X".
THẤP dashboard/model_line.py:83 dùng chung send_clip_usd / sàn bảng giá; THẤP core/cost.py:648 thêm claude_free() vào khóa _memo.
M17 (cờ stale_code_alarm): VỪA core/code_version.py:156/:164 so sha HEAD → mọi commit (kể cả TODO.md / hộp thư) báo "code cũ" giả: ghi dấu vân tay
core/ + dashboard/ (hash các .py) lúc khởi động, chỉ báo khi khác. Test: commit chỉ đổi TODO.md → stale_instances() rỗng, self_stale() None.
THẤP tools/stop_dashboard.ps1:12 chỉ in pid + cổng (không in CommandLine — có thể lộ token), -All lọc theo thư mục repo hiện tại; THẤP core/diag.py:236 plate_stale
thêm item/plate vào khóa gộp hoặc giữ at đầu + last_at; THẤP core/code_version.py:107 bỏ bản ghi pid chết / so thời điểm tạo tiến trình.
Báo cáo docs/RA_CLOUD_FIX_M16_17_2026-10-2x.md + XONG hộp thư (ghi tên nhánh thật anh push được).
```

## Hàng dự phòng bổ sung 20/10 22:20 (pool — nhận bằng `hop_thu.py ke --lane <làn> --nhan --push`)
Luật như "HÀNG VIỆC DỰ PHÒNG": Cấp 2 đã duyệt, cờ mới TẮT (cờ TẮT = byte giống), test ĐỎ→XANH, không API trả phí, không chặn gen/xuất.

#### DP5
```
M5.1 repair router theo mã lỗi — CODE theo docs/V3_1_M5_THIET_KE_REPAIR_RELEASE_2026-10-20.md (phần M5.1). G2-6: router mặc định TẮT. Bảng mã lỗi → hành động sửa
(đổi đầu vào gì — luật 6 CHUAN_XAY_DUNG) → trần ảnh ≤ 3 / video ≤ 2 → dừng hỏi người khi lặp lỗi. Khi cờ TẮT: không đổi gì đường gen lại hiện có (core/pipeline.py
retry, core/autopilot.py AUTO_REGEN_LIMIT). Khi BẬT: chỉ ĐỀ XUẤT sửa (ghi diag + bản ghi), KHÔNG tự gửi job — tự gửi là Cấp 3 (C3-10 để sau). Giữ poll_claim /
pause_before_submit / submit_unknown (đang BẬT). Test theo bảng mã (dùng devsys/errors.json làm nguồn mã).
```

#### DP6
```
M5.2 release gate — CODE theo docs/V3_1_M5_THIET_KE_REPAIR_RELEASE_2026-10-20.md (phần M5.2): checklist đo được trước xuất bản (shot đã duyệt, final QC M4.4 nếu có,
đối soát chi phí qua tools/clipai_cost_reconcile.py / sổ chi, lỗi nghiêm trọng mở trong devsys/errors.json) → báo cáo ĐẠT / CHƯA ĐẠT kèm lý do. Cờ TẮT; khi BẬT chỉ
hiện cảnh báo, KHÔNG chặn nút xuất (chặn = cần người dùng duyệt sau). Test: dự án giả đủ / thiếu từng điều kiện.
```

#### DP7
```
M4.6 khung chạy benchmark QC — CODE công cụ chỉ đọc theo docs/V3_1_M4_6_DAC_TA_BENCHMARK_QC_2026-10-20.md: định dạng bộ ca có nhãn (JSON: artifact, mã lỗi kỳ vọng,
nhãn người), `tools/qc_benchmark.py` chạy các bộ kiểm QC hiện có (shadow) trên bộ ca → bảng báo nhầm / bỏ sót theo mã + hiệu chuẩn độ tin cậy; KHÔNG gọi API trả phí
(bộ kiểm cần Claude dùng client giả trong test; khi chạy thật đi qua llm_provider theo dự án). Test bằng bộ ca tổng hợp nhỏ. Trích ca thật từ data/ là việc máy chính.
```

#### DP8
```
M3.1 scene_world_map THỬ NGHIỆM offline — CODE schema + đọc/ghi + adapter theo docs/V3_1_M3_THIET_KE_WORLD_MAP_2026-10-20.md (M3.1): 3D tọa độ thật / 2D / quan hệ
tương đối / UNKNOWN, version, provenance, invalidation khi geometry/BYĐ đổi. G2-4: chỉ offline, KHÔNG chặn gen, KHÔNG bắt buộc 3D; không ai đọc map trong luồng gen
(cờ TẮT). Lưu ở bảng/JSON mới — migration chỉ code + test CSDL tạm (áp CSDL thật = Cấp 3). Test: ca #31 cảnh 4/6/8 dạng fixture tổng hợp, map thiếu → UNKNOWN.
```

## Việc M2 bổ sung 20/10 22:45 (BẮT ĐẦU KHI golden CX20-2 GỘP — hộp thư tự mở; G2-3)
Mọi việc: golden compat #24/#27 cờ TẮT = byte bằng khung M1.9 (tests/test_golden_replay.py); BYĐ v1, Kho cũ, dự án cũ vẫn chạy; cờ mới TẮT; test ĐỎ→XANH.

#### C-M21
```
M2.1 BYĐ v2 theo docs/V3_1_M2_1_M2_2_THIET_KE_2026-10-20.md (phần M2.1): byd_v, vat[] object, shot_intent.read có provenance, mức BLOCK/REVIEW/WARN (chỉ ghi —
không tự chặn gen khi cờ TẮT; BLOCK thật = Cấp 3 sau). Adapter v1→v2 dùng parser vat v1/v2 (M1.1 đã có core/shot_intent.vat_items). Mọi caller đọc BYĐ qua adapter.
```

#### C-M25
```
M2.5 write guard cấp trường ở chế độ SHADOW theo docs/V3_1_M0_10_BAO_VE_DU_LIEU_2026-10-20.md (đặc tả + audit 34 đường ghi + 10 ca G1–G10): core/write_guard.py
write_scene(actor, expected_rev, mode='shadow') — shadow chỉ GHI diag (field_conflict, stale_write), KHÔNG chặn / không đổi dữ liệu; nối dần các đường ghi
L1–L6 qua guard ở shadow. Enforce = C3-6 (để sau). Cờ field_guard TẮT = byte giống. Quyết định đã chốt: take người chọn = USER_LOCKED; prompt khóa → REVIEW_REQUIRED.
```

#### DP9
```
M2.7 image preflight trong ImageRunner._pregen chung mã lỗi với video — theo docs/V3_1_M2_THIET_KE_CON_LAI_2026-10-20.md (M2.7). Preflight chỉ báo REVIEW/VÀNG có
mã lỗi (devsys/errors.json), cờ TẮT; KHÔNG thêm điểm chặn khi cờ TẮT. Không đụng core/runner.py phần poll/submit (M1.2/M1.3).
```

#### DP10
```
M2.8 router theo khả năng model (không gộp nhóm khi cần khung đầu/cuối, …) — theo docs/V3_1_M2_THIET_KE_CON_LAI_2026-10-20.md (M2.8). Cờ TẮT = hành vi gộp nhóm cũ.
Khi BẬT chỉ đổi cách chia nhóm trước khi gửi (không gọi API trong test; provider giả). Ghi lý do chia nhóm vào sent_package.
```

## Việc bổ sung 20/10 23:20 (cloud-C hết việc — không thuộc M2)

#### C-M47A
```
M4.7 phần XEM (chỉ đọc, cờ mới TẮT): trên Dashboard Bước 4 (dashboard/steps/step4.py, thẻ clip v2) thêm khung gập "Gói sẽ gửi" — dựng gói bằng ĐÚNG hàm dựng gói của
nút Gen (không tính tay, không gọi API), hiện thứ tự ref + nhãn + prompt + giá send_estimate nếu cờ đó bật; và khung "QC shadow" đọc kết quả M4.2/M4.3/M4.1
(video_qc.jsonl, continuity_shadow.json, qc_evidence) của shot. KHÔNG có nút sửa/override (override + bảng overrides = C3-4 chờ). Cờ TẮT = giao diện cũ y nguyên
(test ui snapshot hiện có xanh). Theo mẫu UI hiện có (dashboard/common.py, D.card).
```

#### C-M34
```
M3.4 continuity_state expected/observed/resolved + đồ thị phụ thuộc theo docs/V3_1_M3_THIET_KE_WORLD_MAP_2026-10-20.md (M3.4), chế độ SHADOW: tính trạng thái
mong đợi giữa các shot liền (vật cầm, trang phục, vị trí, hướng) từ BYĐ (shot_intent) + kết quả quan sát QC shadow (M4.2/M4.3) → ghi file/ bảng tạm, mức REVIEW,
không chặn. Cờ mới TẮT. Không đụng core/continuity_shadow.py ngoài việc đọc (C-FIX-THAP-1 vừa sửa). Test chuỗi 3 shot giả: vật mất / đổi tay / giữ đúng.
```

#### C-M32
```
M3.2 người nộm height_m trong whitebox + pitch eye / slightly_high (offline, G2-4) theo docs/V3_1_M3_THIET_KE_WORLD_MAP_2026-10-20.md (M3.2) và
docs/PHUONG_PHAP_SAN_KHAU_3D.md: hàm hình học thuần (tính chiều cao người nộm theo hồ sơ nhân vật, góc pitch máy từ độ cao mắt / hơi cao) + chỗ Blender script
đọc giá trị đó (không chạy Blender trong test — test hàm thuần + kiểm script nhận tham số). Cờ mới TẮT = whitebox cũ.
```

#### DP11
```
M3.3 câu vị trí sinh từ world map (thay tả tay từng shot, G41–G50) theo thiết kế M3 — BẮT ĐẦU KHI DP8 (M3.1 world map) GỘP. Chỉ sinh câu đề xuất + so với câu
hiện tại (REVIEW), cờ TẮT, không đổi prompt gửi đi khi cờ TẮT.
```

#### DP12
```
M5.3 pilot vòng A OFFLINE (0 USD) theo docs/V3_1_M0_11_PILOT_3_VONG_2026-10-20.md (vòng A): khung chạy 5 nhóm ca (payload, continuity, QC, lineage, phục hồi)
trên fixture golden — BẮT ĐẦU KHI CX20-2b GỘP. Tiêu chí đạt/rớt đo được; không VERIFIED khi chỉ offline. Ca cần dữ liệu thật: ghi danh sách để máy chính chụp.
```

## CHIA VIỆC THEO HẠN MỨC GÓI (người dùng 20/10 23:50)
Mỗi làn báo hạn mức thật đầu mỗi lượt (`tin … "HẠN MỨC …"`). Phiên chính chia:
| Hạn mức tuần ĐÃ DÙNG của làn | Giao |
|---|---|
| < 60 % | việc nặng: code M2, rà kỹ, việc ưu tiên 1 — làn chính |
| 60–85 % | việc vừa: sửa VỪA/THẤP, thiết kế, test bổ sung |
| 85–90 % | chỉ việc nhỏ ≤ 30 lượt gọi; không nhận việc mới lớn |
| ≥ 90 % (hoặc 5 giờ ≥ 90 %) | hoàn tất việc dở → xong → het-viec; phiên chính chuyển việc CHỜ của làn đó sang làn khác (`giao` lại cùng mã) |
Ghi nhận 20/10: cloud-B DỪNG (hết tuần); cloud-C còn nhiều tuần (làn chính); cloud-D chưa báo; codex 5 giờ 91 % lúc 23:16, tuần 29 %.

## Làn cloud-E (mở 21/10 11:40 — tài khoản cloud mới)
Prompt dán vào phiên cloud-E (kèm khối "Luật chung" ở đầu file):
```
Bạn là làn cloud-E của dự án AI Video Pipeline (repo GitHub hongvietdoan-byte/Workflow-t-ng-h-a-quy-tr-nh-l-m-video-AI, branch main). Tiếng Việt.
1. git pull; đọc CLAUDE.md, hop_thu/README.md, docs/CLOUD_TASKS.md mục "Luật chung" + "CHIA VIỆC THEO HẠN MỨC GÓI", docs/CHUAN_XAY_DUNG.md.
2. Báo hạn mức: PYTHONUTF8=1 python tools/hop_thu.py tin --lane cloud-E --to phien-chinh --text "HẠN MỨC cloud-E 5h X% · tuần Y%" --push
3. Lấy việc: python tools/hop_thu.py ke --lane cloud-E --nhan --push (việc CHỜ của cloud-E trước, rồi pool). Đề bài ở trường spec.
4. Mỗi việc: nhánh cloud/v31-<mã>, test ĐỎ→XANH, cờ mới TẮT (cờ TẮT = byte giống; thêm cờ verified False thì thêm cờ đó = false vào
   tests/golden/package_inputs.json cả image + video), khai file mới vào devsys/areas.json (không tăng version), báo cáo docs/RA_CLOUD_<MÃ>_2026-10-2x.md,
   push nhánh, rồi hop_thu.py xong <mã> --lane cloud-E --branch <nhánh> --commit <sha> --push. KHÔNG push main ngoài commit hộp thư; không sửa TODO.md.
5. Hết việc → hop_thu.py het-viec --lane cloud-E --push. Tuần ≥ 90 % → hoàn tất việc dở rồi het-viec + báo hạn mức.
```
Việc giao đầu: C-M29 (M2.9 lời dẫn ngoài khớp môi), C-M24 (M2.4 insert_scene_after) — chuyển từ cloud-C; đề `#### C-M26 / C-M29 / C-M24`.

## Việc NHỎ cho cloud-D (21/10 — tuần 89 %, mỗi việc ≤ 30 lượt gọi)

#### C-ERR-UPD2 (cloud-D)
```
Cập nhật devsys/errors.json theo các việc gộp main 21/10 (commit ffa85d2f "V3.1: gộp 9 nhánh 21/10"): CX20-5/5b M1.5 Kho chủ thể (G30, G32, G58, G59; cờ
subject_capacity_guard TẮT), DP7 M4.6 benchmark QC, C-FIX-THAP-3/4/5, C-M34 M3.4 continuity_state (G51, G52, G1), C-M32 M3.2 người nộm (G2, G3, A10, G49),
DP11 M3.3 câu vị trí (G41–G50, G46). Đọc báo cáo docs/RA_CLOUD_*_2026-10-21.md, docs/RA_D20_VIEC5B_CODEX_2026-10-21.md, docs/RA_DP7_CODEX_2026-10-21.md để
lấy mã lỗi + tên test thật. Trạng thái tối đa FIXED_UNVERIFIED (cờ TẮT, chưa chạy thật); điền fix_commit + tests + plan_workstream; KHÔNG VERIFIED.
`python -m devsys.errors check` phải "Hợp lệ"; tests/test_error_registry.py xanh. Không đoán commit/test — git log / grep. Nhánh cloud/v31-err-upd2. XONG hộp thư.
```

#### C-RA-FIX21 (cloud-D — chỉ đọc, BẮT ĐẦU KHI codex báo XONG CX21-FIX)
```
Rà độc lập CHỈ ĐỌC nhánh codex của CX21-FIX (tên nhánh trong sự kiện xong; đề: docs/CODEX_TASKS.md "### CX21-FIX"). Đọc git diff origin/main...<nhánh> +
chỗ gọi tới; kiểm từng mục 1–6 của đề đã sửa đúng gốc và có test ĐỎ→XANH; đặc biệt: core/subjects.capacity khi cờ TẮT giữ byte cũ, SPEND_LOCK không bị
giữ lúc gọi mạng, merge_union không mất mục khi hai bên khác định dạng (thử bằng 2 file tạm). Không sửa code. Báo cáo docs/RA_CLOUD_RA_FIX21_2026-10-2x.md:
GỘP ĐƯỢC / CẦN SỬA, mỗi lỗi mức + file:dòng + cách sửa. Push nhánh cloud/v31-ra-fix21 (chỉ báo cáo). XONG hộp thư.
```

## NHÁNH PHỤ SONG SONG (cloud-C, cloud-E) — người dùng 21/10 12:30 "đẩy nhanh tiến độ"
Làn cloud-C / cloud-E được chạy **tối đa 2 nhánh phụ cùng lúc** (Agent tool, `isolation: worktree`, chạy nền) ngoài việc phiên làn đang tự làm → tối đa 3 việc song song/làn.
1. Mỗi nhánh phụ = MỘT mã việc đã nhận trên hộp thư (`hop_thu.py ke --lane <làn> --nhan --push` lần lượt cho từng việc), nhánh riêng `cloud/v31-<mã>`, báo cáo riêng.
   Phiên làn (không phải nhánh phụ) đăng `xong <mã>` sau khi đọc báo cáo + `git diff --stat` của nhánh phụ.
2. Chỉ chạy song song các việc KHÔNG trùng file mã (ngoài `core/features.py`, `devsys/areas.json`, `tests/golden/package_inputs.json` — phiên chính hợp khi gộp).
   Cặp đã xét 21/10: cloud-C `C-M21` ∥ `C-M25` (M2.5 KHÔNG sửa `core/shot_intent.py`; chỉ bọc đường ghi ở shadow) ∥ `DP12`; cloud-E `DP9` ∥ `C-M29`, sau đó `C-M24`,
   `DP10` (DP10 và DP9 cùng đụng `core/runner.py` → KHÔNG chạy song song hai việc này). Nghi trùng file → chạy nối tiếp.
3. Đề bài cho nhánh phụ phải tự đủ: mã việc + đường dẫn đề (spec) + "Luật chung" + luật cờ mới TẮT/golden fixture + test ĐỎ→XANH chỉ chạy file test liên quan
   (gom MỘT lệnh pytest, ≤ 3 lần) + commit nhỏ + `HANDOFF.md` + push nhánh + báo cáo ≤ 30 dòng; KHÔNG sửa TODO.md, KHÔNG push main, KHÔNG đổi `version` areas.json.
   Tự kiểm trước khi bàn giao: test bị nới để che lỗi; đường dẫn tương đối `data/…`; chặn mới làm vỡ luồng tự động/hàng loạt; bật mặc định đổi hành vi; lời gọi tốn tiền.
4. Hạn mức: làn báo hạn mức sau mỗi việc xong. Tuần ≥ 85 % (hoặc credit ≥ $80) → không mở nhánh phụ mới, chỉ hoàn tất nhánh đang chạy.
5. Phiên chính vẫn gộp từng nhánh riêng (rà theo mức) — M2 chỉ gộp sau khi golden #24/#27 đạt (CX21-GOLDEN).

## Việc phiên chính tự đề xuất 21/10 12:50 (người dùng: "tự đề xuất và giao cho các cloud")

#### C-RA-M21-M25 (cloud-E — chỉ đọc, nhánh phụ được)
```
RÀ KỸ độc lập CHỈ ĐỌC 2 nhánh cloud-C: origin/cloud/v31-m21 (M2.1 BYĐ v2, 13 chỗ core/ chuyển sang đọc qua hàm BYĐ chung) và nhánh C-M25 (M2.5 write guard
SHADOW core/write_guard.py, gắn 6 đường ghi L1–L6) khi cloud-C báo XONG. Đề gốc: docs/CLOUD_TASKS.md "#### C-M21", "#### C-M25"; thiết kế
docs/V3_1_M2_1_M2_2_THIET_KE_2026-10-20.md, docs/V3_1_M0_10_BAO_VE_DU_LIEU_2026-10-20.md. Kiểm: cờ TẮT = byte giống (mọi caller cũ trả đúng giá trị cũ;
so cả kiểu None/""/list rỗng); shadow KHÔNG chặn/không đổi dữ liệu, không ghi CSDL thêm ngoài diag; không làm vỡ luồng tự động (autopilot, byd_fill,
director); chữ so khớp bỏ dấu; test có bị nới không. Không sửa code. Báo cáo docs/RA_CLOUD_RA_M21_M25_2026-10-2x.md: GỘP ĐƯỢC / CẦN SỬA, mỗi lỗi mức +
file:dòng + cách sửa + test chứng minh. Push cloud/v31-ra-m21-m25 (chỉ báo cáo). XONG hộp thư.
```

#### C-RA-DP9-M29 (cloud-C — chỉ đọc, nhánh phụ được; BẮT ĐẦU KHI cloud-E báo XONG DP9 / C-M29)
```
RÀ KỸ độc lập CHỈ ĐỌC nhánh cloud-E: cloud/v31-dp9 (M2.7 image preflight: core/pregen_codes.py, core/image_pregen.py, core/runner.py) và cloud/v31-m29 (M2.9
lời dẫn ngoài khớp môi). Đề: "#### DP9", "#### C-M26 / C-M29 / C-M24"; thiết kế docs/V3_1_M2_THIET_KE_CON_LAI_2026-10-20.md. Kiểm: cờ TẮT = byte giống và
0 điểm chặn mới; preflight chỉ REVIEW/VÀNG có mã devsys/errors.json; không đụng phần poll/submit runner (M1.2/M1.3); M2.9 nghiệm thu
tests/test_narration_regression.py (xfail G15/G16/G17/G53 gỡ đúng ca, strict=True). Báo cáo docs/RA_CLOUD_RA_DP9_M29_2026-10-2x.md (như C-RA-M21-M25).
Push cloud/v31-ra-dp9-m29. XONG hộp thư.
```

#### C-M25B (cloud-C — sau C-M25)
```
Câu hỏi cloud-C nêu ở C-M25: motion prompt người sửa tay chưa có dấu khóa riêng → guard chỉ báo khi trường đã khóa chung. Phiên chính chốt (theo M0.10 đã
duyệt: take người chọn = USER_LOCKED; prompt khóa → REVIEW_REQUIRED): người dùng SỬA TAY motion prompt trên Dashboard Bước 3 (và mọi đường lưu motion prompt
do người, không phải AI) → đặt khóa trường motion_prompt = USER_LOCKED cho shot đó (ghi provenance người + revision), CHỈ khi cờ field_guard BẬT; cờ TẮT =
byte giống, không ghi gì. AI/tự động sắp ghi đè trường khóa → shadow chỉ ghi diag như C-M25. Test ĐỎ→XANH: sửa tay → khóa; AI viết lại → diag
field_conflict, dữ liệu người giữ nguyên ở chế độ shadow (không chặn); cờ TẮT không ghi khóa. Nhánh cloud/v31-m25b, báo cáo docs/RA_CLOUD_M25B_2026-10-2x.md.
```

#### C-PORT4 (cloud-E — nhỏ, chỉ test)
```
4 test đỏ trên Linux/cloud nhưng xanh Windows (các làn báo "4 failed cũ"): recut_by_hand, punches, end_popup_p24, unreadable_picture (tìm bằng
grep -rn trong tests/: test_end_popup_p24.py, test_cost_route_e1.py, test_ffmpeg_studio.py, test_sent_package.py…). Chạy trên cloud, tìm gốc (đường dẫn
\ vs /, font/ffmpeg thiếu, phân biệt hoa thường, encoding…). Sửa test (hoặc code nếu lỗi thật đa nền tảng) để xanh cả hai; thiếu công cụ hệ thống thì
skipif có lý do rõ — KHÔNG nới assert. Báo cáo gốc từng test docs/RA_CLOUD_PORT4_2026-10-2x.md. Nhánh cloud/v31-port4. XONG hộp thư.
```

## Việc chuyển từ codex sang cloud (người dùng 21/10: "giao cho phiên cloud khác hỗ trợ codex trong thời gian nghỉ")

#### C-GOLDEN2 (cloud-C — ưu tiên 0; mở khóa gộp M2)
```
Nghiệm thu golden #24/#27 lần 2 (21/10, công cụ CX21-GOLDEN đã gộp main) vẫn KHÔNG ĐẠT: 68/68 INSUFFICIENT_INPUT, 0 CODE_MISMATCH. Kết quả + fixture ở máy chính
(D:/AI-Video-Output/golden-snapshot-2/ — cloud KHÔNG đọc được; dưới đây là đủ chẩn đoán). Sửa tools/golden_capture.py + tools/golden_db_replay.py (+ test):
(a) Video bản final (submit_final_from_sample, prompt rỗng): source_job_id trỏ job ẢNH, bản nháp video ở draft_job_id → đi theo draft_job_id (29 ca).
(b) ĐỔI ĐỊNH NGHĨA COMPAT (phiên chính chốt theo ý D08 "cờ mới TẮT = byte giống"): máy chính đang BẬT 83 cờ verified False (project_prop_lock,
    plate_anchored_image, video_pregen, two_tier_quality…), nên đòi "mọi cờ verified False TẮT" làm 0 ca thật nào COMPAT. Mới: file cờ structured có
    `baseline_flags` = trạng thái cờ sản xuất lúc chụp (như lúc gửi) + `experimental_flags` = các cờ MỚI của V3.1 (danh sách tường minh do người chụp
    đưa, phải TẮT). COMPAT = dựng lại với baseline_flags + experimental TẮT ra đúng byte gói đã gửi. Ghi rõ vào tests/golden/README.md; giữ fail-closed khi
    thiếu cờ trong catalog.
(c) Model: public-config {} làm dựng ra seedance-fast thay vì seedance-2.5/kling (job 667/657/660/879/909/915/839/790) → lấy model/provider từ cột
    jobs.model (và provider) của chính job, không từ cấu hình chung.
(d) pregen_fingerprint gắn NGOÀI _build_package → tái tạo bằng đúng hàm tạo fingerprint, hoặc so tách riêng trường này (ghi rõ) — job 846 chỉ lệch trường này.
(e) Builder đòi file plate/asset KHÁC file trong refs đã gửi (dữ liệu sân khấu/Kho đổi sau ngày gửi) → xếp DATA_CHANGED có lý do, không INSUFFICIENT_INPUT.
(f) `golden_capture.py --help` lỗi UnicodeEncodeError cp1252 khi thiếu PYTHONUTF8 → reconfigure stdout utf-8.
(g) CX21-GOLDEN (e) nếu chưa có: test cần worker Python 3.14 → skipif khi không có (cloud 3.13), lý do rõ.
Test ĐỎ→XANH bằng fixture tổng hợp cho từng mục. Không sửa core/ (chỉ đọc hàm builder). Nhánh cloud/v31-golden2. Báo cáo docs/RA_CLOUD_GOLDEN2_2026-10-2x.md
kèm LỆNH chụp lại cho phiên chính (máy chính chạy). XONG hộp thư.
```

#### CX21-FIX2 → cloud-C (nhỏ): đề ở docs/CODEX_TASKS.md "### CX21-FIX2" (merge_union: mục một bên xóa bị sống lại). Nhánh cloud/v31-fix2-21.
