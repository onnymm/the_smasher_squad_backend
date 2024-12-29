from fastapi import APIRouter, status, Depends
from app.security.auth import get_current_user
from app.database import db_connection
from app.models.users import UserInDB

router = APIRouter()

@router.get(
    "/me",
    status_code= status.HTTP_200_OK,
    name= "Mi cuenta"
)
async def _get(user: UserInDB = Depends(get_current_user)):
    """
    ## Mi cuenta
    Este endpoint muestra la información del usuario actual.
    """

    # Campos a retornar
    fields = ['id', 'user', 'name', 'avatar', 'create_date', 'write_date']

    # Obtención del usuario
    [ data ] = db_connection.read("users", [user.id], fields= fields, output_format="dict")

    # Retorno de la información
    return data
