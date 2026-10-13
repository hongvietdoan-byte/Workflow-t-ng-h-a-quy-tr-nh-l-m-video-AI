# Rà Đ12 việc 6 — phát âm TTS

## Đánh giá trước build
| Phương án | Lợi ích | Chi phí/rủi ro | Quyết định |
|---|---|---|---|
| Từ → chữ TTS theo giọng trong dự án | Sửa riêng ca Trồi Lên, không đổi phụ đề | 0 USD lưu/kiểm; tạo lại cần người bấm và trả TTS | Làm tối thiểu |
| SSML/phoneme | Có thể chính xác hơn | Adapter ClipAI chỉ nhận text, không chứng minh support | KHÔNG NÊN LÀM |
| ASR có sẵn local | Phát hiện lệch chữ gốc, gợi ý từ điển | ASR có thể sai; không tải model/mạng | VÀNG, người nghe quyết |
| Tự tạo lại | Tiết kiệm thao tác | Tốn tiền, chưa thử phát âm thật | KHÔNG NÊN LÀM; 0 lượt tự động |

Cờ OFF + OPT_IN_ONLY. Từ điển giữ trong voice_profile hiện có (dự án/nhân vật/voice/model), writer kiểm quyền. Cache chỉ đổi khi chữ gửi hoặc model/voice đổi; thay từ không có trong câu không làm mất cache. Bản đã có giọng giữ tới khi người bấm tạo lại. Không sửa dữ liệu thật; chỉ fixture.

## Bằng chứng và giới hạn
- ĐỎ: tests/test_tts_pronunciation.py không import được module chưa tồn tại. XANH nhóm cùng test_voice_casting: 26 qua /12,40 s; bản cuối 28 qua /2,48 s.
- Có bốn lượt pytest nhóm: đỏ, xanh, kiểm bổ sung (1 hỏng fixture), xanh cuối. Fixture bổ sung từng đổi sai cả state superseded thành succeeded; sửa đúng chỉ hoàn tất running, không nới assert.
- Fixture CSDL Pipeline thật → voice.generate thật → audio_lib thật → voice_check.settle_redos thật; provider giả nhận chữ gửi. OFF→ON→OFF không tự gửi lại; sửa mục không có trong câu không stale; câu gốc nguyên; lần manual lỗi provider phục hồi giọng cũ.
- WAV local 1 s + ASR giả báo 'Gồi lên' → VÀNG. Mock constructor chứng minh local_files_only=True; không cài/tải model, không gọi mạng/API.
- Tự rà 2b.5: không bỏ dấu; whole phrase longest single pass; không động paths sản xuất; quyền setter server; cờ OFF/OPT_IN_ONLY; không tự gửi lại khi dictionary stale.
- related_areas chạy với PYTHONUTF8=1: step3/core_infra; caller autopilot, lipsync, budget, dashboard và các caller features. Cả bộ Windows bắt buộc bước gộp thuộc merge operator; worker không chạy.
- Đ12v5 157084cf: khác tại planned_lines, old lookup/unison metadata, timeline/cues. Đ12v6 không thay planned_lines/cues/lipsync: sau gộp cần giữ unison lookup trước guard pron, extra unison_* độc lập extra pronunciation. Không merge nhánh hay sửa live.
- Chưa thử giọng 70/model thật, chưa chứng minh cách viết ví dụ 'Trờ ôi lên' sửa được phát âm. Không preset tự bật. Tự gen lại 0 lượt.
- Rà độc lập và Chrome QA1440/1280 giao root trước commit.

