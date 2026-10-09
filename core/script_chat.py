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
_DIALOGUE_TALK = re.compile(_W + r'(?:thoại|câu\s*\d+|[LP]\d+)' + _E, re.I)
_APPROVE_TARGET = re.compile(_W + r'(?:ok|oke|okay|okie|đồng ý|duyệt|chốt|áp dụng|apply)' + _E + r'.*?' + _W +
                             r'(?:áp dụng|câu|hết|tất cả|cả hai|cả ba|[LP]\d+|đề xuất|bản (?:mới|này|đó))' + _E, re.I)


def is_dialogue_talk(text):
    """Câu ngắn (một dòng) nói về thoại hoặc đồng ý áp dụng đề xuất → chat với Biên kịch (KLD-10)."""
    t = (text or '').strip()
    if not t or '\n' in t or len(t) > 300:
        return False
    return bool(_DIALOGUE_TALK.search(t) or _APPROVE_TARGET.search(t))


def intent(text):
    if re.match(r'^\s*(?:sửa|viết lại|chỉnh)\s+cảnh\s+\d+\b', text, re.I):
        return 'edit'
    if idea_to_script.expand_request(text) is not None:
        return 'idea'
    classification = idea_to_script.classify(text)
    if classification['kind'] == 'unsure' and '\n' in text:
        return 'unsure'
    if classification['kind'] == 'script':
        return 'script'
    if is_dialogue_talk(text):
        return 'chat'
    if re.match(r'^\s*(?:ý tưởng|viết kịch bản|dàn ý)\b', text, re.I):
        return 'idea'
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
    notes = []
    by_id = {ln['id']: ln for ln in all_lines}
    proposals, n = [], dialogue_chat.next_id(context)
    for pr in got['proposals']:
        ln = by_id.get(pr['line'])
        if ln is None:                                  # luật 1: không im lặng bỏ đề xuất trỏ vào câu không có
            notes.append(f"Đề xuất cho {pr['line']} bị bỏ: không có câu thoại {pr['line']} trong dự án.")
            continue
        proposals.append({'id': f'P{n}', 'line': ln['id'], 'speaker': ln['speaker'], 'old': ln['text'],
                          'new': str(pr['new']).strip(), 'why': str(pr.get('why') or '').strip(), 'state': 'open'})
        n += 1
    applied_msg = None
    if got['apply']:
        last_user = next((m['text'] for m in reversed(context) if m['role'] == 'user'), '')
        open_by_id = {pr['id']: pr for pr in dialogue_chat.open_proposals(context)}
        if not dialogue_chat.approved(last_user):       # Claude muốn áp dụng nhưng người chưa nói đồng ý → không sửa gì
            notes.append('Chưa áp dụng: tin của bạn chưa có lời đồng ý rõ — gõ vd "ok áp dụng câu 1" để sửa.')
        else:
            picked = [open_by_id[x] for x in got['apply'] if x in open_by_id]
            closed = [x for x in got['apply'] if x not in open_by_id]
            if closed:
                notes.append(f"Không áp dụng {', '.join(closed)}: đề xuất không còn mở (đã áp dụng / đã hoàn tác / có đề xuất mới hơn).")
            if picked:
                res = dialogue_chat.apply(p, pid, picked)
                for key, why in res['skipped'].items():
                    notes.append(f'Không áp dụng {key}: {why}.')
                if res['applied']:
                    _set_state(p, pid, res['applied'], 'applied')
                    done = [pr for pr in picked if pr['id'] in res['applied']]
                    applied_msg = {'text': 'Đã áp dụng ' + '; '.join(f"{pr['id']} ({pr['line']}): “{pr['new']}”" for pr in done)
                                   + ' — thoại cảnh, đoạn kịch bản cảnh và kịch bản dự án (0 USD).',
                                   'applied': res['applied'], 'undo': res['undo'], 'after': _after(p, pid, res['undo']), 'undone': False}
    text_out = got['reply'] or ('Đề xuất sửa thoại:' if proposals else '(Claude không trả lời bằng chữ.)')
    if notes:
        text_out += '\n\n' + '\n'.join('⚠ ' + x for x in notes)
    append(p, pid, 'assistant', text_out, **({'proposals': proposals} if proposals else {}))
    if applied_msg:
        append(p, pid, 'assistant', applied_msg.pop('text'), **applied_msg)
    return text_out


def _after(p, pid, snapshot):
    """Trạng thái ngay sau khi áp dụng (các cảnh đã sửa + văn bản kịch bản) — hoàn tác chỉ chạy khi chưa ai đổi tiếp."""
    out = {'script_text': p.project(pid)['script_text'] or '', 'scenes': {}}
    for idx in (snapshot.get('scenes') or {}):
        row = p.conn.execute('SELECT data FROM scenes WHERE project_id=? AND idx=?', (pid, int(idx))).fetchone()
        data = json.loads(row['data'] or '{}') if row else {}
        out['scenes'][idx] = {'dialogue': data.get('dialogue'), 'text': data.get('text')}
    return out


def undo(p, pid, i):
    """↩ Hoàn tác lần áp dụng ở tin thứ i: khôi phục thoại cảnh + đoạn kịch bản cảnh + kịch bản dự án; đề xuất → 'undone'.
    Từ chối (nói rõ) khi tin không phải lần áp dụng, đã hoàn tác, hoặc thoại / kịch bản đã đổi tiếp sau đó (không đè sửa mới)."""
    access.need_edit(p, pid, 'hoàn tác thoại')
    msgs = history(p, pid)
    i = int(i)
    if not 0 <= i < len(msgs) or not msgs[i].get('applied'):
        raise ValueError('Tin này không phải một lần áp dụng thoại — không có gì để hoàn tác.')
    m = msgs[i]
    if m.get('undone'):
        raise ValueError('Lần áp dụng này đã được hoàn tác rồi.')
    if m.get('after') and _after(p, pid, m['undo']) != m['after']:
        raise ValueError('Thoại / kịch bản đã đổi sau lần áp dụng này — không hoàn tác để khỏi đè sửa mới. Nhờ Biên kịch đề xuất lại câu cũ.')
    dialogue_chat.undo(p, pid, m['undo'])
    _set(p, pid, i, 'undone', True)
    _set_state(p, pid, m['applied'], 'undone')
    append(p, pid, 'assistant', f"↩ Đã hoàn tác {', '.join(m['applied'])} — thoại về như trước khi áp dụng (0 USD).")
