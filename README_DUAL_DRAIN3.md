# 🔍 Dual Mining Drain3 - Guida Completa

## 📋 Panoramica

Il sistema **Dual Mining Drain3** permette di calcolare cluster e template sia sui **messaggi originali** che sui **messaggi anonimizzati** dei log, fornendo una visione completa dei pattern strutturali e semantici.

## 🎯 Vantaggi del Dual Mining

### **1. Analisi Completa**
- **Messaggi Originali**: Pattern dettagliati con valori specifici (IP, timestamp, ID)
- **Messaggi Anonimizzati**: Pattern strutturali senza dati sensibili

### **2. Use Case Specifici**
- **Sicurezza**: Analisi di pattern sospetti mantenendo la privacy
- **Compliance**: Conformità GDPR/CCPA con analisi strutturale
- **Debugging**: Identificazione di problemi senza esporre dati sensibili
- **Machine Learning**: Dataset sicuri per training di modelli

### **3. Configurazione Flessibile**
- Parametri separati per ogni tipo di miner
- Soglie di similarità personalizzabili
- Profondità e dimensioni cluster ottimizzabili

## 🚀 Utilizzo Base

### **Configurazione**

```yaml
# config/config.yaml
drain3:
  # Parametri per messaggi originali
  original:
    depth: 4
    max_children: 100
    max_clusters: 1000
    similarity_threshold: 0.4
  
  # Parametri per messaggi anonimizzati
  anonymized:
    depth: 3
    max_children: 50
    max_clusters: 500
    similarity_threshold: 0.6
```

### **Utilizzo nel Codice**

```python
from infrastructure.drain3_service import Drain3ServiceImpl

# Crea servizio con configurazione
config = {"drain3": {...}}
drain3_service = Drain3ServiceImpl(config)

# Mining su messaggio originale
original_cluster_id = drain3_service.add_log_message(message, "original")
original_template = drain3_service.get_template(original_cluster_id, "original")

# Mining su messaggio anonimizzato
anonymized_cluster_id = drain3_service.add_log_message(message, "anonymized")
anonymized_template = drain3_service.get_template(anonymized_cluster_id, "anonymized")

# Processamento completo di un record
processed_record = drain3_service.process_record(parsed_record)
```

## 📊 Struttura dei Dati

### **Record Processato**

```json
{
  "parsed_data": {
    "drain3_original": {
      "cluster_id": 1,
      "template": "logver=1.0 idseq=<SEQ_NUM> itime=<TIME>...",
      "cluster_size": 5
    },
    "drain3_anonymized": {
      "cluster_id": 2,
      "template": "logver=<VERSION> idseq=<SEQ_NUM> itime=<TIME>...",
      "cluster_size": 3
    },
    "drain3_cluster_id": 1,        // Compatibilità
    "drain3_template": "...",      // Compatibilità
    "drain3_cluster_size": 5       // Compatibilità
  }
}
```

### **Statistiche Combinate**

```python
stats = drain3_service.get_statistics()
# Risultato:
{
  "original": {
    "total_clusters": 10,
    "total_logs": 150
  },
  "anonymized": {
    "total_clusters": 8,
    "total_logs": 150
  },
  "combined": {
    "total_clusters": 18,
    "total_logs": 300
  }
}
```

## 🔧 API Avanzate

### **Template Combinati**

```python
# Tutti i template da entrambi i miner
all_templates = drain3_service.get_all_templates_combined()
# Risultato: {"original": {...}, "anonymized": {...}}

# Template specifici per tipo
original_templates = drain3_service.get_all_templates("original")
anonymized_templates = drain3_service.get_all_templates("anonymized")
```

### **Informazioni Cluster**

```python
# Info cluster originale
original_info = drain3_service.get_cluster_info(cluster_id, "original")

# Info cluster anonimizzato
anonymized_info = drain3_service.get_cluster_info(cluster_id, "anonymized")
```

### **Persistenza**

```python
# Salva stato di entrambi i miner
drain3_service.save_state("path/to/state")

# Carica stato di entrambi i miner
drain3_service.load_state("path/to/state")
```

## 📁 Output del Reporting

Il sistema genera automaticamente:

### **File di Output**
- `drain3_full.json` - Dump completo combinato
- `drain3_original.json` - Solo cluster originali
- `drain3_anonymized.json` - Solo cluster anonimizzati

### **Struttura Output**

```json
{
  "summary": {
    "total_original_clusters": 10,
    "total_anonymized_clusters": 8,
    "total_clusters": 18
  },
  "original_clusters": [...],
  "anonymized_clusters": [...]
}
```

## 🧪 Testing

### **Eseguire i Test**

```bash
# Test completo
python test_dual_drain3.py

# Esempio pratico
python example_dual_drain3.py
```

### **Test Coverage**

- ✅ Dual mining funzionante
- ✅ Parametri separati per ogni miner
- ✅ Compatibilità con API esistenti
- ✅ Persistenza e caricamento stato
- ✅ Integrazione con sistema di parsing
- ✅ Reporting separato per ogni tipo

## 🔄 Migrazione da Versione Precedente

### **Compatibilità**
- Tutte le API esistenti continuano a funzionare
- I campi `drain3_cluster_id`, `drain3_template` sono mantenuti
- Il comportamento predefinito usa il miner "original"

### **Nuove Funzionalità**
- Aggiungere `miner_type` ai metodi esistenti
- Utilizzare i nuovi campi `drain3_original` e `drain3_anonymized`
- Sfruttare le statistiche combinate

## 💡 Best Practices

### **1. Configurazione Ottimale**
- **Original**: Profondità maggiore (4-5) per pattern dettagliati
- **Anonymized**: Profondità minore (3-4) per pattern strutturali
- **Soglie**: Più alte per anonimizzati (0.6+) per evitare over-clustering

### **2. Analisi dei Risultati**
- Confronta i pattern tra i due miner
- Identifica cluster che differiscono significativamente
- Usa i template anonimizzati per compliance e condivisione

### **3. Performance**
- Il dual mining raddoppia il tempo di elaborazione
- Considera l'uso di parametri più restrittivi per l'anonymized
- Monitora l'uso di memoria per cluster separati

## 🚨 Troubleshooting

### **Problemi Comuni**

1. **Cluster ID Duplicati**
   - Verifica che i miner siano inizializzati correttamente
   - Controlla la configurazione dei parametri

2. **Template Non Corretti**
   - Verifica la configurazione di anonimizzazione
   - Controlla i pattern regex applicati

3. **Performance Degradate**
   - Riduci il numero massimo di cluster
   - Aumenta le soglie di similarità
   - Considera l'uso di un solo miner se non necessario

### **Debug**

```python
# Abilita logging dettagliato
import logging
logging.basicConfig(level=logging.DEBUG)

# Verifica configurazione
print(drain3_service._config)

# Controlla stato miner
print(drain3_service.get_statistics())
```

## 📚 Riferimenti

- [Drain3 Documentation](https://github.com/IBM/Drain3)
- [Template Mining Algorithms](https://ieeexplore.ieee.org/document/7837917)
- [Log Anonymization Best Practices](https://www.nist.gov/publications/log-anonymization-guidelines)

## 🤝 Contributi

Per migliorare il sistema dual mining:

1. Aggiungi nuovi parametri di configurazione
2. Implementa algoritmi di clustering alternativi
3. Migliora le metriche di performance
4. Aggiungi test per edge case specifici

---

**Nota**: Questo sistema mantiene piena compatibilità con le versioni precedenti mentre aggiunge potenti funzionalità di dual mining per analisi avanzate dei log.
