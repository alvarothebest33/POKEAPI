import requests
from requests.exceptions import RequestException, Timeout, HTTPError
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
import logging
from functools import lru_cache

# Logger
logger = logging.getLogger(__name__)


def _transform_pokemon_data(pokemon_data: Dict[str, Any]) -> Dict[str, Any]:
# Coge solo datos relevantes
    try:
        types = [t.get("type", {}).get("name") for t in pokemon_data.get("types", [])]
        stats = {
            stat.get("stat", {}).get("name"): stat.get("base_stat") for stat in pokemon_data.get("stats", [])
        }

        abilities = [a.get("ability", {}).get("name") for a in pokemon_data.get("abilities", [])]

        simplified_data = {
            "id": pokemon_data.get("id"),
            "name": pokemon_data.get("name"),
            "sprite": pokemon_data.get("sprites", {}).get("front_default"),
            "types": types,
            "stats": stats,
            "abilities": abilities
        }
        return simplified_data
    except Exception as e: # <--- Y el EXCEPT está aquí, cerrando el bloque
            logger.error(f"Error al transformar datos de Pokémon: {e}", exc_info=True)
            return pokemon_data

def _transform_type_data(type_data: Dict[str, Any]) -> List[Dict[str, Any]]:
#Coge solo la lista de pokemon
    try:
        pokemon_list = type_data.get("pokemon", [])
        return [p.get("pokemon") for p in pokemon_list if p.get("pokemon")]

    except Exception as e:
        logger.error(f"Error al transformar datos de tipo: {e}", exc_info=True)
        return []  # Devuelve lista vacía en caso de error


def _transform_species_data(species_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        description = "No se encontró descripción en español."
        # Buscamos la primera descripción en español ("es")
        for entry in species_data.get("flavor_text_entries", []):
            if entry.get("language", {}).get("name") == "es":
                # Limpiamos saltos de línea y caracteres extraños
                description = entry.get("flavor_text", "").replace("\n", " ").replace("\f", " ")
                break

        return {
            "id": species_data.get("id"),
            "name": species_data.get("name"),
            "is_legendary": species_data.get("is_legendary"),
            "is_mythical": species_data.get("is_mythical"),
            "description_es": description,
            "evolution_chain_url": species_data.get("evolution_chain", {}).get("url")
        }
    except Exception as e:
        logger.error(f"Error al transformar datos de especie: {e}", exc_info=True)
        return species_data  # Devuelve datos sin procesar si falla


class PokeAPIService:
    BASE_URL = "https://pokeapi.co/api/v2"

    def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        # Lo convierto en una funcion porque se repite en todos
        try:
            response = requests.get(url, params=params, timeout=10.0)
            if response.status_code == status.HTTP_404_NOT_FOUND:
                logger.warning(f"Not found in PokeAPI: {url}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Not found in PokeAPI: {url}"
                )
            response.raise_for_status()

            ''' Si todo va bien, devuelve el JSON '''
            return response.json()
        except HTTPException as e:
            raise e
        except Timeout:  # Error de timeout
            logger.error(f"Timeout al consultar PokeAPI: {url}")
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="La petición a la PokeAPI tardó demasiado."
            )
        except (RequestException, HTTPError) as e:  # Error de red o HTTP
            logger.error(f"Error de red/HTTP al consultar PokeAPI: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error de red al conectar con la PokeAPI: {e}"
            )
        except Exception as e:  # Otros
            logger.error(f"Error inesperado en PokeAPIService: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal Server Error al procesar tu petición: {e}"
            )

    @lru_cache(maxsize=128)
    def get_pokemon(self, identifier: str | int) -> Dict[str, Any]:
        # Buscar pokemon por nombre/ID
        url = f"{self.BASE_URL}/pokemon/{str(identifier)}"
        logger.info(f"Consumiendo PokeAPI: GET {url}")

        raw_data = self._make_request(url)
        transformed_data = _transform_pokemon_data(raw_data)
        return transformed_data


    @lru_cache(maxsize=32)
    def search_pokemon(self, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        #Listar pokemon
        url = f"{self.BASE_URL}/pokemon/"
        params = {"limit": limit, "offset": offset}
        logger.info(f"Consumiendo PokeAPI: GET {url} con params {params}")
        return self._make_request(url, params=params)

    @lru_cache(maxsize=32)
    def get_pokemon_by_type(self, type_name: str) -> List[Dict[str, Any]]:
        # Obtener pokemon por tipo
        url = f"{self.BASE_URL}/type/{type_name.lower()}"
        logger.info(f"Consumiendo PokeAPI (sync): GET {url}")
        raw_data = self._make_request(url)
        return _transform_type_data(raw_data)


    @lru_cache(maxsize=128)
    def get_pokemon_species(self, identifier: str | int) -> Dict[str, Any]:
        # Pokemon por especie
        url = f"{self.BASE_URL}/pokemon-species/{str(identifier)}"
        logger.info(f"Consumiendo PokeAPI: GET {url}")
        raw_data = self._make_request(url)
        return _transform_species_data(raw_data)