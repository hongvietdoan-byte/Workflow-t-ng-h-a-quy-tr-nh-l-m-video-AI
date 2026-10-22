# Bàn giao cloud-claude → phiên chính (22/10/2026, sau khi phiên chính nhận lại điều phối 10:25)

Từ: phiên cloud `claude.ai/code session_0199VQqnF6CAfLBQHaMV8TDF` (nhánh `claude/wonderful-fermi-am712r`). Người dùng 22/10 yêu cầu bàn giao **toàn bộ thông tin** cho phiên chính.

Lịch điều phối 30 phút của cloud-claude đã xóa. Từ 10:25, cloud-claude không gộp `main` và không giao việc nữa.

Danh sách kiểm từng mục trên máy chính nằm ở `docs/handoff/KIEM_MAY_CHINH_TU_CLOUD.md`. Tài liệu này gom lại: quyết định người dùng, việc đã làm, nhánh chờ gộp, việc còn mở.

## 1. Quyết định người dùng trong phiên cloud 22/10 (phiên chính áp dụng tiếp)

| # | Câu người dùng | Đã làm thành |
|---|---|---|
| Q1 | Tổ QC hỗ trợ chấm điểm: "làm đi" | C-QC-BOCUC (mục 3). `qc_team` giữ 🎓 học việc. Bật lại khi máy chính đo khớp cân bằng ≥ 75 % (sổ `qc-team-off-2026-10-14`); bật chặn là bước duyệt riêng (D07) |
| Q2 | "Không chỉ sửa lỗi cố định — sửa GỐC để đặt chỗ khác / cách khác không lặp lại" | 23 lỗi 3D / vị trí / máy gom 5 gốc R1–R5. Mỗi gốc phải có một bất biến chạy cho mọi shot và test biến thể. Lỗi chỉ FIXED khi bất biến + test biến thể + replay ca gốc đều xanh. Đề bài: `docs/CLOUD_TASKS.md` mục C-3D-GOC-A / C-3D-GOC-B |
| Q3 | "Được làm đi, nhưng cần giữ mối liên kết chặt chẽ" | Nguồn bố cục duy nhất `core/layout_facts.facts_for_shot` (đã lên main 31340c68). QC, kiểm bố cục, câu tả nền và hai gói 3D cùng đọc; không viết hàm song song. Hợp đồng: `docs/CLOUD_TASKS.md` mục LIÊN KẾT |
| Q4 | Mỗi vai có hồ sơ riêng (ai, vai trò, việc, trách nhiệm, dưới quyền / giám sát, đầu vào, đầu ra + KPI, ai nhận + đòi hỏi + đáp ứng) và liên kết có hệ quả giữa toàn bộ các vai | Hồ sơ vai + danh mục sản phẩm + bộ kiểm hai chiều (mục 4). Sổ `crew-role-profiles-linked-2026-10-22` |
| Q5 | Đồng ý tách khâu Quay phim khỏi L3 | Thêm khâu **L3b** Quay phim (cỡ, góc, chuyển động, ống kính, blocking, trục 180°). `cinematographer` đứng tên L3b; 5 lỗi P31-G41/G43/G44/G45/G50 chuyển sang L3b (mục 4) |
| Q6 | Golden M1.9 trượt nhiều lần vì sao | Ghi ở mục ⭐ của KIEM_MAY_CHINH_TU_CLOUD.md. Bài học: chạy đối chứng âm TRƯỚC; giữ catalog cờ đứng yên lúc chạy |
| — | Luật tạm do cloud-claude đặt (người dùng chưa phản đối) | **Không gộp vào main code thêm cờ mới cho tới khi CX21-GOLDEN7 chạy xong** (catalog 159 / 32 cờ thử nghiệm TẮT). Phiên chính quyết giữ hay bỏ |

## 2. Đã gộp main trong phiên cloud 22/10

| Mã | Commit gộp |
|---|---|
| C-M81B, C-STAGE-VIEW, C-M61-M69, C-M71, báo cáo codex golden4/6 | c66d6c2d |
| C-M63-FIX | f74aeda6 |
| C-M71-FIX + C-M63-FIX2 | a68ea662 |
| C-FIX3-THAP (+B) | dc0deee0 |
| C-FIX4 | 6ea67537 |
| C-FIX5 | 0c354b05 |
| core/layout_facts v1 | 31340c68 |

Mỗi đợt gộp đều chạy cả bộ test Linux: 31 test hỏng, đúng bằng nền có sẵn (golden_db_replay ×13, golden_replay ×8, s1446 ×2…, danh sách trong scratchpad phiên cloud). **Máy chính vẫn phải pull, khởi động lại 8501/8502 và chạy test Windows.**

## 3. Nhánh chờ phiên chính rà / gộp

