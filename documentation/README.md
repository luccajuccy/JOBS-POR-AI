# 📘 Jobs por AI - Documentação Oficial

![Banner placeholder](Coloque o banner do projeto aqui)

## 📌 Visão Geral
**Jobs por AI** é uma plataforma revolucionária de match profissional inspirada em mecânicas dinâmicas de aplicativos de relacionamento (como o Tinder). A ideia central é agilizar o recrutamento e seleção de candidatos de forma direta, sem formulários extensos e com máxima interatividade.

---

## ⚙️ Arquitetura e Tecnologias
O sistema foi construído visando robustez para cenários reais de acesso simultâneo:
- **Backend:** Python 3 + FastAPI (Totalmente assíncrono para máxima performance)
- **Banco de Dados:** SQLite acionado via `aiosqlite` + SQLAlchemy 2.0 (Modelagem 100% não bloqueante suportando múltiplos requests em paralelo sem travar o event-loop)
- **Frontend:** Jinja2 + TailwindCSS via CDN (Design system mobile-first, focado em alta interatividade, cards e micro-animações)
- **Mapas:** Leaflet.js para processamento de rotas e geolocalização visual.

---

## 🔄 Diagrama de Fluxo (Funil dos Usuários)

Abaixo, o fluxo lógico desde o acesso até a consolidação de uma vaga através de um Match.

```mermaid
graph TD
    A([Visitante]) --> B(Login / Cadastro)
    B --> C{Qual é o Perfil?}
    
    C -->|Candidato| D[Página Explorar - UI de Swipe]
    C -->|Empresa| E[Painel da Empresa - Abas]

    D -->|Swipe Direita| F(Like na Vaga)
    D -->|Swipe Esquerda| G(Dislike na Vaga)
    
    E -->|Cria Nova Vaga| H(Vaga Publicada)
    E -->|Analisa Candidatos| I(Like no Candidato)

    F --> J{Ocorreu Match?}
    I --> J
    
    J -->|Sim| K[Chat Liberado]
    K --> L([Comunicação Direta])
```

---

## 📱 Telas do Sistema (UI/UX)

### 1. Autenticação (Login e Cadastro)
A tela de entrada foca em conversão rápida, com um visual premium utilizando backdrop-blurs e validações claras.
- **Desktop:** 
 <img width="1359" height="698" alt="image" src="https://github.com/user-attachments/assets/d8dc35e7-03f6-481e-a90d-c2713c5104c5" />

- **Mobile:**
  
  <img width="398" height="863" alt="image" src="https://github.com/user-attachments/assets/65c20b89-d5d5-4abf-97d0-af5983890ded" />


### 2. Tela "Explorar" (A visão do Candidato)
O coração da experiência para quem procura emprego. As vagas são exibidas em formato de "Cartas" sobrepostas. O candidato avalia percentual de compatibilidade, pílulas de habilidades e distância em Km.
- **Interação:** Mouse drag no Desktop e Touch Swipe no Mobile. Se o usuário arrastar para a direita (LIKE), o sistema verifica imediatamente se houve um Match mútuo.
- **Desktop:**
- 
<img width="1205" height="842" alt="image" src="https://github.com/user-attachments/assets/d0cc4cab-b9f4-4bb3-9f9c-04c1165f0e50" />

- **Mobile:**

  <img width="402" height="872" alt="image" src="https://github.com/user-attachments/assets/8127098e-78b6-40f6-9f72-43fdcd455713" />


### 3. Dashboard da Empresa (Gestão de Candidatos)
Em vez de listas cansativas, a empresa clica em abas (tabs horizontais) para alternar entre as vagas ativas. Ao selecionar uma vaga, uma API carrega em tempo real todos os candidatos que deram "Like", ordenados pela melhor compatibilidade.
- **Desktop:**

<img width="1170" height="1106" alt="image" src="https://github.com/user-attachments/assets/6faaeca7-e245-4141-a93f-0d18c0550221" />


 
- **Mobile:**

 <img width="400" height="871" alt="image" src="https://github.com/user-attachments/assets/acc2d11d-3790-4d91-b022-2c68afef2239" />

### 4. Integração de Mapas (Leaflet)
Tanto candidatos quanto empresas têm à disposição mapas geográficos. Para não poluir ou "bugar" a tela mobile, o mapa fica encapsulado atrás de botões de expansão (`Ver localização`). No PC, ele pode ser exibido elegantemente ao lado dos cards.
- **Desktop:**
  <img width="1172" height="941" alt="image" src="https://github.com/user-attachments/assets/2538a862-410d-4c17-b45f-cd4fdb531c20" />

- **Mobile:**

  <img width="390" height="857" alt="image" src="https://github.com/user-attachments/assets/f86badaa-2eab-40ef-9b5c-151893681822" />

### 5. Chat em Tempo Real
Quando ocorre o "Match", as partes são habilitadas a conversar.
- O sistema usa **Polling Incremental**: só baixa mensagens novas a cada 2 segundos via uma API `?after_id=X`, economizando tráfego de dados e sem repintar a tela (Zero "flickering" ou quebras de scroll).
- O sistema tem **Idempotência**: evita que a mesma mensagem seja cadastrada duas vezes seguidas se o usuário clicar sem parar ou se a rede lagar (intervalo seguro de 5s).
- **Desktop:**

<img width="1196" height="944" alt="image" src="https://github.com/user-attachments/assets/d978ab0e-21ed-4068-87bf-2b43b988269e" />

- **Mobile:**

<img width="481" height="769" alt="image" src="https://github.com/user-attachments/assets/1b72808e-2dc0-4f93-a6d4-754979b113bd" />



### 6. Perfil, Dashboard Analítico e Assinaturas
- **Desktop:**

  <img width="1119" height="865" alt="image" src="https://github.com/user-attachments/assets/e94635ba-017f-4015-82eb-7207c78583bd" />


- **Mobile:**
  <img width="396" height="866" alt="image" src="https://github.com/user-attachments/assets/1cb058d9-175b-4fe7-8e49-5b50002224c3" />

- **Dashboard:**

  <img width="1160" height="877" alt="image" src="https://github.com/user-attachments/assets/1295e5c7-c93d-4745-b22a-6e2f859b09e6" />
  

---

## 🎯 Monetização: Sistema de Assinaturas e Anúncios

O modelo de negócios é ancorado em um formato **Freemium** inteligente:

1. **Plano Free (Gratuito):**
   - O Candidato possui limites estritos de visualizações/likes diários (ex: 5 interações por dia). 
   - A interface insere nativamente caixas de alerta (Anúncios/Ads - os `AdEvents`) no meio do uso diário avisando sobre as vantagens dos planos Premium.
2. **Plano Básico / Anual:**
   - Remove o limite diário de swipes.
   - Remove permanentemente todas as barras de anúncios da interface.
3. **Premium IA (Agentes Autônomos):**
   - Garante que agentes varram ativamente o banco de dados. Assim que uma empresa publica uma vaga, caso a compatibilidade do candidato passe de 55%, o sistema gera o "Like" do usuário automaticamente.

---

## 🔐 Segurança Implementada
- **Sessões HMAC:** Controle de login via cookies encriptados via Hash, mitigando falsificações.
- **PBKDF2:** Uso de salt e hasheamento moderno para a custódia das senhas dos usuários.
- **Isolamento de Views:** Controle ríspido onde perfis "Empresa" não enxergam a rota `/explorar`, e "Candidatos" não burlam rotas de criação de vagas (`/empresa`).

---
