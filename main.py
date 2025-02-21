from fastapi import FastAPI
from app.routes import (
    account,
    coords,
    status,
    authentication,
    websockets,
)
from fastapi.middleware.cors import CORSMiddleware

# Inicialización de la app
app = FastAPI()

# Configuración de orígenes permitidos
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://thesmashersquad.vercel.app",
]

# Agregar el middleware de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Lista de orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"], # Métodos HTTP permitidos
    allow_headers=["*"], # Encabezados permitidos
)

# Rutas de autenticación
app.include_router(authentication.router, prefix= "/token", tags= ["Autenticación"])
app.include_router(account.router, prefix= "/account", tags= ["Cuenta"])

# Se añaden las rutas
app.include_router(coords.router, prefix= "/alliances", tags= ["Coordenadas"])
app.include_router(status.router, prefix= "/status", tags= ["Estatus"])

app.include_router(websockets.router, prefix= '/ws', tags= ['Websockets'])
