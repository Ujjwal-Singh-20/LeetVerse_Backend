from firebase_admin import firestore
from firebase_config import db, get_coll_path
from models import LeaderboardEntry, UserHistoryEntry, CurriculumEntry, ExtraPractice, Reminder, QuestionValidationRequest
from leetcode_handler import fetch_recent_accepted_submissions
from datetime import datetime, timedelta
from typing import List, Optional, Any
import os
import json
import urllib.request
import urllib.error
from utils import json_serial

# --- CURRICULUM MANAGEMENT ---

def save_curriculum(entry: CurriculumEntry, season: str = None, level: str = None):
    """Saves daily curriculum (class/assigned questions)."""
    coll_path = get_coll_path("curriculum", season, level)
    db.collection(coll_path).document(entry.date).set(entry.dict())
    return True

def get_all_curriculum(season: str = None, level: str = None) -> List[dict]:
    """Fetches all curriculum entries, sorted by date descending."""
    coll_path = get_coll_path("curriculum", season, level)
    docs = db.collection(coll_path).order_by("date", direction=firestore.Query.DESCENDING).stream()
    return [doc.to_dict() for doc in docs]

def delete_curriculum(date_str: str, season: str = None, level: str = None):
    coll_path = get_coll_path("curriculum", season, level)
    db.collection(coll_path).document(date_str).delete()
    return True

# --- EXTRA PRACTICE ---

def add_extra_practice(roll_no: str, date_str: str, slug: str, season: str = None, level: str = None):
    """Adds an extra practice problem for a user."""
    user_ref = db.collection(get_coll_path("users", season, level)).document(roll_no)
    extra_ref = user_ref.collection("extra_practice").document(date_str)
    
    doc = extra_ref.get()
    if doc.exists:
        extra_ref.update({
            "slugs": firestore.ArrayUnion([slug])
        })
    else:
        extra_ref.set({
            "date": date_str,
            "rollNo": roll_no,
            "slugs": [slug]
        })
    return True

def get_user_extra_practice(roll_no: str, season: str = None, level: str = None) -> List[dict]:
    """Fetches all extra practice for a user, sorted by date descending."""
    user_ref = db.collection(get_coll_path("users", season, level)).document(roll_no)
    docs = user_ref.collection("extra_practice").order_by("date", direction=firestore.Query.DESCENDING).stream()
    return [doc.to_dict() for doc in docs]

# --- REMINDERS & SPACED REPETITION ---

def calculate_rs_and_date(req: QuestionValidationRequest, difficulty: str = "Medium") -> tuple:
    """Calculates Retention Score and Reminder Date based on performance and difficulty."""
    rs = 5
    rs += 3 if req.self_solved else 0
    rs += -2 if req.hint_used else 2
    rs += -3 if req.solution_seen else 2
    rs += 2 if req.time_taken_mins < 30 else -2
    
    # Base intervals
    if rs <= 4: interval = 3
    elif rs <= 7: interval = 7
    elif rs <= 9: interval = 14
    else: interval = 21

    # Difficulty Adjustments
    if difficulty == "Easy":
        if rs <= 6: # Struggling with Easy
            interval = max(1, interval - 2) 
        elif rs >= 10: # Mastered Easy
            interval += 7
    elif difficulty == "Hard":
        if rs <= 6: # Struggling with Hard (Expected, give a bit more time to process)
            interval = max(3, interval + 2)
    
    remind_date = (datetime.now() + timedelta(days=interval)).strftime("%Y-%m-%d")
    return rs, remind_date

