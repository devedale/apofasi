"""Log writer interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator
from pathlib import Path

from ..entities.parsed_record import ParsedRecord


class LogWriter(ABC):
    """Abstract interface for log writers."""
    
    @abstractmethod
    def write_records(self, records: Iterator[ParsedRecord], output_path: Path) -> None:
        """
        Write parsed records to output file.
        
        Args:
            records: Iterator of parsed records
            output_path: Path to output file
        """
        pass
    
    @abstractmethod
    def write_metadata(self, metadata: Dict[str, Any], output_path: Path) -> None:
        """
        Write metadata to output file.
        
        Args:
            metadata: Metadata dictionary
            output_path: Path to output file
        """
        pass
    
    @abstractmethod
    def can_write_format(self, format_name: str) -> bool:
        """
        Check if this writer can handle the given format.
        
        Args:
            format_name: Name of the output format
            
        Returns:
            True if this writer can handle the format
        """
        pass
    
    @property
    @abstractmethod
    def supported_formats(self) -> list[str]:
        """Get list of supported output formats."""
        pass 