import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Contest,
    ContestProblems,
    Problem,
    Submission,
    SubmissionCaseResult,
    SubmissionCaseResultPublic,
    SubmissionCreate,
    SubmissionPublic,
    SubmissionsPublic,
    UnlockStatusPublic,
)
from app.services.code_analysis import analyze_code
from app.services.judge import JudgeCaseInput, judge_with_paiza

router = APIRouter(tags=["submissions"])


@router.post("/problems/{problem_id}/submissions", response_model=SubmissionPublic)
async def create_submission(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    problem_id: uuid.UUID,
    submission_in: SubmissionCreate,
) -> Any:
    problem = _get_accessible_problem(
        session=session,
        current_user=current_user,
        problem_id=problem_id,
        contest_id=submission_in.contest_id,
    )

    cases = [
        JudgeCaseInput(input=sample["input"], expected_output=sample["output"])
        for sample in problem.samples
    ]
    analysis = analyze_code(submission_in.language, submission_in.source_code)
    judge_result = await judge_with_paiza(
        source_code=submission_in.source_code,
        language=submission_in.language,
        cases=cases,
        time_limit_ms=round(float(problem.time_limit)),
        memory_limit_kb=problem.memory_limit * 1024 * 1024,
    )

    submission = Submission(
        user_id=current_user.id,
        problem_id=problem.id,
        contest_id=submission_in.contest_id,
        participant_type="user",
        language=submission_in.language,
        source_code=submission_in.source_code,
        verdict=judge_result.verdict,
        total_time_ms=judge_result.total_time_ms,
        peak_memory_kb=judge_result.peak_memory_kb,
        code_bytes=analysis.code_bytes,
        physical_lines=analysis.physical_lines,
        effective_lines=analysis.effective_lines,
        max_nesting_depth=analysis.max_nesting_depth,
        analysis_error=analysis.analysis_error,
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)

    case_results: list[SubmissionCaseResult] = []
    for index, case in enumerate(judge_result.cases):
        case_result = SubmissionCaseResult(
            submission_id=submission.id,
            case_index=index,
            verdict=case.verdict,
            time_ms=case.time_ms,
            memory_kb=case.memory_kb,
            stdout_preview=case.stdout_preview,
            stderr_preview=case.stderr_preview,
            build_stderr_preview=case.build_stderr_preview,
            exit_code=case.exit_code,
        )
        session.add(case_result)
        case_results.append(case_result)

    session.commit()
    for case_result in case_results:
        session.refresh(case_result)

    return _submission_public(submission, case_results)


@router.get("/problems/{problem_id}/submissions/me", response_model=SubmissionsPublic)
def read_my_problem_submissions(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    problem_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    _get_accessible_problem(
        session=session,
        current_user=current_user,
        problem_id=problem_id,
        contest_id=None,
    )

    query = (
        select(Submission)
        .where(
            Submission.problem_id == problem_id, Submission.user_id == current_user.id
        )
        .order_by(col(Submission.created_at).desc())
    )
    count = session.exec(select(func.count()).select_from(query.subquery())).one()
    submissions = session.exec(query.offset(skip).limit(limit)).all()

    return SubmissionsPublic(
        data=[
            _submission_public(
                submission,
                _case_results_for_submission(
                    session=session, submission_id=submission.id
                ),
            )
            for submission in submissions
        ],
        count=count,
    )


@router.get("/submissions/{submission_id}", response_model=SubmissionPublic)
def read_submission(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    submission_id: uuid.UUID,
) -> Any:
    submission = session.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if not current_user.is_superuser and submission.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return _submission_public(
        submission,
        _case_results_for_submission(session=session, submission_id=submission.id),
    )


@router.get("/problems/{problem_id}/unlock-status", response_model=UnlockStatusPublic)
def read_unlock_status(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    problem_id: uuid.UUID,
) -> Any:
    _get_accessible_problem(
        session=session,
        current_user=current_user,
        problem_id=problem_id,
        contest_id=None,
    )
    ac_count = _ac_count(
        session=session, user_id=current_user.id, problem_id=problem_id
    )
    return UnlockStatusPublic(
        problem_id=problem_id,
        ac_count=ac_count,
        unlocked=ac_count >= 1,
    )


def _get_accessible_problem(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    problem_id: uuid.UUID,
    contest_id: uuid.UUID | None,
) -> Problem:
    problem = session.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    if current_user.is_superuser:
        return problem

    now = datetime.now(timezone.utc)
    query = (
        select(ContestProblems)
        .join(Contest, ContestProblems.contest_id == Contest.id)
        .where(
            ContestProblems.problem_id == problem_id,
            Contest.is_deleted.is_(False),
            Contest.start_at <= now,
            Contest.end_at >= now,
        )
    )
    if contest_id is not None:
        query = query.where(ContestProblems.contest_id == contest_id)

    if not session.exec(query).first():
        raise HTTPException(
            status_code=403, detail="この問題へのアクセス権がありません"
        )
    return problem


def _ac_count(*, session: SessionDep, user_id: uuid.UUID, problem_id: uuid.UUID) -> int:
    statement = (
        select(func.count())
        .select_from(Submission)
        .where(
            Submission.user_id == user_id,
            Submission.problem_id == problem_id,
            Submission.verdict == "AC",
            Submission.participant_type == "user",
        )
    )
    return session.exec(statement).one()


def _case_results_for_submission(
    *, session: SessionDep, submission_id: uuid.UUID
) -> list[SubmissionCaseResult]:
    return session.exec(
        select(SubmissionCaseResult)
        .where(SubmissionCaseResult.submission_id == submission_id)
        .order_by(col(SubmissionCaseResult.case_index).asc())
    ).all()


def _submission_public(
    submission: Submission,
    case_results: list[SubmissionCaseResult],
) -> SubmissionPublic:
    return SubmissionPublic(
        id=submission.id,
        user_id=submission.user_id,
        problem_id=submission.problem_id,
        contest_id=submission.contest_id,
        participant_type=submission.participant_type,
        ai_model=submission.ai_model,
        language=submission.language,
        source_code=submission.source_code,
        verdict=submission.verdict,
        total_time_ms=submission.total_time_ms,
        peak_memory_kb=submission.peak_memory_kb,
        code_bytes=submission.code_bytes,
        physical_lines=submission.physical_lines,
        effective_lines=submission.effective_lines,
        max_nesting_depth=submission.max_nesting_depth,
        analysis_error=submission.analysis_error,
        created_at=submission.created_at,
        case_results=[
            SubmissionCaseResultPublic.model_validate(case_result)
            for case_result in case_results
        ],
    )
