#  USE TO DOWNLOAD THE QUESTION OF CLASS,ASSIGNMENT,EXTRA     AND THE PROGRESS OF EACH USER ON EACH ASSIGNED QUESTION

import sys
import os
import argparse
import pandas as pd
from datetime import datetime

# Adjust path to import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))
from firebase_config import db, get_coll_path

def export_practice_data(season, level):
    print(f"Exporting practice data for Season: {season}, Level: {level}...")
    
    # 1. Fetch Curriculum
    print("Fetching curriculum...")
    curr_docs = db.collection(get_coll_path("curriculum", season, level)).order_by("date").stream()
    curriculum = {}
    for doc in curr_docs:
        curriculum[doc.id] = doc.to_dict()
        
    # 2. Fetch Users
    print("Fetching users...")
    users_docs = db.collection(get_coll_path("users", season, level)).stream()
    
    data = []
    
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
            
        row = {
            "Roll No": roll_no,
            "Name": u.get("name", ""),
            "Leetcode Username": u.get("leetcode_username", "NOT_LINKED"),
            "Total Completed (All Time)": len(completed_slugs)
        }
        
        # For each date in curriculum
        for date_str, c_data in curriculum.items():
            class_qs = set(c_data.get("class_questions", []))
            assign_qs = set(c_data.get("assigned_questions", []))
            
            # Class Questions
            if class_qs:
                done_class = class_qs.intersection(completed_slugs)
                missing_class = class_qs - completed_slugs
                row[f"{date_str} Class ({len(class_qs)})"] = f"{len(done_class)}/{len(class_qs)} Done" + (f" | Missing: {', '.join(missing_class)}" if missing_class else "")
            
            # Assigned Questions
            if assign_qs:
                done_assign = assign_qs.intersection(completed_slugs)
                missing_assign = assign_qs - completed_slugs
                row[f"{date_str} Assigned ({len(assign_qs)})"] = f"{len(done_assign)}/{len(assign_qs)} Done" + (f" | Missing: {', '.join(missing_assign)}" if missing_assign else "")
                
            # Extra Practice
            extras = extra_practice.get(date_str, [])
            if extras:
                row[f"{date_str} Extra"] = ", ".join(extras)
            else:
                row[f"{date_str} Extra"] = ""
                
        data.append(row)
        
    print(f"Processed {len(data)} users. Generating Excel...")
    
    df = pd.DataFrame(data)
    
    # Save in the directory where the script is executed
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"practice_report_{season}_{level}_{timestamp}.xlsx"
    
    df.to_excel(filename, index=False)
    print(f"Success! Report saved to {os.path.abspath(filename)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Export practice data to Excel.')
    parser.add_argument('--season', type=str, default='season1', help='Season (e.g. season1)')
    parser.add_argument('--level', type=str, default='level2', help='Level (e.g. level2)')
    
    args = parser.parse_args()
    export_practice_data(args.season, args.level)
