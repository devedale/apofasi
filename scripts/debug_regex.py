#!/usr/bin/env python3
"""
Debug Regex - Test del pattern regex per campi annidati

Questo script testa il pattern regex per capire perché
non cattura tutti i campi come lock e flags.

Author: Edoardo D'Alesio
Version: 1.0.0
"""

import re

def test_regex_pattern():
    """Testa il pattern regex con esempi reali."""
    
    # Pattern attuale
    pattern = r'(\w+)\s*=\s*([^=,]+(?:\s+[^=,]+)*?)(?=\s*,\s*\w+\s*=|$)'
    
    # Esempi di test
    test_cases = [
        "acquire lock=233570404, flags=0x1, tag=\"View Lock\", name=com.android.systemui, ws=null, uid=10037, pid=2227",
        "ready=true,policy=3,wakefulness=1,wksummary=0x23,uasummary=0x1,bootcompleted=true,boostinprogress=false,waitmodeenable=false,mode=false,manual=38,auto=-1,adj=0.0userId=0",
        "allDrawn= false, startingDisplayed =  false, startingMoved =  false, isRelaunching =  false"
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n=== Test Case {i} ===")
        print(f"Text: {text}")
        print(f"Pattern: {pattern}")
        
        matches = re.findall(pattern, text)
        print(f"Matches found: {len(matches)}")
        
        for key, value in matches:
            print(f"  {key} = {value}")
        
        # Test con pattern alternativo
        alt_pattern = r'(\w+)\s*=\s*([^=,]+(?:\s+[^=,]+)*?)(?=\s*\w+\s*=|$)'
        alt_matches = re.findall(alt_pattern, text)
        print(f"Alt pattern matches: {len(alt_matches)}")
        
        for key, value in alt_matches:
            print(f"  {key} = {value}")

if __name__ == "__main__":
    test_regex_pattern() 