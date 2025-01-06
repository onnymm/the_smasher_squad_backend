import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends, status, Body, Query
from app.security.auth import is_active_user, get_current_user
from app import Mobius, db_connection
from app.models.users import UserInDB
from typing import Literal
from datetime import datetime, timedelta
import pytz
from app.constants.constants import planet_wp

router = APIRouter()

@router.get(
    "/coords",
    status_code= status.HTTP_200_OK,
    name= "Coordenadas de la guerra actual"
)
async def _get_current_coords(active: bool = Depends(is_active_user)):
    """
    Obtención de las coordenadas de la guerra actual.
    """

    # Obtención de la alianza enemiga actual
    alliance_id = Mobius.current_opponent_alliance()

    # Si hay guerra
    if alliance_id:

        # Obtención de las coordenadas de la alianza enemiga
        coords = await Mobius.get_alliance_coords(alliance_id)

        # Retorno de las coordenadas en formato JSON
        data = coords.to_dict("records")
        count = len(coords)
        fields = [
            {
                'name': 'id',
                'ttype': 'integer',
            },
            {
                'name': 'x',
                'ttype': 'integer',
            },
            {
                'name': 'y',
                'ttype': 'integer',
            },
            {
                'name': 'war',
                'ttype': 'boolean',
            },
            {
                'name': 'planet',
                'ttype': 'integer',
            },
            {
                'name': 'color',
                'ttype': 'char',
            },
            {
                'name': 'starbase_level',
                'ttype': 'integer',
            },
            {
                'name': 'under_attack_since',
                'ttype': 'char',
            },
            {
                'name': 'attacked_at',
                'ttype': 'integer',
            },
            {
                'name': 'enemy_id',
                'ttype': 'integer',
            },
            {
                'name': 'name',
                'ttype': 'char',
            },
            {
                'name': 'avatar',
                'ttype': 'char',
            },
            {
                'name': 'level',
                'ttype': 'integer',
            },
            {
                'name': 'create_user',
                'ttype': 'char',
            },
            {
                'name': 'create_avatar',
                'ttype': 'char',
            },
            {
                'name': 'write_user',
                'ttype': 'write_avatar',
            },
            {
                'name': 'attack_user',
                'ttype': 'char',
            },
            {
                'name': 'attack_avatar',
                'ttype': 'char',
            },
        ]

        return {
            'data': data,
            'count': count,
            'fields': fields,
        }

    # Retorno de una lista vacía
    else:
        return {
            'data': [],
            'count': 0,
            'fields': [],
        }

