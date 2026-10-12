# Bàn giao Đ10 việc 3b

Nhánh codex/d10-viec3b-project-budget, base3d6004bb. Code chưa commit/push.

Đã sửa: remaining dùng chung cost.estimate_run (bỏ made theo trạng thái); QC enum không cộng agent/team lần hai; nháp người duyệt ON mới/current/nâng được tách final_only, cộng một final qua helper cũ. Giữ runner/sổ chi/cut/seedance_refs/live/data/env nguyên trạng.

Test 5 file: 76passed+6subtests/32,41s. Bổ sung4ca: nhóm cuối79passed+6subtests/32,05s, một ca fixture thiếu currency. Lượt riêng6passed+6subtests/.60s nhưng fixture vẫn thiếu per_video_clip. Đã thêm currency/per_video_clip vào fixture, chưa rerun cuối để root reviewer chạy chung vòng sửa. Không nới assert.

Root reviewer đang gom3finding: unverified margin bị bỏ; QC bảncao có thể thiếu; allpricesunknown còn0. Phiên reviewer sửa gom và chạy nhóm cuối, root đọc diff rồiQA quoteGUI1440/1280+RA+commit/push nhánh. Không mainmerge.

RA: docs/RA_D10_VIEC3B_CODEX_2026-10-13.md. Newtest tests/test_project_budget_video_remaining.py đãđăngkíareasv66. related_areas đãchạy; no paidAPI/dữ liệu thật/UI/widgetkey mới.

Vòng reviewer hoàn tất 3 P2: khôi phục margin1,25 nhánh known (fallback không nhân đôi); QC bản cao còn thiếu; metadata incomplete và câu cảnh báo subtotal khi không thể định giá video. Caller shell_parts chi tiết cũng không hiện Video0 hoặc nói fallback đã định giá khi chưa có giá.

Kết quả mới: 3 regression đỏ→124 passed +6 subtests /34,31s; regression UI chi tiết 1 đỏ→32 passed +6 subtests /1,81s (newtest+quality_tier). 146 test riêng biệt giữa các nhóm. QA money_card component thực DB giả 4 PNG 1440/1280 known/missing tại docs/images/d10,0pageerror/exception/overflow. Root cần đọc diff sửa, xem PNG trước commit/push; code chưa commit. Không trả tiền/main/live/data thật/full suite.
