from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_bedrock_settings
from app.routers.chat import chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Falla al arrancar, no en la primera petición, si el .env es inválido.
    get_bedrock_settings()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(chat_router, prefix="/api/v1")


@app.get("/")
def welcome():
    return {"mensaje": "Bienvenidos a esta prueba"}


@app.get("/health")
def health():
    return {"status": "ok"}
