from fastapi import APIRouter, status, Depends
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from app.security.auth import (
    authenticate_user,
    create_access_token,
    Token,
)

router = APIRouter()

@router.post("/", name= "Obtención de token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    ## Endpoint de obtención de token de autenticación de usuario
    Para obtener un token de acceso se debe contar con una cuenta de usuario.
    """

    # Obtención del usuario
    user = authenticate_user(form_data.username, form_data.password)

    # Gemeración de error en caso de no haber usuario
    if not user:
        raise HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail= "Nombre de usuario o contraseña incorrectos",
            headers= {"WWW-Authenticate": "Bearer"}
        )

    # Creación del token de acceso
    access_token = create_access_token({'sub': user.user})
    print(access_token)

    # Retorno del token
    return Token(access_token= access_token, token_type= "bearer")
