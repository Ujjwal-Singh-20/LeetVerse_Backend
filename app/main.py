from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from datetime import date
import os
from models import UploadResponse, LeaderboardEntry, UserHistoryEntry
from utils import parse_excel_scores
from crud import update_bulk_scores_atomic, get_leaderboard_for_date, get_user_score_history, get_program_details, is_admin
from auth import get_current_user, get_admin_user, set_user_role_claim, verify_firebase_token
from firebase_config import db

app = FastAPI(title="LeetVerse Backend")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health():
    return {"server healthy"}

@app.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """
    Returns the current authenticated user's details and role.
    """
    return {
        "uid": user.get("uid"),
        "email": user.get("email"),
        "name": user.get("name"),
        "role": user.get("role"),
        "rollNo": user.get("rollNo")
    }

@app.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    """
    Fetch details using simplified logic from basic folder:
    - Admin: Return all users' data.
    - Normal User: Return their own data.
    """
    email = user.get("email", "").lower()
    role = user.get("role")
    
    if role == "admin":
        # Admin: Fetch participants and fellow admins
        participants_docs = db.collection("users").stream()
        admins_docs = db.collection("admins").stream()
        
        admins_data = []
        admin_emails = set()
        for doc in admins_docs:
            d = doc.to_dict()
            # Ensure the email (doc ID) is included if missing in fields
            if 'email' not in d:
                d['email'] = doc.id
            admins_data.append(d)
            admin_emails.add(d['email'].lower())
        
        participants_data = []
        for doc in participants_docs:
            d = doc.to_dict()
            # Filter out anyone whose email is in the admin list
            if d.get('email', '').lower() not in admin_emails:
                participants_data.append(d)
                
        from utils import sanitize_dict
        return {
            "role": "admin",
            "requesting_user": email,
            "participants": [sanitize_dict(p) for p in participants_data],
            "admins": [sanitize_dict(a) for a in admins_data]
        }
    else:
        # Normal User: Fetch only their own document
        roll_no = user.get("rollNo")
        user_doc = db.collection("users").document(roll_no).get()
        
        if not user_doc.exists:
            # Fallback if doc doesn't exist yet but user is authenticated
            from utils import sanitize_dict
            return {
                "role": role,
                "requesting_user": email,
                "data": sanitize_dict(user),
                "message": "Detailed profile not found in database."
            }
        
        from utils import sanitize_dict
        return {
            "role": "participant",
            "requesting_user": email,
            "data": sanitize_dict(user_doc.to_dict())
        }

@app.post("/login")
async def login(request: Request, user: dict = Depends(get_current_user)):
    """
    POST endpoint for login, matches the test folder pattern.
    Returns user details after verification.
    Supports both with and without request body.
    """
    return {
        "status": "success",
        "message": "Login Successful",
        "user": {
            "uid": user.get("uid"),
            "email": user.get("email"),
            "name": user.get("name"),
            "role": user.get("role"),
            "rollNo": user.get("rollNo")
        }
    }

@app.post("/upload-excel", response_model=UploadResponse)
async def upload_excel(
    file: UploadFile = File(...),
    score_date: str = Query(None),
    admin: dict = Depends(get_admin_user)
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file format.")
    
    content = await file.read()
    scores = parse_excel_scores(content)
    target_date = score_date or date.today().isoformat()
    admin_email = admin.get("email")
    
    updated_count = update_bulk_scores_atomic(scores, target_date, admin_email)
    return UploadResponse(message="Success", updated_count=updated_count, total_processed=len(scores))

@app.post("/cron/update-leaderboard")
async def cron_update_leaderboard(request: Request):
    auth_header = request.headers.get("Authorization")
    cron_secret = os.getenv("CRON_SECRET")
    
    if not cron_secret or auth_header != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Unauthorized cron request")
        
    from crud import sync_leaderboard_to_edge_config
    success = sync_leaderboard_to_edge_config()
    if success:
        return {"message": "Leaderboard synced to Edge Config successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to sync to Edge Config")

@app.get("/leaderboard/top10")
async def get_top10_leaderboard(rollNo: str = Query(None)):
    from crud import get_edge_leaderboard, get_overall_leaderboard
    top10 = get_edge_leaderboard("leaderboard_top10")
    
    if not top10:
        # Fallback: calculate from Firestore
        full = get_overall_leaderboard(limit=None)
        ranked = [{"rollNo": e.rollNo, "name": e.name, "points": e.points, "rank": i+1} for i, e in enumerate(full)]
        top10 = ranked[:10]
        if rollNo:
            user_entry = next((item for item in ranked if item["rollNo"] == rollNo), None)
            if user_entry and user_entry["rank"] > 10:
                top10.append(user_entry)
        return top10
        
    # If Edge Config fetched successfully and we need a specific user outside top 10
    if rollNo and not any(item["rollNo"] == rollNo for item in top10):
        top100 = get_edge_leaderboard("leaderboard_full")
        if top100:
            user_entry = next((item for item in top100 if item["rollNo"] == rollNo), None)
            if user_entry:
                top10.append(user_entry)
        
        # If still not found (either user is outside top 100 or Edge read failed)
        if not any(item["rollNo"] == rollNo for item in top10):
            # Fallback to firestore just for this user
            full_fs = get_overall_leaderboard(limit=None)
            ranked = [{"rollNo": e.rollNo, "name": e.name, "points": e.points, "rank": i+1} for i, e in enumerate(full_fs)]
            user_entry = next((item for item in ranked if item["rollNo"] == rollNo), None)
            if user_entry:
                top10.append(user_entry)
                
    return top10

@app.get("/leaderboard/full")
async def get_full_leaderboard_endpoint(admin: dict = Depends(get_admin_user)):
    from crud import get_edge_leaderboard, get_overall_leaderboard
    full = get_edge_leaderboard("leaderboard_full")
    if not full:
        full_fs = get_overall_leaderboard(limit=None)
        return [{"rollNo": e.rollNo, "name": e.name, "points": e.points, "rank": i+1} for i, e in enumerate(full_fs)]
    return full

@app.get("/upload-status")
async def get_upload_status(
    score_date: str = Query(None),
    admin: dict = Depends(get_admin_user)
):
    """Checks if scores for a specific date (or today) are already uploaded."""
    from crud import check_scores_exist
    target_date = score_date or date.today().isoformat()
    exists = check_scores_exist(target_date)
    return {"date": target_date, "uploaded": exists}

@app.get("/leaderboard/{score_date}", response_model=List[LeaderboardEntry])
async def get_leaderboard(score_date: str, user: dict = Depends(get_current_user)):
    try:
        date.fromisoformat(score_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format.")
    return get_leaderboard_for_date(score_date)

@app.get("/user/{roll_no}/history")
async def get_user_history_endpoint(
    roll_no: str,
    program_id: str = "default_program",
    current_user: dict = Depends(get_current_user)
):
    role = current_user.get("role")
    user_roll_no = current_user.get("rollNo", "")
    
    if role != "admin" and user_roll_no.lower() != roll_no.lower():
        raise HTTPException(status_code=403, detail="Forbidden.")
    
    history = get_user_score_history(roll_no)
    program = get_program_details(program_id)
    days_completed = program.get("daysCompleted", 1) if program else 1
    days_present = sum(1 for entry in history if entry.attendance)
    attendance_percentage = (days_present / days_completed) * 100 if days_completed > 0 else 0
    
    return {
        "rollNo": roll_no,
        "attendancePercentage": round(attendance_percentage, 2),
        "history": [entry.dict() for entry in history]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
