import pandas as pd
from datetime import datetime

data = [
    {"NAME": "User One", "EMAIL ID": "2405001@kiit.ac.in", "SCORE": 15, "DATE": "2026-03-01"},
    {"NAME": "null", "EMAIL ID": "2405002@kiit.ac.in", "SCORE": 10, "DATE": "2026-03-01"}, # Should be skipped
    {"NAME": "", "EMAIL ID": "2405003@kiit.ac.in", "SCORE": 12, "DATE": "2026-03-01"},     # Should use rollNo (2405003)
    {"NAME": "User Four", "EMAIL ID": "2405004@kiit.ac.in", "SCORE": 8, "DATE": "02/03/2026"}, # Date format test
    {"NAME": "None", "EMAIL ID": "2405005@kiit.ac.in", "SCORE": 5, "DATE": "2026-03-02"},     # Fallback to rollNo
]

df = pd.DataFrame(data)
df.to_excel("tests/sample_scores.xlsx", index=False)
print("Created tests/sample_scores.xlsx")
