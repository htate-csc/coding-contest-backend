import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from app.core.db import engine, init_db
from app.main import app
from app.models import Contest, User
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


def _assert_safe_test_database() -> None:
    if os.getenv("ALLOW_REMOTE_TEST_DB") == "1":
        return

    allowed_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "db"}
    if settings.POSTGRES_SERVER in allowed_hosts:
        return

    pytest.exit(
        "Refusing to run tests against a non-local database. "
        "Set POSTGRES_SERVER to a local test database, or set "
        "ALLOW_REMOTE_TEST_DB=1 only if you intentionally want this.",
        returncode=2,
    )


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    _assert_safe_test_database()
    with Session(engine) as session:
        init_db(session)
        yield session
        statement = delete(Contest)
        session.execute(statement)
        statement = delete(User)
        session.execute(statement)
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
