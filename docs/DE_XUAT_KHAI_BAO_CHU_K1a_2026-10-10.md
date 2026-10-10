# Đề xuất `khai_bao_chu` — K1a (iv) + R1 (10/10)

**Trạng thái: ĐỀ XUẤT, CHƯA ghi CSDL.** Người dùng duyệt từng dòng (cột "Người dùng duyệt"), sau đó mới lưu vào `assets.profile`
qua 📋 Hồ sơ Kho (`core/assets.set_profile` kiểm `validate_khai_bao_chu`).

- Nguồn: `data/manifest.sqlite` bảng `assets` + `asset_images` (đọc `mode=ro`), ảnh mẫu trạng thái `approved`, xem bằng mắt (Claude).
- Khuôn A20: chữ = **món + màu chủ đạo (1–2) + ≤ 1 dấu hiệu** (`dau_hieu`); họa tiết (sọc, gai, rách…) chỉ ghi `hoa_tiet` cho QC sau gen.
- Không tả dáng / mặt / mắt (theo đề bài) → món `face` / `eyes` KHÔNG đề xuất; `declare_from_profile` sẽ còn VÀNG "chưa có ô" cho
  món mặt (suy từ must_keep) — người dùng quyết có cần ô cho mặt không.
- "không chắc" = không thấy rõ trên ảnh → không đưa vào JSON, chờ người dùng.

## 1. KELLY #23

Ảnh căn cứ: `data/assets/23/10.png` (bộ chuẩn 1, mặt trước, không súng, approved), `data/assets/23/1.png` (bảng thiết kế, approved).

| Món | Màu chủ đạo | Màu phụ | `dau_hieu` | Căn cứ trên ảnh | Lệch mô tả Kho / must_keep | Người dùng duyệt |
|---|---|---|---|---|---|---|
| hair (bob) | brown (nâu đậm) | — | blunt bangs | 10.png: bob ngang cằm, mái bằng | khớp must_keep. Mô tả Kho = cốt truyện, không tả màu | |
| choker | black | khoen bạc nhỏ | — | 10.png + 1.png "CHOKER DETAIL" | khớp | |
| crop top | white | viền cổ đen | — | 10.png: áo croptop trắng viền cổ đen | khớp | |
| tracksuit (áo khoác + quần) | yellow | trắng/xám nhạt, đen (sọc) | star stripes | 10.png: sọc dọc tay + ống quần nền trắng–xám nhạt, sao đen, viền đen | **lệch must_keep (nhẹ)**: must_keep ghi "grey sleeve stripes" — ảnh sọc gần TRẮNG (bảng màu 1.png `#F2F2F2`/`#C9C9C9`); must_keep ghi quần "black side stripe" — ảnh: sọc quần GIỐNG sọc tay (nền trắng sao đen, chỉ viền đen), không phải sọc đen | |
| sneakers | white | — | — | 10.png, 1.png "SNEAKER DETAIL" | khớp | |

R1 trên ảnh mẫu: 10.png sạch (nền xám trơn). 1.png là bảng thiết kế có CHỮ (`chu`), bóng người xám so chiều cao, vũ khí / phụ kiện
(thẻ ID, vòng tay) — vai `design_sheet`, nếu gửi làm ảnh tham chiếu thì R1 → VÀNG `ngoai_ho_so` (chữ) tới khi người duyệt `sach`.

## 2. YÊU NỮ TÀ LINH DẠNG 1 #418

Ảnh căn cứ: `data/assets/418/1.jpg` (trước), `2.jpg` (sau), `3.jpg` (cận mặt) — đều `approved`.

| Món | Màu chủ đạo | Màu phụ | `dau_hieu` | Căn cứ trên ảnh | Lệch mô tả Kho | Người dùng duyệt |
|---|---|---|---|---|---|---|
| hair | black, red | — | red lower half | 1.jpg + 2.jpg: đen ở trên, đỏ nửa dưới, dài rối | khớp ("tóc đen dài rối, nửa dưới chuyển đỏ") | |
| dress | white | xám (bẩn ở gấu) | off-the-shoulder | 1.jpg: trễ một vai, gấu rách răng cưa | khớp | |
| belt | **black** | khóa đỏ | red triangle buckle | 1.jpg: đai dây gai đen quấn eo, khóa tam giác viền đỏ ở giữa; dây gai bò xuống váy | **LỆCH: mô tả Kho "đai đỏ ngang eo"** → ảnh đai ĐEN, chỉ khóa tam giác đỏ. R1 bắt `mo_ta_lech` (belt red ↔ black). Đề xuất sửa mô tả: "đai dây gai đen ngang eo, khóa tam giác đỏ" | |
| arms | black | — | thorny vines | 1.jpg + 2.jpg: tay đen, dây gai đen quấn | khớp | |
| nails | red | — | — | 1.jpg + 2.jpg: móng nhọn đỏ | khớp | |
| stockings | black, red | — | fading to red | 1.jpg: tất đen mỏng rách ở đùi, đỏ dần từ gối xuống | khớp | |
| heels | red | — | — | 1.jpg (mũi nhọn) + 2.jpg (gót) | khớp | |
| glitch | red | trắng, lam | — | 1.jpg: vạch nhiễu ngang đỏ/trắng/lam | **lệch nhẹ (không chắc)**: mô tả nói "quanh cổ tay và chân"; ảnh có cả ở vai / ngực / gấu váy | |

