"""
Debug script per CEFParser
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.parsers.cef_parser import CEFParser

# Dati di test CEF
cef_data = """CEF:0|Check Point|VPN-1|4.1|1|VPN-1 Gateway|6|src=192.168.1.1 dst=192.168.1.2
CEF:0|Fortinet|FortiGate|5.0|1|Firewall|5|src=10.0.0.1 dst=10.0.0.2"""

parser = CEFParser()

print("🔍 Debug CEFParser...")
print(f"Can parse: {parser.can_parse(cef_data)}")

results = list(parser.parse(cef_data))
print(f"Numero risultati: {len(results)}")

for i, result in enumerate(results):
    print(f"\nRisultato {i+1}:")
    for key, value in result.items():
        print(f"  {key}: {value}") 