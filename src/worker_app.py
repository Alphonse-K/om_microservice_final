from celery import Celery
from datetime import timedelta
from src.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Autodiscover task modules
celery_app.autodiscover_tasks(["src.tasks"])

# Force import so Celery registers tasks
import src.tasks.gmail_sync
import src.tasks.email_confirmation
import src.tasks.transaction_checker
import src.tasks.transaction_queue


celery_app.conf.beat_schedule = {

    # --------------------------------------------------------
    # 1. WITHDRAWAL (Same Gmail account as deposit)
    # --------------------------------------------------------
    "sync-withdrawal": {
        "task": "src.tasks.gmail_sync.sync_account",
        "schedule": timedelta(seconds=int(settings.GMAIL_FETCH_INTERVAL)),
        "args": (
            "cashout",
            settings.GMAIL_WITHDRAWAL_TOKEN,  # SAME TOKEN for deposit/withdrawal
        ),
    },

    # --------------------------------------------------------
    # 2. DEPOSIT (Same Gmail account as withdrawal)
    # --------------------------------------------------------
    "sync-deposit": {
        "task": "src.tasks.gmail_sync.sync_account",
        "schedule": timedelta(seconds=int(settings.GMAIL_FETCH_INTERVAL)),
        "args": (
            "cashin",
            settings.GMAIL_WITHDRAWAL_TOKEN,  # SAME TOKEN
        ),
    },

    # --------------------------------------------------------
    # 3. AIRTIME (Separate Gmail account)
    # --------------------------------------------------------
    "sync-airtime": {
        "task": "src.tasks.gmail_sync.sync_account",
        "schedule": timedelta(seconds=int(settings.GMAIL_AIRTIME_INTERVAL)),
        "args": (
            "airtime",
            settings.GMAIL_AIRTIME_TOKEN,  # NEW TOKEN for AIRTIME
        ),
    },

    # --------------------------------------------------------
    # 4. Check stale transactions
    # --------------------------------------------------------
    "check-stale-transactions": {
        "task": "src.tasks.transaction_checker.mark_stale_transactions_task",
        "schedule": timedelta(minutes=60),
    },

    # --------------------------------------------------------
    # 5. Transaction Queue Manager
    # --------------------------------------------------------
    "sync-queued-transactions": {
        "task": "src.tasks.transaction_queue.process_transaction_queue",
        "schedule": timedelta(seconds=15),
    },

}

