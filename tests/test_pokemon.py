from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

# Grupo 1
def test_get_pokemon_search_success(client: TestClient, auth_headers: dict):
    response = client.get(
        "/api/v1/pokemon/search?limit=1",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert data["results"][0]["name"] == "bulbasaur"


def test_get_pokemon_search_no_auth(client: TestClient):

    response = client.get("/api/v1/pokemon/search?limit=1")

    assert response.status_code == 401  # Unauthorized
    assert "Not authenticated" in response.json()["detail"]


def test_get_pokemon_details_success(client: TestClient, auth_headers: dict):
    response = client.get(
        "/api/v1/pokemon/pikachu",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "pikachu"
    assert data["id"] == 25
    assert "stats" in data
    assert "hp" in data["stats"]
    assert "generation" not in data


def test_get_pokemon_details_404(client: TestClient, auth_headers: dict):

    response = client.get(
        "/api/v1/pokemon/pokemon_que_no_existe",
        headers=auth_headers
    )

    assert response.status_code == 404
    assert "Not found" in response.json()["detail"]


def test_get_pokemon_by_type_success(client: TestClient, auth_headers: dict):

    response = client.get(
        "/api/v1/pokemon/type/fire",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(p["name"] == "charmander" for p in data)


def test_get_pokemon_species_success(client: TestClient, auth_headers: dict):

    response = client.get(
        "/api/v1/pokemon/pokeon-species/pikachu",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "pikachu"
    assert "description_es" in data


def test_get_pokemon_card_success(client: TestClient, auth_headers: dict):

    response = client.get(
        "/api/v1/pokemon/25/card",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "ficha_pikachu.pdf" in response.headers["content-disposition"]

    assert len(response.content) > 1000


def test_pokemon_endpoint_handles_generic_exception(client: TestClient, auth_headers: dict, mocker: MockerFixture):

    mocker.patch(
        "app.routers.pokemon.poke_service.get_pokemon",
        side_effect=Exception("¡Un error genérico simulado!")
    )

    response = client.get(
        "/api/v1/pokemon/pikachu",
        headers=auth_headers
    )

    assert response.status_code == 500
    assert "Error interno del servidor" in response.json()["detail"]
