from datetime import datetime, timedelta

from database import Base, SyncSessionLocal, sync_engine
from app import geocode_sp, hash_password
from models import CandidateProfile, CompanyProfile, Job, Like, Match, Message, User


def reset(db):
    Base.metadata.drop_all(bind=sync_engine)
    Base.metadata.create_all(bind=sync_engine)


def user(db, name, email, role, plan="free"):
    expires = datetime.utcnow() + timedelta(days=183) if plan != "free" else None
    item = User(name=name, email=email, role=role, plan=plan, plan_expires_at=expires, password_hash=hash_password("123456"))
    db.add(item)
    db.flush()
    return item


def ensure_match_sync(db, candidate_id, job):
    # Check if both candidate and company liked
    candidate_like = db.query(Like).filter_by(candidate_id=candidate_id, job_id=job.id, actor="candidate").first()
    company_like = db.query(Like).filter(
        Like.candidate_id == candidate_id, 
        Like.job_id == job.id, 
        Like.actor.in_(["company", "auto_agent"])
    ).first()

    if not candidate_like or not company_like:
        return None

    match = db.query(Match).filter_by(candidate_id=candidate_id, job_id=job.id).first()
    if not match:
        match = Match(candidate_id=candidate_id, company_id=job.company_id, job_id=job.id)
        db.add(match)
        db.flush()
        db.add(Message(
            match_id=match.id,
            sender_id=job.company.user_id,
            body=f"Match liberado para a vaga {job.title}. Vamos conversar?"
        ))
        db.flush()
    return match


