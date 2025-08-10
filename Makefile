.PHONY: help install install-dev test lint format clean build run-example

# Variabili
PYTHON := python3
PIP := pip3
PROJECT_NAME := clean-log-parser
SRC_DIR := src
TESTS_DIR := tests
CONFIG_DIR := config

help: ## Mostra questo aiuto
	@echo "🧹 Clean Log Parser - Comandi disponibili:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Installa il progetto in modalità sviluppo
	@echo "📦 Installazione Clean Log Parser..."
	$(PIP) install --upgrade setuptools wheel
	$(PIP) install -e .
	@echo "✅ Installazione completata"

install-dev: ## Installa il progetto con dipendenze di sviluppo
	@echo "🔧 Installazione con dipendenze di sviluppo..."
	$(PIP) install --upgrade setuptools wheel
	$(PIP) install -e ".[dev]"
	@echo "✅ Installazione sviluppo completata"

test: ## Esegui i test
	@echo "🧪 Esecuzione test..."
	pytest $(TESTS_DIR) -v --cov=$(SRC_DIR) --cov-report=html --cov-report=term-missing
	@echo "✅ Test completati"

test-fast: ## Esegui i test velocemente (senza coverage)
	@echo "⚡ Esecuzione test veloci..."
	pytest $(TESTS_DIR) -v
	@echo "✅ Test veloci completati"

lint: ## Controlla il codice con linting
	@echo "🔍 Controllo linting..."
	flake8 $(SRC_DIR) $(TESTS_DIR)
	mypy $(SRC_DIR)
	@echo "✅ Linting completato"

format: ## Formatta il codice
	@echo "🎨 Formattazione codice..."
	black $(SRC_DIR) $(TESTS_DIR)
	isort $(SRC_DIR) $(TESTS_DIR)
	@echo "✅ Formattazione completata"

clean: ## Pulisci file temporanei
	@echo "🧹 Pulizia..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf outputs/
	rm -rf drain3_state.bin
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	@echo "✅ Pulizia completata"

build: ## Build del progetto
	@echo "🔨 Build del progetto..."
	$(PYTHON) -m build
	@echo "✅ Build completato"

run-example: ## Esegui esempio con file di test
	@echo "🚀 Esecuzione esempio..."
	@mkdir -p outputs
	clean-parser parse ../log_samples/ -o outputs/ --verbose
	@echo "✅ Esempio completato"

list-parsers: ## Lista parser disponibili
	@echo "📋 Parser disponibili:"
	clean-parser list-parsers

create-examples: ## Crea file di esempio
	@echo "📝 Creazione file di esempio..."
	@mkdir -p examples
	@cp ../log_samples/* examples/ 2>/dev/null || true
	@echo "✅ File di esempio creati"

docker-build: ## Build immagine Docker
	@echo "🐳 Build immagine Docker..."
	docker build -t $(PROJECT_NAME) .
	@echo "✅ Build Docker completato"

docker-run: ## Esegui in Docker
	@echo "🐳 Esecuzione in Docker..."
	docker run -v $(PWD)/examples:/app/examples -v $(PWD)/outputs:/app/outputs $(PROJECT_NAME) parse examples/
	@echo "✅ Esecuzione Docker completata"

check-all: format lint test ## Esegui tutti i controlli
	@echo "✅ Tutti i controlli completati"

dev-setup: install-dev create-examples ## Setup completo per sviluppo
	@echo "🎉 Setup sviluppo completato!"

.PHONY: help install install-dev test lint format clean build run-example list-parsers create-examples docker-build docker-run check-all dev-setup 