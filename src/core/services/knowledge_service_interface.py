"""
Interfaccia per il Knowledge Service, il nucleo di conoscenza
del motore di inferenza euristica.
"""

from abc import abstractmethod
from typing import List, Tuple

from .regex_service_interface import IRegexService

class IKnowledgeService(IRegexService):
    """
    Estende IRegexService con metodi di analisi di alto livello
    per interrogare la natura di una stringa di testo.
    """

    @abstractmethod
    def is_timestamp(self, text: str) -> bool:
        """Verifica se il testo è un timestamp noto."""
        pass

    @abstractmethod
    def extract_timestamps(self, text: str) -> List[str]:
        """Estrae tutti i timestamp noti dal testo."""
        pass

    @abstractmethod
    def is_ip_address(self, text: str) -> bool:
        """Verifica se il testo è un indirizzo IP."""
        pass

    @abstractmethod
    def contains_kv_pairs(self, text: str) -> int:
        """Conta il numero di coppie chiave-valore nel testo."""
        pass

    @abstractmethod
    def looks_like_json(self, text: str) -> bool:
        """Verifica se il testo ha l'aspetto di un JSON."""
        pass

    @abstractmethod
    def get_text_profile(self, text: str) -> dict:
        """
        Genera un "vettore di caratteristiche" completo per il testo,
        usando tutte le altre funzioni di analisi.
        """
        pass

