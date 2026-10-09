"""S14.47: hội thoại Kịch bản lưu theo dự án; chat không tự tạo job.
KLD-10 (người dùng 09/10): chat là trao đổi THOẠI với Biên kịch (core.dialogue_chat) — đề xuất lưu trong tin assistant (`proposals`);
"ok áp dụng câu 1" là sửa luôn (không nút), CHỈ khi Claude trả `apply` VÀ tin cuối của người có lời đồng ý VÀ đề xuất còn mở. Mỗi lần
áp dụng có một tin "Đã áp dụng …" kèm ảnh chụp trước (`undo`) → "↩ Hoàn tác" (`undo()`, 0 USD)."""
import json
import re
from . import access, dialogue_chat, idea_to_script, llm_runner

STAGE = 'script_chat'
RECENT = 30


def history(p, pid):
    access.need_view(p, pid, 'xem chat Kịch bản')
    row = p.conn.execute('SELECT value FROM app_settings WHERE key=?', (f'script_chat:{pid}',)).fetchone()
    return json.loads(row[0]) if row else []


def append(p, pid, role, text, **extra):
    """Thêm một tin; `extra` = trường thêm (KLD-10: proposals / applied / undo / after / undone)."""
    access.need_edit(p, pid, 'gửi chat Kịch bản')
    if role not in ('user', 'assistant'):
        raise ValueError('Vai tin nhắn không hợp lệ')
    message = json.dumps({**extra, 'role': role, 'text': text}, ensure_ascii=False)
    # One atomic statement: simultaneous sessions cannot overwrite each other's new message.
    p.conn.execute("INSERT INTO app_settings(key,value) VALUES (?,json_array(json(?))) "
                   "ON CONFLICT(key) DO UPDATE SET value=json_insert(app_settings.value,'$[#]',json(?))",
                   (f'script_chat:{pid}', message, message))
    p.conn.commit()


def _set(p, pid, i, field, value):
    """Ghi lại MỘT trường của tin thứ i (vd cả mảng proposals khi đổi state) — một câu lệnh, không đè tin mới của phiên khác."""
    access.need_edit(p, pid, 'sửa chat Kịch bản')
    p.conn.execute("UPDATE app_settings SET value=json_set(value, ?, json(?)) WHERE key=?",
                   (f'$[{int(i)}].{field}', json.dumps(value, ensure_ascii=False), f'script_chat:{pid}'))
    p.conn.commit()


def _set_state(p, pid, ids, state):
    ids = set(ids)
    for i, m in enumerate(history(p, pid)):
        props = m.get('proposals') or []
        if any(pr.get('id') in ids for pr in props):
            _set(p, pid, i, 'proposals', [dict(pr, state=state) if pr.get('id') in ids else pr for pr in props])


def window(p, pid):
    messages = history(p, pid)
    return messages[:-RECENT], messages[-RECENT:]


# KLD-10: câu nói về thoại / lời đồng ý áp dụng → chat với Biên kịch. So CÓ DẤU, chặn hai đầu bằng ký tự chữ (không bỏ dấu: 'thoải mái'
# bỏ dấu thành 'thoai', 'ok' nằm trong 'book'). "ok" đứng một mình chưa đủ (chưa rõ đồng ý cái gì) → vẫn hỏi lại như cũ.
_W, _E = r'(?<![\w])', r'(?![\w])'
# 'điện thoại' (đồ vật) không phải thoại; mã Lx / Px chỉ tính khi dự án CÓ mã đó (P90 là tên súng).
_DIALOGUE_TALK = re.compile(r'(?<!điện )' + _W + r'(?:thoại|câu\s*\d+)' + _E, re.I)
_APPROVE_TARGET = re.compile(_W + r'(?:ok|oke|okay|okie|đồng ý|duyệt|chốt|áp dụng|apply)' + _E + r'.*?' + _W +
                             r'(?:áp dụng|câu|hết|tất cả|cả hai|cả ba|[LP]\d+|đề xuất|bản (?:mới|này|đó))' + _E, re.I)


def _known_codes(p, pid):
    """(mã Lx của dự án, mã Px của đề xuất đang mở) — rỗng khi không có dự án."""
    if p is None or pid is None:
        return set(), set()
    try:
        return ({ln['id'] for ln in dialogue_chat.lines(p, pid)},
                {pr['id'] for pr in dialogue_chat.open_proposals(history(p, pid))})
    except Exception:                                   # không đọc được (quyền / CSDL) → coi như không có mã
        return set(), set()


