from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./pokedex.db"


    SECRET_KEY: str = "contrasenaSecretaaa"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 horas

    class Config:
        env_file = ".env"

settings = Settings()