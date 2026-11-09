# API de chat con FastAPI y Amazon Bedrock

API mínima que recibe un mensaje y lo envía a un modelo de Amazon Bedrock mediante la
Converse API, devolviendo el texto y el consumo de tokens.

## Requisitos

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- Credenciales de AWS con permiso `bedrock:InvokeModel`
- El modelo configurado habilitado en la región de Bedrock

## Instalación

```bash
uv sync
```

## Configuración

Crea un archivo `.env` en la raíz a partir de `.env.example`. El `.env` no se versiona.

| Variable | Ejemplo | Descripción |
|---|---|---|
| `BEDROCK__AWS_REGION` | `us-east-1` | Región del cliente `bedrock-runtime` |
| `BEDROCK__MODEL_ID` | `amazon.nova-lite-v1:0` | Identificador del modelo |
| `BEDROCK__MAX_TOKENS` | `1024` | Tope de tokens de salida (0–4200) |
| `BEDROCK__TIMEOUT_S` | `30` | Timeout de conexión y lectura en segundos (0–60) |

El doble guion bajo (`__`) es el delimitador de settings anidados de `pydantic-settings`:
separa el bloque `bedrock` del nombre del campo.

La configuración se valida al arrancar. Si falta una variable o está fuera de rango, el
servidor no inicia y muestra el error de validación.

## Ejecución

```bash
uv run uvicorn app.main:app --reload
```

Documentación interactiva: <http://127.0.0.1:8000/docs>

## Endpoints

### `GET /`

```json
{ "mensaje": "Bienvenidos a esta prueba" }
```

### `GET /health`

```json
{ "status": "ok" }
```

### `POST /api/v1/chat`

Petición:

```json
{
  "message": "Hola",
  "system": null,
  "temperature": 0.7,
  "max_tokens": 4200
}
```

- `message`: obligatorio, entre 1 y 4000 caracteres.
- `system`: opcional, instrucción de comportamiento (1–4000 caracteres).
- `temperature`: opcional, entre 0.0 y 2.0. Si se omite, se usa `0.4`.
- `max_tokens`: opcional, por defecto `4200`; se recorta al máximo configurado.

Respuesta:

```json
{
  "reply": "Hola, ¿en qué puedo ayudarte?",
  "model": "amazon.nova-lite-v1:0",
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 8,
    "total_tokens": 20
  }
}
```

Los valores de `usage` son ilustrativos.

## Errores

Los fallos del proveedor se traducen a HTTP en el router:

| Error interno | HTTP | Causa |
|---|---|---|
| `LLMRequestError` | 400 | Bedrock rechaza la petición |
| `LLMRateLimitError` | 429 | Throttling o cuota agotada |
| `LLMConfigurationError` | 500 | Credenciales, permisos o modelo inexistente |
| `LLMUnavailableError` | 503 | Servicio no disponible o sin conexión |
| `LLMTimeoutError` | 504 | Timeout de conexión, lectura o del modelo |
| `LLMError` | 502 | Fallo no clasificado |

Un body inválido responde `422` antes de ejecutar el endpoint. El detalle completo de cada
fallo queda en el log del servidor.

## Estructura

```text
app/
├── main.py              # App FastAPI y lifespan
├── config.py            # Settings desde .env
├── schemas.py           # Contratos de entrada y salida
├── routers/
│   └── chat.py          # Endpoint y mapeo de errores a HTTP
└── services/
    └── bedrock.py       # Cliente Bedrock y errores de dominio
```

## Seguridad

- No escribas claves de AWS en el código ni en el repositorio. Usa el perfil local de AWS
  o, en EC2, un rol de instancia.
- Mantén `.env` fuera de git; ya está en `.gitignore`.

## Pendientes

- Tests automatizados y CI con GitHub Actions.
- Contenedor Docker y despliegue en EC2.
