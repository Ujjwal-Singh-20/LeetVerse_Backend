import sys
import os
import json

# Adjust path to import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))
from firebase_config import db

def derive_schema(collection_ref, depth=0, max_depth=5):
    if depth > max_depth:
        return {"error": "Max depth reached"}

    schema = {}
    
    # Get a sample of documents to infer fields and check for sub-collections
    docs = collection_ref.limit(1).get()
    
    if not docs:
        return "Empty Collection"

    for doc in docs:
        doc_data = doc.to_dict()
        field_types = {k: str(type(v).__name__) for k, v in doc_data.items()}
        
        # Check for sub-collections within this document
        sub_collections = doc.reference.collections()
        subs = {}
        for sub in sub_collections:
            subs[sub.id] = derive_schema(sub, depth + 1, max_depth)
            
        schema = {
            "fields": field_types,
            "sub_collections": subs
        }
        
    return schema

def main():
    print("Deriving Firestore Schema...")
    root_schema = {}
    
    # Get root collections
    root_collections = db.collections()
    for coll in root_collections:
        print(f"Analyzing root collection: {coll.id}...")
        root_schema[coll.id] = derive_schema(coll)
        
    output_path = "firestore_schema.json"
    with open(output_path, "w") as f:
        json.dump(root_schema, f, indent=4)
    
    print(f"\nSchema derived successfully! Saved to {os.path.abspath(output_path)}")
    print("\nRoot Collections found:", list(root_schema.keys()))

if __name__ == "__main__":
    main()
