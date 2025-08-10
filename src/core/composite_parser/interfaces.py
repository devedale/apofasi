"""
Interfacce Core per il Composite Parser System.

Questo modulo definisce le strutture dati e le interfacce fondamentali
che governano il funzionamento del parser composito.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List

@dataclass
class ParsingResult:
    """
    Struttura dati standardizzata per l'output di qualsiasi nodo di parsing.

    WHY: Fornisce un contratto di output coerente per tutti i parser,
    semplificando la loro composizione e interazione. Un parser non deve
    sapere come funziona un altro; deve solo sapere che riceverà un
    ParsingResult.

    Attributes:
        success: True se il parsing ha avuto successo, altrimenti False.
        parsed_data: I dati strutturati estratti dal testo.
        remaining_text: La parte del testo che non è stata processata.
        errors: Una lista di errori riscontrati during il parsing.
        winning_theory: La teoria euristica che ha portato al successo (forward reference).
    """
    success: bool
    parsed_data: Dict[str, Any] = field(default_factory=dict)
    remaining_text: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    winning_theory: Optional['ParsingTheory'] = None


class ParsingNode(ABC):
    """
    Interfaccia base (Classe Base Astratta) per ogni nodo dell'albero di parsing.

    WHY: Definisce il contratto universale per tutti i componenti del parser.
    Sia un parser primitivo (foglia) che un parser complesso (composito)
    sono trattati allo stesso modo, permettendo una ricorsione e una
    composizione illimitate.
    """

    @abstractmethod
    def parse(self, text: str, **kwargs) -> ParsingResult:
        """
        Metodo principale per eseguire il parsing su una stringa di testo.

        Args:
            text: La stringa di input da parsare.
            **kwargs: Argomenti opzionali che possono essere passati
                      tra i parser (es. contesto, configurazioni).

        Returns:
            Un oggetto ParsingResult con l'esito dell'operazione.
        """
        pass

