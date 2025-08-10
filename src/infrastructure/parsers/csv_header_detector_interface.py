"""
Interfaccia per il Rilevatore di Header CSV
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class CSVHeaderInfo:
    """Contiene informazioni sugli header CSV rilevati."""
    headers: List[str]
    delimiter: str
    confidence: float
    header_line_number: int

class ICSVHeaderDetector(ABC):
    """
    Interfaccia che definisce il contratto per un componente che rileva
    gli header e il delimitatore da un campione di righe CSV.

    WHY: Permette di disaccoppiare la logica di parsing dalla logica
    specifica di rilevamento degli header, consentendo di sostituire
    l'algoritmo di detection senza impattare i parser che lo utilizzano.
    """

    @abstractmethod
    def detect_headers(self, sample_lines: List[str]) -> Optional[CSVHeaderInfo]:
        """
        Analizza le righe di esempio per trovare la riga di intestazione più probabile.

        Args:
            sample_lines: Una lista di stringhe che rappresentano le prime righe di un file.

        Returns:
            Un oggetto CSVHeaderInfo se viene trovata un'intestazione valida, altrimenti None.
        """
        pass

    @abstractmethod
    def clean_header_names(self, headers: List[str]) -> List[str]:
        """
        Pulisce i nomi degli header per renderli validi come identificatori.

        Args:
            headers: La lista dei nomi degli header da pulire.

        Returns:
            Una lista di nomi di header puliti.
        """
        pass

