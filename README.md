# Clean Parser

Parser di log robusto con clustering Drain3, anonimizzazione e parsing multi-strategy.

## Formati Supportati

### Parser Principale (MultiStrategyParser)
- **CSV**: File CSV con header rilevamento automatico
- **JSON**: Log in formato JSON
- **Syslog**: Log di sistema standard
- **Fortinet**: Log specifici Fortinet
- **Apache**: Log di accesso Apache
- **TXT**: File di testo generici
- **LOG**: File di log standard

### Parsing Strategie
1. **Structured Parsing**: Tentativo di parsing strutturato (CSV, JSON)
2. **Pattern-based Parsing**: Estrazione `key=value` con regex
3. **Adaptive Parser**: Fallback per log non strutturati

### Caratteristiche Core
- **Dual Mining Drain3**: Clustering separato per log originali e anonimizzati
- **Anonimizzazione**: Mascheramento di IP, MAC, email, ecc.
- **Regex Centralizzato**: Gestione unificata di tutti i pattern
- **Normalizzazione Timestamp**: Conversione automatica formati data/ora

## Utilizzo

```bash
python3 cli_parser.py parse <input_file> <output_dir>
```

## Configurazione

Il progetto utilizza una configurazione centralizzata in `config/config.yaml` che include:

- **Regex Patterns**: Tutti i pattern regex per anonimizzazione, parsing e cleaning
- **Drain3 Configuration**: Parametri per il template mining
- **File Formats**: Configurazione per i formati di file supportati
- **Parser Configuration**: Configurazione dettagliata per tutti i parser
- **Timestamp Normalization**: Pattern per la normalizzazione delle date
- **Output & Logging**: Configurazione per output e logging

### Struttura della Configurazione

```
config/
└── config.yaml             # Configurazione centralizzata unificata
```

**Nota**: Tutta la configurazione è ora centralizzata in `config.yaml` per evitare duplicazioni e garantire coerenza.
