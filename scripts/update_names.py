import pandas as pd
import sys
import os
import argparse
from dotenv import load_dotenv

# Add the project root to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from app.firebase_config import db

def update_missing_names(file_path):
    print(f"Reading file: {file_path}")
    df = pd.read_excel(file_path)
    
    # Normalize columns
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    # Support both 'EMAIL ID' and 'EMAIL'
    email_col = 'EMAIL' if 'EMAIL' in df.columns else 'EMAIL ID'
    required_cols = ['NAME', email_col]
    
    for col in required_cols:
        if col not in df.columns:
            print(f"Error: Missing required column '{col}'")
            print(f"Available columns: {list(df.columns)}")
            sys.exit(1)
            
    print(f"File loaded with {len(df)} rows.")
    
    updated_count = 0
    skipped_count = 0
    not_found_count = 0
    already_had_name_count = 0
    
    # Process in batches for Firestore efficiency (though naming updates are usually fewer)
    batch = db.batch()
    batch_size = 0
    
    for index, row in df.iterrows():
        new_name_raw = str(row.get('NAME', '')).strip()
        email = str(row.get(email_col, '')).strip()
        
        if not email or email.lower() == 'nan':
            continue
            
        roll_no = email.split('@')[0]
        
        # Skip if the new name provided is "null" or empty
        if not new_name_raw or new_name_raw.lower() == 'null':
            continue
            
        user_ref = db.collection('users').document(roll_no)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            not_found_count += 1
            print(f"Row {index+2}: User {roll_no} not found in database. Skipping.")
            continue
            
        current_data = user_doc.to_dict()
        current_name = str(current_data.get('name', '')).strip()
        
        # CONDITION: Only update if name is empty, is the rollNo, or is "NULL"
        should_update = (
            not current_name or 
            current_name == roll_no or 
            current_name.upper() == 'NULL' or
            current_name.lower() == 'nan'
        )
        
        if should_update:
            batch.update(user_ref, {'name': new_name_raw.upper()})
            updated_count += 1
            batch_size += 1
            print(f"Row {index+2}: Updating {roll_no} -> {new_name_raw.upper()}")
        else:
            already_had_name_count += 1
            # print(f"Row {index+2}: User {roll_no} already has name '{current_name}'. Skipping.")

        # Commit batch every 400 operations
        if batch_size >= 400:
            batch.commit()
            batch = db.batch()
            batch_size = 0

    # Final commit
    if batch_size > 0:
        batch.commit()

    print("\n--- Summary ---")
    print(f"Total rows processed: {len(df)}")
    print(f"Successfully updated: {updated_count}")
    print(f"Users not found:      {not_found_count}")
    print(f"Users already named:  {already_had_name_count}")
    print("----------------")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update user names in Firestore if they are currently set to rollNo")
    parser.add_argument("--path", required=True, help="Path to the Excel file with EMAIL and NAME")
    args = parser.parse_args()
    
    if not os.path.exists(args.path):
        print(f"Error: File {args.path} not found.")
        sys.exit(1)
        
    try:
        update_missing_names(args.path)
        print("\nName update process completed.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
