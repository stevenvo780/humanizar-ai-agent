CLAUDE_CODE_MODEL ?= claude-opus-5-5

.PHONY: setup dev lan check docker stop package claude exam-claude speckit speckit-check
setup:
	bash scripts/bootstrap.sh
dev:
	bash scripts/dev.sh
lan:
	LUMEN_WEB_HOST=0.0.0.0 bash scripts/dev.sh
check:
	bash scripts/check.sh
docker:
	docker compose up --build -d
stop:
	docker compose down
package:
	bash scripts/package.sh
claude:
	claude --model "$(CLAUDE_CODE_MODEL)"
# Exam session: Spec Kit commands target the pending adaptation feature 002, never 001.
exam-claude:
	SPECIFY_FEATURE=002-exam-adaptation SPECIFY_FEATURE_DIRECTORY=specs/002-exam-adaptation \
	claude --model "$(CLAUDE_CODE_MODEL)"
speckit:
	uv tool install specify-cli==1.0.7
speckit-check:
	SPECIFY_FEATURE=001-company-agent SPECIFY_FEATURE_DIRECTORY=specs/001-company-agent bash .specify/scripts/bash/check-prerequisites.sh --json --require-spec --require-tasks --include-tasks
