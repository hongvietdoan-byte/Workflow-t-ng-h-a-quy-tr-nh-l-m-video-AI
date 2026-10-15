# Kế hoạch nối Sân khấu 3D v2 vào chạy tự động — mọi dự án (15/10/2026)

**Trạng thái: CHỜ NGƯỜI DÙNG DUYỆT. Chưa viết code, chưa bật cờ, chưa gọi API.** Bản này chỉ đọc code (main `15f47c26`), đọc
CSDL ở chế độ chỉ đọc và chạy hàm ước tính (`core/cost.llm_estimate`), không gọi Claude.

Nguồn: [phương pháp sân khấu 3D](PHUONG_PHAP_SAN_KHAU_3D.md) (K1–K5, mục 11 quy trình chuẩn, mục 14 stage_facts),
[kế hoạch sân khấu đoạn 12/10](KE_HOACH_SAN_KHAU_DOAN_2026-10-12.md) (bản Đ18 chưa duyệt — bản này **thay phần "điểm nối" của nó**
và giữ hợp đồng dữ liệu stage/segment/state), [chuẩn xây dựng](CHUAN_XAY_DUNG.md), nhánh `claude/p31-plate-rules`
(`33be690f` + biên bản rà `26b3ee4a`).

## 0. Vấn đề và mục tiêu

**Gốc lỗi #31 (người dùng 15/10):** các shot cùng bối cảnh không thống nhất: máy lọt ngoài tường phòng, mê cung máy chỉ nhìn
biệt thự, đêm quá tối. Sân khấu 3D v2 (lưới → Đạo diễn khai khối tọa độ người + vật → bộ giải máy + đo Blender → trường
`stage_camera`) chỉ chạy tay ở #24.

Số đo thật trong CSDL (chỉ đọc, 15/10):

| Dự án | Shot | Shot có `stage_camera` | Cảnh truyện | (bối cảnh, chỗ đứng) |
|---|---|---|---|---|
| #24 | 12 | **12** (chạy tay + `apply_v4.py`) | 1 | 1 |
| #27 | 22 | 0 | 9 | 6 |
| #28 | 5 | 0 | 1 | 2 |
| #30 | 7 | 0 | 1 | 2 |
| #31 | 28 | 0 | 8 | 7 |

Cờ trên máy chính (`D:\AI-Video-Pipeline\data\feature_settings.json`): `stage_camera`, `director_camera_plan`,
`layout_from_follow`, `anchor_by_spot`, `place_render_refs`, `director_blockout`, `continuity_layout`, `travel_truth` **đều BẬT**.
Vì không shot nào có trường `stage_camera`, cờ `stage_camera` bật mà **không có tác dụng** ở #27–#31. Đây là lỗi kiểu
`feedback_fix_mechanism_not_memory`: cờ bật nhưng đầu vào của nó không được tạo.

**Mục tiêu (lời người dùng):**
1. Mỗi phòng/bối cảnh có **MỘT sân khấu 3D gốc**. Đổi shot thì chỉ đổi máy; người và vật giữ nguyên chỗ, trừ khi kịch bản cho
   di chuyển.
2. Nền dựng **khối vật + người nộm tại đúng tọa độ** để ảnh giữ vị trí.
3. Chạy tự động cho mọi dự án, không còn tham số cứng của #24.

## 1. Bối cảnh #31: một mô hình 3D là một hệ tọa độ

Vị trí chỗ đứng trong Kho đều là tọa độ model, nên mọi chỗ đứng trong cùng một file 3D đã chung một khung tọa độ, **không cần
đo phép biến đổi giữa các chỗ đứng**. Đây là điểm kế hoạch 12/10 còn để mở ("world transform cho các spot"). Các chỗ đứng #31:

| Kho | File 3D | Chỗ đứng (shot) | Ghi chú |
|---|---|---|---|
| 447 PHÒNG HAI CỬA ĐÓNG | `phong_2_cua_A_dong.glb` | `goc_nhin_kelly_2_cua` (1, 2) · `kelly_giua_phong` (3, 4) | |
| 448 PHÒNG HAI CỬA MỞ CỬA 1 | `phong_2_cua_B_cua1_mo.glb` | `goc_nhin_kelly_2_cua` (16) · `can_cua_2` (17, 18) | Cùng phòng với 447 (bộ chỗ đứng y hệt, chỉ khác cửa) → **cùng một sân khấu, cửa là trạng thái** |
| 265 Cổng Trời | `T_30_XH_PCMAP_P20/asset.fbx` | `me_cung` (5, 6, 13–15) · `trung_tam_me_cung` (7–12) | Hai chỗ đứng cách nhau ≈ 23,5 m |
| 263 Tháp Đồng Hồ | `T_30_XH_PCMAP_P16/asset.fbx` | `duong_bac` (19–22) · `plaza_front` (23–28) | Cách nhau ≈ 84 m. K1 của `plaza_front` đã có từ #24 |

