# from decimal import Decimal
# from sqlalchemy.orm import Session
# from datetime import datetime, timezone
# from src.models.transaction import CompanyCountryBalance

# def confirm_transaction(db: Session, transaction, parsed_data, email_obj):
#     """Confirm a transaction and handle balance updates"""
    
#     # 1. Update transaction status and metadata
#     transaction.status = "success"
#     transaction.validated_at = datetime.now(timezone.utc)
    
#     # 2. Store operator transaction ID
#     if parsed_data.get("transaction_id"):
#         transaction.service_partner_id = parsed_data["transaction_id"]
    
#     # 3. Save gateway response (raw email metadata)
#     transaction.gateway_response = email_obj.body
    
#     # 4. Handle balance updates based on transaction type
#     balance = db.query(CompanyCountryBalance).filter(
#         CompanyCountryBalance.id == transaction.destination_balance_id
#     ).first()
    
#     if balance:
#         if transaction.transaction_type == "cashin":
#             # DEPOSIT: Company pays FROM their wallet TO Orange Money account
#             # Company's balance DECREASES (they're spending from their pre-funded account)
#             transaction.before_balance = balance.available_balance + balance.held_balance
#             balance.available_balance -= transaction.amount  # Deduct from company's balance
#             transaction.after_balance = balance.available_balance + balance.held_balance
#             print(f"📥 DEPOSIT: Company paid {transaction.amount} to Orange Money → Balance: {transaction.after_balance}")
            
#         elif transaction.transaction_type == "airtime":
#             # AIRTIME: Company pays FROM their wallet FOR airtime
#             # Company's balance DECREASES (they're spending from their pre-funded account)
#             transaction.before_balance = balance.available_balance + balance.held_balance
#             balance.available_balance -= transaction.amount  # Deduct from company's balance
#             transaction.after_balance = balance.available_balance + balance.held_balance
#             print(f"📱 AIRTIME: Company paid {transaction.amount} for airtime → Balance: {transaction.after_balance}")
            
#         elif transaction.transaction_type == "cashout":
#             # WITHDRAWAL: Orange Money pays TO company's wallet
#             # Company's balance INCREASES (they're receiving money into their pre-funded account)
#             transaction.before_balance = balance.available_balance + balance.held_balance
#             balance.available_balance += transaction.amount  # Add to company's balance
#             transaction.after_balance = balance.available_balance + balance.held_balance
#             print(f"📤 WITHDRAWAL: Company received {transaction.amount} from Orange Money → Balance: {transaction.after_balance}")
    
#     # 5. Commit all changes
#     db.commit()
#     db.refresh(transaction)
#     return transaction

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.models.transaction import (
    DepositTransaction,
    WithdrawalTransaction,
    AirtimePurchase,
    CompanyCountryBalance,
)

def confirm_transaction(db: Session, transaction, parsed_data, email_obj):
    # ------------------------------------------------
    # 1. Mark transaction as successful
    # ------------------------------------------------
    transaction.status = "success"
    transaction.validated_at = datetime.now(timezone.utc)

    if parsed_data.get("transaction_id"):
        transaction.service_partner_id = parsed_data["transaction_id"]

    transaction.gateway_response = email_obj.body

    # ------------------------------------------------
    # 2. Load balance (shared by all models)
    # ------------------------------------------------
    if not transaction.balance_id:
        raise ValueError(f"Transaction {transaction.id} has no balance_id")

    balance = db.get(CompanyCountryBalance, transaction.balance_id)
    if not balance:
        raise ValueError(f"Balance {transaction.balance_id} not found")

    transaction.before_balance = balance.available_balance + balance.held_balance

    # ------------------------------------------------
    # 3. Apply money logic by transaction type
    # ------------------------------------------------
    if isinstance(transaction, (DepositTransaction, AirtimePurchase)):
        # Money already held → finalize consumption
        balance.held_balance -= transaction.amount

    elif isinstance(transaction, WithdrawalTransaction):
        # Money comes FROM OM → company receives it
        balance.held_balance -= transaction.amount
        balance.available_balance += transaction.amount

    else:
        raise ValueError(f"Unsupported transaction type {type(transaction)}")

    transaction.after_balance = balance.available_balance + balance.held_balance

    # ------------------------------------------------
    # 4. Commit
    # ------------------------------------------------
    db.commit()
    db.refresh(transaction)

    return transaction