def is_dialogue_talk(text, p=None, pid=None):
    """Câu ngắn (một dòng) nói về thoại, gọi mã Lx/Px có thật, hoặc đồng ý khi dự án ĐANG có đề xuất mở → chat với Biên kịch (KLD-10).
    Đang viết ý tưởng (Biên kịch có inputs) → chỉ lời đồng ý mới là chat; câu khác là 'nói thêm' cho lượt kế như cũ."""
    t = (text or '').strip()
    if not t or '\n' in t or len(t) > 300:
        return False
    line_ids, open_ids = _known_codes(p, pid)
    named = dialogue_chat.named_codes(t)
    agree = bool(open_ids) and bool(_APPROVE_TARGET.search(t)) and dialogue_chat.approved(t)
    if p is not None and pid is not None and idea_to_script.get_state(p.conn, pid).get('inputs'):
        return agree
    return bool(agree or _DIALOGUE_TALK.search(t) or named & (line_ids | open_ids))


# 09/10 (người dùng thử thật): "phân tích kịch bản này" gõ sau khi dán kịch bản bị coi là NỘI DUNG mới (ý tưởng ngắn → hỏi lại "Bạn muốn
# làm gì với tin này?"). Câu LỆNH ngắn = cả tin chỉ có động từ lệnh + từ đệm (đi / nhé / này / giúp mình…), so CÓ DẤU (NFC; bỏ dấu thì
# 'hủy' = 'Huy' tên người) và khớp TRỌN tin: "phân tích tâm lý Kelly…", "viết kịch bản về Kelly đi chợ", "hủy diệt cả map" là nội dung.
_TAIL = r'(?:\s+(?:đi|nhé|nha|nhá|ạ|giúp|giùm|giúp mình|giùm mình|giúp tôi|hộ|hộ mình|luôn|ngay|bây giờ|now))*'
_THIS = r'(?:\s+(?:này|đó|kia|trên|ở trên|bên trên|vừa dán|vừa gửi|mình vừa dán|mình vừa gửi))?'
_CMDS = (
    ('analyse', r'(?:hãy\s+)?(?:chạy\s+|bấm\s+)?(?:phân tích|tách cảnh|chia cảnh)(?:\s+(?:kịch bản|kb|cảnh))?' + _THIS),
    ('write', r'(?:hãy\s+)?viết(?:\s+thành)?\s+kịch bản(?:\s+(?:từ|theo)\s+(?:ý tưởng|dàn ý)' + _THIS + r')?'),
    ('idea', r'(?:dùng|lấy|coi)\s+(?:làm|là)\s+ý tưởng' + _THIS + r'|(?:đây|cái này)\s+là\s+ý tưởng'),
    ('script', r'(?:dùng|lấy|coi)\s+(?:làm|là)\s+kịch bản' + _THIS + r'|(?:đây|cái này)\s+là\s+kịch bản'),
    ('cancel', r'hủy|huỷ|hủy bỏ|huỷ bỏ|bỏ qua|thôi|cancel'),
)
_CMD_RES = [(name, re.compile(r'^\s*[▶►]?\s*(?:' + body + r')' + _TAIL + r'\s*[.!…]*\s*$', re.I)) for name, body in _CMDS]


def command(text):
    """Câu lệnh ngắn của khung chat (0 USD, theo luật): 'analyse' | 'write' | 'idea' | 'script' | 'cancel' | None. Chỉ tin MỘT dòng ≤ 80 ký tự."""
    import unicodedata
    t = unicodedata.normalize('NFC', (text or '').strip())
    if not t or '\n' in t or len(t) > 80:
        return None
    return next((name for name, rx in _CMD_RES if rx.match(t)), None)


# Rà 09/10: "thôi" / "bỏ qua" là lời từ chối mềm — chỉ "hủy" (đúng chữ) mới xóa nội dung đang chờ; khi có đề xuất thoại KLD-10 đang mở thì
# "thôi" / "bỏ qua" là câu trả lời cho Biên kịch (dialogue_chat), không phải lệnh hủy.
_HARD_CANCEL = re.compile(r'^\s*(?:hủy|huỷ|hủy bỏ|huỷ bỏ|cancel)' + _TAIL + r'\s*[.!…]*\s*$', re.I)


def hard_cancel(text):
    import unicodedata
    return bool(_HARD_CANCEL.match(unicodedata.normalize('NFC', (text or '').strip())))


def _soft_cancel_to_writer(text, p, pid):
    """'thôi' / 'bỏ qua' (không phải 'hủy') khi dự án đang có đề xuất thoại mở → chat với Biên kịch."""
    return command(text) == 'cancel' and not hard_cancel(text) and bool(_known_codes(p, pid)[1])


