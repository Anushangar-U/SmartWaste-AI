from backend.auth.security import hash_password
from backend.config import settings

USERS: dict[str, dict] = {}

def seed_admin():
    if settings.admin_password:
        USERS[settings.admin_username] = {
            "password_hash": hash_password(settings.admin_password),
            "role": "admin",
        }