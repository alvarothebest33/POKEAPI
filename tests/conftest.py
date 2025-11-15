import pytest
from fastapi.testclient import TestClient
from sqlmodel import create_engine, SQLModel, Session
from sqlmodel.pool import StaticPool
from app.dependencies import limiter
from app.main import app
from app.database import get_session


@pytest.fixture(name="session")
def session_fixture():

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override

    # Deshabilita el rate limiting
    app.state.limiter.enabled = False

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()
    app.state.limiter.enabled = True


@pytest.fixture(name="test_user")
def test_user_fixture(client: TestClient):

    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser_pokemon",
            "email": "testpokemon@example.com",
            "password": "Testpassword123"
        }
    )
    assert response.status_code in [200, 400]

    return {
        "username": "testuser_pokemon",
        "password": "Testpassword123"
    }


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client: TestClient, test_user: dict):

    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )
    assert response.status_code == 200

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="rate_limited_client")
def rate_limited_client_fixture(session: Session):

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override

    try:
        limiter.reset("testclient")
    except Exception:
        pass

    # Activamos el limiter SOLO para este cliente
    app.state.limiter.enabled = True

    client = TestClient(app)
    yield client


    app.dependency_overrides.clear()
    # Y lo volvemos a deshabilitar para el resto de tests
    app.state.limiter.enabled = False
