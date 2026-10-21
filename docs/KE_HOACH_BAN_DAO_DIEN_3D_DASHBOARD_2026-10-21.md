# Kế hoạch bàn đạo diễn 3D trên Dashboard — phần THAO TÁC (M4.8 b) — 21/10/2026

**Trạng thái: CHỜ NGƯỜI DÙNG DUYỆT (Cấp 2). Chỉ là tài liệu: chưa viết code, chưa thêm cờ, chưa gọi API.** Việc C-STAGE-PLAN (cloud-E),
nhánh `cloud/v31-stage-plan`, tách từ `origin/main` `245dc24c`. Mọi tên hàm trong bản này đã được kiểm bằng grep trên nhánh đó.
Tên nào chưa có trong code thì ghi **MỚI**.

Nguồn đã đọc:
- `docs/KE_HOACH_NOI_SAN_KHAU_3D_TU_DONG_2026-10-15.md`: K1–K5 và Q1–Q7. Q3 "Claude xem tấm ghép K5 trên Dashboard" đã duyệt
  15/10 nhưng chưa làm.
- `docs/KE_HOACH_CHIA_VAI_SAN_KHAU_2026-10-16.md` và `docs/DANH_GIA_CHIA_VAI_SAN_KHAU_2026-10-16.md`.
- `docs/PHUONG_PHAP_SAN_KHAU_3D.md`: mục 1 (bảng 5 khâu) và mục 8 (K5 — người duyệt).
- `docs/V3_1_M3_THIET_KE_WORLD_MAP_2026-10-20.md`.
- Skill `vong-lam-viec-theo-plan`, mục 4b.
- Code: `core/stage_auto.py`, `core/stage_crew.py`, `core/stage_director.py`, `tools/stage_auto.py`, `tools/stage_previs.py`,
  `tools/location_pack.py`, `core/place_refs.py`, `core/plates3d.py`, `core/autopilot.py` (`_stage_phase`, `_plate_ack`).
- Màn CHỈ XEM C-STAGE-VIEW (`origin/cloud/v31-stage-view`, `9617f2b8`): `dashboard/stage_view_ui.py` cùng báo cáo
  `docs/RA_CLOUD_STAGE_VIEW_2026-10-21.md`.
- Write guard M2.5 (`origin/cloud/v31-m2-tichhop`, `core/write_guard.py`).

## 0. Tóm tắt

- **Hiện trạng.** Mọi thao tác sân khấu 3D chỉ chạy được bằng CLI: dàn cảnh, chia vai, duyệt hoặc trả lại, ảnh ghép, render lại,
  previs. Lệnh duyệt `--crew-approve` được thiết kế để **người dùng nói trong chat rồi phiên Claude gõ hộ**. `dashboard/` hiện không
  có dòng nào gọi `stage_auto` hay `stage_crew` (đã grep).
- **Mục tiêu.** Người dùng tự bấm trên Dashboard: xem tấm ghép (đã có ở màn XEM), rồi duyệt hoặc trả lại theo ý đồ, làm lại, render lại
  nền, chạy previs. Phiên Claude (Q3) thao tác cùng các nút đó, không còn phải gõ CLI hộ.
- **Khuyến nghị: Phương án A**, gồm hai lớp:
  1. "Hàng nút" gắn **bên trong expander từng cảnh của màn XEM** `stage_view_ui`, sau cờ mới `stage_desk_ui`.
  2. Tầng điều khiển thuần `core/stage_desk.py` (MỚI). Tầng này gom các hàm có sẵn, chạy nền bằng một luồng cho mỗi dự án, xếp
     hàng Blender qua `plates3d.blender_turn`, ghi tiến độ ra tệp và ghi máy qua write guard.
- **Chia đợt.**
  - **Đợt 1 (0 USD):** duyệt / trả lại / làm lại / ảnh ghép / render lại / render nền / đề bài ngoại tuyến.
  - **Đợt 2:** previs và "chọn lần đo" (cần hàm MỚI).
  - **Đợt 3:** nút gọi Claude API (báo giá, trần cứng, duyệt). Chỉ làm sau khi đã đo chi phí chia vai thật (quyết định
    `stage-crew-plan-2026-10-16` (3)).

## 1. Phụ thuộc và điểm nối

| Phụ thuộc | Trạng thái 21/10 | Ảnh hưởng |
|---|---|---|
| C-STAGE-VIEW (`stage_view_ui`, chỉ đọc) | nhánh `cloud/v31-stage-view`, chưa gộp main | Hàng nút gắn vào expander của màn này. Phải gộp trước |
| M2.5 write guard (`core/write_guard.py`, cờ `field_guard`, chế độ SHADOW) | nhánh `cloud/v31-m2-tichhop`, chưa gộp main | `stage_camera` thuộc `REVIEW_FIELDS`. Nút duyệt ghi máy phải đi qua `write_guard.write_scene(..., who=actor("human", …))` |
| Cờ sân khấu hiện có | `stage_auto` (costs), `stage_crew` (costs, OPT_IN_ONLY), `stage_crew_user_approve` (default_on), `stage_handheld_props` | `features.REQUIRES`: `stage_auto` ← `stage_camera` + `place_render_refs`; `stage_crew` ← `stage_auto` |
| Sổ quyết định | `stage-auto-plan-2026-10-15`, `stage-crew-plan-2026-10-16`, `stage-handheld-new-scenes-2026-10-16` | Bàn thao tác không được làm lệch các check `check_stage_auto_plan`, `check_stage_crew_plan` |

