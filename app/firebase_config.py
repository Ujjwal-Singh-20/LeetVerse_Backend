import firebase_admin
from firebase_admin import credentials, firestore, auth
import os
import json
import base64
from dotenv import load_dotenv

load_dotenv()

def _load_firebase_credentials():
    # 1. Render Secret File Support (Priority for Render Deployments)
    render_secret_path = "/etc/secrets/leetverse-a7324-firebase-adminsdk-fbsvc-5eedee1ba1.json"
    if os.path.exists(render_secret_path):
        return credentials.Certificate(render_secret_path)

    # 2. Prefer inline JSON from env in CI to avoid writing/parsing temp files.
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

    # 3. Local / Env Variable Fallback
    cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "leetverse-a7324-firebase-adminsdk-fbsvc-5eedee1ba1.json")
    
    # Check if the user specified a filename via env var, and see if it's in /etc/secrets
    if cred_path.startswith("./"):
        filename = cred_path[2:]
        alt_secret_path = f"/etc/secrets/{filename}"
        if os.path.exists(alt_secret_path):
            return credentials.Certificate(alt_secret_path)
            
    if not os.path.exists(cred_path):
        if os.path.exists("serviceAccountKey.json"):
            cred_path = "serviceAccountKey.json" # Legacy fallback
        elif os.path.exists("leetverse-a7324-firebase-adminsdk-fbsvc-5eedee1ba1.json"):
            cred_path = "leetverse-a7324-firebase-adminsdk-fbsvc-5eedee1ba1.json"
        
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