## Rà kỹ độc lập + vòng sửa gộp (13/10)
- Nền `1ab50785`; rà 5 finding: mất entry khi ASR giữ snapshot; đường dẫn vượt dự án; cache unavailable không kiểm lại; render ghi với quyền view; stale count khác generate với legacy có model lưu. Đã sửa chung, chưa commit/gộp.
- `audio_lib`: khóa manifest liên thread/process dùng chung `_save`/`patch_manifest`; ghi temp + `os.replace`. ASR ngoài khóa; lúc ghi đọc fresh và chỉ patch identity gồm asset/scene/line/file/text/pronunciation/state còn trùng, mtime còn đúng. Không thêm lại entry đã xóa/cancel/superseded, không xóa job mới. Thay đổi này không chuyển toàn bộ các luồng writer cũ thành transaction read-modify-write; các race writer cũ ngoài tính năng này chưa được xử lý toàn diện.
- Path: loại drive/UNC/absolute/traversal bằng cú pháp trước stat/ASR; resolve containment loại symlink/junction vượt audio_assets. Thiếu file/đường dẫn sai ghi VÀNG rõ, không hiện đường dẫn ngoài dự án.
- ASR: model riêng local-only cache theo VOICE_ASR_MODEL; không tải/mạng. Cache check gồm model/version; unavailable không khóa lần kiểm sau. UI chỉ kiểm khi bấm nút 0USD; generate và render không tự ASR. Chưa chạy Whisper thật/model thật.
- Quyền: render need_view trước SQL; view khóa bảng và cả hai nút, không tạo thư mục/ghi manifest; action check need_edit trước đọc; writer save vẫn need_edit. AppTest thật 4 role none/view/edit/owner chứng minh không có ASR tự động và edit/owner bấm check mới gọi.
- Giao diện dùng bảng hai cột “Cụm gốc” / “Chữ để TTS đọc”; key scoped voice/model. Từ điển hỏng báo rõ ở UI, generate chặn trước paid send; không bỏ qua ngầm. Chưa hoàn tất ảnh Chrome 1440/1280: CUA hiện không có browser (iab unavailable, inventory []); root tiếp tục tại fixture 8617.
- Shared helper changed() cho generate/stale_lines; legacy có model explicit đổi model được đếm; legacy không lưu model không suy đoán để tạo lại tốn tiền. OFF/ON vẫn giữ giọng khi chữ hiệu lực không đổi; dictionary không xuất hiện trong câu không tạo stale.
- ĐỎ: 6 lỗi hồi quy mới / 8 cũ xanh. XANH: 86 test (pronunciation + voice_casting + audio_lib + audio_g2) /9,74s. Có lượt fixture UI sai thiếu added_at gây 2 lỗi, đã sửa fixture đúng schema, không nới assertion. Sau guard malformed + 4 test bổ sung: 27 pronunciation xanh /3,79s. `tests/test_voice_check.py` không tồn tại; tests voice_check/settle_redos trong `test_audio_g2.py` đã chạy cùng nhóm.
- Bằng chứng callback ASR fixture: append job mới giữ nguyên; delete không revive; state cancelled/failed/superseded không patch; source text đổi không patch; unavailable→available xanh; failed atomic replace giữ manifest cũ và dọn temp; need_edit denied không đọc manifest.
- Không API/data thật/env/live/main/TODO/PLAN/commitpush; areas.version giữ nguyên. Cả bộ Windows và Đ12v5 trên nhánh tích hợp thuộc root/merge operator. Chưa chứng minh “Trờ ôi lên” sửa đúng giọng70.

### Ma trận tương thích giữ khi gộp Đ12v5
| Luồng | Đ12v6 | Điều kiện gộp Đ12v5 |
|---|---|---|
| Manual | đổi chữ hiệu lực/model, by_person mới gửi lại; giữ old→settle | lookup theo unison voice/speaker trước guard pronunciation; mỗi take metadata riêng |
| Autopilot | stale succeeded/running giữ bản cũ; không ASR tự động, không retry do check | không tạo unison take phụ khi OFF; không duplicate primary |
| Subtitle/ASR/lipsync | extra.text nguyên gốc; pronunciation.sent_text riêng | giữ unison timeline/cues; không dùng sent_text làm subtitle |
| Failed/refused/cancel | settle phục hồi old; check không revive entry | hợp đồng redo_of/redo_token chung, giữ entry old đúng voice |

## Chốt rà và QA của root
- Đã đọc diff cuối; đăng ký thêm cờ tts_pronunciation vào khu vực step3, giữ areas.version 68 đúng HEAD 1ab50785.
- Nhóm cuối: 90 passed /7,80s (4 file pronunciation, voice_casting, audio_lib, audio_g2), PYTHONUTF8=1, no:cacheprovider.
- Chrome Playwright trên thành phần Streamlit thật, DB/ASSET_DIR/flags/knowledge tạm: quyền sửa và chỉ xem ở 1440/1280, 0 lỗi trang/Streamlit, không tràn ngang. Root đã xem đủ 4 PNG docs/images/d12/pronunciation_{edit,view}_{1440,1280}.png; bảng và nút đúng quyền. Server QA 8617 đã dừng.
- Không gọi API/model thật; chưa nghiệm thu phát âm giọng 70. Cả bộ Windows và tương thích hai nhánh khi tích hợp vẫn cần người gộp kiểm.
