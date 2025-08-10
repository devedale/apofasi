"""Parser orchestrator domain service."""

from typing import Iterator, List, Optional
from pathlib import Path

from ..entities.log_entry import LogEntry
from ..entities.parsed_record import ParsedRecord
from ..interfaces.log_parser import LogParser


class ParserOrchestrator:
    """Domain service for orchestrating multiple parsers."""
    
    def __init__(self, parsers: List[LogParser]) -> None:
        """
        Initialize the parser orchestrator.
        
        Args:
            parsers: List of available parsers
        """
        self._parsers = sorted(parsers, key=lambda p: p.priority)
    
    def find_best_parser(self, log_entry: LogEntry) -> Optional[LogParser]:
        """
        Find the best parser for a log entry.
        
        Args:
            log_entry: The log entry to parse
            
        Returns:
            Best parser or None if no parser can handle it
        """
        for parser in self._parsers:
            if parser.can_parse(log_entry.content, log_entry.source_file):
                return parser
        return None
    
    def parse_with_fallback(self, log_entry: LogEntry) -> Iterator[ParsedRecord]:
        """
        Parse a log entry with fallback to Drain3 if no parser works.
        
        Args:
            log_entry: The log entry to parse
            
        Yields:
            ParsedRecord instances
        """
        # Try specific parsers first
        best_parser = self.find_best_parser(log_entry)
        if best_parser:
            yield from best_parser.parse(log_entry)
        else:
            # Fallback to generic parser (Drain3 will be used)
            yield self._create_fallback_record(log_entry)
    
    def parse_with_all_parsers(self, log_entry: LogEntry) -> Iterator[ParsedRecord]:
        """
        Try parsing with all available parsers.
        
        Args:
            log_entry: The log entry to parse
            
        Yields:
            ParsedRecord instances from all parsers that can handle it
        """
        for parser in self._parsers:
            if parser.can_parse(log_entry.content, log_entry.source_file):
                yield from parser.parse(log_entry)
    
    def get_parser_statistics(self) -> dict[str, int]:
        """
        Get statistics about parser usage.
        
        Returns:
            Dictionary mapping parser names to usage counts
        """
        stats = {}
        for parser in self._parsers:
            stats[parser.name] = 0
        return stats
    
    def get_available_parsers(self) -> List[str]:
        """
        Get list of available parser names.
        
        Returns:
            List of parser names
        """
        return [parser.name for parser in self._parsers]
    
    def get_parser_by_name(self, name: str) -> Optional[LogParser]:
        """
        Get parser by name.
        
        Args:
            name: Parser name
            
        Returns:
            Parser instance or None if not found
        """
        for parser in self._parsers:
            if parser.name == name:
                return parser
        return None
    
    def _create_fallback_record(self, log_entry: LogEntry) -> ParsedRecord:
        """
        Create a fallback record when no parser can handle the entry.
        
        Args:
            log_entry: The log entry
            
        Returns:
            Fallback parsed record
        """
        from ..entities.parsed_record import ParsedRecord
        
        return ParsedRecord(
            original_content=log_entry.content,
            parsed_data={"raw_content": log_entry.content},
            parser_name="fallback",
            source_file=log_entry.source_file,
            line_number=log_entry.line_number,
        ) 