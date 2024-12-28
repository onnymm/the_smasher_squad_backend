import os
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import Depends, status
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import Annotated, Union
from datetime import datetime, timedelta
from app.database import db_connection
from app.models.users import UserData, UserInDB

class Token(BaseModel):
    """
    Modelo de token de acceso de usuario.
    """
    access_token: str
    token_type: str

class _TokenData(BaseModel):
    username: str

# Expiración de token
_expire_days = 30

# Clave de encriptación
_KEY = os.environ.get("CRYPT_KEY")
# Algoritmo de encriptación
_algorithm = "HS256"
# Contexto para hasheo
_pwd_context = CryptContext(schemes= ["bcrypt"], deprecated= "auto")

# Error de credenciales inválidas
_credentials_exception = HTTPException(
    status_code= status.HTTP_401_UNAUTHORIZED,
    detail= "Credenciales inválidas",
    headers= {"WWW-Authenticate": "Bearer"},
)

# Error de usuario inactivo
_inactive_user_exception = HTTPException(
    status_code= status.HTTP_401_UNAUTHORIZED,
    detail= "Usuario inactivo no autorizado",
)

# Esquema OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl= "token")

def _get_user(username) -> UserInDB | bool:
    """
    ## Obtención de usuario
    Esta función interna obtiene el usuario especificado por `username` desde
    la base de datos y lo retorna. En caso de no encontrarlo, retorna `False`.
    """

    # Intento de obtención de usuario
    try:
        [ user ] = db_connection.search_read("users", [('user', '=', username)], fields= ['id', 'user', 'name', 'password'], output_format= "dict")

    # Ausencia de usuario
    except ValueError:
        return False

    # Retorno del usuario
    return UserInDB(**user)

def hash_password(password: str):
    """
    Obtención de hash de contraseña.
    """
    return _pwd_context.hash(password)

def authenticate_user(username: str, password: str) -> UserData | bool:
    """
    ## Autenticación de usuario
    Esta función realiza la autenticación de usuario con el nombre de usuario
    y su contraseña correspondiente.

    La validación se realiza primero obteniendo el registro del usuario en la
    base de datos. En caso de no existir el usuario o haber fallado en la
    coincidencia de contraseña es retorna `False`. Caso contrario, se retorna el
    usuario.
    """

    # Obtención del usuario desde la base de datos
    user = _get_user(username)

    # Si existe el usuario se realiza la validación de contraseña
    if user:

        # Si la validación de contraseña retorna Verdadero
        if _pwd_context.verify(password, user.password):
            # Se retorna el usuario
            return user

    # Se retorna Falso en caso de no existir usuario o tener contraseña incorreta
    else:
        return False

def create_access_token(data: dict):
    """
    ## Creación de token de acceso
    Esta función crea un token temporal para poder acceder a la aplicación
    sin necesidad de colocar el nombre de usuario y la contraseña en todos y
    cada uno de los endpoints del backend
    """
    # Copia del diccionario de entrada
    to_encode = data.copy()

    # Creación de fecha de expiración
    expiration_date = datetime.now() + timedelta(days= _expire_days)
    
    # Asignación de valores al diccionario a codificar
    to_encode.update({'exp': str(expiration_date)})

    # Retorno del diccionario codificado
    return jwt.encode(data, _KEY, algorithm = _algorithm)

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserData:
    """
    ## Obtención del usuario por token
    Esta función recibe un token previamente provisto para autenticar al
    usuario. Si el token es inválido, el usuario no existe o el token ha
    expirado se genera un error de credenciales inválidas. En caso contrario se
    retornan los datos del usuario.
    """

    # Intento de nombre de usuario del token provisto al API
    try:
        # Decodificación del token usando la llave de encriptación y el algoritmo correspondiente
        payload = jwt.decode(token, _KEY, algorithms= [_algorithm])
        # Obtención del nombre de usuario
        username: str = payload.get("sub")

        # Si no se obtuvo el nombre de usuario
        if username is None:
            # Se genera el error de credenciales inválidas
            raise _credentials_exception
        
        # En caso de que el nombre de usuario se halla obtenido, se crean el objeto de datos de token
        token_data = _TokenData(username= username)

    # En caso de ser un token inválido
    except InvalidTokenError:
        # Se genera el error de credenciales inválidas
        raise _credentials_exception

    # Obtención del usuario desde la base de datos por medio del objeto de datos de token
    user = _get_user(token_data.username)

    # Si no hay usuario en la base de datos
    if user is None:
        # Se genera el error de credenciales inválidas
        raise _credentials_exception

    # Retorno del usuario
    return user

def is_active_user(user: UserInDB = Depends(get_current_user)):

    # Obtención del registro del usuario
    [ record ] = db_connection.search_read('users', [('user', '=', user.user)], fields=["active"], output_format='dict')

    # Si el usuario no está activo
    if not record['active']:

        # Se lanza error de autenticación
        raise _inactive_user_exception

    # Retorno de autorización
    return True
