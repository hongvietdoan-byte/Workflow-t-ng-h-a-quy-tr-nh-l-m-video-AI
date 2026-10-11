# Đợt 5 — kiểm kê hiện trạng phục vụ thiết kế Tiểu Nhị

Ngày 11/10/2026; nguồn code worktree `codex/d5-nghien-cuu-tu-phuc-vu`, base `b346d10`. Chỉ đọc mã và tài liệu, KHÔNG mở dữ liệu thật, Dashboard, Blender hoặc gọi API. Bổ sung Đợt 7 đối chiếu base `229f812`; các nguồn mới ở phần “Đối chiếu Đợt 7” dưới đây. Số dòng kế thừa là một-based trên base Đợt 5; đây là bằng chứng cấu trúc, **chưa phải xác nhận chạy thật**. Tài liệu phụ trợ cho `NGHIEN_CUU_TU_PHUC_VU_DASHBOARD.md`.

## Phạm vi và nguồn sự thật

“Bất kể lỗi” nghĩa là mọi lỗi được tiếp nhận, phân tuyến, có chủ xử lý và trạng thái nhìn thấy; không hứa AI tự sửa mọi lỗi. Lỗi chưa phân loại vẫn thành phiếu với bằng chứng tối thiểu, không bị bỏ hoặc hiện “không có lỗi”. Phân biệt kết quả chẩn đoán chưa biết / học việc / cờ tắt / đã kiểm thật.

| Nguồn | Đã đọc / ý nghĩa | Giới hạn khi dùng cho trợ lý |
|---|---|---|
| `core/db.py:295`, `core/diag.py:87`, `core/diag.py:152` | `diag_events`; scan job lâu, file mất/rỗng, autopilot không tick, risk control và lặp lỗi | API recent/repeated là sổ toàn hệ thống: phải lọc project trên server trước khi trả cho đồng nghiệp |
| `devsys/error_types.json:5` đến `:100` | 24 loại L1–L15, V1–V4, A1–A4, R1; mỗi loại có nguồn đo/cờ/trạng thái | `co` trong bảng không đồng nghĩa đang bật hoặc đã nối; R1 ghi rõ hàm có nhưng chưa nối |
| `knowledge/checks/README.md:19`, `knowledge/checks/L13.md:24–31` | Khuôn khai điều thấy, code kết luận, thiếu/unsure→VÀNG; movement_gaps và layout_drift | Không giao VLM quyết số người/trái-phải/hình học; L13 drift chưa nối change_audit |
| `core/db.py:268`, `core/lessons.py:198` | mistakes, clusters, nhóm chưa phân loại | Ngưỡng hiện tại **3 sự kiện / 2 dự án** (`core/lessons.py:20`), khác đề xuất “lặp ≥2”; cần chốt, không lặng đổi |
| `core/db.py:398`, `dashboard/steps/step4.py:497` | content_moderation_failures, lỗi provider của clip | Chẩn đoán dựa thông báo/provider_rules, không hướng dẫn vượt bộ lọc |
| `core/runner.py:56`, `core/runner.py:268`, `dashboard/steps/step2.py:130` | WAIT_REASONS có lý do và thời điểm, UI đọc hàng đợi ảnh | In-memory có thể mất sau restart; cần snapshot an toàn vào phiếu, không coi “trống” là không bị giữ |
| `core/bg_poll.py:206` | Khóa OS theo CSDL tránh hai vòng nền trả tiền hai lần | Tạo lock lỗi OSError hiện **return True** (:217), nên không tuyên bố khóa chống trùng tuyệt đối; wrapper cần fail-closed và idempotency bền vững |
| `core/access.py:107`, `dashboard/common.py:313` | require quyền dự án; scoped đặt p.user | None/local được coi system/admin (:39–56), helper bỏ kiểm khi p.user None (:125); Tiểu Nhị bắt identity thật và không nhận project từ lời chat làm quyền |
| `core/spend_gate.py:115`, `docs/CHUAN_XAY_DUNG.md` luật chi phí | Sổ chi + ước tính, caps chỉ CẢNH BÁO; pause/hết credit là chặn | Trần Tiểu Nhị theo dự án 2 USD, báo 80%, hết trần gửi phiếu admin là **chốt 11/10, chưa triển khai**; không đổi cap Pipeline |

