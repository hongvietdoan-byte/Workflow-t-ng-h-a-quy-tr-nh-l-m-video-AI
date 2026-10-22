# C-QC-BOCUC: Tổ QC có lỗi bố cục / chỗ đứng, sửa vòng chấm học việc (cloud-claude, 22/10)

Người dùng 22/10 nói "làm đi" và "giữ mối liên kết chặt chẽ". Phạm vi:
- 0 USD, không thêm cờ;
- `qc_team` giữ 🎓 học việc;
- mức nặng nhất là đánh dấu (`minor`), theo quyết định D07.

Điều kiện bật lại cờ nằm ở quyết định `qc-team-off-2026-10-14`:
1. checklist có lỗi bố cục / chỗ đứng → **làm trong gói này**;
2. đo khớp ≥ 75 % → **máy chính đo** (mục 4).

## 1. Liên kết: một nguồn sự thật bố cục
`core/layout_facts.facts_for_shot` (v1 lên main ở `31340c68`, hợp đồng trong `docs/CLOUD_TASKS.md`, mục LIÊN KẾT). Tổ QC, kiểm bố cục, câu tả nền (R3) và
hai gói 3D (C-3D-GOC-A/B) đều đọc chung nguồn này, không gói nào tự tính.
- Bên trái/phải của người theo chữ blocking: `layout_facts.blocking_side_match`. Đây cũng chính là câu mệnh đề layout cũ của Tổ QC dùng, nay chỉ còn một chỗ.
- Mốc trong khung lấy từ `stage_facts`; chân trời lấy từ `stage_facts` + `plate_layout.json`; nhóm và chỗ đứng lấy từ `scene_storyboard`.
- Chưa có dữ liệu thì ghi lý do vào `missing`: R2 (số đo người), R3 (mốc khi không có máy 3D), R1 (`world_map`).

## 2. Mệnh đề bố cục mới (`core/qc_spec._layout_assertions`)

| Mệnh đề | Khi nào lập | Ai phán | Mức |
|---|---|---|---|
| Người ở nửa trái/phải/giữa **như shot cùng chỗ rộng nhất** | Shot không tự khai bên; shot tham chiếu cùng chỗ có khai; hai máy **cùng phía trục** (`layout_facts.same_view`: máy 3D lệch ≤ 60°, hoặc cùng `camera_setup`) | code (`qc_measure._layout_side`: một người + một mặt) | minor |
| Nền khớp render 3D | `plate_layout.json` có bản ghi **của đúng khung này** (job) | code (`plate_layout_qc`), không hỏi model | minor |

Những ca không lập mệnh đề, và lý do được ghi vào `layout_missing` chứ không đoán:
- Ngược trục 180°, hoặc không biết hai máy có cùng phía trục không → bên trái/phải không được chép sang. Đây là luật chung cho mọi chỗ đặt máy, không vá riêng ca #31.
- Shot tham chiếu không khai bên.
- Nền chưa được đo cho khung.

Theo N5 (người dùng 10/10), model không được hỏi vị trí vật trong khung. Các mệnh đề mới không bao giờ có trong lời gọi C1, nên bản ghi `calls.jsonl` cũ vẫn chạy lại (replay) được.

Các mệnh đề layout cũ (bên trái/phải khai trong blocking) trước đây không có số đo code nên chưa từng tính vào kết quả. Nay chúng được đo theo cùng cách: chỉ đo khi chắc, gần ranh giới thì để "uncertain".

## 3. Học việc
- `qc_team.decision_of`: khung có lỗi bố cục hoặc nền thì ghi **`flag`** (giữ cho người xem); khi so với người, `flag` tính là "reject" (`trainee.RULES`). Các lỗi nhỏ khác vẫn ghi `pass` như trước.
- **Vì sao 366 dòng học việc có 0 dòng được chấm** (`docs/DANH_GIA_HIEU_QUA_CO_2026-10-21.md` 1.2.4): `trainee.score_project` chỉ chạy lúc Xuất bản (Bước 5)
  và khi bấm "↻ Chấm lại". Code chấm đúng: test `tests/test_trainee_score_report.py` cho thấy dữ liệu đủ thì chấm được. Đây là giả thuyết mạnh nhất; máy chính xác nhận bằng công cụ dưới.
