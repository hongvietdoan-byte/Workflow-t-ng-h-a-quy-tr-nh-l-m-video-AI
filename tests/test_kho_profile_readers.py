"""Kiểm đường gọi thật bằng AST, không dựa vào chuỗi trong comment/docstring."""
import ast
from pathlib import Path


def _legacy_references(tree):
    banned = {'assets': {'get_profile','standard_for','outfit_images','outfit_label'}, 'character_forms':{'for_shot','for_rows'}}
    aliases={name:name for name in banned}
    violations=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            for item in node.names:
                if item.name.split('.')[-1] in banned and item.asname:
                    aliases[item.asname]=item.name.split('.')[-1]
        elif isinstance(node,ast.ImportFrom):
            module=(node.module or '').split('.')[-1]
            for item in node.names:
                if module in banned and item.name in banned[module]:
                    violations.append(node.lineno)
                elif item.name in banned:
                    aliases[item.asname or item.name]=item.name
    for node in ast.walk(tree):
        if isinstance(node,ast.Attribute):
            base=node.value
            name=aliases.get(base.id) if isinstance(base,ast.Name) else base.attr if isinstance(base,ast.Attribute) else None
            if node.attr in banned.get(name,set()):
                violations.append(node.lineno)
    return violations


def test_reader_scan_resolves_alias_and_function_references():
    samples=['from core import assets as lib\nlib.get_profile(c,1)',
             'import core.assets as lib\nread = lib.get_profile\nread(c,1)',
             'import core.assets\ncore.assets.standard_for(c,1,n)',
             'from core.assets import get_profile as read\nread(c,1)',
             'from . import character_forms as cf\ncf.for_rows(c,1,[])']
    assert all(_legacy_references(ast.parse(source)) for source in samples)
    assert not _legacy_references(ast.parse('from core import kho_profile as lib\nlib.read(c,1)'))


def test_all_readers_use_kho_profile():
    violations=[]
    for root in ('core','dashboard','tools'):
        for p in Path(root).rglob('*.py'):
            if p.as_posix() in ('core/assets.py','core/kho_profile.py'):
                continue  # Lõi lưu trữ và adapter duy nhất được phép gọi đường cũ.
            tree=ast.parse(p.read_text(encoding='utf-8-sig'))
            violations.extend(f'{p}:{line}' for line in _legacy_references(tree))
    assert violations == []
