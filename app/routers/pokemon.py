from fastapi import APIRouter, Query, Path, HTTPException, status, Request
from typing import Dict, Any, List, Annotated
from app.services.pokeapi_service import PokeAPIService

from fastapi import Depends
from app.auth import get_current_user
from app.models import User

from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(
    prefix="/pokemon",
    tags=["Pokémon (PokeAPI)"]
)

poke_service = PokeAPIService()


# ENDPOINT de listar pokemon
@router.get("/search", response_model=Dict[str, Any])
@limiter.limit("30/minute")
def call_search_pokemon(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):

    try:
        results = poke_service.search_pokemon(limit=limit, offset=offset)
        return results
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e}"
        )

# ENDPOINT pokemon por nombre
@router.get("/{id_or_name}", response_model=Dict[str, Any])
@limiter.limit("60/minute")
def call_get_pokemon_details(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    id_or_name: str = Path(..., description="ID o nombre del Pokémon (ej: 132 o 'ditto')")
):
    try:
        pokemon_data = poke_service.get_pokemon(identifier=id_or_name)
        return pokemon_data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor en get_pokemon_details: {e}"
        )

#ENDPOINT pokemon por tipo
@router.get("/type/{type_name}", response_model=List[Dict[str, Any]])
@limiter.limit("60/minute")
def call_get_pokemon_by_type(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    type_name: str = Path(..., description="Nombre/numero del tipo (ej: 'fire', 'water', '2'. '4')")
):
    try:
        type_data = poke_service.get_pokemon_by_type(type_name=type_name)
        return type_data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {e}"
        )

# ENDPOINT especies
@router.get("/pokeon-species/{id_or_name}", response_model=Dict[str, Any])
@limiter.limit("60/minute")
def call_get_pokemon_species(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    id_or_name: str = Path(..., description="ID o nombre del Pokémon (ej: 132 o 'ditto')")
):
    try:
        species_data = poke_service.get_pokemon_species(identifier=id_or_name)
        return species_data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {e}"
        )