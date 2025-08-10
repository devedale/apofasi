"""Anonymizer interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..entities.parsed_record import ParsedRecord


class Anonymizer(ABC):
    """Abstract interface for data anonymization."""
    
    @abstractmethod
    def anonymize_record(self, record: ParsedRecord) -> ParsedRecord:
        """
        Anonymize a parsed record.
        
        Args:
            record: The record to anonymize
            
        Returns:
            Anonymized record
        """
        pass
    
    @abstractmethod
    def anonymize_field(self, field_name: str, field_value: Any) -> Any:
        """
        Anonymize a specific field value.
        
        Args:
            field_name: Name of the field
            field_value: Value to anonymize
            
        Returns:
            Anonymized value
        """
        pass
    
    @abstractmethod
    def anonymize_text(self, text: str) -> str:
        """
        Anonymize text content using regex patterns.
        
        Args:
            text: Text to anonymize
            
        Returns:
            Anonymized text
        """
        pass
    
    @property
    @abstractmethod
    def anonymization_methods(self) -> Dict[str, str]:
        """Get available anonymization methods."""
        pass
    
    @property
    @abstractmethod
    def always_anonymize_fields(self) -> list[str]:
        """Get fields that should always be anonymized."""
        pass 