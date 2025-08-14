from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field

class LogEntry(BaseModel):
    """Represents a single log entry to be processed by the parsing chain."""
    line_number: int
    content: str
    source_file: Optional[str] = None

class ParsedRecord(BaseModel):
    """Represents a parsed log record with extracted data and metadata."""
    original_content: str
    line_number: int
    parser_name: str
    parsed_data: Dict[str, Any] = Field(default_factory=dict)
    source_file: Optional[str] = None

    # Fields to be populated by the full pipeline
    presidio_anonymized: Optional[str] = None
    presidio_metadata: List[Dict[str, Any]] = Field(default_factory=list)
    drain3_original: Dict[str, Any] = Field(default_factory=dict)
    drain3_anonymized: Dict[str, Any] = Field(default_factory=dict)
    parsed_data_anonymized: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = 'allow' # Allow extra fields to be added during processing


class AbstractParser(ABC):
    """
    The abstract base class for a handler in the Chain of Responsibility.
    It defines the interface for all concrete parser handlers.
    """
    _next_handler: Optional[AbstractParser] = None

    def set_next(self, handler: AbstractParser) -> AbstractParser:
        """
        Sets the next handler in the chain.
        This allows for building the chain of parsers.
        """
        self._next_handler = handler
        return handler

    @abstractmethod
    def handle(self, log_entry: LogEntry) -> Optional[ParsedRecord]:
        """
        Handles the parsing request.
        If the current handler cannot parse the log, it passes the request
        to the next handler in the chain.
        """
        if self._next_handler:
            return self._next_handler.handle(log_entry)
        return None
