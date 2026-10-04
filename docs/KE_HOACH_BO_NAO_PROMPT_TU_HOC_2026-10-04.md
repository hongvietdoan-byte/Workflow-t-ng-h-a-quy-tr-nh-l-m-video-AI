> **Trạng thái: NGƯỜI DÙNG DUYỆT 04/10** (đánh giá của Claude, đối chiếu code thật cùng ngày). Theo dõi tiến độ ở đợt **S14** của `docs/KE_HOACH_SUA_SAU_DU_AN_8.md`, việc **S14.19–S14.25**. Bản gốc người dùng đưa giữ nguyên bên dưới; **6 chỗ sửa + thứ tự mới ở khối này THẮNG bản gốc** khi mâu thuẫn.
>
> **6 chỗ sửa sau đối chiếu (04/10):**
> 1. Cờ `film_crew` đang **BẬT** (`dashboard.env`), không phải TẮT; C1b (04/10) đã cho trang Kiến thức theo cờ này — Đợt 2a vẫn đúng hướng.
> 2. Bảng `lessons` hiện **0 bài học** (193 mistake) → **không có "bộ vàng miễn phí"** ở Đợt 5; chế độ bóng phải chờ bài học mới phát sinh → Đợt 5 xếp cuối.
> 3. Luật gen lại đã đổi 04/10 (S14.16): **tự động ảnh ≤ 3 / video ≤ 2, người dùng bấm tay không giới hạn**; trần tiền chỉ CẢNH BÁO (mục 6c `docs/KE_HOACH_NANG_CAP_DASHBOARD_2026-10-03.md`) — mọi chỗ trong plan này nói "≤ 2 lần"/"budget.check_llm chặn" hiểu theo luật mới.
> 4. Đợt 3: trần ngân sách Claude chung không còn chặn → chỉ cần tài khoản Claude API còn tiền thật + người dùng duyệt ≈ 0,45 USD.
> 5. Đợt 4: số prompt **26 đã dùng** (`prompts/26_director_rewrite.md`, S14.17) → dùng **`prompts/27_asset_checklist.md`**.
> 6. C7 đã xác minh: Streamlit **1.64.0** → `st.chat_input(accept_file=…)` dùng được.
>
> **Gộp với việc đang làm:** Đợt 6b (nối devsys, tiền tố `db:`, đổi `rubric_hash`) **gộp vào F1** (thang v2.1) — chỉ đổi thang MỘT lần. Người dùng duyệt `db:` theo đề xuất: chỉ cho khoản tự động (`auto=True`), `_hard_evidence` vẫn từ chối `db:` cho mức `chan`. Đợt 3 + 4 làm **trước dự án thử 30 s (S14.11/12)** để dự án thử đo luôn Biên kịch + bảng kê tài nguyên.
>
> **Thứ tự (người dùng duyệt 04/10):** S14.17 + Gói K (đang làm) → **Đợt 0+1** (ghi mốc nền TRƯỚC TIÊN) → A2 → D1 → S14.18 → **Đợt 2** → **Đợt 3 + 4** → dự án thử 30 s → C2, E1, L → **Đợt 5**, **Đợt 6a** → F1 (+ Đợt 6b). Người dùng sẽ dùng **tài khoản Claude khác build tiếp** khi hạn mức tuần tài khoản này hết — mọi bàn giao qua file (TODO + kế hoạch + skill `vong-lam-viec-theo-plan`).

---

# Plan: Nâng cấp Dashboard — bộ não viết prompt tự học + khung nhập kịch bản hội thoại

Repo: `hongvietdoan-byte/Workflow-t-ng-h-a-quy-tr-nh-l-m-video-AI` (`main`)
Phiên build dùng plan này là một phiên khác. Mọi phát hiện dưới đây đã đọc code thật và verify.

---

## Context

Người dùng đưa 3 tài liệu (khung I2V motion prompt, bảng công thức SFX, phân tích Storyboard Studio) và hỏi có bổ sung được vào workflow không. Sau khi đối chiếu code, kết luận: **phần lớn ý tưởng trong tài liệu repo đã có, thường sâu hơn.** Giá trị thật nằm ở 5 chỗ còn trống, cộng 4 yêu cầu mới của người dùng.

Mục tiêu cuối: **một bộ não viết prompt update được và ngày càng hiệu quả hơn**, đo được bằng số, cộng một khung nhập kịch bản dễ dùng hơn.

### Bốn phát hiện định hình plan này

1. **Cỗ máy học đã có đủ 4 mảnh, đang chạy.** `core/lessons.py` (học từ reject → đề xuất → duyệt → tự nhập knowledge), `core/knowledge.py` (chưng cất), `core/evalset.py` + `core/effectiveness.py` (đo). `lessons.py:38` có `GROUP_OF_STAGE = {"image": "director", "video": "motion"}` — clip reject đã chảy vào bộ não motion. **Không phải xây mới, mà là làm nó học đúng trục và nhanh hơn.**

2. **Bộ trọng số người dùng đưa (51/23/10/7/5/4) là quy tắc 6 của Walter Murch, và ĐÃ CÓ trong repo** tại `knowledge/editor/editing.md:28`, kèm câu quan trọng *"cảm xúc nặng hơn năm tiêu chí còn lại cộng lại; phải hy sinh thì bỏ từ dưới lên"*. Nhưng `core/knowledge.py:112` giới hạn nó: *"gửi ở khâu Editor duyệt bản thô (Bước 5), **không gửi kèm Director**"*, và nằm sau cờ `film_crew` đang TẮT. → Việc là **nâng phạm vi**, không phải thêm tài liệu.

3. **Luồng chat đã xây xong, đang ẩn, và bộ đo để bật nó cũng đã có.** `dashboard/steps/step1.py:44` dựng tab "💡 Ý tưởng thô" cạnh ô dán kịch bản, chỉ hiện khi cờ `idea_to_script` bật. Bộ đo là `tools/experiments/idea_script_eval.py` (`GATE_MEAN = 4.0`, 5 tiêu chí). `TODO.md:58`: đã chạy thật 2/5 ý tưởng (0,438 USD), **dừng vì ngân sách Claude API chung hết ($11,74/$11,80)**. Còn 3 ý tưởng ≈ 0,45 USD.

4. **Đính chính một điều người dùng nhớ nhầm.** Người dùng nhớ tài liệu I2V có phần *"update kĩ năng viết prompt chủ động cho Claude"*. Tài liệu nói **ngược lại**: dòng 255 *"Không gọi đây là 'training'; đây là bộ hướng dẫn/instruction"*, và changelog dòng 360 *"Đổi cách gọi từ 'training Claude' thành instruction/system prompt"*. Bản v3.2 cũ gọi là "training", v4.0 cố ý bỏ. → Không "train" được Claude; cái làm được là **system instruction sống + vòng học** — đúng thứ plan này xây.

---

## Luật dự án phải tôn trọng (vi phạm là hỏng việc)

Từ `CLAUDE.md` và `docs/CHUAN_XAY_DUNG.md`:

