from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/review", tags=["review"])

class ReviewInput(BaseModel):
    change_id: str
    decision: str  # approve | edit | reject
    edited_after_id: Optional[str] = None
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    status: str


# In-memory store for demo (replace with DB later)
_DECISIONS: dict[str, ReviewInput] = {}


@router.post("/submit", response_model=ReviewResponse)
def submit_review(input: ReviewInput):
    _DECISIONS[input.change_id] = input
    return ReviewResponse(status="ok")


@router.get("/decisions")
def list_decisions():
    return list(_DECISIONS.values())
