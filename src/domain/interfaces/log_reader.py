"""Log reader interface."""

from abc import ABC, abstractmethod
from typing import Iterator
from pathlib import Path

from ..entities.log_entry import LogEntry


class LogReader(ABC):
    """Abstract interface for log readers."""
    
    @abstractmethod
    def read_file(self, file_path: Path) -> Iterator[LogEntry]:
        """
        Read log entries from a file.
        
        Args:
            file_path: Path to the log file
            
        Yields:
            LogEntry instances
        """
        pass
    
    @abstractmethod
    def read_file_sample(self, file_path: Path, max_lines: int) -> Iterator[LogEntry]:
        """
        Read only the first N lines from a file.
        
        Args:
            file_path: Path to the log file
            max_lines: Maximum number of lines to read
            
        Yields:
            LogEntry instances (limited to max_lines)
        """
        pass
    
    @abstractmethod
    def can_read_file(self, file_path: Path) -> bool:
        """
        Check if this reader can handle the given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if this reader can handle the file
        """
        pass
    
    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Get list of supported file extensions."""
        pass 