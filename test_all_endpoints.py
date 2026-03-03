import requests
import firebase_admin
from firebase_admin import auth, credentials
import os
from dotenv import load_dotenv
from datetime import date, timedelta

# Initialize
load_dotenv()

cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

API_KEY = os.getenv("FIREBASE_CONFIG_API_KEY")
BASE_URL = "http://localhost:8080"#"https://leetverse-backend-latest.onrender.com"

# KIIT email for admin user
ADMIN_EMAIL = "24158130@kiit.ac.in"
NORMAL_EMAIL = "2205789@kiit.ac.in"  # Normal user for testing

def get_id_token(email):
    """Generate ID token for given email"""
    custom_token = auth.create_custom_token(email, {"email": email}).decode('utf-8')
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={API_KEY}"
    payload = {
        "token": custom_token,
        "returnSecureToken": True
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()['idToken']
    else:
        print(f"Error getting token: {response.json()}")
        return None

def test_endpoint(method, endpoint, token=None, data=None, params=None, description=""):
    """Helper function to test endpoints"""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    url = f"{BASE_URL}{endpoint}"
    
    print(f"\n{'='*70}")
    print(f"TEST: {description}")
    print(f"Method: {method.upper()}")
    print(f"URL: {url}")
    if params:
        print(f"Params: {params}")
    print(f"{'='*70}")
    
    try:
        if method.lower() == "get":
            response = requests.get(url, headers=headers, params=params, timeout=10)
        elif method.lower() == "post":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json() if response.text else 'No content'}")
        return response
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    print("\n" + "="*70)
    print("GENERATING TOKENS")
    print("="*70)
    
    # Generate tokens
    admin_token = get_id_token(ADMIN_EMAIL)
    normal_token = get_id_token(NORMAL_EMAIL)
    
    if not admin_token:
        print("Failed to generate admin token!")
        exit(1)
    
    print(f"\n✓ Admin Token Generated for: {ADMIN_EMAIL}")
    print(f"Token: {admin_token[:50]}...")
    
    if normal_token:
        print(f"\n✓ Normal User Token Generated for: {NORMAL_EMAIL}")
        print(f"Token: {normal_token[:50]}...")
    
    # Start testing endpoints
    print("\n\n" + "="*70)
    print("TESTING ENDPOINTS")
    print("="*70)
    
    # 1. Health Check (No auth required)
    test_endpoint("GET", "/", description="Health Check")
    
    # 2. Login with admin token
    test_endpoint("POST", "/login", token=admin_token, description="Login - Admin User")
    
    # 3. Get /me endpoint - Admin
    test_endpoint("GET", "/me", token=admin_token, description="Get Current User - Admin")
    
    # 4. Get /me endpoint - Normal User
    if normal_token:
        test_endpoint("GET", "/me", token=normal_token, description="Get Current User - Normal User")
    
    # 5. Get Profile - Admin (should show all users)
    test_endpoint("GET", "/profile", token=admin_token, description="Get Profile - Admin (All Users)")
    
    # 6. Get Profile - Normal User (should show only their data)
    if normal_token:
        test_endpoint("GET", "/profile", token=normal_token, description="Get Profile - Normal User (Own Data)")
    
    # 7. Get Overall Leaderboard (No auth required)
    test_endpoint("GET", "/leaderboard/overall", description="Get Overall Leaderboard")
    
    # 8. Get Leaderboard for Today
    today = date.today().isoformat()
    test_endpoint("GET", f"/leaderboard/{today}", token=admin_token, 
                 description=f"Get Leaderboard for Today ({today})")
    
    # 9. Get Leaderboard for Yesterday
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    test_endpoint("GET", f"/leaderboard/{yesterday}", token=admin_token,
                 description=f"Get Leaderboard for Yesterday ({yesterday})")
    
    # 10. Check Upload Status for Today (Admin only)
    test_endpoint("GET", "/upload-status", token=admin_token, params={"score_date": today},
                 description="Check Upload Status for Today - Admin")
    
    # 11. Get User History - Admin accessing another user's history
    test_endpoint("GET", "/user/220578900/history", token=admin_token,
                 description="Get User History - Admin Accessing User 220578900")
    
    # 12. Get User History - Normal User accessing own history
    if normal_token:
        test_endpoint("GET", "/user/220578900/history", token=normal_token,
                     description="Get User History - Normal User Accessing Own Data")
    
    # 13. Unauthorized Test - Normal user trying to access upload status
    if normal_token:
        test_endpoint("GET", "/upload-status", token=normal_token,
                     description="Unauthorized Test - Normal User Accessing Admin Endpoint")
    
    # 14. Invalid date format test
    test_endpoint("GET", "/leaderboard/invalid-date", token=admin_token,
                 description="Invalid Date Format Test")
    
    print("\n\n" + "="*70)
    print("TESTING COMPLETE")
    print("="*70)
