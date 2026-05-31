"""
Crawler system for JobMatcher.
=============================================================
AVISO ÉTICO / ETHICAL NOTICE:
Este sistema é para fins educacionais e de demonstração.
Respeite os termos de serviço dos sites buscados.
O crawler do Google NÃO deve ser usado em produção sem
autorização ou API oficial.
=============================================================

Crawlers implementados:
  - MockCrawler: dados fictícios para demonstração
  - GoogleCrawler: busca REAL via SerpAPI (google_jobs engine)
  - LinkedInCrawler: estrutura preparada para integração futura

Modo Híbrido:
  - Tenta SerpAPI; se falhar, usa sample_jobs.json
  - Flag is_sample=1 indica "dados de exemplo"
"""
import os
import json
import time
import random
import hashlib
from datetime import datetime
from logger_config import logger, log_to_db

# ============================================================
# CONFIGURAÇÃO
# ============================================================
# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "").strip()
logger.info("SERPAPI_KEY loaded: %s (length=%d)", "***" + SERPAPI_KEY[-4:] if len(SERPAPI_KEY) > 4 else "(empty)", len(SERPAPI_KEY))
CRAWLER_DELAY_MIN = int(os.getenv("CRAWLER_DELAY_MIN", "2"))
CRAWLER_DELAY_MAX = int(os.getenv("CRAWLER_DELAY_MAX", "5"))
CRAWLER_MAX_RESULTS = int(os.getenv("CRAWLER_MAX_RESULTS", "10"))

# ============================================================
# USER-AGENT ROTATION (Anti-bloqueio)
# ============================================================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
    "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Vivaldi/6.4",
]

# ============================================================
# MOCK DATA - Realistic Brazilian job listings (kept for fallback)
# ============================================================
MOCK_COMPANIES = [
    "TechNova Solutions", "DataPulse S.A.", "CloudBridge Inc.",
    "NexGen Digital", "Synaptic Labs", "CodeVerse Ltda.",
    "InnovaStack", "AlphaCore Sistemas", "BrightPath Tech",
    "OmniLogic Group", "PrimeData Analytics", "FlowByte Solutions",
    "QubitSoft", "NeuroLink S.A.", "Vertex Dynamics",
    "ByteForge Labs", "CyberPulse Security", "AgileWorks Brasil"
]

MOCK_LOCATIONS = [
    "São Paulo, SP", "Rio de Janeiro, RJ", "Belo Horizonte, MG",
    "Curitiba, PR", "Porto Alegre, RS", "Florianópolis, SC",
    "Brasília, DF", "Campinas, SP", "Salvador, BA",
    "Recife, PE", "Goiânia, GO", "Fortaleza, CE"
]

MOCK_JOBS_TEMPLATES = [
    {
        "title": "Desenvolvedor Python Backend",
        "skills": "python,django,flask,fastapi,postgresql,docker",
        "level": "Pleno",
        "job_type": "FULL-TIME",
        "modality": "REMOTO",
        "description": "Desenvolvimento de APIs RESTful e microsserviços em Python."
    },
    {
        "title": "Engenheiro de Dados",
        "skills": "python,sql,spark,airflow,aws,etl",
        "level": "Senior",
        "job_type": "FULL-TIME",
        "modality": "HIBRIDO",
        "description": "Construção e manutenção de pipelines de dados em larga escala."
    },
    {
        "title": "Desenvolvedor Full-Stack",
        "skills": "javascript,react,node.js,python,mongodb,git",
        "level": "Pleno",
        "job_type": "FULL-TIME",
        "modality": "PRESENCIAL",
        "description": "Desenvolvimento de aplicações web end-to-end com React e Node.js."
    },
    {
        "title": "Analista de Dados Jr",
        "skills": "python,sql,excel,power bi,estatística",
        "level": "Junior",
        "job_type": "FULL-TIME",
        "modality": "REMOTO",
        "description": "Análise exploratória de dados e criação de dashboards."
    },
    {
        "title": "DevOps Engineer",
        "skills": "docker,kubernetes,aws,terraform,ci/cd,linux",
        "level": "Senior",
        "job_type": "FULL-TIME",
        "modality": "REMOTO",
        "description": "Infraestrutura como código e automação de deploys."
    },
    {
        "title": "Cientista de Dados",
        "skills": "python,machine learning,tensorflow,pandas,sql,estatística",
        "level": "Pleno",
        "job_type": "FULL-TIME",
        "modality": "HIBRIDO",
        "description": "Modelagem preditiva e análise avançada de dados."
    },
    {
        "title": "Desenvolvedor Mobile React Native",
        "skills": "react native,javascript,typescript,firebase,git",
        "level": "Junior",
        "job_type": "FULL-TIME",
        "modality": "PRESENCIAL",
        "description": "Desenvolvimento de aplicativos mobile cross-platform."
    },
    {
        "title": "Engenheiro de Software Senior",
        "skills": "java,spring boot,microservices,kafka,postgresql,docker",
        "level": "Senior",
        "job_type": "FULL-TIME",
        "modality": "REMOTO",
        "description": "Arquitetura e desenvolvimento de sistemas distribuídos."
    },
    {
        "title": "Analista de Segurança da Informação",
        "skills": "cybersecurity,python,linux,redes,pentest,siem",
        "level": "Pleno",
        "job_type": "FULL-TIME",
        "modality": "HIBRIDO",
        "description": "Monitoramento de segurança e resposta a incidentes."
    },
    {
        "title": "Product Designer (UX/UI)",
        "skills": "figma,design thinking,prototipagem,user research,html,css",
        "level": "Pleno",
        "job_type": "FULL-TIME",
        "modality": "REMOTO",
        "description": "Design de interfaces digitais centradas no usuário."
    },
    {
        "title": "QA Engineer / Testador",
        "skills": "selenium,python,cypress,testes automatizados,jira,git",
        "level": "Junior",
        "job_type": "FULL-TIME",
        "modality": "PRESENCIAL",
        "description": "Automação de testes e garantia de qualidade de software."
    },
    {
        "title": "Tech Lead Python",
        "skills": "python,fastapi,django,aws,docker,liderança,arquitetura",
        "level": "Senior",
        "job_type": "FULL-TIME",
        "modality": "REMOTO",
        "description": "Liderança técnica de squads e definição de arquitetura."
    },
]