@router.get(
    "/enemies",
    status_code= status.HTTP_200_OK,
    name= "Enemigos",
)
async def _get_enemies_coords(active: bool = Depends(is_active_user)):
    """
    Obtención de las coordenadas de la guerra actual para renderización en estilo Excel.
    """

    # Declaración de los nombres de la columna del pivot DataFrame
    planet_names = ['mp', '1th', '2th', '3th', '4th', '5th', '6th', '7th', '8th', '9th', '10th', '11th']

    # Obtención de la alianza enemiga actual
    alliance_id = Mobius.current_opponent_alliance()

    # Si hay guerra
    if alliance_id:

        # Obtención de las coordenadas de la alianza enemiga
        coords = await Mobius.get_alliance_coords(alliance_id)

        # Obtención de los usuarios
        users = (
            db_connection.search_read("users", fields= ['user', 'avatar'])
            .rename(
                columns= {
                    'id': 'attacked_by',
                    'user': 'attacker_user',
                    'avatar': 'attacker_avatar',
                }
            )
        )

        # Diccionario de coordenadas mapeado
        mapped_data = (
            coords
            # Selección de columnas
            [['id', 'x', 'y', 'planet', 'color', 'starbase_level', 'under_attack_since', 'attacked_at', 'attacked_by', 'enemy_id', 'alliance_id']]
            .pipe(
                lambda df: (
                    pd.merge(
                        left= df.astype({'attacked_by': 'Int64'}),
                        right= users,
                        left_on= 'attacked_by',
                        right_on= 'attacked_by',
                        how= 'left'
                    )
                    .replace({np.nan: None})
                )
            )
            .assign(
                # Creación de columna de horario de regeneración
                restores_at = lambda df: get_regeneration_time(df['attacked_at']),
                # Nulidad de información si ha pasado el tiempo establecido
                under_attack_since = lambda df: df['under_attack_since'].apply(expire_time(900)).replace({np.nan: None})
            )
            # Conversión de valores a cadenas de texto
            .pipe(stringify_datetime(['under_attack_since', 'restores_at']))
            # Creación de un índice en cadena de texto para evitar valores numpy.int64
            .assign(
                **{
                    'index': lambda df: df['id'].astype('string'),
                }
            )
            # Se establece la columna de índice
            .set_index('index')
            # Transposición de DataFrame
            .T
            # Se convierte a diccionario
            .to_dict()
        )

        # Creación del DataFrame
        data = (
            coords
            # Se reemplazan los valores numéricos de número de planeta por nombres ordinales
            .assign(
                planet_name= lambda df: df['planet'].apply(lambda sb: f"{sb}th" if sb else "mp")
            )
            # Se Agrega el diccionario de datos de planeta a cada una de las IDs
            .assign(
                data = lambda df: df['id'].apply(lambda value: mapped_data[str(value)])
            )
            # Selección de columnas
            [['enemy_id', 'name', 'avatar', 'level', 'planet_name', 'data']]
            # Creación de pivot DataFrame
            .pivot(
                index= 'enemy_id',
                columns= 'planet_name',
                values= 'data'
            )
            # Se reindexan las columnas en el orden específico, sólo para legibilidad
            .reindex(columns=planet_names)
            # Reemplazo de valores pd.NA a None para poder ser enviados por JSON
            .replace({pd.NA: None})
            .pipe(
                lambda df: (
                    # Unión con los datos de enemigos de alianza
                    pd.merge(
                        left= (
                            db_connection
                            .read(
                                'enemies',
                                (
                                    df
                                    .index
                                    .to_list()
                                ),
                                ['name', 'avatar', 'level', 'online']
                            )
                            .rename(
                                columns={
                                    'id': 'enemy_id'
                                }
                            )
                        ),
                        right= df.reset_index(),
                        left_on= 'enemy_id',
                        right_on= 'enemy_id',
                    )
                )
            )
            # Control de posibles np.NaN por si todos los jugadores no tienen últimas colonias
            .replace({np.nan: None})
            # Se converte a lista de diccionarios
            .to_dict('records')
        )

        # Conteo de registros
        count = len(coords)

        # Retorno de diccionario para renderización en tabla
        return {
            'data': data,
            'count': count,
            'fields': [],
        }

    # Retorno de un diccionario con valores nulos
    else:
        return {
            'data': [],
            'count': 0,
            'fields': [],
        }

@router.post(
    "/update_coords",
    status_code= status.HTTP_201_CREATED,
    name= "Agregar o editar coordenadas"
)
async def _add_new_coords(
    colony_id: int = Body(),
    x: int = Body(),
    y: int = Body(),
    sscolor: Literal['white', 'red', 'green', 'blue', 'blue', 'purple', 'yellow'] | None = Body(None),
    user: UserInDB = Depends(get_current_user)
):

    # Escritura en la base de datos
    return db_connection.update(
        'coords',
        [colony_id],
        {
            'x': x,
            'y': y,
            'color': sscolor,
            'write_uid': user.id,
        }
    )


@router.delete(
    "/delete_coords",
    status_code= status.HTTP_200_OK,
    name= "Eliminar las coordenadas de un planeta"
)
async def _delete_coords(
    planet_id: int = Query(),
    user: UserInDB = Depends(get_current_user)
):

    # Escritura en la base de datos
    return db_connection.update(
        'coords',
        [planet_id],
        {
            'x': None,
            'y': None,
            'color': None,
            'write_uid': user.id,
        }
    )


