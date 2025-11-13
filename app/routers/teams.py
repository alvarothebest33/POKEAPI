from fastapi import APIRouter, Depends, HTTPException, status, Request, logger
from sqlmodel import Session, select
from typing import Annotated, List, Optional

#PDF
import io
import requests
from fastapi.responses import StreamingResponse
from PIL import Image # Para manejar las imágenes
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import black, white, lightgrey, grey
from reportlab.lib.utils import ImageReader

from app.auth import get_current_user
from app.database import get_session
from app.models import (
    User,
    Team,
    TeamCreate,
    TeamRead,
    TeamMember,
    PokedexEntry,
    PokedexEntryRead,
    TeamMemberRead,
    TeamUpdate
)

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


router = APIRouter(
    prefix="/api/v1/teams",
    tags=["Equipos de Batalla"],
    dependencies=[Depends(get_current_user)]
)


def _draw_pokemon_mini_card(c, x, y, width, height, entry: PokedexEntry):
    """Dibuja una mini-ficha de un Pokémon en el lienzo del PDF."""

    # Borde de la mini-ficha
    c.setStrokeColor(grey)
    c.setLineWidth(1)
    c.rect(x, y, width, height, fill=0)

    sprite = None
    if entry.pokemon_sprite:
        try:
            response = requests.get(entry.pokemon_sprite)
            response.raise_for_status()
            sprite_image_data = io.BytesIO(response.content)
            sprite = ImageReader(sprite_image_data)
            c.drawImage(sprite, x + (0.3 * cm), y + height - (3 * cm), width=2.5 * cm, height=2.5 * cm,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            pass  # No se pudo cargar el sprite

    # --- Contenido de la mini-ficha ---
    text_x = x + 3.2 * cm
    text_y = y + height - 0.7 * cm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(text_x, text_y, f"{entry.pokemon_name.capitalize()}")
    text_y -= 0.5 * cm
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(text_x, text_y, f"'{entry.nickname}'" if entry.nickname else "(Sin apodo)")
    text_y -= 0.6 * cm

    c.setFont("Helvetica", 9)
    c.drawString(text_x, text_y, f"Tipos: {entry.pokemon_types or 'N/A'}")
    text_y -= 0.5 * cm

    # Estadísticas
    c.drawString(text_x, text_y, f"HP: {entry.hp or 'N/A'} | Atk: {entry.attack or 'N/A'}")
    text_y -= 0.5 * cm
    c.drawString(text_x, text_y, f"Def: {entry.defense or 'N/A'} | Vel: {entry.speed or 'N/A'}")

    return sprite  # Devolvemos el sprite para la fila final


def _create_team_export_pdf(team: Team, entries: List[PokedexEntry], user: User) -> io.BytesIO:
    """Función helper para generar el PDF de exportación del equipo."""

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    x_margin = 2 * cm
    y_margin = 2 * cm
    current_y = height - y_margin

    # --- 1. Título y Descripción del Equipo ---
    c.setFont("Helvetica-Bold", 20)
    c.drawString(x_margin, current_y, f"Equipo: {team.name}")
    current_y -= 0.7 * cm
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(x_margin, current_y, f"Entrenador: {user.username}")
    current_y -= 0.7 * cm

    # --- ¡TU PETICIÓN: Añadir descripción del equipo! ---
    if team.description:
        c.setFont("Helvetica", 10)
        c.drawString(x_margin, current_y, f"Descripción: {team.description}")
        current_y -= 1.0 * cm
    # --------------------------------------------------

    # --- 2. Fichas de los 6 Pokémon ---
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x_margin, current_y, "Miembros del Equipo")
    current_y -= 0.5 * cm

    sprites_in_row = []  # Para la sección final

    card_height = 3.5 * cm
    card_width = (width - 2 * x_margin - 1 * cm) / 2
    x1 = x_margin
    x2 = x_margin + card_width + 1 * cm

    for i, entry in enumerate(entries):
        if i < 3:  # Columna 1
            card_x = x1
            card_y = current_y - ((i + 1) * card_height)
        else:  # Columna 2
            card_x = x2
            card_y = current_y - ((i - 3 + 1) * card_height)

        # Dibujamos la mini-ficha con la función helper
        sprite = _draw_pokemon_mini_card(c, card_x, card_y, card_width, card_height, entry)
        if sprite:
            sprites_in_row.append(sprite)

    current_y -= (3.5 * card_height)  # Mover Y debajo de las 3 filas de fichas

    # --- 3. Estadísticas Conjuntas ---
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x_margin, current_y, "Estadísticas Conjuntas")
    current_y -= 1 * cm

    # --- ¡TU PETICIÓN: Calcular stats totales! ---
    total_hp = sum(e.hp for e in entries if e.hp)
    total_attack = sum(e.attack for e in entries if e.attack)
    total_defense = sum(e.defense for e in entries if e.defense)
    total_speed = sum(e.speed for e in entries if e.speed)
    # ---------------------------------------------

    c.setFont("Helvetica", 12)
    c.drawString(x_margin, current_y, f"HP Total: {total_hp}")
    c.drawString(x_margin + 5 * cm, current_y, f"Ataque Total: {total_attack}")
    current_y -= 0.7 * cm
    c.drawString(x_margin, current_y, f"Defensa Total: {total_defense}")
    c.drawString(x_margin + 5 * cm, current_y, f"Velocidad Total: {total_speed}")
    current_y -= 1 * cm

    # --- 4. Fila de Sprites (Nuestra alternativa) ---
    c.setFont("Helvetica", 10)
    c.drawString(x_margin, current_y, "Alineación del Equipo:")
    current_y -= 2.2 * cm

    sprite_x = x_margin
    for sprite in sprites_in_row:
        c.drawImage(sprite, sprite_x, current_y, width=2 * cm, height=2 * cm, preserveAspectRatio=True, mask='auto')
        sprite_x += 2.2 * cm

    # --- Finalizar PDF ---
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer



