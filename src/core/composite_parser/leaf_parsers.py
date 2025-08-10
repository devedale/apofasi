"""
Parser Primitivi (Foglie) del sistema Composite.

Questo modulo contiene le implementazioni dei parser di base, i "nodi foglia"
dell'albero, che eseguono operazioni di parsing atomiche e non delegono
ad altri parser.
"""

import re
from typing import Pattern

from .interfaces import ParsingNode, ParsingResult
from ...core.services.regex_service_interface import IRegexService

class RegexParser(ParsingNode):
    """
    Un parser primitivo che utilizza una singola espressione regolare per
    estrarre dati. I gruppi nominati nella regex diventano le chiavi
    nel dizionario dei dati parsati.

    WHY: È il mattone fondamentale per quasi tutti i parser specifici.
    Incapsula la logica di applicare una regex e restituire un risultato
    standardizzato, rendendo banale la creazione di parser per formati
    strutturati come Syslog, CEF, Apache, etc.
    """

    def __init__(self, regex_pattern: Pattern):
        """
        Inizializza il parser con un'espressione regolare pre-compilata.

        Args:
            regex_pattern: Un oggetto `re.Pattern` compilato.
        """
        if not isinstance(regex_pattern, Pattern):
            raise TypeError("regex_pattern must be a compiled regular expression.")
        self.regex_pattern = regex_pattern

    def parse(self, text: str, **kwargs) -> ParsingResult:
        """
        Applica la regex al testo e restituisce i gruppi nominati.

        Args:
            text: La stringa di input da parsare.

        Returns:
            Un ParsingResult. Se il match ha successo, `parsed_data` conterrà
            i gruppi nominati e `remaining_text` sarà la parte della stringa
            dopo il match. Altrimenti, `success` sarà False.
        """
        match = self.regex_pattern.match(text)

        if not match:
            return ParsingResult(success=False, errors=[f"Regex '{self.regex_pattern.pattern}' did not match."])

        parsed_data = match.groupdict()
        remaining_text = text[match.end():]

        return ParsingResult(
            success=True,
            parsed_data=parsed_data,
            remaining_text=remaining_text
        )

# Esempio di come si potrebbe creare un parser più specifico usando RegexParser
def create_cef_header_parser(regex_service: IRegexService) -> RegexParser:
    """
    Factory function per creare un parser specifico per l'header CEF.
    """
    cef_pattern = regex_service.get_pattern('parsing_patterns', 'cef')
    if not cef_pattern:
        raise ValueError("Pattern 'cef' non trovato in RegexService.")
    return RegexParser(cef_pattern)


class KeyValueParser(ParsingNode):
    """
    Un parser primitivo e generico per qualsiasi formato basato su coppie
    chiave-valore separate da delimitatori.

    WHY: Modella una delle famiglie strutturali fondamentali dei dati di log.
    È altamente configurabile per gestire variazioni come 'key=value',
    'key:value', coppie separate da virgole o spazi, etc.
    """
    def __init__(self, pair_delimiter: str = r'\s+', kv_separator: str = '=', quote_char: str = '"'):
        """
        Inizializza il parser.

        Args:
            pair_delimiter: Regex per il carattere che separa le coppie (es. r'\s+' o r',').
            kv_separator: Regex per il carattere che separa chiave e valore (es. '=' o ':').
            quote_char: Il carattere usato per le virgolette (es. '"').
        """
        self.pair_delimiter = pair_delimiter
        self.kv_separator = kv_separator
        self.quote_char = quote_char
        
        # Regex dinamica costruita sulla base dei parametri.
        # Spiegazione:
        self.kv_pattern = re.compile(
            # Gruppo 1: Chiave
            r'([a-zA-Z0-9_.-]+)'
            # Separatore
            r'\s*' + re.escape(self.kv_separator) + r'\s*'
            # Gruppo non catturante per il valore
            r'(?:'
            # Alternativa 1: Valore tra virgolette (Gruppo 2)
            r'"(.*?)"'
            r'|'
            # Alternativa 2: Valore non tra virgolette (Gruppo 3)
            # Qualsiasi sequenza di caratteri non-spazio
            r'(\S+)'
            r')'
        )

    def parse(self, text: str, **kwargs) -> ParsingResult:
        """
        Estrae tutte le coppie chiave-valore, preservando il testo
        non parsato in un campo 'base_message'.
        """
        matches = list(self.kv_pattern.finditer(text))
        
        if not matches:
            return ParsingResult(success=False, errors=[f"No key-value pairs found with separator '{self.kv_separator}'."])

        parsed_data = {}
        # Usiamo un bytearray per "cancellare" le parti di testo che parsiamo.
        # È più efficiente che creare nuove stringhe in un loop.
        remaining_text_mask = bytearray(text, 'utf-8')

        for match in matches:
            key = match.group(1)
            # Il valore può essere nel gruppo 2 (tra virgolette) o 3 (senza).
            value = match.group(2) if match.group(2) is not None else match.group(3)
            
            if key:
                parsed_data[key.strip()] = value.strip()
                # "Cancella" la parte del testo corrispondente al match
                start, end = match.span()
                remaining_text_mask[start:end] = b' ' * (end - start)

        # Il testo rimanente è ciò che non è stato parsato.
        unparsed_content = remaining_text_mask.decode('utf-8', errors='ignore').strip()
        if unparsed_content:
            parsed_data['base_message'] = unparsed_content

        return ParsingResult(success=True, parsed_data=parsed_data)

