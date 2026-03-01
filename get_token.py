import requests
import firebase_admin
from firebase_admin import auth, credentials
import os

# 1. Initialize Admin SDK (if not already done)
# cred_path = "leetversetest-firebase-adminsdk-fbsvc-7545cf3a68.json"
from dotenv import load_dotenv

load_dotenv()

cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

# 2. Configuration
API_KEY = os.getenv("FIREBASE_CONFIG_API_KEY")
EMAIL = "24158130@kiit.ac.in"#admin email, this token can do all things        "2205789@kiit.ac.in" normal user email, is restricted from endpoints like /user/.../history

def get_id_token_via_admin():
    # A. Generate a Custom Token using Admin SDK (Including email claim)
    custom_token = auth.create_custom_token(EMAIL, {"email": EMAIL}).decode('utf-8')
    
    # B. Exchange Custom Token for an ID Token via REST API
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={API_KEY}"
    payload = {
        "token": custom_token,
        "returnSecureToken": True
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()['idToken']
    else:
        print(f"Error: {response.json()}")
        return None

if __name__ == "__main__":
    token = get_id_token_via_admin()
    if token:
        print("\n--- YOUR ID TOKEN ---")
        print(token)
        print("\n--- CURL HEADER ---")
        print(f'-H "Authorization: Bearer {token}"')