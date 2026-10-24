# Báo cáo dự án — 2026-10-24

Ngày đo: 2026-10-24T15:18:45+07:00 · Asia/Saigon · kỳ 2026-10-18 → 2026-10-24

Chỉ đọc, 0 USD. UNKNOWN không phải 0. Nguồn phiên có thể chỉ bao phủ một phần hoạt động.

## 1. Tóm tắt 1 phút

| Chỉ số | Giá trị | Đơn vị | So kỳ trước | Nguồn | Ngày đo |
|---|---|---|---|---|---|
| code_pct | 71.1 | % | không có dữ liệu so sánh | devsys/plans.json → devsys.plan_progress, snapshot lúc đo | 2026-10-24T15:18:45+07:00 |
| gate_pct | 9.2 | % | không có dữ liệu so sánh | devsys/plans.json → devsys.plan_progress, snapshot lúc đo | 2026-10-24T15:18:45+07:00 |
| ep_decisions | 30 |  | không có dữ liệu so sánh | data/decisions.json snapshot lúc đo, phase có khai báo và khác APPROVED | 2026-10-24T15:18:45+07:00 |

Trạng thái theo nguồn hiện có: ĐỎ. Ba điểm: code khác cổng; token khác USD; khoản giữ chỗ khác chi thực tế. Không thay EP nghiệm thu.

## 2. Tiến độ V3.1 theo mốc M0–M8

| Chỉ số | Giá trị | Đơn vị | So kỳ trước | Nguồn | Ngày đo |
|---|---|---|---|---|---|
| code_pct | 71.1 | % | không có dữ liệu so sánh | devsys/plans.json → devsys.plan_progress, snapshot lúc đo | 2026-10-24T15:18:45+07:00 |
| gate_pct | 9.2 | % | không có dữ liệu so sánh | devsys/plans.json → devsys.plan_progress, snapshot lúc đo | 2026-10-24T15:18:45+07:00 |

Nguồn: devsys.plan_progress; ngày đo 2026-10-24T15:18:45+07:00. Các hàng mốc chưa có đối chiếu riêng ⇒ so kỳ trước: UNKNOWN.

| Mốc | Việc | Code % | Cổng % |
|---|---|---|---|
| M0 | 12 | 100.0 | 88.9 |
| M1 | 9 | 100.0 | 0.0 |
| M2 | 10 | 87.0 | 0.0 |
| M3 | 5 | 100.0 | 0.0 |
| M4 | 8 | 84.4 | 0.0 |
| M5 | 5 | 54.5 | 0.0 |
| M6 | 13 | 26.8 | 0.0 |
| M7 | 8 | 81.2 | 0.0 |
| M8 | 5 | 45.8 | 0.0 |
| M9 | 13 | 47.2 | 0.0 |

## 3. Khối lượng

| Chỉ số | Giá trị | Đơn vị | So kỳ trước | Nguồn | Ngày đo |
|---|---|---|---|---|---|
| commits_week | 1865 | commit | không có dữ liệu so sánh | git rev-list, kỳ 7 ngày Asia/Saigon | 2026-10-24T15:18:45+07:00 |
| test_functions_static | 7261 | hàm, không phải cases xanh | không có dữ liệu so sánh | git ls-files + đếm định nghĩa test tĩnh | 2026-10-24T15:18:45+07:00 |
| sessions | UNKNOWN — không có dữ liệu: mẫu token thiếu trường/cache, xung đột ID hoặc nguồn chưa đầy đủ | phiên | không có dữ liệu so sánh | JSONL allowlist metadata đến ngày báo cáo | 2026-10-24T15:18:45+07:00 |
| days | UNKNOWN — không có dữ liệu: mẫu token thiếu trường/cache, xung đột ID hoặc nguồn chưa đầy đủ | ngày | không có dữ liệu so sánh | JSONL allowlist metadata đến ngày báo cáo | 2026-10-24T15:18:45+07:00 |

Nguồn: git ls-files và dòng mã tĩnh; ngày đo 2026-10-24T15:18:45+07:00. So kỳ trước từng thư mục: UNKNOWN.

| Thư mục nguồn | File | Dòng tĩnh |
|---|---|---|
| core | 268 | 98871 |
| dashboard | 78 | 18059 |
| devsys | 22 | 7690 |
| khác | 28 | 2481 |
| tests | 540 | 110562 |
| tools | 141 | 31721 |

## 4. Chi phí — bốn loại riêng

