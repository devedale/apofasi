# Unified Log Analyzer & Anonymizer
 
This project provides a unified, configuration-driven system for parsing, anonymizing, and preprocessing log files. It integrates Microsoft Presidio for AI-powered PII detection and Drain3 for log template mining, with a user-friendly Qt interface. The entire application is containerized with Docker for easy setup and deployment.

## ✨ Features

- **Unified Processing Pipeline:** A cohesive 3-phase pipeline handles parsing, anonymization, and template mining.
- **AI-Powered Anonymization:** Uses Microsoft Presidio to detect and anonymize a wide range of personally identifiable information (PII).
- **Advanced Template Mining:** Employs Drain3 to discover log templates from both original and anonymized log messages.
- **Extensible Parsing:** A "Chain of Responsibility" pattern allows for easily adding new parsers for different log formats (JSON, CSV, Regex, etc.).
- **Centralized Configuration:** A single `config.yaml` file controls all aspects of the application, from regex patterns to Presidio and Drain3 settings.
- **Containerized Environment:** The entire application and its dependencies (including AI models via Ollama) are managed by Docker Compose for a consistent and easy-to-manage setup.
- **Desktop UI:** A Qt-based graphical user interface allows for easy interaction, configuration, and execution of the processing pipeline.

## 🏗️ Architecture

The application is built with a clean, service-oriented architecture, located in the `log_analyzer/` directory.

- **`log_analyzer/parsing`**: Contains the extensible parsing framework using the Chain of Responsibility pattern.
- **`log_analyzer/services`**: Contains the core business logic, including the main `LogProcessingService`, and wrappers for Presidio, Drain3, and configuration management.
- **`log_analyzer/ui`**: Contains the Qt-based user interface components.
- **`docker-compose.yml`**: Orchestrates the main application (`log-processor`), an AI model service (`ollama`), and the UI (`log-ui`).
- **`Makefile`**: Provides simple commands for managing the application lifecycle.

##  prerequisites

- **Docker** and **Docker Compose**
- For Linux/macOS with a graphical interface: An **X Server**.
- For Windows: **WSL2** (Windows Subsystem for Linux) and an X Server like **VcXsrv** or **GWSL**.

## 🚀 Getting Started

Instructions for running the application in a containerized environment with a graphical user interface.

### Step 1: Allow Display Connection (Host Machine)

Before you start, you need to give Docker permission to connect to your computer's graphical display. Open a terminal on your host machine and run this command. You typically only need to do this once per session.

```bash
xhost +local:docker
```

### Step 2: Build and Run the Application Environment

Navigate to the project directory and use the `Makefile` to build and run the Docker containers.

```bash
# This builds the containers and downloads required AI models.
make setup

# This starts the backend services (like Ollama) in the background.
make run
```

### Step 3: Launch the User Interface

You can now launch the UI with this command. It will execute the application *inside* the container but display the window on your desktop.

```bash
make run-ui
```

## Makefile Commands

- `make setup`: Builds all Docker images.
- `make run`: Starts the backend services in detached mode.
- `make run-ui`: Starts the Qt GUI application.
- `make stop`: Stops all running services.
- `make logs`: Tails the logs of all running services.
- `make shell`: Opens a shell inside the main `log-processor` container for debugging.
- `make clean`: Stops and removes all containers, networks, and volumes associated with the project.
