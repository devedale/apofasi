"""Log parser interface."""

from abc import ABC, abstractmethod
from typing import Iterator, Optional
from pathlib import Path

from ..entities.log_entry import LogEntry
from ..entities.parsed_record import ParsedRecord


class LogParser(ABC):
    """Abstract interface for log parsers."""
    
    @abstractmethod
    def can_parse(self, content: str, filename: Optional[Path] = None) -> bool:
        """
        Determine if this parser can handle the given content.
        
        Args:
            content: The content to check
            filename: Optional filename for context
            
        Returns:
            True if this parser can handle the content
        """
        pass
    
    @abstractmethod
    def parse(self, log_entry: LogEntry) -> Iterator[ParsedRecord]:
        """
        Parse a log entry into structured records.
        
        Args:
            log_entry: The log entry to parse
            
        Yields:
            ParsedRecord instances
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of this parser."""
        pass
    
    @property
    @abstractmethod
    def supported_formats(self) -> list[str]:
        """Get list of supported formats."""
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """
        Get parser priority (lower = higher priority).
        
        Used to determine which parser to use when multiple
        parsers can handle the same content.
        """
        pass 