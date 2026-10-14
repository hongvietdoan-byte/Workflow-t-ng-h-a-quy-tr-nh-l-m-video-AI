# Kế hoạch sân khấu chung theo đoạn — Đ18 việc 1 (12/10/2026)

**Khuyến nghị để người dùng chọn: A trước, B mở rộng trên cùng dữ liệu khi cần đo che khuất thật; C dùng để gỡ trước mắt.** A cho mặt bằng, trạng thái người/vật dùng lại và ảnh giữ bố cục, làm được không cần Blender. B cần khi phải chứng minh phía tường, che khuất và khung hình bằng hình học. Không xây đồng thời hai hệ dữ liệu. C đơn giản nhất nhưng không giải quyết nguồn vị trí chung. Đây là đề xuất chưa duyệt; **Đ18 việc 4 chưa được phép bắt đầu**.

Phạm vi bản này: đọc code tại `2cbe4058`, không đọc dữ liệu #27, không bật cờ, không gọi API. Ca #27 lấy từ hộp thư `TODO.md` 12/10 19:20 và đề Đ18 trong `CODEX_TASKS.md:1187`; không phải kết quả đo lại production. Tài liệu gốc: [đặt máy](KE_HOACH_DAT_MAY_3D_2026-10-09.md), [phương pháp sân khấu](PHUONG_PHAP_SAN_KHAU_3D.md), mục 2–3, 9, 11, 14. Phương án A/B/C ở đây là bảng Đ18, không trùng tên các nhánh A/B/C của phương pháp gốc.

## 1. Hiện trạng đã đối chiếu

| Module / dữ liệu | Code hiện tại, số dòng tại bản đọc | Giới hạn cần giữ rõ |
|---|---|---|
| `camera_plan` G0 | `core/camera_plan.py:152` nhóm theo story_scene và bối cảnh 3D; `:130` lưu `<data_dir>/<pid>/plates/camera_plan.json`; `:75` kiểm cờ; `:690` duyệt render | Có bộ góc máy/sơ đồ, chưa phải sân khấu chung qua hai sequence. Cờ `director_camera_plan` chưa verified (`core/features.py:407`); không suy ra đang bật trên #27 |
| `stage_director` + solver | `core/stage_director.py:26` prompt; `:59` kiểm blocking + shot_specs; `:116` kiểm chồng giếng, không phải kiểm mọi loại va chạm. `core/stage_solver.py:24` beat_raw, `:48` chuyển tọa độ so với O, `:555` solve_scene; CLI `tools/stage_grid.py:1538` | Director viết cho một cảnh, lời gọi Claude có tiền. Solver hình học thuần; Blender đo sau. Cờ `stage_camera` (`core/features.py:401`) chỉ dùng máy đã có và duyệt, không tự nối Director cho mọi đoạn |
| `blockout_sheet` | `core/blockout_sheet.py:53` render_top_view, `:146` to_location_pack, `:157` đọc pack | Tấm 2D của blockout bối cảnh, không tự có người/vật thời gian; chưa thấy caller production. Đề xuất adapter chứ không giả định sẵn pipeline sân khấu đoạn |
| `continuity` | `core/continuity.py:214` layout_warnings, `core/director_report.py:209` ghép báo cáo | Cờ `continuity_layout` (`core/features.py:514`), VÀNG từ chữ/trục/phía/mất người; không đo tọa độ hoặc nhìn ảnh để bảo đảm đúng |
| Scene / plate | `core/llm_io.py:476` update continuity_from; `core/location_pack.py:368` plan, `:260` index `<data_dir>/<pid>/plates/index.json` | `scenes.data`: sequence, story_scene, plate_spot, plate_view, blocking, continuity_from là trường shot; blocking văn bản shot không đồng nghĩa blocking.objects/beats của solver. location_pack là cấu hình tài nguyên bối cảnh; index plate là dẫn xuất camera |
| Vá #27 | `core/runner.py:2284` chọn ảnh nguồn, `:2295` layout_reference, `:2875` và `:2955` gửi; `core/scene_storyboard.py:96` other_spot, `:284` job_fields; `core/assets.py:1761`, `core/storyboard_frames.py:24` diễn giải layout_from | Code có đường gửi ảnh giữ bố cục, nguồn chưa duyệt/mất ảnh báo VÀNG. Hộp thư nói đã vá #27; chưa chứng minh job cụ thể đã nhận ảnh/cờ runtime. Không ghi “đã chạy trên #27” từ việc code tồn tại |

