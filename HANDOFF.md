# HANDOFF — D6 trần "đầu vào vẫn đổi" job 928 (#29), 14/10

## Đã xong
- Gốc (dựng lại bằng dữ liệu thật, bản sao CSDL, Claude giả, 0 USD — script tạm theo cách tools/replay_payload.py):
  vân tay đầu vào job 928 (clip ghép shot 3+4) và 926 ỔN ĐỊNH qua hai lần dựng liền (928: 60343fe4…, lượt 2 lấy cache, 0 lời gọi).
  Sổ llm_calls #29: 928 gọi 04:56:38 + 04:57:06, CÙNG 8294 token vào (926: 2 lượt cùng 7452) → cùng đầu vào; chat_prompt_calls:928 =
  {n:2, last:null}, không có cache/fail → cả hai lượt bị code từ chối ("mất mã ảnh / shot: Shot 1, Shot 2"). Code chạy lúc đó (f73e009d)
  KHÔNG lưu bản bị từ chối → vòng chờ sau trả tiền lại → chạm trần; câu trần luôn nói "đầu vào vẫn đổi" (sai). Lời từ chối của 928 bị
  diag.record gộp vào dòng của 926 (gộp theo câu chữ 10 phút, câu không có số job) → nhìn như 928 không bị từ chối.
- Trên main (6dc299be) đã có lượt sửa + lưu bản bị từ chối theo vân tay → cùng đầu vào không trả lại (test mới xác nhận).
- Sửa thêm (core/chat_prompt.py): mỗi lượt trả tiền nhớ "keys" + "parts" (băm từng phần) trong chat_prompt_calls:<job>; câu chat_prompt_cap
  nói đúng: "cùng đầu vào … bị từ chối / Claude lỗi" hoặc "đầu vào đổi: <phần>"; câu chat_prompt / chat_prompt_fail / cap có "D6 job <id>".
  fingerprint() KHÔNG đổi → 0 job đang chờ bị gọi lại.
- Test: tests/test_chat_prompt_cap_928.py (đỏ 3 → xanh; 67 qua cùng test_chat_prompt + image3). Khai devsys/areas.json (core_infra).
- Agent rà khâu liên quan: không thấy chỗ đọc câu/khóa cũ; góp ý băm ảnh 2 lần → đã đổi input_parts chỉ tính khi cần.

## related_areas (py tools/related_areas.py core/chat_prompt.py tests/test_chat_prompt_cap_928.py)
- core_infra: core/chat_prompt.py · gọi tới: budget (core/cost.py), step2 (core/runner.py, dashboard/steps/step2.py),
  step4 (core/runner.py, dashboard/steps/step4.py) · dùng chung cờ: autopilot, step2 · không có test chậm.

## Đợt 2 (điều phối giao): sửa gốc vì sao 928 bị từ chối
- GỐC THẬT: đường Seedance refs (clip ghép) D6 nhìn khung đầu + ảnh Kho của scene đầu (job 923, KELLY 10/12, Tháp, Bom keo, SKORP — 6
  ảnh) trong khi gói gửi thật + "Image N" của bản code ghép = storyboard Shot 1, storyboard Shot 2, KELLY, render nơi chốn Shot 1, Shot 2
  → Claude viết lệch mã → bị từ chối.
- Sửa core/runner.py: `_reference_sources` = MỘT nguồn cho ảnh gửi (`_reference_pictures`, thứ tự/nhãn host y cũ) và ảnh D6
  (`_d6_pictures`: nhãn "Image N: …" đúng mã; đường kỹ năng; shot đơn refs + khung cuối; còn lại như cũ). D6 tắt → không đọc thêm.
- core/chat_prompt.py: mã Image/Images/Shot so không phân biệt hoa/thường (chuẩn hoá), số vẫn phải đúng (\b).
- Bằng chứng (bản sao CSDL, Claude giả, 0 USD, trạng thái lúc gửi: shot sau chưa có clip): job 928 + 926 — 5/5 ảnh D6 khớp
  reference_only thật (tra asset_uri → seedance_subject_pictures, tên bản sạch `<tên>_<sha1 đường dẫn>_marked_none.png` trùng từng
  file, đúng thứ tự); hai lần dựng cùng vân tay, lượt 2 không gọi.
- Ảnh hưởng vân tay: máy chính có 9 job video chờ (#2, #3 — dự án cũ), 0 bản D6 video đã lưu cho job chưa gửi → 0 job mất cache,
  chi phí thêm 0 USD (job mới vẫn ≤ 2 lượt + 1 lượt sửa như cũ).
- Test (tests/test_chat_prompt_cap_928.py): CodesAnyCase (đỏ→xanh), D6SeesTheSentPictures; lệnh gom 11 file 345 qua.
- Agent rà: không lỗi chặn; đã sửa "tính ảnh D6 cả khi cờ tắt". Ghi nhận nhỏ: mã chữ thường trong văn xuôi bản ghép ("shot 2") nay thành
  mã bắt buộc (seedance_refs không sinh dạng này); cảnh refs không có shot_no bị D6 coi là shot đơn (hiếm).

## Việc mở / bước kế
- jobs.sent_package.refs của đường refs chỉ ghi image_path/image_references (tham số adapter bỏ qua), ảnh thật nằm ở params.reference_only
  (asset://) — sổ gói gửi nên ghi file local của reference_only (chưa sửa).
- chat_prompt_calls:928 thật vẫn n=2 (dự án #29 cũ, không ảnh hưởng #31).
- Chưa chạy lại test sau sửa nhỏ cuối (D6 tắt → shown rỗng); cần chạy ở bước gộp.
