# Đánh giá M6 — điều phối và làm việc giữa các vai (22/10/2026)

> **Cấp 1 — CHỈ ĐỌC, 0 USD.** Theo yêu cầu Executive Producer (EP). Không sửa code, không commit.
> **Đối chiếu:**
> - `origin/main` @ `12735052`.
> - Kế hoạch `docs/KE_HOACH_TO_LAM_PHIM_CO_CHU_2026-10-21.md` và M6/M7/M8 trong `docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md`.
> - Audit `docs/V3_1_M6_0_AUDIT_VAI_2026-10-21.md`.
> - Sổ quyết định: `v31-m6-*`, `v31-ep-*-2026-10-21`.
> - Memory `feedback_crew_owns_fixes_claude_code_only`.
> - Code trên các nhánh:
>   - `origin/cloud/v31-m63` (`core/gen_auth.py`);
>   - `origin/cloud/v31-m61-m69` (`data/crew_roles.json`, `core/crew.py`, `core/continuity_validator.py`);
>   - `origin/cloud/v31-m2-tichhop` (`core/write_guard.py`);
>   - `origin/cloud/v31-m210` (kế hoạch gói gửi tối giản);
>   - `docs/KE_HOACH_DASHBOARD_DON_GIAN_2026-10-21.md` (M8.1).

## 0. Kết luận ngắn

1. **Trên giấy thì mô hình vai gần khép kín, trong vận hành thì chưa.** Cụ thể:
   - Role Registry có 11 vai. Mỗi khâu L1–L16 có đúng một vai chủ, mỗi trường trong bảng 44 trường cũng có đúng một vai chủ (`py -m core.crew check` = 0 lỗi).
   - Nhưng 3 thứ còn **là nhãn, chưa phải người làm**:
     - **Chưa có "bàn nhận phiếu":** phiếu chỉ ghi `status=returned, shadow` trong jsonl, không vai nào đọc.
     - **Chưa có Handoff M6.2.**
     - **Chưa có actor = vai** ở bất kỳ đường ghi hay gửi job nào.
   - Hiện nay việc "vai" làm thực ra vẫn do autopilot, vòng QC tự gen lại (J17) và phiên Claude Code làm.
2. **Bàn giao có chỗ có thể lặp mãi hoặc chờ nhau:**
   - Có 2 vòng không có bộ đếm lượt trả về:
     - VPA → Director/Storyboard ("mâu thuẫn đầu vào");
     - Continuity → vai chủ.
   - Director vừa là trọng tài vừa là chủ BYĐ, nên khi tranh chấp xoay quanh BYĐ thì thiếu người phá thế bế tắc độc lập.
   - "Stale" chưa có nguồn revision thật: `_rev` của write guard chỉ tăng khi NGƯỜI khóa trường.
3. **Ba định nghĩa "dữ liệu khóa" và năm bộ đếm lượt đang song song**, và chúng sẽ cho kết quả trái nhau:
   - Các định nghĩa "khóa": `gen_auth.LOCKED_KEYS`, `write_guard.REVIEW_FIELDS/DERIVED`, bảng `fields` của registry.
   - Các bộ đếm lượt: `gen_auth`, `AUTO_REGEN_LIMIT`+`retry_count`, `repair_router`, `quality_tier.RETRY_LIMIT`, `pilot_run shot_sends`.
4. **Code M6-A đúng phạm vi shadow** (cờ TẮT, 0 ghi CSDL, có test), nhưng chưa nối được với nhau:
   - `gen_auth` không đọc registry, không có `actor_role`.
   - Continuity Validator định tuyến theo **khâu phát hiện**, không theo **khâu gây lỗi**.
   - Write guard không biết vai.
5. Có **6 câu cần EP quyết** (mục 6). Trong đó 2 câu chặn thiết kế M6-B:
   - (E1) ai sở hữu prompt khi có builder tối giản M2.10;
   - (E2) chế độ Đơn giản M8 tự khóa / tự duyệt thay EP hay không.

---

## 1. Sơ đồ luồng vai + bàn giao (như THIẾT KẾ, kèm chỗ hở `!!`)