def main():
    db = SyncSessionLocal()
    reset(db)

    companies_seed = [
        ("Nexa Retail", "Produtos digitais para varejo", "Av. Paulista, 1000"),
        ("Orbital Health", "Tecnologia para clinicas e hospitais", "Rua Funchal, Vila Olimpia"),
        ("MetroData", "Dados e automacao para mobilidade", "Av. Berrini, 1500"),
        ("Casa Verde Bank", "Fintech de credito sustentavel", "Largo da Batata, Pinheiros"),
        ("Aster Cloud", "Consultoria cloud e seguranca", "Rua Vergueiro, 2000"),
    ]
    companies = []
    for i, (name, desc, address) in enumerate(companies_seed, start=1):
        u = user(db, f"Recrutador {name}", f"empresa{i}@demo.com", "company", "annual")
        c = CompanyProfile(user_id=u.id, company_name=name, description=desc, website=f"https://{name.lower().replace(' ', '')}.example", address=address)
        db.add(c)
        db.flush()
        companies.append(c)

    candidates_seed = [
        ("Ana Souza", "Desenvolvedora Python", "python, fastapi, sql, docker", "Pleno", "Av. Paulista, 900", "premium_ai"),
        ("Bruno Lima", "Analista de Dados", "sql, power bi, python, analytics", "Junior", "Republica, Sao Paulo", "free"),
        ("Carla Reis", "Product Designer", "figma, ux, ui, pesquisa", "Pleno", "Pinheiros, Sao Paulo", "basic_semester"),
        ("Diego Rocha", "DevOps Engineer", "aws, docker, kubernetes, terraform", "Senior", "Santana, Sao Paulo", "annual"),
        ("Erika Martins", "QA Automation", "selenium, cypress, python, testes", "Pleno", "Tatuape, Sao Paulo", "free"),
        ("Felipe Nunes", "Atendimento Operacional", "atendimento, excel, crm, comunicacao", "Junior", "Santo Amaro, Sao Paulo", "free"),
        ("Giovana Alves", "Frontend React", "react, typescript, css, ux", "Pleno", "Vila Olimpia, Sao Paulo", "premium_ai"),
        ("Heitor Gomes", "Cyber Security", "security, soc, linux, redes", "Junior", "Berrini, Sao Paulo", "free"),
        ("Isabela Costa", "Gerente de Projetos", "scrum, kanban, gestao, produto", "Senior", "Faria Lima, Sao Paulo", "annual"),
        ("Joao Pedro", "Backend Java", "java, spring, sql, microservicos", "Pleno", "Av. Paulista, Sao Paulo", "free"),
    ]
    candidates = []
    for i, (name, title, skills, level, address, plan) in enumerate(candidates_seed, start=1):
        u = user(db, name, f"candidato{i}@demo.com", "candidate", plan)
        lat, lng = geocode_sp(address)
        c = CandidateProfile(
            user_id=u.id,
            desired_title=title,
            skills=skills,
            level=level,
            address=address,
            latitude=lat,
            longitude=lng,
            resume=f"{name} atua como {title} com foco em entregas praticas e colaboracao.",
            experience="Experiencia em projetos digitais, times ageis e operacao local em Sao Paulo.",
            interest_area=title,
        )
        db.add(c)
        db.flush()
        candidates.append(c)

    jobs_seed = [
        (0, "Desenvolvedor Python FastAPI", "APIs, integrações e automacoes internas.", "python, fastapi, sql, docker", "Pleno", "Hibrido", "R$ 8.000", "Av. Paulista, 1000"),
        (0, "Frontend React Pleno", "Interfaces responsivas para o produto principal.", "react, typescript, css, ux", "Pleno", "Remoto", "R$ 7.500", "Pinheiros"),
        (1, "Analista de Dados Jr", "Dashboards operacionais e metricas de negocio.", "sql, power bi, python, analytics", "Junior", "Hibrido", "R$ 4.200", "Vila Olimpia"),
        (1, "QA Automation", "Automacao de testes web e APIs.", "selenium, cypress, python, testes", "Pleno", "Remoto", "R$ 6.500", "Berrini"),
        (2, "Engenheiro DevOps Senior", "Ambientes Kubernetes e observabilidade.", "aws, docker, kubernetes, terraform", "Senior", "Hibrido", "R$ 13.000", "Berrini"),
        (2, "Analista de Mobilidade", "Operacao, dados e relatorios de rotas.", "excel, sql, comunicacao, analytics", "Junior", "Presencial", "R$ 3.800", "Republica"),
        (3, "Backend Java Pleno", "Servicos financeiros em Spring.", "java, spring, sql, microservicos", "Pleno", "Hibrido", "R$ 9.000", "Faria Lima"),
        (3, "Product Designer", "Pesquisa, prototipos e design system.", "figma, ux, ui, pesquisa", "Pleno", "Hibrido", "R$ 8.200", "Pinheiros"),
        (4, "Analista SOC Junior", "Monitoramento de alertas e resposta inicial.", "security, soc, linux, redes", "Junior", "Presencial", "R$ 5.000", "Santana"),
        (4, "Gerente de Projetos Senior", "Conducao de projetos cloud enterprise.", "scrum, kanban, gestao, produto", "Senior", "Hibrido", "R$ 14.000", "Av. Paulista"),
    ]
    jobs = []
    for company_index, title, desc, skills, level, modality, salary, address in jobs_seed:
        lat, lng = geocode_sp(address)
        j = Job(
            company_id=companies[company_index].id,
            title=title,
            description=desc,
            skills=skills,
            level=level,
            modality=modality,
            salary=salary,
            job_type="CLT",
            location="Sao Paulo, SP",
            address=address,
            latitude=lat,
            longitude=lng,
        )
        db.add(j)
        db.flush()
        jobs.append(j)

    interactions = [(0, 0), (1, 2), (2, 7), (3, 4), (6, 1), (8, 9), (9, 6)]
    for candidate_index, job_index in interactions:
        candidate = candidates[candidate_index]
        job = jobs[job_index]
        db.add(Like(candidate_id=candidate.id, job_id=job.id, actor="candidate"))
        db.add(Like(candidate_id=candidate.id, job_id=job.id, actor="company"))
        db.flush()
        match = ensure_match_sync(db, candidate.id, job)
        if match:
            db.add(Message(match_id=match.id, sender_id=candidate.user_id, body="Ola! Tenho interesse nessa oportunidade."))
            db.add(Message(match_id=match.id, sender_id=job.company.user_id, body="Que bom! Podemos agendar uma conversa inicial?"))

    # Also add some partial likes (candidates who liked a job, but company didn't like back yet, to show up in the company dashboard)
    # Let's say candidates 4, 5, and 6 liked job 0 (Desenvolvedor Python FastAPI)
    for c_idx in [4, 5, 6]:
        db.add(Like(candidate_id=candidates[c_idx].id, job_id=jobs[0].id, actor="candidate"))
    
    # Candidate 2 liked job 0 but didn't get match
    db.add(Like(candidate_id=candidates[2].id, job_id=jobs[0].id, actor="candidate"))

    db.commit()
    print("Banco populado.")
    print("Login candidato: candidato1@demo.com / 123456")
    print("Login empresa: empresa1@demo.com / 123456")
    db.close()


if __name__ == "__main__":
    main()
