"""Tùy chọn riêng từng người (người dùng 07/10: hiệu ứng nút sáng 'luôn bật ở mọi tài khoản, ai muốn tắt thì tắt sau').
Lưu trong app_settings theo khóa `pref:<email>:<name>`; không có dòng = giá trị mặc định. Người không đăng nhập (email rỗng) dùng
khóa chung `pref::<name>` của máy đó."""
from typing import Optional

KNOWN = {"next_glow": True}          # tên → mặc định


def _key(email: Optional[str], name: str) -> str:
    if name not in KNOWN:
        raise ValueError(f"Không có tùy chọn “{name}”")
    return f"pref:{(email or '').strip().lower()}:{name}"


def get(conn, email: Optional[str], name: str) -> bool:
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (_key(email, name),)).fetchone()
    return KNOWN[name] if row is None else row[0] == "1"


def set(conn, email: Optional[str], name: str, on: bool) -> None:  # noqa: A001 - matches get/set of the other stores
    conn.execute("INSERT INTO app_settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (_key(email, name), "1" if on else "0"))
    conn.commit()
