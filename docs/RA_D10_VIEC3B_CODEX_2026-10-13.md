# Rà Đ10 việc 3b — báo giá phần còn lại

Nhánh `codex/d10-viec3b-project-budget`, gốc `3d6004bb`. Phạm vi đúng bảng ưu tiên mới: Đ10v3 mục 2, Đ13v4 mục 9 phần `_video_need`, QC đếm hai lần khi `qc_observe_enum` bật. Không sửa runner, usage/follower/cut, seedance_refs, admin_auth hay dữ liệu thật.

## Đánh giá trước build

| Sửa | Lợi ích | Công sức/rủi ro | Quyết định |
|---|---|---|---|
| Dùng chung `estimate_run` cho ngân sách video | Loại bỏ báo 0 cho clip xếp hàng/đầu vào cũ; kế thừa nhóm/giá dự phòng/bản giao | Nhỏ; cần rà hệ số model chưa xác minh | Làm |
| Tách nháp người duyệt còn nâng bản cao | Không trả/quote nháp lần hai; vẫn không coi 480p là bản giao | Nhỏ; phụ thuộc lịch sử duyệt/stamp/nhóm | Làm sau cờ two_tier_quality có sẵn |
| QC enum loại agent/team khỏi phần cộng thêm | Quote đúng đường production enum; không đổi số call video QC | Nhỏ; OFF phải giữ giá cũ | Làm |

## Code và caller

- `project_budget.remaining`: bỏ tập `made` dựa vào trạng thái bất kỳ; lấy giá phần video từ `cost.estimate_run`. QC dùng cùng điều kiện observe_scene như estimate_run để không cộng agent/team khi enum đã thay thế.
- `cost._video_need`: chỉ nháp người duyệt hiện tại, nâng được, sau cờ hai bậc → `needed=False`, `final_only=True`; đây là không cần gen nháp mới, KHÔNG chứng nhận clip giao HD. OFF giữ kiểm nháp cần bản giao cũ.
- `quality_tier.running_draft_final_estimate`: nhận cả nháp approved final_only để cộng một bản cao; giữ nháp running đã trả tiền ở cả OFF.
- `cost.video_need` memo thêm trạng thái cờ hai bậc để không giữ quyết định ON khi OFF trong cùng rerun.
- `model_router._remake_runs` dùng cùng video_need; nháp final_only không nằm trong nhóm gen nháp mới. Helper bản cao dùng sent_group/draft_seconds cũ, không sửa nhóm production.
- `py tools/related_areas.py core/cost.py core/project_budget.py core/quality_tier.py` đã chạy; root giao reviewer độc lập rà budget/step4 + các caller trước commit.

## Ma trận tiền

| Trạng thái | Phần còn lại |
|---|---|
| Clip approved/succeeded thiếu stamp, đầu vào cũ | Gen mới vẫn được quote; ledger đã chi không xóa |
| Queued/retryable/failed/cancelled | Chưa bằng chứng task đang trả tiền: quote gen mới |
| Running có external_id | Không quote lại task đã trả; nháp cộng bản cao còn thiếu |
| Nháp approved hiện tại + nâng được + cờ ON | Chỉ cộng nâng, không nháp lần hai |
| Nháp stale | Gen nháp mới + bản cao theo chính sách cũ |
| Cờ OFF | Không thêm final_only từ approveddraft; vẫn có bản cao sau nháp running |
| Model thiếu giá nhưng có giá cùng loại | Tính dư bằng money_policy; giữ unknown để hiện cảnh báo |

## Bằng chứng / tự rà

