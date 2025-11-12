from fastapi import APIRouter, Query, Path, HTTPException, status, Request
from typing import Dict, Any, List, Annotated
from app.services.pokeapi_service import PokeAPIService

from fastapi import Depends
from app.auth import get_current_user
from app.models import User
import logging

# Para el PDF de la carta
import io
import requests
from fastapi.responses import StreamingResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import black, white, lightgrey, grey
from reportlab.lib.utils import ImageReader
import textwrap


from slowapi import Limiter
from slowapi.util import get_remote_address
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(
    prefix="/pokemon",
    tags=["Pokémon (PokeAPI)"]
)

poke_service = PokeAPIService()

#Funcion para crear el PDF
def _create_pokemon_card_pdf(pokemon_data: dict, species_data: dict) -> io.BytesIO:

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    card_width = 8.8 * cm
    card_height = 14.0 * cm


    card_margin_x = (width - card_width) / 2
    card_margin_y = (height - card_height) / 2

    # Borde y Fondo
    c.setFillColor(lightgrey)
    c.roundRect(card_margin_x, card_margin_y, card_width, card_height, 0.5 * cm, fill=1)
    c.setStrokeColor(black)
    c.setLineWidth(2)
    c.roundRect(card_margin_x, card_margin_y, card_width, card_height, 0.5 * cm, fill=0)

    # Posiciones internas
    inner_x = card_margin_x + 0.7 * cm
    current_y = card_margin_y + card_height - 1.0 * cm

    # Nombre y HP
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(black)
    pokemon_name = pokemon_data.get('name', 'N/A').capitalize()
    c.drawString(inner_x, current_y, pokemon_name)

    hp = pokemon_data.get('stats', {}).get('hp', '??')
    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(card_margin_x + card_width - 0.7 * cm, current_y, f"HP {hp}")

    current_y -= 1.0 * cm

    # Imagen
    sprite_box_height = 5.0 * cm
    sprite_box_y = current_y - sprite_box_height
    c.setStrokeColor(grey)
    c.rect(card_margin_x + 0.5 * cm, sprite_box_y, card_width - 1 * cm, sprite_box_height, fill=0)

    sprite_url = pokemon_data.get("sprite")
    if sprite_url:
        try:
            response = requests.get(sprite_url)
            response.raise_for_status()
            sprite_image_data = io.BytesIO(response.content)
            image_for_pdf = ImageReader(sprite_image_data)

            img_x = card_margin_x + 0.5 * cm + (card_width - 1 * cm - 4 * cm) / 2
            img_y = sprite_box_y + (sprite_box_height - 4 * cm) / 2
            c.drawImage(image_for_pdf, img_x, img_y, width=4 * cm, height=4 * cm, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            c.setFont("Helvetica", 10)
            c.drawString(inner_x, sprite_box_y + sprite_box_height / 2, f"No sprite: {e}")

    current_y = sprite_box_y - 0.5 * cm

    # Estadísticas
    stats_box_height = 2.0 * cm
    stats_box_y = current_y - stats_box_height
    c.setStrokeColor(grey)
    c.rect(card_margin_x + 0.5 * cm, stats_box_y, card_width - 1 * cm, stats_box_height, fill=0)

    stats_y = current_y - 0.5 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(inner_x, stats_y, "Estadísticas:")
    stats_y -= 0.6 * cm

    c.setFont("Helvetica", 10)
    stats_data = pokemon_data.get("stats", {})
    stats_to_display = {'attack': 'Ataque', 'defense': 'Defensa', 'speed': 'Velocidad'}
    stat_line = [f"{label}: {stats_data.get(key, 'N/A')}" for key, label in stats_to_display.items()]
    c.drawString(inner_x, stats_y, "   ".join(stat_line))

    current_y = stats_box_y - 0.2 * cm

    # Tipos y habilidades
    types_abilities_box_height = 1.2 * cm
    types_abilities_box_y = current_y - types_abilities_box_height
    c.setStrokeColor(grey)
    c.rect(card_margin_x + 0.5 * cm, types_abilities_box_y, card_width - 1 * cm, types_abilities_box_height, fill=0)

    ta_y = current_y - 0.5 * cm
    c.setFont("Helvetica", 10)
    types = pokemon_data.get("types", [])
    c.drawString(inner_x, ta_y, f"Tipos: {', '.join(types).capitalize()}")

    abilities = pokemon_data.get("abilities", [])
    c.drawRightString(card_margin_x + card_width - 0.7 * cm, ta_y,
                      f"Habilidades: {abilities[0].capitalize() if abilities else 'N/A'}")

    current_y = types_abilities_box_y - 0.2 * cm


    desc_box_top_y = current_y
    desc_box_bottom_y = card_margin_y + 0.5 * cm
    desc_box_height = desc_box_top_y - desc_box_bottom_y
    c.setStrokeColor(grey)
    c.rect(card_margin_x + 0.5 * cm, desc_box_bottom_y, card_width - 1 * cm, desc_box_height, fill=0)

    # Descripción
    desc_title_y = desc_box_top_y - 0.5 * cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(inner_x, desc_title_y, "Descripción:")

    description = species_data.get("description_es", "No se encontró descripción.")
    c.setFont("Helvetica", 9)

    text_y = desc_title_y - (0.6 * cm)

    lines = textwrap.wrap(description, width=55)

    for line in lines:
        c.drawString(inner_x, text_y, line)
        text_y -= 0.4 * cm
        if text_y < (desc_box_bottom_y + 0.2 * cm):
            break

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer


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

# ENDPOINT de carta
@router.get("/{id_or_name}/card")
@limiter.limit("20/minute")
def get_pokemon_card(
        request: Request,
        id_or_name: str,
        current_user: Annotated[User, Depends(get_current_user)]
):

    try:
        # Obtenemos los datos
        pokemon_data = poke_service.get_pokemon(id_or_name)
        species_data = poke_service.get_pokemon_species(id_or_name)

        # Generamos el PDF
        pdf_buffer = _create_pokemon_card_pdf(pokemon_data, species_data)

        # Nombre del archivo
        filename = f"ficha_{pokemon_data.get('name', id_or_name)}.pdf"

        # Devolvemos el archivo
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error al generar el PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar el PDF: {e}"
        )