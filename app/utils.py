import pandas as pd
from io import BytesIO
from typing import List, Dict

def parse_excel_scores(file_content: bytes) -> List[Dict]:
    """
    Parses an Excel file and returns a list of dictionaries with rollNo, points, and name.
    Expected columns: 'Roll Number', 'Points', 'Name' (or 'Student Name'), 'Remarks' (optional)
    """
    df = pd.read_excel(BytesIO(file_content))
    
    # Normalize column names to handle variations
    df.columns = [c.strip().lower() for c in df.columns]
    
    # Mapping for common column names
    mapping = {
        'roll number': 'rollNo',
        'rollno': 'rollNo',
        'points': 'points',
        'score': 'points',
        'name': 'name',
        'student name': 'name',
        'remarks': 'remarks'
    }
    
    # Additional fuzzy matching for columns
    for col in df.columns:
        if 'total_score' in col:
            mapping[col] = 'points'
        elif 'email' in col:
            mapping[col] = 'email'
    
    data = []
    for _, row in df.iterrows():
        entry = {}
        for col, target in mapping.items():
            if col in df.columns:
                val = row[col]
                if target == 'name' and pd.notna(val):
                    entry[target] = str(val).strip().upper()
                elif target == 'email' and pd.notna(val):
                    # Extract rollNo from email prefix (e.g., 2405600@kiit.ac.in -> 2405600)
                    email_str = str(val).split('@')[0].strip()
                    if 'rollNo' not in entry:  # Only if rollNo not already set by a direct column
                        entry['rollNo'] = email_str
                else:
                    entry[target] = val
        
        if 'rollNo' in entry and 'points' in entry:
            # Clean rollNo to avoid .0 for numeric values (common in pandas/excel)
            roll_val = entry['rollNo']
            if pd.api.types.is_number(roll_val) and not pd.isna(roll_val):
                if float(roll_val).is_integer():
                    entry['rollNo'] = str(int(roll_val))
                else:
                    entry['rollNo'] = str(roll_val)
            else:
                entry['rollNo'] = str(roll_val)
            
            try:
                entry['points'] = int(entry['points'])
            except (ValueError, TypeError):
                entry['points'] = 0
                
            entry['remarks'] = str(entry.get('remarks', '')) if pd.notna(entry.get('remarks')) else ""
            data.append(entry)
            
    return data
