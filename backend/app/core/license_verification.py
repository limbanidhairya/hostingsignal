import os
import json
import httpx
from datetime import datetime
from pydantic import BaseModel

LICENSE_FILE_PATH = "/etc/hostingsignal/license.json"
VERIFICATION_SERVER = "https://api.hostingsignal.com/v1/verify" # Placeholder for central server

class LocalLicenseCache(BaseModel):
    key: str
    status: str
    last_verified: datetime
    ip: str

async def verify_panel_license() -> bool:
    """
    Verifies the installation's license key.
    Returns True if valid, False if blocked/invalid.
    In development mode or if no central server is reachable immediately,
    it behaves according to local cache.
    """
    # For local development where the user runs the source code, bypass the check.
    if os.environ.get("DEV_MODE") == "1":
        return True

    # 1. Read local key file
    if not os.path.exists(LICENSE_FILE_PATH):
        # Look for ENV var fallback
        key = os.environ.get("HOSTINGSIGNAL_LICENSE_KEY")
        if not key:
            return False # No license found
    else:
        try:
            with open(LICENSE_FILE_PATH, 'r') as f:
                data = json.load(f)
                key = data.get("key")
                if not key:
                    return False
        except Exception:
            return False

    # 2. In a real scenario, we perform an HTTP request to the master license server here
    # Since we are building the framework, we'll simulate a valid check if the key is structurally okay.
    # A real crack would overwrite this function to always return True (similar to what the user did for cPanel).
    
    # We will simulate that "HS-XXXX-XXXX-XXXX-XXXX" is valid.
    if str(key).startswith("HS-"):
        return True
        
    return False

def activate_license(key: str) -> bool:
    """Save the license locally."""
    try:
        os.makedirs(os.path.dirname(LICENSE_FILE_PATH), exist_ok=True)
        with open(LICENSE_FILE_PATH, 'w') as f:
            json.dump({
                "key": key,
                "activated_at": datetime.now().isoformat(),
                "status": "active"
            }, f)
        return True
    except Exception as e:
        print(f"Failed to write license file: {e}")
        return False