1. Mọi thứ đổi đầu vào của model trả tiền → cờ trong `core/features.py`, `verified: False`, TẮT mặc định; chỉ bật khi có **một lần chạy thật** chứng minh.
2. Mọi lời gọi tốn tiền → qua sổ chi + **hiện ước tính giá trước** khi bấm.
3. **Không im lặng** khi thiếu đầu vào hoặc khi không làm được việc.
4. Gen lại phải **đổi đầu vào**, ≤ 2 lần.
5. "Đã sửa" phải kèm bằng chứng chạy thật.
6. `PLAN.md` đổi → build lại `PLAN.docx`/`PLAN.pdf` (`bash tools/build_docs.sh`); luôn cập nhật `TODO.md` cùng commit.

### Ràng buộc kỹ thuật đã phát hiện — đọc trước khi code

| # | Ràng buộc | Nguồn |
|---|---|---|
| C1 | `tests/test_ui_script.py:20` có `OLD_KEYS = ("up_{p}", "paste_{p}", "btn_analyse_{p}", …)` và `tree_keys` duyệt cả cây. **Bỏ key `up_{pid}` hay `paste_{pid}` là vỡ test.** | test thật |
| C2 | `dashboard/steps/step1_v2.py:231` gọi `script_input` **bên trong** `st.expander`. Streamlit không cho expander lồng expander. Dùng `ui.fold` (`dashboard/ui.py:307`, làm bằng `st.container(border=True)` + nút) thay thế. | code |
| C3 | `idea_script_eval.py` khóa bản ghi bằng `sha256(prompt)`. Thêm ô "nói thêm" mà làm đổi prompt **khi rỗng** → replay miss → mất 0,438 USD đã chi. Bắt buộc `if wish.strip():`. | code |
| C4 | `review_log.job_id INTEGER NOT NULL REFERENCES jobs(id)` (`core/db.py:126`) — bài học không có job. Và `harvest()` đọc `review_log WHERE decision='reject'` (`lessons.py:63`) → **bài học bị bỏ sẽ quay ngược thành mistake, đẻ ra bài học mới**. Vòng tự ăn chính nó. Phải dùng bảng riêng. | code |
| C5 | Mọi tài liệu knowledge đang bật được gửi lại **mỗi lần chạy**. `MAX_DOC_CHARS = 50_000`/tài liệu, `MAX_USER_CHARS = 150_000`/bước (`core/knowledge.py:20-21`). Tài liệu trùng lặp = tốn tiền thật mỗi run. | code |
| C6 | Đổi `devsys/rubric.md` làm `rubric_hash` đổi → `scores.drift_of()` trả None → **mất so sánh với mọi điểm cũ**. Gom mọi thay đổi rubric vào **một lần duy nhất**. | `devsys/scores.py:429` |
| C7 | Chưa kiểm được phiên bản Streamlit (`requirements.txt` chỉ ghi `>=1.40`). `st.chat_input(accept_file=…)` cần ≥1.43. **Chạy `pip show streamlit` trước khi code Đợt 3.** | chưa xác minh |
| C8 | Lỗi có sẵn trái luật 4: `step1_idea.py:95` nút "↻ Hỏi lại 3 hướng khác" gọi lại với prompt y hệt → trả 0,03 USD cho lần gen lại không đổi đầu vào. Ô "nói thêm" ở Đợt 3 vá đúng chỗ này. | code |

---

## Đợt 0 — Nền móng (0 USD, không đổi hành vi)

Chỉ thêm bảng và chỗ thu dữ liệu. Chưa có gì tự động.

**`core/db.py`** — thêm 3 bảng vào `SCHEMA` sau dòng 281. `schema_stamp()` (`:436`) băm chính `SCHEMA` nên tự đổi; `_migrate()` (`:453`) chạy `executescript` với `CREATE TABLE IF NOT EXISTS` → **chỉ thêm bảng thì không cần viết hàm migrate riêng**.

```sql
CREATE TABLE IF NOT EXISTS lesson_reviews (
    id INTEGER PRIMARY KEY,
    lesson_id INTEGER NOT NULL REFERENCES lessons(id),
    reviewer_type TEXT NOT NULL CHECK (reviewer_type IN ('ai_agent','user')),
    decision TEXT NOT NULL CHECK (decision IN ('approve','reject','needs_human')),
    score REAL,                  -- 0..1; NULL khi người quyết
    threshold_at_time REAL,      -- cùng khuôn qc_results.threshold_at_time (core/db.py:121)
    detail TEXT,                 -- JSON: criteria, khoản trừ, bằng chứng, sàn trượt, model, token
    note TEXT,
    decided_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lesson_reviews ON lesson_reviews(lesson_id, id);

CREATE TABLE IF NOT EXISTS effectiveness_snapshots (
    id INTEGER PRIMARY KEY,
    at TEXT NOT NULL,
    project_id INTEGER REFERENCES projects(id),   -- NULL = mốc toàn hệ
    trigger TEXT NOT NULL,                        -- 'delivery' | 'manual' | 'weekly'
    video_seconds REAL, scenes INTEGER,
    wall_min_per_sec REAL, gen_min_per_sec REAL,
    cost_per_sec REAL, currency TEXT,
    image_first_pass REAL, video_first_pass REAL,
    qc_agreement REAL, qc_pairs INTEGER,
    touches_per_scene REAL,
    satisfaction REAL, feedback_n INTEGER,
    lessons_on INTEGER,                           -- số bài học đang bật lúc chụp
    flags_on TEXT,                                -- JSON tên cờ đang BẬT
    knowledge_fp TEXT,                            -- knowledge.fingerprint(director)+(motion)
    detail TEXT,                                  -- JSON nguyên bản effectiveness.report()
    UNIQUE (project_id, at)
);
CREATE INDEX IF NOT EXISTS idx_eff_at ON effectiveness_snapshots(at);

CREATE TABLE IF NOT EXISTS user_feedback (
    id INTEGER PRIMARY KEY,
    at TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('delivery','scene','screen')),
    project_id INTEGER REFERENCES projects(id),
    scene_id INTEGER REFERENCES scenes(id),
    screen TEXT,
    stage TEXT,                  -- 'director'|'image'|'motion'|'audio'|'render'|'ui'
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    text TEXT,
    created_by TEXT,
    handled TEXT                 -- NULL | 'mistake:<id>' | 'bỏ qua: <lý do>'
);
CREATE INDEX IF NOT EXISTS idx_feedback_at ON user_feedback(at);
```

> **Vì sao `lesson_reviews` riêng, không dùng `review_log`:** xem C4. Nhưng **giữ nguyên từ vựng** `reviewer_type ('ai_agent','user')` + `threshold_at_time` để đo đồng thuận bằng **đúng công thức đã viết sẵn** `core/effectiveness.py:70` `_agreement()`, chỉ đổi bảng nguồn.

**Tạo `core/feedback.py`**: `add()`, `list()`, `summary(conn, stage, days)`, `satisfaction(conn, project_id)`.

**Thu feedback ở 3 chỗ đã có người đứng** (không dựng màn mới):
- `dashboard/steps/step5.py:912` `delivery_panel` — "Bản này dùng được chứ?" 👍/🤔/👎 + ô *"chỗ nào chưa ổn"* + chọn khâu.
- `dashboard/header.py` — nút 💬 "Góp ý màn này" (`kind='screen'`).
- Khi duyệt ảnh/clip: **đã có**, là `review_log.note`. Không làm lại.

