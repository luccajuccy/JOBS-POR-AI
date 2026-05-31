# Jobs por AI — Evolução MVP

## Arquitetura e Decisões de Design

O protótipo inicial foi refatorado para garantir um MVP robusto, responsivo, sem travamentos e com a melhor experiência de usuário.

### Mudanças Principais:

1. **Backend Assíncrono (`app.py`, `database.py`)**
   - Migração completa de SQLAlchemy síncrono para `SQLAlchemy[asyncio]` com driver `aiosqlite`.
   - Isso impede o bloqueio do event-loop do FastAPI durante consultas ao banco de dados, que era a causa principal de lentidão ou travamentos quando múltiplos usuários (Candidato e Empresa) interagiam simultaneamente.

2. **Frontend Padronizado (`Tailwind CSS`)**
   - Centralização do design no arquivo `_base.html`. O arquivo customizado `_style.html` e as duplicações de menu foram removidos.
   - Aplicação de `cdn.tailwindcss.com` garantindo visual moderno, mobile-first e cores coesas (marca em amarelo `#fabd00` e fundos neutros).

3. **Explore — Tinder-style UI (`explore.html`)**
   - A página principal do candidato deixou de ser uma lista e passou a ser uma interface de swipe (arrastar e soltar).
   - Implementada via touch events (mobile) e mouse drag (desktop).
   - Ao soltar um card, a animação processa o Like/Dislike. Em caso de Match, um overlay "IT'S A MATCH" é exibido com link para o Chat.
   - Integração com Leaflet para exibir o mapa e calcular a distância geográfica em km.

4. **Painel da Empresa (`company.html`)**
   - Separação entre a lista de Vagas e a visualização de Candidatos via um sistema de *tabs* laterais/horizontais.
   - Todo carregamento de candidatos ocorre via API JSON assíncrona.
   - Exibição avançada dos candidatos com score de compatibilidade, pílulas de habilidades, mini currículo, e mapa.
   - Permite a criação de novas vagas via Modal.

5. **Chat com Polling Incremental (`chats.html`)**
   - O chat antigo substitua todo o DOM e perdia posição de scroll a cada refresh.
   - Refeito com API via `fetch()` e um fluxo incremental usando um parâmetro `?after_id=X`. Apenas as mensagens novas são inseridas no final do container de mensagens.
   - Adicionada idempotência: para evitar o envio duplicado se o usuário clicar duas vezes no botão de enviar. O servidor rejeita duplicação num intervalo de 5 segundos.

6. **Limpeza de Código Morto**
   - Templates legados (`explorar.html`, `dashboard.html`, `config.html`, `agents.html`) foram apagados para evitar confusão de navegação e garantir apenas as rotas válidas presentes no `app.py`.
   - Scripts paralelos ou rotas que não possuíam implementação (`/agentes`) não foram integrados no menu, mantendo o MVP focado.

## Instalação e Execução

### Pré-requisitos
- Python 3.8+
- Bibliotecas descritas no `requirements.txt` (Instale com `pip install -r requirements.txt`)

### Passos de Instalação e Dados de Teste

1. Instale as dependências.
2. Rode o script de povoamento para apagar dados velhos e gerar novos cenários realistas:
   ```bash
   python populate.py
   ```
3. O script criará o banco `jobmatcher.db` e registrará usuários testes com interações de like/match entre eles.
4. Inicie o servidor:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 5000
   ```

### Usuários Demo:
- **Candidato:** `candidato1@demo.com` | Senha: `123456`
- **Empresa:** `empresa1@demo.com` | Senha: `123456`
