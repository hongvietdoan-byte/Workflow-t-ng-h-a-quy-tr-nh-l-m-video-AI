# Kế hoạch: Đạo diễn + Biên tập viên duyệt bản dựng thô, tối ưu vai Dựng (nháp 2026-10-02 — chưa code)

> **Quyết định người dùng 02/10:** (2) hai vai Đạo diễn + Biên tập viên thống nhất với nhau (mục 5b); (4) trần tiền P2+P4 ≤ 1,5 USD;
> (1) ngưỡng A/B và (3) chép intent vào `scenes.data` còn chờ — đề xuất của tôi: không chép, dùng một hàm đọc `intent_for(scene)` từ
> `director_intent_raw` kèm fingerprint.

Nguồn: rà soát bộ 3 vai ngày 02/10 (vai Dựng không có Claude nào quyết; không ai xem cả bản dựng với mắt người xem) và khảo sát code
(`delivery.render`, `final_qc`, `story_check`, `llm_runner`, `cost`, `experience`). Mọi con số giá là **ước tính từ bảng giá**, chưa đo thật.

## 1. Mục tiêu và giới hạn trung thực
- **Mục tiêu:** thêm một "người giám sát" sau khi ghép bản thô: Claude (vai Đạo diễn/Biên tập) đối chiếu **ý đồ** (đỉnh cảm xúc, trọng tâm,
  thời lượng, ý đồ âm thanh) với **bản dựng thật** (khung hình quanh điểm cắt + số đo âm), chỉ ra chỗ nhịp chùng / cắt hụt / nhạc đè / đỉnh
  không được nâng, và đề xuất chỉnh **bằng các núm có sẵn**. Người dùng duyệt, code áp, dựng lại.
- **Giới hạn đã biết (phải nói trong prompt và giao diện):**
  1. Claude nhìn khung hình lấy mẫu, không nghe được nhịp thật; âm thanh chỉ vào dưới dạng số. Bài học GĐ3 (`reference_qc_model_sees_but_misreasons`):
     model khai **quan sát theo danh sách đóng**, code áp luật kết luận — không để model tự kết luận trái/phải, đúng/sai.
  2. Chưa có bằng chứng việc này làm bản dựng hay hơn. Kế hoạch coi đó là **giả thuyết cần đo** (mục 7), không phải kết quả.
  3. Không đụng việc đã chốt: luật cứng (độ to, vùng an toàn, thoại nguyên văn) vẫn là code.

## 2. Vị trí trong pipeline
- Bản thô = `data/projects/<pid>/output/FINAL_VIDEO.mp4` + manifest (`timeline`, `loudness`, `sound_intent`, `music_breaths`), do `delivery.render()`
  (`core/delivery.py:400-508`) tạo, **trước** lớp phụ đề / end card / nhãn AI / xuất (`deliver()` ~:818).
- Móc: một bước mới `editor_review` giữa `render()` và `subtitle_layer` trong `deliver()`; ở autopilot là pha mới sau `sfx` (`autopilot.py:934`),
  mẫu `_story_check_phase` (:1263): cờ + `ctx.llm` + bắt `LlmError` + cảnh báo, **không bao giờ dừng chạy**.
- `render()` hiện không có chỗ chèn chỉnh sửa và bị khóa (`_locked`, :133) → áp đề xuất = **dựng lại có đổi đầu vào** (ffmpeg, 0 USD); chặn bằng luật 6:
  chỉ dựng lại khi đầu vào đổi, tối đa 2 vòng, cùng lỗi 2 lần thì dừng và báo.

## 3. Đầu vào cho Claude (đủ, không cắt âm thầm — luật 1)
| Nhóm | Nội dung | Lấy từ | Ghi chú |
|---|---|---|---|
| Ý đồ | mỗi cảnh: `emotional_intent`, `peak`, `focus`, `target_s`, `editor_notes`, `sound`; shot: `money_shot` | `director_intent_raw` + `scenes.data` | **Quyết định D1:** `peak/focus/target_s/editor_notes` chỉ nằm trong `director_intent_raw` (có thể cũ khi Director chạy lại). Chép vào `scenes.data` lúc merge (luật 4: một nguồn) |
| Đồng hồ | danh sách shot: cảnh, bắt đầu–kết thúc (s), thoại/không, `transition_in`, `speed`, có `lip_sync` | `manifest["timeline"]`, `delivery.cut_times` | code tính sẵn "độ dài shot so với `target_s` của cảnh" |
| Hình | khung hình trước/sau mỗi điểm cắt (±0,3 s) + khung đỉnh `peak` + khung `money_shot`, **ghép thành ≤ 12 tấm** có nhãn giây | ffmpeg trích | giới hạn cứng `MAX_IMAGES = 12` (`llm_runner.py:35`); vượt thì chia nhiều lời gọi **và báo** "thấy N/M khung", không im lặng bỏ |
| Âm (số) | độ to nhạc/thoại mỗi giây, khoảng lặng, sự kiện nhạc (vào/ra/to lên), LUFS, đỉnh | `ffmpeg_studio.measure_loudness`, `final_qc.silent_spans`, numpy | **Không dùng demucs/whisper/torch** (không có trong `requirements.txt`; `tools/audio_listen.py` chỉ là công cụ tay). Số nhạc/thoại riêng lấy từ các file âm đã tách sẵn trong audio_lib/manifest |
| Sách nghề | các luật phán đoán của Dựng (xem mục 6) | `knowledge/editor/editing.md` qua `role_text` | hiện **không được nạp ở đâu** |

