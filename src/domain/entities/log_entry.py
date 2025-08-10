"""Log entry domain entity."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path


@dataclass(frozen=True)
class LogEntry:
    """Domain entity representing a log entry."""
    
    content: str
    source_file: Path
    line_number: int
    timestamp: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self) -> None:
        """Validate the log entry."""
        if not self.content.strip():
            raise ValueError("Log entry content cannot be empty")
        
        if self.line_number < 1:
            raise ValueError("Line number must be positive")
    
    @property
    def is_empty(self) -> bool:
        """Check if the log entry is empty."""
        return not self.content.strip()
    
    @property
    def length(self) -> int:
        """Get the length of the log entry content."""
        return len(self.content)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary."""
        return {
            "content": self.content,
            "source_file": str(self.source_file),
            "line_number": self.line_number,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "raw_data": self.raw_data,
        } 