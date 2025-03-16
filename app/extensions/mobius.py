from dml_manager import DMLManager
from typing import Any, TypedDict, Literal, Callable, Coroutine
import asyncio
import aiohttp
import json
import pandas as pd
import re
from app.constants import planet_wp
from yarl import URL
import functools

class _AllianceEmblem(TypedDict):
    Shape: int
    Pattern: int
    Icon: int

class _AllianceMember(TypedDict):
    Id: int
    Name: str
    Avatar: str
    Level: int
    AllianceRole: Literal[0, 1, 2]
    TotalWarPoints: int

class AllianceData(TypedDict):
    Id: str
    Name: str
    Description: str
    Emblem: _AllianceEmblem
    AllianceLevel: int
    WarPoints: int
    WarsWon: int
    WarsLost: int
    InWar: bool
    OpponentAllianceId: int
    Members: list[_AllianceMember]

class _UserPlanets(TypedDict):
    OwnerId: int
    HQLevel: int

class _IndividualUser(TypedDict):
    Id: int
    Name: str
    Avatar: str
    Level: str
    Experience: int
    TutorialCompleted: bool
    AllianceId: str | None
    Planets: list[_UserPlanets]

_PipeFunction = Callable[[pd.DataFrame], pd.DataFrame]

# Pipes por defecto
_default_pipes: list[_PipeFunction] = [
    # Conversión de nombres de columna a snake case
    lambda df: (
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
]

def apply_custom_pipes(pipes: list[_PipeFunction] | _PipeFunction = []):

    # Decorador generado a usar
    def decorator(callback: Callable[[], pd.DataFrame]):

        # Función empaquetada
        @functools.wraps(callback)
        async def method_wrapper(*args, **kwargs):

            # Se toman los datos de la función
            df = await callback(*args, **kwargs)

            # Aplicación de pipes por defecto
            for pipe in _default_pipes:
                # Se reasigna el resultado del DataFrame
                df = df.pipe(pipe)

            # Si fue provista una lista de pipes...
            if isinstance(pipes, list):

                # Iteración por cada pipe
                for pipe in pipes:
                    # Se reasigna el resultado del DataFrame
                    df = df.pipe(pipe)

            # Si sólo una función fue provista...
            else:
                df = df.pipe(pipes)

            # Retorno del DataFrame
            return df

        # Retorno del método empaquetado
        return method_wrapper

    # Retorno del decorador generado
    return decorator

def sort_players_by_xplevel(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values('level', ascending=False)

def sort_players_by_sblevel(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values('starbase', ascending=False)

class Mobius():

    # URL base para conexión con el API de Galaxy Life
    _base_url = "https://api.galaxylifegame.net"

        # Roles de la alianza
    _alliance_roles = [
        'general',
        'captain',
        'private',
    ]

    # Nombre de la alianza propia
    _own_alliance = 'the smasher squad'



    def __init__(self, db_instance: DMLManager):
        self._db_connection = db_instance
        # self._analytics = Analytics(self)



    def get_alliance_availability(self, alliance_name: str):
        alliance_players = self.get_alliance_players(alliance_name.lower())
        return self._analytics.validate_availability(alliance_players)



    async def current_opponent_alliance(self) -> int | bool:

        # Obtención de la ID de la alianza enemiga (Si es que estamos en guerra)
        alliance_id: int = self._db_connection.get_value(
                'war',
                1,
                'alliance_id'
            )

        # Si hay una alianza enemiga
        if alliance_id:

            # Se retorna la ID de la alianza enemiga
            return alliance_id

        # Se retorna False para manejo del valor
        else:
            return False



    def init_war(self) -> int | bool:

        # Obtención de los datos de nuestra alianza
        own_alliance_data: AllianceData = self._sync_get('/alliances/get', {'name': self._own_alliance})

        # Se obtiene la ID de la alianza enemiga actual
        current_opponent_alliance_from_api = own_alliance_data['OpponentAllianceId']


        # Si estamos en guerra
        if current_opponent_alliance_from_api != '':

            # Obtención de la ID de la alianza activa en la base de datos
            current_opponent_alliance_from_db: int = self._db_connection.get_value(
                'war',
                1,
                'alliance_id'
            )

            # Obtención de la ID de la alianza enemiga:
            current_opponent_alliance_id = self._get_alliance_id(current_opponent_alliance_from_api)

            # Si la base de datos está desactualizada
            if current_opponent_alliance_from_db != current_opponent_alliance_id:

                # Actualización en la base de datos
                self._db_connection.update(
                    'war',
                    [1],
                    {
                        'alliance_id': current_opponent_alliance_id,
                        'enemy_alliance_regeneration_hours': 3
                    }
                )

                # Registro de la alianza en la base de datos
                self._register_alliance_in_db(current_opponent_alliance_from_api)

            # Retorno de la ID de la alianza actual
            return current_opponent_alliance_id

        else:

            # Se actualiza el estatus de guerra a inactivo
            self._db_connection.update(
                'war',
                [1],
                {
                    'alliance_id': None,
                    'enemy_alliance_regeneration_hours': 3
                }
            )

            # Retorno de nulidad de alianza enemiga
            return False



    async def get_alliance_coords(self, alliance_id: int) -> pd.DataFrame:
        """
        ## Coordenadas de una alianza
        Obtención de las coordenadas de una alianza registrada en la base de datos.
        """

        # Obtención de los planetas
        planets = self._db_connection.search_read(
            'coords',
            [('alliance_id', '=', alliance_id)],
        )

        # Obtención de las IDs de los planetas enemigos
        enemies_planets_ids: list[int] = planets['enemy_id'].to_list()

        # Obtención de la información de los enemigos
        enemies = self._db_connection.search_read(
            'enemies', [('id', 'in', enemies_planets_ids)],
            fields=['name', 'avatar', 'level']
        )

        # Obtención de los usuarios
        users = self._db_connection.search_read('users', fields=['user', 'avatar'])

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



    async def _register_alliance_in_db(self, alliance_name: str) -> int:
        """
        ## Registro de alianza en base de datos
        Registro o tentativa de registro de una alianza y sus miembros en la base de datos.
        """

        # Obtención de la ID de la alianza
        alliance_id = self._get_alliance_id(alliance_name)

        # Conteo de registros
        count = self._db_connection.search_count('enemies', [('alliance_id', '=', alliance_id)])

        # Si no hay registros
        if not count:

            # Obtención de los datos de la alianza
            alliance_data = await self.get_alliance_info(alliance_name)

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
                        'role': lambda df: df['role'].apply(lambda value: self._alliance_roles[value]),
                        'online': False,
                    }
                )
                .assign(
                    **{
                        'alliance_id': alliance_id,
                    }
                )
                .to_dict('records')
            )

            # Registro de los enemigos en la base de datos
            self._db_connection.create('enemies', records)

            # Obtención de los registros de enemigos (Con ID de base de datos)
            enemies = self._db_connection.search_read('enemies', [('alliance_id', '=', alliance_id)], fields=['name', 'alliance_id'])

            # Obtención de los niveles de base estelar de cada enemigo
            planets = self._get_alliance_total_planets(alliance_name)

            # Obtención de los nombres de los enemigos para merge
            alliance_info = await self.get_alliance_info(alliance_name)

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
            self._db_connection.create('coords', coords_records)

        # Retorno de la ID de la alianza en la base de datos
        return alliance_id



    async def _get_alliance_total_planets(self, alliance_name: str) -> pd.DataFrame:
        """
        ## Planetas totales
        Obtención de los planetas totales de una alianza.
        """

        # Obtención de la información de jugadores de la alianza
        alliance_info = await self.get_alliance_info(alliance_name)

        # Obtención de las IDs de los jugadores
        player_ids = alliance_info['id'].to_list()

        # Inicialización de la lista de planetas por jugador
        total_planets: list[pd.DataFrame] = []

        # Iteración por cada una de las IDs de los jugadores
        for player_id in player_ids:

            # Se obtiene la información del jugador
            player = self.get_player_info(player_id)

            # Se crea el DataFrame de planetas del jugador
            planets = (
                pd.DataFrame(player['Planets'])
                .reset_index(names='planet')
            )

            # Se añade el DataFrame a la lista
            total_planets.append( planets )

        # Se retornan los DataFrames concatenados de los planetas totales
        return pd.concat(total_planets)



    def _get_alliance_id(self, alliance_name: str) -> int:
        """
        ## ID de alianza en la base de datos
        Obtención de la ID de una alianza registrada en la base de datos. En caso de no existir
        ésta, se registra y se retorna la ID generada en la base de datos.
        """

        # Se convierte el nombre de la alianza a minúsculas
        alliance_name = alliance_name.lower()

        # Búsqueda de la alianza en la base de datos
        db_data = self._db_connection.search_read(
            'alliances',
            [('name', '=', alliance_name)],
            fields= ['name', 'logo', 'level'],
            output_format= 'dict'
        )

        if not db_data:
            # Búsqueda de la alianza en la API de GL
            api_data: AllianceData = self._sync_get('/alliances/get', {'name': alliance_name})

            # Estructura del registro
            record = {
                'name': api_data['Name'].lower(),
                'logo': f"{ api_data['Emblem']['Shape'] }:{ api_data['Emblem']['Pattern'] }:{ api_data['Emblem']['Icon'] }",
                'level': api_data['AllianceLevel'],
            }

            # Creación del registro en la base de datos
            [ alliance_id ] = self._db_connection.create('alliances', record)

        else:
            # Obtención de la ID de la alianza
            alliance_id: int = db_data[0]['id']

        # Retorno de la ID
        return alliance_id



    @apply_custom_pipes(sort_players_by_xplevel)
    async def get_alliance_players(self, alliance_name: str) -> pd.DataFrame:
        """
        Obtención de la información de los jugadores de una alianza.
        """

        # Obtención de la información de la alianza
        alliance = await self.get_alliance_info(alliance_name)

        # Inicialización de lista de jugadores
        players: list[_IndividualUser] = []

        # Creación de los datos de cada uno de los jugadores
        for player_id in alliance['id'].astype(int).to_list():

            # Obtención de la información del jugador
            player = self.get_player_info(player_id)

            # Creación de la columna del nivel de base estelar
            player['Starbase'] = player['Planets'][0]['HQLevel']

            # Adición de los datos del jugador a la lista de jugadores
            players.append(player)

        # Creación del DataFrame con las columnas relevantes
        data = pd.DataFrame(players)[["Id", "Name", "Avatar", "Level", "Experience", "Starbase"]]

        # Retorno del DataFrame
        return data



    async def get_player_info(self, player: int | str) -> _IndividualUser:
        """
        Obtención de los datos de un jugador individual por ID o usuario.
        """

        if isinstance(player, int):
            # Obtención de los datos del jugador
            data: _IndividualUser = await self._get('/users/get', {'id': player}, error_handler= self._errors._not_user)

        else:
            # Obtención de los datos del jugador
            data: _IndividualUser = await self._get('/users/name', {'name': player}, error_handler= self._errors._not_user)

        return data



    @apply_custom_pipes([])
    async def get_alliance_info(self, alliance_name: str) -> pd.DataFrame:
        """
        Obtención de la información de la alianza desde el API de Galaxy Life.
        """

        # Obtención de los datos desde el API de Galaxy Life
        data: AllianceData = await self._get("/alliances/get", {"name": alliance_name})

        # Retorno de la información para convertirse en DataFrame
        return pd.DataFrame(data['Members'])



    async def _get_alliance_info(self, alliance_name: str) -> AllianceData:
        """
        Obtención de la información de la alianza desde la API de Galaxy Life
        """

        # Obtención de los datos desde la API de Galaxy Life
        return await self._get('/alliances/get', {'name': alliance_name})



    async def _get(self, path: str, params: dict[str, str | int], url: str = _base_url, error_handler = None) -> list[dict]:
        "Método de solicitud al API de Galaxy Life de manera asíncrona"

        return await self._request(url, path, params, error_handler)



    def _sync_get(self, path: str, params: dict[str, str | int], url: str = _base_url, error_handler = None) -> list[dict]:
        """
        Método de solicitud al API de Galaxy Life de manera síncrona.
        """

        # Ejecución asíncrona
        return self._exec_sync(
            self._request(url, path, params, error_handler)
        )



    def _exec_sync(self, callback) -> list[dict] | Any:
        """
        Ejecución de una función asíncrona y obtención de su resolución de promesa.
        """

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Aplicación para entorno py
            loop = None
        
        if loop and loop.is_running():
            # Aplicación para entorno Jupyter
            import nest_asyncio
            nest_asyncio.apply()
            # Ejecución de la función asíncrona en ipynb
            return asyncio.run(callback)
        else:
            # Ejecución de la función asíncrona en py
            return asyncio.run(callback)



    async def _request(self, url: str, path: str, params: dict[str, str | int], error_handler):
        """
        Método de solicitud al API de Galaxy Life.
        """


        # Creación de sesión de solicitud de datos
        async with aiohttp.ClientSession() as session:
            full_url = str(URL(f"{url}{path}").with_query(params))

            # Se crea un conteo de intentos ya que a veces la solicitud no se ejecuta correctamente
            attempts = 1

            # Se intenta ejecutar al menos tres veces
            while attempts <= 3:

                try:

                    # Solicitud de datos
                    async with session.get(full_url) as response:

                        # Obtención del contenido de datos
                        response_content = await response.text()

                        # Transformación a JSON
                        data = json.loads(response_content)

                        # Retorno de la información
                        return data

                # Si no se ejecutó correctamente se cuenta el intento y se reintenta ejecutar
                except json.JSONDecodeError:
                    # Se intenta obtener información alternativa
                    alt_data = error_handler(response_content) if error_handler else None
                    # Si existe la información alternativa, se retorna ésta
                    if not (alt_data is None):
                        return alt_data

                    # Conteo de intentos
                    attempts += 1
                    continue



    class _errors():

        _empty_user = {
            'Id': '',
            'Name': '',
            'Avatar': '',
            'Level': 0,
            'Experience': 0,
            'TutorialCompleted': False,
            'AllianceId': None,
            'Planets': []
        }

        _NOT_USER_ID = 'User with this id does not exist!'
        _NOT_USER_NAME = 'User with this name does not exist!'

        @classmethod
        def _not_user(cls, response_content) -> _IndividualUser:
            if response_content == cls._NOT_USER_ID or response_content == cls._NOT_USER_NAME:
                return {}