def intent(text, p=None, pid=None):
    if re.match(r'^\s*(?:sửa|viết lại|chỉnh)\s+cảnh\s+\d+\b', text, re.I):
        return 'edit'
    # Rà 09/10 (hồi quy S14.43 mục 5): "viết kịch bản từ dàn ý này" là yêu cầu viết chi tiết (expand_request) — xét TRƯỚC lệnh 'write'.
    if idea_to_script.expand_request(text) is not None:
        return 'idea'
    if _soft_cancel_to_writer(text, p, pid):
        return 'chat'                                   # "thôi" khi có đề xuất thoại mở = trả lời Biên kịch, không xóa gì
    if command(text):
        return 'command'                                # step1_box._command chạy đúng hành động (không thành nội dung)
    classification = idea_to_script.classify(text)
    if classification['kind'] == 'unsure' and '\n' in text:
        return 'unsure'
    if classification['kind'] == 'script':
        return 'script'
    if re.match(r'^\s*(?:ý tưởng|viết kịch bản|dàn ý)\b', text, re.I):
        return 'idea'
    if is_dialogue_talk(text, p, pid):
        return 'chat'
    # A clear question / greeting is conversation.
    if re.match(r'^\s*(?:bạn|tại sao|vì sao|thế nào|làm sao|có nên|nên|chào|cảm ơn|hãy giải thích)\b', text, re.I):
        return 'chat'
    if '?' in text and classification['kind'] != 'idea':
        return 'chat'
    # Người dùng 06/10: không chắc thì HỎI LẠI (0 USD) thay vì tự quyết — vd một ý tưởng ngắn không kèm câu yêu cầu, hay một câu có "?"
    # mà đọc như ý tưởng → hỏi "dùng làm ý tưởng / hỏi Claude / đây là kịch bản" trước khi đi tiếp.
    return 'ask'


def send(p, pid, text, client, record_user=True):
    access.need_edit(p, pid, 'gửi chat Kịch bản')
    if record_user:                                     # False: tin đã ghi lúc hỏi lại (intent 'ask')
        append(p, pid, 'user', text)
    if client is None:
        append(p, pid, 'assistant', 'Chưa kết nối Claude — kiểm tra Cài đặt rồi gửi lại. Chưa gọi model.')
        raise ValueError('Chưa kết nối Claude — kiểm tra Cài đặt rồi gửi lại.')
    context = history(p, pid)
    all_lines = dialogue_chat.lines(p, pid)
    prompt = dialogue_chat.prompt(p, pid, context[-RECENT:], all_lines)
    try:
        with llm_runner.tagged(STAGE, pid):
            reply = client.complete(prompt)
        if not reply.text.strip():
            raise llm_runner.LlmError('Claude trả về tin nhắn trống', code='bad_text')
    except Exception as exc:
        append(p, pid, 'assistant', f'Chưa nhận được câu trả lời: {exc}. Không tự gửi lại; bạn có thể gửi một tin mới.')
        raise
    got = dialogue_chat.parse(reply.text)
    notes, applied_msg = [], None
    if got['apply']:
        applied_msg = _apply_turn(p, pid, context, got['apply'], notes)
    # Rà 09/10: đọc lại câu thoại SAU khi áp dụng — đề xuất mới cùng lượt cho cùng Lx phải mang câu cũ là câu vừa áp dụng.
    by_id = {ln['id']: ln for ln in (dialogue_chat.lines(p, pid) if applied_msg else all_lines)}
    proposals, n = [], dialogue_chat.next_id(context)
    for pr in got['proposals']:
        ln = by_id.get(pr['line'])
        if ln is None:                                  # luật 1: không im lặng bỏ đề xuất trỏ vào câu không có
            notes.append(f"Đề xuất cho {pr['line']} bị bỏ: không có câu thoại {pr['line']} trong dự án.")
            continue
        proposals.append({'id': f'P{n}', 'line': ln['id'], 'speaker': ln['speaker'], 'old': ln['text'],
                          'new': str(pr['new']).strip(), 'why': str(pr.get('why') or '').strip(), 'state': 'open'})
        n += 1
    if proposals:                                       # đề xuất cũ còn mở cho cùng câu → 'superseded' (thẻ không còn "chờ đồng ý")
        lines_now = {pr['line'] for pr in proposals}
        old_ids = [pr['id'] for pr in dialogue_chat.open_proposals(history(p, pid)) if pr['line'] in lines_now]
        if old_ids:
            _set_state(p, pid, old_ids, 'superseded')
    text_out = got['reply'] or ('Đề xuất sửa thoại:' if proposals else '(Claude không trả lời bằng chữ.)')
    if notes:
        text_out += '\n\n' + '\n'.join('⚠ ' + x for x in notes)
    append(p, pid, 'assistant', text_out, **({'proposals': proposals} if proposals else {}))
    if applied_msg:
        append(p, pid, 'assistant', applied_msg.pop('text'), **applied_msg)
    return text_out


