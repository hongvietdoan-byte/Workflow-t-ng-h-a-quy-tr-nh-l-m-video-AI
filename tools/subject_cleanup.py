"""Kho chủ thể: báo cáo ngoại tuyến chỉ đọc; không tải/xóa/nạp cấu hình provider.

Ví dụ: py tools/subject_cleanup.py --db <bản-sao.sqlite> --snapshot <assets.json>
Snapshot JSON là danh sách asset đã xuất riêng. Không phải lệnh duyệt/apply.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main(argv=None):
    from core import subjects
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True, help='CSDL chỉ đọc (nên dùng bản sao)')
    parser.add_argument('--snapshot', required=True, help='JSON danh sách asset ngoại tuyến, không chứa credential')
    args = parser.parse_args(argv)
    try:
        assets = json.loads(Path(args.snapshot).read_text(encoding='utf-8'))
        if not isinstance(assets, list) or not all(isinstance(a, dict) for a in assets):
            raise ValueError('snapshot không đúng định dạng')
        # Chỉ whitelist metadata cần thiết; không đưa raw payload/credential ra stdout.
        assets = [{k: a.get(k) for k in ('asset_id', 'provider_status')} for a in assets]
        with sqlite3.connect(Path(args.db).resolve().as_uri() + '?mode=ro', uri=True) as conn:
            conn.execute('PRAGMA query_only=ON')
            dependencies = subjects.cleanup_dependencies(conn, assets)
            plan = subjects.auto_clean_candidates(assets, dependencies)
        plan['notice'] = 'DRY-RUN ngoại tuyến, snapshot chưa xác minh hiện thời; legacy dependency UNKNOWN được giữ. Không có apply.'
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, sqlite3.Error):
        print('VÀNG: không đọc được bản sao/snapshot; giữ nguyên toàn bộ asset, không xóa.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
