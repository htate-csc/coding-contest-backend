import uuid
from typing import Any
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Contest, ContestCreate, ContestPublic, ContestsPublic, ContestUpdate, Message
from app.utils import get_active_contest_filters

router = APIRouter(prefix="/contests", tags=["contests"])


@router.get("/", response_model=ContestsPublic)
def read_Contests(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve Contests.
    """

    if current_user.is_superuser:
        count_statement = select(func.count()).select_from(Contest)
        statement = (
            select(Contest).order_by(
                col(Contest.created_at).desc()).offset(skip).limit(limit)
        )
    else:
        active_filters = get_active_contest_filters()
        count_statement = (
            select(func.count())
            .select_from(Contest)
            .where(active_filters)
        )
        statement = (
            select(Contest)
            .where(active_filters)
            .order_by(col(Contest.created_at).desc())
            .offset(skip)
            .limit(limit)
        )

    count = session.exec(count_statement).one()
    db_contests = session.exec(statement).all()

    db_contests_public = [ContestPublic.model_validate(
        c) for c in db_contests]
    return ContestsPublic(data=db_contests_public, count=count)


@router.get("/{id}", response_model=ContestPublic)
def read_Contest(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get Contest by ID.
    """
    db_contest = session.get(Contest, id)
    now = datetime.now(timezone.utc)
    if not db_contest:
        raise HTTPException(status_code=404, detail="Contest not found")
    if not current_user.is_superuser and (db_contest.start_at <= now <= db_contest.end_at):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return db_contest


@router.post("/", response_model=ContestPublic)
def create_contest(
    *, session: SessionDep, current_user: CurrentUser, contest_in: ContestCreate
) -> Any:
    """
    Create new Contest.
    """
    db_contest = Contest.model_validate(
        contest_in)
    session.add(db_contest)
    session.commit()
    session.refresh(db_contest)
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return db_contest


@router.put("/{id}", response_model=ContestPublic)
def update_contest(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    contest_in: ContestUpdate,
) -> Any:
    """
    Update an Contest.
    """
    db_contest = session.get(Contest, id)
    if not db_contest:
        raise HTTPException(status_code=404, detail="Contest not found")
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    update_dict = contest_in.model_dump(exclude_unset=True)
    db_contest.sqlmodel_update(update_dict)
    session.add(db_contest)
    session.commit()
    session.refresh(db_contest)
    return db_contest


@router.delete("/{id}")
def delete_contest(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete an Contest.
    """
    db_contest = session.get(Contest, id)
    if not db_contest:
        raise HTTPException(status_code=404, detail="Contest not found")
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    session.delete(db_contest)
    session.commit()
    return Message(message="Contest deleted successfully")
