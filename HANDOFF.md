# Bàn giao Đ13 việc 1 phần độc lập — 14/10/2026
- DONE mục 1/3/5; nhánh codex/d13-viec1-post-fx từ 2c43a28f; chưa commit/push.
- Mục 1: post_fx tên shot + SHA256 sourcebytes/spec/seconds/filter/encode, luôn render qua atomic_output; failure giữ bản trước.
- Mục 3: rule 6 director_p24_1110 có schema đầy đủ, cổng p24_lessons giữ nguyên; OFF prompt byte-identical.
- Mục 5: rough_cut mang manifest.post_fx và Editor append context sau post_fx_render; conditional fingerprints tránh cache report cũ.
- Test rgbashift: đọc -filters actual; thiếu thì skip chỉ glitch, lỗi khác không skip; tất cả effect thật local đã qua.
- Đỏ 5 failed/103 passed → xanh cuối 108 passed/45.11s; 3 lượt nhóm 5 file liên quan.
- Proof shell: py C:/Users/hongviet.doan/AppData/Local/Temp/d13_v1_proof.py (launcher ngoài repo).
- Launcher thay os.environ OBJECT bằng dict giả trước import pytest/modules; native Popen explicit env whitelist; context managers teardown.
- Red fakeabsent, green fakepresent; MockLlm/mocks ở tests cũ; không API/khóa/data thật; --tb=no.
- pytest group: tests/test_d13_post_fx.py tests/test_post_fx.py tests/test_p24_lessons_1110.py tests/test_editor_review.py tests/test_rough_cut.py -q -p no:cacheprovider --tb=no.
- File đổi: core/post_fx.py, core/rough_cut.py, core/editor_review.py, knowledge/roles/director_p24_1110.md, tests/test_post_fx.py, tests/test_d13_post_fx.py, devsys/areas.json.
- Areas test mới đăng ký, version 74 giữ; diff --check qua; không đổi widget keys.
- RA: docs/RA_D13_VIEC1_CODEX_2026-10-14.md; related_areas yêu cầu slow tại bước gộp.
- MỞ: mục 2 _hold_end và mục 4 delivery.status do owner xử lý; không đụng delivery/ffmpeg_studio/step5.
- Bước kế: root RÀ KỸ sạch, tích hợp owner; cả bộ Windows gồm slow trước commit/gộp.
- Rủi ro: thêm lượt băm byte nguồn; spec/nguồn thực sự mới giữ file mới; không dọn/xóa UUID cũ hay dữ liệu thật.

Vòng sửa RÀKỸ14/10: 2P2 đã sửa gom. Nối post_fx từ outputĐạoDiễn→shot_data/v3store_plan hoặc DIRECTOR_KEYS/legacymerge→DB→apply, gatedp24_lessons; renderer/contextgatedpost_fx_render. Sharedcontext cho cảEditor vàDirector secondpass; khôngcopy intent. 3callerchainassertion đỏ→3xanh/0,45s; OFFbaseline+invalidyellow/deepcopy bổ sung. Nhóm5file gốc+test_v3 chạy launcherfakeenv/registryblocked/nativewhitelist; chờ sốcuối. Giữareas74/heldfiles/noAPI/noactualdata/commitpush. Root đọcfixdiff, mục2/4chờowner.

DONE vòng sửa: 147passed/131,81s nhóm6file (5fileworker+test_v3), fakeenv/registryblocked/nativewhitelist --tb=no. Root đã đọcfixdiff khônglỗithêm; khôngthay intent_all, sharedcontext lấyres.post_fx từmanifestnguồnchuẩn cho2lượt. RA chốt2P2+redgreen. Mục1/3/5hoàn tấtcode, mục2/4ownerheld vàcảbộ/gộp/commitpush/productionchưa làm.
