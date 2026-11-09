from functools import lru_cache
from pydantic import BaseModel, SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from fastapi import Depends

class BedrockSettings(BaseModel):

    aws_region:str
    model_id: str 
    max_tokens: int = Field(default=1024, ge=0, le=4200)
    timeout_s: int = Field(default=30, ge=0, le=60)


class Settings(BaseSettings):

    bedrock:BedrockSettings

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_nested_delimiter="__", 
        env_file_encoding="utf-8"
    )



@lru_cache()
def _get_global_settings() -> Settings:
    """Carga todo el .env en memoria una sola vez."""
    return Settings()


def get_bedrock_settings() -> BedrockSettings:
    return _get_global_settings().bedrock

