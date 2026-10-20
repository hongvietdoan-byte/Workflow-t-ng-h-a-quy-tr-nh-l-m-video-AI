# V3.1 — Bảng chốt Cấp 2 (phạm vi code theo milestone) và Cấp 3 (xin riêng) — 20/10/2026

Theo quyết định `v31-speedup-milestone-approval-2026-10-20` (người dùng 20/10: "áp dụng cả 3 cách rút ngắn"): Cấp 2 duyệt theo CẢ
milestone; Cấp 3 trình sớm một gói, duyệt TỪNG MỤC. Cấp quyền gốc: `v31-permission-tiers-2026-10-20`. Nguồn phạm vi: kế hoạch chính
`docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md` (mục 4a nghiệm thu, mục 5 việc), gói sửa `docs/V3_1_GOI_SUA_VA_RUI_RO_2026-10-20.md`.

Cách trả lời: ghi cột "Người dùng" = **Duyệt / Không / Để sau** (hoặc nói trong chat theo mã G2-x / C3-x).

## A. Cấp 2 — gói phạm vi code theo milestone

Chung cho mọi gói: chi phí thử 0 USD (provider giả, test offline); mọi thay đổi sau cờ mới TẮT trừ khi ghi khác; cờ TẮT = hành vi cũ
(golden byte khi M1.9 có); quy ước 7 (agent rà khu vực liên quan) + cả bộ test trước gộp; rollback = tắt cờ / revert commit.

