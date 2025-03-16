from fastapi import APIRouter, status
from app import Mobius

router = APIRouter()

@router.get(
    "/refresh",
    status_code= status.HTTP_200_OK,
    name= "Revisión inicial de si hay una nueva guerra"
)
async def _refresh_war() -> int | None:

    # Obtención de la ID de la alianza enemiga
    alliance_id = await Mobius.init_war()

    # Retorno de la ID de la alianza enemiga
    return alliance_id
