from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from backend.schemas import RegisterRequest, TokenResponse
from typing import Literal
from pydantic import BaseModel
from backend.auth import users
from backend.auth.dependencies import require_role
from backend.auth.security import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", status_code=201)
def register(body: RegisterRequest):
    users.create_user(body.username, body.password, "user")
    return {"message": "Registered"}

@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = users.get_user(form.username)
    if not user or user["status"] != "active" or not verify_password(form.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password")
    return TokenResponse(
        access_token=create_access_token(form.username, user["role"]),
        role=user["role"],
    )


class AccountUpdate(BaseModel):
    role: Literal["user", "staff", "admin"]
    status: Literal["active", "disabled"]


@router.get("/users")
def list_accounts(actor=Depends(require_role("admin"))):
    return users.list_users()


@router.patch("/users/{username}")
def edit_account(username: str, body: AccountUpdate, actor=Depends(require_role("admin"))):
    if username == actor["username"] and (body.role != "admin" or body.status != "active"):
        raise HTTPException(409, "Use another administrator to change your own access.")
    if not users.update_user(username, body.role, body.status):
        raise HTTPException(404, "User not found")
    return {"username": username, **body.model_dump()}
