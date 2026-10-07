# Recetas rápidas para la prueba técnica

Escenario más probable: un backend pequeño que **recibe una petición, consulta una base
vectorial de contexto, llama a un modelo y responde** (a veces consumiendo además un endpoint
externo). Estas recetas usan piezas que ya existen y fueron **verificadas el 2026-10-07**.

| Comprobación (2026-10-07) | Resultado |
| --- | --- |
| Clave Anthropic local (`claude-sonnet-5-5`) | Respuesta real en 1,3 s |
| `POST /api/ask` real (FastEmbed + Qdrant local + Haiku, corpus Humanizar) | Respuesta citada `[S1]` en 3,8 s; dato ausente admitido |
| Qdrant como servidor (`QDRANT_URL`, imagen `qdrant/qdrant` en caché) | Ingesta y búsqueda semántica correctas |
| Imágenes Docker del stack (`docker compose build`) | Construidas y en caché (2 min) |
| Receta de API externa (abajo) | 5 pruebas en verde en un worktree aislado |

## R1 — Endpoint RAG: pregunta → base vectorial → modelo (ya implementado)

`POST /api/ask` (`backend/app/api/routes/ask.py`, pruebas en `backend/tests/api/test_ask.py`):
recupera `top_k` fragmentos con `KnowledgeStore.search`, los numera `[S1]…`, llama a Claude con
un system prompt de "sólo contexto, cita y admite lo que falte" y devuelve
`{answer, sources, model}`. En modo demo responde extractivo sin llamar al modelo; los errores
del proveedor salen como 503 `{detail, code}`. Requiere sesión (honra `AUTH_ENABLED`).

Adaptarlo al brief (2–5 min): renombrar ruta/campos en `AskRequest`/`AskResponse`, ajustar
`SYSTEM`, `top_k` o el formato de respuesta y actualizar `test_ask.py`, `docs/API_CONTRACT.md`
y `docs/openapi.json` (generarlo con `create_app().openapi()`).

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/login -H 'content-type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | python3 -c 'import json,sys;print(json.load(sys.stdin)["access_token"])')
curl -s -X POST localhost:8000/api/ask -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' -d '{"question":"¿Qué ofrece la empresa?","top_k":4}'
```

Cargar el contexto: `KNOWLEDGE_DIR=knowledge/<empresa>` con un `DATA_DIR` nuevo, o subir
TXT/MD/PDF/DOCX/CSV/JSON/ZIP en Documentación (admin) o con `POST /api/documents`.

## R2 — Consumir un endpoint externo como herramienta del agente (verificada, no incluida)

1. `backend/app/core/settings.py`: `external_api_url: str = ""` (variable `EXTERNAL_API_URL`).
2. `backend/app/tools/definitions.py`, dentro de la tupla `DEFINITIONS`:

```python
    ToolDefinition(
        "external_lookup",
        "Consulta un recurso por identificador en la API externa configurada.",
        {"identifier": text(80, "identificador")},
    ),
```

3. `backend/app/tools/handlers/external.py`:

```python
"""Example external REST lookup used as an agent tool (bounded, validated, no secrets out)."""

import json
from urllib.parse import quote

from app.tools.handlers.base import ToolContext, ToolOutput


async def external_lookup(context: ToolContext) -> ToolOutput:
    base = context.settings.external_api_url.rstrip("/")
    if not base:
        return ToolOutput(json.dumps({"error": "EXTERNAL_API_URL no configurada."}), failed=True)
    identifier = quote(str(context.arguments["identifier"]), safe="")
    response = await context.http.get(f"{base}/items/{identifier}")
    if response.status_code == 404:
        return ToolOutput(json.dumps({"found": False, "identifier": identifier}))
    response.raise_for_status()  # other HTTP errors become a safe tool error trace
    return ToolOutput(json.dumps({"found": True, "item": response.json()}, ensure_ascii=False))
```

4. Registrar `"external_lookup": external_lookup` en `HANDLERS` (`handlers/__init__.py`).
   El registro valida argumentos, redacta, trunca, mide y convierte `httpx.HTTPError` en un
   error seguro; el agente muestra el resultado aunque no haya citas.
5. Prueba (en `backend/tests/api/test_ask.py` o `tests/tools/`), con `httpx.MockTransport`:

```python
async def test_external_lookup_tool(settings: Settings, store: KnowledgeStore) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/items/A-1":
            return httpx.Response(200, json={"id": "A-1", "status": "enviado"})
        if request.url.path == "/items/BOOM":
            return httpx.Response(500)
        return httpx.Response(404)

    configured = settings.model_copy(update={"external_api_url": "https://api.example.test"})
    registry = ToolRegistry(configured, store)
    await registry.http.aclose()
    registry.http = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        found = (await registry.run("external_lookup", {"identifier": "A-1"})).trace
        missing = (await registry.run("external_lookup", {"identifier": "Z-9"})).trace
        broken = (await registry.run("external_lookup", {"identifier": "BOOM"})).trace
    finally:
        await registry.close()
    assert found.status == "completed" and json.loads(found.output)["item"]["status"] == "enviado"
    assert json.loads(missing.output) == {"found": False, "identifier": "Z-9"}
    assert broken.status == "error"
```

Para llamarlo directamente desde un endpoint (sin agente), usar `httpx.AsyncClient(timeout=…)`
con `raise_for_status()` y validar la respuesta con un modelo Pydantic.

## R3 — Otro proveedor de modelo (no verificado; ~5 min)

`uv add --project backend openai`; añadir `openai_api_key: SecretStr` en `Settings` y, en el
endpoint, `AsyncOpenAI(api_key=…).chat.completions.create(model=…, messages=[system, user])`.
El ciclo de herramientas está tipado para Anthropic (`agent/provider.py`): para un endpoint
simple basta la llamada directa; no caer nunca a demo si el proveedor falla.

## R4 — Otra base vectorial

- Qdrant servidor: `QDRANT_URL=http://localhost:6333` (+ `QDRANT_API_KEY`); `docker run -p
  6333:6333 qdrant/qdrant` (imagen en caché). En producción quitar `QDRANT_URL: ""` de
  `compose.production.yaml`.
- Chroma/pgvector/otra: sustituir los 5 puntos de `self._vectors` en `knowledge/store.py`
  (crear colección, upsert, borrar, consultar) manteniendo SQLite como fuente de verdad.
- Cambiar embeddings: `EMBEDDING_PROVIDER` (`fastembed`/`hash`) y un `DATA_DIR` nuevo.

## R5 — Entrega integral

1. `make check` y los escenarios de `specs/002-exam-adaptation/quickstart.md`.
2. README: cómo arrancar (`make setup && make dev` o `make docker`), variables sin valores,
   ejemplo `curl`, decisiones y pruebas ejecutadas.
3. `make package` si piden ZIP (`zipinfo -1` para revisar); commit, push a `dev` (Vercel) y
   `deploy-vps.py check/up/status` tras el backup (docs/OPERATIONS.md).
