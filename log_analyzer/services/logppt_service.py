import os
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import asyncio

# Import del nuovo servizio Ollama
from .ollama_service import OllamaService

class LogPPTService:
    """
    Servizio LogPPT aggiornato per utilizzare Ollama invece di Hugging Face.
    
    Questo servizio mantiene la compatibilità con l'interfaccia esistente
    ma utilizza Ollama per il parsing dei log invece dei modelli Hugging Face.
    """
    
    def __init__(self, config, task_id, log_manager):
        self.config = config
        self.task_id = task_id
        self.log_manager = log_manager
        
        # Inizializza il servizio Ollama
        self.ollama_service = OllamaService(config, task_id, log_manager)

    def log(self, message):
        self.log_manager.log(self.task_id, message)

    def run_pipeline(self, file_path: str, model_name: str, shots: list, max_train_steps: int, dataset_name: str = "custom", content_config: str = "", columns_order: str = ""):
        """
        Esegue la pipeline LogPPT utilizzando Ollama per il parsing dei log.
        
        Questo metodo sostituisce l'implementazione precedente basata su Hugging Face
        con un approccio che utilizza Ollama per il parsing dei log.
        """
        self.log("LogPPT pipeline started (Ollama mode).")
        
        # Convert shots to list if it's a string
        if isinstance(shots, str):
            try:
                shots = [int(s.strip()) for s in shots.split(',')]
                self.log(f"Converted shots string '{shots}' to list: {shots}")
            except ValueError as e:
                raise ValueError(f"Invalid shots format. Expected comma-separated numbers, got: {shots}")
        
        # Verifica che Ollama sia disponibile
        try:
            ollama_health = asyncio.run(self.ollama_service.health_check())
            if not ollama_health:
                error_msg = "Ollama service is not available. Please ensure Docker Compose is running and Ollama container is healthy."
                self.log(f"ERROR: {error_msg}")
                raise ValueError(error_msg)
            self.log("Ollama service is healthy and available.")
        except Exception as e:
            error_msg = f"Failed to connect to Ollama service: {str(e)}"
            self.log(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
        
        # Verifica che il modello richiesto esista in Ollama
        try:
            available_models = asyncio.run(self.ollama_service.list_models())
            model_exists = any(model["name"].startswith(model_name) for model in available_models)
            
            if not model_exists:
                # Prova a scaricare il modello se è uno di quelli predefiniti
                available_model_names = list(self.ollama_service.get_available_models_info().keys())
                if model_name in available_model_names:
                    self.log(f"Model '{model_name}' not found in Ollama. Attempting to download...")
                    download_result = asyncio.run(self.ollama_service.download_model(model_name))
                    if not download_result.get("success", False):
                        error_msg = f"Failed to download model '{model_name}': {download_result.get('error', 'Unknown error')}"
                        self.log(f"ERROR: {error_msg}")
                        raise ValueError(error_msg)
                    self.log(f"Model '{model_name}' downloaded successfully.")
                else:
                    available_models_str = ", ".join([m["name"] for m in available_models])
                    error_msg = (
                        f"Model '{model_name}' not found in Ollama. "
                        f"Available models: {available_models_str}. "
                        f"Please download the model first from the 'Model Management' tab."
                    )
                    self.log(f"ERROR: {error_msg}")
                    raise ValueError(error_msg)
            else:
                self.log(f"Model '{model_name}' found in Ollama.")
        except Exception as e:
            if "not found in Ollama" in str(e) or "Failed to download model" in str(e):
                raise e
            error_msg = f"Failed to verify model availability: {str(e)}"
            self.log(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
        
        # Con Ollama non abbiamo bisogno dei moduli LogPPT complessi
        # L'elaborazione avviene direttamente tramite le API di Ollama
        self.log("Using Ollama for log parsing - skipping traditional LogPPT model imports.")
        
        # Create a temporary directory for this run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = Path("temp_runs") / f"logppt_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)

        results_dir = run_dir / "results"
        results_dir.mkdir(exist_ok=True)

        # 1. Read and Preprocess the uploaded log file (CSV or plain text)
        self.log("Reading and preprocessing the log file...")
        file_ext = Path(file_path).suffix.lower()
        try:
            if file_ext == '.csv':
                df = pd.read_csv(file_path)
                self.log(f"Successfully read CSV with {len(df)} rows.")
            else:
                # Treat as plain text log: one line per record
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = [line.rstrip('\n') for line in f]
                df = pd.DataFrame({'Content': lines})
                self.log(f"Successfully read plain text with {len(df)} lines; created 'Content' column.")
        except Exception as e:
            raise ValueError(f"Could not read the uploaded file: {e}")

        if content_config:
            self.log("Applying content configuration...")
            try:
                # Find all column names in the format string using regex
                import re
                pattern = r'\{([^}]+)\}'
                req_cols = re.findall(pattern, content_config)
                self.log(f"Found column names in content_config: {req_cols}")
                
                for col in req_cols:
                    if col not in df.columns:
                         raise ValueError(f"Column '{col}' not found in the uploaded file. Available columns: {list(df.columns)}")
                
                df['Content'] = df.apply(lambda row: content_config.format(**row.to_dict()), axis=1)
                self.log(f"Successfully applied content configuration. Content column created with {len(df)} rows.")
            except Exception as e:
                raise ValueError(f"Error applying content_config: {e}. Make sure column names in your format string (e.g., {{message}}) exist in the CSV.")
        else:
            self.log("No content configuration provided, checking for existing 'Content' column...")
            if 'Content' not in df.columns:
                # If it's plain log without structuring, we already created Content; otherwise fail gracefully
                raise ValueError("No 'Content' column found and no content configuration provided. Please either: 1) Include a 'Content' column in your CSV, or 2) Provide a content configuration to construct it from other columns.")
            self.log("Using existing 'Content' column from CSV")

        if 'Content' not in df.columns:
            raise ValueError("The CSV must contain a 'Content' column, or you must define it using the Content Field Configuration.")

        if 'EventTemplate' not in df.columns:
            # If there is no ground truth template, create a placeholder from content
            # This enables sampling/training even on unstructured logs, aligned with LogPPT examples
            df['EventTemplate'] = df['Content']

        if columns_order:
            try:
                ordered_cols = [col.strip() for col in columns_order.split(',')]
                # Ensure essential columns are present if they were in the original df
                for col in ['Content', 'EventTemplate']:
                    if col not in ordered_cols and col in df.columns:
                        ordered_cols.append(col)
                df = df[ordered_cols]
            except KeyError as e:
                raise ValueError(f"Error applying columns_order: Column {e} not found in the CSV.")

        # The rest of the pipeline uses the preprocessed df
        self.log("Preprocessing complete.")
        raw_logs = df['Content'].tolist()
        labels = df['EventTemplate'].tolist()
        
        # Validate data size vs shots
        max_shot = max(shots)
        if len(raw_logs) < max_shot:
            # Suggest appropriate shot sizes
            suggested_shots = []
            for shot in [1, 2, 3, 4, 5, 8, 16, 32]:
                if shot <= len(raw_logs):
                    suggested_shots.append(shot)
            
            if suggested_shots:
                suggested_str = ", ".join(map(str, suggested_shots))
                error_msg = f"Data size ({len(raw_logs)}) is smaller than requested shots ({max_shot}). Suggested shot sizes: {suggested_str}"
            else:
                error_msg = f"Data size ({len(raw_logs)}) is too small for any meaningful sampling. Minimum 1 entry required."
            
            self.log(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
        
        # Additional validation: check if shots are reasonable for the data size
        if max_shot > len(raw_logs) * 0.5:
            self.log(f"Warning: Requested shots ({max_shot}) are very large compared to data size ({len(raw_logs)}). This may result in poor sampling quality.")
        
        self.log(f"Data validation passed: {len(raw_logs)} entries available for {max_shot} shots")

        # 2. Sampling (semplificato per Ollama)
        self.log("Starting sampling phase...")
        self.log(f"Preparing to sample {len(raw_logs)} log entries with shots: {shots}")
        
        # Salva i dati di validazione
        validation_file_path = run_dir / "validation.json"
        with open(validation_file_path, 'w') as f:
            for log, label in zip(raw_logs, labels):
                f.write(json.dumps({'log': log, 'template': label}) + '\n')
        self.log(f"Validation file created at {validation_file_path}")

        # Con Ollama usiamo un approccio più semplice per il sampling
        # Prendiamo i primi N samples come "training examples" per il context
        first_shot = shots[0] if shots else min(16, len(raw_logs))
        sample_size = min(first_shot, len(raw_logs))
        
        sample_logs = raw_logs[:sample_size]
        sample_templates = labels[:sample_size]
        
        self.log(f"Using first {sample_size} entries as training context for Ollama")

        # 3. Parsing con Ollama (sostituisce training + parsing)
        self.log("Starting Ollama-based log parsing...")
        self.log(f"Using model '{model_name}' for parsing {len(raw_logs)} log entries")
        
        try:
            # Parsing tramite Ollama
            parsing_results = asyncio.run(
                self.ollama_service.parse_log_batch(raw_logs, model_name)
            )
            
            # Estrai i template dalla risposta di Ollama
            templates = []
            parsing_metadata = []
            
            for i, result in enumerate(parsing_results):
                if result.get("success", False):
                    parsed_data = result.get("result", {})
                    template = parsed_data.get("template", raw_logs[i])
                    templates.append(template)
                    parsing_metadata.append({
                        "success": True,
                        "fields": parsed_data.get("fields", {}),
                        "raw_response": result.get("raw_response", "")
                    })
                else:
                    # Fallback in caso di errore
                    templates.append(raw_logs[i])
                    parsing_metadata.append({
                        "success": False,
                        "error": result.get("error", "Unknown error"),
                        "raw_response": ""
                    })
                
                # Progress logging
                if (i + 1) % 50 == 0:
                    self.log(f"Parsed {i + 1}/{len(raw_logs)} log entries")
            
            self.log(f"Ollama parsing completed for {len(templates)} entries")
            
        except Exception as e:
            error_msg = f"Ollama parsing failed: {str(e)}"
            self.log(f"ERROR: {error_msg}")
            raise ValueError(error_msg)

        # Aggiorna il DataFrame con i risultati
        df['EventTemplate_parsed'] = pd.Series(templates)
        df['ParsedMetadata'] = pd.Series([json.dumps(meta) for meta in parsing_metadata])

        # Salva i risultati
        parsed_log_path = results_dir / f"{dataset_name}_parsed_log.csv"
        df.to_csv(parsed_log_path, index=False)
        self.log(f"Parsed log saved to {parsed_log_path}")

        # Crea il summary dei template
        counter = pd.Series(templates).value_counts()
        template_df = pd.DataFrame({'EventTemplate': counter.index, 'Occurrence': counter.values})
        templates_path = results_dir / f"{dataset_name}_templates.csv"
        template_df.to_csv(templates_path, index=False)
        self.log(f"Templates summary saved to {templates_path}")

        # Copia i file nella directory outputs per renderli scaricabili
        final_parsed_path = Path("outputs") / parsed_log_path.name
        final_templates_path = Path("outputs") / templates_path.name
        
        import shutil
        try:
            shutil.copy2(parsed_log_path, final_parsed_path)
            shutil.copy2(templates_path, final_templates_path)
            self.log("Output files created successfully in outputs directory.")
        except Exception as copy_error:
            self.log(f"Warning: Could not copy output files: {copy_error}")
            # Fallback: usa i path originali
            final_parsed_path = parsed_log_path
            final_templates_path = templates_path
            self.log("Using original file paths for download.")

        # Calcola alcune statistiche
        successful_parses = sum(1 for meta in parsing_metadata if meta["success"])
        success_rate = (successful_parses / len(parsing_metadata)) * 100 if parsing_metadata else 0
        unique_templates = len(counter)
        
        self.log(f"Parsing Statistics:")
        self.log(f"- Total entries processed: {len(raw_logs)}")
        self.log(f"- Successful parses: {successful_parses}/{len(parsing_metadata)} ({success_rate:.1f}%)")
        self.log(f"- Unique templates found: {unique_templates}")
        self.log("LogPPT pipeline completed successfully using Ollama.")

        return {
            "evaluation": {
                "message": f"Ollama-based parsing completed. Success rate: {success_rate:.1f}% ({successful_parses}/{len(parsing_metadata)})",
                "total_entries": len(raw_logs),
                "successful_parses": successful_parses,
                "success_rate": success_rate,
                "unique_templates": unique_templates
            },
            "parsed_log_url": f"/outputs/{final_parsed_path.name}",
            "templates_url": f"/outputs/{final_templates_path.name}"
        }
