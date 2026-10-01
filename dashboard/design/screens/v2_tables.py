"""HTML table helper shared by lane D screens (Nhóm, Theo dõi). Cells are escaped unless wrapped in Raw (for pills / meters made by
dashboard.design.components, which already escape their own text)."""
from html import escape
from typing import Iterable, Sequence


class Raw(str):
    """Pre-built, already-escaped HTML."""


def _cell(v) -> str:
    return str(v) if isinstance(v, Raw) else escape("" if v is None else str(v))


def table(headers: Sequence[str], rows: Iterable[Sequence], cls: str = "", num_cols: Sequence[int] = (), empty: str = "Chưa có dữ liệu") -> str:
    """`v2-table` HTML (dark/light aware). `num_cols` = column indexes aligned right."""
    head = "".join(f"<th{' class=num' if i in num_cols else ''}>{escape(h)}</th>" for i, h in enumerate(headers))
    body = []
    for r in rows:
        body.append("<tr>" + "".join(f"<td{' class=num' if i in num_cols else ''}>{_cell(v)}</td>" for i, v in enumerate(r)) + "</tr>")
    if not body:
        body.append(f'<tr><td colspan="{len(headers)}" style="color:var(--muted)">{escape(empty)}</td></tr>')
    return f'<div class="{cls.split()[0] + "wrap" if cls else ""}"><table class="v2-table {escape(cls)}"><tr>{head}</tr>{"".join(body)}</table></div>'
