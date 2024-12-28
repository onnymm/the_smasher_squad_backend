from fastapi import APIRouter, Depends, status
from app import Mobius
from app.models.users import UserInDB
from app.security.auth import is_active_user

router = APIRouter()

@router.get(
    "/coords",
    status_code= status.HTTP_200_OK,
    name= "Coordenadas de la guerra actual"
)
async def _get_current_coords(active: bool = Depends(is_active_user)):

    # Obtención de la alianza enemiga actual
    alliance_id = Mobius.current_opponent_alliance()

    # Si hay guerra
    if alliance_id:

        # Obtención de las coordenadas de la alianza enemiga
        coords = await Mobius.get_alliance_coords(alliance_id)

        # Retorno de las coordenadas en formato JSON
        return coords.to_dict("records")

    # Retorno de una lista vacía
    else:
        return []