| Chỉ số | Giá trị | Đơn vị | So kỳ trước | Nguồn | Ngày đo |
|---|---|---|---|---|---|
| tokens | UNKNOWN — không có dữ liệu: mẫu token thiếu trường/cache, xung đột ID hoặc nguồn chưa đầy đủ | token, không phải USD | không có dữ liệu so sánh | JSONL thư mục dự án được chỉ định; message.id cumulative max xuyên file | 2026-10-24T15:18:45+07:00 |
| build_tokens | UNKNOWN — không có dữ liệu: chưa tách được xây công cụ với vận hành video; không suy mọi phiên repo là build | token | không có dữ liệu so sánh | JSONL không có liên kết dự án video/loại tác vụ đáng tin | 2026-10-24T15:18:45+07:00 |
| video_operation_tokens | UNKNOWN — không có dữ liệu: chưa tách được xây công cụ với vận hành video; không suy mọi phiên repo là build | token | không có dữ liệu so sánh | JSONL không có liên kết dự án video/loại tác vụ đáng tin | 2026-10-24T15:18:45+07:00 |
| estimated_usd | UNKNOWN — không có dữ liệu: dự toán snapshot chỉ có tại lúc đo, không phục hồi ngày quá khứ hoặc approved_at tương lai; total thiếu/không hợp lệ cũng UNKNOWN | USD | không có dữ liệu so sánh | app_settings project_budget:<id>.total, snapshot | 2026-10-24T15:18:45+07:00 |
| actual_usd | UNKNOWN — không có dữ liệu: usage_events chỉ có lượng dùng/model; không có USD chi thực tế, không quy đổi giá hiện tại thành hóa đơn | USD | không có dữ liệu so sánh | usage_events.usd nếu có, không tự quy đổi quantity | 2026-10-24T15:18:45+07:00 |
| held_usd | 0 | USD | không có dữ liệu so sánh | llm_holds TTL 30 phút, phần giữ chỗ LLM hiện tại, không phải tổng mọi job | 2026-10-24T15:18:45+07:00 |

Nguồn token: JSONL metadata được chỉ định; nguồn USD: snapshot CSDL. Ngày đo 2026-10-24T15:18:45+07:00. So kỳ trước từng model/dự án: UNKNOWN. Độ phủ token: {"files": 37, "records": 7640, "missing_id": 0, "conflicts": 75, "incomplete": 6, "malformed": 1}.

Token phiên dự án/phạm vi nguồn; chưa tách được xây công cụ với vận hành video. Không phải giá USD; llm_calls production chưa dùng phân loại và không cộng trùng vào tổng JSONL:

| Tháng Asia/Saigon | Model | Vai | Input | Output | Cache read | Cache write |
|---|---|---|---|---|---|---|
| 2026-10 | claude-sonnet-5 | main | 2 | 4 | 22255 | 39569 |
| 2026-10 | claude-opus-5-5 | main | 2578 | 728517 | 296296108 | 4677786 |
| 2026-09 | claude-sonnet-5 | main | 3250 | 829361 | 893578384 | 2115579 |
| 2026-10 | claude-opus-5-5 | agent | 1844 | 232701 | 138867591 | 4228625 |
| 2026-10 | claude-sonnet-5-5 | agent | 72 | 9011 | 2298190 | 562485 |
| 2026-09 | claude-opus-5-5 | main | 358 | 155868 | 138818271 | 897495 |
| 2026-10 | UNKNOWN | agent | 0 | 0 | 0 | 0 |
| 2026-10 | UNKNOWN | main | 0 | 0 | 0 | 0 |

Chi sản xuất theo dự án (không tự gán chi xây công cụ vào video):

| Dự án | Dự toán USD | Chi thực USD |
|---|---|---|
| 31 | UNKNOWN | UNKNOWN |
| 8 | 45.23 | UNKNOWN |

## 5. Chất lượng

