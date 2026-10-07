# Spec Kit 1.0.7 en este proyecto

El scaffolding procede de Specify CLI 1.0.7, con integración `claude`, scripts Bash
y skills invocables. Está incluido en Git: no hace falta regenerarlo en cada laptop.
La versión de la CLI de administración se fija con `make speckit`.

| Comando en Claude Code | Propósito |
| --- | --- |
| `/speckit-constitution` | Revisar principios del proyecto cuando el brief lo requiera |
| `/speckit-specify` | Convertir requisitos reales en una especificación |
| `/speckit-clarify` | Resolver ambigüedades concretas |
| `/speckit-plan` | Definir arquitectura y cambios mínimos |
| `/speckit-checklist` | Revisar la calidad de los requisitos |
| `/speckit-tasks` | Generar tareas verificables y ordenadas |
| `/speckit-analyze` | Revisar coherencia sin modificar los artefactos |
| `/speckit-implement` | Implementar y comprobar las tareas autorizadas |
| `/speckit-converge` | Registrar diferencias que todavía faltan por implementar |
| `/speckit-taskstoissues` | Publicar las tareas como issues de GitHub. Ejecutado para `001` el 2026-10-07: [30 issues](https://github.com/stevenvo780/humanizar-ai-agent/issues?q=label%3Aspec-kit-001) cerrados como completados. Para `002` se ejecuta después de `/speckit-tasks`, cuando exista `plan.md` |

Los nombres utilizan guiones: `/speckit-specify`, no `/speckit.specify`.
Los nombres con puntos en el workflow describen IDs internos de Spec Kit.
Los hooks de extensiones son opcionales; este proyecto no instala extensiones
que publiquen o creen ramas automáticamente.

## Elegir la feature correcta

`001-company-agent` describe la base Humanizar implementada. `002-exam-adaptation`
reserva la adaptación a un enunciado todavía desconocido: todas sus tareas están
pendientes. Las features no dependen del nombre de la rama Git en la versión 1.0.7.

La base también incluye PostgreSQL opcional y el despliegue Vercel/VPS descrito en
[DEPLOYMENT.md](DEPLOYMENT.md). Para presentar desde otro equipo, preparar primero
la copia de [FEDORA.md](FEDORA.md). Esas capacidades están disponibles para adaptar
el brief; no cambian el estado pendiente de `002` ni requieren reinstalar Spec Kit.
La configuración privada y `.specify/feature.json` se crean localmente, sin incluir
secretos ni rutas absolutas en el repositorio público.

`make setup` crea, si falta, `.specify/feature.json` con la ruta relativa de `001`.
Ese archivo es estado local ignorado por el scaffolding oficial. Al cambiar feature,
el CLI actualiza el puntero; no se distribuyen rutas absolutas de una laptop.
`SPECIFY_FEATURE` solo fija el identificador: no selecciona por sí solo el directorio.

Comprobar la base explícitamente:

```bash
make speckit-check
```

### Feature 002 el día del examen

`002` sólo contiene esqueletos y referencias de la base, etiquetadas como tales:
`spec.md` y `tasks.md` (T001–T006 pendientes), `research.md` (tipo de requisito →
implementación actual → archivos → comprobación), `quickstart.md` (escenarios de
aceptación Q0–Q10 con comandos) y `checklists/requirements.md` (calidad del spec).
No hay `plan.md` a propósito: `setup-plan.sh` omite la plantilla oficial si el archivo
existe. Hasta `/speckit-plan`, los checks que exigen plan fallan con
"Run /speckit-plan first": es el orden esperado.

1. Copiar el material en `prueba-tecnica/` y abrir `make exam-claude`, que fija
   `SPECIFY_FEATURE` y `SPECIFY_FEATURE_DIRECTORY` para `002`.
2. `/speckit-specify SPECIFY_FEATURE_DIRECTORY=specs/002-exam-adaptation. Requisitos del brief en prueba-tecnica/ (importado con --no-upload); no crear 003.`
3. `/speckit-clarify` sólo si quedan `NEEDS CLARIFICATION`.
4. `/speckit-plan Conserva el mapa de research.md y Q0–Q10 de quickstart.md; añade las decisiones y criterios del brief.`
5. `/speckit-tasks` y después `/speckit-analyze` (sólo lectura).
6. `/speckit-implement`: usa `checklists/` como puerta y termina con `quickstart.md` (T006).

El atajo `/prueba-tecnica` escribe `spec.md` y `tasks.md` directamente: ejecutar
`/speckit-plan` antes de `/speckit-analyze` o `/speckit-implement`, que exigen `plan.md`.
No marques una tarea como terminada hasta contar con implementación y evidencia.
Ensayo del 2026-10-07 en un clon desechable: las cuatro plantillas se resuelven sin
cambios, `setup-plan.sh` copia la oficial y `setup-tasks.sh` lista `research.md` y `quickstart.md`.

Sin `make exam-claude`, fijar el contexto en tu shell:

```bash
export SPECIFY_FEATURE=002-exam-adaptation
export SPECIFY_FEATURE_DIRECTORY=specs/002-exam-adaptation
bash .specify/scripts/bash/check-prerequisites.sh --json --require-spec --require-tasks --include-tasks
```

Ese comando comprueba existencia y rutas, no demuestra que el examen esté resuelto.
Mantén `001` como referencia y escribe los requisitos de la prueba en `002`.
La validación de prerequisitos es de sólo lectura, también con selectores explícitos:
no crea ni cambia `.specify/feature.json`. Crear una feature o ejecutar su setup
mantiene la selección explícita correspondiente. Un conjunto de regresión comprueba
que validar `002` conserva el puntero de `001` y rechaza tareas inexistentes.

## Auditoría de la base

La revisión de coherencia encontró cobertura cualitativa de los catorce requisitos
mediante las tareas de implementación, sin conflictos críticos de constitución. Los diez
requisitos originales se complementan con PostgreSQL, despliegue Vercel/Docker,
gestión de clientes y legibilidad. La publicación de la nueva API de clientes tiene
su propia tarea pendiente: T015, hasta recuperar acceso SSH y comprobar producción.
T017 registra el lector pendiente en el VPS y T026, la publicación y comprobación del
backend auditado. T018 (copia y preparación en el portátil Fedora) ya está cerrada.
El listado canónico y el estado de las correcciones están en
`specs/001-company-agent/tasks.md`.
Se corrigieron permisos de ingesta, descripción del embedding por defecto y las
referencias a la persistencia del historial. La matriz FR/T de `001` hace explícita
esa cobertura; la evidencia de ejecución vive en [VALIDATION.md](VALIDATION.md).

La CLI local informó versión 1.0.7 y `specify check` terminó correctamente.
Se comprobó también la instalación fijada desde [PyPI](https://pypi.org/project/specify-cli/1.0.7/)
en un directorio de herramientas aislado.
Los dos manifiestos conservan los hashes originales de los 22 scripts/templates/skills.
Se aplica una única corrección local a `check-prerequisites.sh` para que la inspección
no persista el puntero. `.specify/local-overrides.json` registra el hash original,
el hash corregido y su motivo; una prueba comprueba ambos manifiestos y esa excepción.
los diez skills declaran nombres válidos y seis referencias de ejecución locales
resuelven. Las referencias `metadata.source: templates/commands/...` indican
procedencia upstream, no archivos adicionales que falten en el clon.
La sintaxis de los seis scripts Bash se verificó. Los templates se resuelven
mediante `.specify/scripts/bash/resolve-template.sh`, con fallback local cuando
no hay presets. La auditoría no ejecutó un workflow de implementación ni modelos
de pago para fingir un resultado del examen.

El 2026-10-07 se ejecutaron sobre `001`, con selección explícita y sin cambiar el
puntero, `/speckit-clarify` (sección Clarifications de `spec.md`, respondida desde el
código), `/speckit-checklist` (`checklists/requirements-quality.md`), `/speckit-analyze`
(sin hallazgos críticos; deriva de rutas y documentación corregida) y `/speckit-converge`
(fase 2 de `tasks.md`: T027–T030, pruebas de inyección, fallos del proveedor y ZIP
cifrado, más la trazabilidad del tooling de examen).

Fuentes: [Spec Kit](https://github.com/github/spec-kit) y
[skills en Claude Code](https://code.claude.com/docs/en/skills).
