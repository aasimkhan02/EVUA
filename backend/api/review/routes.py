from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from api.auth.utils import get_current_user
from api.auth.models import UserOut
from db import get_db

router = APIRouter(prefix="/review", tags=["review"])


class ReviewInput(BaseModel):
    change_id: str
    session_id: Optional[str] = None
    decision: str  # approve | edit | reject
    edited_after_id: Optional[str] = None
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    status: str


@router.post("/submit", response_model=ReviewResponse)
async def submit_review(
    input: ReviewInput,
    current_user: UserOut = Depends(get_current_user),
):
    db = get_db()
    doc = {
        "change_id": input.change_id,
        "session_id": input.session_id,
        "user_id": current_user.id,
        "decision": input.decision,
        "edited_after_id": input.edited_after_id,
        "comment": input.comment,
        "created_at": datetime.now(timezone.utc),
    }
    await db.decisions.update_one(
        {"change_id": input.change_id, "user_id": current_user.id},
        {"$set": doc},
        upsert=True,
    )
    return ReviewResponse(status="ok")


@router.get("/decisions")
async def list_decisions(current_user: UserOut = Depends(get_current_user)):
    db = get_db()
    cursor = db.decisions.find({"user_id": current_user.id})
    results = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        results.append(doc)
    return results
