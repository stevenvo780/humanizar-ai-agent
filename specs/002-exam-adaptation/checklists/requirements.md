# Specification Quality Checklist: Adaptación a la prueba real

**Purpose**: Validar la completitud y calidad de `spec.md` antes de `/speckit-clarify` o `/speckit-plan`
**Created**: 2026-10-07
**Feature**: [spec.md](../spec.md)

> **Referencia de la base — no son requisitos del examen.** Todos los ítems siguen sin
> marcar: el spec del brief todavía no existe. `/speckit-specify` y `/speckit-clarify`
> mantienen este archivo (lista integrada de Spec Kit); al regenerarlo, conservar la
> sección "Trazabilidad con el brief". `/speckit-implement` lo lee como puerta y no
> lo modifica.

## Content Quality

- [ ] CHK001 No implementation details (languages, frameworks, APIs) salvo restricciones que el brief imponga, citadas como tales en Assumptions
- [ ] CHK002 Focused on user value and business needs
- [ ] CHK003 Written for non-technical stakeholders
- [ ] CHK004 All mandatory sections completed

## Requirement Completeness

- [ ] CHK005 No [NEEDS CLARIFICATION] markers remain
- [ ] CHK006 Requirements are testable and unambiguous
- [ ] CHK007 Success criteria are measurable
- [ ] CHK008 Success criteria are technology-agnostic (no implementation details)
- [ ] CHK009 All acceptance scenarios are defined
- [ ] CHK010 Edge cases are identified
- [ ] CHK011 Scope is clearly bounded
- [ ] CHK012 Dependencies and assumptions identified

## Feature Readiness

- [ ] CHK013 All functional requirements have clear acceptance criteria
- [ ] CHK014 User scenarios cover primary flows
- [ ] CHK015 Feature meets measurable outcomes defined in Success Criteria
- [ ] CHK016 No implementation details leak into specification

## Trazabilidad con el brief

- [ ] CHK017 Cada FR/SC cita o parafrasea una frase concreta del enunciado o la rúbrica; ninguno procede sólo de `001`
- [ ] CHK018 Cada criterio de evaluación del brief tiene un SC y un escenario en `quickstart.md` (Q7)
- [ ] CHK019 Están decididos y documentados proveedor/modelo, almacenamiento, herramientas, interfaces y formato de entrega
- [ ] CHK020 Los hechos de empresa (corpus) están separados de los requisitos técnicos; ninguna consigna o rúbrica va al conocimiento del agente
- [ ] CHK021 Se conservan fuentes visibles, admisión de datos ausentes, confirmación de escrituras, propiedad por usuario y login, o el brief exige explícitamente cambiarlos
- [ ] CHK022 Ningún requisito necesita secretos en código, frontend o documentación

## Notes

- Los ítems sin marcar requieren actualizar el spec antes de `/speckit-clarify` o `/speckit-plan`.
- Marcar `[x]` sólo tras revisar el spec escrito a partir del brief real.