R1 trên ảnh mẫu: **`3.jpg` bẩn** — nét khoanh ĐỎ vẽ tay quanh đầu/tóc (`nen_roi`), mảnh ảnh khác ở mép phải + góc trên phải
(`nguoi_khac`), vệt tím nhỏ ở mép trên (`khac`) → `asset_clean.check` = 3 VÀNG `ngoai_ho_so` (đã chạy). Đề xuất: không dùng `3.jpg`
làm tham chiếu tới khi cắt sạch + người duyệt `sach`. `1.jpg`, `2.jpg`: nền xám trơn, chỉ có glitch (thuộc hồ sơ) → sạch.

## 3. YÊU NỮ TÀ LINH DẠNG 2 #419

Ảnh căn cứ: `data/assets/419/1.jpg` (trước), `2.jpg` (sau), `3.jpg` (cận mặt) — đều `approved`. Phong cách truyện tranh nét gạch chéo.

| Món | Màu chủ đạo | Màu phụ | `dau_hieu` | Căn cứ trên ảnh | Lệch mô tả Kho | Người dùng duyệt |
|---|---|---|---|---|---|---|
| hair | white, red | — | red tips | 1.jpg + 2.jpg: trắng rất dài, lọn/ngọn đỏ | khớp | |
| dress | black | — | off-the-shoulder | 1.jpg: váy đen trễ vai, rách gấu | khớp | |
| belt | white | khóa đỏ | red triangle buckle | 1.jpg: dải trắng ngang eo, khóa tam giác đỏ | **thiếu trong mô tả Kho** (mô tả không nhắc đai; must_keep có "white belt with a red triangle") | |
| nails | red | — | — | 1.jpg + 2.jpg: móng nhọn đỏ | khớp (mô tả không nhắc móng) | |
| legs | red | đùi xám đen (trước) / trắng hồng (sau) | fading to red | 1.jpg + 2.jpg: chân chuyển đỏ dần xuống | khớp "chân đỏ dần" — ban đầu đề xuất black+red thì R1 báo `mo_ta_lech` (legs red ↔ black) → màu đùi KHÔNG CHẮC, chọn red | |
| heels | red | — | — | 2.jpg: gót đỏ; 1.jpg bàn chân đỏ nhọn | khớp | |
| comic linework | black, white | điểm đỏ, chấm lưới | — | toàn thân nét gạch chéo đen–trắng–đỏ | khớp | |
| arms | **không chắc** | — | — | 1.jpg: tay trái (người xem) TRẮNG nét gạch đen; tay phải đỏ–trắng; 2.jpg tương tự | **lệch (không chắc)**: mô tả + must_keep "tay đen vân trắng" — ảnh thấy tay trắng nét đen / đỏ. Chưa đưa vào JSON, chờ người dùng | |
| glitch | **không chắc** | — | — | không thấy rõ hiệu ứng nhiễu trên 1.jpg / 2.jpg | mô tả "quanh toàn thân luôn có glitch" — ảnh mẫu không thể hiện. Chưa đưa vào JSON | |

R1 trên ảnh mẫu: **`3.jpg` bẩn** — nét khoanh đỏ vẽ tay quanh tóc/đầu (`nen_roi`) → VÀNG. `1.jpg`, `2.jpg` sạch.
Ghi chú (không tả mặt): ảnh trước thấy một mắt, cận mặt thấy hai mắt — thuộc món mặt, người dùng quyết.

## 4. JSON đề xuất (đúng schema `validate_khai_bao_chu`)

Kết quả chạy (`py`, 10/10, script đọc CSDL `mode=ro`): `validate_khai_bao_chu` = `[]` cho cả 3 bản. `asset_clean.check([], hồ sơ +
khai_bao_chu đề xuất, mô tả Kho)`: #23 `[]`, #418 `mo_ta_lech belt` (đúng ca cần bắt), #419 `[]`. `declare_from_profile` còn VÀNG
"chưa có ô": #418 `face`; #419 `face`, `hands`, `glitch` (món không chắc / mặt — chờ người dùng).