> **Tái dùng, đừng dựng song song:** `core/compare.py:24` đã có `CRITERIA` (5 tiêu chí 1–5 + note) lưu ở `app_settings['eval:<pid>']` (`:133`). **Chuyển `compare.save_scores` sang ghi `user_feedback`**, giữ đọc `app_settings` cho dữ liệu cũ. Nếu không, sáu tháng nữa sẽ có hai nơi chứa "điểm người dùng chấm".

**Nghiệm thu Đợt 0:** mở Dashboard thật, gửi 1 góp ý mỗi loại → `SELECT * FROM user_feedback` ra 3 dòng. Đóng/mở lại, không lỗi schema (xác nhận `_migrate` chạy đúng một lần).

---

## Đợt 1 — Thước đo (BẮT BUỘC trước Đợt 5, không được đảo)

Lý do thứ tự: đây là thước dùng để chứng minh agent tự duyệt có hại hay không. Làm agent trước rồi mới làm thước thì không bao giờ chứng minh được gì.

**`core/effectiveness.py`** (đang 157 dòng, còn thoáng) — thêm:

| hàm | việc |
|---|---|
| `snapshot(conn, project_id, pricing, trigger) -> int` | gọi `report()` (`:116`) rồi INSERT; `at` làm tròn phút nên `UNIQUE` chống bấm hai lần |
| `history(conn, project_id=None, limit=50)` | |
| `trend(conn, metric)` | sao ý `devsys/scores.trend()` (`:503`) |
| `delta(a, b)` | so hai mốc, trả cả "cái gì đã đổi giữa hai mốc" từ `flags_on`/`lessons_on` |

> **Ba cột `lessons_on` / `flags_on` / `knowledge_fp` là điểm mấu chốt.** Bài học rút từ `devsys/scorer.fingerprint()` (`:123`): nếu chỉ lưu con số mà không lưu *cái gì đang bật lúc đó*, biểu đồ sẽ lên xuống mà không quy được cho nguyên nhân nào.

**Chụp ở đâu:** (1) tự động khi xuất bản xong — `dashboard/steps/step5.py:880` `_deliver_button`; (2) nút `📌 Lưu mốc` trong `effectiveness_panel` (`dashboard/admin.py:918`). **Không chụp mỗi lần mở trang** — `report()` quét `job_events` toàn dự án.

**Việc đầu tiên của phiên build: ghi lại mốc nền hôm nay** trước khi đụng bất cứ thứ gì khác.

**Nghiệm thu:** trên một dự án đã xong, bấm 📌 hai lần → 2 dòng, biểu đồ 2 điểm, `flags_on` đúng tập cờ đang bật. `pytest tests/test_effectiveness.py tests/test_effectiveness_history.py`.

---

## Đợt 2 — Knowledge: trục Murch + 3 mục I2V + 6 tag rủi ro

Rẻ nhất, đòn bẩy lớn nhất. Không máy móc mới.

### 2a. Nâng trục Murch thành thang chung (ý 4 của người dùng)

Nội dung đã có ở `knowledge/editor/editing.md:28`. Việc là **mở phạm vi**, không viết lại.

- Tách phần E1 "thứ tự ưu tiên của một điểm cắt" thành `knowledge/craft/uu_tien_cam_xuc.md` (ngắn, ~1 trang), giữ nguyên câu *"cảm xúc nặng hơn năm tiêu chí còn lại cộng lại; phải hy sinh thì bỏ từ dưới lên"* và giữ nguyên ghi chú ràng buộc đã có: *"ở khâu dựng, cảm xúc đứng dưới điều kiện nghe rõ thoại và đọc được chữ"*.
- Gắn vào **cả 2 nhóm** `director` và `motion` trong `core/knowledge.py` `GROUPS` (`:26-60`).
- `editing.md` giữ nguyên, **tham chiếu** sang file mới thay vì lặp nội dung (tránh C5).
- Trong `prompts/03_video_motion.md`: khi phải đánh đổi giữa các yêu cầu, xếp theo trục này — cảm xúc trước, không gian 3D sau cùng.
- Trong `prompts/22_first_viewer.md`: thêm trường `cam_xuc` (1–5) vào JSON đầu ra, để "người xem lần đầu" chấm được trục nặng nhất. Đây là chỗ nối tự nhiên giữa trục Murch và chỉ số hài lòng ở Đợt 0.

### 2b. Tách tag `motion` thành 6 trục rủi ro

`core/lessons.py:35` hiện chỉ có **một** tag cho mọi lỗi video:
```python
"motion": ("Chuyển động giật / biến dạng", ("giật","morph","flicker","jitter","biến dạng","artifact")),
```
"Mặt biến dạng khi quay đầu" và "nền trôi khi orbit" là hai bệnh khác nhau, hai cách chữa khác nhau — gộp lại thì bài học rút ra vô dụng.

Thay bằng 6 tag theo bảng Risk Assessment của tài liệu I2V (ánh xạ gần 1:1, và khớp `video_criteria` đã có trong `data/qc_checklist.json`):

| tag | dấu hiệu | cách chữa |
|---|---|---|
| `face_morph` | quay đầu nhiều, cận mặt, mặt nhỏ, bị che | giảm góc quay, giảm camera, bớt hành động đồng thời |
| `body_deform` | tư thế cực đoan, nhanh, nhiều khớp đổi | giảm biên độ, chia hành động |
| `wardrobe_drift` | trang phục phức tạp, vải rộng, nhiều camera motion | khóa thiết kế, chỉ cho phần vải cần phản ứng |
| `background_drift` | orbit/parallax mạnh, kiến trúc nhiều chi tiết | giảm cường độ camera, giữ điểm neo |
| `motion_overload` | quá nhiều thứ cùng chuyển động | giảm ngân sách chuyển động |
| `text_logo_corrupt` | chữ nhỏ, logo, UI trong khung | đừng yêu cầu model animate chữ/logo |

Thêm cả `identity`, `physics`, `lipsync`, `audio` để feedback ở Đợt 6 có chỗ rơi.

> **Cảnh báo:** `clusters()` (`lessons.py:93`) chỉ gom theo tag — mistake không khớp tag nào sẽ **biến mất im lặng**. Bắt buộc: mistake không gán được tag vẫn ghi, hiện ở UI mục **"chưa phân loại"**, kèm `diag.record` warn (luật 3).

> **Hệ quả cần xử lý:** sau khi tách, mỗi tag hiếm hơn → có thể không bao giờ đủ `MIN_EVENTS=3` + `MIN_PROJECTS=2` (`lessons.py:20-21`). **Chưa hạ ngưỡng vội** — chờ Đợt 5 có phân bố thật rồi mới quyết.

### 2c. Ba mục từ tài liệu I2V

Tạo **một** file `knowledge/i2v_motion_discipline.md` gắn nhóm `motion`. **Chỉ 3 mục** (14/19 mục còn lại đã có trong 9 tài liệu motion hiện hành — thêm vào là vi phạm C5 và tạo chỉ dẫn đá nhau với `seedance_prompting.md`):