## A — taxonomy toàn khâu (42 loại, có nhánh chưa biết)

Quy ước năng lực: N1 giải thích/đề xuất; N2 chuẩn bị patch dự án rồi người duyệt; N3 chuẩn bị thay đổi dùng chung rồi admin duyệt; N4 lập phiếu code/vận hành, bảo trì xử lý. “Có” dưới đây chỉ là code/UI đã đọc. Các hook đang tắt/chưa nối được ghi theo bảng error_types, không tính là hàng rào hoạt động.

| ID / khâu, triệu chứng | Chẩn đoán / nguồn code | Dashboard hôm nay → tính năng cần có trước trợ lý | Người xử lý / Tiểu Nhị tới đâu |
|---|---|---|---|
| T01 Ý tưởng thiếu mục tiêu, đối tượng, thời lượng | validation scene `core/llm_io.py:41` | Editor có trường shot → checklist brief bắt buộc + phát hiện thiếu | Đồng nghiệp / N1–N2 |
| T02 Kịch bản thiếu/mất/lặp thoại | `_check_lines` `core/llm_io.py:127` | Thoại editor `dashboard/steps/step1.py:273` → diff câu thoại trước/sau | Đồng nghiệp / N2 |
| T03 Biên kịch schema hỏng, model trả dở | SchemaError `core/llm_io.py:13` | Báo lỗi qua `dashboard/common.py:209` → lỗi kèm trường sai + lưu bản nháp sửa | Đồng nghiệp; lỗi parser N4 |
| T04 Director thiếu nguồn, sai BYĐ | `core/llm_io.py:256`, `core/llm_runner.py:785` | Sửa shot tay có → bảng “đã đọc nguồn nào”, diff BYĐ/phạm vi thay đổi | Đồng nghiệp / N1–N2 |
| T05 Chạy Director ghi đè sửa tay | `_user_locked` `core/llm_io.py:428` | Có mở khóa `dashboard/steps/step1.py:292` → xem khóa trước chạy, chọn trường được điền lại | Đồng nghiệp / N2 |
| T06 Thêm/chèn shot thiếu trường hoặc lệch thứ tự | `core/pipeline.py:240` | Có “Thêm cảnh” append rỗng `dashboard/steps/step1.py:477` → wizard shot đầy đủ, chèn/reorder an toàn | Đồng nghiệp / N2 |
| T07 Kho sai danh tính L1 | `devsys/error_types.json:5` | Kho + chọn cast đã có → so ảnh nguồn/hồ sơ/gói gửi, chọn đúng asset | Đồng nghiệp chọn; sửa chung N3 |
| T08 Kho trang phục/dạng lệch L2 | `devsys/error_types.json:10` | Editor cast/background có → so look theo shot, nguồn chuẩn và ngoại lệ | Đồng nghiệp/N2, hồ sơ chung N3 |
| T09 R1 ảnh mẫu bẩn/mô tả lệch | `devsys/error_types.json:100` R1 chưa nối | Không coi asset_clean là gate đang chạy → màn nguồn↔mô tả + trạng thái sạch/admin duyệt | Admin/N3 |
| T10 Map 3D có vật thừa/scale sai | `tools/location_pack.py:41` model3d | Đặt nhân vật lên ảnh bối cảnh có `dashboard/steps/step1_prep.py:295` → inspector object map, bản sao preview trước đề nghị sửa | Admin/N3, Blender worker |
| T11 Kho âm nhạc/SFX thiếu/sai tệp | Audio UI `dashboard/steps/step5.py:204` | Có quản lý âm thanh → nghe so, nguồn/quyền sử dụng, thay tệp trong dự án | Đồng nghiệp/N2; shared N3 |
| T12 BYĐ ngoại lệ chủ ý bị Lock áp đè | `core/lock_exceptions.py:21` | Reader ngoại lệ đã có → editor ngoai_le theo shot, preview lock hiệu lực | Đồng nghiệp/N2 |
| T13 L3 số người/người lạ | `devsys/error_types.json:17` | Chọn cast `step1.py:235` → checklist số người code + liên kết nguồn | Đồng nghiệp/N2 |
| T14 L4 tư thế/hành động sai | `devsys/error_types.json:21` | Blocking text `step1.py:239` → pose/beat editor + mannequin preview | Đồng nghiệp/N2 |
| T15 L5 hướng nhìn/mặt lưng sai | `devsys/error_types.json:25` | Text blocking có → mũi tên facing/gaze + kiểm so góc máy | Đồng nghiệp/N2 |
| T16 L6 vị trí trái/phải sai | `devsys/error_types.json:28` | Text blocking có → sửa số/kéo trên sân khấu, phép chiếu 2D bằng code | Đồng nghiệp/N2 |
| T17 L7 vật/phần thấy sai hình học | `core/stage_facts.py:138` | Chưa editor hình học → facts inspector miệng/thành/camera, không dùng prompt vá riêng | Lỗi bố trí N2; code N4 |
| T18 L8 cỡ cảnh/tỉ lệ không đủ diễn | `devsys/error_types.json:38`, `core/shot_lessons.py:326` | Cỡ/thời lượng editor → subject-box overlay + warning amplitude | Đồng nghiệp/N2 |
| T19 L9 máy/chân trời sai | `core/stage_facts.py:281` | Đặt người lên ảnh bối cảnh có → camera editor + giải máy/preview, đối chiếu góc nền | Đồng nghiệp/N2; solver N4 |
| T20 L10 hòa sáng/màu | `devsys/error_types.json:48` đo còn xây | Lighting text `step1.py:234` → so plate/light rig, không giả kết luận QC đã đo | Đồng nghiệp/N2 |
| T21 L11 nơi/nền/cached góc khác | `core/sent_package.py:167`, `runner.py:490` | Không thấy UI dùng sent_package → ô gói **đã gửi** theo job/phiên bản + cache identity | Đồng nghiệp/N2; cache code N4 |
| T22 L12 thời tiết/giờ/ánh sáng | `devsys/error_types.json:55` | Editor mood/lighting → bộ chọn env đồng bộ plate/prompt | Đồng nghiệp/N2 |
| T23 L13 di chuyển/liên tục shot kề | `core/shot_lessons.py:125`, `:217` | CLI drift chưa UI → timeline beat/end-position, bảo vệ approved shots, diff phụ thuộc | Đồng nghiệp/N2 |
| T24 L14 tay/mặt méo/chữ lạ | `devsys/error_types.json:65` | Duyệt/loại ảnh có → khoanh lỗi + lý do chuẩn, đề xuất thay đầu vào | Đồng nghiệp/N2; giới hạn auto |
| T25 L15 vật lạ ngoài BYĐ | `devsys/error_types.json:68` world_rules chưa nối | Loại ảnh có → hỏi “cố ý hay lỗi”, inspector vật có thật trong map | Đồng nghiệp/N2; shared N3 |
| T26 Khung đầu/cuối thiếu/sai | `core/end_frames.py:256`, `runner.py:1118` | Không thấy UI gọi end_frames → màn cặp đầu–cuối, route/cờ/preview request rõ | Đồng nghiệp/N2, gen duyệt tiền |
| T27 Video ref/model/thời lượng không hợp | `core/video_pregen.py`, `step1.py:212` | Chọn route/duration có → kiểm gói trước tiền + bảng hạn chế model ngay ô nhập | Đồng nghiệp/N2 |
| T28 Video risk control/người thật | `core/db.py:398`, `step4.py:497` | Có lỗi risk trong màn clip → giải thích rule chính thức, chọn nguồn/model hợp lệ | Đồng nghiệp/N1–N2; không bypass |
| T29 V1 trôi hình khỏi khung đầu | `devsys/error_types.json:72` clip_measure.look_drift | Duyệt phiên bản có → so khung đầu/clip, plot đo và gói nguồn | Đồng nghiệp/N2 |
| T30 V2 giật/viền lạ | `devsys/error_types.json:75` | Duyệt clip có → mốc frame lỗi, so phiên bản | Đồng nghiệp/N2 |
| T31 V3 môi không khớp thoại | `devsys/error_types.json:79` | Clip + thoại có → play đồng bộ và mốc lip_sync, không hứa model tự đúng | Đồng nghiệp/N2 |
| T32 V4 động tác/máy lệch BYĐ | `devsys/error_types.json:82` chưa đủ đo | Route editor có → beat-vs-clip timeline, tách thất bại nhóm nhiều shot | Đồng nghiệp/N2 |
| T33 A1 TTS sai người/cắt/im | `core/voice_check.py:141`, `:246` | Âm thanh UI có → transcript so, redo đúng dòng + báo giá | Đồng nghiệp/N2 |
| T34 A2 nhạc/SFX sai nhịp/loudness | `core/ffmpeg_studio.py:525` | Mix UI có → waveform/beat/đo loudness trước dựng | Đồng nghiệp/N2 |
| T35 A3 phụ đề sai chữ/thời điểm | `step5.py:377`, `:402` | Tạo/sửa/in phụ đề đã có → preview safe-area + câu thoại nguồn/khóa sửa tay | Đồng nghiệp/N2 |
| T36 A4 dựng/popup/thứ tự | `step5.py:953`, `:977` | Popup seconds/color có → preview đúng cuối clip, timeline post_fx | Đồng nghiệp/N2 |
| T37 Xuất bản thiếu FINAL/sai kích thước | `core/diag.py:198`, `step5.py:595` | Xuất bản đầy đủ có → checklist deliverables + tải từng bản/nhận biết thiếu | Đồng nghiệp/N2; ffmpeg code N4 |
| T38 Tiền/giá thiếu/sổ chi lệch | `core/spend_gate.py:115`, `core/cost.py:756` | Header tiền `header.py:644` → estimate→approve→receipt, đối soát theo task; trần người cần quyết định mới | Đồng nghiệp duyệt, admin/N1–N4 |
| T39 Queue kẹt/provider429/timeout/credit | `core/diag.py:152`, `runner.py:420` | WAIT ảnh `step2.py:130` và halt `header.py:796` → lý do mọi job + đối soát trước resend | Đồng nghiệp/N1–N2; provider N4 |
| T40 Quyền/tài khoản/truy cập điện thoại | `core/access.py:107`, `common.py:313` | Có project ACL → đăng nhập thật/màn yêu cầu quyền; mobile review hoãn theo chốt 11/10; không gợi mở public máy chủ | Chủ/admin/N1–N4 |
| T41 Dữ liệu hỏng/mất ảnh/cache/DB | `core/diag.py:173`, `:176` | Chẩn đoán file có → khôi phục phiên bản có checksum, backup + preview, không assistant SQL tùy ý | Admin/N4; bản dự án N2 có duyệt |
| T42 Dashboard sập/lỗi code/chưa phân loại | `common.py:209`, `core/lessons.py:217–223` | act báo lỗi không phải inbox bền → điểm tiếp nhận ngoài Dashboard + phiếu logs redacted/repro/status | Bảo trì/N4; không AI sửa main |