def _apply_turn(p, pid, context, wanted, notes):
    """Áp dụng các Px Claude trả về — CHỈ khi tin cuối của người là lời đồng ý rõ. Tự áp dụng chỉ các đề xuất của tin assistant GẦN
    NHẤT có đề xuất ("câu 1" = đề xuất vừa nói); đề xuất cũ hơn chỉ khi người gọi đích danh Px / Lx. Trả tin "Đã áp dụng …" hoặc None."""
    last_user = next((m['text'] for m in reversed(context) if m['role'] == 'user'), '')
    if not dialogue_chat.approved(last_user):           # Claude muốn áp dụng nhưng người chưa nói đồng ý rõ → không sửa gì
        notes.append('Chưa áp dụng: tin của bạn chưa phải lời đồng ý rõ — gõ vd "ok áp dụng câu 1" để sửa.')
        return None
    wanted = list(dict.fromkeys(wanted))                # mã trùng → một lần
    open_by_id = {pr['id']: pr for pr in dialogue_chat.open_proposals(context)}
    latest = next((m for m in reversed(context) if m['role'] == 'assistant' and m.get('proposals')), {})
    latest_ids = {pr['id'] for pr in latest.get('proposals') or []}
    named = dialogue_chat.named_codes(last_user)
    picked, closed, older = [], [], []
    for x in wanted:
        pr = open_by_id.get(x)
        if pr is None:
            closed.append(x)
        elif x in latest_ids or x in named or pr['line'] in named:
            picked.append(pr)
        else:
            older.append(x)
    if closed:
        notes.append(f"Không áp dụng {', '.join(closed)}: đề xuất không còn mở (đã áp dụng / đã hoàn tác / có đề xuất mới hơn).")
    if older:
        notes.append(f"Chưa áp dụng {', '.join(older)}: đề xuất ở lượt trước — gõ đích danh (vd \"ok áp dụng {older[0]}\") để áp dụng.")
    if not picked:
        return None
    res = dialogue_chat.apply(p, pid, picked)
    for key, why in res['skipped'].items():
        notes.append(f'Không áp dụng {key}: {why}.')
    notes.extend(res.get('notes') or [])
    if not res['applied']:
        return None
    _set_state(p, pid, res['applied'], 'applied')
    done = [pr for pr in picked if pr['id'] in res['applied']]
    return {'text': 'Đã áp dụng ' + '; '.join(f"{pr['id']} ({pr['line']}): “{pr['new']}”" for pr in done)
                    + ' — thoại cảnh, đoạn kịch bản cảnh và kịch bản dự án (0 USD).',
            'applied': res['applied'], 'undo': res['undo'], 'after': res['after'], 'undone': False}


def undo(p, pid, i):
    """↩ Hoàn tác lần áp dụng ở tin thứ i: ghi lại nguyên trạng cảnh + kịch bản dự án trước khi áp dụng; đề xuất → 'undone'.
    Từ chối (nói rõ) khi tin không phải lần áp dụng, đã hoàn tác, hoặc cảnh / kịch bản đã đổi tiếp sau đó (không đè sửa mới)."""
    access.need_edit(p, pid, 'hoàn tác thoại')
    msgs = history(p, pid)
    i = int(i)
    if not 0 <= i < len(msgs) or not msgs[i].get('applied'):
        raise ValueError('Tin này không phải một lần áp dụng thoại — không có gì để hoàn tác.')
    m = msgs[i]
    if m.get('undone'):
        raise ValueError('Lần áp dụng này đã được hoàn tác rồi.')
    if not m.get('after') or dialogue_chat.changed_since(p, pid, m['undo'], m['after']):
        raise ValueError('Thoại / kịch bản đã đổi sau lần áp dụng này — không hoàn tác để khỏi đè sửa mới. Nhờ Biên kịch đề xuất lại câu cũ.')
    dialogue_chat.undo(p, pid, m['undo'])
    _set(p, pid, i, 'undone', True)
    _set_state(p, pid, m['applied'], 'undone')
    append(p, pid, 'assistant', f"↩ Đã hoàn tác {', '.join(m['applied'])} — thoại về như trước khi áp dụng (0 USD).")
