import uuid
from typing import Any
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Contest, ContestCreate, ContestPublic, ContestsPublic, ContestUpdate, Message
from app.utils import get_active_contest_filters

router = APIRouter(prefix="/Contests", tags=["Contests"])


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
    contests = session.exec(statement).all()

    Contests_public = [ContestPublic.model_validate(
        Contest) for c in contests]
    return ContestsPublic(data=Contests_public, count=count)


@router.get("/{id}", response_model=ContestPublic)
def read_Contest(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get Contest by ID.
    """
    contest = session.get(Contest, id)
    now = datetime.now(timezone.utc)
    if not contest:
        raise HTTPException(status_code=404, detail="Contest not found")
    if not current_user.is_superuser and (contest.start_at <= now <= contest.end_at):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return contest


@router.post("/", response_model=ContestPublic)
def create_Contest(
    *, session: SessionDep, current_user: CurrentUser, Contest_in: ContestCreate
) -> Any:
    """
    Create new Contest.
    """
    Contest = Contest.model_validate(
        Contest_in)
    session.add(Contest)
    session.commit()
    session.refresh(Contest)
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return Contest


@router.put("/{id}", response_model=ContestPublic)
def update_Contest(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    Contest_in: ContestUpdate,
) -> Any:
    """
    Update an Contest.
    """
    Contest = session.get(Contest, id)
    if not Contest:
        raise HTTPException(status_code=404, detail="Contest not found")
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    update_dict = Contest_in.model_dump(exclude_unset=True)
    Contest.sqlmodel_update(update_dict)
    session.add(Contest)
    session.commit()
    session.refresh(Contest)
    return Contest


@router.delete("/{id}")
def delete_Contest(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete an Contest.
    """
    Contest = session.get(Contest, id)
    if not Contest:
        raise HTTPException(status_code=404, detail="Contest not found")
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    session.delete(Contest)
    session.commit()
    return Message(message="Contest deleted successfully")
