"""Anonymization service domain service."""

from typing import Any, Dict, Iterator
from pathlib import Path

from ..entities.parsed_record import ParsedRecord
from ..interfaces.anonymizer import Anonymizer


class AnonymizationService:
    """Domain service for anonymization operations."""
    
    def __init__(self, anonymizer: Anonymizer) -> None:
        """
        Initialize the anonymization service.
        
        Args:
            anonymizer: Anonymizer implementation
        """
        self._anonymizer = anonymizer
    
    def anonymize_records(self, records: Iterator[ParsedRecord]) -> Iterator[ParsedRecord]:
        """
        Anonymize a stream of parsed records.
        
        Args:
            records: Iterator of parsed records
            
        Yields:
            Anonymized parsed records
        """
        for record in records:
            yield self._anonymizer.anonymize_record(record)
    
    def anonymize_file(self, file_path: Path) -> Iterator[ParsedRecord]:
        """
        Anonymize all records in a file.
        
        Args:
            file_path: Path to the file
            
        Yields:
            Anonymized parsed records
        """
        # This would typically use a reader service
        # For now, we'll assume records are already parsed
        pass
    
    def get_anonymization_statistics(self) -> Dict[str, Any]:
        """
        Get anonymization statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "anonymization_methods": self._anonymizer.anonymization_methods,
            "always_anonymize_fields": self._anonymizer.always_anonymize_fields,
        }
    
    def validate_anonymization_config(self) -> bool:
        """
        Validate anonymization configuration.
        
        Returns:
            True if configuration is valid
        """
        try:
            # Check if anonymization methods are available
            methods = self._anonymizer.anonymization_methods
            if not methods:
                return False
            
            # Check if always anonymize fields are configured
            always_fields = self._anonymizer.always_anonymize_fields
            if not always_fields:
                return False
            
            return True
            
        except Exception:
            return False 