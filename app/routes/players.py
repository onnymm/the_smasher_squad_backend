from typing import Literal
from fastapi import (
    APIRouter,
    status,
    Body,
    Depends,
    Query,
)
from app import db_connection, mobius
from app.core.get_player_coords import search_player_data
from app.models import UserInDB
from app.security.auth import get_current_user

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

@router.post(
    '/add_coords',
    status_code= status.HTTP_201_CREATED,
    name= 'Añadir nuevas coordenadas',
)
async def _add_coords(
    name: str = Body(),
    avatar: str = Body(),
    level: int = Body(),
    role: int = Body(),
    starbase_level: int = Body(),
    planet: int = Body(),
    x: int = Body(),
    y: int = Body(),
    sscolor: Literal['white', 'red', 'green', 'blue', 'blue', 'purple', 'yellow'] | None = Body(None),
    user: UserInDB = Depends(get_current_user)
):

    # Búsqueda del jugador
    player_record = db_connection.search_read('enemies', [('name', '~*', name)], output_format= 'dict')

    if player_record:
        # Obtención del registro del jugador
        [ player_data ] = player_record

        # Búsqueda del planeta
        planet_record = db_connection.search_read('coords', ['&', ('enemy_id', '=', player_data['id']), ('planet', '=', planet)], output_format= 'dict')

        # Si existe un registro de planeta
        if planet_record:

            # Obtención del registro del planeta
            [ planet_data ] = planet_record

            # Se actualiza el registro
            db_connection.update('coords', planet_data['id'], {'x': x, 'y': y, 'color': sscolor})

            # Se termina la ejecución
            return True

        else:

            # Si no existe planeta registrado, se toma la ID del jugador encontrada en la base de datos
            player_id = player_data['id']

    else:
        # Si no existe el jugador en la base de datos, se crea éste
        [ player_id ] = db_connection.create('enemies', {'name': name, 'avatar': avatar, 'level': level, 'role': mobius._alliance_roles[role]})

    # Se realiza la creación del planeta del jugador
    db_connection.create('coords', {'enemy_id': player_id, 'x': x, 'y': y, 'color': sscolor, 'planet': planet, 'starbase_level': starbase_level, 'war': False, 'create_uid': user.id, 'write_uid': user.id})

    return True
