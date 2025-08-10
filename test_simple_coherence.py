#!/usr/bin/env python3
"""
Test semplice per verificare la coerenza tra template anonimizzati e messaggi anonimizzati.
"""

import re
import yaml
from pathlib import Path


class SimpleRegexService:
    """Servizio regex semplificato per test."""
    
    def __init__(self):
        self.anonymization_patterns = {
            "ip_address": {
                "regex": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
                "replacement": "<IP>",
                "description": "Indirizzi IPv4"
            },
            "mac_address": {
                "regex": r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})",
                "replacement": "<MAC>",
                "description": "Indirizzi MAC"
            },
            "fortinet_device_id": {
                "regex": r"FGT[0-9A-Z]{8,}",
                "replacement": "<FORTINET_DEVICE>",
                "description": "ID dispositivi Fortinet"
            },
            "device_name": {
                "regex": r'devname="([^"]+)"',
                "replacement": 'devname="<DEVICE_NAME>"',
                "description": "Nomi dispositivi"
            },
            "hostname": {
                "regex": r'hostname="([^"]+)"',
                "replacement": 'hostname="<HOSTNAME>"',
                "description": "Hostname"
            }
        }
        
        # Compila i pattern
        self.compiled_patterns = {}
        for name, pattern_info in self.anonymization_patterns.items():
            try:
                self.compiled_patterns[name] = re.compile(pattern_info["regex"])
            except re.error as e:
                print(f"Warning: Invalid regex for {name}: {e}")
    
    def anonymize_content(self, content: str) -> str:
        """Anonimizza il contenuto usando i pattern."""
        anonymized_content = content
        
        for name, pattern in self.compiled_patterns.items():
            pattern_info = self.anonymization_patterns[name]
            replacement = pattern_info["replacement"]
            
            if name in ["device_name", "hostname"]:
                # Pattern con gruppi di cattura
                anonymized_content = pattern.sub(replacement, anonymized_content)
            else:
                # Pattern semplici
                anonymized_content = pattern.sub(replacement, anonymized_content)
        
        return anonymized_content
    
    def get_template_from_content(self, content: str, anonymized: bool = False) -> str:
        """Genera un template dal contenuto, opzionalmente anonimizzato."""
        if anonymized:
            # Usa il contenuto anonimizzato per il template
            template_content = self.anonymize_content(content)
        else:
            # Usa il contenuto originale
            template_content = content
        
        # Sostituisci valori specifici con placeholder generici
        template = template_content
        
        # Sostituisci numeri con <NUM>
        template = re.sub(r'\b\d+\b', '<NUM>', template)
        
        # Sostituisci stringhe tra virgolette con <STR>
        template = re.sub(r'"([^"]*)"', '"<STR>"', template)
        
        # Sostituisci timestamp con <TIMESTAMP>
        template = re.sub(r'\d{4}-\d{2}-\d{2}', '<DATE>', template)
        template = re.sub(r'\d{2}:\d{2}:\d{2}', '<TIME>', template)
        
        return template


