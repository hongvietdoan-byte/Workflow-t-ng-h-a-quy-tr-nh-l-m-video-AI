"""Dựng shot vật kỹ năng bằng GHÉP code (lỗi hệ thống 3, #27 shot 16): clip người (ném) tới lúc vật chạm đất + khung cuối (vật đã
dựng) trồi lên từ dưới trong vài khung + rung tắt dần, giữ tới hết clip. 0 USD, không gọi API, không ghi CSDL.

    py tools/skill_object_composite.py --clip videos/16_kling.mp4 --end images/end_284_21.png --cut 0.87 --out videos/16_ghep.mp4
"""
import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import skill_objects


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clip", required=True, help="clip người (phần ném / chạy), giữ cỡ + fps + độ dài")
    ap.add_argument("--end", required=True, help="khung cuối: vật kỹ năng đã dựng xong (ảnh)")
    ap.add_argument("--cut", type=float, required=True, help="giây vật chạm đất (bắt đầu trồi lên)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--rise", type=int, default=7, help="số khung trồi lên (mặc định 7, như shot 16)")
    ap.add_argument("--shake", type=int, default=8, help="số khung rung sau khi dựng xong")
    ap.add_argument("--shake-px", type=int, default=10)
    ap.add_argument("--top", type=int, default=None, help="hàng điểm ảnh mép trên của vật (mặc định tự đo: khác clip ≥ 1/2 bề ngang)")
    a = ap.parse_args(argv)
    for p in (a.clip, a.end):
        if not Path(p).exists():
            print(f"không thấy tệp: {p}", file=sys.stderr)
            return 2
    res = skill_objects.compose(a.clip, a.end, a.out, a.cut, a.rise, a.shake, a.shake_px, a.top)
    sys.stdout.buffer.write((json.dumps(res, ensure_ascii=False) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
