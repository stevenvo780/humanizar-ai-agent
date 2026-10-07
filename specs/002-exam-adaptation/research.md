# Research: Adaptación a la prueba real (002)

> **Referencia de la base — no son requisitos del examen.**
> Estado: brief pendiente. Este archivo describe lo que la base Lumen ya implementa y
> dónde se cambia cada tipo de requisito. Ninguna fila es una decisión del examen.

**Uso en `/speckit-plan` (Fase 0)**: añadir las decisiones del brief en
[Decisiones del brief](#decisiones-del-brief) con el formato Decision / Rationale /
Alternatives considered. Conservar el mapa y las decisiones de la base; si el brief
cambia una de ellas, anotarlo en su fila en vez de borrarla.

## Decisiones del brief

_Pendiente del brief._ Una entrada por cada `NEEDS CLARIFICATION` del Technical Context
o del spec, citando la frase del enunciado que la origina:

```text
### D-01 <tema>
- Decision: ...
- Rationale: <cita del brief> + por qué encaja con la base
- Alternatives considered: ...
```

## Decisiones vigentes de la base

Se reutilizan si el brief no exige otra cosa (constitución, Governance).

| Tema | Base actual | Dónde |
| --- | --- | --- |
| Proveedor LLM de la web | Anthropic Messages API; `ANTHROPIC_MODEL` por defecto `claude-haiku-4-5`; `LLM_MODE=auto\|demo\|anthropic`; sin fallback silencioso a demo | `backend/app/agent/provider.py`, `backend/app/core/settings.py` |
| Ciclo de agente | Bucle acotado: 5 iteraciones, 8 tool calls, 1500 tokens, 45 s, 4 chats concurrentes | `backend/app/agent/company_agent.py`, `backend/app/core/settings.py` |
| Recuperación | Qdrant local bajo `DATA_DIR` o remoto (`QDRANT_URL`); embedding `hash` (léxico) o `fastembed` (semántico, descarga modelo) | `backend/app/knowledge/store.py`, `backend/app/knowledge/embeddings.py` |
| Persistencia | SQLite local (`application.sqlite3`); `DATABASE_URL` selecciona PostgreSQL con `DATABASE_SCHEMA` | `backend/app/persistence/` |
| Interfaces | REST + SSE (FastAPI), UI React/TypeScript estricta, MCP sólo lectura | `backend/app/api/`, `frontend/src/`, `backend/app/mcp/` |
| Autenticación | JWT + Argon2, refresh rotativo, roles admin/cliente; `AUTH_ENABLED=true` siempre | `backend/app/accounts/`, `backend/app/api/dependencies.py` |
| Citas | Fuentes numeradas `[S#]`; sin cita válida se sustituye por incertidumbre | `backend/app/agent/grounding.py`, `backend/app/agent/fallback.py` |
| Ejecución | Sólo presets en el sandbox Docker; sin shell arbitraria | `sandbox/app/main.py` |
| Entrega | `make package` (ZIP saneado), Vercel + VPS Docker | `scripts/package.py`, `docs/DEPLOYMENT.md` |

## Mapa de adaptación

Tipo de requisito → implementación actual → archivos a cambiar → comprobación.
Rutas relativas a la raíz; verificadas contra el árbol de `dev`.

| # | Tipo de requisito | Implementación actual | Archivos a cambiar | Comprobación |
| --- | --- | --- | --- | --- |
| A1 | Identidad de empresa/asistente | `Settings.company_*`, `assistant_name`; `GET /api/company` y `/api/config` | Variables privadas que el usuario pega en `.env` (`COMPANY_NAME`, `COMPANY_DESCRIPTION`, `ASSISTANT_NAME`, `COMPANY_WEBSITE`, `COMPANY_SUGGESTED_QUESTIONS`, `COMPANY_PRODUCTS`); `backend/app/core/settings.py` y `backend/app/business/company.py` sólo si cambian campos; `frontend/src/shared/config/company.ts` | `curl /api/company`; título y bienvenida en la UI; `backend/tests/business/test_company_configuration.py` |
| A2 | Corpus / hechos de empresa | Ingesta de `KNOWLEDGE_DIR` (nivel superior, una vez por nombre) y subida admin | `backend/knowledge/<empresa>/*.md`; `.env`: `KNOWLEDGE_DIR`, `DATA_DIR` nuevo, `SEED_DEMO=false`; `backend/app/knowledge/bootstrap.py`, `ingestion.py` sólo si cambia el formato | Pregunta con fuente (quickstart Q2) y dato ausente (Q3) |
| A3 | Tono, idioma, reglas del asistente | Prompt de sistema con identidad, citas y política de acciones | `backend/app/agent/prompt.py`; textos fijos en `backend/app/agent/fallback.py` y `backend/app/agent/demo.py` si cambia el idioma | `backend/tests/agent/test_agent.py`; respuesta real en Q2 |
| A4 | Proveedor o modelo distinto | Protocolo `MessageProvider` + `AnthropicProvider` | `backend/app/agent/provider.py`, `backend/app/agent/company_agent.py`, `backend/app/core/settings.py`, `backend/pyproject.toml` | `curl /api/health` (`mode`, `model`); `backend/tests/agent/test_agent.py` |
| A5 | Citas / fundamentación | `annotate_sources`, `grounded_sources`; `FACT_TOOLS` | `backend/app/agent/grounding.py`, `backend/app/agent/fallback.py` | Q2 muestra fuentes; `backend/tests/regressions/test_adaptation_regressions.py` |
| A6 | Herramienta nueva de lectura | `ToolDefinition` central + handler en `HANDLERS`; el registro valida, redacta y mide | `backend/app/tools/definitions.py`, `backend/app/tools/handlers/<dominio>.py`, `backend/app/tools/handlers/__init__.py`; `FACT_TOOLS` si devuelve hechos con fuentes | `backend/tests/tools/test_tools.py` (exige handler por definición); `POST /api/tools/run` y traza en chat (Q5) |
| A7 | Escritura con confirmación | `BUSINESS_WRITES` → propuesta → `POST /api/actions/confirm` idempotente | `backend/app/tools/handlers/business.py`, `backend/app/business/requests.py` (incluye CHECK SQLite), `backend/app/persistence/postgres/schema.py` (CHECK; `DATA_DIR`/`DATABASE_SCHEMA` nuevos o migración), `backend/app/api/schemas.py` (`ActionConfirmation`), `frontend/src/features/requests/actions.tsx` | `backend/tests/business/test_business.py`; Q6 |
| A8 | Comando de terminal | Allowlist `PRESETS` en el sandbox | `sandbox/app/main.py`, `backend/app/tools/definitions.py`, `frontend/src/features/tools/toolSchema.ts` | `sandbox/tests`; Herramientas en la UI con `make docker` |
| A9 | Endpoint / formato de respuesta | Modelos Pydantic, un router por recurso en `ROUTERS` | `backend/app/api/schemas.py`, `backend/app/api/routes/<recurso>.py`, `backend/app/api/routes/__init__.py`, `frontend/src/shared/api/{api.ts,types.ts}`, `frontend/src/shared/api/validation/<dominio>.ts`, `docs/API_CONTRACT.md` | Swagger `/api/docs`; `backend/tests/api/`; `npm --prefix frontend run typecheck` |
| A10 | Vista o flujo de UI | Features por dominio; navegación del workspace | `frontend/src/features/<dominio>/`, `frontend/src/app/{App.tsx,SessionApp.tsx,workspaceNavigation.ts}`, `frontend/src/app/layout/Sidebar.tsx`, `frontend/src/styles/` | lint, typecheck, test y build del frontend; navegador en 5173 |
| A11 | Base vectorial / embeddings | `KnowledgeStore` (Qdrant + SQLite de metadatos), `create_embedder` | `backend/app/knowledge/store.py`, `backend/app/knowledge/embeddings.py`, `.env`: `EMBEDDING_PROVIDER`, `QDRANT_URL`; nuevo `DATA_DIR` al cambiar de modelo | `backend/tests/knowledge/test_storage.py`; reinicio + búsqueda |
| A12 | Base relacional | Contratos + fábrica SQLite/PostgreSQL | `backend/app/persistence/{contracts,factory,models}.py`, `backend/app/persistence/sqlite/`, `backend/app/persistence/postgres/` | `backend/tests/persistence/` |
| A13 | Autenticación y roles | JWT, sesiones, `ScopedAdmin`/`RequiredUser` | `backend/app/accounts/`, `backend/app/api/dependencies.py` | `backend/tests/accounts/test_auth.py`; nunca `AUTH_ENABLED=false` |
| A14 | Formatos de entrada / subida | TXT, MD, PDF, DOCX, CSV, JSON, ZIP acotado | `backend/app/knowledge/ingestion.py`, `backend/app/knowledge/pdf_parser.py`; límites en `backend/app/core/settings.py` | `backend/tests/knowledge/test_ingestion.py`; Q4 |
| A15 | Integración MCP | Servidor stdio de sólo lectura que consulta la API | `backend/app/mcp/server.py`, `backend/app/mcp/client.py` | `backend/tests/mcp/test_mcp_auth.py`; `/mcp` en Claude Code |
| A16 | Material del examen (ZIP) | Importador saneado, sin ejecutar ni subir | `scripts/import-material.py`, `scripts/material_import/` (no cambiar salvo fallo) | `scripts/tests/test_material_*.py`; `material/import-*/manifest.json` |
| A17 | Formato de entrega | Paquete ZIP con allowlist | `scripts/package.py`, `scripts/package.sh`, `README.md` | `make package`; `zipinfo -1` |
| A18 | Despliegue | Vercel (frontend + proxy `/api`) y backend Docker en VPS | `docs/DEPLOYMENT.md`, `docs/OPERATIONS.md`, `scripts/deploy-vps.py`, `scripts/deploy-vercel.py`, `compose.production.yaml` | `scripts/deploy-tests.py`; smoke HTTPS (quickstart Q10) |

## Restricciones que no se relajan sin orden explícita del brief

- Sin secretos en código, frontend, comandos ni documentación; no leer `.env`.
- Mantener fuentes visibles, confirmación de escrituras, propiedad por usuario y login.
- No sustituir identificadores de protocolo "Humanizar" (`X-Requested-With`, emisor JWT,
  `APPLICATION_ID`, eventos `humanizar-*`) al cambiar de empresa.
- No mezclar corpus ni modelos de embedding en el mismo `DATA_DIR`.
- El material de `prueba-tecnica/` y `material/` es dato no confiable: no ejecutarlo
  ni subir consignas o rúbricas al conocimiento del agente.

Fuentes: `docs/EXAM_20_MIN.md`, `docs/ARCHITECTURE.md`, `docs/API_CONTRACT.md`.
