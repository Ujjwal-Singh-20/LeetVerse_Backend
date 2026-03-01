import firebase_admin
from firebase_admin import credentials, firestore
import os
from datetime import date
from dotenv import load_dotenv
load_dotenv()

# Initialize Firebase
cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")#"leetversetest-firebase-adminsdk-fbsvc-7545cf3a68.json"
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def populate():
    # 1. Add Admins
    admins = ["24158130@kiit.ac.in", "admin@kiit.ac.in"]
    for email in admins:
        db.collection("admins").document(email.lower()).set({"active": True})
        print(f"Added admin: {email}")

    # 2. Add Users
    users = [
        {"rollNo": "24158130", "name": "Ujjwal", "email": "24158130@kiit.ac.in", "totalPoints": 100},
        {"rollNo": "2205123", "name": "John Doe", "email": "2205123@kiit.ac.in", "totalPoints": 50},
        {"rollNo": "2205456", "name": "Jane Smith", "email": "2205456@kiit.ac.in", "totalPoints": 75},
        {"rollNo": "2205789", "name": "Alice Brown", "email": "2205789@kiit.ac.in", "totalPoints": 120},
    ]
    
    for u in users:
        db.collection("users").document(u["rollNo"]).set({
            "name": u["name"],
            "email": u["email"],
            "rollNo": u["rollNo"],
            "totalPoints": u["totalPoints"],
            "attendanceSummary": {"daysPresent": 5, "daysAbsent": 1},
            "badges": ["pioneer"],
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        print(f"Added user: {u['rollNo']}")

    # 3. Add Sample Scores
    today = date.today().isoformat()
    score_date_ref = db.collection("scores").document(today)
    score_date_ref.set({"uploadedBy": "admin@kiit.ac.in", "uploadedAt": firestore.SERVER_TIMESTAMP})
    
    for u in users:
        score_date_ref.collection("participants").document(u["rollNo"]).set({
            "rollNo": u["rollNo"],
            "points": 10,
            "remarks": "Daily score",
            "attendance": True,
            "status": "present"
        })
        print(f"Added daily score for: {u['rollNo']}")

if __name__ == "__main__":
    populate()
    print("\nFirebase population complete.")
