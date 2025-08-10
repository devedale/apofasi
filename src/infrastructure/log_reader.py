"""Simple log reader implementation."""

import chardet
import gzip
from typing import Iterator, Dict, Any, List
from pathlib import Path

from ..domain.interfaces.log_reader import LogReader
from ..domain.entities.log_entry import LogEntry


class SimpleLogReader(LogReader):
    """Simple implementation of log reader."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inizializza il log reader.
        
        Args:
            config: Configurazione del sistema (opzionale)
        """
        self.config = config or {}
        
        # Carica CSV recognition patterns dalla configurazione
        regex_config = self.config.get('regex', {})
        self.csv_recognition = regex_config.get('csv_recognition', {})
    
    def read_file(self, file_path: Path) -> Iterator[LogEntry]:
        """
        Read log entries from a file.
        
        Args:
            file_path: Path to the log file
            
        Yields:
            LogEntry instances
        """
        if not self.can_read_file(file_path):
            raise ValueError(f"Cannot read file: {file_path}")
        
        # Special handling for CSV files - read entire content
        if file_path.suffix.lower() == '.csv':
            yield from self._read_csv_file(file_path)
        else:
            yield from self._read_line_by_line(file_path)
    
    def _read_csv_file(self, file_path: Path) -> Iterator[LogEntry]:
        """Read CSV file as complete content."""
        # Detect encoding
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            detected = chardet.detect(raw_data)
            encoding = detected['encoding'] or 'utf-8'
        
        # Read entire file content
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            content = f.read()
            
        # Check if this is a structured log CSV (has specific headers or filename pattern)
        is_structured = self._is_structured_log_csv(content) or self._is_structured_log_filename(file_path)
        
        if is_structured:
            # For structured logs, read line by line
            yield from self._read_structured_csv_file(file_path, encoding)
        else:
            # For regular CSV, read as complete content
            yield LogEntry(
                content=content,
                source_file=file_path,
                line_number=1,  # Use line 1 for the entire file
            )
    
    def _is_structured_log_csv(self, content: str) -> bool:
        """Check if CSV contains structured log data."""
        lines = content.strip().split('\n')
        if len(lines) < 2:
            return False
        
        # Check first line for structured log headers
        headers = lines[0].split(',')
        
        # Usa i pattern dalla configurazione unificata
        if not self.csv_recognition:
            # Fallback: usa pattern hardcoded
            return self._check_legacy_structured_indicators(headers)
        
        structured_indicators = self.csv_recognition.get('structured_indicators', {})
        
        # Controlla ogni tipo di indicatori
        for indicator_type, config in structured_indicators.items():
            if indicator_type == 'loghub':
                indicators = config.get('indicators', [])
                min_matches = config.get('min_matches', 3)
                
                matches = sum(1 for header in headers if header.strip() in indicators)
                if matches >= min_matches:
                    return True
                    
            elif indicator_type == 'cybersecurity':
                indicators = config.get('indicators', [])
                min_matches = config.get('min_matches', 5)
                
                matches = sum(1 for header in headers if header.strip() in indicators)
                if matches >= min_matches:
                    return True
                    
            elif indicator_type == 'intrusion_data':
                indicators = config.get('indicators', [])
                min_matches = config.get('min_matches', 5)
                
                matches = sum(1 for header in headers if header.strip() in indicators)
                if matches >= min_matches:
                    return True
        
        return False
    
    def _check_legacy_structured_indicators(self, headers: List[str]) -> bool:
        """Fallback per controllare indicatori legacy."""
        # Specific indicators for loghub structured data
        loghub_indicators = [
            'LineId', 'EventId', 'EventTemplate', 'Content',
            'Component', 'Pid', 'Time', 'Timestamp'
        ]
        
        # Check for loghub structured indicators
        loghub_matches = sum(1 for header in headers if header.strip() in loghub_indicators)
        
        # If has at least 3 loghub indicators, it's structured
        if loghub_matches >= 3:
            return True
        
        # Check for our specific CSV headers (cybersecurity dataset)
        our_indicators = [
            'Event ID', 'Timestamp', 'Source IP', 'Destination IP', 
            'User Agent', 'Attack Type', 'Attack Severity', 
            'Data Exfiltrated', 'Threat Intelligence', 'Response Action'
        ]
        
        # Check for our specific indicators
        our_matches = sum(1 for header in headers if header.strip() in our_indicators)
        
        # If has at least 5 of our indicators, it's structured
        if our_matches >= 5:
            return True
        
        # Check for cybersecurity intrusion data headers
        cybersecurity_indicators = [
            'session_id', 'network_packet_size', 'protocol_type', 'login_attempts',
            'session_duration', 'encryption_used', 'ip_reputation_score', 
            'failed_logins', 'browser_type', 'unusual_time_access', 'attack_detected'
        ]
        
        # Check for cybersecurity intrusion indicators
        cybersecurity_matches = sum(1 for header in headers if header.strip() in cybersecurity_indicators)
        
        # If has at least 5 of cybersecurity indicators, it's structured
        if cybersecurity_matches >= 5:
            return True
        
        # Check if this looks like a regular CSV (has many columns, typical data format)
        # Regular CSVs usually have more than 10 columns and don't have loghub indicators
        if len(headers) > 10 and loghub_matches == 0 and our_matches == 0:
            return False
        
        return False
    
    def _is_structured_log_filename(self, file_path: Path) -> bool:
        """Check if filename indicates structured log data."""
        filename = file_path.name.lower()
        structured_patterns = [
            '_structured.csv',
            '_templates.csv',
            'log_structured.csv',
            'log_templates.csv'
        ]
        return any(pattern in filename for pattern in structured_patterns)
    
    def _read_structured_csv_file(self, file_path: Path, encoding: str) -> Iterator[LogEntry]:
        """Read structured CSV file line by line."""
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            lines = f.readlines()
            
            if len(lines) < 2:
                # File troppo corto, non è un CSV strutturato valido
                return
            
            # La prima riga contiene gli header
            headers = lines[0].strip()
            
            # Prima riga: header
            yield LogEntry(
                content=headers,
                source_file=file_path,
                line_number=1,
            )
            
            # Processa le righe di dati (a partire dalla riga 2)
            for line_number, line in enumerate(lines[1:], 2):
                line = line.strip()
                if line:  # Skip empty lines
                    # Per le righe di dati, passa solo i dati CSV
                    yield LogEntry(
                        content=line,
                        source_file=file_path,
                        line_number=line_number,
                    )
    
    def _read_line_by_line(self, file_path: Path) -> Iterator[LogEntry]:
        """
        Read file line by line, supporting both regular and compressed (.gz) files.
        
        WHY: Many log files are compressed to save space, especially in production
        environments. This allows seamless processing of both formats.
        """
        is_compressed = file_path.suffix.lower() == '.gz'
        
        if is_compressed:
            # Handle compressed files
            # Read a sample for encoding detection
            with gzip.open(file_path, 'rb') as f:
                sample_data = f.read(1024)  # Read first 1KB for encoding detection
                detected = chardet.detect(sample_data)
                encoding = detected['encoding'] or 'utf-8'
                
            # Read the full file with detected encoding
            with gzip.open(file_path, 'rt', encoding=encoding, errors='replace') as f:
                for line_number, line in enumerate(f, 1):
                    line = line.strip()
                    if line:  # Skip empty lines
                        yield LogEntry(
                            content=line,
                            source_file=file_path,
                            line_number=line_number,
                        )
        else:
            # Handle regular files
            # Detect encoding
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                detected = chardet.detect(raw_data)
                encoding = detected['encoding'] or 'utf-8'
            
            # Read file with detected encoding
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                for line_number, line in enumerate(f, 1):
                    line = line.strip()
                    if line:  # Skip empty lines
                        yield LogEntry(
                            content=line,
                            source_file=file_path,
                            line_number=line_number,
                        )
    
    def can_read_file(self, file_path: Path) -> bool:
        """
        Check if this reader can handle the given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if this reader can handle the file
        """
        if not file_path.exists():
            return False
        
        if not file_path.is_file():
            return False
        
        # Check if file extension is supported
        return file_path.suffix.lower() in self.supported_extensions
    
    @property
    def supported_extensions(self) -> list[str]:
        """
        Get list of supported file extensions for log files.
        
        WHY: Standardized list that covers common log formats including
        compressed files, configuration files, and files without extensions.
        """
        return [
            ".txt",     # Generic text files
            ".log",     # Standard log files  
            ".csv",     # Structured CSV data
            ".json",    # JSON/JSONL log files
            ".syslog",  # Syslog specific files
            ".gz",      # Compressed log files
            ".xml",     # XML formatted logs
            ".conf",    # Configuration files (often contain logs)
            ""          # Files without extension (common in Unix)
        ] 

    def read_file_sample(self, file_path: Path, max_lines: int) -> Iterator[LogEntry]:
        """
        Read only the first N lines from a file.
        
        Args:
            file_path: Path to the log file
            max_lines: Maximum number of lines to read
            
        Yields:
            LogEntry instances (limited to max_lines)
        """
        if not self.can_read_file(file_path):
            raise ValueError(f"Cannot read file: {file_path}")
        
        # Special handling for CSV files - read only first N lines
        if file_path.suffix.lower() == '.csv':
            yield from self._read_csv_file_sample(file_path, max_lines)
        else:
            yield from self._read_line_by_line_sample(file_path, max_lines)
    
    def _read_csv_file_sample(self, file_path: Path, max_lines: int) -> Iterator[LogEntry]:
        """Read only the first N lines from CSV file."""
        # Detect encoding
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            detected = chardet.detect(raw_data)
            encoding = detected['encoding'] or 'utf-8'
        
        # Read only first N lines
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                lines.append(line.strip())
        
        content = '\n'.join(lines)
        
        # Check if this is a structured log CSV
        is_structured = self._is_structured_log_csv(content) or self._is_structured_log_filename(file_path)
        
        if is_structured:
            # For structured logs, read line by line (limited)
            yield from self._read_structured_csv_file_sample(file_path, encoding, max_lines)
        else:
            # For regular CSV, read as complete content (limited)
            yield LogEntry(
                content=content,
                source_file=file_path,
                line_number=1,
            )
    
    def _read_structured_csv_file_sample(self, file_path: Path, encoding: str, max_lines: int) -> Iterator[LogEntry]:
        """Read only the first N lines from structured CSV file."""
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            for line_number, line in enumerate(f, 1):
                if line_number > max_lines:
                    break
                    
                line = line.strip()
                if line:  # Skip empty lines
                    yield LogEntry(
                        content=line,
                        source_file=file_path,
                        line_number=line_number,
                    )
    
    def _read_line_by_line_sample(self, file_path: Path, max_lines: int) -> Iterator[LogEntry]:
        """Read only the first N lines from a regular file."""
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for line_number, line in enumerate(f, 1):
                if line_number > max_lines:
                    break
                    
                line = line.rstrip('\n')
                if line:  # Skip empty lines
                    yield LogEntry(
                        content=line,
                        source_file=file_path,
                        line_number=line_number,
                    ) 