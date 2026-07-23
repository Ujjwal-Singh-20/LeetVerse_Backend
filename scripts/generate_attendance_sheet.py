import pandas as pd
import sys
import os
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Add the project root to sys.path to allow importing from 'app'
# This ensures that 'from crud import ...' works even when run from root
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

# Load environment variables explicitly from root .env
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

try:
    from app.firebase_config import db, get_coll_path
    from app.crud import get_all_admins
except ImportError:
    # Fallback for different path structures
    from firebase_config import db, get_coll_path
    from crud import get_all_admins

def generate_attendance_sheet(season, level):
    print(f"Fetching users for Season: {season}, Level: {level}...")
    users_ref = db.collection(get_coll_path("users", season, level))
    users_docs = users_ref.get()
    
    # Get admins to exclude them
    try:
        admins = {a.get("email").lower() for a in get_all_admins() if a.get("email")}
    except Exception as e:
        print(f"Warning: Could not fetch admins: {e}")
        admins = set()
    
    users_data = []
    for doc in users_docs:
        data = doc.to_dict()
        email = data.get("email", "").lower()
        if email in admins or doc.id.lower() in admins:
            continue
        
        users_data.append({
            "rollNo": doc.id,
            "name": data.get("name", ""),
            "email": data.get("email", "")
        })
    
    print(f"Found {len(users_data)} participants.")
    
    print("Fetching attendance dates...")
    scores_ref = db.collection(get_coll_path("scores", season, level))
    dates_docs = scores_ref.get()
    all_dates = sorted([doc.id for doc in dates_docs])
    print(f"Found {len(all_dates)} dates: {all_dates}")
    
    print("Fetching attendance records per date...")
    date_attendance = {}
    for date_str in all_dates:
        print(f"  Fetching for {date_str}...")
        participants_docs = db.collection(get_coll_path("scores", season, level)).document(date_str).collection("participants").get()
        date_attendance[date_str] = {doc.id: doc.to_dict().get("status", "absent") for doc in participants_docs}
    
    # Initialize attendance matrix
    attendance_matrix = []
    
    for user in users_data:
        roll_no = user["rollNo"]
        user_row = {
            "Roll Number": roll_no,
            "Name": user["name"],
            "Email": user["email"]
        }
        
        present_count = 0
        absent_count = 0
        
        for date_str in all_dates:
            status = date_attendance[date_str].get(roll_no, "absent")
            if status == "present":
                user_row[date_str] = "P"
                present_count += 1
            else:
                user_row[date_str] = "A"
                absent_count += 1
                
        user_row["Total Present"] = present_count
        user_row["Total Absent"] = absent_count
        attendance_pct = (present_count / len(all_dates) * 100) if all_dates else 0
        user_row["Attendance %"] = round(attendance_pct, 2)
        
        attendance_matrix.append(user_row)
        
    print("Generating CSV...")
    df = pd.DataFrame(attendance_matrix)
    
    # Reorder columns to have totals at the end
    cols = ["Roll Number", "Name", "Email"] + all_dates + ["Total Present", "Total Absent", "Attendance %"]
    df = df[cols]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"attendance_sheet_{season}_{level}_{timestamp}.xlsx"
    df.to_excel(filename, index=False)
    print(f"\nSUCCESS: Attendance sheet generated: {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate attendance sheet.')
    parser.add_argument('--season', type=str, default='season1', help='Season (e.g. season1)')
    parser.add_argument('--level', type=str, default='level2', help='Level (e.g. level2)')
    
    args = parser.parse_args()
    try:
        generate_attendance_sheet(args.season, args.level)
    except Exception as e:
        print(f"Error during execution: {e}")
        import traceback
        traceback.print_exc()
