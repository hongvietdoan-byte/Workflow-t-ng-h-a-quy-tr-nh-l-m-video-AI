# C-M48-DESK-CORE — Bàn đạo diễn 3D, Đợt 1: tầng lõi (cloud-C, 22/10; chuyển từ cloud-E)

- Nhánh: `cloud/v31-m48-desk-core`.
  - Nền: `origin/cloud/v31-m2-tichhop` (có write guard M2.5) + gộp `origin/main`.
  - Xung đột `features.py` / `areas.json` / `package_inputs.json` đã giải bằng `tools/merge_union.py`, commit `3a728491`.
- **Gộp main CÙNG tích hợp M2 khi golden ĐẠT** (theo đề bài).
- 0 USD. Không gọi Claude API. Không thêm cờ (cờ UI `stage_desk_ui` thuộc C-M48-DESK-UI). Không sửa `dashboard/`.
- Kế hoạch: `docs/KE_HOACH_BAN_DAO_DIEN_3D_DASHBOARD_2026-10-21.md` mục 0, 2, 4, 5, 7, 9, 10, 13.
- Sổ quyết định: `v31-ep-stage-desk-actions-2026-10-21` (S-A…S-G).

## API công khai cho C-M48-DESK-UI (`core/stage_desk.py`, ghi đủ ở docstring đầu module)

| Loại | Hàm | Ghi chú |
|---|---|---|
| Đọc | `status(conn, pid, data_dir)`, `scene_status(…, scene)` | Thuần: không Blender, không ghi, không gỡ khóa |
| Đọc | `progress(data_dir, pid, scene, conn)` | Trạng thái `running` / `done` / `error` / `interrupted` |
| Đọc | `is_executive_producer(conn, pid, user)` | S-B |
| Đọc | `paid_gate(conn, pid, data_dir, scene_ids)` | S-C |
| Đọc | `lock_holder(…, clean=True)`, `busy(…)`, `cam_mark(cam)` | Khóa S |
| Giữ khóa | `hold_segments(conn, pid, data_dir, segs, action, who)` | Autopilot / CLI giữ khóa S |
| Nút | N1 `check_inputs` (nền) · N2 `estimate` · N3 `write_prompt` · N4 `load_answer` (nền, nguồn cố định `claude_code`) · N5 `build_sheet` (nền) | |
| Nút | N6 `approve(…, who, user, confirm_drawn, expected_revs, expected_marks)` · N7 `return_(…, tra_lai, who, user)` | Chỉ EP |
| Nút | N8 `reset(…, confirm=False)` → `preview`; N9 `rerender` (nền); N10 `score`; N11 `render_plates` | |
| S-C | `require_plate(…, user)` · `allow_exception(…, why, who, user)` | Chỉ EP |

**`scene_status` trả về:**
- `phase`, `label`, `k1`;
- `inputs_changed` / `inputs_known`;
- `approved_by`, `cams`, `cams_this_stage`, `bad`, `round`;
- `sheet` (`doan_<S>/beats/san_khau_canh<S>.png`);
- `drawn`, `revs`, `marks`;
- `lock` (có `stale` khi khóa cũ), `progress`, `running`, `user_approves`;
- `buttons` (nút hợp phase; lõi vẫn kiểm lại khi bấm);
- `reset`.

**Mọi nút trả `{"ok", "errors": [câu]}`.** Ngoài ra:
- `needs_confirm`: shot đã vẽ ảnh (N6, N9), hoặc N8 chưa xác nhận;
- `stale`: máy đổi xen giữa (N6).

**UI phải làm:**
1. Truyền `user = common.access_user()`. Tham số này BẮT BUỘC; `None` chỉ khi đăng nhập TẮT.
2. Truyền `who = write_guard.actor("human", email)`.
3. Giữ `scene_status()["marks"]` lúc MỞ màn duyệt, rồi đưa lại vào `approve(expected_marks=…)`.
4. Chạy N1 trước khi K1 chưa có (`k1` False). Lý do: N3 / N6 / N7 / N10 chạy đồng bộ và có thể đo K1 (Blender khoảng 20 s).

## Đã làm

### `core/stage_desk.py` (mới)
**Trạng thái**
- Đọc thuần `crew/state.json`, `result.json` và `scenes.data`.
- Vân tay đầu vào chỉ tính khi đã có K1 trong cache (`stage_auto.k1_cached` mới, không chạy Blender) và đã có lượt chia vai.

