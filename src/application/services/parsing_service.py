"""
Servizio principale per il parsing dei log.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Iterator, Optional

from ...domain.services.log_processing_service import LogProcessingService
from ...infrastructure.parsers.multi_strategy_parser import MultiStrategyParser
from ...infrastructure.drain3_service import Drain3ServiceImpl
from ...infrastructure.anonymizer import RegexAnonymizer
from ...infrastructure.parsers import create_parsers
from ...domain.interfaces.log_parser import LogParser
from ...domain.interfaces.drain3_service import Drain3Service
from ...domain.interfaces.anonymizer import Anonymizer
from ...domain.interfaces.log_reader import LogReader
from ...domain.entities.log_entry import LogEntry
from ...domain.entities.parsed_record import ParsedRecord


# Rimosso MultiStrategyParserAdapter - non più necessario


class ParsingService:
    """
    Servizio principale per il parsing dei log.

    Function Comments:
    - Scopo: coordinare la creazione dei componenti di parsing e offrire API di alto livello
      per processare file o liste di `LogEntry`.
    - Input: `config` obbligatoria; dipendenze opzionali via DI (`log_parser`, `drain3_service`,
      `anonymizer`, `log_reader`).
    - Output: risultati parsati come lista di dict (serializzabili JSON) o accesso alle statistiche.
    - Side effects: lettura file tramite `LogReader` e scrittura output quando usato con `ReportingService` (fuori da questa classe).
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        *,
        log_parser: Optional[LogParser] = None,
        drain3_service: Optional[Drain3Service] = None,
        anonymizer: Optional[Anonymizer] = None,
        log_reader: Optional[LogReader] = None,
    ):
        """
        Inizializza il servizio con supporto a Dependency Injection opzionale.

        Args:
            config: configurazione dell'applicazione e dei componenti di parsing
            log_parser: implementazione `LogParser` da usare (default: `MultiStrategyParser`)
            drain3_service: implementazione `Drain3Service` (default: `Drain3ServiceImpl`)
            anonymizer: implementazione `Anonymizer` (default: `RegexAnonymizer`)
            log_reader: implementazione `LogReader` per l'I/O (default: `SimpleLogReader` interno a `LogProcessingService`)

        Why: permettere testabilità e sostituibilità dei componenti senza rompere la CLI.
        """
        """
        Inizializza il servizio di parsing.
        
        Args:
            config: Configurazione del sistema
        """
        self.config = config
        
        # Crea un RegexService condiviso per evitare logging ripetuto
        from ...core.services.regex_service import RegexService
        self.regex_service = RegexService()
        
        # Crea i componenti con RegexService condiviso, consentendo override via DI
        if log_parser is not None:
            multi_strategy_parser = log_parser
        else:
            parsers = create_parsers(config, self.regex_service)  # Passa RegexService condiviso
            multi_strategy_parser = parsers[0]  # Prendi il primo (e unico) parser

        drain3_service_instance = drain3_service or Drain3ServiceImpl(config)
        anonymizer_instance = anonymizer or RegexAnonymizer(config)
        
        # Crea il servizio principale
        self.log_processing_service = LogProcessingService(
            parser_orchestrator=multi_strategy_parser,  # Usa direttamente MultiStrategyParser
            drain3_service=drain3_service_instance,
            anonymizer=anonymizer_instance,
            config=config,  # Passa la configurazione
            log_reader=log_reader,
        )
    
    def parse_files(self, input_path: str) -> List[Dict[str, Any]]:
        """
        Parsa i file specificati.
        
        Args:
            input_path: Percorso del file o directory da parsare
            
        Returns:
            Lista dei risultati parsati
        """
        input_path_obj = Path(input_path)
        
        if not input_path_obj.exists():
            raise FileNotFoundError(f"Percorso non trovato: {input_path}")
        
        all_records = []
        
        if input_path_obj.is_file():
            print(f"📄 Parsing file: {input_path_obj}")
            records = list(self.log_processing_service.process_file(input_path_obj))
            all_records.extend(records)
            print(f"✅ Processati {len(records)} record dal file")
            
        elif input_path_obj.is_dir():
            print(f"📁 Parsing directory: {input_path_obj}")
            records = list(self.log_processing_service.process_directory(input_path_obj))
            all_records.extend(records)
            print(f"✅ Processati {len(records)} record dalla directory")
            
        else:
            raise ValueError(f"Percorso non valido: {input_path}")
        
        # IMPORTANTE: Ora processa tutto il dataset con Drain3 per clustering significativo
        # Questo sostituisce il processing record-per-record che non aveva senso
        print(f"🔄 Processing {len(all_records)} records with Drain3 for dual mining...")
        all_records = self.log_processing_service.process_dataset_with_drain3(all_records)
        
        # Converti i record in dizionari per il JSON
        results = []
        for record in all_records:
            if hasattr(record, 'to_dict'):
                results.append(record.to_dict())
            else:
                # Se il record è già un dizionario
                results.append(record)
        
        return results

    def parse_log_entries(self, log_entries: List['LogEntry']) -> List[Dict[str, Any]]:
        """
        Parsa una lista di singole entry di log.

        Args:
            log_entries: Lista di oggetti LogEntry da parsare.
            
        Returns:
            Lista dei risultati parsati come dizionari.
        """
        all_records = []
        for entry in log_entries:
            # Il metodo `process_entry` dovrebbe restituire un singolo ParsedRecord
            record = self.log_processing_service.process_entry(entry)
            if record:
                all_records.append(record)
        
        # Converti i record in dizionari per l'output
        results = [rec.to_dict() for rec in all_records if hasattr(rec, 'to_dict')]
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Ottiene le statistiche del parsing.
        
        Returns:
            Statistiche del parsing
        """
        return self.log_processing_service.get_statistics()
    
    def save_drain3_state(self, state_path: str):
        """
        Salva lo stato di Drain3.
        
        Args:
            state_path: Percorso dove salvare lo stato
        """
        self.log_processing_service.save_drain3_state(state_path)
    
    def load_drain3_state(self, state_path: str):
        """
        Carica lo stato di Drain3.
        
        Args:
            state_path: Percorso da cui caricare lo stato
        """
        self.log_processing_service.load_drain3_state(state_path) 