## Chín ca thật 11/10 đối chiếu hiện trạng

Các mô tả lấy từ CODEX_TASKS, không xác nhận lại dữ liệu #24.

| Ca | Hôm nay đã có bằng chứng code | Thiếu / đề xuất Dashboard trước trợ lý |
|---|---|---|
| 1 Miệng giếng sai hình học | `_derive_top` `core/stage_facts.py:138`, contradictions `:475` | Facts + hình chiếu trước gen; phiếu N4 khi luật sai. Không hứa nút “sửa prompt” chữa code |
| 2 Trườn ra khỏi giếng rồi vị trí sai | movement_gaps `shot_lessons.py:125`; drift `:217`; solve_scene `stage_solver.py:555`; v2 CLI `stage_grid.py:1308` | Editor blocking sân khấu/tọa độ, xem trước 0 USD API nhưng CPU; giải/render nền; diff nhiều shot/giữ approved; chưa có wrapper giao dịch |
| 3 Thêm shot10 | Thêm cảnh `step1.py:477`; append empty `pipeline.py:240` | Đã có chức năng cơ bản, cần wizard đầy đủ/BYĐ/shot_no/phụ thuộc; chèn/reorder không gọi append giả |
| 4 Khung đầu/cuối Kling | end_frames.redo `:256`; route/needed `:29–35`; runner last_frame `:1118` | UI cặp khung + duyệt phiên bản + trạng thái cờ/route; reuse core, không dựng generator thứ hai |
| 5 Hai nền 3D khác góc trong gói | sent_package ledger `runner.py:490`, safe_build `sent_package.py:209` | Viewer theo **job thực gửi** (không tính lại gói hôm nay), hash/góc/role; kiểm nhiều nền và phiếu cache |
| 6 Thùng dầu có thật trong shared map | model3d đọc read-only trong preview `location_pack.py:41` | Phiếu asset/map + object-selection screenshot + bản sao preview/admin merge version; người dự án không xóa map chung |
| 7 Ngoại lệ Lock9–10 | for_shot đọc phạm vi `lock_exceptions.py:21`; runner uses `:1968` | Editor ngoại lệ có nguồn, preview lock hiệu lực/ảnh/clip/QC; chỉ N2 scoped project |
| 8 Red cũ/đã xử lý | `dashboard/change_review_ui.py:31` đã có “Đã sửa”, `:35` “Bỏ qua”; core close `:387` | **Không xây lại nút**; thêm lý do bắt buộc, snapshot bằng chứng/quyền server, cảnh báo đóng đỏ sẽ mở queued gen |
| 9 Duyệt trên điện thoại | Core approve `pipeline.py:650`, ACL theo project | Hoãn điện thoại/HTTPS khỏi đợt gần (chốt 11/10); giữ ca chuẩn cho đợt sau. Không kiểm truy cập điện thoại thật phiên này; ngoài Dashboard gửi thông báo chứa link authenticated, không ảnh/gói công khai |