| Chỉ số | Giá trị | Đơn vị | So kỳ trước | Nguồn | Ngày đo |
|---|---|---|---|---|---|
| final_outputs | 14 | artifact | không có dữ liệu so sánh | outputs.kind=final, số bản ghi artifact, không kiểm file | 2026-10-24T15:18:45+07:00 |
| delivered_projects | UNKNOWN — không có dữ liệu: ngày artifact/giao thiếu timezone hoặc không đọc được; không suy lịch sử | dự án | không có dữ liệu so sánh | deliveries DISTINCT project_id, số dự án ghi đã giao | 2026-10-24T15:18:45+07:00 |
| first_pass_rate | 40.13157894736842 | % | không có dữ liệu so sánh | jobs + job_events approved/rejected/running | 2026-10-24T15:18:45+07:00 |
| test_passed | UNKNOWN — không có dữ liệu: chưa có artifact test có cấu trúc; không chạy test để đếm |  | không có dữ liệu so sánh | nguồn chất lượng chưa được nghiệm thu | 2026-10-24T15:18:45+07:00 |
| test_failed | UNKNOWN — không có dữ liệu: chưa có artifact test có cấu trúc; không chạy test để đếm |  | không có dữ liệu so sánh | nguồn chất lượng chưa được nghiệm thu | 2026-10-24T15:18:45+07:00 |
| ledger_rows | 6363 | dòng | không có dữ liệu so sánh | usage_events COUNT metadata snapshot | 2026-10-24T15:18:45+07:00 |

Nguồn: jobs + job_events snapshot mode=ro; ngày đo 2026-10-24T15:18:45+07:00. So kỳ trước từng loại: UNKNOWN.

Lịch sử đạt lần đầu: mẫu số gồm shot đã có phán quyết approved/rejected; tử số approved ngay phán quyết đầu, đúng một running, không failed trước đó; thiếu lịch sử ⇒ UNKNOWN.

| Loại | Đạt lần đầu | Đã phán quyết đủ lịch sử | Thiếu lịch sử | Có gen lại |
|---|---|---|---|---|
| image_gen | 84 | 182 | 0 | 139 |
| video_gen | 38 | 122 | 0 | 106 |

## 6. Rủi ro mở

| Chỉ số | Giá trị | Đơn vị | So kỳ trước | Nguồn | Ngày đo |
|---|---|---|---|---|---|
| open_errors | 91 |  | không có dữ liệu so sánh | devsys/errors.json snapshot lúc đo, status khác VERIFIED | 2026-10-24T15:18:45+07:00 |

