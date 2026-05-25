from typing import List
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Numeric
from sqlmodel import Field, Relationship, SQLModel, JSON


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
        sa_column_kwargs={
            "onupdate": get_datetime_utc
        },
    )
    problem_links: list["ContestProblems"] = Relationship(
        back_populates="contest")


class ContestPublic(ContestBase):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
    problem_links: list["ContestProblemsPublic"] = []


class ContestsPublic(SQLModel):
    data: list[ContestPublic]
    count: int


class TestCaseSample(SQLModel):
    input: str
    output: str


class ProblemBase(SQLModel):
    name: str = Field(min_length=1, max_length=255)
    time_limit: float = Field(
        ...,
        sa_type=Numeric(precision=10, scale=3),
        gt=0,
        le=2000
    )
    memory_limit: int
    content: str = Field(min_length=1, max_length=1000)
    input_format: str = Field(min_length=1, max_length=1000)
    output_format: str = Field(min_length=1, max_length=1000)


class ProblemCreate(ProblemBase):
    samples: List[TestCaseSample] = Field(
        ...,
        sa_type=JSON,
        min_length=3,
        max_length=3
    )


class ProblemUpdate(ProblemBase):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    time_limit: float | None = Field(
        default=None,
        sa_type=Numeric(precision=10, scale=3),
        gt=0,
        le=2000
    )
    memory_limit: int | None = Field(default=None)
    content: str | None = Field(default=None, min_length=1, max_length=1000)
    input_format: str | None = Field(
        default=None, min_length=1, max_length=1000)
    output_format: str | None = Field(
        default=None, min_length=1, max_length=1000)
    samples: List[TestCaseSample] | None = Field(
        default=None,
        sa_type=JSON,
        min_length=3,
        max_length=3
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
        sa_column_kwargs={
            "onupdate": get_datetime_utc
        },
    )
    contest_links: list["ContestProblems"] = Relationship(
        back_populates="problem")
    samples: List[dict] = Field(sa_type=JSON)


class ProblemPublic(ProblemBase):
    id: uuid.UUID
    samples: List[TestCaseSample]
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProblemsPublic(SQLModel):
    data: list[ProblemPublic]
    count: int


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