## B — danh mục công cụ dùng lại (wrapper đề xuất, chưa triển khai)

Không gọi hàm core trực tiếp từ model. Tên tool cố định + schema whitelist; server suy project từ resource và identity, kiểm quyền lại khi apply, kiểm version/sha và duyệt. Các hàm nhận conn hoặc CLI thường **không có ACL nội tại**. Mỗi tool trả cấu trúc kết quả/needs/error, không prompt injection từ log hoặc lỗi nhà cung cấp.

| Hàm code / đầu vào → đầu ra | Chi phí / tác động | Quyền hiện tại và wrapper cần có |
|---|---|---|
| `diag.recent(conn,hours=24,limit=40)` `core/diag.py:125`; scan(conn,data_dir,poll_sec=15) `:152` → list dict | 0 USD API, đọc file/DB | Không ACL; filter project + path allowlist, không expose toàn hệ thống |
| Đọc `jobs.sent_package`, schema build `core/sent_package.py:167` → JSON snapshot/refs SHA | 0 USD API | Dùng SELECT có join project và view ACL; lỗi ledger trống hiện chưa biết, không dựng lại rồi gọi đã gửi |
| `stage_facts.for_shot(conn,pid,data,aspect=None,end=False,render=True)` `:542` → facts dict | 0 USD API, phép tính | conn không ACL; chỉ input snapshot dự án/view; tránh giả rendering real từ tham số render |
| `shot_lessons.movement_gaps(blocking,order=None)` `:125`; `layout_drift(old,new,approved,moved=None,...)` `:217` → list issues | 0 USD API, thuần | view; immutable candidate/approved snapshot, không nhận path chat tự do |
| `stage_solver.solve_scene(specs,blocking,aspect,marks=None,grid_cells=None,...)` `:555` → kết quả máy/facts | 0 USD API, CPU | Thuần không ACL; view để preview, edit+approval để apply bằng tool khác |
| `tools.stage_grid.v2_main(argv)` `:1308`; `run_blender(cfg,out,timeout=1800)` `:1024` → artifacts/cfg | 0 USD API **có CPU/GPU, thời gian, dung lượng** | CLI không ACL; cần render worker argv cố định/sandbox/path scoped, giới hạn resources; không model shell |
| `tools.location_pack.run_preview(a)` `:41` → plate,camera,cache_key hoặc needs/error | DB read-only; Blender CPU/GPU, có ghi out | Không ACL; wrapper kiểm asset project/shared view, output temp riêng; chưa worker safe deploy |
| `llm_io.update_scene(pipeline,pid,idx,fields,text=None)` `:428` → changed fields list | 0 USD API, dữ liệu/lineage/hand-lock | Có need_edit khi p.user; wrapper bắt user thật, version trước ghi; audit/undo snapshot |
| `llm_io.update_scenes_bulk(pipeline,pid,idxs,fields)` `:409` → idx→changed list | 0 USD API, nhiều shot | BULK_FIELDS whitelist đã có; không bảo đảm rollback toàn batch từ hàm này, wrapper cần transaction/draft |
| `Pipeline.add_scene_next(pid,title='')` `:240` → **idx**, không scene_id | 0 USD API, append rỗng | Có edit ACL với p.user; tool add shot đầy đủ cần schema/transaction, không đánh đồng append scene=complete shot |
| `lock_exceptions.for_shot(data)` `:21` → name→items/without | 0 USD API, chỉ đọc | Thuần; ghi ngoai_le là tool riêng cần validation/phạm vi/nguồn/diff |
| `end_frames.redo(p,scene_id,fix=None,auto=False)` `:256` → row_id queued | Chưa submit tại redo nhưng background sẽ tốn tiền | Có need_edit_scene; **chỉ enqueue sau duyệt quote**. reject `:251` không ACL tự thân: wrapper bắt scoped resources |
| `change_review.open_findings(conn,pid)` `:382` → list; close(conn,finding_id,status,who) `:387` → None | 0 USD API, đóng đỏ có thể cho runner gửi tiền kế tiếp | close không ACL/lý do; wrapper edit check finding→project, lý do + preview queued consequences, không tự dismiss |
| `Pipeline.approve(job_id,reviewer_type='user',note=None)` `:650` → None; reject(job_id,...,respawn=True,fix=None,qc=None) `:656` → str | 0 USD API hiện tại; approve mở downstream, reject mặc định **spawn retry** có thể trả tiền | Reuse core ACL; để chỉ ghi lỗi dùng respawn=False; spawn/paid downstream cần quote và duyệt. Không assistant tự duyệt sản phẩm |
| `cost.clip_estimate(conn,scene_id,pricing=None,seconds=None)` `:255`; llm_estimate(conn,stage,calls,...) `:362` → estimate | 0 USD API | Không ACL; server chọn pricing/scene, missing price hiện lý do; quote version/expiry binding |
| `llm_runner.run_director_scene(p,pid,scene_idx,client,note='')` `:823` → dict | Claude tốn tiền/usage hoặc hạn mức Claude CLI tùy client | Quote→user approve→ledger stage/project. Không gọi client chưa có sổ chi, không tính Codex/Claude thuê bao=API miễn phí |
| `llm_runner.run_motion(p,pid,client,data_dir,only_idx=None)` `:921` → dict | Claude tốn tiền | Scope shot và ghi sổ; dùng cùng source mới/old approved, không rerun hàng loạt không báo |
| `lessons.harvest(conn)` `:127`; clusters `:198`; propose(conn,client=None) `:258` → count/list | Harvest/cluster/template 0 API; propose client Claude tốn tiền | Không ACL nội tại, admin tool; đề xuất rule rồi admin decide `:365`, không bật luật chung tự động |
| `voice_check.check_line(path,text,asr=transcribe)` `:141` → dict; measure_loudness(path,ffmpeg=None) `ffmpeg_studio.py:525` → dict/None | CPU, ASR phụ thuộc sẵn có; không mặc định gọi dịch vụ online | Path scope, missing ASR→unknown rõ; tool redo voice `voice_check.py:246` cần quote paid riêng |

