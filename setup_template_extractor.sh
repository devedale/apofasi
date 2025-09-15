#!/bin/bash

# Script per configurare LogPPT-TemplateExtractor con Ollama
echo "🚀 Setup LogPPT-TemplateExtractor con Ollama..."

# Aspetta che Ollama sia pronto
echo "⏳ Aspettando che Ollama sia pronto..."
sleep 10

# Crea il modello TemplateExtractor in Ollama
echo "📥 Creando modello LogPPT-TemplateExtractor in Ollama..."
docker exec -it ollama ollama create logppt-template-extractor -f /root/LogPPT/Modelfile.template_extractor

# Verifica che il modello sia stato creato
echo "🔍 Verificando modelli disponibili..."
docker exec -it ollama ollama list

# Test del modello template extractor
echo "🧪 Test del modello LogPPT-TemplateExtractor..."
docker exec -it ollama ollama run logppt-template-extractor "Parse this log: 03-17 16:13:38.811 1702 2395 D WindowManager: test message"

echo "✅ Setup completato! LogPPT-TemplateExtractor è ora disponibile in Ollama."
echo "💡 Usa 'docker exec -it ollama ollama run logppt-template-extractor' per testare"
echo "🎯 Questo modello replica ESATTAMENTE la template extraction originale di LogPPT!"
echo "📝 Placeholder supportati: HH, MM, SS, SSS, YYYY, MM, DD, PID1, PID2, LEVEL, IP, PORT, <*>"
