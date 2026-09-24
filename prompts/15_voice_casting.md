# Chọn giọng cho nhân vật (Bước 1 · Character Bible → Giọng nói)

Cho danh sách nhân vật (tên, mô tả, giới tính/tuổi nếu có, các câu thoại mẫu) và danh sách giọng có sẵn (id, tên, mô tả nếu có). Chọn cho mỗi nhân vật CÓ THOẠI một giọng hợp nhất (giới tính, tuổi, tính cách), hai nhân vật khác nhau không dùng chung giọng nếu còn giọng phù hợp. Viết `persona` (tiếng Việt, 1 câu: độ dài câu, lớp từ, 1 tật nói — theo knowledge/dialogue_craft.md) để các bước sau giữ giọng nhân vật.
Chỉ chọn id có trong danh sách. Chỉ trả về **một JSON hợp lệ**:
```json
{"cast": [{"name": "", "voice_id": 0, "why": "", "persona": ""}]}
```

Thoại là **tiếng Việt**: danh sách giọng đã lọc — `tieng_viet: true` là giọng ghi hỗ trợ tiếng Việt, chỉ chọn trong số đó khi có; chọn đúng giới tính (`gender`) và tuổi của nhân vật. **Ưu tiên giọng có `uu_tien: true`** (giọng clone tiếng Việt thật của team, 2 nam + 2 nữ): chọn trong nhóm này trước theo giới tính; chỉ dùng giọng khác khi nhóm ưu tiên không còn giọng hợp (nêu lý do trong `why`). Được dùng lại một giọng cho hai nhân vật chỉ khi không còn giọng phù hợp (nêu lý do trong `why`).
