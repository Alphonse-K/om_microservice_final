# seed_initial_emails_multi.py
import logging
from datetime import datetime, timezone
from src.core.database import SessionLocal
from src.services.gmail_service import fetch_recent_emails
from src.services.email_service import create_email, get_email_by_message_id
from src.utils.parser import parse_transaction_email

# --- CONFIG: list of Gmail accounts and their tokens ---
GMAIL_ACCOUNTS = [
    {"label": "airtime", "token_path": "/app/credentials/airtime_token.json"},
    {"label": "cashout", "token_path": "/app/credentials/cashout_token.json"},
]

NUM_EMAILS = 2  # fetch the 2 most recent emails per account

# --- LOGGER ---
logger = logging.getLogger("seed_emails")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

def fetch_and_store_emails(label: str, token_path: str):
    db = SessionLocal()
    try:
        emails = fetch_recent_emails(token_path, max_results=NUM_EMAILS)
        logger.info(f"[{label}] Fetched {len(emails)} emails from Gmail.")

        for msg in emails:
            msg_id = msg.get("id")
            if get_email_by_message_id(db, msg_id):
                logger.info(f"[{label}] Skipping duplicate email {msg_id}")
                continue

            body_text = msg.get("body") or ""
            # detect type from body content
            body_lower = body_text.lower()
            if "retrait de" in body_lower:
                detected_type = "cashout"
            elif "depot vers" in body_lower:
                detected_type = "cashin"
            elif "rechargement" in body_lower:
                detected_type = "airtime"
            else:
                detected_type = "unknown"

            parsed = parse_transaction_email(body_text)

            payload = {
                "gmail_account": detected_type,
                "message_id": msg_id,
                "subject": msg.get("subject"),
                "sender": msg.get("sender"),
                "body": body_text,
                "received_at": datetime.fromtimestamp(msg.get("internalDate", 0), tz=timezone.utc),
                "parsed_transaction_id": parsed.get("transaction_id"),
            }

            try:
                email_obj = create_email(db, payload)
                logger.info(f"[{label}] Inserted email {msg_id} into database.")
            except Exception as db_err:
                logger.error(f"[{label}] Failed to insert email {msg_id}: {db_err}")

    finally:
        db.close()
        logger.info(f"[{label}] DB session closed.")

def main():
    for account in GMAIL_ACCOUNTS:
        fetch_and_store_emails(account["label"], account["token_path"])

if __name__ == "__main__":
    main()
