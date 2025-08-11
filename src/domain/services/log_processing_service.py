"""Log processing service domain service."""

from typing import Dict, Iterator, List, Optional, Any, Tuple
from pathlib import Path
import re

from ..entities.log_entry import LogEntry
from ..entities.parsed_record import ParsedRecord
from ..interfaces.drain3_service import Drain3Service
from ..interfaces.anonymizer import Anonymizer
from ..interfaces.log_reader import LogReader
from ..interfaces.centralized_regex_service import CentralizedRegexService
from .parser_orchestrator import ParserOrchestrator
from .timestamp_normalization_service import TimestampNormalizationService
from ...core.services.file_format_service import FileFormatService


class LogProcessingService:
    """
    Domain service for processing logs with parsers and Drain3.

    Function Comments:
    - Scopo: pipeline unica per processare `LogEntry` in `ParsedRecord`, con arricchimento Drain3,
      normalizzazione temporale e anonimizzazione opzionale.
    - Input: orchestratore `LogParser`, `Drain3Service`, `Anonymizer`, opzionale `LogReader` e config.
    - Output: generatori/collezioni di `ParsedRecord` e statistiche.
    - Side effects: lettura da filesystem tramite `LogReader` e logging/barre di avanzamento.
    """
    
    def __init__(
        self,
        parser_orchestrator: ParserOrchestrator,
        drain3_service: Drain3Service,
        anonymizer: Anonymizer,
        timestamp_normalizer: Optional[TimestampNormalizationService] = None,
        config: Dict[str, Any] = None,
        log_reader: Optional[LogReader] = None,
        centralized_regex_service: Optional[CentralizedRegexService] = None,
    ) -> None:
        """
        Initialize the log processing service.

        Args:
            parser_orchestrator: orchestratore dei parser (entrypoint unico)
            drain3_service: servizio Drain3 per template mining/cluster info
            anonymizer: servizio di anonimizzazione
            timestamp_normalizer: normalizzazione timestamp (default interno)
            config: configurazione generale
            log_reader: lettore di log iniettato; se assente, viene creato un default
            centralized_regex_service: servizio regex centralizzato per configurazione
        """
        self._parser_orchestrator = parser_orchestrator
        self._drain3_service = drain3_service
        self._anonymizer = anonymizer
        self.config = config or {}
        self._centralized_regex_service = centralized_regex_service
        self._timestamp_normalizer = timestamp_normalizer or TimestampNormalizationService(config, self._centralized_regex_service)
        # Optional DI for LogReader; defaults provided lazily in _create_log_reader
        self._log_reader: Optional[LogReader] = log_reader
        
        # Servizio per la gestione dei formati di file supportati
        self._file_format_service = FileFormatService(config, self._centralized_regex_service) if config else None
        
        self._statistics = {
            "total_processed": 0,
            "successfully_parsed": 0,
            "fallback_used": 0,
            "anonymized": 0,
            "errors": 0,
            "timestamp_normalized": 0,
        }

    def process_entry(self, log_entry: LogEntry) -> Optional[ParsedRecord]:
        """
        Process a single log entry and return a single result.
        This is a convenience wrapper around process_log_entry.
        """
        try:
            # Get the first result from the generator
            return next(self.process_log_entry(log_entry), None)
        except StopIteration:
            return None
    
    def process_log_entry(self, log_entry: LogEntry) -> Iterator[ParsedRecord]:
        """
        Process a single log entry.
        
        Args:
            log_entry: The log entry to process
            
        Yields:
            ParsedRecord instances
        """
        self._statistics["total_processed"] += 1
        
        try:
            # Try parsing with specific parsers first
            for record in self._parser_orchestrator.parse_with_fallback(log_entry):
                # Convert dict to ParsedRecord if needed
                if isinstance(record, dict):
                    record = self._dict_to_parsed_record(record, log_entry)
                
                # Normalize timestamp
                record = self._timestamp_normalizer.normalize_parsed_record(record)
                self._statistics["timestamp_normalized"] += 1
                
                # Anonymize ALWAYS to create anonymized_message and anonymized_parsed_data
                # This enables dual Drain3 mining on both original and anonymized content
                record = self._anonymizer.anonymize_record(record)
                self._statistics["anonymized"] += 1
                
                # NOTE: Drain3 processing moved to batch processing after all records are parsed
                # This enables proper clustering on the entire dataset
                
                # Update statistics
                if record.parser_name == "fallback":
                    self._statistics["fallback_used"] += 1
                else:
                    self._statistics["successfully_parsed"] += 1
                
                yield record
                
        except Exception as e:
            self._statistics["errors"] += 1
            # Create error record
            error_record = ParsedRecord(
                original_content=log_entry.content,
                parsed_data={"error": str(e)},
                parser_name="error",
                source_file=log_entry.source_file,
                line_number=log_entry.line_number,
            )
            error_record.add_error(str(e))
            yield error_record
    
    def process_file(self, file_path: Path) -> Iterator[ParsedRecord]:
        """
        Process all log entries in a file.
        
        Args:
            file_path: Path to the log file
            
        Yields:
            ParsedRecord instances
        """
        # Log informazioni sul formato del file se disponibile
        if self._file_format_service:
            format_detected = self._file_format_service.get_file_format(file_path)
            parser_used = self._file_format_service.get_parser_for_format(format_detected)
            self._file_format_service.log_file_processing_info(file_path, parser_used, format_detected)
        
        # Use injected reader when available, otherwise create default
        reader = self._create_log_reader()
        
        # WHY: Limitiamo il numero di righe processate per evitare loop infiniti
        max_lines_to_process = 50000  # 50K righe max per file
        line_count = 0
        
        for log_entry in reader.read_file(file_path):
            line_count += 1
            
            # Controlla se abbiamo superato il limite
            if line_count > max_lines_to_process:
                print(f"⚠️ File {file_path.name}: limite di {max_lines_to_process:,} righe raggiunto, processing interrotto")
                break
            
            yield from self.process_log_entry(log_entry)
        
        print(f"✅ File {file_path.name}: processate {line_count:,} righe")
    
    def process_file_sample(self, file_path: Path, max_lines: int) -> Iterator[ParsedRecord]:
        """
        Process only the first N lines from a file.
        
        Args:
            file_path: Path to the log file
            max_lines: Maximum number of lines to process
            
        Yields:
            ParsedRecord instances (limited to max_lines)
        """
        # Use injected reader when available, otherwise create default
        reader = self._create_log_reader()
        
        for log_entry in reader.read_file_sample(file_path, max_lines):
            yield from self.process_log_entry(log_entry)
    
    def process_directory(self, directory_path: Path) -> Iterator[ParsedRecord]:
        """
        Process all files in a directory.
        
        Args:
            directory_path: Path to directory to process
            
        Yields:
            ParsedRecord instances
        """
        from tqdm import tqdm
        
        # Get all files to process
        files_to_process = []
        for file_path in directory_path.rglob('*'):
            if file_path.is_file() and self.can_process_file(file_path):
                files_to_process.append(file_path)
        
        # Process files with progress bar
        with tqdm(total=len(files_to_process), desc="📄 Processing files", unit="file") as pbar:
            for file_path in files_to_process:
                try:
                    # Update progress bar description
                    pbar.set_description(f"📄 Processing: {file_path.name}")
                    
                    # Log informazioni sul formato del file se disponibile
                    if self._file_format_service:
                        format_detected = self._file_format_service.get_file_format(file_path)
                        parser_used = self._file_format_service.get_parser_for_format(format_detected)
                        self._file_format_service.log_file_processing_info(file_path, parser_used, format_detected)
                    
                    # Process file
                    for record in self.process_file(file_path):
                        yield record
                    
                    # Update progress
                    pbar.update(1)
                    
                except Exception as e:
                    print(f"❌ Error processing {file_path}: {e}")
                    pbar.update(1)
                    continue
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Get processing statistics.
        
        Returns:
            Statistics dictionary
        """
        drain3_stats = self._drain3_service.get_statistics()
        
        stats = {
            **self._statistics,
            "drain3": drain3_stats,
            "available_parsers": self._parser_orchestrator.get_available_parsers(),
        }
        
        # Aggiungi statistiche sui formati se disponibile il FileFormatService
        if self._file_format_service:
            stats["file_formats"] = self._file_format_service.get_formats_summary()
        
        return stats
    
    def sort_records_by_timestamp(self, records: List[ParsedRecord]) -> List[ParsedRecord]:
        """
        Sort records by normalized timestamp.
        
        WHY: Provides temporal ordering for chronological analysis.
        
        Args:
            records: List of records to sort
            
        Returns:
            List sorted by timestamp
        """
        return self._timestamp_normalizer.sort_records_by_timestamp(records)
    
    def get_timeline_statistics(self, records: List[ParsedRecord]) -> Dict[str, any]:
        """
        Get timeline statistics for records.
        
        Args:
            records: List of records to analyze
            
        Returns:
            Timeline statistics
        """
        return self._timestamp_normalizer.get_timeline_statistics(records)
    
    def can_process_file(self, file_path: Path) -> bool:
        """
        Check if a file can be processed.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file can be processed
        """
        # Log informazioni sul file se disponibile il FileFormatService
        if self._file_format_service:
            format_detected = self._file_format_service.get_file_format(file_path)
            is_supported = self._file_format_service.is_format_supported(format_detected)
            
            if self._file_format_service._verbose_logging:
                print(f"🔍 File {file_path.name}: formato '{format_detected}' - Supportato: {'✅' if is_supported else '❌'}")
        
        # WHY: Escludiamo file di documentazione che non sono log
        documentation_files = {
            "readme", "readme.md", "readme.txt", "readme.rst",
            "license", "license.txt", "license.md", "license.rst",
            "citation", "citation.txt", "citation.md",
            "changelog", "changelog.txt", "changelog.md",
            "contributing", "contributing.md", "contributing.txt",
            "install", "install.txt", "install.md",
            "faq", "faq.txt", "faq.md",
            "todo", "todo.txt", "todo.md",
            "bugs", "bugs.txt", "bugs.md",
            "authors", "authors.txt", "authors.md",
            "acknowledgments", "acknowledgments.txt", "acknowledgments.md"
        }
        
        # Controlla se il nome del file è nella lista dei file di documentazione
        file_name_lower = file_path.name.lower()
        if file_name_lower in documentation_files:
            print(f"❌ File {file_path.name}: file di documentazione, saltato")
            return False
        
        # Controlla se il nome del file contiene parole chiave di documentazione
        for doc_keyword in ["readme", "license", "citation", "changelog", "contributing", "install", "faq", "todo", "bugs", "authors", "acknowledgments"]:
            if doc_keyword in file_name_lower:
                print(f"❌ File {file_path.name}: contiene keyword di documentazione '{doc_keyword}', saltato")
                return False
        
        # WHY: Standardized extensions covering all common log formats
        supported_extensions = {
            ".txt", ".log", ".csv", ".json", ".syslog", 
            ".gz", ".xml", ".conf", ""  # Empty string for files without extension
        }
        
        # Check if file has supported extension
        if file_path.suffix.lower() not in supported_extensions:
            if self._file_format_service and self._file_format_service._verbose_logging:
                print(f"❌ File {file_path.name}: estensione '{file_path.suffix}' non supportata")
            return False
        
        # Skip files that are too large
        max_file_size = 100 * 1024 * 1024  # 100MB limit
        if file_path.stat().st_size > max_file_size:
            print(f"⚠️ Skipping large file: {file_path} ({file_path.stat().st_size / 1024 / 1024:.1f}MB)")
            return False
        
        # WHY: Limitiamo il numero di righe per evitare loop infiniti
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)
                max_lines = 100000  # 100K righe max per file
                if line_count > max_lines:
                    print(f"⚠️ File {file_path.name}: troppo lungo ({line_count:,} righe), limitato a {max_lines:,}")
                    return False
                print(f"✅ File {file_path.name}: {line_count:,} righe, processabile")
        except Exception as e:
            print(f"⚠️ Errore nel contare le righe di {file_path.name}: {e}")
            # Se non riusciamo a contare le righe, permettiamo il processing ma con attenzione
        
        return True
    
    def save_drain3_state(self, file_path: str) -> None:
        """
        Save Drain3 state.
        
        Args:
            file_path: Path to save state
        """
        self._drain3_service.save_state(file_path)
    
    def load_drain3_state(self, file_path: str) -> None:
        """
        Load Drain3 state.
        
        Args:
            file_path: Path to load state from
        """
        self._drain3_service.load_state(file_path)
    
    def process_dataset_with_drain3(self, records: List[ParsedRecord]) -> List[ParsedRecord]:
        """
        Processa tutto il dataset con Drain3 per clustering su messaggi originali e anonimizzati.
        
        WHY: Drain3 deve essere eseguito su tutto il dataset per clustering significativo,
        non su singoli record uno per uno. Ottimizziamo raggruppando per file con header simili.
        
        DESIGN: Processing batch completo che:
        1. Raggruppa tutto il dataset per tipologie di file
        2. Identifica file con header simili per condividere miner
        3. Processa in batch per massimizzare l'efficienza
        4. Applica clustering globale per risultati significativi
        
        Args:
            records: Lista di tutti i record parsati e anonimizzati
            
        Returns:
            Lista di record con risultati Drain3 associati
        """
        if not records:
            return records
        
        total_records = len(records)
        print(f"🔍 Processing COMPLETO del dataset: {total_records} records con Drain3 dual mining...")
        
        # 1. ANALISI COMPLETA DEL DATASET
        print("📊 Analizzando struttura del dataset...")
        dataset_stats = self._analyze_dataset_structure(records)
        print(f"   📁 File totali: {dataset_stats['total_files']}")
        print(f"   🔗 Gruppi di similarità: {dataset_stats['similarity_groups']}")
        print(f"   📝 Record con contenuto: {dataset_stats['records_with_content']}")
        
        # 2. RAGGRUPPAMENTO INTELLIGENTE PER PROCESSING BATCH
        print("🔗 Raggruppando dataset per processing batch ottimizzato...")
        
        # 2a. Raggruppa per file sorgente
        records_by_file = self._group_records_by_file(records)
        
        # 2b. Identifica file con header simili per condividere miner
        file_groups = self._group_files_by_similarity(records_by_file)
        
        # 2c. Crea gruppi di processing batch per massimizzare efficienza
        processing_batches = self._create_processing_batches(file_groups)
        
        print(f"   🎯 Creati {len(processing_batches)} batch di processing")
        
        # 3. PROCESSING BATCH COMPLETO DEL DATASET
        print("🚀 Avviando processing batch completo del dataset...")
        
        processed_records = 0
        for batch_id, batch in enumerate(processing_batches, 1):
            batch_size = len(batch['records'])
            print(f"🔄 Batch {batch_id}/{len(processing_batches)}: {batch_size} records da {len(batch['files'])} file simili...")
            
            # 3a. Processing batch dei messaggi originali
            if batch['original_messages']:
                print(f"  📝 Processing {len(batch['original_messages'])} messaggi originali in batch...")
                self._process_messages_batch(batch['original_messages'], "original")
            
            # 3b. Processing batch dei messaggi anonimizzati
            if batch['anonymized_messages']:
                print(f"  🔒 Processing {len(batch['anonymized_messages'])} messaggi anonimizzati in batch...")
                self._process_messages_batch(batch['anonymized_messages'], "anonymized")
            
            processed_records += batch_size
            print(f"  ✅ Batch {batch_id} completato: {processed_records}/{total_records} record processati")
        
        # 4. APPLICAZIONE RISULTATI AL DATASET COMPLETO
        print("🔗 Applicando risultati Drain3 a tutto il dataset...")
        self._apply_drain3_results_to_dataset(records)
        
        # 🆕 5. RIGENERAZIONE TEMPLATE ANONIMIZZATI PER CORREGGERE CAMPI IN CHIARO
        print("🔄 Rigenerando template Drain3 anonimizzati per correggere campi tz, vd, etc...")
        records = self.regenerate_anonymized_drain3_templates(records)
        
        print(f"🎉 Processing batch completo terminato: {total_records} record processati")
        return records
    
    def _analyze_dataset_structure(self, records: List[ParsedRecord]) -> Dict[str, Any]:
        """
        Analizza la struttura completa del dataset per ottimizzare il processing.
        
        Returns:
            Statistiche del dataset per ottimizzazione
        """
        total_files = len(set(str(r.source_file) for r in records if r.source_file))
        
        # Conta record con contenuto valido
        records_with_content = sum(1 for r in records if r.original_content and r.original_content.strip())
        
        # Stima gruppi di similarità
        file_extensions = set()
        for record in records:
            if record.source_file:
                file_extensions.add(Path(record.source_file).suffix.lower())
        
        similarity_groups = len(file_extensions) + 1  # +1 per file senza estensione
        
        return {
            'total_files': total_files,
            'similarity_groups': similarity_groups,
            'records_with_content': records_with_content,
            'file_extensions': list(file_extensions)
        }
    
    def _group_records_by_file(self, records: List[ParsedRecord]) -> Dict[str, List[ParsedRecord]]:
        """
        Raggruppa tutti i record per file sorgente.
        
        Returns:
            Dizionario file -> lista record
        """
        records_by_file = {}
        for record in records:
            source_file = str(record.source_file) if record.source_file else 'unknown'
            if source_file not in records_by_file:
                records_by_file[source_file] = []
            records_by_file[source_file].append(record)
        
        return records_by_file
    
    def _create_processing_batches(self, file_groups: Dict[str, Dict[str, List[ParsedRecord]]]) -> List[Dict[str, Any]]:
        """
        Crea batch di processing ottimizzati per il dataset completo.
        
        WHY: Raggruppa file simili per condividere miner Drain3 e massimizzare efficienza.
        Batch size dinamico basato sulla dimensione del dataset.
        
        Returns:
            Lista di batch di processing
        """
        processing_batches = []
        
        # CALCOLO BATCH SIZE DINAMICO E OTTIMIZZATO
        total_records = sum(len(records) for group_files in file_groups.values() 
                          for records in group_files.values())
        
        # WHY: Batch size ottimale basato sulla dimensione del dataset
        if total_records > 100000:  # Dataset molto grande
            optimal_batch_size = 15000  # Batch molto grandi per efficienza Drain3
        elif total_records > 50000:  # Dataset grande
            optimal_batch_size = 12000  # Batch grandi per efficienza
        elif total_records > 20000:  # Dataset medio
            optimal_batch_size = 8000   # Batch medi
        else:  # Dataset piccolo
            optimal_batch_size = 5000   # Batch piccoli per flessibilità
        
        print(f"🎯 Batch size ottimale per Drain3: {optimal_batch_size} record per batch")
        
        for group_id, group_files in file_groups.items():
            # Raccogli tutti i messaggi del gruppo
            original_messages = []
            anonymized_messages = []
            
            for source_file, file_records in group_files.items():
                for record in file_records:
                    # Messaggi originali
                    if record.original_content and record.original_content.strip():
                        original_messages.append((record, record.original_content))
                    
                    # Messaggi anonimizzati
                    if hasattr(record, 'anonymized_message') and record.anonymized_message:
                        anonymized_messages.append((record, record.anonymized_message))
                    elif hasattr(record, 'anonymized_template') and record.anonymized_template:
                        anonymized_messages.append((record, record.anonymized_template))
            
            # Crea batch solo se ci sono messaggi da processare
            if original_messages or anonymized_messages:
                # DIVIDI IN BATCH OTTIMIZZATI
                total_group_records = len([r for records in group_files.values() for r in records])
                total_batches = (total_group_records + optimal_batch_size - 1) // optimal_batch_size
                
                for batch_num in range(total_batches):
                    start_idx = batch_num * optimal_batch_size
                    end_idx = min(start_idx + optimal_batch_size, total_group_records)
                    
                    # Estrai record per questo batch
                    all_group_records = [r for records in group_files.values() for r in records]
                    batch_records = all_group_records[start_idx:end_idx]
                    
                    # Filtra messaggi per questo batch
                    batch_original = [(r, m) for r, m in original_messages if r in batch_records]
                    batch_anonymized = [(r, m) for r, m in anonymized_messages if r in batch_records]
                    
                    batch = {
                        'group_id': group_id,
                        'batch_num': batch_num + 1,
                        'total_batches': total_batches,
                        'files': list(group_files.keys()),
                        'records': batch_records,
                        'original_messages': batch_original,
                        'anonymized_messages': batch_anonymized,
                        'batch_size_used': optimal_batch_size
                    }
                    processing_batches.append(batch)
        
        return processing_batches
    
    def _process_messages_batch(self, messages: List[Tuple[ParsedRecord, str]], message_type: str) -> None:
        """
        Processa un batch di messaggi con Drain3.
        
        DESIGN: Per il miner anonimizzato, applica PRIMA l'anonimizzazione
        always_anonymize per garantire coerenza nei template generati.
        
        Args:
            messages: Lista di (record, message) da processare
            message_type: "original" o "anonymized"
        """
        for record, message in messages:
            try:
                # 🚨 CORREZIONE: Per il miner anonimizzato, applica PRIMA always_anonymize
                if message_type == "anonymized":
                    # Applica anonimizzazione always_anonymize PRIMA di Drain3
                    anonymized_message = self._apply_always_anonymize_to_message(message)
                    message_to_process = anonymized_message
                else:
                    message_to_process = message
                
                result = self._drain3_service.add_log_message(message_to_process, message_type)
                cluster_id = result['cluster_id']
                template = result['template']
                cluster_size = result['cluster_size']
                
                # Associa i risultati al record
                field_name = f"drain3_{message_type}"
                if field_name not in record.parsed_data:
                    record.parsed_data[field_name] = {}
                
                record.parsed_data[field_name].update({
                    "cluster_id": cluster_id,
                    "template": template,
                    "cluster_size": cluster_size
                })
                
                # 🚨 CORREZIONE: Applica always_anonymize ai campi parsati DOPO Drain3
                # WHY: Ora che anonymized_message è stato generato, applica always_anonymize
                # ai campi parsati per garantire coerenza
                if message_type == "anonymized":
                    record = self._apply_always_anonymize_to_record(record)
                
            except Exception as e:
                print(f"⚠️ Errore processing {message_type} message: {e}")
                # Aggiungi errore al record
                if field_name not in record.parsed_data:
                    record.parsed_data[field_name] = {}
                record.parsed_data[field_name]["error"] = str(e)
    
    def _apply_always_anonymize_to_message(self, message: str) -> str:
        """
        Applica anonimizzazione always_anonymize al messaggio PRIMA di Drain3.
        
        WHY: Garantisce che i template Drain3 anonimizzati siano coerenti
        con la configurazione always_anonymize, eliminando campi in chiaro
        come tz e vd.
        
        Args:
            message: Messaggio da anonimizzare
            
        Returns:
            Messaggio con always_anonymize applicato
        """
        try:
            # Usa il servizio regex centralizzato se disponibile
            if self._centralized_regex_service:
                return self._centralized_regex_service.anonymize_content(message)
            else:
                # Fallback: usa l'anonymizer locale
                return self._anonymizer.anonymize_content(message)
                
        except Exception as e:
            print(f"⚠️ Errore nell'applicazione always_anonymize: {e}")
            # Fallback: ritorna il messaggio originale
            return message
    
    def _apply_always_anonymize_to_record(self, record: ParsedRecord) -> ParsedRecord:
        """
        Applica always_anonymize ai campi parsati del record.
        
        WHY: I campi in always_anonymize devono essere anonimizzati SEMPRE,
        anche quando sono già parsati nei parsed_data, per garantire coerenza.
        
        Args:
            record: Record da anonimizzare
            
        Returns:
            Record con campi parsati anonimizzati
        """
        try:
            if not hasattr(record, 'parsed_data') or not record.parsed_data:
                return record
            
            # WHY: Usa la configurazione in cache per ottenere i campi always_anonymize
            if hasattr(self, '_config_cache') and self._config_cache:
                always_fields = self._config_cache.get_always_anonymize_fields()
            else:
                # Fallback: campi hardcoded se config_cache non disponibile
                always_fields = {"tz", "vd", "devid", "devname", "hostname", "ip_address", "mac_address"}
            
            print(f"🔍 DEBUG always_anonymize: campi configurati = {always_fields}")
            
            # Applica always_anonymize ai campi parsati
            for field in always_fields:
                if field in record.parsed_data and isinstance(record.parsed_data[field], str):
                    raw_val = record.parsed_data[field]
                    if raw_val and raw_val.strip():
                        print(f"🔍 DEBUG always_anonymize: campo '{field}' = '{raw_val}'")
                        
                        # Crea il pattern per trovare il campo nel testo anonimizzato
                        field_pattern = rf'{field}\s*=\s*"([^"]*)"'
                        
                        try:
                            # Cerca se il pattern matcha nel testo anonimizzato
                            matches = re.findall(field_pattern, record.anonymized_message, flags=re.IGNORECASE)
                            if matches:
                                print(f"🔍 DEBUG always_anonymize: TROVATO '{field}' nel testo anonimizzato")
                                
                                # Sostituisci con il placeholder appropriato
                                placeholder = f"<{field.upper()}>"
                                replacement = f'{field}="{placeholder}"'
                                
                                # Sostituisci TUTTI i match del campo
                                record.anonymized_message = re.sub(field_pattern, replacement, record.anonymized_message, flags=re.IGNORECASE)
                                print(f"🔍 DEBUG always_anonymize: SOSTITUITO '{field}' con '{replacement}'")
                            else:
                                print(f"🔍 DEBUG always_anonymize: NESSUN MATCH per '{field}' nel testo anonimizzato")
                                
                        except re.error as e:
                            print(f"⚠️ Errore regex always_anonymize per '{field}': {e}")
            
            print(f"🔍 DEBUG always_anonymize: testo finale = {record.anonymized_message[:200]}...")
            return record
            
        except Exception as e:
            print(f"⚠️ Errore nell'applicazione always_anonymize ai campi parsati: {e}")
            return record
    
    def _apply_drain3_results_to_dataset(self, records: List[ParsedRecord]) -> None:
        """
        Applica i risultati Drain3 a tutto il dataset.
        
        WHY: Assicura che tutti i record abbiano i risultati Drain3 associati.
        """
        for record in records:
            # Assicurati che i campi Drain3 esistano
            if "drain3_original" not in record.parsed_data:
                record.parsed_data["drain3_original"] = {"error": "Non processato"}
            
            if "drain3_anonymized" not in record.parsed_data:
                record.parsed_data["drain3_anonymized"] = {"error": "Non processato"}
    
    def _group_files_by_similarity(self, records_by_file: Dict[str, List[ParsedRecord]]) -> Dict[str, Dict[str, List[ParsedRecord]]]:
        """
        Raggruppa file con header simili per ottimizzare il processing Drain3.
        
        WHY: File con header identici possono condividere lo stesso miner,
        riducendo il tempo di processing e migliorando la qualità del clustering.
        
        Args:
            records_by_file: Dizionario file -> record
            
        Returns:
            Dizionario gruppo -> {file -> record}
        """
        file_groups = {}
        group_counter = 0
        
        # Per ora raggruppiamo per estensione e primi caratteri del contenuto
        # In futuro potremmo implementare analisi più sofisticata degli header
        for source_file, file_records in records_by_file.items():
            if not file_records:
                continue
            
            # Estrai caratteristiche del file per il raggruppamento
            file_extension = Path(source_file).suffix.lower()
            first_record = file_records[0]
            
            # Crea una chiave di raggruppamento basata su estensione e primi caratteri
            if hasattr(first_record, 'original_content') and first_record.original_content:
                content_start = first_record.original_content[:50].lower()
                # Normalizza spazi e caratteri speciali
                content_start = re.sub(r'[^\w\s]', ' ', content_start).strip()
                group_key = f"{file_extension}_{content_start[:20]}"
            else:
                group_key = f"{file_extension}_unknown"
            
            # Crea gruppo se non esiste
            if group_key not in file_groups:
                group_counter += 1
                file_groups[f"group_{group_counter}_{group_key}"] = {}
            
            # Aggiungi file al gruppo
            file_groups[f"group_{group_counter}_{group_key}"][source_file] = file_records
        
        return file_groups
    
    def _create_log_reader(self) -> "LogReader":
        """
        Create a log reader instance.
        
        Returns:
            LogReader instance
        """
        # Why: DI-friendly. Usa il reader iniettato se presente, altrimenti crea quello di default.
        if self._log_reader is not None:
            return self._log_reader
        # Fallback default implementation
        from ...infrastructure.log_reader import SimpleLogReader
        return SimpleLogReader(self.config)
    
    def _dict_to_parsed_record(self, record_dict: Dict[str, Any], log_entry: LogEntry) -> ParsedRecord:
        """
        Convert a dictionary record to ParsedRecord.
        
        Args:
            record_dict: Dictionary representation of the record
            log_entry: Original log entry
            
        Returns:
            ParsedRecord instance
        """
        # Extract core fields
        original_content = record_dict.get('original_content', record_dict.get('raw_line', log_entry.content))
        parsed_data = {k: v for k, v in record_dict.items() 
                      if k not in ['original_content', 'raw_line', 'line_number', 'parser_type']}
        parser_name = record_dict.get('parser_type', 'unknown')
        line_number = record_dict.get('line_number', log_entry.line_number)
        
        # Create ParsedRecord
        parsed_record = ParsedRecord(
            original_content=original_content,
            parsed_data=parsed_data,
            parser_name=parser_name,
            source_file=log_entry.source_file,
            line_number=line_number
        )
        
        # Add confidence if available
        if 'structure_confidence' in record_dict:
            parsed_record.confidence_score = record_dict['structure_confidence']
        
        return parsed_record 

    def regenerate_anonymized_drain3_templates(self, records: List[ParsedRecord]) -> List[ParsedRecord]:
        """
        Rigenera completamente i template Drain3 anonimizzati per tutti i record.
        
        WHY: I record esistenti hanno template Drain3 anonimizzati generati
        PRIMA della correzione always_anonymize, causando campi in chiaro
        come tz e vd. Questo metodo li rigenera tutti.
        
        Args:
            records: Lista di record da rigenerare
            
        Returns:
            Lista di record con template Drain3 anonimizzati corretti
        """
        print(f"🔄 Rigenerando template Drain3 anonimizzati per {len(records)} record...")
        
        # Reset dei miner anonimizzati per evitare contaminazione
        self._drain3_service._anonymized_miner = self._drain3_service._create_template_miner("anonymized")
        
        regenerated_count = 0
        for record in records:
            try:
                if hasattr(record, 'anonymized_message') and record.anonymized_message:
                    # ✅ Usa anonymized_message (già corretto) per rigenerare il template
                    anonymized_result = self._drain3_service.add_log_message(
                        record.anonymized_message, "anonymized"
                    )
                    
                    # Aggiorna il template Drain3 anonimizzato
                    if "drain3_anonymized" not in record.parsed_data:
                        record.parsed_data["drain3_anonymized"] = {}
                    
                    record.parsed_data["drain3_anonymized"].update({
                        "cluster_id": anonymized_result['cluster_id'],
                        "template": anonymized_result['template'],
                        "cluster_size": anonymized_result['cluster_size']
                    })
                    
                    # Applica sempre_anonimizzazione ai campi parsati del record
                    record = self._apply_always_anonymize_to_record(record)
                    
                    regenerated_count += 1
                    
                    # Debug: mostra la differenza
                    if regenerated_count <= 3:  # Solo i primi 3 per debug
                        old_template = record.parsed_data.get("drain3_anonymized", {}).get("template", "")
                        print(f"🔄 Record {record.source_file}:{record.line_number}")
                        print(f"   Vecchio: {old_template[:100]}...")
                        print(f"   Nuovo:   {anonymized_result['template'][:100]}...")
                        print(f"   ✅ Template rigenerato!")
                        
            except Exception as e:
                print(f"❌ Errore rigenerazione template per {record.source_file}:{record.line_number}: {e}")
                # Mantieni il template vecchio in caso di errore
                continue
        
        print(f"✅ Rigenerazione completata: {regenerated_count}/{len(records)} template aggiornati")
        return records 