"""Parser configuration domain entity."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ParserConfig:
    """Domain entity for parser configuration."""
    
    # Parser specific configurations
    csv: Dict[str, Any] = None
    json: Dict[str, Any] = None
    syslog: Dict[str, Any] = None
    cef: Dict[str, Any] = None
    fortinet: Dict[str, Any] = None
    apache: Dict[str, Any] = None
    
    # General settings
    enabled_parsers: List[str] = None
    parser_priorities: Dict[str, int] = None
    
    def __post_init__(self) -> None:
        """Initialize default values."""
        if self.csv is None:
            self.csv = {
                "enabled": True,
                "auto_detect_delimiter": True,
                "supported_delimiters": [",", ";", "\t", "|"],
                "encoding_detection": True,
            }
        
        if self.json is None:
            self.json = {
                "enabled": True,
                "support_jsonl": True,
                "max_depth": 10,
            }
        
        if self.syslog is None:
            self.syslog = {
                "enabled": True,
                "formats": ["RFC3164", "RFC5424", "Cisco", "Linux", "FacilitySeverity"],
            }
        
        if self.cef is None:
            self.cef = {
                "enabled": True,
                "parse_extensions": True,
            }
        
        if self.fortinet is None:
            self.fortinet = {
                "enabled": True,
                "key_value_separator": "=",
            }
        
        if self.apache is None:
            self.apache = {
                "enabled": True,
                "formats": ["Common", "Combined", "Custom"],
            }
        
        if self.enabled_parsers is None:
            self.enabled_parsers = ["csv", "json", "syslog", "cef", "fortinet", "apache"]
        
        if self.parser_priorities is None:
            self.parser_priorities = {
                "csv": 1,
                "json": 2,
                "syslog": 3,
                "cef": 4,
                "fortinet": 5,
                "apache": 6,
            }
    
    def is_parser_enabled(self, parser_name: str) -> bool:
        """
        Check if a parser is enabled.
        
        Args:
            parser_name: Name of the parser
            
        Returns:
            True if parser is enabled
        """
        if parser_name not in self.enabled_parsers:
            return False
        
        parser_config = getattr(self, parser_name, None)
        if parser_config is None:
            return False
        
        return parser_config.get("enabled", True)
    
    def get_parser_config(self, parser_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific parser.
        
        Args:
            parser_name: Name of the parser
            
        Returns:
            Parser configuration or None if not found
        """
        return getattr(self, parser_name, None)
    
    def get_parser_priority(self, parser_name: str) -> int:
        """
        Get priority for a specific parser.
        
        Args:
            parser_name: Name of the parser
            
        Returns:
            Parser priority (lower = higher priority)
        """
        return self.parser_priorities.get(parser_name, 999)
    
    def get_enabled_parsers(self) -> List[str]:
        """
        Get list of enabled parsers.
        
        Returns:
            List of enabled parser names
        """
        return [
            parser for parser in self.enabled_parsers 
            if self.is_parser_enabled(parser)
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "csv": self.csv,
            "json": self.json,
            "syslog": self.syslog,
            "cef": self.cef,
            "fortinet": self.fortinet,
            "apache": self.apache,
            "enabled_parsers": self.enabled_parsers,
            "parser_priorities": self.parser_priorities,
        } 