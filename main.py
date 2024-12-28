from fastapi import FastAPI
from app.routes import (
    coords,
    status,
    authentication,
)

# Inicialización de la app
app = FastAPI()

# Rutas de autenticación
app.include_router(authentication.router, prefix= "/token", tags= ["Autenticación"])

# Se añaden las rutas
app.include_router(coords.router, prefix= "/alliances", tags= ["Coordenadas"])
app.include_router(status.router, prefix= "/status", tags= ["Estatus"])