@router.post(
    "/take_planet",
    status_code= status.HTTP_200_OK,
    name= "Reclamar planeta para atacar",
)
async def _claim_planet_to_attack(
    planet_id: int = Body(),
    user: UserInDB = Depends(get_current_user),
):

    # Obtención del registro del planeta
    [ record ] = db_connection.read('coords', [planet_id], fields=['under_attack_since', 'attacked_by'], output_format='dict')


    # Si el planeta no está siendo atacado...
    if not record['under_attack_since'] or not expire_time()(record['under_attack_since']) or record['attacked_by'] == user.id:

        # Se reclama
        db_connection.update(
            'coords',
            [planet_id],
            {
                'under_attack_since': cdxm_now(),
                'attacked_by': user.id,
            }
        )

        # Confirmación de planeta reclamado
        return True

    # Confirmación de que alguien más llegó primero
    return False

@router.post(
    "/leave_planet",
    status_code= status.HTTP_200_OK,
    name= "Dejar de atacar planeta"
)
async def _leave_planet(
    planet_id: int = Body(),
    user: UserInDB = Depends(get_current_user)
):

    # Obtención del registro del planeta
    [ record ] = db_connection.read('coords', [planet_id], fields=['under_attack_since', 'attacked_by'], output_format='dict')

    # Si el planeta no está siendo atacado o el atacante es el mismo usuario
    if not record['under_attack_since'] or record['attacked_by'] == user.id:

        # Se abandona el planeta
        db_connection.update(
            'coords',
            [planet_id],
            {
                'under_attack_since': None,
            }
        )

    # Confirmación de cambios realizados
    return True


@router.post(
    "/mark_online",
    status_code= status.HTTP_200_OK,
    name= "Marcar un jugador como conectado",
)
async def _mark_online(
    enemy_id: int = Body(),
    user: UserInDB = Depends(get_current_user)
):

    # Obtención de las IDs de planetas del jugador
    planet_ids = (
        db_connection.search_read(
            'coords',
            [('enemy_id', '=', enemy_id)],
            ['id']
        )
        ['id']
        .to_list()
    )

    # Se establece estado online a activo
    db_connection.update('enemies', [enemy_id], {'online': True})

    # Se regeneran los planetas
    db_connection.update(
        'coords',
        planet_ids,
        {
            'attacked_by': user.id,
            'attacked_at': None,
        }
    )

    # Confirmación de cambios realizados
    return True


@router.post(
    "/mark_offline",
    status_code= status.HTTP_200_OK,
    name= "Marcar un jugador como desconectado",
)
async def _mark_offline(
    enemy_id: int = Body(),
    user: UserInDB = Depends(get_current_user)
):
    
    # Escritura en base de datos
    db_connection.update('enemies', [enemy_id], {'online': False})

    return True


@router.post(
    "/mark_attacked",
    status_code= status.HTTP_200_OK,
    name= "Marcar un plnaeta como atacado"
)
async def _mark_attacked(
    planet_id: int = Body(),
    user: UserInDB = Depends(get_current_user),
):

    # Se marca planeta como atacado
    db_connection.update(
        'coords',
        [planet_id],
        {
            'under_attack_since': None,
            'attacked_by': user.id,
            'attacked_at': cdxm_now(),
        }
    )

    # Confirmación de cambios realizado
    return True


@router.post(
        "/restore_planet",
        status_code= status.HTTP_200_OK,
        name= "Regeneración manual",
)
async def _restore_planet(
    planet_id: int = Body(),
    user: UserInDB = Depends(get_current_user)
):

    db_connection.update(
        'coords',
        [planet_id],
        {
            'attacked_by': user.id,
            'attacked_at': None,
        }
    )

    return True


@router.post(
    "/update_regeneration_hours",
    status_code= status.HTTP_200_OK,
    name= "Actualizar timepo de regeneración"
)
async def _update_regeneration_hours(
    time_in_hours: int = Body(),
    user: UserInDB = Depends(get_current_user),
) -> bool:

    # Escritura en base de datos
    db_connection.update('war', [1], {'regeneration_hours': time_in_hours})

    # Confirmación de cambios realizados
    return True


