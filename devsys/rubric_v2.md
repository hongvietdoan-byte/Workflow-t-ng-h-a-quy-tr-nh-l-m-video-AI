# Thang chấm cố định — AI Development System (bản 2, 2026-10-03)

Bản 1 (2026-09-26) lưu ở `devsys/rubric_v1.md`; điểm chấm theo bản 1 vẫn đọc được (code giữ nguyên cách tính của chúng) và hiện "khác thang".
Lý do đổi: bản 1 chạm trần (điểm trung bình 79 → 88 dù lỗi nặng còn đó), mọi khoản trừ chỉ 1–3 điểm bất kể nặng hay nhẹ, không đo gì bằng code,
và bỏ sót lớp lỗi như 6 bug B1–B6 của rà soát 01/10 (xem `docs/DANH_GIA_CACH_CHAM_DEVSYS_2026-10-03.md`).

Mỗi khu vực trong `devsys/areas.json` được chấm 0–100 theo **8 tiêu chí cố định**. Điểm gồm hai nguồn, **cả hai do code tính**:
1. **Khoản trừ của người chấm**: người chấm chỉ *phân loại* mỗi khoản trừ (`muc` = chan / lon / nho, `loai` = loại lỗi) và dẫn bằng chứng.
   **Người chấm không ghi số điểm** — code gán điểm theo mức.
2. **Khoản trừ tự động do code đo** (mục "Khoản trừ do code tính"): người chấm không được trừ lại.

Điểm tiêu chí = điểm tối đa − tổng khoản trừ (không âm); điểm khu vực = tổng 8 tiêu chí, rồi code áp các giới hạn.

