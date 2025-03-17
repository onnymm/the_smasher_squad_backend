from app import mobius
from ._types import AllianceData

class Radar():

    # Lista de alianzas
    _alliances_list: list[AllianceData] = []

    @classmethod
    async def add(cls, alliance_name: str) -> bool:
        # Búsqueda de la alianza
        found_alliance = await mobius._get_alliance_info(alliance_name.strip())
        # Si la alianza existe...
        if found_alliance:
            # Se añade la alianza a la lista del radar
            cls._alliances_list.append(found_alliance)
            # Se retorna un True para confirmar que la alianza fue añadida
            return True
        # Si la alianza no existe, se indica por medio del valor retornado
        else:
            return False

    @classmethod
    async def get_current_alliances(cls) -> list[AllianceData]:
        # Se retorna la lista de alianzas
        return cls._alliances_list

    @classmethod
    async def remove(cls, alliance_name: str) -> bool:
        # Búsqueda de la alianza en la lista de alianzas
        for alliance in cls._alliances_list:
            # Si el nombre de la alianza coincide con la alianza i de la lista...
            if alliance['Id'] == alliance_name:
                # Se remueve la alianza de la lista
                cls._alliances_list.remove(alliance)
                # Se retorna valor de confirmación
                return True
        # Si la alianza no fue encontrada, se retorna valor para error
        return False

    @classmethod
    async def scan(cls) -> list[AllianceData]:
        # Inicialización de alianzas escaneadas a retornar
        scanned_alliances: list[AllianceData] = []
        # Iteración por alianzas
        for alliance in cls._alliances_list:
            # Se escanea la alianza y se añade a la lista de alianzas escaneadas a retornar
            scanned_alliances.append( await mobius._get_alliance_info(alliance['Id']) )
        # Se retorna la lista de alianzas escaneadas
        return scanned_alliances