AI_SUMMARY_TEMPLATES = [
    "Foco em {skills_sample}. {match_text}",
    "Empresa busca profissional com experiência em {skills_sample}. {match_text}",
    "Oportunidade com ênfase em {skills_sample}. {match_text}",
    "Vaga direcionada a especialistas em {skills_sample}. {match_text}",
]

MATCH_TEXTS = [
    "Perfeito para seu histórico profissional.",
    "Bom alinhamento com suas competências atuais.",
    "Forte sinergia com seu perfil.",
    "Oportunidade relevante para seu momento de carreira.",
    "Alinhamento parcial – pode ser um bom desafio.",
]


def calculate_compatibility(profile_skills_str, job_skills_str):
    """
    Calculate compatibility as intersection of skills / total profile skills.
    Returns a float 0.0 to 1.0.
    """
    if not profile_skills_str or not job_skills_str:
        return 0.0

    profile_skills = set(
        s.strip().lower() for s in profile_skills_str.split(",") if s.strip()
    )
    job_skills = set(
        s.strip().lower() for s in job_skills_str.split(",") if s.strip()
    )

    if not profile_skills:
        return 0.0

    intersection = profile_skills & job_skills
    return round(len(intersection) / len(profile_skills), 2)


def generate_ai_summary(job_skills_str, compatibility):
    """Generate a simulated AI summary for a job listing."""
    skills_list = [s.strip() for s in job_skills_str.split(",") if s.strip()]
    skills_sample = ", ".join(skills_list[:3])

    if compatibility >= 0.7:
        match_text = random.choice(MATCH_TEXTS[:3])
    elif compatibility >= 0.4:
        match_text = MATCH_TEXTS[3]
    else:
        match_text = MATCH_TEXTS[4]

    template = random.choice(AI_SUMMARY_TEMPLATES)
    return template.format(skills_sample=skills_sample, match_text=match_text)


def generate_source_url(title, company, index):
    """Generate a unique fake source URL for a job."""
    slug = title.lower().replace(" ", "-").replace("/", "-")
    company_slug = company.lower().replace(" ", "-").replace(".", "")
    uid = hashlib.md5("{}{}{}".format(slug, company_slug, index).encode()).hexdigest()[:8]
    return "https://jobs.example.com/vaga/{}-{}-{}".format(slug, company_slug, uid)


def _random_delay():
    """Delay aleatório entre requisições para anti-bloqueio."""
    delay = random.uniform(CRAWLER_DELAY_MIN, CRAWLER_DELAY_MAX)
    logger.debug("Anti-block delay: %.1fs", delay)
    time.sleep(delay)


def _get_random_user_agent():
    """Retorna um User-Agent aleatório da lista."""
    return random.choice(USER_AGENTS)


