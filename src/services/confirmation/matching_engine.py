from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from src.models.transaction import DepositTransaction, WithdrawalTransaction, AirtimePurchase


def find_matching_transaction(db: Session, parsed: dict):
    tx_type = parsed.get("transaction_type")
    msisdn = parsed.get("msisdn")
    amount = parsed.get("amount")

    model_map = {
        "cashin": DepositTransaction,
        "cashout": WithdrawalTransaction,
        "airtime": AirtimePurchase,
    }

    Model = model_map.get(tx_type)
    if not Model:
        return None

    # Normalize MSISDN
    if msisdn:
        msisdn = msisdn.strip()

    statuses = ["created", "initiated", "pending", "processing"]

    # --------------------------
    # STRICT MATCH: amount + msisdn + pending status
    # Oldest transaction first → safest
    # --------------------------

    if tx_type == "cashout":
        candidate = (
            db.query(Model)
            .filter(Model.status.in_(statuses))
            .filter(Model.amount == amount)
            .filter(Model.sender == msisdn)
            .order_by(Model.created_at.asc())
            .first()
        )
    else:
        candidate = (
            db.query(Model)
            .filter(Model.status.in_(statuses))
            .filter(Model.amount == amount)
            .filter(Model.recipient == msisdn)
            .order_by(Model.created_at.asc())
            .first()
        )
    if candidate:
        return candidate

    # --------------------------
    # TIMED MATCH: amount + msisdn + within last 2 hours
    # Ensures callbacks arriving slightly late still match
    # --------------------------

    window_start = datetime.now(timezone.utc) - timedelta(hours=2)

    if tx_type == "cashout":
        candidate = (
            db.query(Model)
            .filter(Model.status.in_(statuses))
            .filter(Model.amount == amount)
            .filter(Model.sender == msisdn)
            .filter(Model.created_at >= window_start)
            .order_by(Model.created_at.asc())
            .first()
        )
    else:
        candidate = (
            db.query(Model)
            .filter(Model.status.in_(statuses))
            .filter(Model.amount == amount)
            .filter(Model.recipient == msisdn)
            .filter(Model.created_at >= window_start)
            .order_by(Model.created_at.asc())
            .first()
        )
    if candidate:
        return candidate

    # --------------------------
    # HARD STOP: No risky fallbacks
    # --------------------------
    
    return None

