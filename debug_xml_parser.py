#!/usr/bin/env python3
"""Debug script per testare il nuovo XML parser"""

import sys
from pathlib import Path

# Add project path
sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.parsers.xml_log_parser import XMLLogParser
from src.domain.entities.log_entry import LogEntry

def test_xml_parser():
    """Test il nuovo parser XML specializzato"""
    
    parser = XMLLogParser()
    file_path = Path('test_advanced_log.xml')
    
    print(f"Testing XML parser on: {file_path}")
    print(f"File exists: {file_path.exists()}")
    
    # Test can_parse
    with open(file_path, 'r') as f:
        sample_content = f.read(200)
    
    print(f"Can parse: {parser.can_parse(sample_content, file_path)}")
    print()
    
    try:
        # Create LogEntry (dummy, since we read the full file)
        log_entry = LogEntry(content="<xml>dummy</xml>", source_file=file_path, line_number=1)
        
        # Parse and show results
        records = list(parser.parse(log_entry))
        print(f"Successfully parsed {len(records)} XML log records:")
        
        for i, record in enumerate(records[:3], 1):  # Show first 3
            print(f"\n=== Record {i} ===")
            print(f"Parser: {record.parser_name}")
            print(f"Confidence: {record.confidence_score}")
            print(f"Parsed Data Keys: {list(record.parsed_data.keys())}")
            
            # Show some key fields
            for key in ['timestamp', 'level', 'client_ip', 'url', 'email']:
                if key in record.parsed_data:
                    print(f"  {key}: {record.parsed_data[key]}")
            
            # Show detected patterns
            if 'detected_patterns' in record.parsed_data:
                print(f"  Detected Patterns: {record.parsed_data['detected_patterns']}")
        
        if len(records) > 3:
            print(f"\n... and {len(records) - 3} more records")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_xml_parser()
