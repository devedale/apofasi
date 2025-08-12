import sys
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Dict, Any

# Adjust the path to allow imports from the parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from log_analyzer.services.config_service import ConfigService
from log_analyzer.parsing.interfaces import ParsedRecord
# We need to import the Presidio classes directly for the preview
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, Pattern, PatternRecognizer
from presidio_anonymizer import AnonymizerEngine

# --- FastAPI App Initialization ---
app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="log_analyzer/web/static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="log_analyzer/web/templates")

# --- Pydantic Models for API requests ---
class AdHocRecognizer(BaseModel):
    name: str
    regex: str
    score: float

class PreviewRequest(BaseModel):
    sample_text: str
    presidio_config: Dict[str, Any]

# ConfigUpdateRequest is no longer needed if the frontend sends the whole object
# but we'll keep it for the /api/config endpoint which is more specific.
class ConfigUpdateRequest(BaseModel):
    presidio: Dict[str, Any]


# --- API Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/config", response_class=JSONResponse)
async def get_config():
    """
    Returns the current Presidio configuration, augmented with details
    about the recognizers for the UI.
    """
    config_service = ConfigService()
    config = config_service.load_config()
    presidio_config = config.get("presidio", {})

    # --- Augment entity info with regex data ---
    # 1. Load default recognizers to inspect them
    registry = RecognizerRegistry()
    registry.load_predefined_recognizers(languages=["en"])
    default_recognizers = registry.get_recognizers()

    # 2. Create a map of entity -> regex for pattern-based recognizers
    entity_to_regex = {}
    for rec in default_recognizers:
        if isinstance(rec, PatternRecognizer):
            # For simplicity, we'll join multiple patterns with a newline
            regex_str = "\n".join(p.regex for p in rec.patterns)
            entity_to_regex[rec.supported_entity] = regex_str

    # 3. Build the detailed entities object for the frontend
    detailed_entities = {}

    # Ensure nested structures exist
    analyzer_config = presidio_config.get("analyzer", {})
    anonymizer_config = presidio_config.get("anonymizer", {})
    entities_map = analyzer_config.get("entities", {})
    strategies_map = anonymizer_config.get("strategies", {})

    for entity, enabled in entities_map.items():
        detailed_entities[entity] = {
            "enabled": enabled,
            "strategy": strategies_map.get(entity, "replace"),
            "regex": entity_to_regex.get(entity, "N/A (Uses NLP or other logic)"),
            "is_regex_based": entity in entity_to_regex
        }

    # Update the config object that will be returned
    presidio_config["analyzer"]["entities"] = detailed_entities

    return presidio_config

@app.post("/api/config", response_class=JSONResponse)
async def save_config(update_request: ConfigUpdateRequest):
    """Saves the updated Presidio configuration."""
    config_service = ConfigService()
    # Load the full config to avoid overwriting other sections
    full_config = config_service.load_config()
    # Update only the 'presidio' part
    full_config["presidio"] = update_request.presidio

    if config_service.save_config(full_config):
        return {"status": "success", "message": "Configuration saved successfully."}
    else:
        return JSONResponse(status_code=500, content={"status": "error", "message": "Failed to save configuration."})

# --- Sample File Endpoints ---

