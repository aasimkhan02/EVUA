from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from db import get_db


async def create_session(user_id: str, benchmark_id: str, benchmark_name: str) -> str:
    db = get_db()
    doc = {
        "user_id": user_id,
        "benchmark_id": benchmark_id,
        "benchmark_name": benchmark_name,
        "status": "running",
        "created_at": datetime.now(timezone.utc),
        "timeline": [],
        "file_count": 0,
        "risk_summary": {"SAFE": 0, "RISKY": 0, "MANUAL": 0},
    }
    result = await db.sessions.insert_one(doc)
    return str(result.inserted_id)


async def add_timeline_event(
    session_id: str,
    stage: str,
    message: str,
    detail: Optional[dict] = None,
    level: str = "info",
):
    db = get_db()
    event = {
        "timestamp": datetime.now(timezone.utc),
        "stage": stage,
        "message": message,
        "detail": detail,
        "level": level,
    }
    await db.sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$push": {"timeline": event}},
    )


async def update_session_status(session_id: str, status: str, file_count: Optional[int] = None, risk_summary: Optional[dict] = None):
    db = get_db()
    update = {"$set": {"status": status}}
    if file_count is not None:
        update["$set"]["file_count"] = file_count
    if risk_summary is not None:
        update["$set"]["risk_summary"] = risk_summary
    await db.sessions.update_one({"_id": ObjectId(session_id)}, update)


async def store_file_diffs(session_id: str, files: list[dict]):
    db = get_db()
    if not files:
        return
    docs = []
    for f in files:
        docs.append({
            "session_id": session_id,
            "file_path": f["file"],
            "before_content": f.get("before_content", ""),
            "after_content": f.get("after_content", ""),
            "unified_diff": f.get("diff", ""),
            "is_new": f.get("is_new", False),
            "risk_level": f.get("risk_level", "SAFE"),
            "reason": f.get("reason", ""),
            "decision": "pending",
        })
    await db.session_files.insert_many(docs)


async def get_session(session_id: str) -> dict | None:
    db = get_db()
    try:
        doc = await db.sessions.find_one({"_id": ObjectId(session_id)})
    except Exception:
        return None
    if doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


async def get_user_sessions(user_id: str) -> list[dict]:
    db = get_db()
    cursor = db.sessions.find({"user_id": user_id}).sort("created_at", -1)
    sessions = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        sessions.append(doc)
    return sessions


async def get_session_files(session_id: str) -> list[dict]:
    db = get_db()
    cursor = db.session_files.find({"session_id": session_id})
    files = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        files.append(doc)
    return files


async def get_file_diff(session_id: str, file_path: str) -> dict | None:
    db = get_db()
    doc = await db.session_files.find_one(
        {"session_id": session_id, "file_path": file_path}
    )
    if doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


async def update_file_decision(session_id: str, file_path: str, decision: str) -> bool:
    db = get_db()
    result = await db.session_files.update_one(
        {"session_id": session_id, "file_path": file_path},
        {"$set": {"decision": decision}},
    )
    return result.modified_count > 0
