# Rà Đ17 việc 2 — popup cuối từng shot (12/10/2026)

Root đã đọc diff vòng sửa trước commit: `diag` dùng import module, selector giữ USABLE, guard đường shot/hash trước IO, cleanup bọc toàn bộ temp, save/parser giữ quyền; ca video đầu ra đã normalize trước staged/replace/cleanup. UI chỉ thêm guard sai kiểu, layout/key giữ đúng hai PNG đã kiểm. Không lặp nhóm/QA khi không có thay đổi bố cục; test malformed UI đã xanh. Giới hạn lookup legacy end-popup không local_root vẫn ghi rõ, chưa thử thật #27/cả bộ Windows.
Nhánh `codex/d17-viec2-popup-shot`, base `3fa1a61c`; chưa commit/push.

| Ý | Lợi ích / rủi ro | Quyết định |
|---|---|---|
| Popup theo shot | Ca #27 shot 20; có trim/fade/clip nhóm | Timeline theo clip thực đã dựng |
| Tách nền xanh | Icon #432; có thể mất màu xanh thật | Checkbox chủ động, chỉ xanh nối biên, giữ source |
| Khung cắt | Chưa có ca bắt buộc | Để sau |
| UI | 21 shot tránh 21 hàng chỉnh | Một shot chọn, giữ key pid/sid |

Triển khai core/shot_popup.py; tái dùng end_popup + subtitles.safe_box; cờ TẮT/OPT_IN_ONLY.
Delivery và draft nối popup theo scene_id/path; không thêm khung giữ; thiếu/cấu hình lỗi → VÀNG diag + manifest.
Hash bật theo spec/bytes icon+sound/platform; OFF giữ hash/render cũ. areas khai module/test/cờ, version giữ 62.
Quyền save: need_edit + scene thuộc dự án trước UPDATE; không API/lời gọi trả tiền.
ĐỎ ban đầu module ImportError; caller draft HEAD chưa gọi popup. XANH triển khai: 71 passed + 10 subtests, 25,00 s.
FFmpeg thật temp: 2×2s crossfade .25 → 3.75s; popup [1.5–2.0], pop 1.5s; held=0; RMS trong pop>.01, ngoài<.001.
Pixel thật safe-box TikTok/portrait, nền xanh mất và xanh kín icon giữ; GUI 1440/1280 do root kiểm riêng.

## RÀ KỸ độc lập và vòng sửa gộp
1. P1 delivery.py diag local có điều kiện → UnboundLocalError khi popup VÀNG. Đã tái hiện caller memory/temp; bỏ import local, test output/manifest/diag vàng xanh.
2. P1 đường không tin cậy tới exists/hash/probe: guard URL/UNC/device/ADS/reserved-name/badtype trước IO; lỗi không in raw path; tương đối neo LOCAL_ROOT. Mọi call popup shot có local_root dùng rawSQL tránh assets.get kiểm IO trước guard.
3. P2 end_popup mkdtemp trước finally → tiếng mất/start sai rò temp. Đã tái hiện; toàn bộ sau mkdtemp trong try/finally; test renderer partial dọn staged/work, source nguyên.
4. P2 UI JSON []/null/số sập .get; save không kiểm spec. Parser dict chung + validate trước UPDATE; test panel warning, invalid spec no-write, quyền giữ nguyên.
Selector rawSQL giữ assets.USABLE None/approved/claude_ok, sort/id; bỏ pending/rejected và thử ảnh usable tiếp khi ảnh đầu mất. Test riêng ĐỎ→XANH theo root rà diff.
Nhóm ĐỎ mới 13 ca; selector ĐỎ thêm 1 ca. Có một lượt collection lỗi quote SQL test và đã sửa ngay, không đổi assertion.
Nhóm cuối: `py -m pytest -q -p no:cacheprovider tests/test_shot_popup.py tests/test_end_popup_p24.py tests/test_post_fx.py tests/test_delivery_resolution.py`: **102 passed + 10 subtests, 22,87 s**.
Root đọc diff bắt thêm video/staged raw UNC: normalize video trước timeline/staged/replace/cleanup; đường lỗi trả VÀNG không IO. Focused `-k output_video`: 6 ĐỎ → **6 xanh, 0,21 s**, gồm relative video ngoài cwd.
related_areas đã đọc callers; git diff --check và compileall xanh. Không suite rộng/cả bộ/API/data thật/main/commit/push.
Giới hạn: nhánh legacy end_popup cfg không local_root giữ assets.get cũ; guard trước lookup Kho mới chỉ bảo đảm cho mọi popup shot. Không sửa tổng quát assets.
Còn mở: root đọc diff sửa, GUI sau parser nếu cần, cả bộ Windows trước gộp và thử sản xuất/bật riêng do phiên gộp.
