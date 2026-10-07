# Feature Specification: Softop FAQ Bot — POST /preguntar con RAG

**Feature Branch**: `002-exam-adaptation` · **Created**: 2026-10-07 · **Status**: Implemented
**Input**: `prueba-tecnica/Prueba Tecnica Ing IA.zip` → `Pruebas Tecnica Ing IA.docx` (brief) y
`rag-test-base.zip` (repositorio base: `base/app.py` con TODO, `base/faq.json`, `requirements.txt`).

## Goal

Un endpoint FastAPI `POST /preguntar` que responde preguntas del usuario basándose únicamente en
`faq.json` mediante RAG, entregado sobre el repositorio base (`softop-rag/`).

## User Scenarios & Testing

### User Story 1 — Preguntar sobre el software (P1)

Un usuario envía `{"pregunta": "..."}` y recibe `{"respuesta": "..."}` generada sólo con las FAQ.

**Acceptance Scenarios**:
1. **Given** la FAQ de devoluciones, **When** se pregunta "¿Cómo hago una devolución?", **Then** la respuesta describe *Ventas > Devoluciones* (FAQ 8).
2. **Given** una pregunta cuyo dato no está en las FAQ (precio de un examen), **Then** la respuesta indica que no se encuentra la información.
3. **Given** una pregunta ajena o un intento de inyección, **Then** se responde "No encuentro esa información…" sin llamar al modelo.

### Edge Cases
- Payload sin `pregunta` o vacío → 422. Proveedor no configurado o caído → 503 sin detalles internos.

## Requirements

- **FR-001**: Ruta `POST /preguntar` en FastAPI. Entrada `{"pregunta": str}`; salida `{"respuesta": str}`.
- **FR-002**: Recuperar los fragmentos relevantes del documento de FAQ.
- **FR-003**: Formatear el prompt inyectando el contexto recuperado y restringiendo al modelo a responder sólo con esa información.
- **FR-004**: Retornar la respuesta del LLM.

## Success Criteria
- **SC-001**: Las preguntas de prueba recuperan la FAQ correcta en primer lugar (tests).
- **SC-002**: Respuestas reales del LLM ceñidas al documento; dato ausente admitido (evidencia en `softop-rag/README.md`).

## Matrix (requirement → file → change → check)

| Req | Archivo | Cambio | Comprobación |
| --- | --- | --- | --- |
| FR-001 | `softop-rag/base/app.py` | Endpoint + modelos Pydantic | `tests/test_preguntar.py`, curl |
| FR-002 | `softop-rag/base/rag.py` | Índice vectorial numpy (TF-IDF / embeddings OpenAI) + coseno | tests de recuperación |
| FR-003 | `softop-rag/base/llm.py` | `SYSTEM_PROMPT` restrictivo + `build_prompt` con `[FAQ id]` | test del prompt inyectado |
| FR-004 | `softop-rag/base/llm.py` | Claude Haiku u OpenAI según clave, `temperature=0` | prueba real con Haiku |

## Decisions
Proveedor: Claude Haiku (clave verificada) u OpenAI (dependencia de la base). Almacenamiento:
índice en memoria (10 FAQs). Interfaz: sólo el endpoint pedido. Entrega: `softop-rag/` en GitHub.
Sin autenticación (no requerida). Detalle y trade-offs en `softop-rag/README.md`.
