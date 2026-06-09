"""
AI Email Classifier
Uses OpenAI GPT to classify emails as important or not.
Falls back to rule-based classifier if OpenAI is unavailable.
"""

import os
import json
import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    email_id: str
    important: bool
    priority: str          # HIGH / MEDIUM / LOW
    category: str          # PAYMENT_ISSUE, SERVER_DOWN, SPAM, etc.
    reason: str


# ─── Rule-based Fallback ──────────────────────────────────────────────────────

IMPORTANT_KEYWORDS = [
    "urgent", "critical", "server down", "payment failed", "payment failure",
    "billing issue", "complaint", "refund", "legal", "security breach",
    "unauthorized", "hack", "lawsuit", "chargeback", "overdue", "invoice",
    "alert", "warning", "breach", "outage", "production down", "emergency",
    "copyright infringement", "unusual charges", "partnership"
]

SPAM_KEYWORDS = [
    "unsubscribe", "newsletter", "weekly digest", "flash sale", "% off",
    "promo", "coupon", "deal", "offer", "limited time", "click here",
    "activity summary", "you have new", "shipped"
]

CATEGORY_MAP = {
    "payment": "PAYMENT_ISSUE",
    "billing": "PAYMENT_ISSUE",
    "invoice": "PAYMENT_ISSUE",
    "server down": "SERVER_DOWN",
    "outage": "SERVER_DOWN",
    "production": "SERVER_DOWN",
    "complaint": "CLIENT_COMPLAINT",
    "refund": "CLIENT_COMPLAINT",
    "security": "SECURITY_ALERT",
    "breach": "SECURITY_ALERT",
    "unauthorized": "SECURITY_ALERT",
    "legal": "LEGAL",
    "lawsuit": "LEGAL",
    "copyright": "LEGAL",
    "partnership": "BUSINESS_OPPORTUNITY",
    "contract": "BUSINESS_OPPORTUNITY",
    "aws": "BILLING_ALERT",
    "charges": "BILLING_ALERT",
}


def rule_based_classify(email_id: str, subject: str, body: str, sender: str) -> ClassificationResult:
    text = (subject + " " + body).lower()

    spam_score = sum(1 for kw in SPAM_KEYWORDS if kw in text)
    important_score = sum(1 for kw in IMPORTANT_KEYWORDS if kw in text)

    if spam_score > important_score and spam_score >= 2:
        return ClassificationResult(
            email_id=email_id,
            important=False,
            priority="LOW",
            category="SPAM",
            reason="Email contains promotional or newsletter keywords."
        )

    category = "GENERAL"
    for kw, cat in CATEGORY_MAP.items():
        if kw in text:
            category = cat
            break

    if important_score >= 2 or any(kw in text for kw in ["urgent", "critical", "immediately", "emergency"]):
        priority = "HIGH" if important_score >= 3 else "MEDIUM"
        return ClassificationResult(
            email_id=email_id,
            important=True,
            priority=priority,
            category=category,
            reason=f"Email contains important keywords indicating urgency or business-critical content."
        )

    return ClassificationResult(
        email_id=email_id,
        important=False,
        priority="LOW",
        category="GENERAL",
        reason="Email does not appear to require immediate attention."
    )


# ─── OpenAI Classifier ────────────────────────────────────────────────────────

def openai_classify(email_id: str, subject: str, body: str, sender: str) -> Optional[ClassificationResult]:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key == "your-openai-api-key-here":
        return None

    try:
        from openai import OpenAI
        import httpx
        client = OpenAI(api_key=api_key, http_client=httpx.Client())

        prompt = f"""You are an email importance classifier for a business.

Analyze this email and respond ONLY with valid JSON (no markdown, no extra text).

Email:
From: {sender}
Subject: {subject}
Body: {body[:1000]}

Respond with this exact JSON structure:
{{
  "important": true or false,
  "priority": "HIGH" or "MEDIUM" or "LOW",
  "category": one of ["PAYMENT_ISSUE", "SERVER_DOWN", "CLIENT_COMPLAINT", "SECURITY_ALERT", "LEGAL", "BUSINESS_OPPORTUNITY", "BILLING_ALERT", "SPAM", "GENERAL"],
  "reason": "One clear sentence explaining your decision"
}}

Mark as important if it involves: payment failures, server outages, client complaints, security breaches, legal notices, urgent business matters, unusual billing.
Mark as NOT important if it is: newsletters, promotions, routine notifications, social media digests, shipping updates."""

        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200,
        )

        raw = response.choices[0].message.content.strip()
        # Strip markdown code blocks if present
        raw = re.sub(r"```json|```", "", raw).strip()
        data = json.loads(raw)

        return ClassificationResult(
            email_id=email_id,
            important=bool(data.get("important", False)),
            priority=data.get("priority", "LOW"),
            category=data.get("category", "GENERAL"),
            reason=data.get("reason", "AI classification.")
        )

    except Exception as e:
        logger.error(f"OpenAI classification failed: {e}")
        return None


# ─── Main Classifier Entry Point ──────────────────────────────────────────────

def classify_email(email_id: str, subject: str, body: str, sender: str) -> ClassificationResult:
    """
    Tries OpenAI first. Falls back to rule-based if OpenAI is unavailable.
    """
    result = openai_classify(email_id, subject, body, sender)
    if result is not None:
        logger.info(f"[AI] {email_id} → important={result.important}, category={result.category}")
        return result

    result = rule_based_classify(email_id, subject, body, sender)
    logger.info(f"[RULES] {email_id} → important={result.important}, category={result.category}")
    return result
