#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.infrastructure.parsers.universal_parser import CSVParser

def test_csv_parser():
    """Test del CSVParser"""
    
    # Crea il parser
    parser = CSVParser()
    
    # Test content
    content = """timestamp,level,service,message,ip,server
2024-01-15T10:30:45.123Z,ERROR,kernel,Out of memory,,server1
2024-01-15T10:30:46.456Z,WARN,sshd,Failed password for user admin,192.168.1.100,server1"""
    
    # Test can_parse
    can_parse = parser.can_parse(content, "test.csv")
    print(f"Can parse: {can_parse}")
    
    # Test parse
    if can_parse:
        results = list(parser.parse(content, "test.csv"))
        print(f"Parsed {len(results)} records")
        for i, record in enumerate(results):
            print(f"Record {i+1}: {record}")
    else:
        print("Parser cannot parse this content")

if __name__ == "__main__":
    test_csv_parser() 