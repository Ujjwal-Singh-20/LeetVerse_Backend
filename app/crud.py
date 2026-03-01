from google.cloud import firestore
from firebase_config import db
from models import LeaderboardEntry, UserHistoryEntry
from typing import List

def update_bulk_scores_atomic(scores_data: List[dict], score_date: str, admin_email: str):
    """
    Updates multiple users' scores and attendance in a single batch/transactional way.
    Handles increments for totalPoints and attendanceSummary.
    """
    
    # Get all participants to handle missing ones
    users_ref = db.collection("users")
    all_users = users_ref.get()
    all_roll_nos = {doc.id for doc in all_users}
    
    uploaded_roll_nos = {str(s['rollNo']) for s in scores_data}
    missing_roll_nos = all_roll_nos - uploaded_roll_nos

    # Root score document metadata
    score_date_ref = db.collection("scores").document(score_date)
    score_date_ref.set({
        "uploadedBy": admin_email,
        "uploadedAt": firestore.SERVER_TIMESTAMP
    }, merge=True)

    batch = db.batch()
    
    # Process Present Participants
    for item in scores_data:
        roll_no = str(item['rollNo'])
        points = item['points']
        remarks = item.get('remarks', "")
        
        user_ref = users_ref.document(roll_no)
        participant_ref = score_date_ref.collection("participants").document(roll_no)
        
        # Update/Create User increment totals
        batch.set(user_ref, {
            "rollNo": roll_no, # Ensure rollNo exists in doc for future robustness
            "totalPoints": firestore.Increment(points),
            "attendanceSummary": {
                "daysPresent": firestore.Increment(1)
            }
        }, merge=True)
        
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
        
        # Increment daysAbsent
        batch.set(user_ref, {
            "rollNo": roll_no,
            "attendanceSummary": {
                "daysAbsent": firestore.Increment(1)
            }
        }, merge=True)
        
        #Record daily score as absent
        batch.set(participant_ref, {
            "rollNo": roll_no,
            "points": 0,
            "remarks": "N/A",
            "attendance": False,
            "status": "absent"
        })

    batch.commit()
    print(f"Firestore Update Success: Processed {len(uploaded_roll_nos)} records for {score_date} by {admin_email}")
    return len(uploaded_roll_nos)

def is_admin(email: str) -> bool:
    """
    Checks if the email exists in the 'admins' collection.
    """
    if not email:
        return False
    doc = db.collection("admins").document(email.lower()).get()
    return doc.exists

def register_user_if_not_exists(uid: str, email: str, name: str, roll_no: str):
    """
    Registers the user in Firestore if they don't already exist.
    Maintains a robust schema with placeholders for future features.
    """
    user_ref = db.collection("users").document(roll_no)
    doc = user_ref.get()
    
    if not doc.exists:
        user_ref.set({
            "uid": uid,
            "email": email,
            "name": name,
            "rollNo": roll_no,
            "totalPoints": 0,
            "attendanceSummary": {
                "daysPresent": 0,
                "daysAbsent": 0
            },
            "badges": [], # Placeholder for future robustness
            "createdAt": firestore.SERVER_TIMESTAMP
        })
    else:
        # Update UID if it changed or ensure name is current
        user_ref.set({
            "uid": uid,
            "name": name,
            "email": email, # Ensure email is stored
            "rollNo": roll_no
        }, merge=True)
        print(f"User check-in success: {roll_no} ({email})")

def get_leaderboard_for_date(score_date: str) -> List[LeaderboardEntry]:
    scores_ref = db.collection("scores").document(score_date).collection("participants")
    query = scores_ref.order_by("points", direction=firestore.Query.DESCENDING).stream()
    
    leaderboard = []
    for doc in query:
        data = doc.to_dict()
        leaderboard.append(LeaderboardEntry(
            rollNo=doc.id, 
            points=data.get("points", 0), 
            remarks=data.get("remarks", "")
        ))
    
    return leaderboard

def get_user_score_history(roll_no: str) -> List[UserHistoryEntry]:
    """
    Fetches the score history for a specific roll number by iterating through daily scores.
    This avoids the need for a Collection Group index.
    """
    history = []
    
    # 1. Get all date documents from the 'scores' collection
    scores_docs = db.collection("scores").stream()
    
    for date_doc in scores_docs:
        date_id = date_doc.id
        # 2. Check if this user exists in the 'participants' subcollection for this date
        participant_ref = db.collection("scores").document(date_id).collection("participants").document(roll_no).get()
        
        if participant_ref.exists:
            data = participant_ref.to_dict()
            history.append(UserHistoryEntry(
                date=date_id,
                points=data.get("points", 0),
                remarks=data.get("remarks", ""),
                attendance=data.get("attendance", False),
                status=data.get("status", "absent")
            ))
    
    history.sort(key=lambda x: x.date, reverse=True)
    return history

def get_overall_leaderboard(limit: int = 50) -> List[LeaderboardEntry]:
    """
    Fetches the top participants based on totalPoints from the 'users' collection.
    """
    users_ref = db.collection("users")
    query = users_ref.order_by("totalPoints", direction=firestore.Query.DESCENDING).limit(limit).stream()
    
    leaderboard = []
    for doc in query:
        data = doc.to_dict()
        leaderboard.append(LeaderboardEntry(
            rollNo=doc.id,
            points=data.get("totalPoints", 0),
            remarks="" # Total leaderboard usually doesn't have specific remarks
        ))
    
    return leaderboard

def get_program_details(program_id: str):
    doc = db.collection("programs").document(program_id).get()
    return doc.to_dict() if doc.exists else None