## 4. Đầu ra của Claude: quan sát + đề xuất theo danh sách đóng
Một JSON, mỗi mục: `at_s`, `scene`, `observed` (enum), `evidence` (trường/số cụ thể từ đầu vào), `action` (enum), `amount`, `why`.
- **`observed` (Claude khai):** `drag` (chùng), `rush` (dồn), `cut_off_beat` (cắt lệch nhịp thoại/hành động), `peak_unsupported` (đỉnh không có shot đủ dài/đủ gần),
  `music_competes` (nhạc to khi có thoại/đỉnh), `silence_wanted` (đỉnh cần lặng mà không lặng), `transition_jarring`, `flat_run` (nhiều shot cùng cường độ), `other` (+lý do).
- **`action` (chỉ những núm có thật, theo khảo sát):**
  | action | núm | giới hạn code |
  |---|---|---|
  | `shorten_shot` / `extend_hold` | `durations` của `render()` | không đụng shot thoại/khớp môi; không dưới `MIN_SHOT_S`; tổng trong ±max(1 s, 15%) `target_s` |
  | `music_cue` | `sound.music` của shot (`keep|cut|in|breath`) | `MAX_OFF_S = 8`, `MIN_ON_S = 4` (`sound_intent.py`) |
  | `transition` | `transition_in` của shot (`cut|crossfade|dip_to_black`) | chỉ tại đổi cảnh; ≤ N lần |
  | `slow_or_freeze` | `speed`, `freeze_end_s` | chỉ shot không thoại; 1–2 lần/phim; cờ `speed_ramp` (chưa verified → chỉ **đề xuất**, không áp) |
  | `suggest_flag` | bật `j_cut` / `motion_trim` / `speed_ramp` thử A/B | không tự bật; chỉ ghi gợi ý cho người dùng |
  | `retrim_from_raw` | cắt lại từ `<tên>_raw.mp4` (`shots.trim_clip`) | **ngoài giai đoạn 1** (chỉ ghi vào báo cáo) |
- **Code kiểm trước khi hiện:** vượt danh sách → bỏ và ghi; chung một chỗ có hai đề xuất mâu thuẫn → giữ cái ưu tiên cao theo thang chung (`roles/README.md`: thoại rõ > chữ đọc được > nhịp > liền mạch > đẹp);
  tối đa 6 đề xuất mỗi vòng (tránh "sửa tất cả" làm hỏng nhịp); mỗi đề xuất có `why` + `evidence` thật, thiếu thì bỏ.
- **Không có "chấm điểm cảm xúc" bằng số** — tránh số giả chính xác.

## 5. Quy trình và cổng người dùng
1. `render()` → bản thô.  2. Code dựng đầu vào + ước tính tiền.  3. Một lời gọi Claude (stage mới `editor`).  4. Code kiểm → danh sách.
5. Giao diện Bước 5: bảng "chỗ nào / thấy gì / đề xuất / trước→sau" + khung hình chứng cứ; người dùng tick duyệt từng mục.
6. Áp các mục đã duyệt → dựng lại (vòng 2 nếu còn mục) → `final_qc` phải **không tệ hơn** bản thô (số lỗi chặn, độ to, lỗ nhạc).
7. Giữ cả hai bản (A/B) để người dùng đối chiếu.  **Autopilot:** chỉ chạy bước 1–4 và lưu báo cáo; không tự áp (luật 6: không tự duyệt). Chế độ "tự áp lớp an toàn"
(vd. chỉ `music_cue`) chỉ cân nhắc **sau** khi đo ở mục 7.