**Không trùng với C-STAGE-VIEW.** Màn XEM vẫn giữ luật "không `st.button`, không ghi" (test `tests/test_v31_stage_view.py`). Bàn thao
tác là **module riêng** `dashboard/stage_desk_ui.py` (MỚI). Màn XEM gọi nó bằng **một dòng** ở cuối mỗi expander, và chỉ gọi khi cờ
`stage_desk_ui` bật. Test của màn XEM vẫn chạy với cờ đó TẮT nên không phải sửa.

## 2. AS-IS: lệnh CLI và hàm lõi

| Lệnh (`tools/stage_auto.py` trừ khi ghi khác) | Hàm lõi | Tiền | Ghi |
|---|---|---|---|
| `--project N` | `stage_auto.estimate` | 0 | không |
| `--dry [--scene S]` | `ensure_k1_seg` + `inputs_for` + `preflight` | 0 (Blender K1 ≈ 20 s mỗi chỗ đứng, docstring `ensure_k1`) | `stage/<stage>/k1_*` |
| `--scene S --yes --max-usd X` | `stage_auto.run` → `run_segment` hoặc `run_segment_crew` (khi `stage_crew` bật), bọc `script_cap.from_args` | **Claude API** | tệp đoạn + `scenes.data.stage_camera` |
| `--crew --prompt-out F [--crew-reset]` | `crew_prompt` (lưu `crew/state.json`) | 0 | `crew/state.json` |
| `--crew --answer F.json [--source …]` | `crew_answer` → `stage_crew.ingest` + `_crew_measure` (K3 + K4 Blender) → `_crew_finalize(apply_now=True)` khi tới `xong` | 0 (Blender ≈ 60 s mỗi lần đo 4 shot, đánh giá 16/10 mục 3.4) | `crew/answer_*`, `crew/m<n>/`; khi xong thêm `crew/final/`, `result.json`, `stage_camera` |
| `--crew-approve` / `--crew-tra-lai F` | `crew_user_verdict(approve, tra_lai)` → `crew_answer(source="nguoi_dung")` | 0 | duyệt: như dòng trên. Trả lại: `state.json` |
| `--beats DIR` | `stage_auto.result_round` + `tool().top_cut` (Blender nếu thiếu) + `draw_beats` + `stage_sheet` | 0 | ảnh vào DIR. Không ghi CSDL |
| `--score` | `stage_auto.score_saved` (có thể chạy K1) | 0 | không ghi CSDL |
| `--rerender` | `stage_auto.rerender`: từ chối khi vân tay đầu vào đổi | 0 (Blender) | tệp đo + `stage_camera` (`apply`) |
| `--set-family F --place …` | `stage_auto.set_family` | 0 | **Kho** |
| `tools/stage_previs.py --project N --scene S --shots a-b --out D …` | `stage_previs.plan` (thuần) + `stage_grid.run_blender_safe` (timeout 3600 s, `:715`); **chưa có hàm lõi để gọi**, chỉ `main(argv)` | 0 | video vào `--out`. Không ghi CSDL |
| `tools/location_pack.py render --project N [--fresh-shot i]` | `location_pack.ensure_plates(fresh=…)`. Dashboard đã có `place_refs.ensure_async` + `retry_render` (nút "↻ Render lại nền 3D shot N", `dashboard/steps/step2.py:plate_retry_buttons`) | 0 | `plates/`, `plates/index.json` |
| (autopilot) | `autopilot._stage_phase` → `stage_auto.run`; shot hỏng → `_plate_ack` giữ ở cổng `plates` | Claude API | như `run` |

Ba điểm làm Dashboard **không thể chỉ gọi lại CLI** mà phải sửa:
1. **Bật cờ bằng biến môi trường.** CLI đặt `os.environ["FEATURE_STAGE_AUTO"]="1"` để chạy khi cờ tắt ("lệnh tay = người chọn"). Làm vậy
   trong tiến trình Streamlit sẽ **bật cờ cho mọi phiên và cho autopilot**. Dashboard phải truyền tham số rõ, ví dụ
   `run(..., manual=True)` (**MỚI**). Không được đụng vào `os.environ`.
2. **Ghi máy bằng SQL trực tiếp.** `stage_auto.apply` dùng `UPDATE scenes SET data=…` + `commit`, không qua write guard và không có
   `_rev`. Vì vậy hai tác vụ (autopilot và người bấm) có thể ghi đè nhau.
3. **Hàm "đọc" vẫn ghi.** `_crew_ctx` gọi `ensure_k1_seg` (có thể chạy Blender). `crew_prompt` luôn `_crew_save`. Màn thao tác không
   được gọi các hàm này ở mỗi lần vẽ lại Streamlit. Chỉ gọi khi người dùng bấm.

## 3. Luồng người dùng trên Dashboard

**Ở đâu.** Bước 2 (Ảnh) có khối "🧊 Sân khấu 3D (chỉ xem)" nằm ngay trên khối gen ảnh, mỗi cảnh truyện một expander. Đây là màn của
C-STAGE-VIEW. Sân khấu phải chốt **trước** nền 3D và **trước** mọi ảnh (autopilot: phase `stage` sau `previz`, trước `plates`), nên
đặt ở Bước 2 phía trên nút Gen là đúng thứ tự.

**Mỗi cảnh hiện một dòng trạng thái**, đọc thuần từ `crew/state.json` + `result.json` + `scenes.data`:

```
[chưa có K1] → [chưa dàn] → [đang ở vai: dao_dien | quay_phim | quay_phim_duyet | dao_dien_tra_loi]
            → [chờ NGƯỜI DÙNG duyệt] (phase 'duyet' + stage_crew_user_approve)
            → [đã chốt — máy ghi shot a, b; shot c dùng máy thường (lý do)] → [nền 3D cũ → render lại] → (Gen ảnh như cũ)
          ↘ [đầu vào đổi — lượt dở không dùng được] (state.fp ≠ fingerprint) → chỉ còn nút "Làm lại"
```

Chi tiết từng bước:
1. **Xem.** Màn XEM đã có tấm khối, mặt cắt K1, nền từng shot kèm máy, world map 2D và cảnh báo. Bàn thao tác thêm phần chỉ đọc
   (thuần, không Blender):
   - ảnh `top_beats.png` của lần đo đang chọn từng shot (`crew/m<n>/`, `crew/final/`);
   - **bảng đối chiếu "đã khai ↔ đo được"**, đọc từ tệp đã lưu (không gọi `_crew_view`, vì hàm đó đi qua `_crew_ctx` → có thể chạy
     K1);
   - danh sách `giu_lech` (giữ lệch), đề nghị dời người, `unresolved` (chưa giải quyết).
2. **Chưa có tấm ghép** thì có nút "🖼 Dựng tấm ghép" (0 USD).
3. **Phase `duyet`** thì có hai nút "✅ Duyệt sân khấu cảnh S" và "↩ Trả lại". Trả lại mở form: mỗi shot một ô ý đồ, ví dụ "Kelly
   lùi 1 m", "xe nôi phải đọc được".
4. **Vai AI tới lượt.** Có hai đường:
   - (Đợt 1) "📝 Đề bài cho phiên Claude Code" (ngoại tuyến 0 USD, như 16/10). Đề bài ghi vào thư mục đoạn. Phiên Claude đọc, trả lời
     rồi bấm "📥 Nạp câu trả lời".
   - (Đợt 3) "▶ Chạy tổ sân khấu qua API" (báo giá, duyệt, trần cứng).
5. **Đã chốt** thì nút "↻ Render lại nền 3D cảnh này" (0 USD), rồi Gen ảnh như cũ. Bước Gen vẫn qua `tools/pregen_check.py` và cổng có
   sẵn.
6. **Previs** (Đợt 2): nút "🎞 Previs one-shot" cho cảnh đã chốt, xem video ngay trong expander.

**Claude thao tác Dashboard (Q3).** Phiên Claude bấm được mọi nút **trừ "Duyệt" và "Trả lại"**: hai nút này ghi
`approved_by = "nguoi_dung"`, đúng luật "phiên Claude không tự duyệt bước dành cho người dùng" (rà 16/10 CAO,
`crew_answer` chặn `source != "nguoi_dung"` ở phase `duyet`). Dashboard nhận diện người bấm bằng `common.access_user()` + quyền `core/access` (chế độ CHỈ XEM của `access_ui` đã khóa nút ghi). Câu hỏi
**Q-B** ở mục 12 hỏi người dùng chốt cách nhận diện.

## 4. Danh sách NÚT ↔ hàm

Chú thích cột:
- **Khóa**: B = xếp hàng Blender qua `plates3d.blender_turn` (khóa tệp của máy, áp cho mọi cửa sổ Dashboard và mọi công cụ).
  S = khóa thao tác sân khấu theo (dự án, cảnh), **MỚI**, xem mục 5.
- **Nền**: chạy trong luồng nền và hiện tiến độ (mục 5).
- **Thời gian**: số đã đo thì ghi nguồn. "Đo ở ca thử" nghĩa là chưa có số, phải đo trên #31 trước khi in lên nút.