**Khóa S** (`doan_<S>/.desk.lock`, nội dung `{pid, token, owner, action, since}`)
- Tạo bằng `O_EXCL`.
- Nút chạy nền giữ khóa NGAY ở luồng gọi, nên không có khe giữa lúc kiểm và lúc giữ. Luồng nền nhả khóa khi xong.
- Chỉ xóa khóa khi mã thẻ là của mình, và thử xóa lại vài lần (Windows).
- Khóa cũ thì gỡ và báo ⚙ Chẩn đoán. Khóa cũ gồm:
  - tiến trình đã chết;
  - luồng của chính Dashboard đã dừng (thẻ không còn);
  - tệp khóa hỏng hoặc rỗng quá 60 s;
  - quá 3 giờ.

**Luồng nền**
- Mỗi dự án một luồng.
- Mở kết nối sqlite riêng; CSDL `:memory:` thì từ chối.
- Tiến độ ghi ra `desk_progress.json`: bước, ≤ 50 dòng log, `done` / `error` kèm câu.
- Tiến trình tắt giữa chừng → `interrupted` "tác vụ bị ngắt lúc …".

**Nút N1–N11 trừ N13** gọi đúng hàm có sẵn trong `stage_auto` theo bảng mục 4 kế hoạch. N5 dựng giống `--beats` nhưng ghi vào thư mục đoạn.

### `core/stage_auto.py`
- `apply(…, who=None, expected_revs=None)`:
  - mỗi shot đổi đi qua `write_guard.write_scene` (SHADOW) TRƯỚC lệnh UPDATE như cũ;
  - sau commit gọi `write_guard.flush`, để dòng của shot 2, 3… không mất;
  - `who=None` → giống byte cũ.
- `who` được truyền qua `rerender` / `crew_answer` / `_crew_finalize` / `crew_user_verdict` / `run`.
- `run(…, manual=False, who=None)`: `manual=True` chạy được khi cờ `stage_auto` TẮT mà KHÔNG đặt `os.environ`. Cờ REQUIRES vẫn phải bật.
- `k1_cached(seg, base)` (mới).

### `core/autopilot.py` `_stage_phase`
- GIỮ khóa S mọi đoạn trong lúc chạy (`hold_segments`), nên nút gặp autopilot cũng từ chối có câu.
- Gặp khóa của người khác → `_Wait("plates", …)` có câu.
- Ghi máy với `actor("auto", "autopilot.stage")`.

### `tools/stage_auto.py`
- Các nhánh ghi giữ khóa S. Gặp khóa → in "⛔ đang thao tác …" và kết quả `warn`.
- Nhả khóa ở mọi nhánh `return` (`_main` → `_run` trong `try / finally`).

### `core/batch.py` `image_gates`
Nối cổng S-C cho nút Gen ảnh và `tools/pregen_check`:
- `hold` → **chặn**;
- `warn` → VÀNG;
- dự án không có thư mục `stage/` → không đọc gì.

## Sổ quyết định (S-A…S-G)

| | Làm thế nào | Check |
|---|---|---|
| S-A | Phương án A: lõi cho hàng nút trong màn XEM (UI = C-M48-DESK-UI) | — |
| S-B | Duyệt / Trả lại / đặt plate bắt buộc / ngoại lệ: chỉ NGƯỜI và là EP. EP = Owner hoặc chủ dự án (`access.level` own / admin); đăng nhập TẮT = chủ máy. Actor phải trùng email đăng nhập. N4 không nhận lượt duyệt | `check_stage_desk_ep_only` |
| S-C | Mặc định VÀNG khi sân khấu chưa chốt. Shot EP đánh dấu bắt buộc chỉ qua khi đủ: EP duyệt (`approved_by` `nguoi_dung`; Đạo diễn tự chốt hoặc đường không chia vai thì không tính), có máy từ sân khấu đó, nền 3D render xong và không cũ. Thiếu một điều và chưa có ngoại lệ (EP, có lý do) → HOLD. Đã nối vào nút Gen ảnh | `check_stage_desk_paid_gate` |
| S-D | Làm lại = `confirm=False` chỉ XEM TRƯỚC (máy giữ, nền / ảnh / world map sẽ cũ). Xác nhận → cất `crew/` + ghi `desk_reset.json` đánh dấu phụ thuộc; dấu này được xóa ở lượt duyệt mới | `check_stage_desk_reset_confirm` |
| S-E | Không có nút API (Đợt 3) | — |
| S-F | Không có N12 Previs | — |
| S-G | N7 nhận câu ý đồ; Quay phim chọn số đo (`crew_answer` có sẵn) | — |

`enforced_by` của mục sổ đã thêm 3 check. `py -m core.decisions check` xanh.

