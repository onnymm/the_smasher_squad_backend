import json
import aiohttp
import pandas as pd
import re
from typing import Callable

class Mobius():
    """
    Módulo de comunicación con la API de Galaxy Life
    """

    _base_url = "https://api.galaxylifegame.net"

    @classmethod
    async def get_alliance_info(cls, alliance_name: str) -> pd.DataFrame:

        data = await cls._get(cls._base_url, "/alliances/get", {'name': alliance_name})

        # Creación del Pandas DataFrame
        df = pd.DataFrame(data['Members'])

        # Retorno del DataFrame
        return df.pipe(cls._apply_pipes(cls._pipes.sort_players_by_xplevel))

    @classmethod
    async def get_player_info(cls, player_id: int):

        data = await cls._get(cls._base_url, "/users/get", {'id': player_id})

        return data

    @classmethod
    async def get_alliance_players(cls, alliance_name: str):

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
    def _apply_pipes(
        cls,
        pipe: Callable[[pd.DataFrame], pd.DataFrame] = None
    ) -> Callable[[pd.DataFrame], pd.DataFrame]:
        
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

        # Creación de sesión de solicitud de datos
        async with aiohttp.ClientSession() as session:

            # Solicitud de datos
            async with session.get(f"{url}{path}", params= params) as response:

                # Obtención del contenido de datos
                data = json.loads(await response.text())

                # Retorno de la información
                return data

    class _pipes:
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
