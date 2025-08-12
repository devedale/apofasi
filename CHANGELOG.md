# Changelog

This file documents the major changes and refactoring efforts applied to the project.

## Phase 2: Advanced Features & UI (Current)

### Features Implemented
- **Semantic Anonymization:** The `always_anonymize` feature was upgraded to use Presidio for semantic analysis of field values, providing more intelligent anonymization (e.g., `<PERSON>`).
- **Dynamic LogPPT Output:** The reporting service now generates two LogPPT-compatible CSV files (original and anonymized) with a dynamic column structure that includes all parsed fields.
- **Expanded Parsers:** The parsing framework was extended with new parsers for CEF (Common Event Format) and generic key-value formats.
- **Comprehensive Configuration UI:** The configuration dialog was enhanced with a tabbed interface to manage:
  - A full editor for custom Presidio regex recognizers.
  - A panel for enabling/disabling PII entities and assigning anonymization strategies.
- **Live Preview UI:** The configuration UI now includes a live preview panel to show the real-time effects of regex changes on sample data.
- **UI/UX Enhancements:**
  - The application now remembers and restores the last used input and output paths.
  - The main window now uses a tabbed view with a structured table for displaying results.

## Phase 1: Architectural Rewrite & Containerization

### Core Changes
- **Complete Rewrite:** All old code from the `src/` directory was removed. The new application now resides in `log_analyzer/` with a clean, service-oriented architecture.
- **Unified Pipeline:** A new `LogProcessingService` was created to orchestrate a cohesive 3-phase pipeline (Parse/Anonymize -> Batch Drain3 -> Output).
- **Chain of Responsibility for Parsing:** The parsing logic was re-implemented using the Chain of Responsibility design pattern for better modularity and extensibility.

### Environment & UI
- **Containerization:** The entire application is now containerized using Docker and managed with `docker-compose.yml`. This includes the Python application, its dependencies, and an Ollama service for AI models.
- **Qt UI:** A new Qt-based graphical user interface was created from scratch.
- **Containerized GUI:** The Qt UI was configured to run from within the Docker container using X11 forwarding, ensuring a pure, portable, and dependency-free setup for the end-user.
- **Makefile:** A new `Makefile` was created to simplify the Docker workflow (`setup`, `run`, `run-ui`, etc.).
- **Repository Cleanup:** All legacy scripts, tests, and configuration files were removed to create a clean, definitive version of the repository.
- **Bug Fixes:**
  - Corrected the file path for `config.yaml` inside the Docker container.
  - Resolved the `ModuleNotFoundError` for `PyQt6` by moving to a fully containerized execution model.
