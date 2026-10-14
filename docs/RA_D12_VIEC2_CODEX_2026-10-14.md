# Rà nhánh Đ12 việc 2 — SFX theo nhịp
- Nhánh: codex/d12-viec2-sfx-nhip; base 2c43a28f; areas.version giữ 74.
- Code: core/motion_sfx.py, core/sfx_plan.py adapter propose_motion, core/features.py.
- UI: dashboard/motion_sfx_ui.py component độc lập; KHÔNG nối caller step5 đang do Claude giữ.
- Đỏ 16 ImportError + 55 related xanh; lần xanh đầu 71/13,12s.
- Tự rà bổ sung 2 ca đỏ (quyền trước đọc, tên Bo không thành bò); sửa rồi nhóm cuối 77/11,10s.
- Lệnh: py -m pytest -q -p no:cacheprovider --tb=no tests/test_motion_sfx.py tests/test_sound_intent.py tests/test_sound_classification.py tests/test_post_fx.py
- dict environ giả trước import/call trong fixture mới; không khóa/provider/API thật.
- OFF/không opt-in không đọc clip/CSDL/catalog/LLM; prompt/propose/apply cũ không đổi dòng.
- Adapter guard need_view trước timeline; apply giữ need_edit hiện có, component chỉ xem proposal.
- Nhịp BYĐ + động từ motion → bảng code; không chọn theo tên file.
- Catalog duy nhất sfx_plan.catalog (sound_lib.TRUSTED_SQL); thiếu loại âm → unmet + VÀNG, không thay âm khác.
- Mốc đo: motion_series chỉ frame_activity_peak_s; semantic_action_measured=False.
- Máy xác nhận static: cue đỉnh/motion có thể dùng timestamp peak, time_source=frame_activity; alignment vẫn estimated + VÀNG.
- Máy không rõ/đang chạy, thiếu/quiet/dải lỗi/NaN/negative → uniform_byd + VÀNG; không coi là động tác đã đo.
- post_fx dùng validate + filter_for đúng schema; cue chung noise, không dựng/ghi âm tự động.
- Sound đã lỗi thời được cảnh báo theo loại; bỏ thoại và mệnh đề phủ định, không đọc ai thành động tác.
- Loại âm không trong bảng được unmet; Claude chỉ đề xuất trong thông báo, không có đường gọi API.
- related_areas đã chạy: step5/core_infra + callers autopilot/dashboard/common/step5 chỉ dùng API cũ.
- Các caller cũ không gọi adapter mới; autopilot không bật tính năng, widget key cũ nguyên vẹn.
- Diff check + py_compile xanh; không thay delivery/ffmpeg_studio/step5/data/env/runner/admin_auth.
- Chưa chạy clip thật, UI 1440/1280, cả bộ Windows; test đo dùng series giả.
- Giới hạn: trusted accent catalog hiện có thường chưa chứa footsteps/rustle/hiccup/noise; báo thiếu thay vì mở guard.
- Chưa hoàn thành UI sản xuất/Claude bổ sung có báo giá; chờ caller được giải phóng và root review.
- Không TODO/PLAN/commit/push/main/live/spawn; root cần fresh review trước commit.

## Vòng sửa sau rà độc lập — 3 P2
- P2 neo overlap: shot 1 dài 4 s, shot 2 bắt đầu 3 s; cue cuối shot 1 ở 3,95 s trước đây bị `anchor` gán shot 2. Cue nhịp nay giữ `anchor_idx`/`offset`; `apply` kiểm mã sound/shot, số hữu hạn, offset đúng timeline và shot thuộc project TRƯỚC mọi ghi/xóa âm. Cue legacy tiếp tục suy neo theo thời điểm như cũ.
- P2 numeric: `start`/`length=10**1000` trước đây ném OverflowError. `finite` bắt overflow; tổng start+length tràn bị loại cùng cảnh báo VÀNG trước đo/sinh cue.
- P2 motion cũ: adapter trước chỉ đọc `scenes.data.motion_en`; nay JOIN prompt hiện tại từ `motion_prompts`, ưu tiên prompt không rỗng. BYĐ có loại hành động không còn trong prompt → cảnh báo xung đột và bỏ loại âm cũ; sound stale so theo nguồn mới.
- ĐỎ trước sửa: test mới 14 failed / 23 passed, 0,34 s. XANH sau sửa: 92 passed / 10,90 s; bổ sung guard idx SQLite lớn, test dựng lại và teardown environ thiếu/có → nhóm cuối **96 passed / 11,24 s**.
- Một nhóm kiểm: `py -m pytest -q -p no:cacheprovider --tb=no tests/test_motion_sfx.py tests/test_sound_intent.py tests/test_sound_classification.py tests/test_post_fx.py`; `git diff --check` xanh.
- Test adapter/apply dùng SQLite `:memory:`, các thao tác audio/filesystem/đo/guard được mock; environ giả trước import/call, không đọc/in secret, không API/provider/model thật.
- QA Chrome 1440/1280 chưa chạy: Python hiện tại không có Playwright; không cài thư viện hay chạm Dashboard sản xuất. UI component vẫn chưa nối caller đang được phiên Claude giữ.

## Chốt rà lần 2 + QA component
- Root phát hiện thêm 2 ca biên: cue explicit có sound thiếu/file mất/volume lỗi có thể xóa âm cũ; guard idx > 0 loại nhầm shot idx 0 hợp lệ. ĐỎ 4 failed → sửa prevalidate âm Kho + file cục bộ + volume hữu hạn 0,1–1,5 trước mọi ghi; idx 0 chỉ được áp khi thuộc DB project và timeline.
- Sentinel âm AI cũ không bị xóa/thêm khi âm thiếu/file mất/volume NaN; test shot idx 0 trên SQLite tạm xanh. Cue legacy vẫn theo đường cũ.
- Nhóm cuối 4 file **100 passed / 11,06 s**, `--tb=no`; diff check xanh.
- QA đã dùng Playwright Node bundled, không cài thêm. Chrome headless thoát ngay (exitCode 0); fallback Edge headless riêng thành công, không dùng profile/browser người dùng.
- Streamlit fixture riêng loopback 8554, stub `features.on`/`propose_motion` + module registry/credentials/providers/models; child env whitelist trước spawn/import, không dữ liệu/API/key thật. Đã dừng đúng PID server fixture sau mỗi lượt.
- Edge 1440×900 và 1280×900: mở expander → opt-in → bấm code → summary/cues/unmet + 3 warning; mỗi cỡ proposal stub gọi 1 lần, paid calls 0, console/page errors 0, horizontal overflow false. Chờ animation expander xong rồi chụp và xem ảnh.
- PNG: `docs/images/d12/motion_sfx_1440.png`, `docs/images/d12/motion_sfx_1280.png`. Đây là component giả, chưa UI Dashboard sản xuất, caller Bước 5 vẫn deferred.
