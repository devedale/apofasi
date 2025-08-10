"""
Parser Decoratori (o Arricchitori).

Questi parser non implementano una logica di parsing diretta, ma "decorano"
o arricchiscono i risultati di altri parser.
"""

from .interfaces import ParsingNode, ParsingResult
from .leaf_parsers import KeyValueParser

class EnrichmentParser(ParsingNode):
    """
    Un parser decoratore che prende il risultato di un altro parser e tenta
    di "arricchirlo" cercando di parsare ricorsivamente i valori dei campi.

    WHY: Questa è la soluzione al problema della perdita di contesto. Se un parser
    iniziale estrae un grande campo "message", questo parser può riesaminare
    quel campo per trovare dati strutturati annidati (es. key=value),
    aggiungendoli al risultato finale senza perdere i dati originali.
    Implementa la logica di concatenazione delle chiavi (es. message_user).
    """

    def __init__(self, inner_parser: ParsingNode, recursive_parser: ParsingNode = None):
        """
        Inizializza il decoratore.

        Args:
            inner_parser: Il parser principale da eseguire per primo.
            recursive_parser: Il parser da usare per l'analisi ricorsiva dei campi.
                              Se non specificato, usa un KeyValueParser di default.
        """
        self.inner_parser = inner_parser
        self.recursive_parser = recursive_parser or KeyValueParser(pair_delimiter=r'\s*,?\s*')

    def parse(self, text: str, **kwargs) -> ParsingResult:
        """
        Esegue il parsing, poi l'arricchimento non distruttivo.
        """
        initial_result = self.inner_parser.parse(text, **kwargs)

        if not initial_result.success:
            return initial_result

        # Iniziamo con una copia dei dati originali. Non modificheremo mai
        # il risultato iniziale, ma solo la nostra copia arricchita.
        enriched_data = initial_result.parsed_data.copy()
        
        # Iteriamo su una COPIA degli item per evitare problemi di dimensione
        # del dizionario che cambia durante l'iterazione.
        fields_to_enrich = list(initial_result.parsed_data.items())

        for field_key, field_value in fields_to_enrich:
            if isinstance(field_value, str) and len(field_value) > 1:
                # Tentiamo di parsare ricorsivamente il valore di questo campo.
                recursive_result = self.recursive_parser.parse(field_value, **kwargs)
                
                if recursive_result.success and recursive_result.parsed_data:
                    # Arricchimento: Aggiungiamo i nuovi campi con la chiave concatenata.
                    # Il campo originale (field_key) non viene toccato.
                    for sub_key, sub_value in recursive_result.parsed_data.items():
                        # Non vogliamo prefissare il 'base_message' del sotto-parsing.
                        if sub_key == 'base_message': continue
                        
                        new_key = f"{field_key}_{sub_key}"
                        enriched_data[new_key] = sub_value
        
        return ParsingResult(
            success=True,
            parsed_data=enriched_data,
            remaining_text=initial_result.remaining_text,
            winning_theory=getattr(initial_result, 'winning_theory', None)
        )

