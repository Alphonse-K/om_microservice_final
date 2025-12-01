def store_and_confirm_email(db, payload, create_email_fn, process_confirmation_fn):
    from sqlalchemy.exc import IntegrityError

    try:
        email_obj = create_email_fn(db, payload)
        process_confirmation_fn.delay(email_obj.id)
        return email_obj
    except IntegrityError:
        db.rollback()
        print(f"Email with message_id {payload['message_id']} already exists. Skipping.")
        return None


def backfill_emails(token_path, label, create_email_fn, process_confirmation_fn):
    """
    Generic function to backfill emails for any transaction type.
    """
    from src.services.gmail_service import fetch_recent_emails
    from src.core.database import SessionLocal

    db = SessionLocal()
    try:
        emails = fetch_recent_emails(token_path, max_results=100)
        print(f"Fetched {len(emails)} emails for backfill ({label})")

        for msg in emails:
            payload = {
                "gmail_account": label,
                "message_id": msg.get("id"),
                "subject": msg.get("subject"),
                "sender": msg.get("sender"),
                "body": msg.get("body"),
                "parsed_transaction_id": None,  # Optional: parse transaction ID here
            }
            store_and_confirm_email(db, payload, create_email_fn, process_confirmation_fn)

    finally:
        db.close()


if __name__ == "__main__":

    import os

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # /app/src
    PROJECT_ROOT = os.path.dirname(BASE_DIR)  # /app

    TOKEN_PATH_WITHDRAWAL = os.path.join(PROJECT_ROOT, "credentials", "withdrawal_token.json")
    TOKEN_PATH_AIRTIME = os.path.join(PROJECT_ROOT, "credentials", "airtime_token.json")

    # Lazy imports to avoid circular dependencies
    from src.services.email_service import create_email as create_withdrawal_email
    from src.tasks.email_confirmation import process_email_confirmation as process_withdrawal_confirmation


    # Backfill Withdrawals
    backfill_emails(
        TOKEN_PATH_WITHDRAWAL,
        label="withdrawal",
        create_email_fn=create_withdrawal_email,
        process_confirmation_fn=process_withdrawal_confirmation
    )

    # Backfill Airtime
    backfill_emails(
        TOKEN_PATH_AIRTIME,
        label="airtime",
        create_email_fn=create_withdrawal_email,
        process_confirmation_fn=process_withdrawal_confirmation
    )
