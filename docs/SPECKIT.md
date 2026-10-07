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
| `/speckit-taskstoissues` | Crear issues solo cuando se solicite publicar en GitHub |

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

Abrir Claude Code para la prueba real:

```bash
SPECIFY_FEATURE=002-exam-adaptation \
SPECIFY_FEATURE_DIRECTORY=specs/002-exam-adaptation \
make claude
```

Lee primero el material importado con `--no-upload`. Ejecuta `/speckit-specify`
indicando la ruta y los requisitos reales; después `/speckit-clarify` si faltan
decisiones, `/speckit-plan`, `/speckit-tasks`, `/speckit-analyze` y `/speckit-implement`.
El plan inicial de `002` explica el orden, pero no sustituye el análisis del enunciado.
No marques una tarea como terminada hasta contar con implementación y evidencia.

Para cambiar manualmente el contexto en tu shell:

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
T017 registra el lector pendiente en el VPS; T018, la copia y preparación en Fedora;
T026, la publicación y comprobación del backend auditado. El listado canónico y
el estado de las correcciones están en `specs/001-company-agent/tasks.md`.
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

Fuentes: [Spec Kit](https://github.com/github/spec-kit) y
[skills en Claude Code](https://code.claude.com/docs/en/skills).
