import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models import PokedexEntry, Team, TeamMember, User
from pytest_mock import MockerFixture


@pytest.fixture(name="captured_pokemon_id")
def captured_pokemon_fixture(client: TestClient, auth_headers: dict) -> int:
    response = client.post(
        "/api/v1/pokedex/",
        json={
            "pokemon_id": 25,
            "nickname": "Pika-Test",
            "is_captured": True
        },
        headers=auth_headers
    )
    assert response.status_code in [200, 400]

    if response.status_code == 200:
        return response.json()["id"]
    else:
        get_resp = client.get("/api/v1/pokedex/?pokemon_id=25&captured=true", headers=auth_headers)
        return get_resp.json()[0]["id"]



@pytest.fixture(name="uncaptured_pokemon_id")
def uncaptured_pokemon_fixture(client: TestClient, auth_headers: dict) -> int:
    response = client.post(
        "/api/v1/pokedex/",
        json={
            "pokemon_id": 143,
            "nickname": "Dormilón",
            "is_captured": False
        },
        headers=auth_headers
    )
    assert response.status_code in [200, 400]

    if response.status_code == 200:
        return response.json()["id"]
    else:
        get_resp = client.get("/api/v1/pokedex/?pokemon_id=143&captured=false", headers=auth_headers)
        return get_resp.json()[0]["id"]


