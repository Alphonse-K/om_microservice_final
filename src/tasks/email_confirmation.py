from src.worker_app import celery_app
from src.core.database import SessionLocal
from src.models.email_message import EmailMessage
from src.utils.parser import parse_transaction_email
from src.services.confirmation.matching_engine import find_matching_transaction
from src.services.confirmation.confirmation_handler import confirm_transaction
import logging

# Configure a logger for the worker
logger = logging.getLogger("gmail_sync")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


@celery_app.task(bind=True, max_retries=3, name="src.tasks.email_confirmation.process_email_confirmation")
def process_email_confirmation(self, email_id: int):
    db = SessionLocal()
    try:
        email = db.get(EmailMessage, email_id)
        if not email:
            return

        # --- Parse email ---
        parsed = parse_transaction_email(email.body or "")
        if not parsed:
            logger.warning(f"[Email {email.id}] No transaction detected in email body.")
            return

        # --- Enforce SUCCESS ONLY ---
        if parsed.get("status") != "success":
            logger.warning(
                f"[Email {email.id}] Email does NOT contain a success phrase → skipping confirmation."
            )
            return

        # --- Try matching the transaction ---
        tx = find_matching_transaction(db, parsed)
        if not tx:
            logger.warning(
                f"[Email {email.id}] No matching transaction found (msisdn={parsed.get('msisdn')}, amount={parsed.get('amount')})."
            )
            return

        # --- Confirm the transaction ---
        confirm_transaction(db, tx, parsed, email)
        logger.info(f"[Email {email.id}] Transaction {tx.id} marked as SUCCESS.")

    except Exception as e:
        raise self.retry(exc=e, countdown=5)

    finally:
        db.close()
