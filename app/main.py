from fastapi import FastAPI
import uvicorn
import logging
from app.routers import pokemon
from app.database import create_db_and_tables
from app import models

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
# ---------------------------------------------


@app.get("/")
def read_root():
    return {"Bienvenido a la pokeapi"}

app.include_router(pokemon.router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)