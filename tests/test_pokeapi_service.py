import pytest
from fastapi import HTTPException
from pytest_mock import MockerFixture
from app.services.pokeapi_service import PokeAPIService

# Datos Falsos (Mock Data)

MOCK_POKEMON_RAW = {
    "id": 25,
    "name": "pikachu",
    "height": 4,
    "weight": 60,
    "sprites": {
        "front_default": "http://example.com/sprite.png",
        "other": {"official-artwork": {"front_default": "..."}}
    },
    "types": [
        {"type": {"name": "electric"}}
    ],
    "stats": [
        {"base_stat": 35, "stat": {"name": "hp"}},
        {"base_stat": 55, "stat": {"name": "attack"}},
        {"base_stat": 40, "stat": {"name": "defense"}},
        {"base_stat": 90, "stat": {"name": "speed"}}
    ],
    "abilities": [
        {"ability": {"name": "static"}},
        {"ability": {"name": "lightning-rod"}}
    ],
    "generation": {"name": "generation-i"}
}



def test_pokeapi_service_get_pokemon_success_and_transform(mocker: MockerFixture):

    # Preparamos el mock
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_POKEMON_RAW

    mocker.patch("app.services.pokeapi_service.requests.get", return_value=mock_response)


    service = PokeAPIService()
    result = service.get_pokemon("pikachu")

    assert result is not None
    assert result["name"] == "pikachu"
    assert result["id"] == 25
    assert "sprite" in result
    assert "stats" in result
    assert result["stats"]["hp"] == 35
    assert "generation" not in result


def test_pokeapi_service_handles_404(mocker: MockerFixture):

    mock_response = mocker.Mock()
    mock_response.status_code = 404

    # Aplicamos el mock
    mocker.patch("app.services.pokeapi_service.requests.get", return_value=mock_response)

    service = PokeAPIService()

    with pytest.raises(HTTPException) as e:
        service.get_pokemon("pokemon_inexistente")

    assert e.value.status_code == 404
    assert "Not found in PokeAPI" in e.value.detail


def test_pokeapi_service_handles_timeout(mocker: MockerFixture):

    from requests.exceptions import Timeout
    mocker.patch("app.services.pokeapi_service.requests.get", side_effect=Timeout)

    service = PokeAPIService()
    with pytest.raises(HTTPException) as e:
        service.get_pokemon("pikachu")

    assert e.value.status_code == 408
    assert "tardó demasiado" in e.value.detail