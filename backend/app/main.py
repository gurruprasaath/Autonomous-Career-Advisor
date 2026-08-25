"""FastAPI app for the Autonomous Career Advisor."""
import logging
from contextlib import asynccontextmanager

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
                    "resources": json.loads(s.resources_json) if s.resources_json else []
                } for s in sorted(j.steps, key=lambda x: x.order)
            ]
        }
        result.append(j_dict)
    return result

@app.post("/api/tracker/step/{step_id}/status")
def update_step_status(step_id: int, status: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if status not in ["pending", "in_progress", "struggling", "completed"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    step = crud.update_step_status(db, step_id, status)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    
    import json
    return {
        "id": step.id,
        "status": step.status,
        "skill_name": step.skill_name
    }