| Mã lỗi | Khâu | Loại | Mức | Trạng thái |
|---|---|---|---|---|
| P31-G1 | L6 | continuity | vua | IN_PROGRESS |
| P31-G2 | L6 | ti_le | vua | OPEN |
| P31-G3 | L6 | may | vua | IN_PROGRESS |
| P31-G4 | L8 | goi_anh | vua | OPEN |
| P31-G5 | L8 | so_goi | thap | OPEN |
| P31-G6 | L16 | chen_shot | vua | OPEN |
| P31-G7 | L8 | goi_anh | vua | FIXED_UNVERIFIED |
| P31-G8 | L6 | kho_3d | vua | FIXED_UNVERIFIED |
| P31-G9 | L3 | bao_nham | thap | OPEN |
| P31-G10 | L12 | khop_moi | vua | FIXED_UNVERIFIED |
| P31-G11 | L11 | motion | vua | OPEN |
| P31-G12 | L12 | chu_viet | thap | OPEN |
| P31-G13 | L12 | do_dai_prompt | vua | OPEN |
| P31-G14 | L14a | thoi_luong | vua | OPEN |
| P31-G15 | L13 | khop_moi | thap | OPEN |
| P31-G16 | L13 | khop_moi | thap | OPEN |
| P31-G17 | L13 | khop_moi | thap | OPEN |
| P31-G18 | L3 | byd | vua | OPEN |
| P31-G19 | L9 | khung_dau | vua | OPEN |
| P31-G20 | L13 | bao_nham | thap | OPEN |
| P31-G21 | L16 | byd | vua | OPEN |
| P31-G22 | L16 | byd | vua | OPEN |
| P31-G23 | L12 | cong_cu | vua | OPEN |
| P31-G24 | L12 | router | vua | FIXED_UNVERIFIED |
| P31-G26 | L11 | may | vua | OPEN |
| P31-G27 | L12 | goi_video | cao | FIXED_UNVERIFIED |
| P31-G28 | L13 | khung_dau | vua | OPEN |
| P31-G29 | L12 | cong_cu | vua | OPEN |
| P31-G30 | L12 | kho_chu_the | cao | FIXED_UNVERIFIED |
| P31-G31 | UNKNOWN | chi_phi | vua | OPEN |
| P31-G32 | L13 | router | vua | FIXED_UNVERIFIED |
| P31-G33 | UNKNOWN | provider | cao | IN_PROGRESS |
| P31-G34 | L16 | giu_job | vua | OPEN |
| P31-G35 | L16 | giu_job | cao | FIXED_UNVERIFIED |
| P31-G36 | L13 | tam_dung | cao | IN_PROGRESS |
| P31-G37 | L13 | dang_nhan_vat | vua | OPEN |
| P31-G38 | L5 | kho_forms | vua | OPEN |
| P31-G39 | UNKNOWN | cong_cu | vua | OPEN |
| P31-G40 | L9 | khung_dau | vua | OPEN |
| P31-G41 | L3b | vi_tri | vua | OPEN |
| P31-G42 | L14a | loi_dan | vua | OPEN |
| P31-G43 | L3b | vi_tri | vua | IN_PROGRESS |
| P31-G44 | L3b | vi_tri | vua | OPEN |
| P31-G45 | L3b | vi_tri | vua | OPEN |
| P31-G46 | L6 | vi_tri | cao | IN_PROGRESS |
| P31-G47 | L6 | vi_tri | vua | OPEN |
| P31-G48 | L9 | vat | vua | OPEN |
| P31-G49 | L6 | may | vua | OPEN |
| P31-G50 | L3b | vi_tri | vua | OPEN |
| P31-G51 | L13 | chuyen_dong | vua | OPEN |
| P31-G52 | L13 | continuity | vua | OPEN |
| P31-G53 | L12 | khop_moi | thap | OPEN |
| P31-G54 | L12 | do_dai_prompt | vua | OPEN |
| P31-G55 | UNKNOWN | van_hanh | vua | OPEN |
| P31-G56 | UNKNOWN | diag | thap | OPEN |
| P31-G57 | UNKNOWN | provider | vua | IN_PROGRESS |
| P31-G58 | L12 | kho_chu_the | cao | FIXED_UNVERIFIED |
| P33-A1 | L13 | vong_doi_job | cao | FIXED_UNVERIFIED |
| P33-A2 | L16 | provider | cao | IN_PROGRESS |
| P33-A3 | UNKNOWN | provider | cao | FIXED_UNVERIFIED |
| P33-A4 | L10 | khoa_tay | cao | OPEN |
| P33-A5 | L9 | bao_nham | vua | FIXED_UNVERIFIED |
| P33-A6 | L16 | bao_nham | thap | OPEN |
| P33-A7 | UNKNOWN | chi_phi | vua | OPEN |
| P33-A8 | UNKNOWN | chi_phi | vua | OPEN |
| P33-A9 | UNKNOWN | chi_phi | thap | OPEN |
| P33-A10 | L6 | may | vua | IN_PROGRESS |
| P33-A11 | L13 | thong_diep | thap | OPEN |
| P33-A12 | L3 | byd | vua | OPEN |
| P33-A13 | UNKNOWN | provider | cao | FIXED_UNVERIFIED |
| P33-A14 | UNKNOWN | chi_phi | thap | OPEN |
| P33-A15 | L13 | vong_doi_job | vua | FIXED_UNVERIFIED |
| P33-B1 | L5 | anh_mau | vua | OPEN |
| P33-B2 | L7 | ref_bau_troi | vua | OPEN |
| P33-B3 | L8 | vi_tri | vua | OPEN |
| P33-B4 | L6 | nen_3d | thap | OPEN |
| P33-B5 | L6 | bo_cuc | thap | OPEN |
| P33-B6 | L8 | cong | thap | WONT_FIX |
| P33-B7 | L11 | chu_viet | thap | OPEN |
| P33-B8 | L12 | video_ref | vua | OPEN |
| P33-B9 | L13 | khung_dau | vua | OPEN |
| P33-B10 | L11 | chu_viet | thap | OPEN |
| P33-B11 | L15a | dung | thap | OPEN |
| P33-B12 | UNKNOWN | van_hanh | thap | WONT_FIX |
| V21-R3 | L13 | qc_crash | vua | FIXED_UNVERIFIED |
| V31-R2 | UNKNOWN | provider | cao | FIXED_UNVERIFIED |
| V31-GOC1 | L6 | root_cause | vua | IN_PROGRESS |
| V31-GOC2 | L6 | may | vua | IN_PROGRESS |
| V31-GOC3 | L11 | root_cause | vua | IN_PROGRESS |
| V31-GOC4 | L3 | byd | vua | IN_PROGRESS |
| V31-GOC5 | L6 | root_cause | vua | OPEN |

- Nguồn token chưa đầy đủ; không suy USD từ token hoặc hạn mức tài khoản
- Không suy tỉ lệ đạt lần đầu từ retry_count; không coi lượng usage là hóa đơn USD.

## 7. Việc cần EP quyết và kế hoạch hai tuần

