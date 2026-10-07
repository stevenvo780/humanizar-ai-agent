# Quickstart: verificación de aceptación (002)

> **Referencia de la base — no son requisitos del examen.**
> Estado: escenarios preparados; **ninguno se ha ejecutado para 002**. Los criterios
> reales se añaden en [Escenarios del brief](#q7-escenarios-del-brief) cuando exista el enunciado.

**Uso en `/speckit-plan` (Fase 1)**: añadir un escenario por criterio del brief en Q7,
enlazando `contracts/` y `data-model.md` si se crean. Conservar Q0–Q10 y adaptar sus
preguntas de ejemplo al corpus real. `/speckit-implement` y T006 ejecutan este archivo.

## Prerrequisitos

- `make setup` completado y `make dev` corriendo en otra terminal (API `127.0.0.1:8000`,
  web `127.0.0.1:5173`).
- `.env` privado configurado por el usuario (sólo nombres): `ANTHROPIC_API_KEY`,
  `COMPANY_NAME`, `COMPANY_DESCRIPTION`, `ASSISTANT_NAME`, `KNOWLEDGE_DIR`, `DATA_DIR`
  nuevo y `SEED_DEMO=false`. Reiniciar la API tras cambiarlo. No leer ni imprimir `.env`.
- Un administrador creado en la UI o con `python -m app.manage create-admin`.
- `jq` y `curl` disponibles. Las llamadas de chat en modo Anthropic consumen el proveedor.

## Sesión de shell (sin secretos en comandos ni historial)

```bash
API=http://127.0.0.1:8000
read -r -p 'Correo del administrador: ' LUMEN_EMAIL
read -r -s -p 'Contraseña: ' LUMEN_PASSWORD; echo
TOKEN=$(jq -n --arg e "$LUMEN_EMAIL" --arg p "$LUMEN_PASSWORD" '{email:$e,password:$p}' \
  | curl -fsS -H 'Content-Type: application/json' --data @- "$API/api/auth/login" \
  | jq -r .access_token)
unset LUMEN_PASSWORD
ask() {
  jq -n --arg m "$1" '{message:$m}' \
    | curl -fsS -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
        --data @- "$API/api/chat" \
    | jq '{mode, model, answer, sources: [.sources[].document_name], trace: [.trace[] | {tool, status}]}'
}
```

El JWT dura 30 minutos: si una llamada devuelve 401, repetir el login.

## Escenarios

### Q0 Material del brief (sin ejecutar nada)

```bash
python3 -I -m zipfile -l 'prueba-tecnica/<archivo>.zip'
uv run --project backend --locked --extra semantic python scripts/import-material.py 'prueba-tecnica/<archivo>.zip' --no-upload
jq '.' material/import-*/manifest.json
```

Esperado: listado completo sin extraer; el manifest nombra lo importado y lo omitido.
Leer desde el ZIP (`unzip -p`) los formatos no convertidos que importen.

### Q1 Salud y modo del proveedor

```bash
curl -fsS "$API/api/health" | jq '{status, mode, model, embedding, tools}'
curl -fsS "$API/api/company" | jq '{company_name, assistant_name}'
```

Esperado: `status: "ok"`, `mode: "anthropic"` (o el proveedor que exija el brief) y la
identidad de la empresa del brief. Un `mode: "demo"` no vale como evidencia final.

### Q2 Respuesta fundamentada con fuente

```bash
ask '<pregunta sobre un hecho presente en backend/knowledge/<empresa>/>'
```

Esperado: respuesta correcta, `sources` con el documento esperado y `search_knowledge`
`completed` en `trace`. En la UI, abrir la tarjeta de fuente y comprobar el fragmento.

### Q3 Dato ausente admitido

```bash
ask '<pregunta sobre un dato que no figura en el corpus>'
```

Esperado: admite que los documentos no contienen el dato; no inventa cifras ni cita
fuentes irrelevantes.

### Q4 Subida de un documento empresarial

```bash
curl -fsS -H "Authorization: Bearer $TOKEN" -F 'file=@<ruta/documento-empresarial.md>' \
  "$API/api/documents" | jq '{documents: [.documents[] | {name, chunks}], skipped, total_chunks}'
curl -fsS -H "Authorization: Bearer $TOKEN" "$API/api/documents" | jq '[.documents[].name]'
ask '<pregunta cuya respuesta sólo está en el documento subido>'
```

Esperado: `chunks > 0`, `skipped: []` y la última respuesta cita el documento subido.
Nunca subir el enunciado, la rúbrica ni código de evaluación.

### Q5 Llamada real a una herramienta

```bash
curl -fsS -H "Authorization: Bearer $TOKEN" "$API/api/tools" | jq '[.tools[] | {name, enabled}]'
jq -n '{name:"calculate", input:{expression:"(1200*3)/4"}}' \
  | curl -fsS -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
      --data @- "$API/api/tools/run" | jq '{tool, status, output, duration_ms}'
ask '<petición que requiera la herramienta exigida por el brief>'
```

Esperado: `status: "completed"` con salida real; en el chat (`mode: "anthropic"`) la
traza muestra la herramienta del brief con su resultado. Sustituir `calculate` por la
herramienta nueva y su `input` según `GET /api/tools`.

### Q6 Escritura con confirmación (sólo si el brief pide escrituras)

```bash
PROPUESTA=$(mktemp)
jq -n '{name:"create_support_ticket", input:{subject:"<asunto>", description:"<descripción>"}}' \
  | curl -fsS -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
      --data @- "$API/api/tools/run" > "$PROPUESTA"
jq '.output | fromjson | {requires_confirmation, action}' "$PROPUESTA"
jq '(.output | fromjson | .action) + {action_key: .id}' "$PROPUESTA" \
  | curl -fsS -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
      --data @- "$API/api/actions/confirm" | jq '{tool, status, output: (.output | fromjson | .request)}'
curl -fsS -H "Authorization: Bearer $TOKEN" "$API/api/requests" | jq .
rm -f "$PROPUESTA"
```

Esperado: primero sólo una propuesta (`requires_confirmation: true`, nada guardado);
tras confirmar, la solicitud aparece en `/api/requests`. En el chat, la propuesta se
confirma con el botón de la UI.

### Q7 Escenarios del brief

_Pendiente del brief._ Una fila por criterio del evaluador (SC-### del spec):

| SC | Comando, URL o acción de UI | Resultado esperado | Resultado obtenido |
| --- | --- | --- | --- |
| _pendiente_ | | | |

### Q8 Checks estáticos y pruebas

```bash
make check
make speckit-check
SPECIFY_FEATURE=002-exam-adaptation SPECIFY_FEATURE_DIRECTORY=specs/002-exam-adaptation \
  bash .specify/scripts/bash/check-prerequisites.sh --json --require-spec --require-tasks --include-tasks
```

Mientras se itera, subconjuntos proporcionales de `scripts/check.sh`:
`uv run --project backend --locked --extra dev --extra semantic pytest backend/tests -q`
y `npm --prefix frontend run lint && npm --prefix frontend run typecheck && npm --prefix frontend run test -- --run && npm --prefix frontend run build`.
Antes del commit, `make check` completo.

### Q9 Recorrido en el navegador

En `http://127.0.0.1:5173`: login, Q2 y Q3 desde el chat con fuentes visibles, subida
en **Documentos**, herramienta en **Herramientas** y, si aplica, confirmación de Q6.

### Q10 Publicación y despliegue (sólo con autorización del usuario)

```bash
python3 scripts/audit-public.py
gitleaks git   # si está instalado (scripts/install-gitleaks.sh)
PUBLIC_URL=https://humanizar-ai-agent.vercel.app
curl -fsS "$PUBLIC_URL/api/health" | jq '{status, mode, model, features}'
curl -fsS "$PUBLIC_URL/api/company" | jq '{company_name, assistant_name}'
curl -fsS "$PUBLIC_URL/api/auth/status"
curl -fsS -o /dev/null -w '%{http_code}\n' "$PUBLIC_URL/api/docs"
```

Push a `dev` y backend en el VPS según `docs/OPERATIONS.md` (`deploy-vps.py check/up/status`).
Esperado: salud `ok`, modo y empresa del brief, `setup_required: false`, docs 200 y una
respuesta de producción con fuente (llamada de pago, registrar aparte).

## Registro de resultados

| Escenario | Fecha | Resultado | Evidencia |
| --- | --- | --- | --- |
| Q0–Q10 | _pendiente_ | _no ejecutado_ | |