```
                         ┌──────────────────────── EXECUTIVE PRODUCER (người dùng) ────────────────────────┐
                         │ duyệt: ngân sách · cấp lượt · dữ liệu khóa · sân khấu 3D (S-B) · sản phẩm cuối     │
                         │ kênh: 📥 inbox (core/inbox.py)  !! gen_auth / CV chưa đẩy gì vào inbox            │
                         └───────▲─────────────▲───────────────▲───────────────▲───────────────────────────────┘
               needs_ep (lượt/USD/khóa)  │   stage approve │  final approve │  "đạo diễn ngoại tuyến" --crew-approve
                                 │             │               │               │   !! chưa có sổ quyết định EP (chỉ phiên chính trả lời)
                         ┌───────┴─────────────┴───────────────┴───┐
                         │ DIRECTOR — phân công, trọng tài, BYĐ v2   │◄──── conflict_between_roles (CV)
                         │ !! vừa là bên tranh chấp (chủ BYĐ) vừa xử │◄──── input_conflict / attempts_exhausted (mọi vai)
                         └──┬──────┬───────┬──────┬──────┬──────┬────┘
     BYĐ/ý đồ ──────────────┘      │       │      │      │      │
   ┌──────────────┐  ┌─────────────▼┐ ┌────▼─────┐│ ┌────▼────┐ ┌▼──────────┐ ┌──────────────┐
   │ Scriptwriter │→ │Cinematographer│→│ 3D Artist ││ │ Sound   │ │ Editor/VFX│ │ Kỹ sư (code) │
   │ L1, L4       │  │ !! KHÔNG khâu │ │ L6        ││ │ L14a-c  │ │ L14d,L15  │ │ categories   │
   └──────────────┘  └──────┬───────┘ └────┬─────┘│ └─────────┘ └───────────┘ └──────▲───────┘
                            │ camera        │ plate│                                     │ lỗi hệ thống (hop_thu)
                            ▼               ▼      ▼                                     │ !! hộp thư phiên dev,
                     ┌────────────────────────────────┐   ảnh khung đầu  ┌──────────────┴──┐  không phải hàng đợi SX
                     │ STORYBOARD ARTIST  L7–L10       │ ───────────────► │ VIDEO PROMPT    │
                     │ image_prompt, layout, end_frame │ ◄─ trả phiếu ─── │ ARTIST L11–L13  │
                     └───────────────┬────────────────┘  "ảnh ≠ BYĐ"     └───────┬─────────┘
                                     │ job ảnh                                   │ job video
                                     ▼                                           ▼
             ┌──────────────── GENERATION AUTHORIZATION (gen_auth, trước provider.submit) ────────────────┐
             │ ảnh ≤3 · video ≤2 · 40 % tự sửa · 3 shot cùng mã · chưa rõ · trùng · khóa · model            │
             │ !! không biết actor_role; CLI ghi origin='user' → né ngân sách; end_frames/mẫu 4s/lipsync ngoài │
             └───────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                             ▼ ảnh / clip mới
             ┌──────────── CONTINUITY VALIDATOR (năng lực kiểm, chỉ ghi bằng chứng) ────────────┐
             │ continuity_state + qc_evidence + M4.2/M4.3 → owner_of_error → phiếu "returned"   │
             │ !! định tuyến theo KHÂU PHÁT HIỆN (L13 → VPA) chứ không theo nguồn gây lỗi        │
             │ !! QC thật (apply_qc → reject → _spawn_retry J17) vẫn TỰ sinh lượt gen, ngoài vai │
             └───────────────────────────── phiếu ──► (không ai nhận: M6.2 chưa có) ─────────────┘
```

**Vòng bàn giao chính (thiết kế):** Scriptwriter → Director (BYĐ) → Cinematographer (máy) → 3D Artist (plate, **EP duyệt sân khấu**) → Storyboard
(ảnh) → VPA (prompt video) → gen_auth → provider → Continuity/QC → (đạt: Director đề xuất, EP duyệt) / (không đạt: phiếu về vai chủ) → Sound → Editor
→ EP duyệt cuối.

---

## 2. Bảng khâu × vai (L1–L16 theo `devsys/stages.json` + `data/crew_roles.json` nhánh M6.1)

| Khâu | Tên | Vai chủ (registry) | Đầu vào chính | Đầu ra | Ai nghiệm thu (độc lập) | Ai được sửa | Leo thang | Vấn đề |
|---|---|---|---|---|---|---|---|---|
| L1 | Ý tưởng → kịch bản | Scriptwriter | ý tưởng EP, chat | `script_text`, `text` | EP (duyệt kịch bản) | Scriptwriter; EP | Director → EP | ổn |
| L2 | Bảng kê tài nguyên | Director | kịch bản, Kho | danh sách thiếu Kho | — (không có kiểm sau) | Director | EP | **Kho không có vai**: thiếu ảnh thì không ai đi lấy (W23–W30 gán tạm EP) |
| L3 | Chia shot, image_prompt / blocking / action | Director | kịch bản, Bible | shot, BYĐ, **image_prompt**, **blocking** | — | Director | EP | **Lệch chủ:** `image_prompt` thuộc Storyboard, `blocking` thuộc Cinematographer, nhưng khâu L3 thuộc Director, và một lượt `director` ghi trường của 3 vai (W2) |
| L4 | Thoại, chọn giọng | Scriptwriter | thoại | thoại, **giọng** | — | Scriptwriter | Director | **Lệch chủ:** chọn giọng (`characters.voice_profile`) thuộc Sound |
| L5 | Hồ sơ nhân vật / Lock / Bible / ảnh Kho | Director | Kho | Lock, Bible | — (kiểm trước/sau: không có) | Director; khóa = EP | EP | **Không có kiểm độc lập**; Kho không vai; autopilot/MCP khóa Bible thay EP (W5) |
| L6 | Sân khấu 3D: dàn cảnh + **giải máy** + render nền | 3D Artist | BYĐ, camera, Kho | `stage_camera`, plate | **EP (S-B)** — registry chưa có | 3D Artist | Director → EP | **Lệch:**<br>- Cinematographer (đặt máy theo `stage-crew-plan`, S-G) không có khâu nào, nên lỗi máy ở L6 về tay 3D Artist.<br>- Registry chưa ghi "chỉ EP duyệt sân khấu" |
| L7 | Storyboard / ảnh neo | Storyboard | BYĐ, plate, Kho | ảnh neo | QC `d22` | Storyboard | Director | ổn |
| L8 | Lắp gói gửi ảnh | Storyboard | prompt + ref | gói | **không có** | (code) | — | **M2.10:** builder tối giản do CODE chọn ref + viết thân lệnh, nên vai chỉ còn trên danh nghĩa (mục 4d) |
| L9 | Gen ảnh khung đầu | Storyboard | gói | ảnh | QC (`scene_qc`, `qc_team` học việc) | Storyboard | Director → EP | QC thật vẫn tự gen lại (J17) |
| L10 | Gen lại ảnh (Đạo diễn viết lại prompt) | Storyboard | lý do loại | prompt mới | — | **`director_rewrite` gán VPA** | Director | **Lệch:** `director_rewrite` ghi cả `image_prompt` (Storyboard) và motion (VPA) nhưng registry gán claude_stage cho VPA |
| L11 | Motion prompt + dịch | VPA | BYĐ, ảnh đã duyệt | `motion_prompt` | lint (code) | VPA | Director | duyệt motion (`motion_prompts.state`) thuộc Director, nhưng autopilot / MCP / CLI đang tự duyệt (W4) |
| L12 | Lắp gói video | VPA | motion + khung + ref + model | gói | không có | (code) | — | ai chọn ref video? `package_overrides` (W19) gán 2 vai; trường "bộ ref" không có trong `fields` |
| L13 | Gen video (nháp → cao) | VPA | gói | clip | QC video (d42–d47) | VPA | Director → EP | **Mọi lỗi phát hiện ở clip đều đổ về VPA** (cả lỗi gốc ở ảnh / BYĐ / máy) |
| L14a | TTS | Sound | thoại | giọng | `d39` | Sound | Director | `fit_durations` ghi `duration_s` (chủ Director) — hai vai cùng ghi (W13) |
| L14b | Nhạc | Sound | brief | nhạc | — | Sound | Director | không kiểm |
| L14c | SFX | Sound | sfx_plan | sfx | — | Sound | Director | không kiểm |
| L14d | Phụ đề | Editor | thoại | phụ đề | — | Editor | Director | ổn |
| L15a | Dựng, xuất bản | Editor | clip đã duyệt | bản dựng | `d48/d49` (cờ tắt) | Editor | EP | dựng / VFX kiểu #27 chưa thành nút (M6.8) |
| L15b | Popup cuối | Editor | — | popup | — | Editor | Director | ổn |
| L16 | Thay đổi giữa chừng | Director | change_events | phiếu stale | `change_review` (claude_stage gán Continuity) | Director | EP | stale chưa có revision thật (mục 3a) |