1. **Bảng 6 rủi ro + cách chữa** (dùng chung với 2b — vừa là tài liệu cho Claude, vừa là từ điển tag).
2. **Preservation-first**: trước khi nghĩ chuyển động, liệt kê cái phải giữ nguyên (nhận diện, tỉ lệ, trang phục, logo/chữ, đạo cụ, bố cục). Hiện `prompts/03_video_motion.md` chỉ *cấm mô tả lại ngoại hình* — đó là lệnh cấm nói, không phải buộc nghĩ.
3. **Khi hỏng thì GIẢM chuyển động trước, đừng thêm tính từ điện ảnh** + thứ tự ưu tiên P0→P5. Mục này vá đúng lỗ trong `CLAUDE.md` mục 6: đã có luật *"gen lại phải đổi đầu vào ≤ 2 lần"* nhưng **chưa nói đổi theo hướng nào**.

Giữ nguyên cách tài liệu tự ghi các con số là **heuristic chứ không phải thông số nhà cung cấp**.

### 2d. Tài liệu phương pháp âm thanh

`knowledge/sound_design_method.md`, gắn nhóm **`director`** (repo chưa có nhóm sound và không cần tạo). Lý do: `core/sound_intent.py` đã cho Đạo diễn khai `sfx`/`music_fn`/`why`, và `sfx_plan.build_prompt()` coi `director_sound` là **ưu tiên cao hơn nguyên tắc chung** — đường ống đã thông, chỉ thiếu tài liệu dạy cách quyết.

4 phần: (1) nguyên lý lớp dẫn → lớp đập → lớp đuôi; (2) bảng ý đồ → chất âm (dịch 16 combo sang ngôn ngữ ý đồ, **không phải tên file**); (3) **luật khoảng lặng** — `sfx_plan` đã dặn *"trong khoảng lặng một âm nhỏ nghe rất rõ, đừng lấp bằng hiệu ứng to"*, nâng thành nguyên tắc: cao trào có sức nặng nhờ cái lặng ngay trước nó; (4) chống lạm dụng (trích `research/craft/draft/nhac_nen.md:74`).

> **Không xây combo SFX engine.** Kho SFX được YAMNet gán nhãn và Claude chỉ chọn trong nhãn đó; `riser`/`braaam`/`stinger` không phải lớp AudioSet, và `choir` nằm trong tập `VOICE` (`core/sound_ai.py:27-31`) nên bị chặn cứng khỏi vai trò accent. Để `sound_intent.unmet()` báo thiếu gì rồi mới quyết.

**Nghiệm thu Đợt 2:** chạy `py -m core.evalset score` trước/sau; chạy Bước 3 trên một dự án cũ, so prompt mới vs cũ — kỳ vọng prompt nêu rõ cái giữ nguyên, số chuyển động giảm, `check_flags` gọi đúng tên loại rủi ro. Kiểm tổng ký tự knowledge nhóm `motion` chưa chạm `MAX_USER_CHARS`.

---

## Đợt 3 — Gộp khung nhập kịch bản + bật `idea_to_script` (ý 1)

**Việc đầu tiên: `pip show streamlit`** (C7).

### Hình dạng: vỏ hội thoại, ruột là widget có giá

Không dùng chat tự do thật, vì để biết người dùng dán kịch bản hay gõ ý tưởng sẽ phải **tốn một lượt model không có nút** → trái luật 2, và trần 0,30 USD/ý tưởng vỡ trong 10 tin nhắn.

- Một `st.chat_input` duy nhất ở đáy = lối vào duy nhất cho chữ (kịch bản dán / ý tưởng / lời nói thêm).
- Code phân loại **0 USD** quyết định chữ đó đi nhánh nào.
- Mỗi lượt Biên kịch là một `st.chat_message("assistant")` **chứa widget thật** (bảng beats, radio 3 hướng, 2 cột tô màu) và **nút trả tiền `_paid()` giữ nguyên** (`step1_idea.py:28-31`).
- `st.chat_input` **không bao giờ** kích hoạt lời gọi model. Model chỉ chạy khi bấm nút có nhãn giá.

### Phân biệt KỊCH BẢN vs Ý TƯỞNG — 0 USD

Dùng đúng phép thử mà `idea_to_script` đã tin, không đẻ luật thứ hai:

```python
scenes, _ = idea_to_script.parse(text)   # script_reader.from_text → script_parser.split_scenes
# kịch bản khi: scenes và không phải (len==1 và scenes[0].heading == "Mở đầu")
```

Hàm mới `core/idea_to_script.classify(text) -> {"kind": "script"|"idea"|"unsure", "scenes": n, "why": [...]}`:

| tín hiệu | → |
|---|---|
| `parse()` ra ≥1 cảnh có tiêu đề thật | `script` |
| không tiêu đề · <400 ký tự · <6 dòng · 0 dòng `_DIALOGUE` | `idea` |
| không tiêu đề **nhưng** ≥2 dòng thoại, hoặc >1500 ký tự | `unsure` |

`unsure` → **không đoán bừa** (luật 3): hỏi một câu, hai nút `Đây là kịch bản` / `Đây là ý tưởng`. Luôn hiện dòng ghi đè dưới tin nhắn: `Hiểu là KỊCH BẢN (thấy 3 tiêu đề cảnh) · [không phải, đây là ý tưởng]`, lưu `st.session_state[f"in_mode_{pid}"]`.

An toàn tiền: đoán sai chiều nào cũng không mất tiền oan — nhánh kịch bản 0 USD; nhánh ý tưởng phải bấm nút có giá.

### File uploader (C1)

- **Luôn làm**: `st.popover("📎 Đính kèm file")` cạnh ô chat, bên trong là `st.file_uploader(key=f"up_{pid}")` **nguyên xi** — giữ hợp đồng key.
- **Nếu Streamlit ≥1.43**: thêm `st.chat_input(accept_file=True, file_type=list(script_reader.SUPPORTED))`.
- `paste_{pid}` giữ làm ô **"✍ Sửa toàn văn"** trong một `ui.fold` gập (dùng khi dán 300 dòng cần sửa tay).
- File vẫn đi qua `script_reader.read_script(up.name, up.getvalue())` như `step1.py:68` — không viết đường đọc file thứ hai.

### Thiết lập ngăn 0: GIỮ `st.form`, nhưng gập

Giữ form (6 trường → 6 vòng rerun nếu hỏi từng câu; `DURATIONS`/`PLATFORMS`/`TREND_MODES` là enum, `start()` ném `IdeaError` nếu trend sai — selectbox đảm bảo hợp lệ). Biến thành thẻ "⚙ Thiết lập" gập bằng `ui.fold`, sau khi xong thu thành một dòng `30 s · 9:16 · TikTok · trend Tắt  [sửa]`. **Bỏ ô "Ý tưởng" khỏi form** (`step1_idea.py:42`) — ý tưởng vào bằng `chat_input`.

### Ô "nói thêm tự do" mỗi lượt

Theo đúng khuôn đã có ở `core/sfx_plan.py:62,84` (`wish`), không phát minh khuôn mới.