## 5b. Hai vai thống nhất (quyết định 02/10)
1. **Biên tập viên** (lời gọi Claude 1, stage `editor`): xem khung hình + số đo, đọc khối `<!-- review -->` của `editing.md`, đề xuất theo danh sách đóng (mục 4).
2. **Đạo diễn** (lời gọi Claude 2, chỉ chữ, không ảnh): đọc ý đồ gốc + đề xuất; mỗi mục chọn `agree` / `object` (kèm lý do dẫn ý đồ) / `modify` (trong danh sách đóng).
3. **Code tổng hợp:** hai bên đồng ý → đi tiếp; bất đồng → xếp theo thang ưu tiên chung; vẫn hòa → hiện cả hai lý do, người dùng quyết. Không có vòng tranh luận thứ ba.
Hạn chế: cùng một model nên không độc lập hoàn toàn — giá trị là góc nhìn thứ hai theo thang ưu tiên, không phải hai ý kiến khác nhau.

## 6. Tối ưu vai Dựng (ai thực thi luật nào)
Hiện `editing.md` (33 KB) dùng chung một giọng cho luật code, luật phán đoán và tư liệu. Việc cần làm:
- Gắn **chủ thực thi** cho từng luật E1–E12: `code` (đã có hàm), `prompt` (Claude phán đoán, vào bước duyệt bản thô), `người` (chưa tự động, nhắc ở giao diện). Thêm bảng "luật → file/hàm thực thi" (thay các câu "nạp prompt" sai).
- Khối `<!-- review -->…<!-- /review -->` trong `editing.md` cho phần phán đoán (E1 ưu tiên hy sinh, E2 nhịp, E3 nền không khí, E4 nhạc/lặng, E6 chuyển cảnh/rung, E9 tự rà, E12 tư liệu), đồng bộ cách `director.md` dùng `role_text`; phần số cứng (E7 vùng an toàn, E8 độ to) **không** nạp (code giữ).
- Sửa E3/E6/E1 còn nghĩa cố định thành "tùy ý đồ" (đã nêu ở rà soát) — vì từ nay model đọc chúng.
- Nhờ vậy cũng giải xong mục 1 của rà soát: `editing.md` được nạp thật, ở đúng khâu cần phán đoán.

