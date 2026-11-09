
from pydantic import BaseModel, Field


class TokensUsage(BaseModel):
    prompt_tokens:int = Field(ge=0, description="Tokens consumidos en el prompt")
    completion_tokens:int = Field(ge=0, description= "Tokens de salida")
    total_tokens:int|None =Field(None,ge=0, description="Consumo total de tokens")



class InputMessage(BaseModel):
    """
    Schema for the input message.
    """
    message: str = Field(...,min_length=1, max_length=4000)
    system: str|None = Field(
        default=None, 
        description="instrucción de comportamiento del asistente",
        min_length=1, max_length=4000)
    temperature: float|None =Field(default=None, ge=0.0, le=2.0)
    max_tokens: int|None = Field(default=4200, description="límite de la respuesta", ge=1)


class ResponseMessage(BaseModel):
    """
    Schema for the response message.
    """
    reply: str = Field(..., description="la respuesta del modelo")
    model: str = Field(...,description="qué modelo respondió")
    usage: TokensUsage|None = Field(default=None, description="Registro de consumo de tokens")



    