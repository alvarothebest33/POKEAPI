from fastapi import FastAPI
import uvicorn
from app.routers import pokemon

app = FastAPI(
    title="Pokeapi",
    description="Plataforma para buscar y manejar tus pokemon."
)

@app.get("/")
def read_root():
    return {"Bienvenido a la pokeapi"}

app.include_router(pokemon.router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)