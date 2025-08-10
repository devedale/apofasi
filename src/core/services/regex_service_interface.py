"""
Interfaccia per il Servizio di Gestione delle Espressioni Regolari
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
import re

class IRegexService(ABC):
    """
    Interfaccia che definisce il contratto per un servizio che gestisce,
    compila e fornisce espressioni regolari da una fonte centralizzata.

    WHY: Definisce un contratto stabile per disaccoppiare i componenti
    che utilizzano le regex dalla loro implementazione specifica. Questo permette
    di sostituire facilmente l'implementazione (es. per testing o per
    caricare le regex da un database invece che da un file) senza
    modificare i consumatori del servizio.
    """

    @abstractmethod
    def get_pattern(self, category: str, name: str) -> Optional[re.Pattern]:
        """
        Restituisce un pattern regex compilato.

        Args:
            category: La categoria del pattern (es. 'parsing_patterns').
            name: Il nome del pattern (es. 'apache_clf').
        
        Returns:
            Un oggetto re.Pattern compilato o None se non trovato.
        """
        pass

    @abstractmethod
    def get_category(self, category: str) -> Dict[str, re.Pattern]:
        """
        Restituisce tutti i pattern compilati per una data categoria.
        
        Args:
            category: La categoria dei pattern da restituire.
        
        Returns:
            Un dizionario di pattern compilati.
        """
        pass

    @property
    @abstractmethod
    def anonymization_patterns(self) -> Dict[str, re.Pattern]:
        """Restituisce i pattern di anonimizzazione."""
        pass

    @property
    @abstractmethod
    def parsing_patterns(self) -> Dict[str, re.Pattern]:
        """Restituisce i pattern di parsing."""
        pass
        
    @property
    @abstractmethod
    def cleaning_patterns(self) -> Dict[str, re.Pattern]:
        """Restituisce i pattern di pulizia."""
        pass

    @property
    @abstractmethod
    def security_patterns(self) -> Dict[str, re.Pattern]:
        """Restituisce i pattern di sicurezza."""
        pass

    @property
    @abstractmethod
    def type_detection_patterns(self) -> Dict[str, re.Pattern]:
        """Restituisce i pattern per il rilevamento dei tipi."""
        pass