Định nghĩa dùng trong kế hoạch (giữ đúng tên của bản 12/10):
- **stage** = một mô hình 3D, hoặc một **họ** mô hình khai trong Kho (447 + 448). Tọa độ thế giới chính là tọa độ model. Mỗi chỗ
  đứng có một lưới K1 riêng (gốc O tại chỗ đứng, cache theo sha model + chỗ đứng như mục K1 đã có).
- **segment** = một cảnh truyện (`story_scene`) trên stage đó.
- **state** = vị trí và tư thế người/vật theo nhịp (`blocking.beats`). State cuối của cảnh trước trên cùng stage là state đầu của
  cảnh sau, trừ khi kịch bản đổi.

## 2. Chỗ cần sửa (file:dòng tại `15f47c26`)

### 2a. Tham số cứng #24 cần bỏ
| Chỗ | Đang cứng | Đổi thành |
|---|---|---|
| `tools/stage_grid.py:1748-1752` | `KELLY_H`, `YEUNU_H` (= 1,7 **mặc định im lặng**), `WELL_H`, `WELL_D`, `WELL_SRC` | Chiều cao lấy từ hồ sơ Kho `profile.height_m` (`core/assets.py:1383`). Thiếu thì **dừng và hỏi** (đúng luật 1 và mục 3.1 của phương pháp). Kích thước vật lấy từ Kho hoặc từ kịch bản, thiếu thì hỏi |
| `tools/stage_grid.py:1755` `build_cfg` + `host_main` `:1705-1745` (mặc định `--place 263 --spot plaza_front --facing 350 --well-dist 1.6`) | K1 dựng luôn Kelly + giếng + yêu nữ của #24 | Hàm K1 **thuần sân khấu** (không có người, không có vật): đo sàn, ô cấm, mốc. Người và vật thuộc về state, không thuộc về K1 |
| `tools/stage_grid.py:1092` `requests_24`, `:1134` `s1_main` (mặc định project 24) | 3 yêu cầu máy mẫu của #24 | Giữ nguyên làm thí nghiệm, không gọi từ luồng tự động |
| `tools/stage_grid.py:1267-1305` `blender_props` | Chỉ dựng được giếng + người nộm. Vật khác gặp `SystemExit` (`:1278`). Nhiều hơn 1 giếng cũng `SystemExit` (`:1280`) | Mọi vật thành khối `block` box/cylinder theo kích thước (`tools/render_plates.py:579` đã hỗ trợ). Giếng chỉ là một dạng. Lỗi trả về dạng giá trị, không gọi `SystemExit` |
| `tools/stage_grid.py:570` `LABEL_POINTS`, `:466/:478/:645-671` | Tên `STAGE_KELLY` / `STAGE_YEUNU` / `STAGE_WELL` | Chỉ nằm trong `s1_block` (thí nghiệm). `v2_block` `:815` đã chung theo khóa vật, trừ phần đo giếng `:841`; phần này đổi thành chung theo "vật rỗng" |
| `tools/stage_grid.py:1532` `v3_main` | Đầu vào viết tay `tools/experiments/stage_v2_p24/v3_inputs.json` (pid, cảnh, place, spot, vật cố định có tọa độ, người, lời người dùng, ref). Dùng argparse và `print` | Hàm lõi `core/stage_auto.py` (mới) nhận `conn, pid, segment` và trả kết quả + chẩn đoán. CLI v3 gọi lại hàm này |
| `tools/experiments/stage_v2_p24/apply_v4.py:90` `stage_cameras`, `:117` `main` (cứng `project_id=24`) | Ghi `stage_camera` vào scenes bằng SQL tay | Đưa vào `core/stage_auto.apply`: ghi qua đường cập nhật scene có sẵn, tôn trọng `_user_locked`, sao lưu trước, có lịch sử |

