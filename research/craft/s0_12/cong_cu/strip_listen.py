"""Luu so do cua listen.json, bo loi chep (lines). Usage: py strip_listen.py <listen_dir> <out.json>"""
import sys, json
d = json.load(open(sys.argv[1] + "/listen.json", encoding="utf-8"))
d.pop("lines", None)
json.dump(d, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)
