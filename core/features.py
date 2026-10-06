"""Features that change what is sent to a paid model but have not passed a real test (rule 5 of docs/CHUAN_XAY_DUNG.md): off by default
and kept out of the autopilot until a real run closes their test. `FEATURE_<NAME>=1` switches one on (e.g. for the GĐ-I trials).
When a real test passes, set `verified` to True here with the date and the report that shows it."""
import os
from typing import Dict

FEATURES: Dict[str, Dict] = {
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
        "verified": True,       # 2026-09-29 người dùng duyệt (S6.5): #8 chạy thật hai lượt, Đạo diễn duyệt 6/6 cảnh (TONG_KET_DU_AN_8 mục 3)
        "why": "Đã chạy thật: #8 (28–29/09) Director hai lượt, Đạo diễn duyệt 6/6 cảnh; người dùng duyệt 29/09 (S6.5). Lý do ban đầu (GĐ5, "
               "26/09: mới thử bằng Claude giả lập) đã hết hiệu lực (core/director_two_pass.py)",
    },
    "voice_direction": {
        "label": "Chỉ đạo giọng lồng: câu thoại có `delivery` (cảm xúc, cường độ, nhịp, ngắt, nhấn, thẻ v3) → tham số TTS + chữ gửi TTS",
        "verified": True,       # 2026-09-29 người dùng duyệt (S6.5): #8 — 23 câu thoại đúng giọng, đúng người (4 giọng VN)
        "why": "Đã chạy thật: #8 có 23 câu thoại đúng giọng, đúng người (4 giọng VN); người dùng duyệt 29/09 (S6.5). Còn mở: thẻ [whispers] "
               "với giọng Việt chưa nghe thử riêng (tài liệu ElevenLabs mâu thuẫn về `speed` của eleven_v3)",
    },
    "loudness_normalize": {
        "label": "Chuẩn hóa độ to bản giao về −14 LUFS / đỉnh thật −1,5 dBTP (loudnorm 2 lượt, tăng/giảm tuyến tính) khi số đo lệch mục tiêu",
        "verified": True,       # 2026-09-29 người dùng duyệt (S6.5): bản giao #8 đo −14 LUFS
        "why": "Đã chạy thật: bản giao #8 đo −14 LUFS; người dùng duyệt 29/09 (S6.5). Còn mở: chưa nghe thử một bản được chuẩn hóa trên điện "
               "thoại (editing.md E8, D11: không nền tảng nào công bố LUFS)",
    },
    "shot_color_match": {
        "label": "Khớp màu giữa các shot cùng nơi + cùng nhóm cỡ cảnh (điểm đen/trắng, ám màu của vật xám) — sửa bản sao clip lệch trước khi dựng",
        "verified": True,        # 01/10 người dùng xem 2 bản dựng #8 có / không hiệu ứng (đợt 4) và chọn bản CÓ
        "why": "Đã duyệt 01/10 (đợt 4, D:/AI-Video-Output/2026-10-01_ab-hieu-ung-8): người dùng xem bản dựng #8 có hiệu ứng và chọn giữ. Lý do ban đầu — GĐ4 (editing.md E5, D7): đo thật #7 thấy 2/7 shot lệch điểm đen/trắng 0,14–0,15 (một phần do nội dung khung); sửa thử đưa "
               "về ~0,04 — chưa có người xem bản dựng đã khớp màu",
    },
    "j_cut": {
        "label": "Cắt J: câu của người nói mới vào sớm 0,25 s trước khi hình cắt sang shot của họ (không đè câu trước)",
        "verified": False,
        "why": "GĐ4 (editing.md E1, D1): chưa nghe thử bản dựng có cắt J trên giọng Việt lồng — phụ đề đi theo giọng nên cũng vào sớm",
    },
    "music_breath": {
        "label": "Nhạc lặng 0,6 s ngay trước cú ngoặt (phần kịch bản TWIST / CAO TRÀO, hoặc shot ⭐ đầu tiên)",
        "verified": True,        # 01/10 người dùng xem 2 bản dựng #8 có / không hiệu ứng (đợt 4) và chọn bản CÓ
        "why": "Đã duyệt 01/10 (đợt 4, D:/AI-Video-Output/2026-10-01_ab-hieu-ung-8): người dùng xem bản dựng #8 có hiệu ứng và chọn giữ. Lý do ban đầu — GĐ4 (editing.md E4, D6): chưa nghe thử; khoảng lặng dài/ngắn là gu dựng — bật khi người dùng nghe và đồng ý",
    },
    "sound_intent": {
        "label": "Nhạc theo ý đồ âm thanh của Đạo diễn từng shot: tắt hẳn từ shot 'cut' tới shot 'in', lặng 0,6 s trước shot 'breath'",
        "verified": True,        # 01/10 người dùng xem 2 bản dựng #8 có / không hiệu ứng (đợt 4) và chọn bản CÓ
        "why": "Đã duyệt 01/10 (đợt 4, D:/AI-Video-Output/2026-10-01_ab-hieu-ung-8): người dùng xem bản dựng #8 có hiệu ứng và chọn giữ. Lý do ban đầu — 2026-09-26 (director.md Đ9, bài học Handbook ch. V): chưa nghe thử bản dựng có nhạc ngắt theo shot; tắt thì bản dựng "
               "ghi lại số ý đồ chưa áp (manifest `sound_intent`)",
    },
    "flashback_fx": {
        "label": "Hồi tưởng ở khâu Dựng: shot hồi tưởng có flash trắng vào/ra, màu ấm nhạt + viền tối (người xem biết là ký ức)",
        "verified": True,        # 01/10 người dùng xem 2 bản dựng #8 có / không hiệu ứng (đợt 4) và chọn bản CÓ
        "why": "Đã duyệt 01/10 (đợt 4, D:/AI-Video-Output/2026-10-01_ab-hieu-ung-8): người dùng xem bản dựng #8 có hiệu ứng và chọn giữ. Lý do ban đầu — 2026-09-28 (sau #8, người dùng: hồi tưởng không có hiệu ứng nên không ai biết là hồi tưởng): mới thử bằng ffmpeg trên clip "
               "#8, chờ người dùng xem bản dựng lại",
    },
    "end_hold": {
        "label": "Giữ hình shot cuối ít nhất 2,5 s (kéo dài khung cuối) để cái kết không lướt qua",
        "verified": True,        # 01/10 người dùng xem 2 bản dựng #8 có / không hiệu ứng (đợt 4) và chọn bản CÓ
        "why": "Đã duyệt 01/10 (đợt 4, D:/AI-Video-Output/2026-10-01_ab-hieu-ung-8): người dùng xem bản dựng #8 có hiệu ứng và chọn giữ. Lý do ban đầu — 2026-09-28 (sau #8: hai shot kết mỗi shot 1 s, người dùng thấy kết cụt): chờ người dùng xem bản dựng lại",
    },
    "continuous_takes": {
        "label": "Đoạn diễn liên tục theo góc máy: mỗi vị trí máy (camera_setup) quay TRỌN đoạn diễn liên tục của cảnh, rồi mỗi shot được "
                 "cắt đúng chỗ của nó trong đoạn — cắt xen các góc mà động tác vẫn liền (cần bật cùng camera_setups)",
        "verified": False,
        "why": "2026-09-29 (kế hoạch S3.4, sau #8: mỗi shot gen riêng, chuyển động bắt đầu lại ở mỗi điểm cắt): mới thử bằng test ffmpeg — "
               "chưa biết model video có diễn trọn đoạn 8–15 s đúng thứ tự không, và trả tiền nhiều giây hơn cho mỗi góc",
    },
    "closeup_start_frame": {
        "label": "Shot cận thấy mặt (ECU / CU / MCU có nhân vật) không đi nhóm Seedance chỉ-tham-chiếu mà đi Kling từ khung đầu = ảnh "
                 "storyboard đã duyệt — mặt giữ đúng ảnh duyệt",
        "verified": False,
        "why": "2026-09-29 (kế hoạch S4.1, sau #8: cận Kelly đi nhóm tham chiếu ra kiểu anime): chưa chạy thật — A/B S4.6 (cận ref-only vs "
               "khung đầu) quyết có giữ không; Kling tốn tiền theo giây như shot đơn, mất gộp nhóm",
    },
    "shot_transitions": {
        "label": "Chuyển cảnh từng chỗ nối theo `transition_in` của shot (chớp trắng, tối đi, lia nhòe, lao vào khung) — vẽ trong hai clip "
                 "kề nhau nên độ dài phim không đổi",
        "verified": False,
        "why": "2026-09-29 (kế hoạch S3.6): mới thử bằng test ffmpeg — chưa xem trên bản dựng thật (lia nhòe / lao vào khung có thể lộ "
               "giả trên clip AI)",
    },
    "story_check": {
        "label": "Người xem lần đầu: 1 lượt Claude chỉ đọc cái sẽ hiện trên màn hình (hành động, thoại, chữ — không đọc ý đồ Director) rồi "
                 "kể lại truyện và chỉ chỗ khó hiểu, trước khi làm ảnh",
        "verified": False,
        "why": "2026-09-29 (kế hoạch S3.2, sau #8: truyện cụt, Maxim trúng đạn không thấy ai bắn): mới thử bằng Claude giả lập — chưa biết "
               "người xem Claude có bắt đúng chỗ người xem thật thấy khó hiểu không (lần chạy kiểm K)",
    },
    "rough_cut_review": {
        "label": "Duyệt bản dựng thô (P0–P1 chỉ đo, 0 USD): sau khi ghép, đo nhịp thật của bản dựng so với ý đồ Đạo diễn (độ dài cảnh so `target_s`, "
                 "đỉnh `peak` có shot đủ dài không, khoảng lặng) + tấm khung quanh điểm cắt ≤ 12 ảnh. Lượt Claude Biên tập viên + Đạo diễn là P2, chưa có",
        "verified": False,
        "why": "2026-10-02 (kế hoạch docs/KE_HOACH_DUYET_BAN_THO_2026-10-02.md, P0–P1): mới thử bằng test + fixture; chưa chạy trên bản dựng thật, "
               "chưa biết các số đo có giúp người dùng thấy đúng chỗ nhịp chùng hay không",
    },
    "audio_first": {
        "label": "Timeline theo âm thanh: tạo giọng ngay sau Director, kéo độ dài từng shot theo giọng thật, kiểm tổng so với mục tiêu "
                 "kịch bản (±10 %) và khóa timeline TRƯỚC khi làm ảnh / video",
        "verified": False,
        "why": "2026-09-29 (kế hoạch S2, sau #8: dự kiến 58 s ra 83 s vì giọng làm sau clip): mới thử bằng test, chưa chạy trên dự án thật",
    },
    "music_fit": {
        "label": "Nhạc nền đi theo cảnh thật: dời / co giãn từng đoạn của bản nhạc đã soạn cho khớp đầu mỗi cảnh trên bản dựng (miễn phí)",
        "verified": True,        # 01/10 người dùng xem 2 bản dựng #8 có / không hiệu ứng (đợt 4) và chọn bản CÓ
        "why": "Đã duyệt 01/10 (đợt 4, D:/AI-Video-Output/2026-10-01_ab-hieu-ung-8): người dùng xem bản dựng #8 có hiệu ứng và chọn giữ. Lý do ban đầu — 2026-09-28 (sau #8: nhạc soạn cho timeline 64 s, phim thành 84,5 s — đổi nhạc lệch cảnh, người dùng: nhạc phải đi theo "
               "diễn biến): chờ người dùng nghe bản dựng lại",
    },
    "impact_shake": {
        "label": "Rung khung hình 0,25 s ở những giây có hiệu ứng va chạm / nổ / súng trong bản trộn",
        "verified": True,        # 01/10 người dùng xem 2 bản dựng #8 có / không hiệu ứng (đợt 4) và chọn bản CÓ
        "why": "Đã duyệt 01/10 (đợt 4, D:/AI-Video-Output/2026-10-01_ab-hieu-ung-8): người dùng xem bản dựng #8 có hiệu ứng và chọn giữ. Lý do ban đầu — GĐ4 (editing.md E6, D9): chưa xem thử trên bản dựng thật; rung sai chỗ làm người xem khó chịu",
    },
    "ambience_bed": {
        "label": "Âm nền mỗi cảnh từ thư viện âm thanh của bạn (theo thời tiết → giờ → bối cảnh), nhỏ dưới thoại, lặp đủ dài",
        "verified": True,        # 01/10 người dùng xem 2 bản dựng #8 có / không hiệu ứng (đợt 4) và chọn bản CÓ
        "why": "Đã duyệt 01/10 (đợt 4, D:/AI-Video-Output/2026-10-01_ab-hieu-ung-8): người dùng xem bản dựng #8 có hiệu ứng và chọn giữ. Lý do ban đầu — GĐ4 (editing.md E3, D4/D5): thử #7 — cảnh ngày khu nhà trên đảo nhận 'Bird Ambience'; cảnh đêm không có âm đêm trong "
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
    "project_budget": {
        "label": "Ngân sách dự án chia theo khâu (ảnh, video, Claude từng khâu), code tính ngay sau bảng shot, người duyệt thì KHÓA: mọi "
                 "lời gọi trả tiền kiểm trần khâu + tổng trước khi gửi; chạy tự động chờ duyệt ngân sách trước khi gen ảnh",
        "verified": True,       # 2026-09-29 người dùng duyệt (S6.5): #8 — khóa cứng chặn đúng ở trần (TONG_KET_DU_AN_8 mục 3, Chi phí)
        "why": "Đã chạy thật: #8 — khóa cứng chặn đúng ở trần (TONG_KET_DU_AN_8 mục 3); người dùng duyệt 29/09 (S6.5). Lý do ban đầu "
               "(28/09: #8 ước 12,45 USD, chưa làm video đã chi 16,38) là chính điều khóa này ngăn. Lỗi B1 01/10 (khâu Claude 'khác' bị chặn vì "
               "max_tokens mặc định) đã sửa",
    },
    "scene_qc_claude": {
        "label": "QC theo cảnh lớp 1: Claude MỘT lượt mỗi cảnh tự chạy khi đủ khung (tắt: khung mới đi thẳng tới người duyệt, lớp 0 "
                 "bằng code vẫn chạy; bật agent QC thì agent thay lớp này)",
        "verified": False,
        "why": "Nghiệm thu 2026-09-27 trên 33 khung có nhãn của #8 không đạt (bỏ lọt 6 khung dán, báo nhầm 12/21 khung tốt); chấm lại cả "
               "cảnh sau mỗi lần vẽ lại tốn ~0,5 USD Claude chỉ để ghi chú (docs/CHAY_THU_2026-09-27_NHAT_KY.md phát hiện 44)",
    },
    "idea_to_script": {
        "label": "💡 Ý tưởng thô → kịch bản ở Bước 1: Biên kịch (Claude) hỏi lại ≤ 5 câu → 3 hướng → dàn ý theo giây → kịch bản đúng khuôn, "
                 "code kiểm, người duyệt từng lượt + màn 2 cột tô phần thêm (S11.1)",
        "verified": True,       # 2026-10-06 người dùng duyệt bật mặc định (S14.43 mục 5)
        "why": "S14.22 cổng S11.2 ĐẠT: người dùng chấm phiếu 05d (docs/DO_S11_2_Y_TUONG_2026-10-05d.md) TB 4,20 ≥ 4,0, đo thật 0,709 USD; "
               "06/10 người dùng duyệt bật mặc định — dùng khi người dùng yêu cầu hoặc khi kịch bản sơ sài (Claude hỏi trong khung chat, chưa tự chi)",
    },
    "qc_team": {
        "label": "Tổ QC nhiều tầng (docs/THIET_KE_TO_QC_2026-10-01.md): bảng shot → mệnh đề kiểm tra, code đo trước (mặt, hướng mắt, màu trời), "
                 "chuyên viên Nhân vật trả lời có cấu trúc 1 lượt / khung, bảng luật code kết luận — thay lớp 1 của QC theo cảnh",
        "verified": False,
        "why": "GĐ3 01/10 trên #8: mũ đúng 5/5 nhưng trái/phải do model đúng ~50 % → trái/phải chỉ đánh dấu cho người, không tự chặn; "
               "người dùng 01/10 bật thử trên dự án mới — mọi khung vẫn chờ người (ghi chú của Tổ QC), chưa tự duyệt / vẽ lại",
    },
    "qc_agent": {
        "label": "Agent QC điều tra nhiều bước (Claude có công cụ: xem khung / cắt sát / ghép dải nhiều khung / ảnh chuẩn / bộ đo / ghi "
                 "kết luận) theo sổ tay kiểm tra — thay lớp 1 của QC theo cảnh",
        "verified": False,
        "why": "Thử 2026-09-27 bằng agent trong phiên làm việc (không qua API): 11 lỗi chặn đúng trên #8, người dùng xác nhận; bản trong "
               "app (core/qc_agent.py) chưa đo trên bộ nhãn",
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
    "seedance_subjects": {
        "label": "S4.7: ảnh gửi Seedance (chế độ chỉ ảnh tham chiếu: khung storyboard + ảnh định danh, shot kỹ năng) đi qua Kho chủ thể "
                 "ClipAI — ảnh KHÔNG đánh dấu, tải một lần theo sha256, gửi asset://; kho từ chối / chưa duyệt xong → gửi ảnh đánh dấu "
                 "như cũ (P2m) và báo",
        "verified": False,
        "why": "Thử 01/10 (dự án thử #15, docs/KET_QUA_S4_7_S4_10_2026-10-01.md): 2 ảnh FF in-game (khung + Kelly) active sau ~5 s, "
               "Seedance nhận lúc tạo — mới 1 shot / 1 nhân vật chính; chưa qua luồng chính (nhóm nhiều shot, 3 người)",
    },
    "dialogue_take": {
        "label": "Khớp môi (c) — S4.2: shot thoại thấy mặt người nói (cả shot trung / nhiều người) đi trong clip nhóm Seedance 2.5 kèm MỘT "
                 "track giọng của cả nhóm + câu thoại, tên người nói và mốc giây trong prompt (thay 'không khớp môi' khi không có sync.so)",
        "verified": True,       # 01/10 người dùng: S4.2 khớp môi (c) OK (dự án thử #14, 2,82 USD)
        "why": "Đã chạy thật 01/10 (S4.2, dự án #14, 2,82 USD) và người dùng xác nhận OK; A/B S4.6 vòng 2 (29/09, #10): một clip 3 câu / 3 "
               "người nói cho đúng người mở miệng đúng lượt. Còn mở: độ khớp đo 0,39–0,53 < 0,65 (S4.10) — hướng tiếp: mốc 0,1 s / dời giọng",
    },
    "storyboard_api": {
        "label": "Vẽ ảnh các shot của một cảnh bằng MỘT storyboard Deepix (shot rộng nhất làm neo, cùng ảnh tham chiếu) — cách Weave Canvas",
        "verified": False,
        "why": "Thử #7 cảnh 1 (2026-09-25): 4 khung giữ tháp/ánh sáng liền mạch hơn ảnh vẽ riêng; mới 1 cảnh, chưa thử cảnh đông người / hành động",
    },
    "place_render_refs": {
        "label": "Ảnh render 3D đúng góc máy từng shot (và góc rộng nhất của cảnh) làm ẢNH THAM CHIẾU cho model vẽ cả cảnh — không ghép; "
                 "prompt thêm số đo thật (ống kính, độ cao máy, vị trí đầu–chân nhân vật, đường chân trời, hướng nắng); đo độ khớp nền sau khi vẽ",
        "verified": False,
        "why": "Người dùng 2026-09-29: 6 ảnh Kho không đủ mọi góc; ghép phông xanh đã bỏ (#8). #7: ảnh render tháp làm tham chiếu cho kết "
               "quả tốt nhất. Chưa chạy thật trả tiền (Blender 0 USD; ảnh model vẫn tính tiền như thường)",
    },
    "end_frames": {
        "label": "Ảnh khung cuối cho shot có end_state (vẽ thêm 1 ảnh, gửi clip khung đầu + cuối)",
        "verified": False,
        "why": "K1/K2 (kế hoạch tổng K-a): tốn thêm 1 ảnh mỗi shot đổi trạng thái; chưa thử thật Kling end_frame với khung vẽ từ ảnh đầu",
    },
    "ui_v2": {
        "label": "Giao diện v2 kiểu “AI product”: nền tối aurora, thẻ kính, nút gradient + glow, thanh bước viên thuốc, pill trạng thái, chữ gradient (lớp thiết kế dashboard/design/, chạy trên cùng các màn hiện có)",
        "verified": False,
        "why": "S13 (01/10, docs/KE_HOACH_GIAO_DIEN_V2_2026-10-01.md): đang dựng theo giai đoạn; mặc định TẮT cho tới khi người dùng duyệt ảnh chụp trên Dashboard thật (cổng G1) — bật/tắt ở ⚙ → Hệ thống → 🧪 để so với giao diện cũ và quay lại tức thì",
    },
    "storyboard_auto_trust": {
        "label": "Tự bỏ qua cổng duyệt storyboard khi QC đã đủ tin cậy (≥ 90% khớp người trên ≥ 50 ảnh cùng look) và storyboard không có cờ",
        "verified": False,
        "why": "W8 (kế hoạch tổng): chưa có đủ ảnh người duyệt cùng look để đo — bật khi số đo đạt và người dùng đồng ý",
    },
    "ai_label": {
        "label": "Nhãn \"nội dung có dùng AI\" góc trên bản dựng (và các bản xuất khổ khác) — cho thị trường bắt buộc nhãn; "
                 "chữ nhãn: AI_LABEL_TEXT",
        "verified": False,
        "why": "S0.14 T6 (người dùng duyệt 2026-09-29): 《微短剧发展管理办法》 (TQ, hiệu lực 2026-09-01) bắt nhãn AI ở vị trí rõ trong mỗi tập; "
               "phát ở VN không bắt buộc — bật khi phát ở nơi cần",
    },
    "speaker_tags": {
        "label": "Prompt Kling có thoại mà chưa nêu tên người nói → code thêm \"X speaks (mouth moving, no sound).\" + người còn lại "
                 "trong khung \"listens, mouth closed\" (tắt: chỉ báo trong chẩn đoán)",
        "verified": False,
        "why": "S0.14 T2 (2026-09-29): tài liệu chính thức Kling 3.0 gắn thoại theo tên nhân vật; người thử thấy Kling chia thoại giữa "
               "nhân vật chưa chuẩn — chưa thử thật câu thêm có làm đúng người mở miệng hơn không (core/speaker_lint.py)",
    },
    "hero_takes": {
        "label": "Shot ⭐ (hero / money_shot) gửi riêng được gen THÊM một bản cùng đầu vào; code đo lớp 0 cả hai, bản ít lỗi hơn được dùng, "
                 "ngang nhau thì giữ cả hai cho bạn chọn ở Bước 4 (ước tính tính 2 bản)",
        "verified": False,
        "why": "S0.14 T4 (người dùng duyệt 2026-09-30): người làm phim AI TQ 'cảnh xịn = gen nhiều rồi chọn'; dồn tiền vào vài shot then "
               "chốt thay vì gen lại mọi shot (core/hero_takes.py) — chưa chạy thật; thêm ≈ 1 USD mỗi shot ⭐ Seedance 2.5 4–5 s",
    },
    "skill_dossier": {
        "label": "Hồ sơ kỹ năng nhân vật (data/skills/<TÊN>): Director đọc các giai đoạn + luật kịch bản; shot có kỹ năng gửi kèm khung "
                 "hình thật của giai đoạn đó làm ảnh tham chiếu + câu tả chuẩn cho ảnh và video + danh sách không được vẽ; báo chữ trái hồ sơ",
        "verified": False,
        "why": "Người dùng 2026-09-30: #8 tả kỹ năng Kenta sai (rút katana, lốc phá tường) vì chỉ có vài dòng chữ. Hồ sơ Kenta xem 30 "
               "khung/giây video chính thức; chưa thử thật — thử trước 1 cảnh ngắn Kenta dùng kỹ năng",
    },
    "seedance_video_edit": {
        "label": "Sửa clip bằng Seedance 2.5 (S4.12, Advanced Edit): gửi clip lỗi làm bản gốc duy nhất + câu sửa một chỗ "
                 "(`omni_reference_task_type: edit`) thay vì sinh lại — adapter ClipAI `submit_video_edit`",
        "verified": False,
        "why": "S4.12 (2026-10-01, docs/KET_QUA_S4_11_S4_12_2026-10-01.md): thử 1 clip #8; tính tiền cả giây clip nguồn + giây ra",
    },
    "director_rewrite": {
        "label": "Đạo diễn viết lại prompt shot trước mỗi lần gen lại (người từ chối kèm ghi chú / QC từ chối kèm lỗi): sửa đúng chỗ gây "
                 "lỗi, lưu bản cũ, thẻ ảnh/clip hiện so sánh cũ/mới + nút dùng lại prompt cũ — thay cho nối 'Fix: …' cuối prompt",
        "verified": False,
        "why": "S14.17 người dùng duyệt 04/10, chưa chạy thật Claude (core/prompt_rewrite.py; Claude lỗi → quay về 'Fix: …' + diag)",
    },
    "murch_knowledge": {
        "label": "Bộ não prompt Đợt 2: Director + motion đọc thang ưu tiên cảm xúc (Murch), motion đọc kỷ luật I2V (giữ trước, hỏng thì "
                 "giảm chuyển động, check_flags gọi tên rủi ro), Director đọc phương pháp âm thanh; người xem lần đầu chấm thêm cam_xuc",
        "verified": False,
        "why": "S14.20 (05/10): chỉ thêm tài liệu vào prompt (≈ +9 nghìn ký tự mỗi lần chạy Director/motion); chưa so prompt Bước 3 "
               "thật trên dự án cũ (nghiệm thu Đợt 2 cần Claude thật)",
    },
    "auto_voice_cast": {
        "label": "Tự gắn giọng tiếng Việt từ phân tích cảnh: Director ghi giới tính/tuổi/tính cách vai có thoại (cùng lượt Claude), luật "
                 "0 USD gắn giọng data/voices_vi.json (vai chính giọng đầu), quá 2 vai cùng giới → dùng lại giọng + biến thể cao độ "
                 "±2–3 nửa cung (ffmpeg sau TTS) + tốc độ ClipAI; không ghi đè giọng người dùng chọn",
        "verified": False,
        "why": "S14.26 (05/10): chưa chạy Director thật với khối voice_traits; biến thể cao độ ffmpeg chưa nghe thử trên 4 giọng VN "
               "(giọng nam +3 nửa cung có thể nghe méo) — bật để thử ở dự án mới (core/voice_casting.py)",
    },
    "asset_checklist": {
        "label": "Bảng kê tài nguyên trước Director: một lượt Claude rẻ (không ảnh) đọc kịch bản, kê nhân vật/nơi/đồ vật/vũ khí/thú "
                 "cưng/trang phục cần thấy, ghép với Kho (code kiểm lại id + loại) → bảng ✅ đã gắn / có trong Kho / ⚠️ thiếu, gắn "
                 "nhanh trước khi trả tiền cho Director",
        "verified": False,
        "why": "S14.23 (05/10): chưa chạy Claude thật; nghiệm thu = 2 kịch bản thật (Kho đủ / Kho thiếu) — báo đúng cái thiếu, "
               "không báo nhầm cái đã có (core/asset_checklist.py, prompts/27_asset_checklist.md)",
    },
    "kelly_knowledge": {
        "label": "Tri thức kênh Kelly (GỢI Ý trộn được): Biên kịch đọc 4 khuôn kịch bản dựng chắc được + kỹ thuật né + hook/nhịp/cú chốt; "
                 "Đạo diễn, Quay phim, Biên tập (Dựng) mỗi vai đọc một tài liệu ngắn",
        "verified": False,
        "why": "S14.34 (05/10): mẫu MỘT kênh, 40 clip (độ tin tối đa 'có thể'); chỉ thêm ≈ 3,5 nghìn ký tự mỗi vai; chưa so kịch bản/shot "
               "thật khi bật (cần bản ghi Claude thật S14.34 bước 3)",
    },
    "lesson_judge": {
        "label": "Agent chấm bài học (CHẾ ĐỘ BÓNG): Claude chấm mỗi bài học theo 6 tiêu chí (AI ghi khoản trừ + bằng chứng, code tính "
                 "điểm), ghi vào lịch sử duyệt để so với người — KHÔNG tự duyệt, không đổi bài học hay kiến thức nào",
        "verified": False,
        "why": "S14.24 (06/10): mới thử bằng MockJudge; ngưỡng 0,85 mượn QC ảnh. Bật tự duyệt (cờ sau) chỉ khi ≥ 10 cặp agent↔người, "
               "đồng thuận ≥ 90 %, agent-lỏng-quá = 0 (core/lesson_judge.py agreement())",
    },
    "risk_tags": {
        "label": "Bài học lỗi: tách tag 'motion' thành 6 trục rủi ro I2V (face_morph, body_deform, wardrobe_drift, background_drift, "
                 "motion_overload, text_logo_corrupt) + identity/physics/lipsync/audio; lỗi không gán được tag hiện ở 'Chưa phân loại' + diag",
        "verified": False,
        "why": "S14.20 (05/10): bảng lessons còn 0 bài học, từ khóa chưa đo trên lỗi thật; tag hiếm hơn → có thể không đủ ngưỡng 3 lần / "
               "2 dự án (chưa hạ ngưỡng, chờ Đợt 5 có phân bố thật)",
    },
}


# ---- 🧪 Tính năng thử (rà soát 01/10, đợt 2): the person picks a preset / flips one flag on screen instead of editing dashboard.env ----
# preset "custom" (default, nothing saved) = the old rule: FEATURE_<NAME> env, else `verified`.
# "stable" = only the flags that passed a real test (`verified`); "experimental" = every flag but the ones that did harm.
# A per-flag choice made on screen wins over everything. Stored in data/feature_settings.json (this computer, not in git).
PRESETS = {"custom": "Theo dashboard.env (hiện tại)", "stable": "Ổn định — chỉ tính năng đã thử thật",
           "experimental": "Thử nghiệm — bật hết các tính năng chưa thử thật"}
# GĐ6 / rà soát 01/10 mục 3.2 named 3 harmful flags; S14.9 (Gói L, 06/10) removed them from the code — nothing left to keep off here.
HARMFUL: tuple = ()
# S14.9 (Gói L, 06/10, người dùng: cờ gây hại phải bị xóa, không chỉ tắt): flags taken out of the code — the code now always does
# what it did with the flag OFF. An old choice in data/feature_settings.json or a FEATURE_<NAME> line in dashboard.env naming one is
# ignored (said by `removed_in_use()`, never an error). Reasons + dates: docs/TODO_LICH_SU.md.
REMOVED: Dict[str, str] = {
    "layout_to_model": "GĐ6: model chép góc máy từ trên cao + người tí hon của ảnh bố cục ghép",
    "chain_previous_auto": "GĐ6: nối ảnh shot trước bất kể cỡ cảnh → shot cận kéo theo bố cục toàn cảnh",
    "setcheck_autofix": "GĐ6: QC đồng bộ chuẩn theo số đông, sửa sai người rồi tự trả tiền gen lại",
    "seedance_sample_mode": "S4.11 bản mẫu 480p → bản cuối 1080p: chưa từng chạy thật, không luồng nào dùng",
    "location_plates": "Ghép phông xanh lên nền 3D: tạm ngưng từ 27/09 (#8), thay bằng place_render_refs / scene_establishing",
}
_SETTINGS = {"stamp": None, "path": None, "data": None}


def settings_path() -> str:
    return os.environ.get("FEATURE_SETTINGS_FILE") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                                                   "data", "feature_settings.json")


