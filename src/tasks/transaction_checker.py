from datetime import datetime, timezone, timedelta
from src.core.database import SessionLocal
from src.models.transaction import DepositTransaction, WithdrawalTransaction, AirtimePurchase
import logging

logger = logging.getLogger("transaction_checker")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

TIMEOUT = timedelta(days=1)  # 24 hours

def mark_stale_transactions():
    db = SessionLocal()
    now = datetime.now(timezone.utc)

    try:
        models = [DepositTransaction, WithdrawalTransaction, AirtimePurchase]

        for Model in models:
            stale = (
                db.query(Model)
                .filter(
                    Model.status.in_(["created", "initiated", "pending", "processing"]),
                    Model.created_at <= now - TIMEOUT
                )
                .all()
            )

            for tx in stale:
                tx.status = "failed"
                tx.error_message = "No confirmation email received within 24 hours"
                db.commit()
                logger.info(f"{Model.__name__} ID={tx.id} marked as FAILED after timeout.")

    finally:
        db.close()

# Celery wrapper
from src.worker_app import celery_app

@celery_app.task(bind=True, max_retries=3, name="src.tasks.transaction_checker.mark_stale_transactions_task")
def mark_stale_transactions_task(self):
    try:
        mark_stale_transactions()
    except Exception as e:
        # Retry after 10 seconds
        raise self.retry(exc=e, countdown=10)
