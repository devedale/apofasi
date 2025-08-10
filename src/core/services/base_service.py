"""
Classe base per tutti i servizi core.

WHY: Fornisce funzionalità comuni a tutti i servizi core
come logging e gestione errori.
"""

import logging
from typing import Optional


class BaseService:
    """
    Classe base per tutti i servizi core.
    
    WHY: Centralizza funzionalità comuni come logging
    e gestione errori per tutti i servizi.
    
    Contract:
        - Input: Configurazione opzionale
        - Output: Servizio configurato
        - Side effects: Setup logging
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Inizializza il servizio base.
        
        Args:
            logger: Logger opzionale, se non fornito ne crea uno
        """
        if logger is None:
            # Crea logger di default
            self.logger = logging.getLogger(self.__class__.__name__)
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
        else:
            self.logger = logger
    
    def log_info(self, message: str):
        """Logga un messaggio informativo."""
        self.logger.info(message)
    
    def log_warning(self, message: str):
        """Logga un warning."""
        self.logger.warning(message)
    
    def log_error(self, message: str):
        """Logga un errore."""
        self.logger.error(message)
    
    def log_debug(self, message: str):
        """Logga un messaggio di debug."""
        self.logger.debug(message)
    
    # Metodi di compatibilità per il codice esistente
    def info(self, message: str):
        """Logga un messaggio informativo."""
        self.log_info(message)
    
    def warning(self, message: str):
        """Logga un warning."""
        self.log_warning(message)
    
    def error(self, message: str):
        """Logga un errore."""
        self.log_error(message)
    
    def debug(self, message: str):
        """Logga un messaggio di debug."""
        self.log_debug(message) 