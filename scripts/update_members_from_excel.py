import sys
import os
import argparse
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Ensure we can import from the app directory if needed
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

load_dotenv()

def initialize_firebase():
    if not firebase_admin._apps:
        service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
        if not service_account_path or not os.path.exists(service_account_path):
            print(f"Error: Service account file '{service_account_path}' not found.")
            sys.exit(1)
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
    return firestore.client()

def clean_value(val):
    if pd.isna(val) or val == "N/A" or val == "Not created yet" or val == "No":
        return ""
    return str(val).strip()

def sanitize_link(val):
    val = clean_value(val)
    if not val:
        return ""
    if not (val.startswith("http://") or val.startswith("https://")):
        return ""
    return val

def extract_drive_id(url):
    # Just store the raw URL for now, the frontend can handle it or we assume it's direct link
    return clean_value(url)

def update_members_from_excel(excel_path):
    db = initialize_firebase()
    
    try:
        df = pd.read_excel(excel_path)
        print(f"Loaded {len(df)} rows from {excel_path}")
    except Exception as e:
        print(f"Failed to read Excel file: {e}")
        sys.exit(1)
    
    # Expected columns based on the provided screenshot
    required_cols = ['NAME', 'ROLL NUMBER', 'DOMAIN', 'Position', 'LinkedIn Link', 'Github Link', 'Instagram Link', 'Profile Pic']
    
    for col in required_cols:
        if col not in df.columns:
            print(f"Warning: Column '{col}' not found in Excel sheet. Please verify columns.")
    
    # Process rows
    batch = db.batch()
    batch_count = 0
    domains_processed = set()
    
    for index, row in df.iterrows():
        try:
            domain_cell = clean_value(row.get('DOMAIN', ''))
            # Split by comma to support multiple domains
            domains = [d.strip() for d in domain_cell.split(',') if d.strip()]
            name = clean_value(row.get('NAME', '')).upper()
            roll_no = clean_value(row.get('ROLL NUMBER', ''))

            if not domains or not name or not roll_no:
                continue

            for domain_id in domains:
                # Ensure the domain document exists with a name field
                if domain_id not in domains_processed:
                    domain_ref = db.collection('members').document(domain_id)
                    batch.set(domain_ref, {'name': domain_id}, merge=True)
                    domains_processed.add(domain_id)
                    batch_count += 1

                person_ref = db.collection('members').document(domain_id).collection('persons').document(roll_no)

                doc_data = {
                    "name": name,
                    "github": sanitize_link(row.get('Github Link', '')),
                    "instagram": sanitize_link(row.get('Instagram Link', '')),
                    "linkedin": sanitize_link(row.get('LinkedIn Link', '')),
                    # "photoUrl": "", #sanitize_link(row.get('Profile Pic', '')),      doing manual link upload via cloudinary
                    "position": clean_value(row.get('Position', '')),
                    "rollNo": roll_no
                }

                batch.set(person_ref, doc_data, merge = True)
                batch_count += 1
            batch_count += 1
            
            if batch_count >= 400:  # Firestore batch limit is 500
                batch.commit()
                batch = db.batch()
                batch_count = 0
                
        except Exception as e:
            print(f"Error processing row {index}: {e}")
            
    if batch_count > 0:
        batch.commit()
        
    print(f"Successfully processed members for domains: {', '.join(domains_processed)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update members from an Excel sheet")
    parser.add_argument("excel_path", help="Path to the Excel sheet")
    args = parser.parse_args()
    
    update_members_from_excel(args.excel_path)
