from fastapi import FastAPI, Request
import uvicorn
import logging
from app.routers import pokemon, auth, pokedex, teams
from app.database import create_db_and_tables
from app import models

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
limiter = Limiter(key_func=get_remote_address)
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pokedex_api")

app = FastAPI(
    title="Pokeapi",
    description="Plataforma para buscar y manejar tus pokemon."
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    logger.info("Database iniciada con exito.")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"Bienvenido a la pokeapi"}

app.include_router(pokemon.router, prefix="/api/v1")
app.include_router(auth.router)
app.include_router(pokedex.router)
app.include_router(teams.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)