`continuity_from` hiện nhận shot trước **hoặc sau** (hộp thư 19:17, `2b1f6ce`; kiểm tự trỏ, không tồn tại, vòng tại `llm_io.py:476`). Đề Đ18v3 còn nói danh sách TRƯỚC: phải đối chiếu sự thật này khi làm v3, không tự đổi luật nguồn. Hộp thư còn mở việc chờ job nguồn, fingerprint ảnh nguồn và rà ngược; kế hoạch này không nhận các việc đó đã xong.

### Ma trận caller hiện tại và điểm nối đề xuất

| Luồng | Chứng cứ hiện tại | Nghĩa vụ khi làm v4 (đề xuất) |
|---|---|---|
| Bấm tay Director / replan | `dashboard/steps/step1_director.py:15`, `:176` gọi llm_runner; không phải hook stage_director | Sau phân cảnh: resolve stage/state, báo thiếu; giữ phần người chốt; chỉ tái lập phần phụ thuộc |
| Autopilot | `core/autopilot.py:608`, `:629`, `:634` camera_plan trước/sau ensure_plates | Dùng cùng resolver với tay; cờ OFF không thêm call, prompt hoặc cửa duyệt; chưa thử thật thì không đưa vào autopilot |
| Shot riêng / storyboard nhóm | `runner.py:2875`, `:2955` cùng layout_reference; `scene_storyboard.py:44` hiện nhóm theo story_scene | Snapshot mỗi shot, neo cùng spot và state tương thích; không dùng một state cho cả nhóm chuyển động |
| Nhân bản | `core/compare.py:32`, caller `dashboard/header.py:863` | Tạo ID/scope dự án mới, remap shot, bỏ approval/cache dẫn xuất; không giả định tệp stage được copy chỉ vì scene rows được copy |
| Render plate | `location_pack.py:368`; `core/plate_camera.py:405` máy stage đã giải | Nhận transform + state chung, không dựng lại vị trí bằng chữ |
| Báo cáo/QC | `director_report.py:209`; `runner.py:3029` QC layout sau cờ camera_plan | Phân biệt measured/unknown/estimated; QC ảnh sinh không được coi render proxy là chuẩn nhận diện người |
| #27 | Hộp thư 19:20 và code layout_from/other_spot ở trên | Thử khô bằng fixture trước; chưa có runtime flag/job evidence, không tự sửa dữ liệu thật |

## 2. Đoạn, sân khấu và thời gian là ba khái niệm

**stage_id** định danh bất biến một sân khấu vật lý trong dự án (bối cảnh + phiên bản nguồn + hệ tọa độ); **segment_id** định danh bất biến đoạn hành động truyện gắn stage_id; **state_id** xác định một mốc trạng thái trong đoạn. Không băm tên địa điểm/sequence/thời gian thành ID: đổi nhãn hoặc chèn shot không được làm mất liên kết. Location + plate_spot + thời gian chỉ là gợi ý ghép nhóm, không đủ tự gộp. plate_spot là vị trí/vùng tham chiếu trên sân khấu; hai spot khác nhau vẫn có thể thuộc một stage_id khi có transform đã xác minh.

Director đề xuất segment và state theo hành động; code chỉ gợi ý từ sequence/spot, kiểm tham chiếu; người duyệt/sửa đoạn bằng Dashboard sau này. Không biết hai địa điểm có cùng tọa độ → VÀNG “chưa ghép được sân khấu”, không tự quy chúng về O chung.

