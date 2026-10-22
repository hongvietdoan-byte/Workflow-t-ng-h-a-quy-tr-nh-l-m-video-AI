# CX21-M23 — checkpoint 21/10/2026 (CHƯA HOÀN TẤT)

- Nhánh `codex/v31-m23`, base `3c55a7ff`. Không push/gộp/main/live/TODO/dữ liệu thật, 0 USD.
- Có adapter Kho v1/v2, cờ `kho_forms_v2` OFF (`costs=False`, `verified=False`), chuyển các caller module sang adapter, chọn ảnh v2 và bảo vệ ghi v2 bằng actor + CAS theo mẫu `package_overrides` (M0.10 chỉ có đặc tả, chưa có module write_guard).
- ĐỎ: 3/3 test provenance trước module mới. XANH run gom: 55/55 (provenance, v2, AST readers, forms/render, golden DB replay) 37.69s. Các sửa sau run (nested lock, malformed, profile trong asset dict, flag fixture) CẦN chạy lại.
- Còn BẮT BUỘC trước nghiệm thu: test matrix luồng thật bấm tay/autopilot/v2/v3/multi/clone/Director; end-to-end cùng revision qua Director/image/video/QC + lineage; API BYĐ tích hợp cloud-C (không sửa `core/shot_intent.py`); kiểm identity_declare/director_byd/context; UI lưu hồ sơ v2 actor/revision; test tools draft/finalize v2; provenance outfit items; fixture OFF full golden; tự rà related areas + parent fresh review; targeted regressions và cả bộ tại main trước gộp.
- `kho_profile.validate_dang(conn, project_id, name, dang)` API tạm đã nhắn root/cloud-C; enum chưa khai → VÀNG, không bịa.
- Không tuyên bố reader coverage hoàn tất: AST hiện kiểm các lệnh gọi API cũ, chưa phủ raw SQL profile và reader không nhận conn.

## Cập nhật checkpoint 2
- Đã nối UI actor/revision, ghi AI tools model/revision; đã có capture revision vào package + lineage thực, 245 test xanh / 58.20s.
- Đã test SQLite thật: Director/image/video refs/QC, autopilot bible_gaps, clone_project, digest no-write; 3 mode ImageRunner chuẩn bị + package.
- OPEN còn: BYĐ cloud-C; video submit package/multi full; reader raw SQL ngoại lệ; v1 ON byte kiểm riêng; rollback/audit CAS nguyên tử và profile writers ngoài set_profile; self-review/caller + regressions/full suite. Giữ trạng thái CHƯA HOÀN TẤT.

## Lô nhỏ cuối
- Đã có actual VideoRunner prepare/package (single/multi reference-only, model/route/group/mark giả) + v1 ON/OFF prompt/ref equality; cả 3 ca xanh.
- Fixture đặt PIPELINE_DATA tạm, video PAD_DIR tạm và mock mark. Ba ảnh tổng hợp untracked data/ref_padded ghi trong RA; KHÔNG xóa/commit.
- Dừng ghi sau checkpoint theo parent/quota; chưa hoàn thành nhiệm vụ. Rà kỹ fresh rồi xử lý OPEN ở RA, đặc biệt BYĐ cloud-C + reader/writer coverage/CAS audit. Không push/main/live/test cả bộ.

## Rà hẹp đường ghi — CHẶN GỘP (21/10, cuối lượt)
Chỉ đọc 5 tool calls, chưa test tái hiện; không coi là RÀ KỸ toàn nhánh. Sửa ĐỎ→XANH trước các việc khác sau reset:
- P1 core/assets.py:1421,1436,1461: hồ sơ đã schema v2 nhưng tắt kho_forms_v2 rồi lưu rơi vào writer v1, có thể mất forms/face/hair/outfit/_p/revision. Chọn writer theo schema đã lưu; OFF không được downgrade ngầm. Đối chiếu hợp đồng OFF với dữ liệu v1 và bảo vệ v2 đã tồn tại.
- P2 core/kho_profile.py:264–269,315–319: save_outfit_to_kho chép cả outfit rồi save khóa tất cả sets human/USER_LOCKED, kể cả set AI chưa duyệt. Merge theo set id, giữ provenance set không sửa, chỉ khóa set vừa lưu.
- P2 core/kho_profile.py:249–257: AI gửi lại giá trị human khóa giống hệt có thể vượt bảo vệ rồi thay provenance thành AI/REVIEW_REQUIRED. No-op phải giữ nguyên giá trị + provenance; khác mới proposal.
Reviewer tiếp tục: /root/cx21_m23_write_review (đã đọc đúng vùng); ưu tiên gom test/sửa cả ba trong một lượt, rồi root đọc fixdiff. Còn full review readers/lineage/video/rights chưa làm. Không gộp, không sử dụng với dữ liệu thật.
Quota cuối: 5h ĐÃ DÙNG89%, còn11%; tuần57%, còn43%. Reset tự nhiên 21/10 13:47:05 Asia/Saigon. Không mở lượt sửa có nguy cơ vượt95%; giữ automation30phút.

