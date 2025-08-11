"""
Motore Regex Centralizzato per Anonimizzazione e Drain3.

WHY: Fornisce un motore regex unificato e funzionale per
anonimizzazione, parsing e integrazione con Drain3.
"""

import re
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from functools import lru_cache
from collections import defaultdict

from .base_service import BaseService


class RegexEngine(BaseService):
    """
    Motore regex centralizzato per anonimizzazione e Drain3.
    
    WHY: Fornisce un motore regex unificato che supporta
    anonimizzazione, parsing e integrazione con Drain3.
    
    Contract:
        - Input: Testo da processare, categoria regex
        - Output: Testo processato con metadati
        - Side effects: Nessuno, elaborazione pura
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Inizializza il motore regex.
        
        Args:
            config_path: Percorso al file di configurazione
        """
        super().__init__()
        self.config_path = config_path or Path("config/config.yaml")
        self._patterns = {}
        self._compiled_patterns = {}
        self._config = {}
        self._load_config()
    
    def _load_config(self):
        """Carica la configurazione regex."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            
            # Carica tutti i pattern
            self._load_anonymization_patterns()
            self._load_parsing_patterns()
            self._load_security_patterns()
            self._load_cleaning_patterns()
            
            self.logger.info(f"✅ Motore regex caricato: {len(self._patterns)} pattern")
            
        except Exception as e:
            self.logger.error(f"❌ Errore caricamento motore regex: {e}")
            self._load_default_patterns()
    
    def _load_anonymization_patterns(self):
        """Carica pattern per anonimizzazione."""
        patterns = self._config.get('anonymization_patterns', {})
        for name, config in patterns.items():
            self._patterns[f"anonymization_{name}"] = {
                'pattern': config['pattern'],
                'replacement': config.get('replacement', '<ANONYMIZED>'),
                'priority': config.get('priority', 999),
                'category': 'anonymization',
                'description': config.get('description', '')
            }
    
    def _load_parsing_patterns(self):
        """Carica pattern per parsing."""
        patterns = self._config.get('parsing_patterns', {})
        for name, config in patterns.items():
            self._patterns[f"parsing_{name}"] = {
                'pattern': config['pattern'],
                'description': config.get('description', ''),
                'category': 'parsing'
            }
    
    def _load_security_patterns(self):
        """Carica pattern per sicurezza."""
        patterns = self._config.get('security_patterns', {})
        for name, config in patterns.items():
            self._patterns[f"security_{name}"] = {
                'pattern': config['pattern'],
                'flags': config.get('flags', 'IGNORECASE'),
                'description': config.get('description', ''),
                'category': 'security'
            }
    
    def _load_cleaning_patterns(self):
        """Carica pattern per pulizia."""
        patterns = self._config.get('cleaning_patterns', {})
        for name, config in patterns.items():
            self._patterns[f"cleaning_{name}"] = {
                'pattern': config['pattern'],
                'replacement': config.get('replacement', ''),
                'description': config.get('description', ''),
                'category': 'cleaning'
            }
    
    def _load_default_patterns(self):
        """Carica pattern di default."""
        self.logger.warning("⚠️ Caricamento pattern di default")
        self._patterns = {
            'anonymization_ip': {
                'pattern': r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
                'replacement': '<IP>',
                'priority': 1,
                'category': 'anonymization'
            },
            'anonymization_email': {
                'pattern': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                'replacement': '<EMAIL>',
                'priority': 2,
                'category': 'anonymization'
            },
            'anonymization_credit_card': {
                'pattern': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
                'replacement': '<CREDIT_CARD>',
                'priority': 3,
                'category': 'anonymization'
            }
        }
    
    @lru_cache(maxsize=100)
    def get_compiled_pattern(self, pattern_name: str) -> Optional[re.Pattern]:
        """Ottiene un pattern regex compilato con cache."""
        if pattern_name not in self._patterns:
            return None
        
        if pattern_name in self._compiled_patterns:
            return self._compiled_patterns[pattern_name]
        
        try:
            pattern_config = self._patterns[pattern_name]
            pattern = pattern_config['pattern']
            flags = pattern_config.get('flags', 0)
            
            if isinstance(flags, str):
                flag_map = {
                    'IGNORECASE': re.IGNORECASE,
                    'MULTILINE': re.MULTILINE,
                    'DOTALL': re.DOTALL,
                    'VERBOSE': re.VERBOSE
                }
                flags = flag_map.get(flags, 0)
            
            compiled = re.compile(pattern, flags)
            self._compiled_patterns[pattern_name] = compiled
            return compiled
        except Exception as e:
            self.logger.error(f"❌ Errore compilazione pattern {pattern_name}: {e}")
            return None
    
    def anonymize_text(self, text: str, priority_order: bool = True) -> Tuple[str, Dict[str, Any]]:
        """
        Anonimizza il testo con metadati dettagliati.
        
        Args:
            text: Testo da anonimizzare
            priority_order: Se True, applica pattern in ordine di priorità
            
        Returns:
            Tuple di (testo anonimizzato, metadati)
        """
        if not text:
            return text, {}
        
        original_text = text
        anonymized_text = text
        metadata = {
            'original_length': len(text),
            'anonymized_length': len(text),
            'patterns_applied': [],
            'anonymization_count': 0
        }
        
        # Ottieni pattern di anonimizzazione
        anonymization_patterns = [
            (name, config) for name, config in self._patterns.items()
            if config['category'] == 'anonymization'
        ]
        
        # Ordina per priorità se richiesto
        if priority_order:
            anonymization_patterns.sort(key=lambda x: x[1].get('priority', 999))
        
        # Applica pattern
        for pattern_name, config in anonymization_patterns:
            compiled_pattern = self.get_compiled_pattern(pattern_name)
            if not compiled_pattern:
                continue
            
            try:
                # Trova tutte le occorrenze
                matches = list(compiled_pattern.finditer(anonymized_text))
                if matches:
                    # Sostituisci
                    replacement = config.get('replacement', '<ANONYMIZED>')
                    anonymized_text = compiled_pattern.sub(replacement, anonymized_text)
                    
                    # Aggiorna metadati
                    metadata['patterns_applied'].append({
                        'pattern_name': pattern_name,
                        'pattern_description': config.get('description', ''),
                        'matches_count': len(matches),
                        'replacement': replacement
                    })
                    metadata['anonymization_count'] += len(matches)
                    
            except Exception as e:
                self.logger.warning(f"⚠️ Errore applicazione pattern {pattern_name}: {e}")
        
        metadata['anonymized_length'] = len(anonymized_text)
        metadata['anonymization_ratio'] = metadata['anonymization_count'] / max(metadata['original_length'], 1)
        
        return anonymized_text, metadata
    
    def extract_patterns_for_drain3(self, text: str) -> Dict[str, Any]:
        """
        Estrae pattern utili per Drain3.
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Metadati per Drain3
        """
        metadata = {
            'has_ip': False,
            'has_email': False,
            'has_credit_card': False,
            'has_url': False,
            'has_date': False,
            'has_time': False,
            'pattern_matches': []
        }
        
        # Controlla pattern specifici
        patterns_to_check = [
            ('ip', r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'),
            ('email', r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            ('credit_card', r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
            ('url', r'https?://[^\s]+'),
            ('date', r'\d{4}-\d{2}-\d{2}'),
            ('time', r'\d{2}:\d{2}:\d{2}')
        ]
        
        for pattern_name, pattern in patterns_to_check:
            matches = re.findall(pattern, text)
            if matches:
                metadata[f'has_{pattern_name}'] = True
                metadata['pattern_matches'].append({
                    'type': pattern_name,
                    'count': len(matches),
                    'examples': matches[:3]  # Primi 3 esempi
                })
        
        return metadata
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Ottiene statistiche sui pattern."""
        stats = defaultdict(int)
        for pattern_name, config in self._patterns.items():
            category = config['category']
            stats[f'{category}_patterns'] += 1
        
        return {
            'total_patterns': len(self._patterns),
            'categories': dict(stats),
            'compiled_patterns': len(self._compiled_patterns)
        } 