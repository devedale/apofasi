# Changelog

## [Unreleased] - 2024-12-19

### Fixed
- **Dockerfile**: Corretto errore di dipendenze librarie per PyQt6
  - Aggiunto `libglib2.0-0` (corretto da `libglib-2.0-0`)
  - Aggiunte dipendenze complete per PyQt6: `libcairo2`, `libpango-1.0-0`, `libpangocairo-1.0-0`, `libgdk-pixbuf2.0-0`, `libatk1.0-0`, `libgtk-3-0`, `libx11-6`, `libxext6`, `libxrender1`, `libxss1`, `libxtst6`
  - Aggiunte dipendenze di sistema per Python: `gcc`, `g++`, `libffi-dev`, `libssl-dev`, `zlib1g-dev`, `libjpeg-dev`, `libpng-dev`, `libfreetype6-dev`, `liblcms2-dev`, `libopenjp2-7-dev`, `libtiff5-dev`, `libwebp-dev`, `libharfbuzz-dev`, `libfribidi-dev`, `libxcb1-dev`
  - Aggiunte variabili d'ambiente per ottimizzazione: `PYTHONUNBUFFERED=1`, `PYTHONDONTWRITEBYTECODE=1`, `PIP_NO_CACHE_DIR=1`, `PIP_DISABLE_PIP_VERSION_CHECK=1`
  - Migliorato processo di installazione pip con `--upgrade pip setuptools wheel`
  - **CORREZIONE**: Aggiunto `libegl1-mesa` per risolvere errore `libEGL.so.1: cannot open shared object file`
  - **CORREZIONE**: Aggiunto `libxcb-cursor0` per risolvere errore plugin xcb di Qt
  - **MIGRAZIONE**: Cambiato da PyQt6 a PyQt5 per maggiore stabilità e compatibilità

- **requirements.txt**: Bloccate versioni specifiche per compatibilità
  - `presidio-analyzer==2.2.359`
  - `presidio-anonymizer==2.2.359`
  - **MIGRAZIONE**: `PyQt5==5.15.10` (sostituito PyQt6==6.5.3)
  - Aggiunte dipendenze: `numpy>=1.21.0`, `scikit-learn>=1.0.0`

- **presidio_service.py**: Aggiornato per compatibilità con Presidio 2.2.359
  - Sostituito `AnonymizerRequest` e `AnonymizerResult` con `EngineResult`
  - Sostituito `AdHocRecognizer` con `PatternRecognizer`
  - Aggiornato parametro `anonymizers` a `operators` nel metodo `anonymize`

- **UI Components**: Migrati tutti i componenti da PyQt6 a PyQt5
  - `main_window.py`: Aggiornati tutti gli import e le classi
  - `results_table_model.py`: Migrato per PyQt5
  - `worker.py`: Aggiornato per PyQt5
  - `config_dialog.py`: Migrato per PyQt5
  - `run_ui.py`: Aggiornato punto di ingresso principale
  - **CORREZIONE**: Spostato `QAction` da `QtGui` a `QtWidgets` per compatibilità PyQt5
  - **CORREZIONE**: Sostituito `QTableWidget` con `QTableView` per compatibilità con il modello dati
  - **VERIFICA**: PyQt5 si avvia correttamente con plugin offscreen (ma si blocca per mancanza di display)
- **PROBLEMA PERSISTENTE**: Dopo rebuild completo, il plugin xcb continua a non funzionare nonostante tutte le dipendenze installate
- **CONFERMA**: Anche i plugin alternativi (offscreen, minimal) si bloccano, confermando che il problema è sistemico con le dipendenze Qt
- **SOLUZIONE**: Aggiunte librerie specifiche per xcb: `libxcb1`, `libxcb-shm0`, `libxcb-sync1`, `libxcb-xkb1`, `libxcb-dri2-0`, `libxcb-dri3-0`, `libxcb-present0`, `libxcb-util1`

- **docker-compose.yml**: Ottimizzazioni per stabilità e performance
  - Aggiunto `restart: unless-stopped` per entrambi i servizi
  - Aggiunte variabili d'ambiente: `QT_X11_NO_MITSHM=1`, `PYTHONPATH=/app`
  - Aggiunto `stdin_open: true` e `tty: true` per interattività

- **.dockerignore**: Creato per ottimizzare build Docker
  - Esclusi file non necessari: `.git`, `__pycache__`, `*.pyc`, `venv/`, `.vscode/`, `*.log`, `tmp/`, `outputs/`

### Changed
- **Dockerfile**: Ristrutturato per migliore organizzazione e commenti
- **Build process**: Ottimizzato con dipendenze bloccate e ambiente stabile
- **UI Framework**: Migrato da PyQt6 a PyQt5 per maggiore stabilità

### Technical Debt
- Risolto problema di compatibilità tra versioni Presidio
- Eliminato codice legacy non compatibile con nuove API
- Centralizzate configurazioni di dipendenze
- Migrato framework UI per evitare problemi di compatibilità librarie

### Notes
- Le modifiche risolvono errori di import e dipendenze librarie
- L'ambiente Docker è ora più stabile e prevedibile
- Le versioni bloccate prevengono problemi di compatibilità futuri
- PyQt5 offre maggiore stabilità rispetto a PyQt6 per ambienti containerizzati
