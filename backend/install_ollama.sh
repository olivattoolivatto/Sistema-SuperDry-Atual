#!/bin/bash
# ── Instalar Ollama na VM Oracle Cloud (ARM aarch64, Ubuntu 22.04) ────────────
# Uso: bash install_ollama.sh
# Pré-requisito: VM com 24GB RAM (Oracle Free Tier ARM). Recomendado: llama3.2:3b (~2GB)
set -e

echo "=== Instalando Ollama ==="
curl -fsSL https://ollama.com/install.sh | sh

echo ""
echo "=== Baixando modelo llama3.2:3b (~2GB) ==="
ollama pull llama3.2:3b

echo ""
echo "=== Habilitando serviço ==="
# Ollama já cria o systemd unit automaticamente.
# Garante que roda na inicialização:
systemctl enable ollama 2>/dev/null || true
systemctl start ollama 2>/dev/null || true

echo ""
echo "=== Teste rápido ==="
ollama run llama3.2:3b "Responda em uma frase: o que é a SuperDry Lavanderia?"

echo ""
echo "✅ Ollama instalado. API disponível em http://localhost:11434"
echo "   Para verificar: curl http://localhost:11434/api/tags"
echo "   Para testar o parser: python3 test_ollama.py"