# ENDPOINT de crear equipo
@router.post("/", response_model=TeamRead, summary="Crear equipo nuevo")
@limiter.limit("20/minute")
def create_team(
        request: Request,
        team_create: TeamCreate,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)]
):

    #Confirmar que tienes algun pokemon
    entry_ids = team_create.pokedex_entry_ids
    if not entry_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se requiere al menos un Pokémon para crear el equipo."
        )
    if len(entry_ids) > 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un equipo no puede tener más de 6 Pokémon."
        )

    # Validamos que los IDs existen y te pertenecen
    statement = select(PokedexEntry).where(
        PokedexEntry.owner_id == current_user.id,
        PokedexEntry.id.in_(entry_ids),
        PokedexEntry.is_captured == True
    )
    valid_entries = session.exec(statement).all()

    if len(valid_entries) != len(set(entry_ids)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uno o más Pokémon no se encontraron en tu Pokédex (debes capturarlo para poder añadirlo a tu equipo)."
        )

    # Crear equipo
    db_team = Team(
        name=team_create.name,
        description=team_create.description,
        trainer_id=current_user.id
    )
    session.add(db_team)
    session.commit()
    session.refresh(db_team)

    # Crear miembros del equipo
    team_members = []
    member_reads = []

    for i, entry in enumerate(valid_entries):
        db_member = TeamMember(
            team_id=db_team.id,
            pokedex_entry_id=entry.id,
            position=i + 1
        )
        team_members.append(db_member)

        member_reads.append(
            TeamMemberRead(
                pokedex_entry_id=entry.id,
                position=i + 1,
                pokedex_entry=PokedexEntryRead.model_validate(entry)
            )
        )

    session.add_all(team_members)
    session.commit()
    session.refresh(db_team)

    team_read = TeamRead(
        id=db_team.id,
        name=db_team.name,
        description=db_team.description,
        trainer_id=db_team.trainer_id,
        created_at=db_team.created_at,
        members=member_reads
    )

    return team_read

