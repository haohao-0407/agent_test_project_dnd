from __future__ import annotations

from fastapi.testclient import TestClient

from playscript_agent.api.app import create_app
from playscript_agent.api.services.game_state import game_state, reset_auth


def setup_function() -> None:
    game_state.reset()
    reset_auth()


def test_join_claims_existing_seats_and_exhausts_players() -> None:
    client = TestClient(create_app())

    first = client.post("/api/auth/join", json={"role": "player"})
    second = client.post("/api/auth/join", json={"role": "player"})
    third = client.post("/api/auth/join", json={"role": "player"})
    dm = client.post("/api/auth/join", json={"role": "dm"})

    assert first.status_code == 200
    assert first.json()["userId"] == "player-kael"
    assert second.status_code == 200
    assert second.json()["userId"] == "player-mira"
    assert third.status_code == 409
    assert dm.status_code == 200
    assert dm.json()["userId"] == "dm"


def test_protected_endpoint_requires_token() -> None:
    client = TestClient(create_app())

    response = client.get("/api/state")

    assert response.status_code == 401


def test_me_resolves_token_to_seat_principal() -> None:
    client = TestClient(create_app())
    joined = client.post("/api/auth/join", json={"role": "dm"}).json()

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {joined['token']}"},
    )

    assert response.status_code == 200
    assert response.json()["userId"] == "dm"
    assert response.json()["role"] == "dm"


def test_body_user_id_cannot_override_token_principal() -> None:
    client = TestClient(create_app())
    joined = client.post("/api/auth/join", json={"role": "player"}).json()

    response = client.patch(
        "/api/map",
        headers={"Authorization": f"Bearer {joined['token']}"},
        json={"userId": "dm", "updates": {"name": "Forged by body"}},
    )

    assert response.status_code == 403
    assert game_state.snapshot()["map"]["name"] != "Forged by body"


def test_logout_releases_claimed_seat() -> None:
    client = TestClient(create_app())
    joined = client.post("/api/auth/join", json={"role": "dm"}).json()

    logout = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {joined['token']}"},
    )
    rejoined = client.post("/api/auth/join", json={"role": "dm"})

    assert logout.status_code == 200
    assert rejoined.status_code == 200
    assert rejoined.json()["userId"] == "dm"
