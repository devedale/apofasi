# Makefile for the Log Analyzer Project

# Variables
COMPOSE_FILE = docker-compose.yml
SERVICE_NAME = log-processor

.PHONY: help setup run stop logs shell clean

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  setup    - Pulls necessary Docker images and builds the services."
	@echo "  run      - Starts the services in detached mode."
	@echo "  stop     - Stops the running services."
	@echo "  logs     - Follows the logs of all services."
	@echo "  shell    - Opens a bash shell inside the log-processor container."
	@echo "  clean    - Removes Docker containers, networks, and volumes."

setup:
	@echo "--- Pulling Docker images and building services... ---"
	docker-compose -f $(COMPOSE_FILE) build
	docker-compose -f $(COMPOSE_FILE) pull

run:
	@echo "--- Starting services in detached mode... ---"
	docker-compose -f $(COMPOSE_FILE) up -d

run-ui:
	@echo "--- Starting the Log Analyzer UI... ---"
	python3 run_ui.py

stop:
	@echo "--- Stopping services... ---"
	docker-compose -f $(COMPOSE_FILE) down

logs:
	@echo "--- Following logs (Ctrl+C to exit)... ---"
	docker-compose -f $(COMPOSE_FILE) logs -f

shell:
	@echo "--- Opening shell in $(SERVICE_NAME) container... ---"
	docker-compose -f $(COMPOSE_FILE) exec $(SERVICE_NAME) /bin/bash

clean:
	@echo "--- Removing containers, networks, and volumes... ---"
	docker-compose -f $(COMPOSE_FILE) down -v --remove-orphans