# 🧪 Guida Completa ai Test del Sistema

## 📋 File di Esempio Creati

### 📊 Dataset per Fine-Tuning

1. **conversational_dataset.json** - Chat conversazionale in italiano
   - 10 esempi di domande e risposte
   - Formato: {"instruction": "...", "response": "..."}
   - Ideale per training di chatbot

2. **sentiment_classification.csv** - Analisi sentiment
   - 20 esempi con testo, sentiment e confidence
   - Formato CSV standard
   - Perfetto per classificazione di sentimenti

3. **code_generation.yaml** - Generazione codice
   - Esempi Python, JavaScript, SQL
   - Formato YAML strutturato
   - Per training di coding assistant

4. **qa_dataset.txt** - Q&A in formato testo
   - 8 coppie domanda-risposta tecniche
   - Formato TXT semplice
   - Test riconoscimento automatico formato

### 📄 File di Log per LogPPT

1. **sample_logs.txt** - Log applicazione standard
   - 30 righe con diversi livelli (INFO, WARNING, ERROR, CRITICAL)
   - Timestamp, eventi sistema, errori comuni
   - Formato classico per parsing

2. **apache_access.log** - Log server web
   - 20 righe di access log Apache
   - IP, timestamp, richieste HTTP, status code
   - Include tentativi di attacco e traffico normale

## 🔧 Piano di Test Completo

### 1️⃣ Test Gestione Modelli Ollama

**Obiettivo**: Verificare download, lista, eliminazione modelli

**Passi**:
1. Vai su tab "Gestione Modelli"
2. Verifica stato Ollama (dovrebbe essere verde)
3. Prova a scaricare un modello predefinito (es: logppt-parser)
4. Controlla la lista modelli installati
5. Prova eliminazione di un modello

**Risultato Atteso**: 
- ✅ Status Ollama verde
- ✅ Download funzionante
- ✅ Lista aggiornata
- ✅ Eliminazione possibile

### 2️⃣ Test LogPPT (Parsing Log)

**Obiettivo**: Verificare parsing log con Ollama

**Passi**:
1. Vai su tab "LogPPT"
2. Carica il file `examples/sample_logs.txt`
3. Seleziona modello "logppt-parser"
4. Avvia elaborazione
5. Controlla risultati e download

**Test Alternativi**:
- Prova con `apache_access.log` per log web
- Testa diversi modelli LogPPT disponibili

**Risultato Atteso**:
- ✅ Upload file riuscito
- ✅ Parsing completato
- ✅ Risultati leggibili
- ✅ Download Excel disponibile

### 3️⃣ Test Fine-Tuning LLM

**Obiettivo**: Workflow completo di fine-tuning

#### Passo 1: Selezione Modello Base
1. Vai su tab "LLM Fine-Tuning"
2. Seleziona un modello base (es: llama2:7b)
3. Verifica status ✅

#### Passo 2: Template di Training
1. Seleziona template "Conversational AI"
2. Guarda preview del template
3. Verifica status ✅

#### Passo 3: Dataset Upload & Validazione
1. Carica `conversational_dataset.json`
2. Attendi validazione automatica
3. Controlla anteprima dataset
4. Verifica status ✅

**Test Alternativi**:
- Prova CSV: `sentiment_classification.csv`
- Prova YAML: `code_generation.yaml`
- Prova TXT: `qa_dataset.txt`

#### Passo 4: Configurazione & Training
1. Inserisci nome modello (es: "my-chatbot-v1")
2. Verifica parametri (temperatura, top-p, top-k)
3. Clicca "Avvia Fine-Tuning"
4. Monitora progress bar e log live

**Risultato Atteso**:
- ✅ Progress bar attiva
- ✅ Log real-time visibili (testo scuro!)
- ✅ Completamento training
- ✅ Modello disponibile per test

### 4️⃣ Test Modello Fine-Tuned

**Obiettivo**: Testare modello appena creato

**Passi**:
1. Nella sezione "Test del Modello"
2. Clicca refresh (🔄) per aggiornare lista
3. Seleziona il tuo modello fine-tuned
4. Inserisci prompt di test (es: "Spiegami cosa è Python")
5. Clicca "Testa Modello"

**Risultato Atteso**:
- ✅ Lista modelli aggiornata
- ✅ Selezione modello funzionante (no più placeholder!)
- ✅ Test prompt eseguito
- ✅ Risposta coerente con training

### 5️⃣ Test Esportazione Modello

**Obiettivo**: Esportare modello per uso esterno

**Passi**:
1. Seleziona modello fine-tuned
2. Clicca "Esporta Modello"
3. Attendi completamento
4. Verifica status esportazione

## 🐛 Problemi Risolti Durante Test

1. **❌ JavaScript Error**: `modelNameInput` duplicato
   - ✅ **Fix**: Rinominato in `ftModelNameInput` per fine-tuning

2. **❌ Testo Log Invisibile**: Colore bianco su grigio
   - ✅ **Fix**: Cambiato colore a grigio scuro (#2d3748)

3. **❌ Selettore Modelli Vuoto**: Solo modelli fine-tuned
   - ✅ **Fix**: Ora mostra TUTTI i modelli Ollama + fine-tuned

## 📝 Checklist Test Completa

### Funzionalità Base
- [ ] Gestione Modelli Ollama
- [ ] LogPPT parsing con diversi formati
- [ ] Upload dataset multipli formati

### Fine-Tuning Workflow
- [ ] Selezione modello base
- [ ] Scelta template training
- [ ] Validazione dataset (JSON/CSV/YAML/TXT)
- [ ] Configurazione parametri
- [ ] Avvio e monitoraggio training
- [ ] Test modello risultante
- [ ] Esportazione modello

### UI/UX
- [ ] Tab switching funzionale
- [ ] Status indicator corretti
- [ ] Progress bar attive
- [ ] Log real-time leggibili
- [ ] Selettori popolati correttamente

## 🎯 Test Avanzati Opzionali

1. **Test Stress**: Caricare dataset molto grandi
2. **Test Multi-Formato**: Mixare diversi tipi di dataset
3. **Test Parametri**: Variare temperatura, top-p, top-k
4. **Test Modelli Diversi**: Provare llama3.2, mistral, codellama
5. **Test Prompt Complessi**: Prompt multi-lingua o tecnici

## 📞 Supporto

Se trovi problemi:
1. Controlla console browser (F12) per errori JavaScript
2. Verifica log Docker Compose
3. Assicurati che Ollama sia in running
4. Controlla che i modelli base siano scaricati

**Happy Testing! 🚀**
