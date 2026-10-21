"""Kiểm đường gọi thật bằng AST, không dựa vào chuỗi trong comment/docstring."""
import ast
from pathlib import Path


def test_all_readers_use_kho_profile():
    banned = {'assets': {'get_profile','standard_for','outfit_images','outfit_label'}, 'character_forms':{'for_shot','for_rows'}}
    violations=[]
    for root in ('core','dashboard','tools'):
        for p in Path(root).rglob('*.py'):
            if p.as_posix() in ('core/assets.py','core/kho_profile.py'):
                continue  # Lõi lưu trữ và adapter duy nhất được phép gọi đường cũ.
            tree=ast.parse(p.read_text(encoding='utf-8-sig'))
            for n in ast.walk(tree):
                if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name):
                    if n.func.attr in banned.get(n.func.value.id,set()):
                        violations.append(f'{p}:{n.lineno}')
                if isinstance(n,ast.ImportFrom) and n.module and n.module.split('.')[-1] in banned:
                    for a in n.names:
                        if a.name in banned[n.module.split('.')[-1]]:
                            violations.append(f'{p}:{n.lineno}:import')
    assert violations == []
