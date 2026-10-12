# Rà Đ17 việc 1 — 12/10/2026

## Đánh giá trước build
| Việc | Tần suất | Lợi ích | Công sức | Rủi ro | Khuyến nghị |
|---|---|---|---|---|---|
| a Guard skin mới ở rewrite | Cao, ca #27 | Không tự đổi dạng Kho | Nhỏ | Tên dạng trong ghi chú phải được giữ | LÀM: từ chối có fallback báo rõ |
| b Skin + vật liệu mặc định | Vừa | Lộ mâu thuẫn trước gửi | Nhỏ | Chỉ đo thuộc tính sát tên món, bỏ phủ định | LÀM: VÀNG |
| c Ưu tiên khóa hơn plate_wide | Cao khi đông người | Giữ đúng súng | Vừa | Thiếu nền rộng | Chờ người dùng chốt; giữ namedprop reservation |
| d POV + súng | Vừa | Tránh góc FF không hợp lệ | Nhỏ | Nhận nhầm thoại/qua vai | Đề xuất VÀNG; chờ chốt |

## Bằng chứng
- Đỏ a/b: 2 failed, 62 passed, 4 subtests; test cũ giữ nguyên.
- Không API, không dữ liệu thật, chưa thử model thật.

## Phạm vi đã làm / chưa làm
- a: sau kiểm nhân vật mới, chỉ khi project_prop_lock ON; dạng mới so với prompt cũ + note/fix → RewriteRefused, caller before_retry có fallback/diag sẵn. Không gọi thêm API.
- b: VÀNG khi dạng skin có thuộc tính của mặc định và không thuộc skin; bỏ thuộc tính phủ định, dùng cùng bảng thuộc tính song ngữ. Không đổi mô tả Kho hoặc tự chọn dạng.
- c: cảnh báo từ refs CUỐI sau storyboard/sendable filters; so đường dẫn ảnh thực đã resolve, không chỉ tên; Dashboard expander hiện trạng thái mới nhất. Thêm job id để diag không gộp cảnh khác. Không thay thứ tự hay namedprop reservation.
- c ưu tiên plate_wide và d mức cảnh báo/chặn: CHƯA BUILD, chờ người dùng chốt bảng đánh giá; chưa phải hoàn tất toàn Đ17v1.
- Runner sửa tối thiểu ngay trước match_refs (_finish_args): đây là điểm duy nhất biết gói refs cuối sau storyboard. Không sửa place_refs/plate_camera/scene_storyboard.

## Bằng chứng cuối
- Lượt đỏ đầu: b fail assertion; a fixture chưa có file ảnh, assets bỏ ảnh nên guard không thấy variant. Không tính a đỏ đó là regression hợp lệ.
- Đỏ a sau sửa fixture thật: focused unittest tắt guard bằng mock enabled=False → fail AssertionError RewriteRefused not raised; 1 test, 0,06s.
- Đỏ c: missing_refs chưa tồn tại; lượt nhóm 2 có 2 failed / 63 passed (a fixture sai lúc đó, b xanh).
- Xanh cuối: tests/test_prop_lock.py + test_prop_lock_weapons.py + test_prompt_rewrite.py: 84 passed, 4 subtests / 9,97s. Có integration _finish_args → diag → Streamlit warning mock; giữ assertion cũ, OFF unchanged.
- git diff --check xanh. 3 lượt nhóm liên quan + 1 focused baseline do root yêu cầu; không cả bộ.
- related_areas: khu vực gọi assets/autopilot/budget, cùng cờ assets/autopilot/knowledge; kiểm _finish_args dùng chung mọi gen ảnh, guard ON, không chặn batch hoặc trả tiền. Rà độc lập CLAUDE7 do root giao tiếp.
- Skill 2b.5: paths qua assets.resolve; không dựa cwd cho ảnh Kho; không thêm default flag/widget; thoại dùng lại shot_text; không gấp dấu từ súng mới; không API/data/dashboard.env/admin_auth.
- Chưa QA Dashboard 1440/1280 hoặc model thật; root thực hiện GUI QA sau rà. Chưa gộp/commit/push; version areas giữ 62; không file Python/test/flag mới nên không thêm đăng ký.
- Rủi ro b: parser thuộc tính cửa sổ gần tên món kế thừa, không NLP toàn đoạn. Nếu false positive màu vật bên cạnh, thu hẹp cùng cụm/mệnh đề + test lamp/car, giữ VÀNG không block.

