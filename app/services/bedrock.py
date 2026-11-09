from dataclasses import dataclass
import logging
from typing import Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import (
    ClientError,
    ConnectTimeoutError,
    ConnectionClosedError,
    EndpointConnectionError,
    NoCredentialsError,
    PartialCredentialsError,
    ReadTimeoutError,
)

from app.config import BedrockSettings
from app.schemas import TokensUsage

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Error base de la capa de modelo."""


class LLMConfigurationError(LLMError):
    """Credenciales, región, modelo o permisos mal configurados."""


class LLMRequestError(LLMError):
    """La petición no es válida para el modelo."""


class LLMRateLimitError(LLMError):
    """Cuota o límite de peticiones alcanzado."""


class LLMTimeoutError(LLMError):
    """El proveedor no respondió a tiempo."""


class LLMUnavailableError(LLMError):
    """Fallo temporal o interno del proveedor."""


_AUTH_ERROR_CODES = frozenset(
    {
        "AccessDeniedException",
        "UnauthorizedException",
        "UnrecognizedClientException",
        "InvalidSignatureException",
        "ExpiredTokenException",
    }
)


def _translate_client_error(error: ClientError) -> LLMError:
    details = error.response.get("Error", {})
    code = details.get("Code", "desconocido")
    message = details.get("Message", "sin detalle")

    if code in _AUTH_ERROR_CODES:
        return LLMConfigurationError(
            f"Bedrock rechazó las credenciales o permisos ({code}): {message}"
        )
    if code == "ResourceNotFoundException":
        return LLMConfigurationError(f"Modelo o recurso no encontrado: {message}")
    if code in {"ValidationException", "SerializationException"}:
        return LLMRequestError(f"Bedrock rechazó la petición: {message}")
    if code in {
        "ThrottlingException",
        "TooManyRequestsException",
        "ServiceQuotaExceededException",
    }:
        return LLMRateLimitError(f"Bedrock limitó la petición ({code}): {message}")
    if code == "ModelTimeoutException":
        return LLMTimeoutError("Bedrock agotó el tiempo de respuesta")
    if code in {
        "ModelNotReadyException",
        "ServiceUnavailableException",
        "InternalServerException",
    }:
        return LLMUnavailableError(f"Bedrock no está disponible ({code}): {message}")

    return LLMUnavailableError(
        f"Error de Bedrock no reconocido ({code}): {message}"
    )


@dataclass(frozen=True)
class LLMResult:
    reply: str
    model: str
    usage: TokensUsage | None


class LLMService(Protocol):
    def chat(
        self,
        message: str,
        system: str | None,
        temperature: float | None,
        max_tokens: int,
    ) -> LLMResult: ...


class BedrockLLMService(LLMService):

    def __init__(self, settings: BedrockSettings) -> None:

        self._settings = settings
        self._client = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.aws_region,
            config=Config(
                connect_timeout=settings.timeout_s,
                read_timeout=settings.timeout_s,
                retries={"max_attempts": 0, "mode": "standard"},
            ),
        )

    def chat(self, message, system, temperature, max_tokens) -> LLMResult:

        request = {
            "modelId": self._settings.model_id,
            "messages": [{"role": "user", "content": [{"text": message}]}],
            "inferenceConfig": {
                "maxTokens": min(
                    max_tokens or self._settings.max_tokens,
                    self._settings.max_tokens,
                ),
                "temperature": temperature if temperature is not None else 0.4,
            },
        }

        if system:
            request["system"] = [{"text": system}]

        try:
            response = self._client.converse(**request)
        except ClientError as error:
            logger.warning("Bedrock devolvió un error: %s", error)
            raise _translate_client_error(error) from error
        except (NoCredentialsError, PartialCredentialsError) as error:
            logger.exception("Faltan credenciales de AWS")
            raise LLMConfigurationError(
                "No hay credenciales de AWS disponibles"
            ) from error
        except (ConnectTimeoutError, ReadTimeoutError, ConnectionClosedError) as error:
            logger.warning("Tiempo de espera agotado con Bedrock: %s", error)
            raise LLMTimeoutError(
                "Tiempo de espera agotado al hablar con Bedrock"
            ) from error
        except EndpointConnectionError as error:
            logger.warning("No se pudo conectar con Bedrock: %s", error)
            raise LLMUnavailableError(
                "No se pudo conectar con el endpoint de Bedrock"
            ) from error
        except Exception as error:
            logger.exception("Error inesperado al llamar a Bedrock")
            raise LLMError("Error inesperado del proveedor") from error

        usage_raw = response.get("usage")
        usage = (
            TokensUsage(
                prompt_tokens=usage_raw.get("inputTokens", 0),
                completion_tokens=usage_raw.get("outputTokens", 0),
                total_tokens=usage_raw.get("totalTokens"),
            )
            if usage_raw
            else None
        )

        output = response.get("output", {}).get("message", {})
        blocks = output.get("content", [])
        text = "".join(block.get("text", "") for block in blocks)

        return LLMResult(
            reply=text,
            model=self._settings.model_id,
            usage=usage,
        )
