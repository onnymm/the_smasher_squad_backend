from fastapi import FastAPI
from app.routes import coords
from app.routes import status

# Inicialización de la app
app = FastAPI()

# Se añaden las rutas
app.include_router(coords.router, prefix= "/alliances", tags= ["Coordenadas"])
app.include_router(status.router, prefix= "/status", tags= ["Estatus"])
