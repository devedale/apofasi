"""
Classe base ABC per i parser.

WHY: Evita import circolari tra i parser e fornisce
un'interfaccia comune per tutti i parser.
"""

from abc import ABC, abstractmethod
from typing import Iterator, Dict, Any, Optional
import logging


class BaseParserABC(ABC):
    """
    Classe base astratta per tutti i parser.
    
    WHY: Fornisce un'interfaccia comune e evita import circolari.
    
    Contract:
        - Input: Contenuto da parsare
        - Output: Iterator di record parsati
        - Side effects: Logging di errori e warning
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inizializza il parser base.
        
        Args:
            config: Configurazione opzionale
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def can_parse(self, content: str, filename: str = None) -> bool:
        """
        Determina se il contenuto può essere parsato.
        
        Args:
            content: Contenuto da analizzare
            filename: Nome del file (opzionale)
            
        Returns:
            True se il contenuto può essere parsato
        """
        pass
    
    @abstractmethod
    def parse(self, content: str, filename: str = None) -> Iterator[Dict[str, Any]]:
        """
        Parsa il contenuto.
        
        Args:
            content: Contenuto da parsare
            filename: Nome del file (opzionale)
            
        Yields:
            Record parsati
        """
        pass
    
    def log_error(self, message: str, line_number: int = None, line_content: str = None):
        """Logga un errore."""
        error_msg = f"ERROR: {message}"
        if line_number:
            error_msg += f" (line {line_number})"
        if line_content:
            error_msg += f" - Content: {line_content[:100]}"
        self.logger.error(error_msg)
    
    def log_warning(self, message: str, line_number: int = None):
        """Logga un warning."""
        warning_msg = f"WARNING: {message}"
        if line_number:
            warning_msg += f" (line {line_number})"
        self.logger.warning(warning_msg)
    
    def log_info(self, message: str):
        """Logga un messaggio informativo."""
        self.logger.info(message) 