# CLI Parser con Microsoft Presidio - Guida Completa

## 🚀 Panoramica

Il `cli_parser.py` è stato integrato con **Microsoft Presidio** per fornire anonimizzazione avanzata basata su AI/ML oltre al sistema regex esistente.

## 🔐 Modalità di Anonimizzazione

### 1. **CLASSIC** (Regex)
- Usa solo il sistema regex esistente
- Veloce e prevedibile
- Pattern predefiniti per IP, email, ID, ecc.

### 2. **PRESIDIO** (AI/ML)
- Usa solo Microsoft Presidio
- Rilevamento intelligente di entità PII
- Analisi contestuale e ML-based
- Insight datamining avanzati

### 3. **HYBRID** (Entrambi) ⭐ **DEFAULT**
- Processa il messaggio originale **due volte separatamente**
- Fornisce entrambi i risultati per confronto
- **NON sovrappone** le anonimizzazioni
- Copertura completa e analisi complementare

## 📋 Comandi Disponibili

### Parsing Completo con Presidio

```bash
# Modalità ibrida (default) - mostra dettagli Presidio
python3 cli_parser.py parse logs/ output/ --anonymization-mode hybrid --show-presidio-details

# Solo regex classico
python3 cli_parser.py parse logs/ output/ --anonymization-mode classic

# Solo Presidio AI
python3 cli_parser.py parse logs/ output/ --anonymization-mode presidio --show-presidio-details
```

### Campionamento con Presidio

```bash
# Campionamento con modalità ibrida
python3 cli_parser.py sample logs/ sample_report.txt --lines 5 --anonymization-mode hybrid

# Campionamento con solo Presidio
python3 cli_parser.py sample logs/ sample_report.txt --lines 5 --anonymization-mode presidio --show-presidio-details
```

## 🔍 Output e Metadati

### Con `--show-presidio-details`

Il CLI mostra dettagli completi per i primi 5 record:

```
📊 Record 1 - Anonimizzazione HYBRID:
   Originale: User John Doe (ID: 12345) logged in from 192.168.1.100...
   Classic:   User <PERSON> (ID: <NUMERIC_ID>) logged in from <IP_ADDRESS>...
   Presidio:  User <PERSON> (ID: <ID>) logged in from <IP_ADDRESS>...
   Entità Classic: 3
   Entità Presidio: 4
   Totale entità: 7
   Tipi unici: 4
```

### Nel File di Output

Ogni record include sezione Presidio:

```
🔐 Presidio Anonymization (HYBRID):
  Classic: User <PERSON> (ID: <NUMERIC_ID>) logged in from <IP_ADDRESS>...
  Presidio: User <PERSON> (ID: <ID>) logged in from <IP_ADDRESS>...
  Entità Classic: 3
  Entità Presidio: 4
```

## 📊 Struttura Dati Presidio

### Modalità HYBRID
```json
{
  "classic_anonymization": {
    "anonymized_content": "testo anonimizzato da regex",
    "method": "classic_regex",
    "entities_detected": [...],
    "anonymization_metadata": {...}
  },
  "presidio_anonymization": {
    "anonymized_content": "testo anonimizzato da AI",
    "method": "presidio_ai",
    "entities_detected": [...],
    "datamining_insights": {...}
  },
  "hybrid_metadata": {
    "total_entities_classic": 3,
    "total_entities_presidio": 4,
    "processing_method": "separate_processing_original_content"
  }
}
```

### Modalità PRESIDIO
```json
{
  "anonymized_content": "testo anonimizzato",
  "method": "presidio_ai",
  "entities_detected": [
    {
      "entity_type": "PERSON",
      "text": "John Doe",
      "score": 0.95,
      "start": 5,
      "end": 13
    }
  ],
  "datamining_insights": {
    "temporal_patterns": {...},
    "geographic_patterns": {...},
    "security_metrics": {...}
  }
}
```

## ⚙️ Configurazione Presidio

Assicurati che nel `config.yaml` sia presente:

```yaml
presidio:
  enabled: true
  anonymization_mode: "hybrid"  # "classic", "presidio", "hybrid"
  analyzer:
    languages: ["en", "it"]
    entities:
      PERSON: true
      EMAIL_ADDRESS: true
      IP_ADDRESS: true
      # ... altre entità
```

## 🎯 Vantaggi dell'Integrazione

1. **Confronto Diretto**: Vedi come ogni sistema anonimizza lo stesso messaggio
2. **Copertura Completa**: Non perdi informazioni tra i due approcci
3. **Analisi Complementare**: Insight diversi da regex e AI
4. **Debugging Facile**: Analizza separatamente i risultati
5. **Flessibilità**: Scegli la modalità più adatta al tuo caso

## 🚨 Troubleshooting

### Presidio non disponibile
```
⚠️ Presidio non disponibile: [errore]
🔄 Fallback a modalità classic (regex)
```

### Modalità non supportata
```bash
# Fallback automatico se Presidio fallisce
python3 cli_parser.py parse logs/ output/ --anonymization-mode presidio
# Se fallisce → automaticamente usa classic
```

## 📈 Esempi di Output

### Parsing Completo
```bash
python3 cli_parser.py parse logs/ output/ --anonymization-mode hybrid --show-presidio-details
```

Output:
```
🚀 CLI Parser - Sistema di Parsing Unificato
============================================================
🔐 Modalità anonimizzazione: HYBRID
🔍 Mostrando dettagli completi Presidio e metadati

✅ Servizio Presidio inizializzato correttamente
📄 Eseguendo il parsing di: logs/

🔐 Applicando anonimizzazione HYBRID...
📊 Record 1 - Anonimizzazione HYBRID:
   Originale: User admin logged in from 10.0.0.1...
   Classic:   User <USERNAME> logged in from <IP_ADDRESS>...
   Presidio:  User <PERSON> logged in from <IP_ADDRESS>...
   Entità Classic: 2
   Entità Presidio: 2
   Totale entità: 4
   Tipi unici: 2

✅ Anonimizzazione HYBRID completata per 150 record

📊 Generando report completi...
🎉 PARSING COMPLETATO
⏱️  Tempo totale: 45.23s
📈 Record totali: 150
✅ Success rate: 98.7%
📄 Report e dati salvati in: output/
```

### Campionamento
```bash
python3 cli_parser.py sample logs/ sample.txt --lines 3 --anonymization-mode hybrid
```

Output nel file:
```
### File: firewall.log ###

  [L:1] Original: 2025-08-11 18:30:00 admin 10.0.0.1 DENY...
    Parser: firewall
    Template: <TIMESTAMP> <USERNAME> <IP_ADDRESS> <ACTION>...
    Cluster ID: 1
    Cluster Size: 45
    🔐 Presidio Anonymization (HYBRID):
      Classic: <TIMESTAMP> <USERNAME> <IP_ADDRESS> <ACTION>...
      Presidio: <TIMESTAMP> <PERSON> <IP_ADDRESS> <ACTION>...
      Entità Classic: 2
      Entità Presidio: 2
```

## 🎉 Riepilogo

Ora puoi usare `cli_parser.py` con:

- **Modalità CLASSIC**: Solo regex (veloce)
- **Modalità PRESIDIO**: Solo AI (intelligente)  
- **Modalità HYBRID**: Entrambi separatamente (completo)

Ogni modalità fornisce:
- ✅ Messaggi anonimizzati
- ✅ Metadati completi
- ✅ Entità rilevate
- ✅ Insight datamining (Presidio)
- ✅ Confronto diretto (Hybrid)

**La modalità HYBRID è la più potente** perché ti dà entrambi i risultati senza sovrapposizioni! 🚀
