import json
import sys
import importlib.util
import os
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

import pandas as pd


class LogPPT2Service:
    """
    Servizio che replica il workflow della demo di LogPPT (sampling → run → evaluate)
    ma utilizza esclusivamente Ollama per il parsing, evitando qualsiasi elaborazione remota.

    Passi supportati:
    - Preprocessing & validation.json
    - Sampling gerarchico (come 01_sampling.py)
    - "Training" (saltato, documentato nei log)
    - Parsing via Ollama su tutte le righe (come 02_run_logppt.py, ma senza RoBERTa)
    - Salvataggio risultati con stessa nomenclatura della demo
    - Valutazione semplice opzionale se \'EventTemplate\' è disponibile (acc. esatta)
    """

    def __init__(self, config: Dict[str, Any], task_id: str, log_manager):
        self.config = config or {}
        self.task_id = task_id
        self.log_manager = log_manager

    def log(self, message: str):
        self.log_manager.log(self.task_id, message)

    def _get_logppt2_config(self) -> Dict[str, Any]:
        default = {
            "dataset_dir": "examples",
            "ollama_url": os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434"),
            "model_name": "logppt-parser"
        }
        return {**default, **(self.config.get("logppt2") or {})}

    def run_pipeline(
        self,
        dataset_path: str,
        shots: List[int],
        evaluate: bool,
    ) -> Dict[str, Any]:
        self.log("[LogPPT 2] Pipeline avviata.")

        # Import on demand per evitare dipendenze pesanti all'avvio
        try:
            # Carica sampling dalla repo thirdparty evitando conflitti di package name
            sampling_file = Path("thirdparty/LogPPT/logppt/sampling/hierachical_sampling.py").resolve()
            if not sampling_file.exists():
                raise FileNotFoundError(f"Sampling module non trovato: {sampling_file}")
            spec_sampling = importlib.util.spec_from_file_location("thirdparty_logppt_sampling", str(sampling_file))
            if spec_sampling is None or spec_sampling.loader is None:
                raise ImportError("Impossibile creare spec per sampling")
            module_sampling = importlib.util.module_from_spec(spec_sampling)
            spec_sampling.loader.exec_module(module_sampling)  # type: ignore
            sampling = getattr(module_sampling, "sampling")

            # Carica LogPPTOllamaClient dal package locale evitando collisione con thirdparty/logppt
            client_file = Path("logppt/models/logppt_ollama_client.py").resolve()
            if not client_file.exists():
                raise FileNotFoundError(f"Client Ollama non trovato: {client_file}")
            spec_client = importlib.util.spec_from_file_location("local_logppt_ollama_client", str(client_file))
            if spec_client is None or spec_client.loader is None:
                raise ImportError("Impossibile creare spec per LogPPTOllamaClient")
            module_client = importlib.util.module_from_spec(spec_client)
            spec_client.loader.exec_module(module_client)  # type: ignore
            LogPPTOllamaClient = getattr(module_client, "LogPPTOllamaClient")
        except Exception as e:
            self.log(f"ERROR: Impossibile importare componenti LogPPT: {e}")
            raise

        dataset_path = Path(dataset_path)
        if not dataset_path.exists():
            raise ValueError(f"Dataset non trovato: {dataset_path}")

        # Prepara cartelle run/output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = Path("temp_runs") / f"logppt2_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)

        results_dir = run_dir / "results"
        results_dir.mkdir(parents=True, exist_ok=True)

        task_output_dir = results_dir / "logs"
        task_output_dir.mkdir(parents=True, exist_ok=True)

        # Lettura dataset: supporta .csv strutturato o .log/.txt non strutturato
        self.log("[LogPPT 2] Lettura dataset...")
        ext = dataset_path.suffix.lower()
        df = None
        if ext == '.csv':
            try:
                df = pd.read_csv(dataset_path)
            except Exception as e:
                raise ValueError(f"Errore lettura CSV: {e}")
            if 'Content' not in df.columns:
                raise ValueError("CSV senza colonna 'Content'. Per file non strutturati usa .log/.txt.")
        elif ext in ['.log', '.txt']:
            try:
                lines = []
                with open(dataset_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line = line.rstrip('\n')
                        if line:
                            lines.append(line)
                df = pd.DataFrame({'Content': lines})
            except Exception as e:
                raise ValueError(f"Errore lettura file di log: {e}")
        else:
            raise ValueError(f"Formato file non supportato: {ext}. Usa .csv, .log o .txt")

        has_ground_truth = 'EventTemplate' in df.columns
        if not has_ground_truth and ext in ['.log', '.txt']:
            # Se esiste un companion *_structured.csv nella stessa cartella, usalo per GT
            candidate = dataset_path.with_name(f"{dataset_path.stem}_structured.csv")
            if candidate.exists():
                try:
                    comp = pd.read_csv(candidate)
                    if 'EventTemplate' in comp.columns and 'Content' in comp.columns:
                        # Allinea GT per riga; se dimensioni diverse, ignora
                        if len(comp) == len(df):
                            df['EventTemplate'] = comp['EventTemplate']
                            has_ground_truth = True
                            self.log("[LogPPT 2] Ground truth ricavata da companion *_structured.csv")
                except Exception:
                    pass
        if not has_ground_truth:
            self.log("[LogPPT 2] Ground truth assente: valutazione/sampling disabilitati.")

        # Salva validation.json come nella demo
        self.log("[LogPPT 2] Creazione validation.json...")
        raw_logs = df['Content'].astype(str).tolist()
        labels = (df['EventTemplate'].astype(str).tolist() if has_ground_truth else [""] * len(raw_logs))
        validation_file_path = run_dir / "validation.json"
        with open(validation_file_path, 'w') as f:
            for log_line, label in zip(raw_logs, labels):
                f.write(json.dumps({"log": log_line, "template": label}) + "\n")

        # Sampling gerarchico come 01_sampling.py (solo se esiste GT)
        if has_ground_truth:
            self.log("[LogPPT 2] Avvio sampling gerarchico...")
            try:
                sample_candidates = sampling(raw_logs, labels, shots)
            except Exception as e:
                self.log(f"ERROR: Sampling fallito: {e}")
                raise

            for shot, samples in sample_candidates.items():
                shot_file = run_dir / f"samples_{shot}.json"
                with open(shot_file, 'w') as f:
                    for sample in samples:
                        f.write(json.dumps({"log": sample[0], "template": sample[1]}) + "\n")
                self.log(f"[LogPPT 2] Creato file di sample per {shot}-shot: {shot_file}")
        else:
            self.log("[LogPPT 2] Sampling saltato (nessuna ground truth).")

        # Nella demo il passo training allena RoBERTa: qui lo saltiamo esplicitamente
        self.log("[LogPPT 2] Training passo DEMO (02_run_logppt.py): SALTATO – si usa Ollama per parsing locale.")

        # Parsing via Ollama (equivalente logico al parsing della demo)
        cfg = self._get_logppt2_config()
        candidate_urls = [
            cfg.get('ollama_url', 'http://localhost:11434'),
            'http://ollama:11434',
            'http://host.docker.internal:11434'
        ]
        client = None
        start_time = time.time()
        timeout_seconds = 60
        while (time.time() - start_time) < timeout_seconds and client is None:
            for url in candidate_urls:
                try:
                    self.log(f"[LogPPT 2] Inizializzazione client Ollama su {url} con modello {cfg['model_name']}...")
                    c = LogPPTOllamaClient(ollama_url=url, model_name=cfg["model_name"])
                    if c.health_check():
                        client = c
                        break
                except Exception as e:
                    # Log e riprova
                    self.log(f"[LogPPT 2] Health check fallito su {url}: {e}")
            if client is None:
                time.sleep(2)
        if client is None:
            raise RuntimeError("Ollama non risponde. Verifica che il container/servizio sia attivo e che il modello esista (logppt-parser).")

        self.log("[LogPPT 2] Parsing di tutte le righe tramite Ollama...")
        parsed_templates: List[str] = []
        for idx, line in enumerate(raw_logs):
            if not line:
                parsed_templates.append("")
                continue
            result = client.parse_log(line)
            template = (result.get("template") or "").strip()
            parsed_templates.append(template)
            if (idx + 1) % 50 == 0:
                self.log(f"[LogPPT 2] Parsed {idx + 1}/{len(raw_logs)} righe...")

        # Salvataggio risultati con la stessa nomenclatura della demo
        dataset_name = Path(dataset_path).stem
        # Usa un suffisso timestamp per evitare sovrascritture e distinguere i run
        ts_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        full_structured_csv = task_output_dir / f"{dataset_name}_{ts_suffix}.log_structured.csv"
        templates_csv = task_output_dir / f"{dataset_name}_{ts_suffix}.log_templates.csv"

        out_df = df.copy()
        out_df['EventTemplate'] = parsed_templates
        out_df.to_csv(full_structured_csv, index=False)

        # Distribuzione template
        counter = pd.Series(parsed_templates).value_counts()
        template_df = pd.DataFrame({'EventTemplate': counter.index, 'Occurrence': counter.values})
        template_df['EventID'] = [f"E{i + 1}" for i in range(len(template_df))]
        template_df[['EventID', 'EventTemplate', 'Occurrence']].to_csv(templates_csv, index=False)

        # Copia in outputs per download immediato
        outputs_dir = Path("outputs")
        outputs_dir.mkdir(exist_ok=True)
        final_structured = outputs_dir / full_structured_csv.name
        final_templates = outputs_dir / templates_csv.name
        import shutil
        shutil.copy2(full_structured_csv, final_structured)
        shutil.copy2(templates_csv, final_templates)

        eval_report: Dict[str, Any] = {"message": "Evaluation skipped (no ground truth)"}
        if evaluate and has_ground_truth:
            # Valutazione semplice: matching esatto del template
            self.log("[LogPPT 2] Valutazione (semplice) sui template...")
            gt = df['EventTemplate'].astype(str).tolist()
            total = len(gt)
            correct = sum(1 for a, b in zip(parsed_templates, gt) if a == b)
            accuracy = (correct / total * 100.0) if total else 0.0
            eval_report = {
                "total": total,
                "correct": correct,
                "accuracy": round(accuracy, 2),
                "note": "Exact match accuracy (semplificata rispetto alla demo ufficiale)"
            }

        self.log("[LogPPT 2] Pipeline completata.")

        return {
            "evaluation": eval_report,
            "parsed_log_url": f"/outputs/{final_structured.name}",
            "templates_url": f"/outputs/{final_templates.name}"
        }


