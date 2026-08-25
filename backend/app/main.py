"""FastAPI app for the Autonomous Career Advisor."""
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import PyPDF2
import io

from .config import get_settings
from .core.graph import run_advisor
from .core.vectorstore import warm_up
from .providers import get_job_provider
from .db import database, models, crud, auth
from .db.database import engine, run_migrations
from pydantic import BaseModel

from .schemas import AdviseRequest, AdvisorResult, UserCreate, Token

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("advisor")


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=database.engine)
    run_migrations(engine)
    counts = warm_up()
    log.info("vector store ready: %s", counts)
    if not get_settings().llm_available:
        log.warning("LLM unavailable — agents will run in deterministic fallback mode.")
    yield


app = FastAPI(title="Autonomous Career Advisor", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/api/health")
def health():
    s = get_settings()
    return {
        "status": "ok",
        "llm_available": s.llm_available,
        "job_provider": s.job_provider,
        "collections": warm_up(),
    }


@app.get("/api/roles")
def roles():
    return {"roles": get_job_provider().available_roles()}


@app.post("/api/advise", response_model=AdvisorResult)
def advise(request: AdviseRequest, token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)), db: Session = Depends(get_db)):
    if not request.resume_text.strip():
        raise HTTPException(422, "resume_text must not be empty")
    if not request.target_role.strip():
        raise HTTPException(422, "target_role must not be empty")
    try:
        result = run_advisor(request)
        if token and result.path:
            user = get_current_user(token, db)
            journey = crud.create_learning_journey(db, user.id, result.path.target_role)
            crud.create_path_steps(db, journey.id, result.path.steps)
        return result
    except ValueError as e:  # e.g. unknown role
        raise HTTPException(400, str(e))


@app.post("/api/extract_pdf")
async def extract_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "File must be a PDF")
    
    try:
        content = await file.read()
        import pdfplumber
        text = ""
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        
        # If still empty, it might be an image-only PDF
        if not text.strip():
            raise ValueError("No text could be extracted from this PDF. It might be an image-only scan.")
            
        return {"text": text.strip()}
    except Exception as e:
        log.error("Failed to parse PDF: %s", e)
        raise HTTPException(500, f"Error parsing PDF: {str(e)}")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

@app.post("/api/auth/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = crud.create_user(db=db, user=user.model_dump())
    access_token = auth.create_access_token(data={"sub": new_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        import jwt
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    user = crud.get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user

@app.get("/api/tracker/journeys")
def get_journeys(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    from sqlalchemy.orm import joinedload
    journeys = db.query(models.LearningJourney).options(joinedload(models.LearningJourney.steps)).filter(models.LearningJourney.user_id == current_user.id).order_by(models.LearningJourney.created_at.desc()).all()
    
    evidence_by_skill = crud.get_github_evidence_by_skill(db, current_user.id)

    result = []
    for j in journeys:
        import json
        j_dict = {
            "id": j.id,
            "target_role": j.target_role,
            "created_at": j.created_at.isoformat(),
            "steps": [
                {
                    "id": s.id,
                    "order": s.order,
                    "skill_id": s.skill_id,
                    "skill_name": s.skill_name,
                    "objective": s.objective,
                    "milestone": s.milestone,
                    "estimated_weeks": s.estimated_weeks,
                    "status": s.status,
                    "quiz_score": s.quiz_score,
                    "confidence_rating": s.confidence_rating,
                    "time_spent_minutes": s.time_spent_minutes,
                    "resources": json.loads(s.resources_json) if s.resources_json else [],
                    "github_evidence": [
                        {"repo_name": e.repo_name, "last_pushed_at":
                         e.last_pushed_at.isoformat() if hasattr(e.last_pushed_at, "isoformat") else e.last_pushed_at}
                        for e in evidence_by_skill.get(s.skill_id, [])
                    ],
                } for s in sorted(j.steps, key=lambda x: x.order)
            ]
        }
        result.append(j_dict)
    return result

class ProgressUpdate(BaseModel):
    quiz_score: int | None = None
    confidence_rating: int | None = None
    minutes_delta: int = 0

@app.post("/api/tracker/step/{step_id}/progress")
def record_progress(step_id: int, update: ProgressUpdate, db: Session = Depends(get_db),
                    current_user: models.User = Depends(get_current_user)):
    if update.confidence_rating is not None and not (1 <= update.confidence_rating <= 5):
        raise HTTPException(400, "confidence_rating must be 1-5")
    if update.quiz_score is not None and not (0 <= update.quiz_score <= 100):
        raise HTTPException(400, "quiz_score must be 0-100")
    step = crud.record_step_progress(
        db, step_id, quiz_score=update.quiz_score,
        confidence_rating=update.confidence_rating, minutes_delta=update.minutes_delta)
    if not step:
        raise HTTPException(404, "Step not found")
    return {"id": step.id, "status": step.status, "skill_name": step.skill_name,
           "quiz_score": step.quiz_score, "confidence_rating": step.confidence_rating,
           "time_spent_minutes": step.time_spent_minutes}


@app.post("/api/tracker/step/{step_id}/quiz")
def get_step_quiz(step_id: int, db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_user)):
    from .agents.quiz_agent import generate_quiz
    step = db.query(models.PathStep).filter(models.PathStep.id == step_id).first()
    if not step:
        raise HTTPException(404, "Step not found")
    questions = generate_quiz(step.skill_name, step.objective)
    if not questions:
        raise HTTPException(502, "Could not generate a quiz for this step right now")
    return {"questions": questions}


class GithubSyncRequest(BaseModel):
    username: str

@app.post("/api/github/sync")
def sync_github(req: GithubSyncRequest, db: Session = Depends(get_db),
                current_user: models.User = Depends(get_current_user)):
    from .providers.github import GithubRateLimited, GithubUserNotFound, fetch_repo_languages
    from .core.taxonomy import match_mention

    try:
        languages = fetch_repo_languages(req.username)
    except GithubUserNotFound:
        raise HTTPException(404, f"GitHub user '{req.username}' not found")
    except GithubRateLimited as e:
        raise HTTPException(429, str(e))

    current_user.github_username = req.username
    db.commit()

    evidence_rows = []
    for language, repos in languages.items():
        hit = match_mention(language)
        if not hit:
            continue
        skill_id = hit[0]
        for repo in repos:
            # GithubEvidence.last_pushed_at is a DateTime column; GitHub's API gives
            # an ISO-8601 string ("...Z"), so parse it here before handing off to crud.
            last_pushed_at = datetime.fromisoformat(repo["last_pushed_at"].replace("Z", "+00:00"))
            evidence_rows.append({
                "skill_id": skill_id, "repo_name": repo["repo_name"],
                "repo_language": language, "last_pushed_at": last_pushed_at,
            })
    crud.replace_github_evidence(db, current_user.id, evidence_rows)
    return {"matched_skills": sorted({r["skill_id"] for r in evidence_rows}),
           "evidence_count": len(evidence_rows)}