### 2b. Điểm nối vào luồng tự động
| Chỗ | Hiện tại | Nối |
|---|---|---|
| `core/autopilot.py:1289` danh sách phase | `director → storycheck → voicefirst → previz → plates → images …` | Thêm `("stage", _stage_phase)` **sau `previz`, trước `plates`**: sau khi Đạo diễn đã viết shot và Bible đã khóa, trước Đặt máy 3D và trước mọi ảnh |
| `core/autopilot.py:643-677` `_plates_phase` | G0 `_camera_plan` trước/sau (`:652`, `:675`) cho mọi shot | Shot đã có `stage_camera` đã duyệt thì **bỏ qua G0** (tránh hai nguồn máy, tránh trả tiền hai lần). Shot không có thì vẫn chạy G0 như cũ |
| `core/location_pack.py:368-396` `plan` | Đã đọc `stage_field` khi cờ `stage_camera` bật | Không đổi luồng. Khóa cache nền gồm cả máy, nên máy mới tự sinh nền mới. Thêm máy ảnh toàn từ sân khấu (mục 5) |
| `core/plate_camera.py:443` `from_stage` | Trả máy đã khóa + `props` (chỉ giếng) | Nhận thêm `wide` (máy ảnh toàn cùng trục do bộ giải tính, nằm trong phòng) và `props` dạng khối chung |
| `tools/render_plates.py:572` `add_props` | Có `well` và `block` | Thêm lượt render **người nộm** cho ảnh hướng dẫn bố cục (mục 6), không render vào nền sạch |
| `core/runner.py:2668` `layout_reference` | Gửi ảnh shot `continuity_from` làm `layout_from` | Thêm nguồn thứ hai: ảnh hướng dẫn sân khấu (vai `layout_stage`), một hàm chọn (luật 4 chuẩn xây dựng) |
| `core/runner.py:2984-3003` `stage_facts` | Đã chạy khi cờ bật và shot có `stage_camera` | Tự có tác dụng sau khi shot có `stage_camera`. Thêm sự thật "vị trí người/vật theo state" |
| `core/stage_director.py:26` `build_prompt`, `:60` `validate_answer` | Một cảnh, `inputs` viết tay | Giữ prompt 29 nhưng tạo `inputs` bằng code (mục 3). Thêm đầu vào "state đầu (từ cảnh trước cùng sân khấu)" và luật "không dời người/vật đã có nếu kịch bản không cho" |
| `core/cost.py:311` `director_stage_specs` (9000, 12000) | Có bảng token | Đưa vào ước tính trước khi chạy dự án, cạnh `director_camera_plan` (`:312`) |
| `core/features.py:512` `stage_camera` | Chỉ là cờ tiêu thụ | Thêm cờ mới `stage_auto` (mặc định **TẮT**, `verified: False`, `costs: True`). Ghi vào sổ quyết định `data/decisions.json` + `tests/test_decisions.py` |

## 3. Đầu vào lấy từ Kho và kịch bản (thay `v3_inputs.json` viết tay)

Hàm `stage_auto.inputs_for(conn, pid, segment)` chỉ đọc và tốn 0 USD:

| Trường prompt 29 | Nguồn | Thiếu thì |
|---|---|---|
| `place`, `spot`, `aspect` | `location_pack.shots_at_3d_places` + `spot_for` + `formats.project_aspect` | Shot không có bối cảnh 3D thì không vào sân khấu, ghi lý do |
| `people[].H` | `profile.height_m` của nhân vật trong Kho | **Dừng ở cổng `stage`, hỏi người dùng** (không mặc định 1,7 như `YEUNU_H`) |
| `fixed` (vật cố định + mốc) | Vật trong Kho có `size` + mốc của chỗ đứng (`stage.json marks`) | Vật thiếu kích thước thì hỏi. Mốc thiếu thì không đưa vào và ghi rõ |
| `shots` | `_scene_shots` (`tools/stage_grid.py:1482`): action, blocking chữ, cỡ, góc, `plate_view`, `camera_move` | — |
| `floor` | `_floor_notes` (`:1498`) từ grid K1 | Chưa có K1 thì chạy K1 trước (0 USD, Blender ≈ 20 s mỗi chỗ đứng) |
| `prev_state` (mới) | State cuối của segment trước trên cùng stage | Cảnh đầu tiên thì không có |
| `user_notes`, `refs` | Ghi chú người dùng của cảnh + video/ảnh ref của shot | — |

