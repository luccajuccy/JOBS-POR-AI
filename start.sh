#!/bin/bash
echo "========================================="
echo "Jobs por AI - Iniciando o Servidor Linux"
echo "========================================="
echo ""

# Verifica se existe um ambiente virtual e o ativa
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Instala dependências caso ainda não existam (opcional, se pip estiver disponível)
# pip install -r requirements.txt

# Inicia o servidor com hot-reload
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
