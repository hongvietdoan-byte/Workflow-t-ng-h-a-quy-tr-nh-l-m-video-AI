# Rà ĐỢT 6 việc 1 — post_fx

Nhánh `codex/d6-viec1-post-fx` · nền `858804f` · code `f9603c7`.

- Schema: `post_fx={loai,vi_tri,thoi_luong_s,cuong_do}`; loại nhieu_song/glitch/nhap_nhay, vị trí dau/cuoi/ca_shot; thời lượng >0 và ≤ clip, cường độ (0,1]. Shot không có post_fx giữ nguyên; có yêu cầu nhưng sai/thiếu → VÀNG có lý do.
- `delivery.render` áp sau fit/color/flashback/edge/end_hold. Dùng output atomic riêng, không ghi đè nguồn; audio copy; chẩn đoán `post_fx_warning` và manifest.
- `post_fx_render` mặc định TẮT; helper thoát trước đọc CSDL/ffmpeg. Module khai areas, version giữ 48.
- Rà độc lập theo `tools/related_areas.py`: đường dựng chung delivery/rough_cut/editor_apply/animatic/autopilot/compare, giữ ACL của render và paths theo rows. Không sửa dashboard, runner, lock_exceptions, dữ liệu thật.
- Hai P2 tìm thấy: huge integer làm OverflowError; test ffmpeg thật thiếu guard khi ffmpeg không có. Đã sửa; số quá lớn thành VÀNG, shot sau tiếp tục, fixture chỉ skip test thật.
- Lượt hai đối chiếu skill 2b.5: không nới test, paths tuyệt đối, cờ tắt giữ đường cũ, batch tiếp tục sau lỗi shot, không API/Blender/tiền hoặc đổi quyền. Không có widget đổi key.
- Test đỏ đầu: module chưa có → ImportError. Hồi quy rà: hai huge-integer test đỏ OverflowError → xanh. Một lượt giữa lỗi ghi Unicode của công cụ, đã sửa cách ghi, không đổi assert.
- Lệnh nhóm cuối: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider tests/test_post_fx.py tests/test_keep_audio.py tests/test_final_cut.py` → **43 passed, 10,18 s**. `git diff --check` xanh.
- Ffmpeg thật trên clip tổng hợp nhỏ: 3 loại giữ duration (<0,06 s), giữ audio, gốc/cờ tắt byte giống; khung cuối khác cả nguồn và đối chứng cùng filter enable=0. Tích hợp delivery với CSDL tạm chứng minh manifest/diag và shot lỗi không làm mất render.
- Chưa xem hiệu ứng trên phim sản xuất, chưa chạy cả bộ. Bên Claude phải rà bản tích hợp, chạy cả bộ Windows (related_areas báo test chậm bắt buộc) trước gộp; chưa bật cờ hoặc restart máy chính.
