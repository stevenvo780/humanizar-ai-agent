#!/usr/bin/env bash
# Exam layout: Claude Code (lead) | make dev (app) / Codex interactive on its own worktree.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
SESSION="${LUMEN_TMUX_SESSION:-examen}"
WORKTREE="${LUMEN_CODEX_WORKTREE:-$(dirname -- "$ROOT")/$(basename -- "$ROOT")-codex}"
command -v tmux >/dev/null || { echo 'Install tmux first.' >&2; exit 1; }
if tmux has-session -t "$SESSION" 2>/dev/null; then exec tmux attach -t "$SESSION"; fi
bash "$ROOT/scripts/codex-worker.sh" prepare
tmux new-session -d -s "$SESSION" -c "$ROOT" -n trabajo
tmux send-keys -t "$SESSION:trabajo" 'make exam-claude' Enter
tmux split-window -h -t "$SESSION:trabajo" -c "$ROOT"
tmux send-keys -t "$SESSION:trabajo.1" 'make dev' Enter
tmux split-window -v -t "$SESSION:trabajo.1" -c "$WORKTREE"
tmux send-keys -t "$SESSION:trabajo.2" "codex -C '$WORKTREE' -s workspace-write --add-dir \"\$HOME/.cache/uv\" --add-dir \"\$HOME/.npm\"" Enter
tmux select-pane -t "$SESSION:trabajo.0"
exec tmux attach -t "$SESSION"
