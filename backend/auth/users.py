import sqlite3
import uuid
from backend.auth.security import hash_password
from backend.config import settings
from backend.database import connection
from backend.repositories.complaints import now, Conflict


def get_user(username):
    with connection() as db:
        row = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return dict(row) if row else None


def create_user(username, password, role="user"):
    hashed = hash_password(password)
    try:
        with connection() as db:
            db.execute("INSERT INTO users (id,username,password_hash,role,created_at) VALUES (?,?,?,?,?)",
                       (str(uuid.uuid4()), username, hashed, role, now()))
    except sqlite3.IntegrityError as exc:
        raise Conflict("Username already taken") from exc
    return get_user(username)


def seed_admin():
    # Bootstrap only: never reset stored passwords or reactivate accounts.
    if settings.admin_password and not get_user(settings.admin_username):
        try:
            create_user(settings.admin_username, settings.admin_password, "admin")
        except Conflict:
            pass


def list_users():
    with connection() as db:
        return [dict(r) for r in db.execute("SELECT id,username,role,status,created_at FROM users ORDER BY username")]


def update_user(username, role, status):
    with connection() as db:
        return db.execute("UPDATE users SET role=?,status=? WHERE username=?", (role, status, username)).rowcount > 0
