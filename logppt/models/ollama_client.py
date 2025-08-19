"""
Ollama client for log parsing using large language models.

This module provides an interface to Ollama for parsing unstructured logs
and extracting templates using LLM-based approaches.
"""

import requests
import json
import time
from typing import List, Dict, Any, Optional


class OllamaLogParser:
    """
    Log parser using Ollama LLM for template extraction.
    
    This parser uses Ollama to analyze log structures and extract templates
    by identifying static vs dynamic parts of log messages.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "roberta-log-parser"):
        """
        Initialize the Ollama log parser.
        
        Args:
            base_url: Ollama service URL
            model_name: Name of the model to use for parsing
        """
        self.base_url = base_url
        self.model_name = model_name
        self.session = requests.Session()
        
    def health_check(self) -> bool:
        """Check if Ollama service is healthy."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List available models in Ollama."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                return response.json().get("models", [])
            return []
        except Exception as e:
            print(f"Errore nel listare i modelli: {e}")
            return []
    
    def parse_log(self, log_line: str, context: str = "") -> Dict[str, Any]:
        """
        Parse a single log line using Ollama.
        
        Args:
            log_line: The log line to parse
            context: Optional context about the log format
            
        Returns:
            Dictionary containing parsing results
        """
        prompt = f"""
Analizza questa riga di log e estrai il template, identificando quali parti sono statiche (template) e quali dinamiche (parametri).

Log da analizzare: {log_line}

{context if context else "Identifica la struttura del log e sostituisci i valori dinamici con placeholder appropriati."}

Rispondi solo con il template estratto, senza spiegazioni aggiuntive.
"""
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "top_k": 40
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                template = result.get("response", "").strip()
                
                return {
                    "success": True,
                    "original_log": log_line,
                    "template": template,
                    "model_used": self.model_name,
                    "response_time": result.get("eval_duration", 0) / 1e9,  # Convert nanoseconds to seconds
                    "tokens_used": result.get("eval_count", 0)
                }
            else:
                return {
                    "success": False,
                    "original_log": log_line,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "model_used": self.model_name
                }
                
        except Exception as e:
            return {
                "success": False,
                "original_log": log_line,
                "error": str(e),
                "model_used": self.model_name
            }
    
    def parse_logs_batch(self, log_lines: List[str], context: str = "") -> List[Dict[str, Any]]:
        """
        Parse multiple log lines in batch.
        
        Args:
            log_lines: List of log lines to parse
            context: Optional context about the log format
            
        Returns:
            List of parsing results
        """
        results = []
        
        for i, log_line in enumerate(log_lines):
            print(f"Parsing log {i+1}/{len(log_lines)}...")
            result = self.parse_log(log_line, context)
            results.append(result)
            
            # Small delay to avoid overwhelming the service
            time.sleep(0.1)
        
        return results
    
    def save_results(self, results: List[Dict[str, Any]], output_file: str) -> bool:
        """
        Save parsing results to a file.
        
        Args:
            results: List of parsing results
            output_file: Path to output file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Errore nel salvare i risultati: {e}")
            return False
    
    def generate_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary report of parsing results.
        
        Args:
            results: List of parsing results
            
        Returns:
            Summary report dictionary
        """
        total_logs = len(results)
        successful_parses = sum(1 for r in results if r.get("success", False))
        failed_parses = total_logs - successful_parses
        
        # Calculate average response time
        response_times = [r.get("response_time", 0) for r in results if r.get("success", False)]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Calculate total tokens used
        total_tokens = sum(r.get("tokens_used", 0) for r in results if r.get("success", False))
        
        return {
            "summary": {
                "total_logs": total_logs,
                "successful_parses": successful_parses,
                "failed_parses": failed_parses,
                "success_rate": (successful_parses / total_logs * 100) if total_logs > 0 else 0
            },
            "performance": {
                "average_response_time": avg_response_time,
                "total_tokens_used": total_tokens,
                "model_used": self.model_name
            },
            "results": results
        }