| Chỉ số | Giá trị | Đơn vị | So kỳ trước | Nguồn | Ngày đo |
|---|---|---|---|---|---|
| ep_decisions | 30 |  | không có dữ liệu so sánh | data/decisions.json snapshot lúc đo, phase có khai báo và khác APPROVED | 2026-10-24T15:18:45+07:00 |
| decision_phase_unknown | 60 |  | không có dữ liệu so sánh | data/decisions.json, record legacy thiếu phase | 2026-10-24T15:18:45+07:00 |
| mail_questions | 0 |  | không có dữ liệu so sánh | hộp thư sự kiện snapshot lúc đo, hỏi chưa có reply_to | 2026-10-24T15:18:45+07:00 |

Chỉ dẫn mở nguồn theo ID, không xuất văn bản tự do/email của quyết định hoặc tin:
- Quyết định ep-2210-p1-pets-2026-10-22: APPROVED_IN_PRINCIPLE
- Quyết định ep-2210-p2-tieu-nhi-plan-lessons-2026-10-22: APPROVED_IN_PRINCIPLE
- Quyết định ep-2210-q3-self-repair-40-confirm-2026-10-22: APPROVED_IN_PRINCIPLE
- Quyết định ep-2210-e1-ref-set-owner-2026-10-22: APPROVED_IN_PRINCIPLE
- Quyết định ep-2210-e2-approve-all-preview-2026-10-22: APPROVED_IN_PRINCIPLE
- Quyết định ep-2210-e3-offline-director-2026-10-22: PENDING_VERIFICATION
- Quyết định ep-2210-e4-counters-2026-10-22: APPROVED_IN_PRINCIPLE
- Quyết định ep-2210-e5-stage-role-table-2026-10-22: APPROVED_IN_PRINCIPLE
- Quyết định ep-2210-e6-asset-curator-2026-10-22: APPROVED_IN_PRINCIPLE
- Quyết định ep-2210-qa-auto-pick-direction-2026-10-22: APPROVED_IN_PRINCIPLE
- Quyết định ep-2210-qb-motion-prompt-auto-2026-10-22: APPROVED_IN_PRINCIPLE
- Quyết định ep-2210-qc-auto-upscale-1080-2026-10-22: PENDING_VERIFICATION
- Quyết định ep-2210-qd-film-budget-hard-stop-2026-10-22: PENDING_EP_CONFLICT
- Quyết định ep-2210-qe-default-mode-2026-10-22: APPROVED_IN_PRINCIPLE
- Quyết định ep-2210-qf-money-safety-first-2026-10-22: APPROVED_IN_PRINCIPLE
- Quyết định ep-2210-g1-ep-role-per-project-2026-10-22: PENDING_VERIFICATION
- Quyết định ep-2210-g2-ref-end-frames-2026-10-22: APPROVED_IN_PRINCIPLE
- Quyết định ep-2210-g3-ref-only-to-first-frame-2026-10-22: APPROVED_IN_PRINCIPLE
- Quyết định ep-2210-c1-enterprise-llm-2026-10-22: PENDING_VERIFICATION
- Quyết định ep-2210-r1-project-report-2026-10-22: APPROVED_IN_PRINCIPLE
- Quyết định ep-2210-d2-old-agent-branches-2026-10-22: PENDING_VERIFICATION
- Quyết định ep-2210-qd2-hard-stop-automated-only-2026-10-22: APPROVED_IN_PRINCIPLE
- Quyết định ep-2210-g1b-ep-role-package-approved-2026-10-22: APPROVED_IN_PRINCIPLE
- Quyết định ep-2210-upscale-definition-2026-10-22: APPROVED_IN_PRINCIPLE
- Quyết định q6c-anchor-lock-main-only-2026-10-23: APPROVED_IN_PRINCIPLE
- Quyết định ep-2310-mode-labels-basic-advanced-2026-10-23: APPROVED_IN_PRINCIPLE
- Quyết định ep-2310-qd3-auto-spend-limit-2026-10-23: APPROVED_IN_PRINCIPLE
- Quyết định ep-2310-m84-gate-before-auto-paid-2026-10-23: PENDING_VERIFICATION
- Quyết định ep-2310-m81-r2-answers-2026-10-23: APPROVED_IN_PRINCIPLE
- Quyết định ep-2410-test-project-cap-20usd-2026-10-24: APPROVED_IN_PRINCIPLE

ĐỀ XUẤT, chưa phải EP phê duyệt
- Đối soát cổng nghiệm thu còn mở theo kế hoạch chính
- Ưu tiên quyết định EP và lỗi mở trước khi mở phạm vi mới
