# from datetime import datetime
# from src.core.database import SessionLocal
# from src.services.gmail_service import fetch_recent_emails
# from src.services.email_service import create_email, get_email_by_message_id
# from src.utils.parser import parse_transaction_email
# from src.worker_app import celery_app
# from src.models.email_message import EmailMessage
# import logging

# logger = logging.getLogger("gmail_sync")
# logger.setLevel(logging.INFO)
# handler = logging.StreamHandler()
# formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
# handler.setFormatter(formatter)
# logger.addHandler(handler)


# @celery_app.task(bind=True, max_retries=3, name="src.tasks.gmail_sync.sync_account")
# def sync_account(self, label: str, token_path: str):
#     db = SessionLocal()
#     try:
#         # --- Determine latest email timestamp (seconds) ---
#         latest_email = (
#             db.query(EmailMessage)
#             .filter_by(gmail_account=label)
#             .order_by(EmailMessage.received_at.desc())
#             .first()
#         )
#         after_ts = int(latest_email.received_at.timestamp()) if latest_email else 0
#         logger.info(f"[{label}] Fetching emails after timestamp: {after_ts}")

#         # --- Fetch emails ---
#         try:
#             emails = fetch_recent_emails(
#                 token_path, max_results=100, query=f"after:{after_ts}"
#             )
#             logger.info(f"[{label}] Fetched {len(emails)} emails.")
#         except Exception as fetch_err:
#             logger.error(f"[{label}] Error fetching emails: {fetch_err}")
#             raise self.retry(exc=fetch_err, countdown=5)

#         # --- Process each email ---
#         for msg in emails:
#             msg_id = msg.get("id")

#             # Skip duplicates
#             if get_email_by_message_id(db, msg_id):
#                 logger.info(f"[{label}] Skipping duplicate email: {msg_id}")
#                 continue

#             # Parse email safely
#             try:
#                 parsed = parse_transaction_email(msg.get("body", "") or "")
#             except Exception as parse_err:
#                 logger.warning(f"[{label}] Failed to parse email {msg_id}: {parse_err}")
#                 parsed = {}

#             body_text = (msg.get("body") or "")

#             # Auto detect transaction type based on body content
#             body_lower = body_text.lower()

#             if "retrait de" in body_lower:
#                 detected_type = "cashout"
#             elif "depot vers" in body_lower:
#                 detected_type = "cashin"
#             elif "rechargement" in body_lower:
#                 detected_type = "airtime"
#             else:
#                 detected_type = "unknown"

#             # Parse the email to extract tx details
#             parsed = parse_transaction_email(body_text)

#             payload = {
#                 "gmail_account": detected_type,
#                 "message_id": msg_id,
#                 "subject": msg.get("subject"),
#                 "sender": msg.get("sender"),
#                 "body": body_text,
#                 "parsed_transaction_id": parsed.get("transaction_id"),
#             }

#             try:
#                 email_obj = create_email(db, payload)
#                 # Schedule confirmation
#                 from src.tasks.email_confirmation import process_email_confirmation

#                 process_email_confirmation.delay(email_obj.id)

#                 logger.info(f"[{label}] Stored email and scheduled confirmation for {msg_id}.")
#             except Exception as db_err:
#                 logger.error(f"[{label}] DB error storing email {msg_id}: {db_err}")
#                 continue

#     except Exception as exc:
#         logger.error(f"[{label}] Unexpected error: {exc}")
#         raise self.retry(exc=exc, countdown=10)

#     finally:
#         db.close()
#         logger.info(f"[{label}] DB session closed.")
from datetime import datetime, timezone
from src.core.database import SessionLocal
from src.services.gmail_service import fetch_recent_emails
from src.services.email_service import create_email, get_email_by_message_id
from src.utils.parser import parse_transaction_email
from src.worker_app import celery_app
from src.models.email_message import EmailMessage
import logging

logger = logging.getLogger("gmail_sync")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


@celery_app.task(bind=True, max_retries=3, name="src.tasks.gmail_sync.sync_account")
def sync_account(self, label: str, token_path: str):
    db = SessionLocal()
    try:
        # --- Determine latest email timestamp ---
        latest_email = (
            db.query(EmailMessage)
            .filter_by(gmail_account=label)
            .order_by(EmailMessage.received_at.desc())
            .first()
        )
        after_ts = int(latest_email.received_at.timestamp()) if latest_email else 0
        logger.info(f"[{label}] Fetching emails after timestamp: {after_ts}")

        # --- Fetch emails ---
        try:
            emails = fetch_recent_emails(
                token_path, max_results=100, query=f"after:{after_ts}"
            )
            logger.info(f"[{label}] Fetched {len(emails)} emails.")
        except Exception as fetch_err:
            logger.error(f"[{label}] Error fetching emails: {fetch_err}")
            raise self.retry(exc=fetch_err, countdown=5)

        # --- Process each email ---
        for msg in emails:
            msg_id = msg.get("id")

            # Skip duplicates
            if get_email_by_message_id(db, msg_id):
                logger.info(f"[{label}] Skipping duplicate email: {msg_id}")
                continue

            body_text = msg.get("body") or ""

            # Auto detect transaction type
            body_lower = body_text.lower()
            if "retrait de" in body_lower:
                detected_type = "cashout"
            elif "depot vers" in body_lower:
                detected_type = "cashin"
            elif "rechargement" in body_lower:
                detected_type = "airtime"
            else:
                detected_type = "unknown"

            # Parse transaction info
            try:
                parsed = parse_transaction_email(body_text)
            except Exception as parse_err:
                logger.warning(f"[{label}] Failed to parse email {msg_id}: {parse_err}")
                parsed = {}

            # Prepare payload
            payload = {
                "gmail_account": detected_type,
                "message_id": msg_id,
                "subject": msg.get("subject"),
                "sender": msg.get("sender"),
                "body": body_text,
                "parsed_transaction_id": parsed.get("transaction_id"),
                "received_at": msg.get("received_at", datetime.now(timezone.utc)),
            }

            # Store in DB
            try:
                email_obj = create_email(db, payload)
                from src.tasks.email_confirmation import process_email_confirmation
                process_email_confirmation.delay(email_obj.id)
                logger.info(f"[{label}] Stored email and scheduled confirmation for {msg_id}.")
            except Exception as db_err:
                logger.error(f"[{label}] DB error storing email {msg_id}: {db_err}")
                continue

    except Exception as exc:
        logger.error(f"[{label}] Unexpected error: {exc}")
        raise self.retry(exc=exc, countdown=10)

    finally:
        db.close()
        logger.info(f"[{label}] DB session closed.")