| # | Nút (đợt) | Gọi | Tiền | Thời gian | Khóa / nền | Ghi dữ liệu | Lỗi thì nói |
|---|---|---|---|---|---|---|---|
| N1 | 🔍 Kiểm đầu vào (Đ1) | `ensure_k1_seg` + `inputs_for` + `preflight` (như `--dry` một cảnh) | 0 | K1 ≈ 20 s mỗi chỗ đứng nếu chưa cache; còn lại < 1 s | B, S, nền | `stage/<stage>/k1_*` (cache theo sha model + chỗ đứng) | `missing` nguyên văn (ví dụ thiếu `height_m` nhân vật X → "sửa ở Kho"); cổng 0 USD chưa qua → liệt kê; Blender lỗi → `BlenderError` + "không tìm thấy Blender" |
| N2 | 💲 Ước tính (Đ1) | `stage_auto.estimate` (+ `crew_usd` khi `stage_crew` bật) | 0 | < 1 s | — | không | `usd None` → "chưa có giá Claude cho model đang dùng (bảng giá)" |
| N3 | 📝 Đề bài cho phiên Claude Code (Đ1) | `crew_prompt(conn, pid, seg, data_dir)` → ghi `doan_<S>/crew/de_bai_<phase>.md` (**MỚI**: đường cố định thay cho `--prompt-out F`) | 0 | < 2 s (+ K1 nếu thiếu) | S | `crew/state.json` (tạo nếu chưa có), tệp đề bài | `problems` (đầu vào đổi → "Làm lại"; phase `xong`; phase `duyet` → "chờ NGƯỜI DÙNG") |
| N4 | 📥 Nạp câu trả lời vai (Đ1) | `crew_answer(…, obj, source="claude_code")`. Dán JSON hoặc chọn tệp `crew/tra_loi_<phase>.json` | 0 | 1–60 s (đo K3 + K4 khi phase cần; ≈ 60 s mỗi lần đo 4 shot) | B, S, nền | `crew/answer_NN_<phase>.json`, `crew/m<n>/`; tới `xong` thì `_crew_finalize` + `apply` (**qua guard, mục 7**) | `errors` theo dòng (như `<tệp>.loi.txt`); đo lỗi → "không đo được (K3 / K4): …" và state giữ nguyên. **Không cho chọn `source=nguoi_dung` ở nút này** |
| N5 | 🖼 Dựng tấm ghép (Đ1) | `result_round` (hoặc thư mục lần đo hiện tại) + `tool().top_cut` nếu thiếu `top_cut.png` + `draw_beats` + `stage_sheet` → `doan_<S>/beats/san_khau_canh<S>.png` (**MỚI**: đường trong data_dir để màn XEM đọc) | 0 | top_cut chạy Blender: đo ở ca thử; vẽ < 5 s | B (top_cut), nền | tệp ảnh. Không ghi CSDL | "chưa có lượt đã lưu"; "không cắt được mái → vẽ trên ảnh thường" (như CLI) |
| N6 | ✅ Duyệt sân khấu cảnh (Đ1) | `crew_user_verdict(approve=True)` → `_crew_finalize(apply_now=True)` | 0 | < 5 s (không đo lại) | S | `crew/final/`, `result.json`, `inputs.json`, `scenes.data.stage_camera` + `stage_segment` (qua guard), ⚙ Chẩn đoán (`_say`), dòng audit duyệt (mục 7) | Có shot đã vẽ ảnh (`camera_plan.drawn_shots`) → hộp xác nhận riêng "ảnh shot … sẽ lệch nền — vẫn đổi máy?" (tương đương `--force`); phase ≠ `duyet` → nút ẩn; shot hỏng (`bad`) → liệt kê "dùng máy thường" |
| N7 | ↩ Trả lại (Đ1) | `crew_user_verdict(approve=False, tra_lai=[{shot, y_do}])` | 0 cho bước này. Vai kế cần trả lời (N3/N4, hoặc N13 tốn tiền) | < 1 s | S | `crew/state.json` (`n_returns`, phase về `quay_phim_duyet` / `dao_dien_tra_loi`) | Thiếu ý đồ hoặc shot ngoài cảnh → lỗi của `validate_approve` ("duyet=false cần tra_lai: [{shot, y_do}]"). Không giới hạn số lần (kế hoạch 16/10 mục 2.4) |
| N8 | 🗑 Làm lại từ Đạo diễn (Đ1) | `crew_prompt(reset=True)` → `_crew_reset` cất `crew/` → `crew_cu_<giờ>/` | 0 | < 1 s | S, xác nhận hai bước | đổi tên thư mục. **Không gỡ** `stage_camera` đã ghi (đường `run` mới gỡ khi `stale`) | Có máy đã ghi → nói "máy cũ giữ tới khi duyệt lượt mới" |
| N9 | 🔁 Render lại từ câu trả lời đã lưu (Đ1) | `stage_auto.rerender` | 0 | K3 + K4: ≈ 60 s mỗi 4 shot | B, S, nền | tệp đo + `stage_camera` (qua guard) | "đầu vào đã đổi so với lần trả tiền — không dựng lại"; "chưa có câu trả lời Đạo diễn đã lưu" |
| N10 | 🧮 Chấm lại các lượt đã lưu (Đ1) | `stage_auto.score_saved` | 0 | < 5 s (+ K1 nếu thiếu) | S | không ghi CSDL | lỗi từng lượt theo bộ kiểm hiện tại |
| N11 | ↻ Render lại nền 3D cảnh này (Đ1) | `location_pack.forget_shot` từng shot của cảnh + `place_refs.ensure_async` (mở rộng nút sẵn có `plate_retry_buttons` từ một shot lên một cảnh) | 0 | đo ở ca thử (một lượt Blender cho mỗi model + giờ/thời tiết) | B (trong `plates3d.render`), luồng `place_refs._RUNNING[pid]` | `plates/`, `plates/index.json` | `plate_failed` / `plate_needs` của từng shot (màn XEM đã hiện) |
| N12 | 🎞 Previs one-shot (Đ2) | **MỚI** `stage_previs.run(conn, pid, scene, shots, out, opts)` tách từ `main` (`plan` + `run_blender_safe`); tham số cho chọn: `--uniform-run`, `--lens-range 24 35`, `--orbit` | 0 | đo ở ca thử (timeout 3600 s) | B, S, nền | `doan_<S>/previs/<giờ>/` (clay + depth mp4). Không ghi CSDL | "không tìm được lối" (mặc định dừng, như `--allow-straight` tắt); Blender bản Store bị dừng → "dừng Blender bằng Stop-Process" (skill 4b) |
| N13 | ▶ Chạy tổ sân khấu qua API (Đ3) | `stage_auto.run(conn, pid, data, client, scenes={S}, manual=True)` (**MỚI** `manual`), bọc `script_cap.ScriptCap(max_usd, "stage_auto")` | **Claude API**: hiện số `estimate` và `usd_max` ngay trên nút | Claude ≈ 3 phút mỗi lượt (#24) × 4–6 lượt chia vai + Blender | S, nền, B (khi đo) | như `run` + sổ chi `llm_runner.tagged(stage, pid)` | Hết tiền → `_stop_if_claude_blocked` như autopilot; sai mẫu 2 lần → "tổ sân khấu (…) trả lời sai mẫu 2 lần" và **không gọi lại** |
| N14 | 🎯 Chọn lần đo cho shot (Đ2) | **MỚI** `crew_user_pick(…, shot, lan_do)`: ghi `state["accepted"][shot]` như kết luận `khop` (`_crew_pick` ưu tiên lần đã duyệt). Chỉ chọn trong `shot_hist` | 0 | < 1 s | S | `crew/state.json` | lần đo không thuộc shot → lỗi như `validate_review` ("lan_do … không phải một lần đo của shot này") |
| N15 | 🗺 Dựng lại world map cảnh (Đ2, cờ `world_map`) | `world_map.refresh(data_dir, pid, scene, k1_dir=…, seg_dir=…)` | 0 | < 2 s | S | `world/scene_<S>.json` | cờ TẮT → nút ẩn (hàm trả None) |
| N16 | 🏷 Khai họ sân khấu (Đ2) | `stage_auto.set_family(conn, place_ids, family)` từ gợi ý `family_hints` | 0 | < 1 s | — | **Kho** (`stage_family`); qua đường ghi Kho sẵn có | gợi ý VÀNG "chỗ đứng trùng nhau, chưa khai họ" (không tự gộp) |

Không làm nút "sửa blocking/specs bằng tay trên Dashboard". Theo phương pháp mục 8, người dùng sửa bằng **câu ngắn** (N7 trả lại),
còn vai tự đổi thành dữ liệu. Không có luật cấm cứng (skill 4b, bước 1).

## 5. Chạy nền, khóa Blender, tiến độ

- **Luồng nền** theo mẫu `place_refs.ensure_async`: mỗi (dự án, cảnh) **một** `threading.Thread` daemon trong `stage_desk._RUNNING`.
  Luồng mở **kết nối sqlite riêng** (`sqlite3.connect(db, timeout=60)`); CSDL `:memory:` thì từ chối chạy, giống `ensure_async`. Bấm
  lại khi luồng còn sống thì báo "đang chạy …", không chạy thêm luồng thứ hai.
- **Khóa S (MỚI).** Tệp `doan_<S>/.desk.lock` chứa {pid tiến trình, owner, nút, giờ}. Khóa này chặn **autopilot `_stage_phase`** và
  **CLI `tools/stage_auto.py`** đụng cùng đoạn cùng lúc với nút, vì `crew/state.json` không có khóa và hai bên ghi đè nhau. Khóa có
  tiến trình đã chết hoặc quá hạn thì bị gỡ và báo, giống `blender_turn` (`pid_alive`, `LOCK_STALE_SEC`). Autopilot gặp khóa S thì
  `_Wait("plates", "đang thao tác sân khấu cảnh S trên Dashboard")`, không im lặng.
- **Blender** đã xếp hàng sẵn: `stage_grid.run_blender_safe` và `plates3d.render` đều vào `plates3d.blender_turn` (chờ tối đa
  `LOCK_WAIT_SEC` = 1800 s). Nút hiện "chờ lượt Blender (đang có `plates3d.queue_length()` tác vụ chờ)".
- **Tiến độ.** Luồng ghi `doan_<S>/desk_progress.json` gồm {nút, bắt đầu, bước hiện tại, dòng log cuối (≤ 50), xong/lỗi}. Hàm `log`
  truyền vào `crew_answer` / `rerender` / `run` ghi tệp này. Màn tự làm mới mỗi 2 s bằng mẫu `common.periodic`, chỉ trong lúc có
  luồng chạy. Đóng trình duyệt thì luồng vẫn chạy (daemon trong tiến trình Streamlit). **Tắt tiến trình** thì tác vụ dừng; lần mở sau
  thấy `desk_progress.json` không có "xong" và luồng không sống → báo "tác vụ bị ngắt lúc …, state giữ nguyên (crew_answer không lưu
  nửa vời khi đo lỗi)".
