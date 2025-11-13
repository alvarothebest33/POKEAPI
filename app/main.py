from fastapi import FastAPI, Request, Response, status, APIRouter, Depends, HTTPException
import uvicorn
import logging
from app.routers import pokemon, auth, pokedex, teams
from app.database import create_db_and_tables
from app import models
from datetime import datetime
import time
from typing import Annotated
from app.auth import get_current_user
from app.models import User

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
limiter = Limiter(key_func=get_remote_address)
from fastapi.middleware.cors import CORSMiddleware
from app.services.pokeapi_service import PokeAPIService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pokedex_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("pokedex_api")
poke_service = PokeAPIService()


def rate_limit_exceeded_logger(request: Request, exc: RateLimitExceeded):
    # registra el evento
    logger.warning(
        f"Rate limit exceeded: "
        f"IP {request.client.host} on path {request.url.path}. "
        f"Limit: {exc.detail}"
    )

    # Devuelve error 429
    return Response(
        content=f"Demasiadas peticiones: {exc.detail}",
        status_code=status.HTTP_429_TOO_MANY_REQUESTS
    )

app = FastAPI(
    title="Pokeapi",
    description="Plataforma para buscar y manejar tus pokemon."
)


# Loging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Log de la petición entrante
    logger.info(f"Request: {request.method} {request.url.path}")

    # Pasa la petición al endpoint
    response = await call_next(request)

    # Calcula la duración
    duration = time.time() - start_time

    # Log de respuesta
    logger.info(
        f"Response: {response.status_code} | "
        f"Duration: {duration:.3f}s"
    )

    return response


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    logger.info("Database iniciada con exito.")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_logger)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://tu-dominio.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600
)


@app.get("/")
def read_root():
    return {"message": "Bienvenido a la pokeapi"}

app.include_router(pokemon.router, prefix="/api/v1")
app.include_router(auth.router)
app.include_router(pokedex.router)
app.include_router(teams.router)

v2_router = APIRouter(
    prefix="/api/v2",
    tags=["Versión 2 (Ejemplo añadir evoluciones)"]
)

@v2_router.get("/pokemon/{id_or_name}", response_model=dict)
def get_pokemon_v2_with_evolution(
        id_or_name: str,
        current_user: Annotated[User, Depends(get_current_user)]
):
    try:
        pokemon_data = poke_service.get_pokemon(id_or_name)
        species_data = poke_service.get_pokemon_species(id_or_name)
        evolution_url = species_data.get("evolution_chain_url")

        evolution_data = {"chain": []}
        if evolution_url:
            evolution_data = poke_service.get_evolution_chain(evolution_url)
        return {
            "pokemon": pokemon_data,
            "species": species_data,
            "evolution": evolution_data
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error en endpoint V2: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")


app.include_router(v2_router)
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)