def settings() -> Dict:
    """{"preset": custom|stable|experimental, "flags": {name: bool}} — re-read when the file changes."""
    path = settings_path()
    try:
        stamp = os.stat(path).st_mtime_ns
    except OSError:
        stamp = None
    if _SETTINGS["stamp"] != stamp or _SETTINGS["path"] != path:
        data = {"preset": "custom", "flags": {}}
        if stamp is not None:
            try:
                import json
                with open(path, encoding="utf-8") as f:
                    raw = json.load(f)
                if raw.get("preset") in PRESETS:
                    data["preset"] = raw["preset"]
                data["flags"] = {k: bool(v) for k, v in (raw.get("flags") or {}).items() if k in FEATURES}
                data["dropped"] = sorted(k for k in (raw.get("flags") or {}) if k in REMOVED)   # S14.9: ignored, said
            except (OSError, ValueError, AttributeError):
                pass
        _SETTINGS.update(stamp=stamp, path=path, data=data)
    return _SETTINGS["data"]


def save_settings(preset: str = None, flags: Dict = None) -> Dict:
    """Write the choice (flags: {name: True|False|None}; None removes the single choice). Atomic."""
    import json
    cur = {"preset": settings()["preset"], "flags": dict(settings()["flags"])}    # a removed flag's old choice is dropped on save
    if preset is not None:
        if preset not in PRESETS:
            raise ValueError(f"preset không có: {preset}")
        cur["preset"] = preset
    for k, v in (flags or {}).items():
        if k in REMOVED:                  # S14.9: an old page / script still naming a removed flag — nothing to set
            continue
        if k not in FEATURES:
            raise ValueError(f"không có tính năng {k}")
        if v is None:
            cur["flags"].pop(k, None)
        else:
            cur["flags"][k] = bool(v)
    path = settings_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cur, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    _SETTINGS["stamp"] = object()         # two saves in one clock tick keep the same mtime: never serve the old cache (test flake 04/10)
    return settings()


