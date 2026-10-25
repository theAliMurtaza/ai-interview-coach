from unittest.mock import Mock

from app.core.config import settings


async def test_public_provider_configuration_only_exposes_client_id(client, monkeypatch):
    monkeypatch.setattr(
        settings, "GOOGLE_OAUTH_CLIENT_ID", "test-client.apps.googleusercontent.com"
    )
    response = await client.get("/api/v1/auth/providers")
    assert response.status_code == 200
    assert response.json() == {"google_client_id": "test-client.apps.googleusercontent.com"}
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    assert (await client.get("/api/v1/auth/providers")).json() == {"google_client_id": None}


async def test_google_login_verifies_audience_and_returns_name(client, monkeypatch):
    client_id = "test-client.apps.googleusercontent.com"
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", client_id)
    verifier = Mock(
        return_value={
            "email": "google-profile@example.com",
            "email_verified": True,
            "sub": "google-profile-sub",
            "name": "Alex Candidate",
        }
    )
    monkeypatch.setattr("google.oauth2.id_token.verify_oauth2_token", verifier)
    response = await client.post("/api/v1/auth/google", json={"id_token": "google-test-token"})
    assert response.status_code == 200
    assert verifier.call_args.args[0] == "google-test-token"
    assert verifier.call_args.args[2] == client_id
    me = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {response.json()['access_token']}"}
    )
    assert me.json()["full_name"] == "Alex Candidate"
    verifier.side_effect = ValueError("wrong audience or expired token")
    denied = await client.post("/api/v1/auth/google", json={"id_token": "bad-token"})
    assert denied.status_code == 401
