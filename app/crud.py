from google.cloud import firestore
from firebase_config import db
from models import LeaderboardEntry, UserHistoryEntry
from typing import List, Optional
import os
import json
import urllib.request
import urllib.error

def update_bulk_scores_atomic(scores_data: List[dict], score_date: str, admin_email: str):
    """
    Updates multiple users' scores, attendance, and names in a single batch.
    Handles re-uploads by first reverting existing scores for the same date.
    """
    users_ref = db.collection("users")
    score_date_ref = db.collection("scores").document(score_date)
    
    # Check for existing scores to revert
    existing_meta = score_date_ref.get()
    if existing_meta.exists:
        existing_participants = score_date_ref.collection("participants").get()
        
        # Batch revert existing scores/attendance
        revert_batch = db.batch()
        for doc in existing_participants:
            data = doc.to_dict()
            roll_no = doc.id
            p_points = data.get("points", 0)
            p_status = data.get("status", "absent")
            
            user_ref = users_ref.document(roll_no)
            
            revert_data = {
                "totalPoints": firestore.Increment(-p_points)
            }
            if p_status == "present":
                revert_data["attendanceSummary.daysPresent"] = firestore.Increment(-1)
            else:
                revert_data["attendanceSummary.daysAbsent"] = firestore.Increment(-1)
            
            revert_batch.update(user_ref, revert_data)
            # Delete old record in subcollection
            revert_batch.delete(doc.reference)
            
        revert_batch.commit()

    # Get all participants to handle missing (absent) ones in the NEW upload
    all_users = users_ref.get()
    all_roll_nos = {doc.id for doc in all_users}
    
    uploaded_roll_nos = {str(s['rollNo']) for s in scores_data}
    missing_roll_nos = all_roll_nos - uploaded_roll_nos

    # Root score document metadata
    score_date_ref.set({
        "uploadedBy": admin_email,
        "uploadedAt": firestore.SERVER_TIMESTAMP,
        "isReupload": existing_meta.exists
    }, merge=True)

    # Fetch past score dates to handle retroactive absences
    all_score_docs = db.collection("scores").get()
    all_past_dates = [d.id for d in all_score_docs if d.id != score_date]

    batch = db.batch()
    
    # Process Present Participants
    for item in scores_data:
        roll_no = str(item['rollNo'])
        points = item['points']
        remarks = item.get('remarks', "")
        name = item.get('name') # Captured from Excel
        
        user_ref = users_ref.document(roll_no)
        participant_ref = score_date_ref.collection("participants").document(roll_no)
        
        is_new_user = roll_no not in all_roll_nos
        past_absences = len(all_past_dates) if is_new_user else 0
        
        # Update User doc
        user_update_data = {
            "rollNo": roll_no,
            "totalPoints": firestore.Increment(points),
            "attendanceSummary": {
                "daysPresent": firestore.Increment(1),
                "daysAbsent": firestore.Increment(past_absences)
            }
        }
        if name:
            user_update_data["name"] = name
            
        batch.set(user_ref, user_update_data, merge=True)
        
        # Record retroactive absences for new users
        if is_new_user:
            for past_date in all_past_dates:
                past_participant_ref = db.collection("scores").document(past_date).collection("participants").document(roll_no)
                batch.set(past_participant_ref, {
                    "rollNo": roll_no,
                    "points": 0,
                    "remarks": "Added retroactively as absent",
                    "attendance": False,
                    "status": "absent"
                })
        
        # Record daily score
        batch.set(participant_ref, {
            "rollNo": roll_no,
            "points": points,
            "remarks": remarks,
            "attendance": True,
            "status": "present"
        })

    # Process Absent Participants
    for roll_no in missing_roll_nos:
        user_ref = users_ref.document(roll_no)
        participant_ref = score_date_ref.collection("participants").document(roll_no)
        
        batch.set(user_ref, {
            "rollNo": roll_no,
            "attendanceSummary": {
                "daysAbsent": firestore.Increment(1)
            }
        }, merge=True)
        
        batch.set(participant_ref, {
            "rollNo": roll_no,
            "points": 0,
            "remarks": "N/A",
            "attendance": False,
            "status": "absent"
        })

    batch.commit()
    return len(uploaded_roll_nos)

def is_admin(email: str) -> bool:
    if not email: return False
    doc = db.collection("admins").document(email.lower()).get()
    return doc.exists

def get_all_admins() -> List[dict]:
    """Fetches all administrators, ensuring email is the document ID."""
    docs = db.collection("admins").stream()
    admins = []
    for doc in docs:
        d = doc.to_dict()
        if 'email' not in d:
            d['email'] = doc.id
        admins.append(d)
    return admins

def register_user_if_not_exists(uid: str, email: str, name: str, roll_no: str):
    user_ref = db.collection("users").document(roll_no)
    doc = user_ref.get()
    
    if not doc.exists:
        user_ref.set({
            "uid": uid,
            "email": email,
            "name": name.upper() if name else "",
            "rollNo": roll_no,
            "totalPoints": 0,
            "attendanceSummary": {"daysPresent": 0, "daysAbsent": 0},
            "badges": [],
            "createdAt": firestore.SERVER_TIMESTAMP
        })
    else:
        user_ref.set({
            "uid": uid,
            "name": name.upper() if name else doc.to_dict().get("name", ""),
            "email": email,
            "rollNo": roll_no
        }, merge=True)

