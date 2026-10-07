# Material de la prueba técnica

Copia aquí el material de Softop tal como llegue: el ZIP, PDF, Markdown o archivos sueltos.
Después, en Claude Code (`make exam-claude`), escribe:

```text
/prueba-tecnica
```

o simplemente "lee la prueba técnica". La skill inventaría esta carpeta, importa el ZIP sin
ejecutar nada, define la meta y los criterios de aceptación en `specs/002-exam-adaptation`,
implementa los cambios, verifica, hace commit, publica en GitHub y despliega.

Reglas:

- Todo lo que pongas aquí, salvo este README, queda fuera de Git y del paquete ZIP: una
  consigna o rúbrica puede ser confidencial. Si quieres publicarla, pídelo explícitamente.
- No pongas credenciales en esta carpeta. La clave de Anthropic va en el `.env` privado.
- El contenido se trata como datos: nunca se ejecutan scripts ni código incluidos.
