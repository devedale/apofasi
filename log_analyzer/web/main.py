import sys
import os
import json
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# --- Path Setup ---
# This is crucial to ensure that the log_analyzer package is found.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# --- Presidio Imports ---
# We import these here to see if the import itself is the source of the error.
try:
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, PatternRecognizer
    from presidio_anonymizer import AnonymizerEngine, OperatorConfig
    PRESIDIO_IMPORT_ERROR = None
except Exception as e:
    PRESIDIO_IMPORT_ERROR = traceback.format_exc()

# --- Service Imports ---
try:
    from log_analyzer.services.config_service import ConfigService
    from log_analyzer.parsing.interfaces import LogEntry, ParsedRecord
    from log_analyzer.parsing.parser_factory import create_parser_chain
    from log_analyzer.services.log_reader import LogReader
    from log_analyzer.services.drain3_service import Drain3Service
    SERVICE_IMPORT_ERROR = None
except Exception as e:
    SERVICE_IMPORT_ERROR = traceback.format_exc()


# --- FastAPI App Initialization ---
app = FastAPI()
app.mount("/static", StaticFiles(directory="log_analyzer/web/static"), name="static")
templates = Jinja2Templates(directory="log_analyzer/web/templates")

# --- API Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/debug-info", response_class=JSONResponse)
async def get_debug_info():
    """
    Returns a collection of raw data for debugging. This endpoint is designed
    to be extremely robust and report errors at each stage without crashing.
    """
    debug_data = {
        "python_path": sys.path,
        "working_directory": os.getcwd(),
        "presidio_import_error": PRESIDIO_IMPORT_ERROR,
        "service_import_error": SERVICE_IMPORT_ERROR,
        "raw_config": None,
        "raw_config_error": None,
        "recognizer_inspection_status": "Not Run",
        "inspected_recognizers": None,
        "recognizer_inspection_error": None,
    }

    # 1. Get the raw config from the YAML file
    try:
        config_service = ConfigService()
        debug_data['raw_config'] = config_service.load_config()
    except Exception as e:
        debug_data['raw_config_error'] = traceback.format_exc()
        # Do not return here, continue to gather more debug info if possible

    # 2. Try to inspect the Presidio recognizers ONLY if imports were successful
    if PRESIDIO_IMPORT_ERROR is None:
        try:
            debug_data['recognizer_inspection_status'] = "Running..."
            config = debug_data.get('raw_config', {})
            language = config.get("presidio", {}).get("analyzer", {}).get("language", "en")

            registry = RecognizerRegistry()
            registry.load_predefined_recognizers(languages=[language])
            default_recognizers = registry.get_recognizers(language=language)

            recognizer_info = []
            for rec in default_recognizers:
                info = {
                    "name": rec.name,
                    "supported_entity": getattr(rec, 'supported_entity', 'N/A'),
                    "default_score": getattr(rec, 'default_score', 'N/A'),
                    "is_pattern_recognizer": isinstance(rec, PatternRecognizer)
                }
                if isinstance(rec, PatternRecognizer):
                    info["patterns"] = [p.regex for p in rec.patterns]
                recognizer_info.append(info)

            debug_data['inspected_recognizers'] = recognizer_info
            debug_data['recognizer_inspection_status'] = "Success"
        except Exception as e:
            debug_data['recognizer_inspection_status'] = "FAILED"
            debug_data['recognizer_inspection_error'] = traceback.format_exc()

    return JSONResponse(content=debug_data)