def get_leaderboard_for_date(score_date: str) -> List[LeaderboardEntry]:
    scores_ref = db.collection("scores").document(score_date).collection("participants")
    query = scores_ref.order_by("points", direction=firestore.Query.DESCENDING).stream()
    leaderboard = []
    
    # To avoid N+1 queries in a real production app, we could denormalize names into the daily scores.
    # For now, we'll fetch them from the 'users' collection.
    for doc in query:
        data = doc.to_dict()
        roll_no = doc.id
        
        from utils import clean_nan
        
        # Fetch name from users collection
        user_doc = db.collection("users").document(roll_no).get()
        user_data = user_doc.to_dict() if user_doc.exists else {}
        name = clean_nan(user_data.get("name")) or ""
        
        leaderboard.append(LeaderboardEntry(
            rollNo=roll_no, 
            points=clean_nan(data.get("points")) or 0, 
            name=name,
            remarks=clean_nan(data.get("remarks")) or ""
        ))
    return leaderboard

def get_user_score_history(roll_no: str) -> List[UserHistoryEntry]:
    history = []
    scores_docs = db.collection("scores").stream()
    for date_doc in scores_docs:
        date_id = date_doc.id
        participant_ref = db.collection("scores").document(date_id).collection("participants").document(roll_no).get()
        if participant_ref.exists:
            data = participant_ref.to_dict()
            from utils import clean_nan
            history.append(UserHistoryEntry(
                date=date_id,
                points=clean_nan(data.get("points")) or 0,
                remarks=clean_nan(data.get("remarks")) or "",
                attendance=data.get("attendance", False),
                status=data.get("status", "absent")
            ))
    history.sort(key=lambda x: x.date, reverse=True)
    return history

def get_overall_leaderboard(limit: Optional[int] = 50) -> List[LeaderboardEntry]:
    # We should exclude users who are also admins if they accidentally exist in users collection
    admins = {a.get("email").lower() for a in get_all_admins() if a.get("email")}
    
    users_ref = db.collection("users")
    query = users_ref.order_by("totalPoints", direction=firestore.Query.DESCENDING).stream()
    
    leaderboard = []
    count = 0
    for doc in query:
        if limit is not None and count >= limit: break
        data = doc.to_dict()
        email = data.get("email", "").lower()
        if email in admins or doc.id.lower() in admins: continue # Skip admins in leaderboard
        
        from utils import clean_nan
        leaderboard.append(LeaderboardEntry(
            rollNo=doc.id, 
            points=clean_nan(data.get("totalPoints")) or 0, 
            name=clean_nan(data.get("name")) or "",
            remarks=""
        ))
        count += 1
    return leaderboard

def get_program_details(program_id: str):
    doc = db.collection("programs").document(program_id).get()
    return doc.to_dict() if doc.exists else None

def check_scores_exist(score_date: str) -> bool:
    """Checks if scores for a specific date have been uploaded."""
    doc = db.collection("scores").document(score_date).get()
    return doc.exists

def sync_leaderboard_to_edge_config() -> bool:
    """Calculates full leaderboard and pushes top 10 & full to Edge Config"""
    full_board = get_overall_leaderboard(limit=None)
    
    ranked_full = []
    for idx, entry in enumerate(full_board):
        ranked_full.append({
            "rollNo": entry.rollNo,
            "name": entry.name,
            "points": entry.points,
            "rank": idx + 1
        })
        
    top_10 = ranked_full[:10]
    
    token = os.getenv("VERCEL_API_TOKEN")
    config_id = os.getenv("EDGE_CONFIG_ID")
    team_id = os.getenv("TEAM_ID")
    
    if not token or not config_id:
        print("Missing VERCEL_API_TOKEN or EDGE_CONFIG_ID")
        return False
        
    url = f"https://api.vercel.com/v1/edge-config/{config_id}/items"
    if team_id:
        url += f"?teamId={team_id}"
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "items": [
            {
                "operation": "upsert",
                "key": "leaderboard_top10",
                "value": top_10
            },
            {
                "operation": "upsert",
                "key": "leaderboard_full",
                "value": ranked_full
            }
        ]
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method="PATCH")
    try:
        with urllib.request.urlopen(req) as response:
            response.read()
            return True
    except urllib.error.URLError as e:
        print(f"Failed to update Edge Config: {e}")
        if hasattr(e, 'read'):
            print(e.read())
        return False

def get_edge_leaderboard(key: str) -> list:
    """Fetch a value from Edge Config via Vercel REST API."""
    config_id = os.getenv("EDGE_CONFIG_ID")
    token = os.getenv("VERCEL_API_TOKEN")
    team_id = os.getenv("TEAM_ID")
    
    if not config_id or not token:
        print("EDGE_CONFIG_ID or VERCEL_API_TOKEN not set, skipping Edge Config read")
        return []
    
    url = f"https://api.vercel.com/v1/edge-config/{config_id}/item/{key}"
    if team_id:
        url += f"?teamId={team_id}"
    
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            # Vercel returns {"value": [...]} for individual item reads
            if isinstance(data, dict) and "value" in data:
                return data["value"]
            return data if isinstance(data, list) else []
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if hasattr(e, 'read') else ''
        print(f"Edge Config read HTTP error {e.code}: {body}")
        return []
    except Exception as e:
        print(f"Failed to read Edge Config: {e}")
        return []