- **Sửa gốc:** màn 🧪 tự chấm một lần mỗi phiên khi mở (0 USD, chỉ SQL). Nút Chấm lại vẫn giữ.
- **Công cụ** `tools/trainee_score_report.py`: chấm trên BẢN SAO CSDL. In ra: đã chấm trước, chấm được ngay, người duyệt trước vai, lý do còn chờ, khớp gộp / cân bằng, điều kiện còn thiếu. CSDL thật không đổi.

## 4. Lệnh cho máy chính (0 USD)
```
git pull
PYTHONUTF8=1 py tools/trainee_score_report.py --feature qc_team          # khớp thật hiện tại + vì sao chưa chấm
PYTHONUTF8=1 py tools/experiments/qc_team_eval.py --set independent --replay <calls.jsonl GĐ3>   # replay bản ghi cũ (C1 không đổi)
```
Kết quả đo mang báo người dùng. Khớp cân bằng ≥ 75 % thì xin duyệt bật `qc_team` ở mức chấm + đánh dấu; bật chặn là bước duyệt riêng (D07).
Cloud không có CSDL hay bộ ảnh nên **chưa có số đo thật**. "Đã sửa" ở đây mới có bằng chứng là test.

## 5. Test
- `tests/test_layout_facts.py` (14): hợp đồng.
- `tests/test_qc_bocuc.py` (16): cùng chỗ cùng trục; ngược trục / không biết → có lý do; không lập trùng; nền chỉ đo bằng code và không chặn; không có bản ghi → nói ra; thiếu kết nối → không đổi gì; đo bên mặt (9 ca); quyết định `flag`.
- `tests/test_trainee_score_report.py` (2): chấm trên bản sao, CSDL thật không đổi.

## 6. Rà quy ước 7 (Agent, 22/10) và cách đã xử lý
- **CAO, đã sửa.** Bên khung SUY từ shot cùng chỗ từng lọt vào dict `layout` mà nhánh gaze dùng để chọn mặt. Khung 2 người có thoại vì thế có thể bị gaze đánh `block`. Nay gaze chỉ đọc bên người được khai trong blocking (`qc_measure.measure_frame`). Test `test_inferred_side_never_drives_gaze_to_a_block`.
- **VỪA, đã sửa.** `layout_facts` từng đọc `stage_camera` dù cờ `stage_camera` TẮT. Nay chỉ đọc khi cờ bật, cùng điều kiện với ảnh và QC (`layout_facts._stage`). Test `test_stage_camera_flag_off_ignores_old_coordinates`.
- **VỪA, giữ theo ý đồ, đã thêm test.** Mệnh đề bên khai trong blocking cũ nay cũng được đo bằng code. Hệ quả: tỉ lệ khớp qc_team trộn dòng cũ (block/pass) với dòng mới (có `flag`), vì vậy khi đọc số trên máy chính phải **tách theo ngày**. Test `test_old_blocking_side_is_now_measured_by_code`.
- **THẤP, ghi lại, chưa làm.**
  - Mỗi khung gọi `facts_for_shot` 1 + (số người chưa khai bên) lần, chi phí O(khung × shot cùng cảnh). Có thể cache theo cảnh nếu chậm.
  - `qc_observe` gọi `compile_frame` không có `data_dir` nên không có mệnh đề mới. Hiện vẫn nhất quán, nhưng là nơi phải nối khi cần.
  - Màn 🧪 tự chấm một lần mỗi phiên; duyệt mới sau lần đó thì bấm Chấm lại.

## 7. Cả bộ test Linux (sau khi sửa lỗi rà)
- Kết quả: 32 hỏng / 7167 qua.
- 31 hỏng trùng đúng danh sách nền của main (golden_db_replay, golden_replay, s1446…).
- 1 hỏng thêm: `tests/test_v31_t12_m12_m13_gaps.py::test_two_real_processes_poll_one_job_once` (slow; hai tiến trình poll thật, nhạy thời gian khi máy bận). Không dính tới tệp của gói này. Chạy riêng 2 lần đều QUA.
