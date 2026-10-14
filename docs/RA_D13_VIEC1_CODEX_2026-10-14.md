# Tự rà Đ13 việc 1 phần độc lập — 14/10/2026
- Nhánh codex/d13-viec1-post-fx, nền 2c43a28f; chưa commit/push; DONE mục 1/3/5.
- Lợi ích: cùng shot + nội dung nguồn/spec/seconds/filter/encode dùng một tên SHA256 đầy đủ, tránh UUID làm phình mỗi lần dựng.
- Nguồn được băm streaming toàn bộ byte (cả audio); không dùng path/mtime làm định danh, đổi byte cùng kích thước vẫn đổi tên.
- Không tái dùng cache: mỗi lần luôn render atomic, không xóa file dữ liệu/UUID cũ; failed render giữ nguyên bản kết quả trước và paths nguồn.
- Rủi ro: thêm một lượt đọc nguồn; đầu vào/spec thực sự đổi tạo tên mới, cần chính sách dọn lịch sử riêng nếu muốn.
- Kiến thức Đạo diễn thêm schema post_fx tại rule 6, giữ cổng p24_lessons có sẵn; OFF vẫn trả [] nên prompt cũ giữ nguyên byte.
- Editor prompt 24 append context qua editor_prompt, không sửa template chung; OFF parts/images và fingerprint cũ nguyên công thức.
- rough_cut thêm manifest.post_fx chỉ khi post_fx_render; fingerprint ON gồm context, đổi cờ/spec không tái dùng review cũ.
- Context phân biệt XANH đã áp với VÀNG chưa áp, giữ spec/scene_id; không mặc định bỏ mọi glitch khỏi kiểm chất lượng.
- Caller rà: delivery.render gọi post_fx.apply; editor_review.run/editor_apply.apply + step5 dùng rough_cut.build; hợp đồng không đổi.
- Test cũ chỉ đổi input a/b.mp4 thành file giả tmp có byte để SHA đọc thật; giữ nguyên yêu cầu yellow/xanh/nguồn/partial.
- require_filter đọc ffmpeg -filters; chỉ skip ca glitch nếu thiếu rgbashift, các lỗi ffmpeg khác vẫn FAIL; noise/nhap_nhay vẫn chạy.
- Đỏ: 5 failed/103 passed (46.28s), đúng test mới trước sửa; xanh: 108 passed (45.41s), cuối 108 passed (45.11s).
- MỘT nhóm 5 file: test_d13_post_fx, test_post_fx, test_p24_lessons_1110, test_editor_review, test_rough_cut; 3 lượt tổng.
- FFmpeg thật chạy đủ ba loại trên nguồn lavfi local; duration/audio/pixel-change/OFF nguồn không đổi byte đều qua, 0 USD.
- Security proof: patch.object(os,'environ',fake_dict) BEFORE pytest/modules; đỏ không credentials, xanh có credentials giả; context manager teardown.
- Native Popen dùng env whitelist SYSTEMROOT/TEMP/PATH chỉ đường ffmpeg + system; không kế thừa fake credentials hay môi trường thật.
- Không đọc/in/assert/repr khóa/môi trường thật; pytest --tb=no; DB/flags/knowledge/data do fixture fake/temp, clients MockLlm/mocks cũ.
- related_areas: step5 + knowledge, chung cờ plates3d/step1/step3; yêu cầu test CHẬM ở bước gộp (editor_apply/editor_review/rough_cut).
- areas đăng ký test_d13_post_fx.py, giữ version 74; git diff --check qua; widget keys không đổi.
- Tự rà 2b.5: không nới test; không phụ thuộc cwd/data thật; không đổi auto/bulk/OFF; không bỏ dấu, không mạng/API/lời gọi tiền mới.
- MỞ: mục 2 thứ tự trước _hold_end và mục 4 delivery.status stale thuộc owner delivery; chưa hoàn tất toàn bộ Đ13v1.
- Không đụng core/delivery.py/core/ffmpeg_studio.py/dashboard/steps/step5.py/PLAN/TODO/main/live.
- Chờ root RÀ KỸ sạch rồi tích hợp phần owner, cả bộ Windows (gồm slow) trước gộp.