- Tự rà root phát hiện guard a phụ thuộc ảnh dùng được: đã sửa lấy thêm variant metadata bất kể file/status + đầu dạng skin trong mô tả. Selector refs giữ nguyên. Regression ảnh mất: baseline guard cũ ĐỎ RewriteRefused not raised → guard metadata mới 1 passed /0,25s (focused, không lặp nhóm).
- sendable_references giữ nguyên dict/path sau lọc, không sao chép ảnh; bộ cuối _finish_args so path nguồn hợp lệ trước adapter mã hóa ảnh. Không có _prepare_images trong core.

## RÀ KỸ độc lập — findings gom một vòng sửa
- P1 `core/prompt_rewrite.py:304`: `_says_variant` dùng token `skin` sát tên chung, nên nguồn `skin Gloowall OB55` cũng được coi đã chứa `skin Gloowall OB56`. Guard bỏ lọt biến thể mới OB56. Repro helper: cả OB55 và OB56 đều True cho từng chuỗi trên. Sửa guard bằng nhận dạng riêng phần định danh phân biệt từng variant; ưu tiên cụm đầy đủ, chỉ chấp nhận tên rút gọn khi duy nhất. Redcase: Kho có hai skin cùng alias, old OB55/new OB56 phải RewriteRefused, note cho phép OB56 mới qua.
- P1 `core/prompt_rewrite.py:297,304`: mọi chữ note/fix đều được coi cho phép, kể cả `Do not use skin Gloowall OB55; keep default white wall` và `Previous take incorrectly used skin Gloowall OB55. Remove that skin.` Repro propose_rewrite với FakeClient: cả hai cho qua new có OB55. Sửa chỉ lấy chỉ dẫn khẳng định hiện tại từ note/fix; loại đoạn phủ định/nhắc lỗi cũ; giữ variant thật đang có trong old theo yêu cầu. Redcase hai note trên phải refused, note `use skin ...` vẫn qua. Không sửa money/fallback.
- P2 `core/prop_lock.py:525-527`: cửa sổ ký tự nhận màu vật bên cạnh và thiếu phủ định `without`. Repro issues ba chuỗi `A white car passes; Kelly hides behind skin Gloowall OB55.`, `Kelly uses skin Gloowall OB55; a white lamp shines.`, `Kelly uses skin Gloowall OB55, without white paint.` đều báo mâu thuẫn trắng sai. Sửa gắn thuộc tính cùng cụm danh từ/mệnh đề đạo cụ, dừng dấu ngắt và đầu danh từ khác; nhận without/không có/lack(s). Redcase cả ba không có mâu thuẫn, `plain white skin Gloowall OB55 wall` vẫn vàng.
- P2 `core/prop_lock.py:523-524`: chỉ lấy span tên Kho, bỏ từ chung loại dù lock đã nhận skin. Repro `A plain white glue wall with OB55 skin, no pattern.` locks chọn OB55 nhưng issues không có mâu thuẫn. Thêm span từ chung qua `_SHOT_RX[lk['category']]` vào parser cụm đạo cụ ở finding trên; redcase chuỗi này phải vàng.
- Đã đọc callers/fallback/sổ chi, assets namedprop reservation, diag/schema Pipeline, filters refs cuối và OFF: chưa thấy lỗi chặn khác trong diff. Không đổi thứ tự refs hoặc 6 dòng runner; không API/dữ liệu thật, không chạy lại cả bộ. Dashboard giữ latest event theo gói đã dựng; chưa có evidence lỗi stale cần sửa riêng.
- Bằng chứng là các lệnh Python fixture tạm + FakeClient, không thay test/assert production. Chưa sửa code, chưa commit/push. Ưu tiên fix chung parser và guard, chạy test đỏ→xanh focused rồi root QA.

## Kiểm giao diện của root
- Root đã đọc diff của vòng sửa 4 finding trước commit; guard định danh riêng và parser thuộc tính cùng cụm, giữ selector refs/fallback/cờ OFF. Parser chỉ nhận các mẫu rõ, chưa NLP rộng hay kiểm chất lượng model thật.
- Component `dashboard.common.scene_expander` thật trên Streamlit riêng cổng 8519, CSDL/diag giả; không truy cập Dashboard live hoặc dữ liệu sản xuất.
- Chrome Playwright 1440×1000 và 1280×1000: cảnh báo SKORP hiện đầy đủ, 0 pageerror, 0 tràn ngang, không Streamlit exception. Root đã mở xem cả hai PNG `docs/images/d17/dropped_refs_*.png`.
- Đã dừng đúng tiến trình QA có commandline thư mục temp riêng; không ảnh hưởng 8501/8502. Chỉ nghiệm thu component cảnh báo, chưa toàn Dashboard/model thật.

