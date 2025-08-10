"""
Config Manager - Gestione dinamica delle configurazioni per eliminare valori hardcoded
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import re
import yaml


class ConfigManager:
    """Gestore dinamico delle configurazioni per eliminare valori hardcoded"""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = self._load_config()
        self._compile_patterns()
    
    def _load_config(self) -> Dict[str, Any]:
        """Carica la configurazione dal file YAML"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"⚠️ Errore caricamento config {self.config_path}: {e}")
            return {}
    
    def _compile_patterns(self):
        """Compila i pattern regex per performance"""
        self.compiled_name_patterns = {}
        self.compiled_value_patterns = {}
        self.compiled_anonymization_patterns = {}
        self.compiled_log_patterns = []
        
        # Compila pattern per nomi campi
        if 'field_detection' in self.config:
            name_patterns = self.config['field_detection'].get('name_patterns', {})
            for field_type, config in name_patterns.items():
                patterns = config.get('patterns', [])
                self.compiled_name_patterns[field_type] = patterns
        
        # Compila pattern per valori
        if 'field_detection' in self.config:
            value_patterns = self.config['field_detection'].get('value_patterns', {})
            for field_type, config in value_patterns.items():
                patterns = config.get('patterns', [])
                self.compiled_value_patterns[field_type] = [
                    re.compile(pattern) for pattern in patterns
                ]
        
        # Compila pattern per anonimizzazione
        if 'anonymization' in self.config:
            anonymization_patterns = self.config['anonymization'].get('patterns', {})
            for pattern_type, config in anonymization_patterns.items():
                pattern = config.get('pattern', '')
                replacement = config.get('replacement', '')
                if pattern:
                    self.compiled_anonymization_patterns[pattern_type] = {
                        'pattern': re.compile(pattern),
                        'replacement': replacement
                    }
        
        # Compila pattern per log generici
        if 'log_patterns' in self.config:
            for log_pattern in self.config['log_patterns']:
                pattern = log_pattern.get('pattern', '')
                fields = log_pattern.get('fields', [])
                if pattern:
                    self.compiled_log_patterns.append({
                        'name': log_pattern.get('name', ''),
                        'pattern': re.compile(pattern),
                        'fields': fields
                    })
    
    def get_field_type_by_name(self, field_name: str) -> tuple[float, str]:
        """Determina il tipo di campo basandosi sul nome usando configurazione dinamica"""
        field_lower = field_name.lower()
        
        for field_type, patterns in self.compiled_name_patterns.items():
            for pattern in patterns:
                if pattern in field_lower:
                    config = self.config['field_detection']['name_patterns'][field_type]
                    confidence = config.get('confidence', 0.8)
                    return confidence, config.get('field_type', field_type)
        
        return 0.0, "unknown"
    
    def get_field_type_by_value(self, values: List[str]) -> tuple[float, str]:
        """Determina il tipo di campo basandosi sui valori usando configurazione dinamica"""
        if not values:
            return 0.0, "unknown"
        
        type_scores = {}
        
        for field_type, patterns in self.compiled_value_patterns.items():
            matches = 0
            for value in values:
                for pattern in patterns:
                    if pattern.search(str(value)):
                        matches += 1
                        break
            
            score = matches / len(values) if values else 0.0
            type_scores[field_type] = score
        
        if type_scores:
            best_type = max(type_scores.items(), key=lambda x: x[1])
            return best_type[1], best_type[0]
        
        return 0.0, "unknown"
    
    def anonymize_value(self, key: str, value: str) -> str:
        """Anonimizza un valore usando configurazione dinamica"""
        if not value:
            return value
        
        for pattern_type, config in self.compiled_anonymization_patterns.items():
            if config['pattern'].search(value):
                return config['replacement']
        
        return value
    
    def parse_log_line(self, content: str) -> Dict[str, Any]:
        """Parsa una riga di log usando pattern configurabili"""
        content = content.strip()
        
        for log_pattern in self.compiled_log_patterns:
            match = log_pattern['pattern'].match(content)
            if match:
                result = {}
                for field_config in log_pattern['fields']:
                    field_name = field_config['name']
                    group_index = field_config['group'] - 1  # Converti a 0-based
                    if group_index < len(match.groups()):
                        result[field_name] = match.group(group_index + 1)
                return result
        
        # Fallback: contenuto grezzo
        return {'content': content}
    
    def get_anonymization_enabled(self) -> bool:
        """Verifica se l'anonimizzazione è abilitata"""
        return self.config.get('anonymization', {}).get('enabled', True)
    
    def get_adaptive_parser_enabled(self) -> bool:
        """Verifica se il parser adattivo è abilitato"""
        return self.config.get('parser', {}).get('adaptive', {}).get('enabled', True) 