def _env(name: str) -> str:
    return os.environ.get("FEATURE_" + name.upper(), "").strip().lower()


def on(name: str) -> bool:
    """True when the person chose it on screen (🧪), else by the preset: the feature passed its real test, or the person switched it on
    with FEATURE_<NAME>=1 (0 switches it off). A flag removed in S14.9 (`REMOVED`) is always off — the code has no ON branch left."""
    if name in REMOVED:
        return False
    s = settings()
    if name in s["flags"]:
        return s["flags"][name]
    verified = bool(FEATURES[name]["verified"])
    env = _env(name)
    if s["preset"] == "stable":
        return verified
    if s["preset"] == "experimental":
        return False if env in ("0", "false", "off", "no") else (name not in HARMFUL or env in ("1", "true", "on", "yes"))
    if env in ("1", "true", "on", "yes"):
        return True
    if env in ("0", "false", "off", "no"):
        return False
    return verified


# S14.4 C1b (04/10): a flag that only works together with another one (dialogue_take: the runner asks lipsync.enabled() = lip_sync
# first). Shown in 🧪 instead of a flag that looks ON and does nothing.
REQUIRES = {"dialogue_take": ("lip_sync",)}


def unmet(name: str) -> list:
    """The flags `name` needs that are off (empty when it is off itself or has no needs)."""
    if name not in REQUIRES or not on(name):
        return []
    return [n for n in REQUIRES[name] if not on(n)]