## Vòng sửa gom 4 finding
- Guard riêng `_variant_mentions`: cụm định danh đầy đủ ưu tiên, skin chung chỉ hợp lệ khi khớp duy nhất; không sửa `chosen_variant`/selector refs.
- `_variant_instruction` loại mệnh đề phủ định/lần lỗi trước trong note/fix, giữ variant thật trong old; boundary chữ nguyên từ. Fallback/sổ chi nguyên trạng.
- b dùng cụm thuộc tính sát tên/từ chung đạo cụ, cho phép `skin` giữa màu và tên; bỏ phủ định, không lấy cửa sổ màu vật bên cạnh.
- Đỏ focused trước sửa: 8 subtest fail (4 guard, 4 parser), 2 passed + 2 subtests passed. Xanh focused: 4 passed + 10 subtests.
- Xanh nhóm cuối sau thêm biên old-preserved/fixallows: 86 passed, 14 subtests / 7,48s; `git diff --check` xanh. Giữ toàn bộ assert cũ.
- Không thêm runner/UI diff; no API/data/main/TODO/admin_auth, chưa commit/push. c ưu tiên và d POV vẫn chờ chốt.
- Root đã QA component 1440/1280: không lỗi/overflow; PNG docs/images/d17, server tạm đã dừng. Root đọc diff vòng sửa trước bước tiếp.

## c/d sau người dùng chốt 12/10 — đánh giá trước build
- Root đã đọc diff vòng sửa P2 phủ định góc trước commit; ảnh ưu tiên được thay trước mapping cả luồng thường/storyboard, không tăng số slot. Cùng ảnh súng/dạng dùng chung; collage vẫn để sau. Không đổi UI so với hai PNG đã kiểm, không cần lặp QA component.
| Việc | Tần suất/lợi ích | Công sức/rủi ro | Chốt |
|---|---|---|---|
| c Ảnh súng khóa thắng nền rộng | Cao khi đông người; giữ dạng súng | Nhỏ: thay đúng slot place_wide; rủi ro thiếu nền rộng được báo | CÓ, giữ nền chính/storyboard/cast/skill/previous và cap |
| d POV+súng | Vừa; tránh góc FF không có | Nhỏ; parser rõ, phủ định/thoại/OTS không kích | VÀNG cho chạy, không chèn câu/ảnh súng |
| Dùng chung ảnh cùng súng/dạng | Có sẵn: locks dedup asset id + holders | 0 USD; identity câu tên từng người vẫn giữ | Tái dùng; không build thêm |
| Collage nhiều súng/đạo cụ | Tiết kiệm slot có thể hữu ích | Rủi ro nhận nhầm vật/identity, cần thử chất lượng model thật | Chỉ đánh giá, ĐỂ SAU; chưa build |

## Kết quả c/d đã chốt — base a03afe67
- c: prioritize_gun_refs thay đúng một slot `place_wide` bằng ảnh súng khóa thiếu, sau kiểm sendable_references file/model; không tăng số ảnh, không lấy slot cast/mainplate/storyboard/skill/previous. Nhiều holder cùng asset vẫn một ảnh. Không thay reservation namedprop trên main.
- Runner 2572–2574: lọc POV/recover trước `_sent` luồng thường; 2611–2616: lọc/recover shared trước `job_fields`, nên storyboard.image_mapping và đường dẫn gửi cùng bộ. Đổi tối thiểu runner vì chỉ đây có gói thực sau add_wide/filter; không sửa place_refs/scene_storyboard/plate_camera.
- d: explicit angle/camera/shot/size + chữ không thoại, boundary POV/first-person; phủ định/OTS không kích. Gun locks không tạo, `_named_extras` không kéo gun; refs súng `object` của shot khác trong shared storyboard cũng lọc. Đạo cụ khác giữ. Không thể gỡ súng đã nằm trong ảnh người: giữ ref nhân vật chuẩn.
- POV rule mới chỉ VÀNG, không dừng. Guard ĐỎ đã có (dùng súng sai chủ) giữ nghĩa độc lập, không nới guard chỉ vì POV. diag `prop_pov_gun` ghi ở bước gửi, UI dùng issues dao_cu hiện có.
- Đỏ nhóm: 11 failed /87 passed /14 subtests (thiếu helper/d hành vi cũ). Xanh lượt2: 89 passed /23 subtests; xanh cuối sau regression storyboard mapping: **90 passed /23 subtests /7,70s**. Ba lượt nhóm, giữ mọi assert cũ. Không cả bộ/API/ảnhmodel thật.
- Regression giữ refs bảo vệ, OFF, ảnh không hợp lệ, idempotence dedup; integration real job_fields kiểm image_mapping `Image 1 (SKORP)` trùng path gửi và `_sent`, không còn wide map.
- related_areas đã chạy: callers Kho/autopilot/budget/step1/step3/step4/step5/plates3d/knowledge; cùng cờ autopilot/knowledge/step3. Test CHẬM trước gộp: editor_apply/editor_review/rough_cut/ui_v2_acceptance. Rà độc lập root điều phối.
- Skill2b.5: không path mới/cwd dependency; helper resolve reuse; OFF cả prompt/refs; shared tự động và tay đều chung _finish_args; không cờ default/widget mới; không so chữ gấp dấu POV; không thêm lời gọi tiền. areas.version giữ62; không filepy/testfile/flag mới cần đăng ký.
- Collage nhiều assets chưa build, cần người xem ảnh thật xác nhận nhận đúng từng vật. Khả năng dùng chung cùng asset đã có regression `test_two_characters_sharing_a_gun_get_one_sentence_and_one_picture` xanh.
- Chưa commit/push/main/TODO/PLAN/admin_auth/data/dashboard.env. HANDOFF.md có sửa từ đầu task trước do phiên cũ, lượt c/d không đụng; handoff mới ở docs/HANDOFF_D17_VIEC1_CODEX_2026-10-12.md.
- Hạn chế: POV parser rõ theo chữ, chưa hiểu chuyển POV→OTS trong một câu; nếu cần dùng action cấu trúc trong tương lai. Ảnh ref nhân vật cầm súng vẫn giữ nhận diện, không crop/raster sửa vì chưa duyệt.

