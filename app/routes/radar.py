from fastapi import (
    APIRouter,
    status,
    Body,
    Depends,
    Query,
)
from app.extensions.mobius.radar import Radar
from app.extensions.mobius._types import AllianceData
from app.security.auth import get_current_user
from app.models import UserInDB

# Creación del ruteador
router = APIRouter(
    prefix= '/radar',
    tags= ['Radar'],
)

@router.get(
    '/alliances',
    status_code= status.HTTP_200_OK,
    name= 'Alianzas registradas',
)
async def _alliances(
    user: UserInDB = Depends(get_current_user),
) -> list[AllianceData]:
    """
    ## Ver las alianzas registradas en el radar
    Este endpoint permite visualizar las alianzas registradas en el radar para
    ser escaneadas.
    """

    alliances = await Radar.get_current_alliances()
    print(alliances)

    return alliances

@router.post(
    '/register',
    status_code= status.HTTP_201_CREATED,
    name= 'Registrar alianza',
)
async def _register(
    user: UserInDB = Depends(get_current_user),
    alliance_name: str = Body(),
) -> bool:
    """
    ## Registrar una alianza en el radar
    Este endpoint permite registrar una alianza en el radar para posteriormente
    ser escaneada. Se retorna un valor `True` si el registro fue exitoso. En
    caso de que la alianza no exista, se retorna un valor `False`.
    """

    return await Radar.add(alliance_name)

@router.delete(
    '/delete',
    status_code= status.HTTP_200_OK,
    name= 'Eliminar alianza',
)
async def _delete(
    user: UserInDB = Depends(get_current_user),
    alliance_name: str = Query(),
) -> bool:
    """
    ## Eliminar una alianza del radar
    Este endpoint permite eliminar una alianza del radar.
    """

    return await Radar.remove(alliance_name)

@router.get(
    '/scan',
    status_code= status.HTTP_200_OK,
    name= 'Escanear alianzas',
)
async def scan(
    user: UserInDB = Depends(get_current_user),
) -> list[AllianceData]:
    """
    ## Escanear alianzas
    Este endpoint ejecuta el escaneo de las alianzas registradas en el radar y
    retorna la lista de datos retornada por la API de Galaxy Life.
    """

    return await Radar.scan()