| Nhánh | Nội dung | Trạng thái | Ghi chú gộp |
|---|---|---|---|
| `cloud/v31-qc-bocuc` | C-QC-BOCUC: mệnh đề bố cục cùng chỗ + nền so render 3D (tối đa minor), quyết định học việc `flag`, màn 🧪 tự chấm 1 lần/phiên, `tools/trainee_score_report.py`, sửa lỗi rà (gaze không đọc bên SUY; layout_facts theo cờ stage_camera) | XONG hộp thư @ d40d5a19. Rà quy ước 7 (Agent): 1 CAO + 1 VỪA đã sửa. Cả bộ: 31 hỏng nền + 1 chập chờn (poll 2 tiến trình, qua khi chạy riêng) | Gộp TRƯỚC `cloud/v31-crew-hoso`. Báo cáo: `docs/RA_CLOUD_QC_BOCUC_2026-10-22.md` |
| `cloud/v31-crew-hoso` (dựng trên qc-bocuc) | Hồ sơ vai + danh mục 32 sản phẩm (`data/crew_profiles.json`), `core/crew.link_problems` / `profile_gaps` / `hoso_text`, CLI `py -m core.crew hoso`, trang `docs/HO_SO_VAI_2026-10-22.md`, khâu L3b, sổ quyết định + check | @ ccc67571 (merge main + 2 commit). Rà quy ước 7: 0 CAO, VỪA/THẤP đã sửa trừ: L3b tô đỏ khi bật director_camera_plan (đúng — chưa kiểm trước tiền); tools/project_error_report.py vẫn map camera_plan vào L3 | Sau khi gộp: `py -m core.crew check` = 0 lỗi; `py -m core.decisions check` |
| `cloud/v31-m83-tool` | Công cụ đo tải 10 người | **CHƯA gộp**: rà kỹ VỪA (relocate còn rò đường thật mà vẫn chạy) → C-FIX6 mục 7 (cloud-C) | Không chạy `load_test_ui.py --db` trên dữ liệu thật trước C-FIX6 |
| `cloud/v31-m48-desk-core` | Lõi bàn đạo diễn 3D | **CHƯA gộp**: rà kỹ 1 CAO (cổng S-C chỉ nối nút Gen ảnh, autopilot + video trả phí chưa qua) + 4 VỪA → C-FIX6 (cloud-C) | Gộp cùng M2 khi golden ĐẠT |
| `cloud/v31-m2-tichhop` + m24 + golden5 (+ m73, m210, golden4) | M2 tích hợp | Chờ CX21-GOLDEN7 (máy chính chạy, 6 bước ở mục ⭐ KIEM_MAY_CHINH) | Gộp một lần + cả bộ test + Agent rà |
| C-3D-GOC-A (cloud-C báo XONG 9ca59b88 lúc 10:2x) | Sửa gốc R2/R3/R4 | Chưa rà (phiên chính nhận) | Kiểm: đã ĐIỀN vào `layout_facts.facts_for_shot` (không hàm song song)? Có test biến thể? Đã đổi KPI `chua_co:` trong `data/crew_profiles.json` thành cách đo thật chưa (nếu nhánh hồ sơ đã gộp)? |

## 4. Hồ sơ vai: phiên chính cần biết

- **Nguồn dữ liệu:** `data/crew_profiles.json` chứa `profiles` (9 mục mỗi vai) và `products` (vai làm ra, KPI {id, tên, ngưỡng, cách đo}, người nhận → [{yêu cầu, đáp ứng bằng KPI id}]). Quyền đọc/ghi, bảng trường, owns_errors vẫn ở `data/crew_roles.json`. `outputs` của vai trong `crew_roles.json` phải trùng `dau_ra`.
- **Bộ kiểm** `py -m core.crew check` gồm `problems()` và `link_problems()`. Lỗi được báo khi:
  - đầu vào không có nguồn (THIẾU), hoặc sản phẩm không ai nhận (THỪA);
  - liên kết chỉ khai một phía;
  - yêu cầu của người nhận không có KPI đáp ứng;
  - KPI thiếu ngưỡng, hoặc cách đo trỏ tới thứ không có;
  - acceptance không phải KPI của sản phẩm do chính vai làm ra;
  - trường của sản phẩm thuộc vai khác;
  - chuỗi quản lý không về tới EP hoặc có vòng.
- **`py -m core.crew hoso`** in trang hồ sơ và mục "Còn thiếu". Có 9 KPI khai `chua_co:` (chưa đo tự động). Phần lớn chờ C-3D-GOC-A/B (R1/R2/R3/R4) và write guard M2.5. Riêng "bảng kê ↔ tên trong kịch bản" chưa có kiểm bằng code. **Khi các gói 3D xong, đổi `chua_co:` thành `code:` trỏ tới bất biến thật**; `tests/test_crew_profiles.py` giữ trang `docs/HO_SO_VAI_2026-10-22.md` khớp dữ liệu.
- **L3b:** `devsys/stages.json` có thêm khâu L3b (đợt K2, chưa có kiểm trước tiền riêng; lam d80, kiem_sau d81, cờ director_camera_plan). `tools/project_error_report.py` STAGES và `devsys/pipeline_maps.json` CHƯA thêm L3b vì chỉ là sơ đồ, không chặn. Thêm khi vẽ lại sơ đồ khâu.

