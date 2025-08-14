import os
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

# Remove problematic imports that cause startup errors
# These will be imported only when needed during runtime

class LogPPTService:
    def __init__(self, config, task_id, log_manager):
        self.config = config
        self.task_id = task_id
        self.log_manager = log_manager

    def log(self, message):
        self.log_manager.log(self.task_id, message)

    def run_pipeline(self, file_path: str, model_name: str, shots: list, max_train_steps: int, dataset_name: str = "custom", content_config: str = "", columns_order: str = ""):
        self.log("LogPPT pipeline started.")
        
        # Convert shots to list if it's a string
        if isinstance(shots, str):
            try:
                shots = [int(s.strip()) for s in shots.split(',')]
                self.log(f"Converted shots string '{shots}' to list: {shots}")
            except ValueError as e:
                raise ValueError(f"Invalid shots format. Expected comma-separated numbers, got: {shots}")
        
        # Check if model exists before starting the pipeline
        model_path = Path("models") / model_name
        if not model_path.exists():
            error_msg = (
                f"Model '{model_name}' not found. Please download it first from the 'Model Management' tab. "
                f"Go to the Model Management section and click 'Download Model' to download '{model_name}' from Hugging Face Hub."
            )
            self.log(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
        
        # Import required modules only when needed (lazy import)
        try:
            from logppt.sampling.hierachical_sampling import sampling
            from logppt.data.data_loader import DataLoaderForPromptTuning
            from logppt.models.roberta import RobertaForLogParsing
            from logppt.trainer import TrainingArguments, Trainer
            from logppt.parsing_base import template_extraction
            from logppt.evaluation.evaluator_main import evaluator, prepare_results
        except ImportError as e:
            error_msg = f"Failed to import required LogPPT modules. Make sure all dependencies are installed. Error: {str(e)}"
            self.log(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
        
        # Create a temporary directory for this run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = Path("temp_runs") / f"logppt_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)

        results_dir = run_dir / "results"
        results_dir.mkdir(exist_ok=True)

        # 1. Read and Preprocess the uploaded log file
        self.log("Reading and preprocessing the log file...")
        try:
            df = pd.read_csv(file_path)
            self.log(f"Successfully read {len(df)} lines.")
        except Exception as e:
            raise ValueError(f"Could not read the uploaded CSV file: {e}")

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
                raise ValueError("No 'Content' column found and no content configuration provided. Please either: 1) Include a 'Content' column in your CSV, or 2) Provide a content configuration to construct it from other columns.")
            self.log("Using existing 'Content' column from CSV")

        if 'Content' not in df.columns:
            raise ValueError("The CSV must contain a 'Content' column, or you must define it using the Content Field Configuration.")

        if 'EventTemplate' not in df.columns:
            # If there's no ground truth template, we can't do sampling in the same way.
            # For now, let's assume it's required for the demo.
            # We can create a dummy one for parsing-only tasks later.
            df['EventTemplate'] = df['Content'] # Use content as template if not present

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

        # 2. Sampling
        self.log("Starting sampling...")
        self.log(f"Preparing to sample {len(raw_logs)} log entries with shots: {shots}")
        
        validation_file_path = run_dir / "validation.json"
        with open(validation_file_path, 'w') as f:
            for log, label in zip(raw_logs, labels):
                f.write(json.dumps({'log': log, 'template': label}) + '\n')
        self.log(f"Validation file created at {validation_file_path}")

        self.log("Calling sampling function...")
        try:
            # Pass the logging function to sampling
            sample_candidates = sampling(raw_logs, labels, shots, log_func=self.log)
            self.log(f"Sampling completed successfully. Got samples for shots: {list(sample_candidates.keys())}")
        except Exception as e:
            self.log(f"ERROR: Sampling failed with error: {str(e)}")
            raise ValueError(f"Sampling failed: {str(e)}")

        sample_files = {}
        for shot, samples in sample_candidates.items():
            sample_file_path = run_dir / f"samples_{shot}.json"
            sample_files[shot] = sample_file_path
            with open(sample_file_path, 'w') as f:
                for sample in samples:
                    f.write(json.dumps({'log': sample[0], 'template': sample[1]}) + '\n')
            self.log(f"Sample file for {shot}-shot created at {sample_file_path} with {len(samples)} samples")

        first_shot = shots[0]
        if first_shot not in sample_files:
            # If the requested shot size is not available, use the largest available
            available_shots = list(sample_files.keys())
            if not available_shots:
                raise ValueError("No sample files generated. Sampling failed.")
            
            first_shot = max(available_shots)
            self.log(f"Requested shot size {shots[0]} not available. Using largest available: {first_shot}")
        
        train_file = sample_files[first_shot]
        self.log(f"Sampling complete. Using {first_shot} shots for training (requested: {shots[0]}).")

        # 3. Training and Parsing
        self.log("Initializing model and data loader...")
        class SimpleArgs:
            def __init__(self, d):
                self.__dict__.update(d)

        data_args = SimpleArgs({
            "train_file": str(train_file),
            "validation_file": str(validation_file_path),
            "dev_file": str(validation_file_path),  # Add dev_file attribute
            "log_file": file_path,
            "dataset_name": dataset_name,
            "task_output_dir": str(results_dir),
            "text_column_name": "log",  # Add text column name
            "label_column_name": "template"  # Add label column name
        })

        # Model path is already verified at the beginning
        model_args = SimpleArgs({
            "model_name_or_path": str(model_path),
            "use_crf": False
        })

        train_args = SimpleArgs({
            "num_train_epochs": 10,
            "max_train_steps": max_train_steps,
            "per_device_train_batch_size": 8,
            "per_device_eval_batch_size": 8,
            "lr_scheduler_type": "polynomial"
        })

        common_args = SimpleArgs({
            "output_dir": str(results_dir / "model"),
            "seed": 42,
            "no_label_words": 0,
            "parsing_num_processes": 1
        })

        # Initialize data loader and model
        try:
            self.log("Initializing data loader...")
            data_loader = DataLoaderForPromptTuning(data_args)
            
            self.log("Initializing RobertaForLogParsing model...")
            # Try to load from local path first, then from HuggingFace Hub
            try:
                if model_path.exists() and (model_path / "config.json").exists():
                    self.log(f"Loading model from local path: {model_path}")
                    model = RobertaForLogParsing.from_pretrained(str(model_path))
                    
                    # Ensure local model has tokenizer
                    if not hasattr(model, 'tokenizer') or model.tokenizer is None:
                        self.log("Local model has no tokenizer, creating one...")
                        from transformers import RobertaTokenizer
                        model.tokenizer = RobertaTokenizer.from_pretrained(model_name)
                else:
                    self.log(f"Local model not found, loading from HuggingFace Hub: {model_name}")
                    model = RobertaForLogParsing.from_pretrained(model_name)
                    
                    # Ensure HuggingFace model has tokenizer
                    if not hasattr(model, 'tokenizer') or model.tokenizer is None:
                        self.log("HuggingFace model has no tokenizer, creating one...")
                        from transformers import RobertaTokenizer
                        model.tokenizer = RobertaTokenizer.from_pretrained(model_name)
            except Exception as model_error:
                self.log(f"Failed to load model: {str(model_error)}")
                # Fallback: create a model using the HuggingFace hub directly
                self.log("Creating RobertaForLogParsing model from HuggingFace Hub...")
                try:
                    # Create model directly from HuggingFace hub (bypass local corruption)
                    model = RobertaForLogParsing(model_name)
                    
                    self.log("Model created successfully from HuggingFace Hub")
                    
                    # Suggest deleting corrupted local model
                    if model_path.exists():
                        self.log(f"WARNING: Local model at {model_path} appears to be corrupted.")
                        self.log("Consider deleting it from the Model Management tab and re-downloading.")
                    
                except Exception as fallback_error:
                    error_msg = f"Failed to create model from HuggingFace Hub: {str(fallback_error)}"
                    self.log(f"ERROR: {error_msg}")
                    raise ValueError(error_msg)
            
            # Ensure model has plm attribute for compatibility
            if not hasattr(model, 'plm'):
                self.log("Warning: Model missing plm attribute - this may cause issues")
            else:
                self.log("Model plm attribute verified")
            
            # Ensure CRF usage is explicitly disabled for stability on small datasets
            try:
                if hasattr(model, 'use_crf') and model.use_crf:
                    self.log("Disabling CRF (use_crf=False) for this run to avoid mask constraints on small batches")
                    model.use_crf = False
            except Exception:
                # Non-blocking: proceed even if attribute not present
                pass

            self.log("Setting up tokenizer and label tokens...")
            model.tokenizer = data_loader.initialize(model.tokenizer)
            data_loader.tokenize()
            data_loader.build_dataloaders(train_args.per_device_train_batch_size, train_args.per_device_eval_batch_size)
            
            self.log("Finding parameter label words...")
            try:
                param_label_words = data_loader.find_parameter_label_words(model.plm, common_args.no_label_words)
                self.log(f"Found parameter label words: {param_label_words}")
                model.add_label_token(param_label_words)
                self.log("Label tokens added to model successfully")
            except Exception as label_error:
                self.log(f"ERROR in find_parameter_label_words: {str(label_error)}")
                import traceback
                self.log(f"Traceback: {traceback.format_exc()}")
                raise label_error
            
            self.log("Model and data loader initialized successfully")
        except Exception as e:
            error_msg = f"Failed to initialize model '{model_name}'. The model may be corrupted or incomplete. Try deleting and re-downloading it from the Model Management tab. Error: {str(e)}"
            self.log(f"ERROR: {error_msg}")
            raise ValueError(error_msg)

        training_args_obj = TrainingArguments(
            output_dir=common_args.output_dir,
            num_train_epochs=train_args.num_train_epochs,
            max_train_steps=train_args.max_train_steps,
        )

        self.log("Creating Trainer instance...")
        try:
            trainer = Trainer(
                model=model,
                args=training_args_obj,
                train_loader=data_loader.get_train_dataloader(),
                eval_loader=data_loader.get_val_dataloader(),
                no_train_samples=len(data_loader.raw_datasets['train']),
                device='cpu'
            )
            self.log("Trainer created successfully")
        except Exception as trainer_error:
            self.log(f"ERROR creating Trainer: {str(trainer_error)}")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}")
            raise trainer_error

        self.log("Starting model training...")
        try:
            self.log("About to call trainer.train()...")
            
            # Force flush di tutti i buffer di output
            import sys
            sys.stdout.flush()
            sys.stderr.flush()
            
            model = trainer.train()
            self.log("trainer.train() completed successfully")
        except Exception as training_error:
            self.log("="*80)
            self.log("ERRORE CRITICO DURANTE IL TRAINING!")
            self.log("="*80)
            self.log(f"Tipo errore: {type(training_error).__name__}")
            self.log(f"Messaggio: {str(training_error)}")
            
            # Stack trace completo
            import traceback
            full_traceback = traceback.format_exc()
            self.log("STACK TRACE COMPLETO:")
            self.log(full_traceback)
            
            # Informazioni aggiuntive per il debug
            self.log(f"Modello in modalità training: {model.training}")
            self.log(f"Device del modello: {next(model.parameters()).device}")
            self.log(f"Numero di parametri del modello: {sum(p.numel() for p in model.parameters())}")
            
            # Force flush
            import sys
            sys.stdout.flush()
            sys.stderr.flush()
            
            self.log("="*80)
            raise training_error
        self.log("Model training complete.")
        trainer.save_pretrained(common_args.output_dir)
        self.log(f"Model saved to {common_args.output_dir}")

        self.log("Starting log parsing...")
        model.load_checkpoint(common_args.output_dir)
        log_lines = df['Content'].tolist()
        templates, _ = template_extraction(model, 'cpu', log_lines, vtoken=data_loader.vtoken)

        df['EventTemplate_parsed'] = pd.Series(templates)

        # Save the processed dataframe with the new templates
        parsed_log_path = results_dir / f"{dataset_name}_parsed_log.csv"
        df.to_csv(parsed_log_path, index=False)

        counter = pd.Series(templates).value_counts()
        template_df = pd.DataFrame({'EventTemplate': counter.index, 'Occurrence': counter.values})
        templates_path = results_dir / f"{dataset_name}_templates.csv"
        template_df.to_csv(templates_path, index=False)

        self.log("Log parsing complete.")
        # Create dummy output files in the main outputs dir to make them downloadable
        final_parsed_path = Path("outputs") / parsed_log_path.name
        final_templates_path = Path("outputs") / templates_path.name
        # Use copy instead of link to avoid cross-device issues in Docker
        import shutil
        try:
            shutil.copy2(parsed_log_path, final_parsed_path)
            shutil.copy2(templates_path, final_templates_path)
            self.log("Output files created successfully.")
        except Exception as copy_error:
            self.log(f"Warning: Could not copy output files: {copy_error}")
            # Fallback: use the original paths
            final_parsed_path = parsed_log_path
            final_templates_path = templates_path
            self.log("Using original file paths for download.")

        return {
            "evaluation": {"message": "Evaluation step not fully implemented. Parsed files are generated."},
            "parsed_log_url": f"/outputs/{final_parsed_path.name}",
            "templates_url": f"/outputs/{final_templates_path.name}"
        }