## Ranh giới bắt buộc khi chuyển tài liệu chính

1. Trần theo dự án mới có thể chặn Tiểu Nhị; **không sửa ngầm policy caps cảnh báo của pipeline**. Chốt con số, tài khoản chi, múi giờ, reservation đồng thời, cơ chế admin nâng trần. Duyệt payload đúng hash, không duyệt chung “sửa hộ”.
2. View-only vẫn đọc/sinh phiếu được nhưng không edit/approve/queue; đăng nhập thiếu hoặc auth tắt từ remote phải từ chối thao tác trợ lý. Không “hệ thống” thay mặt người thường.
3. Phiếu lỗi code/chung không có job gen tự trả tiền; trạng thái tiếp nhận→đang tái hiện→chờ quyết định→đang sửa→test/rà→chờ admin gộp→triển khai→chờ người xác nhận→đóng. Chỉ “đã sửa” khi có build/triển khai và bằng chứng đúng ca; test fake chỉ báo “kiểm luồng”.
4. Khóa bg_poll là bảo vệ sẵn có nhưng không thay business idempotency/outbox; timeout gửi không được resend đến khi đối soát external_id/provider. Đóng mục đỏ phải hiện danh sách job có thể tiếp tục.
5. Sửa chung map/Bible tạo version và xem phạm vi mọi dự án bị ảnh hưởng; rollout/rollback artifact riêng. Undo dữ liệu dự án không hoàn tiền API hoặc thu hồi job đã gửi.
6. Dashboard trước: gói đã gửi + diagnostic inbox; bổ sung editor đang có; 3D editor/candidate+preview; endframe pair; lý do Tổ rà soát; phiếu admin ngầm. Mobile/HTTPS để sau. Tiểu Nhị gọi lại cùng tool/UI sau đó, không có đường ghi/SQL/shell riêng.