def unmet_all() -> Dict[str, str]:
    """{flag: Vietnamese warning} for every flag that is ON but has no effect because a flag it needs is off."""
    return {k: f"'{k}' đang bật nhưng không có tác dụng: cần bật thêm {', '.join(repr(n) for n in miss)}"
            for k in REQUIRES for miss in [unmet(k)] if miss}


def why_state(name: str) -> str:
    """Why `on(name)` is what it is (shown in 🧪)."""
    miss = unmet(name)
    base = _why_state(name)
    return base + (f" — ⚠ không có tác dụng: cần bật thêm {', '.join(miss)}" if miss else "")


def _why_state(name: str) -> str:
    s = settings()
    if name in s["flags"]:
        return "bạn chọn trên màn này"
    if s["preset"] == "stable":
        return "preset Ổn định: " + ("đã thử thật" if FEATURES[name]["verified"] else "chưa thử thật → tắt")
    if s["preset"] == "experimental":
        return "preset Thử nghiệm" + (" (cờ từng gây hại → tắt)" if name in HARMFUL and on(name) is False else "")
    env = _env(name)
    if env:
        return "dashboard.env / môi trường"
    return "mặc định: " + ("đã thử thật → bật" if FEATURES[name]["verified"] else "chưa thử thật → tắt")