async def verify_and_schedule_reminder(req: QuestionValidationRequest, season: str = None, level: str = None):
    """Verifies LeetCode submission and schedules a one-time reminder."""
    # 1. Get User Profile for leetcode_username
    user_doc = db.collection(get_coll_path("users", season, level)).document(req.rollNo).get()
    if not user_doc.exists:
        return {"error": "User profile not found in database."}
    
    user_data = user_doc.to_dict()
    username = user_data.get("leetcode_username")
    if not username:
        return {"error": "LeetCode username not linked to profile. Please update your settings."}
    
    # 2. Verify recent accepted submissions on LeetCode and get difficulty
    difficulty = "Medium"
    try:
        from leetcode_handler import fetch_recent_accepted_submissions, fetch_problem
        
        import asyncio
        # We need both: verification and difficulty
        lc_data, prob_data = await asyncio.gather(
            fetch_recent_accepted_submissions(username),
            fetch_problem(req.slug)
        )
        
        recent_ac = lc_data.get("recentAcSubmissionList", [])
        is_verified = any(s['titleSlug'] == req.slug for s in recent_ac)
        
        if not is_verified:
            return {"error": "Completion not verified. Ensure your submission is 'Accepted' on LeetCode and try again."}
            
        difficulty = prob_data.get("question", {}).get("difficulty", "Medium")
        
    except Exception as e:
        return {"error": f"Failed to verify with LeetCode: {str(e)}"}
    
    # 3. Calculate RS and initial Remind Date
    rs, remind_date = calculate_rs_and_date(req, difficulty)
    
    # 4. Handle Staggering logic (Avoid reminder overload on a single day)
    final_remind_date = remind_date
    for i in range(7): # Stagger up to 7 days if needed
        check_date = (datetime.strptime(remind_date, "%Y-%m-%d") + timedelta(days=i)).strftime("%Y-%m-%d")
        # Check if this user already has a reminder on this specific date
        existing = db.collection("reminders").document(check_date).collection("participants").document(req.rollNo).get()
        if not existing.exists:
            final_remind_date = check_date
            break
    
    # 5. Save the Reminder
    reminder_doc = {
        "rollNo": req.rollNo,
        "slug": req.slug,
        "remind_date": final_remind_date,
        "status": "pending",
        "rs_score": rs,
        "scheduled_at": firestore.SERVER_TIMESTAMP
    }
    db.collection("reminders").document(final_remind_date).collection("participants").document(req.rollNo).set(reminder_doc)
    
    # 6. Mark as completed in user profile for easy UI tracking
    db.collection(get_coll_path("users", season, level)).document(req.rollNo).update({
        "completed_slugs": firestore.ArrayUnion([req.slug])
    })
    
    return {
        "status": "success", 
        "remind_date": final_remind_date, 
        "rs_score": rs,
        "message": f"Verified! Reminder scheduled for {final_remind_date}."
    }

def get_daily_reminders(roll_no: str, date_str: str) -> List[dict]:
    """Fetches reminders for a specific user on a specific date."""
    doc = db.collection("reminders").document(date_str).collection("participants").document(roll_no).get()
    return [doc.to_dict()] if doc.exists else []

def archive_session_to_edge(season: str, level: str) -> bool:
    """Finalizes a session by archiving its Top 10 to Edge Config."""
    full_board = get_overall_leaderboard(limit=10, season=season, level=level)
    if not full_board:
        return False
        
    top_10 = [{"rollNo": e.rollNo, "name": e.name, "points": e.points, "rank": i+1, "leetcode_username": e.leetcode_username} for i, e in enumerate(full_board)]
    
    config_id = os.getenv("EDGE_CONFIG_ID")
    vercel_token = os.getenv("VERCEL_API_TOKEN")
    if not config_id or not vercel_token:
        return False

    archive_key = f"top10_{season}_{level}"
    url = f"https://api.vercel.com/v1/edge-config/{config_id}/items"
    payload = {"items": [
        {"operation": "upsert", "key": archive_key, "value": top_10}
    ]}
    
    req = urllib.request.Request(url, data=json.dumps(payload, default=json_serial).encode('utf-8'), headers={"Authorization": f"Bearer {vercel_token}", "Content-Type": "application/json"}, method="PATCH")
    try:
        with urllib.request.urlopen(req) as response:
            return response.status in [200, 201, 202]
    except:
        return False

# --- EXISTING SCORE & ADMIN LOGIC ---