Các file cần người viết tài liệu chính đối chiếu lại: `core/access.py:32–130`, `core/spend_gate.py:115–185`, `core/bg_poll.py:206–233`, `dashboard/change_review_ui.py:8–36`, `core/change_review.py:387`, `core/pipeline.py:240`, `core/end_frames.py:251–279`, `knowledge/checks/L13.md:24–31`. Chúng chứa các khác biệt lớn nhất giữa ý tưởng và khả năng hôm nay.

## Đối chiếu Đợt 7 — nguồn mở trên base `229f812`

| Nguồn thật | Kết luận thiết kế, không xây lại |
|---|---|
| `devsys/answers.py:72–84`, `:103–143`; `devsys/app.py:825–867`, `devsys/app.py:975` | answers lưu một câu trả lời/mã việc + history, answered/applied; web lấy username OS, chưa chứng minh login Owner. Không dùng làm ticket store hay capability duyệt. |
| `devsys/error_types.json:5–100`; `devsys/app.py:1161–1197` | taxonomy/cờ đang có; phiếu giữ error_type + phiên bản taxonomy, unknown không bị bỏ; không tạo bảng loại lỗi mới. |
| `core/db.py:153–159`, `:295–308`, `:515–546` | audit_log/diag_events/change_findings có sẵn, giữ link ID; finding không có SLA/phụ trách/branch nên không thay ticket. |
| `core/db.py:83–94`, `core/cost.py:756`, `core/llm_runner.py:615–623` | Sổ chi là usage_events + llm_calls; usage_ledger chỉ tên khái niệm Đợt 5, không bảng sẵn có. |
| `core/experience.py:26–29`, `:41–59`, `:166–174` | experience_cases là lớp 4, có evidence/outcome/confirmed_by; retrieval phải thêm ACL ở adapter. |
| `core/place_refs.py:280–314`, `core/runner.py:2379–2385` | package_problem đã giữ nền khác camera; gói editor gọi lại, không viết bộ kiểm nền thứ hai. |
| `core/scene_storyboard.py:131–169`, `core/runner.py:2518`, `:2587–2593` | Shared refs ưu tiên cast shot, cast_missing báo người thiếu ảnh mẫu; runner hiện VÀNG (không tự chặn). Editor mới hiển thị ĐỎ cần sửa/duyệt trước gen, không tuyên bố runner hiện chặn thiếu cast. Ca 645–651/Kho419 theo đề bài, chưa đọc dữ liệu thật. |
| `core/end_frames.py:56–62`, `core/db.py:190–201` | ready không đủ: start_job_id phải khớp đầu hiện hành + file tồn tại. Người thấy “Khung cuối cũ vì đổi khung đầu”; nút “Tạo lại khung cuối theo đầu mới” kèm giá, duyệt trước enqueue. |
| `dashboard/steps/step1.py:292`; `core/lessons.py:217–223`; `dashboard/steps/step1_prep.py:292–295`; `knowledge/checks/L13.md:24–31` | Bốn tham chiếu sửa: unlock fields; đếm lỗi chưa phân loại (không phải sinh bài học); đặt người trên background (không editor sân khấu3D); movement/drift. |

Ca gói 649 và 645–651 + stale endframe là biến thể C05/C13/C04 trong bộ 42, không tăng mẫu giả lên 45. Thiết kế đầy đủ: [Đợt 7](THIET_KE_TIEU_NHI_LAO_DAI_D7.md). Đồng nghiệp không thấy phiếu/code, sửa dùng chức năng Dashboard; phiếu chạy ngầm, admin thấy kỹ thuật và hạn3 ngày.
