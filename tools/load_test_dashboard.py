"""Điểm vào chính thức cho phép đo tải M8.3; dùng lại harness đã rà ở load_test_ui."""

import os
import sys
from typing import Optional, Sequence

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools import load_test_ui  # noqa: E402


def main(argv: Optional[Sequence[str]] = None) -> int:
    return load_test_ui.main(list(argv) if argv is not None else None)


if __name__ == "__main__":
    raise SystemExit(main())
