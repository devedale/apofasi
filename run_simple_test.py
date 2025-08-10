#!/usr/bin/env python3
"""
Script semplice per testare i file in examples
senza installazione complessa.
"""

import os
import sys
import json
from pathlib import Path

# Aggiungi src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_file_content():
    """Mostra il contenuto dei file di esempio."""
    
    examples_dir = Path("examples")
    if not examples_dir.exists():
        print("❌ Directory 'examples' non trovata!")
        return
    
    print("🧹 Test File in Examples")
    print("=" * 50)
    
    for file_path in examples_dir.glob("*"):
        if file_path.is_file():
            print(f"\n📄 File: {file_path.name}")
            print("-" * 30)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Mostra le prime 5 righe
                    print(f"Prime {min(5, len(lines))} righe:")
                    for i, line in enumerate(lines[:5]):
                        if line.strip():
                            print(f"  {i+1}: {line[:100]}{'...' if len(line) > 100 else ''}")
                    
                    if len(lines) > 5:
                        print(f"  ... e altre {len(lines) - 5} righe")
                        
            except Exception as e:
                print(f"  ❌ Errore nella lettura: {e}")

def run_simple_parser():
    """Esegue un parser semplice sui file."""
    
    print("\n🚀 Per testare i parser, usa questi comandi:")
    print("\n1. Installazione diretta:")
    print("   pip3 install -e .")
    print("   clean-parser parse examples/")
    
    print("\n2. Test con Python diretto:")
    print("   python3 -m src.application.main parse examples/")
    
    print("\n3. Test singolo file:")
    print("   python3 -m src.application.main parse examples/example_json.json")
    
    print("\n4. Con output dettagliato:")
    print("   python3 -m src.application.main parse examples/ --verbose")

if __name__ == "__main__":
    test_file_content()
    run_simple_parser() 