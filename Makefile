PYTHON ?= backend/.venv/bin/python
PIP ?= backend/.venv/bin/pip
LOCAL_DATABASE_URL ?= postgresql+psycopg://finance:finance@127.0.0.1:5432/personal_finance

.PHONY: help setup up down logs migrate seed ollama-up ollama-down ollama-model hermes-local-smoke maintenance-check maintenance-cleanup db-backup db-backup-check db-restore backend-check agent-check frontend-check frontend-e2e cycle3-check cycle3-ready check

help:
	@echo "setup           instala dependências locais do backend e frontend"
	@echo "up              sobe PostgreSQL, API e frontend via Docker Compose"
	@echo "down            encerra os containers sem apagar os volumes"
	@echo "logs            acompanha os logs dos serviços"
	@echo "migrate         aplica as migrations no banco configurado"
	@echo "seed            carrega os dados de demonstração"
	@echo "ollama-up       sobe Ollama opcional, acessível somente no host local"
	@echo "ollama-down     encerra Ollama sem apagar os modelos"
	@echo "ollama-model    baixa llama3.2:3b para Hermes (uso de disco/RAM)"
	@echo "maintenance-check simula a limpeza operacional (Compose ativo ou host)"
	@echo "maintenance-cleanup aplica a limpeza operacional explicitamente"
	@echo "db-backup       cria dump local não cifrado do PostgreSQL"
	@echo "db-backup-check restaura um dump em banco temporário e verifica a estrutura"
	@echo "db-restore      restaura dump com confirmação explícita (destrutivo)"
	@echo "frontend-e2e     roda E2E desktop/mobile em stack e banco descartáveis"
	@echo "check           executa todas as verificações locais"
	@echo "cycle3-check    verifica backend, Ollama, Hermes e pareamento sem alterar estado"
	@echo "cycle3-ready    exige todos os pré-requisitos do round trip WhatsApp"
	@echo "                 (migrations/seed usam LOCAL_DATABASE_URL no host)"
	@echo "hermes-local-smoke executa consulta somente leitura pelo perfil Hermes local"

setup:
	test -x $(PYTHON) || python3.12 -m venv backend/.venv
	$(PIP) install -e 'backend[dev]'
	cd frontend && npm ci

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	cd backend && DATABASE_URL="$(LOCAL_DATABASE_URL)" .venv/bin/alembic upgrade head
	cd backend && DATABASE_URL="$(LOCAL_DATABASE_URL)" .venv/bin/alembic check

seed:
	cd backend && DATABASE_URL="$(LOCAL_DATABASE_URL)" PYTHONPATH=. .venv/bin/python -m app.seed_demo

ollama-up:
	@docker volume inspect personal-finance-ollama >/dev/null 2>&1 || docker volume create personal-finance-ollama >/dev/null
	docker compose -p personal-finance-ollama -f docker-compose.ollama.yml up -d

ollama-down:
	docker compose -p personal-finance-ollama -f docker-compose.ollama.yml down

ollama-model:
	docker compose -p personal-finance-ollama -f docker-compose.ollama.yml exec ollama ollama pull llama3.2:3b

hermes-local-smoke:
	./scripts/hermes_local_smoke.sh

maintenance-check:
	@if docker compose ps --services --filter status=running 2>/dev/null | grep -qx backend; then \
		docker compose exec -T backend python -m app.maintenance; \
	else \
		PYTHONPATH=backend $(PYTHON) -m app.maintenance; \
	fi

maintenance-cleanup:
	@if docker compose ps --services --filter status=running 2>/dev/null | grep -qx backend; then \
		docker compose exec -T backend python -m app.maintenance --apply; \
	else \
		PYTHONPATH=backend $(PYTHON) -m app.maintenance --apply; \
	fi

db-backup:
	./scripts/backup_postgres.sh

db-backup-check:
	test -n "$(BACKUP)" || (echo "Uso: make db-backup-check BACKUP=backups/arquivo.dump"; exit 2)
	./scripts/check_postgres_backup.sh "$(BACKUP)"

db-restore:
	test -n "$(BACKUP)" || (echo "Uso: make db-restore BACKUP=backups/arquivo.dump"; exit 2)
	./scripts/restore_postgres.sh --confirm "$(BACKUP)"

backend-check:
	cd backend && .venv/bin/ruff check app tests
	cd backend && .venv/bin/ruff format --check app tests
	cd backend && .venv/bin/pytest -q

agent-check:
	cd backend && .venv/bin/ruff check --config ../agent/pyproject.toml ../agent
	cd backend && .venv/bin/ruff format --config ../agent/pyproject.toml --check ../agent
	PYTHONPATH=. $(PYTHON) -m pytest -q agent/tests
	$(PYTHON) -m compileall -q backend/app agent

cycle3-check:
	PYTHONPATH=. $(PYTHON) -m agent.integration_check

cycle3-ready:
	PYTHONPATH=. $(PYTHON) -m agent.integration_check --strict

frontend-check:
	cd frontend && npm test
	cd frontend && npm run lint
	cd frontend && npm run typecheck
	cd frontend && npm run build

frontend-e2e:
	./scripts/frontend_e2e.sh

check: backend-check agent-check frontend-check