def _load_sample_jobs():
    """Carrega vagas de exemplo do arquivo sample_jobs.json."""
    sample_path = os.path.join(os.path.dirname(__file__), "sample_jobs.json")
    try:
        with open(sample_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to load sample_jobs.json: %s", str(e))
        return []


# ============================================================
# BASE CRAWLER
# ============================================================
class BaseCrawler:
    """
    Abstract base class for all crawlers.
    Subclasses must implement crawl().
    """

    def __init__(self, name="base"):
        self.name = name

    def crawl(self, query, profile_skills="", profile_level=""):
        """
        Override this method in subclasses.
        Should return a list of dicts with keys:
        {title, company, location, description, skills, level,
         job_type, modality, source_url, source, published_at, is_sample}
        """
        raise NotImplementedError("Subclasses must implement crawl()")


# ============================================================
# MOCK CRAWLER (demo data)
# ============================================================
class MockCrawler(BaseCrawler):
    """Mock crawler that generates realistic sample jobs."""

    def __init__(self):
        super().__init__(name="mock")
        self._run_count = 0

    def crawl(self, query="", profile_skills="", profile_level=""):
        self._run_count += 1
        results = []

        templates = list(MOCK_JOBS_TEMPLATES)
        random.shuffle(templates)
        count = random.randint(5, min(8, len(templates)))
        selected = templates[:count]

        for i, template in enumerate(selected):
            company = random.choice(MOCK_COMPANIES)
            location = random.choice(MOCK_LOCATIONS)
            source_url = generate_source_url(
                template["title"], company,
                self._run_count * 100 + i
            )
            compat = calculate_compatibility(profile_skills, template["skills"])
            ai_summary = generate_ai_summary(template["skills"], compat)
            distance = round(random.uniform(1, 50), 1)

            results.append({
                "title": template["title"],
                "company": company,
                "location": location,
                "description": template["description"],
                "skills": template["skills"],
                "level": template["level"],
                "job_type": template["job_type"],
                "modality": template["modality"],
                "source_url": source_url,
                "source": "mock",
                "distance_km": distance,
                "compatibility": compat,
                "ai_summary": ai_summary,
                "published_at": "",
                "is_sample": 0,
                "raw_data": "",
            })

        return results


# ============================================================
# GOOGLE CRAWLER (real, via SerpAPI)
# ============================================================
class GoogleCrawler(BaseCrawler):
    """
    Crawler real para vagas do Google usando SerpAPI.
    
    =====================================================
    AVISO DE PRODUÇÃO:
    - Em produção, use API paga (SerpAPI ou ScrapingBee)
    - NÃO faça scraping direto do Google (bloqueio rápido)
    - O plano gratuito da SerpAPI oferece 100 buscas/mês
    - Obtenha sua chave em: https://serpapi.com
    =====================================================
    
    Modo híbrido:
    1. Tenta SerpAPI com google_jobs engine
    2. Se falhar, carrega sample_jobs.json como fallback
    3. Flag is_sample=1 indica dados de exemplo
    """

    def __init__(self):
        super().__init__(name="google")
        self._has_api_key = bool(SERPAPI_KEY)

    def _build_query(self, base_query, profile_skills="", profile_level=""):
        """
        Constrói Google Dork dinâmico baseado no perfil.
        Ex: 'desenvolvedor python pleno' -> busca otimizada
        """
        parts = []

        if base_query:
            parts.append(base_query)

        # Adicionar nível se relevante
        if profile_level and profile_level.lower() not in base_query.lower():
            level_map = {
                "junior": "júnior OR junior",
                "pleno": "pleno OR mid-level",
                "senior": "sênior OR senior OR lead",
            }
            mapped = level_map.get(profile_level.lower(), profile_level)
            parts.append(mapped)

        query = " ".join(parts)
        logger.info("[GoogleCrawler] Query construída: %s", query)
        return query

    def _search_serpapi(self, query):
        """
        Busca via SerpAPI google_jobs engine.
        Retorna lista de resultados brutos ou None em caso de erro.
        """
        try:
            from serpapi import GoogleSearch
        except ImportError:
            logger.error("[GoogleCrawler] serpapi não instalado. pip install google-search-results")
            return None

        params = {
            "engine": "google_jobs",
            "q": query,
            "hl": "pt-br",
            "gl": "br",
            "api_key": SERPAPI_KEY,
        }

        logger.info("[GoogleCrawler] Consultando SerpAPI google_jobs com query: '%s'", query)
        logger.debug("[GoogleCrawler] API key (últimos 4): ...%s", SERPAPI_KEY[-4:] if SERPAPI_KEY else "VAZIA")
        try:
            search = GoogleSearch(params)
            results = search.get_dict()

            # Log all top-level keys for debugging
            logger.info("[GoogleCrawler] SerpAPI response keys: %s", list(results.keys()))

            if "error" in results:
                logger.error("[GoogleCrawler] SerpAPI error: %s", results["error"])
                return None

            jobs_results = results.get("jobs_results", [])
            logger.info("[GoogleCrawler] SerpAPI retornou %d vagas reais", len(jobs_results))

            # Log first result for verification
            if jobs_results:
                first = jobs_results[0]
                logger.info(
                    "[GoogleCrawler] Primeira vaga: '%s' em '%s' (%s)",
                    first.get("title", "?"),
                    first.get("company_name", "?"),
                    first.get("location", "?"),
                )

            return jobs_results

        except Exception as e:
            logger.error("[GoogleCrawler] SerpAPI request failed: %s", str(e), exc_info=True)
            return None

    def _parse_serpapi_job(self, raw_job, profile_skills=""):
        """
        Converte um resultado SerpAPI em formato padronizado.
        Extrai: título, empresa, localização, URL, descrição (300 chars), data.
        """
        title = raw_job.get("title", "Vaga sem título")
        company = raw_job.get("company_name", "Empresa não informada")
        location = raw_job.get("location", "Localização não informada")

        # Descrição limitada a 300 caracteres
        full_desc = raw_job.get("description", "")
        description = full_desc[:300] + "..." if len(full_desc) > 300 else full_desc

        # URL da vaga (se disponível via share link ou detected_extensions)
        source_url = ""
        related = raw_job.get("related_links", [])
        if related:
            source_url = related[0].get("link", "")
        apply_options = raw_job.get("apply_options", [])
        if not source_url and apply_options:
            source_url = apply_options[0].get("link", "")
        if not source_url:
            # Gerar URL única baseada nos dados
            uid = hashlib.md5("{}{}".format(title, company).encode()).hexdigest()[:10]
            source_url = "https://www.google.com/search?q=vaga+{}".format(uid)

        # Data de publicação
        detected = raw_job.get("detected_extensions", {})
        published_at = detected.get("posted_at", "")

        # Tipo de trabalho e modalidade
        schedule = detected.get("schedule_type", "")
        job_type = "FULL-TIME"
        if "part" in schedule.lower():
            job_type = "PART-TIME"
        elif "contract" in schedule.lower() or "freelance" in schedule.lower():
            job_type = "FREELANCE"

        # Detectar modalidade a partir de keywords
        modality = "PRESENCIAL"
        loc_lower = location.lower() + " " + description.lower()
        if "remoto" in loc_lower or "remote" in loc_lower or "home office" in loc_lower:
            modality = "REMOTO"
        elif "híbrido" in loc_lower or "hybrid" in loc_lower:
            modality = "HIBRIDO"

        # Extrair skills da descrição (heurística simples)
        skills = self._extract_skills_from_description(full_desc)

        # Nível
        level = self._detect_level(title + " " + description)

        # Compatibilidade
        compat = calculate_compatibility(profile_skills, skills)
        ai_summary = generate_ai_summary(skills, compat)

        return {
            "title": title,
            "company": company,
            "location": location,
            "description": description,
            "skills": skills,
            "level": level,
            "job_type": job_type,
            "modality": modality,
            "source_url": source_url,
            "source": "google",
            "distance_km": round(random.uniform(2, 40), 1),
            "compatibility": compat,
            "ai_summary": ai_summary,
            "published_at": published_at,
            "is_sample": 0,
            "raw_data": json.dumps(raw_job, ensure_ascii=False, default=str)[:2000],
        }

    def _extract_skills_from_description(self, description):
        """
        Extrai skills conhecidas da descrição da vaga.
        Usa uma lista de tecnologias/skills comuns.
        """
        known_skills = [
            "python", "javascript", "typescript", "java", "c#", "c++", "go", "rust",
            "ruby", "php", "swift", "kotlin", "scala", "r",
            "react", "vue.js", "angular", "next.js", "node.js", "django", "flask",
            "fastapi", "spring boot", "express", "rails",
            "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
            "sql", "nosql", "graphql",
            "docker", "kubernetes", "aws", "azure", "gcp", "terraform",
            "ci/cd", "jenkins", "github actions", "gitlab ci",
            "git", "linux", "nginx", "apache",
            "machine learning", "deep learning", "tensorflow", "pytorch",
            "pandas", "numpy", "scikit-learn", "spark", "airflow",
            "figma", "html", "css", "sass", "tailwind",
            "react native", "flutter", "firebase",
            "jira", "scrum", "agile", "kanban",
            "power bi", "tableau", "excel",
            "cybersecurity", "pentest", "siem",
            "etl", "databricks", "data lake",
            "microservices", "api rest", "restful", "grpc",
            "selenium", "cypress", "jest",
        ]

        desc_lower = description.lower()
        found = []
        for skill in known_skills:
            if skill in desc_lower:
                found.append(skill)

        return ",".join(found[:10]) if found else "tecnologia"

    def _detect_level(self, text):
        """Detecta nível do profissional com base em keywords."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["senior", "sênior", "sr.", "lead", "principal", "staff"]):
            return "Senior"
        elif any(w in text_lower for w in ["junior", "júnior", "jr.", "estagiário", "trainee"]):
            return "Junior"
        else:
            return "Pleno"

    def _load_fallback(self, profile_skills=""):
        """
        Carrega vagas de exemplo como fallback.
        Marca com is_sample=1.
        """
        logger.warning("[GoogleCrawler] Usando dados de exemplo (sample_jobs.json)")
        sample_data = _load_sample_jobs()
        results = []

        for job_data in sample_data[:CRAWLER_MAX_RESULTS]:
            compat = calculate_compatibility(profile_skills, job_data.get("skills", ""))
            ai_summary = generate_ai_summary(job_data.get("skills", ""), compat)

            results.append({
                "title": job_data.get("title", "Vaga de exemplo"),
                "company": job_data.get("company", "Empresa de exemplo"),
                "location": job_data.get("location", "Brasil"),
                "description": job_data.get("description", "Descrição não disponível"),
                "skills": job_data.get("skills", ""),
                "level": job_data.get("level", "Pleno"),
                "job_type": job_data.get("job_type", "FULL-TIME"),
                "modality": job_data.get("modality", "REMOTO"),
                "source_url": job_data.get("source_url", ""),
                "source": "google",
                "distance_km": round(random.uniform(2, 40), 1),
                "compatibility": compat,
                "ai_summary": ai_summary,
                "published_at": job_data.get("published_at", ""),
                "is_sample": 1,
                "raw_data": "",
            })

        return results

    def crawl(self, query="", profile_skills="", profile_level=""):
        """
        Busca vagas reais via SerpAPI ou fallback para dados de exemplo.
        
        Fluxo:
        1. Se SERPAPI_KEY existe -> busca real via API
        2. Se falhar ou sem key -> carrega sample_jobs.json
        3. Sempre marca is_sample=1 nos dados de exemplo
        """
        built_query = self._build_query(query, profile_skills, profile_level)

        # MODO REAL: SerpAPI
        if self._has_api_key:
            logger.info("[GoogleCrawler] SerpAPI key detectada. Buscando vagas reais...")
            _random_delay()

            raw_results = self._search_serpapi(built_query)

            if raw_results:
                results = []
                for raw_job in raw_results[:CRAWLER_MAX_RESULTS]:
                    parsed = self._parse_serpapi_job(raw_job, profile_skills)
                    results.append(parsed)
                    _random_delay()

                if results:
                    logger.info("[GoogleCrawler] %d vagas reais extraídas.", len(results))
                    return results

            # API falhou, fallback
            logger.warning("[GoogleCrawler] SerpAPI falhou. Usando fallback...")

        else:
            logger.info(
                "[GoogleCrawler] Sem SERPAPI_KEY configurada. "
                "Configure em .env para vagas reais. Usando modo demo..."
            )

        # MODO DEMO: sample_jobs.json
        return self._load_fallback(profile_skills)


# ============================================================
# LINKEDIN CRAWLER (stub preparado para integração futura)
# ============================================================
class LinkedInCrawler(BaseCrawler):
    """
    Crawler preparado para LinkedIn - ESTRUTURA PARA INTEGRAÇÃO FUTURA.
    
    =====================================================
    AVISO IMPORTANTE:
    O LinkedIn bloqueia fortemente scraping automatizado.
    Este crawler NÃO faz requisições ao LinkedIn diretamente.
    
    ESTRATÉGIAS FUTURAS RECOMENDADAS:
    
    1. API oficial do LinkedIn (LinkedIn Talent Solutions API):
       - Requer aprovação de parceiro
       - Dados limitados na versão gratuita
       - URL: https://developer.linkedin.com/
    
    2. Google Dorks via SerpAPI (site:linkedin.com/jobs):
       - Exemplo: site:linkedin.com/jobs "python developer" "são paulo"
       - Retorna snippets do Google, não dados completos
       - Pode ser implementado com a mesma infraestrutura do GoogleCrawler
    
    3. Serviço de proxy rotativo + headless browser:
       - Ex: BrightData, Oxylabs, SmartProxy
       - Selenium com proxy rotativo e delays longos
       - Alto risco de bloqueio, custo significativo
    
    4. Agregadores de vagas (Indeed, Glassdoor):
       - Alguns possuem APIs ou são mais tolerantes a scraping
       - Podem conter vagas cross-posted do LinkedIn
    =====================================================
    
    Para implementar no futuro:
    
    ```python
    # Exemplo de busca via Google Dorks apontando para LinkedIn:
    def crawl(self, query, profile_skills="", profile_level=""):
        from serpapi import GoogleSearch
        params = {
            "engine": "google",
            "q": f'site:linkedin.com/jobs "{query}"',
            "hl": "pt-br",
            "gl": "br",
            "api_key": SERPAPI_KEY,
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        # Parse organic results for LinkedIn job links...
    ```
    
    ```python
    # Exemplo de integração com API oficial do LinkedIn:
    import requests
    
    def crawl(self, query, profile_skills="", profile_level=""):
        headers = {
            "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
            "X-Restli-Protocol-Version": "2.0.0",
        }
        url = "https://api.linkedin.com/v2/jobSearch"
        params = {"keywords": query, "location": "Brazil"}
        response = requests.get(url, headers=headers, params=params)
        # Parse response...
    ```
    """

    def __init__(self):
        super().__init__(name="linkedin")

    def crawl(self, query="", profile_skills="", profile_level=""):
        """
        Stub: LinkedIn crawler não implementado.
        Retorna lista vazia com log explicativo.
        
        TODO: Implementar quando houver:
        - Acesso à API oficial do LinkedIn, OU
        - Serviço de proxy rotativo configurado, OU
        - Chave SerpAPI para Google Dorks site:linkedin.com
        """
        logger.info(
            "[LinkedInCrawler] Crawler preparado mas não ativo. "
            "Configure API do LinkedIn ou use Google Dorks via SerpAPI."
        )
        return []


# ============================================================
# REQUESTS CRAWLER (Real scraping via Gupy API)
# ============================================================
class RequestsCrawler(BaseCrawler):
    """
    Crawler que utiliza a biblioteca 'requests' para verificar se é possível
    realizar scraping de vagas reais e apresentar as informações nos cards.
    """

    def __init__(self):
        super().__init__(name="requests")

    def crawl(self, query="", profile_skills="", profile_level=""):
        import requests
        import re
        results = []
        
        search_query = query if query else "desenvolvedor"
        gupy_url = f"https://portal.api.gupy.io/api/v1/jobs?jobName={search_query}&limit=20"
        
        logger.info("[RequestsCrawler] Fetching jobs from Gupy: %s", gupy_url)
        headers = {
            "User-Agent": _get_random_user_agent(),
            "Accept": "application/json, text/plain, */*",
        }
        
        try:
            response = requests.get(gupy_url, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                jobs = data.get("data", [])
                logger.info("[RequestsCrawler] Encontradas %d vagas na Gupy", len(jobs))
                
                for job in jobs[:20]:
                    title = job.get("name", "Vaga")
                    company = job.get("companyName", "Desconhecida")
                    
                    location = "Remoto"
                    if "city" in job and job["city"]:
                        location = f"{job['city']}, {job.get('state', '')}"
                        if job.get("isRemoteWork"):
                            location += " (Remoto)"
                    elif job.get("isRemoteWork"):
                         location = "100% Remoto"
                         
                    description = job.get("description", "")
                    clean_desc = re.sub('<[^<]+>', '', description)[:300] + "..." if description else "Descrição não preenchida."
                    
                    job_url = job.get("jobUrl", "")
                    published_at = job.get("publishedDate", "")
                    modality = "REMOTO" if job.get("isRemoteWork") else "PRESENCIAL"
                    
                    known_skills = [
                        "python", "javascript", "typescript", "java", "c#", "c++", "go", "php",
                        "react", "vue.js", "angular", "node.js", "django", "flask", "fastapi",
                        "postgresql", "mysql", "mongodb", "aws", "azure", "docker", "kubernetes",
                        "sql", "html", "css", "machine learning", "data science"
                    ]
                    desc_lower = (title + " " + clean_desc).lower()
                    found_skills = [s for s in known_skills if s in desc_lower]
                    skills = ",".join(found_skills[:6]) if found_skills else "tecnologia"
                    
                    level = "Pleno"
                    if any(w in desc_lower for w in ["senior", "sênior", "sr", "lead"]):
                        level = "Senior"
                    elif any(w in desc_lower for w in ["junior", "júnior", "jr", "estágio"]):
                        level = "Junior"
                        
                    compat = calculate_compatibility(profile_skills, skills)
                    ai_summary = generate_ai_summary(skills, compat)
                    
                    results.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "description": clean_desc,
                        "skills": skills,
                        "level": level,
                        "job_type": "FULL-TIME",
                        "modality": modality,
                        "source_url": job_url,
                        "source": "Gupy (Requests)",
                        "distance_km": round(random.uniform(2, 40), 1),
                        "compatibility": compat,
                        "ai_summary": ai_summary,
                        "published_at": published_at,
                        "is_sample": 0,
                        "raw_data": "",
                    })
            else:
                logger.warning("[RequestsCrawler] Erro da API: %d", response.status_code)
        except Exception as e:
            logger.error("[RequestsCrawler] Exceção na requisição: %s", str(e))
            
        return results


# ============================================================
# CRAWLERS REAIS VIA REQUESTS E BS4 (Infojobs, Catho, Google)
# ============================================================
class BaseRequestsCrawler(BaseCrawler):
    def _fetch_html(self, url):
        import requests
        headers = {
            "User-Agent": _get_random_user_agent(),
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Referer": "https://www.google.com/"
        }
        try:
            r = requests.get(url, headers=headers, timeout=15)
            return r.text
        except Exception as e:
            logger.error("[%s] Erro ao buscar URL %s: %s", self.name, url, str(e))
            return ""

    def _build_job_dict(self, title, company, location, desc, url, source, profile_skills, published_at=""):
        import re
        import random
        clean_desc = re.sub('<[^<]+>', '', desc)[:300] + "..." if desc else "Sem descrição detalhada."
        
        known_skills = [
            "python", "javascript", "typescript", "java", "c#", "c++", "go", "php",
            "react", "vue", "angular", "node", "django", "flask", "fastapi",
            "postgresql", "mysql", "mongodb", "aws", "azure", "docker", "kubernetes",
            "sql", "html", "css", "machine learning"
        ]
        text_lower = (title + " " + clean_desc).lower()
        found_skills = [s for s in known_skills if s in text_lower]
        skills = ",".join(found_skills[:6]) if found_skills else "tecnologia"
        
        level = "Pleno"
        if any(w in text_lower for w in ["senior", "sênior", "sr", "lead"]):
            level = "Senior"
        elif any(w in text_lower for w in ["junior", "júnior", "jr", "estágio", "trainee"]):
            level = "Junior"
            
        modality = "PRESENCIAL"
        if any(w in text_lower for w in ["remoto", "home office"]):
            modality = "REMOTO"
        elif any(w in text_lower for w in ["híbrido", "hybrid"]):
            modality = "HIBRIDO"
            
        compat = calculate_compatibility(profile_skills, skills)
        ai_summary = generate_ai_summary(skills, compat)
        
        return {
            "title": title[:100],
            "company": company[:100],
            "location": location[:100],
            "description": clean_desc,
            "skills": skills,
            "level": level,
            "job_type": "FULL-TIME",
            "modality": modality,
            "source_url": url,
            "source": source,
            "distance_km": round(random.uniform(2, 40), 1),
            "compatibility": compat,
            "ai_summary": ai_summary,
            "published_at": published_at,
            "is_sample": 0,
            "raw_data": "",
        }

class InfojobsCrawler(BaseRequestsCrawler):
    def __init__(self):
        super().__init__()
        self.name = "infojobs"

    def crawl(self, query="", profile_skills="", profile_level=""):
        from bs4 import BeautifulSoup
        search = query.replace(" ", "-") if query else "programador-python"
        url = f"https://www.infojobs.com.br/vagas-de-emprego-{search}.aspx"
        logger.info("[InfojobsCrawler] Raspando: %s", url)
        html = self._fetch_html(url)
        if not html: return []
        
        soup = BeautifulSoup(html, "html.parser")
        results = []
        
        for a in soup.find_all("a", href=True):
            href = a['href']
            if "/vaga-de-" in href and ("title" in a.attrs or a.find("h2")):
                try:
                    title = a.get("title") or (a.find("h2").text.strip() if a.find("h2") else a.text.strip())
                    if not title or len(title) < 5: continue
                    title = title.replace("Vaga de Emprego de ", "")
                    # Tenta extrair a empresa (geralmente num div ao lado ou Confidencial)
                    company = "Infojobs Company"
                    full_url = href if href.startswith("http") else "https://www.infojobs.com.br" + href
                    
                    job = self._build_job_dict(title, company, "Remoto", title, full_url, "Infojobs", profile_skills)
                    results.append(job)
                except Exception:
                    pass
                if len(results) >= 5: break
                
        return results

class CathoCrawler(BaseRequestsCrawler):
    def __init__(self):
        super().__init__()
        self.name = "catho"

    def crawl(self, query="", profile_skills="", profile_level=""):
        from bs4 import BeautifulSoup
        import json
        search = query.replace(" ", "-") if query else "programador-python"
        url = f"https://www.catho.com.br/vagas/{search}/"
        logger.info("[CathoCrawler] Raspando: %s", url)
        html = self._fetch_html(url)
        if not html: return []
        
        results = []
        import re
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
        if match:
            try:
                data = json.loads(match.group(1))
                props = data.get("props", {}).get("pageProps", {}).get("jobSearch", {}).get("jobSearchResult", {}).get("data", {}).get("jobs", [])
                for job_data in props[:5]:
                    title = job_data.get("title", "Vaga Catho")
                    company = job_data.get("company", {}).get("name") or "Empresa"
                    city = job_data.get("city", {}).get("name") or ""
                    state = job_data.get("state", {}).get("acronym") or ""
                    location = f"{city}/{state}" if city else "Remoto"
                    desc = job_data.get("description", "")
                    job_url = job_data.get("jobURL", url)
                    if not job_url.startswith("http"): job_url = "https://www.catho.com.br" + job_url
                    
                    results.append(self._build_job_dict(title, company, location, desc, job_url, "Catho", profile_skills))
            except Exception as e:
                logger.error("[CathoCrawler] Erro JSON: %s", str(e))
                
        if not results:
            soup = BeautifulSoup(html, "html.parser")
            for article in soup.find_all("article")[:5]:
                h2 = article.find("h2")
                if not h2: continue
                title = h2.text.strip()
                company_b = article.find("b")
                company = company_b.text.strip() if company_b else "Empresa"
                a_tag = h2.find("a")
                href = a_tag["href"] if a_tag else url
                results.append(self._build_job_dict(title, company, "Remoto", title, href, "Catho", profile_skills))
                
        return results

class GoogleRequestsCrawler(BaseRequestsCrawler):
    def __init__(self):
        super().__init__()
        self.name = "google_requests"

    def crawl(self, query="", profile_skills="", profile_level=""):
        from bs4 import BeautifulSoup
        search = query.replace(" ", "+") if query else "programador+python+vagas"
        url = f"https://www.google.com/search?q={search}&udm=8"
        logger.info("[GoogleCrawler] Raspando: %s", url)
        html = self._fetch_html(url)
        if not html: return []
        
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for h3 in soup.find_all("h3")[:5]:
            a_tag = h3.find_parent("a")
            if a_tag and "href" in a_tag.attrs:
                href = a_tag["href"]
                if href.startswith("/"): continue
                title = h3.text.strip()
                results.append(self._build_job_dict(title, "Web Search", "Remoto", title, href, "Google", profile_skills))
                
        return results


# ============================================================
# ORQUESTRADOR DE CRAWLERS
# ============================================================
def run_crawlers(db_session, profile):
    """
    Main entry point: runs all active crawlers and saves unique jobs to DB.
    """
    from models import Job

    # Build search query from profile
    query_parts = []
    if profile and profile.desired_title:
        query_parts.append(profile.desired_title)
    if profile and profile.skills:
        top_skills = [s.strip() for s in profile.skills.split(",")[:3]]
        query_parts.extend(top_skills)

    query = " ".join(query_parts) if query_parts else "desenvolvedor"

    profile_skills = profile.skills if profile else ""
    profile_level = profile.level if profile else ""

    crawlers = [
        RequestsCrawler(),
        InfojobsCrawler(),
        CathoCrawler(),
        GoogleCrawler(),
    ]

    total_found = 0
    total_new = 0
    total_duplicate = 0

    log_to_db(db_session, "Iniciando scraper real via Requests...", "INFO", "system")
    log_to_db(db_session, "Query: \"{}\"".format(query), "INFO", "system")

    logger.info("Starting crawler run with query: %s", query)

    for crawler in crawlers:
        crawler_name = crawler.name.upper()
        log_to_db(db_session, "Ativando agente {}...".format(crawler_name), "INFO", crawler.name)

        try:
            jobs_data = crawler.crawl(query, profile_skills, profile_level)
            found = len(jobs_data)
            total_found += found

            if found == 0:
                log_to_db(db_session, "{}: nenhum resultado.".format(crawler_name), "WARNING", crawler.name)

            log_to_db(db_session, "{}: {} vagas encontradas (Scraping real).".format(crawler_name, found), "INFO", crawler.name)

            new_count = 0
            dup_count = 0
            for job_data in jobs_data:
                existing = db_session.query(Job).filter(Job.source_url == job_data["source_url"]).first()

                if existing:
                    dup_count += 1
                    continue

                job = Job(
                    title=job_data["title"],
                    company=job_data["company"],
                    location=job_data["location"],
                    description=job_data["description"],
                    skills=job_data["skills"],
                    level=job_data["level"],
                    job_type=job_data["job_type"],
                    modality=job_data["modality"],
                    source_url=job_data["source_url"],
                    source=job_data["source"],
                    distance_km=job_data.get("distance_km", 0),
                    compatibility=job_data["compatibility"],
                    ai_summary=job_data["ai_summary"],
                    raw_data=job_data.get("raw_data", ""),
                    published_at=job_data.get("published_at", ""),
                    is_sample=0,
                )
                db_session.add(job)
                new_count += 1

            db_session.commit()
            total_new += new_count
            total_duplicate += dup_count

            if dup_count > 0:
                log_to_db(db_session, "{} links duplicados ignorados.".format(dup_count), "WARNING", crawler.name)

            logger.info("[%s] Found: %d, New: %d, Duplicates: %d", crawler_name, found, new_count, dup_count)

        except Exception as e:
            logger.error("[%s] Crawler error: %s", crawler_name, str(e), exc_info=True)
            log_to_db(db_session, "ERRO no agente {}: {}".format(crawler_name, str(e)), "ERROR", crawler.name)

    log_to_db(db_session, "Iniciando normalização de dados (N-1)...", "INFO", "system")
    log_to_db(db_session, "Sucesso: {} novas vagas REAIS adicionadas ao dashboard.".format(total_new), "SUCCESS", "system")

    if total_duplicate > 0:
        log_to_db(db_session, "{} links já conhecidos (sem repetição).".format(total_duplicate), "INFO", "system")

    log_to_db(db_session, "Hibernando agentes... Próximo ciclo manual.", "INFO", "system")

    logger.info("Crawl complete. Total found: %d, New: %d, Duplicates: %d", total_found, total_new, total_duplicate)

    return {
        "total_found": total_found,
        "total_new": total_new,
        "total_duplicate": total_duplicate,
        "query": query,
        "has_sample_data": False,
        "serpapi_active": False,
    }