## 4. Một sân khấu cho mỗi bối cảnh, và chuỗi shot

- **Lưu theo dự án** (`<data_dir>/<pid>/stage/<stage_id>/`): `stage.json` + `grid_<spot>.json` (K1, cache theo sha model +
  chỗ đứng), `segments/<story_scene>/` (blocking, shot_specs, setups, v2, tấm ghép, duyệt). Đường dẫn luôn tính từ
  `data_dir` truyền vào, không tính từ thư mục đang chạy.
- **Họ mô hình:** thêm trường Kho `stage_family` (vd `phong_2_cua` cho 447 + 448). Code thấy hai bối cảnh có bộ chỗ đứng trùng
  hệt mà chưa khai họ thì báo VÀNG và gợi ý; **không tự gộp**.
- **Thứ tự segment:** theo thứ tự cảnh truyện. Các segment trên cùng stage chạy nối tiếp (state truyền tiếp). Các stage khác
  nhau chạy **song song** (theo memory "Đạo diễn #31 21 phút, kỳ vọng dưới 5 phút").
- **Bất biến** (kiểm bằng code, không chỉ dặn trong prompt):
  - Đổi shot trong một segment chỉ đổi máy.
  - Người hoặc vật đổi vị trí giữa hai nhịp phải có chuyển động khai trong `blocking.beats` và lý do từ kịch bản. Không có thì
    trả lời bị coi là sai mẫu và hỏi lại (`validate_answer` đã kiểm "vật cố định không bị dời", mở rộng sang người).
- **Tương thích nhánh `p31-plate-rules`:** `_stage_hold` (`core/autopilot.py`, nhánh) giữ chạy khi một cảnh có nhiều chỗ đứng.
  Sau khi có sân khấu: cảnh có segment đã duyệt, và mọi chỗ đứng thuộc cùng một stage, thì **không cần giữ** nữa (đã chung tọa độ).
  Cảnh trải trên nhiều stage khác nhau vẫn giữ như nhánh làm.

## 5. Máy nằm trong phòng, và ảnh toàn cùng trục

- **Luật mới trong bộ giải (thuần, 0 USD):** ô đặt máy phải **đi tới được từ O mà không vượt ô tường** (loang trên grid K1;
  ô cao hơn 0,3 m = vật chắn). Luật này chặn trường hợp "máy lọt ngoài tường phòng" ngay ở K3. Hiện K3 chỉ kiểm "không đứng
  trong ô vật chắn" (`core/stage_solver.py:507` `_p1_grid`), nên máy vẫn có thể đứng ngoài phòng.
- **Ảnh toàn cùng trục** (memory `feedback_wide_same_axis_every_shot`): bộ giải tính thêm một máy WS cùng phương vị với máy
  shot, cũng qua luật loang trên. Kết quả lưu ở `stage_camera.wide`.
  - Việc này xử lý tận gốc mục **CAO-1** của biên bản rà nhánh: `plate_camera.wide_for` chép `locked` sang máy toàn, máy toàn
    không được dời nên lọt ngoài phòng.
  - Có `stage_camera.wide` thì `wide_for` dùng máy đó thay vì chép.
- **Mục VỪA-8 của nhánh** (máy khóa bị coi là "ngoài phòng" → shot hỏng): với máy sân khấu, nếu Blender vẫn đo ra "ngoài phòng"
  thì đó là **lỗi sân khấu**. Giữ shot ở cổng `stage`, kèm số đo; không tự dời máy, không im lặng.
- **Mê cung "chỉ nhìn biệt thự":** yêu cầu khung ghi `nen` và `khong_duoc_co` (prompt 29). K4 đo % từng nhóm (nhà, tường, trời,
  sàn) theo tia. Nếu nền là "nhà" chiếm quá ngưỡng trong khi shot đòi lối mê cung, shot không đạt và đi vào vòng sửa B5.
- **Đêm quá tối:** thuộc nhánh `p31-plate-rules` (`plate_env.lift_dark`). Kế hoạch này không đụng tới.

## 6. Người nộm và khối vật trong render

