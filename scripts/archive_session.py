import os
import sys
import json
import urllib.request

# Ensure we can import from the app directory
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

try:
    from crud import archive_session_to_edge
    from dotenv import load_dotenv
    load_dotenv()
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def run_archive(season, level):
    print(f">>> Archiving Top 10 for {season} : {level} to Edge Config...")
    success = archive_session_to_edge(season, level)
    if success:
        print(f"SUCCESS: {season}:{level} archived in Edge Config.")
    else:
        print(f"FAILED: No data found for '{season}:{level}' or API error.")
        # List available to help user
        from firebase_config import db
        print("\nAvailable Sessions in Firestore:")
        seasons = db.collection("seasons").stream()
        for s in seasons:
            levels = db.collection(f"seasons/{s.id}/levels").stream()
            ls = [l.id for l in levels]
            print(f"  - Season: {s.id} (Levels: {', '.join(ls)})")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Archive session rankings to Edge Config')
    parser.add_argument('--season', type=str, help='Season ID', required=True)
    parser.add_argument('--level', type=str, help='Level ID', required=True)
    
    args = parser.parse_args()
    run_archive(args.season, args.level)
