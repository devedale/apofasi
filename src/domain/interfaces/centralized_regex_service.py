"""
Interfaccia per il servizio regex centralizzato.

DESIGN: Definisce il contratto per tutti i servizi regex,
garantendo coerenza e intercambiabilità delle implementazioni.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any


class CentralizedRegexService(ABC):
    """Interfaccia astratta per il servizio regex centralizzato."""
    
    @abstractmethod
    def get_anonymization_patterns(self) -> Dict[str, Dict[str, str]]:
        """Restituisce tutti i pattern di anonimizzazione."""
        pass
    
    @abstractmethod
    def get_pattern_detection_patterns(self) -> Dict[str, Dict[str, str]]:
        """Restituisce tutti i pattern per la detection."""
        pass
    
    @abstractmethod
    def get_parsing_patterns(self) -> Dict[str, Dict[str, str]]:
        """Restituisce tutti i pattern per il parsing."""
        pass
    
    @abstractmethod
    def get_cleaning_patterns(self) -> Dict[str, Dict[str, str]]:
        """Restituisce tutti i pattern per il cleaning."""
        pass
    
    @abstractmethod
    def get_csv_recognition_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per il riconoscimento CSV."""
        pass
    
    @abstractmethod
    def get_field_detection_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per il rilevamento automatico dei tipi."""
        pass
    
    @abstractmethod
    def get_timestamp_normalization_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per la normalizzazione timestamp."""
        pass
    
    @abstractmethod
    def get_complex_csv_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per CSV complessi."""
        pass
    
    @abstractmethod
    def get_intelligent_analysis_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per l'analisi intelligente."""
        pass
    
    @abstractmethod
    def get_parsers_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per i parser specifici."""
        pass
    
    @abstractmethod
    def get_output_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per l'output."""
        pass
    
    @abstractmethod
    def get_logging_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per il logging."""
        pass
    
    @abstractmethod
    def get_parser_adaptive_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per il parser universale adattivo."""
        pass
    
    @abstractmethod
    def get_file_formats_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per i formati di file supportati."""
        pass
    
    @abstractmethod
    def get_app_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione generale dell'applicazione."""
        pass
    
    @abstractmethod
    def anonymize_content(self, content: str) -> str:
        """Anonimizza il contenuto usando i pattern centralizzati."""
        pass
    
    @abstractmethod
    def detect_patterns(self, content: str) -> Dict[str, List[str]]:
        """Rileva pattern nel contenuto usando le regex centralizzate."""
        pass
    
    @abstractmethod
    def get_template_from_content(self, content: str, anonymized: bool = False) -> str:
        """Genera un template dal contenuto, opzionalmente anonimizzato."""
        pass