**Đếm:** 19 khâu (gồm a/b/c/d). Có 9 khâu ổn hoặc chỉ lệch nhỏ, 10 khâu lệch hoặc hở:

| Loại vấn đề | Khâu |
|---|---|
| Lệch chủ | L3, L4, L6, L10, L13 |
| Không có kiểm độc lập | L2, L5, L8, L12 |
| Thiếu vai | Kho (rải ở L2, L5) |

### 2a. Trường hai vai cùng ghi, hoặc trường chưa có chủ

| Trường | Chủ registry | Ai khác đang ghi | Ghi chú |
|---|---|---|---|
| `scenes.data.duration_s`, `motion_prompts.duration_sec` | Director | Sound (`voice.fit_durations`, `audio_first.fit_shots`), máy (`dialogue.extend`) | cần quy ước: Sound đề xuất, Director chấp nhận |
| `layout`, `layout_people` | Storyboard | Cinematographer (W9 `also`) | write guard xếp vào **DERIVED** (ghi tự do), mâu thuẫn với "có chủ" |
| `stage_segment`, `plate_setup`, `spatial_state` | 3D / Cinematographer / (không) | máy | write guard xếp DERIVED; registry nói có chủ |
| `stage_camera` | 3D Artist | Cinematographer (`stage_crew`: Quay phim đặt máy), phiên Claude Code (K1) | S-B: chỉ EP duyệt |
| `video_route`, model / độ phân giải (`model_router`) | Director (W10/W11) | runner tự đổi khi bị từ chối | **model / độ phân giải không có trong `fields`** |
| bộ ảnh tham chiếu gửi kèm (`package_overrides`, `sent_package.refs`) | **không có trong `fields`** | EP, code builder, (M2.10 lean) | chính là việc M2.10 đang đổi |
| `scenes.data.lip_sync`, `end_frames.*` ngoài `prompt`, nhạc đã chọn, popup | không có | Sound / Editor / máy | thêm vào `fields` |
| `jobs.state` (duyệt ảnh / clip) | EP (W36) | QC `ai_agent` reject, CLI `"user"` (K3) | "Director duyệt clip trong trần" chưa có trường hay trạng thái nào |

---

## 3. Bàn giao giữa vai — stale, lặp vô hạn, chờ nhau

### 3a. Handoff Contract có đủ để vai sau biết dữ liệu trước đã đổi không? — **Chưa**
- Thiết kế nói revision lấy từ write guard M2.5. Nhưng trên `cloud/v31-m2-tichhop`:
  - `_rev` **chỉ tăng trong `write_guard.lock`** (người sửa tay);
  - mọi lần ghi của AI / máy không tăng `_rev`;
  - chế độ enforce (CAS theo `_rev`) chưa làm (`NotImplementedError`).

  Vì vậy `revision.scene_rev` của handoff sẽ đứng yên khi Director đổi BYĐ.
