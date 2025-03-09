from fastapi import (
    APIRouter,
    Query,
    status,
)
from app.core.get_player_coords import search_player_data

router = APIRouter(
    prefix= '/players',
    tags= ['Jugadores']
)

@router.get(
    '/search',
    status_code= status.HTTP_200_OK,
    name= 'Buscar jugador'
)
async def _search_player(name: str = Query()) -> dict | bool:
    """
    ## Búsqueda de jugador
    Este endpoint realiza la búsqueda de un jugador en la API de Galaxy Life
    con el nombre de usuario de éste y proporciona su información básica.

    ### Parámetros
    - `name` `string`: Nombre de usuario del jugador.
    """

    return await search_player_data(name)
