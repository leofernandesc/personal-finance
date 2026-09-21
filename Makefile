PYTHON ?= backend/.venv/bin/python
PIP ?= backend/.venv/bin/pip

.PHONY: help setup up down logs migrate seed backend-check agent-check frontend-check cycle3-check cycle3-ready check

help:
	@echo "setup           instala dependências locais do backend e frontend"
	@echo "up              sobe PostgreSQL, API e frontend via Docker Compose"
	@echo "down            encerra os containers sem apagar os volumes"
	@echo "logs            acompanha os logs dos serviços"
	@echo "migrate         aplica as migrations no banco configurado"
	@echo "seed            carrega os dados de demonstração"
	@echo "check           executa todas as verificações locais"
	@echo "cycle3-check    verifica backend, Ollama, Hermes e pareamento sem alterar estado"
	@echo "cycle3-ready    exige todos os pré-requisitos do round trip WhatsApp"

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
	cd backend && .venv/bin/alembic upgrade head
	cd backend && .venv/bin/alembic check

seed:
	cd backend && PYTHONPATH=. .venv/bin/python -m app.seed_demo

backend-check:
	cd backend && .venv/bin/ruff check app tests
	cd backend && .venv/bin/ruff format --check app tests
	cd backend && .venv/bin/pytest -q

agent-check:
	backend/.venv/bin/ruff check agent
	backend/.venv/bin/ruff format --check agent
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

check: backend-check agent-check frontend-check
