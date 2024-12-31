import json
import aiohttp
import pandas as pd
import re
from typing import Callable
from app.database import db_connection

class Mobius():
    """
    Módulo de comunicación con la API de Galaxy Life
    """

    # Nombre de la alianza propia
    _own_alliance = 'the smasher squad'

    # URL base para conexión con el API de Galaxy Life
    _base_url = "https://api.galaxylifegame.net"

    # Roles de la alianza
    _alliance_roles = [
        'general',
        'captain',
        'private',
    ]


    @classmethod
    def current_opponent_alliance(cls) -> bool:

        # Obtención de la ID de la alianza enemiga (Si es que estamos en guerra)
        alliance_id = int(
            db_connection.search_read(
                "war",
                [('id', '=', 1)],
                fields=[
                    "alliance_id"
                ]
            )
            .at[0, "alliance_id"]
        )

        # Si hay una alianza enemiga
        if alliance_id != '':

            # Se retorna la ID de la alianza enemiga
            return alliance_id

        # Se retorna False para manejo del valor
        else:
            return False



    @classmethod
    async def init_war(cls) -> int | bool:

        # Obtención de los datos de nuestra alianza
        own_alliance_data = await cls._get(cls._base_url, "/alliances/get", {'name': cls._own_alliance})

        # Se obtiene la ID de la alianza enemiga actual
        current_opponent_alliance_from_api = own_alliance_data['OpponentAllianceId']


        # Si estamos en guerra
        if current_opponent_alliance_from_api != '':

            # Obtención de la ID de la alianza activa en la base de datos
            current_opponent_alliance_from_db = (
                db_connection.search_read(
                    "war",
                    [('id', '=', 1)],
                    fields=[
                        "alliance_id"
                    ]
                )
                .at[0, "alliance_id"]
            )

            # Obtención de la ID de la alianza enemiga:
            current_opponent_alliance_id = await cls._get_alliance_id(current_opponent_alliance_from_api)

            # Si la base de datos está desactualizada
            if current_opponent_alliance_from_db != current_opponent_alliance_from_api:


                # Actualización en la base de datos
                db_connection.update("war", [1], {"alliance_id": current_opponent_alliance_id})

                # Registro de la alianza en la base de datos
                await cls._register_alliance_in_db(current_opponent_alliance_from_api)

            # Retorno de la ID de la alianza actual
            return current_opponent_alliance_id

        else:

            # Se actualiza el estatus de guerra a inactivo
            db_connection.update("war", [1], {"alliance_id": None, 'regeneration_hours': 3})

            # Retorno de nulidad de alianza enemiga
            return False



    @classmethod
    async def get_alliance_coords(cls, alliance_id: int) -> pd.DataFrame:
        """
        Obtención de las coordenadas de una alianza registrada en la base de datos.
        """

        # Obtención de los planetas
        planets = db_connection.search_read(
            'coords',
            [('alliance_id', '=', alliance_id)],
            fields= [
                'x',
                'y',
                'war',
                'planet',
                'color',
                'starbase_level',
                'under_attack_since',
                'attacked_at',
                'attacked_by',
                'enemy_id',
                'alliance_id',
                'create_uid',
                'write_uid',
            ]
        )

        # Obtención de la información de los enemigos
        enemies = db_connection.search_read('enemies', [('id', 'in', planets['enemy_id'].to_list())], fields=['name', 'avatar', 'level'])

        # Obtención de los usuarios
        users = db_connection.search_read('users', fields=['user', 'avatar'])

        # Retorno de la información complementada
        return (
            # Unión de planetas con enemigos
            pd.merge(
                left= planets,
                right= enemies.rename(columns={'id': 'enemy_id'}),
                left_on= 'enemy_id',
                right_on= 'enemy_id',
                how= 'left'
            )
            # Unión con usuario creador
            .pipe(
                lambda df: (
                    pd.merge(
                        left= df,
                        right= users.rename(columns={'id': 'create_uid', 'user': 'create_user', 'avatar': 'create_avatar'}),
                        left_on= 'create_uid',
                        right_on= 'create_uid',
                        how= 'left',
                    )
                )
            )
            # Unión con usuario modificador
            .pipe(
                lambda df: (
                    pd.merge(
                        left= df,
                        right= users.rename(columns={'id': 'write_uid', 'user': 'write_user', 'avatar': 'write_avatar'}),
                        left_on= 'write_uid',
                        right_on= 'write_uid',
                        how= 'left',
                    )
                )
            )
            # Unión con usuario atacante
            .pipe(
                lambda df: (
                    pd.merge(
                        left= df.astype({'attacked_by': 'Int64'}),
                        right= users.rename(columns={'id': 'attacked_by', 'user': 'attack_user', 'avatar': 'attack_avatar'}),
                        left_on= 'attacked_by',
                        right_on= 'attacked_by',
                        how= 'left',
                    )
                    .astype(
                        {
                            'attack_user': 'string',
                            'attack_avatar': 'string',
                        }
                    )
                    .replace(
                        {
                            pd.NA: None
                        }
                    )
                )
            )
        )



    @classmethod
    async def _register_alliance_in_db(cls, alliance_name: str) -> int:
        """
        Registro o tentativa de registro de una alianza y sus miembros en la base de datos.
        """

        # Obtención de la ID de la alianza
        alliance_id = await cls._get_alliance_id(alliance_name)

        # Conteo de registros
        count = db_connection.search_count('enemies', [('alliance_id', '=', alliance_id)])

        # Si no hay registros
        if not count:

            # Obtención de los datos de la alianza
            alliance_data = await Mobius.get_alliance_info(alliance_name)

            # Creación de los datos a registrar en la base de datos
            records = (
                alliance_data
                .rename(
                    columns= {
                        'alliance_role': 'role'
                    }
                )
                [[
                    'id',
                    'name',
                    'avatar',
                    'level',
                    'role',
                ]]
                .assign(
                    **{
                        'role': lambda df: df['role'].apply(lambda value: cls._alliance_roles[value])
                    }
                )
                .assign(
                    **{
                        'alliance_id': await Mobius._get_alliance_id(alliance_name)
                    }
                )
                .to_dict('records')
            )

            # Registro de los enemigos en la base de datos
            db_connection.create('enemies', records)

            # Obtención de los registros de enemigos (Con ID de base de datos)
            enemies = db_connection.search_read('enemies', [('alliance_id', '=', alliance_id)], fields=['name', 'alliance_id'])

            # Obtención de los niveles de base estelar de cada enemigo
            planets = await Mobius._get_alliance_total_planets(alliance_name)

            # Obtención de los nombres de los enemigos para merge
            alliance_info = await Mobius.get_alliance_info(alliance_name)

            # Creación de los datos de planetas principales
            coords_records = (
                # Se unen los planetas con las IDs y nombres de los jugadores
                planets
                .merge(
                    alliance_info[['id', 'name']],
                    left_on= 'OwnerId',
                    right_on= 'id',
                )
                # Selección de columnas necesarias
                [[
                    'name',
                    'HQLevel',
                    'planet',
                ]]
                # Unión con las IDs de enemigos en la base de datos
                .merge(
                    enemies,
                    left_on= 'name',
                    right_on= 'name',
                )
                # Reasignación de nombres de columnas
                .rename(columns={'id': 'enemy_id', 'HQLevel': 'starbase_level'})
                # Selección final de columnas necesarias
                [[
                    'starbase_level',
                    'enemy_id',
                    'alliance_id',
                    'planet',
                ]]
                # Asignación de valores por defecto
                .assign(
                    **{
                        'war': True,
                        'create_uid': 1,
                        'write_uid': 1,
                    }
                )
                .to_dict('records')
            )

            # Registro de los planetas principales
            db_connection.create('coords', coords_records)

        # Retorno de la ID de la alianza en la base de datos
        return alliance_id



    @classmethod
    async def get_alliance_info(cls, alliance_name: str) -> pd.DataFrame:
        """
        Obtención de la información de la alianaza desde el API de Galaxy Life.
        """

        data = await cls._get(cls._base_url, "/alliances/get", {'name': alliance_name})

        # Creación del Pandas DataFrame
        df = pd.DataFrame(data['Members'])

        # Retorno del DataFrame
        return df.pipe(cls._apply_pipes(cls._pipes.sort_players_by_xplevel))



    @classmethod
    async def get_player_info(cls, player_id: int):
        """
        Obtención de los datos de un jugador individual.
        """

        # Obtención de los datos del jugador
        data = await cls._get(cls._base_url, "/users/get", {'id': player_id})

        return data



    @classmethod
    async def get_alliance_players(cls, alliance_name: str):
        """
        Obtención de la información de los jugadores de una alianza.
        """

        # Obtención de la información de la alianza
        alliance = await cls.get_alliance_info(alliance_name)

        # Inicialización de lista de jugadores
        players = []

        # Creación de los datos de cada uno de los jugadores
        for player_id in alliance['id'].to_list():

            # Obtención de la información del jugador
            player = await cls.get_player_info(player_id)

            # Creación de columna de nivel de base estelar
            player['Starbase'] = player['Planets'][0]['HQLevel']

            # Adición de los datos del jugador a la lista de jugadores
            players.append( player )

        # Creación del DataFrame con las columnas relevantes
        data = pd.DataFrame(players)[["Id", "Name", "Avatar", "Level", "Experience", "Starbase"]]

        # Retorno del DataFrame transformado para su uso
        return data.pipe(cls._apply_pipes(cls._pipes.sort_players_by_sblevel))


    @classmethod
    async def _get_alliance_total_planets(cls, alliance_name: str) -> pd.DataFrame:
        """
        Obtención de los planetas totales de una alianza.
        """

        # Obtención de la información de jugadores de la alianza
        alliance_info = await cls.get_alliance_info(alliance_name)

        # Obtención de las IDs de los jugadores
        player_ids = alliance_info['id'].to_list()

        # Inicialización de la lista de planetas por jugador
        total_planets: list[pd.DataFrame] = []

        # Iteración por cada una de las IDs de los jugadores
        for player_id in player_ids:

            # Se obtiene la información del jugador
            player = await cls.get_player_info(player_id)

            # Se crea el DataFrame de planetas del jugador
            planets = pd.DataFrame(player['Planets']).reset_index(names='planet')

            # Se añade el DataFrame a la lista
            total_planets.append( planets )

        # Se retornan los DataFrames concatenados de los planetas totales
        return pd.concat(total_planets)


    @classmethod
    async def _get_alliance_id(cls, alliance_name: str) -> int:
        """
        Obtención de la ID de una alianza registrada en la base de datos. En caso de no existir
        ésta, se registra y se retorna la ID generada en la base de datos.
        """

        # Búsqueda de la alianza en la base de datos
        db_data = db_connection.search_read('alliances', [('name', '=', alliance_name.lower())], fields= ['name', 'logo', 'level'], output_format= 'dict')

        if not len(db_data):
            # Búsqueda de la alianza en la API de GL
            api_data = await Mobius._get(Mobius._base_url, "/alliances/get", {'name': alliance_name})

            # Estructura del registro
            record = {
                'name': api_data['Name'].lower(),
                'logo': f"{api_data['Emblem']['Shape']}:{api_data['Emblem']['Pattern']}:{api_data['Emblem']['Icon']}",
                'level': api_data['AllianceLevel'],
            }

            # Creación del registro en la base de datos
            db_connection.create('alliances', record)

            # Búsqueda de la alianza en la base de datos
            db_data = db_connection.search_read('alliances', [('name', '=', alliance_name)], fields= ['name', 'logo', 'level'], output_format= 'dict')

        # Obtención de la ID de la alianza
        alliance_id = db_data[0]['id']

        # Retorno de la ID
        return alliance_id



    @classmethod
    def _apply_pipes(
        cls,
        pipe: Callable[[pd.DataFrame], pd.DataFrame] = None
    ) -> Callable[[pd.DataFrame], pd.DataFrame]:
        """
        Aplicación de funciones comunes a DataFrame.
        """
        
        default_pipes = [
            cls._pipes.snake_column_names
        ]

        # Función a llamar por Pandas
        def callable_pipe(df: pd.DataFrame):
            # Aplicación de los pipes default
            for i in default_pipes:
                df = df.pipe(i)
            # Aplicación del pipe prorporcionado
            if pipe:
                return df.pipe(pipe)
            else:
                return df

        # Retorno de la función a utilizar
        return callable_pipe

    @classmethod
    async def _get(cls, url: str, path: str, params: dict = {}):
        """
        Método de solicitud al API de Galaxy Life.
        """

        # Creación de sesión de solicitud de datos
        async with aiohttp.ClientSession() as session:

            while True:

                try:

                    # Solicitud de datos
                    async with session.get(f"{url}{path}", params= params) as response:

                        # Obtención del contenido de datos
                        data = json.loads(await response.text())

                        # Retorno de la información
                        return data

                except json.JSONDecodeError:
                    continue

    class _pipes:
        """
        Subclase contenedora de métodos de aplicación a DataFrames.
        """
        @classmethod
        def snake_column_names(cls, df: pd.DataFrame) -> pd.DataFrame:
            """
            Conversión de nombres de columna a snake_case.
            """
            return (
                df
                # Reasignación de nombres de columna
                .rename(
                    # Conversión de nombres usando RegEx
                    columns= {
                        col: (
                            re.sub(
                                r"([A-Z])",
                                r"_\1",
                                col
                            )
                            .lower()
                            [1:]
                        ) for col in df.columns
                    }
                )
            )

        # Pipes personalizados
        @classmethod
        def sort_players_by_xplevel(cls, df: pd.DataFrame) -> pd.DataFrame:
            return df.sort_values('level', ascending=False)
        @classmethod
        def sort_players_by_sblevel(cls, df: pd.DataFrame) -> pd.DataFrame:
            return df.sort_values('starbase', ascending=False)