## Checkpoint fresh review ba regression
- ĐỎ 3/3 với AST hàm cũ từ HEAD trong tiến trình riêng; XANH 28/28 provenance/v2/readers (5.08s).
- Ba sửa writer OFF/v2, provenance outfit per-id và AI locked no-op đã kiểm bằng SQLite tạm. Chưa sản xuất; các OPEN khác phía trên vẫn giữ.

## Checkpoint transaction/audit
- Writer SAVEPOINT + audit_log metadata/hash nguyên tử; actor/revision typeguard. ĐỎ 2 fail / 1 pass; XANH 45/45 (4.88s).
- OPEN mới xác nhận: UI chưa có nút lưu outfit vào Kho (helper không phải entrypoint). Raw SQL readers/AST alias và BYĐ cloud-C vẫn chưa đóng.

## UI lưu outfit đã nối sau cờ OFF
- Nút owner-only với recheck users role/active; fake UI + ảnh khác asset được kiểm. 43/43 Kho (5.57s).
- OPEN UI entrypoint phía trên đã có code/test, chưa chạy Dashboard thật. Raw SQL vẫn OPEN; AST alias đã mở rộng.

## Checkpoint fresh review độc lập (chưa XONG)
- Đã đóng: merge v2 khác cấu trúc/provenance; digest OFF v2 write; raw diagnostic/review readers; schema malformed + AI scalar metadata; lọc form/outfit chưa duyệt; CAS/audit atomic và revision đổi giữa phases.
- XANH 209 assets/golden (79.54s), rồi 115 Kho/schema/change_review (16.93s). Chi tiết RED/fixture correction/SQL inventory/sáu điều kiện ở RA.
- Còn local: dashboard/admin.py profile_form actor hardcode phải lấy identity email xác thực cho v2 và xử lý error/CAS nhánh seed.
- External: BYĐ core/shot_intent.py thuộc cloud-C chưa được phép sửa; cần root tích hợp và acceptance/full suite máy chính. Không nghiệm thu, không XONG.

## Checkpoint cuối của lượt fresh review
- Actor UI hồ sơ v2 đã dùng email identity active + CAS cho cả save/seed, error rõ; không hardcode who.
- Chấp nhận `_p.profile` không state đúng M0.9, giữ guard state ở mọi field; matcher v2 không khớp chuỗi con ice/Alice, BYĐ exact vẫn được chọn.
- ĐỎ actor1; root profile/matcher3. XANH cuối 125/125 (13.38s). Root đọc diff commit trước push.
- Chưa XONG: BYĐ cloud-C/shot_intent không tự sửa; máy chính full suite/acceptance/production vẫn chưa chạy. Không còn mở rộng phạm vi trong lượt này.

## Nối BYĐ sau M2 main (22/10)
- Merge main 0fcedc73 đã chốt; giữ union cờ golden OFF, không đổi version areas.
- validate/assess thêm context project_id; Director/byd_fill truyền project; ON kiểm scalar/list/beat bằng adapter, thiếu/ngoài enum chỉ WARN, OFF giữ mức M21 cũ.
- forms_for_shot chuyển raw BYĐ sang shot_intent.read. Code và test mới chưa kết thúc rà độc lập; root thực hiện trước push.
- Không triển khai R5 vat[].bien_the/stage_shape hoặc quyết định chọn dạng ảnh theo nhiều nhịp ngoài đề M23. Không test production/golden thật/full suite.
- Test cuối XANH103/103 (636,06s) v2/readers/router/golden. Nhóm Director/byd_fill/shot_intent/M21 trước đó qua; AST caller mới đã sửa. Chờ root rà độc lập rồi push/trạng thái; M23 chưa được tự đánh dấu XONG toàn bộ khi còn scopes nêu trên.

## Vòng sửa sau rà độc lập (22/10)
- Hai P2 đã tái hiện ĐỎ5/5 rồi sửa: enum/selector kiểm mã Kho đúng link dự án; singleton-list dùng cùng ref với scalar; nhiều dạng/theo nhịp giữ VÀNG/REVIEW, không tự chọn first/final.
- XANH89/89 (80,82s) một batch v2/readers/M21/Director/byd_fill; không chạy lại golden. Root cần đọc diff sửa trước push.
- R5/vat[].bien_the và policy chọn ảnh nhiều nhịp vẫn OPEN, chưa tự báo toàn M23 XONG; không migration/production/full suite.
