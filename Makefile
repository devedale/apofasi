# Makefile for the Log Analyzer Project

# Variables
COMPOSE_FILE = docker-compose.yml
SERVICE_NAME = log-processor

.PHONY: help setup install-deps update-deps run run-ui stop logs shell clean

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  setup        - Builds and pulls the necessary Docker images."
	@echo "  install-deps - Installs Python dependencies from requirements.txt."
	@echo "  update-deps  - Updates Python dependencies to latest versions."
	@echo "  run          - Starts the backend services (Ollama) in detached mode."
	@echo "  run-ui       - Starts the Log Analyzer UI inside the Docker container."
	@echo "  stop         - Stops the running services."
	@echo "  logs         - Follows the logs of all services."
	@echo "  shell        - Opens a bash shell inside the log-processor container."
	@echo "  clean        - Removes Docker containers, networks, and volumes."

setup:
	@echo "--- Pulling Docker images and building services... ---"
	docker compose -f $(COMPOSE_FILE) build
	docker compose -f $(COMPOSE_FILE) pull

install-deps:
	@echo "--- Installing Python dependencies... ---"
	pip install -r requirements.txt
	@echo "--- Dependencies installed successfully! ---"

update-deps:
	@echo "--- Updating Python dependencies... ---"
	pip install --upgrade -r requirements.txt
	@echo "--- Dependencies updated successfully! ---"

run:
	@echo "--- Starting services in detached mode... ---"
	docker compose -f $(COMPOSE_FILE) up -d

run-ui:
	@echo "--- Starting the Log Analyzer UI inside the container... ---"
	@echo "Note: Make sure you have run 'xhost +local:docker' on your host machine."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_NAME) python3 run_ui.py

stop:
	@echo "--- Stopping services... ---"
	docker compose -f $(COMPOSE_FILE) down

logs:
	@echo "--- Following logs (Ctrl+C to exit)... ---"
	docker compose -f $(COMPOSE_FILE) logs -f

shell:
	@echo "--- Opening shell in $(SERVICE_NAME) container... ---"
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_NAME) /bin/bash

clean:
	@echo "--- Removing containers, networks, and volumes... ---"
	docker compose -f $(COMPOSE_FILE) down -v --remove-orphans