- **Không chạy song song hai sân khấu** trong Đợt 1–2. Blender vốn chạy lần lượt, chỉ phần Claude của N13 (Đợt 3) mới đáng chạy song
  song.

## 6. Tiền: báo giá + duyệt (chỉ N13, Đợt 3)

- Trước khi bấm: hiện `stage_auto.estimate(...)` cho **đúng cảnh đã chọn**, gồm `usd` (thường) và `usd_max` (xấu nhất). Khi
  `stage_crew` bật, hai số này lấy từ `crew_usd` với `CREW_CALLS` × `cost.LLM_MARGIN`. **Không tính giá tay** (quy ước 7b).
- Ô "trần cứng USD" mặc định = `usd_max` của cảnh. Bấm thì cần **tick xác nhận** theo mẫu `common._confirm_big_batch`. Lời gọi chạy
  trong `ScriptCap(max_usd, "stage_auto")`, giống `--max-usd` (`script_cap.from_args`): chạm trần thì `CapReached`, dừng, nói rõ.
- Sổ chi: `llm_runner.tagged(stage, pid)` theo từng vai (`director_stage_blocking`, `dp_stage_specs`, `dp_stage_review`,
  `director_stage_approve`), như `run_segment_crew` đang làm.
- **Điều kiện mở Đợt 3:** đo chi phí chia vai thật trên #31 bằng `cost.llm_estimate` trên đề bài thật (0 USD), rồi người dùng duyệt
  số (quyết định `stage-crew-plan-2026-10-16` (3); `stage_crew` nằm trong `OPT_IN_ONLY`). Đánh giá 16/10 mục 3.5 ghi đề bài Quay
  phim ≈ 20k token mỗi lượt. Phải xử lý cache / cắt `dp.md` trước.
- Mọi nút khác là **0 USD**. Trên nút ghi "(0 USD)" giống "↻ Render lại nền 3D shot N (0 USD)".