## RÀ KỸ c/d độc lập — base a03afe67 (chưa sửa)
- P2 `core/prop_lock.py:247-249,252`: OTS/TPS được ưu tiên bằng `_OTS.search` dù chính cụm đó bị phủ định, nên `not over-the-shoulder; POV`, `Không qua vai; góc nhìn thứ nhất`, `not third-person; first-person view`, `Not OTS, POV with a gun` đều trả False. Repro fixture angle đầu + `Kelly holds a gun`: prompt_part vẫn chèn Prop lock/Weapon scale SKORP, refs vẫn có SKORP, pov_gun_issue None — trái chốt d.
- Sửa cụ thể: dùng cùng helper kiểm phủ định cho cả `_OTS` và `_POV`; chỉ OTS/TPS khẳng định mới override. Giữ ưu tiên angle OTS thật so với chữ POV prompt và boundary/thoại như cũ. Redcase 4 ca trên True; integration angle phủ định OTS + gun có warn, prompt không gunlock, refs không SKORP; `angle=ots` vẫn False, `not POV; OTS` False, OFF y cũ.
- c chưa thấy lỗi chặn mới: thay tại chỗ sau sendable, không tăng slot; shared tối đa 8 + anchor/previous tối đa 2 nằm trong cap model hiện có >=10; job_fields/reference_note xây mapping SAU recover, _sent dùng refs thực. Câu wide nằm trong reference_note được dựng lại, không còn khi role wide bị thay. Nền main/anchor/previous/cast không bị lấy slot; không đổi reservation/dedup.
- d còn lại: prompt_part/clean_prompt/reference_images đều đi locks; named_extras bỏ gun, shared lọc object gun đúng project. ImageRunner ghi diag trước provider call. Video không thêm Prop lock mới (chỉ helper này gắn trong build_image_prompt). OFF không lọc/thay refs. Không API, dữ liệu thật, fullsuite, commit/push hoặc sửa code; root gom một vòng sửa finding trên.

## Sửa finding P2 c/d — gom một vòng
- `_affirmative_angle` kiểm cùng phủ định cho OTS/TPS và POV; OTS/TPS khẳng định vẫn ưu tiên, OTS bị phủ định không che POV nữa.
- Đỏ focused trước sửa: 4 subtests fail ở `is_pov` (EN/VI/third-person/OTS), 1 passed + 3 subtests passed. Đây là assertion đỏ hợp lệ, trước các assertion refs.
- Test integration dùng tên SKORP để OFF có ảnh namedprop như hành vi cũ; chữ nguồn SKORP giữ nguyên, chỉ kiểm không chèn `Prop lock:`/`Weapon scale:`. Fixture mới lúc đầu dùng generic gun nên kỳ vọng ảnh OFF sai, đã sửa fixture; không đổi assertion test cũ.
- Xanh focused: 2 passed + 16 subtests /0,27s. Nhóm cuối: 91 passed + 30 subtests /7,80s; diff check xanh (chỉ cảnh báo LF→CRLF).
- Test giữ phủ định POV/noPOV, OTS thật override, integration actual build_image_prompt/scene_references/yellow và OFF namedrefs. Không đổi runner/assets/selector/chi phí, không API/fullsuite/commit/push/main; root đọc diff sửa trước gộp.
