from __future__ import annotations

from uuid import uuid4

from httpx import AsyncClient

from app.infrastructure.authentication.jwt import JwtTokenService
from app.infrastructure.configuration.settings import Settings


async def test_register_get_list_rename_deactivate_flow(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    register_response = await client.post(
        "/api/v1/users", json={"email": "ada@example.com", "display_name": "Ada Lovelace"}
    )
    assert register_response.status_code == 201
    user = register_response.json()
    assert user["email"] == "ada@example.com"
    assert user["display_name"] == "Ada Lovelace"
    assert user["status"] == "active"
    user_id = user["id"]

    get_response = await client.get(f"/api/v1/users/{user_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == user_id

    list_response = await client.get("/api/v1/users", params={"limit": 10})
    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] >= 1
    assert any(item["id"] == user_id for item in body["items"])

    rename_response = await client.patch(
        f"/api/v1/users/{user_id}",
        json={"display_name": "Ada, Countess of Lovelace"},
        headers=auth_headers,
    )
    assert rename_response.status_code == 200
    assert rename_response.json()["display_name"] == "Ada, Countess of Lovelace"

    deactivate_response = await client.request(
        "DELETE",
        f"/api/v1/users/{user_id}",
        json={"reason": "test cleanup"},
        headers=auth_headers,
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["status"] == "deactivated"


async def test_register_rejects_a_duplicate_email(client: AsyncClient) -> None:
    payload = {"email": "dup@example.com", "display_name": "First"}
    first = await client.post("/api/v1/users", json=payload)
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/users", json={"email": "dup@example.com", "display_name": "Second"}
    )

    assert second.status_code == 409
    problem = second.json()
    assert problem["status"] == 409
    assert "trace_id" in problem


async def test_register_rejects_invalid_email_with_problem_json(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/users", json={"email": "not-an-email", "display_name": "X"}
    )

    assert response.status_code == 422
    body = response.json()
    assert "body.email" in body["errors"]


async def test_get_unknown_user_returns_404_problem_detail(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    body = response.json()
    assert body["title"] == "Not Found"
    assert body["instance"] == "/api/v1/users/00000000-0000-0000-0000-000000000000"


async def test_rename_unknown_user_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.patch(
        "/api/v1/users/00000000-0000-0000-0000-000000000000",
        json={"display_name": "New"},
        headers=auth_headers,
    )

    assert response.status_code == 404


async def test_rename_without_authentication_is_rejected(client: AsyncClient) -> None:
    response = await client.patch(
        "/api/v1/users/00000000-0000-0000-0000-000000000000",
        json={"display_name": "New"},
    )

    assert response.status_code == 401


async def test_rename_without_the_required_permission_is_forbidden(
    client: AsyncClient, settings: Settings
) -> None:
    token = JwtTokenService(settings.auth).issue_access_token(user_id=uuid4())
    response = await client.patch(
        "/api/v1/users/00000000-0000-0000-0000-000000000000",
        json={"display_name": "New"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


async def test_correlation_id_is_echoed_back(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/users", headers={"X-Correlation-ID": "11111111-1111-1111-1111-111111111111"}
    )

    assert response.headers["X-Correlation-ID"] == "11111111-1111-1111-1111-111111111111"


async def test_health_endpoints(client: AsyncClient) -> None:
    live = await client.get("/health/live")
    assert live.status_code == 200

    ready = await client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ok"


async def test_openapi_schema_is_generated(client: AsyncClient) -> None:
    response = await client.get("/api/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/api/v1/users" in schema["paths"]
