from fastapi import APIRouter, status, Depends, Body
from app.security.auth import get_current_user, pwd_context, hash_password
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

@router.post(
    "/change_password",
    status_code= status.HTTP_202_ACCEPTED,
    name= "Cambiar contraseña"
)
async def _change_password(
    current_password: str = Body(),
    new_password: str = Body(),
    user: UserInDB = Depends(get_current_user),
) -> bool:

    # Obtención de los datos del usuario desde la base de datos
    [ user_data ] = db_connection.read('users', [user.id], fields=['password'], output_format='dict')

    # Si la contraseña actual es correcta
    if ( pwd_context.verify(current_password, user_data['password']) ):

        # Se hashea la nueva contraseña
        hashed_password = hash_password(new_password)

        # Actualización de la contraseña en la base de datos
        db_connection.update('users', [user.id], {'password': hashed_password, 'has_changed_password': True})

        # Retorno de movimiento exitoso
        return True

    # Retorno para manejo de excepción
    else:
        return False

@router.post(
    "/change_display_name",
    status_code= status.HTTP_202_ACCEPTED,
    name= "Cambiar nombre"
)
async def _change_display_name(
    name: str = Body(),
    user: UserInDB = Depends(get_current_user),
) -> bool:

    # Actualización de nombre
    return db_connection.update('users', [user.id], {'name': name})

@router.post(
    '/activate_user',
    status_code= status.HTTP_200_OK,
    name= 'Activar usuario',
)
async def _activate_user(
    username: str,
    status: bool,
    user: UserInDB = Depends(get_current_user),
):

    if user.user == 'onnymm':
        [ user_id ] = db_connection.search('users', [('user', '=', username)])
        db_connection.update('users', user_id, {'active': status})

        return True
    return 'No eres Onnymm'
