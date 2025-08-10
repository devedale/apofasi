"""Log processing service domain service."""

from typing import Dict, Iterator, List, Optional, Any
from pathlib import Path

from ..entities.log_entry import LogEntry
from ..entities.parsed_record import ParsedRecord
from ..interfaces.drain3_service import Drain3Service
from ..interfaces.anonymizer import Anonymizer
from ..interfaces.log_reader import LogReader
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
        """
        self._parser_orchestrator = parser_orchestrator
        self._drain3_service = drain3_service
        self._anonymizer = anonymizer
        self._timestamp_normalizer = timestamp_normalizer or TimestampNormalizationService()
        self.config = config or {}
        # Optional DI for LogReader; defaults provided lazily in _create_log_reader
        self._log_reader: Optional[LogReader] = log_reader
        
        # Servizio per la gestione dei formati di file supportati
        self._file_format_service = FileFormatService(config) if config else None
        
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
        
        for log_entry in reader.read_file(file_path):
            yield from self.process_log_entry(log_entry)
    
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
        non su singoli record uno per uno.
        
        Args:
            records: Lista di tutti i record parsati e anonimizzati
            
        Returns:
            Lista di record con risultati Drain3 associati
        """
        if not records:
            return records
        
        print(f"🔍 Processing {len(records)} records with Drain3 for dual mining...")
        
        # 1. Raccogli tutti i messaggi originali e anonimizzati
        original_messages = []
        anonymized_messages = []
        
        for record in records:
            if hasattr(record, 'original_content') and record.original_content:
                original_messages.append((record, record.original_content))
            
            if hasattr(record, 'anonymized_message') and record.anonymized_message:
                anonymized_messages.append((record, record.anonymized_message))
            elif hasattr(record, 'anonymized_template') and record.anonymized_template:
                # Fallback: usa il template anonimizzato se disponibile
                anonymized_messages.append((record, record.anonymized_template))
        
        print(f"📊 Original messages: {len(original_messages)}, Anonymized messages: {len(anonymized_messages)}")
        
        # 2. Processa tutti i messaggi originali con Drain3
        if original_messages:
            print("🔄 Processing original messages with Drain3...")
            for record, message in original_messages:
                cluster_id = self._drain3_service.add_log_message(message, "original")
                template = self._drain3_service.get_template(cluster_id, "original")
                cluster_info = self._drain3_service.get_cluster_info(cluster_id, "original")
                
                # Associa i risultati al record
                if "drain3_original" not in record.parsed_data:
                    record.parsed_data["drain3_original"] = {}
                
                record.parsed_data["drain3_original"].update({
                    "cluster_id": cluster_id,
                    "template": template,
                    "cluster_size": cluster_info["size"] if cluster_info else 0
                })
        
        # 3. Processa tutti i messaggi anonimizzati con Drain3
        if anonymized_messages:
            print("🔄 Processing anonymized messages with Drain3...")
            for record, message in anonymized_messages:
                cluster_id = self._drain3_service.add_log_message(message, "anonymized")
                template = self._drain3_service.get_template(cluster_id, "anonymized")
                cluster_info = self._drain3_service.get_cluster_info(cluster_id, "anonymized")
                
                # Associa i risultati al record
                if "drain3_anonymized" not in record.parsed_data:
                    record.parsed_data["drain3_anonymized"] = {}
                
                record.parsed_data["drain3_anonymized"].update({
                    "cluster_id": cluster_id,
                    "template": template,
                    "cluster_size": cluster_info["size"] if cluster_info else 0
                })
        
        # 4. Mantieni compatibilità con i campi legacy
        for record in records:
            if "drain3_original" in record.parsed_data:
                # Usa i risultati originali come fallback legacy
                record.parsed_data["drain3"] = record.parsed_data["drain3_original"].copy()
                record.drain3_cluster_id = record.parsed_data["drain3_original"]["cluster_id"]
                record.drain3_template = record.parsed_data["drain3_original"]["template"]
        
        print(f"✅ Drain3 processing completed for {len(records)} records")
        return records
    
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