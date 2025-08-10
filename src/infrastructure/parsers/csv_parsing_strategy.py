"""CSV Parsing Strategy Pattern Implementation."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path


class CSVParsingStrategy(ABC):
    """Strategy interface for CSV parsing."""
    
    @abstractmethod
    def can_parse(self, content: str, source_file: Optional[Path] = None) -> bool:
        """Check if this strategy can parse the content."""
        pass
    
    @abstractmethod
    def parse(self, content: str, source_file: Optional[Path] = None) -> Dict[str, Any]:
        """Parse CSV content into structured data."""
        pass
    
    @abstractmethod
    def get_field_names(self, content: str, source_file: Optional[Path] = None) -> List[str]:
        """Get field names for the parsed data."""
        pass


class HeaderBasedCSVParsingStrategy(CSVParsingStrategy):
    """Strategy for parsing CSV with explicit headers."""
    
    def __init__(self):
        self.headers_cache: Dict[str, List[str]] = {}
    
    def can_parse(self, content: str, source_file: Optional[Path] = None) -> bool:
        """Check if we can use header-based parsing."""
        if not source_file or source_file.suffix.lower() != '.csv':
            return False
        
        headers = self._get_headers(source_file)
        return len(headers) > 0
    
    def parse(self, content: str, source_file: Optional[Path] = None) -> Dict[str, Any]:
        """Parse CSV content using headers."""
        # Check if content contains headers (LogReader format: "header1,header2\nvalue1,value2")
        if '\n' in content:
            lines = content.strip().split('\n')
            if len(lines) >= 2:
                headers = lines[0].split(',')
                data_line = lines[1]
                parts = data_line.split(',')
                if len(parts) == len(headers):
                    return dict(zip(headers, [v.strip() for v in parts]))
        
        # Fallback: try to get headers from file
        if source_file:
            headers = self._get_headers(source_file)
            if headers:
                parts = content.split(',')
                if len(parts) == len(headers):
                    return dict(zip(headers, [v.strip() for v in parts]))
        
        return {}
    
    def get_field_names(self, content: str, source_file: Optional[Path] = None) -> List[str]:
        """Get field names from headers."""
        if not source_file:
            return []
        
        return self._get_headers(source_file)
    
    def _get_headers(self, file_path: Path) -> List[str]:
        """Get headers from CSV file with caching."""
        file_key = str(file_path)
        
        if file_key in self.headers_cache:
            return self.headers_cache[file_key]
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                first_line = f.readline().strip()
                if first_line:
                    headers = [header.strip() for header in first_line.split(',')]
                    self.headers_cache[file_key] = headers
                    return headers
        except Exception as e:
            print(f"⚠️ Errore lettura header CSV {file_path}: {str(e)}")
        
        return []


class FallbackCSVParsingStrategy(CSVParsingStrategy):
    """Strategy for parsing CSV without headers (fallback)."""
    
    def can_parse(self, content: str, source_file: Optional[Path] = None) -> bool:
        """Always can parse as fallback."""
        return True
    
    def parse(self, content: str, source_file: Optional[Path] = None) -> Dict[str, Any]:
        """Parse CSV content using generic field names."""
        parts = content.split(',')
        return {f'field_{i}': part.strip() for i, part in enumerate(parts)}
    
    def get_field_names(self, content: str, source_file: Optional[Path] = None) -> List[str]:
        """Get generic field names."""
        parts = content.split(',')
        return [f'field_{i}' for i in range(len(parts))]


class CSVStrategyContext:
    """Context for CSV parsing strategies using Strategy Pattern."""
    
    def __init__(self):
        self.strategies: List[CSVParsingStrategy] = [
            HeaderBasedCSVParsingStrategy(),
            FallbackCSVParsingStrategy()
        ]
    
    def parse_csv(self, content: str, source_file: Optional[Path] = None) -> Dict[str, Any]:
        """Parse CSV using the best available strategy."""
        for strategy in self.strategies:
            if strategy.can_parse(content, source_file):
                return strategy.parse(content, source_file)
        
        return {}
    
    def get_field_names(self, content: str, source_file: Optional[Path] = None) -> List[str]:
        """Get field names using the best available strategy."""
        for strategy in self.strategies:
            if strategy.can_parse(content, source_file):
                return strategy.get_field_names(content, source_file)
        
        return [] 