def update_bulk_scores_atomic(scores_data: List[dict], score_date: str, admin_email: str, season: str = None, level: str = None):
    """
    Updates multiple users' scores, attendance, and names in a single batch.
    Handles re-uploads by first reverting existing scores for the same date.
    """
    users_ref = db.collection(get_coll_path("users", season, level))
    score_date_ref = db.collection(get_coll_path("scores", season, level)).document(score_date)
    
    existing_meta = score_date_ref.get()
    if existing_meta.exists:
        existing_participants = score_date_ref.collection("participants").get()
        revert_batch = db.batch()
        for doc in existing_participants:
            data = doc.to_dict()
            roll_no = doc.id
            p_points = data.get("points", 0)
            p_status = data.get("status", "absent")
            user_ref = users_ref.document(roll_no)
            revert_data = {"totalPoints": firestore.Increment(-p_points)}
            if p_status == "present":
                revert_data["attendanceSummary.daysPresent"] = firestore.Increment(-1)
            else:
                revert_data["attendanceSummary.daysAbsent"] = firestore.Increment(-1)
            revert_batch.update(user_ref, revert_data)
            revert_batch.delete(doc.reference)
        revert_batch.commit()

    all_users = users_ref.get()
    all_roll_nos = {doc.id for doc in all_users}
    uploaded_roll_nos = {str(s['rollNo']) for s in scores_data}
    missing_roll_nos = all_roll_nos - uploaded_roll_nos

    score_date_ref.set({
        "uploadedBy": admin_email,
        "uploadedAt": firestore.SERVER_TIMESTAMP,
        "isReupload": existing_meta.exists
    }, merge=True)

    all_score_docs = db.collection(get_coll_path("scores", season, level)).get()
    all_past_dates = [d.id for d in all_score_docs if d.id != score_date]

    batch = db.batch()
    for item in scores_data:
        roll_no = str(item['rollNo'])
        points = item['points']
        name = item.get('name')
        user_ref = users_ref.document(roll_no)
        participant_ref = score_date_ref.collection("participants").document(roll_no)
        is_new_user = roll_no not in all_roll_nos
        past_absences = len(all_past_dates) if is_new_user else 0
        user_update_data = {
            "rollNo": roll_no,
            "totalPoints": firestore.Increment(points),
            "attendanceSummary": {
                "daysPresent": firestore.Increment(1),
                "daysAbsent": firestore.Increment(past_absences)
            }
        }
        if name: user_update_data["name"] = name
        batch.set(user_ref, user_update_data, merge=True)
        if is_new_user:
            for past_date in all_past_dates:
                past_participant_ref = db.collection(get_coll_path("scores", season, level)).document(past_date).collection("participants").document(roll_no)
                batch.set(past_participant_ref, {"rollNo": roll_no, "points": 0, "status": "absent", "attendance": False})
        batch.set(participant_ref, {"rollNo": roll_no, "points": points, "status": "present", "attendance": True})

    for roll_no in missing_roll_nos:
        batch.set(users_ref.document(roll_no), {"attendanceSummary": {"daysAbsent": firestore.Increment(1)}}, merge=True)
        batch.set(score_date_ref.collection("participants").document(roll_no), {"rollNo": roll_no, "points": 0, "status": "absent", "attendance": False})

    batch.commit()
    return len(uploaded_roll_nos)

def is_admin(email: str) -> bool:
    if not email: return False
    return db.collection(get_coll_path("admins")).document(email.lower()).get().exists

def get_all_admins() -> List[dict]:
    docs = db.collection(get_coll_path("admins")).stream()
    return [{**doc.to_dict(), "email": doc.id} for doc in docs]

def register_user_if_not_exists(uid: str, email: str, name: str, roll_no: str, season: str = None, level: str = None):
    user_ref = db.collection(get_coll_path("users", season, level)).document(roll_no)
    doc = user_ref.get()
    if not doc.exists:
        user_ref.set({"uid": uid, "email": email, "name": name.upper() if name else "", "rollNo": roll_no, "totalPoints": 0, "attendanceSummary": {"daysPresent": 0, "daysAbsent": 0}, "badges": [], "createdAt": firestore.SERVER_TIMESTAMP})
    else:
        user_ref.set({"uid": uid, "name": name.upper() if name else doc.to_dict().get("name", ""), "email": email, "rollNo": roll_no}, merge=True)

# --- SYNC & CACHING LOGIC ---

