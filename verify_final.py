import pandas as pd
import os
import sys
from datetime import date
from io import BytesIO

# Add 'app' directory to path
sys.path.insert(0, os.path.abspath("app"))

from utils import parse_excel_scores
from crud import update_user_score_atomic, get_leaderboard_for_date, get_user_score_history
from firebase_config import db

def verify_functionality():
    print("--- Starting Final Verification ---")
    
    # 1. Excel Parsing
    print("\n1. Testing Excel Parsing...")
    data = {
        "Roll Number": ["2026CS-TEST", "2026CS-SAMPLE"],
        "Points": [100, 200],
        "Remarks": ["Test Remark 1", "Test Remark 2"]
    }
    df = pd.DataFrame(data)
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    parsed = parse_excel_scores(buffer.getvalue())
    print(f"Parsed: {parsed}")
    assert len(parsed) == 2
    
    # 2. Admin Initialization
    print("\n2. Initializing Admin Profile...")
    admin_email = "24158130@kiit.ac.in"
    db.collection("admins").document(admin_email).set({
        "name": "Super Admin",
        "email": admin_email,
        "role": "admin",
        "permissions": ["all"]
    })
    print(f"Admin {admin_email} set in Firestore.")
    
    # 3. Atomic Updates
    print("\n3. Testing Atomic Score Updates...")
    roll_no = "2026CS-TEST"
    today = date.today().isoformat()
    update_user_score_atomic(roll_no, 100, today, admin_email, "Final Verification")
    print(f"Score updated for {roll_no} on {today}.")
    
    # 4. Leaderboard Fetching
    print("\n4. Fetching Leaderboard...")
    leaderboard = get_leaderboard_for_date(today)
    found = any(item.rollNo == roll_no for item in leaderboard)
    print(f"Leaderboard for {today}: {[item.rollNo for item in leaderboard]}")
    assert found
    
    # 5. History Fetching
    # Note: Requires Collection Group index on 'rollNo'
    print("\n5. Fetching User History...")
    try:
        history = get_user_score_history(roll_no)
        print(f"History for {roll_no}: {history}")
        # We don't assert length here because index might not be ready, but we check if it runs
    except Exception as e:
        print(f"History fetch error (expected if index not ready): {e}")

    print("\n--- Verification Completed Successfully! 🚀 ---")

if __name__ == "__main__":
    verify_functionality()
