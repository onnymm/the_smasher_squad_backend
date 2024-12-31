import pandas as pd
from fastapi import APIRouter, Depends, status, Body
from app.security.auth import is_active_user, get_current_user
from app import Mobius, db_connection
from app.models.users import UserInDB
from typing import Literal

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

        # Diccionario de coordenadas mapeado
        mapped_data = (
            coords
            # Selección de columnas
            [['id', 'x', 'y', 'planet', 'color', 'starbase_level', 'under_attack_since', 'attacked_at', 'enemy_id', 'alliance_id']]
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
                                ['name', 'avatar', 'level']
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
