from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./bureaucracy.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define the Database Table for Guides
class GuideModel(Base):
    __tablename__ = "guides"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True)
    steps = Column(Text)  # Stored as text (steps joined by "||")

Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# FastAPI app initialization
app = FastAPI(
    title="German Bureaucracy Helper",
    description="Fullstack app with DB, Backend, and Frontend to help navigate German bureaucracy. Provides step-by-step guides and generates formal email drafts for various bureaucratic topics. ",
    version="2.0.0",
)
 
# --------------------------------------------------------------------------
# Data: bureaucracy guides
# --------------------------------------------------------------------------
GUIDES = [
    {
        "id": 1,
        "title": "Anmeldung (Register your address)",
        "steps": [
            "Find an apartment and get the Wohnungsgeberbestätigung from your landlord.",
            "Book an appointment at the local Bürgeramt (often online).",
            "Bring your passport/ID, rental contract and the Wohnungsgeberbestätigung.",
            "Fill in the Anmeldeformular and submit it at your appointment.",
            "Receive your Meldebescheinigung (registration certificate).",
        ],
    },
    {
        "id": 2,
        "title": "Steuer-ID (Tax identification number)",
        "steps": [
            "Complete your Anmeldung first.",
            "Wait about 2-3 weeks; the Bundeszentralamt für Steuern mails it automatically.",
            "Give the number to your employer for payroll.",
        ],
    },
    {
        "id": 3,
        "title": "Krankenversicherung (Health insurance)",
        "steps": [
            "Choose between public (gesetzlich) and private insurance.",
            "Apply online with a provider such as TK, AOK or Barmer.",
            "Submit your Anmeldung and employment details.",
            "Receive your insurance card (Gesundheitskarte) by post.",
        ],
    },
    {
        "id": 4,
        "title": "Bankkonto (Bank account)",
        "steps": [
            "Choose a bank (e.g. Sparkasse, Commerzbank, N26).",
            "Bring your passport and Meldebescheinigung.",
            "Open the account and receive your IBAN and bank card.",
        ],
    },
    {
        "id": 5,
        "title": "Aufenthaltstitel (Residence permit)",
        "steps": [
            "Book an appointment at the Ausländerbehörde.",
            "Bring passport, biometric photos, rental contract, proof of income and health insurance.",
            "Pay the fee and submit your application.",
            "Collect your residence permit once it is ready.",
        ],
    },
]
 
# --------------------------------------------------------------------------
# Data: email templates (keys are matched against the topic text)
# --------------------------------------------------------------------------
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
 
 
# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------
class EmailRequest(BaseModel):
    topic: str = Field(..., min_length=2, examples=["Anmeldung"])
    sender_name: str = Field("Max Mustermann", examples=["Max Mustermann"])
    recipient_name: Optional[str] = Field(
        None, description="e.g. 'Frau Schmidt'. Leave empty for a generic salutation."
    )
    details: Optional[str] = Field(
        None, description="Optional extra sentence to add to the email."
    )
 
 
class EmailResponse(BaseModel):
    subject: str
    body: str
 
 
# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------
@app.get("/guides")
def get_guides():
    """Return German bureaucracy guides with step-by-step instructions."""
    return {"count": len(GUIDES), "guides": GUIDES}
 
 
@app.post("/generate-email", response_model=EmailResponse)
def generate_email(req: EmailRequest):
    """Generate a formal German email draft for the given topic."""
    topic = req.topic.strip().lower()
 
    template = next((t for key, t in TEMPLATES.items() if key in topic), None)
    if template is None:
        # Generic fallback for unknown topics
        template = {
            "subject": f"Anfrage: {req.topic.strip()}",
            "body": (
                f"ich wende mich an Sie bezüglich des Themas „{req.topic.strip()}“. "
                "Ich würde mich freuen, wenn Sie mir weitere Informationen zum "
                "weiteren Vorgehen mitteilen könnten."
            ),
        }
 
    salutation = (
        f"Sehr geehrte Damen und Herren,"
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
 
 
@app.get("/health")
def health():
    """Simple server status check."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }