# Local Docker UX. Callers: human / CI docs (README → `make docker`).
# No prior Makefile (Glob **/Makefile* = 0). Reads .env + docker-compose.yml;
# may copy .env.example → .env (no secrets written). User: "make it easy to run make docker"

.PHONY: help docker docker-d up down logs rebuild ps health env

COMPOSE ?= docker compose
ENV_FILE ?= .env

help:
	@echo "Targets:"
	@echo "  make docker     - ensure .env, build + start stack (foreground)"
	@echo "  make docker-d   - same, detached"
	@echo "  make down       - stop stack"
	@echo "  make logs       - follow api+frontend logs"
	@echo "  make rebuild    - rebuild images without cache, then up -d"
	@echo "  make health     - curl API /health"
	@echo "  make env        - create .env from .env.example if missing"

env:
	@if [ ! -f "$(ENV_FILE)" ]; then \
		cp .env.example "$(ENV_FILE)"; \
		echo "Created $(ENV_FILE) from .env.example — add API keys."; \
	else \
		echo "$(ENV_FILE) already exists."; \
	fi

docker: env
	$(COMPOSE) up --build

docker-d: env
	$(COMPOSE) up --build -d
	@echo "UI  http://localhost:3000"
	@echo "API http://localhost:8000/health"
	@echo "Phoenix http://localhost:6006"

up: docker-d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f api frontend

rebuild: env
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d

ps:
	$(COMPOSE) ps

health:
	@curl -sf http://localhost:8000/health | tee /dev/stderr | grep -q '"status":"ok"' \
		&& echo " API healthy" || (echo "API not healthy"; exit 1)
