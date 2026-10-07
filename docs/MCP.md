# MCP autenticado para Claude Code

El servidor MCP lee por HTTP la API en ejecución. No abre Qdrant, no ejecuta shell
y no recibe la clave de Anthropic. `company_info` consulta identidad pública;
`search_knowledge` exige una sesión de usuario como el resto de búsquedas de la API.

## Preparar una sesión local

Arranca `make dev`, completa la cuenta local desde la web y ejecuta en otra terminal:

```bash
uv run --project backend --extra semantic python -m app.manage mcp-login
```

El CLI pide correo y contraseña de forma interactiva; la contraseña queda oculta.
Guarda JWT y refresh en `$XDG_DATA_HOME/lumen/mcp-session.json`, o
`~/.local/share/lumen/mcp-session.json` si no hay `XDG_DATA_HOME`. El archivo tiene
modo `0600`, pertenece al usuario y está ligado al origen API. El servidor MCP usa
esa misma ruta por defecto; no hace falta editar `.mcp.json` ni copiar tokens.
El login de Claude Code es independiente de esta sesión de la aplicación.

Abre `make claude`, comprueba `/mcp` y pide una búsqueda de un hecho presente en
tus documentos. Se esperan IDs de documento/fragmento y texto recuperado. Sin
sesión, la búsqueda informa un error de autenticación; la identidad pública sigue
disponible. No desactivar `AUTH_ENABLED` para solucionar ese error.

## Origen y archivo personalizados

`LUMEN_API_URL` selecciona el origen; `LUMEN_API_TOKEN_FILE` permite una ruta privada
alternativa. `mcp-login --api-url ORIGEN --token-file RUTA` prepara esa sesión. El
origen configurado en el servidor debe coincidir con el del archivo de sesión.
La definición pública `.mcp.json` utiliza `http://127.0.0.1:8000`; cambiar sólo el
origen público cuando se necesite otro destino, nunca añadir credenciales a Git.

Se admite HTTP únicamente en loopback y HTTPS para un origen remoto. Los proxies
de entorno y las redirecciones están desactivados. Las rutas disponibles son
identidad y búsqueda. Un `LUMEN_API_TOKEN` privado del proceso permite usar un JWT
existente sin archivo; tiene precedencia y no puede renovarse por sí solo.
No pasar el token como argumento, imprimirlo, incluirlo en el entorno frontend
ni transferir el archivo de sesión a otra máquina.

## Renovación y errores

Un 401 con sesión guardada permite una renovación acotada y un reintento. Un lock
privado coordina procesos MCP que comparten ese archivo para evitar reutilizar
el refresh anterior. La escritura es atómica y conserva permisos privados.
Un rechazo de autenticación pide renovar el acceso; un 403 informa permisos
insuficientes. Una caída de red, un 429 o un 5xx conserva la sesión guardada.
Los mensajes de diagnóstico no incluyen tokens, cookies ni cuerpos HTTP privados.

Inicia sesión por separado en Fedora tras clonar el proyecto. Una copia de código
no incluye estas sesiones ni la autenticación de Claude. La configuración general
y las rutas del portátil están en [FEDORA.md](FEDORA.md).

La conexión stdio se configura siguiendo la
[documentación oficial de Claude Code](https://code.claude.com/docs/en/mcp).
