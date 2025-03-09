from fastapi import APIRouter, status
from app import mobius

router = APIRouter()

@router.get(
    "/refresh",
    status_code= status.HTTP_200_OK,
    name= "Revisión inicial de si hay una nueva guerra"
)
def _refresh_war() -> int | None:

    # Obtención de la ID de la alianza enemiga
    alliance_id = mobius.init_war()

    # Retorno de la ID de la alianza enemiga
    return alliance_id
