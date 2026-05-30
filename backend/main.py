import os
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import database
import tracker
import joblib
import httpx
import agent

app = FastAPI(title="AI Job Agent Command Center")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- DATA MODELS ---
class ProfileData(BaseModel):
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    gender: str = ""
    dob: str = ""  # YYYY-MM-DD
    location: str = ""
    expected_salary: str = ""
    skills: str = ""

    class Config:
        extra = "allow"

class ProfileUpdatePayload(BaseModel):
    data: ProfileData

class LearningPayload(BaseModel):
    field_mappings: Dict[str, str]

# Global/In-memory store for learned corrections (persist to SQLite/JSON as needed)
LEARNED_MAPPINGS = {}

class JobEntry(BaseModel):
    company: str
    role: str
    link: str
    status: str = "Applied"

# --- LOAD MACHINE LEARNING MODEL ---
ML_MODEL_PATH = "../ml_model/form_field_classifier.pkl"
try:
    classifier = joblib.load(ML_MODEL_PATH)
    print("🧠 ML Model Loaded Successfully!")
except FileNotFoundError:
    classifier = None
    print("⚠️ ML Model not found. Run the Jupyter notebook first.")

# --- ENDPOINTS ---
@app.get("/profile/")
def get_profile(db: Session = Depends(get_db)):
    """Dynamically fetches all profile fields from the database."""
    items = db.query(database.UserProfile).all()
    return {item.key: item.value for item in items}

@app.post("/profile/update/")
def update_profile(payload: ProfileUpdatePayload, db: Session = Depends(get_db)):
    """Dynamically updates the database with any provided profile fields."""
    # Handle dict() depending on Pydantic v1 vs v2
    profile_data_dict = getattr(payload.data, "model_dump", payload.data.dict)()
    
    for k, v in profile_data_dict.items():
        db_item = db.query(database.UserProfile).filter(database.UserProfile.key == k).first()
        if db_item:
            db_item.value = str(v)
        else:
            new_item = database.UserProfile(key=k, value=str(v))
            db.add(new_item)
            
    db.commit()
    print(f"💾 Database dynamically updated with profile data.")
    return {"status": "success"}

@app.post("/agent/learn/")
def learn_from_form(payload: LearningPayload, db: Session = Depends(get_db)):
    """Permanently saves manually typed answers into the Master Vault."""
    
    # 1. Fetch all existing Master Vault data to prevent duplicates
    existing_items = db.query(database.UserProfile).all()
    existing_keys = {item.key: item.value for item in existing_items}
    existing_values = list(existing_keys.values())

    new_fields_learned = 0

    for field_id, manual_value in payload.field_mappings.items():
        # Clean the HTML field name to use as a clean database key
        clean_key = field_id.replace("-", "_").replace(" ", "_").lower()

        # Rule 1: Ignore empty values
        if not manual_value or str(manual_value).strip() == "":
            continue

        # Rule 2: Ignore if we already have this exact value in the DB 
        # (This stops the DB from saving your first name 50 times under different HTML ID tags)
        if manual_value in existing_values:
            continue

        # Rule 3: Ignore if the key already exists
        if clean_key in existing_keys:
            continue

        # If it passes all rules, it is a BRAND NEW data point. Save it to SQLite!
        new_profile_item = database.UserProfile(key=clean_key, value=manual_value)
        db.add(new_profile_item)
        new_fields_learned += 1
        print(f"🧠 LEARNED NEW FIELD: [{clean_key}] -> '{manual_value}'")

    if new_fields_learned > 0:
        db.commit()
        print(f"💾 Permanently saved {new_fields_learned} new attributes to the Master Vault.")
        
    return {"status": "success", "learned_count": new_fields_learned}

@app.post("/job/log/")
def log_job(job: JobEntry, db: Session = Depends(get_db)):
    """Logs a successful application and updates the Excel sheet."""
    new_job = database.JobLog(
        company=job.company,
        role=job.role,
        link=job.link,
        status=job.status
    )
    db.add(new_job)
    db.commit()
    
    # Instantly rebuild the Excel tracker
    tracker.export_to_excel()
    
    return {"status": "Job logged and Excel updated!"}




class PredictRequest(BaseModel):
    fields: List[Dict[str, str]]  # List of dicts: [{"id": "field_id", "label": "Text Label"}]
    context: Optional[str] = ""   # The Job Description extracted from the webpage

