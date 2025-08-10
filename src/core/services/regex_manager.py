"""
Manager per la gestione dinamica dei pattern regex.

WHY: Permette di aggiungere/modificare pattern regex senza modificare il codice,
supportando configurazione file e future interfacce utente.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from .regex_service import RegexService


class RegexManager:
    """
    Manager per la gestione dinamica dei pattern regex.
    
    WHY: Fornisce interfaccia per aggiungere/modificare pattern
    senza toccare il codice, supportando configurazione e UI future.
    
    Contract:
        - Input: Pattern config o pattern string
        - Output: Pattern aggiunto/modificato
        - Side effects: Aggiorna configurazione e ricompila
    """
    
    def __init__(self, config_path: Path = None):
        """
        Inizializza il manager regex.
        
        Args:
            config_path: Percorso al file di configurazione
        """
        self.config_path = config_path or Path("config/regex_patterns.yaml")
        self.regex_service = RegexService(self.config_path)
        self._load_config()
    
    def _load_config(self):
        """Carica la configurazione attuale."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            self.regex_service.logger.error(f"❌ Errore caricamento config: {e}")
            self.config = {}
    
    def _save_config(self):
        """Salva la configurazione aggiornata."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            self.regex_service.logger.info("✅ Configurazione regex salvata")
        except Exception as e:
            self.regex_service.logger.error(f"❌ Errore salvataggio config: {e}")
    
    def add_pattern(self, category: str, name: str, pattern: str, 
                   replacement: str = "", priority: int = 999, 
                   description: str = "", flags: str = "") -> bool:
        """
        Aggiunge un nuovo pattern regex.
        
        Args:
            category: Categoria (anonymization, parsing, security, cleaning)
            name: Nome del pattern
            pattern: Stringa del pattern regex
            replacement: Sostituzione (per anonymization/cleaning)
            priority: Priorità (per anonymization)
            description: Descrizione del pattern
            flags: Flag regex (IGNORECASE, MULTILINE, etc.)
            
        Returns:
            True se aggiunto con successo
        """
        try:
            # Valida il pattern
            import re
            re.compile(pattern)
            
            # Crea configurazione pattern
            pattern_config = {
                'pattern': pattern,
                'description': description
            }
            
            # Aggiungi campi specifici per categoria
            if category == 'anonymization':
                pattern_config.update({
                    'replacement': replacement,
                    'priority': priority
                })
            elif category == 'cleaning':
                pattern_config.update({
                    'replacement': replacement
                })
            elif category == 'security':
                pattern_config.update({
                    'flags': flags
                })
            
            # Aggiungi al config
            category_key = f"{category}_patterns"
            if category_key not in self.config:
                self.config[category_key] = {}
            
            self.config[category_key][name] = pattern_config
            
            # Salva configurazione
            self._save_config()
            
            # Ricompila il servizio regex
            self.regex_service = RegexService(self.config_path)
            
            self.regex_service.logger.info(f"✅ Pattern aggiunto: {category}.{name}")
            return True
            
        except Exception as e:
            self.regex_service.logger.error(f"❌ Errore aggiunta pattern: {e}")
            return False
    
    def remove_pattern(self, category: str, name: str) -> bool:
        """
        Rimuove un pattern regex.
        
        Args:
            category: Categoria del pattern
            name: Nome del pattern
            
        Returns:
            True se rimosso con successo
        """
        try:
            category_key = f"{category}_patterns"
            if category_key in self.config and name in self.config[category_key]:
                del self.config[category_key][name]
                self._save_config()
                self.regex_service = RegexService(self.config_path)
                self.regex_service.logger.info(f"✅ Pattern rimosso: {category}.{name}")
                return True
            else:
                self.regex_service.logger.warning(f"⚠️ Pattern non trovato: {category}.{name}")
                return False
        except Exception as e:
            self.regex_service.logger.error(f"❌ Errore rimozione pattern: {e}")
            return False
    
    def update_pattern(self, category: str, name: str, **kwargs) -> bool:
        """
        Aggiorna un pattern esistente.
        
        Args:
            category: Categoria del pattern
            name: Nome del pattern
            **kwargs: Campi da aggiornare
            
        Returns:
            True se aggiornato con successo
        """
        try:
            category_key = f"{category}_patterns"
            if category_key in self.config and name in self.config[category_key]:
                pattern_config = self.config[category_key][name]
                pattern_config.update(kwargs)
                self._save_config()
                self.regex_service = RegexService(self.config_path)
                self.regex_service.logger.info(f"✅ Pattern aggiornato: {category}.{name}")
                return True
            else:
                self.regex_service.logger.warning(f"⚠️ Pattern non trovato: {category}.{name}")
                return False
        except Exception as e:
            self.regex_service.logger.error(f"❌ Errore aggiornamento pattern: {e}")
            return False
    
    def list_patterns(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Lista tutti i pattern disponibili.
        
        Args:
            category: Categoria da filtrare (opzionale)
            
        Returns:
            Dizionario con pattern organizzati per categoria
        """
        if category:
            category_key = f"{category}_patterns"
            return self.config.get(category_key, {})
        else:
            return {
                cat.replace('_patterns', ''): patterns
                for cat, patterns in self.config.items()
                if cat.endswith('_patterns')
            }
    
    def validate_pattern(self, pattern: str) -> Dict[str, Any]:
        """
        Valida un pattern regex.
        
        Args:
            pattern: Stringa del pattern
            
        Returns:
            Risultato della validazione
        """
        try:
            import re
            re.compile(pattern)
            return {'valid': True, 'error': None}
        except re.error as e:
            return {'valid': False, 'error': str(e)}
    
    def test_pattern(self, pattern: str, test_text: str) -> Dict[str, Any]:
        """
        Testa un pattern su testo di esempio.
        
        Args:
            pattern: Stringa del pattern
            test_text: Testo di test
            
        Returns:
            Risultati del test
        """
        try:
            import re
            compiled = re.compile(pattern)
            matches = compiled.findall(test_text)
            return {
                'valid': True,
                'matches': matches,
                'match_count': len(matches)
            }
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Ottiene statistiche sui pattern.
        
        Returns:
            Statistiche sui pattern
        """
        stats = {}
        for category_key, patterns in self.config.items():
            if category_key.endswith('_patterns'):
                category = category_key.replace('_patterns', '')
                stats[category] = len(patterns)
        
        return {
            'total_patterns': sum(stats.values()),
            'categories': stats,
            'config_file': str(self.config_path)
        } 