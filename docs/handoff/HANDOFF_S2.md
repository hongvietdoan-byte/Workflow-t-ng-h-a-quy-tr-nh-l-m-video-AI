# HANDOFF — phiên S2 (gói gửi video: công thức prompt + ref), 13/10

Nhánh: `worktree-agent-a3be4f74faac6c593` (tách từ main ee2e45c7). Chưa push. Nguồn: `docs/handoff/DANH_SACH_SUA_CHUOI_2026-10-13.md`
(S2), `docs/handoff/RA_GOC_VIDEO_P27_2026-10-13.md` V1, V4, V5, V8, V9, V10, V13.

## Đã làm (0 USD, không gọi API; "đã sửa" = test giả lập, CHƯA thử thật)
| Lỗi | Cờ | File | Hành vi |
|---|---|---|---|
| V1 | `plate_view_sentence` (MỚI, TẮT) | seedance_refs `_place_sentence`, `plate_view`, `place_pictures(starts=)` | Bỏ câu "render decides architecture"; khung đầu quyết bố cục + khoảng cách máy; render khác góc / chưa đo → câu "from ANOTHER camera position" |
| V4 | `skill_object_guard` (đang BẬT ở máy chính) | skill_objects `_EN_FIXES`, `guard_prompt`, `skin_sentence`, `deployed_*`, `send_issues` | "elevator skin" → "patterned skin" (không "metal-panel"); câu skin "printed surface pattern on one solid block"; dòng DEPLOYED → "skin pattern shown in Image N"; shot vật mọc lên + Kho thiếu ảnh nhãn "triển khai"/"deployed" → ĐỎ trước gửi clip (`prompt_formula.red_issues` kind motion) kèm gợi ý GHÉP |
| V5 | `ref_mark_off_face` (đang BẬT) | seedance_refs `mark_style`, `step_mark_back`, `mark` | Không bao giờ eye_plus khi cờ bật (kể cả ảnh khung đầu, kể cả sau từ chối, kể cả dòng cũ `ref_mark=eye_plus`); từ chối "người thật" → bậc tuyến ngay |
| V8 | `group_keep_approved` (MỚI, TẮT) | seedance_refs `_groups`, `person_kept` | Nhóm có shot NGƯỜI duyệt (review_log user, còn khớp ảnh + motion) lẫn shot chưa đạt → nhóm bỏ, mỗi shot đi riêng; nhóm duyệt hết giữ nguyên (bản cao theo nhóm) |
| V9 | `motion_consistency_lint` (MỚI, TẮT) | prompt_formula `bleed_issues`, `consistency_issues`, `beat_issues` | VÀNG: diễn xuất có động tác của shot kề; số nhịp > số giây. POV cầm súng trong diễn xuất: ĐỎ đã có từ 12/10 (`pov_hand_issues`, test thêm) |
| V10 | `character_state_lock` (MỚI, TẮT) | seedance_refs `character_states`, `state_sentences`, `shot_motion`; prompt_formula `state_issues` | Câu "X stays <state> for the whole shot…" trong motion code viết + VÀNG thiếu ảnh trạng thái |
| V13 | `ref_rule_early` (MỚI, TẮT) | seedance_refs `pad_to_rule`, `_rule_ok_picture`, `reference_rule_issues`; prompt_formula `_clip_send_reds` | Không có ảnh đạt luật → đệm nền trơn (data/ref_padded, không ghi vào thư mục Kho) + diag; còn sai → ĐỎ ở red_issues (xếp / autopilot / batch / readiness), không đợi lúc gửi |

Test đỏ trước (16 fail trên mã HEAD) → xanh sau: `tests/test_seedance_send_s2.py` (12), `tests/test_skill_objects.py`
(`test_guard_keeps_skin_reference_not_plain_metal`, `test_rising_skill_object_without_deployed_picture_blocks`),
`tests/test_prompt_formula.py::MotionConsistencyV9` (3 đỏ→xanh + `test_pov_performance_weapon_flagged` xanh sẵn),
`tests/test_ref_mark_off_face.py::test_real_person_refusal_goes_down_the_ladder_never_back_to_the_eye_mark` (đổi theo hành vi V5).
Bộ liên quan chạy: 233 passed (seedance_refs, prompt_formula, director_prompt_formula, code_motion_p27, feature_settings, devsys,
prop_lock, skill_objects, ref_mark_off_face, vi_names_p24, kld_seedance_price, test mới).

## Cần phiên khác nối (file tôi không được sửa)
1. **runner.py — V1**: truyền `starts={r["id"]: self._start_frame(pid, r["id"]) for r in rows}` vào MỌI lời gọi
   `seedance_refs.place_pictures` (≈ 1010 `_ref_lint`, 1366 `_render_gap`, 1396 `_reference_pictures`, 1735 prompt) để render cùng góc
   được câu "same"; ghi diag khi view None/"other" (lý do ở `plate_view()["why"]`). Chưa nối: mọi render đi câu "góc máy khác" (an toàn).
   Phần (2)(3) của báo cáo V1 (shot static không gửi plate) CHƯA làm: bỏ plate sẽ vấp lint "thiếu render địa điểm 3D" ở `_ref_lint`.