- Đỏ đầu: fixture initial sai (DELETE foreign-key và approved thiếu nguồn), sửa fixture trước sửa code. Đỏ xác nhận: 5 lỗi (3 test / 3 subtest) cho trạng thái còn lại, enum double count, nháp approved.
- Xanh nhóm 5 file lần đầu: 76 passed, 6 subtests passed / 32,41 s. Sau đó thêm ca missing price/running draft/stale/OFF và chạy cuối; kết quả cập nhật bàn giao.
- Không nới assert cũ. Test dùng SQLite memory + mock provider/probe; không gọi API, không sửa data thật.
- Không widget mới/đổi key, không cờ mới/default thay đổi; areas version giữ 66, đăng ký test mới.
- Tự rà skill 2b.5: không đường cwd/data thật; không chặn hàng loạt mới; không so bỏ dấu; không paid call; feature OFF có ca riêng. Git diff --check xanh.
- Chưa thử dự án thật / chất lượng clip. Chưa chạy full suite (phiên gộp chịu trách nhiệm). QA báo giá GUI1440/1280 và RÀ KỸ độc lập do root hoàn tất trước commit.

## RÀ KỸ độc lập và vòng sửa gộp

Reviewer đối chiếu caller `money_card`, `summary_detail_md`, `estimate_view`, `cost_summary`, `project_reserve`, memo, model_router và quality_tier theo CLAUDE mục 7 / skill 2b.5. Phát hiện 3 lỗi P2:

1. Giá model chưa xác minh đã biết bị mất hệ số 1,25 khi đổi sang estimate_run. Sửa nhánh giá đã biết trong estimate_run; fallback đã có 1,5/1,25 không nhân lần hai.
2. Nháp approved final_only làm todo rỗng, bỏ QC bản cao trong estimate_run. Cộng remaining_final.clips đúng một QC cho mỗi task bản cao, không QC nháp lần hai.
3. Không có bất kỳ giá video thì fallback None bị coi là 0 đủ giá. Giữ subtotal số để không phá caller/ngân sách, nhưng metadata incomplete/unpriced riêng; propose/view/summary/format_run và component chi tiết nói rõ chưa tính được video, tổng phần đã biết. Không bịa giá/không thêm cổng chặn trả tiền. remaining() vẫn chỉ chứa số tiền từng khâu; metadata không nằm trong dict này. Nhánh giá fallback có known rate vẫn hoàn chỉnh.

Bằng chứng vòng sửa: 3 regression đỏ (3 failed, 7 passed, 6 subtests / 0,69 s); nhóm 5 file `test_project_budget_video_remaining.py`, `test_project_budget.py`, `test_money_policy.py`, `test_cost_route_e1.py`, `test_video_quote_current.py`: **124 passed, 6 subtests / 34,31 s**. Sau đối chiếu component thật, bổ sung assertion chi tiết không báo Video 0: **1 failed / 0,74 s**, sửa shell_parts; nhóm `test_project_budget_video_remaining.py` + `test_quality_tier.py`: **32 passed, 6 subtests / 1,81 s**. Hai nhóm xanh có 146 test khác nhau (10 test mới nằm cả hai nhóm); không nới test cũ.

Các lượt fixture trước đó ghi rõ: nhóm worker 79 passed + 6 subtests và 1 lỗi thiếu currency; lượt focused 6 passed + 6 subtests và 1 lỗi thiếu per_video_clip. Đã sửa cấu trúc fixture, không đổi assertion, nhóm cuối xanh. Không chạy lại full suite; số lần vượt 3 do fixture sai và caller UI mới được xác nhận bằng regression.

QA component **dashboard.header.money_card thực** trên Streamlit 127.0.0.1:8519, DB memory/fixtures; pricing mock riêng (giá model chưa xác minh và thiếu toàn bộ giá video), ASSET_DIR/flags/knowledge/temp. Không bấm nút trả tiền. Chrome headless 1440×1000 và 1280×1000: 4 ảnh `docs/images/d10/project_budget_{known,missing}_{1440,1280}.png`, 0 pageerror, 0 stException, không tràn ngang. Đây QA component với dữ liệu giả, không dự án sản xuất/không full dashboard. Chưa thử thật clip/API/full suite.
- Root đọc diff cuối cost/project_budget/quality_tier/shell_parts + tests/areas; xem4PNGknown/missing1440/1280, báo thiếugiá rõ và margin8×1,25=10. Chốt3P2 sửa; giữ numericremaining/no paidblock mới/no jobrunner change. 146test riêng biệt xanh, chưaproduction/cảbộ Windows. Root không chạy lại khi không đổi code.
