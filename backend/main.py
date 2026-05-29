import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, List, Optional
import database
import tracker
import joblib
import httpx

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
class ProfileUpdate(BaseModel):
    data: Dict[str, str]

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
@app.post("/profile/update/")
def update_profile(profile: ProfileUpdate, db: Session = Depends(get_db)):
    """Receives your Master Data (Name, Github, etc.) and saves it permanently."""
    for k, v in profile.data.items():
        db_item = db.query(database.UserProfile).filter(database.UserProfile.key == k).first()
        if db_item:
            db_item.value = v
        else:
            new_item = database.UserProfile(key=k, value=v)
            db.add(new_item)
    db.commit()
    return {"status": "Profile updated successfully"}

@app.get("/profile/")
def get_profile(db: Session = Depends(get_db)):
    """The Chrome Extension will call this to retrieve your data to fill forms."""
    items = db.query(database.UserProfile).all()
    return {item.key: item.value for item in items}

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
    """Calls the local Ollama instance to generate long-form answers."""
    url = "http://localhost:11434/api/generate"
    
    prompt = f"""
    You are an expert career assistant helping me fill out a job application.
    
    My Profile Details:
    {profile_summary}
    
    Job Description Context:
    {job_context}
    
    Question to Answer:
    "{question}"
    
    Instructions:
    Write a concise, professional, and compelling answer to the question based strictly on my profile details and tailored slightly to match the job context. Do not include placeholders. Write the raw answer only.
    """
    
    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=30.0)
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