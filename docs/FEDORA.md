# Fedora en Documentos/repos/SoftopPrueba

La ubicación preparada para desarrollo es
`${HOME}/Documentos/repos/SoftopPrueba`, con el mismo nombre de carpeta que este
proyecto. Cada equipo instala sus propias
dependencias y conserva su configuración privada; no copiar `.env`, sesiones de
Claude ni entornos virtuales desde otra máquina. Los archivos públicos se obtienen
del repositorio y la clave del proveedor se configura localmente sólo en el backend.

## Preparar herramientas

Clonar primero en `Documentos/repos/SoftopPrueba` para ejecutar el script versionado
y revisarlo. Si el destino ya existe, usar el checkout conservado; no ejecutar
otro clon encima ni borrar sus cambios:

```bash
mkdir -p "$HOME/Documentos/repos"
git clone --branch dev --single-branch https://github.com/stevenvo780/humanizar-ai-agent.git \
  "$HOME/Documentos/repos/SoftopPrueba"
cd "$HOME/Documentos/repos/SoftopPrueba"
bash scripts/prepare-fedora.sh
```

Si falta Git, instalarlo primero con `sudo dnf install git`. Ejecutar como el usuario
habitual de Fedora. El script usa `sudo dnf` de forma local para Git, Make, curl,
tar, gzip, Node y npm; el prompt de sudo permanece en ese ordenador. Nunca solicita
una contraseña SSH ni la transmite a otro servicio. No añade repositorios globales
de Claude, no configura un proveedor ni realiza login.

Se comprueba Node **22 o posterior**, se instala uv **0.11.21** si falta o es anterior,
y Python **3.12** mediante uv. Python del sistema de Fedora se conserva; uv usa su
intérprete propio para este proyecto. Un Node antiguo exige actualizar la distribución
o preparar Node compatible antes de continuar. Los paquetes dnf pueden variar entre
versiones de Fedora; el script valida la versión instalada.

Claude Code se instala en el usuario mediante el instalador nativo oficial, versión
**2.1.286** si falta una versión compatible. Se conserva una instalación existente
**2.1.280 o posterior**, requerida por la preferencia `claude-opus-5-5`. El modelo
puede cambiar con `CLAUDE_CODE_MODEL` al invocar Make, sin alterar el modelo Haiku de
la aplicación. El instalador nativo puede actualizar Claude en ejecuciones futuras;
el pin es la versión inicial de preparación, no una promesa de inmovilidad.
[Instalación Claude Code](https://code.claude.com/docs/en/setup),
[configuración de modelos](https://code.claude.com/docs/en/model-config),
[instalación de uv](https://docs.astral.sh/uv/getting-started/installation/).

El script descarga instaladores oficiales por HTTPS a archivos temporales, después
los ejecuta y elimina únicamente esos archivos. Specify CLI se instala como tool de
uv con versión **1.0.7**. No ejecuta código de un ZIP del examen. Un checkout existente
se preserva: no hay pull, cambio de rama, reset ni sobrescritura de archivos locales.
El helper rechaza enlaces simbólicos en el destino, `Documentos` o `Documentos/repos`,
archivos que ocupen esas rutas y carpetas que no sean la raíz de un checkout existente.

Opciones disponibles:

```bash
bash scripts/prepare-fedora.sh --check       # Sólo presencia/versiones de herramientas.
bash scripts/prepare-fedora.sh --skip-claude # Conserva la instalación Claude sin prepararla.
bash scripts/prepare-fedora.sh --skip-setup  # Instala herramientas sin make setup.
```

El modo `--check` no descarga, autentica ni abre configuraciones privadas. El script
se valida por sintaxis y con comandos aislados de preparación; su ejecución completa
en Fedora requiere comprobar los resultados en ese equipo.

## Usar el proyecto

Asegurar `~/.local/bin` en `PATH` para uv, Claude y Specify. Por ejemplo, añadir esta
línea a la configuración de la shell del usuario si aún no existe:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

`make setup` instala los lockfiles, prepara FastEmbed y crea `.env` sólo si falta.
La configuración se crea con modo privado y el script refuerza `0600` sin leer su
contenido. Consultar [config/env.example](../config/env.example) como plantilla
pública y editar `.env` localmente. Para usar la clave de Anthropic, completar el
archivo backend del proyecto; nunca introducirla en el navegador.

```bash
cd "$HOME/Documentos/repos/SoftopPrueba"
make setup
make check
make speckit-check
make dev
```

La web local escucha en `127.0.0.1:5173` y la API en `127.0.0.1:8000`. `make lan`
habilita la web en la red local; no es el despliegue público de producción. El terminal
del agente utiliza el sandbox Docker; si no hay daemon accesible, el dev script deja
esa capacidad desactivada y lo indica. No instalar Docker únicamente para poder
consultar documentación o usar recuperación. La receta VPS está en
[DEPLOYMENT.md](DEPLOYMENT.md).

Abrir Claude Code de forma interactiva en este equipo para iniciar sesión con la
cuenta autorizada; no importar credenciales o settings locales de otra máquina:

```bash
make claude
# Override admitido por Claude Code:
make claude CLAUDE_CODE_MODEL=opus
```

Claude Code lee `CLAUDE.md`, `AGENTS.md` y las skills públicas del checkout. Su login
es independiente de `ANTHROPIC_API_KEY` del backend. Spec Kit usa los artefactos
versionados y el selector de feature local creado por setup; para el examen real,
trabajar desde el brief recibido siguiendo [EXAM_20_MIN.md](EXAM_20_MIN.md).

## Verificación pendiente en Fedora

Estado de esta entrega (2026-10-07): la preparación completa en Fedora aún no se
ha ejecutado ni verificado. El alias SSH `fedora` no resuelve en el entorno actual;
falta una dirección o un alias SSH válido antes de gestionar esa instalación.
La comprobación local de sintaxis y ayuda del helper no acredita que las herramientas,
el setup, el login interactivo de Claude o la aplicación funcionen en aquel equipo.
La autenticación se realiza allí con una cuenta autorizada, sin transferir contraseñas,
sesiones ni configuración privada desde este workspace.