class Analytics():

    _difficulties = {
        'easy': {
            'low': {
                'xp': 0.75,
                'wp': 0.8,
                'sb': -0.75
            },
            'high': {
                'xp': 1.33,
                'wp': 1.25,
                'sb': 1.75
            }
        },
        'medium': {
            'low': {
                'xp': 0.67,
                'wp': 0.75,
                'sb': -1.10
            },
            'high': {
                'xp': 1.5,
                'wp': 1.5,
                'sb': 1.35
            }
        },
        'hard': {
            'low': {
                'xp': 0.5,
                'wp': 0.67,
                'sb': -2.25
            },
            'high': {
                'xp': 2.0,
                'wp': 2.0,
                'sb': 2.5
            }
        },
    }

    def __init__(self, parent: Mobius) -> None:
        self._parent = parent
        self._own_players = self.get_alliance_players(self._parent._own_alliance)
        self._own_stats = self.get_own_stats()

    def get_alliance_players(self, alliance_name: str) -> pd.DataFrame:
        players = (
            self._parent.get_alliance_players(alliance_name)
            .pipe(self.pipes.stars)
        )

        return players

    def get_own_stats(self) -> dict[str, pd.DataFrame]:
        stats = {
            diff: (
                self._own_players
                .agg(
                    {
                        'level': 'mean',
                        'starbase': 'mean',
                        'war_points': 'sum'
                    }
                )
                .reset_index()
                .set_index('index')
                .T
                .pipe(
                    lambda df: pd.concat(
                        [
                            (
                                df
                                .assign(
                                    level= lambda df: df['level'] * self._difficulties[diff]['low']['xp'],
                                    war_points= lambda df: df['war_points'] * self._difficulties[diff]['low']['wp'],
                                    starbase= lambda df: df['starbase'] + self._difficulties[diff]['low']['sb'],
                                )
                            ),
                            (
                                df
                                .assign(
                                    level= lambda df: df['level'] * self._difficulties[diff]['high']['xp'],
                                    war_points= lambda df: df['war_points'] * self._difficulties[diff]['high']['wp'],
                                    starbase= lambda df: df['starbase'] + self._difficulties[diff]['high']['sb'],
                                )
                            ),
                        ]
                    )
                )
            ) for diff in self._difficulties
        }

        return stats



    def validate_availability(self, enemy_alliance: pd.DataFrame):
        """
        ## Revisión de disponibilidad de alianza enemiga
        Este método se encarga de validar si una alianza enemiga está disponible
        para alguna dificultad en declaración de guerra y muestra los datos de las
        razones por las cuales ésta no estaría disponible en alguna de las difucultades
        de guerra.
        """

        # Traducción de nombres de variables
        translation = {
            'level': 'nivel promedio de XP',
            'starbase': 'nivel promedio de bases estelares',
            'war_points': 'suma de puntos de guerra farmeables',
        }

        # Creación de estadísticas de la alianza enemiga
        enemy_stats = (
            enemy_alliance
            .pipe(self.pipes.stars)
            .agg(
                {
                    'level': 'mean',
                    'starbase': 'mean',
                    'war_points': 'sum'
                }
            )
            .reset_index()
            .set_index('index')
            .T
        )

        # Validación de rangos
        alliance_range = {
            'easy': ((enemy_stats - self._own_stats['easy'].iloc[0]) > 0) & ((self._own_stats['easy'].iloc[1] - enemy_stats) > 0),
            'medium': ((enemy_stats - self._own_stats['medium'].iloc[0]) > 0) & ((self._own_stats['medium'].iloc[1] - enemy_stats) > 0),
            'hard': ((enemy_stats - self._own_stats['hard'].iloc[0]) > 0) & ((self._own_stats['hard'].iloc[1] - enemy_stats) > 0),
        }

        # Creación de diccionario de datos de rangos de dificultades
        diff_range = {
            'easy': {'available': None, 'messages': []},
            'medium': {'available': None, 'messages': []},
            'hard': {'available': None, 'messages': []},
        }

        # Obtención de métricas
        for diff in alliance_range:
            diff_range[diff]['available'] = bool(alliance_range[diff].iloc[0].all())
            for value in ['level', 'starbase', 'war_points']:
                if not alliance_range[diff].at[0, value]:
                    diff_range[diff]['messages'].append(f'Estamos fuera del rango de {translation[value]}')

        # Conversión de estadísticas a diccionarios
        data = {
            'own': {
                'level': round(
                    float(
                        self._own_players
                        ['level']
                        .mean()
                    ),
                    2
                ),
                'starbase': round(
                    float(
                        self._own_players
                        ['starbase']
                        .mean()
                    ),
                    2
                ),
                'war_points': round(
                    float(
                        self._own_players
                        ['war_points']
                        .sum()
                    ),
                    2
                ),
            },
            'enemy': {
                'level': round(
                    float(
                        enemy_alliance
                        ['level']
                        .mean()
                    ),
                    2
                ),
                'starbase': round(
                    float(
                        enemy_alliance
                        ['starbase']
                        .mean()
                    ),
                    2
                ),
                'war_points': round(
                    float(
                        enemy_alliance
                        .pipe(self.pipes.stars)
                        ['war_points']
                        .sum()
                    ),
                    2
                ),
            },
        }

        # Unión de datos
        data['range'] = diff_range

        # Retorno de datos
        return data

    class pipes():

        @classmethod
        def stars(cls, data: pd.DataFrame) -> pd.DataFrame:
            return (
                data
                .assign(
                    war_points = lambda df: (
                        df
                        ['starbase']
                        .apply(lambda value: planet_wp[value])
                    )
                )
            )
