# Unified Log Analyzer & Anonymizer

This project provides a unified, configuration-driven system for parsing, anonymizing, and preprocessing log files. It integrates Microsoft Presidio for AI-powered PII detection and Drain3 for log template mining, with a user-friendly web interface. The entire application is containerized with Docker for easy setup and deployment.

## ✨ Features

- **Web-Based UI:** A modern, easy-to-use web interface for interacting with the application.
- **Unified Processing Pipeline:** A cohesive 3-phase pipeline handles parsing, anonymization, and template mining.
- **AI-Powered Anonymization:** Uses Microsoft Presidio to detect and anonymize a wide range of personally identifiable information (PII).
- **Advanced Template Mining:** Employs Drain3 to discover log templates from both original and anonymized log messages.
- **LogPPT Integration:** A powerful integration with the LogPPT (Log Parsing with Prompt-based Few-shot Learning) library for advanced log parsing.
- **Ollama Integration:** Gestione completa dei modelli AI tramite Ollama, sostituendo Hugging Face per una maggiore efficienza e controllo locale.
- **Extensible Parsing:** A "Chain of Responsibility" pattern allows for easily adding new parsers for different log formats (JSON, CSV, Regex, etc.).
- **Centralized Configuration:** A single `config.yaml` file controls all aspects of the application, from regex patterns to Presidio and Drain3 settings.
- **Containerized Environment:** L'intera applicazione e le sue dipendenze (inclusi i modelli AI tramite Ollama) sono gestiti da Docker Compose per un setup consistente e facile da gestire.

## 🏗️ Architecture

The application is built with a clean, service-oriented architecture, located in the `log_analyzer/` directory.

- **`log_analyzer/parsing`**: Contains the extensible parsing framework.
- **`log_analyzer/services`**: Contains the core business logic, including services for configuration, Drain3, LogPPT, and Ollama integration.
- **`log_analyzer/web`**: Contains the FastAPI web application, including the HTML templates and static files for the UI.

## 🚀 Ollama Integration

Il progetto ora utilizza **Ollama** invece di Hugging Face per la gestione dei modelli AI, offrendo:

### Vantaggi
- **Controllo Locale**: Tutti i modelli sono gestiti localmente senza dipendere da servizi esterni
- **Performance Migliorata**: Ollama è ottimizzato per l'inferenza locale e offre prestazioni superiori
- **Gestione Semplificata**: Interfaccia unificata per download, aggiornamento e rimozione dei modelli
- **Scalabilità**: Supporto nativo per modelli di diverse dimensioni e configurazioni

### Modelli Disponibili
1. **logppt-parser**: Modello principale per il parsing di log strutturati e non strutturati
2. **logppt-fast**: Versione veloce ottimizzata per elaborazioni rapide con meno accuratezza
3. **template-extractor**: Specializzato nell'estrazione e identificazione di template ricorrenti
4. **roberta-parser**: Parser basato su architettura RoBERTa per analisi semantiche avanzate

### Configurazione
La configurazione di Ollama è gestita tramite:
- **docker-compose.yml**: Servizio Ollama con health check e networking
- **config/config.yaml**: Parametri di configurazione per URL, timeout e modelli
- **Dockerfile.ollama**: Container personalizzato con modelli LogPPT preinstallati

## 📁 Project Structure

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

The "Model Management" tab allows you to manage the Hugging Face models used by the LogPPT feature. You can:
- See a list of already downloaded models, along with their size on disk.
- Download new models from Hugging Face Hub by providing the model name (e.g., `roberta-base`). The download progress will be shown in a real-time log viewer.
- Delete downloaded models to free up disk space.

### LogPPT Integration

The "LogPPT" tab provides a powerful interface for advanced log parsing using the LogPPT library. When you start a LogPPT process, a real-time log viewer will appear, showing the progress of the sampling, training, and parsing steps.

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
