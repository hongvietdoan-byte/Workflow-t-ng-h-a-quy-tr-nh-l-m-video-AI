# Thang chấm cố định — AI Development System (bản 1, 2026-09-26)

Mỗi khu vực trong `devsys/areas.json` được chấm 0–100 theo **6 tiêu chí cố định**. Người chấm **chỉ ghi các khoản trừ**, mỗi khoản trừ
phải có bằng chứng; **điểm do code tính**: điểm tiêu chí = điểm tối đa − tổng khoản trừ (không âm), điểm khu vực = tổng 6 tiêu chí.
Người chấm không tự đặt con số tổng, nên không thể "cho điểm cảm tính".

| Mã | Tiêu chí | Tối đa | Được trọn điểm khi | Trừ điểm khi (ví dụ) |
|---|---|---|---|---|
| `chuc_nang` | Hoàn thiện chức năng | 30 | Mọi việc khu vực phải làm (theo mô tả khu vực + TODO) đều có code chạy được, xử lý lỗi rõ | Việc còn mở trong TODO (`TODO.md:N`), hàm còn trống / `NotImplementedError`, nhánh lỗi nuốt ngoại lệ, tính năng nằm sau cờ chưa kiểm thật (trừ nhẹ: đúng luật 5 nhưng chưa xong) |
| `bang_chung` | Bằng chứng chạy thật | 20 | Có ghi chú chạy thật cụ thể (ngày, dự án #, số đo) trong TODO/docs/báo cáo, hoặc test dựng từ dữ liệu thật (`tests/fixtures/…`), và cờ của khu vực đã `verified` | "Đã sửa" chỉ vì N test pass; dòng "chưa thử thật" / "chưa chạy thật"; cờ `verified: False`; không có báo cáo nào |
| `test` | Test | 15 | Mỗi module của khu vực có test, lần chạy mới nhất qua hết, có test hồi quy cho lỗi đã sửa | Module không có test nào import tới, test đang lỗi (`test:<tên>`), chưa có lần chạy test lưu lại |
| `tuan_thu` | Tuân thủ `docs/CHUAN_XAY_DUNG.md` | 15 | 8 luật + luật chi phí thể hiện trong code: không im lặng khi thiếu đầu vào, gen lại phải đổi đầu vào ≤ 2 lần, mọi lời gọi tốn tiền qua sổ chi + ước tính trước | `except: pass` / bỏ qua đầu vào thiếu không báo, lời gọi trả tiền không qua sổ chi hoặc không có ước tính trên nút, giả định chỉ nằm trong tài liệu không có guard |
| `trai_nghiem` | Trải nghiệm người dùng | 10 | Nhãn tiếng Việt có dấu, trạng thái rõ, nút tốn tiền ghi giá, lỗi nói rõ cách sửa | Chữ tiếng Anh lộ ra người dùng, thông báo lỗi mơ hồ, nút tốn tiền không hiện giá, file giao diện quá dài khó bảo trì (> 900 dòng) |
| `tai_lieu` | Tài liệu khớp code | 10 | Docstring + tài liệu (TODO/PLAN/docs) mô tả đúng hành vi hiện tại | Tài liệu nói "đã có" nhưng code không có, hoặc ngược lại; số liệu lệch (tên cờ, ngưỡng, tên file) |

## Bằng chứng hợp lệ (mỗi khoản trừ ≥ 1)
- `đường/dẫn/file.py:123` hoặc `đường/dẫn/file.py:120-140` — dòng trong repo (code kiểm file có thật và số dòng không vượt độ dài file).
- `TODO.md:456` — dòng TODO (có trong dữ liệu gửi kèm).
- `test:tests/test_x.py::Lop::test_y` — tên test (đang lỗi, hoặc chứng minh có/không có kiểm).
- `flag:ten_co` — cờ trong `core/features.py`.
- `absent:<điều đã tìm mà không thấy>` — chỉ dùng khi lỗi là **sự vắng mặt** (vd. `absent:không test nào import core/lipsync.py`).
Bằng chứng không kiểm được (file không có, dòng vượt độ dài file) vẫn được lưu nhưng bị đánh dấu ⚠ trong web để người kiểm lại.

## Giới hạn do code áp (người chấm không vượt được)
- `test`: khu vực không có test file nào → tối đa 3; chưa có lần chạy test lưu lại → tối đa 8; lần chạy mới nhất có test của khu vực lỗi → tối đa 7.
- `bang_chung`: điểm > 0 chỉ khi mục `evidence_for` của tiêu chí có ≥ 1 trích dẫn kiểm được trỏ tới `TODO.md`, `docs/`, `PLAN.md`,
  `data/` hoặc `tests/fixtures/` (nơi ghi chạy thật). Không có → code hạ về 0. Commit message **không** bao giờ được gửi cho người chấm,
  nên lời tự khen trong commit không thể thành bằng chứng.
- Khu vực chỉ có tài liệu (không có code): `test` được tính theo test kiểm tài liệu nếu có, không có thì áp giới hạn như trên.

## Cách giữ khách quan
1. Thang cố định (file này, lưu `rubric_hash` trong mỗi file điểm — đổi thang thì mọi điểm cũ hiện "khác thang").
2. Người chấm nhận **dữ liệu thật**: trích code (chữ ký hàm, docstring, dòng đánh dấu có số dòng), kết quả test thật, dòng TODO còn mở kèm
   số dòng, trạng thái cờ, cảnh báo diag, `git diff` từ lần chấm trước. Phần bị cắt vì dài được ghi rõ trong dữ liệu.
3. Không có commit message; câu "đã sửa" trong TODO không kèm test/ghi chú chạy thật thì không được điểm `bang_chung`.
4. Điểm = code cộng từ khoản trừ; giới hạn code áp ở trên; bằng chứng được code kiểm.
5. Model hiện tại (claude-sonnet-5 / opus-5) **không nhận tham số `temperature`** (API trả 400) → dùng `effort` thấp (stage `devsys`),
   prompt cố định, thang cố định để kết quả ổn định. Lưu model, ngày, commit, `input_hash` và toàn bộ JSON trả về.
6. Chấm tăng dần: chỉ chấm lại khu vực có dấu vân tay (nội dung file + dòng TODO + kết quả test + cờ + thang) đổi so với lần chấm trước.

## Định dạng câu trả lời / file điểm (dùng chung cho người chấm ngoài)
Một Claude Code session / subagent có thể chấm miễn phí (dùng gói của người dùng) và ghi file vào `devsys/data/scores/`, web hiện như điểm
của Claude API. Lấy dữ liệu đầu vào bằng `py tools/devsys_score.py --export <khu_vực>` (ghi ra `devsys/data/exports/<khu_vực>.md`), chấm
theo thang này, rồi nhập: `py tools/devsys_score.py --import file.json --scorer claude-code-session`. File phải là JSON:

```json
{
  "format": "devsys-score/1",
  "scorer": "claude-code-session",
  "model": "claude-opus-5-5",
  "area": "step1",
  "criteria": {
    "chuc_nang":  {"deductions": [{"points": 4, "reason": "…", "evidence": ["TODO.md:26"]}], "evidence_for": []},
    "bang_chung": {"deductions": [], "evidence_for": ["docs/BAO_CAO_CHAY_THU_2A_2026-09-25.md:12"]},
    "test":       {"deductions": [], "evidence_for": []},
    "tuan_thu":   {"deductions": [], "evidence_for": []},
    "trai_nghiem":{"deductions": [], "evidence_for": []},
    "tai_lieu":   {"deductions": [], "evidence_for": []}
  },
  "can_kiem_lai": [{"what": "…", "why": "…", "evidence": ["core/x.py:10"]}],
  "summary": "2–4 câu tiếng Việt"
}
```
`points` là số điểm **bị trừ** (số dương). Trường `score` nếu có sẽ bị bỏ qua — code tự tính lại. `commit`, `date`, `input_hash` được điền khi nhập.
