# Bàn giao Đ12 việc 6

Nhánh codex/d12-viec6-phat-am, base1ab50785. Chưa commit/push; root điều phối rà độc lập và QA trước commit.

Đã làm: từ điển chữ thuần theo characters.voice_profile dự án/giọng/model; setter need_edit → writer set_profile. generate áp trước submit, fingerprint chữ hiệu lực/voice/model, giữ cache unrelated; cờ OFF+OPT_IN_ONLY. Manual dictionary đổi giữ audio cũ tới settle success; failed phục hồi old. ASR model local-only so câu gốc VÀNG+gợi ý, unavailable VÀNG, không download/mạng. UI editor JSON expander; nút TTS cũ đếm stale.

Bằng chứng: tests/test_tts_pronunciation.py + tests/test_voice_casting.py: 28 passed/2.48s. Đỏ module chưa tồn tại; xem RA ghi lượt kiểm. Không API/model thật/data thật/main/pull live/restart/TODO/PLAN. areas.version67 nguyên.

Còn: rà độc lập related_areas; QA component thật 1440/1280 (dashboard.tts_pronunciation_ui.render(p,pid,tempdata), fakeDB), ảnh docs/images/d12; kiểm tương thích Đ12v5 khi gộp cả hai trên nhánh tích hợp; cả bộ Windows merge operator. Chưa thử thật 'Trồi Lên' giọng70.

Vòng sửa độc lập 13/10: 5 finding đã xử lý + bảng2cột/ASR cache/actionbutton. ASR ngoài khóa; patch readfresh identity/state/mtime; atomic-save/manifest lock. Quyền view không ghi/ASR; malformed dictionary báo rõ và chặn send. 6 đỏ →86 xanh nhóm4file/9,74s; bổ sung guard và4test→27 pron xanh/3,79s. Không có tests/test_voice_check.py; audio_g2 bao gồm voice_check/settle_redos đã xanh. Xem RA phần vòng sửa để biết giới hạn concurrency writer cũ, legacy thiếu model và ma trận unison.
QA fixture thật Streamlit chạy localhost8617 `?role=edit` / `?role=view`, PID91892, script `%TEMP%\d12-v6-review-qa\app.py`. AppTest rolesnone/view/edit/owner xanh; CUA browser unavailable/inventory[] nên root cần ảnh Chrome1440/1280 + đọcdiff cuối. Chưa commit/push/fullsuite/gộp/thử giọng70; tuyệt đối chưa bật cờ mặc định.

## Chốt rà và QA của root
- Đã đọc diff cuối; đăng ký thêm cờ tts_pronunciation vào khu vực step3, giữ areas.version 68 đúng HEAD 1ab50785.
- Nhóm cuối: 90 passed /7,80s (4 file pronunciation, voice_casting, audio_lib, audio_g2), PYTHONUTF8=1, no:cacheprovider.
- Chrome Playwright trên thành phần Streamlit thật, DB/ASSET_DIR/flags/knowledge tạm: quyền sửa và chỉ xem ở 1440/1280, 0 lỗi trang/Streamlit, không tràn ngang. Root đã xem đủ 4 PNG docs/images/d12/pronunciation_{edit,view}_{1440,1280}.png; bảng và nút đúng quyền. Server QA 8617 đã dừng.
- Không gọi API/model thật; chưa nghiệm thu phát âm giọng 70. Cả bộ Windows và tương thích hai nhánh khi tích hợp vẫn cần người gộp kiểm.
