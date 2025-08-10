"""
Dispatcher Euristico - Il Cervello del Sistema di Parsing.

Questo modulo contiene il componente centrale del parser composito,
il dispatcher, che utilizza euristiche per analizzare il testo
e assemblare dinamicamente catene di parser per decostruirlo.
"""

from typing import List, Callable, Tuple

from .interfaces import ParsingNode, ParsingResult
from .composite_parsers import ChoiceParser

from dataclasses import dataclass

# Un'euristica è una funzione semplice che ritorna True se il testo
# "sembra" di un certo tipo.
Heuristic = Callable[[str], bool]

@dataclass
class ParsingTheory:
    """
    Una "Teoria di Parsing" è una coppia: un'euristica per testare
    e un nodo di parsing da usare se il test ha successo.
    """
    heuristic: Heuristic
    parser: ParsingNode


class HeuristicDispatcher(ParsingNode):
    """
    Un parser composito che funge da "cervello", instradando l'input
    al parser più appropriato basandosi su una serie di euristiche.

    WHY: Incapsula la logica decisionale del sistema. Invece di avere
    un blocco `if/elif` monolitico, permette di registrare dinamicamente
    diverse "teorie" su come un log potrebbe essere strutturato. Questo
    rende il sistema estensibile e facile da comprendere.
    """

    def __init__(self, theories: List[ParsingTheory], fallback_parser: ParsingNode):
        """
        Inizializza il dispatcher.

        Args:
            theories: Una lista di tuple (euristica, parser).
            fallback_parser: Un parser da usare se nessuna euristica ha successo.
        """
        self.theories = theories
        self.fallback_parser = fallback_parser

    def parse(self, text: str, **kwargs) -> ParsingResult:
        """
        Testa ogni euristica sul testo. Se un'euristica ha successo,
        delega il parsing al parser associato. Se nessuna ha successo,
        usa il parser di fallback.
        """
        # Itera attraverso le teorie per trovare la prima applicabile
        for theory in self.theories:
            if theory.heuristic(text):
                # Trovata una teoria valida, delega al suo parser.
                result = theory.parser.parse(text, **kwargs)
                if result.success:
                    # Arricchisce il risultato con la teoria vincente per contestualizzazione
                    result.winning_theory = theory
                    return result
        
        # Se nessuna euristica ha prodotto un risultato valido, usa il fallback.
        fallback_result = self.fallback_parser.parse(text, **kwargs)
        fallback_result.winning_theory = ParsingTheory(lambda t: True, self.fallback_parser) # Crea una teoria di fallback
        return fallback_result

