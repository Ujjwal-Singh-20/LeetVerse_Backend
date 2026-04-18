import pandas as pd
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Add the project root to sys.path to allow importing from 'app'
# This ensures that 'from crud import ...' works even when run from root
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

# Load environment variables explicitly from root .env
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

try:
    from app.firebase_config import db
    from app.crud import get_all_admins
except ImportError:
    # Fallback for different path structures
    from firebase_config import db
    from crud import get_all_admins

def generate_attendance_sheet():
    print("Fetching users...")
    users_ref = db.collection("users")
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
    scores_ref = db.collection("scores")
    dates_docs = scores_ref.get()
    all_dates = sorted([doc.id for doc in dates_docs])
    print(f"Found {len(all_dates)} dates: {all_dates}")
    
    print("Fetching attendance records per date...")
    date_attendance = {}
    for date_str in all_dates:
        print(f"  Fetching for {date_str}...")
        participants_docs = db.collection("scores").document(date_str).collection("participants").get()
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
    filename = f"attendance_sheet_{timestamp}.xlsx"
    df.to_excel(filename, index=False)
    print(f"\nSUCCESS: Attendance sheet generated: {filename}")

if __name__ == "__main__":
    try:
        generate_attendance_sheet()
    except Exception as e:
        print(f"Error during execution: {e}")
        import traceback
        traceback.print_exc()