# ENDPOINT listar equipos
@router.get("/", response_model=List[TeamRead], summary="Lista los equipos de batalla de un usuario")
@limiter.limit("60/minute")
def get_user_teams(
        request: Request,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)]
):

    teams_query = select(Team).where(Team.trainer_id == current_user.id)
    teams = session.exec(teams_query).all()

    response_list = []
    for team in teams:
        member_reads = []
        for member in team.members:
            entry = session.get(PokedexEntry, member.pokedex_entry_id)
            if entry:
                member_reads.append(
                    TeamMemberRead(
                        pokedex_entry_id=entry.id,
                        position=member.position,
                        pokedex_entry=PokedexEntryRead.model_validate(entry)
                    )
                )

        team_read = TeamRead(
            id=team.id,
            name=team.name,
            description=team.description,
            trainer_id=team.trainer_id,
            created_at=team.created_at,
            members=sorted(member_reads, key=lambda m: m.position)
        )
        response_list.append(team_read)

    return response_list


# ENDPOINT de actualizar equipo
@router.put("/{team_id}", response_model=TeamRead, summary="Actualiza alguno de tus equipos")
@limiter.limit("60/minute")
def update_team(
        request: Request,
        team_id: int,
        team_update: TeamUpdate,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)]
):
    db_team = session.get(Team, team_id)

    # Ver que existe y te pertenece
    if not db_team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipo no encontrado."
        )
    if db_team.trainer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar este equipo."
        )

    update_data = team_update.model_dump(exclude_unset=True)

    if "name" in update_data:
        db_team.name = update_data["name"]
    if "description" in update_data:
        db_team.description = update_data["description"]

    # Actualizar miembros
    if "pokedex_entry_ids" in update_data:
        entry_ids = update_data["pokedex_entry_ids"]
        if len(entry_ids) > 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un equipo no puede tener más de 6 Pokémon."
            )

        # Validar la nueva lista
        statement = select(PokedexEntry).where(
            PokedexEntry.owner_id == current_user.id,
            PokedexEntry.id.in_(entry_ids),
            PokedexEntry.is_captured == True
        )
        valid_entries = session.exec(statement).all()

        if len(valid_entries) != len(set(entry_ids)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Uno o más Pokémon no se encontraron en tu Pokédex o no están 'capturados'."
            )

        # Borrar antiguos
        for member in db_team.members:
            session.delete(member)
        session.commit()

        # Crear nuevos
        new_members = []
        for i, entry in enumerate(valid_entries):
            db_member = TeamMember(
                team_id=db_team.id,
                pokedex_entry_id=entry.id,
                position=i + 1
            )
            new_members.append(db_member)

        session.add_all(new_members)

    session.add(db_team)
    session.commit()
    session.refresh(db_team)

    team_read_response = get_user_teams(request, current_user, session)
    updated_team_response = next(t for t in team_read_response if t.id == db_team.id)

    return updated_team_response

# Crear PDF de equipo
@router.get("/{team_id}/export", summary="Exportar equipo en PDF")
@limiter.limit("5R/minute")  # Límite más estricto
def export_team_pdf(
        request: Request,
        team_id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)]
):
    """
    Exporta un equipo en formato PDF con fichas y estadísticas.
    [cite_start][cite: 254-259]
    """
    db_team = session.get(Team, team_id)

    if not db_team:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipo no encontrado.")
    if db_team.trainer_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para exportar este equipo.")

    # Obtenemos todas las PokedexEntry de los miembros
    entry_ids = [member.pokedex_entry_id for member in db_team.members]

    # Nos aseguramos de que las entradas estén ordenadas por la posición en el equipo
    ordered_entries = []
    members_sorted = sorted(db_team.members, key=lambda m: m.position)
    for member in members_sorted:
        entry = session.get(PokedexEntry, member.pokedex_entry_id)
        if entry:
            ordered_entries.append(entry)

    try:
        buffer = _create_team_export_pdf(db_team, ordered_entries, current_user)
        filename = f"equipo_{db_team.name.replace(' ', '_')}.pdf"

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        logger.error(f"Error al generar el PDF del equipo: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar el PDF: {e}"
        )