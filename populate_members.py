import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv

load_dotenv()

# Path to service account key
# Looking for the file in the current directory (backend/)
# service_account_path = 'leetversetest-firebase-adminsdk-fbsvc-7545cf3a68.json'
service_account_path=os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

if not os.path.exists(service_account_path):
    print(f"Error: Service account file {service_account_path} not found.")
    exit(1)

# Initialize Firebase Admin SDK
cred = credentials.Certificate(service_account_path)
firebase_admin.initialize_app(cred)

db = firestore.client()

sample_data = {
    'president': {
        'persons': [
            {
                'name': "Ujjwal Singh",
                'photoUrl': "https://api.dicebear.com/7.x/avataaars/svg?seed=Ujjwal",
                'github': "https://github.com/Ujjwal-Singh-20",
                'linkedin': "https://linkedin.com/in/ujjwal-singh-20",
                'instagram': "https://instagram.com/ujjwal_singh_20"
            },
            {
                'name': "Member Two",
                'photoUrl': "https://api.dicebear.com/7.x/avataaars/svg?seed=Member2",
                'github': "https://github.com/member2",
                'linkedin': "https://linkedin.com/in/member2",
                'instagram': ""
            }
        ]
    },
    'vice-president': {
        'persons': [
            {
                'name': "Member Three",
                'photoUrl': "https://api.dicebear.com/7.x/avataaars/svg?seed=Member3",
                'github': "https://github.com/member3",
                'linkedin': "https://linkedin.com/in/member3",
                'instagram': "https://instagram.com/member3"
            },
            {
                'name': "Member Four",
                'photoUrl': "https://api.dicebear.com/7.x/avataaars/svg?seed=Member4",
                'github': "https://github.com/member4",
                'linkedin': "https://linkedin.com/in/member4",
                'instagram': "https://instagram.com/member4"
            }
        ]
    }
}

def seed():
    print("Starting database seeding...")
    for role, data in sample_data.items():
        role_ref = db.collection('members').document(role)
        
        # Set role document
        role_ref.set({'name': role.replace('-', ' ').title()})
        print(f"Set role: {role}")

        persons_coll = role_ref.collection('persons')
        
        # To avoid duplicates if running multiple times, we might want to clear or just add
        # For seeding, we'll just add
        for person in data['persons']:
            persons_coll.add(person)
            print(f"  Added {person['name']} as {role}")

    print("Seeding completed successfully!")

if __name__ == "__main__":
    try:
        seed()
    except Exception as e:
        print(f"An error occurred: {e}")