## 7. Cách đo có hiệu quả không (luật 5 và 8 — không bật mặc định khi chưa thử thật)
- **Phép thử A/B mù trên dự án đã có (#8 và thêm 2 dự án):** bản thô (A) so với bản đã áp đề xuất (B); người dùng xem **không biết** bản nào. Ghi chọn A/B/ngang nhau + lý do một câu.
- **Chỉ số:** (a) tỷ lệ đề xuất được duyệt, (b) tỷ lệ B được ưa hơn A, (c) `final_qc` B không tệ hơn A, (d) số đề xuất bị bác kèm lý do (nuôi bộ lọc).
- **Ngưỡng đề xuất (người dùng chốt):** bật cờ `rough_cut_review` verified khi B được ưa hơn hoặc ngang ở ≥ 2/3 dự án **và** không dự án nào B tệ rõ rệt. Nếu không đạt thì giữ làm công cụ báo cáo, không áp.
- **Ghi kinh nghiệm:** mỗi đề xuất được duyệt/bị bác → `experience.record(stage="editor_review", outcome=success|false_alarm, confirmed_by=người dùng)`;
  thêm stage vào `lessons.GROUP_OF_STAGE`; khâu sau đọc để bớt đề xuất kiểu cũ đã bị bác. (Hiện `experience.relevant` chỉ đọc `qc_image` → sửa cho nhận stage mới.)

## 8. Chi phí (ước tính, chưa đo)
- Một vòng = 1 lời gọi Sonnet 5 (2/10 USD mỗi triệu token vào/ra): ≈ 12 tấm × 1400 token + ~8k chữ ⇒ ~25k vào, ~3k ra ⇒ **≈ 0,06–0,10 USD**, ×1,3 biên (`cost.LLM_MARGIN`) ≈ 0,13 USD. Thêm lời gọi Đạo diễn (chỉ chữ) ≈ 0,03–0,05 USD ⇒ ≈ 0,17 USD/vòng, hai vòng ≈ 0,34 USD.
- Worst-case khóa theo `max_tokens`: 12k ra ≈ 0,12 USD < `MAX_CALL_USD = 1`.
- Dựng lại: ffmpeg, 0 USD. Phép thử A/B ở mục 7: 3 dự án × ≤ 2 vòng ≈ ≤ 1 USD; **cần người dùng duyệt trước khi chạy**.
- Khóa cứng (feedback_hard_cost_locks): stage mới `editor` phải có `STAGE_SETTINGS` (effort thấp/vừa, `max_tokens` ~12000) — nếu không rơi vào 32k mặc định và bị từ chối vĩnh viễn ở dự án đã khóa ngân sách (bài học 01/10); ánh xạ vào `project_budget.STAGES` (không để rơi `claude_other`);
  thêm `cost.LLM_STAGE_TOKENS`; nút hiện ước tính trước; cache theo fingerprint (đầu vào không đổi thì không gọi lại).

## 9. Ma trận luồng (luật 2) — phải kế thừa
Bước 5 bấm tay · autopilot · v2 · v3 từng shot · multi-shot · nhân bản dự án · chạy lại Director (intent đổi ⇒ báo cáo cũ hết hiệu lực qua fingerprint). Mỗi luồng một test; điền bảng kế thừa của `CHUAN_XAY_DUNG.md` mục 49–59 khi làm.

## 10. Lộ trình (mỗi giai đoạn có thể dừng độc lập)
| GĐ | Việc | Sản phẩm / test | Tiền | Điều kiện sang GĐ sau |
|---|---|---|---|---|
| **P0 ✅ 02/10** | Chuẩn bị: ~~chép vào `scenes.data`~~ → hàm đọc `director_two_pass.intent_all/intent_for` (người dùng chốt, không chép); thêm cờ `rough_cut_review` (verified False), stage `editor` vào `STAGE_SETTINGS`/`project_budget`/`cost`; bảng chủ thực thi E1–E12 + sửa tài liệu sai | test cấu hình, test kế thừa intent | 0 | — |
| **P1 ✅ 02/10 (chưa thử trên bản dựng thật)** | **Chỉ đo, không Claude:** trích khung quanh điểm cắt, ghép tấm ≤ 12, bảng đồng hồ + số đo âm, cảnh báo code (shot lệch `target_s`, `peak` không có shot ≥ 2 s, lặng/nhạc bất thường). Hiện ở Bước 5 như 🧐 hiện có | `core/rough_cut.py` + test fixture #8 | 0 | người dùng thấy bảng đo hữu ích? |
| **P2 ✅ 03/10 (code + test giả lập, CHƯA chạy Claude thật)** | Lời gọi Claude **chỉ báo cáo** (không áp): prompt 24 + khối `<!-- review -->` của `editing.md`; kiểm code; hiển thị; ghi `diag`/kinh nghiệm | prompt, validate, test `MockLlm` (mẫu `test_story_check.py`) | ước tính ≤ 0,15 USD/lần; **thử thật cần duyệt** | báo cáo trên #8 có chỗ đúng thật? (người dùng chấm từng mục) |
| **P3 ✅ 03/10 (test dựng thật bằng ffmpeg; chưa thử trên dự án thật)** | Áp đề xuất đã duyệt + dựng lại + `final_qc` không tệ hơn + giữ A/B | núm `durations`/`sound.music`/`transition_in` nhận danh sách; test chống vượt giới hạn | 0 (ffmpeg) | không lỗi chặn mới |
| **P4** | Phép thử A/B mù 3 dự án (mục 7), ghi kết quả vào `TODO`/báo cáo; quyết định `verified` | báo cáo A/B | ≤ ~1 USD (duyệt trước) | đạt ngưỡng ở mục 7 |
| **P5** | Vòng kinh nghiệm: `experience` cho `editor_review`, bộ lọc đề xuất đã bị bác; cân nhắc `retrim_from_raw` và "tự áp lớp an toàn" | test | 0 | — |

## 11. Rủi ro
- **Model nhận xét sai nhịp** (nhìn khung hình, không nghe) → danh sách đóng + người duyệt + chỉ báo cáo ở P2.
- **Sửa tất cả làm phim mất cá tính** → trần 6 đề xuất/vòng, thang ưu tiên chung, A/B mù.
- **Intent cũ (stale)** → fingerprint gồm intent; chạy lại Director thì báo cáo hết hạn.
- **Tốn token vì ảnh** → mosaic ≤ 12 tấm, cache, stage riêng có trần.
- **Trùng việc với `story_check`/`final_qc`/`viewer_check`** → ba bước đó đo truyện / kỹ thuật / vùng an toàn; bước mới chỉ đo **nhịp và cảm xúc so với ý đồ**; dùng chung hàm đo, không đo lại.

## 12. Cần người dùng quyết
1. Đồng ý ngưỡng "B ≥ A ở ≥ 2/3 dự án" và dự án nào dùng cho A/B (đề xuất #8 + 2 dự án mới).
2. Đồng ý tên vai: "Biên tập duyệt bản thô" do Đạo diễn đảm nhiệm (một lời gọi, cùng stage `editor`), hay tách vai Biên tập riêng trong `knowledge/roles/`.
3. P0 chép `peak/focus/target_s/editor_notes` vào `scenes.data` (đụng luồng Director hai lượt) — đồng ý?
4. ~~Trần tiền P2 + P4~~ — **người dùng chốt 02/10: ≤ 1,5 USD tổng**; khi chạy thật vẫn hiện ước tính trước.
