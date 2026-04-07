"""
Tests for /api/users/* endpoints.
Covers: profile read/update, admin list/get/role-change/soft-delete.
"""

from tests.conftest import TestingSessionLocal
from tests.test_auth import _register_and_verify
from src.models.user import User, UserRole


# ── Helpers ──────────────────────────────────────────────────────────────────


def _login(client, email: str, password: str) -> str:
    """Return a Bearer access token for the given credentials."""
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _promote_to_admin(email: str) -> None:
    """Directly update a user's role to admin in the test DB."""
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == email).first()
    user.role = UserRole.admin
    db.commit()
    db.close()


def _make_admin_client(client, email="admin@test.com", password="adminpass123"):
    """Register, verify, promote, login — return admin Bearer token."""
    _register_and_verify(client, email=email, password=password, name="Admin User")
    _promote_to_admin(email)
    token = _login(client, email, password)
    return token


# ── GET /api/users/me ─────────────────────────────────────────────────────────


def test_get_own_profile(client):
    creds = _register_and_verify(client)
    token = _login(client, creds["email"], creds["password"])
    res = client.get("/api/users/me", headers=_auth_header(token))
    assert res.status_code == 200
    assert res.json()["email"] == creds["email"]
    assert "hashed_password" not in res.json()


def test_get_profile_unauthenticated(client):
    res = client.get("/api/users/me")
    assert res.status_code == 403  # HTTPBearer returns 403 when no credentials


# ── PATCH /api/users/me ───────────────────────────────────────────────────────


def test_update_own_profile(client):
    creds = _register_and_verify(client)
    token = _login(client, creds["email"], creds["password"])
    res = client.patch(
        "/api/users/me",
        json={"full_name": "Updated Name"},
        headers=_auth_header(token),
    )
    assert res.status_code == 200
    assert res.json()["full_name"] == "Updated Name"


def test_update_profile_empty_body_no_change(client):
    creds = _register_and_verify(client)
    token = _login(client, creds["email"], creds["password"])
    res = client.patch("/api/users/me", json={}, headers=_auth_header(token))
    assert res.status_code == 200


# ── GET /api/users (admin only) ───────────────────────────────────────────────


def test_admin_list_users(client):
    _register_and_verify(client, email="u1@test.com")
    _register_and_verify(client, email="u2@test.com", password="pass22223333")
    admin_token = _make_admin_client(client)

    res = client.get("/api/users", headers=_auth_header(admin_token))
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert len(res.json()) >= 2


def test_non_admin_cannot_list_users(client):
    creds = _register_and_verify(client)
    token = _login(client, creds["email"], creds["password"])
    res = client.get("/api/users", headers=_auth_header(token))
    assert res.status_code == 403


# ── GET /api/users/{id} (admin only) ─────────────────────────────────────────


def test_admin_get_user_by_id(client):
    _register_and_verify(client, email="target@test.com")
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "target@test.com").first()
    user_id = user.id
    db.close()

    admin_token = _make_admin_client(client)
    res = client.get(f"/api/users/{user_id}", headers=_auth_header(admin_token))
    assert res.status_code == 200
    assert res.json()["id"] == user_id


def test_admin_get_nonexistent_user(client):
    admin_token = _make_admin_client(client)
    res = client.get("/api/users/nonexistent-id", headers=_auth_header(admin_token))
    assert res.status_code == 404


# ── PATCH /api/users/{id}/role (admin only) ───────────────────────────────────


def test_admin_update_role(client):
    _register_and_verify(client, email="tobeadmin@test.com")
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "tobeadmin@test.com").first()
    user_id = user.id
    db.close()

    admin_token = _make_admin_client(client)
    res = client.patch(
        f"/api/users/{user_id}/role",
        json={"role": "admin"},
        headers=_auth_header(admin_token),
    )
    assert res.status_code == 200
    assert res.json()["role"] == "admin"


# ── DELETE /api/users/{id} (soft-delete, admin only) ──────────────────────────


def test_admin_soft_delete_user(client):
    _register_and_verify(client, email="todelete@test.com")
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "todelete@test.com").first()
    user_id = user.id
    db.close()

    admin_token = _make_admin_client(client)
    res = client.delete(f"/api/users/{user_id}", headers=_auth_header(admin_token))
    assert res.status_code == 204

    # Verify user is deactivated in DB
    db = TestingSessionLocal()
    deleted = db.query(User).filter(User.id == user_id).first()
    db.close()
    assert deleted.is_active is False


def test_non_admin_cannot_delete_user(client):
    _register_and_verify(client, email="victim@test.com")
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "victim@test.com").first()
    user_id = user.id
    db.close()

    creds = _register_and_verify(client, email="attacker@test.com", password="password123")
    token = _login(client, creds["email"], creds["password"])
    res = client.delete(f"/api/users/{user_id}", headers=_auth_header(token))
    assert res.status_code == 403
