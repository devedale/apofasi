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
from typing import Optional

class AdHocRecognizer(BaseModel):
    name: str
    regex: str
    score: float
    strategy: Optional[str] = 'replace'

class PreviewRequest(BaseModel):
    sample_text: str
    presidio_config: Dict[str, Any]

# ConfigUpdateRequest is no longer needed if the frontend sends the whole object
# but we'll keep it for the /api/config endpoint which is more specific.
class ConfigUpdateRequest(BaseModel):
    presidio: Dict[str, Any]


# --- API Endpoints ---

@app.get("/api/debug-info", response_class=JSONResponse)
async def get_debug_info():
    """
    Returns a collection of raw data for debugging the frontend and config issues.
    """
    debug_data = {}

    # 1. Get the raw config from the YAML file
    config_service = ConfigService()
    debug_data['raw_config'] = config_service.load_config()

    # 2. Try to inspect the Presidio recognizers
    try:
        language = debug_data.get('raw_config', {}).get("presidio", {}).get("analyzer", {}).get("language", "en")
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers(languages=[language])
        default_recognizers = registry.get_recognizers(language=language)

        recognizer_info = []
        for rec in default_recognizers:
            info = {
                "name": rec.name,
                "supported_entity": rec.supported_entity,
                "default_score": getattr(rec, 'default_score', 'N/A'),
                "is_pattern_recognizer": isinstance(rec, PatternRecognizer)
            }
            if isinstance(rec, PatternRecognizer):
                info["patterns"] = [p.regex for p in rec.patterns]
            recognizer_info.append(info)
        debug_data['inspected_recognizers'] = recognizer_info
    except Exception as e:
        debug_data['recognizer_inspection_error'] = str(e)

    return debug_data

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/config", response_class=JSONResponse)
async def get_config():
    """
    Returns the current Presidio configuration, augmented with details
    about the recognizers for the UI. This version is more robust.
    """
    config_service = ConfigService()
    config = config_service.load_config()
    presidio_config = config.get("presidio", {})

    # Load user's saved settings for quick lookup
    user_entities = presidio_config.get("analyzer", {}).get("entities", {})
    user_strategies = presidio_config.get("anonymizer", {}).get("strategies", {})

    # This will be the new, detailed map of entities for the UI
    detailed_entities_for_frontend = {}

    try:
        language = presidio_config.get("analyzer", {}).get("language", "en")
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers(languages=[language])
        default_recognizers = registry.get_recognizers(language=language)

        for rec in default_recognizers:
            if not hasattr(rec, 'supported_entity'):
                continue

            entity_name = rec.supported_entity

            # Get saved state or use defaults
            # If an entity is not in the user's config, it's considered disabled by default for clarity in the UI
            is_enabled = user_entities.get(entity_name, False)
            strategy = user_strategies.get(entity_name, "replace")

            score = getattr(rec, 'default_score', 0.0)

            detailed_entities_for_frontend[entity_name] = {
                "enabled": is_enabled,
                "strategy": strategy,
                "score": score if isinstance(score, (int, float)) else 0.0,
                "regex": "N/A (NLP or other logic)",
                "is_regex_based": False
            }

            if isinstance(rec, PatternRecognizer):
                detailed_entities_for_frontend[entity_name]["regex"] = "\n".join(p.regex for p in rec.patterns)
                detailed_entities_for_frontend[entity_name]["is_regex_based"] = True

    except Exception as e:
        # If inspection fails, we can't build the detailed list.
        # It's better to return an error than an empty or incomplete list.
        print(f"CRITICAL: Could not inspect Presidio recognizers to build UI. Error: {e}")
        # Returning the raw config so at least something might render, but this indicates a problem.
        return presidio_config

    # Replace the simple entity map in the config with our new detailed one
    if "analyzer" not in presidio_config: presidio_config["analyzer"] = {}
    presidio_config["analyzer"]["entities"] = detailed_entities_for_frontend

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
    from presidio_anonymizer import OperatorConfig

    config = preview_request.presidio_config
    sample_text = preview_request.sample_text

    if not sample_text:
        return JSONResponse(content={"anonymized_text": ""})

    try:
        language = config.get("analyzer", {}).get("language", "en")

        # 1. Create and configure the RecognizerRegistry
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers(languages=[language])

        # 2. Disable recognizers based on the provided config
        enabled_entities = {k for k, v in config.get("analyzer", {}).get("entities", {}).items() if v}
        all_recognizers = registry.get_recognizers(language=language)
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
        # Also add strategies for the ad-hoc recognizers
        for rec_conf in ad_hoc_recognizers:
            if rec_conf.get("name") and rec_conf.get("strategy"):
                anonymizers_config[rec_conf["name"]] = OperatorConfig(rec_conf["strategy"])

        # 6. Analyze and anonymize the sample text
        analyzer_results = analyzer.analyze(text=sample_text, language=language)
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
from pathlib import Path

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
    try:
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
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"An error occurred during analysis: {str(e)}"})