## 5. Việc còn mở cho phiên chính / máy chính

1. **CX21-GOLDEN7** (ưu tiên 0, đường găng M2): 6 bước ở mục ⭐ KIEM_MAY_CHINH_TU_CLOUD.md. Đối chứng âm chạy trước; đỏ thì dừng.
2. **Gộp `cloud/v31-qc-bocuc` rồi `cloud/v31-crew-hoso`.** Trên máy chính chạy `PYTHONUTF8=1 py tools/trainee_score_report.py --feature qc_team` (0 USD, bản sao CSDL), gửi người dùng số khớp thật. Đọc số tách theo ngày: từ C-QC-BOCUC trở đi có thêm quyết định `flag`.
3. **C-FIX6** (cloud-C đã nhận): sửa DESK-CORE + M83-TOOL rồi rà lại trước khi gộp.
4. **C-3D-GOC-A XONG (cloud-C)**: rà theo mục 3; **C-3D-GOC-B**: tin 10:25 của phiên chính giao cho cloud-claude. Người dùng chưa chốt phiên cloud có làm tiếp không — phiên chính quyết (nếu giao lại thì ghi hộp thư).
5. **C-M48-DESK-UI**: cloud-D im từ 21/10 11:28 → luật 5b.
6. **Cả bộ test Windows** sau mỗi đợt gộp; 8501/8502 khởi động lại (areas.json đã đổi).
7. **Chưa chạy `load_test_ui.py --db` trên dữ liệu thật** (chờ C-FIX6).

## 6. Mẹo kỹ thuật phiên cloud để lại
- `hop_thu --push` tạo commit riêng lên main nên nhánh tích hợp local lệch. Cách xử lý: `git checkout -B <nhánh> origin/main` khi cây sạch.
- `pkill -f <mẫu>` trùng chính dòng lệnh bash, nên tự giết shell. Hãy dừng tiến trình theo PID.
- `tests/test_decisions.py`: check mới phải nằm TRƯỚC dòng `CHECKS = {…}`.

## 7. Bổ sung 22/10 ~11:45: C-3D-GOC-B XONG (cloud-claude, người dùng "có làm luôn đi")
- **Nhánh `cloud/v31-3d-goc-b` @ be02e84c.** Đã chứa sẵn `cloud/v31-3d-goc-a` + `cloud/v31-qc-bocuc` + `cloud/v31-crew-hoso` và đã merge main, không xung đột. **Gộp nhánh này là kéo theo cả 4 gói.** Rà gói A (cloud-C, chưa ai rà kỹ) trước khi gộp.
- **Nội dung:** gốc R1. Vị trí người/vật xuyên shot lấy từ MỘT bản đồ cảnh (`core/world_map`). Có 5 bất biến chạy cho mọi shot (`core/position_invariants`):
  - R1-MAP: thiếu bản đồ cảnh;
  - R1-SIDE: chữ trái/phải ngược bản đồ;
  - R1-AXIS-JUMP: nhảy trục;
  - R1-TRAVEL: đi về phía / rời khỏi X sai chỗ X;
  - R1-PROP-SCENE: khối giữ chỗ mang từ cảnh khác.

  `layout_facts.positions` đọc bản đồ (số shot của bản đồ = `scenes.idx`). Công cụ `tools/position_invariants.py` chỉ đọc. Các KPI trong hồ sơ vai trỏ tới hàm đo của gói A và B; còn 6 KPI chưa đo được. Thiết kế R5 (Kho vật nhiều dạng) chờ CX21-M23.
- **Bằng chứng:**
  - test biến thể 24 seed, 131 ca;
  - rà quy ước 7: 2 CAO + 4 VỪA, đã sửa hết;
  - cả bộ Linux: 31 hỏng nền + 1 test chập chờn (poll 2 tiến trình, chạy riêng thì qua).
- **Máy chính:**
  1. Dựng bản đồ #31 bằng `core.world_map.refresh` (cờ world_map, 0 USD).
  2. Chạy `PYTHONUTF8=1 py tools/position_invariants.py --project 31` để có bằng chứng thật. Có bằng chứng rồi mới đổi trạng thái sổ lỗi G41–G50.
  3. Sửa `dashboard/stage_view_ui.py:175`: đang dùng `shot_no` thay vì `idx` (lỗi có sẵn, cùng loại lỗi đã sửa trong gói).
- **Báo cáo:** `docs/RA_CLOUD_3D_GOC_B_2026-10-22.md` (trên nhánh).
