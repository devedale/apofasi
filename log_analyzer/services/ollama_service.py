"""
Servizio per la gestione dei modelli tramite Ollama.

Questo servizio sostituisce completamente Hugging Face per:
- Download e gestione dei modelli
- Interfaccia API unificata per il parsing dei log
- Gestione lifecycle dei modelli (download, cancellazione, listing)
"""

import os
import json
import requests
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class OllamaService:
    """
    Servizio centralizzato per la gestione dei modelli tramite Ollama.
    
    Funzionalità principali:
    - Gestione completa dei modelli (download, delete, list)
    - API unificata per il parsing dei log
    - Integrazione con LogPPT attraverso Ollama
    - Health check e status monitoring
    """
    
    def __init__(self, config: Dict[str, Any] = None, task_id: str = None, log_manager=None):
        """
        Inizializza il servizio Ollama.
        
        Args:
            config: Configurazione del servizio
            task_id: ID del task per logging
            log_manager: Manager per i log
        """
        self.config = config or {}
        self.task_id = task_id
        self.log_manager = log_manager
        
        # Configurazione di base per Ollama
        self.ollama_config = self._get_ollama_config()
        self.base_url = self.ollama_config.get("url", "http://ollama:11434")
        self.timeout = self.ollama_config.get("timeout", 30)
        
        # Modelli disponibili predefiniti
        self.available_models = {
            "logppt-parser": {
                "description": "Modello LogPPT specializzato per il parsing dei log",
                "modelfile": "Modelfile.logppt",
                "base_model": "llama2:7b"
            },
            "logppt-fast": {
                "description": "Versione veloce di LogPPT per parsing rapido",
                "modelfile": "Modelfile.logppt.fast",
                "base_model": "llama2:7b"
            },
            "template-extractor": {
                "description": "Modello specializzato per estrazione template",
                "modelfile": "Modelfile.template_extractor",
                "base_model": "llama2:7b"
            },
            "roberta-parser": {
                "description": "Parser basato su RoBERTa per Ollama",
                "modelfile": "Modelfile.roberta",
                "base_model": "llama2:7b"
            }
        }

    def log(self, message: str):
        """Helper per logging centralizzato."""
        if self.log_manager and self.task_id:
            self.log_manager.log(self.task_id, message)
        else:
            print(f"[OllamaService] {message}")

    def _get_ollama_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione di Ollama dal config principale."""
        default_config = {
            "url": os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434"),
            "timeout": 30,
            "max_retries": 3
        }
        
        ollama_config = self.config.get("ollama", {})
        return {**default_config, **ollama_config}

    async def health_check(self) -> bool:
        """
        Verifica se Ollama è disponibile e raggiungibile.
        
        Returns:
            bool: True se Ollama è disponibile, False altrimenti
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout)
            return response.status_code == 200
        except Exception as e:
            self.log(f"Health check fallito: {str(e)}")
            return False

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        Lista tutti i modelli disponibili in Ollama.
        
        Returns:
            List[Dict]: Lista dei modelli con metadata
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            models = []
            
            for model in data.get("models", []):
                model_info = {
                    "name": model.get("name", ""),
                    "size": model.get("size", 0),
                    "modified_at": model.get("modified_at", ""),
                    "digest": model.get("digest", ""),
                    "details": model.get("details", {})
                }
                
                # Aggiungi descrizione se è un modello predefinito
                model_name = model_info["name"].split(":")[0]  # Rimuovi tag
                if model_name in self.available_models:
                    model_info["description"] = self.available_models[model_name]["description"]
                
                models.append(model_info)
            
            self.log(f"Trovati {len(models)} modelli in Ollama")
            return models
            
        except Exception as e:
            self.log(f"Errore nel listing dei modelli: {str(e)}")
            return []

    async def download_model(self, model_name: str) -> Dict[str, Any]:
        """
        Scarica/crea un modello in Ollama.
        
        Args:
            model_name: Nome del modello da scaricare
            
        Returns:
            Dict: Risultato dell'operazione
        """
        try:
            self.log(f"Iniziando download del modello: {model_name}")
            
            # Verifica se è un modello predefinito
            if model_name in self.available_models:
                return await self._create_custom_model(model_name)
            else:
                # Download di un modello standard (es. llama2:7b)
                return await self._pull_base_model(model_name)
                
        except Exception as e:
            error_msg = f"Errore durante il download del modello {model_name}: {str(e)}"
            self.log(error_msg)
            return {"success": False, "error": error_msg}

    async def _create_custom_model(self, model_name: str) -> Dict[str, Any]:
        """
        Crea un modello custom usando un Modelfile.
        
        Args:
            model_name: Nome del modello custom
            
        Returns:
            Dict: Risultato dell'operazione
        """
        try:
            model_info = self.available_models[model_name]
            modelfile_path = Path(model_info["modelfile"])
            
            if not modelfile_path.exists():
                raise FileNotFoundError(f"Modelfile non trovato: {modelfile_path}")
            
            # Leggi il Modelfile
            with open(modelfile_path, 'r', encoding='utf-8') as f:
                modelfile_content = f.read()
            
            # Prima assicurati che il modello base sia disponibile
            base_model = model_info["base_model"]
            self.log(f"Verificando disponibilità del modello base: {base_model}")
            
            base_available = await self._check_model_exists(base_model)
            if not base_available:
                self.log(f"Scaricando modello base: {base_model}")
                base_result = await self._pull_base_model(base_model)
                if not base_result.get("success", False):
                    raise Exception(f"Fallito download del modello base: {base_model}")
            
            # Crea il modello custom
            self.log(f"Creando modello custom: {model_name}")
            
            payload = {
                "name": model_name,
                "modelfile": modelfile_content
            }
            
            response = requests.post(
                f"{self.base_url}/api/create",
                json=payload,
                timeout=300  # Timeout esteso per la creazione
            )
            response.raise_for_status()
            
            self.log(f"Modello {model_name} creato con successo")
            return {
                "success": True,
                "message": f"Modello {model_name} creato con successo",
                "model_name": model_name
            }
            
        except Exception as e:
            error_msg = f"Errore nella creazione del modello custom {model_name}: {str(e)}"
            self.log(error_msg)
            return {"success": False, "error": error_msg}

    async def _pull_base_model(self, model_name: str) -> Dict[str, Any]:
        """
        Scarica un modello base da Ollama Hub.
        
        Args:
            model_name: Nome del modello base
            
        Returns:
            Dict: Risultato dell'operazione
        """
        try:
            self.log(f"Scaricando modello base: {model_name}")
            
            payload = {"name": model_name}
            
            response = requests.post(
                f"{self.base_url}/api/pull",
                json=payload,
                timeout=600  # Timeout esteso per il download
            )
            response.raise_for_status()
            
            self.log(f"Modello base {model_name} scaricato con successo")
            return {
                "success": True,
                "message": f"Modello {model_name} scaricato con successo",
                "model_name": model_name
            }
            
        except Exception as e:
            error_msg = f"Errore nel download del modello base {model_name}: {str(e)}"
            self.log(error_msg)
            return {"success": False, "error": error_msg}

    async def _check_model_exists(self, model_name: str) -> bool:
        """
        Verifica se un modello esiste in Ollama.
        
        Args:
            model_name: Nome del modello da verificare
            
        Returns:
            bool: True se il modello esiste, False altrimenti
        """
        try:
            models = await self.list_models()
            return any(model["name"].startswith(model_name) for model in models)
        except Exception:
            return False

    async def delete_model(self, model_name: str) -> Dict[str, Any]:
        """
        Elimina un modello da Ollama.
        
        Args:
            model_name: Nome del modello da eliminare
            
        Returns:
            Dict: Risultato dell'operazione
        """
        try:
            self.log(f"Eliminando modello: {model_name}")
            
            payload = {"name": model_name}
            
            response = requests.delete(
                f"{self.base_url}/api/delete",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            self.log(f"Modello {model_name} eliminato con successo")
            return {
                "success": True,
                "message": f"Modello {model_name} eliminato con successo"
            }
            
        except Exception as e:
            error_msg = f"Errore nell'eliminazione del modello {model_name}: {str(e)}"
            self.log(error_msg)
            return {"success": False, "error": error_msg}

    async def parse_log_line(self, log_line: str, model_name: str = "logppt-parser") -> Dict[str, Any]:
        """
        Parsa una singola riga di log usando Ollama.
        
        Args:
            log_line: Riga di log da parsare
            model_name: Nome del modello da usare per il parsing
            
        Returns:
            Dict: Risultato del parsing
        """
        try:
            payload = {
                "model": model_name,
                "prompt": f"Parse this log line: {log_line}",
                "stream": False
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            response_text = result.get("response", "")
            
            # Prova a parsare la risposta come JSON
            try:
                parsed_result = json.loads(response_text)
                return {
                    "success": True,
                    "result": parsed_result,
                    "raw_response": response_text
                }
            except json.JSONDecodeError:
                # Se non è JSON valido, ritorna la risposta raw
                return {
                    "success": True,
                    "result": {"template": response_text, "fields": {}},
                    "raw_response": response_text
                }
                
        except Exception as e:
            error_msg = f"Errore nel parsing della riga di log: {str(e)}"
            self.log(error_msg)
            return {"success": False, "error": error_msg}

    async def parse_log_batch(self, log_lines: List[str], model_name: str = "logppt-parser") -> List[Dict[str, Any]]:
        """
        Parsa un batch di righe di log usando Ollama.
        
        Args:
            log_lines: Lista di righe di log da parsare
            model_name: Nome del modello da usare per il parsing
            
        Returns:
            List[Dict]: Lista dei risultati del parsing
        """
        results = []
        
        for i, log_line in enumerate(log_lines):
            self.log(f"Parsing riga {i+1}/{len(log_lines)}")
            result = await self.parse_log_line(log_line, model_name)
            results.append(result)
            
            # Piccola pausa per evitare di sovraccaricare Ollama
            await asyncio.sleep(0.1)
        
        return results

    def get_available_models_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Ottiene informazioni sui modelli predefiniti disponibili.
        
        Returns:
            Dict: Informazioni sui modelli predefiniti
        """
        return self.available_models
