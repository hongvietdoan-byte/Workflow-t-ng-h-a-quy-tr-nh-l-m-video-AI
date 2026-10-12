# RÀ KỸ Đ15 việc 1 — Codex 12/10/2026

- Phạm vi: diff chưa commit trên base `7a69f5b`, `tests/test_delivery_resolution.py`, caller dựng/giao/báo giá; chỉ đọc, không API/dữ liệu thật.
- Kết luận: **CHƯA gộp**, còn 2 finding cần gom vào một vòng sửa.

1. **[P1] `core/cost.py:583–592`, `:720`: nháp đang chạy làm báo giá phần bản cao bằng 0.** `_video_need` trả `needed=False` ngay cho mọi job running đã có external_id, kể cả `quality_tier=draft`; nháp nhóm cũng bị nhánh sent_group coi đã đủ. Vì `run_estimate` chỉ nhận `todo`, bản cao bị loại hoàn toàn. Tái hiện trên SQLite memory bằng fixture `tests.test_cost_route_e1.Base`: job draft/running/paid + cờ ON → `video_need={needed:False}`, `estimate_run.videos=0`, clips/drafts/finals_1080 đều 0. Sửa: giữ phân biệt nháp đã trả tiền và bản giao còn thiếu; quote riêng phần cao còn cần, không cộng lại tiền nháp đang chạy, không tạo/gửi lại job running. Test đỏ→xanh cả job riêng và leader/follower nhóm; OFF/ON; final running vẫn không đếm lại tiền đã gửi.
2. **[P2] `core/quality_tier.py:267–274`: clip không đo được vẫn được công nhận bản cao đã xong.** `deliverable` trả `not size`, nên approved/final mất tệp hoặc probe lỗi → `final_ok`; `final_estimate` bỏ qua và trả 0, trong khi guard giao HD từ chối cùng nguồn. Tái hiện memory + probe=None: `state=final_ok`, `final_estimate={usd:0,scenes:[],unknown:[]}`. Sửa: không trả trạng thái *_ok khi chưa đo/thiếu clip; báo rõ kiểm tra/tải lại nguồn (không tự gen trả tiền), giữ giá/unknown phần bản cao nhất quán. Test missing/remote/probe=None không *_ok; clip 720 đo được vẫn *_ok; `final_offer/request_final` không chặn nhầm bởi bản cao không hợp lệ.

- Đã đối chiếu: guard `render` chạy trước postfx/fit/render; clip manual/explicit/follower đều đo tệp; export HD lần về manifest final và chặn legacy thiếu clip; callback deliver/editor/autopilot có guard; bản nháp sidecar riêng, không đăng ký outputs; widget key cũ không đổi.
- Fixture đổi render_size là khung xuất thật, giữ assert; không thấy nới assert hoặc lách export trong diff hiện tại.
- Giới hạn: không chạy lại nhóm 14 file/cả bộ (worker đang chạy); chỉ 2 script tái hiện nhỏ ở SQLite memory, không sửa code/tests, không commit/push.

## Vòng sửa gom (không commit/push)
- P1 đã sửa: `quality_tier.running_draft_final_estimate` cộng riêng giá bản cao còn thiếu của task nháp đang chạy; `cost.estimate_run` nối USD/count/warnings/unknown. `video_need` vẫn không gửi lại task paid. OFF/ON như nhau; group/follower quy về leader+sent_group và tính một lần; final running không tính lại. Giá nâng dùng `upgrade_price` tính dư + UPGRADE_UNMEASURED; đường gen khác giữ ref seconds và giá model.
- P2 đã sửa: clip không đo được không *_ok, trả final_review; final_source_problem yêu cầu kiểm tra/tải lại task đã gửi. final_offer/scene_final_price trả giá None; request_final chặn trước tạo job; final_estimate + estimate_run báo unknown, không tự báo gen mới. Thẻ Dashboard hiện lý do phục hồi, widget key giữ nguyên.
- Đỏ→xanh: 10 subcase tiền/nguồn ban đầu đỏ → 4 test +10 subtest xanh/0,65s; thêm follower running đã bắt lỗi dedup (2 subcase đỏ → xanh). Không gọi API.
- Nhóm sửa: `test_quality_tier`, `test_cost_route_e1`, `test_video_quote_current`, `test_delivery_resolution`: **77 passed +10 subtests /15,44s**. 2 fixture thiếu nguồn được bổ sung path/probe720; assert giữ nguyên.
- Caller cost/UI/model/picker: 30 qua/3 đỏ đều fixture UI byte không phải clip; sửa TwoTierSeed cấp nguồn fixture+probe720 đo được, giữ assert; chạy lại riêng UI: **13 passed /29,26s**, gồm ca nguồn unknown hiện hướng dẫn và không submit. 21 ca cost/model/picker đã xanh trong lượt caller.
- `git diff --check` exit 0. Worker trước sửa: **276 passed /467s** ở 14 file. Không chạy lại 14 file/cả bộ.
- Kết luận vòng sửa: 2 finding đã xử lý; root cần đọc diff phần sửa trước commit. Chưa cả bộ/gộp/production/API.