```json
{
 "23": [
  {"mon": "hair", "dong_nghia": ["bob"], "mau_chinh": ["brown"], "mau_dong_nghia": {"brown": ["dark brown"]}, "dau_hieu": "blunt bangs", "cach_viet": ["straight bangs", "straight fringe"], "hoa_tiet": []},
  {"mon": "choker", "mau_chinh": ["black"], "dau_hieu": null, "hoa_tiet": ["khoen bạc nhỏ phía trước"]},
  {"mon": "crop top", "mau_chinh": ["white"], "dau_hieu": null, "hoa_tiet": ["viền cổ đen"]},
  {"mon": "tracksuit", "dong_nghia": ["track jacket", "track pants", "track suit"], "mau_chinh": ["yellow"], "dau_hieu": "star stripes", "cach_viet": ["star-print stripes", "stripes with black stars"], "hoa_tiet": ["sọc trắng–xám nhạt có sao đen + viền đen dọc tay áo và ống quần", "cổ đứng, khóa kéo bạc, bo gấu"]},
  {"mon": "sneakers", "mau_chinh": ["white"], "dau_hieu": null}
 ],
 "418": [
  {"mon": "hair", "mau_chinh": ["black", "red"], "dau_hieu": "red lower half", "cach_viet": ["turning red in the lower half", "black-to-red ombre"], "hoa_tiet": ["dài, rối, lượn sóng"]},
  {"mon": "dress", "dong_nghia": ["gown"], "mau_chinh": ["white"], "dau_hieu": "off-the-shoulder", "cach_viet": ["off the shoulder"], "hoa_tiet": ["gấu rách răng cưa"]},
  {"mon": "belt", "dong_nghia": ["thorny vine belt", "vine belt"], "mau_chinh": ["black"], "dau_hieu": "red triangle buckle", "cach_viet": ["red triangular buckle"], "hoa_tiet": ["dây gai đen bò xuống váy"]},
  {"mon": "arms", "mau_chinh": ["black"], "dau_hieu": "thorny vines", "cach_viet": ["wrapped in black vines"]},
  {"mon": "nails", "dong_nghia": ["claws"], "mau_chinh": ["red"], "dau_hieu": null},
  {"mon": "stockings", "mau_chinh": ["black", "red"], "dau_hieu": "fading to red", "cach_viet": ["black-to-red gradient"], "hoa_tiet": ["rách ở đùi"]},
  {"mon": "heels", "dong_nghia": ["high heels"], "mau_chinh": ["red"], "dau_hieu": null},
  {"mon": "glitch", "dong_nghia": ["glitch noise"], "mau_chinh": ["red"], "dau_hieu": null, "hoa_tiet": ["vạch ngang đỏ / trắng / lam"]}
 ],
 "419": [
  {"mon": "hair", "mau_chinh": ["white", "red"], "dau_hieu": "red tips", "cach_viet": ["red-tipped", "red streaks"], "hoa_tiet": ["rất dài, lượn sóng"]},
  {"mon": "dress", "dong_nghia": ["gown"], "mau_chinh": ["black"], "dau_hieu": "off-the-shoulder", "cach_viet": ["off the shoulder"], "hoa_tiet": ["gấu rách"]},
  {"mon": "belt", "mau_chinh": ["white"], "dau_hieu": "red triangle buckle", "cach_viet": ["red triangular buckle"]},
  {"mon": "nails", "dong_nghia": ["claws"], "mau_chinh": ["red"], "dau_hieu": null},
  {"mon": "legs", "mau_chinh": ["red"], "dau_hieu": "fading to red", "cach_viet": ["gradient to red"], "hoa_tiet": ["đùi xám đen (trước) / trắng hồng (sau) chuyển đỏ xuống bàn chân"]},
  {"mon": "heels", "dong_nghia": ["high heels"], "mau_chinh": ["red"], "dau_hieu": null},
  {"mon": "comic linework", "dong_nghia": ["crosshatch linework", "manga linework"], "mau_chinh": ["black", "white"], "dau_hieu": null, "hoa_tiet": ["điểm đỏ", "chấm lưới halftone"]}
 ]
}
```

## 5. Việc người dùng cần quyết
1. Duyệt từng dòng bảng 1–3 (cột "Người dùng duyệt"); có cần ô cho món mặt / mắt không.
2. #418: sửa mô tả Kho "đai đỏ ngang eo" → "đai dây gai đen ngang eo, khóa tam giác đỏ" (R1 `mo_ta_lech`).
3. #419: màu tay (mô tả "tay đen vân trắng" ↔ ảnh tay trắng nét đen / đỏ) và glitch (ảnh không thấy) — sửa mô tả hay giữ.
4. #23: sửa must_keep "grey sleeve stripes" / "black side stripe" cho khớp ảnh (sọc trắng–xám nhạt sao đen, viền đen) hay giữ.
5. Ảnh `418/3.jpg`, `419/3.jpg` (nét khoanh đỏ + mảnh ảnh thừa): cắt sạch rồi duyệt `sach`, hoặc đánh `ban` (không gửi làm tham chiếu).
