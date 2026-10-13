# Kho âm thanh cần bổ sung — Đ12 việc 4

Chỉ đề xuất; người dùng duyệt từng nguồn/tệp **trước khi tải**. Không tải âm, model,
không quét Kho, không gọi API hay sửa dữ liệu. Danh sách nhu cầu lấy từ mô tả #24 trong
`docs/CODEX_TASKS.md`, chưa nghe bản #24 và chưa đo bất kỳ bản Kho thật nào.

## Nhu cầu và từ khóa để người duyệt tìm

| Nhu cầu | Link tìm nguồn | Từ khóa bổ sung | Nghe/duyệt trước khi nhập |
|---|---|---|---|
| Vải sột soạt | [Freesound](https://freesound.org/search/?q=cloth+rustle) | clothing movement, fabric friction, robe foley | Vải mềm, sát mic, không bước chân/giọng; ≥3 cường độ |
| Lết gối trên đá | [Freesound](https://freesound.org/search/?q=stone+scrape) | knee crawl stone, fabric scrape concrete, gravel drag | Tách ma sát vải + đá; không tiếng kim loại; nghe sync với động tác |
| Chạm vai | [Freesound](https://freesound.org/search/?q=body+pat) | shoulder pat, cloth tap, soft body impact | Chạm nhẹ qua áo; tránh đấm/slap quá mạnh |
| Chuông tháp lớn | [Freesound](https://freesound.org/search/?q=church+bell) | tower bell, large bell toll, single toll | Một tiếng + đuôi ngân dài; tránh giai điệu/giọng/tiếng phố |
| Sương/khói bùng biến hình | [Pixabay SFX](https://pixabay.com/sound-effects/search/magic%20whoosh/) | smoke burst, steam hiss, dark magic whoosh | Layer vút + hơi rít + rumble nhẹ; tránh glitch điện tử |
| Kinh dị–bi thương | [Pixabay Music](https://pixabay.com/music/search/dark%20ambient/) | horror mournful, tragic drone, sad cinematic, elegy | Không lời; có khoảng trống thoại, không trống dồn liên tục; chốt mood bằng người nghe |

Đây là link tìm và keyword, **chưa chọn tệp có giấy phép cụ thể**, chưa bảo đảm nguồn có đúng âm.
Freesound: lọc CC0 trước, CC BY chỉ khi chấp nhận ghi công; bỏ CC BY-NC cho dự án thương mại.
[Freesound FAQ chính thức](https://freesound.org/help/faq/) liệt kê license theo từng âm.
[CC0 chính thức](https://creativecommons.org/publicdomain/zero/1.0/) không yêu cầu ghi công; CC BY cần tên âm, tác giả, link nguồn, link license đúng phiên bản
và nêu chỉnh sửa (nếu có), theo [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Lưu thông tin license từng tệp khi người dùng duyệt, không coi toàn bộ Freesound cùng license.

Pixabay dùng [Content License](https://pixabay.com/service/license-summary/): cho phép dùng,
chỉnh sửa miễn phí và không bắt buộc attribution, nhưng cấm phân phối/bán nguyên nội dung độc lập.
[FAQ âm nhạc chính thức](https://pixabay.com/service/faq/) cảnh báo track vẫn có thể dính Content ID;
ưu tiên bản không đăng ký, lưu link/chứng nhận nếu có. License là quyền sử dụng, không bảo đảm
không có claim. Chỉ nguồn miễn phí thực sự trên Pixabay, không chọn quảng cáo kho trả tiền.
Nguồn license và config được kiểm qua web ngày 13/10/2026; duyệt lại từng trang tệp lúc tải.

## Mood ≈ 0: đối chiếu code và ontology

`tools/audio_listen.py:tags` dùng **AST MIT** `ast-finetuned-audioset-10-10-0.4593`,
Transformers `audio-classification`, cửa sổ 2 s trên stem nhạc 16 kHz, `top_k=40`;
chỉ giữ mood khớp chính xác 7 tên và score ≥0,05. `top` chỉ lưu 4 nhãn; `mood` chỉ lưu
nhãn đã vượt ngưỡng (score làm tròn 2 chữ số). `listen.json` hiện tại **không đủ** để phân biệt
mood score=0, dưới ngưỡng hay bị loại khỏi top 40. Không suy ra 0 thật từ danh sách mood rỗng.

[Config MIT chính thức tại revision f32fcdf](https://huggingface.co/MIT/ast-finetuned-audioset-10-10-0.4593/blob/f32fcdf8f46bdf5d9f0aa6805aa0caade6c4c878/config.json)
có cả Happy, Funny, Sad, Tender, Exciting, Angry, Scary music (ID 276–282).
Vì vậy câu kế hoạch “nhãn AST không có mood” không đúng với config này; vẫn phải đối chiếu
classmap thực đã dùng khi xuất score. Không tải weights/library hay chạy inference để kiểm.

`core/sound_ai.py` là **YAMNet ONNX** (521 lớp AudioSet), nhận dạng loại âm/voice/accent;
không phải AST, không dùng cùng ngưỡng mood này. `core/sound_lib.py` gán mood từ tên folder/file;
`analyse` bổ sung mood năng lượng từ mean dB (trên −14: sôi động, dưới −22: thư giãn).
Độ to không chứng minh nhạc kinh dị hay bi thương. Công cụ dưới không đổi bất kỳ picker/runtime nào.

## Công cụ đo offline (stdlib, chỉ đọc)

`py tools/audio_mood_audit.py --input <JSON-do-nguoi-dung-cung-cap> [--ontology <CSV-classmap>]`
Không có path data mặc định; URL/UNC bị từ chối trước khi mở file. JSON có `labels` (danh sách classmap đầy đủ), `windows` (danh sách
cửa sổ, mỗi cửa sổ chứa object `label`, `score` số [0,1]), `complete_scores` boolean (mặc định false).
Nếu dùng CSV cột `display_name` thì có thể bỏ `labels`; nếu có cả hai phải giống nhau theo thứ tự.
Chỉ kiểm ontology: `windows: []`. Không nhận thẳng listen.json hiện tại vì bị cắt score.

Ví dụ đầu vào tự tạo (không phải đo Kho):
```json
{"labels":["Music","Sad music"],"windows":[[{"label":"Sad music","score":0}]],"complete_scores":false}
```

Kết quả là số labels/cửa sổ/score, số mood có/không phủ (`not_covered` trong 7 tên),
case mismatch, số ứng viên vượt ≥0,05 theo mood, số score mood chưa quan sát,
cửa sổ cắt nhãn và cửa sổ có đủ score mood nhưng đều dưới ngưỡng. Score 0 hợp lệ.
`candidates` đếm cặp cửa sổ–mood, **không phải số bản nhạc**. Không xuất đường dẫn, nhãn tùy ý,
raw payload hay credentials. Đầu vào thiếu/hỏng/mismatch được báo rõ, không coi là kết quả 0.

Diễn giải: ontology thật không có mood → không đo mood bằng ontology đó; tên khác chữ hoa/thường
→ kiểm mapping; thiếu score mood → cần bản xuất score đầy đủ, chưa kết luận dưới ngưỡng;
đủ score nhưng dưới ngưỡng → xem lại stem/cửa sổ/khả năng model, nghe để xác nhận.
Ứng viên ≥0,05 vẫn chỉ là dự đoán, chưa chứng minh phù hợp shot. Chưa có đầu vào thật nên
chưa xác định nguyên nhân mood Kho ≈0, chưa có số đo #24.

Đề xuất bước kế: người nghe gán tay mood “kinh dị”, “bi thương”/kết hợp theo từng đoạn, ghi người
và ngày duyệt, nguồn/license, cường độ và chỗ vào/ra; chỉ sau duyệt mới nhập Kho ở một việc riêng.
Nếu muốn model khác, cần chốt model, license weights/code, classmap, đầu vào stem/độ dài và fixture
so với người nghe trước; công việc này chưa chọn/không cài model khác và không hạ ngưỡng runtime.
