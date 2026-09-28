"""Write knowledge/ff_styles/<STYLE>.md: hand-written guidance + numbers measured from research/ff_styles (core.reference_analysis).
Run again after analysing more reference videos:  py tools/ff_style_knowledge.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))
from core import reference_analysis as ra  # noqa: E402

OUT = os.path.join("knowledge", "ff_styles")
os.makedirs(OUT, exist_ok=True)

NOTE = ("> Các con số dưới đây là **khoảng tham khảo** đo từ video Free Fire thật, không phải nhịp cố định: độ dài từng shot do "
        "kịch bản quyết định (beat, câu thoại, cảm xúc). Dùng chúng để biết shot kiểu gì thường dài/ngắn cỡ nào và phong cách này "
        "hay dùng cỡ cảnh, chuyển động, chữ trên hình ra sao.\n")

GUIDE = {
"ANIME_CGI": """# Phong cách: Anime / hoạt hình CGI (Free Fire)

Ví dụ: "Kenta's Obsession" (phim ngắn chính thức), "Oscar – The Toxic Tanker", "Chiến Binh Thỏ" (hoạt hình, bản Việt hóa).

## Cách dựng
- **Mở** bằng một hình ảnh gây tò mò (kẻ giám sát trước màn hình, hình bóng đe dọa, toàn cảnh phố đêm từ cao) rồi vào ngay nhân vật chính — thiết lập trong 2–4 shot ngắn.
- **Thân**: nhịp nhanh nhất trong các phong cách. Hành động cắt ngắn, **xen cận mặt phản ứng sau mỗi nhịp hành động**; cao trào dồn chuỗi cận/cận đặc tả (bàn tay, mắt, vũ khí) ~1s/shot.
- **Thoại**: shot/đáp trung cận, ít thoại; đoạn đối thoại tĩnh cho shot dài hơn hẳn đoạn hành động.
- **Kết** bằng động tác tạo dáng hoặc một cận chi tiết có ý nghĩa (bàn tay) rồi logo.
- Nhân vật xuất hiện có "màn chào sân" (nhảy từ trên cao, sét đánh xuống). Giới thiệu nhiều nhân vật theo công thức: hành động khoe kỹ năng → chữ tên cách điệu → phản ứng của nhân vật chính.

## Look (gợi ý World Bible)
Anime cel-shade viền đen mảnh/đậm, màu phẳng; **đổi nhiệt màu theo hồi** (đêm xanh lạnh → lửa cam → phòng vàng ấm); VFX sét/lửa/khói tròn kiểu hoạt hình.

## Khi dùng cho AI video
Nhịp nhanh nghĩa là nhiều shot ngắn hơn thời lượng tối thiểu của model → nên gom shot liền mạch cùng nhóm (multi-shot) hoặc cắt từ clip dài hơn. Cận mặt phản ứng rẻ và dễ giữ nhân vật — dùng nhiều.
""",
"INGAME": """# Phong cách: Gameplay trong game (video kỹ năng, mẹo, cập nhật phiên bản)

Ví dụ nội bộ OB55: Tình huống sử dụng Kenta, Combo Kenta, Combo ném lựu lửa, Lựu đạn dò, Túi cứu thương, Điều chỉnh vũ khí, Top 3 mở trạm, Tối ưu ngựa.

## Cách dựng
- **Mở lạnh** bằng khoảnh khắc đắt nhất (pha hạ gục, kỹ năng) hoặc nhân vật tạo dáng ở sảnh + **tiêu đề lớn chữ vàng**, rồi mới vào nội dung.
- **Thân** chia chương; **mỗi chương mở bằng một câu chữ vàng** (tên tình huống hoặc câu giải thích) giữ trên cả chuỗi shot.
- Gần như toàn bộ là **camera game — góc thứ ba sau lưng nhân vật (`GAME_TPS`)**, giữ nguyên giao diện game (HUD, "Monster Kill", bảng hạ gục) như phần thưởng cho người xem.
- Chèn shot rất ngắn 0,3–0,5s: ống ngắm cận, hiệu ứng kỹ năng/flash làm chuyển, khoảnh khắc lộ địch/hạ gục.
- Video so sánh phiên bản: **màn hình chia đôi** trên/dưới, nhãn phiên bản cố định, shot dài 6–13s cho người xem kịp so.
- Con số then chốt thành chữ lớn giữa màn hình ("3 GIÂY"); thông số: xanh = tăng, đỏ = giảm.
- **Kết** bằng nhân vật trình diễn ở sảnh + câu hỏi kêu gọi + ngày cập nhật (hoặc kết mở bằng một pha gameplay).

