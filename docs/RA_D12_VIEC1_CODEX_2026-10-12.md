# Tự kiểm Đ12 việc 1 — 12/10/2026

Nhánh `codex/d12-viec1-am-nen`, nền `08c11b4`. Chưa commit/push; chờ RÀ KỸ độc lập vì migration + dữ liệu được chọn.

## Phạm vi và nghĩa dữ liệu
- `voice` ghi mới chỉ là giọng người theo nhãn chính AST/YAMNet; `accent` là điểm nhấn nhận dạng trong ACCENT, luôn loại VOICE.
- Schema mới có `accent INTEGER` nullable. Migration chỉ ADD COLUMN theo pattern hiện có; không viết lại các hàng cũ, không nghe lại và không đổi heard/voice/score/path.
- NULL phân biệt bản cũ với kết quả nghe mới (0/1). Khi đọc, nhãn chính VOICE luôn chặn dù voice cũ sai là 0. Nhãn non-human đã biết (ACCENT + danh sách môi trường) trên hàng legacy được phục hồi voice=0. Nhãn lạ/không nghe giữ cờ voice cũ: unknown voice=1 vẫn chặn, unknown voice=0 vẫn giữ fallback theo tên của ambience.
- Danh sách môi trường cố ý bảo thủ; nhãn non-accent cũ ngoài danh sách vẫn giữ voice cũ. Mô hình tải động không cần đọc/tải để phân loại legacy.
- `TRUSTED_SQL` đòi nhãn ACCENT được nhận dạng + ngưỡng TRUST + không VOICE + accent NULL/1. Dế/gió/toilet không lọt vào điểm nhấn dù stored voice=0. `sfx_plan.catalog` và autopilot cùng dùng SQL này.
- `ambience.choose` đổi guard sang VOICE_SQL, giữ nguyên tên/nhãn chính đáng tin, duration >=8, file tồn tại, ưu tiên từ khóa rồi dài nhất. Không đổi mix/volume/timeline/render.

## Rà các chỗ gọi và kiểm 2b.5
- rg core/dashboard/tools: chỉ sound_lib.listen ghi sounds.voice; ambience đọc trực tiếp, sfx_plan/autopilot dùng TRUSTED_SQL. Không phát hiện SQL đếm giọng của Kho hay UI Kho cần đổi. Các voice của TTS/nhân vật/audio_lib là dữ liệu khác.
- Không nới assert có sẵn. Fixture mới gồm #437 Cricket/#307 Wind cũ voice=1, Speech sai voice=0, unknown voice=1, âm cũ chưa nghe voice=0, Explosion, Toilet flush. Fixture fallback đổi tên Wind old thành Gió old để kiểm đúng thứ tự từ khóa mà không tranh thứ tự với Wind đã nghe (không đổi assert).
- Migration test CSDL tạm: bỏ cột accent của schema để mô phỏng bản cũ; connect lại xác nhận ADD COLUMN với NULL và giữ voice=1/label/score.
- Không đường dẫn data thật, không API/ASR/model download, không đổi env/cờ, không ghi TODO/PLAN, không động các file cấm. Dữ liệu chỉ tempfile và SQLite in-memory.
- Không thêm guard ở luồng trả tiền/hàng loạt/autopilot; chỉ thay predicate chọn âm và cột lưu kết quả nghe sẵn có. Không mạng mới, không phụ thuộc cwd mới.
- Nhãn dùng lower(trim) chính xác toàn nhãn; không bỏ dấu, không so chuỗi con với VOICE/ACCENT. Âm nền giữ matcher whole-word cũ.

## Bằng chứng và giới hạn
- Chạy gom `py -m pytest -q -p no:cacheprovider tests/test_sound_classification.py tests/test_sound_lib.py tests/test_editor_cuts.py` với PYTHONUTF8=1, tối đa 3 lượt.
- Đỏ bản cũ: 3 failed / 51 passed (56,98 s): Cricket bị coi voice, ambience #437 None, thiếu cột accent.
- Lượt 2: 1 failed / 53 passed (51,16 s); fixture tranh từ khóa Wind, đã sửa fixture như trên.
- Lượt 3: 54 passed (48,81 s).
- Chưa thử Kho thật #24, chưa chạy cả bộ; không nói đã xác nhận chất lượng thật. Chưa merge. RÀ KỸ cần kiểm lại các nhánh legacy/null/unknown và chỗ gọi.
- `related_areas.py`: step5/core_infra; gọi tới autopilot/dashboard_ui/assets/step2/knowledge/step1, dùng chung cờ step3. Test CHẬM bắt buộc ở bước gộp: editor_apply/editor_review/rough_cut/ui_v2_acceptance. Người điều phối chạy cả bộ Windows trước merge.

- Kiểm bổ sung SQLite query_only=ON: chọn #437 từ voice=1/Cricket, catalog rỗng, so toàn hàng trước–sau giữ nguyên; không UPDATE khi đọc.

## RÀ KỸ độc lập và vòng sửa duy nhất
- Phiên rà độc lập: 0 lỗi chặn gộp, 1 điểm LOW: summary dùng lower nhưng SQL dùng lower(trim), làm nhãn có khoảng trắng phân loại không nhất quán.
- Đã sửa: khóa phân loại strip().lower(), giữ nguyên nhãn gốc để hiển thị. Regression gồm padded Speech/Explosion, unknown, whitespace, rỗng và VOICE giao ACCENT (VOICE thắng).
- Đỏ: test mới test_summary_normalizes_classification_but_preserves_label — 1 failed / 0,20 s, Speech có khoảng trắng bị ghi voice=False.
- Xanh: gom tests/test_sound_classification.py + tests/test_sound_lib.py + tests/test_editor_cuts.py — 55 passed / 50,49 s.
- Migration kiểm độc lập trước sửa: 1 passed / 0,21 s; ADD COLUMN nullable giữ voice/label/score cũ.
- Rà callers: ambience dùng VOICE_SQL; sfx_plan.catalog/autopilot dùng TRUSTED_SQL; listen ghi hai cờ từ cùng kết quả nghe. UI không có guard sounds.voice riêng cần đổi.
- Không cập nhật dữ liệu thật, không nghe model/tải xuống/API, không chạy cả bộ. Test CHẬM bắt buộc tại tích hợp theo related_areas; chưa commit/push.
