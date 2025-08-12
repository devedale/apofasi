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
# We need to import the Presidio classes directly for the preview
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.ad_hoc_recognizer import AdHocRecognizer as PresidioAdHocRecognizer
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
    recognizers: List[AdHocRecognizer]

class ConfigUpdateRequest(BaseModel):
    presidio: Dict[str, Any]


# --- API Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/config", response_class=JSONResponse)
async def get_config():
    """Returns the current Presidio configuration."""
    config_service = ConfigService()
    config = config_service.load_config()
    presidio_config = config.get("presidio", {})

    # Ensure nested structures exist for the frontend
    if "analyzer" not in presidio_config:
        presidio_config["analyzer"] = {}
    if "ad_hoc_recognizers" not in presidio_config["analyzer"]:
        presidio_config["analyzer"]["ad_hoc_recognizers"] = []
    if "entities" not in presidio_config["analyzer"]:
        presidio_config["analyzer"]["entities"] = {}
    if "anonymizer" not in presidio_config:
        presidio_config["anonymizer"] = {}
    if "strategies" not in presidio_config["anonymizer"]:
        presidio_config["anonymizer"]["strategies"] = {}

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

@app.post("/api/preview", response_class=JSONResponse)
async def preview_anonymization(preview_request: PreviewRequest):
    """
    Performs a live preview of anonymization with temporary rules.
    This mimics the logic from the old ConfigDialog.
    """
    sample_text = preview_request.sample_text
    if not sample_text:
        return JSONResponse(content={"anonymized_text": ""})

    try:
        # 1. Create a temporary registry and analyzer engine
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers(languages=["en"])

        # 2. Add the unsaved ad-hoc recognizers from the request
        for rec in preview_request.recognizers:
            if rec.name and rec.regex:
                ad_hoc_recognizer = PresidioAdHocRecognizer(
                    supported_entity=rec.name,
                    patterns=[rec.regex],
                    name=f"Custom '{rec.name}'"
                )
                registry.add_recognizer(ad_hoc_recognizer)

        analyzer = AnalyzerEngine(registry=registry)
        anonymizer = AnonymizerEngine()

        # 3. Analyze and anonymize the sample text
        analyzer_results = analyzer.analyze(text=sample_text, language='en')
        anonymized_result = anonymizer.anonymize(
            text=sample_text,
            analyzer_results=analyzer_results
        )

        return JSONResponse(content={"anonymized_text": anonymized_result.text})

    except Exception as e:
        # Return a 500 error with a message
        return JSONResponse(status_code=500, content={"error": f"An error occurred during preview: {str(e)}"})