## 7. Ghi dữ liệu: write guard (M2.5) + sổ quyết định + audit

- **Ghi máy qua guard.** Thay SQL trực tiếp trong `stage_auto.apply` bằng một đường ghi chung (**MỚI** `stage_auto.apply(...,
  who=None)`). Mỗi shot gọi `write_guard.write_scene(conn, scene_id, {"stage_camera": cam, "stage_segment": seg_id}, who,
  expected_rev=…)` **trước** lệnh UPDATE hiện có (chế độ SHADOW: chỉ ghi chẩn đoán, không chặn). Khi bật enforce (C3-6) thì guard giữ
  trường USER_LOCKED và ghi đề xuất.
  - `who`:
    - nút Duyệt (N6) → `write_guard.actor("human", "<người dùng>", via="stage_desk")`;
    - rerender (N9) → `actor("tool", "stage_desk.rerender")`;
    - API (N13) → `actor("ai", "stage_crew")`;
    - autopilot → `actor("auto", "autopilot.stage")`.
  - `expected_rev` = `_rev` đọc lúc **mở** lượt duyệt (lưu trong `desk_progress.json`). Lệch nghĩa là có tác vụ khác đã ghi shot đó
    → `stale_write` → hiện diff, hỏi lại; không ghi lặng.
  - Giữ đúng hành vi khóa tay hiện có: `FIELD in _user_locked` → giữ. Cờ `field_guard` TẮT → không đọc thêm, không ghi gì thêm (byte
    giống, test).
- **Không ghi CSDL trước khi duyệt.** Mọi nút trừ N6, N9, N13, N16 chỉ ghi tệp trong `stage/<stage>/doan_<S>/` hoặc `plates/`.
  Đây là luật đã chốt 16/10: chưa ghi hoặc gỡ máy CSDL tới khi `--crew-approve`.
- **Sổ quyết định `data/decisions.json`** chỉ chứa quyết định *chính sách* kiểm được bằng code, không chứa lượt duyệt từng cảnh.
  Ghi một mục mới khi người dùng duyệt kế hoạch này, ví dụ `stage-desk-dashboard-2026-10-2x`, với `enforced_by`:
  - cờ `stage_desk_ui` (TẮT);
  - `check_stage_desk` (MỚI, trong `tests/test_decisions.py`). Check này kiểm: nút duyệt chỉ gọi `crew_user_verdict` với
    `source="nguoi_dung"`; N4 không nhận `nguoi_dung`; N13 bọc `ScriptCap`; không đặt `os.environ["FEATURE_*"]` trong `dashboard/`.
- **Lượt duyệt từng cảnh** (ai, lúc nào, cảnh nào, vân tay đầu vào, shot nào ghi máy hoặc dùng máy thường) ghi vào:
  - `crew/state.json` (`approved_by` đã có);
  - `result.json` (`crew.approved_by`);
  - một dòng `⚙ Chẩn đoán` (`_say`, mã `stage_auto`);
  - một dòng audit guard (`_field_prov` của `stage_camera`).

  Không cần bảng mới.
- **World map**: duyệt sân khấu làm `blocking.json` / `shot_specs.json` đổi, nên `world_map.stale` báo map cũ. Màn XEM đã hiện cảnh
  báo này. N15 dựng lại. Không tự dựng lại trong N6 (giữ luật G2-4: map không nằm trên đường gen).

## 8. Phương án thiết kế

### Phương án A — Hàng nút trong expander của màn XEM + tầng `core/stage_desk.py` (KHUYẾN NGHỊ)
- `dashboard/stage_desk_ui.py` vẽ nút theo phase và gọi `core/stage_desk.py`. `stage_desk.py` thuần, test được không cần Streamlit:
  `status(…)`, `start(action, …)`, `progress(…)`, khóa S, luồng nền. Lớp này bọc các hàm có sẵn ở mục 4.
- **Ưu:**
  - Người dùng thấy ảnh và nút ở cùng chỗ (đúng K5).
  - Dùng lại toàn bộ dữ liệu `collect` của màn XEM.
  - Cờ TẮT thì màn XEM y nguyên.
  - Mỗi nút một hàm lõi nên CLI và Dashboard dùng chung (luật 4 chuẩn xây dựng).
  - Phiên Claude bấm được qua Dashboard (Q3).
- **Nhược:**
  - Bước 2 dài thêm.
  - Expander Streamlit bị vẽ lại mỗi lần bấm, nên phải giữ thao tác nặng ngoài vòng vẽ (đã giải ở mục 2 điểm 3 và mục 5).
  - Phụ thuộc C-STAGE-VIEW gộp trước.

### Phương án B — Trang riêng "🎬 Bàn đạo diễn 3D" (màn ngoài các bước, dạng wizard từng cảnh)
- Một trang có thanh cảnh bên trái và khung lớn: tấm ghép, bảng đối chiếu, nút.
- **Ưu:**
  - Rộng chỗ cho tấm ghép lớn và bảng đối chiếu.
  - Không làm nặng Bước 2.
  - Hợp với M6.7 sau này (3D Artist đứng tên sân khấu).
- **Nhược:**
  - Tách khỏi luồng bước, dễ quên duyệt trước khi Gen ảnh. Phải thêm cổng ở Bước 2 trỏ sang.
  - Lặp phần đọc của màn XEM (hai nơi hiện cùng dữ liệu, dễ lệch).
  - Thêm định tuyến trang (`dashboard/app.py`).

