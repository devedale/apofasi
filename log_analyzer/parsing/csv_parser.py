import csv
from io import StringIO
from typing import Optional, List, Dict, Any

from .interfaces import AbstractParser, LogEntry, ParsedRecord
from ..services.header_detection_service import HeaderDetectionService

class CSVParser(AbstractParser):
    """
    A concrete parser that handles CSV log entries.
    This parser needs to be configured with a delimiter and a header.
    It's less of a general-purpose detector and more of a specific processor.
    """
    def __init__(self, delimiter: str = ',', header: Optional[List[str]] = None, config: Optional[Dict[str, Any]] = None):
        self.delimiter = delimiter
        self.header = header
        self.config = config or {}
        self.header_service = HeaderDetectionService(self.config)

    def handle(self, log_entry: LogEntry) -> Optional[ParsedRecord]:
        """
        Tries to parse the log entry content as a CSV line with automatic header detection.

        Args:
            log_entry: The log entry to parse.

        Returns:
            A ParsedRecord if the content can be parsed as a CSV line with
            the detected headers, otherwise the result from the next handler.
        """
        try:
            # Use StringIO to treat the string line as a file for the csv reader
            f = StringIO(log_entry.content)
            reader = csv.reader(f, delimiter=self.delimiter)

            # Read the single line from the "file"
            fields = next(reader)

            # Determine headers to use
            headers_to_use = self.header
            
            # If no explicit header provided, try to detect from content
            if not headers_to_use:
                # Check if this looks like a header row
                if self._looks_like_header_row(fields):
                    # This is a header row, use the field names as headers
                    headers_to_use = [field.strip() for field in fields if field.strip()]
                else:
                    # This is a data row, try to detect headers from the file
                    headers_to_use = self._detect_headers_from_file(log_entry.source_file)
            
            # If we have valid headers, parse with them
            if headers_to_use and len(fields) == len(headers_to_use):
                parsed_data = dict(zip(headers_to_use, fields))
                return ParsedRecord(
                    original_content=log_entry.content,
                    line_number=log_entry.line_number,
                    source_file=log_entry.source_file,
                    parser_name='CSVParser',
                    parsed_data=parsed_data
                )
            # If no valid headers but multiple fields, use generic names
            elif len(fields) > 1:
                parsed_data = {f"field_{i+1}": field for i, field in enumerate(fields)}
                return ParsedRecord(
                    original_content=log_entry.content,
                    line_number=log_entry.line_number,
                    source_file=log_entry.source_file,
                    parser_name='CSVParser',
                    parsed_data=parsed_data
                )

        except (csv.Error, StopIteration):
            # This indicates it's not a valid CSV line for the given delimiter
            # or it's an empty line. Pass to the next handler.
            return super().handle(log_entry)

        # If parsing was attempted but didn't meet criteria (e.g., field count mismatch),
        # pass to the next handler.
        return super().handle(log_entry)
    
    def _looks_like_header_row(self, fields: List[str]) -> bool:
        """
        Determine if a row looks like a header row rather than data.
        
        Args:
            fields: List of field values
            
        Returns:
            True if this looks like a header row
        """
        if not fields or len(fields) < 2:
            return False
            
        # Use the header detection service to validate
        return self.header_service._are_valid_headers(fields)
    
    def _detect_headers_from_file(self, source_file: Optional[str]) -> Optional[List[str]]:
        """
        Detect headers from the source file.
        
        Args:
            source_file: Path to the source file
            
        Returns:
            List of detected headers or None
        """
        if not source_file:
            return None
            
        try:
            return self.header_service.detect_headers_from_file(source_file, 'csv')
        except Exception:
            return None
