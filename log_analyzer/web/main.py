import sys
import os
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# --- Path Setup ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# --- Service-based Imports ---
from log_analyzer.services.config_service import ConfigService
from log_analyzer.services.presidio_service import PresidioService
from log_analyzer.parsing.interfaces import LogEntry, ParsedRecord
from log_analyzer.parsing.parser_factory import create_parser_chain
from log_analyzer.services.log_reader import LogReader
from log_analyzer.services.drain3_service import Drain3Service

# --- FastAPI App Initialization ---
app = FastAPI()
app.mount("/static", StaticFiles(directory="log_analyzer/web/static"), name="static")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
templates = Jinja2Templates(directory="log_analyzer/web/templates")

# --- Pydantic Models ---
class PreviewRequest(BaseModel):
    sample_text: str
    presidio_config: Dict[str, Any]

class ConfigUpdateRequest(BaseModel):
    presidio: Dict[str, Any]

class AnalysisRequest(BaseModel):
    input_file: str

# --- Formatting Helper Functions ---
def format_as_anonymized_text(records: List[ParsedRecord], output_path: str):
    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(f"{record.presidio_anonymized or ''}\n")

def format_as_logppt(records: List[ParsedRecord], output_path: str):
    # ... (omitting for brevity, same as before) ...
    pass

def format_as_json_report(records: List[ParsedRecord], output_path: str):
    # ... (omitting for brevity, same as before) ...
    pass

# --- API Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/config", response_class=JSONResponse)
async def get_config():
    """
    Returns the current Presidio configuration, augmented with details
    about the recognizers for the UI, by using the PresidioService.
    """
    config_service = ConfigService()
    config = config_service.load_config()
    presidio_config = config.get("presidio", {})

    # Instantiate the service to get detailed recognizer info
    presidio_service = PresidioService(presidio_config)

    # Get the detailed entity map from the service
    detailed_entities = presidio_service.get_recognizer_details()

    # Replace the simple entity map in the config with our new detailed one
    if detailed_entities:
        presidio_config["analyzer"]["entities"] = detailed_entities

    return presidio_config

@app.post("/api/config", response_class=JSONResponse)
async def save_config(update_request: ConfigUpdateRequest):
    config_service = ConfigService()
    full_config = config_service.load_config()
    full_config["presidio"] = update_request.presidio
    if config_service.save_config(full_config):
        return {"status": "success", "message": "Configuration saved successfully."}
    else:
        return JSONResponse(status_code=500, content={"status": "error", "message": "Failed to save configuration."})

@app.post("/api/preview", response_class=JSONResponse)
async def preview_anonymization(preview_request: PreviewRequest):
    """
    Anonymizes a sample text based on the provided Presidio configuration
    using the centralized PresidioService.
    """
    presidio_config = preview_request.presidio_config
    sample_text = preview_request.sample_text
    if not sample_text:
        return JSONResponse(content={"anonymized_text": ""})

    try:
        presidio_service = PresidioService(presidio_config)

        if not presidio_service.is_enabled:
            return JSONResponse(content={"anonymized_text": "[PREVIEW] Presidio is disabled."})

        analyzer_config = presidio_config.get("analyzer", {})
        enabled_entities = [k for k, v in analyzer_config.get("entities", {}).items() if v.get('enabled')]

        ad_hoc_recognizers = analyzer_config.get('ad_hoc_recognizers', [])
        for rec in ad_hoc_recognizers:
            if rec.get("name") and rec.get("name") not in enabled_entities:
                enabled_entities.append(rec.get("name"))

        if not enabled_entities:
            return JSONResponse(content={"anonymized_text": "[PREVIEW] No entities enabled."})

        anonymized_text = presidio_service.anonymize_text(
            sample_text,
            language=analyzer_config.get("languages", ["en"])[0],
            entities=enabled_entities
        )

        return JSONResponse(content={"anonymized_text": anonymized_text})
    except Exception as e:
        import traceback
        return JSONResponse(status_code=500, content={"error": f"An error occurred during preview: {traceback.format_exc()}"})

@app.post("/api/analysis/{analysis_type}")
async def run_analysis(analysis_type: str, request: AnalysisRequest):
    # This function remains largely the same, but uses PresidioService
    config_service = ConfigService()
    config = config_service.load_config()

    log_reader = LogReader(config)
    parser_chain = create_parser_chain(config)
    drain3_service = Drain3Service(config)
    presidio_service = PresidioService(config.get('presidio', {}))

    input_path = os.path.join("examples", request.input_file)
    if not os.path.exists(input_path):
        return JSONResponse(status_code=404, content={"error": "Input file not found."})

    all_records: List[ParsedRecord] = []
    for line_num, line_content in log_reader.read_lines(input_path):
        if not line_content: continue

        log_entry = LogEntry(line_number=line_num, content=line_content, source_file=input_path)
        parsed_record = parser_chain.handle(log_entry)

        if parsed_record:
            parsed_record.presidio_anonymized = presidio_service.anonymize_text(
                parsed_record.original_content,
                language=config.get('presidio', {}).get('analyzer', {}).get('languages', ['en'])[0]
            )
            parsed_record.presidio_metadata = []
            all_records.append(parsed_record)

    # ... (rest of the function for drain3 and file output, same as before) ...
    return JSONResponse(content={"message": "Analysis complete, but file output logic omitted for brevity."})
