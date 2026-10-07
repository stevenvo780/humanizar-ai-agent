#!/usr/bin/env bash
set -euo pipefail
umask 077
CHECK_ONLY=false
SKIP_CLAUDE=false
SKIP_SETUP=false
for option in "$@"; do
  case "$option" in
    --check) CHECK_ONLY=true ;;
    --skip-claude) SKIP_CLAUDE=true ;;
    --skip-setup) SKIP_SETUP=true ;;
    --help|-h)
      echo 'Usage: bash scripts/prepare-fedora.sh [--check] [--skip-claude] [--skip-setup]'
      echo 'On Fedora, prepares tools and clones dev into ${HOME}/Documentos/repos/SoftopPrueba.'
      echo 'Uses local sudo only for dnf. Never signs in to Claude or forwards passwords.'
      exit 0 ;;
    *) echo 'Unknown Fedora preparation option. Use --help.' >&2; exit 2 ;;
  esac
done
if [[ ! -f /etc/fedora-release ]]; then
  echo 'Run this preparation script on Fedora Linux.' >&2; exit 1
fi
if (( EUID == 0 )); then
  echo 'Run as your normal desktop user; sudo is used locally for system packages.' >&2; exit 1
fi
export PATH="${HOME}/.local/bin:${PATH}"
if [[ "$CHECK_ONLY" == true ]]; then
  for tool in git make curl node npm uv claude; do
    if command -v "$tool" >/dev/null; then "$tool" --version; else echo "Missing tool: $tool"; fi
  done
  if command -v specify >/dev/null; then specify version; else echo 'Missing tool: specify'; fi
  if command -v uv >/dev/null; then uv python find 3.12 --no-python-downloads --show-version; fi
  echo 'Read-only tool check complete. Repository files and credentials were not opened.'
  exit 0
fi
sudo dnf install -y git make curl tar gzip nodejs npm
NODE_MAJOR="$(node -p 'Number(process.versions.node.split(".")[0])')"
if (( NODE_MAJOR < 22 )); then
  echo 'This Fedora repository provides Node below 22. Upgrade Fedora/Node before setup.' >&2
  exit 1
fi
INSTALL_DIR="$(mktemp -d)"
cleanup() {
  rm -f -- "$INSTALL_DIR/uv-install.sh" "$INSTALL_DIR/claude-install.sh"
  rmdir -- "$INSTALL_DIR" 2>/dev/null || true
}
trap cleanup EXIT
UV_READY=false
if command -v uv >/dev/null; then
  UV_VERSION="$(uv --version)"
  if [[ "$UV_VERSION" =~ ^uv[[:space:]]+([0-9]+)\.([0-9]+)\.([0-9]+) ]]; then
    if (( BASH_REMATCH[1] > 0 || BASH_REMATCH[2] > 11 || (BASH_REMATCH[2] == 11 && BASH_REMATCH[3] >= 21) )); then
      UV_READY=true
    fi
  fi
fi
if [[ "$UV_READY" == false ]]; then
  curl --proto '=https' --proto-redir '=https' --tlsv1.2 --fail --silent --show-error --location \
    https://astral.sh/uv/0.11.21/install.sh -o "$INSTALL_DIR/uv-install.sh"
  UV_INSTALL_DIR="${HOME}/.local/bin" UV_NO_MODIFY_PATH=1 sh "$INSTALL_DIR/uv-install.sh"
fi
uv python install 3.12
if [[ "$SKIP_CLAUDE" == false ]]; then
  CLAUDE_READY=false
  if command -v claude >/dev/null; then
    CLAUDE_VERSION="$(claude --version)"
    if [[ "$CLAUDE_VERSION" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+) ]]; then
      if (( BASH_REMATCH[1] > 2 || (BASH_REMATCH[1] == 2 && (BASH_REMATCH[2] > 1 || (BASH_REMATCH[2] == 1 && BASH_REMATCH[3] >= 280))) )); then
        CLAUDE_READY=true
      fi
    fi
  fi
  if [[ "$CLAUDE_READY" == false ]]; then
    curl --proto '=https' --proto-redir '=https' --tlsv1.2 --fail --silent --show-error --location \
      https://claude.ai/install.sh -o "$INSTALL_DIR/claude-install.sh"
    bash "$INSTALL_DIR/claude-install.sh" 2.1.286
  fi
  claude --version
fi
uv tool install specify-cli==1.0.7
PROJECT_DIR="${HOME}/Documentos/repos/SoftopPrueba"
for destination in "${HOME}/Documentos" "${HOME}/Documentos/repos" "$PROJECT_DIR"; do
  if [[ -L "$destination" ]]; then
    echo 'Project destination or its parent is a symlink; use regular directories locally.' >&2; exit 1
  elif [[ -e "$destination" && ! -d "$destination" ]]; then
    echo 'Project destination or its parent is not a directory; existing files were preserved.' >&2; exit 1
  fi
done
if [[ -e "$PROJECT_DIR" ]]; then
  if ! PROJECT_PREFIX="$(git -C "$PROJECT_DIR" rev-parse --show-prefix 2>/dev/null)" || [[ -n "$PROJECT_PREFIX" ]]; then
    echo 'Project destination is not the root of an existing checkout; it was preserved.' >&2; exit 1
  fi
  echo 'Existing checkout preserved; no pull, branch switch or reset was performed.'
else
  mkdir -p -- "${HOME}/Documentos/repos"
  git clone --branch dev --single-branch https://github.com/stevenvo780/humanizar-ai-agent.git "$PROJECT_DIR"
fi
if [[ "$SKIP_SETUP" == false ]]; then
  make -C "$PROJECT_DIR" setup
  if [[ -f "$PROJECT_DIR/.env" && ! -L "$PROJECT_DIR/.env" ]]; then chmod 600 "$PROJECT_DIR/.env"; fi
fi
echo 'Fedora preparation complete. Add ~/.local/bin to PATH in your shell if necessary.'
echo 'Open ${HOME}/Documentos/repos/SoftopPrueba, then make dev or make claude.'
echo 'Claude authentication is a separate interactive step on this computer.'