### Phương án C — Chỉ nút DUYỆT / TRẢ LẠI trên Dashboard, phần còn lại vẫn CLI qua phiên Claude
- Thêm đúng 2 nút (N6, N7) + N5 vào màn XEM. Đề bài, nạp trả lời, render, previs vẫn do phiên Claude chạy CLI theo hộp thư.
- **Ưu:**
  - Nhỏ nhất (≈ 1 phiên con), rủi ro thấp.
  - Bỏ được khâu "người dùng nói trong chat → Claude gõ `--crew-approve`".
- **Nhược:**
  - Người dùng vẫn phụ thuộc phiên Claude cho mọi bước khác.
  - Không giải quyết render lại nền / previs.
  - Vẫn phải làm khóa S (autopilot và CLI đụng nhau) và guard.

### Khuyến nghị
**A, làm theo đợt.** Đợt 1 về thực chất là C + N1–N5, N8–N11, chạy trên tầng `stage_desk` nên không phải làm lại sau. Đợt 2 thêm
N12, N14–N16. Đợt 3 thêm N13 sau khi đo chi phí. B để dành cho M6.7 nếu Bước 2 quá dài. Tầng `stage_desk` dùng lại được, chỉ đổi
lớp vẽ.

## 9. Cờ

| Cờ | Mặc định | Khai | Ghi chú |
|---|---|---|---|
| `stage_desk_ui` (MỚI) | TẮT, `verified: False`, **không `costs`** (Đợt 1–2 đều 0 USD) | `core/features.py`, `REQUIRES["stage_desk_ui"] = ("stage_view_ui",)`, `tests/golden/package_inputs.json` (false) | Nhãn: "Bàn đạo diễn 3D: duyệt / trả lại / render lại sân khấu trên Bước 2 (0 USD)" |
| `stage_desk_api` (MỚI, Đợt 3) | TẮT, `costs: True`, trong `OPT_IN_ONLY` | `REQUIRES = ("stage_desk_ui", "stage_auto")` | Chỉ cờ này mới hiện N13 |
| `stage_view_ui` | như C-STAGE-VIEW | — | bàn thao tác chỉ hiện khi màn XEM bật |
| `stage_crew_user_approve` | BẬT | — | Tắt thì phase `duyet` do Đạo diễn (API). N6/N7 ẩn, hiện chữ "duyệt chốt do Đạo diễn (cờ …)" |
| `field_guard` | theo M2.5 | — | TẮT thì N6/N9 ghi như hôm nay (byte giống) |

## 10. Kế hoạch test (đỏ → xanh, không gọi API, Blender giả trừ ca đánh dấu chạy thật)

Fixture: thư mục data tạm + CSDL tệp tạm (không `:memory:` vì luồng nền mở kết nối riêng); 2 cảnh, 4 shot; `crew/state.json` dựng sẵn ở
các phase `quay_phim`, `duyet`, `xong`; `measure` giả (hàm thay `_crew_measure`) để không cần Blender.

1. **Cờ TẮT:**
   - `stage_desk_ui` TẮT → không lời gọi `st` nào từ `stage_desk_ui`;
   - test của màn XEM (`tests/test_v31_stage_view.py`) vẫn xanh, kể cả ca "không có `st.button`";
   - Bước 2 giống byte.
2. **Nút theo phase:**
   - phase `duyet` + `stage_crew_user_approve` → có N6/N7;
   - phase khác → không có N6/N7;
   - `state.fp ≠ fingerprint` → chỉ N8.
3. **N6 duyệt:**
   - gọi `crew_user_verdict(approve=True)` với `source="nguoi_dung"`;
   - shot đạt → `stage_camera` trong CSDL, shot hỏng → `bad`;
   - `_user_locked` giữ nguyên;
   - có shot đã vẽ ảnh → phải xác nhận, không xác nhận thì không ghi.
4. **N7 trả lại:**
   - thiếu `y_do` → lỗi `validate_approve`, state không đổi;
   - hợp lệ → phase đổi, CSDL không đổi (sha CSDL trước/sau);
   - trả lại 3 lần liên tiếp đều nhận.
5. **N4 nạp trả lời:**
   - JSON sai → danh sách lỗi, state không đổi;
   - phase `duyet` → từ chối mọi `source` từ nút này;
   - đo lỗi → state giữ nguyên (đúng `crew_answer`).
6. **Không ghi trước duyệt:** N1–N5, N7, N8, N10, N11, N12, N15 → sha CSDL không đổi.
7. **Khóa S:**
   - hai lần bấm liền → một luồng;
   - autopilot `_stage_phase` gặp khóa → `_Wait` có câu;
   - khóa của tiến trình chết bị gỡ và báo;
   - CLI gặp khóa → từ chối có câu.
8. **Không đụng `os.environ`:** quét `dashboard/` + `core/stage_desk.py`, không có `FEATURE_` gán. `run(manual=True)` chạy khi cờ
   `stage_auto` TẮT mà `features.on("stage_auto")` vẫn False sau đó.
9. **Guard (cờ `field_guard` BẬT):**
   - N6 ghi `actor human` → không có chẩn đoán;
   - autopilot ghi đè `stage_camera` khác giá trị người duyệt → `field_review` / `field_conflict`;
   - `expected_rev` cũ → `stale_write`.

   Cờ TẮT → đường ghi y hệt (so dữ liệu).
10. **Tiến độ:** `desk_progress.json` có bước và log. Luồng ném lỗi → "lỗi" kèm câu, không nuốt. Tác vụ bị ngắt → câu "bị ngắt".
11. **N13 (Đợt 3):**
    - client giả: ước tính hiện trước;
    - không tick thì không gọi;
    - `ScriptCap` chạm trần → dừng, sổ chi có dòng;
    - sai mẫu 2 lần → không gọi lại ở lần bấm sau (đúng `run_segment_crew`).
