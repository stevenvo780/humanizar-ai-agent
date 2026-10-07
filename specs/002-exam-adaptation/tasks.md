# Tasks: Softop FAQ Bot

- [x] T001 Leer el ZIP (brief DOCX y `rag-test-base.zip`) sin ejecutar nada; registrar requisitos y entradas.
- [x] T002 Escribir spec.md con objetivo, criterios, matriz y decisiones del brief real.
- [x] T003 Escribir plan.md y la estructura mínima sobre el repositorio base (`softop-rag/`).
- [x] T004 [P] Recuperación vectorial en memoria en `softop-rag/base/rag.py` (TF-IDF numpy; embeddings OpenAI opcionales).
- [x] T005 [P] Prompt restrictivo y proveedor LLM en `softop-rag/base/llm.py`.
- [x] T006 Endpoint `POST /preguntar` en `softop-rag/base/app.py` ("no encuentro" sin LLM si no hay contexto; 422/503).
- [x] T007 Pruebas en `softop-rag/tests/test_preguntar.py` (12, sin llamadas de pago) y ejecución en `make check`.
- [x] T008 Verificación real con Claude Haiku (devolución, precio ausente, fuera de dominio, inyección) documentada en `softop-rag/README.md`.
- [x] T009 README con ejecución, flujo RAG, decisiones y siguientes pasos; publicar en GitHub.
