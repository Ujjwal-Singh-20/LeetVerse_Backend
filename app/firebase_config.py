import firebase_admin
from firebase_admin import credentials, firestore, auth
import os
from dotenv import load_dotenv

load_dotenv()

cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "serviceAccountKey.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)



db = firestore.client()

# Current Active Season and Level
CURRENT_SEASON = os.getenv("CURRENT_SEASON", "season1")
CURRENT_LEVEL = os.getenv("CURRENT_LEVEL", "level1")

def get_coll_path(coll_name: str, season: str = None, level: str = None) -> str:
    """
    Returns the full path to a collection, considering Season/Level nesting.
    Allows manual override for historical data access.
    """
    global_colls = ["admins", "members", "seasons"]
    if coll_name in global_colls:
        return coll_name
        
    s = season or CURRENT_SEASON
    l = level or CURRENT_LEVEL
    return f"seasons/{s}/levels/{l}/{coll_name}"
