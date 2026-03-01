import pandas as pd

data = {
    'Roll Number': ['2026CS123', '2026CS456', '2026CS789'],
    'Points': [100, 150, 200],
    'Remarks': ['Good job', 'Excellent', 'Perfect']
}

df = pd.DataFrame(data)
df.to_excel('test_scores.xlsx', index=False)
print("test_scores.xlsx created successfully.")
