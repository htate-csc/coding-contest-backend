import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    AIBattle,
    AIBattleCreate,
    AIBattleGeneratedCodeCreate,
    AIBattleParticipant,
    AIBattleParticipantPublic,
    AIBattlePublic,
    Contest,
    ContestProblems,
    Problem,
    Submission,
    SubmissionCaseResult,
)
from app.services.code_analysis import analyze_code
from app.services.judge import JudgeCaseInput, judge_with_paiza

router = APIRouter(tags=["ai_battles"])


@router.post("/problems/{problem_id}/ai-battles", response_model=AIBattlePublic)
def create_ai_battle(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    problem_id: uuid.UUID,
    battle_in: AIBattleCreate,
) -> Any:
    _get_accessible_problem(
        session=session,
        current_user=current_user,
        problem_id=problem_id,
        contest_id=battle_in.contest_id,
    )
    ac_count = _ac_count(
        session=session, user_id=current_user.id, problem_id=problem_id
    )
    if ac_count < 1:
        raise HTTPException(status_code=403, detail="AI battle is not unlocked")

    user_submission = session.get(Submission, battle_in.user_submission_id)
    if not user_submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if user_submission.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    if user_submission.problem_id != problem_id:
        raise HTTPException(status_code=400, detail="Submission problem mismatch")
    if user_submission.verdict != "AC":
        raise HTTPException(
            status_code=400, detail="Representative submission must be AC"
        )

    battle = AIBattle(
        user_id=current_user.id,
        problem_id=problem_id,
        contest_id=battle_in.contest_id,
        user_submission_id=user_submission.id,
        status="pending",
    )
    session.add(battle)
    session.commit()
    session.refresh(battle)

    participants = [
        AIBattleParticipant(
            battle_id=battle.id,
            participant_type="user",
            display_name="User",
            submission_id=user_submission.id,
            generation_status="completed",
            order_num=0,
        )
    ]
    participants.extend(
        AIBattleParticipant(
            battle_id=battle.id,
            participant_type="ai",
            display_name=model_id,
            model_id=model_id,
            generation_status="pending",
            order_num=index + 1,
        )
        for index, model_id in enumerate(battle_in.models)
    )

    for participant in participants:
        session.add(participant)
    session.commit()
    for participant in participants:
        session.refresh(participant)

    return _battle_public(battle, participants)


@router.get("/ai-battles/{battle_id}", response_model=AIBattlePublic)
def read_ai_battle(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    battle_id: uuid.UUID,
) -> Any:
    battle = _get_owned_battle(
        session=session, current_user=current_user, battle_id=battle_id
    )
    return _battle_public(
        battle,
        _participants_for_battle(session=session, battle_id=battle.id),
    )


@router.post(
    "/ai-battles/{battle_id}/generated-code",
    response_model=AIBattleParticipantPublic,
)
async def save_generated_code(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    battle_id: uuid.UUID,
    generated_in: AIBattleGeneratedCodeCreate,
) -> Any:
    battle = _get_owned_battle(
        session=session, current_user=current_user, battle_id=battle_id
    )
    participant = session.get(AIBattleParticipant, generated_in.participant_id)
    if not participant or participant.battle_id != battle.id:
        raise HTTPException(status_code=404, detail="AI battle participant not found")
    if participant.participant_type != "ai":
        raise HTTPException(
            status_code=400, detail="Generated code must target an AI participant"
        )

    problem = session.get(Problem, battle.problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    cases = [
        JudgeCaseInput(input=sample["input"], expected_output=sample["output"])
        for sample in problem.samples
    ]
    analysis = analyze_code("python3", generated_in.source_code)
    judge_result = await judge_with_paiza(
        source_code=generated_in.source_code,
        language="python3",
        cases=cases,
        time_limit_ms=round(float(problem.time_limit)),
        memory_limit_kb=problem.memory_limit * 1024 * 1024,
    )
    submission = Submission(
        user_id=current_user.id,
        problem_id=battle.problem_id,
        contest_id=battle.contest_id,
        participant_type="ai",
        ai_model=generated_in.model_id,
        language="python3",
        source_code=generated_in.source_code,
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

    for index, case in enumerate(judge_result.cases):
        session.add(
            SubmissionCaseResult(
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
        )

    participant.submission_id = submission.id
    participant.model_id = generated_in.model_id
    participant.generation_status = "completed"
    battle.status = "evaluated"
    session.add(participant)
    session.add(battle)
    session.commit()
    session.refresh(participant)

    return AIBattleParticipantPublic.model_validate(participant)


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


def _get_owned_battle(
    *, session: SessionDep, current_user: CurrentUser, battle_id: uuid.UUID
) -> AIBattle:
    battle = session.get(AIBattle, battle_id)
    if not battle:
        raise HTTPException(status_code=404, detail="AI battle not found")
    if not current_user.is_superuser and battle.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return battle


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


def _participants_for_battle(
    *, session: SessionDep, battle_id: uuid.UUID
) -> list[AIBattleParticipant]:
    return session.exec(
        select(AIBattleParticipant)
        .where(AIBattleParticipant.battle_id == battle_id)
        .order_by(col(AIBattleParticipant.order_num).asc())
    ).all()


def _battle_public(
    battle: AIBattle, participants: list[AIBattleParticipant]
) -> AIBattlePublic:
    return AIBattlePublic(
        id=battle.id,
        user_id=battle.user_id,
        problem_id=battle.problem_id,
        contest_id=battle.contest_id,
        user_submission_id=battle.user_submission_id,
        status=battle.status,
        created_at=battle.created_at,
        updated_at=battle.updated_at,
        participants=[
            AIBattleParticipantPublic.model_validate(participant)
            for participant in participants
        ],
    )
