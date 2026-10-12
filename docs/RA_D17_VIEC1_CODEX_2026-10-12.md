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
