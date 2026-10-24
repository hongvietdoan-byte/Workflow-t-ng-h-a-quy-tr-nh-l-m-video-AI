# CX24-G4 — rà quyết định có thể kiểm bằng code

Sổ có 74 quyết định active; trước nhánh này 55 mục thiếu `enforced_by`. Đã nối 3 ưu tiên: Q-F → `check_qf_safe_paid_buttons`, M6 policy B → `check_e4_attempt_counters`, Q-D3 → `check_qd3_auto_spend_limit`. Sau khi CX23-M82 pha A (`d15d444d`) gộp `core.simple_budget` vào main, đã bỏ `pending` khỏi QD3. Còn 52 mục chưa nối; không đổi chữ quyết định cũ.

Bằng chứng cập nhật 24/10: `py -m core.decisions check` → **Khớp**; `py -m pytest -q -p no:cacheprovider tests/test_decisions.py` → **43 passed / 25.18s**. Dùng fixture tạm, không gọi API trả phí hay ghi dữ liệu dự án.

## Ứng viên check tiếp theo

| Quyết định active | Check đề xuất | Bằng chứng / điều kiện |
|---|---|---|
| `v31-d02-claude-provider-per-project-2026-10-20` | `check_provider_snapshot_matches_job` | Provider/config đã chụp trên job, không đổi theo cấu hình về sau. |
| `v31-d04-field-level-write-guard-2026-10-20` | `check_user_locked_fields_rejected_on_all_write_paths` | Fixture mọi đường ghi, gồm field-level lock và revision. |
| `v31-d05-kho-structured-forms-2026-10-20` | `check_kho_form_schema_revision_and_guard` | Chỉ gắn sau khi M2.3 đủ 6 điều kiện, không coi proposal là ghi thật. |
| `v31-d06-scene-world-map-flexible-2026-10-20` | `check_world_map_2d_fallback_and_3d_truth` | Ca 2D không có 3D và ca 3D có tọa độ. |
| `v31-d07-qc-shadow-guarded-2026-10-20` | `check_qc_shadow_observes_without_blocking` | Shadow chỉ ghi nhận; guarded chỉ chặn nhóm lỗi đã nghiệm thu. |
| `v31-d08-fixture-capture-readonly-2026-10-20` | `check_fixture_capture_readonly_and_fingerprinted` | DB giả/bản sao, không ghi production, có fingerprint cấu hình. |
| `v31-d09-error-registry-json-overrides-db-2026-10-20` | `check_errors_json_is_definition_source` | Fixture xác nhận JSON định nghĩa, DB chỉ là nhật ký/override. |
| `v31-d10-premiere-bg-replace-outside-core-2026-10-20` | `check_premiere_extension_stays_outside_core` | Kiểm import boundary/interface, không gọi ứng dụng ngoài. |
| `v31-c3-1-provider-columns-applied-2026-10-20`; `v31-c3-2-flags-on-main-2026-10-20` | `check_provider_schema_and_approved_flag_defaults` | Migration fixture + trạng thái cờ mặc định; không đọc DB thật. |
| `v31-ep-g1-golden-compat-production-baseline-2026-10-21`; `v31-ep-golden-ab-acceptance-2026-10-21` | `check_golden_compat_baseline_is_separate_from_correctness` | Fixture baseline tái dựng phải ghi nhãn, A/B dùng cùng snapshot. |
| `v31-ep-motion-prompt-user-locked-2026-10-21` | `check_user_locked_motion_prompt_is_preserved` | Prompt user lock không bị builder/repair ghi đè. |
| `v31-ep-flag-lock-policy-2026-10-21`; `v31-ep-k4-k6-flag-baseline-reset-2026-10-21`; `v31-ep-fb-fc-flag-packs-2026-10-21` | `check_flag_lock_requires_per_flag_evidence` | Từng cờ, đúng thứ tự cấu hình, không khóa hàng loạt. |
| `v31-ep-k3-seedance-ref-groups-with-end-frames-2026-10-21`; `ep-2210-g2-ref-end-frames-2026-10-22`; `ep-2210-g3-ref-only-to-first-frame-2026-10-22` | `check_reference_order_and_revision_on_preview` | Giữ đầu/cuối/thứ tự; chuyển nhóm phải preview, revision, stale đúng phụ thuộc. |
| `v31-ep-m6-self-repair-budget-40-2026-10-21`; `ep-2210-q3-self-repair-40-confirm-2026-10-22` | `check_auto_repair_budget_40_percent_and_ep_overage` | Fixture sổ chi: auto bị giới hạn, thao tác EP không ăn trần tự sửa. |
| `v31-ep-m210-lean-package-2026-10-21` | `check_lean_package_keeps_required_refs_and_sha` | Payload fixture theo loại shot, SHA khớp nội dung gửi. |
| `ep-2210-e1-ref-set-owner-2026-10-22`; `ep-2210-e2-approve-all-preview-2026-10-22`; `ep-2210-e6-asset-curator-2026-10-22` | `check_bulk_asset_approval_previews_and_proposes_only` | Chủ sở hữu ref, preview/quyền từng mục; curator không tự ghi/xóa. |
| `ep-2210-e3-offline-director-2026-10-22`; `ep-2210-e5-stage-role-table-2026-10-22`; `ep-2210-g1b-ep-role-package-approved-2026-10-22` | `check_offline_role_and_project_ep_guards` | Vai/EP kiểm theo dự án và chủ dữ liệu, không hardcode Owner. |
| `ep-2210-qa-auto-pick-direction-2026-10-22`; `ep-2210-qb-motion-prompt-auto-2026-10-22` | `check_auto_choice_keeps_options_and_separates_paid_send` | Giữ 3 lựa chọn/khóa EP; duyệt prompt không tự cấp quyền gửi API. |
| `ep-2210-qc-auto-upscale-1080-2026-10-22`; `ep-2210-upscale-definition-2026-10-22` | `check_upscale_scope_quote_and_separate_counter` | Fixture kiểm scope, giá, giữ bản gốc, bộ đếm upscale riêng. |
| `ep-2210-e4-counters-2026-10-22`; `q6c-anchor-lock-main-only-2026-10-23` | `check_e4_attempt_counters`; `check_q6c_primary_anchor_gate` | Bộ đếm E4 đã được check chung; Q6(c) có thể nối test override anchor M47B. |
| `ep-2210-r1-project-report-2026-10-22` | `check_project_report_reads_only_and_splits_costs` | Fixture chứng minh không ghi DB và tách token/dự toán/chi/giữ chỗ. |
| `ep-2310-mode-labels-basic-advanced-2026-10-23`; `ep-2310-m81-r2-answers-2026-10-23`; `ep-2310-m81-approved-m82-go-2026-10-23` | `check_basic_mode_labels_gates_and_80_percent_warning` | Cờ mặc định TẮT, nhãn không đổi quyền; QD3 80% và cổng M8.4 tách biệt. |

Không đề xuất check implementation cho quyết định thuần quy trình/cấp quyền hoặc cần bằng chứng vận hành thật: `lip-sync-lock-after-real-run`, `v31-permission-tiers`, `v31-pilot-three-rounds`, `v31-speedup-milestone-approval`, `v31-cap2-milestone-packages-approved`, `v31-cap3-items-decided`. Các check trên là đề xuất; chỉ thêm `enforced_by` khi test đúng phạm vi và quyết định còn active.
