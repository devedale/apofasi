#!/usr/bin/env python3
"""
Script semplice per testare i file in examples
senza bisogno di installazione complessa.
"""

import os
import sys
import json
from pathlib import Path

# Aggiungi src al path per importare i moduli
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_examples():
    """Testa i file nella directory examples."""
    
    examples_dir = Path("examples")
    if not examples_dir.exists():
        print("❌ Directory 'examples' non trovata!")
        return
    
    print("🧹 Test Clean Log Parser")
    print("=" * 50)
    
    # Lista tutti i file in examples
    files = list(examples_dir.glob("*"))
    
    if not files:
        print("❌ Nessun file trovato in examples/")
        return
    
    print(f"📁 Trovati {len(files)} file in examples/:")
    for file in files:
        print(f"  - {file.name}")
    
    print("\n🚀 Per testare i file, usa uno di questi comandi:")
    print("\n1. Installazione semplice:")
    print("   pip install -e .")
    print("   clean-parser parse examples/")
    
    print("\n2. Test diretto con Python:")
    print("   python -m src.application.main parse examples/")
    
    print("\n3. Usando il Makefile:")
    print("   make run-example")
    
    print("\n4. Test singolo file:")
    print("   clean-parser parse examples/example_json.json")

if __name__ == "__main__":
    test_examples() 