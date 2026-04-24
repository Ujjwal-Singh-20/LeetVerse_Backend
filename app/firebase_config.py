import firebase_admin
from firebase_admin import credentials, firestore, auth
import os
import json
import base64
from dotenv import load_dotenv

load_dotenv()

def _load_firebase_credentials():
    # Prefer inline JSON from env in CI to avoid writing/parsing temp files.
    raw_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if raw_json:
        try:
            return credentials.Certificate(json.loads(raw_json))
        except json.JSONDecodeError:
            # Support base64-encoded JSON secrets as a fallback format.
            try:
                decoded = base64.b64decode(raw_json).decode("utf-8")
                return credentials.Certificate(json.loads(decoded))
            except Exception as exc:
                raise ValueError(
                    "Invalid FIREBASE_SERVICE_ACCOUNT_JSON. Provide raw JSON or base64-encoded JSON."
                ) from exc

    cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "serviceAccountKey.json")
    return credentials.Certificate(cred_path)

if not firebase_admin._apps:
    cred = _load_firebase_credentials()
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
