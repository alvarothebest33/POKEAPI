from sqlmodel import create_engine, SQLModel, Session
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=True
)


def create_db_and_tables():
    # Creamos tablas y base de datos
    SQLModel.metadata.create_all(engine)


def get_session():
    # Crea y cierra sesion con cada petición
    with Session(engine) as session:
        yield session