- Shot 1–3 ↔ 11–12: có thể cùng stage và đoạn đang bị cắt xen kẽ. Nếu thời gian tiếp nối, tiếp tục state của đoạn, giữ nguyên ID/vị trí đồng đội gục; nếu truyện đã đổi thời gian, dùng segment mới trên stage cũ và state mới có quan hệ nguồn rõ. Sequence mới không tự reset sân khấu.
- S07 nhặt súng/đấu súng: hai plate_spot khác nhau, tọa độ hoặc transform phải chứng minh khác vùng; chưa biết thì yêu cầu đặt lại, không sao chép neo chỉ vì cùng story_scene.
- S08-2 Kelly núp: phía an toàn so với tường/tháp là quan hệ trong world-space; trái/phải màn hình đổi khi máy đổi. Cần xác định mặt tường và phía địch để kiểm, không suy từ câu “Kelly bên trái”.
- Tường keo xuất hiện tại shot 15: event/patch tạo object ID ở state đó; trước event không có, sau event giữ vị trí cho đến patch di chuyển/xóa. Không đưa tường vào mọi shot vì stage được dùng lại.

## 3. Hợp đồng dữ liệu đề xuất — một nguồn

Chưa có schema sân khấu đoạn triển khai. Đề xuất lưu registry theo project, shot chỉ giữ liên kết; đường lưu chính thức phải chốt khi v4, luôn tính từ data_dir được truyền, không từ cwd:

| Khối | Trường và luật |
|---|---|
| Stage | schema_version, stage_id, source_asset_id/revision, world_frame (mét, trục/hệ số/transform gốc O từ K1), spots và transform. Map/floor chưa đo phải ghi provenance=estimated/unknown |
| Actors/objects | actor_id/object_id ổn định và asset/look ID; base position xyz, hướng mặt, tư thế, kích thước có nguồn. Không dùng tên hiển thị làm khóa; thiếu chiều cao/kích thước báo thiếu |
| Segment/state | segment_id, stage_id, initial_state; state_id, parent_state_id, story_time/beat; patch theo ID: vị trí, hướng, tư thế, hidden, spawn/despawn, quan hệ núp. Patch không đổi giữ giá trị trước; DAG state không có vòng |
| Shot | scene ID ổn định (idx chỉ là thứ tự), segment_id, place_spot, state_start/state_end + time_clip; camera/spec/nhip. Chuyển động trong clip có keyframe/đường và trạng thái cuối; không coi một ảnh đầu clip là toàn trạng thái |
| Snapshot | stage/state revision, resolved world positions, transform, nguồn, user locks, camera riêng; hash dependency gồm nguồn ảnh layout job + revisions. Không ghi đè lịch sử snapshot đã gửi |

Tái dùng `stage_solver.beat_raw` cho objects + beat overrides, `objects_from_blocking`/solve_scene cho giải máy, stage_grid cho hệ tọa độ/K4. Adapter world↔local giữ một transform, không định nghĩa lại tọa độ cho prompt, sheet và Blender. `blockout_sheet` nhận projection từ cùng snapshot; không biến 2D giả định thành số đo sàn thật. `camera_plan` dùng lại ý đồ/góc máy, không lập registry người-vật thứ hai.

Máy từng shot là phần tách riêng: đổi camera không đổi state. Di chuyển người/vật phải là patch có chủ đích, không phải tác dụng phụ đổi góc. Sửa người chốt giữ provenance=user; Director replan chỉ đề xuất diff để duyệt, không tự dời đồng đội. Clone/reorder remap ID, không giữ idx cũ như quan hệ nội bộ.

Điểm nối chung đề xuất: sau Director lưu phân cảnh → resolve snapshot trước location_pack.plan/ensure_plates và trước runner hoàn tất refs/prompt; lời vị trí, top-view, render, lựa chọn layout_from cùng snapshot; hậu QC đọc snapshot job đã gửi, không đọc state mới nhất. Dependency graph: source → stage → state → shot snapshot → plate/prompt → image/video. Đổi stage tác động các shot dùng stage; đổi state tác động hậu duệ state; đổi camera chỉ shot đó; đổi ảnh nguồn tác động shot giữ bố cục theo nó. Bảo đảm cờ mới OFF không đổi fingerprint/prompt/grouping cũ và không gọi Claude/Blender mới.

