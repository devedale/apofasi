"""
ConfigCache - Gestione centralizzata e ottimizzata di tutte le configurazioni.

WHY: Evita caricamenti ripetuti di YAML e configurazioni costose durante
il processing di grandi dataset, riducendo il tempo da minuti a secondi.

DESIGN: Singleton pattern per garantire una sola istanza della cache
e massimizzare la condivisione delle configurazioni tra tutti i servizi.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Set
from functools import lru_cache
import logging


class ConfigCache:
    """
    Cache globale per tutte le configurazioni dell'applicazione.
    
    WHY: Evita caricamenti ripetuti di YAML e configurazioni costose,
    riducendo drasticamente il tempo di processing per grandi dataset.
    
    Contract:
        - Input: Percorso file config (opzionale)
        - Output: Configurazioni cacheate e ottimizzate
        - Side effects: Caricamento file YAML una sola volta
    """
    
    _instance = None
    _config_cache = {}
    _config_path = None
    _logger = logging.getLogger(__name__)
    
    def __new__(cls, config_path: Optional[Path] = None):
        """Implementa singleton pattern per massimizzare la condivisione."""
        if cls._instance is None:
            cls._instance = super(ConfigCache, cls).__new__(cls)
            cls._instance._initialize(config_path)
        return cls._instance
    
    def _initialize(self, config_path: Optional[Path] = None):
        """Inizializza la cache delle configurazioni."""
        self._config_path = config_path or Path("config/config.yaml")
        self._config_cache = {}
        self._load_all_configurations()
    
    def _load_all_configurations(self) -> None:
        """
        Carica tutte le configurazioni costose una sola volta.
        
        WHY: Evita caricamenti ripetuti di YAML durante il processing
        di grandi dataset, riducendo il tempo da minuti a secondi.
        """
        try:
            if not self._config_path.exists():
                self._logger.warning(f"⚠️ File di configurazione non trovato: {self._config_path}")
                self._logger.info("📝 Usando configurazioni di default...")
                self._load_default_configurations()
                return
            
            self._logger.info(f"🔄 Caricamento configurazioni da {self._config_path}...")
            
            with open(self._config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            # Cache tutte le sezioni principali
            self._config_cache.update({
                'main': config_data,
                'centralized_regex': config_data.get('centralized_regex', {}),
                'drain3': config_data.get('drain3', {}),
                'regex': config_data.get('regex', {}),
                'csv_recognition': config_data.get('csv_recognition', {}),
                'field_detection': config_data.get('field_detection', {}),
                'timestamp_normalization': config_data.get('timestamp_normalization', {}),
                'complex_csv': config_data.get('complex_csv', {}),
                'intelligent_analysis': config_data.get('intelligent_analysis', {}),
                'parsers': config_data.get('parsers', {}),
                'output': config_data.get('output', {}),
                'logging': config_data.get('logging', {}),
                'parser': config_data.get('parser', {}),
                'file_formats': config_data.get('file_formats', {}),
                'app': config_data.get('app', {}),
            })
            
            # Cache configurazioni specifiche
            self._cache_specific_configs(config_data)
            
            total_sections = len(self._config_cache)
            self._logger.info(f"✅ Configurazioni caricate e cacheate: {total_sections} sezioni")
            
        except Exception as e:
            self._logger.error(f"❌ Errore nel caricamento delle configurazioni: {e}")
            self._logger.info("📝 Usando configurazioni di default...")
            self._load_default_configurations()
    
    def _cache_specific_configs(self, config_data: Dict[str, Any]) -> None:
        """Cache configurazioni specifiche e costose."""
        try:
            # Configurazione anonimizzazione
            drain3_config = config_data.get('drain3', {})
            anonymization_config = drain3_config.get('anonymization', {})
            self._config_cache['anonymization'] = anonymization_config
            self._config_cache['always_anonymize'] = set(anonymization_config.get('always_anonymize', []) or [])
            
            # Configurazione regex patterns
            centralized_regex = config_data.get('centralized_regex', {})
            self._config_cache['anonymization_patterns'] = centralized_regex.get('anonymization', {})
            self._config_cache['parsing_patterns'] = centralized_regex.get('parsing', {})
            self._config_cache['cleaning_patterns'] = centralized_regex.get('cleaning', {})
            self._config_cache['detection_patterns'] = centralized_regex.get('detection', {})
            
            # Configurazione parser adaptive
            parser_config = config_data.get('parser', {})
            self._config_cache['parser_adaptive'] = parser_config.get('adaptive', {})
            
        except Exception as e:
            self._logger.error(f"⚠️ Errore nel caching delle configurazioni specifiche: {e}")
    
    def _load_default_configurations(self) -> None:
        """Carica configurazioni di default quando il file non esiste."""
        self._config_cache.update({
            'main': {},
            'centralized_regex': {},
            'drain3': {},
            'regex': {},
            'csv_recognition': {},
            'field_detection': {},
            'timestamp_normalization': {},
            'complex_csv': {},
            'intelligent_analysis': {},
            'parsers': {},
            'output': {},
            'logging': {},
            'parser': {},
            'file_formats': {},
            'app': {},
            'anonymization': {},
            'always_anonymize': set(),
            'anonymization_patterns': {},
            'parsing_patterns': {},
            'cleaning_patterns': {},
            'detection_patterns': {},
            'parser_adaptive': {},
        })
    
    def get_config(self, section: str) -> Dict[str, Any]:
        """
        Ottiene una sezione di configurazione dalla cache.
        
        Args:
            section: Nome della sezione di configurazione
            
        Returns:
            Configurazione della sezione richiesta
        """
        return self._config_cache.get(section, {})
    
    def get_anonymization_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione di anonimizzazione."""
        return self._config_cache.get('anonymization', {})
    
    def get_always_anonymize_fields(self) -> Set[str]:
        """Ottiene i campi da anonimizzare sempre."""
        return self._config_cache.get('always_anonymize', set())
    
    def get_drain3_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione Drain3."""
        return self._config_cache.get('drain3', {})
    
    def get_presidio_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione Microsoft Presidio."""
        return self._config_cache.get('presidio', {})
    
    def get_regex_patterns(self, pattern_type: str) -> Dict[str, Any]:
        """
        Ottiene i pattern regex per un tipo specifico.
        
        Args:
            pattern_type: Tipo di pattern (anonymization, parsing, cleaning, detection)
            
        Returns:
            Pattern regex per il tipo richiesto
        """
        return self._config_cache.get(f'{pattern_type}_patterns', {})
    
    def get_csv_recognition_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione per il riconoscimento CSV."""
        return self._config_cache.get('csv_recognition', {})
    
    def get_field_detection_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione per il rilevamento automatico dei tipi."""
        return self._config_cache.get('field_detection', {})
    
    def get_timestamp_normalization_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione per la normalizzazione timestamp."""
        return self._config_cache.get('timestamp_normalization', {})
    
    def get_complex_csv_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione per CSV complessi."""
        return self._config_cache.get('complex_csv', {})
    
    def get_intelligent_analysis_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione per l'analisi intelligente."""
        return self._config_cache.get('intelligent_analysis', {})
    
    def get_parsers_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione per i parser specifici."""
        return self._config_cache.get('parsers', {})
    
    def get_output_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione per l'output."""
        return self._config_cache.get('output', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione per il logging."""
        return self._config_cache.get('logging', {})
    
    def get_parser_adaptive_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione per il parser universale adattivo."""
        return self._config_cache.get('parser_adaptive', {})
    
    def get_file_formats_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione per i formati di file supportati."""
        return self._config_cache.get('file_formats', {})
    
    def get_app_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione generale dell'applicazione."""
        return self._config_cache.get('app', {})
    
    def reload_config(self) -> None:
        """
        Ricarica le configurazioni dalla cache.
        
        WHY: Permette di aggiornare le configurazioni senza riavviare l'applicazione.
        """
        self._logger.info("🔄 Ricaricamento configurazioni...")
        self._load_all_configurations()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Ottiene statistiche sulla cache delle configurazioni.
        
        Returns:
            Statistiche sulla cache
        """
        return {
            'total_sections': len(self._config_cache),
            'sections': list(self._config_cache.keys()),
            'config_path': str(self._config_path),
            'cache_size': sum(len(str(v)) for v in self._config_cache.values())
        }
