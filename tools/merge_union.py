"""Hợp JSON theo cấu trúc ba phía; lỗi parse không ghi đè tệp."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

CONFLICT = re.compile(r'<<<<<<< [^\n]*\n(.*?)=======\n(.*?)>>>>>>> [^\n]*\n', re.S)
_MISSING = object()


def merge_json(base, ours, theirs):
    if ours == theirs:
        return ours
    if ours == base:
        return theirs
    if theirs == base:
        return ours
    if isinstance(ours, dict) and isinstance(theirs, dict):
        base = base if isinstance(base, dict) else {}
        result = {}
        for key in dict.fromkeys([*ours, *theirs]):
            value = merge_json(base.get(key, _MISSING), ours.get(key, _MISSING), theirs.get(key, _MISSING))
            if value is not _MISSING:
                result[key] = value
        return result
    if isinstance(ours, list) and isinstance(theirs, list):
        # Danh sách area dùng id ổn định, không nhân bản area rồi mất mapping.
        if all(isinstance(x, dict) and 'id' in x for x in ours + theirs):
            def indexed(items):
                result = {x['id']: x for x in items}
                if len(result) != len(items):
                    raise ValueError('id JSON trùng')
                return result
            old = indexed(base) if isinstance(base, list) else {}
            left, right = indexed(ours), indexed(theirs)
            values = [merge_json(old.get(k, _MISSING), left.get(k, _MISSING), right.get(k, _MISSING))
                      for k in dict.fromkeys([*left, *right])]
            return [value for value in values if value is not _MISSING]
        result = list(ours)
        for item in theirs:
            if item not in result:
                result.append(item)
        return result
    raise ValueError('Xung đột scalar JSON cần giải quyết bằng tay')


def format_json(value, level=0):
    if isinstance(value, dict):
        if not value:
            return '{}'
        pad = '  ' * (level + 1)
        return '{\n' + ',\n'.join(pad + json.dumps(k, ensure_ascii=False) + ': ' + format_json(v, level + 1)
                                  for k, v in value.items()) + '\n' + '  ' * level + '}'
    if isinstance(value, list) and any(isinstance(x, (dict, list)) for x in value):
        return '[\n' + ',\n'.join('  ' * (level + 1) + format_json(x, level + 1) for x in value) + '\n' + '  ' * level + ']'
    return json.dumps(value, ensure_ascii=False)


def read_stage(path, stage):
    path = Path(path).resolve()
    git = next((p for p in ('C:/Program Files/Git/cmd/git.exe', '/usr/bin/git', '/bin/git') if Path(p).is_file()), None)
    if git is None:
        raise ValueError('Không tìm thấy Git native')
    env = {'SYSTEMROOT': 'C:/Windows'} if os.name == 'nt' else {}
    root = subprocess.run([git, 'rev-parse', '--show-toplevel'], cwd=path.parent, env=env,
                          check=True, capture_output=True, text=True, encoding='utf-8').stdout.strip()
    relative = path.relative_to(Path(root).resolve()).as_posix()
    return subprocess.run([git, 'show', f':{stage}:{relative}'], cwd=root, env=env, check=True,
                          capture_output=True, text=True, encoding='utf-8').stdout


def resolve_json(path):
    # Đọc/parse tất cả trước, chỉ ghi khi toàn bộ merge thành công.
    base, ours, theirs = [json.loads(read_stage(path, n)) for n in (1, 2, 3)]
    merged = merge_json(base, ours, theirs)
    text = format_json(merged) + '\n'
    json.loads(text)
    Path(path).write_text(text, encoding='utf-8')


def keep_both_dict_entries(ours, theirs):
    sep = '' if ours.rstrip().endswith('},') else '    },\n'
    return ours + sep + theirs


def main(paths=None):
    for path in sys.argv[1:] if paths is None else paths:
        if str(path).endswith('.json'):
            resolve_json(path)
        else:
            text = Path(path).read_text(encoding='utf-8')
            text = CONFLICT.sub(lambda m: keep_both_dict_entries(m.group(1), m.group(2)), text)
            compile(text, str(path), 'exec')
            Path(path).write_text(text, encoding='utf-8')
        print('ok', path)


if __name__ == '__main__':
    main()
