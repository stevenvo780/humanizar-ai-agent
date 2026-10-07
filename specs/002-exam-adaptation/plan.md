# Implementation Plan: Softop FAQ Bot

**Spec**: [spec.md](spec.md) · **Date**: 2026-10-07

## Summary
Completar el repositorio base entregado (`softop-rag/`) con un pipeline RAG mínimo y explicable:
recuperación vectorial en memoria con numpy → prompt restrictivo → LLM → `{"respuesta"}`.

## Technical Context
Python 3.12 · FastAPI 0.115 · Pydantic 2.9 · numpy 1.26 · openai 1.51 (+ httpx 0.27.2 fijado)
· anthropic · pytest. Sin base de datos: 10 FAQs en memoria. Objetivo: <3 s por respuesta.

## Constitution Check
Respuestas fundamentadas sólo en el documento (I), sin secretos en código ni logs (II), modelo
y fallos visibles (III/V), límites de payload y tiempo de espera del proveedor (IV). PASS.

## Structure
`softop-rag/base/{app.py, rag.py, llm.py, faq.json}`, `softop-rag/tests/test_preguntar.py`,
`softop-rag/README.md`. La plataforma Lumen no cambia; su `POST /api/ask` es la versión completa
(Qdrant + FastEmbed) descrita en `docs/EXAM_RECIPES.md`.
