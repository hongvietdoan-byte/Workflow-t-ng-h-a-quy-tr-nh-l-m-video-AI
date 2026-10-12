# Bàn giao Đ15 việc3
Nhánh codex/d15-viec3-vung-an-toan, base62702921; chưa commit/push.
Đã implement helper bounds + fitON/warnOFF, popup/AIlabel/card/cropcallers, flagOFFoptin.
RA docs/RA_D15_VIEC3_CODEX_2026-10-12.md. Test liênquan5files; lần1 89passed43,19s; lần2 91passed43,15s.
Bằng chứng OFF pixelbaseline AI/card+24frames, fakeffmpeg360x6401s, PNG ON/OFF docs/images/d15.
Còn rà/sửa: exportreframe notes, areas.flags, nội dung quá dài trướcfit/HUD bounds. Rootgomfindingvòngsửa; giữareas.version66; khôngTODO/PLAN/data/API/main.

## Vòng sửa sau rà độc lập
Ba P2 đã sửa: cảnh báo/manifest export crop; areas.flags; ON giữ toàn nội dung chữ dài/multiline trước fit. Root bắt thêm overshoot popup clip, regression ĐỎ→XANH. Nhóm cuối 99 passed/24,12s; OFF AI/card+24popupframe byte-identical baseline sau fix. HUD outline chưa đo, không nghiệm thu mọi lớp chữ. Chưa commit/push; root đọc diff trước commit.