def sync_leaderboard_to_blob() -> bool:
    """Calculates leaderboard and curriculum snapshots, pushing them to Vercel Blob."""
    token = os.getenv("BLOB_READ_WRITE_TOKEN")
    if not token: return False

    # 1. Fetch Current Session Info
    from firebase_config import CURRENT_SEASON, CURRENT_LEVEL
    
    # 2. Generate Leaderboard Snapshots
    full_board = get_overall_leaderboard(limit=None)
    ranked_full = [{"rollNo": e.rollNo, "name": e.name, "points": e.points, "rank": i+1, "leetcode_username": e.leetcode_username} for i, e in enumerate(full_board)]
    top_10 = ranked_full[:10]
    
    # 3. Generate Curriculum Snapshot (Latest on top)
    curr_docs = get_all_curriculum(CURRENT_SEASON, CURRENT_LEVEL)
    
    # 4. Generate Daily Reminders Snapshot (Only for users due today)
    today_str = datetime.now().strftime("%Y-%m-%d")
    reminder_docs = db.collection("reminders").document(today_str).collection("participants").stream()
    today_reminders = [doc.to_dict() for doc in reminder_docs]

    files = {
        f"leaderboard/{CURRENT_SEASON}/{CURRENT_LEVEL}/top10.json": top_10,
        "leaderboard/latest_top10.json": top_10,
        "leaderboard/latest_full.json": ranked_full,
        f"curriculum/{CURRENT_SEASON}/{CURRENT_LEVEL}/snapshot.json": curr_docs,
        "reminders/today_snapshot.json": today_reminders
    }

    success = True
    uploaded_urls = {}
    for path, data in files.items():
        upload_url = f"https://blob.vercel-storage.com/{path}?access=public" 
        req = urllib.request.Request(upload_url, data=json.dumps(data, default=json_serial).encode('utf-8'), headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, method="PUT")
        try:
            with urllib.request.urlopen(req) as response:
                res_body = json.loads(response.read().decode('utf-8'))
                uploaded_urls[path] = res_body.get("url")
        except: success = False
            
    # 3. Update Session Metadata with new Blob URLs
    if success:
        try:
            db.collection("seasons").document(CURRENT_SEASON).collection("levels").document(CURRENT_LEVEL).set({
                "top10_url": uploaded_urls.get("leaderboard/latest_top10.json"),
                "full_url": uploaded_urls.get("leaderboard/latest_full.json"),
                "curriculum_url": uploaded_urls.get(f"curriculum/{CURRENT_SEASON}/{CURRENT_LEVEL}/snapshot.json"),
                "last_synced": firestore.SERVER_TIMESTAMP
            }, merge=True)
        except: pass
            
    return success

# Helper for Edge Config sync (existing)
def sync_leaderboard_to_edge_config() -> bool:
    return sync_leaderboard_to_blob() # Re-use the consolidated blob sync

def get_edge_leaderboard(key: str) -> Any:
    config_id = os.getenv("EDGE_CONFIG_ID")
    token = os.getenv("VERCEL_API_TOKEN")
    if not config_id or not token: return []
    url = f"https://api.vercel.com/v1/edge-config/{config_id}/item/{key}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get("value") if isinstance(data, dict) and "value" in data else data
    except: return None

def get_overall_leaderboard(limit: Optional[int] = 50, season: str = None, level: str = None) -> List[LeaderboardEntry]:
    from utils import clean_nan
    users_ref = db.collection(get_coll_path("users", season, level))
    query = users_ref.order_by("totalPoints", direction=firestore.Query.DESCENDING).stream()
    leaderboard = []
    count = 0
    for doc in query:
        if limit is not None and count >= limit: break
        data = doc.to_dict()
        leaderboard.append(LeaderboardEntry(
            rollNo=doc.id, 
            points=clean_nan(data.get("totalPoints")) or 0, 
            name=clean_nan(data.get("name")) or "", 
            remarks="",
            leetcode_username=data.get("leetcode_username")
        ))
        count += 1
    return leaderboard

def get_leaderboard_for_date(score_date: str, season: str = None, level: str = None) -> List[LeaderboardEntry]:
    from utils import clean_nan
    scores_ref = db.collection(get_coll_path("scores", season, level)).document(score_date).collection("participants")
    query = scores_ref.order_by("points", direction=firestore.Query.DESCENDING).stream()
    leaderboard = []
    for doc in query:
        data = doc.to_dict()
        user_data = db.collection(get_coll_path("users", season, level)).document(doc.id).get().to_dict() or {}
        leaderboard.append(LeaderboardEntry(rollNo=doc.id, points=clean_nan(data.get("points")) or 0, name=clean_nan(user_data.get("name")) or "", remarks=clean_nan(data.get("remarks")) or ""))
    return leaderboard

def get_user_score_history(roll_no: str, season: str = None, level: str = None) -> List[UserHistoryEntry]:
    from utils import clean_nan
    history = []
    scores_docs = db.collection(get_coll_path("scores", season, level)).stream()
    for date_doc in scores_docs:
        part_ref = db.collection(get_coll_path("scores", season, level)).document(date_doc.id).collection("participants").document(roll_no).get()
        if part_ref.exists:
            data = part_ref.to_dict()
            history.append(UserHistoryEntry(date=date_doc.id, points=clean_nan(data.get("points")) or 0, remarks=clean_nan(data.get("remarks")) or "", attendance=data.get("attendance", False), status=data.get("status", "absent")))
    history.sort(key=lambda x: x.date, reverse=True)
    return history