def test_template_coherence():
    """Testa la coerenza tra template anonimizzati e messaggi anonimizzati."""
    print("🧪 Test Coerenza Template Anonimizzati (Semplificato)")
    print("=" * 60)
    
    # Inizializza servizio
    regex_service = SimpleRegexService()
    
    # Messaggio di test Fortinet
    test_message = 'logver=0702111740 idseq=19900372806008868 itime=1751754739 devid="FGT80FTK22013405" devname="mg-project-bari" vd="root" date=2025-07-06 time=00:32:15 eventtime=1751754735214176279 tz="+0200" logid="0100026001" type="event" subtype="system" level="information" logdesc="DHCP Ack log" interface="internal1" dhcp_msg="Ack" mac="9C:53:22:49:C7:8C" ip=10.63.44.101 lease=86400 hostname="ArcherAX55" msg="DHCP server sends a DHCPACK"'
    
    print(f"📝 Messaggio Originale:")
    print(f"   {test_message}")
    print()
    
    # Test 1: Anonimizzazione diretta
    print("🔒 Test 1: Anonimizzazione Diretta")
    anonymized_message = regex_service.anonymize_content(test_message)
    print(f"   Messaggio Anonimizzato:")
    print(f"   {anonymized_message}")
    print()
    
    # Test 2: Template generato dal contenuto originale
    print("📋 Test 2: Template dal Contenuto Originale")
    original_template = regex_service.get_template_from_content(test_message, anonymized=False)
    print(f"   Template Originale:")
    print(f"   {original_template}")
    print()
    
    # Test 3: Template generato dal contenuto anonimizzato
    print("🔒📋 Test 3: Template dal Contenuto Anonimizzato")
    anonymized_template = regex_service.get_template_from_content(test_message, anonymized=True)
    print(f"   Template Anonimizzato:")
    print(f"   {anonymized_template}")
    print()
    
    # Test 4: Verifica Coerenza
    print("✅ Test 4: Verifica Coerenza")
    
    # Verifica che il template anonimizzato sia coerente con il messaggio anonimizzato
    template_anonymized = anonymized_template
    message_anonymized = anonymized_message
    
    # Controlla che i pattern anonimizzati siano presenti in entrambi
    coherence_issues = []
    
    # Verifica IP
    if "<IP>" in template_anonymized and "<IP>" in message_anonymized:
        print("   ✅ IP anonimizzato coerente")
    else:
        coherence_issues.append("IP anonimizzazione incoerente")
    
    # Verifica MAC
    if "<MAC>" in template_anonymized and "<MAC>" in message_anonymized:
        print("   ✅ MAC anonimizzato coerente")
    else:
        coherence_issues.append("MAC anonimizzazione incoerente")
    
    # Verifica Device ID
    if "<FORTINET_DEVICE>" in template_anonymized and "<FORTINET_DEVICE>" in message_anonymized:
        print("   ✅ Device ID anonimizzato coerente")
    else:
        coherence_issues.append("Device ID anonimizzazione incoerente")
    
    # Verifica Hostname
    if "<HOSTNAME>" in template_anonymized and "<HOSTNAME>" in message_anonymized:
        print("   ✅ Hostname anonimizzato coerente")
    else:
        coherence_issues.append("Hostname anonimizzazione incoerente")
    
    if coherence_issues:
        print(f"   ❌ Problemi di coerenza rilevati:")
        for issue in coherence_issues:
            print(f"      - {issue}")
    else:
        print("   🎉 Tutti i pattern sono coerenti!")
    
    print()
    
    # Test 5: Confronto Dettagliato
    print("🔍 Test 5: Confronto Dettagliato")
    
    print("   Messaggio Anonimizzato:")
    print(f"   {message_anonymized}")
    print()
    print("   Template Anonimizzato:")
    print(f"   {template_anonymized}")
    print()
    
    # Verifica che tutti i valori sensibili siano stati anonimizzati in entrambi
    sensitive_values = [
        ("10.63.44.101", "<IP>"),
        ("9C:53:22:49:C7:8C", "<MAC>"),
        ("FGT80FTK22013405", "<FORTINET_DEVICE>"),
        ("mg-project-bari", "<DEVICE_NAME>"),
        ("ArcherAX55", "<HOSTNAME>")
    ]
    
    print("   Verifica Anonimizzazione:")
    for original, placeholder in sensitive_values:
        in_message = original in message_anonymized
        in_template = original in template_anonymized
        placeholder_in_message = placeholder in message_anonymized
        placeholder_in_template = placeholder in template_anonymized
        
        if not in_message and not in_template and placeholder_in_message and placeholder_in_template:
            print(f"     ✅ {original} → {placeholder} (coerente)")
        else:
            print(f"     ❌ {original} → {placeholder} (incoerente)")
            if in_message:
                print(f"        - Originale ancora presente nel messaggio")
            if in_template:
                print(f"        - Originale ancora presente nel template")
            if not placeholder_in_message:
                print(f"        - Placeholder mancante nel messaggio")
            if not placeholder_in_template:
                print(f"        - Placeholder mancante nel template")
    
    print()
    print("🏁 Test Completato!")


if __name__ == "__main__":
    test_template_coherence()
