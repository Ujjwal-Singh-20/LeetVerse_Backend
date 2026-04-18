import firebase_admin
from firebase_admin import credentials, firestore
import os
import time
from dotenv import load_dotenv

load_dotenv()

# Configuration
# SEASON_ID = "season1"
# LEVEL_ID = "level1"
COLLECTIONS_TO_MOVE = ["users", "scores", "programs"]
BATCH_SIZE = 50  # Number of documents to fetch per batch
RETRY_ATTEMPTS = 3
DELAY_BETWEEN_BATCHES = 0.5  # Seconds

# Initialize Firebase
cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "serviceAccountKey.json")
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def copy_document_recursive(doc_snapshot, target_coll_ref):
    """Copies a single document and all its subcollections recursively."""
    doc_id = doc_snapshot.id
    data = doc_snapshot.to_dict()
    
    # Retry logic for document write
    for attempt in range(RETRY_ATTEMPTS):
        try:
            target_doc_ref = target_coll_ref.document(doc_id)
            target_doc_ref.set(data)
            break
        except Exception as e:
            if attempt == RETRY_ATTEMPTS - 1:
                print(f"    [ERROR] Failed to copy document {doc_id} after {RETRY_ATTEMPTS} attempts: {e}")
                return
            time.sleep(2 ** attempt)

    # Copy subcollections
    try:
        subcollections = doc_snapshot.reference.collections()
        for sub_coll in subcollections:
            copy_collection_paginated(sub_coll, target_doc_ref.collection(sub_coll.id))
    except Exception as e:
        print(f"    [ERROR] Failed to fetch subcollections for {doc_id}: {e}")

def copy_collection_paginated(source_coll_ref, target_coll_ref):
    """Copies a collection in paginated batches to avoid timeouts."""
    print(f"  Migrating collection: {source_coll_ref.id}")
    
    last_doc = None
    while True:
        query = source_coll_ref.order_by("__name__").limit(BATCH_SIZE)
        if last_doc:
            query = query.start_after(last_doc)
        
        docs = list(query.stream())
        if not docs:
            break
        
        for doc in docs:
            print(f"    Copying: {doc.id}")
            copy_document_recursive(doc, target_coll_ref)
        
        last_doc = docs[-1]
        time.sleep(DELAY_BETWEEN_BATCHES)

def main():
    print(f"Starting robust migration to seasons/{SEASON_ID}/levels/{LEVEL_ID}...")
    
    # Create the season and level documents if they don't exist
    db.collection("seasons").document(SEASON_ID).set({"id": SEASON_ID, "initialized": True}, merge=True)
    db.collection("seasons").document(SEASON_ID).collection("levels").document(LEVEL_ID).set({"id": LEVEL_ID, "initialized": True}, merge=True)
    
    for coll_name in COLLECTIONS_TO_MOVE:
        print(f"\n>>> Migrating root collection: {coll_name}")
        source_ref = db.collection(coll_name)
        target_ref = db.collection("seasons").document(SEASON_ID).collection("levels").document(LEVEL_ID).collection(coll_name)
        
        copy_collection_paginated(source_ref, target_ref)
        print(f"<<< Finished root collection: {coll_name}")

    print("\nMigration complete!")

if __name__ == "__main__":
    main()
