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
        # Admin: Fetch all users
        users_ref = db.collection("users")
        docs = users_ref.stream()
        all_users = [doc.to_dict() for doc in docs]
        return {
            "role": "admin",
            "requesting_user": email,
            "data": all_users
        }
    else:
        # Normal User: Fetch only their own document
        roll_no = user.get("rollNo")
        user_doc = db.collection("users").document(roll_no).get()
        
        if not user_doc.exists:
            # Fallback if doc doesn't exist yet but user is authenticated
            return {
                "role": role,
                "requesting_user": email,
                "data": user,
                "message": "Detailed profile not found in database."
            }
        
        return {
            "role": "participant",
            "requesting_user": email,
            "data": user_doc.to_dict()
        }

@app.post("/login")
async def login(user: dict = Depends(get_current_user)):
    """
    POST endpoint for login, matches the test folder pattern.
    Returns user details after verification.
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
    admin: dict = Depends(get_admin_user)
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file format.")
    
    content = await file.read()
    scores = parse_excel_scores(content)
    today_str = date.today().isoformat()
    admin_email = admin.get("email")
    
    updated_count = update_bulk_scores_atomic(scores, today_str, admin_email)
    return UploadResponse(message="Success", updated_count=updated_count, total_processed=len(scores))

@app.get("/leaderboard/overall", response_model=List[LeaderboardEntry])
async def get_overall_rankings(user: dict = Depends(get_current_user)):
    from crud import get_overall_leaderboard
    return get_overall_leaderboard()

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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
