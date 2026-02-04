# ----------------- CONFIRM TRANSACTION ----------------- #
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from src.models.transaction import (
    DepositTransaction,
    WithdrawalTransaction,
    AirtimePurchase,
    CompanyCountryBalance,
)

def confirm_transaction(db: Session, transaction, parsed_data, email_obj):
    # 1️⃣ Mark transaction as successful
    transaction.status = "success"
    transaction.validated_at = datetime.now(timezone.utc)

    if parsed_data.get("transaction_id"):
        transaction.service_partner_id = parsed_data["transaction_id"]

    transaction.gateway_response = email_obj.body

    # 2️⃣ Load balance
    if not transaction.balance_id:
        raise ValueError(f"Transaction {transaction.id} has no balance_id")

    balance = db.get(CompanyCountryBalance, transaction.balance_id)
    if not balance:
        raise ValueError(f"Balance {transaction.balance_id} not found")

    transaction.before_balance = balance.available_balance + balance.held_balance

    # 3️⃣ Apply money logic by transaction type
    if isinstance(transaction, (DepositTransaction, AirtimePurchase)):
        # Debit-type: consume held
        balance.held_balance -= transaction.amount

    elif isinstance(transaction, WithdrawalTransaction):
        # Credit-type: directly increase available
        balance.available_balance += transaction.amount

    else:
        raise ValueError(f"Unsupported transaction type {type(transaction)}")

    transaction.after_balance = balance.available_balance + balance.held_balance

    # 4️⃣ Commit
    db.commit()
    db.refresh(transaction)

    return transaction

# from datetime import datetime, timezone
# from sqlalchemy.orm import Session
# from src.models.transaction import (
#     DepositTransaction,
#     WithdrawalTransaction,
#     AirtimePurchase,
#     CompanyCountryBalance,
# )

# def confirm_transaction(db: Session, transaction, parsed_data, email_obj):
#     # ------------------------------------------------
#     # 1. Mark transaction as successful
#     # ------------------------------------------------
#     transaction.status = "success"
#     transaction.validated_at = datetime.now(timezone.utc)

#     if parsed_data.get("transaction_id"):
#         transaction.service_partner_id = parsed_data["transaction_id"]

#     transaction.gateway_response = email_obj.body

#     # ------------------------------------------------
#     # 2. Load balance (shared by all models)
#     # ------------------------------------------------
#     if not transaction.balance_id:
#         raise ValueError(f"Transaction {transaction.id} has no balance_id")

#     balance = db.get(CompanyCountryBalance, transaction.balance_id)
#     if not balance:
#         raise ValueError(f"Balance {transaction.balance_id} not found")

#     transaction.before_balance = balance.available_balance + balance.held_balance

#     # ------------------------------------------------
#     # 3. Apply money logic by transaction type
#     # ------------------------------------------------
#     if isinstance(transaction, (DepositTransaction, AirtimePurchase)):
#         # Money already held → finalize consumption
#         balance.held_balance -= transaction.amount

#     elif isinstance(transaction, WithdrawalTransaction):
#         # Money comes FROM OM → company receives it
#         balance.held_balance -= transaction.amount
#         balance.available_balance += transaction.amount

#     else:
#         raise ValueError(f"Unsupported transaction type {type(transaction)}")

#     transaction.after_balance = balance.available_balance + balance.held_balance

#     # ------------------------------------------------
#     # 4. Commit
#     # ------------------------------------------------
#     db.commit()
#     db.refresh(transaction)

#     return transaction