@app.get("/api/sample-files", response_class=JSONResponse)
async def get_sample_files():
    """Scans the 'examples' directory and returns a list of file names."""
    examples_dir = "examples"
    try:
        files = [f for f in os.listdir(examples_dir) if os.path.isfile(os.path.join(examples_dir, f))]
        return {"files": files}
    except FileNotFoundError:
        return JSONResponse(status_code=404, content={"error": "Examples directory not found."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/sample-line", response_class=JSONResponse)
async def get_sample_line(filepath: str, line_number: int = 1):
    """Returns a specific line from a file in the 'examples' directory."""
    if not filepath:
        return JSONResponse(status_code=400, content={"error": "Filepath is required."})

    # Security: Ensure the path is within the 'examples' directory
    examples_dir = os.path.abspath("examples")
    requested_path = os.path.abspath(os.path.join(examples_dir, os.path.basename(filepath)))

    if not requested_path.startswith(examples_dir):
        return JSONResponse(status_code=403, content={"error": "Access to the requested file is forbidden."})

    try:
        with open(requested_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i + 1 == line_number:
                    return {"line_content": line.strip()}
            # If the line number is out of bounds
            return JSONResponse(status_code=404, content={"error": f"Line {line_number} not found in file."})
    except FileNotFoundError:
        return JSONResponse(status_code=404, content={"error": "File not found."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/preview", response_class=JSONResponse)
async def preview_anonymization(preview_request: PreviewRequest):
    """
    Performs a live preview of anonymization using the full, unsaved UI configuration.
    """
    from presidio_anonymizer.entities import OperatorConfig

    config = preview_request.presidio_config
    sample_text = preview_request.sample_text

    if not sample_text:
        return JSONResponse(content={"anonymized_text": ""})

    try:
        # 1. Create and configure the RecognizerRegistry
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers(languages=["en"])

        # 2. Disable recognizers based on the provided config
        enabled_entities = {k for k, v in config.get("analyzer", {}).get("entities", {}).items() if v}
        all_recognizers = registry.get_recognizers()
        recognizers_to_remove = [
            rec.name for rec in all_recognizers if rec.supported_entity not in enabled_entities
        ]
        for rec_name in recognizers_to_remove:
            registry.remove_recognizer(rec_name)

        # 3. Add the ad-hoc recognizers from the config
        ad_hoc_recognizers = config.get('analyzer', {}).get('ad_hoc_recognizers', [])
        for rec_conf in ad_hoc_recognizers:
            if rec_conf.get("name") and rec_conf.get("regex"):
                pattern = Pattern(
                    name=f"Custom '{rec_conf['name']}'",
                    regex=rec_conf['regex'],
                    score=rec_conf['score']
                )
                recognizer = PatternRecognizer(
                    supported_entity=rec_conf['name'],
                    patterns=[pattern]
                )
                registry.add_recognizer(recognizer)

        # 4. Create the Analyzer and Anonymizer engines
        analyzer = AnalyzerEngine(registry=registry)
        anonymizer = AnonymizerEngine()

        # 5. Configure anonymizer strategies
        strategies = config.get('anonymizer', {}).get('strategies', {})
        anonymizers_config = {
            entity: OperatorConfig(strategy) for entity, strategy in strategies.items()
        }

        # 6. Analyze and anonymize the sample text
        analyzer_results = analyzer.analyze(text=sample_text, language='en')
        anonymized_result = anonymizer.anonymize(
            text=sample_text,
            analyzer_results=analyzer_results,
            anonymizers=anonymizers_config
        )

        return JSONResponse(content={"anonymized_text": anonymized_result.text})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"An error occurred during preview: {str(e)}"})


# --- Analysis Endpoints ---
from log_analyzer.services.log_processing_service import LogProcessingService
import json
import csv
from datetime import datetime

# Mount the outputs directory to serve generated files
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

class AnalysisRequest(BaseModel):
    input_file: str

def format_as_anonymized_text(records: List[ParsedRecord], output_path: str):
    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(f"{record.presidio_anonymized}\n")

def format_as_logppt(records: List[ParsedRecord], output_path: str):
    if not records:
        return

    # Dynamically determine all possible parsed keys
    all_keys = set()
    for record in records:
        all_keys.update(record.parsed_data.keys())

    sorted_keys = sorted(list(all_keys))
    headers = ["LineId", "Timestamp"] + sorted_keys + ["Content", "EventId", "Template"]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()

        for record in records:
            row = {
                "LineId": record.line_number,
                "Timestamp": record.timestamp,
                "Content": record.unparsed_content,
                "EventId": record.drain3_anonymized.get("cluster_id", "N/A"),
                "Template": record.drain3_anonymized.get("template_mined", "N/A")
            }
            # Add all parsed keys, filling missing ones with empty string
            for key in sorted_keys:
                row[key] = record.parsed_data.get(key, "")

            writer.writerow(row)

def format_as_json_report(records: List[ParsedRecord], output_path: str):
    report = [record.model_dump() for record in records]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

@app.post("/api/analysis/{analysis_type}")
async def run_analysis(analysis_type: str, request: AnalysisRequest):
    """Runs a specific analysis type on an input file."""
    config_service = ConfigService()
    config = config_service.load_config()
    processing_service = LogProcessingService(config)

    input_path = os.path.join("examples", request.input_file)
    if not os.path.exists(input_path):
        return JSONResponse(status_code=404, content={"error": "Input file not found."})

    # Generate a unique output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{Path(request.input_file).stem}_{analysis_type}_{timestamp}"

    # Process the file to get the records
    records = processing_service.process_files([input_path])

    if analysis_type == "anonymize":
        output_filename += ".log"
        output_path = os.path.join("outputs", output_filename)
        format_as_anonymized_text(records, output_path)
    elif analysis_type == "logppt":
        output_filename += ".csv"
        output_path = os.path.join("outputs", output_filename)
        format_as_logppt(records, output_path)
    elif analysis_type == "json_report":
        output_filename += ".json"
        output_path = os.path.join("outputs", output_filename)
        format_as_json_report(records, output_path)
    else:
        return JSONResponse(status_code=400, content={"error": "Invalid analysis type."})

    return {"download_url": f"/outputs/{output_filename}"}