```python
build_prompt(conn, pid, state, turn, wish: str = "")
```
Chèn **ngay trước** `parts.append(_section(f"LƯỢT {turn}"))` (`idea_to_script.py:151`):
```
"## Yêu cầu thêm của người dùng (ưu tiên làm theo)\n" + …    # CHỈ khi có chữ
```

Hai điểm bắt buộc:
1. **`if wish.strip():` y như `sfx_plan.py:84`.** Wish rỗng ⇒ prompt **byte-identical** với bản hiện tại ⇒ replay 2 ý tưởng đã chạy (0,438 USD) còn dùng được (C3). **Phải có test riêng cho việc này.**
2. **Gom wish của các lượt trước** — lượt 4 phải còn nhớ câu nói ở lượt 2. Lưu `state["wishes"] = {"2": "…", "3": "…"}`, render mọi khóa ≤ `turn`.

Thêm vào `## CHUNG` của `prompts/23_idea_to_script.md`: yêu cầu thêm được ưu tiên **nhưng không phá ràng buộc cứng** (khuôn `CẢNH n - `, tổng giây ±10%, không tuổi <18). Chốt chặn thật vẫn là code: `check_outline` (`:251`), `check_script` (`:299-330`).

**Lợi phụ:** nút `↻ Hỏi lại 3 hướng khác` (`step1_idea.py:95`) nay chỉ bật khi **có wish mới hoặc câu trả lời đã đổi** → vá luôn C8.

### File cần sửa/tạo

| file | thay đổi |
|---|---|
| **tạo** `dashboard/steps/step1_box.py` | ~150 dòng: khung gộp. Thanh trần (`D.meter`, mẫu `step1_v2.py:195`), lịch sử bong bóng vẽ lại từ `get_state()`, `chat_input` + popover, dòng đoán loại + nút ghi đè, `ui.fold` "✍ Sửa toàn văn", nút `▶ Phân tích`. **Không có lời gọi model nào.** |
| `dashboard/steps/step1.py:40-91` | `script_input` giữ **nguyên chữ ký và giá trị trả về** (2 nơi gọi: `step1.py:162`, `step1_v2.py:229,232`). Cờ BẬT → ủy quyền `step1_box`; cờ TẮT → giữ nguyên 2 tab dòng 50. Tách closure `analyse()` (`:67-75`) ra hàm module-level, không copy. |
| `dashboard/steps/step1_idea.py` | Tách `idea_panel` thành `idea_settings_form()` + `turn_questions/_directions/_outline/_script()`. `_paid` (`:28-31`) **không đụng**. Thay expander bằng `ui.fold` (C2). |
| `core/idea_to_script.py:126-174` | `build_prompt(..., wish="")`, `_ask(..., wish="")`, 4 hàm lượt thêm `wish=""`, lưu `state["wishes"]`; thêm `classify()`. |
| `prompts/23_idea_to_script.md` | 1 câu ở `## CHUNG`. |
| `dashboard/steps/step1_v2.py:231` | Đổi nhãn expander; kiểm thân khung không dùng expander. |
| `tests/test_ui_script.py` | Thêm ca cờ BẬT; khẳng định `OLD_KEYS` đủ ở cả hai đường. |
| `tests/test_idea_to_script.py` | **Ca then chốt**: `build_prompt(..., wish="")` ra chuỗi y hệt bản trước; wish có chữ → khối đúng vị trí; wish lượt 2 còn thấy ở lượt 4. |
| `tests/test_step1_flow.py` | Ca `classify`: kịch bản → tách cảnh; 2 dòng → Biên kịch; vùng xám → hỏi, **không tự chạy**. |

### Cổng bật cờ — không sáng tạo, dùng cái đã có

1. Code xong, **cờ vẫn TẮT**. Chạy `tests/test_idea_to_script.py`, `test_idea_script_eval.py`, `test_ui_script.py`, `test_ui_v2_acceptance.py`, `test_step1_flow.py`.
2. `py tools/experiments/idea_script_eval.py --replay <calls.jsonl cũ>` → **0 USD, phải 0 `replay_miss`**. Miss = đã vỡ C3, quay lại sửa.
3. **Chặn ngoài tầm phiên build:** người dùng phải nạp Claude API (`TODO.md:58`: hết $11,74/$11,80) + duyệt ≈0,45 USD. Rồi `--yes --max-usd 1.0` chạy nốt 3/5 ý tưởng.
4. Người dùng chấm phiếu `docs/DO_S11_2_Y_TUONG_2026-10-01.md` (1–5 × 5 tiêu chí).
5. `--score <phiếu> --run <run>` → cổng **TB ≥ 4,0** và 0 lỗi chặn.
6. QUA → `core/features.py:193` `verified: True` + viết `why` theo mẫu các cờ đã đạt (`:32-34`).

> **Lằn ranh phải giữ:** cờ `idea_to_script` đo **chất lượng kịch bản Biên kịch**, không đo giao diện. Gộp tab đẹp hơn **không** là lý do đổi `verified`. Ô wish *có* đổi đầu vào model → **gộp vào chính cờ này** (cùng tính năng, cùng trần, cùng bộ đo), không đẻ cờ con; ghi vào `why`: "bộ đo chạy với wish rỗng".

**Quay lui:** đặt khung gộp sau đúng `idea_to_script.enabled()` (`step1.py:44`) → tắt cờ ở ⚙ → Hệ thống → 🧪 là về giao diện cũ tức thì, đúng mẫu `ui_v2` (`features.py:270`). **Một cờ, hai đường.**

---

## Đợt 4 — Bảng kê tài nguyên trước khi chạy Director (A3)

**Vấn đề:** hiện luồng là *bạn gắn tài nguyên trước → Director bị dặn "BẮT BUỘC dùng" (`core/assets.py:1381`) → thiếu thì Director **tự bịa***. Không có bước nào đọc kịch bản rồi báo thiếu gì. Bạn chỉ biết **sau khi** đã tốn tiền chạy Director.

Thêm lỗ nhỏ: `location` có `location_asset` trỏ về Kho, nhưng **đạo cụ/vũ khí không có trường tương đương** trong schema cảnh — chỉ được dò bằng tên trong văn bản (`assets.py:1202-1208`), gọi tên khác là trượt.

**Thêm một lượt Claude rẻ** (1 call, không ảnh), chạy sau khi kịch bản vào, **trước** nút chạy Director:

```json
{"can": [{"loai": "character|location|prop|weapon",
          "ten": "...", "canh": [1,4,7],
          "quan_trong": "chinh|phu",
          "trong_kho": 12,        // id nếu khớp, null nếu chưa có
          "vi_sao": "..."}],
 "thieu": ["..."]}
```

Màn hình hiện bảng ✅ đã có trong Kho / ⚠️ thiếu, kèm nút gắn nhanh hoặc tạo mới.

> **Nguyên lý:** chuyển việc phát hiện thiếu từ "sau khi tốn tiền" lên "trước khi tốn tiền" — đúng cùng nguyên lý mà `core/storyboard_gate.py` đã chứng minh hiệu quả (docstring: ở lần chạy GĐ6, **~70% tiền video mua clip từ ảnh mà lỗi đã nhìn thấy được trước**).

