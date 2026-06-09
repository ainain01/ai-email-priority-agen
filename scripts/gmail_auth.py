"""
Gmail OAuth2 Authentication Helper
Run this ONCE on your local machine (not in Docker) to generate token.json.
After running, copy token.json to your project root.

Usage:
    pip install google-auth-oauthlib google-api-python-client
    python scripts/gmail_auth.py
"""

import os
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

CREDS_PATH = Path(__file__).parent.parent / "credentials.json"
TOKEN_PATH  = Path(__file__).parent.parent / "token.json"


def main():
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_PATH.exists():
                print(f"ERROR: credentials.json not found at {CREDS_PATH}")
                print("Download it from Google Cloud Console → APIs & Services → Credentials")
                return

            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    print(f"✅ Authentication successful!")
    print(f"   token.json saved to: {TOKEN_PATH}")
    print(f"   Copy this file to your project root before running Docker.")


if __name__ == "__main__":
    main()
