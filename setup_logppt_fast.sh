#!/bin/bash

# Script per configurare LogPPT-Fast con Ollama
echo "🚀 Setup LogPPT-Fast con Ollama..."

# Aspetta che Ollama sia pronto
echo "⏳ Aspettando che Ollama sia pronto..."
sleep 10

# Crea il modello LogPPT-Fast in Ollama
echo "📥 Creando modello LogPPT-Fast in Ollama..."
docker exec -it ollama ollama create logppt-parser-fast -f /root/LogPPT/Modelfile.logppt.fast

# Verifica che il modello sia stato creato
echo "🔍 Verificando modelli disponibili..."
docker exec -it ollama ollama list

# Test del modello veloce
echo "🧪 Test del modello LogPPT-Fast..."
docker exec -it ollama ollama run logppt-parser-fast "Parse this log: 03-17 16:13:38.811 1702 2395 D WindowManager: test message"

echo "✅ Setup completato! LogPPT-Fast è ora disponibile in Ollama."
echo "💡 Usa 'docker exec -it ollama ollama run logppt-parser-fast' per testare"
echo "🚀 Il modello è ottimizzato per velocità e non dovrebbe più bloccarsi!"