# Grupo 4
def test_create_team_success(
        client: TestClient,
        auth_headers: dict,
        captured_pokemon_id: int
):

    team_name = "Equipo de Prueba"
    response = client.post(
        "/api/v1/teams/",
        json={
            "name": team_name,
            "description": "Mi primer equipo",
            "pokedex_entry_ids": [captured_pokemon_id]
        },
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == team_name
    assert len(data["members"]) == 1
    assert data["members"][0]["pokedex_entry_id"] == captured_pokemon_id


def test_create_team_pokemon_not_captured(
        client: TestClient,
        auth_headers: dict,
        uncaptured_pokemon_id: int
):
    response = client.post(
        "/api/v1/teams/",
        json={
            "name": "Equipo Fantasma",
            "pokedex_entry_ids": [uncaptured_pokemon_id]
        },
        headers=auth_headers
    )

    assert response.status_code == 404
    assert "Uno o más Pokémon no se encontraron en tu Pokédex (debes capturarlo para poder añadirlo a tu equipo)." in response.json()["detail"]


def test_get_teams_list(client: TestClient, auth_headers: dict, session: Session):

    team = Team(name="Equipo para Listar", trainer_id=1)  # Asumimos ID 1
    session.add(team)
    session.commit()

    response = client.get("/api/v1/teams/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["name"] == "Equipo para Listar"


def test_update_team(client: TestClient, auth_headers: dict, session: Session):

    team = Team(name="Equipo para Actualizar", trainer_id=1)
    session.add(team)
    session.commit()
    session.refresh(team)
    team_id = team.id

    new_name = "Equipo Actualizado"
    response = client.put(
        f"/api/v1/teams/{team_id}",
        json={
            "name": new_name,
            "description": "Descripción actualizada"
        },
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name
    assert data["description"] == "Descripción actualizada"


def test_create_team_empty_ids(client: TestClient, auth_headers: dict):
    response = client.post(
        "/api/v1/teams/",
        json={"name": "Equipo Vacío", "pokedex_entry_ids": []},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert "Se requiere al menos un Pokémon" in response.json()["detail"]


def test_create_team_too_many_pokemon(client: TestClient, auth_headers: dict):
    response = client.post(
        "/api/v1/teams/",
        json={"name": "Equipo Grande", "pokedex_entry_ids": [1, 2, 3, 4, 5, 6, 7]},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert "más de 6 Pokémon" in response.json()["detail"]


def test_create_team_pokemon_not_owned(client: TestClient, auth_headers: dict, session: Session):

    otro_usuario = User(username="otro_user", email="otro@example.com", hashed_password="hash")
    session.add(otro_usuario)
    session.commit()
    session.refresh(otro_usuario)

    otro_entry = PokedexEntry(
        owner_id=otro_usuario.id, pokemon_id=150, pokemon_name="mewtwo",
        pokemon_sprite="", is_captured=True, hp=100, attack=100, defense=100, speed=100
    )
    session.add(otro_entry)
    session.commit()
    session.refresh(otro_entry)

    response = client.post(
        "/api/v1/teams/",
        json={"name": "Equipo Ladrón", "pokedex_entry_ids": [otro_entry.id]},
        headers=auth_headers
    )
    assert response.status_code == 404
    assert "no se encontraron en tu Pokédex" in response.json()["detail"]


def test_update_team_not_found(client: TestClient, auth_headers: dict):
    response = client.put(
        "/api/v1/teams/99999",
        json={"name": "No Existo"},
        headers=auth_headers
    )
    assert response.status_code == 404
    assert "Equipo no encontrado" in response.json()["detail"]


def test_update_team_not_owned(client: TestClient, auth_headers: dict, session: Session):

    otro_usuario = User(username="otro_user_2", email="otro2@example.com", hashed_password="hash")
    session.add(otro_usuario)
    session.commit()
    session.refresh(otro_usuario)
    otro_team = Team(name="Equipo Ajeno", trainer_id=otro_usuario.id)
    session.add(otro_team)
    session.commit()
    session.refresh(otro_team)

    response = client.put(
        f"/api/v1/teams/{otro_team.id}",
        json={"name": "HACKED"},
        headers=auth_headers
    )
    assert response.status_code == 403
    assert "No tienes permiso" in response.json()["detail"]


def test_update_team_too_many_pokemon(client: TestClient, auth_headers: dict, session: Session):
    team = Team(name="Equipo para Actualizar", trainer_id=1)
    session.add(team)
    session.commit()
    session.refresh(team)

    response = client.put(
        f"/api/v1/teams/{team.id}",
        json={"pokedex_entry_ids": [1, 2, 3, 4, 5, 6, 7]},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert "más de 6 Pokémon" in response.json()["detail"]


def test_update_team_invalid_members(client: TestClient, auth_headers: dict, session: Session):
    team = Team(name="Equipo para Actualizar 2", trainer_id=1)
    session.add(team)
    session.commit()
    session.refresh(team)

    response = client.put(
        f"/api/v1/teams/{team.id}",
        json={"pokedex_entry_ids": [99999]},
        headers=auth_headers
    )
    assert response.status_code == 404
    assert "no están 'capturados'" in response.json()["detail"]


# Test exportar PDF

def test_export_team_pdf_success(client: TestClient, auth_headers: dict, session: Session, captured_pokemon_id: int):

    team = Team(name="Equipo PDF", trainer_id=1)
    session.add(team)
    session.commit()
    session.refresh(team)
    member = TeamMember(team_id=team.id, pokedex_entry_id=captured_pokemon_id, position=1)
    session.add(member)
    session.commit()

    response = client.get(f"/api/v1/teams/{team.id}/export", headers=auth_headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "equipo_Equipo_PDF.pdf" in response.headers["content-disposition"]
    assert len(response.content) > 1000


def test_export_team_pdf_not_found(client: TestClient, auth_headers: dict):
    response = client.get("/api/v1/teams/99999/export", headers=auth_headers)
    assert response.status_code == 404
    assert "Equipo no encontrado" in response.json()["detail"]


def test_export_team_pdf_not_owned(client: TestClient, auth_headers: dict, session: Session):
    otro_usuario = User(username="otro_user_3", email="otro3@example.com", hashed_password="hash")
    session.add(otro_usuario)
    session.commit()
    session.refresh(otro_usuario)
    otro_team = Team(name="Equipo Ajeno PDF", trainer_id=otro_usuario.id)
    session.add(otro_team)
    session.commit()
    session.refresh(otro_team)

    response = client.get(f"/api/v1/teams/{otro_team.id}/export", headers=auth_headers)
    assert response.status_code == 403
    assert "No tienes permiso" in response.json()["detail"]


def test_export_pdf_handles_generic_exception(client: TestClient, auth_headers: dict, session: Session, captured_pokemon_id: int, mocker: MockerFixture):

    team = Team(name="Equipo PDF Error", trainer_id=1)
    session.add(team)
    session.commit()
    session.refresh(team)
    member = TeamMember(team_id=team.id, pokedex_entry_id=captured_pokemon_id, position=1)
    session.add(member)
    session.commit()


    mocker.patch("app.routers.teams._create_team_export_pdf", side_effect=Exception("Error de PDF simulado"))

    response = client.get(f"/api/v1/teams/{team.id}/export", headers=auth_headers)

    assert response.status_code == 500
    assert "Error al generar el PDF" in response.json()["detail"]

