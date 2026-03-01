from fastapi import Header, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth
from firebase_config import db
from crud import is_admin, register_user_if_not_exists
import os

security = HTTPBearer()

async def verify_firebase_token(res: HTTPAuthorizationCredentials = Security(security)):
    """
    Verifies Firebase ID Token, checks for @kiit.ac.in domain,
    and determines the user role.
    """
    id_token = res.credentials
    
    try:
        # 1. Verify ID Token
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token.get("uid")
        email = decoded_token.get("email", "").lower()
        name = decoded_token.get("name", "KIIT Student")
        
        # 2. Enforce @kiit.ac.in domain
        if not email or not email.endswith("@kiit.ac.in"):
            print(f"Unauthorized access attempt from: {email}")
            raise HTTPException(status_code=403, detail="Access restricted to @kiit.ac.in emails.")
        
        # 3. Extract Roll Number
        roll_no = email.split("@")[0].upper()
        
        # 4. Check Roles
        role = "participant"
        if is_admin(email):
            role = "admin"
            
        # 5. Set Custom Claims for future robustness (Faster client/rules check)
        # This makes 'role' and 'rollNo' available directly in the Firebase token
        auth.set_custom_user_claims(uid, {
            "role": role,
            "rollNo": roll_no
        })
            
        # 6. Register User (Robustness/Badges)
        register_user_if_not_exists(uid, email, name, roll_no)
        
        # Attach our metadata to the token dict for this specific request
        decoded_token.update({
            "role": role,
            "rollNo": roll_no,
            "email": email,
            "name": name
        })
        
        print(f"Auth Success: {email} | Role: {role} | RollNo: {roll_no}")
        return decoded_token
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid authentication: {str(e)}")

async def get_current_user(decoded_token: dict = Depends(verify_firebase_token)):
    return decoded_token

async def get_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required.")
    return current_user

def set_user_role_claim(uid: str, role: str):
    """
    Optional: Set custom claims in Firebase Auth for faster client-side checks.
    """
    auth.set_custom_user_claims(uid, {"role": role})
