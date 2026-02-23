from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from src.models.transaction import DepositTransaction, WithdrawalTransaction, AirtimePurchase
import re
from datetime import datetime, timezone


def extract_datetime_from_reference(ref: str) -> datetime | None:
    """
    Extract datetime from Orange Money reference ID.
    Example: CO260209.1042.C72045
    """
    match = re.search(r'(\d{6})\.(\d{4})', ref)
    if not match:
        return None

    date_part = match.group(1)
    time_part = match.group(2)

    try:
        year = 2000 + int(date_part[:2])
        month = int(date_part[2:4])
        day = int(date_part[4:6])
        hour = int(time_part[:2])
        minute = int(time_part[2:4])
        return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
    except Exception:
        return None


# def find_matching_transaction(db: Session, parsed: dict):
#     tx_type = parsed.get("transaction_type")
#     msisdn = parsed.get("msisdn")
#     amount = parsed.get("amount")

#     model_map = {
#         "cashin": DepositTransaction,
#         "cashout": WithdrawalTransaction,
#         "airtime": AirtimePurchase,
#     }

#     Model = model_map.get(tx_type)
#     if not Model:
#         return None

#     # Normalize MSISDN
#     if msisdn:
#         msisdn = msisdn.strip()

#     statuses = ["created", "initiated", "pending", "processing"]

#     # --------------------------
#     # STRICT MATCH: amount + msisdn + pending status
#     # Oldest transaction first → safest
#     # --------------------------

#     if tx_type == "cashout":
#         candidate = (
#             db.query(Model)
#             .filter(Model.status.in_(statuses))
#             .filter(Model.amount == amount)
#             .filter(Model.sender == msisdn)
#             .order_by(Model.created_at.asc())
#             .first()
#         )
#     else:
#         candidate = (
#             db.query(Model)
#             .filter(Model.status.in_(statuses))
#             .filter(Model.amount == amount)
#             .filter(Model.recipient == msisdn)
#             .order_by(Model.created_at.asc())
#             .first()
#         )
#     if candidate:
#         return candidate

#     # --------------------------
#     # TIMED MATCH: amount + msisdn + within last 2 hours
#     # Ensures callbacks arriving slightly late still match
#     # --------------------------

#     window_start = datetime.now(timezone.utc) - timedelta(hours=2)

#     if tx_type == "cashout":
#         candidate = (
#             db.query(Model)
#             .filter(Model.status.in_(statuses))
#             .filter(Model.amount == amount)
#             .filter(Model.sender == msisdn)
#             .filter(Model.created_at >= window_start)
#             .order_by(Model.created_at.asc())
#             .first()
#         )
#     else:
#         candidate = (
#             db.query(Model)
#             .filter(Model.status.in_(statuses))
#             .filter(Model.amount == amount)
#             .filter(Model.recipient == msisdn)
#             .filter(Model.created_at >= window_start)
#             .order_by(Model.created_at.asc())
#             .first()
#         )
#     if candidate:
#         return candidate

#     # --------------------------
#     # HARD STOP: No risky fallbacks
#     # --------------------------
    
#     return None

# from datetime import timedelta

def find_matching_transaction(db: Session, parsed: dict):
    tx_type = parsed.get("transaction_type")
    msisdn = parsed.get("msisdn")
    amount = parsed.get("amount")
    provider_ref = parsed.get("transaction_id")

    model_map = {
        "cashin": DepositTransaction,
        "cashout": WithdrawalTransaction,
        "airtime": AirtimePurchase,
    }

    Model = model_map.get(tx_type)
    if not Model:
        return None

    provider_dt = extract_datetime_from_reference(provider_ref)
    if not provider_dt:
        return None

    # 1-minute guaranteed max delay
    lower_bound = provider_dt - timedelta(minutes=1)

    query = db.query(Model).filter(
        Model.status.in_(["created", "initiated", "pending", "processing"]),
        Model.amount == amount,
        Model.created_at <= provider_dt, 
        Model.created_at >= lower_bound,
    )

    if tx_type == "cashout":
        query = query.filter(Model.sender == msisdn)
    else:
        query = query.filter(Model.recipient == msisdn)

    return (
        query
        .order_by(Model.created_at.desc())
        .first()
    )