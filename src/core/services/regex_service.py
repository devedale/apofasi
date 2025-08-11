"""
Servizio core centralizzato per la gestione di TUTTI i pattern regex.

WHY: Centralizza tutti i pattern regex per evitare duplicazioni, hardcoding
e garantire consistenza in tutto il sistema.
"""

import re
import signal
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import yaml
from functools import lru_cache

from .base_service import BaseService


class RegexService(BaseService):
    """
    Servizio centralizzato per la gestione di pattern regex.
    
    WHY: Fornisce un punto unico per tutti i pattern regex del sistema,
    con cache, timeout e gestione errori.
    
    Contract:
        - Input: Pattern name o pattern string
        - Output: Compiled regex pattern con configurazione
        - Side effects: Cache di pattern compilati, timeout handling
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inizializza il servizio regex.
        
        Args:
            config: Configurazione del sistema (opzionale)
        """
        # Inizializza prima il logger
        super().__init__()
        
        self.config = config or {}
        
        # Inizializza pattern e config
        self._patterns = {}
        self._compiled_patterns = {}
        self._config = {}
        
        # Carica configurazione regex dalla configurazione unificata
        regex_config = self.config.get('regex', {})
        # Carica pattern da configurazione centralizzata se disponibile
        if 'centralized_regex' in self.config:
            patterns_file = self.config['centralized_regex'].get('patterns_file', 'config/config.yaml')
        else:
            patterns_file = 'config/config.yaml'
        
        # Carica i pattern dal file
        self._load_patterns_from_file(patterns_file)
        
        # Carica categorie dalla configurazione
        self.categories = regex_config.get('categories', ['parsing', 'anonymization', 'detection'])
        
        # Carica CSV recognition patterns
        self.csv_recognition = regex_config.get('csv_recognition', {})
    
    def _load_patterns_from_file(self, patterns_file: str):
        """
        Carica TUTTI i pattern dal file unico.
        
        Args:
            patterns_file: Percorso al file dei pattern
        """
        try:
            import yaml
            from pathlib import Path
            
            config_path = Path(patterns_file)
            if not config_path.exists():
                self.warning(f"File pattern non trovato: {patterns_file}")
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            
            # Carica TUTTI i pattern dal file unico
            self._load_all_patterns()
            
            total_patterns = sum(len(patterns) for patterns in self._patterns.values())
            self.info(f"✅ Configurazione regex caricata: {total_patterns} pattern")
            
        except Exception as e:
            self.error(f"❌ Errore caricamento pattern: {e}")
            # Fallback: usa pattern di default
            self._load_default_patterns()
    
    def _load_all_patterns(self):
        """
        Carica TUTTI i pattern dal file unico.
        
        WHY: Punto unico di configurazione per tutti i pattern regex.
        """
        # Carica pattern di anonimizzazione
        if 'anonymization_patterns' in self._config:
            for name, config in self._config['anonymization_patterns'].items():
                full_config = config.copy()
                full_config['category'] = 'anonymization'
                self._patterns[f"anonymization_{name}"] = full_config
        
        # Carica pattern di pulizia
        if 'cleaning_patterns' in self._config:
            for name, config in self._config['cleaning_patterns'].items():
                full_config = config.copy()
                full_config['category'] = 'cleaning'
                self._patterns[f"cleaning_{name}"] = full_config
        
        # Carica pattern di parsing
        if 'parsing_patterns' in self._config:
            for name, config in self._config['parsing_patterns'].items():
                full_config = config.copy()
                full_config['category'] = 'parsing'
                self._patterns[f"parsing_{name}"] = full_config
        
        # Carica pattern di detection (se presenti)
        if 'detection_patterns' in self._config:
            for name, config in self._config['detection_patterns'].items():
                full_config = config.copy()
                full_config['category'] = 'detection'
                self._patterns[f"detection_{name}"] = full_config

        # Carica pattern di sicurezza (se presenti)
        if 'security_patterns' in self._config:
            for name, config in self._config['security_patterns'].items():
                full_config = config.copy()
                full_config['category'] = 'security'
                self._patterns[f"security_{name}"] = full_config
    
    def _load_default_patterns(self):
        """Carica pattern di default se il file non esiste."""
        self.logger.warning("⚠️ Caricamento pattern di default")
        self._patterns = {
            'anonymization_ip': {
                'pattern': r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
                'replacement': '<IP>',
                'priority': 1,
                'category': 'anonymization'
            }
        }
    
    @lru_cache(maxsize=100)
    def get_compiled_pattern(self, pattern_name: str) -> Optional[re.Pattern]:
        """
        Ottiene un pattern regex compilato con cache.
        
        Args:
            pattern_name: Nome del pattern
            
        Returns:
            Pattern regex compilato o None se non trovato
        """
        if pattern_name not in self._patterns:
            self.logger.warning(f"⚠️ Pattern non trovato: {pattern_name}")
            return None
        
        if pattern_name in self._compiled_patterns:
            return self._compiled_patterns[pattern_name]
        
        try:
            pattern_config = self._patterns[pattern_name]
            pattern_str = pattern_config['pattern']

            # Normalizza pattern YAML che possono essere scritti come r'...'/r"..."
            if isinstance(pattern_str, str):
                if pattern_str.startswith("r'") and pattern_str.endswith("'"):
                    pattern_str = pattern_str[2:-1]
                elif pattern_str.startswith('r"') and pattern_str.endswith('"'):
                    pattern_str = pattern_str[2:-1]
            
            # Gestisci flags
            flags = 0
            if pattern_config.get('flags'):
                if 'IGNORECASE' in pattern_config['flags']:
                    flags |= re.IGNORECASE
                if 'MULTILINE' in pattern_config['flags']:
                    flags |= re.MULTILINE
                if 'DOTALL' in pattern_config['flags']:
                    flags |= re.DOTALL
            
            # Compila pattern con timeout
            compiled = re.compile(pattern_str, flags)
            self._compiled_patterns[pattern_name] = compiled
            
            return compiled
            
        except Exception as e:
            self.logger.error(f"❌ Errore compilazione pattern {pattern_name}: {e}")
            return None
    
    def apply_pattern(self, text: str, pattern_name: str, timeout_ms: int = 1000) -> str:
        """
        Applica un pattern regex al testo con timeout.
        
        Args:
            text: Testo da processare
            pattern_name: Nome del pattern
            timeout_ms: Timeout in millisecondi
            
        Returns:
            Testo processato
        """
        if not isinstance(text, str):
            return text
        
        pattern = self.get_compiled_pattern(pattern_name)
        if not pattern:
            return text
        
        pattern_config = self._patterns[pattern_name]
        
        try:
            # Gestisci timeout
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Timeout applicazione pattern {pattern_name}")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_ms // 1000)
            
            try:
                if pattern_config['category'] == 'anonymization':
                    return pattern.sub(pattern_config['replacement'], text)
                elif pattern_config['category'] == 'cleaning':
                    return pattern.sub(pattern_config['replacement'], text)
                else:
                    return text
                    
            finally:
                signal.alarm(0)
                
        except TimeoutError:
            self.logger.warning(f"⚠️ Timeout applicazione pattern {pattern_name}")
            return text
        except Exception as e:
            self.logger.error(f"❌ Errore applicazione pattern {pattern_name}: {e}")
            return text
    
    def apply_patterns_by_category(self, text: str, category: str, 
                                 priority_order: bool = True) -> str:
        """
        Applica tutti i pattern di una categoria al testo.
        
        Args:
            text: Testo da processare
            category: Categoria di pattern (anonymization, parsing, security, cleaning)
            priority_order: Se True, applica in ordine di priorità
            
        Returns:
            Testo processato
        """
        if not isinstance(text, str):
            return text
        
        # Filtra pattern per categoria
        category_patterns = {
            name: config for name, config in self._patterns.items()
            if config['category'] == category
        }
        
        if not category_patterns:
            return text
        
        # Ordina per priorità se richiesto
        if priority_order and category == 'anonymization':
            sorted_patterns = sorted(
                category_patterns.items(),
                key=lambda x: x[1].get('priority', 999)
            )
        else:
            sorted_patterns = list(category_patterns.items())
        
        # Applica pattern in ordine
        result = text
        for pattern_name, _ in sorted_patterns:
            result = self.apply_pattern(result, pattern_name)
        
        return result
    
    def get_pattern_info(self, pattern_name: str) -> Optional[Dict[str, Any]]:
        """
        Ottiene informazioni su un pattern.
        
        Args:
            pattern_name: Nome del pattern
            
        Returns:
            Informazioni del pattern o None se non trovato
        """
        return self._patterns.get(pattern_name)
    
    def list_patterns(self, category: Optional[str] = None) -> List[str]:
        """
        Lista tutti i pattern disponibili.
        
        Args:
            category: Categoria da filtrare (opzionale)
            
        Returns:
            Lista dei nomi dei pattern
        """
        if category:
            return [
                name for name, config in self._patterns.items()
                if config['category'] == category
            ]
        return list(self._patterns.keys())

    def get_patterns_by_category(self, category: str) -> Dict[str, Any]:
        """
        Restituisce un dizionario di pattern filtrati per categoria.
        
        Args:
            category: La categoria di pattern da restituire (es. 'parsing_patterns').
            
        Returns:
            Un dizionario contenente i pattern della categoria specificata.
        """
        # Il file di configurazione ha categorie come 'parsing_patterns', 
        # ma il servizio internamente le normalizza in 'parsing'.
        # Per coerenza, ci aspettiamo la categoria normalizzata.
        normalized_category = category.replace('_patterns', '')
        
        return {
            name: config for name, config in self._patterns.items()
            if config.get('category') == normalized_category
        }
    
    def test_pattern(self, pattern_name: str, test_text: str) -> Dict[str, Any]:
        """
        Testa un pattern su un testo di esempio.
        
        Args:
            pattern_name: Nome del pattern
            test_text: Testo di test
            
        Returns:
            Risultati del test
        """
        pattern = self.get_compiled_pattern(pattern_name)
        if not pattern:
            return {'success': False, 'error': 'Pattern non trovato'}
        
        try:
            # Ottieni la stringa originale dal dizionario dei pattern
            pattern_config = self._patterns.get(pattern_name, {})
            original_pattern = pattern_config.get('pattern', pattern.pattern)
            
            # Usa match per pattern che iniziano con ^, search per altri
            # Rimuovi r'...' se presente
            clean_pattern = original_pattern
            if clean_pattern.startswith("r'") and clean_pattern.endswith("'"):
                clean_pattern = clean_pattern[2:-1]
            elif clean_pattern.startswith('r"') and clean_pattern.endswith('"'):
                clean_pattern = clean_pattern[2:-1]
            
            # Debug
            self.logger.debug(f"Testing pattern {pattern_name}:")
            self.logger.debug(f"  Original: {original_pattern}")
            self.logger.debug(f"  Clean: {clean_pattern}")
            self.logger.debug(f"  Starts with ^: {clean_pattern.startswith('^')}")
            self.logger.debug(f"  Test text: {test_text}")
            
            if clean_pattern.startswith('^'):
                match = pattern.match(test_text)
                self.logger.debug(f"  Using match(), result: {match}")
                if match:
                    if pattern.groups > 0:
                        matches = [match.groupdict()]
                    else:
                        matches = [match.group()]
                else:
                    matches = []
            else:
                if pattern.groups > 0:
                    match = pattern.search(test_text)
                    self.logger.debug(f"  Using search(), result: {match}")
                    matches = [match.groupdict()] if match else []
                else:
                    matches = pattern.findall(test_text)
                    self.logger.debug(f"  Using findall(), result: {matches}")
            
            self.logger.debug(f"  Final matches: {matches}")
            
            return {
                'success': True,
                'matches': matches,
                'match_count': len(matches),
                'pattern_info': self.get_pattern_info(pattern_name)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def validate_pattern(self, pattern_str: str) -> Dict[str, Any]:
        """
        Valida un pattern regex.
        
        Args:
            pattern_str: Stringa del pattern
            
        Returns:
            Risultato della validazione
        """
        try:
            re.compile(pattern_str)
            return {'valid': True, 'error': None}
        except re.error as e:
            return {'valid': False, 'error': str(e)}
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Ottiene statistiche sui pattern.
        
        Returns:
            Statistiche sui pattern
        """
        categories = {}
        for name, config in self._patterns.items():
            category = config['category']
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
        
        return {
            'total_patterns': len(self._patterns),
            'compiled_patterns': len(self._compiled_patterns),
            'categories': categories,
            'cache_hits': getattr(self.get_compiled_pattern, 'cache_info', lambda: {})()
        } 