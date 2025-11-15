import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.models import PokedexEntry, User


@pytest.fixture(name="pokedex_entry")
def pokedex_entry_fixture(client: TestClient, auth_headers: dict, session: Session):

    existing = session.exec(
        select(PokedexEntry).where(
            PokedexEntry.pokemon_id == 1,
            PokedexEntry.owner_id == 1
        )
    ).first()

    if existing:
        return existing.id

    response = client.post(
        "/api/v1/pokedex/",
        json={
            "pokemon_id": 1,
            "nickname": "Bulby",
            "is_captured": True
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    return response.json()["id"]



def test_add_pokemon_to_pokedex_success(client: TestClient, auth_headers: dict, session: Session):

    response = client.post(
        "/api/v1/pokedex/",
        json={
            "pokemon_id": 25,  # Pikachu
            "nickname": "Sparky",
            "is_captured": True
        },
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["pokemon_name"] == "pikachu"
    assert data["nickname"] == "Sparky"

    # Verificamos que se guardó en la BBDD
    entry = session.get(PokedexEntry, data["id"])
    assert entry is not None
    assert entry.pokemon_name == "pikachu"


def test_add_duplicate_pokemon(client: TestClient, auth_headers: dict, pokedex_entry: int):

    response = client.post(
        "/api/v1/pokedex/",
        json={
            "pokemon_id": 1,
            "nickname": "Otro Bulby",
            "is_captured": False
        },
        headers=auth_headers
    )

    assert response.status_code == 400
    assert "ya está en tu Pokédex" in response.json()["detail"]


def test_add_pokemon_not_found_in_pokeapi(client: TestClient, auth_headers: dict):

    response = client.post(
        "/api/v1/pokedex/",
        json={"pokemon_id": 99999999},
        headers=auth_headers
    )

    assert response.status_code == 404
    assert "no existe en la PokeAPI" in response.json()["detail"]


def test_get_pokedex_list_success(client: TestClient, auth_headers: dict, pokedex_entry: int):

    response = client.get("/api/v1/pokedex/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["pokemon_name"] == "bulbasaur"


def test_get_pokedex_with_filters(client: TestClient, auth_headers: dict, pokedex_entry: int):

    response_false = client.get(
        "/api/v1/pokedex/?captured=false",
        headers=auth_headers
    )
    assert response_false.status_code == 200
    assert response_false.json() == []

    response_true = client.get(
        "/api/v1/pokedex/?captured=true",
        headers=auth_headers
    )
    assert response_true.status_code == 200
    assert len(response_true.json()) > 0
    assert response_true.json()[0]["pokemon_name"] == "bulbasaur"


def test_update_pokedex_entry(client: TestClient, auth_headers: dict, pokedex_entry: int):

    entry_id_to_update = pokedex_entry

    response = client.patch(
        f"/api/v1/pokedex/{entry_id_to_update}",
        json={
            "nickname": "Mi Bulbasaur Actualizado",
            "favorite": True
        },
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["nickname"] == "Mi Bulbasaur Actualizado"
    assert data["favorite"] is True


def test_delete_pokedex_entry(client: TestClient, auth_headers: dict, session: Session):

    entry_resp = client.post(
        "/api/v1/pokedex/",
        json={"pokemon_id": 25, "nickname": "Para Borrar"},
        headers=auth_headers
    )
    assert entry_resp.status_code == 200
    entry_id_to_delete = entry_resp.json()["id"]

    response = client.delete(
        f"/api/v1/pokedex/{entry_id_to_delete}",
        headers=auth_headers
    )


    assert response.status_code == 204

    db_entry = session.get(PokedexEntry, entry_id_to_delete)
    assert db_entry is None


def test_cannot_modify_other_user_pokedex(client: TestClient, session: Session, auth_headers: dict):

    otro_usuario = User(username="otro_usuario", email="otro@example.com", hashed_password="hash")
    session.add(otro_usuario)
    session.commit()
    session.refresh(otro_usuario)

    otro_entry = PokedexEntry(owner_id=otro_usuario.id, pokemon_id=150, pokemon_name="mewtwo", pokemon_sprite="")
    session.add(otro_entry)
    session.commit()
    session.refresh(otro_entry)


    response = client.patch(
        f"/api/v1/pokedex/{otro_entry.id}",
        json={"nickname": "HACKED"},
        headers=auth_headers
    )

    assert response.status_code == 403
    assert "No tienes permiso" in response.json()["detail"]


def test_get_pokedex_stats(
        client: TestClient,
        auth_headers: dict,
        pokedex_entry: int
):


    response = client.get("/api/v1/pokedex/stats", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total_pokemon"] >= 1
    assert data["captured"] >= 1
    assert data["completion_percentage"] > 0
    assert data["most_common_type"] in ["grass", "poison"]


def test_export_pokedex_pdf(
        client: TestClient,
        auth_headers: dict,
        pokedex_entry: int
):

    response = client.get("/api/v1/pokedex/export", headers=auth_headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in response.headers["content-disposition"]

    assert len(response.content) > 1000