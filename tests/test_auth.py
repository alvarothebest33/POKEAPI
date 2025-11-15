from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models import User
import pytest



# Tests registro

def test_register_user_success(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "Testpassword123"
        }
    )

    # Comprueba el código de estado
    assert response.status_code == 200

    # Comprueba que los datos devueltos son correctos
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "hashed_password" not in data


def test_register_duplicate_username(client: TestClient, session: Session):
    existing_user = User(
        username="duplicate",
        email="email1@example.com",
        hashed_password="hash1"
    )
    session.add(existing_user)
    session.commit()

    # Registro mismo username
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "duplicate",
            "email": "email2@example.com",
            "password": "Testpassword123"
        }
    )

    # Comprueba el error 400
    assert response.status_code == 400
    assert "ya están registrados" in response.json()["detail"]


def test_register_invalid_password(client: TestClient):
    #Comprueba contraseña incorrecta
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "Testpassword"
        }
    )
    assert response.status_code == 422


# Test de login
@pytest.fixture(name="test_user")
def test_user_fixture(session: Session, client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "loginuser",
            "email": "login@example.com",
            "password": "Loginpass123"
        }
    )
    assert response.status_code == 200
    return response.json()


def test_login_success(client: TestClient, test_user: dict):
    # login ok
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user["username"],
            "password": "Loginpass123"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client: TestClient, test_user: dict):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user["username"],
            "password": "WRONGpassword123"
        }
    )

    assert response.status_code == 401
    assert "incorrectos" in response.json()["detail"]


def test_login_invalid_username(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "usuario_que_no_existe",
            "password": "password123"
        }
    )

    assert response.status_code == 401

    def test_rate_limit_exceeded(rate_limited_client: TestClient, test_user: dict):
        login_data = {
            "username": test_user["username"],
            "password": "WRONGpassword123"
        }

        # El límite del login es "10/minute"
        # Hacemos 10 llamadas que deberían funcionar (y dar 401)
        for _ in range(10):
            response = rate_limited_client.post(
                "/api/v1/auth/login",
                data=login_data
            )
            assert response.status_code == 401

            # --- La 11ª llamada ---
        response = rate_limited_client.post(
            "/api/v1/auth/login",
            data=login_data
        )

        # Esta llamada debe fallar con 429
        assert response.status_code == 429
        assert "Demasiadas peticiones" in response.text
