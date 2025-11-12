from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlmodel import Session, select
from typing import Annotated, List, Optional
from datetime import datetime

#PDF
import io

from fastapi.responses import StreamingResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm


from app.auth import get_current_user
from app.database import get_session
from app.models import (
    User,
    PokedexEntry,
    PokedexEntryCreate,
    PokedexEntryRead,
    PokedexEntryUpdate
)
from app.services.pokeapi_service import PokeAPIService

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


router = APIRouter(
    prefix="/api/v1/pokedex",
    tags=["Tu Pokédex"],
    dependencies=[Depends(get_current_user)]
)

poke_service = PokeAPIService()

# Funcion que hace el PDF
def _create_pokedex_pdf(entries: List[PokedexEntry], user: User) -> io.BytesIO:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Coordenadas
    x = 2 * cm
    y = height - 3 * cm

    # Título
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x, y, f"Pokédex de {user.username}")
    y -= 1.5 * cm

    # Cabecera de la tabla
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, "ID")
    c.drawString(x + 2 * cm, y, "Nombre")
    c.drawString(x + 6 * cm, y, "Nickname")
    c.drawString(x + 10 * cm, y, "Capturado")
    c.drawString(x + 13 * cm, y, "Favorito")
    y -= 0.6 * cm
    c.line(x, y, width - x, y)
    y -= 0.2 * cm

    # Contenido de la tabla
    c.setFont("Helvetica", 9)
    for entry in entries:
        y -= 0.6 * cm
        if y < 3 * cm:  # Salto de página
            c.showPage()
            c.setFont("Helvetica", 9)
            y = height - 3 * cm

        c.drawString(x, y, str(entry.pokemon_id))
        c.drawString(x + 2 * cm, y, entry.pokemon_name)
        c.drawString(x + 6 * cm, y, entry.nickname or "-")
        c.drawString(x + 10 * cm, y, "Sí" if entry.is_captured else "No")
        c.drawString(x + 13 * cm, y, "★" if entry.favorite else "-")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


# Añadir pokemon
@router.post("/", response_model=PokedexEntryRead, summary="Añadir un pokemon a mi pokedex")
@limiter.limit("60/minute")
def add_pokemon_to_pokedex(
        request: Request,
        entry_create: PokedexEntryCreate,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)]
):

    # Ver que no es duplicado
    statement = select(PokedexEntry).where(
        PokedexEntry.owner_id == current_user.id,
        PokedexEntry.pokemon_id == entry_create.pokemon_id
    )
    existing_entry = session.exec(statement).first()

    if existing_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este Pokémon ya está en tu Pokédex."
        )

    # Ver que existe
    try:
        pokemon_data = poke_service.get_pokemon(entry_create.pokemon_id)
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El Pokémon no existe en la PokeAPI."
            )
        else:
            raise e

    # Crear base de datos
    db_entry = PokedexEntry(
        owner_id=current_user.id,
        pokemon_id=entry_create.pokemon_id,
        nickname=entry_create.nickname,
        is_captured=entry_create.is_captured,

        pokemon_name=pokemon_data.get("name"),
        pokemon_sprite=pokemon_data.get("sprite"),
        pokemon_types=",".join(pokemon_data.get("types", []))
    )

    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)

    return PokedexEntryRead.model_validate(db_entry)

# ENDPOINT de get pokedex
@router.get("/", response_model=List[PokedexEntryRead], summary="Ver lista de mi pokedex")
@limiter.limit("100/minute")
def get_user_pokedex(
        request: Request,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],

        # Filtro
        captured: Optional[bool] = Query(None, description="Filtrar por capturados"),
        favorite: Optional[bool] = Query(None, description="Filtrar por favoritos"),

        # Paginacion
        limit: int = Query(default=20, ge=1, le=100, description="Resultados por página"),
        offset: int = Query(default=0, ge=0, description="Offset de resultados"),

        # Ordenar
        sort: str = Query(default="pokemon_id", description="Ordenar por: pokemon_id, capture_date, pokemon_name"),
        order: str = Query(default="asc", description="Orden: 'asc' o 'desc'")
):

    statement = select(PokedexEntry).where(PokedexEntry.owner_id == current_user.id)
    if captured is not None:
        statement = statement.where(PokedexEntry.is_captured == captured)
    if favorite is not None:
        statement = statement.where(PokedexEntry.favorite == favorite)

    # Mapear y ordenar
    sort_column_map = {
        "pokemon_id": PokedexEntry.pokemon_id,
        "capture_date": PokedexEntry.capture_date,
        "pokemon_name": PokedexEntry.pokemon_name,
    }

    sort_column = sort_column_map.get(sort, PokedexEntry.pokemon_id)

    if order.lower() == "desc":
        statement = statement.order_by(sort_column.desc().nullslast())
    else:
        statement = statement.order_by(sort_column.asc().nullsfirst())

    statement = statement.offset(offset).limit(limit)
    pokedex_entries = session.exec(statement).all()

    return [PokedexEntryRead.model_validate(entry) for entry in pokedex_entries]


# ENDPOINT de patch
@router.patch("/{entry_id}", response_model=PokedexEntryRead, summary="Actualizar una entrada de mi Pokédex (añadir favoritos...)")
@limiter.limit("100/minute")
def update_pokedex_entry(
        request: Request,
        entry_id: int,
        entry_update: PokedexEntryUpdate,  # Schema de entrada [cite: 208-213]
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)]
):
    # Obtenemos de la base de datos
    db_entry = session.get(PokedexEntry, entry_id)

    # Verificar que existe y lo tiene
    if not db_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrada de Pokédex no encontrada."
        )

    if db_entry.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar esta entrada."
        )

    # Actualizamos
    update_data = entry_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_entry, key, value)

    if entry_update.is_captured and not db_entry.capture_date:
        db_entry.capture_date = datetime.utcnow()
    elif entry_update.is_captured is False:
        db_entry.capture_date = None

    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)

    return PokedexEntryRead.model_validate(db_entry)


# ENDPOINT de delete
@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar pokemon de mi pokedex")
@limiter.limit("100/minute")
def delete_pokedex_entry(
        request: Request,
        entry_id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)]
):

    db_entry = session.get(PokedexEntry, entry_id)

    # Verificar que existe y lo tiene
    if not db_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrada de Pokédex no encontrada."
        )

    if db_entry.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar esta entrada."
        )

    # Eliminamos entrada
    session.delete(db_entry)
    session.commit()

    return None

# ENDPOINT de la pokedex en PDF
@router.get("/export")
@limiter.limit("5/minute")
def export_user_pokedex_pdf(
        request: Request,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],

        captured: Optional[bool] = Query(None, description="Filtrar por capturados"),
        favorite: Optional[bool] = Query(None, description="Filtrar por favoritos")
):
    # Filtramos
    statement = select(PokedexEntry).where(PokedexEntry.owner_id == current_user.id)
    if captured is not None:
        statement = statement.where(PokedexEntry.is_captured == captured)
    if favorite is not None:
        statement = statement.where(PokedexEntry.favorite == favorite)

    entries = session.exec(statement.order_by(PokedexEntry.pokemon_id)).all()

    # Generamos el PDF
    buffer = _create_pokedex_pdf(entries, current_user)
    media_type = "application/pdf"
    filename = f"pokedex_{current_user.username}.pdf"

    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )