# 📘 Jobs por AI - MVP

Bem-vindo ao **Jobs por AI**, uma plataforma de match profissional que visa simplificar e acelerar o processo de recrutamento com uma interface inspirada em apps de relacionamento.

![Status](https://img.shields.io/badge/Status-Concluido-success)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Assincrono-00a393)

## 📖 Documentação Completa

Para aprofundamento na arquitetura, modelos de monetização (freemium), diagramas de fluxo e UI, acesse a pasta interna:
👉 **[documentation/README.md](./documentation/README.md)**

---

## 🚀 Como Executar Localmente

Este projeto foi construído nativamente usando Python e SQLite, o que o torna portátil e funcional de imediato em qualquer sistema operacional, seja Windows, Linux ou macOS.

### Pré-requisitos
- Ter o **Python 3.8+** (ou mais recente) instalado.
- Ter o **Git** instalado.

### 1. Clonar e Preparar
Abra o terminal e baixe o projeto:
```bash
git clone https://github.com/luccajuccy/JOBS-POR-AI.git
cd JOBS-POR-AI
```

### 2. Instalar as Dependências
Recomendamos o uso de um ambiente virtual (venv):

**No Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**No Linux (Ubuntu, Arch Linux, etc) / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Gerar a Base de Dados
Para popular o SQLite com dados de teste, contas de exemplo e simular matches:
```bash
python populate.py
```
*O console exibirá as credenciais de exemplo criadas.*

### 4. Rodar o Servidor
Com tudo instalado, inicie o FastAPI localmente na porta 5000:

**Opção A (Windows via Batch):**
Dê um duplo clique no arquivo `start.bat`.

**Opção B (Linux via Script):**
```bash
chmod +x start.sh
./start.sh
```

**Opção C (Manual - Qualquer S.O):**
```bash
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

Acesse no navegador: **[http://localhost:5000](http://localhost:5000)**

---

*Repositório construído sob encomenda de forma profissional para escalabilidade e alta interatividade.*