def get_program_details(program_id: str, season: str = None, level: str = None):
    doc = db.collection(get_coll_path("programs", season, level)).document(program_id).get()
    return doc.to_dict() if doc.exists else None

def check_scores_exist(score_date: str, season: str = None, level: str = None) -> bool:
    return db.collection(get_coll_path("scores", season, level)).document(score_date).get().exists

def get_all_practice_progress(season: str, level: str):
    """Aggregates all users' practice progress by date."""
    # 1. Fetch Curriculum
    curr_docs = db.collection(get_coll_path("curriculum", season, level)).order_by("date").stream()
    curriculum = {}
    dates = []
    for doc in curr_docs:
        data = doc.to_dict()
        curriculum[doc.id] = data
        dates.append(doc.id)
        
    # 2. Fetch Users
    users_docs = db.collection(get_coll_path("users", season, level)).stream()
    
    progress_by_date = {d: [] for d in dates}
    
    for doc in users_docs:
        u = doc.to_dict()
        roll_no = u.get("rollNo")
        if not roll_no or roll_no == "ADMIN":
            continue
            
        completed_slugs = set(u.get("completed_slugs", []))
        
        # Fetch extra practice
        extra_docs = db.collection(get_coll_path("users", season, level)).document(roll_no).collection("extra_practice").stream()
        extra_practice = {}
        for edoc in extra_docs:
            extra_practice[edoc.id] = edoc.to_dict().get("slugs", [])
            
        user_base_info = {
            "rollNo": roll_no,
            "name": u.get("name", ""),
            "leetcode_username": u.get("leetcode_username", "NOT_LINKED"),
            "total_completed": len(completed_slugs)
        }
        
        for date_str in dates:
            c_data = curriculum[date_str]
            class_qs = set(c_data.get("class_questions", []))
            assign_qs = set(c_data.get("assigned_questions", []))
            
            done_class = list(class_qs.intersection(completed_slugs))
            missing_class = list(class_qs - completed_slugs)
            
            done_assign = list(assign_qs.intersection(completed_slugs))
            missing_assign = list(assign_qs - completed_slugs)
            
            extras = extra_practice.get(date_str, [])
            
            progress_by_date[date_str].append({
                **user_base_info,
                "class_done": done_class,
                "class_missing": missing_class,
                "class_total": len(class_qs),
                "assign_done": done_assign,
                "assign_missing": missing_assign,
                "assign_total": len(assign_qs),
                "extra": extras
            })
            
    return {
        "dates": dates,
        "curriculum": curriculum,
        "progress": progress_by_date
    }

def export_practice_to_excel(season: str, level: str, date_str: str = None):
    """Generates an Excel file from practice progress data."""
    import pandas as pd
    import io
    
    # Reuse the aggregation logic
    progress_data = get_all_practice_progress(season, level)
    
    if date_str and date_str in progress_data["dates"]:
        dates = [date_str]
    else:
        dates = progress_data["dates"]

    
    # Group by user instead of date for the spreadsheet
    user_rows = {}
    
    for date_str in dates:
        users_for_date = progress_data["progress"][date_str]
        for u in users_for_date:
            roll_no = u["rollNo"]
            if roll_no not in user_rows:
                user_rows[roll_no] = {
                    "Roll No": roll_no,
                    "Name": u["name"],
                    "Leetcode Username": u["leetcode_username"],
                    "Total Completed (All Time)": u["total_completed"]
                }
            
            # Add date-specific columns
            class_total = u["class_total"]
            if class_total > 0:
                done = len(u["class_done"])
                missing = u["class_missing"]
                user_rows[roll_no][f"{date_str} Class ({class_total})"] = f"{done}/{class_total} Done" + (f" | Missing: {', '.join(missing)}" if missing else "")
            
            assign_total = u["assign_total"]
            if assign_total > 0:
                done = len(u["assign_done"])
                missing = u["assign_missing"]
                user_rows[roll_no][f"{date_str} Assigned ({assign_total})"] = f"{done}/{assign_total} Done" + (f" | Missing: {', '.join(missing)}" if missing else "")
            
            extras = u["extra"]
            if extras:
                user_rows[roll_no][f"{date_str} Extra"] = ", ".join(extras)
            else:
                user_rows[roll_no][f"{date_str} Extra"] = ""

    df = pd.DataFrame(list(user_rows.values()))
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Practice Progress')
    
    output.seek(0)
    return output


