"""
Interfaccia per i parser di log.

WHY: Questa interfaccia definisce il contratto che tutti i parser devono rispettare,
garantendo coerenza e iniezione di dipendenze obbligatorie come source_file.

DESIGN: Interfaccia che forza l'iniezione di source_file per evitare errori
"source_file is not defined" e garantire tracciabilità completa.
"""

from abc import ABC, abstractmethod
from typing import Iterator, Optional, Dict, Any, List
from pathlib import Path

from ..entities.log_entry import LogEntry
from ..entities.parsed_record import ParsedRecord


class LogParser(ABC):
    """
    Interfaccia astratta per tutti i parser di log.
    
    WHY: Garantisce che tutti i parser abbiano accesso a source_file e
    seguano lo stesso contratto per evitare errori di scope.
    
    Contract:
        - Input: LogEntry con source_file obbligatorio
        - Output: Iterator di ParsedRecord con source_file sempre definito
        - Side effects: Nessuno, parsing puro
        - source_file: SEMPRE iniettato e disponibile
        - detected_keys: SEMPRE estratte e aggiunte a parsed_data
    """
    
    @abstractmethod
    def can_parse(self, content: str, filename: Optional[str] = None) -> bool:
        """
        Determina se questo parser può gestire il contenuto.
        
        Args:
            content: Contenuto da analizzare
            filename: Nome del file (opzionale ma raccomandato)
            
        Returns:
            True se il contenuto può essere parsato da questo parser
        """
        pass
    
    @abstractmethod
    def parse(self, log_entry: LogEntry) -> Iterator[ParsedRecord]:
        """
        Parsa il contenuto del log e restituisce record strutturati.
        
        WHY: source_file è SEMPRE disponibile tramite log_entry.source_file.
        Questo elimina gli errori "source_file is not defined" by design.
        
        Args:
            log_entry: Entry del log con source_file OBBLIGATORIO
            
        Yields:
            ParsedRecord instances con source_file sempre definito
            
        Raises:
            ValueError: Se log_entry.source_file è None o vuoto
        """
        pass
    
    @abstractmethod
    def extract_detected_keys(self, content: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estrae e aggiunge le chiavi rilevate al parsed_data.
        
        WHY: By design, tutti i parser devono implementare questa funzione
        per garantire coerenza nell'estrazione di chiavi e pattern rilevati.
        
        DESIGN: Metodo obbligatorio che:
        1. Analizza il contenuto per identificare chiavi rilevanti
        2. Estrae pattern, tipi di dati, e metadati
        3. Aggiunge le chiavi rilevate a parsed_data
        4. Garantisce coerenza tra tutti i parser
        
        Args:
            content: Contenuto originale del log
            parsed_data: Dati già parsati dal parser
            
        Returns:
            parsed_data arricchito con chiavi rilevate
            
        Raises:
            NotImplementedError: Se il parser non implementa l'estrazione
        """
        pass
    
    def get_parser_info(self) -> dict:
        """
        Restituisce informazioni sul parser.
        
        Returns:
            Dizionario con informazioni sul parser
        """
        return {
            'name': self.__class__.__name__,
            'description': 'Parser di log generico',
            'implements_detected_keys': True
        }
    
    def _validate_log_entry(self, log_entry: LogEntry) -> None:
        """
        Valida che log_entry abbia source_file definito.
        
        WHY: Prevenzione by design degli errori "source_file is not defined".
        Questo metodo deve essere chiamato all'inizio di ogni parse().
        
        Args:
            log_entry: Entry del log da validare
            
        Raises:
            ValueError: Se source_file è None o vuoto
        """
        if not log_entry.source_file:
            raise ValueError(
                f"LogEntry deve avere source_file definito. "
                f"Ricevuto: {log_entry.source_file}"
            )
        
        if not str(log_entry.source_file).strip():
            raise ValueError(
                f"LogEntry.source_file non può essere vuoto. "
                f"Ricevuto: '{log_entry.source_file}'"
            )
    
    def _enrich_parsed_data_with_detected_keys(self, content: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Metodo helper per arricchire parsed_data con chiavi rilevate.
        
        WHY: Metodo comune che tutti i parser possono usare per
        arricchire i dati parsati con chiavi rilevate standard.
        
        Args:
            content: Contenuto originale del log
            parsed_data: Dati parsati dal parser
            
        Returns:
            parsed_data arricchito con chiavi rilevate standard
        """
        # Estrai chiavi rilevate specifiche del parser
        enriched_data = self.extract_detected_keys(content, parsed_data)
        
        # Aggiungi metadati standard
        enriched_data.update({
            '_parser_metadata': {
                'parser_name': self.__class__.__name__,
                'implements_detected_keys': True,
                'extraction_method': 'standard'
            }
        })
        
        return enriched_data 