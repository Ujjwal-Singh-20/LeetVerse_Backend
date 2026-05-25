import os
import json
import urllib.request
from typing import List, Dict, Any
from firebase_admin import firestore
from firebase_config import db
from utils import json_serial

def fetch_all_members_from_db() -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetches all members grouped by domain/role.
    Returns:
        {
            "President": [...],
            "Web Dev": [...],
            "Marketing and PR": [...]
        }
    """
    members_data = {}
    
    try:
        # Get all domains/roles
        domains_ref = db.collection('members').stream()
        
        for domain_doc in domains_ref:
            domain_id = domain_doc.id
            persons = []
            
            # Get persons in this domain
            persons_ref = db.collection('members').document(domain_id).collection('persons').stream()
            for person_doc in persons_ref:
                person_data = person_doc.to_dict()
                # Ensure id is included just in case
                person_data['id'] = person_doc.id
                persons.append(person_data)
                
            if persons:
                members_data[domain_id] = persons
                
        return members_data
    except Exception as e:
        print(f"Error fetching members from DB: {e}")
        return {}

def sync_members_to_blob() -> bool:
    """
    Fetches members from Firestore, uploads to Vercel Blob, 
    and updates Edge Config with the new Blob URL.
    """
    token = os.getenv("BLOB_READ_WRITE_TOKEN")
    config_id = os.getenv("EDGE_CONFIG_ID")
    vercel_token = os.getenv("VERCEL_API_TOKEN")
    
    if not token or not config_id or not vercel_token:
        print("Missing required Vercel environment variables (BLOB_READ_WRITE_TOKEN, EDGE_CONFIG_ID, VERCEL_API_TOKEN).")
        return False
        
    members_data = fetch_all_members_from_db()
    
    if not members_data:
        print("No members data found or error fetching.")
        return False
        
    # 1. Upload to Vercel Blob
    upload_url = "https://blob.vercel-storage.com/members/latest_members.json?access=public"
    req = urllib.request.Request(
        upload_url, 
        data=json.dumps(members_data, default=json_serial).encode('utf-8'), 
        headers={
            "Authorization": f"Bearer {token}", 
            "Content-Type": "application/json"
        }, 
        method="PUT"
    )
    
    blob_url = None
    try:
        with urllib.request.urlopen(req) as response:
            res_body = json.loads(response.read().decode('utf-8'))
            blob_url = res_body.get("url")
            print(f"Successfully uploaded members to blob: {blob_url}")
    except Exception as e:
        print(f"Failed to upload members to blob: {e}")
        return False
        
    if not blob_url:
        return False
        
    # 2. Update Edge Config
    edge_url = f"https://api.vercel.com/v1/edge-config/{config_id}/items"
    payload = {
        "items": [
            {
                "operation": "upsert", 
                "key": "members_blob_url", 
                "value": blob_url
            }
        ]
    }
    
    edge_req = urllib.request.Request(
        edge_url, 
        data=json.dumps(payload).encode('utf-8'), 
        headers={
            "Authorization": f"Bearer {vercel_token}", 
            "Content-Type": "application/json"
        }, 
        method="PATCH"
    )
    
    try:
        with urllib.request.urlopen(edge_req) as response:
            if response.status in [200, 201, 202]:
                print("Successfully updated Edge Config with members_blob_url.")
                return True
            else:
                print(f"Failed to update Edge Config: Status {response.status}")
                return False
    except Exception as e:
        print(f"Failed to update Edge Config: {e}")
        return False
