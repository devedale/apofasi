#!/usr/bin/env python3
"""
Esempio pratico di utilizzo del dual mining Drain3.
Mostra come calcolare cluster sia sui messaggi originali che su quelli anonimizzati.
"""

import sys
from pathlib import Path

# Aggiungi src al path
sys.path.append('src')

from infrastructure.drain3_service import Drain3ServiceImpl
from domain.entities.parsed_record import ParsedRecord


def main():
    """Esempio principale del dual mining Drain3."""
    
    print("🚀 Esempio Dual Mining Drain3")
    print("=" * 50)
    
    # Configurazione con parametri separati per i due miner
    config = {
        "drain3": {
            # Parametri per messaggi originali
            "original": {
                "depth": 4,
                "max_children": 100,
                "max_clusters": 1000,
                "similarity_threshold": 0.4
            },
            # Parametri per messaggi anonimizzati
            "anonymized": {
                "depth": 3,  # Profondità minore per pattern più semplici
                "max_children": 50,
                "max_clusters": 500,
                "similarity_threshold": 0.6  # Soglia più alta per anonimizzati
            }
        }
    }
    
    # Crea il servizio Drain3
    drain3_service = Drain3ServiceImpl(config)
    
    # Messaggi di log di esempio (Fortinet)
    log_messages = [
        # Gruppo 1: Log di traffico normale
        "logver=1.0 idseq=123 itime=2024-01-01 10:00:00 devid=\"FGT123\" devname=\"Firewall1\" vd=\"root\" date=2024-01-01 time=10:00:00 eventtime=1234567890 tz=+0100 logid=\"0000000013\" type=\"traffic\" subtype=\"forward\" level=\"notice\" srcip=192.168.1.100 srcport=12345 srcintf=\"lan1\" srcintfrole=\"lan\" dstip=10.0.0.50 dstport=80 dstintf=\"wan1\" dstintfrole=\"wan\" srccountry=\"Italy\" dstcountry=\"United States\" sessionid=12345 proto=6 action=\"accept\" policyid=1 policytype=\"policy\" service=\"HTTP\" trandisp=\"noop\" app=\"HTTP\" duration=30 sentbyte=1024 rcvdbyte=2048 sentpkt=10 rcvdpkt=20 appcat=\"Web\" crscore=5 craction=0 crlevel=\"low\"",
        
        "logver=1.0 idseq=124 itime=2024-01-01 10:01:00 devid=\"FGT123\" devname=\"Firewall1\" vd=\"root\" date=2024-01-01 time=10:01:00 eventtime=1234567950 tz=+0100 logid=\"0000000013\" type=\"traffic\" subtype=\"forward\" level=\"notice\" srcip=192.168.1.101 srcport=12346 srcintf=\"lan1\" srcintfrole=\"lan\" dstip=10.0.0.51 dstport=443 dstintf=\"wan1\" dstintfrole=\"wan\" srccountry=\"Italy\" dstcountry=\"Germany\" sessionid=12346 proto=6 action=\"accept\" policyid=1 policytype=\"policy\" service=\"HTTPS\" trandisp=\"noop\" app=\"HTTPS\" duration=45 sentbyte=2048 rcvdbyte=4096 sentpkt=15 rcvdpkt=25 appcat=\"Web\" crscore=5 craction=0 crlevel=\"low\"",
        
        "logver=1.0 idseq=125 itime=2024-01-01 10:02:00 devid=\"FGT123\" devname=\"Firewall1\" vd=\"root\" date=2024-01-01 time=10:02:00 eventtime=1234568010 tz=+0100 logid=\"0000000013\" type=\"traffic\" subtype=\"forward\" level=\"notice\" srcip=192.168.1.102 srcport=12347 srcintf=\"lan1\" srcintfrole=\"lan\" dstip=10.0.0.52 dstport=22 dstintf=\"wan1\" dstintfrole=\"wan\" srccountry=\"Italy\" dstcountry=\"Netherlands\" sessionid=12347 proto=6 action=\"accept\" policyid=2 policytype=\"policy\" service=\"SSH\" trandisp=\"noop\" app=\"SSH\" duration=300 sentbyte=512 rcvdbyte=1024 sentpkt=5 rcvdpkt=10 appcat=\"Remote Access\" crscore=5 craction=0 crlevel=\"low\"",
        
        # Gruppo 2: Log di traffico negato
        "logver=1.0 idseq=126 itime=2024-01-01 10:03:00 devid=\"FGT123\" devname=\"Firewall1\" vd=\"root\" date=2024-01-01 time=10:03:00 eventtime=1234568070 tz=+0100 logid=\"0000000013\" type=\"traffic\" subtype=\"forward\" level=\"notice\" srcip=192.168.1.103 srcport=12348 srcintf=\"lan1\" srcintfrole=\"lan\" dstip=10.0.0.53 dstport=23 dstintf=\"wan1\" dstintfrole=\"wan\" srccountry=\"Italy\" dstcountry=\"France\" sessionid=12348 proto=6 action=\"deny\" policyid=0 policytype=\"local-in-policy\" service=\"TELNET\" trandisp=\"noop\" app=\"TELNET\" duration=0 sentbyte=0 rcvdbyte=0 sentpkt=0 rcvdpkt=0 appcat=\"Remote Access\" crscore=5 craction=0 crlevel=\"low\"",
        
        "logver=1.0 idseq=127 itime=2024-01-01 10:04:00 devid=\"FGT123\" devname=\"Firewall1\" vd=\"root\" date=2024-01-01 time=10:04:00 eventtime=1234568130 tz=+0100 logid=\"0000000013\" type=\"traffic\" subtype=\"forward\" level=\"notice\" srcip=192.168.1.104 srcport=12349 srcintf=\"lan1\" srcintfrole=\"lan\" dstip=10.0.0.54 dstport=21 dstintf=\"wan1\" dstintfrole=\"wan\" srccountry=\"Italy\" dstcountry=\"Spain\" sessionid=12349 proto=6 action=\"deny\" policyid=0 policytype=\"local-in-policy\" service=\"FTP\" trandisp=\"noop\" app=\"FTP\" duration=0 sentbyte=0 rcvdbyte=0 sentpkt=0 rcvdpkt=0 appcat=\"File Transfer\" crscore=5 craction=0 crlevel=\"low\"",
        
        # Gruppo 3: Log di sistema
        "logver=1.0 idseq=128 itime=2024-01-01 10:05:00 devid=\"FGT123\" devname=\"Firewall1\" vd=\"root\" date=2024-01-01 time=10:05:00 eventtime=1234568190 tz=+0100 logid=\"0000000001\" type=\"system\" subtype=\"system\" level=\"information\" msg=\"System is starting up\"",
        
        "logver=1.0 idseq=129 itime=2024-01-01 10:06:00 devid=\"FGT123\" devname=\"Firewall1\" vd=\"root\" date=2024-01-01 time=10:06:00 eventtime=1234568250 tz=+0100 logid=\"0000000002\" type=\"system\" subtype=\"system\" level=\"information\" msg=\"System startup completed\"",
        
        # Gruppo 4: Log di admin
        "logver=1.0 idseq=130 itime=2024-01-01 10:07:00 devid=\"FGT123\" devname=\"Firewall1\" vd=\"root\" date=2024-01-01 time=10:07:00 eventtime=1234568310 tz=+0100 logid=\"0000000003\" type=\"admin\" subtype=\"admin\" level=\"notice\" user=\"admin\" msg=\"User admin logged in from 192.168.1.50\"",
        
        "logver=1.0 idseq=131 itime=2024-01-01 10:08:00 devid=\"FGT123\" devname=\"Firewall1\" vd=\"root\" date=2024-01-01 time=10:08:00 eventtime=1234568370 tz=+0100 logid=\"0000000004\" type=\"admin\" subtype=\"admin\" level=\"notice\" user=\"admin\" msg=\"User admin logged out from 192.168.1.50\""
    ]
    
    print(f"📝 Processando {len(log_messages)} messaggi di log...")
    print()
    
    # Processa ogni messaggio con entrambi i miner
    results = []
    
    for i, message in enumerate(log_messages):
        print(f"🔍 Processando messaggio {i+1}/{len(log_messages)}...")
        
        # Crea un record parsato
        record = ParsedRecord(
            original_content=message,
            parsed_data={"line_number": i + 1},
            parser_name="fortinet_parser",
            source_file="example.log",
            line_number=i + 1
        )
        
        # Processa con Drain3 (dual mining)
        processed_record = drain3_service.process_record(record)
        
        # Estrai informazioni sui cluster
        original_info = processed_record.parsed_data.get("drain3_original", {})
        anonymized_info = processed_record.parsed_data.get("drain3_anonymized", {})
        
        results.append({
            "line": i + 1,
            "original_cluster": original_info.get("cluster_id"),
            "original_template": original_info.get("template", "")[:100] + "..." if original_info.get("template") else None,
            "anonymized_cluster": anonymized_info.get("cluster_id"),
            "anonymized_template": anonymized_info.get("template", "")[:100] + "..." if anonymized_info.get("template") else None,
            "message_preview": message[:80] + "..."
        })
        
        print(f"   ✅ Cluster originale: {original_info.get('cluster_id')}")
        print(f"   ✅ Cluster anonimizzato: {anonymized_info.get('cluster_id')}")
    
    print("\n" + "=" * 50)
    print("📊 RISULTATI DEL DUAL MINING")
    print("=" * 50)
    
    # Mostra statistiche
    stats = drain3_service.get_statistics()
    print(f"🔍 Cluster originali: {stats['original']['total_clusters']}")
    print(f"🔒 Cluster anonimizzati: {stats['anonymized']['total_clusters']}")
    print(f"📈 Totale combinato: {stats['combined']['total_clusters']}")
    
    print("\n📋 Dettaglio per messaggio:")
    print("-" * 80)
    print(f"{'Linea':<6} {'Cluster Orig':<12} {'Cluster Anon':<12} {'Messaggio'}")
    print("-" * 80)
    
    for result in results:
        print(f"{result['line']:<6} {result['original_cluster']:<12} {result['anonymized_cluster']:<12} {result['message_preview']}")
    
    print("\n🔍 Template originali:")
    original_templates = drain3_service.get_all_templates("original")
    for cluster_id, template in original_templates.items():
        print(f"   Cluster {cluster_id}: {template[:80]}...")
    
    print("\n🔒 Template anonimizzati:")
    anonymized_templates = drain3_service.get_all_templates("anonymized")
    for cluster_id, template in anonymized_templates.items():
        print(f"   Cluster {cluster_id}: {template[:80]}...")
    
    print("\n💡 ANALISI DEI RISULTATI:")
    print("   • I messaggi originali mostrano pattern dettagliati con IP, timestamp, ecc.")
    print("   • I messaggi anonimizzati mostrano pattern strutturali senza dati sensibili")
    print("   • Il dual mining permette di analizzare sia la struttura che i valori specifici")
    print("   • Utile per: analisi di sicurezza, pattern recognition, compliance")
    
    return results


if __name__ == "__main__":
    try:
        results = main()
        print(f"\n🎉 Esempio completato con successo! Processati {len(results)} messaggi.")
    except Exception as e:
        print(f"\n❌ Errore durante l'esecuzione: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
