SHELL := /bin/bash

UV   ?= $(HOME)/.local/bin/uv
APP  ?= happyrobot-fde-tb

.PHONY: help
help:
	@echo "Targets:"
	@echo "  setup         - install backend venv (uv) and frontend deps"
	@echo "  dev-api       - run backend locally on :8000"
	@echo "  dev-web       - run frontend locally on :5173 (proxies /api -> :8000)"
	@echo "  test          - run backend pytest"
	@echo "  lint          - ruff check on backend"
	@echo "  build-image   - build the production Docker image"
	@echo "  run-image     - run the image locally on :8000 with .env"
	@echo "  fly-launch    - one-time Fly.io app create"
	@echo "  fly-deploy    - deploy to Fly.io"
	@echo "  fly-secrets   - push API_KEY + FMCSA_API_KEY to Fly secrets"

.PHONY: setup
setup:
	cd backend && $(UV) venv --python 3.12 && $(UV) pip install -e ".[dev]"
	cd frontend && npm install

.PHONY: dev-api
dev-api:
	cd backend && ./.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: dev-web
dev-web:
	cd frontend && npm run dev

.PHONY: test
test:
	cd backend && ./.venv/bin/pytest -q

.PHONY: lint
lint:
	cd backend && ./.venv/bin/ruff check app tests

.PHONY: build-image
build-image:
	docker build -t $(APP):latest .

.PHONY: run-image
run-image:
	docker run --rm -p 8000:8000 \
		-e API_KEY=$${API_KEY:-dev-api-key-change-me} \
		-e FMCSA_API_KEY=$${FMCSA_API_KEY:-} \
		-e CORS_ORIGINS=$${CORS_ORIGINS:-*} \
		-v $$(pwd)/.docker-data:/data \
		$(APP):latest

.PHONY: fly-launch
fly-launch:
	flyctl launch --no-deploy --copy-config --name $(APP)

.PHONY: fly-deploy
fly-deploy:
	flyctl deploy

.PHONY: fly-secrets
fly-secrets:
	@if [ -z "$$API_KEY" ] || [ -z "$$FMCSA_API_KEY" ]; then \
		echo "set API_KEY and FMCSA_API_KEY in your shell first"; exit 1; fi
	flyctl secrets set API_KEY=$$API_KEY FMCSA_API_KEY=$$FMCSA_API_KEY
