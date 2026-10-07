---
description: "Tareas pendientes de adaptación a la prueba real (002)"
---

# Tasks: Adaptación a la prueba real

**Input**: Documentos de diseño de `specs/002-exam-adaptation/`

**Prerequisites**: plan.md (lo crea `/speckit-plan`), spec.md (lo reescribe `/speckit-specify` desde el brief); referencias de base: research.md, quickstart.md, checklists/requirements.md

**Estado**: pendiente del brief. Ninguna tarea está hecha; estas tareas preparan el
análisis y no describen ni acreditan un examen resuelto. `/speckit-tasks` sustituirá
este archivo por las tareas reales (T004).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias)
- **[Story]**: historia del spec a la que pertenece (US1, US2…)

## Phase 1: Setup (material del brief)

- [ ] T001 Leer ZIP/enunciado y rúbrica de `prueba-tecnica/` importados sin ejecutar (`material/import-*/manifest.json`); registrar restricciones y datos de entrada

## Phase 2: Foundational (artefactos Spec Kit)

- [ ] T002 Completar `specs/002-exam-adaptation/spec.md` con requisitos y aceptación reales, sin suposiciones (`/speckit-specify`, `/speckit-clarify` si hace falta)
- [ ] T003 Completar `specs/002-exam-adaptation/plan.md` desde la plantilla oficial y la matriz de cambios mínimos de `research.md` (`/speckit-plan`)
- [ ] T004 Regenerar `specs/002-exam-adaptation/tasks.md` con archivos y verificaciones trazables al brief (`/speckit-tasks`, `/speckit-analyze`)

## Phase 3: Implementación

- [ ] T005 Implementar los cambios definidos por las tareas reales (`/speckit-implement`)

## Phase 4: Verificación

- [ ] T006 Verificar la aceptación exigida con `specs/002-exam-adaptation/quickstart.md` y `make check`; documentar resultados y pendientes

## Dependencies & Execution Order

T001 → T002 → T003 → T004 → T005 → T006, en secuencia. No hay tareas [P] hasta
conocer el brief.
