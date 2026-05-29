import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Numeric
from sqlmodel import JSON, Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class UserBase(SQLModel):
    login_id: str = Field(unique=True, index=True, max_length=255)
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    login_id: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class UserUpdate(UserBase):
    login_id: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    login_id: str | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )


class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


class ContestBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    start_at: datetime | None = Field(
        ...,
        sa_type=DateTime(timezone=True),
    )
    end_at: datetime | None = Field(
        ...,
        sa_type=DateTime(timezone=True),
    )


class ContestCreate(ContestBase):
    pass


class ContestUpdate(ContestBase):
    pass


class Contest(ContestBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    is_deleted: bool = Field(default=False, index=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"onupdate": get_datetime_utc},
    )
    problem_links: list["ContestProblems"] = Relationship(back_populates="contest")


class ContestPublic(ContestBase):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
    problem_links: list["ContestProblemsPublic"] = []


class ContestsPublic(SQLModel):
    data: list[ContestPublic]
    count: int


class ContestSummaryPublic(SQLModel):
    id: uuid.UUID
    title: str
    start_at: datetime
    end_at: datetime


class ContestSummariesPublic(SQLModel):
    data: list[ContestSummaryPublic]
    count: int
    server_now: datetime


class TestCaseSample(SQLModel):
    input: str
    output: str


class ProblemBase(SQLModel):
    name: str = Field(min_length=1, max_length=255, unique=True, index=True)
    time_limit: float = Field(
        ..., sa_type=Numeric(precision=10, scale=3), gt=0, le=2000
    )
    memory_limit: int
    content: str = Field(min_length=1, max_length=1000)
    input_format: str = Field(min_length=1, max_length=1000)
    output_format: str = Field(min_length=1, max_length=1000)


class ProblemCreate(ProblemBase):
    samples: list[TestCaseSample] = Field(..., sa_type=JSON, min_length=3, max_length=3)


class ProblemUpdate(ProblemBase):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    time_limit: float | None = Field(
        default=None, sa_type=Numeric(precision=10, scale=3), gt=0, le=2000
    )
    memory_limit: int | None = Field(default=None)
    content: str | None = Field(default=None, min_length=1, max_length=1000)
    input_format: str | None = Field(default=None, min_length=1, max_length=1000)
    output_format: str | None = Field(default=None, min_length=1, max_length=1000)
    samples: list[TestCaseSample] | None = Field(
        default=None, sa_type=JSON, min_length=3, max_length=3
    )


class Problem(ProblemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"onupdate": get_datetime_utc},
    )
    contest_links: list["ContestProblems"] = Relationship(back_populates="problem")
    samples: list[dict] = Field(sa_type=JSON)


class ProblemPublic(ProblemBase):
    id: uuid.UUID
    samples: list[TestCaseSample]
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProblemsPublic(SQLModel):
    data: list[ProblemPublic]
    count: int


class SubmissionCaseResultPublic(SQLModel):
    id: uuid.UUID
    case_index: int
    verdict: str
    time_ms: int | None = None
    memory_kb: int | None = None
    stdout_preview: str | None = None
    stderr_preview: str | None = None
    build_stderr_preview: str | None = None
    exit_code: int | None = None
    created_at: datetime | None = None


class SubmissionBase(SQLModel):
    language: str = Field(max_length=50)
    source_code: str = Field(min_length=1)


class SubmissionCreate(SubmissionBase):
    contest_id: uuid.UUID | None = None


class Submission(SubmissionBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID | None = Field(default=None, foreign_key="user.id", index=True)
    problem_id: uuid.UUID = Field(..., foreign_key="problem.id", index=True)
    contest_id: uuid.UUID | None = Field(
        default=None, foreign_key="contest.id", index=True
    )
    participant_type: str = Field(default="user", max_length=20, index=True)
    ai_model: str | None = Field(default=None, max_length=255)
    verdict: str = Field(default="RE", max_length=10, index=True)
    total_time_ms: int | None = None
    peak_memory_kb: int | None = None
    code_bytes: int | None = None
    physical_lines: int | None = None
    effective_lines: int | None = None
    max_nesting_depth: int | None = None
    analysis_error: str | None = None
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )


class SubmissionCaseResult(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    submission_id: uuid.UUID = Field(..., foreign_key="submission.id", index=True)
    case_index: int
    verdict: str = Field(max_length=10)
    time_ms: int | None = None
    memory_kb: int | None = None
    stdout_preview: str | None = None
    stderr_preview: str | None = None
    build_stderr_preview: str | None = None
    exit_code: int | None = None
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )


class SubmissionPublic(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    problem_id: uuid.UUID
    contest_id: uuid.UUID | None = None
    participant_type: str
    ai_model: str | None = None
    language: str
    source_code: str
    verdict: str
    total_time_ms: int | None = None
    peak_memory_kb: int | None = None
    code_bytes: int | None = None
    physical_lines: int | None = None
    effective_lines: int | None = None
    max_nesting_depth: int | None = None
    analysis_error: str | None = None
    created_at: datetime | None = None
    case_results: list[SubmissionCaseResultPublic] = []


class SubmissionsPublic(SQLModel):
    data: list[SubmissionPublic]
    count: int


class UnlockStatusPublic(SQLModel):
    problem_id: uuid.UUID
    ac_count: int
    unlocked: bool


class AIBattleCreate(SQLModel):
    contest_id: uuid.UUID | None = None
    user_submission_id: uuid.UUID
    models: list[str] = Field(min_length=1, max_length=3)


class AIBattleGeneratedCodeCreate(SQLModel):
    participant_id: uuid.UUID
    model_id: str = Field(max_length=255)
    source_code: str = Field(min_length=1)
    finish_reason: str | None = Field(default=None, max_length=255)
    usage: dict | None = Field(default=None, sa_type=JSON)


class AIBattle(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(..., foreign_key="user.id", index=True)
    problem_id: uuid.UUID = Field(..., foreign_key="problem.id", index=True)
    contest_id: uuid.UUID | None = Field(
        default=None, foreign_key="contest.id", index=True
    )
    user_submission_id: uuid.UUID = Field(..., foreign_key="submission.id")
    status: str = Field(default="pending", max_length=30, index=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"onupdate": get_datetime_utc},
    )


class AIBattleParticipant(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    battle_id: uuid.UUID = Field(..., foreign_key="aibattle.id", index=True)
    participant_type: str = Field(max_length=20)
    display_name: str = Field(max_length=255)
    model_id: str | None = Field(default=None, max_length=255)
    submission_id: uuid.UUID | None = Field(default=None, foreign_key="submission.id")
    generation_status: str | None = Field(default=None, max_length=30)
    generation_error: str | None = None
    order_num: int = Field(default=0)


class AIBattleParticipantPublic(SQLModel):
    id: uuid.UUID
    battle_id: uuid.UUID
    participant_type: str
    display_name: str
    model_id: str | None = None
    submission_id: uuid.UUID | None = None
    generation_status: str | None = None
    generation_error: str | None = None
    order_num: int


class AIBattlePublic(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    problem_id: uuid.UUID
    contest_id: uuid.UUID | None = None
    user_submission_id: uuid.UUID
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    participants: list[AIBattleParticipantPublic] = []


class ContestProblemsBase(SQLModel):
    problem_id: uuid.UUID = Field(..., foreign_key="problem.id")
    contest_id: uuid.UUID = Field(..., foreign_key="contest.id")
    order_num: int = Field(default=0)


class ContestProblemsCreate(ContestProblemsBase):
    pass


class ContestProblemsUpdate(ContestProblemsBase):
    pass


class ContestProblems(ContestProblemsBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    contest: "Contest" = Relationship(back_populates="problem_links")
    problem: "Problem" = Relationship(back_populates="contest_links")


class ProblemMinimal(SQLModel):
    id: uuid.UUID
    name: str
    time_limit: float
    memory_limit: int


class ContestProblemsPublic(ContestProblemsBase):
    id: uuid.UUID
    problem: ProblemMinimal | None = None


class ContestProblemsListPublic(SQLModel):
    data: list[ContestProblemsPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
