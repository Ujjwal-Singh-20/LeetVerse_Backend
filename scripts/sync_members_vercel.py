import os
import sys

# Ensure we can import from the app directory
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

try:
    from crud_members import sync_members_to_blob
    from dotenv import load_dotenv
    load_dotenv()
except ImportError as e:
    print(f"Error importing modules: {e}")
    print(f"Current Sys Path: {sys.path}")
    sys.exit(1)

def run_sync():
    print(">>> Starting Members Vercel Sync Script...")
    
    # Check for required env vars
    required_vars = ["BLOB_READ_WRITE_TOKEN", "VERCEL_API_TOKEN", "EDGE_CONFIG_ID"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    print("\n[1/1] Syncing Members to Vercel (Blob + Edge Config)...")
    success = sync_members_to_blob()
    if success:
        print("\n>>> ALL SYNC OPERATIONS COMPLETED SUCCESSFULLY.")
    else:
        print("\n>>> SYNC COMPLETED WITH ERRORS.")
        sys.exit(1)

if __name__ == "__main__":
    run_sync()
