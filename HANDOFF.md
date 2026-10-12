# HANDOFF — sửa runner NÂNG BẢN CAO 1080p clip nhóm Seedance (12/10, trước khi gen #27)

## Đã xong
1. **Bản cao cắt đúng đoạn nháp** (#24 shot 05 cắt từ 0 s thay vì 1,833–4,833 s):
   - Mỗi take tải về giờ ghi `jobs.clip_span` (cột mới, `core/db.py`): `{start, length, trim, lone_ref, whole}` = vị trí file của
     shot trong clip nguyên của task (phần trong clip nhóm + mép bỏ `clean_edges` + điểm cắt `trim_clip`). Ghi ở
     `VideoRunner._after_download` (leader/lẻ) và `_finish_group` (follower). Chỉ là sổ ghi: không đổi byte file nháp/clip lẻ.
   - `shots.trim_clip(..., at=, out=)`: `at` = cắt tại điểm cho sẵn (không dò lại), `out` = báo điểm đã cắt. Mặc định như cũ.
   - `shots.group_parts(group)` = một nguồn cho `split_group_clip` và cho bản ghi đoạn. `seedance_refs.split` trả thêm `end`.
   - Job `final` có gói gửi `call=submit_final_from_sample` → `_finish_upgrade`: cắt clip 1080p theo `clip_span` của nháp
     (dùng lại `seedance_refs._cut_parts` + `shots.trim_clip(at=)`), không dò lại. Nháp cũ không có span → diag VÀNG
     `final_span_unknown`, cắt theo cách cũ (không im lặng).
2. **Follower ra 1080p từ clip nhóm cao**: `_upgrade_follower` — mỗi shot khác của task nháp được một job `final` (dùng job final
   đang `queued` nếu có), `group_leader`=job final, cùng `external_id`, stamp `input_hash`/`source_job_id` của nháp, `draft_job_id`,
   gói gửi chép từ final (không thêm dòng sổ chi). Không cắt (diag VÀNG `final_follower_skipped`, ghi rõ S<idx> + lý do) khi:
   nháp shot đó không phải nháp người đã duyệt / đầu vào đổi sau nháp (motion…) / shot đã có bản cao khác / nháp không ghi đoạn.
   Cắt lỗi → job follower FAILED + diag ĐỎ `final_follower_cut`, file sai bị xóa, nháp cũ còn trong thùng rác.
   Clip nhóm 1080p nguyên giữ ở `<idx>_group.mp4` cạnh file final → `seedance_refs.recut` (✂) dùng được.
   - Chặn trả tiền 2 lần: `_final_shared_task` — job final mà task nháp của nó đang được job final khác nâng → `_wait` (giữ queued,
     phần của nó cắt từ clip đó); task đã nâng xong → `_hold` (fail có lý do, không nâng lần 2).
3. **Sổ chi giây clip nhóm**: `quality_tier.draft_seconds` ưu tiên `clip_span.whole` (độ dài clip nguyên thật của task nháp; clip lẻ
   đã cắt 3/5 s trước đây bị đo 3 s). Một dòng `usage_events` cho cả nhóm (trên job final gửi), follower không có dòng.

## Test (tests/test_cost_route_e1.py, runner thật + MockVideoProvider tải clip dốc sáng thật bằng ffmpeg, 0 USD)
ĐỎ trên code gốc (6 failed) → XANH: `UpgradeCutsTheDraftPartTests` (leader cắt 1 s không phải 0; follower 4 s/6 s ra 1080p + stamp;
follower đổi motion bị báo không cắt; follower hỏi bản cao giữa chừng chờ, chỉ 1 lần nâng; sổ chi 8 s một dòng) và
`UpgradeLoneTrimmedDraftTests` (lẻ 1,833 s, sổ chi 5 s). Lượt xanh 9 file liên quan: 177 passed, 1 xfailed (xfail Đ8 có sẵn).

## Đang dở / việc mở
- Chưa chạy agent rà khâu liên quan (CLAUDE.md luật 7) — phiên gốc chạy trước khi gộp main (`py tools/related_areas.py`:
  core_infra/step4/step2/step1 + autopilot/budget/dashboard_ui/step3/step5 gọi tới; test CHẬM ở bước gộp).
- Dữ liệu #24 cũ (nháp không có `clip_span`) không tự sửa được: follower 02/03/09 và 05 phải cắt tay từ `_raw`/`_group` (0 USD).
- `_upgrade_draft` với job final THIẾU gói gửi (dữ liệu cũ) coi là nâng khi nháp 2.5, không xác nhận gen mới, không câu sửa.
- Chưa thử nhà cung cấp thật (ClipAI): độ dài clip 1080p có thể lệch vài khung so với nháp; `_cut_span` chấp nhận lệch ≤ 0,35 s.

## Bước kế
Phiên gốc: rà (agent), gộp nhánh, cập nhật TODO; gen #27 nháp mới sẽ có `clip_span` ngay từ lần tải đầu.