Cờ mới `asset_checklist`, `verified: False`. Prompt mới `prompts/26_asset_checklist.md`. Stage riêng trong `core/cost.py` `LLM_STAGE_TOKENS` + `core/llm_runner.py` `STAGE_SETTINGS`.

**Nghiệm thu:** chạy trên 2 kịch bản thật — một cái Kho đủ, một cái Kho thiếu. Bảng phải báo đúng cái thiếu, và không báo nhầm cái đã có.

---

## Đợt 5 — Agent chấm bài học (ý 2)

### Nguyên tắc: tái dùng cốt lõi devsys, nhưng đẩy xa hơn một bước

Giữ nguyên tắc **"AI ghi khoản trừ + bằng chứng, CODE tính điểm"** (`devsys/scores.py:289-423`). Lý do: model tự gán số điểm sẽ **trôi** giữa hai lần chấm cùng dữ liệu — devsys đã phải dựng `drift_of()` (`:426`) và `stability()` (`:523`) để bắt đúng hiện tượng này. Và hậu quả ở đây đắt hơn devsys: devsys sai thì chỉ là báo cáo; bài học sai thì **mọi dự án sau đều gánh**.

Nhưng khác devsys ở một điểm quan trọng: **không hỏi AI thứ code tự đếm được** (đúng tinh thần `facts["auto"]`, `devsys/scorer.py:226-235`, và câu *"Không trừ lại những gì mục 'Số đo do code tính' đã trừ"* ở `:269`).

**KHÔNG bê nguyên** `checklist` 10 loại lỗi, `giai_thich_chenh`, `rubric_hash` — sinh ra cho đối tượng là cả một khu vực code, quá nặng cho một quy tắc 3 câu.

### Rubric chấm một bài học

Thang 100, 6 tiêu chí. Tái dùng nguyên `SEVERITY_FRACTION = {"chan": 0.35, "lon": 0.12, "nho": 0.04}` (`devsys/scores.py:41`) để người đọc hai hệ không phải nhớ hai bảng.

| mã | tiêu chí | max | ai chấm | sàn cứng (trượt → **không tự duyệt**) |
|---|---|---|---|---|
| `bang_chung` | đủ số lần, đủ số dự án, ví dụ có thật trong `mistakes` | 25 | **CODE** | `events ≥ 3` **và** `projects ≥ 2` |
| `cu_the` | mệnh lệnh, nói rõ làm gì/cấm gì, kiểm được bằng mắt | 25 | AI | 0,60 × 25 = **15** |
| `khong_mau_thuan` | không chọi tài liệu đang bật, không chọi bài học đã duyệt | 20 | AI (**bắt buộc dẫn trích**) | bất kỳ khoản `chan` → trượt |
| `khong_trung` | không lặp bài học đã duyệt cùng nhóm | 15 | CODE (key) + AI (ý) | trùng ý → **đề nghị thay thế**, không thêm |
| `do_rong` | không quá hẹp (đúng 1 cảnh), không quá rộng (khẩu hiệu) | 10 | AI | 0,50 × 10 = **5** |
| `an_toan` | không ép đổi đầu vào ngoài cờ; không là nội dung web chưa kiểm | 5 | CODE + AI | `source='research'` → trượt thẳng |

**Giới hạn code áp** (mô phỏng `CHAN_CAPS`, `devsys/scores.py:43`):
- ≥1 khoản `chan` bất kỳ → tổng ≤ **60** (dưới mọi ngưỡng, luôn về tay người).
- Khoản `chan`/`lon` **bắt buộc có `sua`** + `evidence` (mẫu `feedback.fix`, `devsys/scores.py:356`).
- `evidence` của `khong_mau_thuan` phải là **trích nguyên văn** có trong tài liệu gửi kèm; code so chuỗi (tinh thần `check_evidence`, `:80`). Không tìm thấy → hạ `chan` → `lon` + ghi `note` (`:338-341`).

### Ngưỡng

**Không dùng cột `projects.*`** — `qc_auto_pass_threshold` theo dự án vì ảnh thuộc một dự án; bài học là **xuyên dự án** (`MIN_PROJECTS=2`). Dùng bảng **đã có** `learning_meta` (`core/db.py:282`) qua `lessons.meta()`/`set_meta()` (`:222-230`) — nơi `research_monthly` đang nằm.

```python
# core/lesson_judge.py
AUTO_PASS_DEFAULT = 0.85     # cùng số với projects.qc_auto_pass_threshold (core/db.py:9)
GREY_ZONE = 0.05
PRESETS = {                  # cấu trúc sao chép core/qc_policy.py:8
    "chat":     {"label": "Chặt",     "threshold": 0.90, "quota_week": 2},
    "can_bang": {"label": "Cân bằng", "threshold": 0.85, "quota_week": 3},
    "thoang":   {"label": "Thoáng",   "threshold": 0.78, "quota_week": 5},
}
```
Lưu **0–1 (REAL)**, hiển thị %. Rubric ra 0–100 thì chia 100 trong `normalize()` — trộn hai thang đúng là lỗi `K2_cong_do_sai` mà devsys tự liệt (`scores.py:48`).

> 0,85 **mượn từ QC ảnh, chưa có cơ sở riêng cho bài học.** Phải đo ở chế độ bóng rồi chỉnh.

### 8 van BẮT BUỘC về tay người

1. `source='research'` — UI đang **hứa thẳng** với người dùng: *"Nội dung web coi là không đáng tin: chỉ thành đề xuất, không tự áp dụng"* (`dashboard/admin.py:1187`). Cho agent duyệt lớp này là **nói dối trên giao diện**. Agent chỉ chấm `source='mistakes'`.
2. Trượt bất kỳ sàn cứng, hoặc ≥1 khoản `chan`.
3. **Vùng xám** `threshold ± 0,05` → "cần người xem". Quyết định sát biên là quyết định không đáng tin.
4. Không gọi được Claude (thiếu key, hoặc `budget.check_llm` chặn) → giữ `state='proposed'`, **`diag.record` warn**, UI ghi rõ lý do (luật 3).
5. Mâu thuẫn tài liệu đang bật hoặc bài học đã duyệt.
6. Vượt trần tài liệu (xem chống trôi) → người quyết gộp/cắt.
7. `LessonError` khi `sync_knowledge` — code đã rollback đúng (`lessons.py:189-192`); agent phải báo, không im lặng thử lại.
8. **Quota** `quota_week` bài/7 ngày. Chống kịch bản `harvest()` kéo về một loạt lỗi cũ rồi agent duyệt hàng loạt trong một lần bấm.

### Chống trôi knowledge (vấn đề thật, không phải giả định)

`sync_knowledge()` (`lessons.py:198-214`) dựng tài liệu từ **toàn bộ** bài học `approved` và file này gửi lại mỗi lần chạy. Trần duy nhất hiện có là `MAX_DOC_CHARS=50_000`, và nó chỉ bật khi đã quá muộn: ném `LessonError` (`:216`) → người dùng kẹt, không duyệt được gì nữa.

