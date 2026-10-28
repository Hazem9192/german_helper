from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from fastapi.responses import FileResponse

# --- Database Setup (SQLite) ---
DATABASE_URL = "sqlite:///./germany_helper.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class GuideModel(Base):
    __tablename__ = "guides"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True)
    steps = Column(Text)  # Stored as text (steps joined by "||")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- FastAPI Initialization ---
app = FastAPI(
    title="German Bureaucracy Helper",
    description="Full-stack app with Database Guides and German Email Templates.",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Seed initial data on startup
def seed_initial_data(db: Session):
    if db.query(GuideModel).count() == 0:
        initial_guides = [
            ("Anmeldung (Register your address)", "Find an apartment and get the Wohnungsgeberbestätigung.||Book an appointment at the Bürgeramt.||Bring passport and rental contract.||Receive your Meldebescheinigung."),
            ("Steuer-ID (Tax identification number)", "Complete your Anmeldung first.||Wait 2-3 weeks for it to arrive by mail.||Give the number to your employer."),
            ("Krankenversicherung (Health insurance)", "Choose public (TK/AOK) or private insurance.||Apply online with your employment details.||Receive your health card by post."),
            ("Bankkonto (Bank account)", "Choose a bank (e.g., N26, Sparkasse).||Bring your passport and Meldebescheinigung.||Receive your IBAN."),
            ("Aufenthaltstitel (Residence permit)", "Book an appointment at the Ausländerbehörde.||Bring biometric photos, passport, and proof of income.||Collect your permit.")
        ]
        for title, steps in initial_guides:
            db.add(GuideModel(title=title, steps=steps))
        db.commit()

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    seed_initial_data(db)
    db.close()

# --- German Email Templates ---
TEMPLATES = {
    "anmeldung": {
        "subject": "Anfrage zu einem Termin für die Wohnsitzanmeldung",
        "body": (
            "ich ziehe demnächst in Ihren Zuständigkeitsbereich und möchte meinen "
            "Wohnsitz anmelden. Hierfür bitte ich Sie um die Vergabe eines Termins. "
            "Bitte teilen Sie mir außerdem mit, welche Unterlagen ich mitbringen muss."
        ),
    },
    "termin": {
        "subject": "Terminanfrage",
        "body": (
            "hiermit bitte ich Sie höflich um einen Termin in Ihrer Behörde. "
            "Bitte teilen Sie mir die nächstmöglichen Termine sowie die erforderlichen "
            "Unterlagen mit."
        ),
    },
    "kündigung": {
        "subject": "Kündigung meines Vertrags",
        "body": (
            "hiermit kündige ich meinen Vertrag fristgerecht zum nächstmöglichen "
            "Zeitpunkt. Bitte bestätigen Sie mir die Kündigung sowie das genaue "
            "Vertragsende schriftlich."
        ),
    },
    "widerspruch": {
        "subject": "Widerspruch gegen Ihren Bescheid",
        "body": (
            "hiermit lege ich fristgerecht Widerspruch gegen Ihren Bescheid ein. "
            "Eine ausführliche Begründung reiche ich nach. Bitte bestätigen Sie den "
            "Eingang meines Widerspruchs."
        ),
    },
}

# --- Pydantic Schemas ---
class EmailRequest(BaseModel):
    topic: str = Field(..., min_length=2, examples=["Anmeldung"])
    sender_name: str = Field("Max Mustermann", examples=["Max Mustermann"])
    recipient_name: Optional[str] = Field(None, description="e.g. 'Frau Schmidt'")
    details: Optional[str] = Field(None, description="Optional extra sentence.")

class EmailResponse(BaseModel):
    subject: str
    body: str

# --- Endpoints ---

@app.get("/")
def serve_frontend():
    """Serves the frontend index.html directly from the backend."""
    return FileResponse("index.html")

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/guides")

def get_guides(db: Session = Depends(get_db)):
    """Fetches all bureaucracy guides directly from the Database."""
    db_guides = db.query(GuideModel).all()
    result = []
    for g in db_guides:
        result.append({
            "id": g.id,
            "title": g.title,
            "steps": g.steps.split("||")
        })
    return {"count": len(result), "guides": result}

@app.post("/generate-email", response_model=EmailResponse)
def generate_email(req: EmailRequest):
    """Generates a formal German email draft using official templates."""
    topic = req.topic.strip().lower()
    
    # Search for a matching template
    template = next((t for key, t in TEMPLATES.items() if key in topic), None)
    if template is None:
        template = {
            "subject": f"Anfrage: {req.topic.strip()}",
            "body": (
                f"ich wende mich an Sie bezüglich des Themas „{req.topic.strip()}“. "
                "Ich würde mich freuen, wenn Sie mir weitere Informationen zum "
                "weiteren Vorgehen mitteilen könnten."
            ),
        }

    salutation = (
        "Sehr geehrte Damen und Herren,"
        if not req.recipient_name
        else f"Sehr geehrte/r {req.recipient_name},"
    )

    extra = f"\n\n{req.details.strip()}" if req.details else ""

    body = (
        f"{salutation}\n\n"
        f"{template['body']}{extra}\n\n"
        "Für Rückfragen stehe ich Ihnen gerne zur Verfügung.\n\n"
        "Vielen Dank im Voraus für Ihre Unterstützung.\n\n"
        "Mit freundlichen Grüßen\n"
        f"{req.sender_name}"
    )

    return EmailResponse(subject=template["subject"], body=body)