import os
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

from logppt.sampling.hierachical_sampling import sampling
from logppt.data.data_loader import DataLoaderForPromptTuning
from logppt.models.roberta import RobertaForLogParsing
from logppt.trainer import TrainingArguments, Trainer
from logppt.parsing_base import template_extraction
from logppt.evaluation.evaluator_main import evaluator, prepare_results

class LogPPTService:
    def __init__(self, config, task_id, log_manager):
        self.config = config
        self.task_id = task_id
        self.log_manager = log_manager

    def log(self, message):
        self.log_manager.log(self.task_id, message)

    def run_pipeline(self, file_path: str, model_name: str, shots: list, max_train_steps: int, dataset_name: str = "custom", content_config: str = "", columns_order: str = ""):
        self.log("LogPPT pipeline started.")
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
                # Find all column names in the format string
                req_cols = [col[1:-1] for col in content_config.split('}') if '{' in col]
                for col in req_cols:
                    if col not in df.columns:
                         raise ValueError(f"Column '{col}' not found in the uploaded file.")
                df['Content'] = df.apply(lambda row: content_config.format(**row.to_dict()), axis=1)
            except Exception as e:
                raise ValueError(f"Error applying content_config: {e}. Make sure column names in your format string (e.g., {{message}}) exist in the CSV.")

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

        # 2. Sampling
        self.log("Starting sampling...")
        validation_file_path = run_dir / "validation.json"
        with open(validation_file_path, 'w') as f:
            for log, label in zip(raw_logs, labels):
                f.write(json.dumps({'log': log, 'template': label}) + '\n')

        sample_candidates = sampling(raw_logs, labels, shots)

        sample_files = {}
        for shot, samples in sample_candidates.items():
            sample_file_path = run_dir / f"samples_{shot}.json"
            sample_files[shot] = sample_file_path
            with open(sample_file_path, 'w') as f:
                for sample in samples:
                    f.write(json.dumps({'log': sample[0], 'template': sample[1]}) + '\n')

        first_shot = shots[0]
        train_file = sample_files[first_shot]
        self.log(f"Sampling complete. Using {first_shot} shots for training.")

        # 3. Training and Parsing
        self.log("Initializing model and data loader...")
        class SimpleArgs:
            def __init__(self, d):
                self.__dict__.update(d)

        data_args = SimpleArgs({
            "train_file": str(train_file),
            "validation_file": str(validation_file_path),
            "log_file": file_path,
            "dataset_name": dataset_name,
            "task_output_dir": str(results_dir)
        })

        model_path = Path("models") / model_name
        if not model_path.exists():
            raise ValueError(f"Model '{model_name}' not found. Please download it first from the 'Model Management' tab.")

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

        data_loader = DataLoaderForPromptTuning(data_args)
        p_model = RobertaForLogParsing(model_args.model_name_or_path, use_crf=model_args.use_crf)
        p_model.tokenizer = data_loader.initialize(p_model.tokenizer)
        data_loader.tokenize()
        data_loader.build_dataloaders(train_args.per_device_train_batch_size, train_args.per_device_eval_batch_size)
        param_label_words = data_loader.find_parameter_label_words(p_model.plm, common_args.no_label_words)
        p_model.add_label_token(param_label_words)

        training_args_obj = TrainingArguments(
            output_dir=common_args.output_dir,
            num_train_epochs=train_args.num_train_epochs,
            max_train_steps=train_args.max_train_steps,
        )

        trainer = Trainer(
            model=p_model,
            args=training_args_obj,
            train_loader=data_loader.get_train_dataloader(),
            eval_loader=data_loader.get_val_dataloader(),
            no_train_samples=len(data_loader.raw_datasets['train']),
            device='cpu'
        )

        self.log("Starting model training...")
        p_model = trainer.train()
        self.log("Model training complete.")
        trainer.save_pretrained(common_args.output_dir)
        self.log(f"Model saved to {common_args.output_dir}")

        self.log("Starting log parsing...")
        p_model.load_checkpoint(common_args.output_dir)
        log_lines = df['Content'].tolist()
        templates, _ = template_extraction(p_model, 'cpu', log_lines, vtoken=data_loader.vtoken)

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
        os.link(parsed_log_path, final_parsed_path)
        os.link(templates_path, final_templates_path)
        self.log("Output files created.")

        return {
            "evaluation": {"message": "Evaluation step not fully implemented. Parsed files are generated."},
            "parsed_log_url": f"/outputs/{final_parsed_path.name}",
            "templates_url": f"/outputs/{final_templates_path.name}"
        }