@router.get(
    "/get_enemy_alliance_stats",
    status_code= status.HTTP_200_OK,
    name= "Obtención del resumen de la alianza enemiga actual",
)
async def _get_enemy_alliance_stats(
    _: UserInDB = Depends(get_current_user),
):

    # Obtención de la alianza de guerra actual
    current_enemy_alliance_id = await Mobius.init_war()

    # Si no hay alianza se retorna False
    if not current_enemy_alliance_id:
        return False

    # Obtención del registro de la alianza guardada
    [ alliance_record ] = db_connection.read('alliances', [current_enemy_alliance_id], ['name'], output_format='dict')

    # Obtención nuevamente de la API para mostrar los datos en el frontend
    alliance_data_from_api = await Mobius._get(Mobius._base_url, "/alliances/get", {'name': alliance_record['name']})

    # Obtención de los miembros de la alianza enemiga en diccionario
    enemy_alliance_members = ( await Mobius.get_alliance_info(alliance_data_from_api['Name']) ).to_dict('records')

    # Obtención de cantidad de estrellas recolectables en PPs
    farmeable_stars = int(
        db_connection.search_read(
            'coords',
            ['&',
                ('planet', '=', 0),
                ('alliance_id', '=', current_enemy_alliance_id)], ['starbase_level']
        )
        .replace(
            {'starbase_level': planet_wp}
        )
        ['starbase_level']
        .sum()
    )

    # Retorno de los datos
    return {
        # Nombre de la alianza
        'enemy_alliance_name': alliance_data_from_api['Name'],
        # Descripción de la alianza
        'enemy_alliance_description': alliance_data_from_api['Description'],
        # Nivel de la alianza
        'enemy_alliance_level': alliance_data_from_api['AllianceLevel'],
        # Guerras ganadas
        'enemy_alliance_wars_won': alliance_data_from_api['WarsWon'],
        # Guerras perdidas
        'enemy_alliance_wars_lost': alliance_data_from_api['WarsLost'],
        # Estrellas recolectables
        'enemy_alliance_farmeable_wp': farmeable_stars,
        # Escudo de la alianza
        'enemy_alliance_logo': {
            'shape': alliance_data_from_api['Emblem']['Shape'],
            'pattern': alliance_data_from_api['Emblem']['Pattern'],
            'icon': alliance_data_from_api['Emblem']['Icon'],
        },
        # Miembros de la alianza
        'enemy_alliance_members': {
            'data': enemy_alliance_members,
            'count': len(enemy_alliance_members),
            'fields': [],
        }
    }


def cdxm_now():
    return datetime.now(pytz.timezone('Etc/GMT+6')).replace(tzinfo=None)

def expire_time(seconds: int = 900) -> datetime | None:
    
    def callback(time: datetime | None):
        if time:
            if (cdxm_now() - time).seconds < seconds:
                return time
        return None

    return callback


def get_regeneration_time(s: pd.Series) -> pd.Series:

    # Obtención de la información de la guerra actual
    [ war_info ] = db_connection.search_read('war', fields=['regeneration_hours'], output_format= 'dict')

    # Obtención de las horas de regeneración
    regeneration_hours = war_info['regeneration_hours']

    return s.apply(lambda time: (time + timedelta(hours= regeneration_hours)) if expire_time(regeneration_hours * 3600)(time) else None).replace({np.nan: None})

def stringify_datetime(columns: list[str]):

    # Función de transformación de valor a cadena de texto
    f = lambda time: str(time) if time else time

    # Función ejecutable por el pipe
    def callable(df: pd.DataFrame) -> pd.DataFrame:

        # Iteración por columnas
        for col in columns:
            # Aplicación de función de transformación
            df[col] = df[col].apply(f)

        # Retorno del DataFrame
        return df

    # Retorno de la función ejecutable
    return callable
