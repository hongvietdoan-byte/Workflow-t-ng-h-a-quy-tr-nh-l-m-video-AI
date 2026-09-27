"""Features that change what is sent to a paid model but have not passed a real test (rule 5 of docs/CHUAN_XAY_DUNG.md): off by default
and kept out of the autopilot until a real run closes their test. `FEATURE_<NAME>=1` switches one on (e.g. for the GĐ-I trials).
When a real test passes, set `verified` to True here with the date and the report that shows it."""
import os
from typing import Dict

FEATURES: Dict[str, Dict] = {
    "layout_to_model": {
        "label": "Gửi ảnh bố cục ghép (nền map + hình cắt nhân vật) cho model ảnh",
        "verified": False,
        "why": "GĐ6 (R7/L1): model chép luôn góc máy từ trên cao và cỡ người tí hon của ảnh ghép, bất kể cỡ cảnh của shot",
    },
    "chain_previous_auto": {
        "label": "Tự nối ảnh shot trước làm ảnh tham chiếu trong cùng chuỗi",
        "verified": False,
        "why": "GĐ6 (F8/I2): nối bất kể cỡ cảnh/góc máy → shot cận kéo theo bố cục toàn cảnh của shot trước",
    },
    "voice_check_redo": {
        "label": "Chạy tự động: tạo lại giọng thoại bị cờ lỗi (cắt/thiếu chữ/ngắt quãng) một lần",
        "verified": False,
        "why": "AU-f mới (2026-09-24): ngưỡng độ dài/im lặng và so chữ nghe được chưa đo trên giọng Việt thật — cờ sai thì trả tiền TTS vô ích",
    },
    "film_crew": {
        "label": "Tổ làm phim: Director đọc bộ nguyên tắc Đạo diễn + Quay phim (knowledge/roles/) thay cho 3 tài liệu rải rác (cinematography_basics, film_director_method, dialogue_craft), ghi tradeoffs",
        "verified": False,
        "why": "Kế hoạch V4 GĐ4: bộ kỹ năng nghề 3 vai (đã chấm độc lập, docs/DANH_GIA_BO_NGUYEN_TAC_V4.md) chờ người dùng duyệt; "
               "chưa có lần Director thật nào chạy với bộ mới",
    },
    "director_two_pass": {
        "label": "Director hai lượt (dự án chia shot): Tầng A Đạo diễn viết Bible + ý đồ từng cảnh, Tầng B Quay phim chia shot MỖI cảnh "
                 "một lượt (phần chung cache), code Đạo diễn duyệt bảng shot so với ý đồ",
        "verified": False,
        "why": "Kế hoạch V4 GĐ5 (H2/H7, 2026-09-26): mới thử bằng Claude giả lập — chưa có lần Director thật nào chạy hai lượt để so chất "
               "lượng và tiền với một lượt (core/director_two_pass.py)",
    },
    "voice_direction": {
        "label": "Chỉ đạo giọng lồng: câu thoại có `delivery` (cảm xúc, cường độ, nhịp, ngắt, nhấn, thẻ v3) → tham số TTS + chữ gửi TTS",
        "verified": False,
        "why": "GĐ4 (director.md Đ5): tài liệu ElevenLabs tự mâu thuẫn về tham số áp dụng cho eleven_v3 (speed); thẻ [whispers] với giọng Việt "
               "chưa nghe thử — cần tạo thử vài câu (tốn lượt âm thanh) trước khi bật",
    },
    "loudness_normalize": {
        "label": "Chuẩn hóa độ to bản giao về −14 LUFS / đỉnh thật −1,5 dBTP (loudnorm 2 lượt, tăng/giảm tuyến tính) khi số đo lệch mục tiêu",
        "verified": False,
        "why": "GĐ4 (editing.md E8, D11): không nền tảng nào công bố LUFS; bản giao #7 đo −14,7 LUFS (đã đạt) — chưa nghe thử một bản "
               "được chuẩn hóa trên điện thoại",
    },
    "shot_color_match": {
        "label": "Khớp màu giữa các shot cùng nơi + cùng nhóm cỡ cảnh (điểm đen/trắng, ám màu của vật xám) — sửa bản sao clip lệch trước khi dựng",
        "verified": False,
        "why": "GĐ4 (editing.md E5, D7): đo thật #7 thấy 2/7 shot lệch điểm đen/trắng 0,14–0,15 (một phần do nội dung khung); sửa thử đưa "
               "về ~0,04 — chưa có người xem bản dựng đã khớp màu",
    },
    "j_cut": {
        "label": "Cắt J: câu của người nói mới vào sớm 0,25 s trước khi hình cắt sang shot của họ (không đè câu trước)",
        "verified": False,
        "why": "GĐ4 (editing.md E1, D1): chưa nghe thử bản dựng có cắt J trên giọng Việt lồng — phụ đề đi theo giọng nên cũng vào sớm",
    },
    "music_breath": {
        "label": "Nhạc lặng 0,6 s ngay trước cú ngoặt (phần kịch bản TWIST / CAO TRÀO, hoặc shot ⭐ đầu tiên)",
        "verified": False,
        "why": "GĐ4 (editing.md E4, D6): chưa nghe thử; khoảng lặng dài/ngắn là gu dựng — bật khi người dùng nghe và đồng ý",
    },
    "sound_intent": {
        "label": "Nhạc theo ý đồ âm thanh của Đạo diễn từng shot: tắt hẳn từ shot 'cut' tới shot 'in', lặng 0,6 s trước shot 'breath'",
        "verified": False,
        "why": "2026-09-26 (director.md Đ9, bài học Handbook ch. V): chưa nghe thử bản dựng có nhạc ngắt theo shot; tắt thì bản dựng "
               "ghi lại số ý đồ chưa áp (manifest `sound_intent`)",
    },
    "impact_shake": {
        "label": "Rung khung hình 0,25 s ở những giây có hiệu ứng va chạm / nổ / súng trong bản trộn",
        "verified": False,
        "why": "GĐ4 (editing.md E6, D9): chưa xem thử trên bản dựng thật; rung sai chỗ làm người xem khó chịu",
    },
    "name_cards": {
        "label": "Bảng tên nhân vật (kiểu thông báo game) ở lần đầu mỗi nhân vật xuất hiện",
        "verified": False,
        "why": "GĐ4 (editing.md E6, D10): dùng kiểu chữ thông báo game sẵn có; chưa xem thử — người dùng chọn có cần không",
    },
    "ambience_bed": {
        "label": "Âm nền mỗi cảnh từ thư viện âm thanh của bạn (theo thời tiết → giờ → bối cảnh), nhỏ dưới thoại, lặp đủ dài",
        "verified": False,
        "why": "GĐ4 (editing.md E3, D4/D5): thử #7 — cảnh ngày khu nhà trên đảo nhận 'Bird Ambience'; cảnh đêm không có âm đêm trong "
               "thư viện nên để trống (báo) — chưa nghe bản trộn",
    },
    "speed_ramp": {
        "label": "Quay chậm / dừng hình khi cắt shot: shot không thoại có `speed` < 1 (nội suy khung) hoặc `freeze_end_s` (editing.md E10)",
        "verified": False,
        "why": "2026-09-26 (người chấm bộ 3 vai): đã thử bằng ffmpeg trên clip mẫu (test), chưa xem trên clip Kling/Seedance thật — nội "
               "suy chuyển động có thể làm méo tay/vũ khí khi chuyển động nhanh; xem A/B trên clip có sẵn trước khi bật",
    },
    "motion_trim": {
        "label": "Cắt shot từ clip dài: dời điểm bắt đầu (≤ 1 s) khi hành động chính đến muộn (đo chuyển động trong clip)",
        "verified": False,
        "why": "GĐ4 (editing.md E1, D2): thử #7 shot 3 — giọt lệ lăn từ 1,1 s, bộ chọn dời 1,0 s (hợp lý); rủi ro: model tự chèn cảnh "
               "khác cuối clip cũng là 'chuyển động mạnh' — giới hạn 1 s, bỏ qua shot thoại / nối liền / khớp môi",
    },
    "profile_digest": {
        "label": "Hồ sơ nhân vật rút gọn: prompt ảnh dùng lock_medium (≤ 500 ký tự), prompt video dùng lock_short (≤ 200) thay cho bản đầy đủ",
        "verified": False,
        "why": "V4 4.4 (core/profile_digest.py): bản rút gọn bỏ bớt chi tiết — chưa đo model ảnh có giữ đúng nhân vật với bản ngắn không (GĐ8)",
    },
    "camera_setups": {
        "label": "Quay theo vị trí máy: Director/Quay phim gán camera_setup cho shot (một clip cho nhiều shot cùng góc)",
        "verified": False,
        "why": "Chạy thử 2A (H5): một cặp shot tiết kiệm 33% nhưng mất khung nhấn riêng — cần thử thêm ở cảnh thoại dày trước khi bật",
    },
    "seedance_ref_groups": {
        "label": "Video Seedance chỉ ảnh tham chiếu (đánh dấu tờ thiết kế): gộp 2–4 shot liền của một cảnh thành một lần gen (mỗi shot có "
                 "ảnh storyboard riêng) → bị từ chối thì Seedance từng shot → rồi Kling (người dùng chốt thứ tự 2026-09-27). Thay nhóm H5",
        "verified": False,
        "why": "Thử 2026-09-27 (docs/PHAN_TICH_GOP_SHOT_2026-09-27.md mục 6): 2/2 lần gen qua bộ lọc, cắt 3 shot đúng storyboard — mới thử "
               "bằng công cụ riêng trên 1 cảnh ban ngày, chưa chạy qua luồng chính / cảnh tháp đêm / cắt clip theo điểm cắt dò được",
    },
    "scene_qc": {
        "label": "QC theo cảnh: lớp 0 bằng code (số mặt, cỡ cảnh đo bằng mặt, vùng an toàn, mặt đủ sáng) + lớp 1 Claude MỘT lượt mỗi cảnh "
                 "(tấm ghép các khung + ảnh toàn cảnh + ảnh chuẩn nhân vật, hỏi có/không kèm bằng chứng) — thay QC từng ảnh + QC đồng bộ",
        "verified": False,
        "why": "Rà soát 2026-09-27 (docs/RA_SOAT_CLAUDE_KY_NANG_2026-09-27.md): QC từng ảnh không phân biệt ảnh lỗi (0,67) với ảnh tốt (0,69) "
               "trên 54 ảnh #8 — QC mới chưa đo trên bộ nhãn",
    },
    "scene_qc_trusted": {
        "label": "Cho QC theo cảnh (lớp 1, Claude) TỰ duyệt / tự vẽ lại — chỉ bật khi đã qua nghiệm thu (bắt đủ lỗi nhìn thấy rõ, báo nhầm ≤ 10 %)",
        "verified": False,
        "why": "Nghiệm thu 2026-09-27 trên 33 ảnh ghép có nhãn của #8 (tools/experiments/qc_regression.py): bắt 6/12 lỗi rõ nhưng không lần "
               "nào vì đúng lỗi, cho qua 6 khung chữ nhật dán + tháp Big Ben, báo nhầm 12/21 ảnh tốt → khi tắt: mọi khung chờ người, "
               "nhận xét của QC chỉ là ghi chú",
    },
    "scene_establishing": {
        "label": "Mỗi cảnh kịch bản một ảnh toàn cảnh ngang 2048×1152 (nơi chốn + giờ + ánh sáng, không người) vẽ từ ảnh bối cảnh của Kho, "
                 "làm ảnh tham chiếu nơi chốn chung cho mọi shot của cảnh; câu ánh sáng theo giờ (đêm vẫn sáng mặt)",
        "verified": False,
        "why": "Thử 2026-09-27 (#8 cảnh 1, tools/experiments/scene_wide_test.py): 1 ảnh ngang + 4 khung storyboard ngang/hơn 4 frame #7 — "
               "mới 1 cảnh đêm; chưa thử cảnh ngày, chưa qua luồng chính",
    },
    "lip_sync": {
        "label": "Khớp môi: shot cận đánh dấu được Seedance tạo kèm giọng (người dùng chốt 2026-09-26 không dùng sync.so — shot trung/toàn "
                 "không khớp môi, được báo)",
        "verified": False,
        "why": "Kế hoạch V4 GĐ3: chưa thử thật; Seedance không công bố hỗ trợ tiếng Việt — thử 1 shot cận giọng Việt (~$0,60) trước khi tin",
    },
    "storyboard_api": {
        "label": "Vẽ ảnh các shot của một cảnh bằng MỘT storyboard Deepix (shot rộng nhất làm neo, cùng ảnh tham chiếu) — cách Weave Canvas",
        "verified": False,
        "why": "Thử #7 cảnh 1 (2026-09-25): 4 khung giữ tháp/ánh sáng liền mạch hơn ảnh vẽ riêng; mới 1 cảnh, chưa thử cảnh đông người / hành động",
    },
    "location_plates": {
        "label": "Gói bối cảnh: nền là ảnh render 3D của bối cảnh (đúng góc máy shot), AI chỉ vẽ nhân vật trên phông xanh rồi ghép",
        "verified": False,
        "why": "Kế hoạch V4 mục 1: đã render + ghép thật miễn phí (2026-09-25); chưa thử ảnh phông xanh Deepix thật và clip thật (GĐ8)",
    },
    "end_frames": {
        "label": "Ảnh khung cuối cho shot có end_state (vẽ thêm 1 ảnh, gửi clip khung đầu + cuối)",
        "verified": False,
        "why": "K1/K2 (kế hoạch tổng K-a): tốn thêm 1 ảnh mỗi shot đổi trạng thái; chưa thử thật Kling end_frame với khung vẽ từ ảnh đầu",
    },
    "storyboard_auto_trust": {
        "label": "Tự bỏ qua cổng duyệt storyboard khi QC đã đủ tin cậy (≥ 90% khớp người trên ≥ 50 ảnh cùng look) và storyboard không có cờ",
        "verified": False,
        "why": "W8 (kế hoạch tổng): chưa có đủ ảnh người duyệt cùng look để đo — bật khi số đo đạt và người dùng đồng ý",
    },
    "setcheck_autofix": {
        "label": "QC đồng bộ cả bộ ảnh tự gen lại ảnh lệch (autopilot)",
        "verified": False,
        "why": "GĐ6 (R3/I4): chuẩn theo số đông của bộ ảnh, sửa sai người (Kenta→Maxim) rồi tự trả tiền gen lại",
    },
}


def on(name: str) -> bool:
    """True when the feature passed its real test, or the person switched it on with FEATURE_<NAME>=1 (0 switches it off)."""
    env = os.environ.get("FEATURE_" + name.upper(), "").strip().lower()
    if env in ("1", "true", "on", "yes"):
        return True
    if env in ("0", "false", "off", "no"):
        return False
    return bool(FEATURES[name]["verified"])


def pending() -> Dict[str, Dict]:
    """Features still waiting for their real test (shown to the person so an off feature is never a mystery)."""
    return {k: v for k, v in FEATURES.items() if not on(k)}
