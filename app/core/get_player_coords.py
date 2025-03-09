import pandas as pd
import numpy as np
from app import (
    db_connection,
    mobius,
)

def _get_player_coords(player_name) -> pd.DataFrame:

    # Obtención de las coordenadas del jugador desde la base de datos
    search_results = db_connection.search_read('enemies', [('name', '~*', player_name)], output_format= 'dict')

    # Si no existen resultados, se termina la ejecución
    if not len(search_results):
        return pd.DataFrame()

    # Se destructura la información de la lista de resultados
    [ player_info ] = search_results

    # Obtención del DataFrame de datos relevantes de las coordenadas
    player_coords = db_connection.search_read('coords', ['&', '&', ('enemy_id', '=', player_info['id']), ('x', '!=', None), ('y', '!=', None)], fields= ['x', 'y', 'war', 'planet', 'color'], output_format='dataframe')

    # Retorno del DataFrame
    return player_coords


async def search_player_data(player_name: str):

    # Obtención de los datos del jugador desde la API de Galaxy Life
    player_data_from_api = await mobius.get_player_info(player_name)

    # Si no existe ningún resultado, se termina la ejecución
    if not player_data_from_api:
        return False
    
    # Conversión de datos a DataFrame
    player_data = (
        pd.DataFrame(
            player_data_from_api['Planets']
        )
        [['HQLevel']]
        .reset_index(names='planet')
        .assign(
            **{
                'name': player_data_from_api['Name']
            }
        )
        .rename(
            columns= {'HQLevel': 'starbase_level'}
        )
    )

    # Búsqueda de coordenadas en la base de datos
    player_data_from_db = _get_player_coords(player_name)

    # Si existen registros de coordenadas en la base de datos...
    if not player_data_from_db.empty:

        # Se agregan éstos a los datos base
        player_data = (
            player_data
            .merge(
                right= player_data_from_db,
                on= 'planet',
                how= 'left'
            )
            .replace({np.nan: -1})
            .astype(
                {
                    'id': 'int',
                    'x': 'int',
                    'y': 'int',
                }
            )
            .replace({-1: None})
        )

    # Si el jugador tiene alianza...
    if player_data_from_api['AllianceId']:
        # Obtención de los datos de la alianza del jugador
        alliance_data = await mobius._get_alliance_info(player_data_from_api['AllianceId'])
    # Si el jugador no tiene alianza...
    else:
        # Se crea la variable como diccionario vacío
        alliance_data = {}

    # Retorno de los datos
    return {
        'player': player_data_from_api,
        'coords': player_data.to_dict('records'),
        'alliance': alliance_data
    }
