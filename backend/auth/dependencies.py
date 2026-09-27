import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from backend.auth.security import decode_token
from backend.auth.users import get_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = decode_token(token)
        account = get_user(payload["sub"])
        if not account or account["status"] != "active":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account is unavailable")
        return {"username": account["username"], "role": account["role"], "id": account["id"]}
    except (jwt.PyJWTError, KeyError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

def require_role(*roles: str):
    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user
    return checker
