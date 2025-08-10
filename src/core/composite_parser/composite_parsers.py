"""
Parser Compositi del sistema Composite.

Questo modulo contiene le implementazioni dei parser "ramo" dell'albero,
che orchestrano altri nodi (sia foglie che altri rami) per eseguire
operazioni di parsing complesse e ricorsive.
"""

from .interfaces import ParsingNode, ParsingResult

class HeaderPayloadParser(ParsingNode):
    """
    Un parser composito che implementa la logica ricorsiva di separare
    un "header" da un "payload".

    WHY: Questo è il cuore della nostra architettura ricorsiva. Permette di
    processare formati annidati (es. CEF dentro Syslog) in modo elegante.
    Un parser di alto livello non deve conoscere i dettagli del payload;
    il suo unico compito è separare l'header e rimettere in circolo
    il payload per un'ulteriore analisi.
    """

    def __init__(self, header_parser: ParsingNode, header_field_name: str = "header"):
        """
        Inizializza il parser.

        Args:
            header_parser: Un `ParsingNode` (tipicamente un `RegexParser`)
                           configurato per estrarre l'header.
            header_field_name: Il nome della chiave sotto cui verranno
                               salvati i dati dell'header nel risultato finale.
        """
        self.header_parser = header_parser
        self.header_field_name = header_field_name

    def parse(self, text: str, **kwargs) -> ParsingResult:
        """
        Esegue il parsing in due fasi:
        1. Applica l'header_parser per estrarre l'header.
        2. Restituisce i dati dell'header e il payload come `remaining_text`.
        """
        header_result = self.header_parser.parse(text, **kwargs)

        if not header_result.success:
            return ParsingResult(
                success=False,
                errors=[f"Header parsing failed."] + header_result.errors
            )

        # Il risultato finale avrà successo, i dati dell'header saranno
        # annidati sotto la chiave specificata, e il testo rimanente
        # sarà il payload da processare ulteriormente.
        final_data = {self.header_field_name: header_result.parsed_data}
        
        return ParsingResult(
            success=True,
            parsed_data=final_data,
            remaining_text=header_result.remaining_text
        )


from typing import List

class ChoiceParser(ParsingNode):
    """
    Un parser composito che prova una lista di parser in sequenza e
    restituisce il risultato del primo che ha successo.

    WHY: È il costrutto fondamentale per creare fallback e per testare
    diversi formati possibili su un dato input. Sostituisce la logica
    imperativa "if format A, else if format B, else..." con un approccio
    dichiarativo e componibile.
    """

    def __init__(self, parsers: List[ParsingNode]):
        """
        Inizializza il parser con una lista di nodi da provare.

        Args:
            parsers: Una lista di istanze `ParsingNode`.
        """
        self.parsers = parsers

    def parse(self, text: str, **kwargs) -> ParsingResult:
        """
        Itera attraverso i parser e restituisce il primo risultato positivo.
        """
        all_errors = []
        for parser in self.parsers:
            result = parser.parse(text, **kwargs)
            if result.success:
                return result
            all_errors.extend(result.errors)
        
        return ParsingResult(
            success=False,
            errors=["No parser in the choice was successful."] + all_errors
        )


from .leaf_parsers import KeyValueParser

class InlineHeaderParser(ParsingNode):
    """
    Parser di Famiglia per dati con "Header Inline" (es. key=value).
    Questo è essenzialmente un wrapper attorno a un KeyValueParser più generico.

    WHY: Rappresenta l'astrazione di una delle famiglie strutturali fondamentali.
    Il motore di inferenza può decidere di usare questo parser quando rileva
    che un log appartiene a questa famiglia.
    """
    def __init__(self, **kwargs):
        """
        Inizializza il parser, passando eventuali configurazioni
        (es. pair_delimiter, kv_separator) al KeyValueParser sottostante.
        """
        self.kv_parser = KeyValueParser(**kwargs)

    def parse(self, text: str, **kwargs) -> ParsingResult:
        return self.kv_parser.parse(text, **kwargs)


import csv
import io

class SeparateLineHeaderParser(ParsingNode):
    """
    Parser di Famiglia per dati con "Header Separato" (es. CSV), potenziato
    con il modulo CSV standard di Python per gestire correttamente i campi virgolettati.
    """
    def __init__(self, delimiter: str = ',', header: List[str] = None):
        self.delimiter = delimiter
        self.header = header

    def _parse_line(self, line: str) -> List[str]:
        """Usa il modulo csv per parsare una singola linea in modo robusto."""
        # Trattiamo la linea come un piccolo file in memoria
        reader = csv.reader(io.StringIO(line), delimiter=self.delimiter)
        try:
            return next(reader)
        except StopIteration:
            return []

    def parse(self, text: str, **kwargs) -> ParsingResult:
        if self.header:
            # Modalità "Specialista"
            values = self._parse_line(text)
            if not values:
                return ParsingResult(success=False, errors=["Empty data line."])

            if len(values) > len(self.header):
                values = values[:len(self.header)]
            elif len(values) < len(self.header):
                return ParsingResult(success=False, errors=[f"Data column count ({len(values)}) is less than header count ({len(self.header)})."])

            parsed_data = dict(zip(self.header, values))
            return ParsingResult(success=True, parsed_data=parsed_data)
        else:
            # Modalità "Investigatore"
            lines = text.strip().split('\n')
            if len(lines) < 2:
                return ParsingResult(success=False, errors=["Requires at least 2 lines for header and data."])

            header = self._parse_line(lines[0])
            values = self._parse_line(lines[1])

            if not header or not values:
                return ParsingResult(success=False, errors=["Could not parse header or data line."])
            
            if len(values) != len(header):
                return ParsingResult(success=False, errors=["Header and data column count mismatch."])

            parsed_data = dict(zip(header, values))
            remaining_text = '\n'.join(lines[2:])
            return ParsingResult(success=True, parsed_data=parsed_data, remaining_text=remaining_text)

