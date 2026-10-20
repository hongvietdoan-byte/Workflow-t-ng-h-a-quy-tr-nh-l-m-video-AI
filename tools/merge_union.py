"""Hợp xung đột 'cả hai bên đều thêm' cho devsys/areas.json (gộp danh sách) và core/features.py (giữ cả hai mục dict)."""
import json
import re
import sys

CONFLICT = re.compile(r'<<<<<<< [^\n]*\n(.*?)=======\n(.*?)>>>>>>> [^\n]*\n', re.S)


def union_json_lists(ours: str, theirs: str) -> str:
    out = []
    for line in ours.splitlines(True):
        k = re.match(r'(\s*)"(\w+)": (\[.*\])(,?)\s*$', line)
        if not k:
            out.append(line)
            continue
        lt = re.search(r'"%s": (\[.*?\])' % k.group(2), theirs)
        a = json.loads(k.group(3))
        b = json.loads(lt.group(1)) if lt else []
        out.append('%s"%s": %s%s\n' % (k.group(1), k.group(2), json.dumps(list(dict.fromkeys(a + b)), ensure_ascii=False), k.group(4)))
    return ''.join(out)


def keep_both_dict_entries(ours: str, theirs: str) -> str:
    sep = '' if ours.rstrip().endswith('},') else '    },\n'
    return ours + sep + theirs


for path in sys.argv[1:]:
    s = open(path, encoding='utf-8').read()
    fn = union_json_lists if path.endswith('.json') else keep_both_dict_entries
    s = CONFLICT.sub(lambda m: fn(m.group(1), m.group(2)), s)
    if path.endswith('.json'):
        json.loads(s)
    else:
        compile(s, path, 'exec')
    open(path, 'w', encoding='utf-8').write(s)
    print('ok', path)