## Rà kỹ độc lập Đ13v1 partial (14/10)
- Phạm vi mục1/3/5, nền2c43a28f; không sửa code/delivery/ffmpeg_studio/step5, không commit/push/fullsuite. Diff --check sạch; version74 giữ nguyên.
- P2A `knowledge/roles/director_p24_1110.md:26` hướng dẫn Đạo diễn ghi post_fx nhưng `core/shots.py:183` shot_data không giữ trường, và `core/llm_io.py:264` DIRECTOR_KEYS cũng không có. Kết quả mới từ Đạo diễn bị mất trước scenes.data; post_fx.apply không thấy để dựng. Repro offline thật gọi shot_data(scene,shot{post_fx},1) trả dữ liệu thiếu post_fx; legacy DIRECTOR_KEYS cũng thiếu. Sửa đề xuất: nối persistence/validation cho shot và scene legacy theo cờ đã chốt, giữ quy tắc OFF và cảnh báo invalid; test end-to-end store_scene_analysis/store_plan→DB→apply bằng fake renderer. Test prompt/schema hiện tại chỉ grep chưa khóa luồng lưu.
- P2B `core/editor_review.py:335` director_prompt (lượt phán quyết thứ hai) không mang res.post_fx; `director_two_pass.intent_all` chỉ lấy INTENT_KEYS, không phục hồi hiệu ứng. Vì vậy sau Editor có context, Director vẫn có thể đồng ý/đổi đề xuất cắt hiệu ứng có chủ ý với thiếu đầu vào. Repro gọi director_prompt với res.post_fx xanh/glitch: text không chứa post_fx. Sửa đề xuất: shared effect-context block cho cả editor_prompt và director_prompt, gated post_fx_render; test cả hai prompt OFF byte-identical, ON có spec/muc/shot/vùng thời gian, run MockLlm bắt hai payload không paid.
- Đã đọc caller render/apply/roughcut/editor_apply: render_lock hiện có + atomic_output mỗi lần tên tạm riêng giữ failure isolation; không thêm paid calls; editor run còn need_edit/spend_cap. ON fingerprint mang manifestpost_fx; OFF giữ công thức cũ; p24_blocks OFF trả[] trước đọc knowledge. Bool/NaN/huge numeric đã có guard/test; rgbashift skip chỉ effectglitch đúng.
- Rủi ro không nâng thành finding: source được hash trước ffmpeg mở file, source thay giữa hai bước có thể làm tên SHA không phản ánh byte đã render; hiện luôn render và production render_lock giảm race. Có thể kiểm stat/hash lại sau render trước publish hoặc snapshot input nếu cần chốt mạnh hơn. File UUID cũ không được dọn (đã ghi giới hạn).
- Security repro `C:/Users/hongviet.doan/AppData/Local/Temp/d13_v1_review_repro.py`: patch.object(os,'environ',dictfake) BEFORE coreimports/calls, winreg OpenKey blocked, features/knowledge/directorintent mocked. Không credential/provider/model/native process trong repro; không đọc/in môi trường thật. Kết quả in3boolean: shot_data_drops_post_fx=True, legacy_DIRECTOR_KEYS_drops=True, second_reviewer_context_missing=True. Lần đầu launcher thiếu sys.path nên ModuleNotFoundError; sửa path launcher rồi repro xác nhận, không test ứng dụng bị nới.
- Không chạy lại108test worker; không API/DBdata thật/env/dashboard/live. Hai finding cần gom một vòng sửa, rồi root đọc diff sửa và mergeoperator cảbộ Windows gồmslow.

## Vòng sửa gộp hai P2 (14/10)
- P2A đã nối `shots.shot_data` giữ deep-copy post_fx của từng shot, và `llm_io.DIRECTOR_KEYS` + legacy merge giữ post_fx khi p24_lessons bật. post_fx_render vẫn chỉ quyết định dựng/context; p24 OFF không thêm field mới, không xóa hậu kỳ đã lưu bằng tay. Dữ liệu sai vẫn giữ để apply.validate báo VÀNG; không gây paid retry Đạo diễn do hậu kỳ chưa hợp lệ.
- P2B dùng cùng `_post_fx_context(res)` ở editor_prompt và director_prompt, gated post_fx_render. Cả hai đọc manifest của bản dựng thực tế; không sửa/copy thêm director_intent_raw vào scenes.data. OFF block=[] giữ byte prompt cũ.
- ĐỎ 3 assertion callerchain (legacy storage, v3 storage, second reviewer) trước sửa; XANH 3/0,45s sau sửa. Test thật `store_scene_analysis`→v3 store_plan/legacymerge→scenes.data→post_fx.apply (fake ffmpeg), không chỉ grep keys. Thêm OFF shot_data==baseline và invalidspec giữ nguyên để VÀNG/deepcopy không alias nguồn.
- Launcher `%TEMP%/d13_v1_fix_{red,green}.py` thay os.environ OBJECT dictfake trước coreimports/calls; winreg OpenKey blocked. Green native Popen explicit whitelist giống proof worker; không API/môi trường thật/data thật. pytest --tb=no; chưa gộp/chưa commitpush.
- File thêm trong vòng sửa: core/shots.py/core/llm_io.py đã thuộc step1 areas; test mới đã đăng ký step5; areas.version74 giữ. Không sửa helddelivery/ffmpeg_studio/step5/runner. Root đọc diff sửa trước bước tích hợp.

### Chốt vòng sửa
- XANH cuối: **147 passed /131,81s**, nhóm6file: test_d13_post_fx, test_post_fx, test_p24_lessons_1110, test_editor_review, test_rough_cut, test_v3; không repeat fullsuite. Launcher d13_v1_fix_green.py, security isolation như trên, không API.
- Không thay `director_two_pass.intent_all`: nguồn chuẩn cho hiệu ứng đã áp là `res.post_fx` từ manifest bản dựng, shared context truyền vào cả hai lượt. Không thêm bản sao post_fx vào intent_all hay scenes.data từ intent.
- Root đã đọc diff sửa shots/llm_io/editor/roughcut/postfx/test và kiểm DIRECTOR_KEYS chỉ có1consumer; không thấy lỗi thêm. Vòng sửa 2P2 DONE trong phạm vi mục1/3/5. Mục2/4 vẫn ownerheld; chưa fullsuite/gộp/commit/push/thử production. Diff --check sạch.
