import sys
import os
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# --- Path Setup ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# --- Direct Imports ---
from log_analyzer.services.config_service import ConfigService
from log_analyzer.parsing.interfaces import LogEntry, ParsedRecord
from log_analyzer.parsing.parser_factory import create_parser_chain
from log_analyzer.services.log_reader import LogReader
from log_analyzer.services.drain3_service import Drain3Service
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, Pattern, PatternRecognizer
from presidio_anonymizer import AnonymizerEngine, OperatorConfig

# --- FastAPI App Initialization ---
app = FastAPI()
app.mount("/static", StaticFiles(directory="log_analyzer/web/static"), name="static")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
templates = Jinja2Templates(directory="log_analyzer/web/templates")

# --- Pydantic Models ---
class AdHocRecognizer(BaseModel):
    name: str
    regex: str
    score: float
    strategy: Optional[str] = 'replace'

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
    if not records: return
    all_keys = set()
    for record in records:
        if record.parsed_data: all_keys.update(record.parsed_data.keys())
    sorted_keys = sorted(list(all_keys))
    headers = ["LineId", "Timestamp"] + sorted_keys + ["Content", "EventId", "Template"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for record in records:
            drain_result = record.drain3_anonymized or {}
            row = {"LineId": record.line_number, "Timestamp": record.timestamp, "Content": record.unparsed_content, "EventId": drain_result.get("cluster_id", "N/A"), "Template": drain_result.get("template_mined", "N/A")}
            for key in sorted_keys:
                row[key] = record.parsed_data.get(key, "")
            writer.writerow(row)

def format_as_json_report(records: List[ParsedRecord], output_path: str):
    report = [record.model_dump(exclude_none=True) for record in records]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

# --- API Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
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
    language = presidio_config.get("analyzer", {}).get("language", "en")

    detailed_entities = {}

    try:
        # Instead of using the registry directly, initialize a full analyzer
        analyzer = AnalyzerEngine(supported_languages=[language])
        default_recognizers = analyzer.get_recognizers(language=language)

        for rec in default_recognizers:
            if not hasattr(rec, 'supported_entity'): continue

            entity_name = rec.supported_entity
            is_enabled = user_entities.get(entity_name, True) # Default to enabled
            strategy = user_strategies.get(entity_name, "replace")
            score = getattr(rec, 'default_score', 0.0)

            detailed_entities[entity_name] = {
                "enabled": is_enabled,
                "strategy": strategy,
                "score": score if isinstance(score, (int, float)) else 0.0,
                "regex": "N/A (NLP or other logic)",
                "is_regex_based": False
            }

            if isinstance(rec, PatternRecognizer):
                detailed_entities[entity_name]["regex"] = "\\n".join(p.regex for p in rec.patterns)
                detailed_entities[entity_name]["is_regex_based"] = True

    except Exception as e:
        import traceback
        print(f"ERROR in get_config while inspecting recognizers: {traceback.format_exc()}")
        # If inspection fails, fall back to just returning the raw config from the file.
        # The UI will be less rich, but it won't be empty.
        return presidio_config

    # Replace the simple entity map in the config with our new detailed one
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

@app.get("/api/sample-files", response_class=JSONResponse)
async def get_sample_files():
    examples_dir = "examples"
    try:
        files = [f for f in os.listdir(examples_dir) if os.path.isfile(os.path.join(examples_dir, f))]
        return {"files": files}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/sample-line", response_class=JSONResponse)
async def get_sample_line(filepath: str, line_number: int = 1):
    examples_dir = os.path.abspath("examples")
    requested_path = os.path.abspath(os.path.join(examples_dir, os.path.basename(filepath)))
    if not requested_path.startswith(examples_dir):
        return JSONResponse(status_code=403, content={"error": "Access forbidden."})
    try:
        with open(requested_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i + 1 == line_number: return {"line_content": line.strip()}
        return JSONResponse(status_code=404, content={"error": f"Line {line_number} not found."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/preview", response_class=JSONResponse)
async def preview_anonymization(preview_request: PreviewRequest):
    config = preview_request.presidio_config
    sample_text = preview_request.sample_text
    if not sample_text: return JSONResponse(content={"anonymized_text": ""})
    try:
        language = config.get("analyzer", {}).get("language", "en")

        # Create a new analyzer engine for the preview
        analyzer = AnalyzerEngine(supported_languages=[language])

        # Get the default recognizers and remove the ones disabled by the user
        enabled_entities = {k for k, v in config.get("analyzer", {}).get("entities", {}).items() if v}
        default_recognizers = analyzer.get_recognizers(language=language)
        recognizers_to_remove = [rec for rec in default_recognizers if rec.supported_entity not in enabled_entities]
        analyzer.remove_recognizer(recognizers_to_remove)

        # Add the ad-hoc recognizers from the UI
        ad_hoc_recognizers = config.get('analyzer', {}).get('ad_hoc_recognizers', [])
        for rec_conf in ad_hoc_recognizers:
            if rec_conf.get("name") and rec_conf.get("regex"):
                pattern = Pattern(name=f"Custom '{rec_conf['name']}'", regex=rec_conf['regex'], score=rec_conf['score'])
                recognizer = PatternRecognizer(supported_entity=rec_conf['name'], patterns=[pattern])
                analyzer.add_recognizer(recognizer)

        # If no recognizers are active at all, return the original text.
        if not analyzer.get_recognizers(language=language):
            return JSONResponse(content={"anonymized_text": f"[PREVIEW] No entities enabled or defined. Original text: {sample_text}"})
        anonymizer = AnonymizerEngine()
        strategies = config.get('anonymizer', {}).get('strategies', {})
        anonymizers_config = {entity: OperatorConfig(strategy) for entity, strategy in strategies.items()}
        for rec_conf in ad_hoc_recognizers:
            if rec_conf.get("name") and rec_conf.get("strategy"):
                anonymizers_config[rec_conf["name"]] = OperatorConfig(rec_conf["strategy"])
        analyzer_results = analyzer.analyze(text=sample_text, language=language)
        anonymized_result = anonymizer.anonymize(text=sample_text, analyzer_results=analyzer_results, anonymizers=anonymizers_config)
        return JSONResponse(content={"anonymized_text": anonymized_result.text})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"An error occurred during preview: {str(e)}"})

@app.post("/api/analysis/{analysis_type}")
async def run_analysis(analysis_type: str, request: AnalysisRequest):
    try:
        config_service = ConfigService()
        config = config_service.load_config()
        log_reader = LogReader(config)
        parser_chain = create_parser_chain(config)
        drain3_service = Drain3Service(config)
        presidio_anonymizer = AnonymizerEngine()
        presidio_config = config.get('presidio', {})
        language = presidio_config.get("analyzer", {}).get("language", "en")
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers(languages=[language])
        presidio_analyzer = AnalyzerEngine(registry=registry)
        input_path = os.path.join("examples", request.input_file)
        if not os.path.exists(input_path):
            return JSONResponse(status_code=404, content={"error": "Input file not found."})
        all_records: List[ParsedRecord] = []
        for line_num, line_content in log_reader.read_lines(input_path):
            if not line_content: continue
            log_entry = LogEntry(line_number=line_num, content=line_content, source_file=input_path)
            parsed_record = parser_chain.handle(log_entry)
            if parsed_record:
                if presidio_config.get('enabled', False):
                    analyzer_results = presidio_analyzer.analyze(text=parsed_record.original_content, language=language)
                    conf_strategies = presidio_config.get('anonymizer', {}).get('strategies', {})
                    anonymizers_config = {entity: OperatorConfig(op) for entity, op in conf_strategies.items()}
                    anonymized_result = presidio_anonymizer.anonymize(text=parsed_record.original_content, analyzer_results=analyzer_results, anonymizers=anonymizers_config)
                    parsed_record.presidio_anonymized = anonymized_result.text
                    parsed_record.presidio_metadata = [res.to_dict() for res in analyzer_results]
                else:
                    parsed_record.presidio_anonymized = parsed_record.original_content
                all_records.append(parsed_record)
        original_content = [rec.original_content for rec in all_records]
        original_results = drain3_service.process_batch(original_content, 'original')
        anonymized_content = [rec.presidio_anonymized or "" for rec in all_records]
        anonymized_results = drain3_service.process_batch(anonymized_content, 'anonymized')
        for i, record in enumerate(all_records):
            if i < len(original_results): record.drain3_original = original_results[i]
            if i < len(anonymized_results): record.drain3_anonymized = anonymized_results[i]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename_base = f"{Path(request.input_file).stem}_{analysis_type}_{timestamp}"
        output_filename = ""
        if analysis_type == "anonymize":
            output_filename = f"{output_filename_base}.log"
            output_path = os.path.join("outputs", output_filename)
            format_as_anonymized_text(all_records, output_path)
        elif analysis_type == "logppt":
            output_filename = f"{output_filename_base}.csv"
            output_path = os.path.join("outputs", output_filename)
            format_as_logppt(all_records, output_path)
        elif analysis_type == "json_report":
            output_filename = f"{output_filename_base}.json"
            output_path = os.path.join("outputs", output_filename)
            format_as_json_report(all_records, output_path)
        else:
            return JSONResponse(status_code=400, content={"error": "Invalid analysis type."})
        return {"download_url": f"/outputs/{output_filename}"}
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": f"An error occurred during analysis: {str(e)}"})
