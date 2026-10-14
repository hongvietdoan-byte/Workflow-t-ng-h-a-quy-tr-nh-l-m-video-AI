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

## Việc mở / bước kế
- Đường Seedance refs (928 thật): `shown` cho D6 chỉ = khung đầu + ảnh tham chiếu của scene đầu; gói gửi thật có storyboard Shot 1/2 +
  ảnh nơi chốn → D6 không thấy "đúng các ảnh sẽ gửi" cho clip ghép (core/runner.py ~1971). Nên rà riêng.
- "mất mã Shot N" còn khả năng tái diễn (REF_TOKEN phân biệt hoa/thường: "SHOT 1"/"shot 1" bị tính mất), nhưng main đã liệt kê mã trong
  đề bài + 1 lượt sửa chỉ đúng lỗi → khả năng thấp, và không còn trả lại cho cùng đầu vào.
- chat_prompt_calls:928 thật vẫn n=2 (dự án #29 cũ, không ảnh hưởng #31).
