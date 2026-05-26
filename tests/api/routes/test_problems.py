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