## Look
Render gốc của game, màu tươi bão hòa, trời xanh; sảnh nền tím; chữ vàng/trắng viền đen font game.

## Khi dùng cho AI video
Model video khó tái tạo HUD đúng — ưu tiên đặt chữ/giao diện bằng hậu kỳ (card, phụ đề) thay vì bắt model vẽ. Góc `GAME_TPS` cần mô tả rõ: camera sau lưng, cao hơn vai, nhân vật ở 1/3 dưới khung.
""",
"KELLY_SHOW": """# Phong cách: Kelly Show (người dẫn là nhân vật game, tiểu phẩm giới thiệu)

Ví dụ: "Ninjas Return to OB55 – Nine-Tails Attacks Bermuda | Kelly Show". **Dữ liệu mỏng (1 video)** — dùng làm định hướng, chưa phải quy luật.

## Cách dựng
- **Mở** bằng toàn cảnh map/sự kiện (hook), lia nhanh vào **Kelly nói thẳng vào máy quay** giới thiệu.
- **Thân** theo chương tính năng; **mỗi chương mở bằng thẻ "Kelly Show"** (cờ vàng–tím–trắng) — thẻ lặp 4–5 lần/tập làm nhịp.
- Bên trong chương: Kelly chơi thử (gameplay có lời dẫn + phụ đề nhỏ), giao diện game đặt **trong khung trang trí** thay vì toàn màn hình, chèn cảnh anime/CGI của sự kiện.
- **Kết** bằng cận người dẫn nói lời kết, chớp trắng, logo show.

## Look
Kelly CGI tả thực trong map game; khung sự kiện viền vàng; chữ trắng viền đen.

## Khi dùng cho AI video (kịch bản hài có nhiều nhân vật)
Người dẫn/nhân vật nói thẳng vào máy quay ở trung cận là shot dễ làm và giữ nhân vật tốt; lời dẫn đặt đè lên các shot hành động bằng TTS + phụ đề. Thẻ chương/tiêu đề làm bằng card hậu kỳ.
""",
"REAL_CGI_VFX": """# Phong cách: CGI tả thực / phim kỹ xảo (trailer sự kiện, giới thiệu trang phục)

Ví dụ: "Thánh Nữ Tái Sinh – phim kỹ xảo", "Thẻ Vô Cực 11 – Kẻ Giết Rồng", "Phi Vụ Cuối Cùng", CGI trailer "Bí Ẩn Biển Sâu".

## Cách dựng
- **Mở** bằng hook không khí (cận thấp chiến binh trong lửa, phòng tối có màn hình) hoặc hook hài của nhân vật chính (teaser ngắn).
- **Thân**: nhịp chậm hơn anime. Hai kiểu: (a) **cú máy liền dài** bay/vòng qua nhân vật 5–10s xen shot chèn ngắn 1–2s (trăng, vũ khí); (b) **chuỗi cận đặc tả** giáp/vũ khí/thiết bị 0,6–2s xen **cú máy vòng chậm** khoe trang phục.
- Đối thoại (nếu có) để shot dài 4–12s ở toàn/trung, xen cận phản ứng rất ngắn (~0,6s).
- **Kết** bằng "money shot" toàn cảnh (rồng bay, núi vàng) hoặc nhân vật nhìn thẳng máy quay → logo sự kiện; chuyển bằng chớp trắng, nhiễu màu, mực loang.

## Look
CGI tả thực, tương phản cao, tông đơn sắc theo sự kiện (đỏ–đen, xanh biển phát sáng), khói, tàn lửa, ánh sáng nguồn rõ (cửa sổ, trăng).

## Khi dùng cho AI video
Cú máy vòng/bay dài hợp với Seedance (mô tả đường máy điểm đầu–cuối); cận đặc tả chất liệu là thế mạnh của Seedance 2.5. Money shot cuối là shot đáng chi nhiều nhất.
""",
"SHORT_FILM": """# Phong cách: Phim ngắn (kể chuyện có hồi, CGI tạo hình game hoặc dựng trong engine game)