| Mã | Tiêu chí | Tối đa | Được trọn điểm khi | Người chấm trừ khi (ví dụ) |
|---|---|---|---|---|
| `chuc_nang` | Hoàn thiện chức năng | 26 | Mọi việc khu vực phải làm (theo mô tả khu vực + TODO) đều có code chạy được, xử lý lỗi rõ | Hàm còn trống / `NotImplementedError`, lỗi thật đã chứng minh (B1…), việc đã hứa trong TODO mà code không có |
| `bang_chung` | Bằng chứng chạy thật & đo chất lượng đầu ra | 16 | Có ghi chú chạy thật cụ thể (ngày, dự án #, số đo) trong TODO/docs/báo cáo, test dựng từ dữ liệu thật; khu vực làm ra ảnh/clip/âm thanh có **số đo chất lượng đầu ra** (QC, A/B, báo cáo xem thật), không chỉ "chạy được" | "Đã sửa" chỉ vì N test pass; thấy "chưa thử thật"; có đầu ra phim mà không số đo chất lượng nào |
| `test` | Test | 12 | Mỗi module có test, lần chạy mới nhất qua hết, có test hồi quy cho lỗi đã sửa | Test đang lỗi (`test:<tên>`), lỗi đã sửa mà không có test hồi quy, test không kiểm hành vi chính |
| `tuan_thu` | Tuân thủ `docs/CHUAN_XAY_DUNG.md` | 8 | 8 luật + luật chi phí thể hiện trong code: không im lặng khi thiếu đầu vào, gen lại phải đổi đầu vào ≤ 2 lần, mọi lời gọi tốn tiền qua sổ chi + ước tính trước | Lời gọi trả tiền không qua sổ chi / không ước tính trên nút, giả định chỉ nằm trong tài liệu không có guard |
| `tin_cay` | Độ tin cậy & an toàn (lỗi, tiền, quyền, bí mật) | 12 | Khi lỗi thì dừng sạch và nói rõ; không nuốt lỗi; không gửi lặp tốn tiền; kiểm quyền theo dự án (`core/access.py`); khóa/API key không lộ; dữ liệu từ web/ngoài không được coi là đáng tin; thao tác phá hủy có xác nhận + sao lưu | Công thức cổng sai (B2), nhánh lỗi im lặng, dữ liệu ngoài đưa thẳng vào lệnh/prompt, khóa trong log, kiểm quyền thiếu ở đường phụ |
| `bao_tri` | Khả năng bảo trì | 8 | File/hàm vừa phải, ít nhánh, không trùng lặp, cấu hình/bảng khai báo ở một nơi | Cùng một danh mục khai báo lặp ở nhiều nơi (B1), logic trùng, tên/ranh giới module khó hiểu *(file dài, hàm dài, hàm phức tạp do code đo)* |
| `trai_nghiem` | Trải nghiệm người dùng | 10 | Nhãn tiếng Việt có dấu, trạng thái rõ, nút tốn tiền ghi giá, lỗi nói rõ cách sửa, **đã đo thật** (tương phản, cỡ chữ, số click, hiệu năng) | Chữ tiếng Anh lộ ra người dùng, lỗi mơ hồ, nút tốn tiền không hiện giá, không có đường sửa trên giao diện cho lỗi dữ liệu (B5) |
| `tai_lieu` | Tài liệu khớp code | 8 | Docstring + tài liệu (TODO/PLAN/docs) mô tả đúng hành vi hiện tại | Tài liệu nói "đã có" nhưng code không có, hoặc ngược lại; số liệu lệch (tên cờ, ngưỡng, tên file) |

So với bản 1: 30/20/15/15/10/10 → 26/16/12/8/12/8/10/8 (thêm `tin_cay`, `bao_tri`; `tuan_thu` hạ vì phần lớn đã thành luật code; `bang_chung` thêm đo chất lượng đầu ra).

## Mức nghiêm trọng (`muc`) — điểm trừ do code gán
| `muc` | Nghĩa | Điểm trừ = tỉ lệ điểm tối đa của tiêu chí | Ví dụ ở tiêu chí 26 điểm |
|---|---|---|---|
| `chan` | **Chặn**: một đường chính hỏng / có thể tốn tiền sai / bỏ qua cổng an toàn / mất dữ liệu — đã chứng minh được | 35 % | −9,1 |
| `lon` | **Lớn**: thiếu hẳn một việc người dùng cần, hoặc lỗi rõ nhưng có đường vòng | 12 % | −3,1 |
| `nho` | **Nhỏ**: lệch nhỏ, thiếu chi tiết, không ảnh hưởng đường chính | 4 % | −1,0 |
- `chan` chỉ được tính khi có ít nhất một bằng chứng **file:dòng kiểm được hoặc `test:`**; chỉ có `absent:` / `flag:` / TODO → code hạ thành `lon`.
- Khoản `chan` và `lon` **bắt buộc kèm `feedback`** có `fix` (≥ 10 ký tự: sửa ở file/hàm nào) và `effort` (💻 / 💵 / 👤). Thiếu → câu trả lời bị từ chối (hỏi lại).
- Còn bao nhiêu khoản `chan` thì khu vực bị giới hạn: ≥ 1 → tối đa 89/100; ≥ 2 → tối đa 79/100.
- Không trừ trùng một lỗi ở hai tiêu chí; không trừ lại thứ code đã trừ tự động.

## Khoản trừ do code tính (tự động, có bằng chứng `file:dòng`)
Code đo bằng `ast` / grep có cấu trúc (`devsys/metrics.py`), người chấm thấy kết quả trong dữ liệu ("Số đo do code tính"). Hằng số nằm ở đầu `devsys/metrics.py`.

| Luật | Tiêu chí | Mỗi lần | Tối đa | Đo gì |
|---|---|---|---|---|
| `file_dai` | `bao_tri` | −1,0 | −3 | file code > 900 dòng |
| `ham_dai` | `bao_tri` | −0,4 | −2 | hàm > 150 dòng |
| `ham_phuc_tap` | `bao_tri` | −0,4 | −2 | hàm có độ phức tạp (số nhánh + 1) > 30 |
| `todo_mo` | `chuc_nang` | −0,3 | −3 | dòng `TODO.md` còn mở gán cho khu vực (không tính dòng chờ người dùng quyết) |
| `co_bat_chua_thu` | `bang_chung` | −0,5 | −4 | cờ của khu vực đang BẬT mà `verified=False` |
| `nuot_loi` | `tin_cay` | −0,4 | −4 | `except` / `except Exception` chỉ có pass / continue / return hằng, không log, không raise |
| `tien_khong_qua_so` | `tuan_thu` | −0,5 | −2 | lời gọi `submit` / `generate_*` của nhà cung cấp trong hàm không có từ khóa ngân sách / sổ chi / ước tính (dấu hiệu — người chấm xác minh) |
| `module_khong_test` | `test` | −0,6 | −3 | module của khu vực không có test nào import tới |
| `ham_khong_test` | `test` | −1 / −2 / −3 | −3 | > 50 % / 75 % / 90 % hàm công khai (≥ 5 hàm) không được test nhắc tới tên (dấu hiệu) |
| `man_nhieu_nut` | `trai_nghiem` | −0,5 | −3 | file màn hình có hơn 60 điều khiển (nút, ô nhập, khối gập…) |
| `tuong_phan` | `trai_nghiem` | −0,1 | −2 | phần tử chữ có tương phản < 4,5:1 (đo thật, `tools/ui_contrast_audit.js`) |
| `chu_nho` | `trai_nghiem` | −0,05 | −1 | chữ nhỏ hơn 12,5 px (đo thật) |
| `ui_nhieu_click` | `trai_nghiem` | −1 | −1 | số click "Dự án mới → video đầu" của v2 lớn hơn bản cũ (`tools/ui_v2_acceptance.py`) |
| `ui_cham` | `trai_nghiem` | −1 | −1 | rerun giao diện chậm hơn bản cũ > 20 % |
Hai luật cuối cùng và `tuong_phan` / `chu_nho` / `ui_*` chỉ áp cho khu vực đánh dấu `"ui_metrics": true` trong `areas.json`, khi có file đo
`devsys/data/ui_metrics.json` (tạo bằng `py tools/devsys_ui_metrics.py`).

## Giới hạn do code áp (người chấm không vượt được)
- `test` (giới hạn đặt cho tiêu chí 15 điểm, nhân tỉ lệ 12/15): không có test file nào → tối đa 2,4; chưa có lần chạy test lưu lại → tối đa 6,4; lần chạy mới nhất có test của khu vực lỗi → tối đa 5,6.
- `bang_chung`: điểm > 0 chỉ khi mục `evidence_for` có ≥ 1 trích dẫn kiểm được trỏ tới `TODO.md`, `docs/`, `PLAN.md`, `data/`, `tests/fixtures/`, `research/` hoặc `eval/`.
  Không có → code hạ về 0. Commit message **không** bao giờ được gửi cho người chấm.
- `trai_nghiem`: khu vực giao diện (`"ui_metrics": true`) chưa có `devsys/data/ui_metrics.json` → tối đa 6/10.
- Lỗi `chan` còn lại: khu vực tối đa 89 (một lỗi) / 79 (hai lỗi trở lên).
- Khu vực chỉ có tài liệu (không có code): `test` áp giới hạn như trên.

## Bằng chứng hợp lệ (mỗi khoản trừ ≥ 1)
- `đường/dẫn/file.py:123` hoặc `đường/dẫn/file.py:120-140` — dòng trong repo (code kiểm file có thật và số dòng không vượt độ dài file).
- `TODO.md:456` — dòng TODO (có trong dữ liệu gửi kèm).
- `test:tests/test_x.py::Lop::test_y` — tên test (đang lỗi, hoặc chứng minh có/không có kiểm).
- `flag:ten_co` — cờ trong `core/features.py`.
- `absent:<điều đã tìm mà không thấy>` — chỉ dùng khi lỗi là **sự vắng mặt** (vd. `absent:không test nào import core/lipsync.py`).
Bằng chứng không kiểm được (file không có, dòng vượt độ dài file) vẫn được lưu nhưng bị đánh dấu ⚠ trong web để người kiểm lại.

## Checklist các loại lỗi đã gặp — BẮT BUỘC trả lời đủ
Mỗi loại dưới đây từng thật sự xảy ra (B1–B6 của rà soát 01/10, lỗi người chấm tìm 26/09). Người chấm phải trả lời **cả 10** cho khu vực:
`"tra_loi"` = `co` (thấy lỗi loại này — **phải có ít nhất một khoản trừ cùng `loai`**), `khong` (đã tìm, không thấy), `khong_ap_dung` (khu vực không có
chỗ nào thuộc loại này) và `"ghi_chu"` (≥ 8 ký tự: đã tìm ở đâu / vì sao không áp dụng). Thiếu một mục hoặc `co` không có khoản trừ → bị từ chối.

| `loai` | Loại lỗi | Đã gặp |
|---|---|---|
| `K1_khai_bao_chung` | Bảng/danh mục khai báo chung (khâu Claude, cờ, giá, luật model, bản đồ khu vực) không khớp nơi dùng thật | B1: 11 khâu Claude thiếu `max_tokens` riêng → luôn bị chặn; B6 |
| `K2_cong_do_sai` | Công thức đo / cổng tin cậy / ngưỡng sai mẫu số, sai chiều, tự bỏ qua cổng | B2: `look_trust` chia sai mẫu số → có thể bỏ cổng storyboard |
| `K3_rang_buoc_ben_ngoai` | Ràng buộc của nhà cung cấp (tỉ lệ ảnh, độ dài, định dạng) không kiểm trước khi gửi tốn tiền | B3: ảnh tỉ lệ 3,74 bị Seedance từ chối sau khi gửi |
| `K4_dien_giai_dau_ra_model` | Code diễn giải đầu ra LLM/QC sai ở biên | B4: `CTA_TEXT` bị coi là nhân vật mới |
| `K5_du_lieu_mat` | File/dữ liệu tham chiếu mất, lỗi lặp lại mà giao diện không có đường sửa | B5: 6 ảnh Kho mất file, ~30 lần báo lỗi |
| `K6_bo_do_sot` | Bộ đo/dò (devsys, diag, QC) bỏ sót một cách viết hợp lệ nên báo sai | B6: dò cờ bỏ sót `features.on(FEATURE)` |
| `K7_tien_ngoai_so` | Lời gọi tốn tiền không qua sổ chi / ước tính / trần | 26/09: `experiments.kling_multishot`, nút Claude không giá |
| `K8_im_lang` | Nuốt lỗi, bỏ qua đầu vào thiếu mà không báo | 26/09: `diag.record` nuốt lỗi SQLite; `ensure_plates` |
| `K9_quyen_bi_mat` | Quyền theo dự án (`core/access.py`), khóa/API key, dữ liệu web/ngoài coi là đáng tin | chưa có lỗi thật — vẫn phải tìm (đường phụ không `need_edit`, khóa trong log, nội dung web vào prompt) |
| `K10_giao_dien_do_that` | Giao diện chưa đo thật: tương phản, cỡ chữ, số click, hiệu năng, màn quá nhiều nút | 01/10: ~250 điều khiển trên 5 bước |

## Độ ổn định (chống chấm lệch giữa các lần)
Nếu khu vực đã có điểm bản 2 trước đó (cùng thang), dữ liệu gửi kèm điểm và **các khoản trừ lần trước**. Điểm lần này **chưa tính khoản trừ tự động**
không được lệch quá **5 điểm** so với lần trước, trừ khi trả lời có `giai_thich_chenh`: danh sách `{"criterion", "why", "evidence"}` nói khoản trừ nào
bị bỏ/thêm và vì sao (code thật đã đổi, hay lần trước chấm sai). Không có → bị từ chối (hỏi lại). Khoản trừ lần trước còn đúng thì **giữ nguyên**.

## Cách giữ khách quan
1. Thang cố định (file này, lưu `rubric_hash` trong mỗi file điểm — đổi thang thì mọi điểm cũ hiện "khác thang").
2. Người chấm nhận **dữ liệu thật**: trích code (chữ ký hàm, docstring, dòng đánh dấu có số dòng), kết quả test thật, dòng TODO còn mở kèm số dòng,
   trạng thái cờ, cảnh báo diag, số đo do code tính, `git diff` từ lần chấm trước. Phần bị cắt vì dài được ghi rõ trong dữ liệu.
3. Không có commit message; câu "đã sửa" trong TODO không kèm test/ghi chú chạy thật thì không được điểm `bang_chung`.
4. Điểm = code gán theo mức + code đo tự động; giới hạn do code áp; bằng chứng được code kiểm; checklist và độ ổn định do code ép.
5. Model hiện tại (claude-sonnet-5 / opus-5) **không nhận tham số `temperature`** (API trả 400) → dùng `effort` thấp (stage `devsys`),
   prompt cố định, thang cố định. Lưu model, ngày, commit, `input_hash` và toàn bộ JSON trả về.
6. Chấm tăng dần: chỉ chấm lại khu vực có dấu vân tay (nội dung file + dòng TODO + kết quả test + cờ + thang + file đo UI) đổi so với lần chấm trước.

## Định dạng câu trả lời / file điểm (dùng chung cho người chấm ngoài)
Một Claude Code session / subagent có thể chấm miễn phí (dùng gói của người dùng) và ghi file vào `devsys/data/scores/`, web hiện như điểm
của Claude API. Lấy dữ liệu đầu vào bằng `py tools/devsys_score.py --export <khu_vực>` (ghi ra `devsys/data/exports/<khu_vực>.md`), chấm
theo thang này, rồi nhập: `py tools/devsys_score.py --import file.json --scorer claude-code-session`. File phải là JSON:

```json
{
  "format": "devsys-score/2",
  "scorer": "claude-code-session",
  "model": "claude-opus-5-5",
  "area": "step1",
  "criteria": {
    "chuc_nang":  {"deductions": [{"muc": "lon", "loai": "K1_khai_bao_chung", "reason": "…", "evidence": ["core/llm_runner.py:58"],
                                   "feedback": {"why": "…", "fix": "Một bảng STAGES duy nhất ở core/llm_runner.py + test quét", "files": ["core/llm_runner.py"],
                                                "verify": "tests/test_stage_budget_scan.py", "effort": "💻", "priority": 1}}],
                   "evidence_for": []},
    "bang_chung": {"deductions": [], "evidence_for": ["docs/BAO_CAO_CHAY_THU_2A_2026-09-25.md:12"]},
    "test":       {"deductions": [], "evidence_for": []},
    "tuan_thu":   {"deductions": [], "evidence_for": []},
    "tin_cay":    {"deductions": [], "evidence_for": []},
    "bao_tri":    {"deductions": [], "evidence_for": []},
    "trai_nghiem":{"deductions": [], "evidence_for": []},
    "tai_lieu":   {"deductions": [], "evidence_for": []}
  },
  "checklist": {
    "K1_khai_bao_chung": {"tra_loi": "co", "ghi_chu": "bảng STAGES thiếu khâu X", "evidence": ["core/llm_runner.py:58"]},
    "K2_cong_do_sai": {"tra_loi": "khong", "ghi_chu": "đã đọc core/effectiveness.py:85-107, mẫu số đúng"},
    "K3_rang_buoc_ben_ngoai": {"tra_loi": "khong_ap_dung", "ghi_chu": "khu vực không gửi gì cho nhà cung cấp"},
    "K4_dien_giai_dau_ra_model": {"tra_loi": "khong", "ghi_chu": "…"}, "K5_du_lieu_mat": {"tra_loi": "khong", "ghi_chu": "…"},
    "K6_bo_do_sot": {"tra_loi": "khong", "ghi_chu": "…"}, "K7_tien_ngoai_so": {"tra_loi": "khong", "ghi_chu": "…"},
    "K8_im_lang": {"tra_loi": "khong", "ghi_chu": "…"}, "K9_quyen_bi_mat": {"tra_loi": "khong", "ghi_chu": "…"},
    "K10_giao_dien_do_that": {"tra_loi": "khong_ap_dung", "ghi_chu": "…"}
  },
  "giai_thich_chenh": [],
  "can_kiem_lai": [{"what": "…", "why": "…", "evidence": ["core/x.py:10"]}],
  "summary": "2–4 câu tiếng Việt"
}
```
`muc` là mức nghiêm trọng (chan / lon / nho); **không ghi số điểm** — trường `points` nếu có sẽ bị bỏ qua, trường `score` cũng vậy: code tự tính lại.
`commit`, `date`, `input_hash` được điền khi nhập.
