"""
Email Reader Module
Supports:
  - Mock JSON data (default, no credentials needed)
  - Gmail via OAuth2
  - Generic IMAP
"""

import os
import json
import email
import imaplib
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RawEmail:
    id: str
    sender: str
    subject: str
    body: str
    timestamp: Optional[datetime]


# ─── Mock Email Reader ────────────────────────────────────────────────────────

def read_mock_emails() -> List[RawEmail]:
    mock_path = os.getenv("MOCK_EMAIL_PATH", "/app/data/mock_emails.json")
    fallback = Path(__file__).parent.parent / "data" / "mock_emails.json"

    path = mock_path if Path(mock_path).exists() else str(fallback)

    try:
        with open(path, "r", encoding="utf-8") as f:
            emails = json.load(f)

        result = []
        for e in emails:
            ts = None
            if e.get("timestamp"):
                try:
                    ts = datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
                except Exception:
                    pass
            result.append(RawEmail(
                id=e["id"],
                sender=e["from"],
                subject=e["subject"],
                body=e["body"],
                timestamp=ts,
            ))
        return result
    except Exception as ex:
        logger.error(f"Failed to read mock emails: {ex}")
        return []


# ─── IMAP Email Reader ────────────────────────────────────────────────────────

def read_imap_emails(limit: int = 20) -> List[RawEmail]:
    host = os.getenv("IMAP_HOST", "imap.gmail.com")
    port = int(os.getenv("IMAP_PORT", "993"))
    user = os.getenv("IMAP_USER", "")
    password = os.getenv("IMAP_PASSWORD", "")

    if not user or not password:
        logger.warning("IMAP credentials not set. Falling back to mock data.")
        return read_mock_emails()

    try:
        mail = imaplib.IMAP4_SSL(host, port)
        mail.login(user, password)
        mail.select("inbox")

        _, msg_nums = mail.search(None, "UNSEEN")
        ids = msg_nums[0].split()
        ids = ids[-limit:]  # Take last N unread

        result = []
        for num in ids:
            _, data = mail.fetch(num, "(RFC822)")
            raw = data[0][1]
            msg = email.message_from_bytes(raw)

            subject = msg.get("Subject", "(No Subject)")
            sender = msg.get("From", "unknown")
            date_str = msg.get("Date", "")

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

            ts = None
            try:
                from email.utils import parsedate_to_datetime
                ts = parsedate_to_datetime(date_str)
            except Exception:
                pass

            email_id = f"imap_{num.decode()}"
            result.append(RawEmail(
                id=email_id,
                sender=sender,
                subject=subject,
                body=body[:2000],
                timestamp=ts,
            ))

        mail.logout()
        return result

    except Exception as ex:
        logger.error(f"IMAP read failed: {ex}. Falling back to mock data.")
        return read_mock_emails()


# ─── Gmail OAuth Reader ───────────────────────────────────────────────────────

def read_gmail_emails(limit: int = 20) -> List[RawEmail]:
    """
    Reads Gmail using the Gmail API (OAuth2).
    Requires credentials.json in the project root.
    """
    creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "/app/credentials.json")
    token_path = os.getenv("GMAIL_TOKEN_PATH", "/app/token.json")

    if not Path(creds_path).exists():
        logger.warning("Gmail credentials.json not found. Falling back to mock data.")
        return read_mock_emails()

    try:
        import pickle
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        import base64

        SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
        creds = None

        if Path(token_path).exists():
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                logger.error("Gmail OAuth token invalid or missing. Run auth flow first.")
                return read_mock_emails()

        service = build("gmail", "v1", credentials=creds)
        results = service.users().messages().list(userId="me", q="is:unread", maxResults=limit).execute()
        messages = results.get("messages", [])

        result = []
        for msg_ref in messages:
            msg = service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute()
            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}

            subject = headers.get("Subject", "(No Subject)")
            sender = headers.get("From", "unknown")
            date_str = headers.get("Date", "")

            body = ""
            parts = msg["payload"].get("parts", [])
            for part in parts:
                if part.get("mimeType") == "text/plain":
                    data = part["body"].get("data", "")
                    body = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
                    break

            if not body:
                data = msg["payload"]["body"].get("data", "")
                if data:
                    body = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")

            ts = None
            try:
                from email.utils import parsedate_to_datetime
                ts = parsedate_to_datetime(date_str)
            except Exception:
                pass

            result.append(RawEmail(
                id=msg_ref["id"],
                sender=sender,
                subject=subject,
                body=body[:2000],
                timestamp=ts,
            ))

        return result

    except Exception as ex:
        logger.error(f"Gmail API failed: {ex}. Falling back to mock data.")
        return read_mock_emails()


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def fetch_emails() -> List[RawEmail]:
    mode = os.getenv("EMAIL_SOURCE", "mock").lower()

    if mode == "gmail":
        return read_gmail_emails()
    elif mode == "imap":
        return read_imap_emails()
    else:
        return read_mock_emails()
