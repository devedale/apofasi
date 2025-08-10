"""Parsed record domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path


@dataclass
class ParsedRecord:
    """Domain entity representing a parsed log record."""
    
    # Core data
    original_content: str
    parsed_data: Dict[str, Any]
    parser_name: str
    source_file: Path
    line_number: int
    
    # Metadata
    timestamp: Optional[datetime] = None
    template_id: Optional[int] = None
    confidence_score: Optional[float] = None
    
    # Parsing metadata (separato dai dati parsati)
    detected_headers: Optional[list[str]] = None
    template: Optional[str] = None
    anonymized_template: Optional[str] = None  # Template anonimizzato coerente
    cluster_id: Optional[int] = None
    cluster_size: Optional[int] = None
    detected_patterns: Optional[Dict[str, Any]] = None
    log_timestamp: Optional[Dict[str, Any]] = None  # Timestamp estratto dal log
    
    # Processing info
    is_anonymized: bool = False
    anonymization_method: Optional[str] = None
    processing_errors: list[str] = field(default_factory=list)
    processing_warnings: list[str] = field(default_factory=list)
    
    # Drain3 specific
    drain3_template: Optional[str] = None
    drain3_cluster_id: Optional[int] = None
    
    def __post_init__(self) -> None:
        """Validate the parsed record."""
        if not self.original_content.strip():
            raise ValueError("Original content cannot be empty")
        
        if not self.parser_name:
            raise ValueError("Parser name cannot be empty")
        
        if self.line_number < 1:
            raise ValueError("Line number must be positive")
        
        if self.confidence_score is not None:
            if not 0.0 <= self.confidence_score <= 1.0:
                raise ValueError("Confidence score must be between 0.0 and 1.0")
    
    @property
    def is_valid(self) -> bool:
        """Check if the parsed record is valid."""
        return len(self.processing_errors) == 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if the parsed record has warnings."""
        return len(self.processing_warnings) > 0
    
    def add_error(self, error: str) -> None:
        """Add a processing error."""
        self.processing_errors.append(error)
    
    def add_warning(self, warning: str) -> None:
        """Add a processing warning."""
        self.processing_warnings.append(warning)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parsed record to dictionary."""
        return {
            "success": self.is_valid,
            "original_content": self.original_content,
            "parsed_data": self.parsed_data,
            "parser_name": self.parser_name,
            "source_file": str(self.source_file),
            "line_number": self.line_number,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "template_id": self.template_id,
            "confidence_score": self.confidence_score,
            "is_anonymized": self.is_anonymized,
            "anonymization_method": self.anonymization_method,
            "processing_errors": self.processing_errors,
            "processing_warnings": self.processing_warnings,
            "drain3_template": self.drain3_template,
            "drain3_cluster_id": self.drain3_cluster_id,
            # Parsing metadata
            "detected_headers": self.detected_headers,
            "template": self.template,
            "anonymized_template": self.anonymized_template,
            "cluster_id": self.cluster_id,
            "cluster_size": self.cluster_size,
            "detected_patterns": self.detected_patterns,
            "log_timestamp": self.log_timestamp,
        }
    
    def get_field_value(self, field_name: str) -> Any:
        """Get a specific field value from parsed data."""
        return self.parsed_data.get(field_name)
    
    def set_field_value(self, field_name: str, value: Any) -> None:
        """Set a specific field value in parsed data."""
        self.parsed_data[field_name] = value 