| Mã | Gói | Việc trong gói | File / module chính | Hợp đồng / tác động đường cũ | Nghiệm thu | Đề xuất | Người dùng |
|---|---|---|---|---|---|---|---|
| G2-1 | **M0.4–M0.5 Sổ lỗi** (D09 = C) | schema `devsys/errors.json` + test hợp đồng; nhập G1–G58, A1–A15, B1–B12 có nguồn | `devsys/errors.json`, `devsys/errors.py`, `tests/test_error_registry.py`, trang devsys | chỉ devsys, không đụng pipeline sản xuất | mã không trùng; VERIFIED cần commit + test + bằng chứng chạy thật; coverage 100 % (G25 khuyết ghi rõ) | Duyệt ngay | |
| G2-2 | **M1 Nền tin cậy** (trừ phần Cấp 3 ở C3-1, C3-3) | M1.2 succeed/poll nguyên tử + ghi tệp tạm rồi đổi tên; M1.3 kiểm tạm dừng ngay trước `provider.submit` (cả thử lại / lùi model); M1.4b provider Claude theo dự án + snapshot theo job + dừng khi hết quota; M1.5 kiểm Kho chủ thể trước gửi video (code, cờ TẮT); M1.6 ước tính giá đúng gói gửi + giá video trong `pregen_check`; M1.7 báo Dashboard chạy code cũ, gộp diag lặp, regen kiểm data_dir; M1.8 `tools/project_error_report.py` (chỉ đọc); M1.9 golden B0–B2 | `core/runner.py`, `core/bg_poll.py`, `core/db.py` (claim), `core/llm_runner.py`, `core/change_review.py`, `core/autoqc.py`, `core/autopilot.py`, `core/subjects.py`, `core/delivered.py`, `core/archive.py`, `core/cost.py`, `core/spend_gate.py`, `tools/pregen_check.py`, `dashboard/common.py`, `tests/fixtures/golden_*` | job đang chạy giữ provider snapshot; dự án cũ cột trống = env cũ; 0 điểm chặn ngân sách mới (D01); Kho không xác minh được → báo, không gửi im lặng (D03) | 2 worker + crash/reconcile: 0 job trả tiền trùng; 2 dự án 2 provider; hết quota CLI → dừng có giờ mở, 0 lời gọi API; ước tính lệch sổ chi ≤ 10 % khi đủ dữ liệu; golden có SHA/cờ/schema/payload/hash | Duyệt ngay (M1.1 ✅, M1.4a đang gộp) | |
| G2-3 | **M2 Hợp đồng sản xuất** | M2.1 BYĐ v2 (`byd_v`, `vat[]` object, `shot_intent.read` có provenance); M2.2 field readers A2a–A2f + BYĐ vào lineage (cờ); M2.3 Kho forms code (thiết kế M0.9); M2.4 `insert_scene_after` kế thừa bối cảnh + BYĐ DRAFT; M2.5 write guard cấp trường ở SHADOW (đặc tả M0.10); M2.6 `sent_package` nhãn theo rel_path/asset_id; M2.7 image preflight chung mã lỗi với video; M2.8 router theo khả năng model; M2.9 lời dẫn ngoài khớp môi mọi caller | `core/shot_intent.py`, `core/llm_io.py`, `core/lineage*.py`, Kho (`core/assets*`, `core/profiles*`), `core/pipeline.py`, `core/write_guard.py` (mới), `core/runner.py` (`ImageRunner._pregen`), `core/seedance_refs.py`, `core/lipsync.py`, `core/speaker_lint.py` | #24/#27 cờ TẮT giống golden từng byte; v1 đọc qua adapter; guard chỉ ghi diag (shadow), không chặn | golden byte; #31/#33 correctness; khóa tay không bị ghi đè (đo ở shadow); regression lời dẫn (Codex Đ19 việc 1) hết xfail | Duyệt khi M0.9 + M0.10 (cloud) và M1.9 golden xong | |
| G2-4 | **M3 Thế giới & liên tục** | M3.1 `scene_world_map` thử nghiệm (3D / 2D / UNKNOWN, version, provenance, invalidation); M3.2 người nộm `height_m` trong whitebox, pitch eye/slightly_high; M3.3 câu vị trí sinh từ map; M3.4 `continuity_state` expected/observed/resolved; M3.5 bỏ kiểm chân trời khi nền không có trời | `core/world_map.py` (mới), `core/plates3d*`, `core/stage_auto.py`, `core/camera_plan.py`, `core/continuity*.py`, Blender scripts | map chưa duyệt KHÔNG chặn gen (D06); tắt định tuyến map = ref cũ | offline #31 cảnh 4/6/8 + #33 tháp; người dùng duyệt ảnh map | Duyệt sau M2 | |
| G2-5 | **M4 QC & Dashboard** | M4.1 schema bằng chứng QC + mã lỗi; M4.2 video QC (đứng yên > 1,5 s = REVIEW…); M4.3 cross-shot `qc_sequence_logic` shadow; M4.4 final QC blackdetect/freezedetect; M4.5 sửa báo nhầm A5/A6; M4.6 benchmark theo mã; M4.7 Dashboard BYĐ / thẻ gói gửi / sổ lỗi / overrides (code, bảng CSDL ở C3-4) | `core/qc_*.py`, `core/autoqc.py`, `core/final_cut.py`, `dashboard/steps/*`, `devsys` | QC chỉ shadow / REVIEW, không tự BLOCK (D07) | benchmark ≥ 20 lỗi + 20 đạt mỗi mã; ca báo nhầm A5/A6/G20 | Duyệt sau M2 (chạy song song M3) | |
| G2-6 | **M5 Sửa & pilot A** | M5.1 repair router theo mã lỗi, trần ảnh ≤ 3 / video ≤ 2 (cờ TẮT); M5.2 release gate; M5.3 pilot vòng A offline 0 USD (replay #31/#33) | `core/repair_router.py` (mới), `core/autopilot.py`, `core/final_cut.py`, `tools/pilot_*` | router TẮT = không tự sửa | vòng A: 5 nhóm ca thử theo mã lỗi (M0.11) | Duyệt sau M3/M4 | |

## B. Cấp 3 — xin riêng từng mục (trình sớm)

| Mã | Mục | Thuộc | Làm gì cụ thể | Rủi ro nếu duyệt | Rollback | Chi phí | Cần lúc nào | Đề xuất | Người dùng |
|---|---|---|---|---|---|---|---|---|---|
| C3-0 | **Đổi `dashboard.env` máy chính `LLM_PROVIDER=anthropic` → `claude_cli`** | R2 / M1.4 | sửa 1 dòng + khởi động lại Dashboard (người dùng hoặc Claude khi được cho phép rõ) | bước Claude chạy qua gói Claude Code (có giới hạn lượt, hết lượt → dừng có giờ mở) | đổi lại dòng cũ | 0 USD API | NGAY (đóng R2 trên máy chính; quyết định 19/10) | Duyệt | |
| C3-1 | Migration cột provider: `projects.llm_provider`, `jobs.llm_provider` + `llm_config_ver`, `llm_calls.provider` | M1.4b | thêm cột (ALTER TABLE ADD COLUMN), rỗng = theo env như cũ | thấp — chỉ thêm cột, không sửa dữ liệu | bỏ qua cột (code đọc rỗng = cũ); sao lưu CSDL trước | 0 | khi bắt đầu M1.4b (tuần này) | Duyệt | |
| C3-2 | Bật cờ M1.2 / M1.3 (claim nguyên tử, kiểm tạm dừng trước submit) trên máy chính | M1 | bật sau khi cả bộ test + thử 2 worker giả xanh | thấp–vừa: đổi đường gửi job thật | tắt cờ | 0 | sau gộp M1 | Duyệt (bật ngay sau nghiệm thu) | |
| C3-3 | Bật tự dọn Kho chủ thể ClipAI (M1.5, luật `v31-d03b` 3 ngày) | M1.5 | xóa asset khung bị loại / dự án đã giao-cất ≥ 3 ngày; giữ asset dự án khác còn tham chiếu | **xóa ngoài, không hoàn tác** | tắt cờ (asset đã xóa không lấy lại) | 0 (list/delete miễn phí) | sau gộp M1.5 + chạy thử chế độ chỉ liệt kê 1 lượt | Duyệt kèm điều kiện: lượt đầu chỉ liệt kê, người dùng xem danh sách rồi mới cho xóa | |
| C3-4 | Bảng CSDL `overrides` (D09) | M4.7 | tạo bảng mới (override ↔ mã lỗi / finding, người, revision, lý do, bằng chứng) | thấp — bảng mới | DROP bảng; sao lưu trước | 0 | khi làm M4.7 | Duyệt | |
| C3-5 | Migration / backfill Kho forms v2 (dạng, trang phục, tóc, mặt) | M2.3 | ghi `forms[]` + `schema_version` vào hồ sơ Kho từ dòng mô tả cũ; soạn nháp face/hair bằng `claude_cli` | vừa — đụng hồ sơ Kho thật; người dùng duyệt từng hồ sơ nháp | adapter vẫn đọc v1; giữ bản sao hồ sơ trước backfill | 0 USD API (claude_cli) | sau M0.9 + code M2.3 | Duyệt khi có số liệu Kho (máy chính đo 0 USD) | |
| C3-6 | Bật write guard ENFORCE (sau shadow) | M2.5 | AI / tự động không ghi đè trường USER_LOCKED; xung đột → REVIEW_REQUIRED | vừa — có thể chặn luồng tự động nếu đặc tả sót đường ghi | về shadow (cờ) | 0 | sau ≥ 1 dự án chạy shadow sạch (0 ghi đè sai) | Để sau (duyệt khi có số đo shadow) | |
| C3-7 | Bật cờ production M2 (BYĐ v2 vào lineage, image preflight, router) | M2 | bật từng cờ sau golden byte + correctness | vừa — đổi gói gửi ảnh/video | tắt từng cờ con | 0 | sau gộp M2 | Duyệt theo từng cờ khi trình | |
| C3-8 | Gen chứng minh world map (ảnh/video trả phí) + cho map chặn gen | M3 | vài shot #31 cảnh 4/6/8 gen thật để chứng minh map đúng | tiền + đổi luồng gen | tắt định tuyến map | ước tính qua `pregen_check` lúc trình (chưa có số) | sau anh duyệt ảnh map offline | Để sau | |
| C3-9 | Cho QC tự BLOCK luật kỹ thuật có bằng chứng; benchmark VLM | M4 | chỉ luật kỹ thuật đạt benchmark được chặn; ngữ nghĩa / góc / continuity vẫn REVIEW (D07) | vừa — chặn nhầm làm dừng autopilot | QC về shadow | benchmark qua `claude_cli` 0 USD API | sau M4.6 | Để sau | |
| C3-10 | Bật repair router tự gen lại trên production | M5.1 | tự sửa + gen lại theo mã lỗi, trần ảnh ≤ 3 / video ≤ 2, dừng khi lặp lỗi | tiền (gen lại) | tắt router | theo trần, ước tính khi trình | sau pilot B | Để sau | |
| C3-11 | **Pilot vòng B** 5–8 shot (đoạn #31 bóng mờ + tường keo) | M5.4 | gen thật, duyệt từng đợt; ngưỡng B: duyệt lần đầu ≥ 40 %, can thiệp tay ≤ 2/shot | tiền | dừng đợt | **≈ 15–37 USD** (giữa ≈ 30; trần lý thuyết 115) — dự toán M0.11, phải chạy `pregen_check` trước khi xin | sau M5.1–M5.3 | Duyệt khung tiền, xin lại số `pregen_check` trước khi chạy | |
| C3-12 | **Pilot vòng C** 20–40 shot (dự án mới thật) | M5.5 | autopilot theo cờ đã bật; ngưỡng C: duyệt lần đầu ≥ 50 %, gen lại video ≤ 1,0/shot, ảnh ≤ 1,5/shot | tiền | dừng đợt | **≈ 52–136 USD** (giữa ≈ 112; trần lý thuyết 576) | sau pilot B đạt | Để sau (quyết theo kết quả B) | |

Không phải Cấp 3 (Cấp 1, 0 USD, chỉ đọc — làm khi người dùng bảo): chụp fixture / dữ liệu vòng A ở máy chính (D08), đếm số liệu Kho cho M0.9.

## C. KẾT QUẢ DUYỆT 20/10 (văn bản "PHÊ DUYỆT GÓI CẤP 2 / CẤP 3 — V3.1") + tiêu chí mở khóa

Sổ: `v31-cap2-milestone-packages-approved-2026-10-20`, `v31-cap3-items-decided-2026-10-20`. Đây là phê duyệt triển khai có kiểm soát,
KHÔNG phải phê duyệt chi tiêu hay toàn quyền production. Cột "Người dùng" ở mục A/B lấy theo bảng này.

| Mã | Kết quả | Điều kiện / tiêu chí mở khóa (phải chứng minh bằng test hoặc báo cáo kiểm tra) | Trạng thái |
|---|---|---|---|
| G2-1 | DUYỆT | không VERIFIED nếu thiếu commit + test + bằng chứng vận hành | được làm |
| G2-2 | DUYỆT CÓ ĐK | checkpoint có test + rollback độc lập; đối chiếu HEAD M1.1/M1.4a trước khi làm tiếp; không tự làm Cấp 3 | được làm (ưu tiên 1) |
| G2-3 | DUYỆT CÓ ĐK | mở khi: M0.9 + M0.10 gộp main, M1.9 golden có fixture #24/#27; BYĐ v1, Kho cũ, dự án cũ vẫn chạy | chờ đầu vào |
| G2-4 | DUYỆT CÓ ĐK | world map chỉ offline; không chặn gen; không bắt buộc 3D | chờ M2 |
| G2-5 | DUYỆT CÓ ĐK | QC chỉ Shadow/REVIEW; không tự BLOCK/tự sửa production | chờ M2 |
| G2-6 | DUYỆT CÓ ĐK | router mặc định TẮT; pilot A offline 0 USD | chờ M3/M4 |
| C3-0 | DUYỆT CÓ ĐK | M1.4a gộp main + test chứng minh tiến trình CLI không nhận key (`test_the_claude_subprocess_never_receives_the_key`) → đổi `dashboard.env` → restart → kiểm worker/tiến trình (env tiến trình con không có key, `provider_status`, health 8501/8503) | chờ M1.4a gộp |
| C3-1 | DUYỆT CÓ ĐK | backup CSDL; test worker cũ/mới cùng chạy với cột mới; kế hoạch khôi phục CSDL viết sẵn | XONG 20/10 — 4 cột đã thêm, sao lưu trước |
| C3-2 | DUYỆT CÓ ĐK | test 2 worker, crash/reconcile, submit không rõ kết quả đều đạt | XONG 20/10 — 2 cờ bật máy chính |
| C3-3 | CHỈ DRY-RUN | chạy liệt kê: danh sách asset + dependency + lý do → trình duyệt riêng TỪNG lần xóa | chờ code M1.5 |
| C3-4 | DUYỆT CÓ ĐK | M4.7 sẵn sàng; backup; test schema | chờ M4.7 |
| C3-5 | KHẢO SÁT + NHÁP | đếm số liệu Kho (0 USD) + nháp; người dùng duyệt dữ liệu trước backfill; không ghi đè hồ sơ production | chờ M0.9 |
| C3-6 | ĐỂ SAU | số liệu shadow ≥ 1 dự án + kiểm đủ mọi đường ghi | — |
| C3-7 | ĐỂ SAU | golden + correctness regression xanh; trình từng cờ | — |
| C3-8 | ĐỂ SAU | map offline được duyệt + dự toán riêng | — |
| C3-9 | ĐỂ SAU | benchmark từng mã lỗi, nhất là tỉ lệ báo nhầm | — |
| C3-10 | ĐỂ SAU | pilot + cơ chế giới hạn chi phí tự động | — |
| C3-11 | NGUYÊN TẮC (chưa chi) | trình `pregen_check`, hard cap, phạm vi job, phương án dừng trước khi chạy | chờ M5.1–M5.3 |
| C3-12 | ĐỂ SAU | pilot B đạt nghiệm thu | — |
