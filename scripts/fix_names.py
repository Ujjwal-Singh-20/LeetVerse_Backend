# KEEP NAMES CORRECTLY UPDATED FROM OFFICIAL REGISTRAION SHEET

"""
NAME	ROLL NUMBER

"""


import sys
import os
import pandas as pd
import math

# Add the app directory to the path so we can import from firebase_config
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
from app.firebase_config import db

def is_invalid_name(name):
    """
    Checks if a name is 'NAN', floats, none, blank, or composed of digits.
    """
    if name is None:
        return True
    if isinstance(name, float) and math.isnan(name):
        return True
    
    name_str = str(name).strip().upper()
    if name_str in ['NAN', 'NONE', 'NV', 'N/A', '', 'NULL']:
        return True
    
    # Check if name is composed entirely of digits (ignoring spaces/decimals just in case)
    # e.g. "2405600" or equivalent
    clean_name = name_str.replace(' ', '').replace('.', '')
    if clean_name.isdigit():
        return True
        
    return False

def update_names_from_excel(file_path):
    print(f"Reading {file_path}...")
    df = pd.read_excel(file_path)
    
    # Normalize columns to lowercase for easier matching
    df.columns = [str(c).strip().lower() for c in df.columns]
    print(f"Columns found: {df.columns.tolist()}")
    
    # Attempt to locate roll number and name columns
    roll_col = None
    name_col = None
    
    for col in df.columns:
        if 'roll' in col:
            roll_col = col
        if 'name' in col:
            name_col = col
            
    if not roll_col or not name_col:
        print("Error: Could not find 'roll number' and/or 'name' columns in the sheet.")
        print("Please ensure the sheet has headers like 'Name' and 'Roll Number'.")
        return
        
    print(f"Using column '{roll_col}' for Roll Numbers.")
    print(f"Using column '{name_col}' for Names.")
    
    updated_count = 0
    skipped_count = 0
    not_found_count = 0
    
    batch = db.batch()
    operations_in_batch = 0
    
    print("\nScanning Firebase users...")
    
    for _, row in df.iterrows():
        roll_val = row[roll_col]
        new_name_val = row[name_col]
        
        if pd.isna(roll_val) or pd.isna(new_name_val):
            continue
            
        if pd.api.types.is_number(roll_val):
            roll_no = str(int(roll_val)).strip()
        else:
            roll_no = str(roll_val).strip()
            
        if not roll_no or roll_no == 'nan':
            # Skip empty roll numbers completely
            continue
            
        new_name = str(new_name_val).strip().upper()
        
        user_ref = db.collection("users").document(roll_no)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            data = user_doc.to_dict()
            current_name = data.get("name")
            
            if is_invalid_name(current_name):
                # Update document and clean NaN or digit-only names
                print(f"Updating {roll_no}: '{current_name}' -> '{new_name}'")
                batch.update(user_ref, {"name": new_name})
                operations_in_batch += 1
                updated_count += 1
                
                # Firestore batch limit is 500 operations
                if operations_in_batch >= 450:
                    batch.commit()
                    batch = db.batch()
                    operations_in_batch = 0
            else:
                skipped_count += 1
        else:
            not_found_count += 1
                
    if operations_in_batch > 0:
        batch.commit()
        
    print(f"\n=== Summary ===")
    print(f"Updated successfully: {updated_count} users")
    print(f"Skipped (already valid): {skipped_count} users")
    print(f"Not found in database: {not_found_count} users")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Update invalid names in Firestore from Excel")
    parser.add_argument("--file_path", help="Path to the Excel file containing correct names")
    args = parser.parse_args()
    
    if os.path.exists(args.file_path):
        update_names_from_excel(args.file_path)
    else:
        print(f"Error: File not found at path: {args.file_path}")
