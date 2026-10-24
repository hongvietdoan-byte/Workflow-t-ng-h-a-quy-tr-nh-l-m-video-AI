"""Kiểm đường gọi thật bằng AST, không dựa vào chuỗi trong comment/docstring."""
import ast
from pathlib import Path
import re
from collections import Counter


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


def test_explicit_profile_sql_is_in_reviewed_inventory():
    # Mỗi ngoại lệ có hàm + số statement cố định + lý do; thêm đường SQL mới phải rà lại.
    reviewed = {
        ('core/assets.py','get_profile'):(1,'Lõi lưu trữ raw duy nhất cho adapter'),
        ('core/assets.py','set_profile'):(1,'Writer v1; schema v2 chuyển qua CAS trước nhánh này'),
        ('core/assets.py','merge'):(2,'Gộp bảo thủ chặn mọi khác biệt v2 trước filesystem'),
        ('core/assets.py','set_size'):(2,'Metadata kích thước vật riêng; guard chung chờ M0.10'),
        ('core/kho_profile.py','save'):(3,'Writer v2 actor/revision/CAS; đọc, cập nhật có điều kiện, đọc lại khi xung đột'),
        ('core/kho_profile.py','write_fields'):(3,'Writer chung v1 CAS/audit; v2 chuyển sang save'),
        ('core/before_run.py','_input_items'):(2,'Projection nhận diện; nội dung ON đọc lại adapter'),
        ('core/change_review.py','build_prompt'):(1,'Raw cho OFF; khóa v2 ON từ adapter'),
        ('core/director_blockout.py','scene_uses_blockout'):(1,'Chỉ model3d/path để chọn nhánh sân khấu'),
        ('core/location_pack.py','set_model3d'):(1,'Đọc snapshot model3d; ghi qua guard chung write_fields'),
        ('core/location_pack.py','set_script_view'):(1,'Đọc snapshot model3d; ghi qua guard chung write_fields'),
        ('core/stage_auto.py','set_family'):(2,'Chỉ model3d.stage_family'),
        ('core/profile_digest.py','refresh'):(1,'Cache chỉ ghi v1 OFF; v2 mọi cờ không ghi'),
        ('core/project_defaults.py','places_fingerprint'):(1,'Hash raw để phát hiện mọi thay đổi, không diễn giải prompt'),
        ('tools/dryrun_k0b_p24.py','_kho_decl'):(1,'Tool offline; ON adapter, OFF replay legacy'),
        ('tools/kho_merge.py','apply'):(1,'Chỉ chép khi đích trống; plan chặn cả hai profile khác nhau'),
        ('tools/library_audit.py','audit'):(2,'Báo cáo nguyên nguồn, không tạo prompt/gen'),
        ('tools/location_pack.py','run_preview'):(1,'Chỉ model3d preview'),
        ('tools/stage_grid.py','_place_model3d'):(1,'Chỉ model3d/path'),
        ('tools/stage_grid.py','fix_spot_main'):(1,'Chỉ model3d spots'),
        ('tools/stage_grid.py','host_main'):(1,'Chỉ model3d metadata'),
        ('tools/tower_pack.py','spots_of'):(1,'Chỉ model3d spots')}
    found=Counter()
    for root in ('core','dashboard','tools'):
        for path in Path(root).rglob('*.py'):
            tree=ast.parse(path.read_text(encoding='utf-8-sig'))
            parents={child:node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
            for node in ast.walk(tree):
                if not (isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr in ('execute','executemany') and node.args):
                    continue
                sql=' '.join(n.value for n in ast.walk(node.args[0]) if isinstance(n,ast.Constant) and isinstance(n.value,str))
                if not (re.search(r'\bprofile\b',sql,re.I) and re.search(r'\bassets\b',sql,re.I)):
                    continue
                owner=node
                while owner in parents and not isinstance(owner,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    owner=parents[owner]
                found[path.as_posix(),getattr(owner,'name','module')]+=1
    assert found==Counter({key:value[0] for key,value in reviewed.items()})
    assert all(reason for count,reason in reviewed.values())
