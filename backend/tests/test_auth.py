from tests.conftest import client
from app.core.security import create_access_token, create_refresh_token


def test_register_success():
    resp = client.post("/auth/register", json={
        "email": "new@test.com",
        "username": "newuser",
        "password": "SecurePass1",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@test.com"
    assert data["username"] == "newuser"
    assert "hashed_password" not in data


def test_register_duplicate_email(registered_user):
    resp = client.post("/auth/register", json={
        "email": "test@example.com",
        "username": "another",
        "password": "SecurePass1",
    })
    assert resp.status_code == 400
    assert "Email" in resp.json()["detail"]


def test_register_duplicate_username(registered_user):
    resp = client.post("/auth/register", json={
        "email": "another@test.com",
        "username": "testuser",
        "password": "SecurePass1",
    })
    assert resp.status_code == 400
    assert "Username" in resp.json()["detail"]


def test_login_success(registered_user):
    resp = client.post("/auth/login", json={
        "username": "testuser",
        "password": "Password123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(registered_user):
    resp = client.post("/auth/login", json={
        "username": "testuser",
        "password": "WrongPass",
    })
    assert resp.status_code == 401


def test_login_nonexistent_user():
    resp = client.post("/auth/login", json={
        "username": "nobody",
        "password": "whatever",
    })
    assert resp.status_code == 401


def test_refresh_token(registered_user):
    refresh = create_refresh_token({"sub": str(registered_user.id)})
    resp = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_with_access_token(registered_user):
    access = create_access_token({"sub": str(registered_user.id)})
    resp = client.post("/auth/refresh", json={"refresh_token": access})
    assert resp.status_code == 401


def test_get_me(auth_headers, registered_user):
    resp = client.get("/users/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == registered_user.id
    assert data["email"] == "test@example.com"


def test_get_me_no_token():
    resp = client.get("/users/me")
    assert resp.status_code == 401
