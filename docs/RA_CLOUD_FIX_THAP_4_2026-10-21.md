# C-FIX-THAP-4 — qc_scene: tách regex "máy sau lưng" + sửa câu banner (cloud-C, 21/10)

Nhánh `cloud/v31-fix-thap-4`, tạo từ origin/main.

## VỪA — `core/qc_scene._behind_any`
- **Lỗi:** `image_prompt` và `action` đang quét cùng regex với các trường máy. Vì vậy những câu tả HÀNH ĐỘNG cũng bị coi là "bố cục sau lưng / qua vai", ví dụ:
  - "hides the grenade behind her back"
  - "grabs him from behind"
  - "sneaks up from behind the wall"
  - "vác súng qua vai", "nhìn qua vai"
  
  Khi bật cờ `qc_false_alarm_fix`, các shot này bị bỏ kiểm cỡ shot dù không nên.
- **Sửa:** dùng hai regex.
  - Trường máy / bố cục (`angle`, `shot`, `blocking`, `start_frame`): giữ nguyên `_BEHIND_ANY` như trước.
  - Chữ tả cảnh (`image_prompt`, `action`): dùng regex mới `_BEHIND_PROSE`, chỉ khớp khi chữ gắn với MÁY:
    - `OTS`
    - `over-the-shoulder shot|view|angle|framing|on|of`
    - `(low|high) camera (is|placed|…) behind`
    - `(shot|seen|filmed|framed|viewed) from behind`
    - `back(s) to camera`, `rear view`
    - `máy … sau lưng`, `góc (máy) qua vai`, `quay lưng về máy`
- Ca thật P33-A5 (#33 S2, "Low camera behind the group") vẫn khớp. Các ca dương của DP1 và C-FIX-THAP-1/2 vẫn xanh.

## THẤP — `core/code_version.banner`
- **Lỗi:** bản ghi có dấu code nhưng máy không tính được dấu hiện tại (`code_fingerprint` trả None), nên phải so bằng sha. Banner vẫn báo "tệp .py đã đổi" dù thực tế chưa so file.
- **Sửa:**
  - `stale_instances` ghi thêm `by`: `"code"` hoặc `"sha"`.
  - Khi `by="sha"`, banner nói: "không tính được dấu code hiện tại — so sha … ≠ HEAD …, chưa biết code có đổi".

## Bằng chứng
- `tests/test_v31_fix_thap_4.py` có 21 test. 7 test đỏ được commit riêng trước khi sửa, sau đó cả 21 xanh:
  - 6 ca âm (5 ca phiên chính nêu + "glances over the shoulder");
  - 10 ca dương ở `image_prompt` / `action` (gồm P33-A5);
  - 4 ca trường máy giữ regex rộng;
  - 1 ca banner so bằng sha.
- Đã đăng ký test trong `devsys/areas.json`, ở khu step2 và diag.
- Bộ test đầy đủ: xem tin hộp thư `xong C-FIX-THAP-4`.
