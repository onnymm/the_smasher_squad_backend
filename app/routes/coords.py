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
