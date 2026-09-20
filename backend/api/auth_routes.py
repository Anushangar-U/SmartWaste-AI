from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from backend.schemas import RegisterRequest, TokenResponse
from backend.auth.users import USERS
from backend.auth.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", status_code=201)
def register(body: RegisterRequest):
    if body.username in USERS:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")
    USERS[body.username] = {"password_hash": hash_password(body.password), "role": "user"}
    return {"message": "Registered"}

@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = USERS.get(form.username)
    if not user or not verify_password(form.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password")
    return TokenResponse(access_token=create_access_token(form.username, user["role"]))