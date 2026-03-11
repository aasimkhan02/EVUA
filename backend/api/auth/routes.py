from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from api.auth.models import RegisterInput, LoginInput, UserOut, TokenResponse
from api.auth.utils import hash_password, verify_password, create_access_token, get_current_user
from db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(input: RegisterInput):
    db = get_db()

    existing = await db.users.find_one({"email": input.email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user_doc = {
        "name": input.name,
        "email": input.email,
        "password_hash": hash_password(input.password),
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)

    token = create_access_token(user_id, input.email)
    return TokenResponse(
        access_token=token,
        user=UserOut(
            id=user_id,
            name=input.name,
            email=input.email,
            created_at=user_doc["created_at"],
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(input: LoginInput):
    db = get_db()

    user = await db.users.find_one({"email": input.email})
    if not user or not verify_password(input.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_id = str(user["_id"])
    token = create_access_token(user_id, user["email"])
    return TokenResponse(
        access_token=token,
        user=UserOut(
            id=user_id,
            name=user["name"],
            email=user["email"],
            created_at=user["created_at"],
        ),
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: UserOut = Depends(get_current_user)):
    return current_user