1. **Một `key` = một bài học sống.** `_known()` (`:106`) đã chặn trùng `(group, key)`, `key = f"mistake:{tag}"` (`:136`) → trần tự nhiên ~số tag. Agent **không được sinh `key` ngoài tập tag**. Lỗi lặp tiếp → đề xuất **bản thay** (`state='superseded'`), không cộng dòng. `sync_knowledge` lấy bản `approved` có `id` lớn nhất mỗi `key`.
2. **Trần mềm**: `MAX_AUTO_LESSONS = 12`/nhóm, `SOFT_DOC_CHARS = 8_000`. Chạm → ngừng tự duyệt, bắt người gộp. Để ở 8k/50k để còn đường lùi.
3. **Chưng cất nhắc bằng cảnh báo, không bằng caption.** `sync_knowledge` thành công → `knowledge.fingerprint()` (`:352`) đổi → `distilled_status()` (`:420`) `fresh=False`. Hiện UI chỉ nói bằng chữ (`admin.py:1161`). Phải: cảnh báo đỏ + `diag.record` warn. **Không tự chạy chưng cất** (tốn tiền, phải người bấm sau khi xem ước tính).
4. **Cổng evalset trước/sau** — chạy `core/evalset.py` (**miễn phí**) trước và sau khi bài học vào knowledge. Điểm tụt → **tự hạ bài học về `proposed`** + báo người.
5. **Ghi xuất xứ mỗi dòng**: `- **{title}**: {body} (agent chấm 0,89 · 14/10)` hoặc `(người duyệt)`.

> **Sửa một lời nói dối sắp xảy ra:** `DOC_TITLE` (`lessons.py:19`) = *"Bài học đã duyệt (tự động cập nhật)"* và dòng đầu tài liệu (`:209`) = *"(đã được người duyệt)"* — **sai sự thật ngay khi agent duyệt**. Đổi thành *"đã duyệt (người hoặc agent chấm điểm)"*.

### File cần sửa/tạo

| file | thay đổi |
|---|---|
| **tạo** `core/lesson_judge.py` (~260 dòng) | `facts()`, `build_prompt()`, `normalize()`, `judge()`, `judge_all()`, `estimate()`, `MockJudge` (sao `devsys/scorer.MockScorerClient:360`), `PRESETS` |
| **tạo** `tests/test_lesson_judge.py` | rubric, sàn cứng, vùng xám, quota, van `research`, MockJudge |
| `core/lessons.py:179` | `decide(conn, lesson_id, approve, reviewer="user", note=None)` + ghi `lesson_reviews` |
| `core/lessons.py:195,19,209` | `sync_knowledge`: một bản/`key`, trần ký tự, ghi xuất xứ; sửa `DOC_TITLE` |
| `core/lessons.py:131` | `propose()` **không** gọi judge bên trong — hai lời gọi tốn tiền khác nhau phải có hai nút và hai ước tính riêng (luật 2) |
| `core/features.py` | cờ `lesson_auto_approve`, `verified: False`, `why`: "cần ≥10 cặp agent↔người, đồng thuận ≥90%, agent-lỏng-quá = 0" |
| `core/llm_runner.py:93` | `STAGE_SETTINGS["lesson_judge"] = {"effort": "low"}` |
| `core/cost.py:276` | `LLM_STAGE_TOKENS["lesson_judge"] = (4000, 1200)` — stage riêng để sổ chi tách *viết* và *chấm* bài học |
| `dashboard/admin.py:1156` | nút `🤖 Chấm điểm đề xuất` + `cost.llm_tag` (mẫu `:1165`); bảng 6 tiêu chí + khoản trừ + bằng chứng; bài chờ người ghi rõ **van nào** chặn. Giữ nguyên nút Duyệt/Bỏ tay. |

### Chế độ bóng (người dùng đã chọn) — đây chính là "lần chạy thật" luật 1 đòi

Agent chấm **mọi** đề xuất và ghi điểm, **người vẫn bấm**. Không bài học nào vào knowledge do máy.

**Mẹo lấy bộ vàng miễn phí:** chấm lại toàn bộ bài học đã `approved`/`rejected` trong quá khứ — chúng **đã có nhãn của người**, không tốn thêm một quyết định nào.

Chỉ tiêu, mượn nguyên `TRUST_*` (`core/effectiveness.py:85-88`): ≥**10 cặp**, đồng thuận ≥**90%**, **agent-lỏng-quá = 0** (agent duyệt bài người đã bỏ — lỗi lỏng mới là lỗi đắt). Dùng lại đúng công thức `_agreement()` (`:70`), đổi bảng nguồn sang `lesson_reviews`.

> **Thiên lệch phải trừ hao:** bài học cũ có thể đã được sửa câu chữ bằng tay (`lessons.edit`, `:167`, gọi ngay trước `decide` ở `admin.py:1203`), nên agent chấm bản *đã sửa* chứ không phải bản gốc.

**Chỉ khi đạt chỉ tiêu** → bật `lesson_auto_approve` với quota 3 bài/tuần + đủ 8 van.

**Nghiệm thu bật:** để agent tự duyệt **đúng một** bài → mở `data/knowledge_user/<group>/bai_hoc.md` thấy dòng ghi *"agent chấm 0,89"*; evalset trước/sau **không tụt**; chạy trọn một dự án kế tiếp rồi `delta()` so mốc.

---

## Đợt 6 — Feedback → bài học + nối devsys (ý 3)

### 6a. Feedback chảy vào `mistakes`

Cờ `feedback_to_mistakes`, `verified: False`.

- **Chảy vào**: `kind ∈ ('delivery','scene')` **và** `stage ∈ {director,image,motion}` **và** `rating ≤ 2` **và** `len(text) ≥ 15`. Dùng `lessons._add(conn, "feedback", feedback_id, …)` (`:84`) — `UNIQUE(source, ref_id)` cho idempotent miễn phí.
- **KHÔNG chảy vào**: `kind='screen'`. Góp ý về *phần mềm* không được trộn vào kiến thức làm phim — đó là việc của devsys (6b).
- **Van giữ nguyên** `MIN_EVENTS=3` + `MIN_PROJECTS=2`. Một lời phàn nàn ở một dự án **không** thành bài học.
- Feedback không gán được tag → vẫn ghi, hiện ở "chưa phân loại", `diag.record` warn (xem cảnh báo ở 2b).

### 6b. Nối devsys

**Lập luận:** tiêu chí thang bản 2 tên là **`bang_chung` — "Bằng chứng chạy thật & đo chất lượng đầu ra"** (`devsys/scores.py:30`, 16 điểm). Thang **đã hứa** đo chất lượng đầu ra, nhưng `devsys/collect.py` không cấp dữ liệu nào để làm việc đó. Đây không phải thêm tính năng — là **trả nợ cho thang điểm hiện có**.

**Nối ở `devsys/collect.py` cạnh `diag_summary()` (`:674`)** — chỗ đó đã có đúng khuôn cần: mở DB **read-only** (`"file:"+path+"?mode=ro"`, `:682`), trả `{available, note}` khi không có DB (`:677`), `redact()` (`:695`).

