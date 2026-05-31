import hashlib
import hmac
import math
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, desc, select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import AsyncSessionLocal, async_engine, get_db, init_db
from models import AdEvent, CandidateProfile, CompanyProfile, Job, Like, Match, Message, User


app = FastAPI(title="Jobs por AI", description="MVP de match profissional")
templates = Jinja2Templates(directory="templates")
SESSION_SECRET = os.getenv("SESSION_SECRET", "jobs-por-ai-dev-secret")

PLAN_LABELS = {
    "free": "Gratuito",
    "basic_semester": "Basico Semestral",
    "annual": "Anual",
    "premium_ai": "Premium IA",
}
PAID_PLANS = {"basic_semester", "annual", "premium_ai"}
FREE_DAILY_LIKES = 5


# ── Helpers ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000).hex()
        return hmac.compare_digest(candidate, digest)
    except ValueError:
        return False


def sign_user_id(user_id: int) -> str:
    value = str(user_id)
    sig = hmac.new(SESSION_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()
    return f"{value}.{sig}"


def read_session_user_id(request: Request):
    raw = request.cookies.get("jobs_session")
    if not raw or "." not in raw:
        return None
    value, sig = raw.split(".", 1)
    expected = hmac.new(SESSION_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        return int(value)
    except ValueError:
        return None


async def current_user(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = read_session_user_id(request)
    if not user_id:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def require_user(request: Request, db: AsyncSession = Depends(get_db)):
    return await current_user(request, db)


def render(request: Request, name: str, context: Optional[dict] = None):
    context = context or {}
    context["request"] = request
    return templates.TemplateResponse(name, context)


def redirect(path: str):
    return RedirectResponse(path, status_code=303)


def login_redirect(user: User):
    response = redirect("/")
    response.set_cookie("jobs_session", sign_user_id(user.id), httponly=True, samesite="lax")
    return response


def normalize_skills(skills: str):
    return [s.strip().lower() for s in (skills or "").split(",") if s.strip()]


def compatibility(candidate: CandidateProfile, job: Job) -> float:
    cskills = set(normalize_skills(candidate.skills))
    jskills = set(normalize_skills(job.skills))
    if not cskills or not jskills:
        return 0.35
    skill_score = len(cskills & jskills) / max(len(jskills), 1)
    level_score = 0.2 if (candidate.level or "").lower() == (job.level or "").lower() else 0
    return min(0.98, round(0.25 + skill_score * 0.6 + level_score, 2))


def distance_km(a_lat, a_lng, b_lat, b_lng):
    radius = 6371
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dlat = math.radians(b_lat - a_lat)
    dlng = math.radians(b_lng - a_lng)
    h = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
    return round(2 * radius * math.asin(math.sqrt(h)), 1)


def geocode_sp(address: str):
    text = (address or "").lower()
    points = [
        ("paulista", -23.5614, -46.6559),
        ("pinheiros", -23.5663, -46.7018),
        ("faria lima", -23.5777, -46.6860),
        ("berrini", -23.6086, -46.6962),
        ("santo amaro", -23.6547, -46.7107),
        ("tatuape", -23.5407, -46.5766),
        ("santana", -23.5025, -46.6244),
        ("vila olimpia", -23.5956, -46.6852),
        ("republica", -23.5448, -46.6427),
    ]
    for key, lat, lng in points:
        if key in text:
            return lat, lng
    return -23.5505, -46.6333


def plan_active(user: User):
    return user.plan in PAID_PLANS and (not user.plan_expires_at or user.plan_expires_at > datetime.utcnow())


async def can_like(user: User, db: AsyncSession):
    if plan_active(user):
        return True, None
    today = datetime.utcnow().date()
    start = datetime(today.year, today.month, today.day)
    result = await db.execute(
        select(sa_func.count(Like.id))
        .join(CandidateProfile)
        .where(
            CandidateProfile.user_id == user.id,
            Like.actor == "candidate",
            Like.created_at >= start,
        )
    )
    count = result.scalar() or 0
    if count >= FREE_DAILY_LIKES:
        return False, f"Limite gratuito de {FREE_DAILY_LIKES} likes diarios atingido."
    return True, None


async def ensure_match(db: AsyncSession, candidate_id: int, job: Job):
    result = await db.execute(
        select(Like).where(Like.candidate_id == candidate_id, Like.job_id == job.id, Like.actor == "candidate")
    )
    candidate_like = result.scalar_one_or_none()

    result = await db.execute(
        select(Like).where(Like.candidate_id == candidate_id, Like.job_id == job.id, Like.actor.in_(["company", "auto_agent"]))
    )
    company_like = result.scalar_one_or_none()

    if not candidate_like or not company_like:
        return None

    result = await db.execute(
        select(Match).where(Match.candidate_id == candidate_id, Match.job_id == job.id)
    )
    match = result.scalar_one_or_none()

    if not match:
        match = Match(candidate_id=candidate_id, company_id=job.company_id, job_id=job.id)
        db.add(match)
        await db.flush()
        db.add(Message(
            match_id=match.id,
            sender_id=job.company.user_id,
            body=f"Match liberado para a vaga {job.title}. Vamos conversar?"
        ))
    return match


async def run_premium_agent_for_job(db: AsyncSession, job: Job):
    result = await db.execute(
        select(CandidateProfile).join(User).where(User.plan == "premium_ai")
    )
    candidates = result.scalars().all()
    for candidate in candidates:
        if compatibility(candidate, job) >= 0.55:
            existing = await db.execute(
                select(Like).where(Like.candidate_id == candidate.id, Like.job_id == job.id, Like.actor == "candidate")
            )
            if not existing.scalar_one_or_none():
                db.add(Like(candidate_id=candidate.id, job_id=job.id, actor="candidate"))
            company_existing = await db.execute(
                select(Like).where(Like.candidate_id == candidate.id, Like.job_id == job.id, Like.actor == "company")
            )
            if not company_existing.scalar_one_or_none():
                db.add(Like(candidate_id=candidate.id, job_id=job.id, actor="company"))
            await db.flush()
            await ensure_match(db, candidate.id, job)


# ── Lifecycle ────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    await init_db()


# ── Auth Routes ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    user = await current_user(request, db)
    if not user:
        return redirect("/login")
    return redirect("/explorar" if user.role == "candidate" else "/empresa")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return render(request, "auth.html", {"mode": "login", "hide_nav": True})


@app.get("/cadastro", response_class=HTMLResponse)
async def register_page(request: Request):
    return render(request, "auth.html", {"mode": "register", "hide_nav": True})


@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == email.strip().lower()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return render(request, "auth.html", {"mode": "login", "error": "Email ou senha invalidos.", "hide_nav": True})
    return login_redirect(user)


@app.post("/cadastro")
async def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    company_name: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    email = email.strip().lower()
    if role not in ("candidate", "company"):
        return render(request, "auth.html", {"mode": "register", "error": "Perfil invalido.", "hide_nav": True})
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        return render(request, "auth.html", {"mode": "register", "error": "Email ja cadastrado.", "hide_nav": True})
    user = User(name=name, email=email, password_hash=hash_password(password), role=role)
    db.add(user)
    await db.flush()
    if role == "candidate":
        db.add(CandidateProfile(user_id=user.id, desired_title="", skills="", address="Sao Paulo, SP"))
    else:
        db.add(CompanyProfile(user_id=user.id, company_name=company_name or name, address="Sao Paulo, SP"))
    await db.commit()
    return login_redirect(user)


@app.get("/logout")
async def logout(request: Request):
    response = redirect("/login")
    response.delete_cookie("jobs_session")
    return response


# ── Profile ──────────────────────────────────────────────────────────────────

@app.get("/perfil", response_class=HTMLResponse)
async def profile_page(request: Request, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    if not user:
        return redirect("/login")
    return render(request, "profile.html", {
        "user": user,
        "plan_label": PLAN_LABELS.get(user.plan, user.plan),
        "active_page": "perfil",
    })


@app.post("/perfil")
async def save_profile(
    request: Request,
    desired_title: str = Form(""),
    skills: str = Form(""),
    level: str = Form("Junior"),
    address: str = Form(""),
    resume: str = Form(""),
    experience: str = Form(""),
    interest_area: str = Form(""),
    company_name: str = Form(""),
    description: str = Form(""),
    website: str = Form(""),
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    if not user:
        return redirect("/login")
    if user.role == "candidate":
        profile = user.candidate_profile
        lat, lng = geocode_sp(address)
        profile.desired_title = desired_title
        profile.skills = skills
        profile.level = level
        profile.address = address
        profile.latitude = lat
        profile.longitude = lng
        profile.resume = resume
        profile.experience = experience
        profile.interest_area = interest_area
    else:
        profile = user.company_profile
        profile.company_name = company_name
        profile.description = description
        profile.website = website
        profile.address = address
    await db.commit()
    return redirect("/perfil")


@app.post("/plano")
async def update_plan(plan: str = Form(...), user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    if not user:
        return redirect("/login")
    durations = {"free": 0, "basic_semester": 183, "annual": 365, "premium_ai": 183}
    if plan not in durations:
        return redirect("/perfil")
    user.plan = plan
    user.plan_expires_at = None if plan == "free" else datetime.utcnow() + timedelta(days=durations[plan])
    await db.commit()
    return redirect("/perfil")


# ── Explore (Candidate) ─────────────────────────────────────────────────────

@app.get("/explorar", response_class=HTMLResponse)
async def explore_page(request: Request, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    if not user:
        return redirect("/login")
    if user.role != "candidate":
        return redirect("/empresa")
    candidate = user.candidate_profile
    liked_q = select(Like.job_id).where(Like.candidate_id == candidate.id, Like.actor == "candidate")
    result = await db.execute(
        select(Job).where(Job.is_active == 1, ~Job.id.in_(liked_q)).order_by(desc(Job.created_at))
    )
    jobs = result.scalars().all()
    cards = []
    for job in jobs:
        cards.append({
            "job": {
                "id": job.id,
                "title": job.title,
                "location": job.location,
                "address": job.address,
                "description": job.description,
                "skills": job.skills,
                "level": job.level,
                "modality": job.modality,
                "salary": job.salary,
                "job_type": job.job_type,
                "latitude": job.latitude,
                "longitude": job.longitude,
                "company": {
                    "company_name": job.company.company_name if job.company else "Empresa Confidencial"
                }
            },
            "score": compatibility(candidate, job),
            "distance": distance_km(candidate.latitude, candidate.longitude, job.latitude, job.longitude),
        })
    show_ad = not plan_active(user) and secrets.randbelow(100) < 55
    if show_ad:
        db.add(AdEvent(user_id=user.id, placement="explorar", campaign="Plano Basico Semestral"))
        await db.commit()
    return render(request, "explore.html", {
        "user": user,
        "cards": cards,
        "show_ad": show_ad,
        "active_page": "explorar",
    })


@app.post("/vagas/{job_id}/like")
async def candidate_like(job_id: int, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    if not user or user.role != "candidate":
        return JSONResponse(status_code=403, content={"ok": False, "error": "Acesso negado"})
    ok, error = await can_like(user, db)
    if not ok:
        return JSONResponse(status_code=429, content={"ok": False, "error": error})
    result = await db.execute(select(Job).where(Job.id == job_id, Job.is_active == 1))
    job = result.scalar_one_or_none()
    if not job:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Vaga nao encontrada"})
    candidate = user.candidate_profile
    existing = await db.execute(
        select(Like).where(Like.candidate_id == candidate.id, Like.job_id == job.id, Like.actor == "candidate")
    )
    if not existing.scalar_one_or_none():
        db.add(Like(candidate_id=candidate.id, job_id=job.id, actor="candidate"))
    match = await ensure_match(db, candidate.id, job)
    await db.commit()
    return {"ok": True, "matched": bool(match), "match_id": match.id if match else None}


# ── Company ──────────────────────────────────────────────────────────────────

@app.get("/empresa", response_class=HTMLResponse)
async def company_page(request: Request, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    if not user:
        return redirect("/login")
    if user.role != "company":
        return redirect("/explorar")
    result = await db.execute(
        select(Job).where(Job.company_id == user.company_profile.id).order_by(desc(Job.created_at))
    )
    jobs = result.scalars().all()
    return render(request, "company.html", {
        "user": user,
        "jobs": jobs,
        "active_page": "empresa",
    })


@app.post("/empresa/vagas")
async def create_job(
    title: str = Form(...),
    description: str = Form(""),
    skills: str = Form(""),
    level: str = Form("Junior"),
    job_type: str = Form("CLT"),
    modality: str = Form("Presencial"),
    salary: str = Form(""),
    address: str = Form("Av. Paulista, 1000 - Sao Paulo, SP"),
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    if not user or user.role != "company":
        return redirect("/login")
    lat, lng = geocode_sp(address)
    job = Job(
        company_id=user.company_profile.id,
        title=title,
        description=description,
        skills=skills,
        level=level,
        job_type=job_type,
        modality=modality,
        salary=salary,
        location="Sao Paulo, SP",
        address=address,
        latitude=lat,
        longitude=lng,
    )
    db.add(job)
    await db.flush()
    await run_premium_agent_for_job(db, job)
    await db.commit()
    return redirect("/empresa")


@app.get("/api/empresa/{job_id}/candidatos")
async def api_company_candidates(job_id: int, request: Request, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    """API: returns candidates who liked a specific job, with compatibility and distance."""
    if not user or user.role != "company":
        return JSONResponse(status_code=403, content={"candidates": []})

    result = await db.execute(select(Job).where(Job.id == job_id, Job.company_id == user.company_profile.id))
    job = result.scalar_one_or_none()
    if not job:
        return JSONResponse(status_code=404, content={"candidates": []})

    # Find candidates who liked this job
    result = await db.execute(
        select(Like).where(Like.job_id == job_id, Like.actor == "candidate")
    )
    likes = result.scalars().all()

    candidates_data = []
    for like in likes:
        candidate = like.candidate
        # Check if company already liked this candidate for this job
        company_like_result = await db.execute(
            select(Like).where(Like.candidate_id == candidate.id, Like.job_id == job_id, Like.actor.in_(["company", "auto_agent"]))
        )
        company_liked = company_like_result.scalar_one_or_none() is not None

        # Check if match exists
        match_result = await db.execute(
            select(Match).where(Match.candidate_id == candidate.id, Match.job_id == job_id)
        )
        match = match_result.scalar_one_or_none()

        candidates_data.append({
            "id": candidate.id,
            "name": candidate.user.name,
            "initials": "".join(w[0].upper() for w in candidate.user.name.split()[:2]),
            "desired_title": candidate.desired_title,
            "skills": candidate.skills,
            "level": candidate.level,
            "resume": candidate.resume or "",
            "experience": candidate.experience or "",
            "address": candidate.address,
            "latitude": candidate.latitude,
            "longitude": candidate.longitude,
            "compatibility": compatibility(candidate, job),
            "distance": distance_km(candidate.latitude, candidate.longitude, job.latitude, job.longitude),
            "company_liked": company_liked,
            "matched": match is not None,
            "match_id": match.id if match else None,
        })

    candidates_data.sort(key=lambda c: c["compatibility"], reverse=True)
    return {"candidates": candidates_data, "job": {"title": job.title, "latitude": job.latitude, "longitude": job.longitude}}


@app.post("/api/empresa/like")
async def api_company_like(request: Request, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    """API: company likes a candidate for a job."""
    if not user or user.role != "company":
        return JSONResponse(status_code=403, content={"ok": False})
    data = await request.json()
    candidate_id = data.get("candidate_id")
    job_id = data.get("job_id")

    result = await db.execute(select(Job).where(Job.id == job_id, Job.company_id == user.company_profile.id))
    job = result.scalar_one_or_none()
    if not job:
        return JSONResponse(status_code=404, content={"ok": False})

    existing = await db.execute(
        select(Like).where(Like.candidate_id == candidate_id, Like.job_id == job_id, Like.actor == "company")
    )
    if not existing.scalar_one_or_none():
        db.add(Like(candidate_id=candidate_id, job_id=job_id, actor="company"))
        await db.flush()
        match = await ensure_match(db, candidate_id, job)
        await db.commit()
        return {"ok": True, "matched": bool(match), "match_id": match.id if match else None}
    return {"ok": True, "matched": False}


# ── Chat ─────────────────────────────────────────────────────────────────────

@app.get("/chats", response_class=HTMLResponse)
async def chats_page(request: Request, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    if not user:
        return redirect("/login")
    if user.role == "candidate":
        result = await db.execute(
            select(Match).where(Match.candidate_id == user.candidate_profile.id).order_by(desc(Match.created_at))
        )
    else:
        result = await db.execute(
            select(Match).where(Match.company_id == user.company_profile.id).order_by(desc(Match.created_at))
        )
    matches = result.scalars().all()
    active = matches[0] if matches else None
    return render(request, "chats.html", {"user": user, "matches": matches, "active": active, "active_page": "chats"})


@app.get("/chats/{match_id}", response_class=HTMLResponse)
async def chat_detail(match_id: int, request: Request, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    if not user:
        return redirect("/login")
    query = select(Match).where(Match.id == match_id)
    if user.role == "candidate":
        query = query.where(Match.candidate_id == user.candidate_profile.id)
        all_q = select(Match).where(Match.candidate_id == user.candidate_profile.id)
    else:
        query = query.where(Match.company_id == user.company_profile.id)
        all_q = select(Match).where(Match.company_id == user.company_profile.id)

    result = await db.execute(query)
    active = result.scalar_one_or_none()
    if not active:
        return redirect("/chats")

    result = await db.execute(all_q)
    matches = result.scalars().all()
    return render(request, "chats.html", {"user": user, "matches": matches, "active": active, "active_page": "chats"})


@app.post("/chats/{match_id}/mensagens")
async def send_message_form(match_id: int, body: str = Form(...), user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    """Form-based message send (fallback)."""
    if not user:
        return redirect("/login")
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    allowed = match and (
        (user.role == "candidate" and match.candidate.user_id == user.id)
        or (user.role == "company" and match.company.user_id == user.id)
    )
    if allowed and body.strip():
        db.add(Message(match_id=match.id, sender_id=user.id, body=body.strip()))
        await db.commit()
    return redirect(f"/chats/{match_id}")


@app.get("/api/chat/{match_id}")
async def chat_api(match_id: int, request: Request, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    """API: returns messages for a match. Supports ?after_id= for incremental polling."""
    if not user:
        return JSONResponse(status_code=401, content={"messages": []})
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    allowed = match and (
        (user.role == "candidate" and match.candidate.user_id == user.id)
        or (user.role == "company" and match.company.user_id == user.id)
    )
    if not allowed:
        return JSONResponse(status_code=403, content={"messages": []})

    after_id = request.query_params.get("after_id")
    query = select(Message).where(Message.match_id == match_id).order_by(Message.created_at)
    if after_id:
        try:
            query = query.where(Message.id > int(after_id))
        except ValueError:
            pass

    result = await db.execute(query)
    messages = result.scalars().all()
    return {
        "messages": [
            {
                "id": msg.id,
                "sender": msg.sender.name,
                "mine": msg.sender_id == user.id,
                "body": msg.body,
                "time": msg.created_at.strftime("%H:%M"),
            }
            for msg in messages
        ]
    }


@app.post("/api/chat/{match_id}/mensagens")
async def chat_api_send(match_id: int, request: Request, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    """API: send a message via JSON. Returns the new message. Idempotent: checks for duplicate body+sender within 5s."""
    if not user:
        return JSONResponse(status_code=401, content={"ok": False})
    data = await request.json()
    body = (data.get("body") or "").strip()
    if not body:
        return JSONResponse(status_code=400, content={"ok": False, "error": "Mensagem vazia"})

    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    allowed = match and (
        (user.role == "candidate" and match.candidate.user_id == user.id)
        or (user.role == "company" and match.company.user_id == user.id)
    )
    if not allowed:
        return JSONResponse(status_code=403, content={"ok": False})

    # Idempotency: check for duplicate message in the last 5 seconds
    five_seconds_ago = datetime.utcnow() - timedelta(seconds=5)
    dup_check = await db.execute(
        select(Message).where(
            Message.match_id == match_id,
            Message.sender_id == user.id,
            Message.body == body,
            Message.created_at >= five_seconds_ago,
        )
    )
    existing = dup_check.scalar_one_or_none()
    if existing:
        return {
            "ok": True,
            "duplicate": True,
            "message": {
                "id": existing.id,
                "sender": existing.sender.name,
                "mine": True,
                "body": existing.body,
                "time": existing.created_at.strftime("%H:%M"),
            },
        }

    msg = Message(match_id=match.id, sender_id=user.id, body=body)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return {
        "ok": True,
        "duplicate": False,
        "message": {
            "id": msg.id,
            "sender": user.name,
            "mine": True,
            "body": msg.body,
            "time": msg.created_at.strftime("%H:%M"),
        },
    }


# ── Dashboard ────────────────────────────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    if not user:
        return redirect("/login")
    users_count = (await db.execute(select(sa_func.count(User.id)))).scalar() or 0
    companies_count = (await db.execute(select(sa_func.count(User.id)).where(User.role == "company"))).scalar() or 0
    candidates_count = (await db.execute(select(sa_func.count(User.id)).where(User.role == "candidate"))).scalar() or 0
    jobs_count = (await db.execute(select(sa_func.count(Job.id)))).scalar() or 0
    matches_count = (await db.execute(select(sa_func.count(Match.id)))).scalar() or 0
    messages_count = (await db.execute(select(sa_func.count(Message.id)))).scalar() or 0
    ads_count = (await db.execute(select(sa_func.count(AdEvent.id)))).scalar() or 0
    stats = {
        "users": users_count,
        "companies": companies_count,
        "candidates": candidates_count,
        "jobs": jobs_count,
        "matches": matches_count,
        "messages": messages_count,
        "ads": ads_count,
    }
    return render(request, "dashboard_mvp.html", {"user": user, "stats": stats, "active_page": "dashboard"})


# ── Dev ──────────────────────────────────────────────────────────────────────

@app.post("/dev/reset")
async def dev_reset():
    async with async_engine.begin() as conn:
        from database import Base
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    return {"ok": True}


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
