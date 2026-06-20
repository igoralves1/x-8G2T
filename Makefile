# =============================================================================
# X-8G2T convenience Makefile
# =============================================================================
SHELL := /bin/bash
COMPOSE := docker compose

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

.PHONY: env
env: ## Create .env from template if it does not exist
	@test -f .env || (cp .env.example .env && echo "Created .env - edit the <CHANGE_ME> values")

.PHONY: certs
certs: ## Generate the TLS certificates for MQTT
	@cd ssl && chmod +x generate-certs.sh && ./generate-certs.sh

.PHONY: models
models: ## Download the GGUF models into the shared docker volume
	@chmod +x scripts/download-models.sh && ./scripts/download-models.sh

.PHONY: build
build: ## Build all images
	$(COMPOSE) build

.PHONY: up
up: ## Start the full stack (build if needed)
	$(COMPOSE) --profile all up -d --build

.PHONY: core
core: ## Start only the core pipeline (no Superset / VLM)
	$(COMPOSE) --profile core up -d --build

.PHONY: index
index: ## (Re)build the RAG knowledge base (incl. SPC books) in Qdrant
	$(COMPOSE) --profile index run --rm rag-indexer

.PHONY: spc-test
spc-test: ## Run the SPC engine test suite
	$(COMPOSE) run --rm --entrypoint python spc-mcp test_spc.py

.PHONY: down
down: ## Stop the stack
	$(COMPOSE) --profile all down

.PHONY: clean
clean: ## Stop the stack and DELETE all volumes (DESTRUCTIVE)
	$(COMPOSE) --profile all down -v

.PHONY: ps
ps: ## Show service status
	$(COMPOSE) ps

.PHONY: logs
logs: ## Tail logs (use S=service to filter, e.g. make logs S=agent-orchestrator)
	$(COMPOSE) logs -f $(S)

.PHONY: bootstrap
bootstrap: env certs ## First-time setup: .env + certs (then run `make models && make up && make index`)
	@echo "Bootstrap done. Next: make models && make up && make index"
