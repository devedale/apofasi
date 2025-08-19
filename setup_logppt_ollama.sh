#!/bin/bash

# Script per configurare LogPPT con Ollama
echo "🚀 Setup LogPPT con Ollama..."

# Aspetta che Ollama sia pronto
echo "⏳ Aspettando che Ollama sia pronto..."
sleep 10

# Crea il modello LogPPT in Ollama
echo "📥 Creando modello LogPPT in Ollama..."
docker exec -it ollama ollama create logppt-parser -f /root/LogPPT/Modelfile.logppt

# Verifica che il modello sia stato creato
echo "🔍 Verificando modelli disponibili..."
docker exec -it ollama ollama list

# Test del modello
echo "🧪 Test del modello LogPPT..."
docker exec -it ollama ollama run logppt-parser "Parse this log: 03-17 16:13:38.811 1702 2395 D WindowManager: test message"

echo "✅ Setup completato! LogPPT è ora disponibile in Ollama."
echo "💡 Usa 'docker exec -it ollama ollama run logppt-parser' per testare"
