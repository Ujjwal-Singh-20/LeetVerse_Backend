import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv

load_dotenv()

cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "serviceAccountKey.json")
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

print("Listing Seasons:")
seasons = db.collection("seasons").stream()
for s in seasons:
    print(f"Season: {s.id}")
    levels = db.collection(f"seasons/{s.id}/levels").stream()
    for l in levels:
        print(f"  Level: {l.id}")
