"""
Knowledge Service - Implementazione concreta del nucleo di conoscenza.
"""
import re
from pathlib import Path
from typing import Dict, Any, List

from .knowledge_service_interface import IKnowledgeService
from .regex_service import RegexService

class KnowledgeService(RegexService, IKnowledgeService):
    """
    Estende RegexService per fornire metodi di analisi di alto livello
    basati sui pattern regex caricati.
    """
    
    def __init__(self, config_path: Path = Path('config/config.yaml')):
        super().__init__(config_path)
        # Cache per i pattern aggregati, per evitare di ricalcolarli ogni volta
        self._aggregated_timestamp_pattern = None

    def _get_aggregated_timestamp_pattern(self) -> re.Pattern:
        """
        Crea un'unica, grande regex che matcha qualsiasi formato di timestamp
        definito nella configurazione.
        """
        if self._aggregated_timestamp_pattern:
            return self._aggregated_timestamp_pattern

        timestamp_patterns = self.get_category('timestamp_patterns')
        if not timestamp_patterns:
            # Ritorna un pattern che non matcha mai nulla se non ci sono definizioni
            return re.compile(r"^\b$") 

        # Unisce tutti i pattern dei timestamp con un "OR" (|)
        pattern_str = "|".join(p.pattern for p in timestamp_patterns.values())
        self._aggregated_timestamp_pattern = re.compile(pattern_str)
        return self._aggregated_timestamp_pattern

    def is_timestamp(self, text: str) -> bool:
        """Verifica se il testo è un timestamp noto."""
        # Controlla se l'INTERA stringa matcha uno dei pattern
        pattern = self._get_aggregated_timestamp_pattern()
        return pattern.fullmatch(text.strip()) is not None

    def extract_timestamps(self, text: str) -> List[str]:
        """Estrae tutti i timestamp noti dal testo."""
        pattern = self._get_aggregated_timestamp_pattern()
        return pattern.findall(text)

    def is_ip_address(self, text: str) -> bool:
        """Verifica se il testo è un indirizzo IP."""
        ip_pattern = self.get_pattern('anonymization_patterns', 'ip')
        return ip_pattern and ip_pattern.fullmatch(text.strip()) is not None

    def contains_kv_pairs(self, text: str) -> int:
        """Conta il numero di coppie chiave-valore nel testo."""
        # Usiamo un'euristica semplice per ora: contiamo le occorrenze di '='.
        # Questo può essere potenziato con regex più complessi in futuro.
        return text.count('=')

    def looks_like_json(self, text: str) -> bool:
        """Verifica se il testo ha l'aspetto di un JSON."""
        return text.strip().startswith('{') and text.strip().endswith('}')

    def get_text_profile(self, text: str) -> dict:
        """
        Genera un "vettore di caratteristiche" completo per il testo.
        """
        return {
            'starts_with_timestamp': len(self.extract_timestamps(text)) > 0 and text.startswith(self.extract_timestamps(text)[0]),
            'contains_kv_pairs': self.contains_kv_pairs(text),
            'looks_like_json': self.looks_like_json(text),
            'ip_address_count': len(self.get_pattern('anonymization_patterns', 'ip').findall(text)),
            'length': len(text)
        }