def on_unverified() -> Dict[str, Dict]:
    """S6.3 (kế hoạch sau #8): features switched ON by the person (FEATURE_<NAME>=1) that have not passed a real test yet — what a cut
    made now is really trying out (#8 used 23 of them; nobody could tell which part of the film came from which)."""
    return {k: v for k, v in FEATURES.items() if on(k) and not v["verified"]}


def removed_in_use() -> Dict[str, str]:
    """S14.9: {removed flag: Vietnamese note} for every removed flag still named in data/feature_settings.json or switched ON by a
    FEATURE_<NAME> env line — ignored (the code always runs as with it off), said in 🧪 instead of a silent no-op."""
    out = {}
    for k in settings().get("dropped") or []:
        out[k] = f"'{k}' đã bị bỏ khỏi code (S14.9) — lựa chọn cũ trong data/feature_settings.json bị bỏ qua: {REMOVED[k]}"
    for k in REMOVED:
        if k not in out and _env(k) in ("1", "true", "on", "yes"):
            out[k] = f"'{k}' đã bị bỏ khỏi code (S14.9) — dòng FEATURE_{k.upper()}=1 không còn tác dụng: {REMOVED[k]}"
    return out


def pending() -> Dict[str, Dict]:
    """Features still waiting for their real test (shown to the person so an off feature is never a mystery)."""
    return {k: v for k, v in FEATURES.items() if not on(k)}
