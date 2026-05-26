import uuid
from typing import Any
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Problem, ProblemCreate, ProblemPublic, ProblemsPublic, ProblemUpdate, Message

router = APIRouter(prefix="/problems", tags=["problems"])


@router.get("/", response_model=ProblemsPublic)
def read_problems(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve Problems.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="一般ユーザーは問題の一覧を取得できません")

    count_statement = select(func.count()).select_from(Problem)
    count = session.exec(count_statement).one()

    statement = (
        select(Problem).order_by(
            col(Problem.created_at).desc()).offset(skip).limit(limit)
    )

    db_problems = session.exec(statement).all()

    db_problems_public = [ProblemPublic.model_validate(p) for p in db_problems]
    return ProblemsPublic(data=db_problems_public, count=count)


@router.get("/{id}", response_model=ProblemPublic)
def read_problem(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get Problem by ID.
    """
    db_problem = session.get(Problem, id)
    if not db_problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    if current_user.is_superuser:
        return db_problem

    now = datetime.now(timezone.utc)

    is_accessible = any(
        link.contest.start_at <= now <= link.contest.end_at
        for link in db_problem.contest_links if link.contest
    )

    if not is_accessible:
        raise HTTPException(status_code=403, detail="この問題へのアクセス権がありません")
    return db_problem


@router.post("/", response_model=ProblemPublic)
def create_problem(
    *, session: SessionDep, current_user: CurrentUser, problem_in: ProblemCreate
) -> Any:
    """
    Create new Problem.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Check if a problem with the same name already exists
    statement = select(Problem).where(Problem.name == problem_in.name)
    existing_problem = session.exec(statement).first()
    if existing_problem:
        raise HTTPException(
            status_code=400,
            detail="同じ名前の問題が既に存在します"
        )

    db_problem = Problem.model_validate(
        problem_in.model_dump())
    session.add(db_problem)
    session.commit()
    session.refresh(db_problem)
    return db_problem


@router.put("/{id}", response_model=ProblemPublic)
def update_problem(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    problem_in: ProblemUpdate,
) -> Any:
    """
    Update an Problem.
    """
    db_problem = session.get(Problem, id)
    if not db_problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Check if the name is being updated and if the new name is already taken by another problem
    if problem_in.name is not None:
        statement = select(Problem).where(
            Problem.name == problem_in.name,
            Problem.id != id
        )
        existing_problem = session.exec(statement).first()
        if existing_problem:
            raise HTTPException(
                status_code=400,
                detail="同じ名前の問題が既に存在します"
            )

    update_dict = problem_in.model_dump(exclude_unset=True)
    db_problem.sqlmodel_update(update_dict)
    session.add(db_problem)
    session.commit()
    session.refresh(db_problem)
    return db_problem


@router.delete("/{id}")
def delete_problem(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete an Problem.
    """
    problem = session.get(Problem, id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    session.delete(problem)
    session.commit()
    return Message(message="Problem deleted successfully")