- `depends_on` dùng khóa `lineage` (input_hash). Đây là nguồn stale tốt nhất hiện có, nhưng `lineage.summary` #31 mất 7,6–11,3 s (E5) và M6.11 đã hoãn (Q5). Hệ quả: kiểm stale cho mỗi lần bàn giao sẽ rất đắt.
- Có **hai cơ chế stale song song**:
  - `change_review` (L16, 648 lượt Claude / #31);
  - handoff `depends_on`.

  Kế hoạch mục 9 muốn change_review chỉ chạy khi có handoff, nhưng chưa ghi rõ cái nào là nguồn duy nhất.
- **Đề xuất:**
  - revision = số đếm tăng ở MỌI lần ghi `scenes.data` qua guard. Guard đã thấy mọi đường ghi trong shadow, nên chỉ cần thêm bước tăng `_rev_field[field]`. Đây là Cấp 2, M2.5.
  - handoff ghi `fields_rev` của đúng các trường vai sau đọc (`reads[]` trong registry).
  - vai sau so `reads[]` với `fields_rev` hiện tại; khác nhau nghĩa là stale. Không cần tính lineage toàn dự án.

### 3b. Vòng có thể lặp mãi / chờ nhau

| # | Vòng | Vì sao có thể không dừng | Chặn hiện có | Thiếu |
|---|---|---|---|---|
| D1 | VPA ↔ Storyboard ↔ Director: "ảnh quỳ, BYĐ ghi đứng" | VPA trả phiếu về "vai chủ dữ liệu". Storyboard nói "ảnh đúng plate", Director nói "BYĐ đúng", phiếu bật qua lại. Mỗi lượt trả về không tốn lượt gen nên **gen_auth không bao giờ chặn** | không | **bộ đếm lượt trả về theo (shot, cặp vai)**: ≥ 2 lần thì lên EP |
| D2 | Director là trọng tài nhưng cũng là chủ BYĐ | tranh chấp về chính BYĐ thì Director tự phân xử cho mình | `stage-crew-plan` (Quay phim ↔ Đạo diễn: Đạo diễn thắng) | quy tắc: tranh chấp về trường của Director thì EP là trọng tài; Continuity cấp bằng chứng |
| D3 | Continuity → VPA → gen lại → Continuity | lỗi gốc ở ảnh hoặc máy, nhưng phiếu về VPA (L13). VPA gen lại 1 lần thì hết lượt video 2/2, rồi lên EP. **Tốn 1 clip mà không thể sửa được** | trần 2 video | định tuyến theo **nguồn gây lỗi** (mục 4c) + `repair_router` kiểm "input_delta thuộc vai nào" trước khi cho gen |
| D4 | Tự sửa → LOCKED_CHANGE → EP | `gen_auth.LOCKED_KEYS` gồm `blocking`, `layout`, `duration_s`. Đó là trường làm việc của Cinematographer / Storyboard / Director, không phải "ý đồ khóa". Mọi lần sửa trong quyền của vai đó đều bị đẩy lên EP | — | dùng **một** định nghĩa khóa: `write_guard.state()` (USER_LOCKED) + BYĐ đã duyệt; bỏ danh sách riêng |
| D5 | Director đổi BYĐ → stale ảnh → Storyboard gen lại → stale motion → VPA … | chuỗi đổi lan dần. Mỗi bước hợp lệ, nhưng tổng lượt ảnh đã dùng (3/3) không trả lại | trần lượt (đúng chính sách) | Director phải xem **dự báo lan truyền** (shot nào stale, còn bao nhiêu lượt) trước khi đổi BYĐ (S-D đã chốt cho sân khấu; nên áp cho BYĐ) |
| D6 | 3 shot cùng mã lỗi → "dừng + phiếu" | `cause` = `reject_reason` (câu tự do của C2). Hai câu hiếm khi giống hệt nhau nên điều kiện **gần như không bao giờ kích hoạt**. Kể cả khi kích hoạt, chưa có ai nhận phiếu | shadow ghi jsonl | chuẩn hóa `cause` về mã `qc_evidence.CODES` / `devsys/errors.json`; phiếu gửi Director **và** Kỹ sư |
| D7 | Hết lượt → EP, EP chưa trả lời | shot đứng yên, autopilot có thể chờ mãi | 📥 inbox có sẵn | gen_auth / CV chưa đẩy vào inbox; cần trạng thái "chờ EP" + nhắc + cho autopilot làm shot khác |
| D8 | Kỹ sư ↔ vai: lỗi hệ thống qua `tools/hop_thu.py` | hộp thư là kênh giữa các **phiên dev**. Đẩy lỗi sản xuất vào đó sẽ làm ngập, và không có SLA | shadow: chưa đăng | kênh riêng `devsys/errors.json` + diag, hộp thư chỉ nhận bản gom theo ngày |

**Ai phá thế bế tắc (đề xuất ghi vào registry `escalate`):**
- Giữa hai vai chuyên trách: **Director**.
- Tranh chấp liên quan tới trường của Director (BYĐ / route / duration): **EP**, có bằng chứng của Continuity.
- Lượt trả về theo (shot, cặp vai) ≥ 2, hoặc chờ EP quá N giờ: tự lên EP và autopilot bỏ qua shot đó.

---

## 4. Khớp với quyết định EP 21/10 và việc mới

### 4a. Trần lượt / ngân sách 40 % / 3 shot cùng lỗi (`v31-m6-generation-limits-policy-b`, `v31-ep-m6-self-repair-budget-40`)

| Điều | `gen_auth` (shadow) | Khớp? |
|---|---|---|
| ảnh ≤ 3, video ≤ 2, tổng, không đặt lại | `attempts()` theo (scene, type), không dùng `retry_count` | ✔ |
| Q1 nâng 1080p không tính | `is_upgrade` theo `sent_package.call` | ✔ |
| Q2 EP bấm có trừ lượt | ✔ trừ lượt. Hết lượt thì `needs_ep`; ngân sách chỉ áp cho `origin='auto'` | ✔ |
| Q4 lùi model trong danh sách | `approved_models`, tạm thời. Chính rà M63 thừa nhận "gần như luôn đạt" | ⚠ cần danh sách model đã duyệt theo dự án |
| 40 % tiền lượt đầu, EP đổi theo dự án | `app_settings gen_auth_repair_pct:<pid>` | ✔ (chưa có ô Dashboard) |
| "không vượt tổng ngân sách dự án" | **không kiểm**: chỉ kiểm 40 %, không so `project_budget` / `spend_gate` | ✖ |
| 3 shot liên tiếp cùng mã → dừng + phiếu | mã = câu tự do; không tạo phiếu | ✖ (D6) |
| không tự gửi lại job submit chưa rõ | `PROVIDER_UNVERIFIED` | ✔ |
| tính chung **mọi đường gọi** | end_frames (ảnh khung cuối), quality_samples (video 4 s), experiments, lipsync **không qua** gen_auth | ✖ cần EP quyết (E4) |
| không cho Kỹ sư né | `tools/redraw_compare.py`, `pilot_run.py` ghi `origin='user'`, nên được coi là EP bấm và né ngân sách tự sửa | ✖ (check Q3 của audit, đang ĐỎ) |
| một cách đếm | còn 4 cách khác chạy song song: `AUTO_REGEN_LIMIT` + `retry_count` (pipeline), `repair_router.plan` (`retry_count`, `REPAIR_SAME_CODE_TWICE`), `quality_tier.RETRY_LIMIT`, `pilot_run shot_sends` | ✖ khi M6-B bật chặn thì phải thay, không được cộng thêm |

### 4b. S-B: chỉ EP duyệt sân khấu; S-G: Cinematographer chọn dữ liệu đo máy
- Registry: `artist_3d.writes` có `stage_camera`, nhưng không có bước "EP duyệt". `acceptance` không nhắc tới EP. `escalate.executive_producer` không có lý do `stage_approval`.
- Cinematographer **không có khâu nào**: L6 (giải máy) thuộc 3D Artist. Điều này trái với S-G và `stage-crew-plan` (Quay phim đặt máy, tự sửa theo bảng số đo).
- **Đề xuất:**
  - tách L6 thành L6a dàn cảnh / plate (3D Artist) và L6b đặt máy (Cinematographer), hoặc gán L6 cho Cinematographer kèm `codes` máy;
  - thêm trường trạng thái `stage_approved_by` thuộc EP;
  - 3D Artist chỉ ghi `stage_camera` ở trạng thái đề xuất (REVIEW_REQUIRED). Write guard đã có `stage_camera` trong REVIEW_FIELDS.

### 4c. "Đạo diễn ngoại tuyến" = vai hợp lệ
- Câu trả lời "VAI chạy ngoại tuyến HỢP LỆ, với 4 điều kiện" nằm ở `hop_thu/su_kien/20261021-202220-phien-chinh-pjb5.json`. Đây là **lời của phiên chính, không phải mục trong `data/decisions.json`**.
- Registry K1 vẫn ghi "chờ EP quyết (Q8)". Code vẫn để `--source` mặc định `claude_code` (`tools/stage_auto.py:34`, `core/stage_auto.py:1016/1263`). Cả 4 điều kiện **chưa có cơ chế nào ép**:
  1. source = tên vai;
  2. không sửa code cùng lượt;
  3. EP duyệt cuối;
  4. có sự kiện `cli_step`.
- Mặt tốt: đây là vai **có công cụ thật duy nhất** hiện nay (bàn đạo diễn ngoại tuyến + Blender). Nó nên là **khuôn mẫu "vai chạy ngoài Dashboard"** cho các vai khác.
- **Cần EP xác nhận (E3)** để ghi vào sổ. Sau đó:
  - đổi mặc định `--source` thành tên vai;
  - check Q8 đỏ khi actor = `claude_code` mà không kèm vai.

### 4d. M2.10 gói gửi tối giản (`v31-ep-m210-lean-package`)
- Kế hoạch M2.10 (nhánh `cloud/v31-m210`) cho **code** làm phần lớn việc:
  - chọn bộ ref tối thiểu theo loại shot;
  - bỏ ref thừa / trùng;
  - viết "dòng vai" mỗi ref;
  - áp "thân lệnh 2–4 câu".

  Điều này chạm vào ba nguyên tắc M6:
  - VPA/SBA quyết cách diễn đạt prompt;
  - "code chỉ đóng gói + kiểm payload, không âm thầm sửa nội dung";
  - Storyboard Artist chủ "chọn ảnh ref gửi kèm" (bảng 2a).
- Tài liệu M2.10 **không nhắc vai nào, cũng không nhắc USER_LOCKED** (prompt người sửa tay `v31-ep-motion-prompt-user-locked`).
- **Đề xuất:**
  - lean builder = **công cụ của VPA/SBA**. Nó đưa ra *đề xuất* bộ ref + khung prompt; vai (hoặc EP) chấp nhận; mỗi ref bị bỏ có mã (M2.10 đã có);
  - prompt hoặc bộ ref USER_LOCKED thì builder không đổi, chỉ ghi diff đề xuất;
  - thêm `scenes.data.ref_set` (hoặc `package_overrides`) vào `fields`, chủ là SBA (ảnh) / VPA (video). **EP chốt (E1).**

### 4e. M8.1 chế độ Đơn giản (`docs/KE_HOACH_DASHBOARD_DON_GIAN_2026-10-21.md`, chưa duyệt)
- Thiết kế đúng hướng M6:
  - người không chuyên chỉ thấy 4 cổng duyệt + "góp ý bằng lời → Đạo diễn sửa";
  - lỗi được dịch thành "Máy đang sửa X / Cần bạn: …".
- Nhưng có 5 chỗ chạm quyền M6:
  1. "Director chia shot + Bible, **tự khóa**": khóa Bible là quyền EP (`characters.locked`, W5 đang bị đánh dấu sai).
  2. "Viết + **duyệt motion tự động**": `motion_prompts.state` thuộc Director, W4 đang sai.
  3. "Sân khấu 3D … **ẨN + TỰ ĐỘNG**": S-B bắt buộc EP duyệt sân khấu, và chế độ Đơn giản không có ô nào cho việc đó.
  4. "ảnh trượt tự vẽ lại trong trần M6": hiện là QC tự sinh job (J17). M6 nói Continuity chỉ ghi bằng chứng; quyền gen lại thuộc vai chủ + gen_auth.
  5. "góp ý bằng lời → Đạo diễn phân vai" cần **bộ định tuyến yêu cầu ngôn ngữ tự nhiên** (M6.10). Bộ này chưa có trong M6-A/B, nên M8.6 phụ thuộc M6.10 chứ không chỉ M6-B.
- **Chữ "vai" bị dùng cho hai nghĩa:** vai tài khoản (`auth/access`: "người làm phim", quản trị) và vai tổ làm phim (registry). Đề xuất gọi vai tài khoản là "quyền tài khoản".
- **Cần EP quyết (E2):** ở chế độ Đơn giản, "✔ Được, làm tiếp" / "✔ Duyệt hết" có được tính là EP đã duyệt các mục 1–3 không? Nếu có, ghi actor `human` + nút cụ thể; không để autopilot ghi thay.

### 4f. M7 cờ
- Cờ M6 hiện có: `gen_auth_shadow`, `crew_registry`, `continuity_validator` (REQUIRES `crew_registry`), `field_guard`. Tất cả `verified: False`, TẮT, đã thêm vào golden. ✔ Đúng K4 / K7 (không tự bật).
- **Hở:**
  - `gen_auth_shadow` không REQUIRES `crew_registry` (nó không đọc registry). Khi nối registry thì phải thêm.
  - Chưa có cờ chặn riêng cho M6-B. Rà M63 mục 18 đã cảnh báo: máy nào đang để ON sẽ chặn ngay khi đổi nghĩa cờ. Đề xuất cờ riêng `gen_auth_enforce`, `crew_role_guard` (M6.4), `crew_handoff_shadow` (M6.2), mỗi cờ khóa riêng theo K1 / K2.

---

## 5. Code đã làm — đúng thiết kế không, thiếu gì để vai "làm việc với nhau"

### 5a. M6.3 `core/gen_auth.py` (nhánh `cloud/v31-m63`, 3 commit, 21 test)
**Đúng:**
- một chỗ gọi, ngay trước `provider.submit` (trong `SPEND_LOCK`, sau `_paused_now`);
- shadow thật: 0 ghi CSDL, gói byte giống;
- đếm không dùng `retry_count`;
- Q1 / Q2 / Q4 / 40 % đều có;
- lỗi của cổng không làm hỏng lượt gửi;
- model thật lấy qua `_sent_model`.

**Lệch so với thiết kế 4b:**
- Chữ ký thiết kế là `authorize(conn, *, project_id, scene_id, kind, model, actor_role, cause_code, input_fingerprint, est_usd)`. Bản cài là `authorize(conn, job, model, upgrade, data_dir, est_usd)`, **thiếu**:
  - `actor_role`, nên không đo được lượt theo vai, cũng không chặn được vai gửi job ngoài quyền;
  - `cause_code` (lấy câu tự do, D6);
  - `input_fingerprint` (không kiểm được "gen lại phải đổi đầu vào", `CHUAN_XAY_DUNG`).
- Không có `record_outcome`, nên lượt bị provider từ chối khi poll vẫn tính (THẤP 16).
- `grants.jsonl` chỉ có đọc, không có code ghi. EP chưa cấp lượt được, và Q2 ("EP xác nhận vượt") chưa làm được.

**Thiếu để phối hợp:**
1. `needs_ep` chưa đẩy vào 📥 inbox, chưa tạo phiếu;
2. không đọc registry (model duyệt, vai);
3. các đường tiền ngoài `jobs` chưa qua cổng;
4. `repair_budget()` quét mọi shot mỗi lần gửi (lặp `attempts` theo shot). Với #31 khoảng 39 × 2 truy vấn mỗi lần gửi: chấp nhận được ở shadow, nhưng nên nhớ theo `PRAGMA data_version`.

### 5b. M6.1 `data/crew_roles.json` + `core/crew.py` (nhánh `cloud/v31-m61-m69`, 19 test)
**Đúng:**
- đủ trường bắt buộc;
- `problems()` kiểm trường thật, khâu thật, mã QC thật, id quyết định thật;
- W1–W38 / K1–K16 / job_insert_points có dữ liệu cho các check Q1 / Q2 / Q3 / Q6 / Q8;
- Continuity không đứng tên lỗi.

**Vấn đề:**
- Cinematographer không khâu; L3 / L4 / L10 lệch chủ (bảng mục 2).
- Kho không vai; EP bị gán W23–W30, tức EP thành người làm.
- `fields` thiếu model / route / ref set / lip_sync / end_frames / duyệt take (mục 2a).
- `escalate` không có điều kiện số lần (D1).
- Không có `approves[]` (vai nào duyệt sản phẩm của vai nào). Handoff có `approved_by_director` nhưng registry không nói Director được duyệt gì.
- `claude_stage` gán `change_review` cho Continuity, nhưng L16 thuộc Director. Cần nói rõ: Continuity phát hiện, Director quyết.

### 5c. M6.9 `core/continuity_validator.py` (15 test, fixture #31 định tuyến 6/6)
**Đúng:** chỉ ghi `crew/continuity_validator.jsonl`; thiếu đầu vào thì ghi `inputs.thieu`; móc 2 dòng ở `sequence_logic.check`; không gọi model.

**Vấn đề:**
- `owner_of_error` đi theo thứ tự: mã QC → category → **khâu phát hiện** → Director. Fixture cho thấy G51 / G52 ("cam", shot 28–29) về VPA (L13), trong khi chính báo cáo M61 thừa nhận "lỗi cam từ BYĐ có thể của Director". Cần thêm bước **nguồn gây lỗi**:
  - so finding với `reads[]` / `fields` của các vai thượng nguồn;
  - ví dụ: thuộc tính `cam` nằm trong `byd.vat`, nên về Director;
  - `huong_khung` về Cinematographer.
- Phiếu `status=returned` không có `handoff_id`, `fields_rev`, `attempts` nên không nối được vào M6.2.
- Chạy ở `sequence_logic.check` (theo lượt QC cả cảnh), **không chạy khi có ảnh / clip mới** như thiết kế mục 5 ("chạy khi có handoff ảnh/clip mới").

### 5d. Write guard `core/write_guard.py` (nhánh `cloud/v31-m2-tichhop`)
**Đúng:**
- 3 trạng thái AUTO / USER_LOCKED / REVIEW_REQUIRED;
- shadow không commit hộ, bỏ dòng khi rollback;
- `lock()` cho motion người sửa (`v31-ep-motion-prompt-user-locked`);
- actor có `kind` / `who`.

**Thiếu cho M6.4:**
- actor không có `role`. `ACTOR_KINDS = human/ai/auto/tool` nên không phân biệt được VPA ghi `image_prompt` (sai quyền) với Storyboard ghi (đúng).
- `_rev` chỉ tăng khi người khóa (3a).
- Phân loại trường khác registry: `layout`, `layout_people`, `stage_segment`, `plate_setup`, `spatial_state` là DERIVED (ghi tự do), trong khi registry cho chúng có chủ.
- **Đề xuất:**
  - thêm `actor(kind, who, role=…)`;
  - `assess` thêm mã `role_write_violation` khi `not crew.can_write(role, field)` (shadow);
  - sinh DERIVED từ registry (trường `owner: null` hoặc `derived: true`), không giữ hai danh sách.

### 5e. Tóm lại: để vai thật sự "làm việc với nhau" còn thiếu 5 mảnh
1. **Actor = vai** ở 3 chỗ (write guard, gen_auth, `jobs.origin` / `created_by`), cộng với chặn CLI giả "user".
2. **Phiếu có người nhận:**
   - Handoff M6.2 (jsonl) có `handoff_id`, `fields_rev`, `return_count`;
   - một "bàn phiếu" mỗi vai (đọc jsonl), và một bộ chạy vai biến phiếu thành hành động qua công cụ có sẵn (`repair_router.plan` → vai chủ → gen_auth);
   - EP nhận qua inbox.
3. **Một nguồn sự thật** cho:
   - khóa: `write_guard.state` + BYĐ đã duyệt;
   - lượt: `gen_auth.attempts`, dùng để thay `retry_count` ở `repair_router` / `AUTO_REGEN_LIMIT` khi M6-B bật;
   - chủ trường: registry, từ đó sinh DERIVED / REVIEW_FIELDS / LOCKED_KEYS.
4. **Định tuyến theo nguồn gây lỗi** + giới hạn lượt trả về.
5. **QC không tự sinh job** (check Q7): `apply_qc(autofix)` → phiếu cho vai chủ → vai chủ xin gen_auth.

---

## 6. Đề xuất sửa — xếp ưu tiên (đều Cấp 2, 0 USD, cờ TẮT, trừ chỗ ghi khác)

| Ưu tiên | Việc | Nơi | Gói | EP cần quyết? |
|---|---|---|---|---|
| P1 | Sửa registry:<br>- L6 tách hoặc gán Cinematographer;<br>- L4 tách giọng → Sound;<br>- `director_rewrite` gán cả SBA;<br>- thêm `fields`: model / route / ref_set / lip_sync / end_frames / duyệt take;<br>- thêm `approves[]`;<br>- `escalate` có `max_returns` | `data/crew_roles.json`, `core/crew.py problems()` | M6-A (bổ sung, chỉ đọc) | xác nhận bảng khâu → vai (E5) |
| P2 | Chuẩn hóa `cause` của gen_auth về mã `qc_evidence.CODES` / `errors.json`; thêm `actor_role` + `input_fingerprint`; `SAME_CAUSE_STREAK` và `needs_ep` tạo dòng 📥 inbox (shadow: chỉ ghi "lẽ ra") | `core/gen_auth.py` | M6-A sửa | không |
| P3 | Một định nghĩa khóa: gen_auth dùng `write_guard.state` + BYĐ duyệt, bỏ `LOCKED_KEYS` riêng (D4); DERIVED sinh từ registry | `gen_auth.py`, `write_guard.py` | M6-A + M2 | không |
| P4 | Continuity: bước "nguồn gây lỗi" (thuộc tính → trường → vai chủ thượng nguồn) trước bước khâu; chạy khi có ảnh / clip mới | `continuity_validator.py`, `crew.owner_of_error` | M6-A sửa | không |
| P5 | Ghi sổ quyết định "đạo diễn ngoại tuyến"; đổi `--source` mặc định = tên vai; cài check Q3 (CLI không giả "user") + Q8 | `data/decisions.json`, `tools/stage_auto.py`, `tests/test_decisions.py` | Cấp 2 nhỏ | **E3** |
| P6 | Handoff M6.2 có `fields_rev` (từ `_rev` theo trường, tăng mọi lần ghi qua guard), `return_count`, `handoff_id` trong phiếu CV | `core/handoff.py` (mới), `write_guard.py` | M6-B | không (đã trong kế hoạch) |
| P7 | Write guard theo vai: `actor.role` + mã `role_write_violation` (shadow) | `write_guard.py` | M6-B (M6.4) | không |
| P8 | Thay các bộ đếm cũ bằng `gen_auth.attempts` khi bật chặn; cờ chặn riêng `gen_auth_enforce` | `pipeline`, `repair_router`, `quality_tier`, `pilot_run` | M6-B, Cấp 3 khi bật | thời điểm bật |
| P9 | QC không tự sinh job khi cờ vai bật: `apply_qc` → phiếu, cài check Q7 | `pipeline.apply_qc` | M6-B | không |
| P10 | Đường tiền ngoài `jobs` (end_frames, quality_samples, lipsync) đi qua `gen_auth` | `end_frames.py`, `quality_samples.py`, `lipsync.py` | M6-B | **E4** |
| P11 | M2.10 lean builder = công cụ VPA/SBA (đề xuất → vai chấp nhận; tôn trọng USER_LOCKED; ref_set có chủ) | kế hoạch M2.10 + registry | M2.10 bước 1 | **E1** |
| P12 | M8.1 sửa 5 điểm chạm quyền (mục 4e) trước khi trình; M8.6 thêm phụ thuộc M6.10 | `KE_HOACH_DASHBOARD_DON_GIAN` | Cấp 1 | **E2** |
| P13 | Kho có vai (gợi ý: "Asset / Kho" dưới Director, hoặc gộp vào Storyboard + 3D) thay cho EP làm tay | registry | M6-B | **E6** |

### Câu cần Executive Producer quyết
- **E1 (chặn M2.10 / M6.5):** builder gói tối giản là *công cụ đề xuất* của Video Prompt Artist / Storyboard Artist (vai chấp nhận, prompt hoặc bộ ref người khóa không bị đổi) — **hay** là code tự quyết bộ ref + khung prompt (vai chỉ viết 2–4 câu hành động)? Ai là chủ "bộ ảnh tham chiếu gửi kèm"?
- **E2 (chặn M8):** ở chế độ Đơn giản, một lần bấm "✔ Được, làm tiếp" / "✔ Duyệt hết" có được coi là EP đã (a) khóa Bible, (b) duyệt motion, (c) duyệt sân khấu 3D (S-B) không? Nếu không, chế độ Đơn giản cần thêm một cổng "duyệt sân khấu".
- **E3:** xác nhận và ghi sổ "đạo diễn ngoại tuyến (tools/stage_auto --crew/--answer) = vai chạy ngoại tuyến hợp lệ, với 4 điều kiện". Hiện mới là lời phiên chính, chưa có mục trong `data/decisions.json`.
- **E4:** ảnh khung cuối (end_frames) có tính vào trần 3 ảnh / shot không? Video mẫu 4 s (quality_samples) có tính vào trần 2 video không? Lipsync có tính không?
- **E5:** bảng khâu → vai đề xuất:
  - L6 máy → Cinematographer;
  - L4 giọng → Sound;
  - L13 lỗi do ảnh / BYĐ → về vai thượng nguồn thay vì VPA;
  - tranh chấp về trường của Director → EP làm trọng tài.
- **E6:** Kho (hồ sơ, ảnh mẫu, gộp mục) giao vai nào, hay EP giữ làm tay?

---

## 7. Phụ lục — nguồn đã đọc
- Quyết định:
  - `v31-m6-crew-architecture-2026-10-21`, `v31-m6-generation-limits-policy-b-2026-10-21`;
  - `v31-ep-m6-self-repair-budget-40-2026-10-21`, `v31-ep-m6-pack-a-approved-2026-10-21`;
  - `v31-ep-stage-desk-actions-2026-10-21` (S-B, S-G), `v31-ep-motion-prompt-user-locked-2026-10-21`;
  - `v31-ep-m210-lean-package-2026-10-21`, `v31-ep-flag-lock-policy-2026-10-21`, `v31-ep-k4-k6-flag-baseline-reset-2026-10-21`;
  - `stage-crew-plan-2026-10-16`, `v31-d04-field-level-write-guard-2026-10-20`.
- Hộp thư: `hop_thu/su_kien/20261021-201405-cloud-E-504w.json` (câu hỏi K1), `…-202220-phien-chinh-pjb5.json` (trả lời của phiên chính).
- Báo cáo nhánh: `docs/RA_CLOUD_M63_2026-10-21.md`, `docs/RA_CLOUD_M61_M69_2026-10-21.md`, `docs/RA_CLOUD_M2_TICHHOP_2026-10-21.md`.
- Code chính: `core/runner.py:542–551` (móc gen_auth), `core/repair_router.py:85–112` (đếm theo `retry_count`), `core/stage_auto.py:1016/1263` (`source="claude_code"`).
