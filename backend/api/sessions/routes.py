from fastapi import APIRouter, HTTPException, Depends
from api.auth.utils import get_current_user
from api.auth.models import UserOut
from api.sessions import store
from api.sessions.models import SessionOut, SessionDetail, TimelineEvent, FileChange, FileDiff

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionOut])
async def list_sessions(current_user: UserOut = Depends(get_current_user)):
    sessions = await store.get_user_sessions(current_user.id)
    return [
        SessionOut(
            id=s["id"],
            user_id=s["user_id"],
            benchmark_id=s["benchmark_id"],
            benchmark_name=s["benchmark_name"],
            status=s["status"],
            created_at=s["created_at"],
            file_count=s.get("file_count", 0),
            risk_summary=s.get("risk_summary"),
        )
        for s in sessions
    ]


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(session_id: str, current_user: UserOut = Depends(get_current_user)):
    s = await store.get_session(session_id)
    if not s or s["user_id"] != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    files_raw = await store.get_session_files(session_id)
    files = [
        FileChange(
            path=f["file_path"],
            status="NEW" if f.get("is_new") else "MODIFIED",
            risk_level=f.get("risk_level", "SAFE"),
            reason=f.get("reason", ""),
            decision=f.get("decision", "pending"),
        )
        for f in files_raw
    ]

    timeline = [
        TimelineEvent(**evt) for evt in s.get("timeline", [])
    ]

    return SessionDetail(
        id=s["id"],
        user_id=s["user_id"],
        benchmark_id=s["benchmark_id"],
        benchmark_name=s["benchmark_name"],
        status=s["status"],
        created_at=s["created_at"],
        file_count=s.get("file_count", 0),
        risk_summary=s.get("risk_summary"),
        timeline=timeline,
        files=files,
    )


@router.get("/{session_id}/files")
async def list_files(session_id: str, current_user: UserOut = Depends(get_current_user)):
    s = await store.get_session(session_id)
    if not s or s["user_id"] != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    files_raw = await store.get_session_files(session_id)
    return [
        FileChange(
            path=f["file_path"],
            status="NEW" if f.get("is_new") else "MODIFIED",
            risk_level=f.get("risk_level", "SAFE"),
            reason=f.get("reason", ""),
            decision=f.get("decision", "pending"),
        )
        for f in files_raw
    ]


@router.get("/{session_id}/files/{file_path:path}", response_model=FileDiff)
async def get_file_diff(
    session_id: str, file_path: str, current_user: UserOut = Depends(get_current_user)
):
    s = await store.get_session(session_id)
    if not s or s["user_id"] != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    f = await store.get_file_diff(session_id, file_path)
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    return FileDiff(
        file_path=f["file_path"],
        before_content=f.get("before_content", ""),
        after_content=f.get("after_content", ""),
        unified_diff=f.get("unified_diff", ""),
        is_new=f.get("is_new", False),
        risk_level=f.get("risk_level", "SAFE"),
        reason=f.get("reason", ""),
        decision=f.get("decision", "pending"),
    )


@router.post("/{session_id}/files/{file_path:path}/accept")
async def accept_file(
    session_id: str, file_path: str, current_user: UserOut = Depends(get_current_user)
):
    s = await store.get_session(session_id)
    if not s or s["user_id"] != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    ok = await store.update_file_decision(session_id, file_path, "accepted")
    if not ok:
        raise HTTPException(status_code=404, detail="File not found")
    return {"status": "accepted", "file_path": file_path}


@router.post("/{session_id}/files/{file_path:path}/revert")
async def revert_file(
    session_id: str, file_path: str, current_user: UserOut = Depends(get_current_user)
):
    s = await store.get_session(session_id)
    if not s or s["user_id"] != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    ok = await store.update_file_decision(session_id, file_path, "reverted")
    if not ok:
        raise HTTPException(status_code=404, detail="File not found")
    return {"status": "reverted", "file_path": file_path}


@router.post("/{session_id}/commit")
async def commit_session(
    session_id: str, current_user: UserOut = Depends(get_current_user)
):
    s = await store.get_session(session_id)
    if not s or s["user_id"] != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    if s["status"] == "completed":
        raise HTTPException(status_code=400, detail="Session already committed")

    from pathlib import Path
    import shutil

    out_dir = Path("out/angular-app").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    files = await store.get_session_files(session_id)
    accepted_count = 0
    reverted_count = 0

    for f in files:
        file_path = out_dir / f["file_path"]
        if f.get("decision") == "accepted":
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(f["after_content"], encoding="utf-8")
            accepted_count += 1
        elif f.get("decision") == "reverted":
            if f.get("before_content") and not f.get("is_new"):
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(f["before_content"], encoding="utf-8")
            reverted_count += 1

    await store.update_session_status(session_id, "completed")
    await store.add_timeline_event(
        session_id,
        "decision",
        f"Session committed: {accepted_count} accepted, {reverted_count} reverted",
        {"accepted": accepted_count, "reverted": reverted_count},
    )

    return {
        "status": "committed",
        "accepted": accepted_count,
        "reverted": reverted_count,
    }