Ví dụ: "Pitch Party" (Free Fire Short Film), "The Last Hero" (dựng trong engine game), "Free Fire x Blue Lock – phim ngắn".

## Cách dựng
- **Mở** bằng mục tiêu/hook (cúp vàng giữa phố, cầu thủ lao đi + chớp sáng) rồi toàn cảnh địa điểm.
- **Thân** kể theo hồi; **mỗi hồi mở bằng toàn cảnh địa điểm**; thẻ chữ nhảy thời gian ("1 NGÀY SAU…"). Cao trào: montage 0,5–1,5s/shot xen cận chi tiết (chân–bóng–lưới) và **cận mắt/mặt phản ứng** sau mỗi pha.
- Dùng một yếu tố làm mốc nhịp kể (bảng tỉ số), một chữ ký hình ảnh (vệt sáng xanh cho cú sút).
- Mô hình game ít biểu cảm mặt → dựng bằng toàn/trung + hành động; thoại qua giọng lồng + phụ đề.
- **Kết** bằng khoảnh khắc chiến thắng / nhân vật nhìn thẳng máy quay → logo sự kiện, logo game.

## Look
CGI 3D tạo hình nhân vật Free Fire (hoặc machinima trong map thật), ánh sáng sân vận động đêm / nắng trời xanh, VFX lửa–băng rực.

## Khi dùng cho AI video
Hợp với kịch bản có nhiều nhân vật và hành động nối tiếp (như "Kenta cướp kill"): mỗi hồi một nhóm cảnh (`sequence`), mở bằng toàn cảnh, cao trào cắt nhanh, phản ứng xen giữa.
""",
"DRAMA_DOC": """# Phong cách: Drama ngắn dọc (kiểu ReelShort, lồng tiếng Việt)

> **GỢI Ý THAM KHẢO, KHÔNG BẮT BUỘC** (người dùng 2026-09-28): đây là cách MỘT phim thật đã dựng. Chọn điều hợp với kịch bản, trộn với
> phong cách khác, làm khác khi kịch bản cần — không phải khung chung cho mọi phim.

