import uuid
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.core.config import settings
from app.models import Problem


def test_create_problem(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # Ensure database is clean of this test name
    db_problem = db.exec(select(Problem).where(Problem.name == "Unique Test Problem")).first()
    if db_problem:
        db.delete(db_problem)
        db.commit()

    data = {
        "name": "Unique Test Problem",
        "time_limit": 2.0,
        "memory_limit": 256,
        "content": "Description for unique test problem.",
        "input_format": "Input description",
        "output_format": "Output description",
        "samples": [
            {"input": "1", "output": "2"},
            {"input": "2", "output": "3"},
            {"input": "3", "output": "4"}
        ]
    }
    response = client.post(
        f"{settings.API_V1_STR}/problems/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["name"] == data["name"]
    assert float(content["time_limit"]) == data["time_limit"]
    assert content["memory_limit"] == data["memory_limit"]
    assert "id" in content

    # Clean up
    created_id = content["id"]
    db_problem = db.get(Problem, uuid.UUID(created_id))
    if db_problem:
        db.delete(db_problem)
        db.commit()


def test_create_problem_duplicate(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # 1. Create first problem
    data1 = {
        "name": "Duplicate Test Problem",
        "time_limit": 1.0,
        "memory_limit": 256,
        "content": "Description 1",
        "input_format": "Input 1",
        "output_format": "Output 1",
        "samples": [
            {"input": "1", "output": "2"},
            {"input": "2", "output": "3"},
            {"input": "3", "output": "4"}
        ]
    }
    # Ensure duplicate problem name does not exist beforehand
    db_problem1 = db.exec(select(Problem).where(Problem.name == "Duplicate Test Problem")).first()
    if db_problem1:
        db.delete(db_problem1)
        db.commit()

    resp1 = client.post(
        f"{settings.API_V1_STR}/problems/",
        headers=superuser_token_headers,
        json=data1,
    )
    assert resp1.status_code == 200
    id1 = resp1.json()["id"]

    # 2. Attempt to create second problem with the same name
    resp2 = client.post(
        f"{settings.API_V1_STR}/problems/",
        headers=superuser_token_headers,
        json=data1,  # Same data, same name
    )
    assert resp2.status_code == 400
    assert resp2.json()["detail"] == "同じ名前の問題が既に存在します"

    # Clean up
    db_problem = db.get(Problem, uuid.UUID(id1))
    if db_problem:
        db.delete(db_problem)
        db.commit()


def test_update_problem_success(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # Create problem
    data = {
        "name": "Update Success Problem",
        "time_limit": 1.0,
        "memory_limit": 256,
        "content": "Description",
        "input_format": "Input",
        "output_format": "Output",
        "samples": [
            {"input": "1", "output": "2"},
            {"input": "2", "output": "3"},
            {"input": "3", "output": "4"}
        ]
    }
    db_problem = db.exec(select(Problem).where(Problem.name == "Update Success Problem")).first()
    if db_problem:
        db.delete(db_problem)
        db.commit()

    resp = client.post(
        f"{settings.API_V1_STR}/problems/",
        headers=superuser_token_headers,
        json=data,
    )
    assert resp.status_code == 200
    problem_id = resp.json()["id"]

    # Update description but keep the name (or set same name)
    update_data = {
        "name": "Update Success Problem",
        "time_limit": 1.5,
        "memory_limit": 512,
        "content": "Updated description",
        "input_format": "Input",
        "output_format": "Output",
        "samples": [
            {"input": "1", "output": "2"},
            {"input": "2", "output": "3"},
            {"input": "3", "output": "4"}
        ]
    }
    resp_update = client.put(
        f"{settings.API_V1_STR}/problems/{problem_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert resp_update.status_code == 200
    assert resp_update.json()["content"] == "Updated description"
    assert float(resp_update.json()["time_limit"]) == 1.5

    # Clean up
    db_problem = db.get(Problem, uuid.UUID(problem_id))
    if db_problem:
        db.delete(db_problem)
        db.commit()


def test_update_problem_duplicate(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # 1. Create two problems
    data1 = {
        "name": "Problem One",
        "time_limit": 1.0,
        "memory_limit": 256,
        "content": "Description",
        "input_format": "Input",
        "output_format": "Output",
        "samples": [
            {"input": "1", "output": "2"},
            {"input": "2", "output": "3"},
            {"input": "3", "output": "4"}
        ]
    }
    data2 = {
        "name": "Problem Two",
        "time_limit": 1.0,
        "memory_limit": 256,
        "content": "Description",
        "input_format": "Input",
        "output_format": "Output",
        "samples": [
            {"input": "1", "output": "2"},
            {"input": "2", "output": "3"},
            {"input": "3", "output": "4"}
        ]
    }

    # Clean beforehand
    for name in ["Problem One", "Problem Two"]:
        db_problem = db.exec(select(Problem).where(Problem.name == name)).first()
        if db_problem:
            db.delete(db_problem)
            db.commit()

    resp1 = client.post(
        f"{settings.API_V1_STR}/problems/",
        headers=superuser_token_headers,
        json=data1,
    )
    resp2 = client.post(
        f"{settings.API_V1_STR}/problems/",
        headers=superuser_token_headers,
        json=data2,
    )
    assert resp1.status_code == 200
    assert resp2.status_code == 200

    id1 = resp1.json()["id"]
    id2 = resp2.json()["id"]

    # 2. Try to update Problem Two's name to "Problem One" (duplicate)
    update_data = {
        "name": "Problem One",
        "time_limit": 1.0,
        "memory_limit": 256,
        "content": "Description",
        "input_format": "Input",
        "output_format": "Output",
        "samples": [
            {"input": "1", "output": "2"},
            {"input": "2", "output": "3"},
            {"input": "3", "output": "4"}
        ]
    }
    resp_update = client.put(
        f"{settings.API_V1_STR}/problems/{id2}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert resp_update.status_code == 400
    assert resp_update.json()["detail"] == "同じ名前の問題が既に存在します"

    # Clean up
    for problem_id in [id1, id2]:
        db_problem = db.get(Problem, uuid.UUID(problem_id))
        if db_problem:
            db.delete(db_problem)
            db.commit()


def test_read_problem_samples_limit(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
    db: Session,
) -> None:
    from datetime import datetime, timedelta, timezone
    from app.models import Contest, ContestProblems

    # 1. Create a problem with 3 samples
    problem_data = {
        "name": "Limit Test Problem",
        "time_limit": 1.0,
        "memory_limit": 256,
        "content": "Description",
        "input_format": "Input",
        "output_format": "Output",
        "samples": [
            {"input": "in1", "output": "out1"},
            {"input": "in2", "output": "out2"},
            {"input": "in3", "output": "out3"}
        ]
    }
    
    # Make sure it doesn't already exist
    existing = db.exec(select(Problem).where(Problem.name == "Limit Test Problem")).first()
    if existing:
        db.delete(existing)
        db.commit()

    resp = client.post(
        f"{settings.API_V1_STR}/problems/",
        headers=superuser_token_headers,
        json=problem_data,
    )
    assert resp.status_code == 200
    problem_id = resp.json()["id"]

    # 2. Verify superuser gets all 3 samples
    resp_super = client.get(
        f"{settings.API_V1_STR}/problems/{problem_id}",
        headers=superuser_token_headers,
    )
    assert resp_super.status_code == 200
    samples_super = resp_super.json()["samples"]
    assert len(samples_super) == 3
    assert samples_super[2]["input"] == "in3"

    # 3. Create an active contest
    now = datetime.now(timezone.utc)
    contest = Contest(
        title="Ongoing Contest",
        start_at=now - timedelta(hours=1),
        end_at=now + timedelta(hours=1),
    )
    db.add(contest)
    db.commit()
    db.refresh(contest)

    # 4. Link the problem to the contest
    link = ContestProblems(
        contest_id=contest.id,
        problem_id=uuid.UUID(problem_id),
    )
    db.add(link)
    db.commit()

    # 5. Verify normal user only gets the first 2 samples
    resp_normal = client.get(
        f"{settings.API_V1_STR}/problems/{problem_id}",
        headers=normal_user_token_headers,
    )
    assert resp_normal.status_code == 200
    samples_normal = resp_normal.json()["samples"]
    assert len(samples_normal) == 2
    assert samples_normal[0]["input"] == "in1"
    assert samples_normal[1]["input"] == "in2"

    # Clean up
    db.delete(link)
    db.delete(contest)
    db_problem = db.get(Problem, uuid.UUID(problem_id))
    if db_problem:
        db.delete(db_problem)
    db.commit()
