#!/usr/bin/env python3
"""Debug script for testing gzip file reading"""

import sys
from pathlib import Path

# Add project path
sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.log_reader import SimpleLogReader

def test_gzip_reading():
    """Test gzip file reading with our SimpleLogReader"""
    
    reader = SimpleLogReader()
    file_path = Path('test_compressed.log.gz')
    
    print(f"Testing file: {file_path}")
    print(f"File exists: {file_path.exists()}")
    print(f"Can read file: {reader.can_read_file(file_path)}")
    print()
    
    try:
        entries = list(reader.read_file(file_path))
        print(f"Successfully read {len(entries)} entries:")
        for i, entry in enumerate(entries, 1):
            print(f"  Entry {i}: {repr(entry.content)}")
    except Exception as e:
        print(f"Error reading file: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gzip_reading()
