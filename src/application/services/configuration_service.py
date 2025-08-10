"""
Servizio per la gestione della configurazione.
"""

import yaml
from pathlib import Path
from typing import Dict, Any

from ...infrastructure.config_loader import ConfigLoader


class ConfigurationService:
    """Servizio per la gestione della configurazione."""
    
    def __init__(self):
        self.config_loader = ConfigLoader()
    
    def load_configuration(self, config_path: str) -> Dict[str, Any]:
        """
        Carica la configurazione dal file specificato.
        
        Args:
            config_path: Percorso del file di configurazione
            
        Returns:
            Configurazione caricata
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"File di configurazione non trovato: {config_path}")
        
        return self.config_loader.load_config(config_file)
    
    def load_default_configuration(self) -> Dict[str, Any]:
        """
        Carica la configurazione di default.
        
        Returns:
            Configurazione di default
        """
        return self.config_loader.load_default_config()
    
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Valida la configurazione.
        
        Args:
            config: Configurazione da validare
            
        Returns:
            True se la configurazione è valida
        """
        required_sections = ["app", "drain3", "parsers"]
        
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Sezione mancante nella configurazione: {section}")
        
        return True 