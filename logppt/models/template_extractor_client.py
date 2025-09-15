"""
Client specializzato per Template Extraction LogPPT su Ollama.
Replica esattamente la logica di template_extraction() originale con cache e gestione template.
"""

import json
import requests
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
import re

logger = logging.getLogger(__name__)


class TemplateExtractorClient:
    """
    Client per Template Extraction LogPPT integrato con Ollama.
    Replica esattamente la logica di template_extraction() originale.
    """
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model_name: str = "logppt-template-extractor"):
        """
        Inizializza il client Template Extractor.
        
        Args:
            ollama_url: URL del servizio Ollama
            model_name: Nome del modello Template Extractor in Ollama
        """
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.base_url = f"{ollama_url}/api"
        
        # Cache per template (replica ParsingCache di LogPPT)
        self.template_cache = {}
        self.template_tree = {}
        self.threshold = 0.8
        
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
    
    def match_event(self, log_line: str) -> tuple:
        """
        Replica la logica di cache.match_event() di LogPPT.
        
        Args:
            log_line: Riga di log da analizzare
            
        Returns:
            Tuple (template, confidence, metadata) come in LogPPT
        """
        # Normalizza la riga di log
        normalized_log = " ".join(log_line.strip().split())
        
        # Cerca match esatti nella cache
        if normalized_log in self.template_cache:
            return self.template_cache[normalized_log], 1.0, {}
        
        # Cerca match fuzzy per template simili
        best_match = None
        best_score = 0.0
        
        for cached_log, template in self.template_cache.items():
            # Calcola similarità semplice (può essere migliorata)
            similarity = self._calculate_similarity(normalized_log, cached_log)
            if similarity > self.threshold and similarity > best_score:
                best_score = similarity
                best_match = template
        
        if best_match:
            return best_match, best_score, {}
        
        return "NoMatch", 0.0, {}
    
    def _calculate_similarity(self, log1: str, log2: str) -> float:
        """
        Calcola similarità tra due righe di log.
        Implementazione semplificata per ora.
        """
        # Tokenizzazione semplice
        tokens1 = set(re.findall(r'\S+', log1))
        tokens2 = set(re.findall(r'\S+', log2))
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        
        return intersection / union if union > 0 else 0.0
    
    def add_templates(self, template: str, is_valid: bool, metadata: Dict):
        """
        Aggiunge template alla cache (replica cache.add_templates() di LogPPT).
        
        Args:
            template: Template da aggiungere
            is_valid: Se il template è valido
            metadata: Metadati aggiuntivi
        """
        if is_valid and template:
            # Normalizza il template
            normalized_template = " ".join(template.strip().split())
            
            # Aggiungi alla cache
            self.template_cache[normalized_template] = template
            
            # Aggiorna l'albero dei template (semplificato)
            template_key = self._extract_template_key(template)
            if template_key not in self.template_tree:
                self.template_tree[template_key] = []
            self.template_tree[template_key].append(template)
    
    def _extract_template_key(self, template: str) -> str:
        """
        Estrae una chiave per raggruppare template simili.
        """
        # Rimuovi placeholder per creare una chiave
        key = re.sub(r'<[^>]+>', '<*>', template)
        key = re.sub(r'HH|MM|SS|SSS|YYYY|DD|PID\d+|LEVEL|IP|PORT', '<*>', key)
        return key
    
    def extract_template(self, log_line: str) -> str:
        """
        Estrae template da una riga di log (replica model.parse() di LogPPT).
        
        Args:
            log_line: Riga di log da parsare
            
        Returns:
            Template estratto con placeholder
        """
        try:
            # Prompt specifico per template extraction
            prompt = (
                "Extract the template from this log line. "
                "Replace dynamic parts with EXACT placeholders: HH, MM, SS, SSS, YYYY, MM, DD, PID1, PID2, LEVEL, IP, PORT, <*>. "
                "Return ONLY valid JSON with template, fields, and log_type.\n\n"
                f"Log line: {log_line}"
            )
            
            # Chiamata a Ollama
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_ctx": 512,
                    "num_predict": 128,
                    "num_thread": 4
                }
            }
            
            response = requests.post(
                f"{self.base_url}/generate", 
                json=payload, 
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "")
                
                # Parsing JSON
                try:
                    if isinstance(response_text, dict):
                        parsed_result = response_text
                    else:
                        parsed_result = self._extract_json_from_response(response_text)
                    
                    template = parsed_result.get("template", "")
                    
                    # Valida il template
                    if self._verify_template(template):
                        return template
                    else:
                        logger.warning(f"Template non valido: {template}")
                        return self._fallback_template(log_line)
                        
                except Exception as e:
                    logger.error(f"Errore parsing JSON: {e}")
                    return self._fallback_template(log_line)
            else:
                logger.error(f"HTTP {response.status_code}: {response.text}")
                return self._fallback_template(log_line)
                
        except Exception as e:
            logger.error(f"Errore nell'estrazione del template: {e}")
            return self._fallback_template(log_line)
    
    def _verify_template(self, template: str) -> bool:
        """
        Verifica se il template è valido (replica verify_template() di LogPPT).
        """
        if not template:
            return False
        
        # Rimuovi placeholder
        clean_template = template.replace("<*>", "")
        clean_template = re.sub(r'HH|MM|SS|SSS|YYYY|DD|PID\d+|LEVEL|IP|PORT', '', clean_template)
        
        # Verifica che non sia solo punteggiatura
        import string
        return any(char not in string.punctuation for char in clean_template)
    
    def _fallback_template(self, log_line: str) -> str:
        """
        Template di fallback se l'estrazione fallisce.
        """
        # Sostituisci numeri e valori dinamici con placeholder generici
        template = re.sub(r'\d+', '<*>', log_line)
        template = re.sub(r'[a-fA-F0-9]{8,}', '<*>', template)  # Hash/ID lunghi
        return template
    
    def _extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """
        Estrae JSON dalla risposta di Ollama.
        """
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx + 1]
                return json.loads(json_str)
            else:
                return {"template": "", "fields": {}, "log_type": "unknown"}
        except json.JSONDecodeError:
            logger.warning(f"Impossibile parsare JSON da: {response_text}")
            return {"template": "", "fields": {}, "log_type": "unknown"}
    
    def template_extraction(self, log_lines: List[str], vtoken: str = "virtual-param") -> tuple:
        """
        Replica esattamente template_extraction() di LogPPT.
        
        Args:
            log_lines: Lista di righe di log da parsare
            vtoken: Token virtuale (non usato in questa implementazione)
            
        Returns:
            Tuple (templates, model_time) come in LogPPT
        """
        logger.info("Starting template extraction")
        start_time = time.time()
        templates = []
        cache_for_all_invocations = {}
        model_time = 0
        
        logger.info(f"Parsing {len(log_lines)} log lines...")
        
        for i, log in enumerate(log_lines):
            if i % 50 == 0:
                logger.info(f"Parsed {i}/{len(log_lines)} lines...")
            
            log = " ".join(log.strip().split())
            
            # Controlla cache locale
            try:
                template = cache_for_all_invocations[log]
            except KeyError:
                template = None
            
            if template is not None:
                templates.append(template)
                continue
            
            # Controlla cache globale
            results = self.match_event(log)
            if results[0] != "NoMatch":
                templates.append(results[0])
                continue
            else:
                # Estrai template con il modello
                t0 = time.time()
                template = self.extract_template(log)
                model_time += time.time() - t0
                
                if self._verify_template(template):
                    self.add_templates(template, True, results[2])
                cache_for_all_invocations[log] = template
                templates.append(template)
        
        total_time = time.time() - start_time
        logger.info(f"Total time taken: {total_time}")
        logger.info(f"No of model invocations: {len(cache_for_all_invocations.keys())}")
        logger.info(f"Total time taken by model: {model_time}")
        
        return templates, model_time