## 4. Bảng đánh giá để duyệt

Quyền ghi đề xuất cho v4: state/snapshot riêng dự án chỉ sửa qua server với quyền sửa đúng dự án, kiểm revision trước ghi và lưu lịch sử; Director gửi đề xuất, không ghi đè khóa người. Map/location_pack hoặc mẫu sân khấu dùng chung chỉ Owner xuất bản, không tự ghi lại Kho từ thay đổi của một dự án. Consumer render/prompt/QC chỉ đọc snapshot thuộc đúng dự án. Nhân bản phải remap scope/ID và bỏ approval/cache; không mang quyền/khóa cũ sang dự án mới.

| Phương án | Chặn trước gửi / chỉ hỗ trợ phát hiện ở ba lỗi #27 | Công sức và rủi ro | Chi phí API mỗi đoạn / bấm |
|---|---|---|---|
| A: mặt bằng 2D + prompt + layout_from | Registry/ID/patch có thể chặn dời đồng đội không có event; kiểm spot có thể chặn dùng nhầm vùng S07; quan hệ tường đã khai có thể chặn Kelly ở sai phía **trong dữ liệu**. Ảnh sinh vẫn có thể sai cả ba; 2D không chứng minh che khuất/độ cao | Ước tính tương đối thấp hơn B, cao hơn C: schema/resolver, adapter sheet, điểm nối, dependency, UI duyệt. Rủi ro map suy sai, projection sai, ảnh neo khóa góc; chưa đo công làm/bấm tiết kiệm | Nhập/chốt tay + code: 0 USD API bổ sung; gen ảnh/QC hiện có vẫn có tiền. Director tự khai bổ sung là tùy chọn có tiền. Một lần duyệt mỗi segment/state cần đổi + sửa ca thiếu, chưa có đo UI |
| B: người/vật proxy thật trong Blender | Cùng kiểm dữ liệu như A, thêm tia/khung/collision hoặc kiểm half-space tường cần xây cho ca #27. Chặn vi phạm hình học đã đo ở proxy trước gen; không ngăn tuyệt đối model dời người sau gen. Solver hiện có không đồng nghĩa đã kiểm tường keo | Ước tính cao nhất: geometry/kích thước, transform/floor, export/render/cache, UI và đo tia. Có lợi khi thay góc nhiều và cần che khuất; không nên xây thêm bộ ID/state riêng | Code/Blender local 0 USD API; máy/điện/thời gian không phải miễn phí. Director tùy chọn như A + lượt đọc lại nếu chọn. Duyệt tấm ghép theo đoạn + xử lý shot thất bại, số bấm chưa đo |
| C: vá continuity_from + VÀNG | Layout_from hỗ trợ 1–3 ↔ 11–12 nhưng model có thể bỏ qua/chồng người; other_spot tránh neo khác spot nếu trường đã đúng, không phát hiện hai spot thực ra trùng; continuity chữ chỉ phát hiện một phần bên/mất người. Không có nguồn world-space để chặn Kelly phía địch | Ước tính thấp nhất; dùng lại Đ18v2/v3. **Không nên chọn C làm giải pháp tận gốc** vì lỗi vị trí qua nhiều góc tiếp tục phụ thuộc người | Code chọn nguồn/cảnh báo: 0 USD API bổ sung; vẽ lại/QC trả riêng. Chọn nguồn từng shot cần giữ bố cục và sửa lỗi, chưa đo số bấm |

Không có benchmark A/B trên #27, không có số tiết kiệm tiền hoặc click đã đo. Ca lặp lại qua đổi góc cho thấy A có ích, nhưng tần suất ngoài #27 chưa biết. C là phương án người dùng có thể chọn nếu ưu tiên ít thay đổi; B có thể chọn ngay nếu yêu cầu đo hình học là bắt buộc. Khuyến nghị A→B giữ đường nâng cấp, không cam kết A đủ cho che khuất.

### Giá và số đo — không suy giá cũ thành ngân sách mới

