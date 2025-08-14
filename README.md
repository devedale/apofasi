# Unified Log Analyzer & Anonymizer

This project provides a unified, configuration-driven system for parsing, anonymizing, and preprocessing log files. It integrates Microsoft Presidio for AI-powered PII detection and Drain3 for log template mining, with a user-friendly web interface. The entire application is containerized with Docker for easy setup and deployment.

## ✨ Features

- **Web-Based UI:** A modern, easy-to-use web interface for interacting with the application.
- **Unified Processing Pipeline:** A cohesive 3-phase pipeline handles parsing, anonymization, and template mining.
- **AI-Powered Anonymization:** Uses Microsoft Presidio to detect and anonymize a wide range of personally identifiable information (PII).
- **Advanced Template Mining:** Employs Drain3 to discover log templates from both original and anonymized log messages.
- **LogPPT Integration:** A powerful integration with the LogPPT (Log Parsing with Prompt-based Few-shot Learning) library for advanced log parsing.
- **LLM Model Management:** A dedicated UI for managing and downloading LLM models from Ollama.
- **Extensible Parsing:** A "Chain of Responsibility" pattern allows for easily adding new parsers for different log formats (JSON, CSV, Regex, etc.).
- **Centralized Configuration:** A single `config.yaml` file controls all aspects of the application, from regex patterns to Presidio and Drain3 settings.
- **Containerized Environment:** The entire application and its dependencies (including AI models via Ollama) are managed by Docker Compose for a consistent and easy-to-manage setup.

## 🏗️ Architecture

The application is built with a clean, service-oriented architecture, located in the `log_analyzer/` directory.

- **`log_analyzer/parsing`**: Contains the extensible parsing framework.
- **`log_analyzer/services`**: Contains the core business logic, including services for configuration, Drain3, and LogPPT.
- **`log_analyzer/web`**: Contains the FastAPI web application, including the HTML templates and static files for the UI.
- **`docker-compose.yml`**: Orchestrates the main application (`log-processor`) and an AI model service (`ollama`).
- **`Makefile`**: Provides simple commands for managing the application lifecycle.

## 🚀 Getting Started

### Prerequisites

- **Docker** and **Docker Compose**

### Step 1: Build and Run the Application

Navigate to the project directory and use the `Makefile` to build and run the Docker containers.

```bash
# This builds the containers and downloads required AI models.
make setup

# This starts the backend services and the web UI.
make run
```

### Step 2: Access the Web UI

Open your web browser and navigate to `http://localhost:7979`.

## Features in Detail

### Model Management

The "Model Management" tab allows you to manage the LLM models used by the application. You can:
- See a list of already downloaded models.
- Download new models from Ollama by providing the model name (e.g., `roberta-base`).

### LogPPT Integration

The "LogPPT" tab provides a powerful interface for advanced log parsing using the LogPPT library.

**Workflow:**
1.  **Upload a structured log file (CSV).** This file should be the output of a previous analysis step or a custom CSV file.
2.  **Configure the LogPPT process:**
    -   **Number of Shots:** Define the number of samples for few-shot learning.
    -   **Select Model:** Choose a downloaded model to use for parsing.
    -   **Max Train Steps:** Set the maximum number of training steps.
3.  **Advanced Configuration:**
    -   **Content Field Configuration:** Define how to construct the `Content` field that LogPPT will analyze. You can combine multiple columns from your CSV using a format string (e.g., `{message} - {user}`).
    -   **Column Order:** Specify which columns to include in the final output and their order.
4.  **Run the process** and download the parsed logs and templates.

## Makefile Commands

- `make setup`: Builds all Docker images.
- `make run`: Starts the backend services and web UI in detached mode.
- `make stop`: Stops all running services.
- `make logs`: Tails the logs of all running services.
- `make shell`: Opens a shell inside the main `log-processor` container for debugging.
- `make clean`: Stops and removes all containers, networks, and volumes associated with the project.
