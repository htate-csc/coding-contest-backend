import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.models import ContestProblems, ContestProblemsCreate, ContestProblemsPublic, ContestProblemsPublic, ContestProblemsUpdate, Message

router = APIRouter(prefix="/contest_problems", tags=["contest_problems"])


@router.post("/", response_model=ContestProblemsPublic)
def create_contest_problems(
    *, session: SessionDep, current_user: CurrentUser, ContestProblems_in: ContestProblemsCreate
) -> Any:
    """
    Create new ContestProblems.
    """
    db_contest_problems = ContestProblems.model_validate(
        ContestProblems_in)
    session.add(db_contest_problems)
    session.commit()
    session.refresh(db_contest_problems)
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return db_contest_problems


@router.put("/{id}", response_model=ContestProblemsPublic)
def update_contest_problems(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    ContestProblems_in: ContestProblemsUpdate,
) -> Any:
    """
    Update an ContestProblems.
    """
    db_contest_problems = session.get(db_contest_problems, id)
    if not db_contest_problems:
        raise HTTPException(
            status_code=404, detail="ContestProblems not found")
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    update_dict = ContestProblems_in.model_dump(exclude_unset=True)
    db_contest_problems.sqlmodel_update(update_dict)
    session.add(db_contest_problems)
    session.commit()
    session.refresh(db_contest_problems)
    return db_contest_problems


@router.delete("/{id}")
def delete_contest_problems(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete an ContestProblems.
    """
    contest_problems = session.get(ContestProblems, id)
    if not contest_problems:
        raise HTTPException(
            status_code=404, detail="ContestProblems not found")
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    session.delete(contest_problems)
    session.commit()
    return Message(message="ContestProblems deleted successfully")