Ví dụ: "(Lồng tiếng) Từ Hôn Năm Người Bạn Đời Định Mệnh" (ReelShort) — 5 đoạn × 2–3 phút đo trong trình duyệt ngày 2026-09-28 (kế hoạch
sau #8, S0; phiếu đầy đủ: research/ff_styles/DRAMA_DOC/PHIEU_bzsP_ArSIUA.md). Không phải video Free Fire: dùng để học **ngữ pháp dựng
drama dọc** cho phim truyện có thoại.

## Cách dựng
- **Mở** thẳng vào mâu thuẫn: 1 toàn cảnh bối cảnh rồi ngay cận mặt người nói — không logo, không dạo đầu.
- **Thoại**: mỗi lượt nói = 1 shot cận / trung cận của **người đang nói**; cắt sang người nghe bằng shot phản ứng xen giữa; khi hai bên ngắt
  lời nhau shot rút xuống 0,3–0,7 s. **Không dùng qua vai** (0/397 shot). Hiếm khi giữ hai người cùng khung trừ shot thiết lập.
- **Máy gần như luôn tĩnh** (98 %); đẩy máy vào (push-in) chỉ ở khoảnh khắc lặng / xúc động, và shot đó dài gấp ~2 lần shot quanh nó.
- **Xung đột / bạo lực qua hậu quả** (cận đặc tả máu, dao, vết thương), gần như không quay va chạm trực tiếp; shot "hành động" rất ngắn.
- **Hồi tưởng** có dấu hiệu rõ: cả đoạn chuyển **đen trắng** (vào bằng hòa hình, ra bằng 1 khung lóa trắng ~0,4 s), hoặc giữ màu nhưng
  hòa hình vào + lóa trắng ra.
- **Tên nhân vật**: chữ nhỏ trên khung chỉ ở LẦN GIỚI THIỆU ĐẦU TIÊN (hiện suốt shot đó), không lặp lại.
- **Kết** đoạn / tập bằng cao trào có câu hỏi treo (cliffhanger).

## Look
Tả thực kiểu phim cổ trang / lâu đài; nhiều cảnh tối tương phản cao xen cảnh sáng; phụ đề chữ trắng nền mờ gần đáy trong vùng an toàn.

## Khi dùng cho AI video
- Nhịp cắt ~1,9 s/shot là bình thường cho drama dọc — **không** kéo dài shot để "bớt giật"; cái làm giật ở #8 là mỗi shot gen riêng nên
  chuyển động bắt đầu lại từ đầu (S3.4: gen đoạn diễn liên tục rồi cắt xen).
- Thoại dựng bằng cận người nói → **khớp môi quan trọng hơn** mọi thứ khác ở shot thoại (S4.2).
- Ít cỡ cảnh (cận / trung cận ~79 %) nhưng đổi người trong khung liên tục — đa dạng đến từ người, không từ cỡ cảnh.
- Hồi tưởng phải có dấu hiệu hình (đen trắng hoặc lóa trắng) — cờ `flashback_fx` (S1.7) làm đúng việc này.
""",
"MV_NARRATIVE": """# Phong cách: MV kể chuyện (clip mẫu làm bằng ClipAI)

> **GỢI Ý THAM KHẢO, KHÔNG BẮT BUỘC.** Người dùng 2026-09-29: máy quay, góc, dựng, âm thanh không có nghĩa mặc định — ghi ở đây là **cách
> MỘT clip đã làm và ý đồ ở chỗ đó**, để chọn khi ý đồ cảnh cần, không phải công thức.

Ví dụ: clip mẫu người dùng gửi 2026-09-28 — MV 201 s, 16:9, 62 shot (phân tích + mốc giây:
`docs/PHAN_TICH_CLIP_MAU_CLIPAI_2026-09-28.md`). Không phải video Free Fire.

## Clip này đã làm gì
- Quy ước MV: bài hát có trước, mỗi câu hát ≈ một shot minh họa câu, cắt ở ranh câu. (Phim thoại không cần theo.)
- Một bối cảnh chính nhìn nhiều góc + vài biến thể (sân khấu neon, thế giới phóng to, cửa ra mưa); mở và kết cùng hình ảnh mưa.
- Chuyển động toàn thân mượt: nhảy nhóm đồng bộ, breakdance, váy xoay có vật lý vải; shot bắt đầu khi nhân vật đã đang chuyển động.
- Chuyển cảnh bằng chuyển động máy trong cùng clip (xuyên đèn chùm xuống mặt bàn); nối bằng cử chỉ có chủ ý (tay lật quân Át lóe sáng).
- Nhân vật đám đông mũ trùm không mặt, nhân vật chính nhiều dấu hiệu nhận diện — lựa chọn sản xuất giúp AI giữ nhất quán.

## Look
Một bảng màu (tím–vàng, sàn bóng phản chiếu); đổi ánh sáng khi truyện đổi (đêm mưa → sáng sau mưa).

## Khi dùng cho AI video
- Động tác khó: cân nhắc video tham chiếu chuyển động (suy luận) và đầu vào không ép dáng (Director Workspace ClipAI khuyên).
- Shot trung vị 2,5 s; nhạc −14,6 LUFS liên tục — số của một clip, không phải mục tiêu.
""",
"FAN_3D": """# Phong cách: Hoạt hình 3D do fan làm (viral)

**Chưa có dữ liệu** — video fan 3D chưa được phân tích (xem "Việc để sau — phân tích video" trong kế hoạch v3). Tạm thời:
- Cách dựng: dựa **SHORT_FILM** (kể có hồi, hành động nối tiếp) + nhịp nhanh và cận phản ứng của **ANIME_CGI**.
- Đặc trưng thường thấy ở video fan viral (chưa đo): hook trong 1–2 giây đầu, hài/twist cuối, nhân vật game quen thuộc, tỉ lệ khung dọc 9:16.
Khi có dữ liệu, thay mục này bằng số liệu đo được.
""",
}


def main():
    for style, guide in GUIDE.items():
        recs = ra.load_records(style)
        parts = [guide.rstrip() + "\n"]
        if recs:
            parts.append("\n" + NOTE + "\n" + ra.stats_markdown(style, ra.style_stats(recs)) + "\n")
            srcs = "\n".join(f"- {r.get('title')}" + (f" — {r['source']}" if str(r.get('source', '')).startswith('http') else " (nội bộ)")
                             for r in recs)
            parts.append("\n## Nguồn đã phân tích (" + str(len(recs)) + " video)\n" + srcs + "\n")
        with io.open(os.path.join(OUT, f"{style}.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(parts))
        print(style, len(recs))


if __name__ == "__main__":
    main()
