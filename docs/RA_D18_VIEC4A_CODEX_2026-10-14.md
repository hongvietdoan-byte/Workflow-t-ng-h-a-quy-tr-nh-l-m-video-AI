# Tự rà Đ18.4a — trước rà độc lập

Nhánh `codex/d18-viec4a-schema`, base `000c9e1f`; chưa commit/gộp/push.
Người dùng duyệt phạm vi đề sau `64452104`. Chỉ schema/resolver thuần.
Areas version giữ **78 theo base thực tế**, không hạ xuống 77 trong prompt cũ.

## Bằng chứng

Một lệnh target hai file, không test rộng; PYTHONUTF8=1, --tb=no,
-p no:cacheprovider. Lượt 1: hai collection error (module chưa tồn tại).
Lượt 2: một collection error import fixture (không gọi là lỗi schema).
Lượt 3: 27 passed/0,43s. Lượt 4 sau sửa ID Kho thành int + test bool/âm:
**29 passed/0,49s**. Không nới test. Vượt dự tính 3 lượt do sửa hợp đồng ID
sau đối chiếu manifest; không dùng lỗi import fixture làm chứng cứ lỗi nghiệp vụ.
Chưa cả bộ Windows, chưa thử chất lượng ảnh/video hoặc ca dữ liệu thật.

## Checklist 2b.5

- Không path tương đối/I/O/env/provider trong module mới; không data/env thật.
- Không sửa caller tự động/lô/autopilot; không flags/defaults/runner/UI.
- Không thay sandbox/network, không gọi model/API hoặc subprocess native.
- Không bỏ dấu/so từ ngắn, không xử lý title như content, không auto ID rename.
- Test import module mới dưới patch.object(os,environ,dict giả), không patch.dict.
- Scope manifest project/scene/Kho dùng positive int không bool; IDs aggregate
  opaque string. Không scan DB/Kho. Pin index theo (id,revision), không latest.
- Scan payload và DAG iterative, giới hạn node/depth/string; lỗi sanitize.
- Fixture không chứng minh render measured; unknown warning, measurement unknown.
- Inheritance/hidden/in/lying/spawn/despawn/continuation/hash/deepcopy/locks đã
  có kiểm giả. Không claim sửa #24/#27 hoặc storage/migration đã xong.

## Điểm cần vòng rà độc lập xác nhận

1. Warning hiện lấy từ toàn bundle và path theo chỉ số stage. Reorder nhiều
   stage có unknown có thể đổi hash qua warning path dù dependencies giữ nguyên;
   nên canonical warning theo stage pin và lọc đúng dependency trước hash.
2. validate_bundle hiện kiểm cấu trúc/FK/DAG; lifecycle/presence/quan hệ guard
   tại resolver. 4b phải resolve affected states trước apply. Rà xem có cần
   public validator semantic thống nhất để 4b không thể vô ý chỉ validate schema.
3. shapes/object geometry/pose là mô tả nguồn, chưa diễn giải mesh/skeleton.
   Rà mức strict nested keys/provenance/unknown dimensions theo phạm vi 4a.
4. Chưa kiểm root không-parent khác initial_state và quan hệ ancestor của
   shot start→end. Cần reviewer đánh giá guard orphan/lineage trước nhận 4a.
5. Resolver materialize lineage mỗi lần, chưa memoize nhiều beat/state; node
   budget chống nesting nhưng chi phí dài graph có thể tăng theo số beat.
6. tests/__init__.py và conftest sẵn có đọc env lúc pytest bootstrap trước
   thân test; các module mới không đọc env. Không sửa framework chung trong nhánh.

Đây là tự rà có điểm mở, **không phải nghiệm thu đủ toàn bộ 4a**. Root giao
reviewer sạch context, gom lỗi rồi sửa một vòng trước commit/cả bộ/gộp.


## RÀ KỸ độc lập + sửa gom (reviewer Codex)

