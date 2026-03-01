import pandas as pd
from io import BytesIO
from typing import List, Dict

def parse_excel_scores(file_content: bytes) -> List[Dict]:
    """
    Parses an Excel file and returns a list of dictionaries with rollNo and points.
    Expected columns: 'Roll Number', 'Points', 'Remarks' (optional)
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
        'remarks': 'remarks'
    }
    
    data = []
    for _, row in df.iterrows():
        entry = {}
        for col, target in mapping.items():
            if col in df.columns:
                entry[target] = row[col]
        
        if 'rollNo' in entry and 'points' in entry:
            # Clean rollNo to avoid .0 for numeric values (common in pandas/excel)
            roll_val = entry['rollNo']
            if pd.api.types.is_number(roll_val) and not pd.isna(roll_val):
                if float(roll_val).is_integer():
                    entry['rollNo'] = int(roll_val)
            
            entry['points'] = int(entry['points'])
            entry['remarks'] = str(entry.get('remarks', '')) if pd.notna(row.get('remarks')) else ""
            data.append(entry)
            
    return data
