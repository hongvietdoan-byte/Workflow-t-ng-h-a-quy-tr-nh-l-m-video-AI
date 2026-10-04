# HANDOFF — S14.4 phần C1b (nhánh `s14-c1b-data-knowledge`, 04/10)

Nguồn: `docs/KE_HOACH_NANG_CAP_DASHBOARD_2026-10-03.md` mục 3.3 (từ `sync_knowledge` tới hết "Khác (nhỏ)") + mục 8 dòng J1.
0 USD, không gọi API thật. Không sửa `TODO.md`, chưa push/merge main.

## Đã làm (mỗi việc: test đỏ trước → xanh sau)
1. **Người nói CTA/TITLE** — `core/dialogue.py`: `NOT_SPEAKERS` thêm CTA, CTA TEXT/CTA_TEXT, TITLE, SUPER, SUBTITLE, LOGO, CHỮ TRÊN MÀN…;
   `is_non_speaker(name)` so không dấu (trừ `CHỮ`→`chu`: chỉ khớp khi có dấu, nhân vật tên CHU vẫn nói). Dùng chung ở
   `idea_to_script` (bỏ `_ON_SCREEN_SPEAKERS`), `script_parser._characters` (đường kịch bản DÁN), `shots`, `speaker_lint`,
   `shot_normalize`, `director_report`, `director_two_pass`, `llm_io`. Test: `tests/test_b3_b4_fixes_2026_10_01.py::B4Tests`.
2. **diag stage** — `core/diag.py`: `normalize_stage()` + `STAGE_ALIASES` (videos/images/image_gen/video_gen/delivery), thêm hàng
   `voice`, hàng `other` ("Khác") chỉ hiện khi có stage lạ; `record()` chuẩn hóa khi ghi; `stage_table` gộp cả dòng cũ ghi tên khác.
   Sửa hằng: `autopilot.py` 511–519 (`images`), 544/575 (`videos`), `lipsync.py:174`, `delivery.py:475`, `qc_agent.py:722`
   (chỉ đổi đúng dòng hằng). `devsys/areas.json`: step3 thêm `voice`, step5 bỏ `delivery` (KHÔNG tăng `version`);
   `devsys/collect.py diag_summary` chuẩn hóa tên. Test: `tests/test_diag.py::StageNameTests` (có test quét hằng stage).
3. **Bài học** — `knowledge.replace_doc` (dựng + kiểm trần, không tính tài liệu sắp thay, rồi mới xóa cũ); `lessons.decide` lỗi →
   trả trạng thái cũ + `LessonError` tiếng Việt; `admin.py` nút Duyệt/Bỏ/Gỡ qua `act()`; `LessonError` vào `common.ERRORS`.
4. **research.run** — kết quả không phải object: bỏ qua, đếm vào `errors`, ghi diag.
5. **J1** — câu lỗi `SchemaError`/`ValueError`/`KeyError` ở `llm_io`, `director_two_pass`, `editor_review`, `story_check` sang tiếng
   Việt; `ask_json` sai 2 lần → tiếng Việt + cách xử lý; thiếu `DEEPIX_TOKEN` → tiếng Việt + cách xử lý; thẻ ngân sách dự án
   hiện lý do + cách xử lý (+ diag). Test quét: `tests/test_j1_vietnamese_errors.py`.
6. **knowledge.GROUPS theo `film_crew`** — `CREW_REPLACES`/`CREW_DOCS`: bật cờ thì 3 tài liệu cũ ghi "không gửi", thêm
   roles/director.md, roles/dp.md, editor/editing.md (editing.md ghi "gửi ở khâu Editor", không cộng vào số ký tự Director).
7. Khác (nhỏ): Kiểm Bible/Character Lock báo ảnh Kho mất file (diag `library_file_missing`); Biên kịch cộng tiền lượt lỗi vào trần;
   so thoại theo `Counter` (`llm_io._check_lines`, `director_report.report`); `audio_lib.missing_in_mix` + diag khi ghép;
   `_MINOR_AGE` (profile_digest) bắt aged 17/17yo/17 tuổi/seventeen-year-old/age 16; `asset_vision.pending` khớp `_eligible`;
   `features.REQUIRES` (dialogue_take cần lip_sync) + 🧪 ghi "không có tác dụng"; người nói thiếu ảnh định danh → diag
   (`seedance_refs.identity_pictures`, code `speaker_no_identity`); `qc_worse` so cả mức chặn.
   Kèm: sửa test chập chờn `test_feature_settings` (cache `features.settings()` cùng mtime sau 2 lần lưu liền).

## Sửa theo rà soát độc lập (04/10)
1. `tests/test_role_books_docs.py`: bỏ cấm chuỗi editing.md trong `knowledge.py`; thay bằng kiểm mục editing.md có `elsewhere=True`
   và không cộng vào số ký tự Director (vẫn cấm editing.md trong `prompts.py`, cấm `safe_zones`).
2. Alias stage `translate→motion`; test quét hằng stage mở rộng sang `_run`/`claude_tasks._run` (đối số 3, chấp nhận alias vì là
   nhãn chi phí) và `_retry_note`/`_note`.
3. `knowledge.replace_doc`: thêm-mới + bỏ-cũ trong MỘT lần `_save`; `_save` ghi nguyên tử (tmp + replace); lỗi → xóa file mới.
4. `lessons.sync_knowledge` (không còn bài duyệt): lỗi `remove_doc` → `LessonError` tiếng Việt, bài học giữ trạng thái cũ.
5. Dịch nốt: `ask_text` sai 2 lần; `knowledge.set_enabled/remove_doc` không tìm thấy tài liệu.
6. `seedance_refs`: diag `speaker_no_identity` chỉ ghi khi chưa có cùng nội dung trong 10 phút (không phồng `count`).

## Chưa làm (để nhánh khác, theo giao việc)
`_SPENT_CACHE`; hợp nhất danh sách khâu Claude (+ khâu riêng STAGE_SETTINGS cho 4 việc Claude nhỏ); Meshy; Blender;
`location_pack.cache_key`; `effectiveness`.

## Rủi ro cần rà khi gộp
- `core/autopilot.py`, `core/lipsync.py` đang được nhánh khác sửa: ở đây chỉ đổi 7 dòng hằng stage (511, 513, 515, 517, 519, 544, 575)
  và 1 dòng (lipsync 174) — xung đột (nếu có) chỉ là đổi chuỗi.
- `devsys/areas.json` đổi `diag_stages` → fingerprint khu vực step3/step5 đổi; `version` để nhánh tích hợp tăng.
- `NOT_SPEAKERS` rộng hơn (LOGO, SUBTITLE, TITLE…): nhân vật thật tên trùng các chữ này sẽ không được tính là người nói.
- Câu lỗi `SchemaError` giờ tiếng Việt → câu "hỏi lại" gửi Claude cũng tiếng Việt (prompt vốn tiếng Việt).
- `seedance_refs.identity_pictures` giờ ghi diag (gộp 10 phút) mỗi lần gọi khi người nói thiếu ảnh.
