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

- `config/config.ini`: Configurazione principale
- `config/centralized_regex.yaml`: Pattern regex centralizzati