12. **Đường dẫn:** mọi tệp qua `data_dir` của pipeline (chạy với cwd khác); tấm ghép N5 nằm trong `doan_<S>/beats/` và màn XEM đọc được.
13. **Ma trận luồng (luật 2 chuẩn xây dựng):** cùng một cảnh qua CLI `--crew-approve` và qua N6 ra cùng `result.json` + `stage_camera`
    (trừ `approved_by` / audit).
14. **Ca thật (0 USD, máy chính, #31 cảnh 3, ngoại tuyến):** N5 → N7 (một ý đồ) → N3/N4 (phiên Claude Code trả lời) → N5 → N6 → N11.
    Ghi số giây từng nút vào báo cáo để thay các ô "đo ở ca thử" ở mục 4.

Trước commit code: `py tools/related_areas.py` → một agent rà quy ước 7 (vùng step2, stage_auto, autopilot `_stage_phase`,
write_guard). `py -m core.decisions check` xanh.

## 11. Rollback

- **Tắt cờ `stage_desk_ui`** → không nút nào hiện, màn XEM như C-STAGE-VIEW. Không cần migration: Đợt 1–2 không thêm bảng hay cột.
- Tệp do nút tạo đều nằm trong thư mục đoạn: `beats/`, `previs/`, `de_bai_*.md`, `desk_progress.json`, `.desk.lock`. Xóa được, không ai
  khác đọc.
- **Máy đã ghi bằng N6** cùng dạng với `--crew-approve`. Gỡ bằng N8 + chạy lại, hoặc Bước 2 "đặt lại máy" có sẵn. Guard có
  `_field_prov` để biết ai ghi.
- `stage_auto.apply(who=…)` là tham số tùy chọn: `who=None` → hành vi cũ. Revert commit thì CLI vẫn chạy.
- Khóa S hỏng (kẹt) → tự gỡ khi tiến trình chết hoặc quá hạn. Có thể xóa tay `.desk.lock`.

## 12. Câu hỏi cần người dùng chốt

- **Q-A — Phương án:** A (nút trong màn XEM, theo đợt) *(khuyến nghị)* / B (trang riêng) / C (chỉ Duyệt + Trả lại).
- **Q-B — Ai được bấm Duyệt:**
  - chỉ người dùng (Dashboard ghi `approved_by = nguoi_dung` theo `common.access_user()`; phiên Claude thao tác Dashboard bị ẩn N6/N7)
    *(khuyến nghị, giữ quyết định 16/10 (1))*;
  - hoặc cho phiên Claude bấm khi người dùng đã nói duyệt trong chat. Khi đó cần cơ chế xác minh, như `devsys.answers add … --source
    chat`.
- **Q-C — Cổng trước Gen ảnh:** cảnh có sân khấu đang ở phase `duyet` (chờ người dùng) thì nút Gen ảnh của **các shot cảnh đó**:
  - chỉ cảnh báo VÀNG *(khuyến nghị, hợp chính sách "không chặn cứng")*;
  - hoặc chặn tới khi duyệt.

  Autopilot hiện đã giữ ở cổng `plates`.
- **Q-D — Shot đã vẽ ảnh:** N6 với cảnh có shot đã vẽ:
  - hỏi xác nhận riêng (như `--force`) *(khuyến nghị)*;
  - hoặc cấm trên Dashboard, chỉ CLI.
- **Q-E — Đợt 3 (API):** đồng ý điều kiện "đo chi phí chia vai thật trên #31 rồi mới mở N13", và trần mặc định = `usd_max` của cảnh?
- **Q-F — Previs trên Dashboard (Đợt 2):** có cần không? Lượt thử V2V 16/10 chưa theo được đường máy vòng (đánh giá mục 4). Nếu tạm
  chưa dùng previs làm ref thì có thể bỏ N12.
- **Q-G — Chọn lần đo (N14):** người dùng muốn tự chọn lần đo cho từng shot (ví dụ "lấy m1 của shot 10"), hay chỉ trả lại bằng câu
  ý đồ (N7) để Quay phim chọn?

## 13. Thứ tự làm (sau khi duyệt)

| Đợt | Việc | Tiền | Điều kiện |
|---|---|---|---|
| 0 | Gộp C-STAGE-VIEW + nhánh tích hợp M2 (write guard) vào main | 0 | phiên chính |
| 1 | `core/stage_desk.py` (status, khóa S, luồng nền, tiến độ) + `stage_auto.apply(who)` + `run(manual)` + N1–N11 trừ N13 + cờ `stage_desk_ui` + test 1–10, 12–13 + sổ quyết định | 0 | rà quy ước 7 |
| 1b | Ca thật #31 cảnh 3 (test 14) trên máy chính → ghi số giây | 0 | người dùng xem tấm ghép, duyệt bằng N6 |
| 2 | N12 (tách `stage_previs.run`), N14 (`crew_user_pick`), N15, N16 | 0 | Q-F, Q-G |
| 3 | N13 + cờ `stage_desk_api` + test 11 | Claude API (báo giá trên nút) | Q-E + số đo chi phí thật |

Ước lượng công: Đợt 1 ≈ 2 phiên con (một phiên `core/stage_desk.py` + `stage_auto`, một phiên `dashboard/stage_desk_ui.py` + test UI,
không chồng file). Đợt 2 ≈ 1 phiên. Đợt 3 ≈ 1 phiên.