`PHUONG_PHAP_SAN_KHAU_3D.md:247` ghi thử #24 ≈0,53 USD/2 lượt + một hỏi lại, ≈10 phút; `:258` ghi **ước tính** ≈0,15–0,3 USD/cảnh 9 shot. `KE_HOACH_DAT_MAY_3D_2026-10-09.md:27` ghi G0 #24 ≈0,37 USD. Các mốc này là báo cáo lịch sử #24, không phải giá/đo #27 và không áp tự động mỗi đoạn.

Ước tính mới phải lấy `core/cost.py:307` cấu hình token camera_plan và `cost.llm_estimate` theo stage/model/bảng giá hiện tại; CLI `tools/stage_grid.py:1538` có cách dự toán stage_director, tối đa `2 * MAX_ROUNDS` calls gồm hỏi lại sai schema, nhân LLM_MARGIN. Công thức dự toán đoạn: `Σ estimate(stage, calls) × margin + Σ estimate(image/video/QC được chọn)`. A/B nhập tay: số calls Director bổ sung = 0; dùng Director: cộng lượt đầu, sửa/hỏi lại trong giới hạn đã duyệt; R1/R2 tùy chọn báo riêng. C không tự thêm paid call nhưng người gen lại vẫn chịu giá ảnh/video/QC. Không dùng trần cảnh báo tiền thay sự đồng ý gọi API.

Đo click khi có mockup: `click = duyệt đoạn + chọn/sửa state + chọn nguồn layout + xử lý thiếu`, tính mỗi thao tác thực tế một lần; ghi baseline C và A/B cùng kịch bản. Đo effort bằng thời gian thiết kế/code/QA/render và số vòng sửa, hiện chỉ có thứ hạng ước tính. Trần từng thử trả tiền phải liệt kê sau khi biết số shot/calls/model; chưa đủ đầu vào → chưa đặt số USD. Lần này không gọi provider.

## 5. Lộ trình tối thiểu và cổng chọn

1. Đ18v2 neo theo (story_scene, plate_spot), OFF giữ cũ; Đ18v3 ô continuity_from dùng update_scene và quyền hiện có. Hai việc không tự tạo sân khấu hay chứng minh lỗi model đã hết. Đối chiếu nguồn trước/sau đã mở ở main khi làm v3.
2. Người dùng đọc bảng A/B/C và chốt: A trước (khuyến nghị), B ngay, hoặc C/để sau. Đ18v4 chỉ mở khi có quyết định; khi đó viết phạm vi nhánh cụ thể và dependency trước sửa code.
3. Nếu chọn A: fixture không dữ liệu thật cho quay lại 1–3/11–12, S07 hai spot, Kelly/tường, spawn tường, state cuối clip; schema/resolver + sheet + diff + một nút duyệt đoạn, sau cờ TẮT. Kiểm đỏ→xanh, caller tay/autopilot/nhóm/clone/replan, OFF không thay hành vi. Không bật autopilot trước thử thật.
4. Gỡ #27 không cần Blender: người có dữ liệu chốt spot/source/state, xem tấm 2D và refs của từng shot trước gửi; thiếu vị trí/nguồn cảnh báo rõ. Thao tác sửa dữ liệu thật và gen lại chỉ sau sao lưu/đồng ý đúng phạm vi và dự toán. 1 ảnh/nhóm → người xem → 1 clip → mở rộng; ghi kết quả “chưa thử thật” đến khi có bằng chứng.
5. Nếu chọn/nâng B: cùng schema, thêm proxy và đo K4 ở ca tường/gục; kiểm render trước gen. Trước paid QA báo giá riêng. QA hình học/proxy chỉ chứng minh những gì đo; chất lượng ảnh/video phải xem thật, không đóng lỗi #27 từ test giả lập.

Rủi ro còn mở: world transform cho các spot, kích thước/tư thế người gục và tường, thứ tự story_time khi cắt xen, chuẩn hình ảnh cho QC, phụ thuộc nguồn continuity_from chưa có ảnh. Thiếu thông tin ghi unknown + lý do; không tự bịa tọa độ/trần tiền để hoàn tất kế hoạch.