| Lớp | Ở đâu | Gửi model ảnh |
|---|---|---|
| **Khối vật** (giếng, xe nôi, tường keo… thứ không có trong model 3D) | Dựng trong **nền sạch** đúng tọa độ và kích thước (cách #24 đã làm: model vẽ đạo cụ thật lên đúng khuôn) | Có, là nền |
| **Người nộm** (cao H, tư thế theo state, màu theo nhân vật) | Lượt render thứ hai, **cùng máy**: nền + người nộm màu đặc → `stage_guide.png` | Đề xuất: gửi làm ảnh **hướng dẫn bố cục** (vai `layout_stage`), kèm câu do code viết ("Kelly đứng 1/3 trái, cách máy 2,4 m"). Không vẽ người nộm vào nền sạch, để model không chép người nộm xám (**quyết định Q2**) |
| **Tấm ghép duyệt K5** | Hình phác + vùng đích + khung cuối + số đo | Không gửi model. Người dùng (hoặc Claude thao tác Dashboard) xem |

Vật xuất hiện giữa chừng (vd tường keo shot 15 #27) là một sự kiện trong state: trước nhịp đó không có, sau nhịp đó giữ nguyên chỗ.

## 7. Cổng giữ shot khi bộ giải không đặt được máy

Quy trình mỗi segment (mục 11 phương pháp: B0 → B6):
1. K1 thiếu thì chạy (0 USD).
2. Ước tính, ghi sổ chi, rồi gọi Đạo diễn (1 lượt). Sai mẫu thì hỏi lại 1 lần.
3. K3 giải máy và K4 đo Blender.
4. Shot hỏng thì sửa tự động **tối đa 2 lượt Claude** (`MAX_ROUNDS = 2`, luật 6). Lượt sau phải mang số đo mới, tức là đầu vào
   đã đổi.
5. Vẫn hỏng thì **giữ shot đó** ở cổng `_Wait("stage", …)` (cùng cơ chế `_plate_ack` có dấu vân tay), liệt kê:
   - shot nào, hỏng luật gì, số đo bao nhiêu;
   - 2–3 lựa chọn cụ thể (`stage_solver.advise`): dời chỗ đứng, đổi cỡ, chấp nhận che, hoặc dùng máy cũ `camera_for` kèm nhãn
     VÀNG "không theo sân khấu".

   Các shot đạt vẫn đi tiếp. **Không bao giờ âm thầm quay về máy cũ.**
6. Thiếu đầu vào (chiều cao, kích thước vật, chỗ đứng không có trong model, Blender không có) thì dừng segment đó và nói rõ thiếu
   gì. Các stage khác vẫn chạy.
7. Lỗi Claude (hết tiền, `out_of_credit`) thì dừng như các khâu Claude khác (`_stop_if_claude_blocked`).

## 8. Test cần có (đỏ → xanh, không gọi API, Blender giả trừ test đánh dấu chạy thật)
1. `inputs_for` trên fixture #31 (447/448/265/263): đủ trường, đúng chỗ đứng. Nhân vật thiếu `height_m` thì dừng (không phải 1,7).
2. Họ mô hình: 447 + 448 khai `stage_family` thì ra một stage. Chưa khai mà chỗ đứng trùng thì báo VÀNG, không gộp.
3. Truyền state: S1 → S5 phòng, người giữ chỗ. Kịch bản cho đi thì phải có beat chuyển động. Trả lời dời người không lý do thì
   bị bắt sai mẫu.
4. Luật loang: fixture phòng nhỏ 4 tường. Lời giải ngoài tường bị loại. Ảnh toàn cùng trục nằm trong phòng (ca CAO-1).
5. `blender_props` chung: vật box/cylinder không gặp `SystemExit`. Có 2 vật rỗng thì báo lỗi dạng giá trị.
6. Autopilot: cờ `stage_auto` TẮT thì không thêm lời gọi, prompt, cổng hay khóa cache nào (so dấu vân tay prompt và nền trước/sau).
   Cờ BẬT thì phase `stage` chạy trước `plates`, shot có `stage_camera` bỏ qua G0.
7. Cổng: segment có 1 shot hỏng sau 2 lượt thì `_Wait("stage")` liệt kê lựa chọn. Shot khác vẫn có `stage_camera`. Bấm Tiếp tục
   với "dùng máy cũ" thì nhãn VÀNG được ghi.
8. Ước tính: trước lời gọi Claude có dòng sổ chi + ước tính. Chạy lại không tính tiền hai lần cho segment đã có trả lời (dùng lại
   như `resume=True`).
9. Ma trận luồng (luật 2 chuẩn xây dựng): bấm tay (CLI v3 gọi lõi) · autopilot · nhân bản dự án (remap stage, bỏ duyệt) · chạy lại
   Đạo diễn (state cũ thành ⚠ cũ, không tự xóa máy đã duyệt) · `continuity_from` (ảnh nguồn và sân khấu không mâu thuẫn chỗ đứng).
10. Hồi quy #24: dùng `blocking.json` + `shot_specs.json` của #24 qua đường lõi mới, ra cùng camera với `v2.json` đã duyệt (sai
    lệch ≤ 1 cm / 0,5°).

## 9. Thứ tự làm (sau khi nhánh `p31-plate-rules` sửa xong 3 CAO + gộp main)

| Bước | Việc | Tiền | Ghi chú |
|---|---|---|---|
| S0 | Gộp `p31-plate-rules` (phiên khác). Nhánh mới cắt từ main sau gộp | 0 | Cùng file `location_pack.py` / `plate_camera.py` / `autopilot.py`, nên **không làm song song** |
| S1 | K1 thuần sân khấu + `blender_props` chung + bỏ hằng số #24 + test 5, 10 | 0 | Blender cục bộ |
| S2 | `core/stage_auto.py`: `inputs_for`, stage/segment/state, luật loang + ảnh toàn, `apply` (ghi scene có sao lưu) + test 1–4 | 0 | |
| S3 | Phase `stage` trong autopilot + cổng + bỏ G0 cho shot có sân khấu + cờ `stage_auto` + sổ quyết định + test 6–9 | 0 | Rà quy ước 7 (agent) trước commit |
| S4 | Người nộm → `stage_guide.png` + vai `layout_stage` + stage_facts vị trí | 0 | Theo Q2 |
| S5 | **Thử khô #31 (0 USD):** K1 cho 7 chỗ đứng + dựng `inputs_for` 8 cảnh, in prompt, **không gọi** | 0 | Người dùng xem đầu vào |
| S6 | **Thử thật 1 cảnh** (phòng S1, 4 shot) → tấm ghép → người dùng xem | ≈ 0,23–0,91 USD | Thang kiểm thật (luật 5) |
| S7 | 7 cảnh còn lại → render nền lại → gen lại ảnh #31 | Xem mục 10 + báo giá ảnh riêng | Ảnh/video báo giá trước khi gen |

Ước lượng công: S1–S4 cỡ 2–3 phiên con (mỗi phiên một nhóm file, không chồng file).

## 10. Báo giá Claude cho #31 (ước tính, không gọi API)

Tính bằng `cost.llm_estimate(conn, "director_stage_specs", n) × LLM_MARGIN` (CSDL máy chính, chỉ đọc, 15/10):
- Model `claude-sonnet-5`, giá **đo thật trung bình 6 lời gọi** trong sổ chi (vào ≈ 4,1k, ra ≈ 7,9k token/lượt).
- **1 lượt ≈ 0,175 USD**; nhân hệ số dư 1,3 → **0,228 USD/lượt**.
- Đối chiếu #24: 3 lời gọi ≈ 0,53 USD, tức ≈ 0,177 USD/lời gọi, khớp với giá đo.

| Cách chia | Lượt cơ bản | Ước tính thường | Xấu nhất (mỗi cảnh 2 lượt sửa × hỏi lại sai mẫu = 4 lời gọi) |
|---|---|---|---|
| **A. Mỗi cảnh truyện 1 lượt (8 cảnh)** — khuyến nghị | 8 | **≈ 1,82 USD** (8 × 0,228). Nếu như #24 trung bình 1,5 lượt/cảnh thì ≈ 2,7 USD | **≈ 7,30 USD** (32 lời gọi) |
| B. Gộp theo chuỗi cùng bối cảnh (5 đoạn: phòng S1 · mê cung S2–S4 · phòng S5 · tháp S6–S7 · tháp S8) | 5 | ≈ 1,14 USD | ≈ 4,56 USD |

Ghi chú:
- Mỗi cảnh #31 chỉ 2–6 shot, ít hơn 9 shot của #24, nên giá đo (từ cảnh 9 shot) đã **tính dư**.
- Cách B rẻ hơn trên giấy nhưng một lượt phải khai 10–11 shot trên hai chỗ đứng. Cỡ đó chưa thử, và đầu ra có thể vượt
  `max_tokens 24000` (`core/llm_runner.py:108`).
- Thêm vào giá: G0 `director_camera_plan` ≈ 0,027 USD/lượt sẽ **không** chạy cho shot có sân khấu (tiết kiệm nhỏ). K1/K3/K4
  Blender 0 USD.
- **Không gồm:** vẽ lại ảnh khung đầu #31 sau khi nền đổi (gpt-image / Seedream) và QC. Báo giá riêng ở S7 bằng bộ ước tính
  ảnh, trước khi gen.
- Thời gian: Claude ≈ 3 phút/lượt (#24). 8 cảnh chạy song song theo 3 stage thì ≈ 10–15 phút, Blender ≈ 1 phút/cảnh.
- Theo chính sách tiền 04/10: trần chỉ cảnh báo. Đề xuất **mức dự tính cảnh báo 3 USD** cho khâu sân khấu #31 (quyết định Q6).

## 11. Rủi ro
1. **Đạo diễn chưa thử trên cảnh ngoài #24.** Prompt 29 được tinh chỉnh trên giếng/quảng trường. Phòng nhỏ và mê cung có thể ra
   nhiều shot hỏng → nhiều lượt sửa hơn ước tính thường. Giảm rủi ro bằng S6 (thử 1 cảnh trước).
2. **Phòng không trần / mê cung tường thấp:** K1 bắn tia từ trên xuống. Phòng không trần thì loang vẫn đúng. Mê cung tường thấp
   dưới 0,3 m thì không bị coi là tường, cần kiểm ngưỡng trên grid thật ở S5.
3. **Ảnh hướng dẫn người nộm:** model có thể chép màu/khối người nộm vào ảnh. Đo trên S6 trước khi bật cho mọi shot. Đường lùi là
   chỉ gửi câu vị trí (stage_facts).
4. **Xung đột file với nhánh `p31-plate-rules`:** bắt buộc gộp nhánh đó trước (S0).
5. **Chạy lại Đạo diễn** sau khi đã có sân khấu thì state cũ có thể lệch kịch bản mới. Đánh dấu ⚠ cũ và hỏi, không tự xóa máy
   đã duyệt.
6. **Thời gian:** thêm một phase Claude trước ảnh. Dự án có hạn chót (`feedback_fast_mode_deadline`) có thể tắt cờ `stage_auto`
   theo dự án. Tắt thì nói rõ "không theo sân khấu", không im lặng.
7. **Tốn Blender:** K4 ≈ 40 s / 9 shot, chạy nối tiếp (khóa `blender_turn`). Song song theo stage chỉ song song phần Claude.

## 12. Quyết định người dùng cần chọn
- **Q1 – Chia lượt Đạo diễn:** A. mỗi cảnh truyện 1 lượt *(khuyến nghị)* / B. gộp theo chuỗi bối cảnh.
- **Q2 – Người nộm:** (a) ảnh hướng dẫn riêng + câu vị trí, nền sạch chỉ có khối vật *(khuyến nghị)* / (b) vẽ người nộm thẳng vào
  nền / (c) không người nộm, chỉ khối vật + câu vị trí.
- **Q3 – Duyệt tấm ghép K5:** shot đạt đo số thì tự qua, chỉ dừng shot hỏng; Claude xem tấm ghép trên Dashboard *(khuyến nghị,
  hợp "người dùng chỉ duyệt ảnh/video")* / luôn dừng chờ người dùng duyệt từng cảnh.
- **Q4 – G0 `director_camera_plan`:** bỏ cho shot đã có sân khấu *(khuyến nghị)* / chạy cả hai.
- **Q5 – Phòng 447 + 448:** một sân khấu (khai `stage_family` trong Kho) *(khuyến nghị)* / hai sân khấu riêng.
- **Q6 – Tiền:** duyệt báo giá Claude #31 ≈ 1,8 USD thường / tối đa ≈ 7,3 USD, mức dự tính cảnh báo 3 USD. Thử 1 cảnh trước
  (S6, ≈ 0,23–0,91 USD).
- **Q7 – Thứ tự:** chờ nhánh `p31-plate-rules` gộp xong rồi mới làm *(khuyến nghị)* / làm song song phần không chung file
  (S1–S2).
