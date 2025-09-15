"""
Client per integrare LogPPT con Ollama per parsing locale e anonimo.
Questo client usa il modello LogPPT addestrato su Ollama invece di Hugging Face.
"""

import json
import requests
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class LogPPTOllamaClient:
    """
    Client per LogPPT integrato con Ollama per parsing locale.
    """
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model_name: str = "logppt-parser"):
        """
        Inizializza il client LogPPT + Ollama.
        
        Args:
            ollama_url: URL del servizio Ollama
            model_name: Nome del modello LogPPT in Ollama
        """
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.base_url = f"{ollama_url}/api"
        
    def health_check(self) -> bool:
        """Verifica che Ollama sia attivo."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Errore health check Ollama: {e}")
            return False
    
    def list_models(self) -> List[Dict[str, Any]]:
        """Lista i modelli disponibili in Ollama."""
        try:
            response = requests.get(f"{self.base_url}/tags")
            if response.status_code == 200:
                return response.json().get("models", [])
            return []
        except Exception as e:
            logger.error(f"Errore nel listare i modelli: {e}")
            return []
    
    def parse_log(self, log_line: str) -> Dict[str, Any]:
        """
        Parsa una singola riga di log usando LogPPT su Ollama.
        
        Args:
            log_line: Riga di log da parsare
            
        Returns:
            Dizionario con template, fields e log_type
        """
        try:
            # Prompt restrittivo per forzare output JSON puro
            prompt = (
                "You are a log parser. Return ONLY a compact JSON object with keys: "
                "template (string), fields (object), log_type (string). Do not include any explanation.\n"
                f"Log line: {log_line}"
            )
            
            # Chiamata a Ollama
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                # Attiva JSON mode dell'API di Ollama per forzare un JSON valido
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    # Riduci contesto e risorse per velocizzare su CPU
                    "num_ctx": 1024,
                    "num_predict": 256
                }
            }
            
            start_time = time.time()
            response = requests.post(f"{self.base_url}/generate", json=payload, timeout=120)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "")
                
                # Se l'API ha rispettato format=json la risposta è già JSON
                parsed_result = {}
                if isinstance(response_text, dict):
                    parsed_result = response_text
                else:
                    parsed_result = self._extract_json_from_response(response_text)
                
                return {
                    "success": True,
                    "original_log": log_line,
                    "template": parsed_result.get("template", ""),
                    "fields": parsed_result.get("fields", {}),
                    "log_type": parsed_result.get("log_type", "unknown"),
                    "model_used": self.model_name,
                    "response_time": response_time,
                    "tokens_used": result.get("eval_count", 0),
                    "raw_response": response_text
                }
            else:
                return {
                    "success": False,
                    "original_log": log_line,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "model_used": self.model_name
                }
                
        except Exception as e:
            logger.error(f"Errore nel parsing del log: {e}")
            return {
                "success": False,
                "original_log": log_line,
                "error": str(e),
                "model_used": self.model_name
            }
    
    def parse_logs_batch(self, log_lines: List[str]) -> List[Dict[str, Any]]:
        """
        Parsa multiple righe di log in batch.
        
        Args:
            log_lines: Lista di righe di log da parsare
            
        Returns:
            Lista di risultati di parsing
        """
        results = []
        for i, log_line in enumerate(log_lines):
            logger.info(f"Parsing log {i+1}/{len(log_lines)}")
            result = self.parse_log(log_line)
            results.append(result)
            
            # Pausa breve tra le chiamate
            if i < len(log_lines) - 1:
                time.sleep(0.5)
        
        return results
    
    def _extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """
        Estrae JSON dalla risposta di Ollama.
        
        Args:
            response_text: Testo della risposta
            
        Returns:
            Dizionario parsato o default
        """
        try:
            # Cerca JSON nella risposta
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx + 1]
                return json.loads(json_str)
            else:
                # Fallback: crea template semplice
                return {
                    "template": response_text.strip(),
                    "fields": {},
                    "log_type": "unknown"
                }
        except json.JSONDecodeError:
            logger.warning(f"Impossibile parsare JSON da: {response_text}")
            return {
                "template": response_text.strip(),
                "fields": {},
                "log_type": "unknown"
            }
    
    def save_results(self, results: List[Dict[str, Any]], output_file: str) -> bool:
        """
        Salva i risultati del parsing in un file JSON.
        
        Args:
            results: Lista dei risultati
            output_file: Percorso del file di output
            
        Returns:
            True se salvato con successo
        """
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Risultati salvati in: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Errore nel salvare i risultati: {e}")
            return False
    
    def generate_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera un report dei risultati del parsing.
        
        Args:
            results: Lista dei risultati
            
        Returns:
            Report con statistiche
        """
        if not results:
            return {"error": "Nessun risultato da analizzare"}
        
        successful = [r for r in results if r.get("success", False)]
        failed = [r for r in results if not r.get("success", False)]
        
        # Statistiche per tipo di log
        log_types = {}
        for result in successful:
            log_type = result.get("log_type", "unknown")
            log_types[log_type] = log_types.get(log_type, 0) + 1
        
        # Tempo medio di risposta
        response_times = [r.get("response_time", 0) for r in successful if r.get("response_time")]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Token totali
        total_tokens = sum(r.get("tokens_used", 0) for r in successful)
        
        return {
            "total_logs": len(results),
            "successful_parses": len(successful),
            "failed_parses": len(failed),
            "success_rate": len(successful) / len(results) * 100 if results else 0,
            "log_types_distribution": log_types,
            "average_response_time": avg_response_time,
            "total_tokens_used": total_tokens,
            "model_used": self.model_name
        }