Đã gửi root toàn bộ nhóm lỗi trước sửa; sửa một vòng, không storage/UI/caller.

| Vị trí gốc | Lỗi và cách sửa | Test hồi quy |
|---|---|---|
| schema:110,119 | ident ASCII chặn users.email; author validator TEXT riêng, không echo | email_author_contract |
| resolver:94–98 | warning whole bundle/index làm hash lệch; canonical pin stage và lọc dependencies | warning_dependency_order_and_irrelevant_stage |
| schema:217–247,285–305 | orphan root, shot sibling/reversed beat, setup khác start; strict root/lineage/pin | review_semantic_and_nested_rejections, review_malformed_sanitized |
| schema:154–196 | shapes/object geometry/locks/height chưa guard; nested descriptor strict, lock path và unknown warning | strict_nested_geometry_valid_and_budget_options, missing_height_warns |
| resolver:25–27,112–127 | pin extra và malformed cache lookup, lặp beats không budget; validate request trước lookup, cache độc lập, work count cả payload | public_validation_malformed_and_request_exact_pin, snapshot_beats_cache_has_no_aliases |
| resolver:30–88 | service dễ nhận shape-only; public validate_registry materialize mọi state + POV | safe_semantic_validator_rejects, semantic_public_validation_and_budget |
| schema:41–53,232 | số khổng lồ và option cap/traversal không giới hạn; bit cap + resource cap | review_malformed_sanitized, strict_nested_geometry_valid_and_budget_options |

ĐỎ thật 10 failed/29 passed 0,69s; XANH 39 passed 0,74s; lượt target cuối
49 passed 0,55s. Tổng 3 lượt, cùng hai file, --tb=no/no cache; test autouse
thay OBJECT os.environ bằng dict giả ở mọi call. Không API/provider/data thật.
Sau lượt cuối chỉ chuyển request validation trước cache lookup (guard nhỏ);
root xác nhận phần này bằng lượt integration. Không nới test.

6 điểm mở builder: (1),(2),(4),(5) đã có guard/hợp đồng; (3) descriptor strict
nhưng không có mesh/skeleton như phạm vi 4a; (6) bootstrap framework cũ giữ
nguyên, module mới thuần. Còn mở: fullsuite Windows/integration/root đọc lần 2;
benchmark Dashboard 4–5 projects; storage/ACL/lock enforcement/adapter/real QA
thuộc 4b–4f, chưa claim #24/#27/renderer. Areas version giữ78, không commit.

## Root rà lần hai và chốt target

- Đã đọc phần sửa schema/resolver/protocol: author TEXT, revision pin, nested geometry/lock, root/shot lineage, canonical warning chỉ dependency, semantic entry, cache deepcopies và trần work. Chưa có caller sản xuất, không đổi cờ/keys hay luồng OFF.
- Guard request chuyển trước cache sau lượt reviewer: root thêm ca public API với ID None/list/dict, đặt lại thứ tự cũ để tái hiện **2 fail/50 pass**, khôi phục guard → **52 pass/0,50s**.
- Root phát hiện ID Kho vượt INTEGER SQLite còn qua schema: thêm ca source_asset_id=2**63 → **1 fail/52 pass**, chặn mọi ID số/revision ở 1..2**63-1 → **53 passed/0,49s**.
- Tổng lượt hẹp: builder4 + reviewer3 + root4; vượt dự tính đã ghi rõ, thêm lượt root do có guard đổi sau GREEN và lỗi giới hạn ID mới, không chạy lại rộng/cả bộ. Không nới test.
- `git diff --check` sạch. RÀ KỸ độc lập và root rà sửa lần hai xong cho phạm vi 4a. Còn cả bộ Windows tại integration; benchmark Dashboard, mesh/skeleton/chất lượng thật và storage/ACL/migration/adapter/UI thuộc bước sau. Không gọi API, không đọc/ghi dữ liệu thật.
