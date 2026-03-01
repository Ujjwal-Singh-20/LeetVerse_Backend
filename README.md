# LeetVerse Backend

FastAPI backend integrated with Firebase Firestore for managing participant scores, leaderboard, and user history.

## Setup Instructions

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Firebase Configuration**:
   - Place your Firebase Service Account key file in the root directory.
   - Update `.env` with the path: `FIREBASE_SERVICE_ACCOUNT_PATH=your-file.json`.
   - Also set `FIREBASE_CONFIG_API_KEY` for client-side token exchange.     
   `under project settings->general-> firebase config -> apiKey`

3. **Environment Variables**:
   Create a `.env` file from `.env.example`:
   ```env
   FIREBASE_SERVICE_ACCOUNT_PATH=leetversetest-firebase-adminsdk-fbsvc-7545cf3a68.json
   FIREBASE_CONFIG_API_KEY=your_firebase_api_key
   ```

4. **Run the Server**:
   ```bash
   python app/main.py
   ```
   The API will be available at `http://localhost:8000`.

---

## Authentication & Token Generation

LeetVerse uses **Firebase ID Tokens** for authentication. All endpoints (except public ones, if any) require a `Bearer` token in the `Authorization` header.

### Generating a Token for Testing
You can use the provided `get_token.py` script to generate a valid ID token for any `@kiit.ac.in` email.

1. Open `get_token.py`.
2. Update the `EMAIL` variable to the user you want to impersonate:
   - Use an admin email (e.g., `24158130@kiit.ac.in`) for admin access.
   - Use a student email (e.g., `2205789@kiit.ac.in`) for participant access.
3. Run the script:
   ```bash
   python get_token.py
   ```
4. Copy the `CURL HEADER` output (e.g., `-H "Authorization: Bearer <token>"`).

---

## Roles and Privileges

| Feature | Participant (User) | Admin |
| :--- | :---: | :---: |
| View own profile (`/me`, `/profile`) | ✅ | ✅ |
| View overall leaderboard | ✅ | ✅ |
| View daily leaderboard | ✅ | ✅ |
| View own history | ✅ | ✅ |
| View **all** users details (`/profile`) | ❌ | ✅ |
| Upload scores (`/upload-excel`) | ❌ | ✅ |
| View **any** user's history | ❌ | ✅ |

---

## API Endpoints & Curl Examples

### 1. User Authentication Check
**Endpoint:** `GET /me`  
Check if your token is valid and see your assigned role.

```bash
curl -X GET "http://localhost:8000/me" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. Login
**Endpoint:** `POST /login`  
Used by the frontend to initiate/verify a login session.

```bash
curl -X POST "http://localhost:8000/login" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. User Profile
**Endpoint:** `GET /profile`  
- **Admin:** Returns a list of all registered users.
- **User:** Returns the user's personal Firestore document.

```bash
curl -X GET "http://localhost:8000/profile" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Upload Daily Scores (Admin Only)
**Endpoint:** `POST /upload-excel`  
Uploads an `.xlsx` file containing roll numbers and points.

```bash
curl -X POST "http://localhost:8000/upload-excel" \
     -H "Authorization: Bearer ADMIN_TOKEN" \
     -F "file=@path/to/your/scores.xlsx"
```

### 5. Overall Leaderboard
**Endpoint:** `GET /leaderboard/overall`  
Returns the cumulative rankings for all users.

```bash
curl -X GET "http://localhost:8000/leaderboard/overall" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

### 6. Daily Leaderboard
**Endpoint:** `GET /leaderboard/{date}`  
Returns rankings for a specific date (Format: `YYYY-MM-DD`).

```bash
curl -X GET "http://localhost:8000/leaderboard/2026-02-26" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

### 7. User Score History
**Endpoint:** `GET /user/{roll_no}/history`  
- Users can only view their own history.
- Admins can view any user's history.

```bash
# Example for user viewing their own history (e.g., 2205789)
curl -X GET "http://localhost:8000/user/2205789/history" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Project Structure
- `app/main.py`: Main FastAPI entry point and routes.
- `app/auth.py`: Firebase token verification and role logic.
- `app/crud.py`: Firestore database operations.
- `app/utils.py`: Excel parsing and helper functions.
- `get_token.py`: Utility for generating ID tokens for development.
