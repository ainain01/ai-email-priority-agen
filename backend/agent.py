"""
AI Email Agent - Main Processing Loop
Fetches emails → classifies → stores in DB → provides data for dashboard
"""

import os
import logging
import time
from datetime import datetime
from typing import List, Dict, Any

from database import init_db, get_session, ProcessedEmail
from email_reader import fetch_emails
from classifier import classify_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("agent")

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL_SECONDS", "120"))  # default: 2 minutes


def process_emails() -> int:
    """
    Main processing cycle:
    1. Fetch emails from configured source
    2. Skip already-processed emails (duplicate prevention)
    3. Classify each new email
    4. Store result in DB
    Returns count of newly processed emails.
    """
    db = get_session()
    emails = fetch_emails()
    new_count = 0

    try:
        for raw in emails:
            # Duplicate prevention
            existing = db.query(ProcessedEmail).filter(ProcessedEmail.id == raw.id).first()
            if existing:
                logger.debug(f"Skipping already-processed email: {raw.id}")
                continue

            # Classify
            result = classify_email(
                email_id=raw.id,
                subject=raw.subject,
                body=raw.body,
                sender=raw.sender,
            )

            # Persist
            record = ProcessedEmail(
                id=raw.id,
                sender=raw.sender,
                subject=raw.subject,
                body_preview=raw.body[:300] if raw.body else "",
                is_important=result.important,
                priority=result.priority,
                category=result.category,
                reason=result.reason,
                received_at=raw.timestamp,
                processed_at=datetime.utcnow(),
            )
            db.add(record)
            db.commit()
            new_count += 1

            status = "✅ IMPORTANT" if result.important else "⬜ ignored"
            logger.info(f"{status} | [{result.priority}] {result.category} | {raw.subject[:60]}")

    except Exception as e:
        logger.error(f"Error during processing: {e}")
        db.rollback()
    finally:
        db.close()

    return new_count


def get_important_emails() -> List[Dict[str, Any]]:
    """Returns all important emails from the DB for the dashboard."""
    db = get_session()
    try:
        records = (
            db.query(ProcessedEmail)
            .filter(ProcessedEmail.is_important == True)
            .order_by(ProcessedEmail.processed_at.desc())
            .all()
        )
        return [
            {
                "id": r.id,
                "sender": r.sender,
                "subject": r.subject,
                "body_preview": r.body_preview,
                "priority": r.priority,
                "category": r.category,
                "reason": r.reason,
                "received_at": r.received_at.isoformat() if r.received_at else None,
                "processed_at": r.processed_at.isoformat() if r.processed_at else None,
            }
            for r in records
        ]
    finally:
        db.close()


def get_stats() -> Dict[str, Any]:
    """Returns summary statistics for the dashboard."""
    db = get_session()
    try:
        total = db.query(ProcessedEmail).count()
        important = db.query(ProcessedEmail).filter(ProcessedEmail.is_important == True).count()
        high = db.query(ProcessedEmail).filter(ProcessedEmail.priority == "HIGH", ProcessedEmail.is_important == True).count()
        medium = db.query(ProcessedEmail).filter(ProcessedEmail.priority == "MEDIUM", ProcessedEmail.is_important == True).count()
        low_imp = db.query(ProcessedEmail).filter(ProcessedEmail.priority == "LOW", ProcessedEmail.is_important == True).count()
        return {
            "total_processed": total,
            "total_important": important,
            "ignored": total - important,
            "high": high,
            "medium": medium,
            "low": low_imp,
        }
    finally:
        db.close()


def run_agent_loop():
    """Continuous polling loop (used when running as standalone process)."""
    init_db()
    logger.info(f"🚀 AI Email Agent started. Polling every {POLL_INTERVAL}s")
    while True:
        logger.info("🔍 Checking for new emails...")
        count = process_emails()
        logger.info(f"✔ Processed {count} new emails. Sleeping {POLL_INTERVAL}s...")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_agent_loop()
