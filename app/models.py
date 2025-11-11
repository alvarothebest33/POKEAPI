from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from pydantic import validator
import re

class User(SQLModel, table=True):
    """Usuario del sistema"""
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, min_length=3, max_length=50)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

    # Relaciones
    pokedex_entries: List["PokedexEntry"] = Relationship(back_populates="owner")
    teams: List["Team"] = Relationship(back_populates="trainer")


class PokedexEntry(SQLModel, table=True):
    """Entrada en la Pokédex de un usuario"""
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id")

    # Datos del Pokémon (de PokeAPI)
    pokemon_id: int = Field(index=True)
    pokemon_name: str
    pokemon_sprite: str

    # Datos del usuario
    is_captured: bool = Field(default=False)
    capture_date: Optional[datetime] = None
    nickname: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=500)
    favorite: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relaciones
    owner: User = Relationship(back_populates="pokedex_entries")


class Team(SQLModel, table=True):
    # Equipo de batalla (máximo 6 Pokémon)
    id: Optional[int] = Field(default=None, primary_key=True)
    trainer_id: int = Field(foreign_key="user.id")
    name: str = Field(max_length=100)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relaciones
    trainer: User = Relationship(back_populates="teams")
    members: List["TeamMember"] = Relationship(back_populates="team")


class TeamMember(SQLModel, table=True):
    #Relación muchos a muchos entre Team y PokedexEntry
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id")
    pokedex_entry_id: int = Field(foreign_key="pokedexentry.id")
    position: int = Field(ge=1, le=6)

    # Relaciones
    team: Team = Relationship(back_populates="members")

# Esquemas usuario

class UserBase(SQLModel):
    username: str = Field(min_length=3, max_length=50)
    email: str

class UserCreate(UserBase):
    """(Schema Create)"""
    password: str = Field(min_length=8)

    @validator('password')
    def validate_password(cls, v):
        if isinstance(v, bytes):
            try:
                v = v.decode('utf-8')
            except Exception:
                # fallback seguro
                v = str(v)

        if len(v) > 72:
            raise ValueError("La contraseña no puede superar los 72 caracteres")

        if not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos un número')

        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')

        return v

class UserRead(UserBase):
    """(Schema Read)"""
    id: int
    created_at: datetime
    is_active: bool

class UserLogin(SQLModel):
    """(Schema) Para el formulario de login"""
    username: str
    password: str

class Token(SQLModel):
    """(Schema) Para devolver el token JWT"""
    access_token: str
    token_type: str = "bearer"

class TokenData(SQLModel):
    """(Schema) Para los datos dentro del token"""
    username: Optional[str] = None
    user_id: Optional[int] = None

# --- Schemas de Pokédex ---

class PokedexEntryRead(SQLModel):
    """(Schema Read) Para devolver una entrada de Pokédex"""
    # Definimos explícitamente los campos que queremos devolver
    id: int
    owner_id: int
    pokemon_id: int
    pokemon_name: str
    pokemon_sprite: str
    pokemon_types: Optional[str]
    is_captured: bool
    capture_date: Optional[datetime]
    nickname: Optional[str]
    notes: Optional[str]
    favorite: bool
    created_at: datetime

class PokedexEntryCreate(SQLModel):
    """(Schema Create) Para añadir un Pokémon [cite: 193-197]"""
    pokemon_id: int
    nickname: Optional[str] = Field(default=None, max_length=50)
    is_captured: bool = Field(default=False)

class PokedexEntryUpdate(SQLModel):
    """(Schema Update) Para actualizar una entrada [cite: 208-213]"""
    is_captured: Optional[bool] = None
    capture_date: Optional[datetime] = None
    nickname: Optional[str] = Field(default=None, max_length=50)
    favorite: Optional[bool] = None
    notes: Optional[str] = Field(default=None, max_length=500)

# --- Schemas de Team ---

class TeamBase(SQLModel):
    """(Schema Base)"""
    name: str = Field(max_length=100)
    description: Optional[str] = None

class TeamCreate(TeamBase):
    pokedex_entry_ids: List[int]

class TeamMemberRead(SQLModel):
    """(Schema Read) Para mostrar miembros de un equipo"""
    pokedex_entry_id: int
    position: int
    pokedex_entry: PokedexEntryRead  # Anidamos los datos del Pokémon

class TeamRead(TeamBase):
    """(Schema Read)"""
    id: int
    trainer_id: int
    created_at: datetime
    members: List[TeamMemberRead] = Field(default_factory=list)

class TeamUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    pokedex_entry_ids: Optional[List[int]] = None