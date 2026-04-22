"""
Tests for /api/auth/* endpoints.
Covers: register, verify-email, resend-verification, login, refresh,
        logout, forgot-password, reset-password.
"""

from tests.conftest import TestingSessionLocal
from src.models.user import User


# wasaidizi 


def _get_user_from_db(email: str) -> User:
    """Fetch a user directly from the test DB."""
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == email).first()
    db.close()
    return user


def _register(client, email="user@test.com", password="password123", name="Test User"):
    """Register a user and return the response."""
    return client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": name},
    )


def _verify(client, token: str):
    """Verify an email using the token."""
    return client.get(f"/api/auth/verify-email?token={token}")


def _register_and_verify(client, email="user@test.com", password="password123", name="Test User"):
    """Register + verify email — returns credentials dict."""
    _register(client, email, password, name)
    user = _get_user_from_db(email)
    _verify(client, user.verification_token)
    return {"email": email, "password": password}


#Registration

def test_register_success(client):
    res = _register(client)
    assert res.status_code == 201
    assert "message" in res.json()


def test_register_duplicate_email(client):
    _register(client)
    res = _register(client)
    assert res.status_code == 409


def test_register_weak_password(client):
    res = client.post(
        "/api/auth/register",
        json={"email": "a@b.com", "password": "short", "full_name": "A B"},
    )
    assert res.status_code == 422


def test_register_invalid_email(client):
    res = client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "password123", "full_name": "A B"},
    )
    assert res.status_code == 422


#Email Verification


def test_verify_email_success(client):
    _register(client)
    user = _get_user_from_db("user@test.com")
    res = _verify(client, user.verification_token)
    assert res.status_code == 200

    activated = _get_user_from_db("user@test.com")
    assert activated.is_active is True
    assert activated.is_verified is True
    assert activated.verification_token is None


def test_verify_email_invalid_token(client):
    res = client.get("/api/auth/verify-email?token=bad-token")
    assert res.status_code == 400


def test_verify_email_already_used(client):
    _register(client)
    user = _get_user_from_db("user@test.com")
    token = user.verification_token
    _verify(client, token)
    # Token cleared after first use — second call should fail
    res = _verify(client, token)
    assert res.status_code == 400


#Login


def test_login_success(client):
    creds = _register_and_verify(client)
    res = client.post("/api/auth/login", json=creds)
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client):
    _register_and_verify(client)
    res = client.post(
        "/api/auth/login",
        json={"email": "user@test.com", "password": "wrongpassword"},
    )
    assert res.status_code == 401


def test_login_unverified_account(client):
    _register(client)
    res = client.post(
        "/api/auth/login",
        json={"email": "user@test.com", "password": "password123"},
    )
    assert res.status_code == 403


def test_login_nonexistent_user(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "nobody@test.com", "password": "password123"},
    )
    assert res.status_code == 401


#Token Refresh


def test_refresh_returns_new_tokens(client):
    creds = _register_and_verify(client)
    login_res = client.post("/api/auth/login", json=creds)
    refresh_token = login_res.json()["refresh_token"]

    res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body
    assert "refresh_token" in body
    # New refresh token must differ from old one
    assert body["refresh_token"] != refresh_token


def test_refresh_token_reuse_detection(client):
    creds = _register_and_verify(client)
    login_res = client.post("/api/auth/login", json=creds)
    refresh_token = login_res.json()["refresh_token"]

    # First use is fine
    client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    # Second use of same token should raise 401
    res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 401


#Logout


def test_logout_invalidates_refresh_token(client):
    creds = _register_and_verify(client)
    login_res = client.post("/api/auth/login", json=creds)
    refresh_token = login_res.json()["refresh_token"]

    client.post("/api/auth/logout", json={"refresh_token": refresh_token})

    # Refresh after logout should fail
    res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 401


#Forgot / Reset Password


def test_forgot_password_always_returns_success(client):
    # Even with a non-existent email, response is 200 (anti-enumeration)
    res = client.post(
        "/api/auth/forgot-password", json={"email": "ghost@test.com"}
    )
    assert res.status_code == 200


def test_forgot_password_sets_reset_token(client):
    _register_and_verify(client)
    client.post("/api/auth/forgot-password", json={"email": "user@test.com"})

    user = _get_user_from_db("user@test.com")
    assert user.reset_token is not None
    assert user.reset_token_expires is not None


def test_reset_password_success(client):
    _register_and_verify(client)
    client.post("/api/auth/forgot-password", json={"email": "user@test.com"})

    user = _get_user_from_db("user@test.com")
    reset_token = user.reset_token

    res = client.post(
        "/api/auth/reset-password",
        json={"token": reset_token, "new_password": "newpassword123"},
    )
    assert res.status_code == 200

    # Should now be able to login with new password
    login_res = client.post(
        "/api/auth/login",
        json={"email": "user@test.com", "password": "newpassword123"},
    )
    assert login_res.status_code == 200


def test_reset_password_invalid_token(client):
    res = client.post(
        "/api/auth/reset-password",
        json={"token": "bad-token", "new_password": "newpassword123"},
    )
    assert res.status_code == 400