## ⚠️ Câu hỏi và việc tiếp (cho phiên chính / EP)
1. **EP = chủ dự án (người tạo, kể cả member) + Owner + đăng nhập TẮT.** "Chỉ EP" có cần hẹp hơn, chỉ Owner? Hiện phiên Claude bấm qua Dashboard local (đăng nhập TẮT) cũng là EP. Ở tầng lõi không phân biệt được, chỉ UI ẩn được (Q-B kế hoạch).
2. **S-C chưa nối:** gen VIDEO trả phí, và autopilot `_director_phase` (autopilot có cổng ảnh riêng, không qua `image_gates`). Cần việc riêng.
3. **CLI ghi chưa có `who`:** `--crew-approve` / `run` CLI chưa qua write guard (khác N6). Đề xuất `actor("tool", "cli.stage_auto")`.
4. **`runner.py:2925 / 2933`** vẫn đòi `stage_auto.enabled()` mới dùng `guide`. Nút chạy tay khi cờ tắt không đổi điều này.
5. **Test 14 (ca thật #31 cảnh 3)** = máy chính, ghi số giây từng nút.

## Rà soát (quy tắc 7) — 1 lượt agent, đã sửa hết CAO / VỪA

| Mức | Lỗi | Sửa |
|---|---|---|
| CAO | Dòng shadow write guard của shot 2, 3… mất (giữ trong giao dịch, không flush) | `_flush` sau commit trong `apply`; test stale shot 2 + 3 và rerender nền 3 shot |
| CAO | Khóa S một chiều: autopilot / CLI chỉ hỏi, không giữ; khe giữa kiểm và giữ ở `_start` | `hold_segments` ở autopilot + CLI; `_start` giữ ở luồng gọi |
| VỪA | S-B mặc định mở (`user=None` = admin); `who` / `user` không đối chiếu | `user` bắt buộc; actor phải trùng email |
| VỪA | `expected_rev` không bắt được ghi xen giữa (SHADOW không tăng `_rev`) | `marks` + `approve(expected_marks)` từ chối |
| VỪA | `paid_gate` mở sớm (vừa duyệt mà nền chưa render) / Đạo diễn tự chốt tính là duyệt; chưa nối | Ba điều kiện + `approved_by` `nguoi_dung`; nối `image_gates` |
| VỪA | Khóa của chính Dashboard kẹt 3 giờ; khóa rỗng kẹt mãi; nhả xóa khóa người khác | Thẻ theo luồng, khóa hỏng 60 s, chỉ nhả khóa của mình |
| VỪA | `status()` gỡ khóa + ghi diag khi vẽ; `inputs_for` mỗi lần vẽ | `clean=False`; vân tay chỉ khi có lượt chia vai |
| THẤP | `desk_gate.json` đọc-sửa-ghi không khóa; `desk_reset.json` không xóa; docstring nói `run` | Khóa trong tiến trình; xóa khi duyệt; sửa docstring |
| — | `world_map` import vào đường gen (luật G2-4, test `dp8`) | Không import, tự dựng đường tệp |

**Ghi nhận, không sửa:**
- Nút đồng bộ có thể đo K1 (UI chạy N1 trước).
- Khi `field_guard` bật, autopilot ghi máy tự động khác giá trị cũ sinh `field_review` (đúng luật).
- `check_*` của sổ khớp chuỗi mã nguồn (theo lệ).

## Test
- `tests/test_v31_m48_desk_core.py`: **51 xanh**, theo mục 10 kế hoạch:
  - 1 / 8: không `os.environ` FEATURE_ ở `dashboard/` và `stage_desk`; `run(manual)` khi cờ tắt.
  - 2: nút theo phase / đầu vào đổi / cờ duyệt tắt / trạng thái không Blender.
  - 3: S-B, khóa tay giữ, shot đã vẽ cần xác nhận, shot hỏng → máy thường.
  - 4: trả lại thiếu ý đồ / 3 lần / CSDL không đổi.
  - 5: JSON sai, phase `duyet`, đo lỗi → state giữ.
  - 6: mọi nút trước duyệt không đổi CSDL, gồm N11 / N2.
  - 7: một luồng / autopilot chờ / khóa chết, hỏng, mồ côi / CLI từ chối / nút gặp autopilot / không xóa khóa người khác.
  - 9: guard bật / tắt, stale shot ≥ 2, nền.
  - 10: tiến độ / lỗi có câu / bị ngắt / `:memory:`.
  - 12: tấm ghép đúng thư mục với cwd khác.
  - 13: CLI `--crew-approve` ≡ N6.
  - S-C, S-D.
- 13 test sửa theo rà ĐỎ trên commit trước sửa (`fd0a8dbd`).
- Test liên quan (`stage_auto`, `stage_crew`, `stage_view`, `decisions`, `autopilot`, `write_guard`, `world_map`, `devsys` maps): xanh.
- `tests/test_devsys_pipeline_maps.py`: số đếm `step.update(result="warn")` của CLI 4 → 5 (nhánh khóa S mới).
- Full suite (cloud 3.13, `-m "not slow" -n auto`): **7418 passed, 0 đỏ** (nhánh nền tích hợp M2 không còn 25 đỏ golden nền).
