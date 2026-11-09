from fastapi import APIRouter, Depends, HTTPException

from app.config import BedrockSettings, get_bedrock_settings
from app.schemas import InputMessage, ResponseMessage
from app.services.bedrock import (
    BedrockLLMService,
    LLMConfigurationError,
    LLMError,
    LLMRateLimitError,
    LLMRequestError,
    LLMTimeoutError,
    LLMUnavailableError,
)

chat_router = APIRouter(prefix="/chat", tags=["Chat"])

_ERROR_STATUS = (
    (LLMRequestError, 400),
    (LLMRateLimitError, 429),
    (LLMTimeoutError, 504),
    (LLMUnavailableError, 503),
    (LLMConfigurationError, 500),
)


def get_llm_service(
    settings: BedrockSettings = Depends(get_bedrock_settings),
) -> BedrockLLMService:
    return BedrockLLMService(settings)


def _http_error(error: LLMError) -> HTTPException:
    status_code = next(
        (status for kind, status in _ERROR_STATUS if isinstance(error, kind)),
        502,
    )
    return HTTPException(status_code=status_code, detail=str(error))


@chat_router.post("", response_model=ResponseMessage)
def chat_converse(
    request: InputMessage,
    service: BedrockLLMService = Depends(get_llm_service),
) -> ResponseMessage:

    try:
        result = service.chat(
            message=request.message,
            system=request.system,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except LLMError as error:
        raise _http_error(error) from error

    return ResponseMessage(
        reply=result.reply,
        model=result.model,
        usage=result.usage,
    )