# --- HELPER: OLLAMA LLM CALL ---
async def ask_ollama(question: str, job_context: str, profile_summary: str) -> str:
    """Calls the local Ollama instance with strict, persona-driven prompt engineering."""
    url = "http://localhost:11434/api/generate"
    
    # The "Leash": A highly restrictive prompt forcing the AI to only use your data
    prompt = f"""
    You are answering a job application question on my behalf. You must act as me.
    
    ### MY ACTUAL PERSONAL DATA (YOUR ONLY KNOWLEDGE BASE):
    {profile_summary}
    
    ### THE JOB I AM APPLYING FOR:
    {job_context}
    
    ### THE QUESTION YOU MUST ANSWER:
    "{question}"
    
    ### STRICT RULES YOU MUST FOLLOW:
    1. Answer strictly in the first person ("I", "my").
    2. NEVER invent, fabricate, or hallucinate skills, experiences, or degrees that are not explicitly listed in MY ACTUAL PERSONAL DATA.
    3. If the question asks for an experience I do not have in my data, confidently explain how my existing skills (from my data) make me capable of learning it quickly. Do not lie.
    4. Tailor the answer to align with the job description, but keep it factual to my profile.
    5. Be concise and professional. Maximum 3 to 4 sentences.
    6. Output ONLY the exact text that should be typed into the form box. Do not include phrases like "Here is the answer:" or "Based on your data:".
    """
    
    payload = {
        "model": "qwen2.5:3b", # Updated to match your specific downloaded model
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2, # Lower temperature = less creative, more factual
            "top_p": 0.9
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=45.0) # slightly longer timeout for generation
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except Exception as e:
            print(f"❌ Ollama Error: {e}")
    return ""


@app.post("/predict/")
async def predict_fields(request: PredictRequest, db: Session = Depends(get_db)):
    """Smart routing: DB Lookup -> ML Classifier -> Ollama Generative Fallback."""
    predictions = {}
    
    # Pre-fetch user profile data for processing
    profile_items = db.query(database.UserProfile).all()
    master_data = {item.key: item.value for item in profile_items}
    profile_summary = "\n".join([f"- {k}: {v}" for k, v in master_data.items()])

    for field in request.fields:
        field_id = field.get("id", "")
        field_label = field.get("label", "")
        
        # Clean identifiers for matching
        clean_id = field_id.replace("_", " ").replace("-", " ").lower()
        clean_label = field_label.lower()
        
        # Strategy 1: Direct Match in Database keys
        found_key = None
        for key in master_data.keys():
            if key in clean_id or key in clean_label:
                found_key = key
                break
                
        if found_key:
            predictions[field_id] = master_data[found_key]
            continue

        # Strategy 2: Machine Learning Classification
        if classifier:
            predicted_key = classifier.predict([clean_label if clean_label else clean_id])[0]
            if predicted_key in master_data:
                predictions[field_id] = master_data[predicted_key]
                continue

        # Strategy 3: Local LLM (Ollama) Generative Fallback
        # Triggered if it looks like a long-form question or if other strategies failed
        if request.context and (len(clean_label) > 15 or "why" in clean_label or "describe" in clean_label):
            ai_answer = await ask_ollama(field_label, request.context, profile_summary)
            if ai_answer:
                predictions[field_id] = ai_answer
                print(f"🤖 Ollama Generated Answer for field [{field_id}]")

    return {"predictions": predictions}


@app.get("/jobs/")
def get_jobs(db: Session = Depends(get_db)):
    """Fetches all applied jobs to display on the React Dashboard."""
    jobs = db.query(database.JobLog).order_by(database.JobLog.applied_on.desc()).all()
    return jobs

class AgentTrigger(BaseModel):
    portal: str

@app.post("/agent/prepare/")
def prepare_agent(request: AgentTrigger):
    """Opens a new tab for the user to log into manually."""
    print(f"🧭 Preparing browser for {request.portal}")
    agent.prepare_browser(request.portal)
    return {"status": "Browser opened. Waiting for login."}

@app.post("/agent/start/")
async def start_agent(request: AgentTrigger, background_tasks: BackgroundTasks):
    """Starts the actual automation loop."""
    print(f"🚀 Running Agent on {request.portal}")
    background_tasks.add_task(agent.run_autonomous_agent, request.portal)
    return {"status": "Agent deployed!"}

