"""Set (or reset) the OWNER's dashboard password from a terminal on the machine that runs the dashboard.

  py tools/reset_owner.py

Needs access to this machine and its database, which is exactly the trust the owner account rests on. All sessions of the
owner are signed out and the reset is written to the audit log.
"""
import getpass
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import auth  # noqa: E402
from core.db import connect  # noqa: E402

DB = os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite"))


def main():
    conn = connect(DB)
    auth.ensure_owner(conn, os.path.dirname(DB) or "data")
    print(f"Owner: {auth.OWNER_EMAIL}")
    pw = getpass.getpass("Mat khau moi (>= 8 ky tu): ")
    if pw != getpass.getpass("Nhap lai: "):
        sys.exit("Hai mat khau khong giong nhau.")
    try:
        auth.check_new_password(pw, auth.OWNER_EMAIL)
    except auth.AuthError as e:
        sys.exit(str(e))
    conn.execute("UPDATE users SET pw_hash=?, invite_hash=NULL, invite_expires=NULL, failed=0, locked_until=NULL, active=1 WHERE email=?",
                 (auth.hash_password(pw), auth.OWNER_EMAIL))
    conn.commit()
    auth.revoke_sessions(conn, auth.OWNER_EMAIL)
    auth.audit(conn, "system", "owner_password_reset", "from terminal")
    auth.ensure_owner(conn, os.path.dirname(DB) or "data")       # removes a leftover setup-code file
    print("Da dat lai mat khau Owner.")


if __name__ == "__main__":
    main()