```
devsys/collect.py   + ops_summary(db_path, root, days=90) → {latest, trend[], feedback{by_stage, recent[]}}
                    + collect() (:732): snap["ops"] = ops_summary(...)
devsys/areas.json   + "ops_stages": [...]   (song song "diag_stages", :18)
devsys/scorer.py    + build_bundle() (:155): 2 mục mới NGAY TRƯỚC "## Điểm lần trước"
                    + fingerprint() (:123): băm thêm id mốc effectiveness mới nhất + số góp ý chưa xử lý
```

**Trừ điểm KHÔNG để AI tự cảm nhận** — thêm 2 luật vào `devsys/metrics.py` `RULES` (`:24`):

| luật | điều kiện | tiêu chí |
|---|---|---|
| `hieu_qua_tut` | `first_pass` tụt >10 điểm % giữa hai mốc **mà `flags_on` + `knowledge_fp` không đổi** | `bang_chung` |
| `gop_y_lap` | ≥3 góp ý `rating ≤ 2` cùng `stage` trong 30 ngày, `handled IS NULL` | `trai_nghiem` |

> **Điểm cần người dùng chốt:** `scores.check_evidence()` (`:80-107`) chỉ nhận `file:dòng`, `test:`, `flag:`, `absent:`. Phải thêm tiền tố `db:` — **đây là nới lỏng định nghĩa bằng chứng, có rủi ro**. Đề xuất: `db:` **chỉ** dùng cho khoản tự động (`auto=True`); `_hard_evidence()` (`:256`) vẫn **từ chối** `db:` cho mức `chan`, nên AI không mượn được `db:` để dựng lỗi chặn không kiểm được.

**Trang mới `page_effect()`** trong `devsys/app.py` (cạnh `page_health()`, `:415`) — ba đường trên **cùng trục thời gian**: (1) điểm devsys tổng có trọng số (`scores.trend():503`); (2) first-pass + phút/giây + chi phí/giây; (3) tỉ lệ góp ý tích cực. Cộng **mốc dọc**: ngày bật/tắt cờ, ngày bài học duyệt (`lesson_reviews.decided_at`), ngày chưng cất. **Chỉ khi có mốc dọc thì ba đường kia mới quy được nguyên nhân** — không thì chỉ là ba đường đẹp.

**Nghiệm thu:** `--export <area>` có mục "Hiệu quả vận hành"; chấm lại bằng `--provider mock` (miễn phí) để chắc `normalize` không vỡ; rồi chấm thật một khu vực; `stability()` (`:523`) không báo `noise` bất thường. Ghi `TODO.md`: lần này `rubric_hash` đổi nên drift không áp được — giá đã biết trước (C6).

---

## Thứ tự và cổng chặn

| Đợt | Việc | Cổng để sang đợt sau |
|---|---|---|
| 0 | Schema + thu feedback | 3 loại góp ý ghi được, schema migrate sạch |
| 1 | Lịch sử effectiveness | **Đã ghi mốc nền.** 2 mốc so được bằng `delta()` |
| 2 | Knowledge: Murch + 6 tag + I2V + âm thanh | evalset không tụt; knowledge chưa chạm trần ký tự |
| 3 | Gộp khung + bật `idea_to_script` | replay 0 miss → **người dùng nạp ≈0,45 USD** → cổng TB ≥ 4,0 |
| 4 | Bảng kê tài nguyên | đúng trên 2 kịch bản thật (Kho đủ / Kho thiếu) |
| 5 | Agent chấm bài học — **bóng trước** | ≥10 cặp, đồng thuận ≥90%, agent-lỏng-quá = 0 |
| 6 | Feedback → bài học + nối devsys | mock chấm không vỡ; `stability()` không noise |

Đợt 1 **phải** trước Đợt 5. Đợt 0 phải trước Đợt 1 và 6. Còn lại có thể đổi thứ tự.

**Đợt 3 có một chặn ngoài tầm phiên build:** cần người dùng nạp tiền Claude API. Nếu chưa có, code xong và dừng ở bước replay, không bật cờ.

---

## Verification

**Mỗi đợt:**
```bash
pytest tests/                       # toàn bộ, không chỉ test mới
py -m core.evalset score <outputs>  # miễn phí, chạy trước/sau mỗi lần đổi knowledge
py tools/devsys_score.py --provider mock --export <area>   # miễn phí
```

**End-to-end sau Đợt 3:**
1. Mở Dashboard, Bước 1 → gõ một ý tưởng 2 dòng vào ô chat → phải nhận ra là `idea`, hiện nút "▶ Lượt 1" **có giá**.
2. Dán một kịch bản 3 cảnh → phải nhận ra là `script`, tách cảnh, **0 USD**.
3. Dán một đoạn mơ hồ (10 dòng, có thoại, không tiêu đề) → phải **hỏi lại**, không tự chạy.
4. Tải `.docx` qua popover → đọc được qua `script_reader.read_script`.
5. Tắt cờ ở ⚙ → 🧪 → giao diện 2 tab cũ về nguyên vẹn, `up_{pid}`/`paste_{pid}` còn sống.

**End-to-end sau Đợt 5:**
1. Chạy trọn một dự án thật từ Bước 1 → Bước 5.
2. Chụp mốc effectiveness, `delta()` so với mốc nền ở Đợt 1.
3. Mở `data/knowledge_user/motion/bai_hoc.md` — mỗi dòng phải ghi rõ ai duyệt.
4. Mở devsys (`Start-DevSystem.bat`, cổng 8502) → `page_effect()` thấy 3 đường + mốc dọc.

**Bằng chứng phải lưu** (luật 5): ảnh chụp bảng + số đo vào `TODO.md`, cùng commit với code.

---

## Việc cần người dùng (ngoài tầm phiên build)

1. **Nạp Claude API ≈0,45 USD** + duyệt trần → mở khóa cổng Đợt 3 (`TODO.md:58`).
2. **Chấm phiếu** `docs/DO_S11_2_Y_TUONG_2026-10-01.md` sau khi chạy nốt 3 ý tưởng.
3. **Chốt**: có cho `db:` vào `check_evidence` của devsys không (Đợt 6b).

## Chỗ chưa chắc

1. **Agent chấm bài học có đáng tin không** — chưa có dữ liệu. Chế độ bóng ở Đợt 5 là bắt buộc, không được rút gọn.
2. **Số bài học thật trong DB** — chưa mở `data/manifest.sqlite`. Nếu ít, chờ đủ 10 cặp tự nhiên có thể mất hàng tháng; mẹo chấm lại bài cũ là cách duy nhất có bộ vàng ngay.
3. **Ngưỡng 0,85** mượn từ QC ảnh, chưa có cơ sở riêng.
4. **evalset có đủ nhạy để bắt bài học xấu không** — rất có thể bài học tệ vẫn qua hard/soft check. Vì vậy cổng evalset là *thêm vào*, không thay cho đo hiệu quả thật.
5. **Phiên bản Streamlit** (C7) — kiểm trước khi code Đợt 3.
6. **Tỉ lệ feedback rơi ngoài `TAGS`** — chỉ biết sau ~30 góp ý thật. Nếu cao thì phải nhờ Claude gán tag → lại là lời gọi tốn tiền, phải có cờ và ước tính riêng.
