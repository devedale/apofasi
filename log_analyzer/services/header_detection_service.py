import csv
import json
from io import StringIO
from typing import Dict, Any, List, Optional, Tuple
import re

class HeaderDetectionService:
    """
    Centralized service for detecting headers in various file formats.
    Supports CSV, JSON, and other structured formats.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the header detection service.
        
        Args:
            config: Application configuration containing header detection settings
        """
        self.config = config.get('header_detection', {})
        self.csv_config = config.get('csv_recognition', {})
        
    def detect_csv_headers(self, content: str, delimiter: str = ',') -> Optional[List[str]]:
        """
        Detect CSV headers from the first line of content.
        
        Args:
            content: CSV content as string
            delimiter: CSV delimiter character
            
        Returns:
            List of header names if detected, None otherwise
        """
        try:
            lines = content.strip().split('\n')
            if not lines:
                return None
                
            first_line = lines[0].strip()
            if not first_line:
                return None
                
            # Use csv.reader to properly handle quoted fields
            f = StringIO(first_line)
            reader = csv.reader(f, delimiter=delimiter)
            headers = next(reader)
            
            # Validate headers - they should look like column names, not data
            if self._are_valid_headers(headers):
                return [h.strip() for h in headers if h.strip()]
                
        except Exception:
            pass
            
        return None
    
    def _are_valid_headers(self, headers: List[str]) -> bool:
        """
        Validate if a list of strings looks like valid CSV headers.
        
        Args:
            headers: List of potential header strings
            
        Returns:
            True if they look like valid headers
        """
        if not headers or len(headers) < 2:
            return False
            
        # Headers should not be empty and should look like column names
        for header in headers:
            header = header.strip()
            if not header:
                return False
            # Headers should not look like typical data values
            if self._looks_like_data(header):
                return False
                
        return True
    
    def _looks_like_data(self, value: str) -> bool:
        """
        Check if a value looks like data rather than a header.
        
        Args:
            value: String to check
            
        Returns:
            True if it looks like data
        """
        # Check for common data patterns
        if re.match(r'^\d+$', value):  # Pure numbers
            return True
        if re.match(r'^\d{4}-\d{2}-\d{2}', value):  # Date format
            return True
        if re.match(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$', value):  # UUID
            return True
        if re.match(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', value):  # IP address
            return True
        if value.lower() in ['true', 'false', 'null', 'none']:  # Boolean/null values
            return True
            
        return False
    
    def detect_json_headers(self, content: str) -> Optional[List[str]]:
        """
        Detect headers from JSON content by analyzing the structure.
        
        Args:
            content: JSON content as string
            
        Returns:
            List of header names if detected, None otherwise
        """
        try:
            # Try to parse as JSON
            data = json.loads(content)
            
            if isinstance(data, dict):
                # Single JSON object - use keys as headers
                return list(data.keys())
            elif isinstance(data, list) and len(data) > 0:
                # JSON array - use keys from first object
                first_item = data[0]
                if isinstance(first_item, dict):
                    return list(first_item.keys())
                    
        except (json.JSONDecodeError, IndexError):
            pass
            
        return None
    
    def detect_headers_from_file(self, file_path: str, file_type: str = None) -> Optional[List[str]]:
        """
        Detect headers from a file by reading the first few lines.
        
        Args:
            file_path: Path to the file
            file_type: Type of file (csv, json, etc.) or None for auto-detection
            
        Returns:
            List of header names if detected, None otherwise
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_lines = []
                for i, line in enumerate(f):
                    if i >= 5:  # Read max 5 lines
                        break
                    first_lines.append(line.strip())
                    
                if not first_lines:
                    return None
                    
                content = '\n'.join(first_lines)
                
                # Auto-detect file type if not specified
                if not file_type:
                    file_type = self._detect_file_type(content)
                
                # Detect headers based on file type
                if file_type == 'csv':
                    return self.detect_csv_headers(content)
                elif file_type == 'json':
                    return self.detect_json_headers(content)
                    
        except Exception:
            pass
            
        return None
    
    def _detect_file_type(self, content: str) -> str:
        """
        Auto-detect file type from content.
        
        Args:
            content: File content as string
            
        Returns:
            Detected file type ('csv', 'json', or 'unknown')
        """
        lines = content.strip().split('\n')
        if not lines:
            return 'unknown'
            
        first_line = lines[0].strip()
        
        # Check for JSON
        if first_line.startswith('{') or first_line.startswith('['):
            return 'json'
            
        # Check for CSV (has commas and looks structured)
        if ',' in first_line and len(first_line.split(',')) > 2:
            return 'csv'
            
        return 'unknown'
    
    def get_structured_headers(self, content: str, file_type: str = None) -> Dict[str, Any]:
        """
        Get structured header information including field types and patterns.
        
        Args:
            content: File content as string
            file_type: Type of file or None for auto-detection
            
        Returns:
            Dictionary with header information
        """
        headers = None
        
        if file_type == 'csv' or (not file_type and self._detect_file_type(content) == 'csv'):
            headers = self.detect_csv_headers(content)
        elif file_type == 'json' or (not file_type and self._detect_file_type(content) == 'json'):
            headers = self.detect_json_headers(content)
            
        if not headers:
            return {}
            
        # Analyze header patterns
        header_info = {
            'headers': headers,
            'field_count': len(headers),
            'field_patterns': self._analyze_field_patterns(headers),
            'detected_format': file_type or self._detect_file_type(content)
        }
        
        return header_info
    
    def _analyze_field_patterns(self, headers: List[str]) -> Dict[str, Any]:
        """
        Analyze patterns in header names to infer field types.
        
        Args:
            headers: List of header names
            
        Returns:
            Dictionary with field type analysis
        """
        patterns = {
            'timestamp_fields': [],
            'id_fields': [],
            'ip_fields': [],
            'numeric_fields': [],
            'text_fields': []
        }
        
        for header in headers:
            header_lower = header.lower()
            
            # Timestamp fields
            if any(keyword in header_lower for keyword in ['time', 'date', 'timestamp', 'when']):
                patterns['timestamp_fields'].append(header)
            # ID fields
            elif any(keyword in header_lower for keyword in ['id', 'uuid', 'hash', 'key']):
                patterns['id_fields'].append(header)
            # IP fields
            elif any(keyword in header_lower for keyword in ['ip', 'address', 'src', 'dst', 'source', 'dest']):
                patterns['ip_fields'].append(header)
            # Numeric fields
            elif any(keyword in header_lower for keyword in ['count', 'number', 'size', 'amount', 'score', 'rate']):
                patterns['numeric_fields'].append(header)
            # Text fields
            else:
                patterns['text_fields'].append(header)
                
        return patterns
