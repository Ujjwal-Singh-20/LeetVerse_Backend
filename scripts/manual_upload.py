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

from app.crud import update_bulk_scores_atomic
from app.firebase_config import db

def parse_and_upload(file_path):
    print(f"Reading file: {file_path}")
    df = pd.read_excel(file_path)
    
    # Normalize columns to upper case for consistent access
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    print(f"Columns found: {list(df.columns)}")
    
    # Support both 'EMAIL ID' and 'EMAIL'
    email_col = 'EMAIL' if 'EMAIL' in df.columns else 'EMAIL ID'
    required_cols = ['NAME', email_col, 'SCORE', 'DATE']
    
    for col in required_cols:
        if col not in df.columns:
            print(f"Error: Missing required column '{col}'")
            print(f"Available columns: {list(df.columns)}")
            sys.exit(1)
            
    # Filtering and preprocessing
    processed_data = []
    for index, row in df.iterrows():
        name_raw = str(row.get('NAME', ''))
        name = name_raw.strip()
        email = str(row.get(email_col, '')).strip()
        score = row.get('SCORE', 0)
        date_val = row.get('DATE')
        
        # Skip entries where name is "null" (case-insensitive)
        if name.lower() == 'null':
            print(f"Row {index+2}: Skipping 'null' name.")
            continue
            
        # Extract rollNo from email
        roll_no = email.split('@')[0]
        
        # If name is blank or NaN, use rollNo as name
        if not name or name.lower() == 'nan' or name_raw == 'None' or name == '':
            name = roll_no
            
        # Handle Date formatting
        formatted_date = None
        if pd.isna(date_val):
            print(f"Row {index+2}: Skipping due to missing date.")
            continue
            
        if isinstance(date_val, datetime):
            formatted_date = date_val.strftime('%Y-%m-%d')
        elif hasattr(date_val, 'strftime'):
            formatted_date = date_val.strftime('%Y-%m-%d')
        else:
            date_str = str(date_val).strip()
            try:
                # Try common formats
                for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y'):
                    try:
                        formatted_date = datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
                        break
                    except ValueError:
                        continue
                if not formatted_date:
                    # Try pandas to_datetime as fallback
                    formatted_date = pd.to_datetime(date_str).strftime('%Y-%m-%d')
            except Exception as e:
                print(f"Row {index+2}: Error parsing date '{date_val}': {e}")
                continue

        processed_data.append({
            'rollNo': roll_no,
            'name': name.upper(),
            'points': int(score) if pd.notna(score) else 0,
            'date': formatted_date,
            'remarks': 'Manual Upload'
        })

    if not processed_data:
        print("No valid data to upload.")
        return

    # Group by date
    grouped = {}
    for item in processed_data:
        d = item['date']
        if d not in grouped:
            grouped[d] = []
        grouped[d].append(item)

    # Get admin email for metadata
    admin_emails = os.getenv("ADMIN_EMAILS", "admin@kiit.ac.in")
    admin_email = admin_emails.split(',')[0].strip()
    
    print(f"\nProcessing {len(processed_data)} entries across {len(grouped)} dates...")
    
    for score_date, scores_list in grouped.items():
        print(f"Uploading {len(scores_list)} scores for date: {score_date}...")
        try:
            count = update_bulk_scores_atomic(scores_list, score_date, admin_email)
            print(f"Successfully updated/re-uploaded {count} entries for {score_date}.")
        except Exception as e:
            print(f"Error uploading for {score_date}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload scores from Excel to Firebase")
    parser.add_argument("--path", required=True, help="Path to the Excel file")
    args = parser.parse_args()
    
    if not os.path.exists(args.path):
        print(f"Error: File {args.path} not found.")
        sys.exit(1)
        
    try:
        parse_and_upload(args.path)
        print("\nManual upload process completed.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