2. **runner.py — V4**: gửi `skill_objects.deployed_pictures(conn, pid, rows)` sau render trong `_reference_pictures` (extras), truyền
   `objects=` vào `seedance_refs.prompt` (≈1742) và đếm trong `_ref_lint` (n_pictures / n_expected) — hiện ảnh dạng triển khai CHƯA được gửi,
   chỉ có ĐỎ khi Kho thiếu. Kling (start frame) cũng nên gửi ảnh này làm ref.
3. **runner.py — V5**: nhánh `step_mark_back` (≈1897–1900) giờ không bao giờ chạy — có thể xóa diag "gửi lại với dấu trên mắt".
4. **runner/end_frames — V8**: khi shot đã duyệt đứng trước, shot còn lại nên lấy khung cuối phần đã duyệt làm khung đầu + đo nối bằng
   `framing_guard.similarity` (báo cáo V8) — chưa làm. Job follower `queued` cũ của shot đã duyệt (nếu có) sẽ thành job đơn lẻ.
5. **V10**: ảnh danh tính dạng trạng thái (cắt từ khung đầu đã duyệt) thay ảnh Kho dạng thường — chưa làm (cần runner/identity).
   Motion code đã lưu không tự viết lại khi bật cờ (chỉ khi lineage báo motion cũ).

## Rủi ro
- V4 + V5 chạy dưới cờ ĐANG BẬT ở máy chính (`data/feature_settings.json`): đổi chữ gửi ngay khi gộp. V4 ĐỎ chặn clip shot "tường keo mọc
  lên" của dự án có Bom keo trong Kho mà chưa có ảnh nhãn "triển khai" (autopilot/batch thấy qua `group_red_issues`, giữ job).
- V5: bỏ bậc eye_plus → sau 1 lần từ chối "người thật" là đổi tuyến (single → Kling) sớm hơn trước.
- Chưa có agent rà khâu liên quan (quy ước 7): đề bài `py tools/related_areas.py` — khu vực step1, step4, autopilot, budget (cost.groups),
  lipsync (dialogue_take dùng prompt/lint_group). Cả bộ test chạy ở bước gộp.

## Vòng sửa sau rà (13/10, theo `docs/handoff/RA_S1_S2_2026-10-13.md` mục 1–8; quyết định người dùng 21:31: tường keo XUẤT HIỆN LUÔN)
- **Bỏ ĐỎ V4 / bỏ ý "mọc lên"** — `skill_objects.send_issues` giờ chỉ VÀNG "chưa có ảnh dạng triển khai, skin tả bằng chữ" (Kho thiếu
  ảnh), đi kèm `issues()`; `_clip_send_reds` không còn gì từ vật kỹ năng → shot ném keo không bị giữ. Mục "Rủi ro" V4 ĐỎ ở trên HẾT hiệu lực.
- `standing_text` (gọi trong `guard_prompt`): câu vật kỹ năng (hoặc "it pops up") đổi rise/grow/emerge/erupt/shoots up/pops up/mọc/trồi
  → "already standing at full height" (chủ ngữ phải là tường/it/tên Kho; "the camera rises", "Kelly rises", "the sun rises" giữ).
  `FORBID` thêm "It appears at once at full height, never grows, rises or emerges."; `director_note` dặn không tả mọc; ghép code mặc
  định cắt cứng (`rise=0` ở `composite_frames`/`compose`/CLI); chữ diag runner + nhãn cờ `skill_object_guard` theo "xuất hiện luôn".
- `skin_sentence`: chữ chung "The glue wall skin …" (qua `sanitize`); `forbid_sentence` bỏ tên Kho có chữ thang máy/cửa, bỏ dấu.
  "elevator" đơn → "patterned".
- `readiness._formula` (video) hiện ĐỎ `_clip_send_reds` (kể cả cờ công thức tắt). runner `_finish_kwargs` ghi `note_sent` theo
  `mark_style()` thật; xóa nhánh chết `step_mark_back` trong `_on_refused`. `reserve(conn, pid, text)`: +140 chỉ khi prompt có vật kỹ năng.
  `pad_to_rule(path, conn)` → `pad_dir`: cạnh file CSDL đang dùng, không có thì cạnh `PIPELINE_DATA` (không theo `__file__`).
- Test đỏ→xanh: 13 (skill_objects 8, seedance_send_s2 3, readiness_f5a 1, ref_mark_off_face 1). Agent rà khâu liên quan (quy ước 7): không lỗi chặn; đã sửa ngữ pháp "has risen/will rise/rose", "it" chỉ tính trong câu vật kỹ năng hoặc ngay sau; docstring `_clip_send_reds`. `step_mark_back` giữ (luôn False, test dùng).

**Việc cho S3:** (1) khung cuối (`end_frames` / end_state của shot ném keo) dùng CÙNG câu "already standing at full height" (gọi
`skill_objects.standing_text` / `STANDING`), không tả mọc; (2) nối `skill_objects.deployed_pictures` vào `_reference_pictures` +
`objects=` cho `seedance_refs.prompt` + đếm trong `_ref_lint` (Kling: làm ref); (3) truyền `starts=` vào mọi `place_pictures` (V1).
